"""
ETA-Sync Model Training Pipeline.

Trains all 4 modules (VisualEncoder, IMUEncoder, DTWGuidedCrossAttention,
PredictionHead) end-to-end using synthetic sensor data with DTW-in-the-loop.

Synthetic data generation creates physics-based IMU patterns and correlated
visual features for 6 activity classes:
  walking, running, standing, jumping, sitting, unknown

Usage:
    python train.py                   # Train with defaults (100 epochs)
    python train.py --epochs 50       # Custom epoch count
    python train.py --lr 0.0005       # Custom learning rate
"""

import argparse
import logging
import os
import sys
import time
from typing import List, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch import optim
from torch.optim.adam import Adam
from torch.utils.data import Dataset, DataLoader

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import settings
from app.models.encoder import VisualEncoder, IMUEncoder
from app.models.attention import DTWGuidedCrossAttention, PredictionHead
from app.services.dtw import DTWService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("etasync.train")

# ── Constants ───────────────────────────────────────────────

ACTIVITY_LABELS = settings.activity_labels  # 6 classes
NUM_CLASSES = len(ACTIVITY_LABELS)
VISUAL_FEATURE_DIM = 12
IMU_FEATURE_DIM = 6
CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), "etasync_model.pt")


# ── Synthetic Data Generator ───────────────────────────────

class SyntheticSensorDataset(Dataset):
    """
    Generates synthetic multi-modal sensor data for 6 activity classes.

    Each sample produces:
      - IMU sequence:    (T_i, 6)  — ax, ay, az, gx, gy, gz
      - Visual features: (T_v, 12) — synthetic per-frame summary stats
      - Label: int (0-5)

    Physics-based IMU patterns:
      walking  → periodic accel (1.8Hz), moderate gyro
      running  → fast periodic accel (3Hz), high gyro
      standing → flat accel (~9.81 az), near-zero gyro
      jumping  → spike pattern, high vertical accel
      sitting  → flat with slight noise
      unknown  → random noise
    """

    def __init__(
        self,
        num_samples: int = 1000,
        t_imu: int = 50,
        t_visual: int = 10,
        noise_level: float = 0.1,
    ):
        self.num_samples = num_samples
        self.t_imu = t_imu
        self.t_visual = t_visual
        self.noise = noise_level
        self.data = self._generate_all()

    def _generate_all(self) -> List[Tuple[np.ndarray, np.ndarray, int]]:
        data = []
        for _ in range(self.num_samples):
            label = np.random.randint(0, NUM_CLASSES)
            imu = self._generate_imu(label)
            vis = self._generate_visual(label, imu)
            data.append((imu, vis, label))
        return data

    def _generate_imu(self, label: int) -> np.ndarray:
        """Generate physics-based IMU sequence for given activity."""
        t = np.linspace(0, 2.0, self.t_imu)
        noise = np.random.randn(self.t_imu, 6).astype(np.float32) * self.noise

        if label == 0:  # walking
            ax = 0.3 * np.sin(2 * np.pi * 1.8 * t)
            ay = 0.2 * np.sin(2 * np.pi * 1.8 * t + np.pi / 3)
            az = 9.81 + 0.5 * np.sin(2 * np.pi * 3.6 * t)
            gx = 0.1 * np.sin(2 * np.pi * 1.8 * t)
            gy = 0.15 * np.cos(2 * np.pi * 1.8 * t)
            gz = 0.05 * np.sin(2 * np.pi * 0.9 * t)
        elif label == 1:  # running
            ax = 0.8 * np.sin(2 * np.pi * 3.0 * t)
            ay = 0.6 * np.sin(2 * np.pi * 3.0 * t + np.pi / 4)
            az = 9.81 + 1.5 * np.sin(2 * np.pi * 6.0 * t)
            gx = 0.3 * np.sin(2 * np.pi * 3.0 * t)
            gy = 0.4 * np.cos(2 * np.pi * 3.0 * t)
            gz = 0.2 * np.sin(2 * np.pi * 1.5 * t)
        elif label == 2:  # standing
            ax = np.full(self.t_imu, 0.02)
            ay = np.full(self.t_imu, 0.01)
            az = np.full(self.t_imu, 9.81)
            gx = np.full(self.t_imu, 0.001)
            gy = np.full(self.t_imu, 0.001)
            gz = np.full(self.t_imu, 0.001)
        elif label == 3:  # jumping
            jump_center = self.t_imu // 2
            ax = np.zeros(self.t_imu)
            ay = np.zeros(self.t_imu)
            az = np.full(self.t_imu, 9.81)
            # Add jump spike
            spike = np.exp(-0.5 * ((np.arange(self.t_imu) - jump_center) / 3.0) ** 2)
            az = az + 8.0 * spike
            ax = ax + 0.5 * spike
            gx = 0.5 * spike
            gy = 0.3 * spike
            gz = np.zeros(self.t_imu)
        elif label == 4:  # sitting
            ax = np.full(self.t_imu, 0.01)
            ay = np.full(self.t_imu, -0.05)
            az = np.full(self.t_imu, 9.78)
            gx = np.full(self.t_imu, 0.0)
            gy = np.full(self.t_imu, 0.0)
            gz = np.full(self.t_imu, 0.0)
        else:  # unknown
            ax = np.random.randn(self.t_imu) * 2.0
            ay = np.random.randn(self.t_imu) * 2.0
            az = 9.81 + np.random.randn(self.t_imu) * 3.0
            gx = np.random.randn(self.t_imu) * 0.5
            gy = np.random.randn(self.t_imu) * 0.5
            gz = np.random.randn(self.t_imu) * 0.5

        imu = np.stack([ax, ay, az, gx, gy, gz], axis=1).astype(np.float32)
        return imu + noise

    def _generate_visual(self, label: int, imu: np.ndarray) -> np.ndarray:
        """Generate correlated visual features from the same activity class."""
        vis = np.zeros((self.t_visual, VISUAL_FEATURE_DIM), dtype=np.float32)
        noise = np.random.randn(self.t_visual, VISUAL_FEATURE_DIM).astype(np.float32) * self.noise * 0.5

        if label == 0:  # walking — moderate motion, periodic brightness
            t = np.linspace(0, 2.0, self.t_visual)
            vis[:, 0:3] = 0.4 + 0.1 * np.sin(2 * np.pi * 1.8 * t)[:, None]  # RGB
            vis[:, 3:6] = 0.15  # moderate std
            vis[:, 6] = 0.3 + 0.1 * np.sin(2 * np.pi * 1.8 * t)  # grad_x
            vis[:, 7] = 0.2  # grad_y
            vis[:, 8] = 0.5 + 0.1 * np.sin(2 * np.pi * 1.8 * t)  # brightness
            vis[:, 9] = 0.2  # contrast
        elif label == 1:  # running — high motion blur
            t = np.linspace(0, 2.0, self.t_visual)
            vis[:, 0:3] = 0.35 + 0.15 * np.sin(2 * np.pi * 3.0 * t)[:, None]
            vis[:, 3:6] = 0.25  # high std (motion blur)
            vis[:, 6] = 0.5 + 0.2 * np.sin(2 * np.pi * 3.0 * t)
            vis[:, 7] = 0.4
            vis[:, 8] = 0.45
            vis[:, 9] = 0.3
        elif label == 2:  # standing — stable, low gradients
            vis[:, 0:3] = 0.5
            vis[:, 3:6] = 0.05
            vis[:, 6:8] = 0.05
            vis[:, 8] = 0.55
            vis[:, 9] = 0.1
        elif label == 3:  # jumping — brightness spike
            center = self.t_visual // 2
            spike = np.exp(-0.5 * ((np.arange(self.t_visual) - center) / 2.0) ** 2)
            vis[:, 0:3] = 0.4 + 0.3 * spike[:, None]
            vis[:, 3:6] = 0.1 + 0.2 * spike[:, None]
            vis[:, 6] = 0.2 + 0.4 * spike
            vis[:, 7] = 0.2 + 0.3 * spike
            vis[:, 8] = 0.4 + 0.4 * spike
            vis[:, 9] = 0.15 + 0.25 * spike
        elif label == 4:  # sitting — very stable
            vis[:, 0:3] = 0.45
            vis[:, 3:6] = 0.03
            vis[:, 6:8] = 0.02
            vis[:, 8] = 0.48
            vis[:, 9] = 0.08
        else:  # unknown — random
            vis = np.random.rand(self.t_visual, VISUAL_FEATURE_DIM).astype(np.float32) * 0.8

        # Temporal context
        vis[:, 10] = np.linspace(0, 1, self.t_visual)  # timestamp_norm
        vis[:, 11] = np.linspace(0, 1, self.t_visual)  # frame_id_norm

        return vis + noise

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        imu, vis, label = self.data[idx]
        return (
            torch.tensor(imu, dtype=torch.float32),
            torch.tensor(vis, dtype=torch.float32),
            torch.tensor(label, dtype=torch.long),
        )


# ── Training Loop ──────────────────────────────────────────

def train(args):
    device = torch.device(settings.device)
    logger.info(f"Training on device: {device}")
    logger.info(f"Activity labels: {ACTIVITY_LABELS}")

    # Initialize models
    visual_encoder = VisualEncoder(
        feature_mode=True, feature_dim=VISUAL_FEATURE_DIM
    ).to(device)
    imu_encoder = IMUEncoder(input_dim=IMU_FEATURE_DIM).to(device)
    cross_attention = DTWGuidedCrossAttention().to(device)
    prediction_head = PredictionHead().to(device)

    # DTW service (not differentiable, used to generate bias)
    dtw_service = DTWService()

    # Dataset and loader
    dataset = SyntheticSensorDataset(
        num_samples=args.num_samples,
        t_imu=args.t_imu,
        t_visual=args.t_visual,
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=True)

    # Optimizer and loss
    all_params = (
        list(visual_encoder.parameters())
        + list(imu_encoder.parameters())
        + list(cross_attention.parameters())
        + list(prediction_head.parameters())
    )
    optimizer = Adam(all_params, lr=args.lr, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = nn.CrossEntropyLoss()

    # Training
    visual_encoder.train()
    imu_encoder.train()
    cross_attention.train()
    prediction_head.train()

    best_loss = float("inf")
    logger.info(f"Starting training: {args.epochs} epochs, {len(dataset)} samples, batch={args.batch_size}")

    for epoch in range(1, args.epochs + 1):
        epoch_loss = 0.0
        correct = 0
        total = 0
        t_epoch = time.time()

        for batch_idx, (imu_batch, vis_batch, labels) in enumerate(loader):
            imu_batch = imu_batch.to(device)   # (B, T_i, 6)
            vis_batch = vis_batch.to(device)   # (B, T_v, 12)
            labels = labels.to(device)         # (B,)

            B = imu_batch.shape[0]

            # Step 1: Generate DTW bias for each sample in batch
            # DTW is non-differentiable — computed on CPU numpy
            bias_list = []
            for b in range(B):
                imu_np = imu_batch[b].cpu().numpy()   # (T_i, 6)
                vis_np = vis_batch[b].cpu().numpy()    # (T_v, 12)
                dtw_result = dtw_service.compute_alignment(imu_np, vis_np)
                bias_list.append(dtw_result["bias_matrix"])  # (T_v, T_i)

            # Use first sample's bias for the batch (all same length)
            dtw_bias = torch.tensor(
                bias_list[0], dtype=torch.float32
            ).to(device)

            # Step 2: Encode
            imu_embeddings = imu_encoder(imu_batch)       # (B, T_i, D)
            vis_embeddings = visual_encoder(vis_batch)     # (B, T_v, D)

            # Step 3: Cross-attention fusion with DTW bias
            fused, _ = cross_attention(vis_embeddings, imu_embeddings, dtw_bias)
            # fused: (B, T_v, D)

            # Step 4: Predict
            logits = prediction_head(fused)  # (B, num_classes)
            loss = criterion(logits, labels)

            # Backward
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(all_params, max_norm=1.0)
            optimizer.step()

            epoch_loss += loss.item() * B
            preds = logits.argmax(dim=-1)
            correct += (preds == labels).sum().item()
            total += B

        scheduler.step()
        epoch_loss /= total
        accuracy = correct / total
        elapsed = time.time() - t_epoch

        if epoch % 10 == 0 or epoch == 1:
            logger.info(
                f"Epoch {epoch:3d}/{args.epochs} | "
                f"Loss: {epoch_loss:.4f} | "
                f"Acc: {accuracy:.1%} | "
                f"LR: {scheduler.get_last_lr()[0]:.6f} | "
                f"Time: {elapsed:.1f}s"
            )

        # Save best checkpoint
        if epoch_loss < best_loss:
            best_loss = epoch_loss
            checkpoint = {
                "epoch": epoch,
                "loss": best_loss,
                "accuracy": accuracy,
                "visual_encoder": visual_encoder.state_dict(),
                "imu_encoder": imu_encoder.state_dict(),
                "cross_attention": cross_attention.state_dict(),
                "prediction_head": prediction_head.state_dict(),
                "settings": {
                    "embedding_dim": settings.embedding_dim,
                    "num_heads": settings.num_attention_heads,
                    "num_classes": NUM_CLASSES,
                    "visual_feature_dim": VISUAL_FEATURE_DIM,
                },
            }
            torch.save(checkpoint, CHECKPOINT_PATH)

    # Final report
    logger.info("=" * 60)
    logger.info(f"Training complete!")
    logger.info(f"  Best loss:  {best_loss:.4f}")
    logger.info(f"  Checkpoint: {CHECKPOINT_PATH}")
    logger.info(f"  Size:       {os.path.getsize(CHECKPOINT_PATH) / 1024:.1f} KB")
    logger.info("=" * 60)

    # Quick validation
    visual_encoder.eval()
    imu_encoder.eval()
    cross_attention.eval()
    prediction_head.eval()

    val_dataset = SyntheticSensorDataset(num_samples=200, t_imu=args.t_imu, t_visual=args.t_visual)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    val_correct = 0
    val_total = 0

    with torch.no_grad():
        for imu_batch, vis_batch, labels in val_loader:
            imu_batch = imu_batch.to(device)
            vis_batch = vis_batch.to(device)
            labels = labels.to(device)

            imu_np = imu_batch[0].cpu().numpy()
            vis_np = vis_batch[0].cpu().numpy()
            dtw_result = dtw_service.compute_alignment(imu_np, vis_np)
            dtw_bias = torch.tensor(dtw_result["bias_matrix"], dtype=torch.float32).to(device)

            imu_emb = imu_encoder(imu_batch)
            vis_emb = visual_encoder(vis_batch)
            fused, _ = cross_attention(vis_emb, imu_emb, dtw_bias)
            logits = prediction_head(fused)
            preds = logits.argmax(dim=-1)
            val_correct += (preds == labels).sum().item()
            val_total += labels.shape[0]

    logger.info(f"Validation accuracy: {val_correct/val_total:.1%}")


# ── Entry Point ────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ETA-Sync fusion model")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--num-samples", type=int, default=1200, help="Number of synthetic samples")
    parser.add_argument("--t-imu", type=int, default=50, help="IMU sequence length per sample")
    parser.add_argument("--t-visual", type=int, default=10, help="Visual sequence length per sample")
    args = parser.parse_args()

    train(args)
