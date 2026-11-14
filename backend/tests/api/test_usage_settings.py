"""HTTP contracts of /api/usage and /api/settings (services patched or config-only)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import create_app
from app.schemas.usage import UsageCall, UsageDays, UsageSummary
from app.services import usage
from tests.services.test_usage import ROWS, TODAY


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.mark.parametrize(("query", "expected"), [("7", 7), ("30", 30), ("all", "all")])
def test_summary_accepts_days(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, query: str, expected: object
) -> None:
    seen: list[object] = []

    def summary(db: Session, days: UsageDays) -> UsageSummary:
        seen.append(days)
        return usage.summarize(usage.to_frame(ROWS), days, TODAY)

    monkeypatch.setattr(usage, "get_summary", summary)

    response = client.get("/api/usage/summary", params={"days": query})

    assert response.status_code == 200 and seen == [expected]
    assert response.json()["totals"]["requests"] >= 7


@pytest.mark.parametrize("query", ["14", "0", "forever"])
def test_summary_rejects_other_windows(client: TestClient, query: str) -> None:
    assert client.get("/api/usage/summary", params={"days": query}).status_code == 422


def test_recent_limit_is_bounded(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    limits: list[int] = []

    def recent(db: Session, limit: int) -> list[UsageCall]:
        limits.append(limit)
        return []

    monkeypatch.setattr(usage, "recent_calls", recent)

    assert client.get("/api/usage/recent").status_code == 200
    assert client.get("/api/usage/recent", params={"limit": 200}).status_code == 200
    assert client.get("/api/usage/recent", params={"limit": 201}).status_code == 422
    assert limits == [50, 200]


def test_settings_reports_configuration_without_keys(client: TestClient) -> None:
    response = client.get("/api/settings")

    assert response.status_code == 200
    body = response.json()
    providers = {p["id"]: p for p in body["providers"]}
    assert providers["groq"]["configured"] is True  # conftest sets a dummy Groq key
    assert providers["openai"]["configured"] is False
    assert providers["groq"]["is_default"] is True
    assert body["copilot_min_similarity"] == 0.5
    assert body["seed_demo_data"] is False and body["rate_limit_enabled"] is True
    assert body["embedding_backend"] == "sentence-transformers" and body["demo_mode"] is False
    assert "test-groq-key" not in response.text  # the key value never leaves the backend
    assert not any("key" in field for field in body)
