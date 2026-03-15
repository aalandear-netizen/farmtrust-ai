"""Tests for the TFT model architecture."""
import pytest
import torch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.tft import TemporalFusionTransformer


@pytest.fixture
def model():
    return TemporalFusionTransformer(
        num_static_features=12,
        num_temporal_features=15,
        hidden_dim=64,   # smaller for tests
        num_heads=4,
        num_lstm_layers=2,
        dropout=0.0,     # disable dropout for determinism
        seq_len=24,
    )


def test_model_forward_shape(model):
    """Model output tensors should have expected shapes."""
    B, T = 4, 24
    static = torch.randn(B, 12)
    temporal = torch.randn(B, T, 15)

    outputs = model(static, temporal)

    assert outputs["trust_score"].shape == (B,), "trust_score shape mismatch"
    assert outputs["sub_scores"].shape == (B, 6), "sub_scores shape mismatch"
    assert outputs["confidence"].shape == (B,), "confidence shape mismatch"


def test_trust_score_range(model):
    """Trust scores should be in [0, 100]."""
    static = torch.randn(10, 12)
    temporal = torch.randn(10, 24, 15)
    outputs = model(static, temporal)
    scores = outputs["trust_score"]
    # Clamp is applied in the serving layer, but raw sigmoid * 100 should be in range
    assert scores.min() >= 0, "Score below 0"
    assert scores.max() <= 100, "Score above 100"


def test_score_to_grade_mapping():
    """score_to_grade should return correct letter grades."""
    mapping = [
        (95, "AAA"),
        (85, "AA"),
        (75, "A"),
        (65, "BBB"),
        (55, "BB"),
        (45, "B"),
        (35, "C"),
        (20, "D"),
    ]
    for score, expected in mapping:
        assert TemporalFusionTransformer.score_to_grade(score) == expected, (
            f"Expected grade {expected} for score {score}"
        )


def test_batch_size_one(model):
    """Model should handle batch size of 1 without errors."""
    outputs = model(torch.randn(1, 12), torch.randn(1, 24, 15))
    assert outputs["trust_score"].shape == (1,)


def test_model_is_differentiable(model):
    """Loss should be differentiable through the model."""
    static = torch.randn(2, 12, requires_grad=False)
    temporal = torch.randn(2, 24, 15, requires_grad=False)
    outputs = model(static, temporal)
    loss = outputs["trust_score"].mean()
    loss.backward()  # should not raise
