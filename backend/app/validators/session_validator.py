"""
Session validation rules per LLD Section 15.
"""

import logging
from typing import Tuple

logger = logging.getLogger("etasync.validator")


def validate_session_create(data: dict) -> Tuple[bool, str]:
    """
    Validate session creation request.
    Returns (is_valid, error_message).
    """
    device_id = data.get("device_id", "")
    if not device_id or not isinstance(device_id, str):
        return False, "device_id is required and must be a non-empty string"

    mode = data.get("mode", "sync")
    if mode not in ("sync", "async"):
        return False, f"Invalid mode: {mode}. Must be 'sync' or 'async'"

    return True, ""
