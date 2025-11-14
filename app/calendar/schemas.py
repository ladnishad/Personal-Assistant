"""Calendar request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.calendar.models import EventStatus


class CalendarEventResponse(BaseModel):
    """Calendar event response."""

    id: str = Field(..., alias="_id")
    user_id: str
    event_id: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    timezone: str
    is_all_day: bool
    organizer: Optional[str] = None
    attendees: List[str]
    status: EventStatus
    is_recurring: bool
    meeting_link: Optional[str] = None
    html_link: Optional[str] = None

    class Config:
        populate_by_name = True


class CalendarEventListResponse(BaseModel):
    """Calendar event list response."""

    events: List[CalendarEventResponse]
    total: int


class CalendarSyncResponse(BaseModel):
    """Calendar sync response."""

    synced_count: int
    new_events: int
    updated_events: int
    last_sync: datetime
