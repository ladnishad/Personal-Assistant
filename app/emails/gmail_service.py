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
    def _parse_gmail_message(message: dict) -> Optional[dict]:
        """Parse Gmail message into email data."""
        try:
            headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}

            # Extract body
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
                "from_email": headers.get("From", ""),
                "to": [headers.get("To", "")],
                "cc": headers.get("Cc", "").split(",") if headers.get("Cc") else [],
                "subject": headers.get("Subject"),
                "body_text": body_text,
                "body_html": body_html,
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
