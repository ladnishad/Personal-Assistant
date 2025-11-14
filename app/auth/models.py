"""User database models."""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import EmailStr, Field


class User(Document):
    """User document model."""

    email: EmailStr = Field(..., unique=True, index=True)
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Profile
    timezone: str = Field(default="UTC")
    preferences: dict = Field(default_factory=dict)

    class Settings:
        name = "users"
        indexes = [
            "email",
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "timezone": "America/New_York",
            }
        }
