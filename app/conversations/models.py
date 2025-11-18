"""Conversation database models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class Conversation(Document):
    """Conversation document model for chat sessions."""

    user_id: Indexed(PydanticObjectId)

    # Conversation metadata
    title: str = Field(default="New Conversation")
    message_count: int = Field(default=0)
    is_active: bool = Field(
        default=True, description="True if messages received in last hour"
    )

    # Optional link to a specific task
    task_id: Optional[PydanticObjectId] = Field(
        default=None, description="Link to task if this is a task-specific conversation"
    )

    # Phase 2: Summary fields (optional for now)
    summary: Optional[str] = Field(
        default=None, description="AI-generated conversation summary for search/discovery"
    )
    summary_updated_at: Optional[datetime] = Field(
        default=None, description="When summary was last generated"
    )
    summary_message_count: int = Field(
        default=0, description="Message count when summary was last generated"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "conversations"
        indexes = [
            [("user_id", 1), ("updated_at", -1)],  # List user's recent conversations
            [("user_id", 1), ("is_active", 1)],  # Find active conversations
            [("user_id", 1), ("task_id", 1)],  # Find task-specific conversations
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Rent increase discussion",
                "message_count": 15,
                "is_active": False,
                "summary": "User discussed rent increase with landlord. Decided to negotiate for 5% instead of 8%.",
            }
        }


class ConversationMessage(Document):
    """Individual message within a conversation."""

    conversation_id: Indexed(PydanticObjectId)

    # Message content
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")

    # Optional metadata
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Tools called by agent in this message"
    )
    tokens_used: Optional[int] = Field(
        default=None, description="Tokens consumed by this message"
    )

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "conversation_messages"
        indexes = [
            [
                ("conversation_id", 1),
                ("timestamp", 1),
            ],  # Get messages in chronological order
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Create a task to call the landlord by Friday",
                "tool_calls": None,
                "tokens_used": 15,
            }
        }
