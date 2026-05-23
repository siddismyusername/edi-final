"""Tests for window buffer — LLD Section 19."""

import time
import pytest
from app.buffers.window_buffer import WindowBuffer


@pytest.fixture
def buffer():
    return WindowBuffer(
        window_size=2.0,
        overlap_ratio=0.5,
        min_imu=5,
        min_frames=2,
    )


class TestWindowReadiness:
    def test_empty_buffer_not_ready(self, buffer):
        assert buffer.is_window_ready() is False

    def test_imu_only_not_ready(self, buffer):
        base = time.time()
        for i in range(20):
            buffer.add_imu_packet({"timestamp": base + i * 0.1, "ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0})
        assert buffer.is_window_ready() is False

    def test_frames_only_not_ready(self, buffer):
        base = time.time()
        for i in range(10):
            buffer.add_frame_packet({"timestamp": base + i * 0.2, "frame_id": i})
        assert buffer.is_window_ready() is False

    def test_ready_with_enough_data(self, buffer):
        base = time.time()
        for i in range(60):
            buffer.add_imu_packet({"timestamp": base + i * 0.04, "ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0})
        for i in range(12):
            buffer.add_frame_packet({"timestamp": base + i * 0.2, "frame_id": i})
        assert buffer.is_window_ready() is True


class TestWindowExtraction:
    def test_extract_returns_data(self, buffer):
        base = time.time()
        for i in range(60):
            buffer.add_imu_packet({"timestamp": base + i * 0.04, "ax": 0.1, "ay": 0.2, "az": 9.81, "gx": 0, "gy": 0, "gz": 0})
        for i in range(12):
            buffer.add_frame_packet({"timestamp": base + i * 0.2, "frame_id": i})

        window = buffer.extract_window()
        assert window is not None
        assert "window_id" in window
        assert "imu_packets" in window
        assert "frame_packets" in window
        assert len(window["imu_packets"]) >= 5
        assert len(window["frame_packets"]) >= 2

    def test_extract_empty_returns_none(self, buffer):
        assert buffer.extract_window() is None

    def test_window_count_increments(self, buffer):
        base = time.time()
        for i in range(60):
            buffer.add_imu_packet({"timestamp": base + i * 0.04, "ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0})
        for i in range(12):
            buffer.add_frame_packet({"timestamp": base + i * 0.2, "frame_id": i})

        buffer.extract_window()
        assert buffer.windows_extracted == 1

    def test_staggered_sources_align_to_common_time_range(self, buffer):
        base = time.time()

        for i in range(400):
            buffer.add_imu_packet({"timestamp": base + i * 0.05, "ax": 0.1, "ay": 0.2, "az": 9.81, "gx": 0, "gy": 0, "gz": 0})

        camera_start = base + 10.0
        for i in range(16):
            buffer.add_frame_packet({"timestamp": camera_start + i * 0.2, "frame_id": i})

        assert buffer.is_window_ready() is True
        window = buffer.extract_window()

        assert window is not None
        assert window["start_time"] >= camera_start
        assert len(window["imu_packets"]) >= buffer.min_imu
        assert len(window["frame_packets"]) >= buffer.min_frames


class TestBufferClear:
    def test_clear_resets(self, buffer):
        base = time.time()
        buffer.add_imu_packet({"timestamp": base, "ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0})
        buffer.add_frame_packet({"timestamp": base, "frame_id": 0})
        buffer.clear()
        assert buffer.imu_count == 0
        assert buffer.frame_count == 0
