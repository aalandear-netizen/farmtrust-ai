"""SQLAlchemy models for the FarmTrust AI database."""

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    """User accounts for authentication."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        SAEnum(
            "farmer", "bank_officer", "government_official", "admin", name="user_role"
        ),
        nullable=False,
        default="farmer",
    )
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    farmer = relationship("Farmer", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")


class Farmer(TimestampMixin, Base):
    """Farmer profile and agricultural information."""

    __tablename__ = "farmers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    aadhaar_number = Column(String(12), nullable=True, unique=True)
    pan_number = Column(String(10), nullable=True, unique=True)

    # Farm details
    farm_size_acres = Column(Float, nullable=True)
    primary_crop = Column(String(100), nullable=True)
    secondary_crops = Column(JSONB, default=list)
    farm_location = Column(Geometry("POINT", srid=4326), nullable=True)
    district = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pin_code = Column(String(6), nullable=True)

    # Financial
    annual_income = Column(Numeric(12, 2), nullable=True)
    bank_account_number = Column(String(20), nullable=True)
    bank_ifsc = Column(String(11), nullable=True)

    # KYC
    kyc_status = Column(
        SAEnum("pending", "verified", "rejected", name="kyc_status"),
        default="pending",
        nullable=False,
    )
    kyc_documents = Column(JSONB, default=dict)

    user = relationship("User", back_populates="farmer")
    trust_scores = relationship(
        "TrustScore", back_populates="farmer", order_by="TrustScore.created_at.desc()"
    )
    loans = relationship("Loan", back_populates="farmer")
    insurance_policies = relationship("InsurancePolicy", back_populates="farmer")
    market_listings = relationship("MarketListing", back_populates="farmer")
    satellite_data = relationship("SatelliteData", back_populates="farmer")
    weather_data = relationship("WeatherData", back_populates="farmer")


class TrustScore(TimestampMixin, Base):
    """AI-computed trust score history for farmers."""

    __tablename__ = "trust_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(
        UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False, index=True
    )

    score = Column(Float, nullable=False)  # 0-100
    confidence = Column(Float, nullable=False)  # 0-1
    grade = Column(String(2), nullable=False)  # AAA, AA, A, BBB, BB, B, C, D

    # Sub-scores
    repayment_score = Column(Float, nullable=True)
    crop_yield_score = Column(Float, nullable=True)
    weather_risk_score = Column(Float, nullable=True)
    market_volatility_score = Column(Float, nullable=True)
    satellite_health_score = Column(Float, nullable=True)
    social_capital_score = Column(Float, nullable=True)

    # Model metadata
    model_version = Column(String(20), nullable=True)
    feature_importance = Column(JSONB, default=dict)
    explanation = Column(Text, nullable=True)

    farmer = relationship("Farmer", back_populates="trust_scores")


class Loan(TimestampMixin, Base):
    """Loan applications and disbursements."""

    __tablename__ = "loans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(
        UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False, index=True
    )
    loan_number = Column(String(20), unique=True, nullable=False)

    amount = Column(Numeric(12, 2), nullable=False)
    interest_rate = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    purpose = Column(String(255), nullable=True)

    status = Column(
        SAEnum(
            "applied",
            "under_review",
            "approved",
            "disbursed",
            "repaying",
            "closed",
            "rejected",
            "defaulted",
            name="loan_status",
        ),
        default="applied",
        nullable=False,
    )

    disbursed_at = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    trust_score_at_application = Column(Float, nullable=True)

    repayment_schedule = Column(JSONB, default=list)
    documents = Column(JSONB, default=list)

    farmer = relationship("Farmer", back_populates="loans")
    repayments = relationship("LoanRepayment", back_populates="loan")


class LoanRepayment(TimestampMixin, Base):
    """Loan repayment records."""

    __tablename__ = "loan_repayments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(
        UUID(as_uuid=True), ForeignKey("loans.id"), nullable=False, index=True
    )
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(DateTime(timezone=True), nullable=False)
    payment_method = Column(String(50), nullable=True)
    transaction_id = Column(String(100), nullable=True, unique=True)
    status = Column(
        SAEnum("pending", "completed", "failed", name="payment_status"),
        default="pending",
        nullable=False,
    )

    loan = relationship("Loan", back_populates="repayments")


class InsurancePolicy(TimestampMixin, Base):
    """Crop insurance policies."""

    __tablename__ = "insurance_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(
        UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False, index=True
    )
    policy_number = Column(String(20), unique=True, nullable=False)

    crop = Column(String(100), nullable=False)
    area_insured_acres = Column(Float, nullable=False)
    sum_insured = Column(Numeric(12, 2), nullable=False)
    premium = Column(Numeric(10, 2), nullable=False)

    status = Column(
        SAEnum("active", "expired", "claimed", "cancelled", name="insurance_status"),
        default="active",
        nullable=False,
    )

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    scheme = Column(String(200), nullable=True)  # e.g., PMFBY

    farmer = relationship("Farmer", back_populates="insurance_policies")
    claims = relationship("InsuranceClaim", back_populates="policy")


class InsuranceClaim(TimestampMixin, Base):
    """Insurance claim records."""

    __tablename__ = "insurance_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(
        UUID(as_uuid=True), ForeignKey("insurance_policies.id"), nullable=False
    )
    claim_number = Column(String(20), unique=True, nullable=False)
    reason = Column(Text, nullable=False)
    amount_claimed = Column(Numeric(12, 2), nullable=False)
    amount_approved = Column(Numeric(12, 2), nullable=True)
    status = Column(
        SAEnum(
            "submitted",
            "under_review",
            "approved",
            "rejected",
            "paid",
            name="claim_status",
        ),
        default="submitted",
        nullable=False,
    )
    evidence = Column(JSONB, default=list)

    policy = relationship("InsurancePolicy", back_populates="claims")


class MarketListing(TimestampMixin, Base):
    """Agricultural produce market listings."""

    __tablename__ = "market_listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(
        UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False, index=True
    )
    crop = Column(String(100), nullable=False)
    quantity_kg = Column(Float, nullable=False)
    asking_price_per_kg = Column(Numeric(8, 2), nullable=False)
    quality_grade = Column(String(5), nullable=True)
    available_from = Column(DateTime(timezone=True), nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)

    status = Column(
        SAEnum("active", "sold", "expired", "cancelled", name="listing_status"),
        default="active",
        nullable=False,
    )

    farmer = relationship("Farmer", back_populates="market_listings")


class MarketPrice(TimestampMixin, Base):
    """Historical and real-time market prices (time-series)."""

    __tablename__ = "market_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crop = Column(String(100), nullable=False, index=True)
    mandi = Column(String(200), nullable=False)
    state = Column(String(100), nullable=False)
    min_price = Column(Numeric(8, 2), nullable=False)
    max_price = Column(Numeric(8, 2), nullable=False)
    modal_price = Column(Numeric(8, 2), nullable=False)
    price_date = Column(DateTime(timezone=True), nullable=False, index=True)


class GovernmentScheme(TimestampMixin, Base):
    """Government subsidy and welfare schemes for farmers."""

    __tablename__ = "government_schemes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    ministry = Column(String(200), nullable=True)
    eligibility_criteria = Column(JSONB, default=dict)
    benefits = Column(JSONB, default=dict)
    application_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)


class SchemeApplication(TimestampMixin, Base):
    """Farmer applications to government schemes."""

    __tablename__ = "scheme_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False)
    scheme_id = Column(
        UUID(as_uuid=True), ForeignKey("government_schemes.id"), nullable=False
    )
    status = Column(
        SAEnum(
            "submitted", "approved", "rejected", "disbursed", name="scheme_app_status"
        ),
        default="submitted",
        nullable=False,
    )
    application_data = Column(JSONB, default=dict)

    __table_args__ = (
        UniqueConstraint("farmer_id", "scheme_id", name="uq_farmer_scheme"),
    )


class SatelliteData(TimestampMixin, Base):
    """Satellite imagery analysis data for farms (time-series)."""

    __tablename__ = "satellite_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(
        UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False, index=True
    )
    observation_date = Column(DateTime(timezone=True), nullable=False, index=True)
    ndvi = Column(Float, nullable=True)  # Normalized Difference Vegetation Index
    evi = Column(Float, nullable=True)  # Enhanced Vegetation Index
    soil_moisture = Column(Float, nullable=True)
    crop_health_score = Column(Float, nullable=True)
    anomaly_detected = Column(Boolean, default=False)
    source = Column(String(50), nullable=True)  # e.g., Sentinel-2, Landsat-8

    farmer = relationship("Farmer", back_populates="satellite_data")


class WeatherData(TimestampMixin, Base):
    """Weather observations and forecasts (time-series)."""

    __tablename__ = "weather_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(
        UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False, index=True
    )
    observation_date = Column(DateTime(timezone=True), nullable=False, index=True)
    temperature_celsius = Column(Float, nullable=True)
    rainfall_mm = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)
    is_forecast = Column(Boolean, default=False, nullable=False)
    data_source = Column(String(50), nullable=True)

    farmer = relationship("Farmer", back_populates="weather_data")


class AuditLog(TimestampMixin, Base):
    """Immutable audit log for regulatory compliance."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    actor_role = Column(String(50), nullable=True)
    changes = Column(JSONB, default=dict)
    extra_metadata = Column("metadata", JSONB, default=dict)
    ip_address = Column(String(45), nullable=True)


class Notification(TimestampMixin, Base):
    """User notifications."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    data = Column(JSONB, default=dict)

    user = relationship("User", back_populates="notifications")
