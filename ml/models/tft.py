"""
Temporal Fusion Transformer (TFT) model for agricultural trust scoring.

This module implements a multi-task TFT that simultaneously predicts:
  - Overall creditworthiness score (0-100)
  - Sub-scores: repayment, crop yield, weather risk, market volatility,
    satellite health, social capital

Reference: Lim et al. (2021) – "Temporal Fusion Transformers for
Interpretable Multi-horizon Time Series Forecasting"
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


# ─── Helper Modules ───────────────────────────────────────────────────────────

class GatedLinearUnit(nn.Module):
    """Gating mechanism used throughout the TFT architecture."""

    def __init__(self, input_dim: int, output_dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, output_dim)
        self.fc2 = nn.Linear(input_dim, output_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.fc1(x)) * torch.sigmoid(self.fc2(x))


class GatedResidualNetwork(nn.Module):
    """Gated Residual Network (GRN) – core building block of TFT."""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        dropout: float = 0.1,
        context_dim: Optional[int] = None,
    ):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.context_fc = nn.Linear(context_dim, hidden_dim, bias=False) if context_dim else None
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.glu = GatedLinearUnit(hidden_dim, output_dim, dropout)
        self.layer_norm = nn.LayerNorm(output_dim)
        self.skip = nn.Linear(input_dim, output_dim) if input_dim != output_dim else nn.Identity()

    def forward(self, x: torch.Tensor, context: Optional[torch.Tensor] = None) -> torch.Tensor:
        h = F.elu(self.fc1(x))
        if self.context_fc is not None and context is not None:
            h = h + self.context_fc(context)
        h = self.fc2(h)
        out = self.glu(h) + self.skip(x)
        return self.layer_norm(out)


class VariableSelectionNetwork(nn.Module):
    """
    Learns which input variables are most important via soft attention
    over input embeddings.
    """

    def __init__(self, num_vars: int, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.grn = GatedResidualNetwork(
            input_dim=num_vars * hidden_dim,
            hidden_dim=hidden_dim,
            output_dim=num_vars,
            dropout=dropout,
        )
        self.var_grns = nn.ModuleList(
            [GatedResidualNetwork(hidden_dim, hidden_dim, hidden_dim, dropout) for _ in range(num_vars)]
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (batch, num_vars, hidden_dim)
        Returns:
            combined: (batch, hidden_dim)
            weights:  (batch, num_vars)  – variable importance
        """
        batch = x.shape[0]
        flat = x.reshape(batch, -1)                              # (B, V*H)
        weights = torch.softmax(self.grn(flat), dim=-1)          # (B, V)

        processed = torch.stack(
            [self.var_grns[i](x[:, i, :]) for i in range(x.shape[1])], dim=1
        )                                                         # (B, V, H)

        combined = (processed * weights.unsqueeze(-1)).sum(dim=1)  # (B, H)
        return combined, weights


class InterpretableMultiHeadAttention(nn.Module):
    """
    Multi-head attention where all heads share the same V projection,
    enabling interpretable per-head attention weights.
    """

    def __init__(self, d_model: int, num_heads: int, dropout: float = 0.1):
        super().__init__()
        assert d_model % num_heads == 0
        self.d_head = d_model // num_heads
        self.num_heads = num_heads

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, self.d_head)  # shared V
        self.out_proj = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        B, T, D = q.shape
        H, Dh = self.num_heads, self.d_head

        Q = self.q_proj(q).reshape(B, T, H, Dh).transpose(1, 2)  # (B,H,T,Dh)
        K = self.k_proj(k).reshape(B, T, H, Dh).transpose(1, 2)
        V = self.v_proj(v).unsqueeze(1).expand(-1, H, -1, -1)     # shared V

        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(Dh)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float("-inf"))
        attn = self.dropout(torch.softmax(scores, dim=-1))

        out = torch.matmul(attn, V).transpose(1, 2).reshape(B, T, D)
        return self.out_proj(out), attn.mean(dim=1)  # average over heads


# ─── Main TFT Model ───────────────────────────────────────────────────────────

class TemporalFusionTransformer(nn.Module):
    """
    Temporal Fusion Transformer adapted for agricultural trust scoring.

    Inputs
    ------
    static_features   : (B, num_static)    – farm / farmer attributes
    temporal_features : (B, T, num_temporal) – time-series observations

    Outputs
    -------
    trust_score      : (B,)  – overall score in [0, 100]
    sub_scores       : (B, 6) – repayment, yield, weather, market, satellite, social
    variable_weights : (B, num_vars) – interpretability
    attention_weights: (B, T, T)
    """

    def __init__(
        self,
        num_static_features: int = 12,
        num_temporal_features: int = 15,
        hidden_dim: int = 128,
        num_heads: int = 4,
        num_lstm_layers: int = 2,
        dropout: float = 0.1,
        seq_len: int = 24,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.seq_len = seq_len
        self.num_temporal_features = num_temporal_features

        # Static feature processing
        self.static_embedding = nn.Linear(num_static_features, hidden_dim)
        self.static_context_h = GatedResidualNetwork(hidden_dim, hidden_dim, hidden_dim, dropout)
        self.static_context_c = GatedResidualNetwork(hidden_dim, hidden_dim, hidden_dim, dropout)
        self.static_context_enrichment = GatedResidualNetwork(hidden_dim, hidden_dim, hidden_dim, dropout)

        # Per-variable temporal projections: each scalar feature → hidden_dim vector
        self.var_projections = nn.ModuleList(
            [nn.Linear(1, hidden_dim) for _ in range(num_temporal_features)]
        )
        # Variable Selection Network over the num_temporal_features axis
        self.vsn = VariableSelectionNetwork(num_temporal_features, hidden_dim, dropout)

        # Sequential processing
        self.lstm_encoder = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_lstm_layers,
            batch_first=True,
            dropout=dropout if num_lstm_layers > 1 else 0,
        )
        self.post_lstm_gate = GatedLinearUnit(hidden_dim, hidden_dim, dropout)
        self.post_lstm_norm = nn.LayerNorm(hidden_dim)

        # Static enrichment
        self.static_enrichment = GatedResidualNetwork(
            hidden_dim, hidden_dim, hidden_dim, dropout, context_dim=hidden_dim
        )

        # Attention
        self.attention = InterpretableMultiHeadAttention(hidden_dim, num_heads, dropout)
        self.post_attn_gate = GatedLinearUnit(hidden_dim, hidden_dim, dropout)
        self.post_attn_norm = nn.LayerNorm(hidden_dim)

        self.position_ffn = GatedResidualNetwork(hidden_dim, hidden_dim, hidden_dim, dropout)
        self.pre_output_gate = GatedLinearUnit(hidden_dim, hidden_dim, dropout)
        self.pre_output_norm = nn.LayerNorm(hidden_dim)

        # Multi-task output heads
        self.trust_score_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )
        self.sub_score_head = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 6),
            nn.Sigmoid(),
        )
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        static_features: torch.Tensor,
        temporal_features: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        B, T, _ = temporal_features.shape

        # ── Static context ────────────────────────────────────────────────────
        s_emb = F.elu(self.static_embedding(static_features))   # (B, H)
        h0 = self.static_context_h(s_emb).unsqueeze(0)          # (1, B, H) – LSTM init h
        c0 = self.static_context_c(s_emb).unsqueeze(0)          # (1, B, H) – LSTM init c
        static_enrich = self.static_context_enrichment(s_emb)   # (B, H)

        # ── Per-variable temporal embeddings → Variable Selection ─────────────
        # temporal_features: (B, T, num_temporal)
        # Embed each variable separately to get (B, T, num_temporal, H)
        var_embs = torch.stack(
            [self.var_projections[i](temporal_features[:, :, i : i + 1]) for i in range(self.num_temporal_features)],
            dim=2,
        )  # (B, T, num_temporal, H)

        # Apply VSN across the variable axis per time step
        B, T, V, H = var_embs.shape
        var_embs_flat = var_embs.reshape(B * T, V, H)           # (B*T, V, H)
        vsn_combined, var_weights_flat = self.vsn(var_embs_flat) # (B*T, H), (B*T, V)
        t_emb = vsn_combined.reshape(B, T, H)                   # (B, T, H)
        var_weights = var_weights_flat.reshape(B, T, V).mean(dim=1)  # (B, V) – avg over time

        # ── LSTM encoder ─────────────────────────────────────────────────────
        lstm_out, _ = self.lstm_encoder(
            t_emb,
            (h0.expand(self.lstm_encoder.num_layers, -1, -1).contiguous(),
             c0.expand(self.lstm_encoder.num_layers, -1, -1).contiguous()),
        )                                                          # (B, T, H)
        lstm_out = self.post_lstm_gate(lstm_out) + t_emb
        lstm_out = self.post_lstm_norm(lstm_out)

        # ── Static enrichment ─────────────────────────────────────────────────
        enriched = self.static_enrichment(
            lstm_out, context=static_enrich.unsqueeze(1).expand(-1, T, -1)
        )                                                          # (B, T, H)

        # ── Temporal self-attention ───────────────────────────────────────────
        attn_out, attn_weights = self.attention(enriched, enriched, enriched)
        attn_out = self.post_attn_gate(attn_out) + enriched
        attn_out = self.post_attn_norm(attn_out)

        # ── Position-wise feed-forward ────────────────────────────────────────
        ffn_out = self.position_ffn(attn_out)
        out = self.pre_output_gate(ffn_out) + enriched
        out = self.pre_output_norm(out)                            # (B, T, H)

        # Aggregate over time (last step)
        final = out[:, -1, :]                                      # (B, H)

        trust_score = self.trust_score_head(final).squeeze(-1) * 100     # (B,)
        sub_scores = self.sub_score_head(final) * 100                    # (B, 6)
        confidence = self.confidence_head(final).squeeze(-1)             # (B,)

        return {
            "trust_score": trust_score,
            "sub_scores": sub_scores,
            "confidence": confidence,
            "variable_importance": var_weights,
            "attention_weights": attn_weights,
        }

    @staticmethod
    def score_to_grade(score: float) -> str:
        """Convert numerical trust score to credit-like letter grade."""
        if score >= 90:
            return "AAA"
        elif score >= 80:
            return "AA"
        elif score >= 70:
            return "A"
        elif score >= 60:
            return "BBB"
        elif score >= 50:
            return "BB"
        elif score >= 40:
            return "B"
        elif score >= 30:
            return "C"
        return "D"
