"""
Sliding Temporal Window Buffer.
Maintains separate IMU and video buffers with 50% overlap,
FIFO eviction, and window completion detection per LLD Section 10.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from collections import deque

from config.settings import settings

logger = logging.getLogger("etasync.buffer")


@dataclass
class WindowBuffer:
    """
    Manages sliding temporal windows for a session.
    Buffers incoming IMU and camera packets and emits complete windows
    when sufficient data has been collected.
    """

    window_size: float = field(default_factory=lambda: settings.window_size_seconds)
    overlap_ratio: float = field(default_factory=lambda: settings.window_overlap_ratio)
    min_imu: int = field(default_factory=lambda: settings.min_imu_packets_per_window)
    min_frames: int = field(default_factory=lambda: settings.min_frames_per_window)

    # Internal buffers
    _imu_buffer: List[Dict[str, Any]] = field(default_factory=list)
    _frame_buffer: List[Dict[str, Any]] = field(default_factory=list)

    # Window tracking
    _window_start: Optional[float] = None
    _window_count: int = 0

    def _synchronize_window_start(self):
        """
        For multimodal windows, start from the first timestamp where both
        streams can contribute. This avoids processing many empty frame windows
        when one external source starts earlier than the other.
        """
        if self.min_frames <= 0 or not self._imu_buffer or not self._frame_buffer:
            return

        first_common_start = max(
            self._imu_buffer[0]["timestamp"],
            self._frame_buffer[0]["timestamp"],
        )
        if self._window_start is None or self._window_start < first_common_start:
            old_start = self._window_start
            self._window_start = first_common_start

            imu_before = len(self._imu_buffer)
            frame_before = len(self._frame_buffer)

            self._imu_buffer = [
                p for p in self._imu_buffer if p["timestamp"] >= self._window_start
            ]
            self._frame_buffer = [
                p for p in self._frame_buffer if p["timestamp"] >= self._window_start
            ]

            imu_evicted = imu_before - len(self._imu_buffer)
            frame_evicted = frame_before - len(self._frame_buffer)
            if imu_evicted > 0 or frame_evicted > 0:
                logger.warning(
                    f"Staggered start sync: window_start moved "
                    f"{old_start:.3f} → {first_common_start:.3f}, "
                    f"evicted {imu_evicted} IMU / {frame_evicted} frame packets"
                )

    def add_imu_packet(self, packet: Dict[str, Any]):
        """Add an IMU packet to the buffer."""
        self._imu_buffer.append(packet)
        if self._window_start is None:
            self._window_start = packet["timestamp"]

    def add_frame_packet(self, packet: Dict[str, Any]):
        """Add a camera frame packet to the buffer."""
        self._frame_buffer.append(packet)
        if self._window_start is None:
            self._window_start = packet["timestamp"]

    def is_window_ready(self) -> bool:
        """
        Check if the current window has enough data.
        A window is ready when:
        - Sufficient IMU packets exist
        - Sufficient frame packets exist (if min_frames > 0)
        - The time span covers the window size
        """
        if not self._imu_buffer:
            return False

        if self.min_frames > 0 and not self._frame_buffer:
            return False

        self._synchronize_window_start()

        if len(self._imu_buffer) < self.min_imu:
            return False

        if self.min_frames > 0 and len(self._frame_buffer) < self.min_frames:
            return False

        if self._window_start is None:
            return False

        # Check the span covered by all required streams.
        latest_timestamp = self._imu_buffer[-1]["timestamp"]
        if self.min_frames > 0:
            latest_timestamp = min(
                latest_timestamp,
                self._frame_buffer[-1]["timestamp"],
            )
        time_span = latest_timestamp - self._window_start
        return time_span >= self.window_size

    def extract_window(self) -> Optional[Dict[str, Any]]:
        """
        Extract the current window data and advance with overlap.
        Returns a dict with imu_packets, frame_packets, window_id, timestamps.
        Returns None if the extracted window has insufficient data.
        """
        if not self.is_window_ready():
            return None

        window_end = self._window_start + self.window_size

        # Extract packets within the window
        imu_window = [
            p for p in self._imu_buffer
            if self._window_start <= p["timestamp"] <= window_end
        ]
        frame_window = [
            p for p in self._frame_buffer
            if self._window_start <= p["timestamp"] <= window_end
        ]

        # Reject if extracted window has no data in either modality
        if len(imu_window) < self.min_imu or (self.min_frames > 0 and len(frame_window) < self.min_frames):
            logger.debug(
                f"Window rejected: {len(imu_window)} IMU, {len(frame_window)} frames "
                f"(need {self.min_imu}/{self.min_frames})"
            )
            # Still advance the window to avoid re-checking the same range
            advance = self.window_size * (1.0 - self.overlap_ratio)
            self._window_start = self._window_start + advance
            return None

        self._window_count += 1
        window_id = f"w{self._window_count:04d}"

        window_data = {
            "window_id": window_id,
            "start_time": self._window_start,
            "end_time": window_end,
            "imu_packets": imu_window,
            "frame_packets": frame_window,
            "imu_count": len(imu_window),
            "frame_count": len(frame_window),
        }

        # Advance window with overlap (keep overlap_ratio of data)
        advance = self.window_size * (1.0 - self.overlap_ratio)
        new_start = self._window_start + advance

        # Evict old packets (FIFO)
        self._imu_buffer = [
            p for p in self._imu_buffer if p["timestamp"] >= new_start
        ]
        self._frame_buffer = [
            p for p in self._frame_buffer if p["timestamp"] >= new_start
        ]
        self._window_start = new_start

        logger.info(
            f"Window {window_id} extracted: "
            f"{len(imu_window)} IMU, {len(frame_window)} frames, "
            f"span={window_end - window_data['start_time']:.2f}s"
        )

        return window_data

    def clear(self):
        """Clear all buffers."""
        self._imu_buffer.clear()
        self._frame_buffer.clear()
        self._window_start = None

    @property
    def imu_count(self) -> int:
        return len(self._imu_buffer)

    @property
    def frame_count(self) -> int:
        return len(self._frame_buffer)

    @property
    def windows_extracted(self) -> int:
        return self._window_count
