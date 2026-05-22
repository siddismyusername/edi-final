"""
Session management endpoints.
POST /session/create, POST /session/close, GET /session/list, GET /session/export
Per LLD Section 3.1 and 7.
"""

from fastapi import APIRouter, HTTPException
from typing import List

from app.models.schemas import (
    SessionCreateRequest, SessionResponse, SessionInfo, ErrorResponse,
)

router = APIRouter(prefix="/session", tags=["session"])


@router.post("/create", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest):
    """Create a new sensor streaming session."""
    from app.main import get_session_manager, get_session_store

    sm = get_session_manager()
    store = get_session_store()

    try:
        session = sm.create_session(
            device_id=request.device_id,
            mode=request.mode.value,
            notes=request.notes,
        )

        # Persist metadata
        store.save_metadata(session.session_id, session.to_dict())

        return SessionResponse(
            session_id=session.session_id,
            status="created",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))


@router.post("/close", response_model=SessionResponse)
async def close_session(session_id: str):
    """Close an active session."""
    from app.main import get_session_manager, get_session_store, get_buffers, get_sync_replay_cache

    sm = get_session_manager()
    session = sm.close_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Clean up buffer
    buffers = get_buffers()
    if session_id in buffers:
        buffers[session_id].clear()
        del buffers[session_id]

    get_sync_replay_cache().clear_session(session_id)

    # Update persisted metadata
    store = get_session_store()
    store.save_metadata(session_id, session.to_dict())

    return SessionResponse(
        session_id=session_id,
        status="closed",
    )


@router.get("/list", response_model=List[SessionInfo])
async def list_sessions():
    """List all active sessions."""
    from app.main import get_session_manager

    sm = get_session_manager()
    sessions = sm.list_sessions()

    return [
        SessionInfo(
            session_id=s.session_id,
            device_id=s.metadata.device_id,
            mode=s.metadata.mode,
            state=s.state.value,
            created_at=s.metadata.created_at,
            imu_packet_count=s.stream_state.imu_packet_count,
            frame_count=s.stream_state.frame_count,
            windows_processed=s.windows_processed,
            notes=s.metadata.notes,
        )
        for s in sessions
    ]


@router.get("/export/{session_id}")
async def export_session(session_id: str):
    """Export session artifacts."""
    from app.main import get_session_store

    store = get_session_store()
    metadata = store.load_metadata(session_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {
        "session_id": session_id,
        "metadata": metadata,
        "status": "exported",
    }
