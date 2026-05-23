"""
Sensor streaming endpoints.
POST /imu — receive IMU packet (HTTP, compatible with mobile app)
POST /frame — receive camera frame (HTTP, compatible with mobile app)
WebSocket /ws/stream — optional WebSocket sensor ingestion

Per LLD Section 3.1, 7, 8.
"""

import asyncio
import base64
import json
import logging
import time
from typing import Dict, Any, List, Set

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.models.schemas import SensorPacket, CameraPacket, ErrorResponse
from app.models.session import SessionStateEnum
from app.validators.sensor_validator import validate_imu_packet, validate_camera_packet

logger = logging.getLogger("etasync.stream")

router = APIRouter(tags=["stream"])
_processing_sessions: Set[str] = set()


def _summarize_imu_packets(packets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a compact IMU summary for sync replay responses."""
    if not packets:
        return {"count": 0}

    axes = ("ax", "ay", "az", "gx", "gy", "gz")
    summary: Dict[str, Any] = {
        "count": len(packets),
        "start_timestamp": packets[0].get("timestamp"),
        "end_timestamp": packets[-1].get("timestamp"),
        "axes": {},
    }

    for axis in axes:
        values = [float(packet[axis]) for packet in packets if axis in packet]
        if values:
            summary["axes"][axis] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
            }

    return summary


def _cache_sync_replay_snapshot(
    session_id: str,
    window_data: Dict[str, Any],
    result: Dict[str, Any],
    server_timestamp: float,
) -> None:
    """Store the fused window in the rolling mobile sync replay cache."""
    from app.core.sync_replay_cache import SyncReplaySnapshot
    from app.main import get_sync_replay_cache

    probabilities = {
        str(label): float(score)
        for label, score in result["all_probabilities"].items()
    }

    frame_preview = None
    frame_packets = window_data.get("frame_packets") or []
    if frame_packets:
        last_frame = frame_packets[-1]
        if isinstance(last_frame, dict):
            frame_preview = last_frame.get("data") or last_frame.get("preview")

    snapshot = SyncReplaySnapshot(
        session_id=session_id,
        server_timestamp=server_timestamp,
        window_start=float(window_data["start_time"]),
        window_end=float(window_data["end_time"]),
        prediction=str(result["prediction"]),
        confidence_score=float(result["confidence_score"]),
        all_probabilities=probabilities,
        imu_summary=_summarize_imu_packets(window_data["imu_packets"]),
        frame_preview=frame_preview,
        dtw_distance=float(result["dtw_distance"]),
        alignment_path=result["alignment_path"],
    )
    get_sync_replay_cache().add(snapshot)


# ── Helper: get or create default session ───────────────────

def _get_or_create_session(mode: str = "sync", sensor: str = "imu"):
    """Get the latest active streaming session, or auto-create one.

    Session matching is mode-agnostic so that an ESP32 (IMU) and a
    mobile phone (camera) always land on the **same** session regardless
    of which mode string each device sends.  When a camera frame
    arrives on a session that was originally created as ``imu_only``,
    the buffer is dynamically upgraded to require frames.
    """
    from app.main import get_session_manager, get_buffers
    from app.buffers.window_buffer import WindowBuffer
    from config.settings import settings

    sm = get_session_manager()
    requested_mode = mode or "sync"

    # Pick the most recent active session regardless of mode so that
    # dual-device streams always converge on one session.
    sessions = sm.list_sessions()

    if sessions:
        session = sessions[-1]
    else:
        # Auto-create a default session for direct IMU/frame posts
        session = sm.create_session(device_id="mobile-auto", mode=requested_mode)

    # Ensure buffer exists
    buffers = get_buffers()
    if session.session_id not in buffers:
        min_frames = 0 if requested_mode == "imu_only" else settings.min_frames_per_window
        buffers[session.session_id] = WindowBuffer(min_frames=min_frames)

    # Dynamic buffer upgrade: if a camera frame arrives on a session
    # whose buffer was created with min_frames=0 (imu_only), upgrade
    # it so that future windows will wait for frames.
    buf = buffers[session.session_id]
    if sensor == "camera" and buf.min_frames == 0:
        buf.min_frames = settings.min_frames_per_window
        if session.metadata.mode == "imu_only":
            session.metadata.mode = "sync"
        logger.info(
            f"Buffer for session {session.session_id} upgraded: "
            f"min_frames=0 → {buf.min_frames} (camera frames detected)"
        )

    # Update state
    if session.state == SessionStateEnum.INITIALIZED:
        sm.transition_state(session.session_id, SessionStateEnum.STREAMING)

    return session


def _schedule_window_processing(session_id: str) -> None:
    """Schedule window processing without blocking ingestion responses."""
    try:
        asyncio.get_running_loop().create_task(_process_ready_windows(session_id))
    except RuntimeError:
        logger.warning("No running event loop; processing window inline is unavailable")


async def _process_ready_windows(session_id: str) -> None:
    """Process all currently ready windows for a session, one worker at a time."""
    if session_id in _processing_sessions:
        return

    _processing_sessions.add(session_id)
    try:
        while await _try_process_window(session_id):
            pass
    finally:
        _processing_sessions.discard(session_id)


async def _try_process_window(session_id: str) -> bool:
    """Check if buffer is ready and trigger fusion pipeline."""
    from app.main import get_buffers, get_fusion_service, get_artifact_store, get_ws_manager, get_session_manager, get_session_store

    buffers = get_buffers()
    buffer = buffers.get(session_id)
    if not buffer or not buffer.is_window_ready():
        return False

    window_data = buffer.extract_window()
    if not window_data:
        return False

    sm = get_session_manager()
    sm.transition_state(session_id, SessionStateEnum.PROCESSING)

    artifact_store = get_artifact_store()
    ws_manager = get_ws_manager()

    try:
        fusion_service = get_fusion_service()
        session_dir = get_session_store().session_dir(session_id, create=True)

        # Resolve session mode for downstream fusion decisions
        session = sm.get_session(session_id)
        session_mode = session.metadata.mode if session else "sync"

        # Run fusion pipeline
        result = fusion_service.process_window(
            imu_packets=window_data["imu_packets"],
            frame_packets=window_data["frame_packets"],
            session_dir=session_dir,
            mode=session_mode,
        )

        # Fusion returns None for empty/invalid windows
        if result is None:
            sm.transition_state(session_id, SessionStateEnum.STREAMING)
            return True

        window_id = window_data["window_id"]

        # Persist artifacts
        artifact_store.save_cost_matrix(session_id, window_id, result["cost_matrix"])
        artifact_store.save_bias_matrix(session_id, window_id, result["bias_matrix"])
        artifact_store.save_attention_weights(session_id, window_id, result["attention_weights"])
        artifact_store.save_fused_vectors(session_id, window_id, result["fused_representation"])
        artifact_store.save_predictions(session_id, window_id, {
            "prediction": result["prediction"],
            "confidence_score": result["confidence_score"],
            "all_probabilities": result["all_probabilities"],
            "dtw_distance": result["dtw_distance"],
        })

        server_timestamp = time.time()
        _cache_sync_replay_snapshot(
            session_id=session_id,
            window_data=window_data,
            result=result,
            server_timestamp=server_timestamp,
        )

        # Update session metrics
        session = sm.get_session(session_id)
        if session:
            session.windows_processed += 1
            session.latest_dtw_latency_ms = result["dtw_latency_ms"]
            session.latest_fusion_latency_ms = result["fusion_latency_ms"]
            session.latest_confidence = result["confidence_score"]
            session.latest_prediction = result["prediction"]

        # Broadcast to dashboard via WebSocket
        await ws_manager.broadcast({
            "event": "FUSION_COMPLETED",
            "session_id": session_id,
            "timestamp": server_timestamp,
            "data": {
                "window_id": window_id,
                "prediction": result["prediction"],
                "confidence_score": result["confidence_score"],
                "all_probabilities": result["all_probabilities"],
                "dtw_distance": result["dtw_distance"],
                "dtw_latency_ms": result["dtw_latency_ms"],
                "fusion_latency_ms": result["fusion_latency_ms"],
                "T_v": result["T_v"],
                "T_i": result["T_i"],
                "cost_matrix": result["cost_matrix"].tolist(),
                "bias_matrix": result["bias_matrix"].tolist(),
                "alignment_path": result["alignment_path"],
                "attention_weights": result["attention_weights"].mean(axis=0).tolist(),
            },
        })

        sm.transition_state(session_id, SessionStateEnum.STREAMING)

        logger.info(
            f"Window {window_id} processed: "
            f"{result['prediction']} ({result['confidence_score']:.2f})"
        )
        return True

    except Exception as e:
        logger.error(f"Fusion pipeline error: {e}", exc_info=True)
        sm.transition_state(session_id, SessionStateEnum.STREAMING)
        return True


# ── REST Endpoints ──────────────────────────────────────────

@router.post("/imu")
async def receive_imu(packet: SensorPacket):
    """Receive IMU sensor data from mobile device."""
    from app.main import get_buffers, get_session_store, get_ws_manager

    packet_dict = packet.model_dump()

    # Validate
    valid, err = validate_imu_packet(packet_dict)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    session = _get_or_create_session(packet.mode, sensor="imu")
    session.stream_state.imu_packet_count += 1
    session.stream_state.last_imu_timestamp = packet.timestamp
    session.touch()

    # Buffer the packet
    buffers = get_buffers()
    buffers[session.session_id].add_imu_packet(packet_dict)

    # Persist (offloaded to thread pool to avoid blocking the event loop)
    store = get_session_store()
    await asyncio.to_thread(store.append_sensor_data, session.session_id, packet_dict)

    # Broadcast packet received event
    ws_manager = get_ws_manager()
    await ws_manager.broadcast({
        "event": "PACKET_RECEIVED",
        "session_id": session.session_id,
        "timestamp": time.time(),
        "data": {
            "sensor": "imu",
            "imu_count": session.stream_state.imu_packet_count,
            "frame_count": session.stream_state.frame_count,
            "ax": packet.ax,
            "ay": packet.ay,
            "az": packet.az,
            "gx": packet.gx,
            "gy": packet.gy,
            "gz": packet.gz,
            "timestamp": packet.timestamp,
        },
    })

    # Process any ready windows asynchronously so ingestion stays responsive.
    _schedule_window_processing(session.session_id)

    return {"status": "ok", "session_id": session.session_id}


@router.post("/frame")
async def receive_frame(packet: CameraPacket):
    """Receive camera frame from mobile device."""
    from app.main import get_buffers, get_session_store, get_ws_manager

    packet_dict = packet.model_dump()

    # Validate
    valid, err = validate_camera_packet(packet_dict)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    session = _get_or_create_session(packet.mode, sensor="camera")
    session.stream_state.frame_count += 1
    session.stream_state.last_frame_timestamp = packet.timestamp
    session.touch()

    # Save raw frame bytes (offloaded to thread pool to avoid blocking the event loop)
    try:
        frame_bytes = base64.b64decode(packet.data, validate=True)
        store = get_session_store()
        await asyncio.to_thread(store.save_frame, session.session_id, packet.frame_id, frame_bytes)
    except Exception as e:
        logger.error(f"Frame decode/save error: {e}")
        raise HTTPException(status_code=400, detail="Invalid frame payload")

    # Buffer frame metadata along with a lightweight preview for sync replay.
    frame_meta = {
        "timestamp": packet.timestamp,
        "frame_id": packet.frame_id,
        "resolution": packet.resolution,
        "mode": packet.mode,
        "data": packet.data,
    }
    buffers = get_buffers()
    buffers[session.session_id].add_frame_packet(frame_meta)

    # Broadcast
    ws_manager = get_ws_manager()
    await ws_manager.broadcast({
        "event": "PACKET_RECEIVED",
        "session_id": session.session_id,
        "timestamp": time.time(),
        "data": {
            "sensor": "camera",
            "imu_count": session.stream_state.imu_packet_count,
            "frame_count": session.stream_state.frame_count,
            "frame_id": packet.frame_id,
            "data": packet.data,
            "timestamp": packet.timestamp,
        },
    })

    # Process any ready windows asynchronously so frame ingestion stays responsive.
    _schedule_window_processing(session.session_id)

    return {"status": "ok", "session_id": session.session_id}
