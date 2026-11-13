"""Request/response models for the monthly Report Generator (/api/reports)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.common import ClientId, LlmCallMeta
from app.schemas.insights import ChannelBreakdown, Kpi, Signal, TimeSeriesPoint
from app.schemas.seo import CheckStatus

Month = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
ReportStatus = Literal["draft", "final"]


# --- Computed facts (never LLM-generated) -----------------------------------------------------


class ReportMonth(BaseModel):
    """A month the client's data covers, for the month picker."""

    month: Month
    label: str
    complete: bool = Field(description="False when the data starts or ends inside the month.")
    has_previous: bool = Field(description="True when the previous month has data to compare.")


class MonthPeriod(BaseModel):
    month: Month
    label: str
    start: date
    end: date
    previous_month: Month
    previous_label: str
    previous_start: date
    previous_end: date
    has_previous: bool


class MonthSnapshot(BaseModel):
    period: MonthPeriod
    kpis: list[Kpi]
    channels: list[ChannelBreakdown]
    timeseries: list[TimeSeriesPoint]
    top_movers: list[Signal]


class ReportSeoIssue(BaseModel):
    name: str
    status: CheckStatus
    value: str
    recommendation: str


class ReportSeo(BaseModel):
    audit_id: uuid.UUID
    url: str
    score: int
    audited_at: datetime
    top_issues: list[ReportSeoIssue]


class ReportMetrics(MonthSnapshot):
    seo: ReportSeo | None


# --- LLM output -------------------------------------------------------------------------------


class ReportContent(BaseModel):
    """The narrative the LLM writes (and the user edits). Every number comes from the metrics."""

    title: str = Field(min_length=1, max_length=120)
    executive_summary: str = Field(min_length=1, max_length=2000)
    wins: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=2, max_length=5
    )
    challenges: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=1, max_length=4
    )
    channel_commentary: str = Field(min_length=1, max_length=2500)
    seo_highlights: str | None = Field(
        default=None, max_length=1500, description="Null when there is no SEO audit."
    )
    next_month_plan: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=3, max_length=5
    )
    closing_note: str = Field(min_length=1, max_length=800)


# --- API bodies -------------------------------------------------------------------------------


class ReportGenerateRequest(BaseModel):
    client: ClientId
    month: Month


class ReportUpdate(BaseModel):
    content: ReportContent | None = None
    status: ReportStatus | None = None


class ReportSummary(BaseModel):
    id: uuid.UUID
    client: str
    client_name: str
    month: Month
    month_label: str
    status: ReportStatus
    title: str
    created_at: datetime
    updated_at: datetime


class Report(ReportSummary):
    content: ReportContent
    metrics: ReportMetrics
    seo_audit_id: uuid.UUID | None
    meta: LlmCallMeta
