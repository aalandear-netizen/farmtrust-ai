"""Farmer management router."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.models import Farmer, User
from app.schemas.schemas import (
    FarmerCreate,
    FarmerResponse,
    FarmerUpdate,
    PaginatedResponse,
)
from app.utils.cache import cache_delete_pattern, cache_get, cache_set

router = APIRouter(prefix="/farmers", tags=["Farmers"])


@router.post("/", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
async def create_farmer(
    farmer_data: FarmerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new farmer profile linked to the current user."""
    result = await db.execute(select(Farmer).where(Farmer.user_id == current_user.id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Farmer profile already exists")

    farmer = Farmer(
        id=uuid.uuid4(),
        user_id=current_user.id,
        **farmer_data.model_dump(exclude={"latitude", "longitude"}),
    )

    if farmer_data.latitude and farmer_data.longitude:
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point

        farmer.farm_location = from_shape(
            Point(farmer_data.longitude, farmer_data.latitude), srid=4326
        )

    db.add(farmer)
    await db.flush()
    await db.refresh(farmer)
    await cache_delete_pattern("farmers:*")
    return farmer


@router.get("/", response_model=PaginatedResponse)
async def list_farmers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: Optional[str] = None,
    crop: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles("bank_officer", "government_official", "admin")
    ),
):
    """List all farmers with optional filters (admin/bank only)."""
    cache_key = f"farmers:list:{page}:{page_size}:{state}:{crop}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    query = select(Farmer)
    if state:
        query = query.where(Farmer.state == state)
    if crop:
        query = query.where(Farmer.primary_crop == crop)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    farmers = result.scalars().all()

    response = {
        "items": [FarmerResponse.model_validate(f).model_dump() for f in farmers],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }
    await cache_set(cache_key, response)
    return response


@router.get("/{farmer_id}", response_model=FarmerResponse)
async def get_farmer(
    farmer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific farmer's profile."""
    result = await db.execute(select(Farmer).where(Farmer.id == farmer_id))
    farmer = result.scalar_one_or_none()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    # Farmers can only view their own profile unless privileged
    if current_user.role == "farmer" and farmer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return farmer


@router.put("/{farmer_id}", response_model=FarmerResponse)
async def update_farmer(
    farmer_id: uuid.UUID,
    farmer_data: FarmerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a farmer's profile."""
    result = await db.execute(select(Farmer).where(Farmer.id == farmer_id))
    farmer = result.scalar_one_or_none()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    if current_user.role == "farmer" and farmer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    for field, value in farmer_data.model_dump(
        exclude_unset=True, exclude={"latitude", "longitude"}
    ).items():
        setattr(farmer, field, value)

    if farmer_data.latitude and farmer_data.longitude:
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point

        farmer.farm_location = from_shape(
            Point(farmer_data.longitude, farmer_data.latitude), srid=4326
        )

    await db.flush()
    await db.refresh(farmer)
    await cache_delete_pattern("farmers:*")
    return farmer
