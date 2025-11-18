"""Email service layer."""

import logging
from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId

from app.emails.gmail_service import GmailService
from app.emails.models import Email, EmailLabel
from app.integrations.models import Integration, IntegrationType

logger = logging.getLogger(__name__)


class EmailService:
    """Email service."""

    @staticmethod
    async def sync_emails(user_id: PydanticObjectId) -> dict:
        """Sync emails from all connected integrations."""
        # Get all active integrations for user
        integrations = await Integration.find(
            Integration.user_id == user_id, Integration.is_active == True
        ).to_list()

        total_synced = 0
        total_new = 0
        total_updated = 0

        for integration in integrations:
            try:
                if integration.integration_type == IntegrationType.GOOGLE:
                    synced, new, updated = await EmailService._sync_gmail(integration)
                    total_synced += synced
                    total_new += new
                    total_updated += updated
                # Add Microsoft sync here when implemented

            except Exception as e:
                logger.error(
                    f"Error syncing emails for integration {integration.id}: {e}"
                )
                continue

        return {
            "synced_count": total_synced,
            "new_emails": total_new,
            "updated_emails": total_updated,
            "last_sync": datetime.utcnow(),
        }

    @staticmethod
    async def _sync_gmail(integration: Integration) -> tuple[int, int, int]:
        """Sync emails from Gmail."""
        synced = 0
        new = 0
        updated = 0

        try:
            # Fetch emails from Gmail
            emails_data, _ = await GmailService.fetch_emails(integration, max_results=10)

            for email_data in emails_data:
                # Check if email already exists
                existing = await Email.find_one(Email.message_id == email_data["message_id"])

                if existing:
                    # Update existing email
                    existing.is_read = email_data["is_read"]
                    existing.is_starred = email_data["is_starred"]
                    existing.labels = email_data["labels"]
                    await existing.save()
                    updated += 1
                else:
                    # Create new email
                    email = Email(
                        user_id=integration.user_id,
                        integration_id=integration.id,
                        **email_data,
                    )
                    await email.insert()
                    new += 1

                synced += 1

            # Update integration sync state
            integration.last_email_sync = datetime.utcnow()
            await integration.save()

            logger.info(
                f"Gmail sync complete: {synced} total, {new} new, {updated} updated"
            )

        except Exception as e:
            logger.error(f"Error syncing Gmail: {e}")
            raise

        return synced, new, updated

    @staticmethod
    async def get_user_emails(
        user_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 50,
        is_read: Optional[bool] = None,
        is_starred: Optional[bool] = None,
        labels: Optional[List[EmailLabel]] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Email], int]:
        """Get user emails with filters."""
        # Build query
        query = {"user_id": user_id}

        if is_read is not None:
            query["is_read"] = is_read

        if is_starred is not None:
            query["is_starred"] = is_starred

        if labels:
            query["labels"] = {"$in": labels}

        # Search in subject or body
        if search:
            query["$or"] = [
                {"subject": {"$regex": search, "$options": "i"}},
                {"body_text": {"$regex": search, "$options": "i"}},
                {"from_email": {"$regex": search, "$options": "i"}},
            ]

        # Get emails
        emails = (
            await Email.find(query)
            .sort(-Email.received_at)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        # Get total count
        total = await Email.find(query).count()

        return emails, total
