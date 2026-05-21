"""
Persistence layer for session artifacts.
Handles file-based session storage per LLD Section 9 directory structure.
"""

import json
import os
import logging
import time
from typing import Optional, Dict, Any

import numpy as np

from config.settings import settings

logger = logging.getLogger("etasync.storage")


class SessionStore:
    """Manages file-based session persistence."""

    def __init__(self, base_dir: Optional[str] = None):
        self._base_dir = base_dir or settings.sessions_dir
        os.makedirs(self._base_dir, exist_ok=True)

    def _session_dir(self, session_id: str) -> str:
        path = os.path.join(self._base_dir, session_id)
        os.makedirs(path, exist_ok=True)
        return path

    # ── Metadata ────────────────────────────────────────────

    def save_metadata(self, session_id: str, metadata: Dict[str, Any]):
        """Save session metadata JSON."""
        path = os.path.join(self._session_dir(session_id), "metadata.json")
        with open(path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.debug(f"Saved metadata for session {session_id}")

    def load_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session metadata."""
        path = os.path.join(self._session_dir(session_id), "metadata.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    # ── Sensor Data (append-only JSONL) ─────────────────────

    def append_sensor_data(self, session_id: str, packet: Dict[str, Any]):
        """Append a sensor packet to the session's JSONL file."""
        path = os.path.join(self._session_dir(session_id), "sensor_data.jsonl")
        with open(path, "a") as f:
            f.write(json.dumps(packet) + "\n")

    # ── Frame Storage ───────────────────────────────────────

    def save_frame(self, session_id: str, frame_id: int, frame_bytes: bytes):
        """Save a camera frame as JPEG."""
        frames_dir = os.path.join(self._session_dir(session_id), "camera_frames")
        os.makedirs(frames_dir, exist_ok=True)
        path = os.path.join(frames_dir, f"frame_{frame_id:06d}.jpg")
        with open(path, "wb") as f:
            f.write(frame_bytes)

    # ── Diagnostics ─────────────────────────────────────────

    def save_diagnostics(self, session_id: str, diagnostics: Dict[str, Any]):
        """Save diagnostics snapshot."""
        path = os.path.join(self._session_dir(session_id), "diagnostics.json")
        with open(path, "w") as f:
            json.dump(diagnostics, f, indent=2)

    # ── Session listing ─────────────────────────────────────

    def list_sessions(self):
        """List all persisted session IDs."""
        if not os.path.exists(self._base_dir):
            return []
        return [
            d for d in os.listdir(self._base_dir)
            if os.path.isdir(os.path.join(self._base_dir, d))
        ]


class ArtifactStore:
    """Manages numpy and JSON artifacts for alignment/fusion outputs."""

    def __init__(self, base_dir: Optional[str] = None):
        self._base_dir = base_dir or settings.sessions_dir

    def _artifact_dir(self, session_id: str, category: str) -> str:
        path = os.path.join(self._base_dir, session_id, category)
        os.makedirs(path, exist_ok=True)
        return path

    # ── Alignment Artifacts ─────────────────────────────────

    def save_cost_matrix(self, session_id: str, window_id: str, matrix: np.ndarray) -> str:
        """Save DTW cost matrix as .npy."""
        dirpath = self._artifact_dir(session_id, "alignment")
        filename = f"cost_matrix_{window_id}.npy"
        filepath = os.path.join(dirpath, filename)
        np.save(filepath, matrix)
        logger.debug(f"Saved cost matrix: {filepath}")
        return filepath

    def save_bias_matrix(self, session_id: str, window_id: str, matrix: np.ndarray) -> str:
        """Save DTW bias matrix as .npy."""
        dirpath = self._artifact_dir(session_id, "alignment")
        filename = f"dtw_bias_{window_id}.npy"
        filepath = os.path.join(dirpath, filename)
        np.save(filepath, matrix)
        return filepath

    def save_alignment_result(self, session_id: str, window_id: str, result: Dict[str, Any]) -> str:
        """Save alignment metadata as JSON."""
        dirpath = self._artifact_dir(session_id, "alignment")
        filename = f"dtw_alignment_{window_id}.json"
        filepath = os.path.join(dirpath, filename)
        with open(filepath, "w") as f:
            json.dump(result, f, indent=2)
        return filepath

    # ── Fusion Artifacts ────────────────────────────────────

    def save_attention_weights(self, session_id: str, window_id: str, weights: np.ndarray) -> str:
        """Save attention weight matrix as .npy."""
        dirpath = self._artifact_dir(session_id, "fusion")
        filename = f"attention_weights_{window_id}.npy"
        filepath = os.path.join(dirpath, filename)
        np.save(filepath, weights)
        return filepath

    def save_fused_vectors(self, session_id: str, window_id: str, vectors: np.ndarray) -> str:
        """Save fused representation vectors as .npy."""
        dirpath = self._artifact_dir(session_id, "fusion")
        filename = f"fused_vectors_{window_id}.npy"
        filepath = os.path.join(dirpath, filename)
        np.save(filepath, vectors)
        return filepath

    def save_predictions(self, session_id: str, window_id: str, predictions: Dict[str, Any]) -> str:
        """Save prediction results as JSON."""
        dirpath = self._artifact_dir(session_id, "fusion")
        filename = f"predictions_{window_id}.json"
        filepath = os.path.join(dirpath, filename)
        with open(filepath, "w") as f:
            json.dump(predictions, f, indent=2)
        return filepath

    # ── Load Artifacts ──────────────────────────────────────

    def load_numpy(self, filepath: str) -> Optional[np.ndarray]:
        """Load a .npy artifact."""
        if os.path.exists(filepath):
            return np.load(filepath)
        return None
