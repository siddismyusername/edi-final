"""Tests for session management lifecycle — LLD Section 19."""

import pytest
from app.core.session_manager import SessionManager
from app.models.session import SessionStateEnum


@pytest.fixture
def sm():
    return SessionManager()


class TestSessionLifecycle:
    def test_create_session(self, sm):
        session = sm.create_session(device_id="dev-001", mode="sync")
        assert session.session_id
        assert session.metadata.device_id == "dev-001"
        assert session.state == SessionStateEnum.INITIALIZED

    def test_list_sessions(self, sm):
        sm.create_session(device_id="dev-001", mode="sync")
        sm.create_session(device_id="dev-002", mode="async")
        sessions = sm.list_sessions()
        assert len(sessions) == 2

    def test_close_session(self, sm):
        session = sm.create_session(device_id="dev-001", mode="sync")
        closed = sm.close_session(session.session_id)
        assert closed is not None
        assert closed.state == SessionStateEnum.COMPLETED

    def test_close_nonexistent_session(self, sm):
        result = sm.close_session("nonexistent-id")
        assert result is None

    def test_get_session(self, sm):
        session = sm.create_session(device_id="dev-001", mode="sync")
        found = sm.get_session(session.session_id)
        assert found is not None
        assert found.session_id == session.session_id


class TestStateTransitions:
    def test_init_to_streaming(self, sm):
        session = sm.create_session(device_id="dev-001", mode="sync")
        sm.transition_state(session.session_id, SessionStateEnum.STREAMING)
        assert sm.get_session(session.session_id).state == SessionStateEnum.STREAMING

    def test_streaming_to_processing(self, sm):
        session = sm.create_session(device_id="dev-001", mode="sync")
        sm.transition_state(session.session_id, SessionStateEnum.STREAMING)
        sm.transition_state(session.session_id, SessionStateEnum.PROCESSING)
        assert sm.get_session(session.session_id).state == SessionStateEnum.PROCESSING

    def test_processing_to_streaming(self, sm):
        session = sm.create_session(device_id="dev-001", mode="sync")
        sm.transition_state(session.session_id, SessionStateEnum.STREAMING)
        sm.transition_state(session.session_id, SessionStateEnum.PROCESSING)
        sm.transition_state(session.session_id, SessionStateEnum.STREAMING)
        assert sm.get_session(session.session_id).state == SessionStateEnum.STREAMING


class TestSessionToDict:
    def test_to_dict_includes_all_fields(self, sm):
        session = sm.create_session(device_id="dev-001", mode="sync", notes="test")
        d = session.to_dict()
        assert "session_id" in d
        assert "device_id" in d
        assert "mode" in d
        assert "state" in d
        assert "windows_processed" in d
        assert "notes" in d
        assert d["notes"] == "test"
