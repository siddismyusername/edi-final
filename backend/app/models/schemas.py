"""
Pydantic schemas for all API request/response contracts.
Matches the JSON structures defined in LLD Section 6-7.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from enum import Enum
import time


# ── Enums ───────────────────────────────────────────────────

class SensorType(str, Enum):
    IMU = "imu"
    CAMERA = "camera"


class StreamingMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"
    IMU_ONLY = "imu_only"


class SessionState(str, Enum):
    INITIALIZED = "initialized"
    STREAMING = "streaming"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ERROR = "error"


class RuntimeState(str, Enum):
    IDLE = "idle"
    SESSION_ACTIVE = "session_active"
    BUFFERING = "buffering"
    ALIGNING = "aligning"
    FUSING = "fusing"
    BROADCASTING = "broadcasting"
    ERROR = "error"


# ── Sensor Packets ──────────────────────────────────────────

class SensorPacket(BaseModel):
    """IMU sensor data packet from mobile device."""
    timestamp: float
    ax: float = Field(..., description="Accelerometer X-axis (m/s²)")
    ay: float = Field(..., description="Accelerometer Y-axis (m/s²)")
    az: float = Field(..., description="Accelerometer Z-axis (m/s²)")
    gx: float = Field(..., description="Gyroscope X-axis (rad/s)")
    gy: float = Field(..., description="Gyroscope Y-axis (rad/s)")
    gz: float = Field(..., description="Gyroscope Z-axis (rad/s)")
    mode: Optional[str] = "sync"

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Timestamp must be positive")
        return v


class CameraPacket(BaseModel):
    """Camera frame packet from mobile device."""
    timestamp: float
    frame_id: int = Field(..., description="Sequential frame identifier")
    resolution: Optional[str] = "640x480"
    data: str = Field(..., description="Base64-encoded JPEG frame data")
    mode: Optional[str] = "sync"

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Timestamp must be positive")
        return v


# ── Session ─────────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    """Request to create a new session."""
    device_id: str = Field(..., min_length=1, description="Unique device identifier")
    mode: StreamingMode = StreamingMode.SYNC
    notes: Optional[str] = None


class SessionResponse(BaseModel):
    """Response after session creation."""
    session_id: str
    status: str


class SessionInfo(BaseModel):
    """Detailed session information."""
    session_id: str
    device_id: str
    mode: str
    state: SessionState
    created_at: float
    imu_packet_count: int = 0
    frame_count: int = 0
    windows_processed: int = 0
    notes: Optional[str] = None


# ── Error ───────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    session_id: Optional[str] = None


# ── Alignment / Fusion Outputs ──────────────────────────────

class AlignmentOutput(BaseModel):
    """DTW alignment result for a processing window."""
    session_id: str
    window_id: str
    cost_matrix_path: Optional[str] = None
    alignment_path: List[List[int]] = []
    dtw_bias_matrix_path: Optional[str] = None
    dtw_distance: float = 0.0
    computation_time_ms: float = 0.0


class FusionOutput(BaseModel):
    """Cross-attention fusion result."""
    session_id: str
    window_id: str
    prediction: str = "unknown"
    confidence_score: float = 0.0
    attention_weights_path: Optional[str] = None
    fused_representation_path: Optional[str] = None
    computation_time_ms: float = 0.0


# ── WebSocket Events ────────────────────────────────────────

class WSEvent(BaseModel):
    """WebSocket event for dashboard broadcast."""
    event: str
    session_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    data: Optional[dict] = None


# ── Diagnostics ─────────────────────────────────────────────

class DiagnosticsSnapshot(BaseModel):
    """Runtime diagnostics for observability."""
    session_id: str
    runtime_state: RuntimeState
    imu_packet_rate: float = 0.0
    frame_rate: float = 0.0
    dropped_packets: int = 0
    dtw_latency_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    confidence_score: float = 0.0
    windows_processed: int = 0


# ── Health ──────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    active_sessions: int = 0
    device: str = "cpu"
