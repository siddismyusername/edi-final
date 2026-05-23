"""
DTW-Guided Cross-Attention Module.
Core contribution of ETA-Sync per the cross-attention document.

Attention(Q, K, V) = Softmax(QK^T / √d_k + α·B_DTW) × V

Where B_DTW is the normalized DTW temporal alignment bias.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional

from config.settings import settings


class DTWGuidedCrossAttention(nn.Module):
    """
    Multi-head DTW-guided cross-attention.
    Visual queries attend to IMU keys/values with DTW temporal prior injection.
    """

    def __init__(
        self,
        embed_dim: Optional[int] = None,
        num_heads: Optional[int] = None,
        alpha: Optional[float] = None,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.embed_dim = embed_dim or settings.embedding_dim
        self.num_heads = num_heads or settings.num_attention_heads
        self.alpha = alpha if alpha is not None else settings.alpha_dtw
        self.head_dim = self.embed_dim // self.num_heads

        assert self.embed_dim % self.num_heads == 0, (
            f"embed_dim ({self.embed_dim}) must be divisible by "
            f"num_heads ({self.num_heads})"
        )

        # Q/K/V projections
        self.W_Q = nn.Linear(self.embed_dim, self.embed_dim)
        self.W_K = nn.Linear(self.embed_dim, self.embed_dim)
        self.W_V = nn.Linear(self.embed_dim, self.embed_dim)

        # Output projection
        self.W_O = nn.Linear(self.embed_dim, self.embed_dim)

        self.dropout = nn.Dropout(dropout)
        self.scale = math.sqrt(self.head_dim)

    def forward(
        self,
        visual_embeddings: torch.Tensor,
        imu_embeddings: torch.Tensor,
        dtw_bias: torch.Tensor,
    ) -> tuple:
        """
        DTW-guided cross-attention.

        Args:
            visual_embeddings: (B, T_v, D) — query source
            imu_embeddings: (B, T_i, D) — key/value source
            dtw_bias: (T_v, T_i) or (B, T_v, T_i) — DTW alignment bias

        Returns:
            fused: (B, T_v, D) — fused representation
            attention_weights: (B, num_heads, T_v, T_i) — attention maps
        """
        B, T_v, D = visual_embeddings.shape
        _, T_i, _ = imu_embeddings.shape

        # Project Q (from visual), K and V (from IMU)
        Q = self.W_Q(visual_embeddings)  # (B, T_v, D)
        K = self.W_K(imu_embeddings)     # (B, T_i, D)
        V = self.W_V(imu_embeddings)     # (B, T_i, D)

        # Reshape for multi-head: (B, num_heads, T, head_dim)
        Q = Q.view(B, T_v, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.view(B, T_i, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(B, T_i, self.num_heads, self.head_dim).transpose(1, 2)

        # Compute semantic similarity: QK^T / √d_k
        # Shape: (B, num_heads, T_v, T_i)
        scores = torch.matmul(Q, K.transpose(-2, -1)) / self.scale

        # Prepare DTW bias for broadcasting
        if dtw_bias.dim() == 2:
            # (T_v, T_i) → (1, 1, T_v, T_i)
            dtw_bias_expanded = dtw_bias.unsqueeze(0).unsqueeze(0)
        elif dtw_bias.dim() == 3:
            # (B, T_v, T_i) → (B, 1, T_v, T_i)
            dtw_bias_expanded = dtw_bias.unsqueeze(1)
        else:
            dtw_bias_expanded = dtw_bias

        # Inject DTW temporal prior:
        # Attention(Q,K,V) = Softmax(QK^T/√d_k + α·B_DTW) × V
        scores = scores + self.alpha * dtw_bias_expanded

        # Softmax normalization → attention weights
        attention_weights = F.softmax(scores, dim=-1)
        attention_weights = self.dropout(attention_weights)

        # Apply attention to values
        # (B, num_heads, T_v, head_dim)
        attended = torch.matmul(attention_weights, V)

        # Reshape back: (B, T_v, D)
        attended = attended.transpose(1, 2).contiguous().view(B, T_v, D)

        # Output projection
        fused = self.W_O(attended)

        return fused, attention_weights


class PredictionHead(nn.Module):
    """
    Classification head for activity prediction from fused representations.
    Performs global average pooling → MLP → softmax.
    """

    def __init__(
        self,
        embed_dim: Optional[int] = None,
        num_classes: Optional[int] = None,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.embed_dim = embed_dim or settings.embedding_dim
        self.num_classes = num_classes or settings.num_activity_classes

        self.classifier = nn.Sequential(
            nn.Linear(self.embed_dim, self.embed_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(self.embed_dim // 2, self.num_classes),
        )

    def forward(self, fused: torch.Tensor) -> torch.Tensor:
        """
        Args:
            fused: (B, T_v, D) fused representation
        Returns:
            logits: (B, num_classes) prediction logits
        """
        # Global average pooling over temporal dimension
        pooled = fused.mean(dim=1)  # (B, D)
        logits = self.classifier(pooled)  # (B, num_classes)
        return logits
