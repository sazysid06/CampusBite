from datetime import datetime, timezone
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import CurrentUserDep, RoleChecker, SessionDep
from backend.app.models.order import (
    Delivery,
    DeliveryStatus,
    Order,
    OrderItem,
    OrderStatus,
)
from backend.app.models.restaurant import MenuItem, Restaurant
from backend.app.models.user import User, UserRole
from backend.app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
)

router = APIRouter(prefix="/orders", tags=["Orders & Delivery"])

CustomerDep = Annotated[User, Depends(RoleChecker([UserRole.CUSTOMER]))]


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreate,
    session: SessionDep,
    current_user: CustomerDep,
):
    """Place a new order with atomic price calculation and initial delivery creation."""
    # 1. Verify restaurant existence and operational status
    res = await session.execute(
        select(Restaurant).where(Restaurant.id == order_in.restaurant_id)
    )
    restaurant = res.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found",
        )
    if not restaurant.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant is currently closed for new orders",
        )

    # 2. Extract item IDs and fetch from database
    item_ids = [i.menu_item_id for i in order_in.items]
    items_query = await session.execute(
        select(MenuItem).where(
            MenuItem.id.in_(item_ids),
            MenuItem.restaurant_id == restaurant.id,
        )
    )
    db_items = {item.id: item for item in items_query.scalars().all()}

    if len(db_items) != len(set(item_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more items are invalid or do not belong to this restaurant",
        )

    # 3. Calculate total amount server-side and build order item records
    total_amount = 0.0
    order_items: List[OrderItem] = []

    for item_in in order_in.items:
        db_item = db_items[item_in.menu_item_id]
        if not db_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item '{db_item.name}' is currently unavailable",
            )
        line_total = db_item.price * item_in.quantity
        total_amount += line_total

        order_items.append(
            OrderItem(
                menu_item_id=db_item.id,
                quantity=item_in.quantity,
                unit_price=db_item.price,
            )
        )

    # 4. Construct Order and attach Delivery record
    order = Order(
        customer_id=current_user.id,
        restaurant_id=restaurant.id,
        total_amount=round(total_amount, 2),
        status=OrderStatus.PENDING,
        delivery_address=order_in.delivery_address,
        special_instructions=order_in.special_instructions,
        items=order_items,
        delivery=Delivery(status=DeliveryStatus.UNASSIGNED),
    )

    session.add(order)
    await session.commit()

    # Re-fetch with eager loaded relationships for response schema
    result = await session.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(
            selectinload(Order.items),
            selectinload(Order.delivery),
        )
    )
    return result.scalar_one()


@router.get("/me", response_model=List[OrderResponse])
async def get_my_orders(
    session: SessionDep,
    current_user: CurrentUserDep,
):
    """Retrieve orders relevant to the authenticated user."""
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.delivery),
        )
        .order_by(Order.created_at.desc())
    )

    if current_user.role == UserRole.CUSTOMER:
        stmt = stmt.where(Order.customer_id == current_user.id)
    elif current_user.role == UserRole.RESTAURANT_OWNER:
        stmt = stmt.join(Restaurant).where(Restaurant.owner_id == current_user.id)
    elif current_user.role == UserRole.DELIVERY_PARTNER:
        stmt = stmt.join(Delivery).where(
            Delivery.delivery_partner_id == current_user.id
        )

    res = await session.execute(stmt)
    return res.scalars().all()


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    """Update order lifecycle status and synchronize delivery tracking."""
    res = await session.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items),
            selectinload(Order.delivery),
            selectinload(Order.restaurant),
        )
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # 1. Permission checks based on actor role
    if current_user.role == UserRole.RESTAURANT_OWNER:
        if order.restaurant.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update orders for this restaurant",
            )
        allowed_owner_statuses = [
            OrderStatus.CONFIRMED,
            OrderStatus.PREPARING,
            OrderStatus.CANCELLED,
        ]
        if status_in.status not in allowed_owner_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Restaurant owners can only transition to: {[s.value for s in allowed_owner_statuses]}",
            )

    elif current_user.role == UserRole.DELIVERY_PARTNER:
        allowed_rider_statuses = [
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.DELIVERED,
        ]
        if status_in.status not in allowed_rider_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Delivery partners can only transition to: {[s.value for s in allowed_rider_statuses]}",
            )

    elif current_user.role == UserRole.CUSTOMER:
        if order.customer_id != current_user.id or status_in.status != OrderStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers can only cancel their own pending orders",
            )
        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel order once preparation has started",
            )

    # 2. Update order status
    order.status = status_in.status

    # 3. Synchronize delivery entity if present
    delivery = order.delivery
    if delivery:
        now = datetime.now(timezone.utc)
        if current_user.role == UserRole.DELIVERY_PARTNER:
            if not delivery.delivery_partner_id:
                delivery.delivery_partner_id = current_user.id
                delivery.status = DeliveryStatus.ASSIGNED

        if status_in.status == OrderStatus.OUT_FOR_DELIVERY:
            delivery.status = DeliveryStatus.PICKED_UP
            if not delivery.pickup_time:
                delivery.pickup_time = now

        elif status_in.status == OrderStatus.DELIVERED:
            delivery.status = DeliveryStatus.COMPLETED
            if not delivery.delivered_time:
                delivery.delivered_time = now

    await session.commit()
    await session.refresh(order)
    return order
