from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ==========================
# MenuItem Schemas
# ==========================
class MenuItemBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    price: float = Field(..., gt=0, description="Price must be greater than zero")
    category: str = Field(..., min_length=2, max_length=50)
    is_available: bool = True


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, min_length=2, max_length=50)
    is_available: Optional[bool] = None


class MenuItemResponse(MenuItemBase):
    id: int
    restaurant_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================
# Restaurant Schemas
# ==========================
class RestaurantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    address: str = Field(..., min_length=5, max_length=255)
    phone_number: str = Field(..., min_length=10, max_length=20)
    is_open: bool = True


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    is_open: Optional[bool] = None


class RestaurantResponse(RestaurantBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RestaurantDetailResponse(RestaurantResponse):
    menu_items: List[MenuItemResponse] = []