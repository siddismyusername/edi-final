"""Tests for fusion pipeline tensor shapes — LLD Section 19."""

import numpy as np
import torch
import pytest
from app.models.encoder import VisualEncoder, IMUEncoder
from app.models.attention import DTWGuidedCrossAttention, PredictionHead
from config.settings import settings


class TestVisualEncoder:
    def test_feature_mode_shape(self):
        enc = VisualEncoder(feature_mode=True, feature_dim=12)
        x = torch.randn(2, 10, 12)
        out = enc(x)
        assert out.shape == (2, 10, settings.embedding_dim)

    def test_feature_mode_2d_input(self):
        enc = VisualEncoder(feature_mode=True, feature_dim=12)
        x = torch.randn(10, 12)  # no batch dim
        out = enc(x)
        assert out.shape == (1, 10, settings.embedding_dim)


class TestIMUEncoder:
    def test_output_shape(self):
        enc = IMUEncoder(input_dim=6)
        x = torch.randn(2, 50, 6)
        out = enc(x)
        assert out.shape == (2, 50, settings.embedding_dim)

    def test_2d_input_unsqueeze(self):
        enc = IMUEncoder(input_dim=6)
        x = torch.randn(50, 6)
        out = enc(x)
        assert out.shape == (1, 50, settings.embedding_dim)


class TestCrossAttention:
    def test_output_shapes(self):
        ca = DTWGuidedCrossAttention()
        vis = torch.randn(1, 10, settings.embedding_dim)
        imu = torch.randn(1, 50, settings.embedding_dim)
        bias = torch.randn(10, 50)
        fused, attn = ca(vis, imu, bias)
        assert fused.shape == (1, 10, settings.embedding_dim)
        assert attn.shape[0] == 1
        assert attn.shape[2] == 10  # T_v
        assert attn.shape[3] == 50  # T_i


class TestPredictionHead:
    def test_output_shape(self):
        head = PredictionHead()
        x = torch.randn(1, 10, settings.embedding_dim)
        logits = head(x)
        assert logits.shape == (1, len(settings.activity_labels))


class TestFusionPipeline:
    def test_end_to_end_shapes(self):
        """Full pipeline shape test without DTW."""
        ve = VisualEncoder(feature_mode=True, feature_dim=12)
        ie = IMUEncoder(input_dim=6)
        ca = DTWGuidedCrossAttention()
        ph = PredictionHead()

        imu_raw = torch.randn(1, 50, 6)
        vis_raw = torch.randn(1, 10, 12)
        dtw_bias = torch.randn(10, 50)

        imu_emb = ie(imu_raw)
        vis_emb = ve(vis_raw)
        fused, attn = ca(vis_emb, imu_emb, dtw_bias)
        logits = ph(fused)

        assert logits.shape == (1, len(settings.activity_labels))
        probs = torch.softmax(logits, dim=-1)
        assert abs(probs.sum().item() - 1.0) < 1e-5
