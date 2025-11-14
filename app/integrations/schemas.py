"""Integration request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.integrations.models import IntegrationType


class IntegrationConnectRequest(BaseModel):
    """Request to initiate OAuth connection."""

    scopes: List[str] = Field(
        default_factory=lambda: ["email", "calendar"],
        description="Requested scopes",
    )


class IntegrationConnectResponse(BaseModel):
    """OAuth authorization URL response."""

    authorization_url: str
    state: str


class IntegrationCallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str
    state: str


class IntegrationResponse(BaseModel):
    """Integration response model."""

    id: str = Field(..., alias="_id")
    user_id: str
    integration_type: IntegrationType
    is_active: bool
    email: Optional[str] = None
    scope: List[str]
    last_email_sync: Optional[datetime] = None
    last_calendar_sync: Optional[datetime] = None
    created_at: datetime

    class Config:
        populate_by_name = True


class IntegrationListResponse(BaseModel):
    """List of integrations response."""

    integrations: List[IntegrationResponse]
    total: int
