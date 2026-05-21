"""
DTW Alignment Service.
Stateless, deterministic computation of temporal alignment per LLD Section 11.

Pipeline: Input Window → Feature Distance → DTW Cost Matrix →
          Alignment Path → Bias Matrix → Normalization

DTW operates on RAW features (not encoder embeddings) per LLD spec:
  - IMU: 6D vector [ax, ay, az, gx, gy, gz]
  - Visual: per-frame summary statistics (mean RGB + spatial gradients)
"""

import logging
import time
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
from scipy.spatial.distance import cdist
from fastdtw import fastdtw

from config.settings import settings

logger = logging.getLogger("etasync.dtw")


class DTWService:
    """Stateless DTW alignment computation."""

    def __init__(self, radius: int = None, normalization: str = None):
        self._radius = radius or settings.dtw_radius
        self._normalization = normalization or settings.dtw_normalization_mode

    def compute_alignment(
        self,
        imu_features: np.ndarray,
        visual_features: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Compute DTW alignment between IMU and visual RAW feature sequences.

        Args:
            imu_features: shape (T_i, D_i) — raw IMU features (typically 6D)
            visual_features: shape (T_v, D_v) — raw visual summary features

        Returns:
            dict with cost_matrix, alignment_path, bias_matrix, dtw_distance,
            and computation_time_ms.
        """
        t_start = time.time()

        T_v, D_v = visual_features.shape
        T_i, D_i = imu_features.shape

        # When feature dimensions differ (IMU=6, Visual=12),
        # we need a shared representation for pairwise distance.
        # Project both to the same dimensionality via zero-padding.
        max_d = max(D_i, D_v)
        if D_i != D_v:
            imu_padded = np.zeros((T_i, max_d), dtype=np.float32)
            imu_padded[:, :D_i] = imu_features
            vis_padded = np.zeros((T_v, max_d), dtype=np.float32)
            vis_padded[:, :D_v] = visual_features
        else:
            imu_padded = imu_features
            vis_padded = visual_features

        # Step 1: Compute pairwise distance matrix
        cost_matrix = cdist(vis_padded, imu_padded, metric="euclidean")
        # cost_matrix shape: (T_v, T_i)

        # Step 2: FastDTW for alignment path
        distance, path = fastdtw(
            vis_padded, imu_padded,
            radius=self._radius,
            dist=2,  # Euclidean
        )

        # Step 3: Convert path to list of [i, j] pairs
        alignment_path = [[int(i), int(j)] for i, j in path]

        # Step 4: Generate bias matrix from alignment path
        bias_matrix = self._path_to_bias_matrix(
            alignment_path, T_v, T_i
        )

        # Step 5: Normalize bias matrix
        normalized_bias = self._normalize_bias(bias_matrix)

        elapsed_ms = (time.time() - t_start) * 1000

        logger.info(
            f"DTW alignment: T_v={T_v}, T_i={T_i}, "
            f"distance={distance:.4f}, time={elapsed_ms:.1f}ms"
        )

        return {
            "cost_matrix": cost_matrix,
            "alignment_path": alignment_path,
            "bias_matrix": normalized_bias,
            "dtw_distance": float(distance),
            "computation_time_ms": elapsed_ms,
        }

    def _path_to_bias_matrix(
        self,
        path: List[List[int]],
        T_v: int,
        T_i: int,
    ) -> np.ndarray:
        """
        Convert DTW alignment path to a soft bias matrix.
        High values at aligned positions, decaying with distance from path.
        """
        bias = np.zeros((T_v, T_i), dtype=np.float32)

        # Set path positions to 1.0
        for i, j in path:
            if i < T_v and j < T_i:
                bias[i, j] = 1.0

        # Apply Gaussian smoothing around the path for soft alignment
        from scipy.ndimage import gaussian_filter
        bias = gaussian_filter(bias, sigma=1.0)

        return bias

    def _normalize_bias(self, bias: np.ndarray) -> np.ndarray:
        """Normalize bias matrix using configured mode."""
        if self._normalization == "softmax":
            # Row-wise softmax normalization
            # Subtract max for numerical stability
            bias_shifted = bias - np.max(bias, axis=1, keepdims=True)
            exp_bias = np.exp(bias_shifted)
            normalized = exp_bias / (np.sum(exp_bias, axis=1, keepdims=True) + 1e-8)
            return normalized.astype(np.float32)
        elif self._normalization == "minmax":
            bmin = bias.min()
            bmax = bias.max()
            if bmax - bmin < 1e-8:
                return np.zeros_like(bias)
            return ((bias - bmin) / (bmax - bmin)).astype(np.float32)
        else:
            return bias

    @staticmethod
    def extract_imu_features(imu_packets: List[Dict[str, Any]]) -> np.ndarray:
        """
        Extract a feature matrix from raw IMU packets.
        Each packet → 6D vector [ax, ay, az, gx, gy, gz].
        Returns shape (T_i, 6).
        """
        features = []
        for p in imu_packets:
            features.append([
                p["ax"], p["ay"], p["az"],
                p["gx"], p["gy"], p["gz"],
            ])
        return np.array(features, dtype=np.float32)

    @staticmethod
    def extract_visual_features(
        frame_packets: List[Dict[str, Any]],
        session_dir: str = None,
    ) -> np.ndarray:
        """
        Extract visual summary features from camera frame data.

        If session_dir is provided, attempts to load saved JPEG frames and
        compute per-frame statistics (mean RGB, spatial gradients).
        Otherwise falls back to timestamp-derived features.

        Returns shape (T_v, 12) — 12D summary per frame:
          [mean_r, mean_g, mean_b, std_r, std_g, std_b,
           grad_x_mean, grad_y_mean, brightness, contrast,
           timestamp_norm, frame_id_norm]
        """
        import os

        features = []
        base_ts = frame_packets[0]["timestamp"] if frame_packets else 0.0
        max_id = max((p.get("frame_id", i) for i, p in enumerate(frame_packets)), default=1) or 1

        for idx, p in enumerate(frame_packets):
            feat = np.zeros(12, dtype=np.float32)

            # Try loading actual frame from disk
            frame_loaded = False
            if session_dir:
                frame_path = os.path.join(
                    session_dir, "camera_frames",
                    f"frame_{p.get('frame_id', idx):06d}.jpg"
                )
                if os.path.exists(frame_path):
                    try:
                        import cv2
                        img = cv2.imread(frame_path)
                        if img is not None:
                            img = cv2.resize(img, (64, 64))
                            img_f = img.astype(np.float32) / 255.0

                            # Mean/std RGB
                            feat[0:3] = img_f.mean(axis=(0, 1))  # mean R,G,B
                            feat[3:6] = img_f.std(axis=(0, 1))   # std R,G,B

                            # Spatial gradients (Sobel)
                            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
                            grad_x = np.abs(np.diff(gray, axis=1)).mean()
                            grad_y = np.abs(np.diff(gray, axis=0)).mean()
                            feat[6] = grad_x
                            feat[7] = grad_y

                            # Brightness and contrast
                            feat[8] = gray.mean()
                            feat[9] = gray.std()

                            frame_loaded = True
                    except Exception:
                        pass

            # Fallback: use metadata-derived features
            if not frame_loaded:
                ts_norm = (p["timestamp"] - base_ts) / max(1.0, frame_packets[-1]["timestamp"] - base_ts + 1e-6)
                feat[0:3] = [0.5, 0.5, 0.5]  # neutral gray
                feat[8] = 0.5  # mid brightness
                feat[10] = ts_norm

            feat[10] = (p["timestamp"] - base_ts) / max(1.0, frame_packets[-1]["timestamp"] - base_ts + 1e-6)
            feat[11] = p.get("frame_id", idx) / max(max_id, 1)

            features.append(feat)

        return np.array(features, dtype=np.float32)
