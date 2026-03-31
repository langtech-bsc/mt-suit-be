"""Health check endpoint."""

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class HealthStatus(BaseModel):
    status: str = "ok"

@router.get("/health", response_model=HealthStatus, status_code=status.HTTP_200_OK)
async def health_check():
    """Provides a simple health check endpoint."""
    return HealthStatus()