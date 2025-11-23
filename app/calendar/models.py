"""Calendar and event database models."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class EventStatus(str, Enum):
    """Event status enumeration."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class EventVisibility(str, Enum):
    """Event visibility enumeration."""

    DEFAULT = "default"
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class ReminderMethod(str, Enum):
    """Reminder delivery method."""

    EMAIL = "email"
    POPUP = "popup"


class Calendar(Document):
    """Calendar model representing a user's calendar."""

    user_id: Indexed(PydanticObjectId)
    integration_id: Indexed(PydanticObjectId)

    # Calendar identifiers
    provider_calendar_id: str  # Google Calendar ID or other provider ID
    summary: str  # Calendar name/title
    description: Optional[str] = None

    # Calendar settings
    timezone: str = Field(default="UTC")
    background_color: Optional[str] = None  # Hex color code
    foreground_color: Optional[str] = None  # Hex color code
    is_primary: bool = Field(default=False)
    is_selected: bool = Field(default=True)  # Whether to show events from this calendar

    # Access control
    access_role: Optional[str] = None  # owner, writer, reader
    is_hidden: bool = Field(default=False)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_synced_at: Optional[datetime] = None

    class Settings:
        name = "calendars"
        indexes = [
            [("user_id", 1), ("provider_calendar_id", 1)],
            [("user_id", 1), ("is_primary", 1)],
            IndexModel(
                [("user_id", 1), ("provider_calendar_id", 1)],
                name="calendar_unique_idx",
                unique=True,
            ),
        ]


class CalendarEvent(Document):
    """Calendar event document model."""

    user_id: Indexed(PydanticObjectId)
    integration_id: Indexed(PydanticObjectId)
    calendar_doc_id: Optional[Indexed(PydanticObjectId)] = None  # Reference to Calendar document

    # Event identifiers
    event_id: str  # Unique index defined in Settings.indexes
    provider_calendar_id: Optional[str] = None  # Which calendar this event belongs to
    icaluid: Optional[str] = None  # iCalendar UID

    # Event details
    title: str  # Event summary
    description: Optional[str] = None
    location: Optional[str] = None

    # Time
    start_time: datetime
    end_time: datetime
    timezone: str = Field(default="UTC")
    is_all_day: bool = Field(default=False)

    # Recurrence
    is_recurring: bool = Field(default=False)
    recurrence_rule: Optional[str] = None  # RRULE format
    recurring_event_id: Optional[str] = None  # For recurring event instances

    # Status and visibility
    status: EventStatus = Field(default=EventStatus.CONFIRMED)
    visibility: EventVisibility = Field(default=EventVisibility.DEFAULT)

    # Attendees and organization
    creator_email: Optional[str] = None
    organizer: Optional[str] = None
    organizer_name: Optional[str] = None
    attendees: List[dict] = Field(default_factory=list)  # List of attendee dicts with email, responseStatus, etc.

    # Meeting details
    meeting_link: Optional[str] = None  # Google Meet, Zoom, etc.
    conference_data: Optional[Dict] = None  # Full conference details
    hangout_link: Optional[str] = None  # Legacy Google Meet link

    # Reminders
    reminders: List[dict] = Field(default_factory=list)  # List of reminder dicts
    use_default_reminders: bool = Field(default=True)

    # Metadata
    color_id: Optional[str] = None  # Event color
    html_link: Optional[str] = None  # Link to event in calendar UI
    attachments: List[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_synced_at: Optional[datetime] = None

    # AI-generated insights
    ai_summary: Optional[str] = None  # Brief intelligent summary
    preparation_items: List[str] = Field(default_factory=list)  # What to prepare
    estimated_travel_time: Optional[int] = None  # Minutes to location
    is_important: Optional[bool] = None  # AI-determined importance
    conflict_detected: bool = Field(default=False)  # Overlapping events
    suggested_prep_time: Optional[int] = None  # Minutes before to prepare
    analyzed_at: Optional[datetime] = None

    # Embeddings for semantic search
    embedding: Optional[List[float]] = None
    embedded_at: Optional[datetime] = None

    class Settings:
        name = "calendar_events"
        indexes = [
            [("user_id", 1), ("start_time", -1)],  # Most recent first
            [("user_id", 1), ("calendar_doc_id", 1), ("start_time", -1)],
            [("user_id", 1), ("status", 1), ("start_time", -1)],
            [("start_time", 1), ("end_time", 1)],  # For time range queries
            IndexModel([("event_id", 1)], name="calendar_event_id_unique_idx", unique=True),
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Team Meeting",
                "description": "Weekly sync meeting",
                "location": "Conference Room A",
                "start_time": "2024-01-15T14:00:00",
                "end_time": "2024-01-15T15:00:00",
                "attendees": [{"email": "john@example.com"}, {"email": "jane@example.com"}],
            }
        }
