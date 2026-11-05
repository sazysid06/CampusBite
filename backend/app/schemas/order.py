from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.models.order import DeliveryStatus, OrderStatus


# ==========================
# OrderItem Schemas
# ==========================
class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be at least 1")


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    unit_price: float

    model_config = ConfigDict(from_attributes=True)


# ==========================
# Delivery Schemas
# ==========================
class DeliveryResponse(BaseModel):
    id: int
    order_id: int
    delivery_partner_id: Optional[int] = None
    status: DeliveryStatus
    pickup_time: Optional[datetime] = None
    delivered_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus


# ==========================
# Order Schemas
# ==========================
class OrderCreate(BaseModel):
    restaurant_id: int
    delivery_address: str = Field(..., min_length=5, max_length=255)
    special_instructions: Optional[str] = None
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Order must contain at least one item")


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
    items: List[OrderItemResponse] = []
    delivery: Optional[DeliveryResponse] = None

    model_config = ConfigDict(from_attributes=True)