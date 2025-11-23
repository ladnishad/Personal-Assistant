# Calendar Management System - Implementation Guide

## Overview

A comprehensive calendar management system has been implemented for LifeOS, following the same architecture patterns as the email system. The implementation includes:

- **Google Calendar Integration** - Sync calendars and events from Google Calendar
- **Calendar Management Agent** - Specialized AI agent for calendar operations
- **Rich Calendar Tools** - 9 function tools for comprehensive calendar management
- **Database Models** - Calendar and CalendarEvent models with full metadata
- **API Endpoints** - RESTful endpoints for calendar operations

---

## 🏗️ Architecture

### Components Created

```
app/calendar/
├── __init__.py              # Module initialization
├── models.py                # Calendar and CalendarEvent models ✅ ENHANCED
├── google_calendar_service.py  # Google Calendar API integration ✅ NEW
├── service.py               # Calendar business logic ✅ ENHANCED
├── router.py                # API endpoints ✅ EXISTS
└── schemas.py               # Request/response schemas ✅ EXISTS

app/agent/
├── calendar_tools.py        # 9 calendar function tools ✅ NEW
└── calendar_agent.py        # Calendar Management Specialist ✅ NEW
```

---

## 📊 Database Models

### Calendar Model

Represents a user's calendar (e.g., "Work Calendar", "Personal Calendar").

**Key Fields:**
- `user_id` - Owner of the calendar
- `integration_id` - Google integration reference
- `provider_calendar_id` - Google Calendar ID
- `summary` - Calendar name
- `timezone` - Calendar timezone
- `is_primary` - Whether this is the user's primary calendar
- `is_selected` - Whether to sync events from this calendar
- `access_role` - owner/writer/reader
- `background_color`, `foreground_color` - Display colors

### CalendarEvent Model

Represents individual calendar events.

**Key Fields:**

**Identifiers:**
- `event_id` - Unique event ID
- `provider_calendar_id` - Which calendar this belongs to
- `icaluid` - iCalendar UID for interoperability

**Event Details:**
- `title` - Event summary
- `description` - Event description
- `location` - Event location
- `start_time`, `end_time` - Event times
- `timezone` - Event timezone
- `is_all_day` - All-day event flag

**Attendees & Organization:**
- `organizer` - Organizer email
- `organizer_name` - Organizer display name
- `attendees` - List of attendee dicts (email, response_status, etc.)
- `meeting_link` - Google Meet/Zoom link
- `conference_data` - Full conference details

**Recurrence:**
- `is_recurring` - Recurring event flag
- `recurrence_rule` - RRULE format
- `recurring_event_id` - Parent event ID for instances

**AI Insights** (Future Enhancement):
- `ai_summary` - Intelligent event summary
- `preparation_items` - What to prepare for the event
- `estimated_travel_time` - Travel time to location
- `is_important` - AI-determined importance
- `conflict_detected` - Overlapping events flag

---

## 🔧 Google Calendar Integration

### GoogleCalendarService

Located in `app/calendar/google_calendar_service.py`.

**Methods:**

1. **`fetch_calendars(integration)`**
   - Fetches all calendars from Google Calendar
   - Returns list of calendar dictionaries

2. **`fetch_events(integration, calendar_id, time_min, time_max, ...)`**
   - Fetches events from a specific calendar
   - Supports pagination via `page_token`
   - Default range: next 30 days

3. **`create_event(integration, calendar_id, summary, start_time, end_time, ...)`**
   - Creates a new event in Google Calendar
   - Supports description, location, attendees, reminders

4. **`update_event(integration, calendar_id, event_id, ...)`**
   - Updates an existing event
   - Partial updates supported

5. **`delete_event(integration, calendar_id, event_id)`**
   - Deletes an event from Google Calendar

**Authentication:**
- Reuses existing Google OAuth integration
- Automatically refreshes access tokens
- Same integration as Gmail

---

## 🤖 Calendar Agent

### Calendar Management Specialist

Specialized agent for calendar operations.

**Agent Name:** `"Calendar Management Specialist"`

**Capabilities:**
- View and search calendar events
- Check availability and scheduling conflicts
- Create new calendar events
- Provide intelligent scheduling suggestions
- Help users understand their schedule

**Tools Available:**
1. `sync_calendars` - Sync from Google Calendar
2. `get_upcoming_events` - Get events for next N days
3. `get_today_events` - Today's schedule
4. `get_tomorrow_events` - Tomorrow's schedule
5. `get_this_week_events` - This week's schedule
6. `search_events` - Search by keyword
7. `get_event_details` - Get full event details
8. `check_availability` - Check if free during time range
9. `create_calendar_event` - Create new event

**Handoff Triggers:**

The main agent transfers to Calendar Management Specialist when user asks about:
- Schedule queries ("What's on my calendar?")
- Availability checks ("Am I free at 2pm?")
- Event searches ("When is my dentist appointment?")
- Event creation ("Schedule a meeting...")
- Schedule overview ("What does my week look like?")

---

## 🛠️ Calendar Tools

### 1. sync_calendars()

Syncs calendars and events from Google Calendar.

**Use Cases:**
- "Refresh my calendar"
- "Sync my calendar"
- "Update my calendar"

**Returns:** Sync summary with count of calendars and events synced.

---

### 2. get_upcoming_events(days_ahead=7, limit=20)

Get upcoming events for the next N days.

**Parameters:**
- `days_ahead` - Number of days to look ahead (default: 7)
- `limit` - Max events to return (default: 20)

**Use Cases:**
- "What's on my calendar?"
- "Show me my schedule"
- "What do I have coming up?"

**Returns:** List of event summaries with times, locations, and attendees.

---

### 3. get_today_events()

Get all events scheduled for today.

**Use Cases:**
- "What's on my calendar today?"
- "What do I have today?"
- "Am I free today?"

**Returns:** Detailed list of today's events.

---

### 4. get_tomorrow_events()

Get all events scheduled for tomorrow.

**Use Cases:**
- "What's on my calendar tomorrow?"
- "What do I have tomorrow?"

**Returns:** Detailed list of tomorrow's events.

---

### 5. get_this_week_events()

Get all events for this week (Monday to Sunday).

**Use Cases:**
- "What's my schedule this week?"
- "Show me this week's calendar"

**Returns:** Events grouped by day.

---

### 6. search_events(query, limit=10)

Search events by title, description, or location.

**Parameters:**
- `query` - Search term
- `limit` - Max results (default: 10)

**Use Cases:**
- "Find my meeting with John"
- "When is my dentist appointment?"
- "Search for team meetings"

**Returns:** Matching events with full details.

---

### 7. get_event_details(event_id)

Get detailed information about a specific event.

**Parameters:**
- `event_id` - Event ID from previous queries

**Use Cases:**
- Getting more details after a search
- Viewing full event information

**Returns:** Complete event details including attendees, meeting link, description.

---

### 8. check_availability(start_time_iso, end_time_iso)

Check if user is free during a specific time range.

**Parameters:**
- `start_time_iso` - Start time in ISO format
- `end_time_iso` - End time in ISO format

**Use Cases:**
- "Am I free on Monday at 2pm?"
- "Do I have anything at 3pm tomorrow?"
- "Can I schedule a meeting at 10am Friday?"

**Returns:** Availability status and any conflicting events.

---

### 9. create_calendar_event(...)

Create a new calendar event.

**Parameters:**
- `title` - Event title (required)
- `start_time_iso` - Start time (required)
- `end_time_iso` - End time (required)
- `description` - Event description (optional)
- `location` - Event location (optional)
- `attendees` - List of attendee emails (optional)

**Use Cases:**
- "Schedule a team meeting next Monday at 10am for 1 hour"
- "Add a dentist appointment tomorrow at 2pm"
- "Block time for lunch at noon"

**Process:**
1. Checks for conflicts
2. Creates event in Google Calendar
3. Saves to database
4. Returns confirmation with event link

**Returns:** Success confirmation with event details.

---

## 📡 API Endpoints

Calendar router already exists at `app/calendar/router.py`.

### Endpoints:

**1. POST `/api/v1/calendar/sync`**
- Sync calendars from all connected integrations
- Returns sync statistics

**2. GET `/api/v1/calendar/events`**
- List calendar events with filters
- Query params: `start_date`, `end_date`, `page`, `page_size`
- Returns paginated event list

---

## 🔄 Integration with Main Agent

### Service Integration

**File:** `app/agent/service.py`

**Changes Made:**

1. **Import:**
   ```python
   from app.agent.calendar_agent import create_calendar_management_agent
   ```

2. **Agent Creation (both streaming and non-streaming):**
   ```python
   calendar_agent = create_calendar_management_agent()
   ```

3. **Handoffs Array:**
   ```python
   handoffs=[package_agent, computer_agent, calendar_agent]
   ```

4. **Instructions Updated:**
   - Added CALENDAR MANAGEMENT section
   - Explains when to transfer to Calendar Management Specialist
   - Lists capabilities and example queries
   - Updated final tools list to include "calendar management"

### Database Registration

**File:** `app/database.py`

**Changes Made:**

1. **Import:**
   ```python
   from app.calendar.models import Calendar, CalendarEvent
   ```

2. **Document Models:**
   ```python
   document_models=[
       ...
       Calendar,  # User's calendars from Google Calendar
       CalendarEvent,  # Calendar events
       ...
   ]
   ```

---

## 🎯 Usage Examples

### Example 1: View Today's Schedule

**User:** "What's on my calendar today?"

**Flow:**
1. Main agent recognizes calendar query
2. Transfers to Calendar Management Specialist
3. Specialist calls `get_today_events()`
4. Returns formatted list of today's events

**Response:**
```
You have 3 events today:

1. 📅 Team Standup (9:00 AM - 9:30 AM)
   Location: Google Meet
   Meeting link: https://meet.google.com/abc-defg-hij

2. 📅 Project Review (2:00 PM - 3:00 PM)
   Location: Conference Room A
   Attendees: John, Jane, Bob

3. 📅 Dentist Appointment (5:00 PM - 6:00 PM)
   Location: Downtown Dental Clinic
```

---

### Example 2: Check Availability

**User:** "Am I free tomorrow at 2pm for a 1-hour meeting?"

**Flow:**
1. Transfer to Calendar Management Specialist
2. Parse time: tomorrow 2pm-3pm
3. Call `check_availability(start_time, end_time)`
4. Return availability status

**Response (Available):**
```
✅ You're free from 2:00 PM to 3:00 PM tomorrow. Would you like me to schedule something?
```

**Response (Conflict):**
```
❌ You have a conflict:
- Project Review (2:00 PM - 3:00 PM)
  Location: Conference Room A

Alternative times available:
- 10:00 AM - 11:00 AM
- 3:30 PM - 4:30 PM
- 4:00 PM - 5:00 PM
```

---

### Example 3: Create Event

**User:** "Schedule a team meeting next Monday at 10am for 1 hour with john@company.com and jane@company.com"

**Flow:**
1. Transfer to Calendar Management Specialist
2. Parse details:
   - Title: "Team Meeting"
   - Time: Next Monday 10:00 AM - 11:00 AM
   - Attendees: [john@company.com, jane@company.com]
3. Call `check_availability()` - no conflicts
4. Call `create_calendar_event(...)`
5. Event created in Google Calendar
6. Event saved to database

**Response:**
```
✅ Created event 'Team Meeting' on Monday, January 15 at 10:00 AM

Event Details:
- Time: 10:00 AM - 11:00 AM (1 hour)
- Attendees: john@company.com, jane@company.com
- Calendar invites sent

View in Google Calendar: https://calendar.google.com/event?eid=...
```

---

### Example 4: Search Events

**User:** "When is my dentist appointment?"

**Flow:**
1. Transfer to Calendar Management Specialist
2. Call `search_events(query="dentist")`
3. Return matching events

**Response:**
```
Found your dentist appointment:

📅 Dentist Appointment
- Date: Thursday, January 18
- Time: 5:00 PM - 6:00 PM
- Location: Downtown Dental Clinic
- 123 Main Street

Preparation tip: Arrive 10 minutes early to fill out forms.
```

---

## ⚙️ Configuration

### Google Calendar Scopes

The existing Google OAuth integration provides calendar access through:
- `https://www.googleapis.com/auth/calendar.readonly` (read calendars)
- `https://www.googleapis.com/auth/calendar.events` (manage events)

These scopes are already included in the Google integration setup.

### Sync Settings

Default sync range (configurable in `CalendarService.sync_calendar`):
- **Past:** Last 30 days
- **Future:** Next 90 days

This ensures recent past events and upcoming events are synced.

---

## 🧪 Testing

### Manual Testing

1. **Connect Google Calendar:**
   ```
   User: "Connect my Google Calendar"
   → Follow OAuth flow
   ```

2. **Sync Calendars:**
   ```
   User: "Sync my calendar"
   → Agent calls sync_calendars()
   → Confirms sync complete
   ```

3. **View Events:**
   ```
   User: "What's on my calendar today?"
   → Agent calls get_today_events()
   → Shows today's schedule
   ```

4. **Create Event:**
   ```
   User: "Schedule a meeting tomorrow at 2pm for 1 hour"
   → Agent checks availability
   → Creates event
   → Confirms creation
   ```

---

## 🔮 Future Enhancements

### AI-Powered Features

1. **Smart Event Summaries**
   - AI-generated event summaries in `ai_summary` field
   - Context-aware preparation suggestions

2. **Intelligent Scheduling**
   - Suggest optimal meeting times based on:
     - Attendee availability
     - Time zone optimization
     - Energy levels (morning person vs. night owl)
     - Travel time between events

3. **Conflict Detection & Resolution**
   - Detect double-bookings
   - Suggest rescheduling options
   - Auto-detect buffer time needs

4. **Travel Time Intelligence**
   - Calculate travel time to event locations
   - Suggest departure times
   - Integrate with Maps API

5. **Meeting Preparation**
   - Extract action items from event descriptions
   - Find related documents
   - Suggest preparation tasks

### Additional Integrations

- **Outlook Calendar** integration
- **Apple Calendar** integration
- **CalDAV** support for universal calendar access

### Advanced Tools

- `reschedule_event()` - Modify existing events
- `delete_event()` - Remove events
- `find_meeting_time()` - Find common availability for multiple attendees
- `bulk_create_events()` - Create multiple events at once
- `get_calendar_analytics()` - Meeting time analysis, busy hours, etc.

---

## 📝 Summary

### What Was Implemented

✅ **Models:**
- Calendar model for user's calendars
- Enhanced CalendarEvent model with rich metadata
- Support for recurring events, attendees, conference links

✅ **Google Calendar Integration:**
- Fetch calendars and events
- Create, update, delete events
- Automatic token refresh
- Pagination support

✅ **Service Layer:**
- Full sync implementation
- Event queries with filters
- Search functionality
- Availability checking

✅ **Agent & Tools:**
- Calendar Management Specialist agent
- 9 comprehensive calendar tools
- Natural language time parsing
- Conflict detection

✅ **Database & API:**
- Calendar and CalendarEvent models registered
- API endpoints already in place
- Proper indexing for performance

✅ **Integration:**
- Main agent handoff configured
- System instructions updated
- Seamless user experience

### Files Modified

- ✅ `app/calendar/models.py` - Enhanced models
- ✅ `app/calendar/service.py` - Enhanced service layer
- ✅ `app/calendar/google_calendar_service.py` - **NEW** Google API integration
- ✅ `app/agent/calendar_tools.py` - **NEW** 9 calendar tools
- ✅ `app/agent/calendar_agent.py` - **NEW** Calendar agent
- ✅ `app/agent/service.py` - Updated for calendar handoff
- ✅ `app/database.py` - Registered Calendar model

### Ready to Use

The calendar system is **production-ready** and follows the exact same patterns as the email system. Users can now:

1. Connect their Google Calendar (reusing existing Google integration)
2. Sync calendars and events
3. Ask natural language questions about their schedule
4. Check availability
5. Create new events
6. Search for specific events
7. Get intelligent scheduling assistance

All through conversational interactions with the AI agent! 🎉
