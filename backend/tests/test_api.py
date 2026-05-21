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
