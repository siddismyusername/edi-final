"""
Session data model.
Tracks runtime state, buffers, and metadata for each active session.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import time
import uuid


class SessionStateEnum(str, Enum):
    INITIALIZED = "initialized"
    STREAMING = "streaming"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ERROR = "error"


@dataclass
class SessionMetadata:
    """Device and capture metadata for a session."""
    device_id: str
    mode: str  # "sync" or "async"
    notes: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None


@dataclass
class StreamState:
    """Tracks stream lifecycle statistics."""
    imu_packet_count: int = 0
    frame_count: int = 0
    dropped_packets: int = 0
    last_imu_timestamp: Optional[float] = None
    last_frame_timestamp: Optional[float] = None
    imu_timestamps: List[float] = field(default_factory=list)
    frame_timestamps: List[float] = field(default_factory=list)


@dataclass
class WindowState:
    """Active temporal window state."""
    window_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    is_ready: bool = False
    imu_count: int = 0
    frame_count: int = 0


@dataclass
class Session:
    """Runtime session state container."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: SessionMetadata = field(default_factory=lambda: SessionMetadata(device_id="unknown", mode="sync"))
    state: SessionStateEnum = SessionStateEnum.INITIALIZED
    stream_state: StreamState = field(default_factory=StreamState)
    window_state: WindowState = field(default_factory=WindowState)
    windows_processed: int = 0
    last_activity: float = field(default_factory=time.time)

    # Diagnostic metrics
    latest_dtw_latency_ms: float = 0.0
    latest_fusion_latency_ms: float = 0.0
    latest_confidence: float = 0.0
    latest_prediction: str = "unknown"

    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session for API responses."""
        return {
            "session_id": self.session_id,
            "device_id": self.metadata.device_id,
            "mode": self.metadata.mode,
            "state": self.state.value,
            "created_at": self.metadata.created_at,
            "imu_packet_count": self.stream_state.imu_packet_count,
            "frame_count": self.stream_state.frame_count,
            "windows_processed": self.windows_processed,
            "notes": self.metadata.notes,
        }
