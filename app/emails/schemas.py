"""Email request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_serializer

from app.emails.models import EmailLabel


class EmailAttachmentResponse(BaseModel):
    """Email attachment response."""

    filename: str
    mime_type: str
    size: int
    attachment_id: str


class EmailResponse(BaseModel):
    """Email response model."""

    id: str = Field(..., serialization_alias="_id")
    user_id: str
    message_id: str
    from_email: EmailStr
    from_name: Optional[str] = None
    to: List[str]
    cc: List[str] = Field(default_factory=list)
    subject: Optional[str] = None
    snippet: Optional[str] = None
    body_text: Optional[str] = None
    has_attachments: bool
    attachments: List[dict] = Field(default_factory=list)
    labels: List[EmailLabel]
    is_read: bool
    is_starred: bool
    received_at: datetime
    extracted_entities: dict = Field(default_factory=dict)

    @field_serializer('received_at')
    def serialize_datetime(self, dt: datetime, _info):
        """Serialize datetime to ISO8601 format without microseconds."""
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    model_config = {
        "populate_by_name": True
    }


class EmailListResponse(BaseModel):
    """Email list response."""

    emails: List[EmailResponse]
    total: int
    page: int
    page_size: int


class EmailQueryParams(BaseModel):
    """Email query parameters."""

    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None
    labels: Optional[List[EmailLabel]] = None
    search: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class EmailSyncResponse(BaseModel):
    """Email sync response."""

    synced_count: int
    new_emails: int
    updated_emails: int
    last_sync: datetime
