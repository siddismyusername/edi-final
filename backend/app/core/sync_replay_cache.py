"""
Rolling synchronized replay cache for mobile sync playback.

The cache stores only fused window snapshots produced by the existing fusion
pipeline. It is intentionally in-memory and bounded by replay duration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SyncReplaySnapshot:
    """Serializable fused window snapshot for /sync/latest."""

    session_id: str
    server_timestamp: float
    window_start: float
    window_end: float
    prediction: str
    confidence_score: float
    all_probabilities: Dict[str, float]
    imu_summary: Dict[str, Any]
    frame_preview: Optional[str]
    dtw_distance: float
    alignment_path: List[List[int]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "server_timestamp": self.server_timestamp,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "prediction": self.prediction,
            "confidence_score": self.confidence_score,
            "all_probabilities": self.all_probabilities,
            "imu_summary": self.imu_summary,
            "frame_preview": self.frame_preview,
            "dtw_distance": self.dtw_distance,
            "alignment_path": self.alignment_path,
        }


class SyncReplayCache:
    """Per-session replay cache bounded to the latest replay window."""

    def __init__(self, max_seconds: float = 120.0):
        self.max_seconds = float(max_seconds)
        self._items: Dict[str, List[SyncReplaySnapshot]] = {}

    def add(self, snapshot: SyncReplaySnapshot) -> None:
        items = self._items.setdefault(snapshot.session_id, [])
        items.append(snapshot)
        items.sort(key=lambda item: item.window_end)
        self._evict_old(snapshot.session_id)

    def clear_session(self, session_id: str) -> None:
        self._items.pop(session_id, None)

    def clear(self) -> None:
        self._items.clear()

    def status(self, session_id: str) -> Dict[str, Any]:
        items = self._items.get(session_id, [])
        if not items:
            return {
                "session_id": session_id,
                "ready": False,
                "available_seconds": 0.0,
                "max_replay_seconds": self.max_seconds,
            }

        available = max(0.0, items[-1].window_end - items[0].window_start)
        return {
            "session_id": session_id,
            "ready": True,
            "available_seconds": min(self.max_seconds, available),
            "max_replay_seconds": self.max_seconds,
        }

    def latest(self, session_id: str, offset_seconds: float = 0.0) -> Optional[Dict[str, Any]]:
        items = self._items.get(session_id, [])
        if not items:
            return None

        offset = max(0.0, min(float(offset_seconds), self.max_seconds))
        target_end = items[-1].window_end - offset

        selected = items[0]
        for item in items:
            if item.window_end <= target_end:
                selected = item
            else:
                break

        return selected.to_dict()

    def _evict_old(self, session_id: str) -> None:
        items = self._items.get(session_id, [])
        if not items:
            return

        cutoff = items[-1].window_end - self.max_seconds
        self._items[session_id] = [
            item for item in items if item.window_end >= cutoff
        ]
