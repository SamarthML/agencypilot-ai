"""reports routes. Endpoints are added in later phases."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/reports", tags=["reports"])
