"""Usage aggregation math on a hand-built llm_usage frame (no database)."""

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from app.services import usage

TODAY = date(2026, 11, 13)


def row(
    when: date,
    feature: str,
    *,
    model: str = "openai/gpt-oss-120b",
    provider: str = "groq",
    tokens: tuple[int, int] = (0, 0),
    latency: int = 0,
    cost: float = 0.0,
    success: bool = True,
    cached: bool = False,
    skipped: bool = False,
    saved: float | None = None,
) -> tuple[object, ...]:
    created = datetime(when.year, when.month, when.day, 12, 0, tzinfo=UTC)
    return (
        created, feature, provider, model, tokens[0], tokens[1], latency, cost, success,
        cached, skipped, saved,
    )  # fmt: skip


NOV_13, NOV_12, NOV_10, OCT_01 = (
    date(2026, 11, 13), date(2026, 11, 12), date(2026, 11, 10), date(2026, 10, 1),
)  # fmt: skip

ROWS = [
    # Two SEO calls, a cache hit that saved the first call's cost, and a failed call.
    row(NOV_13, "seo_audit", tokens=(1000, 500), latency=1000, cost=0.004),
    row(NOV_13, "seo_audit", tokens=(1000, 300), latency=3000, cost=0.002),
    row(NOV_13, "seo_audit", latency=5, cached=True, saved=0.004),
    row(NOV_13, "seo_audit", latency=900, success=False),
    # A Copilot answer and a guardrail skip.
    row(NOV_12, "copilot", tokens=(2000, 100), latency=2000, cost=0.001),
    row(NOV_12, "copilot", latency=40, skipped=True),
    # An OpenAI insights summary.
    row(
        NOV_10,
        "insights_summary",
        provider="openai",
        model="gpt-4o-mini",
        tokens=(800, 200),
        latency=4000,
        cost=0.0003,
    ),  # fmt: skip
    # Outside the 7- and 30-day windows.
    row(OCT_01, "report", tokens=(5000, 2000), latency=6000, cost=0.01),
]


@pytest.fixture
def frame() -> pd.DataFrame:
    return usage.to_frame(ROWS)


def test_totals_separate_calls_hits_and_skips(frame: pd.DataFrame) -> None:
    totals = usage.summarize(frame, 7, TODAY).totals

    assert totals.requests == 7
    assert totals.llm_calls == 5  # 3 SEO (incl. the failure) + copilot + insights
    assert (totals.cache_hits, totals.guardrail_skips, totals.errors) == (1, 1, 1)
    assert (totals.input_tokens, totals.output_tokens, totals.total_tokens) == (4800, 1100, 5900)
    assert totals.cost_usd == pytest.approx(0.0073)
    assert totals.cache_hit_rate == pytest.approx(round(1 / 6, 4))
    assert totals.saved_usd == pytest.approx(0.004)
    assert totals.saved_includes_estimates is False


def test_latency_uses_successful_provider_calls_only(frame: pd.DataFrame) -> None:
    totals = usage.summarize(frame, 7, TODAY).totals

    # 1000, 3000, 2000, 4000 ms: the cache hit, skip and failed call are excluded.
    assert totals.avg_latency_ms == 2500.0
    assert totals.p95_latency_ms == pytest.approx(3850.0)  # linear interpolation


def test_window_filters_rows_and_fills_every_day(frame: pd.DataFrame) -> None:
    week = usage.summarize(frame, 7, TODAY)
    everything = usage.summarize(frame, "all", TODAY)

    assert (week.start, week.end) == (date(2026, 11, 7), TODAY)
    assert [d.date for d in week.by_day] == [date(2026, 11, d) for d in range(7, 14)]
    by_date = {d.date: d for d in week.by_day}
    assert by_date[NOV_13].llm_calls == 3 and by_date[NOV_13].cache_hits == 1
    assert by_date[NOV_13].errors == 1 and by_date[NOV_13].cost_usd == pytest.approx(0.006)
    assert by_date[NOV_12].guardrail_skips == 1
    assert by_date[date(2026, 11, 11)].llm_calls == 0  # gaps are zero-filled
    assert everything.start == OCT_01 and len(everything.by_day) == 44
    assert everything.totals.cost_usd == pytest.approx(0.0173)


def test_by_feature_and_by_model(frame: pd.DataFrame) -> None:
    summary = usage.summarize(frame, 30, TODAY)
    features = {f.feature: f for f in summary.by_feature}

    assert [f.feature for f in summary.by_feature] == ["seo_audit", "copilot", "insights_summary"]
    seo = features["seo_audit"]
    assert (seo.requests, seo.llm_calls, seo.cache_hits, seo.errors) == (4, 3, 1, 1)
    assert seo.cost_usd == pytest.approx(0.006) and seo.avg_latency_ms == 2000.0
    assert features["copilot"].guardrail_skips == 1

    models = {(m.provider, m.model): m for m in summary.by_model}
    groq = models[("groq", "openai/gpt-oss-120b")]
    assert (groq.llm_calls, groq.input_tokens, groq.cost_usd) == (4, 4000, pytest.approx(0.007))
    assert models[("openai", "gpt-4o-mini")].cost_usd == pytest.approx(0.0003)
    assert sum(m.cost_usd for m in summary.by_model) == pytest.approx(summary.totals.cost_usd)


def test_older_hits_without_saved_cost_are_estimated() -> None:
    rows = [
        row(NOV_13, "insights_summary", cost=0.002, latency=100),
        row(NOV_13, "insights_summary", cost=0.004, latency=100),
        row(NOV_13, "insights_summary", cached=True),  # logged before saved_cost_usd existed
        row(NOV_13, "insights_summary", cached=True, saved=0.005),
    ]

    totals = usage.summarize(usage.to_frame(rows), 7, TODAY).totals

    assert totals.saved_usd == pytest.approx(0.005 + 0.003)  # recorded + mean of the calls
    assert totals.saved_includes_estimates is True


def test_empty_frame_is_all_zeros() -> None:
    summary = usage.summarize(usage.to_frame([]), 30, TODAY)

    assert summary.totals.requests == 0 and summary.totals.cost_usd == 0
    assert summary.totals.avg_latency_ms is None and summary.totals.cache_hit_rate is None
    assert summary.by_feature == [] and summary.by_model == []
    assert len(summary.by_day) == 30 and all(d.llm_calls == 0 for d in summary.by_day)


def test_feature_names_match_the_usage_page_labels() -> None:
    """Every LLM feature logs under a stable name; frontend/lib/usage.ts labels these names."""
    from app.services import copilot, insights_ai, reports, seo_audit

    assert {
        insights_ai.SUMMARY_FEATURE,
        insights_ai.ASK_FEATURE,
        seo_audit.FEATURE,
        copilot.FEATURE,
        copilot.REWRITE_FEATURE,
        reports.FEATURE,
    } == {"insights_summary", "insights_ask", "seo_audit", "copilot", "copilot_rewrite", "report"}
