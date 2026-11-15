import asyncio

import pytest

from backend.app.api.deps import get_current_user
from backend.app.api.v1 import recommendations as recommendations_api
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.user import User, UserRole
from backend.app.services.ai import advisor


@pytest.mark.asyncio
async def test_food_advisor_returns_configuration_message_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    result = await advisor.GeminiFoodAdvisor().get_recommendation(
        "Something vegetarian",
        [{"id": 1, "name": "Dosa"}],
    )

    assert result == {
        "recommended_item_ids": [],
        "explanation": "Gemini API key is not configured.",
    }


@pytest.mark.asyncio
async def test_food_advisor_sends_menu_and_returns_gemini_json(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    captured = {}
    menu = [{"id": 1, "name": "Dosa"}]

    class FakeModels:
        async def generate_content(self, model, contents, config):
            captured.update(model=model, contents=contents, config=config)
            return type(
                "Response",
                (),
                {"text": '{"recommended_item_ids":[1],"explanation":"A tasty fit."}'},
            )()

    class FakeClient:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.aio = type("Async", (), {"models": FakeModels()})()

    monkeypatch.setattr(advisor.genai, "Client", FakeClient)
    result = await advisor.GeminiFoodAdvisor().get_recommendation(
        "Something vegetarian",
        menu,
    )

    assert result == {
        "recommended_item_ids": [1],
        "explanation": "A tasty fit.",
    }
    assert captured["api_key"] == "test-key"
    assert captured["model"] == settings.GEMINI_MODEL
    assert "Something vegetarian" in captured["contents"]
    assert '"name": "Dosa"' in captured["contents"]
    assert captured["config"].response_mime_type == "application/json"
    assert captured["config"].temperature == 0.2


@pytest.mark.asyncio
async def test_food_advisor_returns_unavailable_result_on_timeout(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    menu = [{"id": 1}, {"id": 2}, {"id": 3}]

    class FakeModels:
        async def generate_content(self, **_kwargs):
            return None

    class FakeClient:
        def __init__(self, api_key):
            self.aio = type("Async", (), {"models": FakeModels()})()

    async def timeout(awaitable, timeout):
        assert timeout == 15.0
        awaitable.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(advisor.genai, "Client", FakeClient)
    monkeypatch.setattr(advisor.asyncio, "wait_for", timeout)

    result = await advisor.GeminiFoodAdvisor().get_recommendation("Anything", menu)

    assert result == {
        "recommended_item_ids": [],
        "explanation": advisor._UNAVAILABLE_EXPLANATION,
    }


@pytest.mark.asyncio
async def test_food_advisor_returns_unavailable_result_for_invalid_json(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    class FakeModels:
        async def generate_content(self, **_kwargs):
            return type("Response", (), {"text": "not valid JSON"})()

    class FakeClient:
        def __init__(self, api_key):
            self.aio = type("Async", (), {"models": FakeModels()})()

    monkeypatch.setattr(advisor.genai, "Client", FakeClient)

    result = await advisor.GeminiFoodAdvisor().get_recommendation(
        "Anything",
        [{"id": 7}],
    )

    assert result == {
        "recommended_item_ids": [],
        "explanation": advisor._UNAVAILABLE_EXPLANATION,
    }


@pytest.mark.asyncio
async def test_food_advisor_returns_unavailable_result_for_invalid_schema(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    class FakeModels:
        async def generate_content(self, **_kwargs):
            return type(
                "Response",
                (),
                {"text": '{"recommended_item_ids":["7"],"explanation":"A tasty fit."}'},
            )()

    class FakeClient:
        def __init__(self, api_key):
            self.aio = type("Async", (), {"models": FakeModels()})()

    monkeypatch.setattr(advisor.genai, "Client", FakeClient)

    result = await advisor.GeminiFoodAdvisor().get_recommendation(
        "Anything",
        [{"id": 7}],
    )

    assert result == {
        "recommended_item_ids": [],
        "explanation": advisor._UNAVAILABLE_EXPLANATION,
    }


@pytest.mark.asyncio
async def test_food_advisor_returns_unavailable_result_on_gemini_api_error(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    class FakeModels:
        async def generate_content(self, **_kwargs):
            raise advisor.genai_errors.APIError(
                code=503,
                response_json={
                    "error": {
                        "code": 503,
                        "status": "UNAVAILABLE",
                        "message": "provider failure",
                    }
                },
            )

    class FakeClient:
        def __init__(self, api_key):
            self.aio = type("Async", (), {"models": FakeModels()})()

    monkeypatch.setattr(advisor.genai, "Client", FakeClient)

    result = await advisor.GeminiFoodAdvisor().get_recommendation("Anything", [])

    assert result == {
        "recommended_item_ids": [],
        "explanation": advisor._UNAVAILABLE_EXPLANATION,
    }


@pytest.mark.asyncio
async def test_food_advisor_does_not_hide_unexpected_errors(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    class FakeModels:
        async def generate_content(self, **_kwargs):
            raise RuntimeError("unexpected programming error")

    class FakeClient:
        def __init__(self, api_key):
            self.aio = type("Async", (), {"models": FakeModels()})()

    monkeypatch.setattr(advisor.genai, "Client", FakeClient)

    with pytest.raises(RuntimeError, match="unexpected programming error"):
        await advisor.GeminiFoodAdvisor().get_recommendation("Anything", [])


@pytest.mark.asyncio
async def test_recommendations_api_passes_menu_to_advisor_and_returns_match(
    client,
    monkeypatch,
):
    captured = {}

    async def fake_recommendation(self, user_query, available_menu):
        captured["query"] = user_query
        captured["menu"] = available_menu
        return {
            "recommended_item_ids": [available_menu[1]["id"]],
            "explanation": "A suitable option from the available menu.",
        }

    monkeypatch.setattr(
        recommendations_api.GeminiFoodAdvisor,
        "get_recommendation",
        fake_recommendation,
    )
    app.dependency_overrides[get_current_user] = lambda: User(
        id=987654,
        email="recommendations-test@example.test",
        role=UserRole.CUSTOMER,
    )

    try:
        response = await client.post(
            "/api/v1/recommendations/",
            json={"query": "A vegetarian meal"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert captured["query"] == "A vegetarian meal"
    assert len(captured["menu"]) > 1
    assert response.json()["explanation"] == "A suitable option from the available menu."
    assert response.json()["recommended_items"][0]["id"] == captured["menu"][1]["id"]
