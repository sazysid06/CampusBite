from datetime import datetime
from typing import Annotated, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from backend.app.models.order import (
    DeliveryStatus,
    OrderStatus,
    PaymentStatus,
    RefundStatus,
)


# --- Order Item Schemas ---
class OrderItemBase(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0, description="Quantity must be at least 1")


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    unit_price: float

    model_config = ConfigDict(from_attributes=True)


# --- Payment & Delivery Schemas ---
class PaymentResponse(BaseModel):
    id: int
    amount: float
    status: PaymentStatus
    transaction_reference: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryResponse(BaseModel):
    id: int
    delivery_partner_id: Optional[int] = None
    status: DeliveryStatus
    pickup_time: Optional[datetime] = None
    delivered_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus


class RiderAvailabilityUpdate(BaseModel):
    is_available: bool


class RiderAvailabilityResponse(BaseModel):
    is_available: bool


class DeliveryCreate(BaseModel):
    order_id: int
    delivery_partner_id: Optional[int] = None


# --- Review Schemas ---
class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5, description="Rating must be between 1 and 5")
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    order_id: int
    restaurant_id: int
    customer_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Refund Schemas ---
class RefundRequestCreate(BaseModel):
    reason: Annotated[
        str,
        StringConstraints(
            min_length=5,
            max_length=1000,
            strip_whitespace=True,
        ),
    ] = Field(description="Reason for the refund request")


class RefundDecisionUpdate(BaseModel):
    status: Literal[RefundStatus.APPROVED, RefundStatus.REJECTED] = Field(
        description="Must be approved or rejected"
    )
    decision_notes: Optional[str] = None


class RefundRequestResponse(BaseModel):
    id: int
    order_id: int
    reason: str
    status: RefundStatus
    decision_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Order Lifecycle & Management Schemas ---
class OrderCreate(BaseModel):
    restaurant_id: int
    delivery_address: str = Field(min_length=5)
    special_instructions: Optional[str] = None
    items: List[OrderItemCreate] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    restaurant_id: int
    total_amount: float
    status: OrderStatus
    delivery_address: str
    special_instructions: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse]
    delivery: Optional[DeliveryResponse] = None
    payment: Optional[PaymentResponse] = None
    refund_request: Optional[RefundRequestResponse] = None
    review: Optional[ReviewResponse] = None

    model_config = ConfigDict(from_attributes=True)


# --- Analytics, Reminders & AI Schemas ---
class RestaurantStatsResponse(BaseModel):
    restaurant_id: int
    total_orders: int
    total_revenue: float
    completed_orders: int
    cancelled_orders: int
    refunded_orders: int


class StaleOrderReminderResponse(BaseModel):
    order_id: int
    status: OrderStatus
    last_updated: datetime
    minutes_elapsed: int
    warning: str


class CustomerOrderInsights(BaseModel):
    customer_id: int
    total_orders_analyzed: int
    total_spent: float
    favorite_items: List[str]
    ai_summary: str
    personalized_recommendation: str