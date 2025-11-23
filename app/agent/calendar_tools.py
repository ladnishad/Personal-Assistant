"""Calendar management tools for AI agents."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents import function_tool
from beanie import PydanticObjectId

from app.calendar.google_calendar_service import GoogleCalendarService
from app.calendar.models import Calendar, CalendarEvent, EventStatus
from app.calendar.service import CalendarService
from app.integrations.models import Integration, IntegrationType

logger = logging.getLogger(__name__)


# Import user context from tools.py
def get_current_user_id() -> PydanticObjectId:
    """Get the current user ID from execution context."""
    from app.agent.tools import get_current_user_id as _get_user_id

    return _get_user_id()


def _format_event_summary(event: CalendarEvent) -> Dict[str, Any]:
    """Format event into concise summary for list responses.

    Args:
        event: CalendarEvent document

    Returns:
        Concise event summary
    """
    # Calculate duration
    duration_minutes = int((event.end_time - event.start_time).total_seconds() / 60)

    return {
        "event_id": str(event.id),
        "title": event.title,
        "start_time": event.start_time.isoformat(),
        "end_time": event.end_time.isoformat(),
        "duration_minutes": duration_minutes,
        "location": event.location,
        "is_all_day": event.is_all_day,
        "meeting_link": event.meeting_link,
        "attendees_count": len(event.attendees) if event.attendees else 0,
    }


def _format_event_detail(event: CalendarEvent) -> Dict[str, Any]:
    """Format event into detailed response.

    Args:
        event: CalendarEvent document

    Returns:
        Detailed event dictionary
    """
    # Calculate duration
    duration_minutes = int((event.end_time - event.start_time).total_seconds() / 60)

    # Extract attendee emails
    attendee_emails = []
    if event.attendees:
        for att in event.attendees:
            if isinstance(att, dict):
                attendee_emails.append(att.get("email"))
            elif hasattr(att, "email"):
                attendee_emails.append(att.email)

    return {
        "event_id": str(event.id),
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "start_time": event.start_time.isoformat(),
        "end_time": event.end_time.isoformat(),
        "duration_minutes": duration_minutes,
        "timezone": event.timezone,
        "is_all_day": event.is_all_day,
        "status": event.status.value,
        "organizer": event.organizer,
        "organizer_name": event.organizer_name,
        "attendees": attendee_emails,
        "meeting_link": event.meeting_link,
        "html_link": event.html_link,
        "is_recurring": event.is_recurring,
        "ai_summary": event.ai_summary,
        "preparation_items": event.preparation_items,
        "estimated_travel_time": event.estimated_travel_time,
        "is_important": event.is_important,
    }


@function_tool
async def sync_calendars() -> str:
    """Sync user's calendars and events from connected services (Google Calendar, etc.).

    Use this when:
    - User asks to "refresh", "update", or "sync" their calendar
    - Before showing calendar data to ensure it's current
    - After connecting a new calendar integration

    Returns:
        Summary of sync results including number of events synced
    """
    try:
        user_id = get_current_user_id()
        result = await CalendarService.sync_calendar(user_id)

        return f"✅ Calendar sync complete! Synced {result['calendars_synced']} calendars with {result['synced_count']} total events ({result['new_events']} new, {result['updated_events']} updated)."

    except Exception as e:
        logger.error(f"Error syncing calendars: {e}")
        return f"❌ Error syncing calendars: {str(e)}"


@function_tool
async def get_upcoming_events(days_ahead: int = 7, limit: int = 20) -> Dict[str, Any]:
    """Get upcoming events for the next N days.

    Use this when user asks about:
    - "What's on my calendar?"
    - "What do I have coming up?"
    - "Show me my schedule"
    - "What's next week look like?"

    Args:
        days_ahead: Number of days to look ahead (default: 7)
        limit: Maximum number of events to return (default: 20)

    Returns:
        Dictionary with upcoming events list and summary
    """
    try:
        user_id = get_current_user_id()

        # Get events from now until days_ahead from now
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days_ahead)

        events, total = await CalendarService.get_user_events(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            status=EventStatus.CONFIRMED,
            limit=limit,
        )

        if not events:
            return {
                "message": f"No upcoming events in the next {days_ahead} days.",
                "events": [],
                "total_count": 0,
            }

        event_summaries = [_format_event_summary(e) for e in events]

        return {
            "message": f"Found {len(events)} upcoming events in the next {days_ahead} days.",
            "events": event_summaries,
            "total_count": total,
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Error getting upcoming events: {e}")
        return {"error": str(e), "events": []}


@function_tool
async def get_today_events() -> Dict[str, Any]:
    """Get all events scheduled for today.

    Use this when user asks:
    - "What's on my calendar today?"
    - "What do I have today?"
    - "What's my schedule for today?"
    - "Am I free today?"

    Returns:
        Dictionary with today's events and summary
    """
    try:
        user_id = get_current_user_id()

        # Get events for today (00:00 to 23:59)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        events, total = await CalendarService.get_user_events(
            user_id=user_id,
            start_date=today_start,
            end_date=today_end,
        )

        if not events:
            return {
                "message": "No events scheduled for today. You're free!",
                "events": [],
                "total_count": 0,
            }

        event_summaries = [_format_event_detail(e) for e in events]

        return {
            "message": f"You have {len(events)} event(s) today.",
            "events": event_summaries,
            "total_count": total,
        }

    except Exception as e:
        logger.error(f"Error getting today's events: {e}")
        return {"error": str(e), "events": []}


@function_tool
async def get_tomorrow_events() -> Dict[str, Any]:
    """Get all events scheduled for tomorrow.

    Use this when user asks:
    - "What's on my calendar tomorrow?"
    - "What do I have tomorrow?"
    - "What's tomorrow looking like?"

    Returns:
        Dictionary with tomorrow's events
    """
    try:
        user_id = get_current_user_id()

        # Get events for tomorrow
        tomorrow_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(days=1)

        events, total = await CalendarService.get_user_events(
            user_id=user_id,
            start_date=tomorrow_start,
            end_date=tomorrow_end,
        )

        if not events:
            return {
                "message": "No events scheduled for tomorrow.",
                "events": [],
                "total_count": 0,
            }

        event_summaries = [_format_event_detail(e) for e in events]

        return {
            "message": f"You have {len(events)} event(s) tomorrow.",
            "events": event_summaries,
            "total_count": total,
        }

    except Exception as e:
        logger.error(f"Error getting tomorrow's events: {e}")
        return {"error": str(e), "events": []}


@function_tool
async def get_this_week_events() -> Dict[str, Any]:
    """Get all events for this week (Monday to Sunday).

    Use this when user asks:
    - "What's my schedule this week?"
    - "What do I have this week?"
    - "Show me this week's calendar"

    Returns:
        Dictionary with this week's events
    """
    try:
        user_id = get_current_user_id()

        # Calculate this week's Monday and Sunday
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=7)  # Next Monday

        events, total = await CalendarService.get_user_events(
            user_id=user_id,
            start_date=datetime.combine(week_start, datetime.min.time()),
            end_date=datetime.combine(week_end, datetime.min.time()),
        )

        event_summaries = [_format_event_summary(e) for e in events]

        return {
            "message": f"You have {len(events)} event(s) this week.",
            "events": event_summaries,
            "total_count": total,
            "week": {
                "start": week_start.isoformat(),
                "end": week_end.isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Error getting this week's events: {e}")
        return {"error": str(e), "events": []}


@function_tool
async def search_events(query: str, limit: int = 10) -> Dict[str, Any]:
    """Search calendar events by title, description, or location.

    Use this when user asks:
    - "Find my meeting with John"
    - "Do I have any doctor appointments?"
    - "Search for team meetings"
    - "When is my dentist appointment?"

    Args:
        query: Search term (searches in title, description, location)
        limit: Maximum number of results (default: 10)

    Returns:
        Dictionary with matching events
    """
    try:
        user_id = get_current_user_id()
        events = await CalendarService.search_events(user_id, query, limit)

        if not events:
            return {
                "message": f"No events found matching '{query}'.",
                "events": [],
                "query": query,
            }

        event_details = [_format_event_detail(e) for e in events]

        return {
            "message": f"Found {len(events)} event(s) matching '{query}'.",
            "events": event_details,
            "query": query,
        }

    except Exception as e:
        logger.error(f"Error searching events: {e}")
        return {"error": str(e), "events": [], "query": query}


@function_tool
async def get_event_details(event_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific calendar event.

    Use this when user asks for more details about an event.

    Args:
        event_id: The event ID (from previous queries)

    Returns:
        Dictionary with full event details
    """
    try:
        event = await CalendarService.get_event_by_id(event_id)

        if not event:
            return {"error": f"Event {event_id} not found."}

        return _format_event_detail(event)

    except Exception as e:
        logger.error(f"Error getting event details: {e}")
        return {"error": str(e)}


@function_tool
async def check_availability(
    start_time_iso: str,
    end_time_iso: str,
) -> Dict[str, Any]:
    """Check if user is available during a specific time range.

    Use this when user asks:
    - "Am I free on Monday at 2pm?"
    - "Do I have anything at 3pm tomorrow?"
    - "Can I schedule a meeting at 10am on Friday?"

    Args:
        start_time_iso: Start time in ISO format (e.g., "2024-01-15T14:00:00Z")
        end_time_iso: End time in ISO format

    Returns:
        Dictionary with availability status and any conflicts
    """
    try:
        user_id = get_current_user_id()

        # Parse ISO times
        start_time = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end_time_iso.replace("Z", "+00:00"))

        is_available, conflicts = await CalendarService.check_availability(
            user_id, start_time, end_time
        )

        if is_available:
            return {
                "available": True,
                "message": f"You're free from {start_time.strftime('%I:%M%p')} to {end_time.strftime('%I:%M%p')}.",
                "conflicts": [],
            }
        else:
            conflict_summaries = [_format_event_summary(e) for e in conflicts]
            return {
                "available": False,
                "message": f"You have {len(conflicts)} conflicting event(s).",
                "conflicts": conflict_summaries,
            }

    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        return {"error": str(e), "available": None}


@function_tool
async def create_calendar_event(
    title: str,
    start_time_iso: str,
    end_time_iso: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a new calendar event.

    Use this when user asks to:
    - "Schedule a meeting..."
    - "Add an event..."
    - "Create a calendar entry..."
    - "Block time for..."

    Args:
        title: Event title/summary
        start_time_iso: Start time in ISO format (e.g., "2024-01-15T14:00:00Z")
        end_time_iso: End time in ISO format
        description: Event description (optional)
        location: Event location (optional)
        attendees: List of attendee email addresses (optional)

    Returns:
        Dictionary with created event details
    """
    try:
        user_id = get_current_user_id()

        # Get user's primary Google Calendar integration
        integration = await Integration.find_one(
            {
                "user_id": user_id,
                "integration_type": IntegrationType.GOOGLE,
                "is_active": True,
            }
        )

        if not integration:
            return {
                "error": "No active Google Calendar integration found. Please connect your Google account first."
            }

        # Get user's primary calendar
        primary_calendar = await Calendar.find_one(
            {
                "user_id": user_id,
                "integration_id": integration.id,
                "is_primary": True,
            }
        )

        if not primary_calendar:
            # Fallback to first calendar
            primary_calendar = await Calendar.find_one(
                {
                    "user_id": user_id,
                    "integration_id": integration.id,
                }
            )

        if not primary_calendar:
            return {"error": "No calendar found. Please sync your calendars first."}

        # Parse times
        start_time = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end_time_iso.replace("Z", "+00:00"))

        # Create event via Google Calendar API
        event_data = await GoogleCalendarService.create_event(
            integration=integration,
            calendar_id=primary_calendar.provider_calendar_id,
            summary=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            attendees=attendees,
        )

        if not event_data:
            return {"error": "Failed to create event."}

        # Save event to database
        new_event = CalendarEvent(
            **event_data,
            user_id=user_id,
            integration_id=integration.id,
            calendar_doc_id=primary_calendar.id,
        )
        await new_event.insert()

        return {
            "success": True,
            "message": f"✅ Created event '{title}' on {start_time.strftime('%A, %B %d at %I:%M%p')}",
            "event": _format_event_detail(new_event),
        }

    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        return {"error": str(e), "success": False}


# Export all calendar tools
CALENDAR_TOOLS = [
    sync_calendars,
    get_upcoming_events,
    get_today_events,
    get_tomorrow_events,
    get_this_week_events,
    search_events,
    get_event_details,
    check_availability,
    create_calendar_event,
]
