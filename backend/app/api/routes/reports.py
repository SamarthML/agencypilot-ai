"""Monthly client reports: generate (LLM), list/read/edit/delete, and PDF export."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import LlmProviderDep
from app.core.db import get_db
from app.schemas.common import ClientId
from app.schemas.reports import (
    Report,
    ReportGenerateRequest,
    ReportMonth,
    ReportSummary,
    ReportUpdate,
)
from app.services import report_pdf, reports

router = APIRouter(prefix="/api/reports", tags=["reports"])

DbDep = Annotated[Session, Depends(get_db)]


@router.get("/months", response_model=list[ReportMonth])
def months(db: DbDep, client: Annotated[ClientId, Query()]) -> list[ReportMonth]:
    """Months covered by the client's data, newest first (for the month picker)."""
    return reports.list_months(db, client)


@router.post("/generate", response_model=Report, status_code=status.HTTP_201_CREATED)
async def generate(body: ReportGenerateRequest, db: DbDep, provider: LlmProviderDep) -> Report:
    """Compute the month's KPIs (+ latest SEO audit) and have the LLM write a draft report."""
    return await reports.generate_report(db, body, provider)


@router.get("", response_model=list[ReportSummary])
def list_reports(
    db: DbDep, client: Annotated[ClientId | None, Query()] = None
) -> list[ReportSummary]:
    return reports.list_reports(db, client)


@router.get("/{report_id}", response_model=Report)
def get_report(report_id: uuid.UUID, db: DbDep) -> Report:
    return reports.get_report(db, report_id)


@router.put("/{report_id}", response_model=Report)
def update_report(report_id: uuid.UUID, body: ReportUpdate, db: DbDep) -> Report:
    """Replace the narrative sections and/or set the status (draft | final)."""
    return reports.update_report(db, report_id, body)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: uuid.UUID, db: DbDep) -> None:
    reports.delete_report(db, report_id)


@router.get(
    "/{report_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def report_pdf_file(report_id: uuid.UUID, db: DbDep) -> Response:
    """The report as a branded A4 PDF, rendered on the server."""
    report = reports.get_report(db, report_id)
    filename = f"agencypilot-{report.client}-{report.month}.pdf"
    return Response(
        content=report_pdf.render(report),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
