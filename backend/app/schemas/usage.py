"""Response models for LLM usage and cost (/api/usage)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field


def _days(value: object) -> object:
    """'7' / '30' from the query string become ints; anything else (e.g. 'all') passes through."""
    return int(value) if isinstance(value, str) and value.strip().isdigit() else value


UsageDays = Annotated[Literal[7, 30, "all"], BeforeValidator(_days)]


class UsageTotals(BaseModel):
    requests: int = Field(description="Every logged request: provider calls, cache hits, skips.")
    llm_calls: int = Field(description="Requests that reached a provider (incl. failed calls).")
    cache_hits: int
    guardrail_skips: int = Field(description="Answered without a provider call (guardrail).")
    errors: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    avg_latency_ms: float | None = Field(description="Successful provider calls only.")
    p95_latency_ms: float | None
    cache_hit_rate: float | None = Field(description="cache_hits / (cache_hits + llm_calls).")
    saved_usd: float = Field(description="Cost of the original calls that cache hits replayed.")
    saved_includes_estimates: bool = Field(
        description="True when some older hits had no recorded cost and were estimated."
    )


class FeatureUsage(BaseModel):
    feature: str
    requests: int
    llm_calls: int
    cache_hits: int
    guardrail_skips: int
    errors: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    avg_latency_ms: float | None


class ModelUsage(BaseModel):
    provider: str
    model: str
    llm_calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class DailyUsage(BaseModel):
    date: date
    llm_calls: int
    cache_hits: int
    guardrail_skips: int
    errors: int
    cost_usd: float


class UsageSummary(BaseModel):
    days: Literal[7, 30, "all"]
    start: date
    end: date
    totals: UsageTotals
    by_feature: list[FeatureUsage]
    by_model: list[ModelUsage]
    by_day: list[DailyUsage]


class UsageCall(BaseModel):
    id: uuid.UUID
    created_at: datetime
    feature: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    cached: bool
    skipped: bool
    saved_cost_usd: float | None
    success: bool
    error: str | None
