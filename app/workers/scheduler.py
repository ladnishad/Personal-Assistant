"""APScheduler configuration and job scheduling."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = AsyncIOScheduler()


def setup_jobs():
    """Set up all scheduled jobs."""
    from app.workers.tasks import (
        check_reminders_job,
        refresh_tokens_job,
        sync_calendar_job,
        sync_emails_job,
    )

    # Email sync job
    scheduler.add_job(
        sync_emails_job,
        trigger=IntervalTrigger(minutes=settings.email_sync_interval_minutes),
        id="sync_emails",
        name="Sync emails from integrations",
        replace_existing=True,
    )
    logger.info(
        f"Scheduled email sync job every {settings.email_sync_interval_minutes} minutes"
    )

    # Calendar sync job
    scheduler.add_job(
        sync_calendar_job,
        trigger=IntervalTrigger(minutes=settings.calendar_sync_interval_minutes),
        id="sync_calendar",
        name="Sync calendar events from integrations",
        replace_existing=True,
    )
    logger.info(
        f"Scheduled calendar sync job every {settings.calendar_sync_interval_minutes} minutes"
    )

    # Reminder check job
    scheduler.add_job(
        check_reminders_job,
        trigger=IntervalTrigger(minutes=settings.reminder_check_interval_minutes),
        id="check_reminders",
        name="Check and send reminders",
        replace_existing=True,
    )
    logger.info(
        f"Scheduled reminder check job every {settings.reminder_check_interval_minutes} minutes"
    )

    # Token refresh job (daily)
    scheduler.add_job(
        refresh_tokens_job,
        trigger=IntervalTrigger(hours=24),
        id="refresh_tokens",
        name="Refresh OAuth tokens",
        replace_existing=True,
    )
    logger.info("Scheduled token refresh job every 24 hours")


# Set up jobs when module is imported
if settings.enable_scheduler:
    setup_jobs()
