"""
Session Manager — owns session lifecycle, state transitions, and expiration.
In-memory session store with logging on all transitions.
"""

import logging
import time
from typing import Dict, Optional, List

from app.models.session import Session, SessionMetadata, SessionStateEnum

logger = logging.getLogger("etasync.session")


class SessionManager:
    """Manages active sessions and their lifecycles."""

    def __init__(self, timeout_seconds: int = 600, max_sessions: int = 10):
        self._sessions: Dict[str, Session] = {}
        self._timeout = timeout_seconds
        self._max_sessions = max_sessions

    # ── Session CRUD ────────────────────────────────────────

    def create_session(
        self,
        device_id: str,
        mode: str = "sync",
        notes: Optional[str] = None,
    ) -> Session:
        """Create a new session."""
        # Evict expired sessions first
        self._cleanup_expired()

        if len(self._sessions) >= self._max_sessions:
            raise RuntimeError(
                f"Maximum active sessions ({self._max_sessions}) reached. "
                "Close existing sessions first."
            )

        metadata = SessionMetadata(device_id=device_id, mode=mode, notes=notes)
        session = Session(metadata=metadata)

        self._sessions[session.session_id] = session
        logger.info(
            f"Session created: {session.session_id} "
            f"(device={device_id}, mode={mode})"
        )
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        session = self._sessions.get(session_id)
        if session and self._is_expired(session):
            self._expire_session(session)
            return None
        return session

    def close_session(self, session_id: str) -> Optional[Session]:
        """Close an active session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        session.state = SessionStateEnum.COMPLETED
        session.metadata.closed_at = time.time()
        logger.info(f"Session closed: {session_id}")
        return session

    def remove_session(self, session_id: str) -> bool:
        """Remove a session from the active store."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Session removed: {session_id}")
            return True
        return False

    def list_sessions(self) -> List[Session]:
        """List all active sessions."""
        self._cleanup_expired()
        return list(self._sessions.values())

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    # ── State Transitions ───────────────────────────────────

    def transition_state(
        self, session_id: str, new_state: SessionStateEnum
    ) -> bool:
        """Transition a session to a new state with logging."""
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"State transition failed: session {session_id} not found")
            return False

        old_state = session.state
        session.state = new_state
        session.touch()

        logger.info(
            f"Session {session_id}: {old_state.value} → {new_state.value}"
        )
        return True

    # ── Expiration ──────────────────────────────────────────

    def _is_expired(self, session: Session) -> bool:
        return (time.time() - session.last_activity) > self._timeout

    def _expire_session(self, session: Session):
        logger.warning(f"Session expired: {session.session_id}")
        session.state = SessionStateEnum.COMPLETED
        session.metadata.closed_at = time.time()
        del self._sessions[session.session_id]

    def _cleanup_expired(self):
        expired = [
            sid for sid, s in self._sessions.items() if self._is_expired(s)
        ]
        for sid in expired:
            self._expire_session(self._sessions[sid])
