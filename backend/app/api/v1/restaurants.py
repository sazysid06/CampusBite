from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import RoleChecker, SessionDep
from backend.app.models.restaurant import MenuItem, Restaurant
from backend.app.models.user import User, UserRole
from backend.app.schemas.restaurant import (
    MenuItemCreate,
    MenuItemResponse,
    RestaurantCreate,
    RestaurantDetailResponse,
    RestaurantResponse,
)

router = APIRouter(prefix="/restaurants", tags=["Restaurants & Menus"])

# Dependency alias enforcing restaurant_owner role
RestaurantOwnerDep = Annotated[User, Depends(RoleChecker([UserRole.RESTAURANT_OWNER]))]


@router.post(
    "/",
    response_model=RestaurantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_restaurant(
    restaurant_in: RestaurantCreate,
    session: SessionDep,
    current_user: RestaurantOwnerDep,
):
    """Register a new restaurant (Restricted to Restaurant Owners)."""
    restaurant = Restaurant(
        owner_id=current_user.id,
        name=restaurant_in.name,
        description=restaurant_in.description,
        address=restaurant_in.address,
        phone_number=restaurant_in.phone_number,
        is_open=restaurant_in.is_open,
    )
    session.add(restaurant)
    await session.commit()
    await session.refresh(restaurant)
    return restaurant


@router.get("/", response_model=List[RestaurantResponse])
async def list_restaurants(
    session: SessionDep,
    skip: int = 0,
    limit: int = 20,
):
    """List open and available restaurants (Public)."""
    result = await session.execute(
        select(Restaurant).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/{restaurant_id}", response_model=RestaurantDetailResponse)
async def get_restaurant_detail(restaurant_id: int, session: SessionDep):
    """Fetch restaurant details including the full menu (Public)."""
    result = await session.execute(
        select(Restaurant)
        .where(Restaurant.id == restaurant_id)
        .options(selectinload(Restaurant.menu_items))
    )
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found",
        )
    return restaurant


@router.post(
    "/{restaurant_id}/items",
    response_model=MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_menu_item(
    restaurant_id: int,
    item_in: MenuItemCreate,
    session: SessionDep,
    current_user: RestaurantOwnerDep,
):
    """Add a new item to the restaurant's menu (Restricted to the Restaurant Owner)."""
    result = await session.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found",
        )

    if restaurant.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this restaurant's menu",
        )

    menu_item = MenuItem(
        restaurant_id=restaurant.id,
        name=item_in.name,
        description=item_in.description,
        price=item_in.price,
        category=item_in.category,
        is_available=item_in.is_available,
    )
    session.add(menu_item)
    await session.commit()
    await session.refresh(menu_item)
    return menu_item