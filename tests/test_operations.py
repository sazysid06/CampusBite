import pytest
from jose import jwt


async def get_token(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def get_user_id(token: str) -> int:
    return int(jwt.get_unverified_claims(token)["sub"])


async def create_delivered_order(client, student_token: str, owner_token: str, rider_token: str) -> int:
    rider_id = get_user_id(rider_token)

    # 1. Place order
    res = await client.post(
        "/api/v1/orders/",
        json={
            "restaurant_id": 1,
            "delivery_address": "Hostel C Room 101",
            "items": [{"menu_item_id": 1, "quantity": 1}],
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 201
    order_id = res.json()["id"]

    # 2. Kitchen workflow to READY
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
    await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "ready"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    # 3. Rider workflow to DELIVERED
    await client.post(
        f"/api/v1/orders/{order_id}/assign-rider",
        json={"delivery_partner_id": rider_id},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "out_for_delivery"},
        headers={"Authorization": f"Bearer {rider_token}"},
    )
    await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {rider_token}"},
    )
    return order_id


@pytest.mark.asyncio
async def test_review_submission_post_delivery(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    owner_token = await get_token(client, "dhaba_owner@campus.edu", "OwnerPass123!")
    rider_token = await get_token(client, "rider@campus.edu", "RiderPass123!")

    order_id = await create_delivered_order(client, student_token, owner_token, rider_token)

    # Submit review
    res = await client.post(
        f"/api/v1/orders/{order_id}/review",
        json={"rating": 5, "comment": "Food arrived hot and fresh!"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 201
    assert res.json()["rating"] == 5

    # Reject duplicate review
    res_dup = await client.post(
        f"/api/v1/orders/{order_id}/review",
        json={"rating": 4, "comment": "Duplicate review"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res_dup.status_code == 400


@pytest.mark.asyncio
async def test_refund_workflow(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    owner_token = await get_token(client, "dhaba_owner@campus.edu", "OwnerPass123!")
    rider_token = await get_token(client, "rider@campus.edu", "RiderPass123!")

    order_id = await create_delivered_order(client, student_token, owner_token, rider_token)

    # 1. Customer requests refund
    res_req = await client.post(
        f"/api/v1/orders/{order_id}/refund-request",
        json={"reason": "Incorrect item delivered"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res_req.status_code == 201
    assert res_req.json()["status"] == "pending"

    # 2. Owner approves refund
    res_decide = await client.post(
        f"/api/v1/orders/{order_id}/refund-decision",
        json={"status": "approved", "decision_notes": "Verified complaint, refund issued."},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_decide.status_code == 200
    assert res_decide.json()["status"] == "refunded"
    assert res_decide.json()["payment"]["status"] == "refunded"


@pytest.mark.asyncio
async def test_restaurant_analytics(client):
    owner_token = await get_token(client, "dhaba_owner@campus.edu", "OwnerPass123!")
    res = await client.get(
        "/api/v1/orders/restaurant/analytics",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "total_orders" in data
    assert "total_revenue" in data


@pytest.mark.asyncio
async def test_customer_order_insights(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    res = await client.get(
        "/api/v1/orders/insights/summary",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "total_orders_analyzed" in data
    assert "favorite_items" in data
    assert "ai_summary" in data
    assert "personalized_recommendation" in data