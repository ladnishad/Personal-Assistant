"""Background job tasks."""

import logging
from datetime import datetime, timedelta

from app.emails.service import EmailService
from app.integrations.google_service import GoogleService
from app.integrations.microsoft_service import MicrosoftService
from app.integrations.models import Integration, IntegrationType
from app.tasks.models import Task

logger = logging.getLogger(__name__)


async def sync_emails_job():
    """Background job to sync emails for all users."""
    logger.info("Starting email sync job")

    try:
        # Get all active integrations
        integrations = await Integration.find(Integration.is_active == True).to_list()

        synced_count = 0
        for integration in integrations:
            try:
                # Sync emails for this integration's user
                result = await EmailService.sync_emails(integration.user_id)
                synced_count += result["synced_count"]
                logger.debug(
                    f"Synced {result['synced_count']} emails for user {integration.user_id}"
                )
            except Exception as e:
                logger.error(
                    f"Error syncing emails for integration {integration.id}: {e}"
                )
                continue

        logger.info(f"Email sync job completed. Total synced: {synced_count}")

    except Exception as e:
        logger.error(f"Error in email sync job: {e}")


async def sync_calendar_job():
    """Background job to sync calendar events for all users."""
    logger.info("Starting calendar sync job")

    try:
        # Placeholder for calendar sync implementation
        # Similar to email sync
        logger.info("Calendar sync job completed")

    except Exception as e:
        logger.error(f"Error in calendar sync job: {e}")


async def check_reminders_job():
    """Background job to check and send reminders."""
    logger.info("Starting reminder check job")

    try:
        # Find tasks with reminders that are due
        now = datetime.utcnow()
        tasks_with_reminders = await Task.find(
            Task.reminder_at <= now,
            Task.reminder_sent == False,
            Task.status != "done",
        ).to_list()

        logger.info(f"Found {len(tasks_with_reminders)} reminders to send")

        for task in tasks_with_reminders:
            try:
                # TODO: Implement actual reminder sending (email, push notification, etc.)
                logger.info(f"Would send reminder for task: {task.title}")

                # Mark reminder as sent
                task.reminder_sent = True
                await task.save()

            except Exception as e:
                logger.error(f"Error sending reminder for task {task.id}: {e}")
                continue

        logger.info("Reminder check job completed")

    except Exception as e:
        logger.error(f"Error in reminder check job: {e}")


async def refresh_tokens_job():
    """Background job to refresh OAuth tokens."""
    logger.info("Starting token refresh job")

    try:
        # Find integrations with tokens expiring in next 24 hours
        expiry_threshold = datetime.utcnow() + timedelta(hours=24)

        integrations = await Integration.find(
            Integration.is_active == True,
            Integration.token_expiry <= expiry_threshold,
        ).to_list()

        logger.info(f"Found {len(integrations)} tokens to refresh")

        refreshed_count = 0
        for integration in integrations:
            try:
                if integration.integration_type == IntegrationType.GOOGLE:
                    await GoogleService.refresh_access_token(integration)
                    refreshed_count += 1
                elif integration.integration_type == IntegrationType.MICROSOFT:
                    await MicrosoftService.refresh_access_token(integration)
                    refreshed_count += 1

                logger.debug(f"Refreshed token for integration {integration.id}")

            except Exception as e:
                logger.error(
                    f"Error refreshing token for integration {integration.id}: {e}"
                )
                # Mark integration as inactive if refresh fails
                integration.is_active = False
                await integration.save()
                continue

        logger.info(f"Token refresh job completed. Refreshed: {refreshed_count}")

    except Exception as e:
        logger.error(f"Error in token refresh job: {e}")
