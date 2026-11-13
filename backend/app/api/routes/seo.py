"""SEO Audit: audit a URL, list recent audits, fetch one audit."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import LlmProviderDep
from app.core.db import get_db
from app.schemas.common import ClientId
from app.schemas.seo import SeoAuditRequest, SeoAuditResponse, SeoAuditSummary
from app.services import seo_audit

router = APIRouter(prefix="/api/seo", tags=["seo"])

DbDep = Annotated[Session, Depends(get_db)]


@router.post("/audit", response_model=SeoAuditResponse)
async def audit(body: SeoAuditRequest, db: DbDep, provider: LlmProviderDep) -> SeoAuditResponse:
    """Fetch the URL safely, run 10 checks, score it and attach an AI report (cached 1 h)."""
    return await seo_audit.run_audit(db, body.url, body.client_id, provider)


@router.get("/history", response_model=list[SeoAuditSummary])
def history(db: DbDep, client: Annotated[ClientId | None, Query()] = None) -> list[SeoAuditSummary]:
    """The 10 most recent audits, optionally for one client."""
    return seo_audit.history(db, client)


@router.get("/audits/{audit_id}", response_model=SeoAuditResponse)
def get_audit(audit_id: uuid.UUID, db: DbDep) -> SeoAuditResponse:
    return seo_audit.get_audit(db, audit_id)
