"""LLM usage and cost analytics over `llm_usage` (Pandas).

Row kinds: a provider call (`cached` and `skipped` false; may have failed), a cache hit
(`cached`, cost 0, `saved_cost_usd` = the original call's cost) and a guardrail skip (`skipped`,
cost 0). `summarize` is pure so the aggregation math is unit-tested without a database.
"""

from datetime import UTC, date, datetime, time, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.llm_usage import LlmUsage
from app.schemas.usage import (
    DailyUsage,
    FeatureUsage,
    ModelUsage,
    UsageCall,
    UsageDays,
    UsageSummary,
    UsageTotals,
)

COLUMNS = (
    "created_at", "feature", "provider", "model", "input_tokens", "output_tokens",
    "latency_ms", "cost_usd", "success", "cached", "skipped", "saved_cost_usd",
)  # fmt: skip
COST_DIGITS = 6
P95 = 0.95


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def window_start(days: UsageDays, today: date) -> date | None:
    return None if days == "all" else today - timedelta(days=days - 1)


def load_frame(db: Session, since: date | None) -> pd.DataFrame:
    query = select(*(getattr(LlmUsage, c) for c in COLUMNS))
    if since is not None:
        query = query.where(LlmUsage.created_at >= datetime.combine(since, time.min, UTC))
    return to_frame([tuple(row) for row in db.execute(query).all()])


def to_frame(rows: list[tuple[object, ...]]) -> pd.DataFrame:
    """Typed frame from raw rows (also used by tests to build fixtures)."""
    frame = pd.DataFrame(rows, columns=list(COLUMNS))
    frame["created_at"] = pd.to_datetime(frame["created_at"], utc=True)
    frame["day"] = frame["created_at"].dt.date
    for column in ("cost_usd", "saved_cost_usd"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
    for column in ("input_tokens", "output_tokens", "latency_ms"):
        frame[column] = frame[column].fillna(0).astype("int64")
    for column in ("success", "cached", "skipped"):
        frame[column] = frame[column].fillna(False).astype(bool)
    return frame


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _flags(frame: pd.DataFrame) -> pd.DataFrame:
    calls = ~frame["cached"] & ~frame["skipped"]
    return frame.assign(
        is_call=calls,
        is_ok_call=calls & frame["success"],
        is_error=~frame["success"],
    )


def _money(value: float) -> float:
    return round(float(value), COST_DIGITS)


def _mean(series: pd.Series) -> float | None:
    return None if series.empty else round(float(series.mean()), 1)


def estimated_savings(frame: pd.DataFrame) -> tuple[float, bool]:
    """Recorded savings, plus an estimate for older hits logged without the original cost.

    The estimate is the mean cost of successful provider calls for the same feature and model.
    """
    hits = frame[frame["cached"]]
    recorded = float(hits["saved_cost_usd"].sum(skipna=True))
    missing = hits[hits["saved_cost_usd"].isna()]
    if missing.empty:
        return _money(recorded), False
    calls = frame[frame["is_ok_call"]]
    mean_cost = calls.groupby(["feature", "model"])["cost_usd"].mean()
    keys = pd.MultiIndex.from_frame(missing[["feature", "model"]])
    estimated = mean_cost.reindex(keys).fillna(0.0).sum()
    return _money(recorded + estimated), bool(estimated > 0)


def _totals(frame: pd.DataFrame) -> UsageTotals:
    calls, hits = int(frame["is_call"].sum()), int(frame["cached"].sum())
    latency = frame.loc[frame["is_ok_call"], "latency_ms"]
    saved, estimated = estimated_savings(frame)
    tokens_in, tokens_out = int(frame["input_tokens"].sum()), int(frame["output_tokens"].sum())
    return UsageTotals(
        requests=len(frame),
        llm_calls=calls,
        cache_hits=hits,
        guardrail_skips=int(frame["skipped"].sum()),
        errors=int(frame["is_error"].sum()),
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        total_tokens=tokens_in + tokens_out,
        cost_usd=_money(frame["cost_usd"].sum()),
        avg_latency_ms=_mean(latency),
        p95_latency_ms=None if latency.empty else round(float(latency.quantile(P95)), 1),
        cache_hit_rate=round(hits / (hits + calls), 4) if hits + calls else None,
        saved_usd=saved,
        saved_includes_estimates=estimated,
    )


def _by_feature(frame: pd.DataFrame) -> list[FeatureUsage]:
    rows = []
    for feature, group in frame.groupby("feature", sort=False):
        rows.append(
            FeatureUsage(
                feature=str(feature),
                requests=len(group),
                llm_calls=int(group["is_call"].sum()),
                cache_hits=int(group["cached"].sum()),
                guardrail_skips=int(group["skipped"].sum()),
                errors=int(group["is_error"].sum()),
                input_tokens=int(group["input_tokens"].sum()),
                output_tokens=int(group["output_tokens"].sum()),
                cost_usd=_money(group["cost_usd"].sum()),
                avg_latency_ms=_mean(group.loc[group["is_ok_call"], "latency_ms"]),
            )
        )
    return sorted(rows, key=lambda r: (-r.cost_usd, -r.requests, r.feature))


def _by_model(frame: pd.DataFrame) -> list[ModelUsage]:
    calls = frame[frame["is_call"]]
    grouped = calls.groupby(["provider", "model"], sort=False).agg(
        llm_calls=("is_call", "size"),
        input_tokens=("input_tokens", "sum"),
        output_tokens=("output_tokens", "sum"),
        cost_usd=("cost_usd", "sum"),
    )
    rows = [
        ModelUsage(
            provider=str(provider),
            model=str(model),
            llm_calls=int(r.llm_calls),
            input_tokens=int(r.input_tokens),
            output_tokens=int(r.output_tokens),
            cost_usd=_money(r.cost_usd),
        )  # fmt: skip
        for (provider, model), r in grouped.iterrows()
    ]
    return sorted(rows, key=lambda r: (-r.cost_usd, -r.llm_calls))


def _by_day(frame: pd.DataFrame, start: date, end: date) -> list[DailyUsage]:
    days = pd.Index(pd.date_range(start, end, freq="D").date, name="day")
    daily = (
        frame.groupby("day")
        .agg(
            llm_calls=("is_call", "sum"),
            cache_hits=("cached", "sum"),
            guardrail_skips=("skipped", "sum"),
            errors=("is_error", "sum"),
            cost_usd=("cost_usd", "sum"),
        )
        .reindex(days, fill_value=0)
    )
    return [
        DailyUsage(
            date=day,
            llm_calls=int(r.llm_calls),
            cache_hits=int(r.cache_hits),
            guardrail_skips=int(r.guardrail_skips),
            errors=int(r.errors),
            cost_usd=_money(r.cost_usd),
        )  # fmt: skip
        for day, r in daily.iterrows()
    ]


def summarize(frame: pd.DataFrame, days: UsageDays, today: date) -> UsageSummary:
    """Totals and breakdowns for rows from the window's first day through `today`."""
    start = window_start(days, today)
    if start is not None:
        frame = frame[frame["day"] >= start]
    else:
        start = min(frame["day"]) if not frame.empty else today
    frame = _flags(frame)
    return UsageSummary(
        days=days,
        start=start,
        end=today,
        totals=_totals(frame),
        by_feature=_by_feature(frame),
        by_model=_by_model(frame),
        by_day=_by_day(frame, start, today),
    )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def get_summary(db: Session, days: UsageDays, today: date | None = None) -> UsageSummary:
    today = today or datetime.now(UTC).date()
    return summarize(load_frame(db, window_start(days, today)), days, today)


def recent_calls(db: Session, limit: int) -> list[UsageCall]:
    rows = db.scalars(select(LlmUsage).order_by(LlmUsage.created_at.desc()).limit(limit))
    return [
        UsageCall(
            id=row.id,
            created_at=row.created_at,
            feature=row.feature,
            provider=row.provider,
            model=row.model,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            latency_ms=row.latency_ms,
            cost_usd=float(row.cost_usd),
            cached=row.cached,
            skipped=row.skipped,
            saved_cost_usd=None if row.saved_cost_usd is None else float(row.saved_cost_usd),
            success=row.success,
            error=row.error,
        )  # fmt: skip
        for row in rows
    ]
