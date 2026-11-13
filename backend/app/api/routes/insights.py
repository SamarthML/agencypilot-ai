"""Client Insights dashboard: CSV upload, computed KPIs, AI summary and Q&A."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import LlmProviderDep
from app.core.config import get_settings
from app.core.db import get_db
from app.schemas.common import ClientId
from app.schemas.insights import (
    AiSummaryRequest,
    AskRequest,
    AskResponse,
    DatasetUploadResponse,
    Days,
    InsightsDashboard,
    InsightSummary,
    OverviewResponse,
    SampleLoadResponse,
)
from app.services import insights, insights_ai

router = APIRouter(prefix="/api/insights", tags=["insights"])

DbDep = Annotated[Session, Depends(get_db)]


async def _read_upload(file: UploadFile) -> bytes:
    max_bytes = int(get_settings().max_upload_mb * 1024 * 1024)
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"The file is larger than {get_settings().max_upload_mb:g} MB.",
        )
    return content


@router.post("/sample", response_model=SampleLoadResponse)
def load_sample(db: DbDep) -> SampleLoadResponse:
    """(Re)load the bundled demo CSV for every demo client."""
    return insights.load_sample(db)


@router.get("/overview", response_model=OverviewResponse)
def overview(db: DbDep, days: Days = 30) -> OverviewResponse:
    """Agency-wide KPIs across every client's dataset."""
    return insights.get_overview(db, days)


@router.post("/{client_id}/upload", response_model=DatasetUploadResponse)
async def upload(
    client_id: ClientId,
    db: DbDep,
    file: Annotated[UploadFile, File(description="CSV: date, channel, sessions, ...")],
    client_name: Annotated[str | None, Form(max_length=100)] = None,
) -> DatasetUploadResponse:
    """Replace the client's dataset with an uploaded CSV."""
    content = await _read_upload(file)
    name = client_name or client_id.replace("-", " ").title()
    return insights.upload_dataset(db, client_id, name, file.filename or "upload.csv", content)


@router.get("/{client_id}/summary", response_model=InsightsDashboard)
def summary(client_id: ClientId, db: DbDep, days: Days = 30) -> InsightsDashboard:
    """KPIs, timeseries, channel breakdown and notable changes, computed with Pandas."""
    return insights.get_dashboard(db, client_id, days)


@router.post("/{client_id}/ai-summary", response_model=InsightSummary)
async def ai_summary(
    client_id: ClientId, body: AiSummaryRequest, db: DbDep, provider: LlmProviderDep
) -> InsightSummary:
    """LLM summary grounded only in the computed KPIs; cached per dataset/period/model."""
    return await insights_ai.summarize(db, client_id, body.days, provider)


@router.post("/{client_id}/ask", response_model=AskResponse)
async def ask(
    client_id: ClientId, body: AskRequest, db: DbDep, provider: LlmProviderDep
) -> AskResponse:
    """Answer a question using only the computed KPIs."""
    return await insights_ai.ask(db, client_id, body.days, body.question, provider)
