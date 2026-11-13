"""Small, hand-checkable data for report tests: Aug 15 - Oct 31 2026, two channels.

September: Organic 100 sessions/day (2 conv, $200), Paid Search 50/day (1 conv, $100, $25 spend).
October:   Organic  80 sessions/day (2 conv, $180), Paid Search 60/day (2 conv, $150, $30 spend).
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pandas as pd

from app.schemas.common import LlmCallMeta
from app.schemas.reports import Report, ReportContent, ReportMetrics, ReportSeo, ReportSeoIssue
from app.services import analytics

REPORT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
START = date(2026, 8, 15)
END = date(2026, 10, 31)


def _rows_for(day: date) -> list[dict[str, object]]:
    october = day.month == 10
    return [
        {"date": day, "channel": "Organic", "sessions": 80 if october else 100,
         "conversions": 2, "revenue": 180.0 if october else 200.0, "spend": 0.0},
        {"date": day, "channel": "Paid Search", "sessions": 60 if october else 50,
         "conversions": 2 if october else 1, "revenue": 150.0 if october else 100.0,
         "spend": 30.0 if october else 25.0},
    ]  # fmt: skip


def report_frame() -> pd.DataFrame:
    days = [START + timedelta(days=n) for n in range((END - START).days + 1)]
    frame = pd.DataFrame([row for day in days for row in _rows_for(day)])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


SEO = ReportSeo(
    audit_id=uuid.UUID("00000000-0000-0000-0000-00000000005e"),
    url="https://apex.example/",
    score=71,
    audited_at=datetime(2026, 11, 1, tzinfo=UTC),
    top_issues=[
        ReportSeoIssue(
            name="Canonical link", status="fail", value="Missing", recommendation="Add one."
        )
    ],
)


def october_metrics(with_seo: bool = True) -> ReportMetrics:
    snapshot = analytics.build_month_snapshot(report_frame(), "2026-10")
    return ReportMetrics(**dict(snapshot), seo=SEO if with_seo else None)


def content(seo_highlights: str | None = "Score 71/100; canonical link missing.") -> ReportContent:
    return ReportContent(
        title="October 2026: Paid Search up 24%",
        executive_summary="Sessions fell 3.6% to 4,340 while revenue rose to $10,230.",
        wins=["Paid Search sessions up 24.0% (1,500 → 1,860).", "Revenue up 13.7% to $10,230."],
        challenges=["Organic sessions down 17.3% (3,000 → 2,480)."],
        channel_commentary="Paid Search grew while Organic slipped.",
        seo_highlights=seo_highlights,
        next_month_plan=["Fix the canonical link.", "Refresh organic content.", "Hold spend."],
        closing_note="Thanks for a great month.",
    )


def content_json(seo_highlights: str | None = "Score 71/100.") -> str:
    return content(seo_highlights).model_dump_json()


META = LlmCallMeta(
    provider="groq", model="openai/gpt-oss-120b", input_tokens=1500, output_tokens=600,
    latency_ms=2100, cost_usd=0.00052, cached=False,
)  # fmt: skip


def report(with_seo: bool = True) -> Report:
    now = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
    body = content() if with_seo else content(seo_highlights=None)
    return Report(
        id=REPORT_ID,
        client="apex-fitness", client_name="Apex Fitness", month="2026-10",
        month_label="October 2026", status="draft", title=body.title,
        created_at=now, updated_at=now, content=body, metrics=october_metrics(with_seo),
        seo_audit_id=SEO.audit_id if with_seo else None, meta=META,
    )  # fmt: skip
