"""seo_audits persistence round trip against Postgres. Skipped when the database isn't running."""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, check_db
from app.models.seo import SeoAudit
from app.schemas.common import LlmCallMeta
from app.schemas.seo import SeoAiReport, SeoFix, SeoPageSummary
from app.services import seo_audit
from app.services.seo import checks

pytestmark = pytest.mark.skipif(not check_db(), reason="Postgres is not running")

CLIENT_ID = "pytest-seo-co"


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
        session.execute(delete(SeoAudit).where(SeoAudit.client_id == CLIENT_ID))
        session.commit()


def result(score_hint: str, with_ai: bool) -> seo_audit.AuditResult:
    page = checks.extract_page(f"<title>{score_hint}</title><h1>Hello</h1>")
    report = SeoAiReport(
        summary="ok",
        top_fixes=[SeoFix(title="t", detail="d", priority="Low", impact="i")] * 5,
        rewritten_title="t", rewritten_meta_description="m",
        suggested_keywords=["k"] * 8, content_ideas=["c"] * 3,
    )  # fmt: skip
    meta = LlmCallMeta(
        provider="groq", model="m", input_tokens=1, output_tokens=2, latency_ms=3,
        cost_usd=float(Decimal("0.000123")), cached=False,
    )  # fmt: skip
    results = checks.run_checks(page, "https://site.example/")
    return seo_audit.AuditResult(
        normalized_url="https://site.example/", final_url="https://site.example/",
        status_code=200, load_ms=50, html_bytes=100,
        page=SeoPageSummary(title=page.title, meta_description=None, h1="Hello", word_count=1),
        checks=results, score=42, ai=report if with_ai else None,
        ai_error=None if with_ai else "no key", meta=meta if with_ai else None,
    )  # fmt: skip


def test_audit_round_trips_through_jsonb(db: Session) -> None:
    saved = seo_audit.save_audit(db, "site.example", CLIENT_ID, result("A", with_ai=True))

    loaded = seo_audit.get_audit(db, saved.id)

    assert loaded == saved
    assert loaded.ai is not None and len(loaded.ai.top_fixes) == 5
    assert loaded.meta is not None and loaded.meta.cost_usd == pytest.approx(0.000123)
    assert [c.id for c in loaded.checks] == [c.id for c in saved.checks]


def test_missing_ai_is_stored_as_sql_null(db: Session) -> None:
    """Regression: JSONB stored Python None as JSON 'null', so `ai IS NULL` didn't match."""
    saved = seo_audit.save_audit(db, "site.example", CLIENT_ID, result("A", with_ai=False))

    row = db.execute(
        select(SeoAudit.ai.is_(None), SeoAudit.llm_meta.is_(None)).where(SeoAudit.id == saved.id)
    ).one()

    assert tuple(row) == (True, True)


def test_history_is_newest_first_and_filtered(db: Session) -> None:
    first = seo_audit.save_audit(db, "a.example", CLIENT_ID, result("A", with_ai=False))
    second = seo_audit.save_audit(db, "b.example", CLIENT_ID, result("B", with_ai=True))

    rows = seo_audit.history(db, CLIENT_ID)

    assert [r.id for r in rows] == [second.id, first.id]
    expected_issues = sum(1 for c in second.checks if c.status != "pass")
    assert rows[0].issue_count == expected_issues > 0
    assert all(r.client_id == CLIENT_ID for r in rows)
    assert seo_audit.history(db, "nobody-has-this-client") == []
