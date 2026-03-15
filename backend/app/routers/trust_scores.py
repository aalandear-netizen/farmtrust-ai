"""Trust score router – AI-powered creditworthiness scoring."""

import uuid
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.models import Farmer, TrustScore, User
from app.schemas.schemas import TrustScoreResponse
from app.utils.cache import cache_get, cache_set

router = APIRouter(prefix="/trust-scores", tags=["Trust Scores"])
settings = get_settings()


async def _compute_trust_score(farmer_id: str) -> dict:
    """Call the ML microservice to compute a fresh trust score."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/predict",
                json={"farmer_id": farmer_id},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            # Fallback: return a placeholder score so the API remains available
            return {
                "score": 50.0,
                "confidence": 0.5,
                "grade": "BB",
                "repayment_score": 50.0,
                "crop_yield_score": 50.0,
                "weather_risk_score": 50.0,
                "market_volatility_score": 50.0,
                "satellite_health_score": 50.0,
                "social_capital_score": 50.0,
                "model_version": "fallback-1.0",
                "feature_importance": {},
                "explanation": "ML service unavailable – using placeholder score",
            }


@router.post("/farmers/{farmer_id}/compute", response_model=TrustScoreResponse)
async def compute_trust_score(
    farmer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles("bank_officer", "government_official", "admin")
    ),
):
    """Trigger ML pipeline to compute and store a new trust score for a farmer."""
    result = await db.execute(select(Farmer).where(Farmer.id == farmer_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Farmer not found")

    score_data = await _compute_trust_score(str(farmer_id))

    trust_score = TrustScore(
        id=uuid.uuid4(),
        farmer_id=farmer_id,
        **{k: v for k, v in score_data.items() if k != "farmer_id"},
    )
    db.add(trust_score)
    await db.flush()

    # Invalidate cache
    await cache_set(
        f"trust_score:{farmer_id}:latest",
        TrustScoreResponse.model_validate(trust_score).model_dump(),
    )
    return trust_score


@router.get("/farmers/{farmer_id}/latest", response_model=TrustScoreResponse)
async def get_latest_trust_score(
    farmer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the most recent trust score for a farmer."""
    # Allow farmers to see their own score
    if current_user.role == "farmer":
        farmer_result = await db.execute(select(Farmer).where(Farmer.id == farmer_id))
        farmer = farmer_result.scalar_one_or_none()
        if not farmer or farmer.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    cache_key = f"trust_score:{farmer_id}:latest"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(TrustScore)
        .where(TrustScore.farmer_id == farmer_id)
        .order_by(TrustScore.created_at.desc())
        .limit(1)
    )
    trust_score = result.scalar_one_or_none()
    if not trust_score:
        raise HTTPException(
            status_code=404, detail="No trust score found for this farmer"
        )

    await cache_set(
        cache_key, TrustScoreResponse.model_validate(trust_score).model_dump()
    )
    return trust_score


@router.get("/farmers/{farmer_id}/history", response_model=List[TrustScoreResponse])
async def get_trust_score_history(
    farmer_id: uuid.UUID,
    limit: int = 12,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get historical trust scores for trend analysis."""
    result = await db.execute(
        select(TrustScore)
        .where(TrustScore.farmer_id == farmer_id)
        .order_by(TrustScore.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
