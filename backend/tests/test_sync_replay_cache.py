"""Tests for mobile sync replay cache."""

from app.core.sync_replay_cache import SyncReplayCache, SyncReplaySnapshot


def make_snapshot(session_id: str, start: float, end: float) -> SyncReplaySnapshot:
    return SyncReplaySnapshot(
        session_id=session_id,
        server_timestamp=end,
        window_start=start,
        window_end=end,
        prediction="walking",
        confidence_score=0.9,
        all_probabilities={"walking": 0.9, "unknown": 0.1},
        imu_summary={"count": 2},
        frame_preview=None,
        dtw_distance=0.1,
        alignment_path=[[0, 0]],
    )


class TestSyncReplayCache:
    def test_empty_status_not_ready(self):
        cache = SyncReplayCache(max_seconds=120)
        status = cache.status("s1")
        assert status["ready"] is False
        assert status["available_seconds"] == 0.0

    def test_latest_zero_offset_returns_newest(self):
        cache = SyncReplayCache(max_seconds=120)
        cache.add(make_snapshot("s1", 0, 2))
        cache.add(make_snapshot("s1", 10, 12))
        latest = cache.latest("s1", offset_seconds=0)
        assert latest["window_end"] == 12

    def test_offset_returns_older_window(self):
        cache = SyncReplayCache(max_seconds=120)
        cache.add(make_snapshot("s1", 0, 2))
        cache.add(make_snapshot("s1", 10, 12))
        cache.add(make_snapshot("s1", 20, 22))
        latest = cache.latest("s1", offset_seconds=10)
        assert latest["window_end"] == 12

    def test_offset_clamps_to_replay_range(self):
        cache = SyncReplayCache(max_seconds=120)
        cache.add(make_snapshot("s1", 0, 2))
        cache.add(make_snapshot("s1", 150, 152))
        latest = cache.latest("s1", offset_seconds=999)
        assert latest["window_end"] == 150 + 2
        assert cache.status("s1")["available_seconds"] <= 120

    def test_sessions_are_isolated(self):
        cache = SyncReplayCache(max_seconds=120)
        cache.add(make_snapshot("s1", 0, 2))
        cache.add(make_snapshot("s2", 10, 12))
        assert cache.latest("s1")["window_end"] == 2
        assert cache.latest("s2")["window_end"] == 12
