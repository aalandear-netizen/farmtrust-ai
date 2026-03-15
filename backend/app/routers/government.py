"""Government schemes and subsidies router."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Farmer, GovernmentScheme, SchemeApplication, User
from app.schemas.schemas import GovernmentSchemeResponse
from app.utils.cache import cache_get, cache_set

router = APIRouter(prefix="/government", tags=["Government Schemes"])


@router.get("/schemes", response_model=List[GovernmentSchemeResponse])
async def list_schemes(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available government schemes."""
    cache_key = f"gov_schemes:{active_only}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    query = select(GovernmentScheme)
    if active_only:
        query = query.where(GovernmentScheme.is_active)

    result = await db.execute(query.order_by(GovernmentScheme.name))
    schemes = result.scalars().all()
    serialized = [
        GovernmentSchemeResponse.model_validate(s).model_dump() for s in schemes
    ]
    await cache_set(cache_key, serialized, ttl=1800)
    return serialized


@router.get("/schemes/{scheme_id}", response_model=GovernmentSchemeResponse)
async def get_scheme(
    scheme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details about a specific scheme."""
    result = await db.execute(
        select(GovernmentScheme).where(GovernmentScheme.id == scheme_id)
    )
    scheme = result.scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme


@router.post("/schemes/{scheme_id}/apply", status_code=201)
async def apply_to_scheme(
    scheme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply for a government scheme."""
    farmer_result = await db.execute(
        select(Farmer).where(Farmer.user_id == current_user.id)
    )
    farmer = farmer_result.scalar_one_or_none()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer profile not found")

    scheme_result = await db.execute(
        select(GovernmentScheme).where(GovernmentScheme.id == scheme_id)
    )
    if not scheme_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Scheme not found")

    # Check for duplicate application
    existing = await db.execute(
        select(SchemeApplication).where(
            SchemeApplication.farmer_id == farmer.id,
            SchemeApplication.scheme_id == scheme_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already applied to this scheme")

    application = SchemeApplication(
        id=uuid.uuid4(),
        farmer_id=farmer.id,
        scheme_id=scheme_id,
        status="submitted",
        application_data={},
    )
    db.add(application)
    await db.flush()
    return {
        "message": "Application submitted successfully",
        "application_id": str(application.id),
    }
