"""Tests for DTW alignment service — LLD Section 19."""

import numpy as np
import pytest
from app.services.dtw import DTWService


@pytest.fixture
def dtw_service():
    return DTWService(radius=5, normalization="softmax")


class TestDTWAlignment:
    def test_cost_matrix_shape(self, dtw_service):
        imu = np.random.randn(50, 6).astype(np.float32)
        vis = np.random.randn(10, 12).astype(np.float32)
        result = dtw_service.compute_alignment(imu, vis)
        assert result["cost_matrix"].shape == (10, 50)

    def test_bias_matrix_shape(self, dtw_service):
        imu = np.random.randn(30, 6).astype(np.float32)
        vis = np.random.randn(8, 12).astype(np.float32)
        result = dtw_service.compute_alignment(imu, vis)
        assert result["bias_matrix"].shape == (8, 30)

    def test_alignment_path_valid(self, dtw_service):
        imu = np.random.randn(20, 6).astype(np.float32)
        vis = np.random.randn(5, 12).astype(np.float32)
        result = dtw_service.compute_alignment(imu, vis)
        path = result["alignment_path"]
        assert len(path) > 0
        assert path[0][0] == 0 and path[0][1] == 0  # starts at (0,0)

    def test_dtw_distance_non_negative(self, dtw_service):
        imu = np.random.randn(25, 6).astype(np.float32)
        vis = np.random.randn(10, 12).astype(np.float32)
        result = dtw_service.compute_alignment(imu, vis)
        assert result["dtw_distance"] >= 0.0

    def test_computation_time_recorded(self, dtw_service):
        imu = np.random.randn(15, 6).astype(np.float32)
        vis = np.random.randn(5, 12).astype(np.float32)
        result = dtw_service.compute_alignment(imu, vis)
        assert result["computation_time_ms"] > 0.0


class TestBiasNormalization:
    def test_softmax_rows_sum_to_one(self):
        service = DTWService(normalization="softmax")
        imu = np.random.randn(10, 6).astype(np.float32)
        vis = np.random.randn(5, 12).astype(np.float32)
        result = service.compute_alignment(imu, vis)
        row_sums = result["bias_matrix"].sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-5)

    def test_minmax_range(self):
        service = DTWService(normalization="minmax")
        imu = np.random.randn(10, 6).astype(np.float32)
        vis = np.random.randn(5, 12).astype(np.float32)
        result = service.compute_alignment(imu, vis)
        bias = result["bias_matrix"]
        assert bias.min() >= -1e-7
        assert bias.max() <= 1.0 + 1e-7


class TestFeatureExtraction:
    def test_imu_features_shape(self):
        packets = [
            {"ax": 0.1, "ay": 0.2, "az": 9.81, "gx": 0.01, "gy": 0.02, "gz": 0.03}
            for _ in range(20)
        ]
        features = DTWService.extract_imu_features(packets)
        assert features.shape == (20, 6)
        assert features.dtype == np.float32

    def test_visual_features_shape(self):
        packets = [
            {"timestamp": 1.0 + i * 0.1, "frame_id": i}
            for i in range(10)
        ]
        features = DTWService.extract_visual_features(packets)
        assert features.shape == (10, 12)
        assert features.dtype == np.float32
