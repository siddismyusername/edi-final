"""
ETA-Sync Backend — FastAPI Application Entry Point.
Mounts all route modules, initializes services, and manages lifecycle.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from app.core.session_manager import SessionManager
from app.core.sync_replay_cache import SyncReplayCache
from app.storage.session_store import SessionStore, ArtifactStore
from app.buffers.window_buffer import WindowBuffer
from app.api.routes.diagnostics import WebSocketManager

# ── Logging Setup ───────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("etasync")

# ── Global Service Instances ────────────────────────────────

_session_manager: Optional[SessionManager] = None
_session_store: Optional[SessionStore] = None
_artifact_store: Optional[ArtifactStore] = None
_fusion_service = None  # Lazy-initialized to avoid import-time torch loading
_ws_manager: Optional[WebSocketManager] = None
_sync_replay_cache: Optional[SyncReplayCache] = None
_buffers: Dict[str, WindowBuffer] = {}


def get_session_manager() -> SessionManager:
    assert _session_manager is not None
    return _session_manager


def get_session_store() -> SessionStore:
    assert _session_store is not None
    return _session_store


def get_artifact_store() -> ArtifactStore:
    assert _artifact_store is not None
    return _artifact_store


def get_fusion_service():
    global _fusion_service
    if _fusion_service is None:
        from app.services.fusion import FusionService
        _fusion_service = FusionService()
    return _fusion_service


def get_ws_manager() -> WebSocketManager:
    assert _ws_manager is not None
    return _ws_manager


def get_sync_replay_cache() -> SyncReplayCache:
    assert _sync_replay_cache is not None
    return _sync_replay_cache


def get_buffers() -> Dict[str, WindowBuffer]:
    return _buffers


# ── Application Lifecycle ───────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    global _session_manager, _session_store, _artifact_store, _ws_manager, _sync_replay_cache

    logger.info("=" * 60)
    logger.info("  ETA-Sync Backend Starting")
    logger.info(f"  Device: {settings.device}")
    logger.info(f"  Embedding dim: {settings.embedding_dim}")
    logger.info(f"  Window size: {settings.window_size_seconds}s")
    logger.info(f"  DTW radius: {settings.dtw_radius}")
    logger.info(f"  Alpha (DTW bias): {settings.alpha_dtw}")
    logger.info("=" * 60)

    # Initialize services
    _session_manager = SessionManager(
        timeout_seconds=settings.session_timeout_seconds,
        max_sessions=settings.max_active_sessions,
    )
    _session_store = SessionStore(base_dir=settings.sessions_dir)
    _artifact_store = ArtifactStore(base_dir=settings.sessions_dir)
    _ws_manager = WebSocketManager()
    _sync_replay_cache = SyncReplayCache(max_seconds=settings.sync_replay_seconds)

    # Lazy-load fusion service (loads PyTorch model)
    logger.info("Initializing fusion service...")
    get_fusion_service()
    logger.info("Fusion service ready.")

    logger.info("ETA-Sync Backend ready. Waiting for connections...")

    yield

    # Shutdown
    logger.info("ETA-Sync Backend shutting down...")
    _buffers.clear()
    if _sync_replay_cache:
        _sync_replay_cache.clear()


# ── FastAPI App ─────────────────────────────────────────────

app = FastAPI(
    title="ETA-Sync Backend",
    description=(
        "Real-time DTW-guided asynchronous multi-modal sensor fusion "
        "backend for the ETA-Sync research prototype."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Routes ────────────────────────────────────────────

from app.api.routes.health import router as health_router
from app.api.routes.session import router as session_router
from app.api.routes.stream import router as stream_router
from app.api.routes.diagnostics import router as diagnostics_router
from app.api.routes.sync import router as sync_router

app.include_router(health_router)
app.include_router(session_router)
app.include_router(stream_router)
app.include_router(diagnostics_router)
app.include_router(sync_router)


# ── Root Endpoint ───────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "ETA-Sync Backend",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }
