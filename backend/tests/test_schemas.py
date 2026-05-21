"""Tests for Pydantic schema validation — LLD Section 19."""

import pytest
from pydantic import ValidationError
from app.models.schemas import (
    SensorPacket, CameraPacket, SessionCreateRequest,
    SessionInfo, SessionState, DiagnosticsSnapshot,
)


class TestSensorPacket:
    def test_valid_imu_packet(self):
        p = SensorPacket(
            timestamp=1715800000.0, ax=0.12, ay=0.44, az=9.81,
            gx=0.01, gy=0.04, gz=0.07,
        )
        assert p.ax == 0.12
        assert p.mode == "sync"

    def test_negative_timestamp_rejected(self):
        with pytest.raises(ValidationError):
            SensorPacket(
                timestamp=-1.0, ax=0.0, ay=0.0, az=0.0,
                gx=0.0, gy=0.0, gz=0.0,
            )

    def test_zero_timestamp_rejected(self):
        with pytest.raises(ValidationError):
            SensorPacket(
                timestamp=0.0, ax=0.0, ay=0.0, az=0.0,
                gx=0.0, gy=0.0, gz=0.0,
            )

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            SensorPacket(timestamp=1.0, ax=0.0, ay=0.0, az=0.0)  # missing gx/gy/gz


class TestCameraPacket:
    def test_valid_frame_packet(self):
        p = CameraPacket(
            timestamp=1715800000.0, frame_id=0,
            data="base64data", resolution="640x480",
        )
        assert p.frame_id == 0

    def test_negative_timestamp_rejected(self):
        with pytest.raises(ValidationError):
            CameraPacket(timestamp=-5.0, frame_id=0, data="abc")


class TestSessionCreateRequest:
    def test_valid_request(self):
        r = SessionCreateRequest(device_id="test-001", mode="sync")
        assert r.device_id == "test-001"

    def test_empty_device_id_rejected(self):
        with pytest.raises(ValidationError):
            SessionCreateRequest(device_id="", mode="sync")


class TestSessionInfo:
    def test_includes_windows_processed(self):
        info = SessionInfo(
            session_id="abc", device_id="d1", mode="sync",
            state=SessionState.STREAMING, created_at=1.0,
            imu_packet_count=10, frame_count=5, windows_processed=3,
        )
        assert info.windows_processed == 3

    def test_defaults(self):
        info = SessionInfo(
            session_id="abc", device_id="d1", mode="sync",
            state=SessionState.INITIALIZED, created_at=1.0,
        )
        assert info.imu_packet_count == 0
        assert info.frame_count == 0
        assert info.windows_processed == 0
