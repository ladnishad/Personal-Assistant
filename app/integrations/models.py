"""Integration database models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document
from pydantic import Field
from beanie import PydanticObjectId


class IntegrationType(str, Enum):
    """Integration type enumeration."""

    GOOGLE = "google"
    MICROSOFT = "microsoft"


class Integration(Document):
    """Integration document model for OAuth connections."""

    user_id: PydanticObjectId = Field(..., index=True)
    integration_type: IntegrationType
    is_active: bool = Field(default=True)

    # OAuth tokens
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    scope: list[str] = Field(default_factory=list)

    # Integration-specific data
    email: Optional[str] = None  # Connected email account
    account_id: Optional[str] = None

    # Sync state
    last_email_sync: Optional[datetime] = None
    last_calendar_sync: Optional[datetime] = None
    email_sync_token: Optional[str] = None  # For incremental sync
    calendar_sync_token: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "integrations"
        indexes = [
            "user_id",
            [("user_id", 1), ("integration_type", 1)],
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "integration_type": "google",
                "is_active": True,
                "email": "user@gmail.com",
                "scope": ["gmail.readonly", "calendar.readonly"],
            }
        }
