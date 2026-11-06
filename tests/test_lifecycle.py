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

    # 1. Customer places order (PLACED)
    order_id = await place_order(client, student_token)

    # 2. Owner accepts order (ACCEPTED)
    res_accept = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "accepted"

    # 3. Owner begins preparing (PREPARING)
    res_prep = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "preparing"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_prep.status_code == 200
    assert res_prep.json()["status"] == "preparing"

    # 4. Owner marks ready (READY)
    res_ready = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "ready"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"

    # 5. Owner assigns delivery partner (ASSIGNED)
    res_assign = await client.post(
        f"/api/v1/orders/{order_id}/assign-rider",
        json={"delivery_partner_id": rider_id},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["status"] == "assigned"
    assert res_assign.json()["delivery"]["delivery_partner_id"] == rider_id

    # 6. Rider marks out for delivery (OUT_FOR_DELIVERY)
    res_pickup = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "out_for_delivery"},
        headers={"Authorization": f"Bearer {rider_token}"},
    )
    assert res_pickup.status_code == 200
    assert res_pickup.json()["status"] == "out_for_delivery"

    # 7. Rider marks delivered (DELIVERED)
    res_deliv = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {rider_token}"},
    )
    assert res_deliv.status_code == 200
    assert res_deliv.json()["status"] == "delivered"


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