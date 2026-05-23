"""
Neural network encoders for visual and IMU modalities.
Lightweight architectures suitable for edge deployment per LLD Section 3.6.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional

from config.settings import settings


class VisualEncoder(nn.Module):
    """
    Lightweight CNN encoder for camera frame embeddings.
    Input: (B, T_v, C, H, W) raw frame tensors (default C=3, H=64, W=64).
    Output: (B, T_v, D) visual embeddings.

    Falls back to (B, T_v, raw_dim) feature vectors when raw frames
    are not available (e.g., training with synthetic features).
    """

    def __init__(
        self,
        input_channels: int = 3,
        frame_size: int = 64,
        embed_dim: Optional[int] = None,
        feature_mode: bool = False,
        feature_dim: int = 12,
    ):
        super().__init__()
        self.embed_dim = embed_dim or settings.embedding_dim
        self.feature_mode = feature_mode

        if feature_mode:
            # MLP encoder for pre-extracted feature vectors (B, T_v, feature_dim)
            self.encoder = nn.Sequential(
                nn.Linear(feature_dim, 64),
                nn.ReLU(),
                nn.LayerNorm(64),
                nn.Linear(64, self.embed_dim),
                nn.ReLU(),
                nn.LayerNorm(self.embed_dim),
            )
        else:
            # CNN encoder for raw frame pixels (B*T_v, C, H, W)
            self.cnn = nn.Sequential(
                nn.Conv2d(input_channels, 16, kernel_size=3, stride=2, padding=1),
                nn.ReLU(),
                nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
                nn.ReLU(),
                nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d(1),  # → (B*T_v, 64, 1, 1)
            )
            self.projection = nn.Sequential(
                nn.Linear(64, self.embed_dim),
                nn.ReLU(),
                nn.LayerNorm(self.embed_dim),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            feature_mode: x shape (B, T_v, feature_dim)
            CNN mode:     x shape (B, T_v, C, H, W)
        Returns:
            (B, T_v, D) embeddings
        """
        if self.feature_mode:
            if x.dim() == 2:
                x = x.unsqueeze(0)
            return self.encoder(x)

        # CNN mode: reshape to (B*T_v, C, H, W)
        B, T_v = x.shape[:2]
        x = x.reshape(B * T_v, *x.shape[2:])  # (B*T_v, C, H, W)
        x = self.cnn(x)                        # (B*T_v, 64, 1, 1)
        x = x.squeeze(-1).squeeze(-1)          # (B*T_v, 64)
        x = self.projection(x)                 # (B*T_v, D)
        x = x.reshape(B, T_v, self.embed_dim)  # (B, T_v, D)
        return x


class IMUEncoder(nn.Module):
    """
    MLP-based encoder for IMU sensor embeddings.
    Input: (B, T_i, 6) raw IMU readings [ax, ay, az, gx, gy, gz].
    Output: (B, T_i, D) IMU embeddings.

    Uses LayerNorm instead of BatchNorm1d for batch-size-1 compatibility
    during inference.
    """

    def __init__(self, input_dim: int = 6, embed_dim: Optional[int] = None):
        super().__init__()
        self.embed_dim = embed_dim or settings.embedding_dim

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.LayerNorm(32),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.LayerNorm(64),
            nn.Linear(64, self.embed_dim),
            nn.ReLU(),
            nn.LayerNorm(self.embed_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, T_i, 6) raw IMU sequence
        Returns:
            (B, T_i, D) embeddings
        """
        if x.dim() == 2:
            x = x.unsqueeze(0)
        return self.encoder(x)
