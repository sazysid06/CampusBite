import pytest
from jose import jwt


async def get_token(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def get_user_id_from_token(token: str) -> int:
    claims = jwt.get_unverified_claims(token)
    return int(claims["sub"])


async def place_order(client, student_token: str) -> int:
    order_payload = {
        "restaurant_id": 1,
        "delivery_address": "Hostel Block B, Room 204",
        "special_instructions": "Leave at front desk",
        "items": [{"menu_item_id": 1, "quantity": 2}],
    }
    res = await client.post(
        "/api/v1/orders/",
        json=order_payload,
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 201, f"Order placement failed: {res.text}"
    data = res.json()
    assert data["status"] == "placed"
    assert data["payment"]["status"] == "mock_paid"
    return data["id"]


@pytest.mark.asyncio
async def test_order_full_lifecycle(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    owner_token = await get_token(client, "dhaba_owner@campus.edu", "OwnerPass123!")
    rider_token = await get_token(client, "rider@campus.edu", "RiderPass123!")
    rider_id = get_user_id_from_token(rider_token)
    rider_headers = {"Authorization": f"Bearer {rider_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    availability = await client.patch(
        "/api/v1/orders/rider/availability",
        json={"is_available": True},
        headers=rider_headers,
    )
    assert availability.status_code == 200

    order_id = await place_order(client, student_token)
    res_accept = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers=owner_headers,
    )
    assert res_accept.status_code == 200
    assert res_accept.json()["delivery"]["delivery_partner_id"] == rider_id

    at_restaurant = await client.patch(
        f"/api/v1/orders/{order_id}/delivery-status",
        json={"status": "at_restaurant"},
        headers=rider_headers,
    )
    assert at_restaurant.status_code == 200, at_restaurant.text

    for order_status in ("preparing", "ready"):
        response = await client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": order_status},
            headers=owner_headers,
        )
        assert response.status_code == 200

    for delivery_status in ("picked_up", "on_route"):
        response = await client.patch(
            f"/api/v1/orders/{order_id}/delivery-status",
            json={"status": delivery_status},
            headers=rider_headers,
        )
        assert response.status_code == 200

    delivered = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=student_headers,
    )
    assert delivered.status_code == 200
    assert delivered.json()["delivery"]["status"] == "completed"

    availability = await client.get(
        "/api/v1/orders/rider/availability",
        headers=rider_headers,
    )
    assert availability.json()["is_available"] is True


@pytest.mark.asyncio
async def test_waiting_order_is_assigned_when_rider_becomes_available(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    owner_token = await get_token(client, "dhaba_owner@campus.edu", "OwnerPass123!")
    rider_token = await get_token(client, "rider@campus.edu", "RiderPass123!")
    rider_headers = {"Authorization": f"Bearer {rider_token}"}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    offline = await client.patch(
        "/api/v1/orders/rider/availability",
        json={"is_available": False},
        headers=rider_headers,
    )
    assert offline.status_code == 200
    order_id = await place_order(client, student_token)
    accepted = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers=owner_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["delivery"]["delivery_partner_id"] is None

    online = await client.patch(
        "/api/v1/orders/rider/availability",
        json={"is_available": True},
        headers=rider_headers,
    )
    assert online.status_code == 200
    assert online.json()["is_available"] is False

    order = await client.get(
        f"/api/v1/orders/{order_id}",
        headers=student_headers,
    )
    assert order.json()["delivery"]["delivery_partner_id"] == get_user_id_from_token(
        rider_token
    )
    assert order.json()["delivery"]["status"] == "on_the_way_to_restaurant"


@pytest.mark.asyncio
async def test_customer_unauthorized_status_update(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    order_id = await place_order(client, student_token)

    # Customer tries to advance status to delivered
    res = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 400
    assert "Customers can only cancel orders" in res.json()["detail"]


@pytest.mark.asyncio
async def test_owner_cannot_perform_delivery_transitions(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    owner_token = await get_token(client, "dhaba_owner@campus.edu", "OwnerPass123!")
    order_id = await place_order(client, student_token)

    # Owner attempts to skip kitchen workflow directly to out_for_delivery
    res = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "out_for_delivery"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res.status_code == 400
    assert "Invalid transition" in res.json()["detail"]


@pytest.mark.asyncio
async def test_rider_cannot_perform_kitchen_transitions(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    rider_token = await get_token(client, "rider@campus.edu", "RiderPass123!")
    order_id = await place_order(client, student_token)

    # Rider attempts to accept an order
    res = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {rider_token}"},
    )
    assert res.status_code == 403
    assert "Only the assigned delivery partner can update this order" in res.json()["detail"]


@pytest.mark.asyncio
async def test_customer_cannot_cancel_after_preparation_starts(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    owner_token = await get_token(client, "dhaba_owner@campus.edu", "OwnerPass123!")
    order_id = await place_order(client, student_token)

    # Owner accepts and prepares
    await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "preparing"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    # Customer tries to cancel while preparing
    cancel_res = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert cancel_res.status_code == 400
    assert "Customers can only cancel orders in 'placed' status" in cancel_res.json()["detail"]