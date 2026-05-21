"""Evaluate the ETA-Sync checkpoint and generate confusion-matrix/performance reports.

Outputs are written under backend/reports/:
- confusion_matrix.json
- classification_report.json
- classification_report.txt
- evaluation_summary.json

Usage:
    python evaluate.py
    python evaluate.py --num-samples 500 --batch-size 16
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.dirname(__file__))

from config.settings import settings
from app.models.encoder import VisualEncoder, IMUEncoder
from app.models.attention import DTWGuidedCrossAttention, PredictionHead
from app.services.dtw import DTWService
from train import SyntheticSensorDataset, VISUAL_FEATURE_DIM, IMU_FEATURE_DIM


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("etasync.evaluate")

CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), "etasync_model.pt")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")


@dataclass
class Metrics:
    precision: float
    recall: float
    f1: float
    support: int


def _ensure_reports_dir() -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    return REPORT_DIR


def _load_model(device: torch.device):
    visual_encoder = VisualEncoder(feature_mode=True, feature_dim=VISUAL_FEATURE_DIM).to(device)
    imu_encoder = IMUEncoder(input_dim=IMU_FEATURE_DIM).to(device)
    cross_attention = DTWGuidedCrossAttention().to(device)
    prediction_head = PredictionHead().to(device)

    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError(
            f"Checkpoint not found: {CHECKPOINT_PATH}. Run `python train.py` first."
        )

    checkpoint = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True)
    visual_encoder.load_state_dict(checkpoint["visual_encoder"])
    imu_encoder.load_state_dict(checkpoint["imu_encoder"])
    cross_attention.load_state_dict(checkpoint["cross_attention"])
    prediction_head.load_state_dict(checkpoint["prediction_head"])

    visual_encoder.eval()
    imu_encoder.eval()
    cross_attention.eval()
    prediction_head.eval()

    return visual_encoder, imu_encoder, cross_attention, prediction_head, checkpoint


def _confusion_matrix(y_true: List[int], y_pred: List[int], num_classes: int) -> np.ndarray:
    matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
    for truth, pred in zip(y_true, y_pred):
        matrix[truth, pred] += 1
    return matrix


def _metrics_from_confusion(matrix: np.ndarray) -> Dict[str, Metrics]:
    num_classes = matrix.shape[0]
    report: Dict[str, Metrics] = {}
    for idx in range(num_classes):
        tp = int(matrix[idx, idx])
        fp = int(matrix[:, idx].sum() - tp)
        fn = int(matrix[idx, :].sum() - tp)
        support = int(matrix[idx, :].sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        report[str(idx)] = Metrics(precision=precision, recall=recall, f1=f1, support=support)
    return report


@torch.no_grad()
def _predict_batch(
    visual_encoder,
    imu_encoder,
    cross_attention,
    prediction_head,
    dtw_service: DTWService,
    imu_batch: torch.Tensor,
    vis_batch: torch.Tensor,
    device: torch.device,
) -> List[int]:
    batch_size = imu_batch.shape[0]
    predictions: List[int] = []

    for index in range(batch_size):
        imu_np = imu_batch[index].cpu().numpy()
        vis_np = vis_batch[index].cpu().numpy()
        dtw_result = dtw_service.compute_alignment(imu_np, vis_np)
        dtw_bias = torch.tensor(dtw_result["bias_matrix"], dtype=torch.float32, device=device)

        imu_emb = imu_encoder(imu_batch[index:index + 1])
        vis_emb = visual_encoder(vis_batch[index:index + 1])
        fused, _ = cross_attention(vis_emb, imu_emb, dtw_bias)
        logits = prediction_head(fused)
        predictions.append(int(logits.argmax(dim=-1).item()))

    return predictions


def evaluate(args: argparse.Namespace) -> None:
    device = torch.device(settings.device)
    reports_dir = _ensure_reports_dir()
    labels = list(settings.activity_labels)

    logger.info("Loading checkpoint and model modules...")
    visual_encoder, imu_encoder, cross_attention, prediction_head, checkpoint = _load_model(device)
    dtw_service = DTWService()

    dataset = SyntheticSensorDataset(
        num_samples=args.num_samples,
        t_imu=args.t_imu,
        t_visual=args.t_visual,
        noise_level=args.noise_level,
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, drop_last=False)

    y_true: List[int] = []
    y_pred: List[int] = []

    logger.info("Running evaluation on synthetic validation set...")
    for imu_batch, vis_batch, batch_labels in loader:
        imu_batch = imu_batch.to(device)
        vis_batch = vis_batch.to(device)
        batch_predictions = _predict_batch(
            visual_encoder,
            imu_encoder,
            cross_attention,
            prediction_head,
            dtw_service,
            imu_batch,
            vis_batch,
            device,
        )
        y_true.extend(batch_labels.tolist())
        y_pred.extend(batch_predictions)

    matrix = _confusion_matrix(y_true, y_pred, num_classes=len(labels))
    report = _metrics_from_confusion(matrix)

    total = int(matrix.sum())
    accuracy = float(np.trace(matrix) / total) if total > 0 else 0.0
    macro_precision = float(np.mean([m.precision for m in report.values()]))
    macro_recall = float(np.mean([m.recall for m in report.values()]))
    macro_f1 = float(np.mean([m.f1 for m in report.values()]))

    weighted_precision = float(
        sum(m.precision * m.support for m in report.values()) / total
    ) if total > 0 else 0.0
    weighted_recall = float(
        sum(m.recall * m.support for m in report.values()) / total
    ) if total > 0 else 0.0
    weighted_f1 = float(
        sum(m.f1 * m.support for m in report.values()) / total
    ) if total > 0 else 0.0

    report_json = {
        "labels": labels,
        "per_class": {
            labels[int(label_idx)]: {
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1,
                "support": metrics.support,
            }
            for label_idx, metrics in report.items()
        },
        "macro_avg": {
            "precision": macro_precision,
            "recall": macro_recall,
            "f1_score": macro_f1,
        },
        "weighted_avg": {
            "precision": weighted_precision,
            "recall": weighted_recall,
            "f1_score": weighted_f1,
        },
        "accuracy": accuracy,
        "support": total,
    }

    summary = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "device": settings.device,
        "checkpoint": os.path.basename(CHECKPOINT_PATH),
        "checkpoint_epoch": checkpoint.get("epoch"),
        "checkpoint_loss": checkpoint.get("loss"),
        "num_samples": args.num_samples,
        "batch_size": args.batch_size,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "reports_dir": reports_dir,
    }

    matrix_payload = {
        "labels": labels,
        "matrix": matrix.tolist(),
    }

    def _to_text(report_obj: Dict[str, object]) -> str:
        lines = []
        lines.append("ETA-Sync Classification Report")
        lines.append("=" * 34)
        lines.append("")
        lines.append(f"Accuracy: {accuracy:.4f}")
        lines.append(f"Macro avg  P/R/F1: {macro_precision:.4f} / {macro_recall:.4f} / {macro_f1:.4f}")
        lines.append(
            f"Weighted   P/R/F1: {weighted_precision:.4f} / {weighted_recall:.4f} / {weighted_f1:.4f}"
        )
        lines.append("")
        lines.append("Per-class metrics:")
        for label in labels:
            item = report_obj["per_class"][label]
            lines.append(
                f"- {label:>8}: precision={item['precision']:.4f}, recall={item['recall']:.4f}, f1={item['f1_score']:.4f}, support={item['support']}"
            )
        return "\n".join(lines) + "\n"

    confusion_path = os.path.join(reports_dir, "confusion_matrix.json")
    report_json_path = os.path.join(reports_dir, "classification_report.json")
    report_text_path = os.path.join(reports_dir, "classification_report.txt")
    summary_path = os.path.join(reports_dir, "evaluation_summary.json")

    with open(confusion_path, "w", encoding="utf-8") as f:
        json.dump(matrix_payload, f, indent=2)

    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)

    with open(report_text_path, "w", encoding="utf-8") as f:
        f.write(_to_text(report_json))

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n=== ETA-Sync Evaluation Complete ===")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    print(f"Reports saved to: {reports_dir}")
    print(f"- {confusion_path}")
    print(f"- {report_json_path}")
    print(f"- {report_text_path}")
    print(f"- {summary_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ETA-Sync confusion matrix and performance reports")
    parser.add_argument("--num-samples", type=int, default=400, help="Number of synthetic validation samples")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size for evaluation")
    parser.add_argument("--t-imu", type=int, default=50, help="IMU sequence length")
    parser.add_argument("--t-visual", type=int, default=10, help="Visual sequence length")
    parser.add_argument("--noise-level", type=float, default=0.1, help="Synthetic data noise level")
    return parser.parse_args()


if __name__ == "__main__":
    evaluate(parse_args())