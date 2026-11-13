"""Turn llm.py results into the `LlmCallMeta` shown under every AI response."""

import time

from app.core.config import LlmProvider
from app.schemas.common import LlmCallMeta
from app.services import llm


def call_meta(result: llm.LLMResult) -> LlmCallMeta:
    return LlmCallMeta(
        provider=result.provider,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
        cost_usd=float(result.cost_usd),
        cached=result.cached,
    )


async def cache_hit_meta(
    feature: str, provider: LlmProvider, model: str, started: float
) -> LlmCallMeta:
    """Log a cache hit to llm_usage (cached=true, cost 0) and return its meta."""
    latency_ms = int((time.perf_counter() - started) * 1000)
    await llm.record_cache_hit(feature, provider, model, latency_ms)
    return LlmCallMeta(
        provider=provider, model=model, input_tokens=0, output_tokens=0,
        latency_ms=latency_ms, cost_usd=0.0, cached=True,
    )  # fmt: skip
