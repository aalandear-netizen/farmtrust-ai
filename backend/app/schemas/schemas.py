"""Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ─── Auth Schemas ────────────────────────────────────────────────────────────


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = "farmer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Farmer Schemas ───────────────────────────────────────────────────────────


class FarmerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    aadhaar_number: Optional[str] = Field(None, min_length=12, max_length=12)
    pan_number: Optional[str] = Field(None, min_length=10, max_length=10)
    farm_size_acres: Optional[float] = Field(None, gt=0)
    primary_crop: Optional[str] = None
    secondary_crops: Optional[List[str]] = []
    district: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = Field(None, min_length=6, max_length=6)
    annual_income: Optional[float] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class FarmerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    farm_size_acres: Optional[float] = None
    primary_crop: Optional[str] = None
    secondary_crops: Optional[List[str]] = None
    district: Optional[str] = None
    state: Optional[str] = None
    annual_income: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class FarmerResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    phone: Optional[str]
    farm_size_acres: Optional[float]
    primary_crop: Optional[str]
    secondary_crops: List[str]
    district: Optional[str]
    state: Optional[str]
    kyc_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Trust Score Schemas ──────────────────────────────────────────────────────


class TrustScoreResponse(BaseModel):
    id: uuid.UUID
    farmer_id: uuid.UUID
    score: float
    confidence: float
    grade: str
    repayment_score: Optional[float]
    crop_yield_score: Optional[float]
    weather_risk_score: Optional[float]
    market_volatility_score: Optional[float]
    satellite_health_score: Optional[float]
    social_capital_score: Optional[float]
    model_version: Optional[str]
    feature_importance: Dict[str, Any]
    explanation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Loan Schemas ─────────────────────────────────────────────────────────────


class LoanCreate(BaseModel):
    amount: float = Field(..., gt=0)
    tenure_months: int = Field(..., gt=0, le=360)
    purpose: Optional[str] = None


class LoanResponse(BaseModel):
    id: uuid.UUID
    farmer_id: uuid.UUID
    loan_number: str
    amount: float
    interest_rate: float
    tenure_months: int
    purpose: Optional[str]
    status: str
    disbursed_at: Optional[datetime]
    due_date: Optional[datetime]
    trust_score_at_application: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class LoanRepaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None


class LoanRepaymentResponse(BaseModel):
    id: uuid.UUID
    loan_id: uuid.UUID
    amount: float
    payment_date: datetime
    payment_method: Optional[str]
    transaction_id: Optional[str]
    status: str

    class Config:
        from_attributes = True


# ─── Insurance Schemas ────────────────────────────────────────────────────────


class InsurancePolicyCreate(BaseModel):
    crop: str
    area_insured_acres: float = Field(..., gt=0)
    sum_insured: float = Field(..., gt=0)
    scheme: Optional[str] = None
    start_date: datetime
    end_date: datetime


class InsurancePolicyResponse(BaseModel):
    id: uuid.UUID
    farmer_id: uuid.UUID
    policy_number: str
    crop: str
    area_insured_acres: float
    sum_insured: float
    premium: float
    status: str
    start_date: datetime
    end_date: datetime
    scheme: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class InsuranceClaimCreate(BaseModel):
    reason: str
    amount_claimed: float = Field(..., gt=0)
    evidence: Optional[List[Dict[str, Any]]] = []


class InsuranceClaimResponse(BaseModel):
    id: uuid.UUID
    policy_id: uuid.UUID
    claim_number: str
    reason: str
    amount_claimed: float
    amount_approved: Optional[float]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Market Schemas ───────────────────────────────────────────────────────────


class MarketListingCreate(BaseModel):
    crop: str
    quantity_kg: float = Field(..., gt=0)
    asking_price_per_kg: float = Field(..., gt=0)
    quality_grade: Optional[str] = None
    available_from: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class MarketListingResponse(BaseModel):
    id: uuid.UUID
    farmer_id: uuid.UUID
    crop: str
    quantity_kg: float
    asking_price_per_kg: float
    quality_grade: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class MarketPriceResponse(BaseModel):
    id: uuid.UUID
    crop: str
    mandi: str
    state: str
    min_price: float
    max_price: float
    modal_price: float
    price_date: datetime

    class Config:
        from_attributes = True


# ─── Government Scheme Schemas ────────────────────────────────────────────────


class GovernmentSchemeResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    ministry: Optional[str]
    eligibility_criteria: Dict[str, Any]
    benefits: Dict[str, Any]
    application_url: Optional[str]
    is_active: bool
    deadline: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Notification Schemas ─────────────────────────────────────────────────────


class NotificationResponse(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    notification_type: str
    is_read: bool
    data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Pagination ───────────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int
