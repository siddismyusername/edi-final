"""
Mobile sync replay endpoints.

These endpoints expose the latest fused windows from the existing pipeline.
They do not trigger fusion or read persisted artifacts.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/sync", tags=["sync"])


def _require_active_session(session_id: str):
    from app.main import get_session_manager
    from app.models.session import SessionStateEnum

    session = get_session_manager().get_session(session_id)
    if not session or session.state in {
        SessionStateEnum.COMPLETED,
        SessionStateEnum.ARCHIVED,
        SessionStateEnum.ERROR,
    }:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


@router.get("/status")
async def sync_status(session_id: str):
    """Return whether synchronized playback is ready for an active session."""
    from app.main import get_sync_replay_cache

    _require_active_session(session_id)
    return get_sync_replay_cache().status(session_id)


@router.get("/latest")
async def sync_latest(session_id: str, offset_seconds: float = 0.0):
    """Return the fused replay window at the requested live offset."""
    from app.main import get_sync_replay_cache

    _require_active_session(session_id)
    snapshot = get_sync_replay_cache().latest(
        session_id=session_id,
        offset_seconds=offset_seconds,
    )
    if snapshot is None:
        raise HTTPException(
            status_code=409,
            detail=f"Sync playback for session {session_id} is not ready",
        )
    return snapshot
