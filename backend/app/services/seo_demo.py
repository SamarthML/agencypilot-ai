"""Demo seed: one realistic SEO audit per demo client, built from bundled fixture HTML.

Each demo client gets an audit of its own fictional site (`*.example`, which never resolves),
so the Home "Open SEO issues" card and monthly reports show believable client data. Checks and
score run through the real pipeline (`checks` + `scoring`); only the fetch is replaced by a
local file, and the AI report is a hand-written `SeoAiReport` bundled next to the HTML (no LLM
call, so `meta` is null and no cost is shown). Seeding skips any client that already has audits.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.core.db import SessionLocal
from app.models.seo import SeoAudit
from app.schemas.seo import SeoAiReport
from app.services import seo_audit
from app.services.seo import checks, scoring

logger = logging.getLogger(__name__)

FIXTURE_DIR = BACKEND_DIR / "sample_data" / "seo"


@dataclass(frozen=True)
class DemoSite:
    client_id: str
    url: str
    # Fixed, plausible fetch timing so the seeded audits are deterministic.
    load_ms: int
    fixture_dir: Path = FIXTURE_DIR

    @property
    def html_path(self) -> Path:
        return self.fixture_dir / f"{self.client_id}.html"

    @property
    def ai_path(self) -> Path:
        return self.fixture_dir / f"{self.client_id}.ai.json"


DEMO_SITES: tuple[DemoSite, ...] = (
    DemoSite("bloom-bakery", "https://bloombakery.example/", load_ms=412),
    DemoSite("apex-fitness", "https://apexfitness.example/", load_ms=688),
    DemoSite("nova-dental", "https://novadental.example/", load_ms=534),
)


def build_demo_audit(site: DemoSite) -> seo_audit.AuditResult:
    """Run the real checks and scoring on the site's fixture HTML (no network, no LLM)."""
    html = site.html_path.read_bytes()
    page = checks.extract_page(html)
    results = checks.run_checks(page, site.url)
    return seo_audit.AuditResult(
        normalized_url=site.url,
        final_url=site.url,
        status_code=200,
        load_ms=site.load_ms,
        html_bytes=len(html),
        page=seo_audit.page_summary(page),
        checks=results,
        score=scoring.score(results),
        ai=SeoAiReport.model_validate_json(site.ai_path.read_bytes()),
        ai_error=None,
        meta=None,
    )


def _has_audits(db: Session, client_id: str) -> bool:
    query = select(SeoAudit.id).where(SeoAudit.client_id == client_id).limit(1)
    return db.scalar(query) is not None


def seed_demo_audits(db: Session, sites: tuple[DemoSite, ...] = DEMO_SITES) -> int:
    """Save a fixture audit for every site whose client has no audits yet; returns how many."""
    created = 0
    for site in sites:
        if _has_audits(db, site.client_id):
            continue
        seo_audit.save_audit(db, site.url, site.client_id, build_demo_audit(site))
        created += 1
    return created


def seed_demo_data() -> None:
    """Startup hook: never blocks or breaks startup (e.g. when the database is down)."""
    try:
        with SessionLocal() as db:
            created = seed_demo_audits(db)
    except Exception:
        logger.exception("Demo seed failed; continuing without it")
        return
    if created:
        logger.info("Seeded %d demo SEO audit(s)", created)
