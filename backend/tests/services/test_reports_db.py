"""Report CRUD against Postgres with a fake LLM. Skipped when the database isn't running."""

from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, check_db
from app.models.reports import Report as ReportRow
from app.schemas.reports import ReportGenerateRequest, ReportUpdate
from app.services import insights, llm, reports
from tests.fakes import FakeProvider, ok, use_provider
from tests.report_data import content, content_json, report_frame

pytestmark = pytest.mark.skipif(not check_db(), reason="Postgres is not running")

CLIENT = "pytest-reports-co"


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    dataset = SimpleNamespace(id=None, client_name="Pytest Reports Co")
    monkeypatch.setattr(insights, "get_dataset", lambda db, client: dataset)
    monkeypatch.setattr(insights, "load_frame", lambda db, dataset_id: report_frame())
    monkeypatch.setattr(reports, "latest_seo", lambda db, client: None)
    with SessionLocal() as session:
        yield session
        session.execute(delete(ReportRow).where(ReportRow.client == CLIENT))
        session.commit()


async def generate(db: Session, monkeypatch: pytest.MonkeyPatch) -> reports.Report:
    use_provider(monkeypatch, FakeProvider([ok(content_json(seo_highlights=None))]))
    request = ReportGenerateRequest(client=CLIENT, month="2026-10")
    return await reports.generate_report(db, request, "groq")


async def test_generate_persists_a_draft_with_metrics_and_cost(
    db: Session, monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    created = await generate(db, monkeypatch)

    loaded = reports.get_report(db, created.id)
    assert loaded == created
    assert (loaded.status, loaded.month, loaded.month_label) == ("draft", "2026-10", "October 2026")
    assert loaded.client_name == "Pytest Reports Co"
    kpis = {k.key: k.value for k in loaded.metrics.kpis}
    assert kpis["sessions"] == 4340 and kpis["revenue"] == 10230.0
    assert len(loaded.metrics.timeseries) == 31
    assert loaded.meta.input_tokens == 1000 and loaded.meta.cost_usd > 0
    assert loaded.seo_audit_id is None and loaded.content.seo_highlights is None


async def test_update_edits_sections_and_finalises(
    db: Session, monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    created = await generate(db, monkeypatch)
    edited = content(seo_highlights="No audit, so this is dropped.").model_copy(
        update={"executive_summary": "Edited by the account manager."}
    )

    updated = reports.update_report(db, created.id, ReportUpdate(content=edited, status="final"))

    assert updated.status == "final"
    assert updated.content.executive_summary == "Edited by the account manager."
    assert updated.content.seo_highlights is None  # report has no audit
    assert updated.updated_at >= created.updated_at
    assert reports.get_report(db, created.id) == updated

    back = reports.update_report(db, created.id, ReportUpdate(status="draft"))
    assert back.status == "draft" and back.content == updated.content


async def test_list_filters_by_client_and_delete_removes(
    db: Session, monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    first = await generate(db, monkeypatch)
    second = await generate(db, monkeypatch)

    listed = reports.list_reports(db, CLIENT)
    assert [r.id for r in listed] == [second.id, first.id]
    assert listed[0].title == second.content.title
    assert all(r.client == CLIENT for r in reports.list_reports(db, CLIENT))

    reports.delete_report(db, first.id)
    with pytest.raises(reports.ReportNotFoundError):
        reports.get_report(db, first.id)
    assert [r.id for r in reports.list_reports(db, CLIENT)] == [second.id]
