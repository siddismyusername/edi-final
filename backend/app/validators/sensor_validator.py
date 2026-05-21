"""
Sensor packet validation.
Enforces schema, timestamp, and payload constraints per LLD Section 15.
"""

import logging
import time
from typing import Tuple

from config.settings import settings

logger = logging.getLogger("etasync.validator")

# Reasonable timestamp bounds: within 1 day of current time
_TIMESTAMP_DRIFT_SECONDS = 86400


def validate_imu_packet(data: dict) -> Tuple[bool, str]:
    """
    Validate an incoming IMU sensor packet.
    Returns (is_valid, error_message).
    """
    required_fields = ["timestamp", "ax", "ay", "az", "gx", "gy", "gz"]

    for field in required_fields:
        if field not in data:
            msg = f"Missing required field: {field}"
            logger.warning(f"IMU validation failed: {msg}")
            return False, msg

    # Validate timestamp
    ts = data.get("timestamp")
    if not isinstance(ts, (int, float)) or ts <= 0:
        return False, "Invalid timestamp: must be a positive number"

    now = time.time()
    if abs(now - ts) > _TIMESTAMP_DRIFT_SECONDS:
        return False, f"Timestamp drift too large: {abs(now - ts):.0f}s"

    # Validate numeric fields
    for field in ["ax", "ay", "az", "gx", "gy", "gz"]:
        val = data.get(field)
        if not isinstance(val, (int, float)):
            return False, f"Field '{field}' must be numeric, got {type(val).__name__}"

    # Validate mode if present
    mode = data.get("mode", "sync")
    if mode not in ("sync", "async"):
        return False, f"Invalid mode: {mode}"

    return True, ""


def validate_camera_packet(data: dict) -> Tuple[bool, str]:
    """
    Validate an incoming camera frame packet.
    Returns (is_valid, error_message).
    """
    required_fields = ["timestamp", "frame_id", "data"]

    for field in required_fields:
        if field not in data:
            msg = f"Missing required field: {field}"
            logger.warning(f"Camera validation failed: {msg}")
            return False, msg

    # Validate timestamp
    ts = data.get("timestamp")
    if not isinstance(ts, (int, float)) or ts <= 0:
        return False, "Invalid timestamp: must be a positive number"

    # Validate frame_id
    frame_id = data.get("frame_id")
    if not isinstance(frame_id, int) or frame_id < 0:
        return False, "frame_id must be a non-negative integer"

    # Validate data (base64 string) size
    frame_data = data.get("data", "")
    if not isinstance(frame_data, str) or len(frame_data) == 0:
        return False, "Frame data must be a non-empty base64 string"

    # Approximate decoded size (base64 is ~4/3 of original)
    approx_size = len(frame_data) * 3 // 4
    if approx_size > settings.max_frame_size_bytes:
        return False, f"Frame too large: ~{approx_size} bytes (max: {settings.max_frame_size_bytes})"

    return True, ""
