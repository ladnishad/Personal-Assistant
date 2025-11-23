"""Google Calendar API service for fetching and managing calendar events."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from googleapiclient.discovery import build

from app.calendar.models import Calendar, CalendarEvent, EventStatus
from app.integrations.google_service import GoogleService
from app.integrations.models import Integration

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Google Calendar API service."""

    @staticmethod
    async def fetch_calendars(integration: Integration) -> List[dict]:
        """Fetch all calendars from Google Calendar.

        Args:
            integration: User's Google integration

        Returns:
            List of calendar dictionaries
        """
        try:
            # Ensure token is valid
            integration = await GoogleService.check_and_refresh_token(integration)
            credentials = GoogleService.get_credentials(integration)

            # Build Calendar service
            service = build("calendar", "v3", credentials=credentials)

            # Fetch calendar list
            calendar_list = service.calendarList().list().execute()

            calendars = []
            for cal in calendar_list.get("items", []):
                calendar_data = {
                    "provider_calendar_id": cal["id"],
                    "summary": cal.get("summary", "Unknown Calendar"),
                    "description": cal.get("description"),
                    "timezone": cal.get("timeZone", "UTC"),
                    "background_color": cal.get("backgroundColor"),
                    "foreground_color": cal.get("foregroundColor"),
                    "is_primary": cal.get("primary", False),
                    "is_selected": cal.get("selected", True),
                    "access_role": cal.get("accessRole"),
                    "is_hidden": cal.get("hidden", False),
                }
                calendars.append(calendar_data)

            logger.info(f"Fetched {len(calendars)} calendars from Google Calendar")
            return calendars

        except Exception as e:
            logger.error(f"Error fetching calendars from Google: {e}")
            raise

    @staticmethod
    async def fetch_events(
        integration: Integration,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 250,
        single_events: bool = True,
        page_token: Optional[str] = None,
    ) -> Tuple[List[dict], Optional[str]]:
        """Fetch events from a specific Google Calendar.

        Args:
            integration: User's Google integration
            calendar_id: Calendar ID (default: primary)
            time_min: Start time for events
            time_max: End time for events
            max_results: Maximum number of events to return
            single_events: Expand recurring events into instances
            page_token: Pagination token

        Returns:
            Tuple of (list of event dictionaries, next page token)
        """
        try:
            # Ensure token is valid
            integration = await GoogleService.check_and_refresh_token(integration)
            credentials = GoogleService.get_credentials(integration)

            # Build Calendar service
            service = build("calendar", "v3", credentials=credentials)

            # Default time range if not specified (next 30 days)
            if not time_min:
                time_min = datetime.utcnow()
            if not time_max:
                time_max = time_min + timedelta(days=30)

            # Fetch events
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min.isoformat() + "Z",
                    timeMax=time_max.isoformat() + "Z",
                    maxResults=max_results,
                    singleEvents=single_events,
                    orderBy="startTime" if single_events else None,
                    pageToken=page_token,
                )
                .execute()
            )

            events = []
            for event in events_result.get("items", []):
                event_data = GoogleCalendarService._parse_google_event(event, calendar_id)
                if event_data:
                    events.append(event_data)

            next_page_token = events_result.get("nextPageToken")

            logger.info(f"Fetched {len(events)} events from calendar {calendar_id}")
            return events, next_page_token

        except Exception as e:
            logger.error(f"Error fetching events from Google Calendar: {e}")
            raise

    @staticmethod
    def _parse_google_event(event: dict, calendar_id: str) -> Optional[dict]:
        """Parse Google Calendar event into our format.

        Args:
            event: Google Calendar event object
            calendar_id: Calendar ID this event belongs to

        Returns:
            Parsed event dictionary
        """
        try:
            # Extract start and end times
            start = event.get("start", {})
            end = event.get("end", {})

            # Handle all-day events vs. timed events
            is_all_day = "date" in start

            if is_all_day:
                start_time = datetime.fromisoformat(start["date"])
                end_time = datetime.fromisoformat(end["date"])
            else:
                start_time = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))

            # Extract attendees
            attendees = []
            for attendee in event.get("attendees", []):
                attendees.append({
                    "email": attendee.get("email"),
                    "display_name": attendee.get("displayName"),
                    "response_status": attendee.get("responseStatus"),
                    "is_organizer": attendee.get("organizer", False),
                    "is_optional": attendee.get("optional", False),
                    "comment": attendee.get("comment"),
                })

            # Extract reminders
            reminders = []
            reminder_overrides = event.get("reminders", {}).get("overrides", [])
            for reminder in reminder_overrides:
                reminders.append({
                    "method": reminder.get("method"),
                    "minutes_before": reminder.get("minutes"),
                })

            # Extract conference/meeting data
            conference_data = event.get("conferenceData")
            meeting_link = None
            if conference_data:
                entry_points = conference_data.get("entryPoints", [])
                for entry in entry_points:
                    if entry.get("entryPointType") == "video":
                        meeting_link = entry.get("uri")
                        break

            # Handle status
            status = event.get("status", "confirmed").lower()
            event_status = EventStatus.CONFIRMED
            if status == "tentative":
                event_status = EventStatus.TENTATIVE
            elif status == "cancelled":
                event_status = EventStatus.CANCELLED

            return {
                "event_id": event["id"],
                "provider_calendar_id": calendar_id,
                "icaluid": event.get("iCalUID"),
                "title": event.get("summary", "(No title)"),
                "description": event.get("description"),
                "location": event.get("location"),
                "start_time": start_time,
                "end_time": end_time,
                "timezone": start.get("timeZone") or end.get("timeZone") or "UTC",
                "is_all_day": is_all_day,
                "is_recurring": "recurrence" in event or "recurringEventId" in event,
                "recurrence_rule": event.get("recurrence", [None])[0] if event.get("recurrence") else None,
                "recurring_event_id": event.get("recurringEventId"),
                "status": event_status,
                "creator_email": event.get("creator", {}).get("email"),
                "organizer": event.get("organizer", {}).get("email"),
                "organizer_name": event.get("organizer", {}).get("displayName"),
                "attendees": attendees,
                "meeting_link": meeting_link,
                "conference_data": conference_data,
                "hangout_link": event.get("hangoutLink"),
                "reminders": reminders,
                "use_default_reminders": event.get("reminders", {}).get("useDefault", True),
                "color_id": event.get("colorId"),
                "html_link": event.get("htmlLink"),
                "attachments": event.get("attachments", []),
                "created_at": datetime.fromisoformat(
                    event["created"].replace("Z", "+00:00")
                ) if event.get("created") else datetime.utcnow(),
                "updated_at": datetime.fromisoformat(
                    event["updated"].replace("Z", "+00:00")
                ) if event.get("updated") else datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Error parsing Google Calendar event {event.get('id')}: {e}")
            return None

    @staticmethod
    async def create_event(
        integration: Integration,
        calendar_id: str,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[List[dict]] = None,
    ) -> Optional[dict]:
        """Create a new event in Google Calendar.

        Args:
            integration: User's Google integration
            calendar_id: Calendar ID to create event in
            summary: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            location: Event location
            attendees: List of attendee email addresses
            reminders: List of reminder dicts

        Returns:
            Created event data
        """
        try:
            integration = await GoogleService.check_and_refresh_token(integration)
            credentials = GoogleService.get_credentials(integration)
            service = build("calendar", "v3", credentials=credentials)

            # Build event body
            event_body = {
                "summary": summary,
                "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
            }

            if description:
                event_body["description"] = description
            if location:
                event_body["location"] = location

            if attendees:
                event_body["attendees"] = [{"email": email} for email in attendees]

            if reminders:
                event_body["reminders"] = {
                    "useDefault": False,
                    "overrides": reminders,
                }

            # Create event
            created_event = (
                service.events().insert(calendarId=calendar_id, body=event_body).execute()
            )

            logger.info(f"Created event {created_event['id']} in calendar {calendar_id}")
            return GoogleCalendarService._parse_google_event(created_event, calendar_id)

        except Exception as e:
            logger.error(f"Error creating event in Google Calendar: {e}")
            raise

    @staticmethod
    async def update_event(
        integration: Integration,
        calendar_id: str,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Optional[dict]:
        """Update an existing event in Google Calendar.

        Args:
            integration: User's Google integration
            calendar_id: Calendar ID
            event_id: Event ID to update
            summary: New event title
            start_time: New start time
            end_time: New end time
            description: New description
            location: New location

        Returns:
            Updated event data
        """
        try:
            integration = await GoogleService.check_and_refresh_token(integration)
            credentials = GoogleService.get_credentials(integration)
            service = build("calendar", "v3", credentials=credentials)

            # Get current event
            current_event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )

            # Update fields
            if summary is not None:
                current_event["summary"] = summary
            if description is not None:
                current_event["description"] = description
            if location is not None:
                current_event["location"] = location
            if start_time is not None:
                current_event["start"] = {"dateTime": start_time.isoformat(), "timeZone": "UTC"}
            if end_time is not None:
                current_event["end"] = {"dateTime": end_time.isoformat(), "timeZone": "UTC"}

            # Update event
            updated_event = (
                service.events()
                .update(calendarId=calendar_id, eventId=event_id, body=current_event)
                .execute()
            )

            logger.info(f"Updated event {event_id} in calendar {calendar_id}")
            return GoogleCalendarService._parse_google_event(updated_event, calendar_id)

        except Exception as e:
            logger.error(f"Error updating event in Google Calendar: {e}")
            raise

    @staticmethod
    async def delete_event(
        integration: Integration,
        calendar_id: str,
        event_id: str,
    ) -> bool:
        """Delete an event from Google Calendar.

        Args:
            integration: User's Google integration
            calendar_id: Calendar ID
            event_id: Event ID to delete

        Returns:
            True if successful
        """
        try:
            integration = await GoogleService.check_and_refresh_token(integration)
            credentials = GoogleService.get_credentials(integration)
            service = build("calendar", "v3", credentials=credentials)

            # Delete event
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

            logger.info(f"Deleted event {event_id} from calendar {calendar_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting event from Google Calendar: {e}")
            raise
