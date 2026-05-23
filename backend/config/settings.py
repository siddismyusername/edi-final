"""
ETA-Sync Configuration Module
Centralizes all configurable parameters for the backend.
"""

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    # ── Server ──────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    cors_origins: List[str] = ["*"]

    # ── Session ─────────────────────────────────────────────
    session_timeout_seconds: int = 600  # 10 minutes
    max_active_sessions: int = 10

    # ── Window Buffer ───────────────────────────────────────
    window_size_seconds: float = 2.0
    window_overlap_ratio: float = 0.5
    min_imu_packets_per_window: int = 20
    min_frames_per_window: int = 3

    # ── DTW ─────────────────────────────────────────────────
    dtw_radius: int = 10  # FastDTW radius constraint
    dtw_normalization_mode: str = "softmax"  # "softmax" | "minmax"

    # ── AI / Fusion ─────────────────────────────────────────
    embedding_dim: int = 128
    num_attention_heads: int = 4
    alpha_dtw: float = 1.0  # DTW bias influence coefficient
    num_activity_classes: int = 6
    activity_labels: List[str] = [
        "walking", "running", "standing",
        "sitting", "jumping", "unknown",
    ]
    device: str = "cpu"  # "cpu" or "cuda"

    # ── Camera / Frames ─────────────────────────────────────
    max_frame_size_bytes: int = 5_000_000  # 5 MB
    frame_width: int = 224
    frame_height: int = 224

    # ── Persistence ─────────────────────────────────────────
    sessions_dir: str = "sessions"

    # ── WebSocket ───────────────────────────────────────────
    ws_heartbeat_interval: float = 5.0
    ws_max_clients: int = 20

    # ── Mobile Sync Replay ─────────────────────────────────
    sync_replay_seconds: int = 120

    model_config = ConfigDict(
        env_prefix="ETASYNC_",
        env_file=".env",
    )


# Singleton settings instance
settings = Settings()
