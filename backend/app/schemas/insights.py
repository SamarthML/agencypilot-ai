"""Request/response models for the Client Insights dashboard (/api/insights)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from app.core.config import LlmProvider


def _digits_to_int(value: object) -> object:
    """Query strings arrive as text; Literal[int] validation doesn't coerce '30' to 30."""
    return int(value) if isinstance(value, str) and value.strip().isdigit() else value


Days = Annotated[Literal[7, 30, 90], BeforeValidator(_digits_to_int)]
KpiUnit = Literal["count", "currency", "percent", "ratio"]
GoodWhen = Literal["up", "down", "neutral"]
ClientId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=50)]


class DatasetInfo(BaseModel):
    id: uuid.UUID
    client_id: str
    client_name: str
    filename: str
    source: Literal["sample", "upload"]
    row_count: int
    channels: list[str]
    start_date: date
    end_date: date
    created_at: datetime


class DatasetUploadResponse(BaseModel):
    dataset: DatasetInfo
    warnings: list[str]


class SampleLoadResponse(BaseModel):
    datasets: list[DatasetInfo]


class Period(BaseModel):
    days: int
    start: date
    end: date
    previous_start: date
    previous_end: date
    has_previous: bool = Field(description="False when the data doesn't cover the prior period.")


class Kpi(BaseModel):
    key: str
    label: str
    value: float | None
    previous: float | None
    delta_pct: float | None
    unit: KpiUnit
    good_when: GoodWhen


class TimeSeriesPoint(BaseModel):
    date: date
    sessions: int
    conversions: int
    revenue: float
    spend: float
    by_channel: dict[str, int] = Field(description="Sessions per channel on this day.")


class ChannelBreakdown(BaseModel):
    channel: str
    sessions: int
    previous_sessions: int
    sessions_delta_pct: float | None
    sessions_share_pct: float
    conversions: int
    revenue: float
    revenue_delta_pct: float | None
    spend: float
    conversion_rate: float | None
    roas: float | None


class Signal(BaseModel):
    """A notable period-over-period change, computed (not LLM-generated)."""

    kind: Literal["channel", "kpi"]
    metric: str
    channel: str | None
    delta_pct: float
    current: float
    previous: float
    sentiment: Literal["positive", "negative", "neutral"]
    message: str


class InsightsSnapshot(BaseModel):
    period: Period
    kpis: list[Kpi]
    timeseries: list[TimeSeriesPoint]
    channels: list[ChannelBreakdown]
    signals: list[Signal]


class InsightsDashboard(InsightsSnapshot):
    dataset: DatasetInfo


class LlmCallMeta(BaseModel):
    provider: LlmProvider
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    cached: bool


class AiSummaryRequest(BaseModel):
    days: Days = 30


class AiSummaryContent(BaseModel):
    """The structured output the LLM must return."""

    headline: str = Field(min_length=1, max_length=300)
    highlights: list[str] = Field(min_length=1, max_length=5)
    concerns: list[str] = Field(max_length=4)
    recommendations: list[str] = Field(min_length=1, max_length=4)


class InsightSummary(BaseModel):
    client_id: str
    period: Period
    summary: AiSummaryContent
    meta: LlmCallMeta


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    days: Days = 30


class AskResponse(BaseModel):
    question: str
    answer: str
    meta: LlmCallMeta


class OverviewResponse(BaseModel):
    days: int
    client_count: int
    kpis: list[Kpi]
