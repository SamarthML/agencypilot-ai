"""Insights datasets: storage in Postgres, loading into Pandas, and dashboard assembly.

Each client has one active dataset (a new upload replaces the old one). If the database has no
datasets at all, the bundled demo CSV is loaded on first use so the dashboard is never empty.
"""

import logging
import uuid
from typing import Any

import pandas as pd
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.models.insights import InsightDataset, InsightRow
from app.schemas.insights import (
    DatasetInfo,
    DatasetUploadResponse,
    InsightsDashboard,
    InsightsSnapshot,
    OverviewResponse,
    SampleLoadResponse,
)
from app.services import analytics

logger = logging.getLogger(__name__)

SAMPLE_CSV = BACKEND_DIR / "sample_data" / "marketing_demo.csv"
FRAME_COLUMNS = ("date", "channel", *analytics.METRICS)


class DatasetNotFoundError(LookupError):
    """No dataset exists for the requested client."""


def dataset_info(dataset: InsightDataset) -> DatasetInfo:
    return DatasetInfo.model_validate(dataset, from_attributes=True)


def _row_records(dataset_id: uuid.UUID, frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = frame.assign(dataset_id=dataset_id, date=frame["date"].dt.date)
    return rows[["dataset_id", *FRAME_COLUMNS]].to_dict("records")


def save_dataset(
    db: Session, client: analytics.ClientFrame, filename: str, source: str
) -> InsightDataset:
    """Replace the client's active dataset with `client.frame`."""
    frame = client.frame
    db.execute(delete(InsightDataset).where(InsightDataset.client_id == client.client_id))
    dataset = InsightDataset(
        client_id=client.client_id,
        client_name=client.client_name,
        filename=filename,
        source=source,
        row_count=len(frame),
        channels=sorted(frame["channel"].unique().tolist()),
        start_date=frame["date"].min().date(),
        end_date=frame["date"].max().date(),
    )
    db.add(dataset)
    db.flush()
    db.execute(insert(InsightRow), _row_records(dataset.id, frame))
    db.commit()
    db.refresh(dataset)
    return dataset


def load_sample(db: Session) -> SampleLoadResponse:
    clients = analytics.parse_multi_client_csv(SAMPLE_CSV.read_bytes())
    datasets = [save_dataset(db, client, SAMPLE_CSV.name, "sample") for client in clients]
    logger.info("Loaded sample data for %d clients", len(datasets))
    return SampleLoadResponse(datasets=[dataset_info(d) for d in datasets])


def ensure_sample_loaded(db: Session) -> None:
    if not db.scalar(select(func.count()).select_from(InsightDataset)):
        load_sample(db)


def upload_dataset(
    db: Session, client_id: str, client_name: str, filename: str, content: bytes
) -> DatasetUploadResponse:
    parsed = analytics.parse_client_csv(content, client_id, client_name)
    client = analytics.ClientFrame(client_id, client_name, parsed.frame)
    dataset = save_dataset(db, client, filename, "upload")
    return DatasetUploadResponse(dataset=dataset_info(dataset), warnings=parsed.warnings)


def get_dataset(db: Session, client_id: str) -> InsightDataset:
    ensure_sample_loaded(db)
    dataset = db.scalar(
        select(InsightDataset)
        .where(InsightDataset.client_id == client_id)
        .order_by(InsightDataset.created_at.desc())
        .limit(1)
    )
    if dataset is None:
        raise DatasetNotFoundError(
            f"No data for client '{client_id}' yet. Upload a CSV or load the sample data."
        )
    return dataset


def load_frame(db: Session, dataset_id: uuid.UUID) -> pd.DataFrame:
    columns = [getattr(InsightRow, name) for name in FRAME_COLUMNS]
    rows = db.execute(
        select(*columns).where(InsightRow.dataset_id == dataset_id).order_by(InsightRow.date)
    ).all()
    frame = pd.DataFrame(rows, columns=list(FRAME_COLUMNS))
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.astype({"revenue": float, "spend": float})


def load_snapshot(
    db: Session, client_id: str, days: int
) -> tuple[InsightDataset, InsightsSnapshot]:
    dataset = get_dataset(db, client_id)
    return dataset, analytics.build_snapshot(load_frame(db, dataset.id), days)


def get_dashboard(db: Session, client_id: str, days: int) -> InsightsDashboard:
    dataset, snapshot = load_snapshot(db, client_id, days)
    return InsightsDashboard(dataset=dataset_info(dataset), **dict(snapshot))


def get_overview(db: Session, days: int) -> OverviewResponse:
    ensure_sample_loaded(db)
    datasets = db.scalars(select(InsightDataset)).all()
    frames = [load_frame(db, dataset.id) for dataset in datasets]
    return OverviewResponse(
        days=days,
        client_count=len(datasets),
        kpis=analytics.build_overview_kpis(frames, days),
    )
