"""Calendar service layer."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from beanie import PydanticObjectId

from app.calendar.google_calendar_service import GoogleCalendarService
from app.calendar.models import Calendar, CalendarEvent, EventStatus
from app.integrations.models import Integration, IntegrationType

logger = logging.getLogger(__name__)


class CalendarService:
    """Calendar service for managing calendars and events."""

    @staticmethod
    async def sync_calendar(user_id: PydanticObjectId) -> dict:
        """Sync calendar events from all connected integrations.

        Args:
            user_id: User ID to sync calendars for

        Returns:
            Sync statistics
        """
        try:
            # Get all Google integrations for this user
            integrations = await Integration.find(
                {
                    "user_id": user_id,
                    "integration_type": IntegrationType.GOOGLE,
                    "is_active": True,
                }
            ).to_list()

            if not integrations:
                return {
                    "synced_count": 0,
                    "new_events": 0,
                    "updated_events": 0,
                    "last_sync": datetime.utcnow(),
                    "calendars_synced": 0,
                }

            total_new = 0
            total_updated = 0
            total_calendars = 0

            for integration in integrations:
                # Sync calendars first
                calendars = await GoogleCalendarService.fetch_calendars(integration)
                for cal_data in calendars:
                    # Upsert calendar
                    await Calendar.find_one(
                        {
                            "user_id": user_id,
                            "provider_calendar_id": cal_data["provider_calendar_id"],
                        }
                    ).upsert(
                        {
                            "$set": {
                                **cal_data,
                                "user_id": user_id,
                                "integration_id": integration.id,
                                "last_synced_at": datetime.utcnow(),
                            }
                        },
                        on_insert=Calendar,
                    )
                    total_calendars += 1

                # Get selected calendars for this integration
                user_calendars = await Calendar.find(
                    {
                        "user_id": user_id,
                        "integration_id": integration.id,
                        "is_selected": True,
                    }
                ).to_list()

                # Sync events from each selected calendar
                for calendar in user_calendars:
                    # Fetch events from the last 30 days and next 90 days
                    time_min = datetime.utcnow() - timedelta(days=30)
                    time_max = datetime.utcnow() + timedelta(days=90)

                    events, next_page = await GoogleCalendarService.fetch_events(
                        integration=integration,
                        calendar_id=calendar.provider_calendar_id,
                        time_min=time_min,
                        time_max=time_max,
                    )

                    for event_data in events:
                        # Check if event exists
                        existing_event = await CalendarEvent.find_one(
                            {"event_id": event_data["event_id"]}
                        )

                        if existing_event:
                            # Update existing event
                            await existing_event.set(
                                {
                                    **event_data,
                                    "user_id": user_id,
                                    "integration_id": integration.id,
                                    "calendar_doc_id": calendar.id,
                                    "last_synced_at": datetime.utcnow(),
                                }
                            )
                            total_updated += 1
                        else:
                            # Create new event
                            new_event = CalendarEvent(
                                **event_data,
                                user_id=user_id,
                                integration_id=integration.id,
                                calendar_doc_id=calendar.id,
                                last_synced_at=datetime.utcnow(),
                            )
                            await new_event.insert()
                            total_new += 1

            logger.info(
                f"Synced {total_calendars} calendars, {total_new} new events, {total_updated} updated events for user {user_id}"
            )

            return {
                "synced_count": total_new + total_updated,
                "new_events": total_new,
                "updated_events": total_updated,
                "last_sync": datetime.utcnow(),
                "calendars_synced": total_calendars,
            }

        except Exception as e:
            logger.error(f"Error syncing calendar for user {user_id}: {e}")
            raise

    @staticmethod
    async def get_user_events(
        user_id: PydanticObjectId,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        calendar_id: Optional[PydanticObjectId] = None,
        status: Optional[EventStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[CalendarEvent], int]:
        """Get user calendar events with filters.

        Args:
            user_id: User ID
            start_date: Filter events starting after this date
            end_date: Filter events starting before this date
            calendar_id: Filter by specific calendar
            status: Filter by event status
            skip: Pagination skip
            limit: Pagination limit

        Returns:
            Tuple of (events list, total count)
        """
        # Build query
        query = {"user_id": user_id}

        if start_date or end_date:
            query["start_time"] = {}
            if start_date:
                query["start_time"]["$gte"] = start_date
            if end_date:
                query["start_time"]["$lte"] = end_date

        if calendar_id:
            query["calendar_doc_id"] = calendar_id

        if status:
            query["status"] = status

        # Get events
        events = (
            await CalendarEvent.find(query)
            .sort("-start_time")  # Most recent first
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        # Get total count
        total = await CalendarEvent.find(query).count()

        return events, total

    @staticmethod
    async def get_event_by_id(event_id: str) -> Optional[CalendarEvent]:
        """Get a specific event by its event_id.

        Args:
            event_id: Event ID

        Returns:
            CalendarEvent or None
        """
        return await CalendarEvent.find_one({"event_id": event_id})

    @staticmethod
    async def search_events(
        user_id: PydanticObjectId,
        query: str,
        limit: int = 20,
    ) -> List[CalendarEvent]:
        """Search events by title, description, or location.

        Args:
            user_id: User ID
            query: Search query
            limit: Maximum results

        Returns:
            List of matching events
        """
        # MongoDB text search on title, description, location
        events = await CalendarEvent.find(
            {
                "user_id": user_id,
                "$or": [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"description": {"$regex": query, "$options": "i"}},
                    {"location": {"$regex": query, "$options": "i"}},
                ],
            }
        ).limit(limit).to_list()

        return events

    @staticmethod
    async def check_availability(
        user_id: PydanticObjectId,
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[bool, List[CalendarEvent]]:
        """Check if user is available during a time range.

        Args:
            user_id: User ID
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Tuple of (is_available, conflicting_events)
        """
        # Find overlapping events
        conflicting_events = await CalendarEvent.find(
            {
                "user_id": user_id,
                "status": {"$ne": EventStatus.CANCELLED},
                "$or": [
                    # Event starts during the range
                    {
                        "start_time": {"$gte": start_time, "$lt": end_time},
                    },
                    # Event ends during the range
                    {
                        "end_time": {"$gt": start_time, "$lte": end_time},
                    },
                    # Event spans the entire range
                    {
                        "start_time": {"$lte": start_time},
                        "end_time": {"$gte": end_time},
                    },
                ],
            }
        ).to_list()

        is_available = len(conflicting_events) == 0
        return is_available, conflicting_events
