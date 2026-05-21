"""
WebSocket diagnostic endpoints for dashboard real-time feeds.
Per LLD Section 8.

/ws/diagnostics — session events and metrics
"""

import asyncio
import json
import logging
import time
from typing import Set, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("etasync.ws")

router = APIRouter(tags=["diagnostics"])


class WebSocketManager:
    """Manages connected dashboard WebSocket clients."""

    def __init__(self):
        self._clients: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket client."""
        await websocket.accept()
        self._clients.add(websocket)
        logger.info(f"Dashboard client connected. Total: {len(self._clients)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected client."""
        self._clients.discard(websocket)
        logger.info(f"Dashboard client disconnected. Total: {len(self._clients)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected dashboard clients."""
        if not self._clients:
            return

        data = json.dumps(message, default=str)
        disconnected = set()

        for client in self._clients:
            try:
                await client.send_text(data)
            except Exception:
                disconnected.add(client)

        # Clean up disconnected clients
        for client in disconnected:
            self._clients.discard(client)

    @property
    def client_count(self) -> int:
        return len(self._clients)


# ── WebSocket Endpoint ──────────────────────────────────────

@router.websocket("/ws/diagnostics")
async def diagnostics_ws(websocket: WebSocket):
    """
    Dashboard WebSocket endpoint.
    Streams session events, alignment outputs, fusion results, and metrics.
    """
    from app.main import get_ws_manager, get_session_manager

    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket)

    try:
        # Send initial state
        sm = get_session_manager()
        sessions = sm.list_sessions()

        await websocket.send_json({
            "event": "CONNECTED",
            "timestamp": time.time(),
            "data": {
                "active_sessions": len(sessions),
                "sessions": [s.to_dict() for s in sessions],
            },
        })

        # Keep connection alive and listen for any client messages
        while True:
            try:
                # Wait for client messages (heartbeat/ping)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,
                )

                # Handle ping
                if data == "ping":
                    await websocket.send_json({
                        "event": "PONG",
                        "timestamp": time.time(),
                    })

                # Handle status request
                elif data == "status":
                    sessions = sm.list_sessions()
                    await websocket.send_json({
                        "event": "STATUS",
                        "timestamp": time.time(),
                        "data": {
                            "active_sessions": len(sessions),
                            "sessions": [s.to_dict() for s in sessions],
                        },
                    })

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "event": "HEARTBEAT",
                    "timestamp": time.time(),
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
