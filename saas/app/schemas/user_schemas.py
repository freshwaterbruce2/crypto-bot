"""
User Schemas
===========

Pydantic schemas for user-related API endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, validator


class UserCreate(BaseModel):
    """Schema for user creation"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = "UTC"
    preferences: Optional[dict[str, Any]] = None

    @validator("username")
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Username must be less than 50 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for user updates"""
    full_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    preferences: Optional[dict[str, Any]] = None


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    company: Optional[str]
    phone: Optional[str]
    timezone: str
    is_active: bool
    is_verified: bool
    is_admin: bool
    subscription_tier: Optional[str]
    created_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserStats(BaseModel):
    """Schema for user statistics"""
    strategies_created: int
    strategies_purchased: int
    api_keys: int
    total_trades: int
    total_spent: float
    member_since: Optional[str]
    last_login: Optional[str]


class NotificationResponse(BaseModel):
    """Schema for notification response"""
    id: int
    title: str
    message: str
    type: str
    priority: str
    data: dict[str, Any]
    action_url: Optional[str]
    is_read: bool
    is_dismissed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationUpdate(BaseModel):
    """Schema for notification updates"""
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None
