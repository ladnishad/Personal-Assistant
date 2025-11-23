"""Beanie document model for confirmations."""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field

from app.confirmations.models import ConfirmationStatus, RiskLevel


class Confirmation(Document):
    """MongoDB document for storing confirmation requests."""

    user_id: str = Field(..., description="ID of the user who needs to confirm")
    conversation_id: Optional[str] = Field(default=None, description="Associated conversation ID if applicable")
    action_description: str = Field(..., description="Description of the action requiring confirmation")
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM)
    status: ConfirmationStatus = Field(default=ConfirmationStatus.PENDING)

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="When this confirmation expires")
    resolved_at: Optional[datetime] = Field(default=None)

    # Response
    approved: bool = Field(default=False)
    user_note: Optional[str] = Field(default=None)

    # Additional context
    metadata: Optional[dict] = Field(default=None)

    class Settings:
        name = "confirmations"
        indexes = [
            "user_id",
            "conversation_id",
            "status",
            "created_at",
            "expires_at",
            [("user_id", 1), ("status", 1)],  # Compound index for pending confirmations
        ]
