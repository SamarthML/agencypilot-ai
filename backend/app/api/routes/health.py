from fastapi import APIRouter

from app.core import db
from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_ok = db.check_db()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db="ok" if db_ok else "down",
        version=get_settings().version,
    )
