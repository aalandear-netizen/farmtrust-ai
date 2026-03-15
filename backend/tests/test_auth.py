"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient):
    """Register a new user and verify the response."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "farmer@test.com", "password": "password123", "role": "farmer"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "farmer@test.com"
    assert data["role"] == "farmer"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Registering with an existing email should return 400."""
    payload = {"email": "dup@test.com", "password": "password123"}
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Successful login should return a JWT access token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@test.com", "password": "password123"},
    )
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "login@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Wrong password should return 401."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@test.com", "password": "correctpass"},
    )
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "wrong@test.com", "password": "wrongpass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    """Authenticated user should be able to retrieve their own profile."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "me@test.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": "me@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@test.com"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    """Request without token should return 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
