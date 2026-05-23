"""Tests for REST API endpoints — LLD Section 19."""

import time
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "device" in data


class TestSessionEndpoints:
    def test_create_session(self, client):
        r = client.post("/session/create", json={
            "device_id": "test-api", "mode": "sync",
        })
        assert r.status_code == 200
        assert "session_id" in r.json()

    def test_list_sessions(self, client):
        client.post("/session/create", json={"device_id": "test-list", "mode": "sync"})
        r = client.get("/session/list")
        assert r.status_code == 200
        sessions = r.json()
        assert isinstance(sessions, list)
        assert len(sessions) >= 1

    def test_close_session(self, client):
        r = client.post("/session/create", json={"device_id": "test-close", "mode": "sync"})
        sid = r.json()["session_id"]
        r = client.post(f"/session/close?session_id={sid}")
        assert r.status_code == 200
        assert r.json()["status"] == "closed"

    def test_close_nonexistent_404(self, client):
        r = client.post("/session/close?session_id=nonexistent")
        assert r.status_code == 404


class TestStreamEndpoints:
    def test_imu_packet(self, client):
        ts = time.time()
        r = client.post("/imu", json={
            "timestamp": ts, "ax": 0.1, "ay": 0.2, "az": 9.81,
            "gx": 0.01, "gy": 0.02, "gz": 0.03,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_imu_invalid_timestamp(self, client):
        r = client.post("/imu", json={
            "timestamp": -1.0, "ax": 0, "ay": 0, "az": 0,
            "gx": 0, "gy": 0, "gz": 0,
        })
        assert r.status_code == 422  # Pydantic validation error

    def test_frame_packet(self, client):
        import base64
        ts = time.time()
        data = base64.b64encode(b'\xff\xd8\xff' + b'\x00' * 100 + b'\xff\xd9').decode()
        r = client.post("/frame", json={
            "timestamp": ts, "frame_id": 0,
            "resolution": "640x480", "data": data,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_frame_invalid_base64_rejected(self, client):
        ts = time.time()
        r = client.post("/frame", json={
            "timestamp": ts, "frame_id": 0,
            "resolution": "640x480", "data": "not-valid-base64!!!",
        })
        assert r.status_code == 400

    def test_imu_only_window_processing(self, client):
        ts = time.time()
        for i in range(25):
            packet_ts = ts + i * 0.1
            r = client.post("/imu", json={
                "timestamp": packet_ts,
                "ax": 0.1, "ay": 0.2, "az": 9.81,
                "gx": 0.01, "gy": 0.02, "gz": 0.03,
                "mode": "imu_only",
            })
            assert r.status_code == 200

        r = client.get("/session/list")
        assert r.status_code == 200
        sessions = r.json()
        active_session = [s for s in sessions if s["device_id"] == "mobile-auto"]
        assert len(active_session) >= 1
        # Session mode may be imu_only or sync depending on ordering
        assert active_session[0]["windows_processed"] >= 1

    def test_dual_source_interleaved_streaming(self, client):
        """Simulate ESP32 (IMU) and mobile phone (camera) streaming simultaneously.

        Both devices send `mode="sync"`. They must land on the same
        session and produce at least one fused window.
        """
        import base64
        ts = time.time()

        for i in range(60):
            # IMU packet at 20 Hz (every 50ms)
            imu_ts = ts + i * 0.05
            r = client.post("/imu", json={
                "timestamp": imu_ts,
                "ax": 0.1 + i * 0.001, "ay": 0.2, "az": 9.81,
                "gx": 0.01, "gy": 0.02, "gz": 0.03,
                "mode": "sync",
            })
            assert r.status_code == 200
            imu_session_id = r.json()["session_id"]

            # Camera frame at ~5 FPS (every 4th IMU packet ≈ 200ms)
            if i % 4 == 0:
                frame_ts = ts + i * 0.05
                frame_data = base64.b64encode(
                    b'\xff\xd8\xff' + b'\x00' * 100 + b'\xff\xd9'
                ).decode()
                r = client.post("/frame", json={
                    "timestamp": frame_ts,
                    "frame_id": i // 4,
                    "resolution": "640x480",
                    "data": frame_data,
                    "mode": "sync",
                })
                assert r.status_code == 200
                frame_session_id = r.json()["session_id"]

                # Both devices MUST share the same session
                assert imu_session_id == frame_session_id

        # Verify session state
        r = client.get("/session/list")
        assert r.status_code == 200
        sessions = r.json()
        session = [s for s in sessions if s["session_id"] == imu_session_id]
        assert len(session) == 1
        s = session[0]
        assert s["imu_packet_count"] == 60
        assert s["frame_count"] >= 1
        # The window buffer should have processed at least 1 window
        # (60 IMU at 20Hz = 3s span, window_size=2s → at least 1 window)
        assert s["windows_processed"] >= 1
