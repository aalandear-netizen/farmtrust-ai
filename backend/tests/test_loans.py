"""Tests for loan management endpoints."""
import pytest
from httpx import AsyncClient


async def _setup_farmer(client: AsyncClient, email: str) -> tuple[str, str]:
    """Register a farmer user, create a profile, and return (token, farmer_id)."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "role": "farmer"},
    )
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/farmers/",
        json={"name": "Test Farmer"},
        headers=headers,
    )
    farmer_id = create.json()["id"]
    return token, farmer_id


@pytest.mark.asyncio
async def test_apply_for_loan(client: AsyncClient):
    """Farmer can apply for a loan."""
    token, _ = await _setup_farmer(client, "loanfarmer@test.com")
    response = await client.post(
        "/api/v1/loans/",
        json={"amount": 50000, "tenure_months": 12, "purpose": "Seeds and fertiliser"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 50000.0
    assert data["status"] == "applied"
    assert "loan_number" in data
    assert "interest_rate" in data


@pytest.mark.asyncio
async def test_loan_interest_rate_default_score(client: AsyncClient):
    """With no trust score, interest rate should default to a mid-range value."""
    token, _ = await _setup_farmer(client, "loanrate@test.com")
    response = await client.post(
        "/api/v1/loans/",
        json={"amount": 100000, "tenure_months": 24},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    # Default trust score is 50.0 → interest rate should be 11.0%
    assert response.json()["interest_rate"] == 11.0


@pytest.mark.asyncio
async def test_list_loans(client: AsyncClient):
    """Farmer can list their own loans."""
    token, _ = await _setup_farmer(client, "listloan@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/v1/loans/", json={"amount": 10000, "tenure_months": 6}, headers=headers)
    response = await client.get("/api/v1/loans/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_loan_requires_farmer_profile(client: AsyncClient):
    """Applying for a loan without a farmer profile should return 404."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "noprofile@test.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": "noprofile@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    response = await client.post(
        "/api/v1/loans/",
        json={"amount": 5000, "tenure_months": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
