"""
Fusion Pipeline Service.
Orchestrates the full pipeline: Raw Features → DTW → Embedding → Cross-Attention → Prediction.
Per LLD Section 12 and Cross-Attention document.

Pipeline order (matches LLD Section 11-12):
  1. Extract RAW features (IMU: 6D, Visual: 12D summary stats)
  2. DTW alignment on RAW features → B_DTW
  3. Encode raw features → embeddings via neural encoders
  4. Inject B_DTW into cross-attention on embeddings
  5. Prediction head
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional

import numpy as np
import torch
import torch.nn.functional as F

from config.settings import settings
from app.models.encoder import VisualEncoder, IMUEncoder
from app.models.attention import DTWGuidedCrossAttention, PredictionHead
from app.services.dtw import DTWService

logger = logging.getLogger("etasync.fusion")

# Visual feature dimension for DTW (12D summary stats)
VISUAL_FEATURE_DIM = 12
CHECKPOINT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "etasync_model.pt",
)


class FusionService:
    """
    End-to-end fusion pipeline:
    1. Raw feature extraction
    2. DTW temporal alignment on raw features
    3. Embedding via neural encoders
    4. DTW-guided cross-attention fusion
    5. Activity prediction
    """

    def __init__(self):
        self._device = torch.device(settings.device)

        # Initialize neural network modules
        # VisualEncoder in feature_mode=True for inference
        # (decodes frames into 12D features, then encodes to embeddings)
        self._visual_encoder = VisualEncoder(
            feature_mode=True,
            feature_dim=VISUAL_FEATURE_DIM,
        ).to(self._device)
        self._imu_encoder = IMUEncoder(input_dim=6).to(self._device)
        self._cross_attention = DTWGuidedCrossAttention().to(self._device)
        self._prediction_head = PredictionHead().to(self._device)

        # DTW service (stateless)
        self._dtw_service = DTWService()

        # Try loading trained weights
        self._load_weights()

        # Set to eval mode (inference only)
        self._visual_encoder.eval()
        self._imu_encoder.eval()
        self._cross_attention.eval()
        self._prediction_head.eval()

        logger.info(
            f"Fusion service initialized on device={self._device}, "
            f"embed_dim={settings.embedding_dim}, "
            f"heads={settings.num_attention_heads}, "
            f"alpha={settings.alpha_dtw}"
        )

    def _load_weights(self):
        """Load trained model checkpoint if available."""
        if os.path.exists(CHECKPOINT_PATH):
            try:
                checkpoint = torch.load(CHECKPOINT_PATH, map_location=self._device, weights_only=True)
                self._visual_encoder.load_state_dict(checkpoint["visual_encoder"])
                self._imu_encoder.load_state_dict(checkpoint["imu_encoder"])
                self._cross_attention.load_state_dict(checkpoint["cross_attention"])
                self._prediction_head.load_state_dict(checkpoint["prediction_head"])
                logger.info(
                    f"Loaded trained weights from {CHECKPOINT_PATH} "
                    f"(epoch {checkpoint.get('epoch', '?')}, "
                    f"loss {checkpoint.get('loss', '?'):.4f})"
                )
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}. Using random weights.")
        else:
            logger.warning(
                f"No checkpoint found at {CHECKPOINT_PATH}. "
                "Running with random weights (demo mode). "
                "Run `python train.py` to train the model."
            )

    @torch.no_grad()
    def process_window(
        self,
        imu_packets: List[Dict[str, Any]],
        frame_packets: List[Dict[str, Any]],
        session_dir: str = None,
    ) -> Dict[str, Any]:
        """
        Process a complete temporal window through the full fusion pipeline.

        Args:
            imu_packets: list of IMU sensor dicts with ax,ay,az,gx,gy,gz
            frame_packets: list of camera frame metadata dicts
            session_dir: optional path to session directory for frame loading

        Returns:
            dict with prediction, confidence, attention weights, cost matrix,
            bias matrix, alignment path, and timing info.
        """
        t_start = time.time()

        # Guard against empty windows
        if not imu_packets or not frame_packets:
            logger.warning("Skipping empty window (no IMU or frame data)")
            return None

        # ── Step 1: Extract RAW features (per LLD Section 11) ───
        imu_features_np = DTWService.extract_imu_features(imu_packets)  # (T_i, 6)
        visual_features_np = DTWService.extract_visual_features(
            frame_packets, session_dir=session_dir
        )  # (T_v, 12)

        T_i = imu_features_np.shape[0]
        T_v = visual_features_np.shape[0]

        # ── Step 2: DTW alignment on RAW features ───────────────
        dtw_result = self._dtw_service.compute_alignment(
            imu_features_np, visual_features_np
        )

        cost_matrix = dtw_result["cost_matrix"]
        alignment_path = dtw_result["alignment_path"]
        bias_matrix = dtw_result["bias_matrix"]
        dtw_distance = dtw_result["dtw_distance"]
        dtw_time_ms = dtw_result["computation_time_ms"]

        # ── Step 3: Generate embeddings via encoders ────────────
        imu_tensor = torch.tensor(
            imu_features_np, dtype=torch.float32
        ).unsqueeze(0).to(self._device)
        visual_tensor = torch.tensor(
            visual_features_np, dtype=torch.float32
        ).unsqueeze(0).to(self._device)

        imu_embeddings = self._imu_encoder(imu_tensor)           # (1, T_i, D)
        visual_embeddings = self._visual_encoder(visual_tensor)  # (1, T_v, D)

        # ── Step 4: DTW-guided cross-attention fusion ───────────
        # bias_matrix from DTW is already (T_v, T_i) — matches attention layout
        dtw_bias_tensor = torch.tensor(
            bias_matrix, dtype=torch.float32
        ).to(self._device)

        # Ensure correct shape: (T_v, T_i)
        if dtw_bias_tensor.shape != (T_v, T_i):
            dtw_bias_tensor = dtw_bias_tensor.T

        fused, attention_weights = self._cross_attention(
            visual_embeddings, imu_embeddings, dtw_bias_tensor
        )
        # fused: (1, T_v, D)
        # attention_weights: (1, num_heads, T_v, T_i)

        # ── Step 5: Prediction ──────────────────────────────────
        logits = self._prediction_head(fused)  # (1, num_classes)
        probs = F.softmax(logits, dim=-1).squeeze(0)  # (num_classes,)

        pred_idx = probs.argmax().item()
        confidence = probs[pred_idx].item()
        prediction = settings.activity_labels[pred_idx]

        t_total_ms = (time.time() - t_start) * 1000

        # Convert tensors to numpy for serialization
        attn_np = attention_weights.squeeze(0).cpu().numpy()  # (heads, T_v, T_i)
        fused_np = fused.squeeze(0).cpu().numpy()  # (T_v, D)

        logger.info(
            f"Fusion complete: prediction={prediction}, "
            f"confidence={confidence:.3f}, "
            f"total_time={t_total_ms:.1f}ms"
        )

        return {
            "prediction": prediction,
            "confidence_score": float(confidence),
            "all_probabilities": {
                label: float(probs[i])
                for i, label in enumerate(settings.activity_labels)
            },
            "attention_weights": attn_np,
            "fused_representation": fused_np,
            "cost_matrix": cost_matrix,
            "bias_matrix": bias_matrix,
            "alignment_path": alignment_path,
            "dtw_distance": dtw_distance,
            "dtw_latency_ms": dtw_time_ms,
            "fusion_latency_ms": t_total_ms,
            "T_v": T_v,
            "T_i": T_i,
        }
