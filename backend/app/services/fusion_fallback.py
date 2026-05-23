"""
Fallback fusion service used when PyTorch is unavailable.

This keeps API/session/window flows operational in development environments
without ML dependencies. It is deterministic and preserves the FusionService
response shape, but it is not a replacement for trained model inference.
"""

import logging
import time
from typing import Any, Dict, List

import numpy as np

from config.settings import settings
from app.services.dtw import DTWService

logger = logging.getLogger("etasync.fusion")


class FallbackFusionService:
    """NumPy-only fallback that mirrors FusionService.process_window output."""

    def __init__(self):
        self._dtw_service = DTWService()
        logger.warning("Fallback fusion service initialized; predictions are heuristic.")

    def process_window(
        self,
        imu_packets: List[Dict[str, Any]],
        frame_packets: List[Dict[str, Any]],
        session_dir: str = None,
        mode: str = "sync",
    ) -> Dict[str, Any]:
        t_start = time.time()
        if not imu_packets:
            logger.warning("Skipping empty window (no IMU data)")
            return None

        imu_features_np = DTWService.extract_imu_features(imu_packets)

        imu_only = mode == "imu_only" or not frame_packets
        if not imu_only and frame_packets:
            visual_features_np = DTWService.extract_visual_features(
                frame_packets,
                session_dir=session_dir,
            )
        else:
            mock_T_v = max(1, imu_features_np.shape[0] // 4)
            visual_features_np = np.zeros((mock_T_v, 12), dtype=np.float32)

        dtw_result = self._dtw_service.compute_alignment(
            imu_features_np,
            visual_features_np,
        )

        T_i = imu_features_np.shape[0]
        T_v = visual_features_np.shape[0]
        embed_dim = settings.embedding_dim

        imu_energy = float(np.mean(np.linalg.norm(imu_features_np, axis=1)))
        labels = settings.activity_labels
        scores = np.full(len(labels), 0.05, dtype=np.float32)
        if "standing" in labels:
            scores[labels.index("standing")] = max(0.1, 1.0 / (1.0 + imu_energy))
        if "walking" in labels:
            scores[labels.index("walking")] = min(0.7, imu_energy / 15.0)
        if "unknown" in labels:
            scores[labels.index("unknown")] = 0.2
        scores = scores / max(float(scores.sum()), 1e-8)

        pred_idx = int(np.argmax(scores))
        prediction = labels[pred_idx]
        confidence = float(scores[pred_idx])

        attention_weights = np.tile(
            dtw_result["bias_matrix"][None, :, :],
            (settings.num_attention_heads, 1, 1),
        ).astype(np.float32)
        fused = np.zeros((T_v, embed_dim), dtype=np.float32)

        return {
            "prediction": prediction,
            "confidence_score": confidence,
            "all_probabilities": {
                label: float(scores[i])
                for i, label in enumerate(labels)
            },
            "attention_weights": attention_weights,
            "fused_representation": fused,
            "cost_matrix": dtw_result["cost_matrix"],
            "bias_matrix": dtw_result["bias_matrix"],
            "alignment_path": dtw_result["alignment_path"],
            "dtw_distance": dtw_result["dtw_distance"],
            "dtw_latency_ms": dtw_result["computation_time_ms"],
            "fusion_latency_ms": (time.time() - t_start) * 1000,
            "T_v": T_v,
            "T_i": T_i,
        }
