import pytest


@pytest.mark.asyncio
async def test_application_smoke(client):
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    restaurants = await client.get("/api/v1/restaurants/")
    assert restaurants.status_code == 200
    assert restaurants.json()

    login = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "rider@campus.edu",
            "password": "RiderPass123!",
        },
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    rider_headers = {"Authorization": f"Bearer {token}"}

    profile = await client.get("/api/v1/auth/me", headers=rider_headers)
    assert profile.status_code == 200
    assert profile.json()["role"] == "delivery_partner"

    availability = await client.get(
        "/api/v1/orders/rider/availability",
        headers=rider_headers,
    )
    assert availability.status_code == 200
    assert availability.json()["is_available"] is True

    offline = await client.patch(
        "/api/v1/orders/rider/availability",
        json={"is_available": False},
        headers=rider_headers,
    )
    assert offline.status_code == 200
    assert offline.json()["is_available"] is False

    online = await client.patch(
        "/api/v1/orders/rider/availability",
        json={"is_available": True},
        headers=rider_headers,
    )
    assert online.status_code == 200
    assert online.json()["is_available"] is True
