import pytest
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.order import Order, OrderStatus
from backend.app.models.restaurant import Restaurant
from backend.app.models.user import User


async def get_token(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


async def create_delivered_order(client, student_token: str, owner_token: str, rider_token: str) -> int:
    student_headers = {"Authorization": f"Bearer {student_token}"}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    rider_headers = {"Authorization": f"Bearer {rider_token}"}
    availability = await client.patch(
        "/api/v1/orders/rider/availability",
        json={"is_available": True},
        headers=rider_headers,
    )
    assert availability.status_code == 200

    response = await client.post(
        "/api/v1/orders/",
        json={
            "restaurant_id": 1,
            "delivery_address": "Hostel C Room 101",
            "items": [{"menu_item_id": 1, "quantity": 1}],
        },
        headers=student_headers,
    )
    assert response.status_code == 201
    order_id = response.json()["id"]

    accepted = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers=owner_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["delivery"]["delivery_partner_id"] is not None
    at_restaurant = await client.patch(
        f"/api/v1/orders/{order_id}/delivery-status",
        json={"status": "at_restaurant"},
        headers=rider_headers,
    )
    assert at_restaurant.status_code == 200
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
    assert delivered.status_code == 200, delivered.text
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
    assert res_decide.json()["refund_request"]["status"] == "approved"

    duplicate = await client.post(
        f"/api/v1/orders/{order_id}/refund-request",
        json={"reason": "Another refund request"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert duplicate.status_code == 400


@pytest.mark.asyncio
async def test_refund_validation_and_rejection(client):
    student_token = await get_token(client, "student@campus.edu", "StudentPass123!")
    owner_token = await get_token(client, "dhaba_owner@campus.edu", "OwnerPass123!")
    rider_token = await get_token(client, "rider@campus.edu", "RiderPass123!")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    placed = await client.post(
        "/api/v1/orders/",
        json={
            "restaurant_id": 1,
            "delivery_address": "Hostel C Room 101",
            "items": [{"menu_item_id": 1, "quantity": 1}],
        },
        headers=student_headers,
    )
    assert placed.status_code == 201
    payment = placed.json()["payment"]
    assert payment["status"] == "mock_paid"
    assert payment["transaction_reference"].startswith("MOCK_TXN_")

    before_delivery = await client.post(
        f"/api/v1/orders/{placed.json()['id']}/refund-request",
        json={"reason": "Not delivered yet"},
        headers=student_headers,
    )
    assert before_delivery.status_code == 400

    order_id = await create_delivered_order(client, student_token, owner_token, rider_token)
    missing_reason = await client.post(
        f"/api/v1/orders/{order_id}/refund-request",
        json={},
        headers=student_headers,
    )
    assert missing_reason.status_code == 422

    short_reason = await client.post(
        f"/api/v1/orders/{order_id}/refund-request",
        json={"reason": "  "},
        headers=student_headers,
    )
    assert short_reason.status_code == 422

    request = await client.post(
        f"/api/v1/orders/{order_id}/refund-request",
        json={"reason": "Incorrect item delivered"},
        headers=student_headers,
    )
    assert request.status_code == 201
    assert request.json()["status"] == "pending"

    invalid_decision = await client.post(
        f"/api/v1/orders/{order_id}/refund-decision",
        json={"status": "pending"},
        headers=owner_headers,
    )
    assert invalid_decision.status_code == 422

    rejected = await client.post(
        f"/api/v1/orders/{order_id}/refund-decision",
        json={"status": "rejected", "decision_notes": "The order matches the receipt."},
        headers=owner_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "delivered"
    assert rejected.json()["payment"]["status"] == "mock_paid"
    assert rejected.json()["refund_request"]["status"] == "rejected"

    duplicate = await client.post(
        f"/api/v1/orders/{order_id}/refund-request",
        json={"reason": "Trying again after rejection"},
        headers=student_headers,
    )
    assert duplicate.status_code == 400

    second_decision = await client.post(
        f"/api/v1/orders/{order_id}/refund-decision",
        json={"status": "approved"},
        headers=owner_headers,
    )
    assert second_decision.status_code == 400


@pytest.mark.asyncio
async def test_restaurant_analytics(client):
    owner_token = await get_token(client, "dhaba_owner@campus.edu", "OwnerPass123!")
    headers = {"Authorization": f"Bearer {owner_token}"}
    baseline_res = await client.get(
        "/api/v1/orders/restaurant/analytics",
        headers=headers,
    )
    assert baseline_res.status_code == 200
    baseline = baseline_res.json()

    async with AsyncSessionLocal() as session:
        owner = await session.scalar(
            select(User).where(User.email == "dhaba_owner@campus.edu")
        )
        restaurant = await session.scalar(
            select(Restaurant).where(Restaurant.owner_id == owner.id)
        )
        customer = await session.scalar(
            select(User).where(User.email == "student@campus.edu")
        )
        session.add_all(
            [
                Order(
                    customer_id=customer.id,
                    restaurant_id=restaurant.id,
                    total_amount=amount,
                    status=order_status,
                    delivery_address="Campus Block A",
                )
                for amount, order_status in [
                    (25.25, OrderStatus.DELIVERED),
                    (37.50, OrderStatus.DELIVERED),
                    (12.00, OrderStatus.CANCELLED),
                    (18.00, OrderStatus.REFUNDED),
                    (22.00, OrderStatus.PLACED),
                ]
            ]
        )
        await session.commit()

    res = await client.get("/api/v1/orders/restaurant/analytics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_orders" in data
    assert "total_revenue" in data
    assert data["total_orders"] == baseline["total_orders"] + 5
    assert data["completed_orders"] == baseline["completed_orders"] + 2
    assert data["cancelled_orders"] == baseline["cancelled_orders"] + 1
    assert data["refunded_orders"] == baseline["refunded_orders"] + 1
    assert data["total_revenue"] == pytest.approx(baseline["total_revenue"] + 62.75)


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