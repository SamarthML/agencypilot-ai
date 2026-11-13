"""Demo SEO seed: fixture HTML through the real checks/scoring, bundled AI report, idempotence."""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, check_db
from app.models.seo import SeoAudit
from app.services import seo_audit, seo_demo
from app.services.seo import fetcher

# Pinned so a fixture or check change that moves the demo numbers is a deliberate decision.
EXPECTED = {
    "bloom-bakery": (84, {"title": "warn", "image_alt": "warn", "open_graph": "warn"}),
    "apex-fitness": (
        63,
        {
            "meta_description": "fail",
            "canonical": "fail",
            "image_alt": "fail",
            "heading_hierarchy": "warn",
            "word_count": "warn",
        },
    ),
    "nova-dental": (
        74,
        {"title": "warn", "meta_description": "warn", "h1": "warn", "open_graph": "fail"},
    ),
}
SITES = {site.client_id: site for site in seo_demo.DEMO_SITES}


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(*args: object) -> None:
        raise AssertionError("the demo seed must not fetch pages")

    monkeypatch.setattr(fetcher, "fetch_page", fail)


@pytest.mark.parametrize("client_id", list(EXPECTED))
def test_demo_audit_runs_real_checks_on_fixture(client_id: str) -> None:
    site = SITES[client_id]
    expected_score, expected_issues = EXPECTED[client_id]

    audit = seo_demo.build_demo_audit(site)

    assert audit.score == expected_score
    assert {c.id: c.status for c in audit.checks if c.status != "pass"} == expected_issues
    assert audit.final_url == site.url and site.url.startswith("https://")
    assert site.url.endswith(".example/")  # reserved TLD: never a real site
    assert audit.status_code == 200 and audit.html_bytes > 1000
    assert audit.meta is None  # no LLM call, so no model/cost is shown
    assert audit.is_demo is True


def test_demo_scores_are_distinct() -> None:
    scores = [seo_demo.build_demo_audit(site).score for site in seo_demo.DEMO_SITES]
    assert len(set(scores)) == len(scores)


@pytest.mark.parametrize("client_id", list(EXPECTED))
def test_bundled_ai_report_addresses_the_failing_checks(client_id: str) -> None:
    audit = seo_demo.build_demo_audit(SITES[client_id])
    assert audit.ai is not None

    fixes = " ".join(f"{f.title} {f.detail}".lower() for f in audit.ai.top_fixes)
    keywords = {
        "title": "title",
        "meta_description": "meta description",
        "h1": "h1",
        "heading_hierarchy": "h3",
        "image_alt": "alt text",
        "canonical": "canonical",
        "open_graph": "og",
        "word_count": "300 words",
    }
    for check_id in EXPECTED[client_id][1]:
        assert keywords[check_id] in fixes, f"{client_id}: no fix mentions {check_id}"
    assert len(audit.ai.rewritten_title) <= 60
    assert 70 <= len(audit.ai.rewritten_meta_description) <= 160


# --- Seeding against Postgres -----------------------------------------------------------------

TEST_CLIENT = "pytest-seo-demo"


@pytest.fixture
def db() -> Iterator[Session]:
    if not check_db():
        pytest.skip("Postgres is not running")
    with SessionLocal() as session:
        yield session
        session.execute(delete(SeoAudit).where(SeoAudit.client_id == TEST_CLIENT))
        session.commit()


@pytest.fixture
def test_site(tmp_path: Path) -> seo_demo.DemoSite:
    source = SITES["bloom-bakery"]
    shutil.copy(source.html_path, tmp_path / f"{TEST_CLIENT}.html")
    shutil.copy(source.ai_path, tmp_path / f"{TEST_CLIENT}.ai.json")
    return seo_demo.DemoSite(TEST_CLIENT, source.url, load_ms=100, fixture_dir=tmp_path)


def test_seed_creates_one_audit_and_is_idempotent(
    db: Session, test_site: seo_demo.DemoSite
) -> None:
    assert seo_demo.seed_demo_audits(db, (test_site,)) == 1
    assert seo_demo.seed_demo_audits(db, (test_site,)) == 0

    history = seo_audit.history(db, TEST_CLIENT)
    assert len(history) == 1
    assert (history[0].final_url, history[0].score, history[0].issue_count) == (
        "https://bloombakery.example/", 84, 3,
    )  # fmt: skip
    saved = seo_audit.get_audit(db, history[0].id)
    assert saved.ai is not None and saved.meta is None and saved.cached is False
    assert saved.is_demo is True and history[0].is_demo is True


def test_seed_skips_clients_with_real_audits(db: Session, test_site: seo_demo.DemoSite) -> None:
    real = seo_demo.build_demo_audit(test_site)
    seo_audit.save_audit(db, "https://real-site.example/", TEST_CLIENT, real)

    assert seo_demo.seed_demo_audits(db, (test_site,)) == 0
    assert [h.url for h in seo_audit.history(db, TEST_CLIENT)] == ["https://real-site.example/"]
