from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google import genai
from sqlalchemy import select
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
from backend.app.models.user import User, UserRole
from backend.app.schemas.order import (
    AssignDeliveryPartner,
    CustomerOrderInsights,
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    RefundDecisionUpdate,
    RefundRequestCreate,
    RefundRequestResponse,
    RestaurantStatsResponse,
    ReviewCreate,
    ReviewResponse,
    StaleOrderReminderResponse,
)

router = APIRouter(prefix="/orders", tags=["Orders & Delivery"])

CustomerDep = Annotated[User, Depends(RoleChecker([UserRole.CUSTOMER]))]
OwnerDep = Annotated[User, Depends(RoleChecker([UserRole.RESTAURANT_OWNER]))]
RiderDep = Annotated[User, Depends(RoleChecker([UserRole.DELIVERY_PARTNER]))]


def order_eager_options():
    return (
        selectinload(Order.items).selectinload(OrderItem.menu_item),
        selectinload(Order.delivery),
        selectinload(Order.payment),
        selectinload(Order.refund_request),
        selectinload(Order.review),
        selectinload(Order.restaurant),
    )


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
    rest_res = await session.execute(
        select(Restaurant).where(Restaurant.owner_id == current_user.id)
    )
    restaurant = rest_res.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No restaurant found for current owner")

    orders_res = await session.execute(
        select(Order).where(Order.restaurant_id == restaurant.id)
    )
    all_orders = orders_res.scalars().all()

    total_orders = len(all_orders)
    completed_orders = sum(1 for o in all_orders if o.status == OrderStatus.DELIVERED)
    cancelled_orders = sum(1 for o in all_orders if o.status == OrderStatus.CANCELLED)
    refunded_orders = sum(1 for o in all_orders if o.status == OrderStatus.REFUNDED)
    total_revenue = sum(o.total_amount for o in all_orders if o.status == OrderStatus.DELIVERED)

    return RestaurantStatsResponse(
        restaurant_id=restaurant.id,
        total_orders=total_orders,
        total_revenue=round(total_revenue, 2),
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        refunded_orders=refunded_orders,
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

    # 1. Customer Cancellation
    if current_user.role == UserRole.CUSTOMER:
        if order.customer_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
        if target_status != OrderStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customers can only cancel orders",
            )
        if current_status != OrderStatus.PLACED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customers can only cancel orders in 'placed' status",
            )
        order.status = OrderStatus.CANCELLED
        if order.payment:
            order.payment.status = PaymentStatus.REFUNDED

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
        if target_status == OrderStatus.CANCELLED and order.payment:
            order.payment.status = PaymentStatus.REFUNDED

    # 3. Delivery Partner Transitions
    elif current_user.role == UserRole.DELIVERY_PARTNER:
        if not order.delivery or order.delivery.delivery_partner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned delivery partner can update this order",
            )

        rider_valid_transitions = {
            OrderStatus.ASSIGNED: [OrderStatus.OUT_FOR_DELIVERY],
            OrderStatus.OUT_FOR_DELIVERY: [OrderStatus.DELIVERED],
        }

        allowed = rider_valid_transitions.get(current_status, [])
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition from '{current_status.value}' to '{target_status.value}'. Allowed: {[s.value for s in allowed]}",
            )

        order.status = target_status
        if target_status == OrderStatus.OUT_FOR_DELIVERY:
            order.delivery.status = DeliveryStatus.PICKED_UP
            order.delivery.pickup_time = now
        elif target_status == OrderStatus.DELIVERED:
            order.delivery.status = DeliveryStatus.COMPLETED
            order.delivery.delivered_time = now

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted to update status")

    await session.commit()
    await session.refresh(order)
    return order


# ==========================================
# 4. Restaurant Owner: Assign Delivery Partner
# ==========================================
@router.post("/{order_id}/assign-rider", response_model=OrderResponse)
async def assign_delivery_partner(
    order_id: int,
    payload: AssignDeliveryPartner,
    session: SessionDep,
    current_user: OwnerDep,
):
    """Assign delivery partner to an order once status is READY."""
    res = await session.execute(
        select(Order).where(Order.id == order_id).options(*order_eager_options())
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.restaurant.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    if order.status != OrderStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery partner can only be assigned when order is in 'ready' status",
        )

    rider_res = await session.execute(
        select(User).where(User.id == payload.delivery_partner_id)
    )
    rider = rider_res.scalar_one_or_none()
    if not rider or rider.role != UserRole.DELIVERY_PARTNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided ID is not a registered delivery partner",
        )

    if not order.delivery:
        order.delivery = Delivery(order_id=order.id)

    order.delivery.delivery_partner_id = rider.id
    order.delivery.status = DeliveryStatus.ASSIGNED
    order.status = OrderStatus.ASSIGNED

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
    await session.commit()
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