"""Tests for mobile sync replay endpoints."""

from fastapi.testclient import TestClient

import app.main as app_main
from app.core.sync_replay_cache import SyncReplaySnapshot

app = app_main.app


def make_snapshot(session_id: str) -> SyncReplaySnapshot:
    return SyncReplaySnapshot(
        session_id=session_id,
        server_timestamp=123.0,
        window_start=100.0,
        window_end=102.0,
        prediction="walking",
        confidence_score=0.8,
        all_probabilities={"walking": 0.8, "unknown": 0.2},
        imu_summary={"count": 20},
        frame_preview=None,
        dtw_distance=0.25,
        alignment_path=[[0, 0], [1, 1]],
    )


def create_session(client: TestClient) -> str:
    response = client.post(
        "/session/create",
        json={"device_id": "sync-api-test", "mode": "sync"},
    )
    assert response.status_code == 200
    return response.json()["session_id"]


class TestSyncEndpoints:
    def test_status_without_session_reports_api_available(self, monkeypatch):
        monkeypatch.setattr(app_main, "_fusion_service", object())
        with TestClient(app) as client:
            response = client.get("/sync/status")
            assert response.status_code == 200
            assert response.json()["available"] is True

    def test_status_not_ready_for_active_session(self, monkeypatch):
        monkeypatch.setattr(app_main, "_fusion_service", object())
        with TestClient(app) as client:
            session_id = create_session(client)
            response = client.get(f"/sync/status?session_id={session_id}")
            assert response.status_code == 200
            assert response.json() == {
                "session_id": session_id,
                "ready": False,
                "available_seconds": 0.0,
                "max_replay_seconds": 120.0,
            }

    def test_latest_returns_409_before_fusion_snapshot(self, monkeypatch):
        monkeypatch.setattr(app_main, "_fusion_service", object())
        with TestClient(app) as client:
            session_id = create_session(client)
            response = client.get(f"/sync/latest?session_id={session_id}")
            assert response.status_code == 409

    def test_latest_returns_required_shape_when_ready(self, monkeypatch):
        monkeypatch.setattr(app_main, "_fusion_service", object())
        with TestClient(app) as client:
            session_id = create_session(client)
            app_main.get_sync_replay_cache().add(make_snapshot(session_id))

            status = client.get(f"/sync/status?session_id={session_id}")
            assert status.status_code == 200
            assert status.json()["ready"] is True

            response = client.get(f"/sync/latest?session_id={session_id}&offset_seconds=0")
            assert response.status_code == 200
            data = response.json()
            assert set(data) == {
                "session_id",
                "server_timestamp",
                "window_start",
                "window_end",
                "prediction",
                "confidence_score",
                "all_probabilities",
                "imu_summary",
                "frame_preview",
                "dtw_distance",
                "alignment_path",
            }
            assert data["session_id"] == session_id
            assert data["frame_preview"] is None

    def test_unknown_or_closed_session_returns_404(self, monkeypatch):
        monkeypatch.setattr(app_main, "_fusion_service", object())
        with TestClient(app) as client:
            response = client.get("/sync/status?session_id=missing")
            assert response.status_code == 404

            session_id = create_session(client)
            app_main.get_sync_replay_cache().add(make_snapshot(session_id))
            client.post(f"/session/close?session_id={session_id}")

            response = client.get(f"/sync/latest?session_id={session_id}")
            assert response.status_code == 404
