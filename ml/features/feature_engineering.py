"""
Feature engineering pipeline for agricultural trust scoring.

Transforms raw farmer, satellite, weather and market data
into the static + temporal feature tensors expected by the TFT.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler


# ─── Feature Definitions ─────────────────────────────────────────────────────

STATIC_FEATURES = [
    "farm_size_acres",
    "annual_income_log",
    "years_farming",
    "num_crops",
    "district_encoded",
    "state_encoded",
    "has_bank_account",
    "has_insurance",
    "kyc_verified",
    "crop_diversity_index",
    "total_loan_history",
    "avg_repayment_delay_days",
]

TEMPORAL_FEATURES = [
    "ndvi",
    "evi",
    "soil_moisture",
    "crop_health_score",
    "temperature_celsius",
    "rainfall_mm",
    "humidity_percent",
    "modal_price",
    "price_volatility_30d",
    "price_trend_30d",
    "repayment_on_time",
    "repayment_ratio",
    "weather_anomaly_score",
    "satellite_anomaly",
    "income_proxy",
]


class FarmerFeatureExtractor:
    """
    Transforms a farmer's data dictionary into model-ready numpy arrays.

    Parameters
    ----------
    seq_len : int
        Number of time steps (months) to use in temporal window.
    """

    def __init__(self, seq_len: int = 24):
        self.seq_len = seq_len
        self.static_scaler = StandardScaler()
        self.temporal_scaler = MinMaxScaler(feature_range=(-1, 1))
        self._fitted = False

    # ── Fitting ───────────────────────────────────────────────────────────────

    def fit(self, farmer_records: List[Dict]) -> "FarmerFeatureExtractor":
        """Fit scalers on a list of farmer records (training data)."""
        statics = np.array([self._extract_static(r) for r in farmer_records])
        temporals = np.vstack(
            [self._extract_temporal(r).reshape(-1, len(TEMPORAL_FEATURES)) for r in farmer_records]
        )
        self.static_scaler.fit(statics)
        self.temporal_scaler.fit(temporals)
        self._fitted = True
        return self

    # ── Transform ─────────────────────────────────────────────────────────────

    def transform(
        self, record: Dict
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns
        -------
        static_features  : (num_static,)
        temporal_features: (seq_len, num_temporal)
        """
        static = self._extract_static(record).reshape(1, -1)
        temporal = self._extract_temporal(record)

        if self._fitted:
            static = self.static_scaler.transform(static)
            temporal = self.temporal_scaler.transform(temporal)

        return static.squeeze(0), temporal

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_static(self, record: Dict) -> np.ndarray:
        """Extract static (time-invariant) farmer features."""
        return np.array(
            [
                float(record.get("farm_size_acres", 0) or 0),
                np.log1p(float(record.get("annual_income", 0) or 0)),
                float(record.get("years_farming", 0) or 0),
                float(len(record.get("secondary_crops", [])) + 1),
                float(self._encode_str(record.get("district", ""))),
                float(self._encode_str(record.get("state", ""))),
                float(1 if record.get("bank_account_number") else 0),
                float(1 if record.get("has_insurance", False) else 0),
                float(1 if record.get("kyc_status") == "verified" else 0),
                float(self._crop_diversity(record)),
                float(record.get("total_loan_count", 0) or 0),
                float(record.get("avg_repayment_delay_days", 0) or 0),
            ],
            dtype=np.float32,
        )

    def _extract_temporal(self, record: Dict) -> np.ndarray:
        """
        Build temporal feature matrix of shape (seq_len, num_temporal).

        Expects record["time_series"] as a list of monthly dicts.
        If shorter than seq_len, pad with zeros.  If longer, truncate.
        """
        ts = record.get("time_series", [])
        rows = []
        for t in ts[-self.seq_len :]:
            row = [
                float(t.get("ndvi", 0) or 0),
                float(t.get("evi", 0) or 0),
                float(t.get("soil_moisture", 0) or 0),
                float(t.get("crop_health_score", 50) or 50),
                float(t.get("temperature_celsius", 25) or 25),
                float(t.get("rainfall_mm", 0) or 0),
                float(t.get("humidity_percent", 50) or 50),
                float(t.get("modal_price", 0) or 0),
                float(t.get("price_volatility_30d", 0) or 0),
                float(t.get("price_trend_30d", 0) or 0),
                float(1 if t.get("repayment_on_time") else 0),
                float(t.get("repayment_ratio", 1.0) or 1.0),
                float(t.get("weather_anomaly_score", 0) or 0),
                float(1 if t.get("satellite_anomaly") else 0),
                float(t.get("income_proxy", 0) or 0),
            ]
            rows.append(row)

        # Pad to seq_len
        while len(rows) < self.seq_len:
            rows.insert(0, [0.0] * len(TEMPORAL_FEATURES))

        return np.array(rows[-self.seq_len :], dtype=np.float32)

    @staticmethod
    def _encode_str(value: str) -> int:
        """Simple deterministic hash encoding for categorical strings."""
        return hash(value or "") % 1000

    @staticmethod
    def _crop_diversity(record: Dict) -> float:
        """Herfindahl–Hirschman index approximation for crop diversity."""
        crops = record.get("secondary_crops", [])
        n = len(crops) + 1
        return 1.0 - (1.0 / n)
