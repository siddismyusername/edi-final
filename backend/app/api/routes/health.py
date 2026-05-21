"""
Health check endpoint.
GET /health — returns server status per LLD Section 3.1.
"""

from fastapi import APIRouter

from app.models.schemas import HealthResponse
from config.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Backend health check endpoint."""
    # Import here to avoid circular dependency
    from app.main import get_session_manager
    sm = get_session_manager()

    return HealthResponse(
        status="ok",
        version="1.0.0",
        active_sessions=sm.active_count if sm else 0,
        device=settings.device,
    )
