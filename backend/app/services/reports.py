"""Monthly client reports: computed metrics → grounded LLM narrative → Postgres → edits.

The LLM only sees `ReportContext`: calendar-month KPIs vs the previous month, channel totals,
computed top movers and (if any) the client's latest SEO score and top issues. The daily series
and raw rows are stored for charts but never sent. PDF rendering lives in `report_pdf.py`.
"""

import asyncio
import uuid
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import LlmProvider
from app.models.reports import Report as ReportRow
from app.models.seo import SeoAudit
from app.schemas.common import LlmCallMeta
from app.schemas.insights import GoodWhen, KpiUnit
from app.schemas.reports import (
    Report,
    ReportContent,
    ReportGenerateRequest,
    ReportMetrics,
    ReportMonth,
    ReportSeo,
    ReportSeoIssue,
    ReportSummary,
    ReportUpdate,
)
from app.services import analytics, insights, llm
from app.services.insights_ai import ContextChannel, context_channel
from app.services.llm_meta import call_meta

FEATURE = "report"
# Generous: reasoning models (gpt-oss on Groq) spend part of the budget thinking.
REPORT_MAX_TOKENS = 4000
SEO_TOP_ISSUES = 3
LIST_LIMIT = 100

REPORT_SYSTEM_PROMPT = """\
You are a senior account manager at a digital-marketing agency writing the monthly performance \
report a client will read. You receive pre-computed facts for one client as JSON: KPIs for the \
report month vs the previous month, per-channel totals, the biggest movers and, optionally, \
the latest SEO audit.

Rules:
- Every number you write must appear in the JSON (values, previous values or change_pct). \
Never invent, estimate, round differently, extrapolate or forecast figures.
- Percent changes compare the report month with the previous month. If a value is null, say \
it is unavailable instead of guessing.
- `better_when` says which direction is good for a KPI ("down" for cost per conversion).
- Write for the client: clear, specific, confident and honest; no jargon, no hype.
- title: short and specific to the month (at most 12 words).
- executive_summary: 3-5 sentences leading with the most important result.
- wins: 2-5 bullets; challenges: 1-4 bullets; each one specific sentence citing the numbers.
- channel_commentary: one paragraph comparing the channels that matter most.
- seo_highlights: if `seo` is null, return null. Otherwise 2-3 sentences on the score and the \
top issues.
- next_month_plan: 3-5 concrete actions that follow from the data; never promise results.
- closing_note: one or two warm sentences."""


class ReportNotFoundError(LookupError):
    """No report with the requested id."""


# ---------------------------------------------------------------------------
# Computed facts
# ---------------------------------------------------------------------------


def _top_issues(audit: SeoAudit) -> list[ReportSeoIssue]:
    failing = [c for c in audit.checks if c["status"] != "pass"]
    failing.sort(key=lambda c: (c["status"] != "fail", -int(c["weight"])))
    return [ReportSeoIssue.model_validate(c) for c in failing[:SEO_TOP_ISSUES]]


def latest_seo(db: Session, client: str) -> ReportSeo | None:
    audit = db.scalar(
        select(SeoAudit)
        .where(SeoAudit.client_id == client)
        .order_by(SeoAudit.created_at.desc())
        .limit(1)
    )
    if audit is None:
        return None
    return ReportSeo(
        audit_id=audit.id,
        url=audit.final_url,
        score=audit.score,
        audited_at=audit.created_at,
        top_issues=_top_issues(audit),
    )


def list_months(db: Session, client: str) -> list[ReportMonth]:
    dataset = insights.get_dataset(db, client)
    return analytics.available_months(insights.load_frame(db, dataset.id))


def build_metrics(db: Session, client: str, month: str) -> tuple[str, ReportMetrics]:
    """The client's display name and everything computed for the month (no LLM)."""
    dataset = insights.get_dataset(db, client)
    snapshot = analytics.build_month_snapshot(insights.load_frame(db, dataset.id), month)
    return dataset.client_name, ReportMetrics(**dict(snapshot), seo=latest_seo(db, client))


# ---------------------------------------------------------------------------
# Grounding context (the only thing the LLM sees)
# ---------------------------------------------------------------------------


class ContextKpi(BaseModel):
    metric: str
    unit: KpiUnit
    better_when: GoodWhen
    this_month: float | None
    previous_month: float | None
    change_pct: float | None


class ContextSeo(BaseModel):
    url: str
    score_out_of_100: int
    top_issues: list[str]


class ReportContext(BaseModel):
    client: str
    report_month: str
    previous_month: str | None
    kpis: list[ContextKpi]
    channels: list[ContextChannel]
    top_movers: list[str]
    seo: ContextSeo | None


def _context_seo(seo: ReportSeo | None) -> ContextSeo | None:
    if seo is None:
        return None
    issues = [f"{i.name} ({i.status}): {i.value}. Fix: {i.recommendation}" for i in seo.top_issues]
    return ContextSeo(url=seo.url, score_out_of_100=seo.score, top_issues=issues)


def build_report_context(client_name: str, metrics: ReportMetrics) -> ReportContext:
    period = metrics.period
    return ReportContext(
        client=client_name,
        report_month=period.label,
        previous_month=period.previous_label if period.has_previous else None,
        kpis=[
            ContextKpi(
                metric=k.label,
                unit=k.unit,
                better_when=k.good_when,
                this_month=k.value,
                previous_month=k.previous,
                change_pct=k.delta_pct,
            )  # fmt: skip
            for k in metrics.kpis
        ],
        channels=[context_channel(c) for c in metrics.channels],
        top_movers=[s.message for s in metrics.top_movers],
        seo=_context_seo(metrics.seo),
    )


def build_report_messages(context: ReportContext) -> list[llm.ChatMessage]:
    content = (
        f"Facts for {context.client}'s {context.report_month} report (JSON):\n"
        f"{context.model_dump_json()}\n\nWrite the monthly report."
    )
    return [llm.ChatMessage(role="user", content=content)]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _meta(row: ReportRow) -> LlmCallMeta:
    return LlmCallMeta(
        provider=row.provider, model=row.model, input_tokens=row.input_tokens,
        output_tokens=row.output_tokens, latency_ms=row.latency_ms,
        cost_usd=float(row.cost_usd), cached=False,
    )  # fmt: skip


def _summary_fields(row: ReportRow) -> dict[str, object]:
    return {
        "id": row.id,
        "client": row.client,
        "client_name": row.client_name,
        "month": row.month,
        "month_label": analytics.month_label(row.month),
        "status": row.status,
        "title": row.content["title"],
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def to_summary(row: ReportRow) -> ReportSummary:
    return ReportSummary.model_validate(_summary_fields(row))


def to_response(row: ReportRow) -> Report:
    return Report.model_validate(
        {
            **_summary_fields(row),
            "content": row.content,
            "metrics": row.metrics,
            "seo_audit_id": row.seo_audit_id,
            "meta": _meta(row),
        }
    )


def save_report(
    db: Session,
    client: str,
    client_name: str,
    metrics: ReportMetrics,
    content: ReportContent,
    meta: LlmCallMeta,
) -> Report:
    row = ReportRow(
        client=client,
        client_name=client_name,
        month=metrics.period.month,
        status="draft",
        content=content.model_dump(mode="json"),
        metrics=metrics.model_dump(mode="json"),
        seo_audit_id=metrics.seo.audit_id if metrics.seo else None,
        provider=meta.provider,
        model=meta.model,
        input_tokens=meta.input_tokens,
        output_tokens=meta.output_tokens,
        latency_ms=meta.latency_ms,
        cost_usd=Decimal(str(meta.cost_usd)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_response(row)


def _row(db: Session, report_id: uuid.UUID) -> ReportRow:
    row = db.get(ReportRow, report_id)
    if row is None:
        raise ReportNotFoundError(f"No report with id {report_id}.")
    return row


def get_report(db: Session, report_id: uuid.UUID) -> Report:
    return to_response(_row(db, report_id))


def list_reports(db: Session, client: str | None) -> list[ReportSummary]:
    query = select(ReportRow).order_by(ReportRow.created_at.desc()).limit(LIST_LIMIT)
    if client is not None:
        query = query.where(ReportRow.client == client)
    return [to_summary(row) for row in db.scalars(query)]


def update_report(db: Session, report_id: uuid.UUID, update: ReportUpdate) -> Report:
    row = _row(db, report_id)
    if update.content is not None:
        content = update.content
        if row.seo_audit_id is None and row.metrics.get("seo") is None:
            content = content.model_copy(update={"seo_highlights": None})
        row.content = content.model_dump(mode="json")
    if update.status is not None:
        row.status = update.status
    db.commit()
    db.refresh(row)
    return to_response(row)


def delete_report(db: Session, report_id: uuid.UUID) -> None:
    db.delete(_row(db, report_id))
    db.commit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def generate_report(
    db: Session, request: ReportGenerateRequest, provider: LlmProvider
) -> Report:
    """Compute the month's facts, have the LLM write the narrative from them, save a draft."""
    client_name, metrics = await asyncio.to_thread(build_metrics, db, request.client, request.month)
    structured = await llm.generate_structured(
        build_report_messages(build_report_context(client_name, metrics)),
        ReportContent,
        feature=FEATURE,
        system=REPORT_SYSTEM_PROMPT,
        provider=provider,
        max_tokens=REPORT_MAX_TOKENS,
        temperature=0.3,
        max_repairs=1,
    )
    content = structured.data
    if metrics.seo is None:
        content = content.model_copy(update={"seo_highlights": None})
    meta = call_meta(structured.result)
    return await asyncio.to_thread(
        save_report, db, request.client, client_name, metrics, content, meta
    )
