"""llm.py with a fake provider: no SDK client, no network, usage rows captured in memory."""

from decimal import Decimal

import pytest
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.services import llm
from app.services.llm import ChatMessage, Usage
from tests.fakes import FakeProvider, TransientError, ok, use_provider

MESSAGES = [ChatMessage(role="user", content="Summarise the KPIs.")]


async def test_generate_returns_text_and_logs_usage(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider([ok()]))

    result = await llm.generate(MESSAGES, feature="insights")

    assert result.text == "All good."
    assert result.provider == "groq"
    assert result.model == "openai/gpt-oss-120b"
    # (1000 * 0.15 + 200 * 0.60) / 1e6
    assert result.cost_usd == Decimal("0.000270")
    [row] = usage_rows
    assert row.feature == "insights"
    assert (row.input_tokens, row.output_tokens, row.success) == (1000, 200, True)
    assert row.cost_usd == result.cost_usd


async def test_generate_passes_system_and_limits_to_provider(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok()]))

    await llm.generate(MESSAGES, feature="x", system="Be brief.", max_tokens=50, model="m-1")

    [request] = fake.requests
    assert (request.system, request.max_tokens, request.model) == ("Be brief.", 50, "m-1")


async def test_transient_error_is_retried(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([TransientError("429"), ok()]))

    result = await llm.generate(MESSAGES, feature="insights")

    assert result.text == "All good."
    assert len(fake.requests) == 2
    assert [row.success for row in usage_rows] == [True]


async def test_retries_exhausted_raises_and_logs_failure(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([TransientError("503")] * 3))

    with pytest.raises(llm.ProviderUnavailableError):
        await llm.generate(MESSAGES, feature="insights")

    assert len(fake.requests) == 3  # 1 attempt + LLM_MAX_RETRIES (2)
    [row] = usage_rows
    assert row.success is False
    assert row.error is not None and "TransientError" in row.error
    assert row.cost_usd == Decimal("0")


async def test_non_retryable_error_fails_fast(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ValueError("bad request")]))

    with pytest.raises(llm.ProviderUnavailableError):
        await llm.generate(MESSAGES, feature="insights")

    assert len(fake.requests) == 1


async def test_unconfigured_provider_raises_and_logs(usage_rows: list[llm.UsageRecord]) -> None:
    with pytest.raises(llm.ProviderNotConfiguredError, match="OPENAI_API_KEY"):
        await llm.generate(MESSAGES, feature="insights", provider="openai")

    [row] = usage_rows
    assert (row.provider, row.model, row.success) == ("openai", "gpt-4o-mini", False)


def test_available_providers_reflects_configured_keys() -> None:
    settings = Settings(_env_file=None, groq_api_key="k", openai_api_key="", anthropic_api_key="")

    assert llm.available_providers(settings) == {"groq": True, "openai": False, "claude": False}


def test_empty_messages_rejected() -> None:
    with pytest.raises(ValueError):
        llm._prepare([], None, None, None, 100, 0.2, None)


async def test_stream_yields_text_and_logs_usage_at_end(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider(stream_items=["Hel", "lo", Usage(50, 2)]))

    chunks = [chunk async for chunk in llm.stream(MESSAGES, feature="copilot")]

    assert chunks == ["Hel", "lo"]
    [row] = usage_rows
    assert (row.feature, row.input_tokens, row.output_tokens, row.success) == (
        "copilot",
        50,
        2,
        True,
    )


async def test_stream_reports_result_on_completion_only(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider(stream_items=["Hel", "lo", Usage(1000, 200)]))
    results: list[llm.LLMResult] = []

    async for _ in llm.stream(MESSAGES, feature="copilot", on_complete=results.append):
        assert results == []  # not called until the stream has finished

    [result] = results
    assert (result.text, result.input_tokens, result.output_tokens) == ("Hello", 1000, 200)
    assert result.cost_usd == usage_rows[0].cost_usd > 0


async def test_stream_failure_skips_on_complete(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider(stream_items=["partial", TransientError("drop")]))
    results: list[llm.LLMResult] = []

    with pytest.raises(llm.ProviderUnavailableError):
        async for _ in llm.stream(MESSAGES, feature="copilot", on_complete=results.append):
            pass

    assert results == []


async def test_stream_failure_is_logged(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider(stream_items=["partial", TransientError("drop")]))

    with pytest.raises(llm.ProviderUnavailableError):
        async for _ in llm.stream(MESSAGES, feature="copilot"):
            pass

    [row] = usage_rows
    assert row.success is False


class Verdict(BaseModel):
    headline: str
    score: int


async def test_generate_structured_parses_json(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider([ok('```json\n{"headline": "Up", "score": 3}\n```')]))

    structured = await llm.generate_structured(MESSAGES, Verdict, feature="insights")

    assert structured.data == Verdict(headline="Up", score=3)


async def test_generate_structured_repairs_once_and_sums_cost(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(
        monkeypatch, FakeProvider([ok('{"headline": "Up"}'), ok('{"headline": "Up", "score": 1}')])
    )

    structured = await llm.generate_structured(MESSAGES, Verdict, feature="insights")

    assert structured.data.score == 1
    assert structured.result.input_tokens == 2000
    assert structured.result.cost_usd == sum((r.cost_usd for r in usage_rows), Decimal("0"))
    assert "did not match" in fake.requests[1].messages[-1].content


async def test_generate_structured_gives_up_after_repair(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider([ok("nope"), ok("still nope")]))

    with pytest.raises(llm.LLMOutputError):
        await llm.generate_structured(MESSAGES, Verdict, feature="insights")

    assert len(usage_rows) == 2


class Outer(BaseModel):
    items: list[Verdict]


def test_json_schema_inlines_refs_and_closes_objects() -> None:
    schema = llm.json_schema_for(Outer)

    item = schema["properties"]["items"]["items"]
    assert "$defs" not in schema and "$ref" not in str(schema)
    assert item["additionalProperties"] is False
    assert item["required"] == ["headline", "score"]
    assert "title" not in item


class Fix(BaseModel):
    title: str = Field(max_length=120)
    default: str


class Report(BaseModel):
    fixes: list[Fix] = Field(min_length=5, max_length=5)
    keywords: list[str] = Field(description="Search phrases", min_length=8, max_length=8)


def test_json_schema_keeps_properties_named_like_keywords() -> None:
    """Regression: a field called "title" was stripped along with the `title` keyword."""
    fix = llm.json_schema_for(Report)["properties"]["fixes"]["items"]

    assert set(fix["properties"]) == {"title", "default"}
    assert fix["required"] == ["title", "default"]


def test_json_schema_restates_dropped_constraints_in_descriptions() -> None:
    props = llm.json_schema_for(Report)["properties"]

    assert props["fixes"]["description"] == "Exactly 5 items"
    assert props["keywords"]["description"] == "Search phrases (exactly 8 items)"
    assert "maxItems" not in props["keywords"]
    assert props["fixes"]["items"]["properties"]["title"]["description"] == "At most 120 characters"


async def test_cache_hit_logged_with_zero_cost(usage_rows: list[llm.UsageRecord]) -> None:
    await llm.record_cache_hit("insights_summary", "groq", "openai/gpt-oss-120b")

    [row] = usage_rows
    assert row.cached is True
    assert row.cost_usd == Decimal("0")
    assert row.input_tokens == row.output_tokens == 0


def test_write_usage_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_session() -> None:
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    monkeypatch.setattr(llm, "SessionLocal", broken_session)

    llm.write_usage(llm.UsageRecord("insights", "groq", "openai/gpt-oss-120b"))
