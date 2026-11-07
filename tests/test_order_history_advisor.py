from uuid import uuid4

import httpx
import pytest
from fastapi import status

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.order import Order, OrderItem, OrderStatus
from backend.app.models.restaurant import MenuItem, Restaurant
from backend.app.models.user import User, UserRole
from backend.app.services.ai.order_history_advisor import (
    OrderAdvisorError,
    answer_order_history_question,
    build_order_history_context,
)
from backend.app.services.ai import order_history_advisor as advisor_service
from backend.app.api.v1.orders import UserRequestRateLimiter
from backend.app.api.v1 import orders as orders_api


@pytest.mark.asyncio
async def test_order_advisor_sends_context_to_openai(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    captured_request = {}

    class FakeResponse:
        status_code = status.HTTP_200_OK
        headers = {}
        is_error = False

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "You ordered two meals."}}]}

    class FakeAsyncClient:
        def __init__(self, timeout):
            assert timeout.connect == 20.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url, headers, json):
            captured_request.update(url=url, headers=headers, payload=json)
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    context = build_order_history_context(
        total_orders=2,
        recent_orders=[{"order_id": 12, "status": "delivered", "items": []}],
        active_orders=[],
        spending_this_week=250,
        most_ordered_items=[{"name": "Dosa", "quantity": 2}],
    )
    answer = await answer_order_history_question("Summarize my last five orders.", context)

    assert answer == ("You ordered two meals.", "openai")
    assert captured_request["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured_request["headers"]["Authorization"] == "Bearer test-key"
    assert captured_request["payload"]["messages"][1]["content"].find('"order_id": 12') >= 0


@pytest.mark.asyncio
async def test_order_advisor_reports_missing_openai_key(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    with pytest.raises(OrderAdvisorError) as error:
        await answer_order_history_question("How much did I spend?", {})

    assert error.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_order_advisor_maps_openai_rate_limit(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")

    class FakeResponse:
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
        headers = {"Retry-After": "17"}
        is_error = True

    class FakeAsyncClient:
        def __init__(self, timeout):
            assert timeout.connect == 20.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url, headers, json):
            assert url == "https://api.openai.com/v1/chat/completions"
            assert headers["Authorization"] == "Bearer test-key"
            assert json["messages"]
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(OrderAdvisorError) as error:
        await answer_order_history_question("Which meals do I order?", {})

    assert error.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert error.value.retry_after == "17"


@pytest.mark.asyncio
async def test_order_advisor_uses_gemini_when_openai_is_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")
    captured_request = {}

    class FakeModels:
        async def generate_content(self, model, contents, config):
            captured_request.update(model=model, contents=contents, config=config)
            return type("Response", (), {"text": "You ordered two meals."})()

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-gemini-key"
            self.aio = type("Async", (), {"models": FakeModels()})()

    monkeypatch.setattr(advisor_service.genai, "Client", FakeClient)
    answer = await answer_order_history_question(
        "Summarize my last five orders.",
        {"recent_orders": [{"order_id": 12}]},
    )

    assert answer == ("You ordered two meals.", "gemini")
    assert captured_request["model"] == settings.GEMINI_MODEL
    assert "order_id" in captured_request["contents"]
    assert "Summarize my last five orders." in captured_request["contents"]


@pytest.mark.asyncio
async def test_advisor_limits_requests_per_customer():
    limiter = UserRequestRateLimiter(limit=2, window_seconds=60)

    assert await limiter.check(101) is None
    assert await limiter.check(101) is None
    assert await limiter.check(101) is not None
    assert await limiter.check(202) is None


@pytest.mark.asyncio
async def test_order_advisor_rejects_non_customer_role(client):
    owner = User(id=90210, email="owner@example.test", role=UserRole.RESTAURANT_OWNER)
    app.dependency_overrides[get_current_user] = lambda: owner

    try:
        response = await client.post(
            "/api/v1/orders/advisor",
            json={"question": "Summarize my recent orders."},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_order_advisor_context_contains_only_authenticated_customers_orders(
    client,
    monkeypatch,
):
    identifier = uuid4().hex[:12]
    async with AsyncSessionLocal() as session:
        owner = User(
            email=f"advisor-owner-{identifier}@example.test",
            hashed_password="unused",
            full_name="Advisor Owner",
            phone_number=f"91{identifier[:10]}",
            role=UserRole.RESTAURANT_OWNER,
        )
        customer = User(
            email=f"advisor-customer-{identifier}@example.test",
            hashed_password="unused",
            full_name="Advisor Customer",
            phone_number=f"92{identifier[:10]}",
            role=UserRole.CUSTOMER,
        )
        other_customer = User(
            email=f"advisor-other-{identifier}@example.test",
            hashed_password="unused",
            full_name="Other Customer",
            phone_number=f"93{identifier[:10]}",
            role=UserRole.CUSTOMER,
        )
        session.add_all([owner, customer, other_customer])
        await session.flush()

        restaurant = Restaurant(
            owner_id=owner.id,
            name="Advisor Test Kitchen",
            address="100 Test Campus Road",
            phone_number=f"94{identifier[:10]}",
        )
        session.add(restaurant)
        await session.flush()
        menu_item = MenuItem(
            restaurant_id=restaurant.id,
            name="Private History Dish",
            price=125,
            category="Test",
        )
        session.add(menu_item)
        await session.flush()

        own_order = Order(
            customer_id=customer.id,
            restaurant_id=restaurant.id,
            total_amount=125,
            status=OrderStatus.DELIVERED,
            delivery_address="Customer address not sent to AI",
            items=[OrderItem(menu_item_id=menu_item.id, quantity=1, unit_price=125)],
        )
        other_order = Order(
            customer_id=other_customer.id,
            restaurant_id=restaurant.id,
            total_amount=250,
            status=OrderStatus.DELIVERED,
            delivery_address="Other customer's private address",
            items=[OrderItem(menu_item_id=menu_item.id, quantity=2, unit_price=125)],
        )
        session.add_all([own_order, other_order])
        await session.commit()
        customer_id = customer.id
        own_order_id = own_order.id

    captured_context = {}

    async def fake_answer(_question, context):
        captured_context["question"] = _question
        captured_context.update(context)
        return "Your order history was checked.", "openai"

    monkeypatch.setattr(orders_api, "answer_order_history_question", fake_answer)
    app.dependency_overrides[get_current_user] = lambda: User(
        id=customer_id,
        email=f"advisor-customer-{identifier}@example.test",
        role=UserRole.CUSTOMER,
    )

    try:
        response = await client.post(
            "/api/v1/orders/advisor",
            json={"question": "Summarize my last five orders."},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total_orders"] == 1
    assert captured_context["recent_orders"][0]["order_id"] == own_order_id
    assert captured_context["question"] == "Summarize my last five orders."
    assert captured_context["most_ordered_items_all_time"] == [
        {"name": "Private History Dish", "quantity": 1}
    ]
    assert "delivery_address" not in str(captured_context)
    assert "Other customer's private address" not in str(captured_context)
