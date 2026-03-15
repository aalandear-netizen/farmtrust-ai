"""Tests for farmer management endpoints."""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, role: str = "farmer") -> str:
    """Helper: register a user and return the JWT token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "role": role},
    )
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_farmer_profile(client: AsyncClient):
    """Authenticated user can create a farmer profile."""
    token = await _register_and_login(client, "farmer1@test.com")
    response = await client.post(
        "/api/v1/farmers/",
        json={
            "name": "Ramesh Kumar",
            "phone": "9876543210",
            "farm_size_acres": 5.0,
            "primary_crop": "wheat",
            "state": "Punjab",
            "district": "Ludhiana",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Ramesh Kumar"
    assert data["primary_crop"] == "wheat"
    assert data["state"] == "Punjab"


@pytest.mark.asyncio
async def test_create_duplicate_farmer_profile(client: AsyncClient):
    """Creating a second farmer profile for the same user should return 400."""
    token = await _register_and_login(client, "farmer2@test.com")
    payload = {"name": "Test Farmer", "farm_size_acres": 3.0}
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/v1/farmers/", json=payload, headers=headers)
    response = await client.post("/api/v1/farmers/", json=payload, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_farmers_requires_privilege(client: AsyncClient):
    """A plain farmer should not be able to list all farmers."""
    token = await _register_and_login(client, "farmer3@test.com", role="farmer")
    response = await client.get(
        "/api/v1/farmers/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_farmers_as_bank_officer(client: AsyncClient):
    """Bank officers can list farmers."""
    token = await _register_and_login(client, "banker@test.com", role="bank_officer")
    response = await client.get(
        "/api/v1/farmers/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_own_farmer_profile(client: AsyncClient):
    """Farmer can read their own profile by ID."""
    token = await _register_and_login(client, "farmer4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    create_resp = await client.post(
        "/api/v1/farmers/",
        json={"name": "Own Profile", "farm_size_acres": 2.5},
        headers=headers,
    )
    farmer_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/farmers/{farmer_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == farmer_id


@pytest.mark.asyncio
async def test_update_farmer_profile(client: AsyncClient):
    """Farmer can update their own profile."""
    token = await _register_and_login(client, "farmer5@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    create_resp = await client.post(
        "/api/v1/farmers/",
        json={"name": "Original Name"},
        headers=headers,
    )
    farmer_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/farmers/{farmer_id}",
        json={"name": "Updated Name", "primary_crop": "rice"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Name"
    assert update_resp.json()["primary_crop"] == "rice"
