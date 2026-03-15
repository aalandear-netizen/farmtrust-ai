"""Insurance management router."""

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Farmer, InsuranceClaim, InsurancePolicy, User
from app.schemas.schemas import (
    InsuranceClaimCreate,
    InsuranceClaimResponse,
    InsurancePolicyCreate,
    InsurancePolicyResponse,
)

router = APIRouter(prefix="/insurance", tags=["Insurance"])

_PREMIUM_RATES = {
    "kharif": 0.02,  # 2% of sum insured (PMFBY)
    "rabi": 0.015,  # 1.5%
    "commercial": 0.05,
}


def _generate_policy_number() -> str:
    return f"POL{datetime.utcnow().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"


def _generate_claim_number() -> str:
    return f"CLM{datetime.utcnow().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"


def _compute_premium(sum_insured: float, crop: str) -> float:
    """Estimate crop insurance premium based on PMFBY-style rates."""
    rate = _PREMIUM_RATES.get("kharif", 0.02)
    return round(sum_insured * rate, 2)


@router.post("/policies", response_model=InsurancePolicyResponse, status_code=201)
async def create_policy(
    policy_data: InsurancePolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply for a new crop insurance policy."""
    farmer_result = await db.execute(
        select(Farmer).where(Farmer.user_id == current_user.id)
    )
    farmer = farmer_result.scalar_one_or_none()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer profile not found")

    premium = _compute_premium(float(policy_data.sum_insured), policy_data.crop)

    policy = InsurancePolicy(
        id=uuid.uuid4(),
        farmer_id=farmer.id,
        policy_number=_generate_policy_number(),
        crop=policy_data.crop,
        area_insured_acres=policy_data.area_insured_acres,
        sum_insured=policy_data.sum_insured,
        premium=premium,
        scheme=policy_data.scheme,
        start_date=policy_data.start_date,
        end_date=policy_data.end_date,
        status="active",
    )
    db.add(policy)
    await db.flush()
    return policy


@router.get("/policies", response_model=List[InsurancePolicyResponse])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List insurance policies for the current farmer."""
    farmer_result = await db.execute(
        select(Farmer).where(Farmer.user_id == current_user.id)
    )
    farmer = farmer_result.scalar_one_or_none()
    if not farmer:
        return []

    result = await db.execute(
        select(InsurancePolicy).where(InsurancePolicy.farmer_id == farmer.id)
    )
    return result.scalars().all()


@router.post(
    "/policies/{policy_id}/claims",
    response_model=InsuranceClaimResponse,
    status_code=201,
)
async def file_claim(
    policy_id: uuid.UUID,
    claim_data: InsuranceClaimCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """File an insurance claim against a policy."""
    result = await db.execute(
        select(InsurancePolicy).where(InsurancePolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    claim = InsuranceClaim(
        id=uuid.uuid4(),
        policy_id=policy_id,
        claim_number=_generate_claim_number(),
        reason=claim_data.reason,
        amount_claimed=claim_data.amount_claimed,
        evidence=claim_data.evidence or [],
        status="submitted",
    )
    db.add(claim)
    await db.flush()
    return claim
