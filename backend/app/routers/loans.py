"""Loan management router."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.models import Farmer, Loan, LoanRepayment, TrustScore, User
from app.schemas.schemas import (
    LoanCreate,
    LoanRepaymentCreate,
    LoanRepaymentResponse,
    LoanResponse,
)

router = APIRouter(prefix="/loans", tags=["Loans"])


def _calculate_interest_rate(trust_score: float) -> float:
    """Compute interest rate based on trust score (higher score → lower rate)."""
    if trust_score >= 80:
        return 6.5
    elif trust_score >= 60:
        return 8.5
    elif trust_score >= 40:
        return 11.0
    else:
        return 14.0


def _generate_loan_number() -> str:
    """Generate a unique loan reference number."""
    return f"LN{datetime.utcnow().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"


@router.post("/", response_model=LoanResponse, status_code=201)
async def apply_for_loan(
    loan_data: LoanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a loan application. Interest rate is determined by the farmer's trust score."""
    farmer_result = await db.execute(
        select(Farmer).where(Farmer.user_id == current_user.id)
    )
    farmer = farmer_result.scalar_one_or_none()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer profile not found")

    # Fetch latest trust score
    score_result = await db.execute(
        select(TrustScore)
        .where(TrustScore.farmer_id == farmer.id)
        .order_by(TrustScore.created_at.desc())
        .limit(1)
    )
    trust_score_obj = score_result.scalar_one_or_none()
    score_value = trust_score_obj.score if trust_score_obj else 50.0

    interest_rate = _calculate_interest_rate(score_value)
    loan = Loan(
        id=uuid.uuid4(),
        farmer_id=farmer.id,
        loan_number=_generate_loan_number(),
        amount=loan_data.amount,
        interest_rate=interest_rate,
        tenure_months=loan_data.tenure_months,
        purpose=loan_data.purpose,
        trust_score_at_application=score_value,
        status="applied",
    )
    db.add(loan)
    await db.flush()
    return loan


@router.get("/", response_model=List[LoanResponse])
async def list_loans(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List loans for the current user (farmers see own loans, admins see all)."""
    query = select(Loan)
    if current_user.role == "farmer":
        farmer_result = await db.execute(
            select(Farmer).where(Farmer.user_id == current_user.id)
        )
        farmer = farmer_result.scalar_one_or_none()
        if not farmer:
            return []
        query = query.where(Loan.farmer_id == farmer.id)
    if status:
        query = query.where(Loan.status == status)

    result = await db.execute(query.order_by(Loan.created_at.desc()))
    return result.scalars().all()


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details for a specific loan."""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@router.patch("/{loan_id}/status")
async def update_loan_status(
    loan_id: uuid.UUID,
    new_status: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("bank_officer", "admin")),
):
    """Update a loan's status (bank officer / admin only)."""
    valid_statuses = {"approved", "disbursed", "rejected", "closed"}
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Choose from: {valid_statuses}"
        )

    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    loan.status = new_status
    if new_status == "disbursed":
        loan.disbursed_at = datetime.utcnow()
        loan.due_date = datetime.utcnow() + timedelta(days=loan.tenure_months * 30)

    await db.flush()
    return {"message": f"Loan status updated to {new_status}"}


@router.post(
    "/{loan_id}/repayments", response_model=LoanRepaymentResponse, status_code=201
)
async def record_repayment(
    loan_id: uuid.UUID,
    repayment_data: LoanRepaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a loan repayment."""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    repayment = LoanRepayment(
        id=uuid.uuid4(),
        loan_id=loan_id,
        amount=repayment_data.amount,
        payment_date=datetime.utcnow(),
        payment_method=repayment_data.payment_method,
        transaction_id=repayment_data.transaction_id,
        status="completed",
    )
    db.add(repayment)
    await db.flush()
    return repayment
