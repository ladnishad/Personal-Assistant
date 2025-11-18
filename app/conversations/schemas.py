"""Conversation request/response schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer


class MessageResponse(BaseModel):
    """Individual message response."""

    id: str = Field(..., serialization_alias="_id")
    conversation_id: str
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tokens_used: Optional[int] = None
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime, _info):
        """Serialize datetime to ISO8601 format without microseconds."""
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    model_config = {"populate_by_name": True}


class ConversationResponse(BaseModel):
    """Conversation response."""

    id: str = Field(..., serialization_alias="_id")
    user_id: str
    title: str
    message_count: int
    is_active: bool
    task_id: Optional[str] = None
    summary: Optional[str] = None
    summary_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at", "summary_updated_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """Serialize datetime to ISO8601 format without microseconds."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    model_config = {"populate_by_name": True}


class ConversationWithMessages(ConversationResponse):
    """Conversation response with full message history."""

    messages: List[MessageResponse]


class ConversationListResponse(BaseModel):
    """Conversation list response."""

    conversations: List[ConversationResponse]
    total: int


class ConversationUpdate(BaseModel):
    """Conversation update request."""

    title: Optional[str] = None
    is_active: Optional[bool] = None
