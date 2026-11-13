"""Audit orchestration: fetch and DB are faked, the LLM is the shared FakeProvider."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import httpx
import pytest
from sqlalchemy.orm import Session

from app.models.seo import SeoAudit
from app.schemas.seo import SeoAuditResponse
from app.services import llm, seo_audit
from app.services.seo import fetcher
from tests.fakes import FakeProvider, ok, use_provider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "seo"
NO_DB = cast(Session, None)  # save_audit is patched
AI_JSON = json.dumps(
    {
        "summary": "A solid page with minor gaps.",
        "top_fixes": [
            {"title": f"Fix {i}", "detail": "Do it.", "priority": "High", "impact": "CTR"}
            for i in range(5)
        ],
        "rewritten_title": "Strength Classes in Austin | Apex Fitness",
        "rewritten_meta_description": "Small-group strength classes in Austin with expert coaches.",
        "suggested_keywords": [f"keyword {i}" for i in range(8)],
        "content_ideas": ["Idea 1", "Idea 2", "Idea 3"],
    }
)


SAVED: list[SeoAudit] = []  # rows "persisted" by fake_save


class FakeSite:
    """Stands in for fetcher.fetch_page and records the URLs it was asked for."""

    def __init__(self, page: str = "good.html", final_url: str = "https://site.example/") -> None:
        self.content = (FIXTURES / page).read_bytes()
        self.final_url = final_url
        self.calls: list[str] = []

    async def __call__(self, url: httpx.URL) -> fetcher.FetchResult:
        self.calls.append(str(url))
        return fetcher.FetchResult(
            final_url=self.final_url, status_code=200, load_ms=120,
            html_bytes=len(self.content), content=self.content, charset="utf-8",
        )  # fmt: skip


def fake_save(
    db: Session, url: str, client_id: str | None, result: seo_audit.AuditResult
) -> SeoAuditResponse:
    """save_audit without a database: build the row in memory and serialise it the real way."""
    row = SeoAudit(
        id=uuid.uuid4(), url=url, normalized_url=result.normalized_url,
        final_url=result.final_url, client_id=client_id, status_code=result.status_code,
        score=result.score, checks=[c.model_dump() for c in result.checks],
        page=result.page.model_dump(), ai=result.ai.model_dump() if result.ai else None,
        llm_meta=result.meta.model_dump() if result.meta else None, ai_error=result.ai_error,
        load_ms=result.load_ms, html_bytes=result.html_bytes, cached=result.cached,
        is_demo=result.is_demo,
        created_at=datetime.now(UTC),
    )  # fmt: skip
    SAVED.append(row)
    return seo_audit.to_response(row)


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    SAVED.clear()
    seo_audit.audit_cache().clear()
    monkeypatch.setattr(seo_audit, "save_audit", fake_save)


@pytest.fixture
def site(monkeypatch: pytest.MonkeyPatch) -> FakeSite:
    fake = FakeSite()
    monkeypatch.setattr(fetcher, "fetch_page", fake)
    return fake


def ai_input(provider: FakeProvider, index: int = 0) -> dict[str, object]:
    content = provider.requests[index].messages[0].content
    return json.loads(content.split("\n", 1)[1].rsplit("\n\n", 1)[0])


# --- Happy path -------------------------------------------------------------------


async def test_audit_scores_in_code_and_attaches_ai_report(
    site: FakeSite, monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider([ok(AI_JSON, 1500, 600)]))

    response = await seo_audit.run_audit(NO_DB, "Site.Example", "apex-fitness", "groq")

    assert site.calls == ["https://site.example/"]
    assert response.score == 100  # good.html passes every check
    assert len(response.checks) == 10
    assert response.ai is not None and len(response.ai.top_fixes) == 5
    assert response.ai_error is None
    assert response.meta is not None and response.meta.cost_usd > 0
    assert response.cached is False
    assert (response.url, response.client_id) == ("Site.Example", "apex-fitness")
    assert response.page.h1 == "Strength classes that fit your week"
    assert [(r.feature, r.cached) for r in usage_rows] == [("seo_audit", False)]


async def test_llm_gets_checks_and_a_capped_text_excerpt_only(
    site: FakeSite, monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok(AI_JSON)]))

    await seo_audit.run_audit(NO_DB, "https://site.example/", None, "groq")

    payload = ai_input(fake)
    assert set(payload) == {
        "url",
        "title",
        "meta_description",
        "h1",
        "visible_text_excerpt",
        "checks",
    }
    assert len(str(payload["visible_text_excerpt"])) == seo_audit.TEXT_EXCERPT_CHARS
    assert "analytics" not in str(payload["visible_text_excerpt"])  # <script> content
    sent_checks = cast(list[dict[str, str]], payload["checks"])
    assert [c["id"] for c in sent_checks][:3] == ["title", "meta_description", "h1"]
    assert fake.requests[0].system == seo_audit.SYSTEM_PROMPT
    assert fake.requests[0].json_schema is not None


async def test_bad_page_scores_low(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    monkeypatch.setattr(fetcher, "fetch_page", FakeSite("bad.html", "http://site.example/"))
    use_provider(monkeypatch, FakeProvider([ok(AI_JSON)]))

    response = await seo_audit.run_audit(NO_DB, "http://site.example/", None, "groq")

    assert response.score == 3  # only the heading-hierarchy warning earns points (6 * 0.5)


# --- Cache --------------------------------------------------------------------------


async def test_second_audit_is_served_from_cache_at_zero_cost(
    site: FakeSite, monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok(AI_JSON)]))

    first = await seo_audit.run_audit(NO_DB, "https://site.example", None, "groq")
    second = await seo_audit.run_audit(NO_DB, "SITE.example/", "apex-fitness", "groq")

    assert len(site.calls) == 1 and len(fake.requests) == 1
    assert second.cached is True and second.meta is not None
    assert (second.meta.cost_usd, second.meta.input_tokens, second.meta.cached) == (0, 0, True)
    assert second.score == first.score and second.ai == first.ai
    assert second.id != first.id and len(SAVED) == 2  # every audit is persisted
    assert [(r.feature, r.cached, r.cost_usd) for r in usage_rows][1] == ("seo_audit", True, 0)
    assert usage_rows[0].cost_usd > 0
    assert usage_rows[1].saved_cost_usd == pytest.approx(usage_rows[0].cost_usd)


async def test_cache_is_per_provider(
    site: FakeSite, monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider([ok(AI_JSON), ok(AI_JSON)]))

    await seo_audit.run_audit(NO_DB, "https://site.example/", None, "groq")
    await seo_audit.run_audit(NO_DB, "https://site.example/", None, "openai")

    assert len(site.calls) == 2


# --- AI failures ----------------------------------------------------------------------


async def test_invalid_json_is_repaired_once(
    site: FakeSite, monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok('{"summary": "only"}'), ok(AI_JSON)]))

    response = await seo_audit.run_audit(NO_DB, "https://site.example/", None, "groq")

    assert response.ai is not None
    assert len(fake.requests) == 2


async def test_ai_failure_still_returns_checks_and_score_and_is_not_cached(
    site: FakeSite, monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider([ok("nope"), ok("still nope"), ok(AI_JSON)]))

    failed = await seo_audit.run_audit(NO_DB, "https://site.example/", None, "groq")
    retried = await seo_audit.run_audit(NO_DB, "https://site.example/", None, "groq")

    assert failed.ai is None and failed.meta is None
    assert failed.ai_error is not None and "invalid JSON" in failed.ai_error
    assert failed.score == 100 and len(failed.checks) == 10
    assert retried.ai is not None and retried.cached is False
    assert len(site.calls) == 2


async def test_unconfigured_provider_degrades_gracefully(
    site: FakeSite, usage_rows: list[llm.UsageRecord]
) -> None:
    response = await seo_audit.run_audit(NO_DB, "https://site.example/", None, "claude")

    assert response.ai is None
    assert response.ai_error is not None and "ANTHROPIC_API_KEY" in response.ai_error


# --- Fetch failures ------------------------------------------------------------------


async def test_invalid_url_is_rejected_before_fetching(site: FakeSite) -> None:
    with pytest.raises(fetcher.InvalidUrlError):
        await seo_audit.run_audit(NO_DB, "ftp://site.example/", None, "groq")

    assert site.calls == [] and SAVED == []


async def test_fetch_errors_propagate_and_nothing_is_saved(monkeypatch: pytest.MonkeyPatch) -> None:
    async def blocked(url: httpx.URL) -> fetcher.FetchResult:
        raise fetcher.BlockedAddressError("private")

    monkeypatch.setattr(fetcher, "fetch_page", blocked)

    with pytest.raises(fetcher.BlockedAddressError):
        await seo_audit.run_audit(NO_DB, "https://intranet.example/", None, "groq")

    assert SAVED == []
