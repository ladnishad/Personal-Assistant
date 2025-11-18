"""Authentication request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_serializer


class UserRegister(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None
    timezone: str = Field(default="UTC")


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model."""

    id: str = Field(..., serialization_alias="_id")
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    timezone: str
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info):
        """Serialize datetime to ISO8601 format without microseconds."""
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_verified": False,
                "timezone": "America/New_York",
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
    }


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

    model_config = {
        "populate_by_name": True
    }


class TokenRefresh(BaseModel):
    """Token refresh request."""

    refresh_token: str


class PasswordChange(BaseModel):
    """Password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
