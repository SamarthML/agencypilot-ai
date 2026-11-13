"""LLM usage and cost: Pandas aggregations over llm_usage, plus the latest calls."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.usage import UsageCall, UsageDays, UsageSummary
from app.services import usage

router = APIRouter(prefix="/api/usage", tags=["usage"])

DbDep = Annotated[Session, Depends(get_db)]


@router.get("/summary", response_model=UsageSummary)
def summary(db: DbDep, days: Annotated[UsageDays, Query()] = 30) -> UsageSummary:
    """Totals, latency, cache savings and breakdowns by feature, model and day (UTC)."""
    return usage.get_summary(db, days)


@router.get("/recent", response_model=list[UsageCall])
def recent(db: DbDep, limit: Annotated[int, Query(ge=1, le=200)] = 50) -> list[UsageCall]:
    """The latest logged requests, newest first."""
    return usage.recent_calls(db, limit)
