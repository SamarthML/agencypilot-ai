"""Seed one fixture-based SEO audit per demo client that has no audits yet.

The API does this at startup when SEED_DEMO_DATA=true; this script runs it on demand, e.g.
after clearing a client's audit history.

Usage (from backend/):
    .\.venv\Scripts\python.exe scripts/seed_demo_data.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal  # noqa: E402
from app.services.seo_demo import seed_demo_audits  # noqa: E402

logger = logging.getLogger("seed_demo_data")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with SessionLocal() as db:
        created = seed_demo_audits(db)
    logger.info("Created %d demo SEO audit(s); clients with existing audits were skipped.", created)


if __name__ == "__main__":
    main()
