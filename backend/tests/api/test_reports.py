"""HTTP contract of /api/reports. The service is patched: no DB or LLM."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import create_app
from app.schemas.reports import Report, ReportGenerateRequest, ReportMonth, ReportUpdate
from app.services import analytics, reports
from tests.report_data import REPORT_ID, report


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> dict[uuid.UUID, Report]:
    store = {REPORT_ID: report()}

    def get(db: Session, report_id: uuid.UUID) -> Report:
        if report_id not in store:
            raise reports.ReportNotFoundError(f"No report with id {report_id}.")
        return store[report_id]

    monkeypatch.setattr(reports, "get_report", get)
    return store


def test_generate_passes_body_and_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[ReportGenerateRequest, str]] = []

    async def generate(db: Session, body: ReportGenerateRequest, provider: str) -> Report:
        calls.append((body, provider))
        return report()

    monkeypatch.setattr(reports, "generate_report", generate)

    response = client.post(
        "/api/reports/generate",
        json={"client": "apex-fitness", "month": "2026-10"},
        headers={"X-LLM-Provider": "openai"},
    )

    assert response.status_code == 201
    assert calls[0][0].month == "2026-10" and calls[0][1] == "openai"
    body = response.json()
    assert body["content"]["title"].startswith("October 2026")
    assert body["meta"]["model"] == "openai/gpt-oss-120b"
    assert {k["key"] for k in body["metrics"]["kpis"]} >= {"sessions", "revenue", "roas"}


@pytest.mark.parametrize("month", ["2026-13", "Oct 2026", "2026-1"])
def test_generate_rejects_bad_month(client: TestClient, month: str) -> None:
    response = client.post("/api/reports/generate", json={"client": "apex-fitness", "month": month})
    assert response.status_code == 422


def test_month_without_data_is_422(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def generate(*args: object) -> Report:
        raise analytics.NoDataForMonthError("There is no data for July 2026.")

    monkeypatch.setattr(reports, "generate_report", generate)

    response = client.post(
        "/api/reports/generate", json={"client": "apex-fitness", "month": "2026-07"}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "There is no data for July 2026."


def test_months_lists_available_months(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    month = ReportMonth(month="2026-10", label="October 2026", complete=True, has_previous=True)
    monkeypatch.setattr(reports, "list_months", lambda db, c: [month])

    response = client.get("/api/reports/months", params={"client": "apex-fitness"})

    assert response.status_code == 200
    assert response.json() == [month.model_dump()]


def test_get_and_missing(client: TestClient, stored: dict[uuid.UUID, Report]) -> None:
    assert client.get(f"/api/reports/{REPORT_ID}").json()["id"] == str(REPORT_ID)

    missing = client.get(f"/api/reports/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["detail"].startswith("No report with id")


def test_update_passes_status(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    updates: list[ReportUpdate] = []

    def update(db: Session, report_id: uuid.UUID, body: ReportUpdate) -> Report:
        updates.append(body)
        return report().model_copy(update={"status": "final"})

    monkeypatch.setattr(reports, "update_report", update)

    response = client.put(f"/api/reports/{REPORT_ID}", json={"status": "final"})

    assert response.status_code == 200 and response.json()["status"] == "final"
    assert updates[0].status == "final" and updates[0].content is None


def test_update_rejects_invalid_sections(client: TestClient) -> None:
    bad = report().content.model_dump() | {"next_month_plan": ["only one"]}
    response = client.put(f"/api/reports/{REPORT_ID}", json={"content": bad})
    assert response.status_code == 422


def test_delete_returns_204(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[uuid.UUID] = []
    monkeypatch.setattr(reports, "delete_report", lambda db, report_id: deleted.append(report_id))

    response = client.delete(f"/api/reports/{REPORT_ID}")

    assert response.status_code == 204 and deleted == [REPORT_ID]


def test_list_filters_by_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str | None] = []
    monkeypatch.setattr(reports, "list_reports", lambda db, c: seen.append(c) or [])

    assert client.get("/api/reports", params={"client": "nova-dental"}).json() == []
    assert client.get("/api/reports").status_code == 200
    assert seen == ["nova-dental", None]


def test_pdf_download(client: TestClient, stored: dict[uuid.UUID, Report]) -> None:
    response = client.get(f"/api/reports/{REPORT_ID}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "agencypilot-apex-fitness-2026-10.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-") and len(response.content) > 2000


def test_pdf_missing_report_is_404(client: TestClient, stored: dict[uuid.UUID, Report]) -> None:
    assert client.get(f"/api/reports/{uuid.uuid4()}/pdf").status_code == 404
