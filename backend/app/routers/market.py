"""Market place router for produce listings and price data."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Farmer, MarketListing, MarketPrice, User
from app.schemas.schemas import (
    MarketListingCreate,
    MarketListingResponse,
    MarketPriceResponse,
)
from app.utils.cache import cache_get, cache_set

router = APIRouter(prefix="/market", tags=["Market"])


@router.post("/listings", response_model=MarketListingResponse, status_code=201)
async def create_listing(
    listing_data: MarketListingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a produce listing for sale."""
    farmer_result = await db.execute(
        select(Farmer).where(Farmer.user_id == current_user.id)
    )
    farmer = farmer_result.scalar_one_or_none()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer profile not found")

    listing = MarketListing(
        id=uuid.uuid4(),
        farmer_id=farmer.id,
        crop=listing_data.crop,
        quantity_kg=listing_data.quantity_kg,
        asking_price_per_kg=listing_data.asking_price_per_kg,
        quality_grade=listing_data.quality_grade,
        available_from=listing_data.available_from,
        status="active",
    )
    db.add(listing)
    await db.flush()
    return listing


@router.get("/listings", response_model=List[MarketListingResponse])
async def list_listings(
    crop: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse active market listings."""
    query = select(MarketListing).where(MarketListing.status == "active")
    if crop:
        query = query.where(MarketListing.crop == crop)
    result = await db.execute(query.order_by(MarketListing.created_at.desc()))
    return result.scalars().all()


@router.get("/prices", response_model=List[MarketPriceResponse])
async def get_market_prices(
    crop: str = Query(..., description="Crop name to look up"),
    state: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent mandi prices for a crop."""
    cache_key = f"market_prices:{crop}:{state}:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    query = (
        select(MarketPrice)
        .where(MarketPrice.crop == crop)
        .order_by(MarketPrice.price_date.desc())
        .limit(limit)
    )
    if state:
        query = query.where(MarketPrice.state == state)

    result = await db.execute(query)
    prices = result.scalars().all()
    serialized = [MarketPriceResponse.model_validate(p).model_dump() for p in prices]
    await cache_set(cache_key, serialized, ttl=900)  # 15 min cache
    return serialized
