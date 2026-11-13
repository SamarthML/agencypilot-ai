"""usage routes. Endpoints are added in later phases."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/usage", tags=["usage"])
