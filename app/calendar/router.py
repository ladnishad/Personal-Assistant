"""Calendar API routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.calendar.schemas import (
    CalendarEventListResponse,
    CalendarEventResponse,
    CalendarSyncResponse,
)
from app.calendar.service import CalendarService

router = APIRouter()


@router.post("/sync", response_model=CalendarSyncResponse)
async def sync_calendar(current_user: User = Depends(get_current_active_user)):
    """Sync calendar events from all connected integrations."""
    result = await CalendarService.sync_calendar(current_user.id)
    return CalendarSyncResponse(**result)


@router.get("/events", response_model=CalendarEventListResponse)
async def list_events(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    """List calendar events."""
    skip = (page - 1) * page_size

    events, total = await CalendarService.get_user_events(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=page_size,
    )

    event_responses = [
        CalendarEventResponse(
            _id=str(e.id),
            user_id=str(e.user_id),
            event_id=e.event_id,
            title=e.title,
            description=e.description,
            location=e.location,
            start_time=e.start_time,
            end_time=e.end_time,
            timezone=e.timezone,
            is_all_day=e.is_all_day,
            organizer=e.organizer,
            attendees=e.attendees,
            status=e.status,
            is_recurring=e.is_recurring,
            meeting_link=e.meeting_link,
            html_link=e.html_link,
        )
        for e in events
    ]

    return CalendarEventListResponse(events=event_responses, total=total)
