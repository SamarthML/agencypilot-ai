"""The ONLY module that talks to LLM providers (see CLAUDE.md).

Features call `generate`, `generate_structured` or `stream` with a `feature` tag. Every call,
successful or not, writes one row to `llm_usage` (tokens, latency, estimated cost, error).
Provider SDK clients are created with their own retries disabled; retries with exponential
backoff happen here so the policy is the same for every provider.
"""

import asyncio
import copy
import json
import logging
import random
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from functools import lru_cache
from typing import Any, Literal, Protocol, get_args

import anthropic
import groq
import openai
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import LlmProvider, Settings, get_settings
from app.core.db import SessionLocal
from app.models.llm_usage import LlmUsage
from app.services.pricing import estimate_cost

logger = logging.getLogger(__name__)

PROVIDER_IDS: tuple[LlmProvider, ...] = get_args(LlmProvider)
PROVIDER_LABELS: dict[LlmProvider, str] = {"groq": "Groq", "openai": "OpenAI", "claude": "Claude"}
PROVIDER_KEY_ENV: dict[LlmProvider, str] = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}
MAX_BACKOFF_SECONDS = 8.0


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


@dataclass(frozen=True)
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    provider: LlmProvider
    model: str
    cost_usd: Decimal
    cached: bool = False


@dataclass(frozen=True)
class StructuredResult[T: BaseModel]:
    data: T
    result: LLMResult


class LLMError(Exception):
    """Base class for errors raised by this module."""


class ProviderNotConfiguredError(LLMError):
    """The selected provider has no API key in backend/.env."""


class ProviderUnavailableError(LLMError):
    """The provider call failed (after retries) or the model declined."""


class LLMOutputError(LLMError):
    """The model's output could not be validated against the requested schema."""


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompletionRequest:
    messages: tuple[ChatMessage, ...]
    system: str | None
    model: str
    max_tokens: int
    temperature: float
    json_schema: dict[str, Any] | None


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class Completion:
    text: str
    usage: Usage


StreamItem = str | Usage


class Provider(Protocol):
    name: LlmProvider
    retryable_errors: tuple[type[BaseException], ...]

    async def complete(self, request: CompletionRequest) -> Completion: ...

    def stream(self, request: CompletionRequest) -> AsyncIterator[StreamItem]: ...


JSON_INSTRUCTION = (
    "Respond with a single JSON object and nothing else (no prose, no code fences). "
    "It must match this JSON schema:\n{schema}"
)


def _system_with_schema(system: str | None, schema: dict[str, Any] | None) -> str | None:
    if schema is None:
        return system
    instruction = JSON_INSTRUCTION.format(schema=json.dumps(schema, separators=(",", ":")))
    return f"{system}\n\n{instruction}" if system else instruction


def _chunk_usage(chunk: Any) -> Usage | None:
    """OpenAI reports stream usage on `chunk.usage`; Groq on `chunk.x_groq.usage`."""
    usage = getattr(chunk, "usage", None) or getattr(getattr(chunk, "x_groq", None), "usage", None)
    if usage is None:
        return None
    return Usage(usage.prompt_tokens or 0, usage.completion_tokens or 0)


class OpenAICompatibleProvider:
    """Chat Completions API, shared by OpenAI and Groq (their SDKs expose the same surface)."""

    def __init__(
        self,
        name: LlmProvider,
        client: openai.AsyncOpenAI | groq.AsyncGroq,
        retryable_errors: tuple[type[BaseException], ...],
        stream_usage_option: bool,
    ) -> None:
        self.name = name
        self.retryable_errors = retryable_errors
        self._client = client
        # OpenAI needs stream_options to report usage; Groq always sends it in `x_groq`.
        self._stream_usage_option = stream_usage_option

    def _params(self, request: CompletionRequest) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        system = _system_with_schema(request.system, request.json_schema)
        if system:
            messages.append({"role": "system", "content": system})
        messages.extend({"role": m.role, "content": m.content} for m in request.messages)
        params: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_completion_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.json_schema is not None:
            params["response_format"] = {"type": "json_object"}
        return params

    async def complete(self, request: CompletionRequest) -> Completion:
        response = await self._client.chat.completions.create(**self._params(request))
        text = (response.choices[0].message.content or "") if response.choices else ""
        return Completion(text=text, usage=_chunk_usage(response) or Usage(0, 0))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamItem]:
        params: dict[str, Any] = {**self._params(request), "stream": True}
        if self._stream_usage_option:
            params["stream_options"] = {"include_usage": True}
        response = await self._client.chat.completions.create(**params)
        usage: Usage | None = None
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            usage = _chunk_usage(chunk) or usage
        yield usage or Usage(0, 0)


class AnthropicProvider:
    """Claude Messages API. `system` is a separate parameter and `max_tokens` is required."""

    name: LlmProvider = "claude"

    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        self._client = client
        self.retryable_errors = _retryable(anthropic)

    def _params(self, request: CompletionRequest) -> dict[str, Any]:
        # Low effort keeps short analytical answers cheap and fast. Temperature is deliberately
        # not sent: current Claude models reject non-default sampling parameters.
        output_config: dict[str, Any] = {"effort": "low"}
        if request.json_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": request.json_schema}
        params: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "output_config": output_config,
        }
        if request.system:
            params["system"] = request.system
        return params

    async def complete(self, request: CompletionRequest) -> Completion:
        message = await self._client.messages.create(**self._params(request))
        _raise_if_refused(message)
        text = "".join(block.text for block in message.content if block.type == "text")
        return Completion(text, Usage(message.usage.input_tokens, message.usage.output_tokens))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamItem]:
        async with self._client.messages.stream(**self._params(request)) as response:
            async for text in response.text_stream:
                yield text
            message = await response.get_final_message()
        _raise_if_refused(message)
        yield Usage(message.usage.input_tokens, message.usage.output_tokens)


def _raise_if_refused(message: Any) -> None:
    if getattr(message, "stop_reason", None) == "refusal":
        raise ProviderUnavailableError("Claude declined this request.")


def _retryable(sdk: Any) -> tuple[type[BaseException], ...]:
    """Rate limits, timeouts, connection drops and 5xx errors are worth retrying."""
    names = ("RateLimitError", "APITimeoutError", "APIConnectionError", "InternalServerError")
    return tuple(getattr(sdk, name) for name in names if hasattr(sdk, name))


@lru_cache(maxsize=8)
def _make_provider(name: LlmProvider, api_key: str, timeout: float) -> Provider:
    if name == "groq":
        client = groq.AsyncGroq(api_key=api_key, timeout=timeout, max_retries=0)
        return OpenAICompatibleProvider("groq", client, _retryable(groq), stream_usage_option=False)
    if name == "openai":
        client = openai.AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=0)
        return OpenAICompatibleProvider(
            "openai", client, _retryable(openai), stream_usage_option=True
        )
    claude = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=0)
    return AnthropicProvider(claude)


def build_provider(name: LlmProvider, settings: Settings) -> Provider:
    key = settings.api_key_for(name)
    if key is None:
        raise ProviderNotConfiguredError(
            f"{PROVIDER_LABELS[name]} is not configured: add {PROVIDER_KEY_ENV[name]} "
            "to backend/.env and restart the API."
        )
    return _make_provider(name, key.get_secret_value(), settings.llm_timeout_seconds)


def available_providers(settings: Settings) -> dict[LlmProvider, bool]:
    return {name: settings.api_key_for(name) is not None for name in PROVIDER_IDS}


# ---------------------------------------------------------------------------
# Usage logging
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsageRecord:
    feature: str
    provider: LlmProvider
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: Decimal = Decimal("0")
    success: bool = True
    error: str | None = None
    cached: bool = False


def write_usage(record: UsageRecord) -> None:
    """Persist one usage row. Logging must never break the user-facing call."""
    try:
        with SessionLocal() as db:
            db.add(LlmUsage(**asdict(record)))
            db.commit()
    except SQLAlchemyError:
        logger.exception("Failed to write llm_usage row for feature=%s", record.feature)


async def _record(record: UsageRecord) -> None:
    await asyncio.to_thread(write_usage, record)


async def record_cache_hit(
    feature: str, provider: LlmProvider, model: str, latency_ms: int = 0
) -> None:
    """A response served from an app-level cache: logged with zero tokens and zero cost."""
    await _record(UsageRecord(feature, provider, model, latency_ms=latency_ms, cached=True))


# ---------------------------------------------------------------------------
# Calls
# ---------------------------------------------------------------------------

_sleep = asyncio.sleep  # patched in tests


def _backoff_delay(attempt: int) -> float:
    return min(MAX_BACKOFF_SECONDS, 0.5 * 2**attempt) + random.uniform(0, 0.25)


async def _with_retries[R](
    call: Callable[[], Awaitable[R]], retryable: tuple[type[BaseException], ...], max_retries: int
) -> R:
    for attempt in range(max_retries + 1):
        try:
            return await call()
        except retryable as exc:
            if attempt == max_retries:
                raise
            delay = _backoff_delay(attempt)
            logger.warning(
                "LLM call failed (%s); retry %d in %.1fs", type(exc).__name__, attempt + 1, delay
            )
            await _sleep(delay)
    raise AssertionError("unreachable")


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _as_llm_error(exc: Exception, provider: LlmProvider) -> LLMError:
    if isinstance(exc, LLMError):
        return exc
    return ProviderUnavailableError(f"{PROVIDER_LABELS[provider]} request failed: {exc}")


def _error_text(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:500]


def _prepare(
    messages: Sequence[ChatMessage],
    system: str | None,
    provider: LlmProvider | None,
    model: str | None,
    max_tokens: int,
    temperature: float,
    json_schema: dict[str, Any] | None,
) -> tuple[Settings, LlmProvider, CompletionRequest]:
    if not messages:
        raise ValueError("At least one message is required")
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    settings = get_settings()
    provider_name = provider or settings.default_provider
    request = CompletionRequest(
        messages=tuple(messages),
        system=system,
        model=model or settings.model_for(provider_name),
        max_tokens=max_tokens,
        temperature=temperature,
        json_schema=json_schema,
    )
    return settings, provider_name, request


async def generate(
    messages: Sequence[ChatMessage],
    *,
    feature: str,
    system: str | None = None,
    provider: LlmProvider | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    json_schema: dict[str, Any] | None = None,
) -> LLMResult:
    """One completion. Raises an LLMError subclass on failure; usage is logged either way."""
    settings, provider_name, request = _prepare(
        messages, system, provider, model, max_tokens, temperature, json_schema
    )
    started = time.perf_counter()
    try:
        impl = build_provider(provider_name, settings)
        completion = await _with_retries(
            lambda: impl.complete(request), impl.retryable_errors, settings.llm_max_retries
        )
    except Exception as exc:
        failure = UsageRecord(
            feature, provider_name, request.model,
            latency_ms=_elapsed_ms(started), success=False, error=_error_text(exc),
        )  # fmt: skip
        await _record(failure)
        raise _as_llm_error(exc, provider_name) from exc

    result = LLMResult(
        text=completion.text,
        input_tokens=completion.usage.input_tokens,
        output_tokens=completion.usage.output_tokens,
        latency_ms=_elapsed_ms(started),
        provider=provider_name,
        model=request.model,
        cost_usd=estimate_cost(
            request.model, completion.usage.input_tokens, completion.usage.output_tokens
        ),
    )
    await _record(_success_record(feature, result))
    return result


def _success_record(feature: str, result: LLMResult) -> UsageRecord:
    return UsageRecord(
        feature=feature,
        provider=result.provider,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
        cost_usd=result.cost_usd,
    )


async def stream(
    messages: Sequence[ChatMessage],
    *,
    feature: str,
    system: str | None = None,
    provider: LlmProvider | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> AsyncIterator[str]:
    """Yield text chunks. Usage is recorded when the stream ends, fails or is abandoned.

    Retries only happen before the first chunk; once text has been sent it can't be un-sent.
    """
    settings, provider_name, request = _prepare(
        messages, system, provider, model, max_tokens, temperature, None
    )
    started = time.perf_counter()
    usage = Usage(0, 0)
    error: BaseException | None = None
    try:
        impl = build_provider(provider_name, settings)
        async for item in _stream_with_retries(impl, request, settings.llm_max_retries):
            if isinstance(item, Usage):
                usage = item
            else:
                yield item
    except GeneratorExit:
        error = GeneratorExit("stream closed by client before completion")
        raise
    except Exception as exc:
        error = exc
        raise _as_llm_error(exc, provider_name) from exc
    finally:
        await _record(_stream_record(feature, provider_name, request.model, usage, started, error))


async def _stream_with_retries(
    impl: Provider, request: CompletionRequest, max_retries: int
) -> AsyncIterator[StreamItem]:
    for attempt in range(max_retries + 1):
        started_output = False
        try:
            async for item in impl.stream(request):
                started_output = True
                yield item
            return
        except impl.retryable_errors as exc:
            if started_output or attempt == max_retries:
                raise
            delay = _backoff_delay(attempt)
            logger.warning(
                "LLM stream failed (%s); retry %d in %.1fs", type(exc).__name__, attempt + 1, delay
            )
            await _sleep(delay)


def _stream_record(
    feature: str,
    provider: LlmProvider,
    model: str,
    usage: Usage,
    started: float,
    error: BaseException | None,
) -> UsageRecord:
    return UsageRecord(
        feature=feature,
        provider=provider,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        latency_ms=_elapsed_ms(started),
        cost_usd=estimate_cost(model, usage.input_tokens, usage.output_tokens),
        success=error is None,
        error=_error_text(error) if error else None,
    )


# ---------------------------------------------------------------------------
# Structured (JSON) output
# ---------------------------------------------------------------------------

_UNSUPPORTED_SCHEMA_KEYS = {"title", "default", "minItems", "maxItems", "minLength", "maxLength"}


def json_schema_for(model: type[BaseModel]) -> dict[str, Any]:
    """A strict, self-contained JSON schema for structured output.

    Inlines $refs, closes every object (additionalProperties: false, all fields required) and
    drops keywords that structured-output engines don't all support. Pydantic still enforces
    the full constraints when the reply is validated.
    """
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})
    return _clean_schema(schema, defs)


_RANGE_KEYWORDS = (("minItems", "maxItems", "items"), ("minLength", "maxLength", "characters"))


def _range_hint(low: int | None, high: int | None, unit: str) -> str | None:
    if low is not None and low == high:
        return f"exactly {low} {unit}"
    parts = [f"at least {low} {unit}"] if low is not None else []
    if high is not None:
        parts.append(f"at most {high} {unit}")
    return " and ".join(parts) or None


def _constraint_hint(node: dict[str, Any]) -> str | None:
    """Dropped length/size keywords, restated in words so the model still sees them."""
    hints = [_range_hint(node.get(lo), node.get(hi), unit) for lo, hi, unit in _RANGE_KEYWORDS]
    return "; ".join(h for h in hints if h) or None


def _clean_schema(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_clean_schema(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _clean_schema(copy.deepcopy(defs[node["$ref"].rsplit("/", 1)[-1]]), defs)
    cleaned = {
        k: _clean_schema(v, defs) for k, v in node.items() if k not in _UNSUPPORTED_SCHEMA_KEYS
    }
    if "properties" in node:
        # Property NAMES are data, not keywords: a field called "title" must survive.
        cleaned["properties"] = {
            name: _clean_schema(sub, defs) for name, sub in node["properties"].items()
        }
    hint = _constraint_hint(node)
    if hint:
        description = cleaned.get("description")
        cleaned["description"] = f"{description} ({hint})" if description else hint.capitalize()
    if cleaned.get("type") == "object" and "properties" in cleaned:
        cleaned["required"] = list(cleaned["properties"])
        cleaned["additionalProperties"] = False
    return cleaned


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0]
    return stripped.strip()


def _combine(results: Sequence[LLMResult]) -> LLMResult:
    """Merge the attempts of one logical call (e.g. a JSON repair) into a single result."""
    last = results[-1]
    return replace(
        last,
        input_tokens=sum(r.input_tokens for r in results),
        output_tokens=sum(r.output_tokens for r in results),
        latency_ms=sum(r.latency_ms for r in results),
        cost_usd=sum((r.cost_usd for r in results), Decimal("0")),
    )


def _repair_messages(
    messages: Sequence[ChatMessage], bad_output: str, error: ValidationError
) -> list[ChatMessage]:
    problems = "; ".join(
        f"{'.'.join(map(str, e['loc'])) or 'reply'}: {e['msg']}" for e in error.errors()[:5]
    )
    return [
        *messages,
        ChatMessage(role="assistant", content=bad_output.strip() or "(empty reply)"),
        ChatMessage(
            role="user",
            content=f"That reply did not match the required JSON schema ({problems}). "
            "Reply again with only the corrected JSON object.",
        ),
    ]


async def generate_structured[T: BaseModel](
    messages: Sequence[ChatMessage],
    output_model: type[T],
    *,
    feature: str,
    system: str | None = None,
    provider: LlmProvider | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    max_repairs: int = 1,
) -> StructuredResult[T]:
    """Generate JSON validated against `output_model`, asking the model to repair it once."""
    schema = json_schema_for(output_model)
    attempt_messages = list(messages)
    results: list[LLMResult] = []
    for _ in range(max_repairs + 1):
        result = await generate(
            attempt_messages,
            feature=feature,
            system=system,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            json_schema=schema,
        )
        results.append(result)
        try:
            data = output_model.model_validate_json(_strip_code_fences(result.text))
            return StructuredResult(data=data, result=_combine(results))
        except ValidationError as exc:
            logger.warning("Invalid structured output for feature=%s: %s", feature, exc)
            attempt_messages = _repair_messages(messages, result.text, exc)
    raise LLMOutputError("The model returned invalid JSON twice. Try again or switch models.")
