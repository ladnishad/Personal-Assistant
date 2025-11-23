"""Models for user confirmation system."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level for actions requiring confirmation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfirmationStatus(str, Enum):
    """Status of a confirmation request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ConfirmationRequest(BaseModel):
    """Request model for creating a confirmation."""
    action_description: str = Field(..., description="Clear description of the action to be performed")
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Risk level of the action")
    timeout_seconds: int = Field(default=300, description="How long to wait for user response (default 5 minutes)")
    metadata: Optional[dict] = Field(default=None, description="Additional context about the action")


class ConfirmationResponse(BaseModel):
    """Response model for confirmation results."""
    confirmation_id: str
    status: ConfirmationStatus
    approved: bool
    user_note: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class PendingConfirmation(BaseModel):
    """Model for a pending confirmation displayed to the user."""
    confirmation_id: str
    action_description: str
    risk_level: RiskLevel
    created_at: datetime
    expires_at: datetime
    metadata: Optional[dict] = None


class UserConfirmationDecision(BaseModel):
    """User's decision on a confirmation request."""
    approved: bool
    note: Optional[str] = Field(default=None, description="Optional note from the user about their decision")
