"""HTTP contract of /api/seo. The service is patched: no network, DB or LLM."""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import create_app
from app.schemas.seo import SeoAuditResponse, SeoAuditSummary, SeoPageSummary
from app.services import seo_audit
from app.services.seo import fetcher

AUDIT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def response(url: str = "https://site.example/", client_id: str | None = None) -> SeoAuditResponse:
    return SeoAuditResponse(
        id=AUDIT_ID, url=url, final_url=url, client_id=client_id, status_code=200, load_ms=100,
        html_bytes=1000, score=80, checks=[],
        page=SeoPageSummary(title="T", meta_description=None, h1=None, word_count=10),
        ai=None, ai_error="no key", meta=None, cached=False, created_at=datetime.now(UTC),
    )  # fmt: skip


def test_audit_passes_url_client_and_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str | None, str]] = []

    async def run(db: Session, url: str, client_id: str | None, provider: str) -> SeoAuditResponse:
        calls.append((url, client_id, provider))
        return response(url, client_id)

    monkeypatch.setattr(seo_audit, "run_audit", run)

    result = client.post(
        "/api/seo/audit",
        json={"url": "site.example", "client_id": "apex-fitness"},
        headers={"X-LLM-Provider": "openai"},
    )

    assert result.status_code == 200
    assert calls == [("site.example", "apex-fitness", "openai")]
    assert result.json()["score"] == 80


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (fetcher.InvalidUrlError("Only http:// and https:// URLs can be audited."), 422),
        (fetcher.BlockedAddressError("points to a private or reserved address"), 400),
        (fetcher.FetchTimeoutError("took longer than 10 seconds"), 504),
        (fetcher.NotHtmlError("not an HTML page"), 415),
        (fetcher.PageTooLargeError("larger than 2 MB"), 422),
        (fetcher.SiteBlocksBotsError("blocks automated audits"), 502),
        (fetcher.SiteUnreachableError("Couldn't find site"), 502),
    ],
)
def test_fetch_errors_map_to_friendly_responses(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, error: Exception, status: int
) -> None:
    async def run(*args: object) -> SeoAuditResponse:
        raise error

    monkeypatch.setattr(seo_audit, "run_audit", run)

    result = client.post("/api/seo/audit", json={"url": "https://site.example/"})

    assert result.status_code == status
    assert result.json() == {"detail": str(error)}


@pytest.mark.parametrize("body", [{}, {"url": ""}, {"url": "x", "client_id": "Not A Slug"}])
def test_invalid_body_is_422(client: TestClient, body: dict[str, str]) -> None:
    assert client.post("/api/seo/audit", json=body).status_code == 422


def test_unknown_provider_is_400(client: TestClient) -> None:
    result = client.post(
        "/api/seo/audit", json={"url": "site.example"}, headers={"X-LLM-Provider": "gemini"}
    )

    assert result.status_code == 400


def test_history_filters_by_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str | None] = []

    def history(db: Session, client_id: str | None) -> list[SeoAuditSummary]:
        calls.append(client_id)
        return [
            SeoAuditSummary(
                id=AUDIT_ID,
                url="u",
                final_url="u",
                client_id=client_id,
                score=50,
                issue_count=3,
                created_at=datetime.now(UTC),
            )  # fmt: skip
        ]

    monkeypatch.setattr(seo_audit, "history", history)

    assert client.get("/api/seo/history?client=apex-fitness").json()[0]["score"] == 50
    assert client.get("/api/seo/history").status_code == 200
    assert calls == ["apex-fitness", None]
    assert client.get("/api/seo/history?client=BAD_ID").status_code == 422


def test_get_audit_and_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def get(db: Session, audit_id: uuid.UUID) -> SeoAuditResponse:
        if audit_id != AUDIT_ID:
            raise seo_audit.SeoAuditNotFoundError(f"No SEO audit with id {audit_id}.")
        return response()

    monkeypatch.setattr(seo_audit, "get_audit", get)

    assert client.get(f"/api/seo/audits/{AUDIT_ID}").status_code == 200
    missing = client.get(f"/api/seo/audits/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert "No SEO audit" in missing.json()["detail"]
    assert client.get("/api/seo/audits/not-a-uuid").status_code == 422
