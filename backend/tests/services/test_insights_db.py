"""Dataset storage round trip against Postgres. Skipped when the database isn't running."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, check_db
from app.models.insights import InsightDataset
from app.services import analytics, insights

pytestmark = pytest.mark.skipif(not check_db(), reason="Postgres is not running")

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "marketing_small.csv"
CLIENT_ID = "pytest-roundtrip-co"


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
        session.execute(delete(InsightDataset).where(InsightDataset.client_id == CLIENT_ID))
        session.commit()


def test_upload_replaces_dataset_and_round_trips(db: Session) -> None:
    content = FIXTURE.read_bytes().replace(b"Test Co", b"Pytest Roundtrip Co")

    first = insights.upload_dataset(db, CLIENT_ID, "Pytest Roundtrip Co", "a.csv", content)
    second = insights.upload_dataset(db, CLIENT_ID, "Pytest Roundtrip Co", "b.csv", content)

    dataset = insights.get_dataset(db, CLIENT_ID)
    assert dataset.id == second.dataset.id != first.dataset.id
    assert dataset.filename == "b.csv"
    assert dataset.channels == ["Organic", "Paid Search"]
    frame = insights.load_frame(db, dataset.id)
    expected = analytics.parse_client_csv(content, CLIENT_ID, "x").frame
    assert frame.to_dict("records") == expected.to_dict("records")


def test_dashboard_from_db_matches_pure_analytics(db: Session) -> None:
    content = FIXTURE.read_bytes().replace(b"Test Co", b"Pytest Roundtrip Co")
    insights.upload_dataset(db, CLIENT_ID, "Pytest Roundtrip Co", "a.csv", content)

    dashboard = insights.get_dashboard(db, CLIENT_ID, 7)

    expected = analytics.build_snapshot(
        analytics.parse_client_csv(content, CLIENT_ID, "x").frame, 7
    )
    assert dashboard.kpis == expected.kpis
    assert dashboard.dataset.client_name == "Pytest Roundtrip Co"
