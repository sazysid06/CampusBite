from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from backend.app.models.user import UserRole


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int


# User Registration Schema
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    role: UserRole = UserRole.CUSTOMER


# User Login Schema
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# User Response / Profile Schema (omits sensitive fields like password)
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone_number: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)