"""Tests for the feature engineering pipeline."""
import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from features.feature_engineering import FarmerFeatureExtractor, STATIC_FEATURES, TEMPORAL_FEATURES


@pytest.fixture
def sample_record():
    return {
        "farm_size_acres": 8.5,
        "annual_income": 250000,
        "years_farming": 15,
        "secondary_crops": ["wheat", "mustard"],
        "district": "Nashik",
        "state": "Maharashtra",
        "kyc_status": "verified",
        "bank_account_number": "123456789",
        "has_insurance": True,
        "total_loan_count": 3,
        "avg_repayment_delay_days": 2,
        "time_series": [
            {
                "ndvi": 0.65,
                "evi": 0.45,
                "soil_moisture": 0.55,
                "crop_health_score": 78.0,
                "temperature_celsius": 28.0,
                "rainfall_mm": 85.0,
                "humidity_percent": 72.0,
                "modal_price": 2200.0,
                "price_volatility_30d": 0.08,
                "price_trend_30d": 0.02,
                "repayment_on_time": True,
                "repayment_ratio": 0.95,
                "weather_anomaly_score": 0.1,
                "satellite_anomaly": False,
                "income_proxy": 18000.0,
            }
        ] * 24,
    }


def test_static_feature_shape(sample_record):
    extractor = FarmerFeatureExtractor(seq_len=24)
    static, _ = extractor.transform(sample_record)
    assert static.shape == (len(STATIC_FEATURES),), (
        f"Expected {len(STATIC_FEATURES)} static features, got {static.shape[0]}"
    )


def test_temporal_feature_shape(sample_record):
    extractor = FarmerFeatureExtractor(seq_len=24)
    _, temporal = extractor.transform(sample_record)
    assert temporal.shape == (24, len(TEMPORAL_FEATURES))


def test_padding_short_time_series():
    """Short time series should be zero-padded to seq_len."""
    extractor = FarmerFeatureExtractor(seq_len=24)
    record = {
        "farm_size_acres": 5.0,
        "time_series": [{"ndvi": 0.5} for _ in range(6)],  # only 6 months
    }
    _, temporal = extractor.transform(record)
    assert temporal.shape == (24, len(TEMPORAL_FEATURES))
    # First 18 rows should be zeros (padded)
    assert np.all(temporal[:18] == 0.0)


def test_fit_transform_normalizes(sample_record):
    """After fitting, values should be normalized."""
    extractor = FarmerFeatureExtractor(seq_len=24)
    records = [sample_record] * 5
    extractor.fit(records)
    static, temporal = extractor.transform(sample_record)
    # After StandardScaler, values should be roughly in [-3, 3]
    assert np.all(np.abs(static) < 10), "Static features not normalized"
