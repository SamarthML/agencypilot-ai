"""AI summary / Q&A: grounding, caching and usage logging, with the provider mocked."""

import re
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.schemas.insights import InsightsSnapshot
from app.services import analytics, insights, insights_ai, llm
from tests.fakes import FakeProvider, ok, use_provider

SAMPLE_CSV = Path(__file__).resolve().parents[2] / "sample_data" / "marketing_demo.csv"
SUMMARY_JSON = (
    '{"headline": "Organic traffic fell 33.2%.", "highlights": ["Organic sessions down 33.2%."],'
    ' "concerns": [], "recommendations": ["Audit organic rankings."]}'
)
DATASET_ID = uuid.uuid4()
NO_DB = cast(Session, None)  # load_snapshot is patched, so no DB session is used


@pytest.fixture(scope="module")
def apex_snapshot() -> InsightsSnapshot:
    clients = analytics.parse_multi_client_csv(SAMPLE_CSV.read_bytes())
    apex = next(c for c in clients if c.client_id == "apex-fitness")
    return analytics.build_snapshot(apex.frame, 30)


@pytest.fixture(autouse=True)
def patched_data(monkeypatch: pytest.MonkeyPatch, apex_snapshot: InsightsSnapshot) -> None:
    dataset = SimpleNamespace(id=DATASET_ID, client_name="Apex Fitness")
    monkeypatch.setattr(
        insights, "load_snapshot", lambda db, client_id, days: (dataset, apex_snapshot)
    )
    insights_ai.summary_cache().clear()


# --- Grounding -------------------------------------------------------------------


def prompt_text(messages: list[llm.ChatMessage]) -> str:
    return "\n".join(m.content for m in messages)


def test_prompt_contains_only_computed_aggregates(apex_snapshot: InsightsSnapshot) -> None:
    context = insights_ai.build_context("Apex Fitness", apex_snapshot)
    prompt = prompt_text(insights_ai.build_summary_messages(context))

    period = apex_snapshot.period
    boundaries = {
        str(d) for d in (period.start, period.end, period.previous_start, period.previous_end)
    }
    assert set(re.findall(r"\d{4}-\d{2}-\d{2}", prompt)) <= boundaries  # no per-day rows
    assert "by_channel" not in prompt and "timeseries" not in prompt
    assert "Organic sessions down 33.2%" in prompt
    assert "44062" in prompt  # the total sessions KPI


def test_prompt_is_small(apex_snapshot: InsightsSnapshot) -> None:
    context = insights_ai.build_context("Apex Fitness", apex_snapshot)

    assert len(prompt_text(insights_ai.build_summary_messages(context))) < 4000


def test_system_prompts_forbid_invented_numbers() -> None:
    for prompt in (insights_ai.SUMMARY_SYSTEM_PROMPT, insights_ai.ASK_SYSTEM_PROMPT):
        assert "Never invent" in prompt


# --- Summary + cache --------------------------------------------------------------


async def test_summary_calls_llm_then_serves_from_cache(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok(SUMMARY_JSON, 1200, 300)]))

    first = await insights_ai.summarize(NO_DB, "apex-fitness", 30, "groq")
    second = await insights_ai.summarize(NO_DB, "apex-fitness", 30, "groq")

    assert len(fake.requests) == 1
    assert first.summary.headline == "Organic traffic fell 33.2%."
    assert first.meta.cached is False and first.meta.cost_usd > 0
    assert second.summary == first.summary
    assert second.meta.cached is True
    assert second.meta.cost_usd == 0 and second.meta.input_tokens == 0
    assert [(r.feature, r.cached) for r in usage_rows] == [
        ("insights_summary", False),
        ("insights_summary", True),
    ]
    # The hit costs nothing and records what the original call cost (the money saved).
    assert usage_rows[1].cost_usd == 0
    assert usage_rows[1].saved_cost_usd == pytest.approx(usage_rows[0].cost_usd)


async def test_summary_request_is_grounded_and_structured(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok(SUMMARY_JSON)]))

    await insights_ai.summarize(NO_DB, "apex-fitness", 30, "groq")

    [request] = fake.requests
    assert request.system == insights_ai.SUMMARY_SYSTEM_PROMPT
    assert request.json_schema is not None
    assert "notable_changes" in request.messages[0].content


async def test_cache_is_keyed_by_period_and_provider(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok(SUMMARY_JSON)] * 2))

    await insights_ai.summarize(NO_DB, "apex-fitness", 30, "groq")
    await insights_ai.summarize(NO_DB, "apex-fitness", 7, "groq")

    assert len(fake.requests) == 2


async def test_failed_summary_is_not_cached(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok("nope"), ok("nope"), ok(SUMMARY_JSON)]))

    with pytest.raises(llm.LLMOutputError):
        await insights_ai.summarize(NO_DB, "apex-fitness", 30, "groq")
    result = await insights_ai.summarize(NO_DB, "apex-fitness", 30, "groq")

    assert result.meta.cached is False
    assert len(fake.requests) == 3


# --- Ask ------------------------------------------------------------------------


async def test_ask_answers_from_context(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok("  Organic, down 33.2%.  ")]))

    response = await insights_ai.ask(NO_DB, "apex-fitness", 30, "Which channel dropped?", "groq")

    assert response.answer == "Organic, down 33.2%."
    assert "<question>Which channel dropped?</question>" in fake.requests[0].messages[0].content
    assert usage_rows[0].feature == "insights_ask"


async def test_ask_rejects_empty_model_answer(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider([ok("   ")]))

    with pytest.raises(llm.LLMOutputError):
        await insights_ai.ask(NO_DB, "apex-fitness", 30, "Anything?", "groq")
