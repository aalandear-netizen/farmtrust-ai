"""
ML model serving microservice.

Exposes a /predict endpoint that accepts a farmer_id and returns
a trust score computed by the TFT model.
"""
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from ml.features.feature_engineering import FarmerFeatureExtractor
from ml.models.tft import TemporalFusionTransformer


class ServingSettings(BaseSettings):
    MODEL_PATH: str = "/app/ml/models/tft_weights.pt"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEVICE: str = "cpu"

    class Config:
        env_file = ".env"


config = ServingSettings()

app = FastAPI(title="FarmTrust ML Service", version="1.0.0")

# ─── Model Loading ────────────────────────────────────────────────────────────

_model: Optional[TemporalFusionTransformer] = None
_extractor: Optional[FarmerFeatureExtractor] = None


def _load_model() -> TemporalFusionTransformer:
    """Load or create the TFT model."""
    model = TemporalFusionTransformer(
        num_static_features=12,
        num_temporal_features=15,
        hidden_dim=128,
        num_heads=4,
        num_lstm_layers=2,
        dropout=0.1,
        seq_len=24,
    )
    model_path = Path(config.MODEL_PATH)
    if model_path.exists():
        state = torch.load(model_path, map_location=config.DEVICE, weights_only=True)
        model.load_state_dict(state)
    model.eval()
    return model


@app.on_event("startup")
async def startup():
    global _model, _extractor
    _model = _load_model()
    _extractor = FarmerFeatureExtractor(seq_len=24)


# ─── Request / Response schemas ───────────────────────────────────────────────

class PredictRequest(BaseModel):
    farmer_id: str
    farmer_data: Optional[Dict] = None  # if None, a mock record is used


class PredictResponse(BaseModel):
    farmer_id: str
    score: float
    confidence: float
    grade: str
    repayment_score: float
    crop_yield_score: float
    weather_risk_score: float
    market_volatility_score: float
    satellite_health_score: float
    social_capital_score: float
    model_version: str
    feature_importance: Dict[str, float]
    explanation: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Run TFT inference and return a trust score for the given farmer."""
    if _model is None or _extractor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    record = request.farmer_data or _mock_farmer_record(request.farmer_id)
    static_np, temporal_np = _extractor.transform(record)

    static_t = torch.from_numpy(static_np).unsqueeze(0).float()     # (1, S)
    temporal_t = torch.from_numpy(temporal_np).unsqueeze(0).float() # (1, T, F)

    with torch.no_grad():
        outputs = _model(static_t, temporal_t)

    score = float(outputs["trust_score"][0].clamp(0, 100))
    sub = outputs["sub_scores"][0].clamp(0, 100)
    confidence = float(outputs["confidence"][0].clamp(0, 1))
    var_imp = outputs["variable_importance"][0].tolist()

    sub_names = [
        "repayment_score",
        "crop_yield_score",
        "weather_risk_score",
        "market_volatility_score",
        "satellite_health_score",
        "social_capital_score",
    ]
    from ml.features.feature_engineering import TEMPORAL_FEATURES

    feature_importance = {
        f: round(float(v), 4)
        for f, v in zip(
            TEMPORAL_FEATURES[: len(var_imp)],
            var_imp,
        )
    }

    grade = TemporalFusionTransformer.score_to_grade(score)
    explanation = _build_explanation(score, sub, grade)

    return PredictResponse(
        farmer_id=request.farmer_id,
        score=round(score, 2),
        confidence=round(confidence, 4),
        grade=grade,
        repayment_score=round(float(sub[0]), 2),
        crop_yield_score=round(float(sub[1]), 2),
        weather_risk_score=round(float(sub[2]), 2),
        market_volatility_score=round(float(sub[3]), 2),
        satellite_health_score=round(float(sub[4]), 2),
        social_capital_score=round(float(sub[5]), 2),
        model_version="tft-v1.0",
        feature_importance=feature_importance,
        explanation=explanation,
    )


@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": _model is not None}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mock_farmer_record(farmer_id: str) -> Dict:
    """Generate a synthetic record when no real data is provided."""
    import numpy as np

    rng = np.random.default_rng(int(uuid.UUID(farmer_id).int % 2**32) if _is_valid_uuid(farmer_id) else 42)
    return {
        "farm_size_acres": float(rng.uniform(1, 20)),
        "annual_income": float(rng.uniform(50000, 500000)),
        "years_farming": float(rng.integers(1, 30)),
        "secondary_crops": ["wheat", "mustard"][: rng.integers(0, 3)],
        "district": "Nashik",
        "state": "Maharashtra",
        "kyc_status": "verified",
        "has_insurance": bool(rng.integers(0, 2)),
        "time_series": [
            {
                "ndvi": float(rng.uniform(0.2, 0.9)),
                "evi": float(rng.uniform(0.1, 0.7)),
                "soil_moisture": float(rng.uniform(0.2, 0.8)),
                "crop_health_score": float(rng.uniform(40, 100)),
                "temperature_celsius": float(rng.uniform(20, 38)),
                "rainfall_mm": float(rng.uniform(0, 200)),
                "humidity_percent": float(rng.uniform(40, 90)),
                "modal_price": float(rng.uniform(1000, 5000)),
                "price_volatility_30d": float(rng.uniform(0, 0.3)),
                "price_trend_30d": float(rng.uniform(-0.1, 0.1)),
                "repayment_on_time": bool(rng.integers(0, 2)),
                "repayment_ratio": float(rng.uniform(0.5, 1.0)),
                "weather_anomaly_score": float(rng.uniform(0, 1)),
                "satellite_anomaly": bool(rng.integers(0, 5) == 0),
                "income_proxy": float(rng.uniform(3000, 40000)),
            }
            for _ in range(24)
        ],
    }


def _is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


def _build_explanation(score: float, sub_scores: torch.Tensor, grade: str) -> str:
    worst_idx = int(sub_scores.argmin())
    sub_names = [
        "loan repayment history",
        "crop yield predictability",
        "weather risk exposure",
        "market price volatility",
        "satellite-derived crop health",
        "social capital",
    ]
    worst = sub_names[worst_idx]
    return (
        f"Overall trust grade {grade} ({score:.1f}/100). "
        f"Primary area for improvement: {worst}. "
        f"Score reflects analysis of historical weather, market, satellite and financial data."
    )


if __name__ == "__main__":
    uvicorn.run(app, host=config.HOST, port=config.PORT)
