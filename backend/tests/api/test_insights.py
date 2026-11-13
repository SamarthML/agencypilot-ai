"""HTTP contract of /api/insights. Services are patched, so no DB or LLM is needed."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.schemas.insights import DatasetInfo, InsightsDashboard
from app.services import analytics, insights

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "marketing_small.csv"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def fake_dashboard(client_id: str, days: int) -> InsightsDashboard:
    frame = analytics.parse_client_csv(FIXTURE.read_bytes(), "test-co", "Test Co").frame
    snapshot = analytics.build_snapshot(frame, days)
    dataset = DatasetInfo(
        id="00000000-0000-0000-0000-000000000001", client_id=client_id, client_name="Test Co",
        filename="f.csv", source="upload", row_count=len(frame), channels=["Organic"],
        start_date=snapshot.period.previous_start, end_date=snapshot.period.end,
        created_at="2026-01-05T00:00:00Z",
    )  # fmt: skip
    return InsightsDashboard(dataset=dataset, **dict(snapshot))


def test_summary_accepts_days_from_query_string(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, int]] = []

    def dashboard(db: object, client_id: str, days: int) -> InsightsDashboard:
        calls.append((client_id, days))
        return fake_dashboard(client_id, 7)

    monkeypatch.setattr(insights, "get_dashboard", dashboard)

    response = client.get("/api/insights/test-co/summary?days=90")

    assert response.status_code == 200
    assert calls == [("test-co", 90)]
    body = response.json()
    assert {"dataset", "period", "kpis", "timeseries", "channels", "signals"} <= set(body)


@pytest.mark.parametrize("days", ["12", "abc", "0"])
def test_unsupported_days_rejected(client: TestClient, days: str) -> None:
    assert client.get(f"/api/insights/test-co/summary?days={days}").status_code == 422


def test_invalid_client_id_rejected(client: TestClient) -> None:
    assert client.get("/api/insights/Not_A_Slug/summary").status_code == 422


def test_unknown_client_is_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(db: object, client_id: str, days: int) -> InsightsDashboard:
        raise insights.DatasetNotFoundError("No data for client 'ghost' yet.")

    monkeypatch.setattr(insights, "get_dashboard", missing)

    response = client.get("/api/insights/ghost/summary")

    assert response.status_code == 404
    assert "ghost" in response.json()["detail"]


def test_upload_with_missing_columns_is_422(client: TestClient) -> None:
    files = {"file": ("bad.csv", b"date,channel\n2026-01-01,Organic\n", "text/csv")}

    response = client.post("/api/insights/test-co/upload", files=files)

    assert response.status_code == 422
    assert "Missing required column(s): sessions" in response.json()["detail"]


def test_upload_too_large_is_413(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0.0001)  # ~100 bytes
    files = {"file": ("big.csv", FIXTURE.read_bytes(), "text/csv")}

    response = client.post("/api/insights/test-co/upload", files=files)

    assert response.status_code == 413


def test_ai_summary_rejects_unknown_provider(client: TestClient) -> None:
    response = client.post(
        "/api/insights/test-co/ai-summary", json={"days": 30}, headers={"X-LLM-Provider": "nope"}
    )

    assert response.status_code == 400


def test_ask_validates_question_length(client: TestClient) -> None:
    response = client.post("/api/insights/test-co/ask", json={"question": "?"})

    assert response.status_code == 422
