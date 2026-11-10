import asyncio
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google import genai
from pydantic import BaseModel, Field
from sqlalchemy import case, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from backend.app.api.deps import CurrentUserDep, RoleChecker, SessionDep
from backend.app.core.config import settings
from backend.app.models.order import (
    Delivery,
    DeliveryStatus,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    RefundRequest,
    RefundStatus,
    Review,
)
from backend.app.models.restaurant import MenuItem, Restaurant
from backend.app.models.rider import RiderAvailability
from backend.app.models.user import User, UserRole
from backend.app.schemas.order import (
    CustomerOrderInsights,
    DeliveryStatusUpdate,
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    RefundDecisionUpdate,
    RefundRequestCreate,
    RefundRequestResponse,
    RestaurantStatsResponse,
    ReviewCreate,
    ReviewResponse,
    RiderAvailabilityResponse,
    RiderAvailabilityUpdate,
    StaleOrderReminderResponse,
)
from backend.app.services.ai.order_history_advisor import (
    OrderAdvisorError,
    answer_order_history_question,
    build_order_history_context,
)

router = APIRouter(prefix="/orders", tags=["Orders & Delivery"])

CustomerDep = Annotated[User, Depends(RoleChecker([UserRole.CUSTOMER]))]
OwnerDep = Annotated[User, Depends(RoleChecker([UserRole.RESTAURANT_OWNER]))]
RiderDep = Annotated[User, Depends(RoleChecker([UserRole.DELIVERY_PARTNER]))]

ORDER_HISTORY_LIMIT = 50
ADVISOR_REQUESTS_PER_MINUTE = 10


class OrderAdvisorRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class OrderAdvisorResponse(BaseModel):
    answer: str
    provider: str
    total_orders: int
    recent_orders_included: int


class UserRequestRateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: dict[int, list[float]] = {}
        self.lock = asyncio.Lock()

    async def check(self, user_id: int) -> int | None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self.lock:
            for existing_user_id, timestamps in list(self.requests.items()):
                active = [timestamp for timestamp in timestamps if timestamp > cutoff]
                if active:
                    self.requests[existing_user_id] = active
                else:
                    self.requests.pop(existing_user_id, None)

            timestamps = self.requests.setdefault(user_id, [])
            if len(timestamps) >= self.limit:
                return max(1, int(self.window_seconds - (now - timestamps[0])))
            timestamps.append(now)
        return None


advisor_rate_limiter = UserRequestRateLimiter(
    limit=ADVISOR_REQUESTS_PER_MINUTE,
    window_seconds=60,
)


def _order_summary(order: Order) -> dict:
    created_at = order.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return {
        "order_id": order.id,
        "restaurant": order.restaurant.name if order.restaurant else "Unknown restaurant",
        "status": order.status.value,
        "created_at": created_at.isoformat(),
        "total_inr": round(order.total_amount, 2),
        "items": [
            {
                "name": item.menu_item.name if item.menu_item else f"Item #{item.menu_item_id}",
                "quantity": item.quantity,
                "unit_price_inr": round(item.unit_price, 2),
            }
            for item in order.items
        ],
    }


@router.post("/advisor", response_model=OrderAdvisorResponse)
async def ask_order_history_advisor(
    request: OrderAdvisorRequest,
    session: SessionDep,
    current_user: CustomerDep,
):
    retry_after = await advisor_rate_limiter.check(current_user.id)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You have reached the order-advisor request limit. Please try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )

    customer_filter = Order.customer_id == current_user.id
    excluded_statuses = [
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    ]
    order_options = (
        selectinload(Order.items).selectinload(OrderItem.menu_item),
        selectinload(Order.restaurant),
    )

    total_orders_result = await session.execute(
        select(func.count(Order.id)).where(customer_filter)
    )
    total_orders = total_orders_result.scalar_one()

    recent_orders_result = await session.execute(
        select(Order)
        .where(customer_filter)
        .options(*order_options)
        .order_by(desc(Order.created_at))
        .limit(ORDER_HISTORY_LIMIT)
    )
    recent_orders = recent_orders_result.scalars().all()

    active_orders_result = await session.execute(
        select(Order)
        .where(
            customer_filter,
            Order.status.not_in(
                [OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.REFUNDED]
            ),
        )
        .options(*order_options)
        .order_by(desc(Order.created_at))
        .limit(ORDER_HISTORY_LIMIT)
    )
    active_orders = active_orders_result.scalars().all()

    now = datetime.now(timezone.utc)
    week_start = datetime(
        now.year, now.month, now.day, tzinfo=timezone.utc
    ) - timedelta(days=now.weekday())
    weekly_spending_result = await session.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0.0)).where(
            customer_filter,
            Order.created_at >= week_start,
            Order.status.not_in(excluded_statuses),
        )
    )
    spending_this_week = float(weekly_spending_result.scalar_one())

    popular_items_result = await session.execute(
        select(
            MenuItem.name,
            func.sum(OrderItem.quantity).label("quantity"),
        )
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(customer_filter, Order.status.not_in(excluded_statuses))
        .group_by(MenuItem.id, MenuItem.name)
        .order_by(desc("quantity"), MenuItem.name)
        .limit(10)
    )
    popular_items = [
        {"name": name, "quantity": quantity}
        for name, quantity in popular_items_result.all()
    ]

    context = build_order_history_context(
        total_orders=total_orders,
        recent_orders=[_order_summary(order) for order in recent_orders],
        active_orders=[_order_summary(order) for order in active_orders],
        spending_this_week=spending_this_week,
        most_ordered_items=popular_items,
    )

    try:
        answer, provider = await answer_order_history_question(request.question, context)
    except OrderAdvisorError as error:
        headers = {"Retry-After": error.retry_after} if error.retry_after else None
        raise HTTPException(
            status_code=error.status_code,
            detail=str(error),
            headers=headers,
        ) from error

    return OrderAdvisorResponse(
        answer=answer,
        provider=provider,
        total_orders=total_orders,
        recent_orders_included=len(recent_orders),
    )


def order_eager_options():
    return (
        selectinload(Order.items).selectinload(OrderItem.menu_item),
        selectinload(Order.delivery),
        selectinload(Order.payment),
        selectinload(Order.refund_request),
        selectinload(Order.review),
        selectinload(Order.restaurant),
    )


async def assign_available_rider(session, order: Order) -> bool:
    if not order.delivery:
        order.delivery = Delivery(status=DeliveryStatus.UNASSIGNED)
        await session.flush()
    if order.delivery.delivery_partner_id is not None:
        return True

    candidates_result = await session.execute(
        select(RiderAvailability)
        .join(User, User.id == RiderAvailability.user_id)
        .where(
            RiderAvailability.is_available.is_(True),
            User.role == UserRole.DELIVERY_PARTNER,
            User.is_active.is_(True),
        )
    )
    candidates = list(candidates_result.scalars().all())
    random.shuffle(candidates)

    for candidate in candidates:
        claimed = await session.execute(
            update(RiderAvailability)
            .where(
                RiderAvailability.user_id == candidate.user_id,
                RiderAvailability.is_available.is_(True),
            )
            .values(is_available=False)
        )
        if claimed.rowcount != 1:
            continue

        order.delivery.delivery_partner_id = candidate.user_id
        order.delivery.status = DeliveryStatus.ON_THE_WAY_TO_RESTAURANT
        await session.flush()
        return True
    return False


async def assign_waiting_order(session, rider: RiderAvailability) -> None:
    waiting_result = await session.execute(
        select(Order)
        .join(Delivery, Delivery.order_id == Order.id)
        .options(selectinload(Order.delivery))
        .where(
            Order.status.in_(
                [OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY]
            ),
            Delivery.delivery_partner_id.is_(None),
            Delivery.status == DeliveryStatus.UNASSIGNED,
        )
        .order_by(Order.created_at)
        .limit(1)
    )
    waiting_order = waiting_result.scalar_one_or_none()
    if waiting_order is None:
        return

    rider.is_available = False
    waiting_order.delivery.delivery_partner_id = rider.user_id
    waiting_order.delivery.status = DeliveryStatus.ON_THE_WAY_TO_RESTAURANT


# ==========================================
# 1. Customer: Order Creation & Mock Payment
# ==========================================
@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreate,
    session: SessionDep,
    current_user: CustomerDep,
):
    """Place a new order, calculate totals atomically, and issue dummy payment."""
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

    rounded_total = round(total_amount, 2)
    tx_ref = f"MOCK_TXN_{uuid.uuid4().hex[:12].upper()}"

    order = Order(
        customer_id=current_user.id,
        restaurant_id=restaurant.id,
        total_amount=rounded_total,
        status=OrderStatus.PLACED,
        delivery_address=order_in.delivery_address,
        special_instructions=order_in.special_instructions,
        items=order_items,
        delivery=Delivery(status=DeliveryStatus.UNASSIGNED),
        payment=Payment(
            amount=rounded_total,
            status=PaymentStatus.MOCK_PAID,
            transaction_reference=tx_ref,
        ),
    )

    session.add(order)
    await session.commit()

    result = await session.execute(
        select(Order).where(Order.id == order.id).options(*order_eager_options())
    )
    return result.scalar_one()


# ==========================================
# 2. Universal & Role-Based Order Queries
# ==========================================
@router.get("/me", response_model=List[OrderResponse])
async def get_my_orders(
    session: SessionDep,
    current_user: CurrentUserDep,
    status_filter: Optional[OrderStatus] = Query(None, description="Filter by Order status"),
):
    """Retrieve orders relevant to the authenticated user with optional status filter."""
    stmt = (
        select(Order)
        .options(*order_eager_options())
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

    if status_filter:
        stmt = stmt.where(Order.status == status_filter)

    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/insights/summary", response_model=CustomerOrderInsights)
async def get_customer_order_insights(
    session: SessionDep,
    current_user: CustomerDep,
):
    """Aggregate customer order history and generate AI-powered dietary and spending insights."""
    stmt = (
        select(Order)
        .options(*order_eager_options())
        .where(Order.customer_id == current_user.id)
        .order_by(Order.created_at.desc())
    )
    res = await session.execute(stmt)
    orders = res.scalars().all()

    if not orders:
        return CustomerOrderInsights(
            customer_id=current_user.id,
            total_orders_analyzed=0,
            total_spent=0.0,
            favorite_items=[],
            ai_summary="No orders placed yet. Place your first order to get personalized recommendations!",
            personalized_recommendation="Explore campus favorites and signature dishes to get started.",
        )

    total_spent = round(sum(o.total_amount for o in orders if o.status == OrderStatus.DELIVERED), 2)
    item_counts: dict[str, int] = {}

    for o in orders:
        for item in o.items:
            name = item.menu_item.name if item.menu_item else f"Item #{item.menu_item_id}"
            item_counts[name] = item_counts.get(name, 0) + item.quantity

    top_items = sorted(item_counts.keys(), key=lambda k: item_counts[k], reverse=True)[:3]

    ai_summary = "Regular campus diner enjoying consistent local favorites."
    ai_rec = "Consider exploring vegetarian thali combinations and lighter dining options."

    try:
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if api_key:
            client = genai.Client(api_key=api_key)
            prompt = (
                f"Analyze this campus student's dining profile:\n"
                f"- Total delivered spending: INR {total_spent}\n"
                f"- Order count: {len(orders)}\n"
                f"- Top items: {', '.join(top_items)}\n"
                f"Respond with exactly two lines: Line 1 = short eating habits summary. Line 2 = specific meal recommendation."
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response.text:
                lines = [line.strip() for line in response.text.split("\n") if line.strip()]
                if len(lines) >= 2:
                    ai_summary = lines[0]
                    ai_rec = lines[1]
                else:
                    ai_summary = response.text.strip()
    except Exception:
        pass

    return CustomerOrderInsights(
        customer_id=current_user.id,
        total_orders_analyzed=len(orders),
        total_spent=total_spent,
        favorite_items=top_items,
        ai_summary=ai_summary,
        personalized_recommendation=ai_rec,
    )


@router.get("/restaurant/analytics", response_model=RestaurantStatsResponse)
async def get_restaurant_stats(
    session: SessionDep,
    current_user: OwnerDep,
):
    """Aggregate restaurant performance, orders, and total revenue."""
    stats_res = await session.execute(
        select(
            Restaurant.id.label("restaurant_id"),
            func.count(Order.id).label("total_orders"),
            func.coalesce(
                func.sum(case((Order.status == OrderStatus.DELIVERED, 1), else_=0)),
                0,
            ).label("completed_orders"),
            func.coalesce(
                func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)),
                0,
            ).label("cancelled_orders"),
            func.coalesce(
                func.sum(case((Order.status == OrderStatus.REFUNDED, 1), else_=0)),
                0,
            ).label("refunded_orders"),
            func.coalesce(
                func.sum(
                    case(
                        (Order.status == OrderStatus.DELIVERED, Order.total_amount),
                        else_=0,
                    )
                ),
                0.0,
            ).label("total_revenue"),
        )
        .outerjoin(Order, Order.restaurant_id == Restaurant.id)
        .where(Restaurant.owner_id == current_user.id)
        .group_by(Restaurant.id)
    )
    stats = stats_res.one_or_none()
    if stats is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No restaurant found for current owner")

    return RestaurantStatsResponse(
        restaurant_id=stats.restaurant_id,
        total_orders=stats.total_orders,
        total_revenue=round(stats.total_revenue, 2),
        completed_orders=stats.completed_orders,
        cancelled_orders=stats.cancelled_orders,
        refunded_orders=stats.refunded_orders,
    )


@router.get("/stale-reminders", response_model=List[StaleOrderReminderResponse])
async def get_stale_order_reminders(
    session: SessionDep,
    current_user: OwnerDep,
    threshold_minutes: int = Query(15, ge=5, le=120, description="Inactivity threshold in minutes"),
):
    """Retrieve active orders pending progress that have stalled past the threshold."""
    rest_res = await session.execute(
        select(Restaurant).where(Restaurant.owner_id == current_user.id)
    )
    restaurant = rest_res.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No restaurant found for current owner")

    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    active_statuses = [
        OrderStatus.PLACED,
        OrderStatus.ACCEPTED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ]

    stmt = (
        select(Order)
        .where(
            Order.restaurant_id == restaurant.id,
            Order.status.in_(active_statuses),
            Order.updated_at <= cutoff_time,
        )
        .order_by(Order.updated_at.asc())
    )
    res = await session.execute(stmt)
    stale_orders = res.scalars().all()

    reminders = []
    now = datetime.now(timezone.utc)
    for o in stale_orders:
        # Normalize updated_at to UTC aware if SQLite returned a naive datetime
        updated_at = o.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        
        diff_mins = max(0, int((now - updated_at).total_seconds() // 60))
        reminders.append(
            StaleOrderReminderResponse(
                order_id=o.id,
                status=o.status,
                last_updated=updated_at,
                minutes_elapsed=diff_mins,
                warning=f"Order #{o.id} has been in '{o.status.value}' for {diff_mins} minutes without updates.",
            )
        )
    return reminders


@router.get("/rider/availability", response_model=RiderAvailabilityResponse)
async def get_rider_availability(
    session: SessionDep,
    current_user: RiderDep,
):
    result = await session.execute(
        select(RiderAvailability).where(
            RiderAvailability.user_id == current_user.id
        )
    )
    availability = result.scalar_one_or_none()
    return RiderAvailabilityResponse(
        is_available=availability.is_available if availability else False
    )


@router.patch("/rider/availability", response_model=RiderAvailabilityResponse)
async def set_rider_availability(
    payload: RiderAvailabilityUpdate,
    session: SessionDep,
    current_user: RiderDep,
):
    result = await session.execute(
        select(RiderAvailability).where(
            RiderAvailability.user_id == current_user.id
        )
    )
    availability = result.scalar_one_or_none()

    active_delivery = await session.execute(
        select(Delivery.id).where(
            Delivery.delivery_partner_id == current_user.id,
            Delivery.status.not_in(
                [DeliveryStatus.COMPLETED, DeliveryStatus.FAILED]
            ),
        ).limit(1)
    )
    if active_delivery.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete your active delivery before changing availability",
        )

    if availability is None:
        availability = RiderAvailability(
            user_id=current_user.id,
            is_available=payload.is_available,
        )
        session.add(availability)
    else:
        availability.is_available = payload.is_available

    if payload.is_available:
        await session.flush()
        await assign_waiting_order(session, availability)

    await session.commit()
    return RiderAvailabilityResponse(is_available=availability.is_available)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    """Fetch details of a single order with authorization checks."""
    res = await session.execute(
        select(Order).where(Order.id == order_id).options(*order_eager_options())
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == UserRole.RESTAURANT_OWNER and order.restaurant.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if (
        current_user.role == UserRole.DELIVERY_PARTNER
        and (not order.delivery or order.delivery.delivery_partner_id != current_user.id)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return order


# ==========================================
# 3. Order Lifecycle & Status Transitions
# ==========================================
@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    """Enforce strict 7-stage lifecycle state machine transitions with RBAC."""
    res = await session.execute(
        select(Order).where(Order.id == order_id).options(*order_eager_options())
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    current_status = order.status
    target_status = status_in.status
    now = datetime.now(timezone.utc)

    if current_status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.REFUNDED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot change status from terminal state '{current_status.value}'",
        )

    # 1. Customer cancellation or delivery confirmation
    if current_user.role == UserRole.CUSTOMER:
        if order.customer_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
        if target_status == OrderStatus.DELIVERED:
            if (
                current_status != OrderStatus.OUT_FOR_DELIVERY
                or not order.delivery
                or order.delivery.status != DeliveryStatus.ON_ROUTE
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customers can only cancel orders while placed or confirm delivery once the rider is on route",
                )
            order.status = OrderStatus.DELIVERED
            order.delivery.status = DeliveryStatus.COMPLETED
            order.delivery.delivered_time = now
            availability_result = await session.execute(
                select(RiderAvailability).where(
                    RiderAvailability.user_id
                    == order.delivery.delivery_partner_id
                )
            )
            availability = availability_result.scalar_one_or_none()
            if availability is None:
                availability = RiderAvailability(
                    user_id=order.delivery.delivery_partner_id,
                    is_available=True,
                )
                session.add(availability)
            else:
                availability.is_available = True
        elif target_status == OrderStatus.CANCELLED:
            if current_status != OrderStatus.PLACED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customers can only cancel orders in 'placed' status",
                )
            order.status = OrderStatus.CANCELLED
            if order.payment:
                order.payment.status = PaymentStatus.REFUNDED
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customers can only cancel placed orders or confirm delivery",
            )

    # 2. Restaurant Owner Transitions
    elif current_user.role == UserRole.RESTAURANT_OWNER:
        if order.restaurant.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

        owner_valid_transitions = {
            OrderStatus.PLACED: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
            OrderStatus.ACCEPTED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
            OrderStatus.PREPARING: [OrderStatus.READY],
        }

        allowed = owner_valid_transitions.get(current_status, [])
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition from '{current_status.value}' to '{target_status.value}'. Allowed: {[s.value for s in allowed]}",
            )
        order.status = target_status
        if target_status == OrderStatus.ACCEPTED:
            await assign_available_rider(session, order)
        if target_status == OrderStatus.CANCELLED:
            if order.payment:
                order.payment.status = PaymentStatus.REFUNDED
            if order.delivery and order.delivery.delivery_partner_id:
                availability_result = await session.execute(
                    select(RiderAvailability).where(
                        RiderAvailability.user_id
                        == order.delivery.delivery_partner_id
                    )
                )
                availability = availability_result.scalar_one_or_none()
                if availability:
                    availability.is_available = True
                order.delivery.status = DeliveryStatus.FAILED

    # 3. Delivery Partner transitions are handled by the delivery tracker endpoint.
    elif current_user.role == UserRole.DELIVERY_PARTNER:
        if not order.delivery or order.delivery.delivery_partner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned delivery partner can update this order",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the delivery tracker to update rider progress",
        )

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted to update status")

    await session.commit()
    await session.refresh(order)
    return order


@router.patch(
    "/{order_id}/delivery-status",
    response_model=OrderResponse,
)
async def update_delivery_status(
    order_id: int,
    status_in: DeliveryStatusUpdate,
    session: SessionDep,
    current_user: RiderDep,
):
    result = await session.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(*order_eager_options())
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if not order.delivery or order.delivery.delivery_partner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned delivery partner can update this delivery",
        )

    current_delivery_status = order.delivery.status
    target_delivery_status = status_in.status
    valid_transitions = {
        DeliveryStatus.ON_THE_WAY_TO_RESTAURANT: [DeliveryStatus.AT_RESTAURANT],
        DeliveryStatus.ASSIGNED: [DeliveryStatus.AT_RESTAURANT],
        DeliveryStatus.AT_RESTAURANT: [DeliveryStatus.PICKED_UP],
        DeliveryStatus.PICKED_UP: [DeliveryStatus.ON_ROUTE],
    }
    if target_delivery_status not in valid_transitions.get(
        current_delivery_status, []
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid delivery transition from '{current_delivery_status.value}' "
                f"to '{target_delivery_status.value}'"
            ),
        )
    if (
        target_delivery_status == DeliveryStatus.PICKED_UP
        and order.status != OrderStatus.READY
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The restaurant must mark the order ready before pickup",
        )

    order.delivery.status = target_delivery_status
    if target_delivery_status == DeliveryStatus.PICKED_UP:
        order.delivery.pickup_time = datetime.now(timezone.utc)
    elif target_delivery_status == DeliveryStatus.ON_ROUTE:
        order.status = OrderStatus.OUT_FOR_DELIVERY

    await session.commit()
    await session.refresh(order)
    return order


# ==========================================
# 5. Return & Refund Management
# ==========================================
@router.post("/{order_id}/refund-request", response_model=RefundRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_refund(
    order_id: int,
    payload: RefundRequestCreate,
    session: SessionDep,
    current_user: CustomerDep,
):
    """Customer requests refund post-delivery with mandatory reason."""
    res = await session.execute(
        select(Order).where(Order.id == order_id).options(*order_eager_options())
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refunds can only be requested after the order has been delivered",
        )

    if order.refund_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A refund request has already been submitted for this order",
        )

    refund = RefundRequest(
        order_id=order.id,
        reason=payload.reason,
        status=RefundStatus.PENDING,
    )
    session.add(refund)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A refund request has already been submitted for this order",
        ) from error
    await session.refresh(refund)
    return refund


@router.post("/{order_id}/refund-decision", response_model=OrderResponse)
async def decide_refund(
    order_id: int,
    payload: RefundDecisionUpdate,
    session: SessionDep,
    current_user: OwnerDep,
):
    """Restaurant owner approves or rejects a refund request."""
    res = await session.execute(
        select(Order).where(Order.id == order_id).options(*order_eager_options())
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.restaurant.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    if not order.refund_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No refund request found for this order")

    if order.refund_request.status != RefundStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund request has already been resolved as '{order.refund_request.status.value}'",
        )

    order.refund_request.status = payload.status
    order.refund_request.decision_notes = payload.decision_notes

    if payload.status == RefundStatus.APPROVED:
        order.status = OrderStatus.REFUNDED
        if order.payment:
            order.payment.status = PaymentStatus.REFUNDED

    await session.commit()
    await session.refresh(order)
    return order


# ==========================================
# 6. Customer Ratings & Reviews
# ==========================================
@router.post("/{order_id}/review", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def add_order_review(
    order_id: int,
    payload: ReviewCreate,
    session: SessionDep,
    current_user: CustomerDep,
):
    """Customer submits rating and review after successful delivery."""
    res = await session.execute(
        select(Order).where(Order.id == order_id).options(*order_eager_options())
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviews can only be submitted after the order has been delivered",
        )

    if order.review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A review has already been submitted for this order",
        )

    review = Review(
        order_id=order.id,
        restaurant_id=order.restaurant_id,
        customer_id=current_user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review