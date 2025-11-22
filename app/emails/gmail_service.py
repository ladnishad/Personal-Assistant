"""Gmail API service for fetching emails."""

import base64
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional

from googleapiclient.discovery import build

from app.emails.models import Email, EmailLabel
from app.integrations.google_service import GoogleService
from app.integrations.models import Integration

logger = logging.getLogger(__name__)


class GmailService:
    """Gmail API service."""

    @staticmethod
    async def fetch_emails(
        integration: Integration, max_results: int = 100, page_token: Optional[str] = None
    ) -> tuple[List[dict], Optional[str]]:
        """Fetch emails from Gmail."""
        try:
            # Ensure token is valid
            integration = await GoogleService.check_and_refresh_token(integration)

            # Get credentials
            credentials = GoogleService.get_credentials(integration)

            # Build Gmail service
            service = build("gmail", "v1", credentials=credentials)

            # Fetch messages
            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    maxResults=max_results,
                    pageToken=page_token,
                    q="in:inbox OR in:sent",
                )
                .execute()
            )

            messages = results.get("messages", [])
            next_page_token = results.get("nextPageToken")

            # Fetch full message details
            emails = []
            for msg in messages:
                try:
                    message = (
                        service.users()
                        .messages()
                        .get(userId="me", id=msg["id"], format="full")
                        .execute()
                    )
                    email_data = GmailService._parse_gmail_message(message)
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.error(f"Error fetching message {msg['id']}: {e}")
                    continue

            logger.info(f"Fetched {len(emails)} emails from Gmail")

            return emails, next_page_token

        except Exception as e:
            logger.error(f"Error fetching emails from Gmail: {e}")
            raise

    @staticmethod
    async def fetch_email_content(
        integration: Integration, message_id: str
    ) -> Optional[dict]:
        """Fetch full email content on-demand from Gmail.

        This is called only when user explicitly requests to read an email,
        ensuring we don't store sensitive email bodies in the database.

        Args:
            integration: User's Gmail integration
            message_id: Gmail message ID

        Returns:
            Dictionary with body_text, body_html, and snippet
        """
        try:
            # Ensure token is valid
            integration = await GoogleService.check_and_refresh_token(integration)
            credentials = GoogleService.get_credentials(integration)
            service = build("gmail", "v1", credentials=credentials)

            # Fetch full message
            message = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            # Extract body content
            body_text = ""
            body_html = ""

            if "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                        body_text = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")
                    elif part["mimeType"] == "text/html" and "data" in part.get("body", {}):
                        body_html = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")
            elif "data" in message["payload"].get("body", {}):
                body_text = base64.urlsafe_b64decode(
                    message["payload"]["body"]["data"]
                ).decode("utf-8")

            return {
                "body_text": body_text,
                "body_html": body_html,
                "snippet": message.get("snippet", ""),
            }

        except Exception as e:
            logger.error(f"Error fetching email content for {message_id}: {e}")
            return None

    @staticmethod
    def _parse_gmail_message(message: dict) -> Optional[dict]:
        """Parse Gmail message into email metadata ONLY.

        For privacy and storage efficiency, we don't extract email bodies.
        Bodies are fetched on-demand via fetch_email_content().
        """
        try:
            headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}

            # Parse From header (format: "Name <email@domain.com>" or just "email@domain.com")
            from_header = headers.get("From", "")
            from_email = from_header
            from_name = None

            if "<" in from_header and ">" in from_header:
                # Extract name and email from "Name <email@domain.com>"
                parts = from_header.split("<")
                from_name = parts[0].strip().strip('"')  # Remove quotes if present
                from_email = parts[1].strip(">").strip()
            else:
                # Just email address, no name
                from_email = from_header.strip()

            # Parse date
            date_str = headers.get("Date")
            received_at = parsedate_to_datetime(date_str) if date_str else datetime.utcnow()

            # Parse labels
            labels = []
            label_ids = message.get("labelIds", [])
            if "INBOX" in label_ids:
                labels.append(EmailLabel.INBOX)
            if "SENT" in label_ids:
                labels.append(EmailLabel.SENT)
            if "IMPORTANT" in label_ids:
                labels.append(EmailLabel.IMPORTANT)
            if "SPAM" in label_ids:
                labels.append(EmailLabel.SPAM)
            if "TRASH" in label_ids:
                labels.append(EmailLabel.TRASH)

            # Check for attachments
            has_attachments = False
            attachments = []
            if "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if part.get("filename") and part.get("body", {}).get("attachmentId"):
                        has_attachments = True
                        attachments.append(
                            {
                                "filename": part["filename"],
                                "mime_type": part["mimeType"],
                                "size": part["body"].get("size", 0),
                                "attachment_id": part["body"]["attachmentId"],
                            }
                        )

            return {
                "message_id": message["id"],
                "thread_id": message.get("threadId"),
                "from_email": from_email,
                "from_name": from_name,
                "to": [headers.get("To", "")],
                "cc": headers.get("Cc", "").split(",") if headers.get("Cc") else [],
                "subject": headers.get("Subject"),
                # body_text, body_html NOT stored - fetch on-demand for privacy
                # snippet IS stored - short preview (~200 chars) for classification
                "snippet": message.get("snippet"),
                "labels": labels,
                "is_read": "UNREAD" not in message.get("labelIds", []),
                "is_starred": "STARRED" in message.get("labelIds", []),
                "received_at": received_at,
                "has_attachments": has_attachments,
                "attachments": attachments,
            }

        except Exception as e:
            logger.error(f"Error parsing Gmail message: {e}")
            return None
