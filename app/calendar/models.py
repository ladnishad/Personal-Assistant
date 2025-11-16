"""Calendar event database models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class EventStatus(str, Enum):
    """Event status enumeration."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class CalendarEvent(Document):
    """Calendar event document model."""

    user_id: Indexed(PydanticObjectId)
    integration_id: Indexed(PydanticObjectId)

    # Event identifiers
    event_id: Indexed(str, unique=True)
    calendar_id: Optional[str] = None

    # Event details
    title: str
    description: Optional[str] = None
    location: Optional[str] = None

    # Time
    start_time: datetime
    end_time: datetime
    timezone: str = Field(default="UTC")
    is_all_day: bool = Field(default=False)

    # Attendees
    organizer: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)

    # Status
    status: EventStatus = Field(default=EventStatus.CONFIRMED)

    # Recurrence
    is_recurring: bool = Field(default=False)
    recurrence_rule: Optional[str] = None

    # Links
    meeting_link: Optional[str] = None
    html_link: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Embeddings
    embedding: Optional[List[float]] = None
    embedded_at: Optional[datetime] = None

    class Settings:
        name = "calendar_events"
        indexes = [
            [("user_id", 1), ("start_time", 1)],
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Team Meeting",
                "description": "Weekly sync meeting",
                "location": "Conference Room A",
                "start_time": "2024-01-15T14:00:00",
                "end_time": "2024-01-15T15:00:00",
                "attendees": ["john@example.com", "jane@example.com"],
            }
        }
