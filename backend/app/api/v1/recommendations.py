from typing import Any, Dict, List
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.api.deps import CurrentUserDep, SessionDep
from backend.app.models.restaurant import MenuItem, Restaurant
from backend.app.schemas.restaurant import MenuItemResponse
from backend.app.services.ai import GeminiFoodAdvisor

router = APIRouter(prefix="/recommendations", tags=["AI Food Advisor"])


class RecommendationRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="User food preference or budget request",
    )


class RecommendationResponse(BaseModel):
    query: str
    explanation: str
    recommended_items: List[MenuItemResponse] = []


@router.post("/", response_model=RecommendationResponse)
async def recommend_food(
    request: RecommendationRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    print(f"[DEBUG 1] Authenticated as user: {current_user.email}")

    # 1. Query available menu items
    stmt = (
        select(MenuItem)
        .join(Restaurant)
        .where(
            Restaurant.is_open.is_(True),
            MenuItem.is_available.is_(True),
        )
    )
    result = await session.execute(stmt)
    available_items = result.scalars().all()
    print(f"[DEBUG 2] Fetched {len(available_items)} menu items from database")

    if not available_items:
        return RecommendationResponse(
            query=request.query,
            explanation="No menu items are currently available across open restaurants.",
            recommended_items=[],
        )

    # 2. Prepare payload
    menu_inventory: List[Dict[str, Any]] = [
        {
            "id": item.id,
            "restaurant_id": item.restaurant_id,
            "name": item.name,
            "description": item.description or "",
            "price": item.price,
            "category": item.category,
        }
        for item in available_items
    ]

    print("[DEBUG 3] Calling GeminiFoodAdvisor...")
    advisor = GeminiFoodAdvisor()
    ai_result = await advisor.get_recommendation(
        user_query=request.query,
        available_menu=menu_inventory,
    )
    print(f"[DEBUG 4] Gemini response received: {ai_result}")

    recommended_ids = set(ai_result.get("recommended_item_ids", []))
    matched_items = [
        MenuItemResponse.model_validate(item)
        for item in available_items
        if item.id in recommended_ids
    ]

    return RecommendationResponse(
        query=request.query,
        explanation=ai_result.get("explanation", "Here are your recommendations."),
        recommended_items=matched_items,
    )