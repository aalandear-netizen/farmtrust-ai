"""Training pipeline for the FarmTrust AI Temporal Fusion Transformer model."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Dataset
# ─────────────────────────────────────────────────────────────────────────────


class FarmerDataset(Dataset):
    """PyTorch Dataset that wraps numpy arrays of static + temporal features."""

    def __init__(
        self,
        static_features: np.ndarray,
        temporal_features: np.ndarray,
        labels: np.ndarray,
    ) -> None:
        self.static = torch.tensor(static_features, dtype=torch.float32)
        self.temporal = torch.tensor(temporal_features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            "static": self.static[idx],
            "temporal": self.temporal[idx],
            "label": self.labels[idx],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Trainer
# ─────────────────────────────────────────────────────────────────────────────


class TFTTrainer:
    """Training harness for the Temporal Fusion Transformer trust-score model."""

    def __init__(
        self,
        model: nn.Module,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        device: Optional[str] = None,
    ) -> None:
        self.model = model
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.model.to(self.device)
        self.optimiser = torch.optim.Adam(
            model.parameters(), lr=learning_rate, weight_decay=weight_decay
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimiser, patience=5, factor=0.5
        )
        self.criterion = nn.MSELoss()

    # ── training loop ─────────────────────────────────────────────────────────

    def _step(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        static = batch["static"].to(self.device)
        temporal = batch["temporal"].to(self.device)
        labels = batch["label"].to(self.device)

        outputs = self.model(static, temporal)
        trust_scores = outputs["trust_score"].squeeze(-1)
        return self.criterion(trust_scores, labels)

    def train_epoch(self, loader: DataLoader) -> float:
        """Run one full pass over the training set and return mean loss."""
        self.model.train()
        total_loss = 0.0
        for batch in loader:
            self.optimiser.zero_grad()
            loss = self._step(batch)
            loss.backward()
            nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimiser.step()
            total_loss += loss.item()
        return total_loss / max(len(loader), 1)

    @torch.no_grad()
    def evaluate(self, loader: DataLoader) -> float:
        """Evaluate the model on *loader* and return mean MSE loss."""
        self.model.eval()
        total_loss = 0.0
        for batch in loader:
            total_loss += self._step(batch).item()
        return total_loss / max(len(loader), 1)

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        epochs: int = 50,
        save_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Train the model for *epochs* and return a list of per-epoch metrics.

        Args:
            train_loader: DataLoader for training batches.
            val_loader: Optional DataLoader for validation.
            epochs: Number of full passes over the training set.
            save_dir: If provided, saves the best checkpoint here.
        """
        history: List[Dict[str, Any]] = []
        best_val = float("inf")

        for epoch in range(1, epochs + 1):
            train_loss = self.train_epoch(train_loader)
            metrics: Dict[str, Any] = {"epoch": epoch, "train_loss": train_loss}

            if val_loader is not None:
                val_loss = self.evaluate(val_loader)
                metrics["val_loss"] = val_loss
                self.scheduler.step(val_loss)

                if val_loss < best_val:
                    best_val = val_loss
                    metrics["best"] = True
                    if save_dir:
                        self._save_checkpoint(save_dir, epoch, val_loss)
            else:
                self.scheduler.step(train_loss)

            history.append(metrics)
            logger.info("Epoch %d/%d | %s", epoch, epochs, metrics)

        return history

    # ── persistence ───────────────────────────────────────────────────────────

    def _save_checkpoint(self, save_dir: str, epoch: int, val_loss: float) -> None:
        path = Path(save_dir)
        path.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "epoch": epoch,
            "val_loss": val_loss,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimiser.state_dict(),
        }
        ckpt_path = path / "best_model.pt"
        torch.save(checkpoint, ckpt_path)
        logger.info("Saved checkpoint → %s (val_loss=%.4f)", ckpt_path, val_loss)

    def load_checkpoint(self, checkpoint_path: str) -> int:
        """Load a checkpoint; returns the epoch it was saved at."""
        ckpt = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.optimiser.load_state_dict(ckpt["optimizer_state_dict"])
        logger.info("Loaded checkpoint from epoch %d", ckpt["epoch"])
        return ckpt["epoch"]
