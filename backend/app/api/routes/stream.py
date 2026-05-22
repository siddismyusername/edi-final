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
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.models.schemas import SensorPacket, CameraPacket, ErrorResponse
from app.models.session import SessionStateEnum
from app.validators.sensor_validator import validate_imu_packet, validate_camera_packet

logger = logging.getLogger("etasync.stream")

router = APIRouter(tags=["stream"])


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

    snapshot = SyncReplaySnapshot(
        session_id=session_id,
        server_timestamp=server_timestamp,
        window_start=float(window_data["start_time"]),
        window_end=float(window_data["end_time"]),
        prediction=str(result["prediction"]),
        confidence_score=float(result["confidence_score"]),
        all_probabilities=probabilities,
        imu_summary=_summarize_imu_packets(window_data["imu_packets"]),
        frame_preview=None,
        dtw_distance=float(result["dtw_distance"]),
        alignment_path=result["alignment_path"],
    )
    get_sync_replay_cache().add(snapshot)


# ── Helper: get or create default session ───────────────────

def _get_or_create_session():
    """Get the latest active streaming session, or auto-create one."""
    from app.main import get_session_manager, get_buffers
    from app.buffers.window_buffer import WindowBuffer

    sm = get_session_manager()
    sessions = sm.list_sessions()

    if sessions:
        # Prefer the most recently created session (last in list)
        session = sessions[-1]
    else:
        # Auto-create a default session for direct IMU/frame posts
        session = sm.create_session(device_id="mobile-auto", mode="sync")

    # Ensure buffer exists
    buffers = get_buffers()
    if session.session_id not in buffers:
        buffers[session.session_id] = WindowBuffer()

    # Update state
    if session.state == SessionStateEnum.INITIALIZED:
        sm.transition_state(session.session_id, SessionStateEnum.STREAMING)

    return session


async def _try_process_window(session_id: str):
    """Check if buffer is ready and trigger fusion pipeline."""
    from app.main import get_buffers, get_fusion_service, get_artifact_store, get_ws_manager, get_session_manager

    buffers = get_buffers()
    buffer = buffers.get(session_id)
    if not buffer or not buffer.is_window_ready():
        return

    window_data = buffer.extract_window()
    if not window_data:
        return

    sm = get_session_manager()
    sm.transition_state(session_id, SessionStateEnum.PROCESSING)

    fusion_service = get_fusion_service()
    artifact_store = get_artifact_store()
    ws_manager = get_ws_manager()

    try:
        # Run fusion pipeline
        result = fusion_service.process_window(
            imu_packets=window_data["imu_packets"],
            frame_packets=window_data["frame_packets"],
        )

        # Fusion returns None for empty/invalid windows
        if result is None:
            sm.transition_state(session_id, SessionStateEnum.STREAMING)
            return

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

    except Exception as e:
        logger.error(f"Fusion pipeline error: {e}", exc_info=True)
        sm.transition_state(session_id, SessionStateEnum.STREAMING)


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

    session = _get_or_create_session()
    session.stream_state.imu_packet_count += 1
    session.stream_state.last_imu_timestamp = packet.timestamp
    session.touch()

    # Buffer the packet
    buffers = get_buffers()
    buffers[session.session_id].add_imu_packet(packet_dict)

    # Persist
    store = get_session_store()
    store.append_sensor_data(session.session_id, packet_dict)

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
        },
    })

    # Check if window is ready for processing
    await _try_process_window(session.session_id)

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

    session = _get_or_create_session()
    session.stream_state.frame_count += 1
    session.stream_state.last_frame_timestamp = packet.timestamp
    session.touch()

    # Save raw frame bytes
    try:
        frame_bytes = base64.b64decode(packet.data)
        store = get_session_store()
        store.save_frame(session.session_id, packet.frame_id, frame_bytes)
    except Exception as e:
        logger.warning(f"Frame decode/save error: {e}")

    # Buffer frame metadata (without raw bytes for memory efficiency)
    frame_meta = {
        "timestamp": packet.timestamp,
        "frame_id": packet.frame_id,
        "resolution": packet.resolution,
        "mode": packet.mode,
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
        },
    })

    # Check if window is ready
    await _try_process_window(session.session_id)

    return {"status": "ok", "session_id": session.session_id}
