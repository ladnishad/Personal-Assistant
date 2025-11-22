"""Email summarization service using LLM."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from app.emails.gmail_service import GmailService
from app.emails.models import Email
from app.integrations.models import Integration

logger = logging.getLogger(__name__)

# Initialize OpenAI client with validation
if not settings.openai_api_key or settings.openai_api_key == "":
    logger.warning(
        "OPENAI_API_KEY not set - email summarization will be disabled. "
        "Set OPENAI_API_KEY environment variable to enable AI summaries."
    )
    openai_client = None
else:
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


class EmailSummary(BaseModel):
    """Email summary response from LLM."""

    summary: str  # 2-3 sentence summary
    action_items: List[str]  # Extracted action items
    key_people: List[str]  # Important people mentioned
    key_dates: List[str]  # Important dates (ISO format strings)
    priority_score: float  # 0-1, higher = more important
    requires_response: bool  # Does this need a reply?
    sentiment: str  # positive/neutral/negative/urgent


class EmailSummarizer:
    """Service for generating AI summaries of emails."""

    # Categories that should be eagerly summarized
    EAGER_CATEGORIES = [
        "personal",
        "financial",
        "package_shipping",
        "travel",
        "calendar_event",
        "ecommerce_order",
    ]

    # Categories to skip (low value)
    SKIP_CATEGORIES = ["promotional", "spam", "notification"]

    @staticmethod
    async def summarize_email(
        email: Email, integration: Integration, force: bool = False
    ) -> Optional[EmailSummary]:
        """Generate AI summary for an email.

        Args:
            email: Email document to summarize
            integration: User's email integration (for fetching content)
            force: Force summarization even if already summarized

        Returns:
            EmailSummary object or None if summarization failed/skipped
        """
        try:
            # Skip if already summarized (unless forced)
            if email.ai_summary and not force:
                logger.info(f"Email {email.id} already summarized, skipping")
                return None

            # Skip low-value categories
            if (
                email.email_category in EmailSummarizer.SKIP_CATEGORIES
                and not force
            ):
                logger.info(
                    f"Skipping summarization for category {email.email_category}"
                )
                return None

            # Fetch email content on-demand
            content = await GmailService.fetch_email_content(
                integration, email.message_id
            )

            if not content or not content.get("body_text"):
                logger.warning(f"No content available for email {email.id}")
                return None

            # Use body_text for summarization
            email_text = content["body_text"]

            # Skip very short emails (snippet is enough)
            if len(email_text) < 100:
                logger.info(f"Email {email.id} too short to summarize")
                return None

            # Truncate very long emails (to save tokens)
            max_chars = 4000
            if len(email_text) > max_chars:
                email_text = email_text[:max_chars] + "... [truncated]"

            # Generate summary using OpenAI
            summary = await EmailSummarizer._generate_summary(
                subject=email.subject or "No subject",
                sender=email.from_email,
                body=email_text,
                category=email.email_category,
            )

            # Update email document
            if summary:
                email.ai_summary = summary.summary
                email.action_items = summary.action_items
                email.key_people = summary.key_people

                # Parse dates with error handling (LLM might return invalid formats)
                parsed_dates = []
                for date_str in summary.key_dates:
                    try:
                        parsed_dates.append(datetime.fromisoformat(date_str))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid date format from LLM: {date_str} - {e}")
                        # Skip invalid dates rather than crashing
                        continue
                email.key_dates = parsed_dates

                email.priority_score = summary.priority_score
                email.requires_response = summary.requires_response
                email.sentiment = summary.sentiment
                email.summarized_at = datetime.utcnow()
                email.summary_model = "gpt-4o-mini"
                await email.save()

                logger.info(f"Successfully summarized email {email.id}")

            return summary

        except Exception as e:
            logger.error(f"Error summarizing email {email.id}: {e}", exc_info=True)
            return None

    @staticmethod
    async def _generate_summary(
        subject: str, sender: str, body: str, category: Optional[str] = None
    ) -> Optional[EmailSummary]:
        """Generate summary using OpenAI LLM.

        Args:
            subject: Email subject
            sender: Email sender
            body: Email body text
            category: Email category (if classified)

        Returns:
            EmailSummary object or None
        """
        # Check if OpenAI client is available
        if openai_client is None:
            logger.warning("OpenAI client not initialized - skipping summarization")
            return None

        try:
            prompt = f"""Analyze this email and extract key information.

Subject: {subject}
From: {sender}
Category: {category or 'unknown'}

Email body:
{body}

Provide a structured analysis with:
1. A concise 2-3 sentence summary of the email
2. Any action items or tasks mentioned
3. Important people mentioned (names, not email addresses)
4. Important dates mentioned (in ISO format YYYY-MM-DD)
5. Priority score (0-1, where 1 is most important/urgent)
6. Whether this email requires a response (true/false)
7. Sentiment/urgency (positive/neutral/negative/urgent)

Focus on what the user needs to know and do."""

            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert email analyst. Extract key information concisely and accurately.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "email_summary",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "summary": {
                                    "type": "string",
                                    "description": "2-3 sentence summary",
                                },
                                "action_items": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of action items",
                                },
                                "key_people": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Important people mentioned",
                                },
                                "key_dates": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Important dates in ISO format",
                                },
                                "priority_score": {
                                    "type": "number",
                                    "description": "Priority from 0-1",
                                },
                                "requires_response": {
                                    "type": "boolean",
                                    "description": "Whether response is needed",
                                },
                                "sentiment": {
                                    "type": "string",
                                    "enum": [
                                        "positive",
                                        "neutral",
                                        "negative",
                                        "urgent",
                                    ],
                                    "description": "Email sentiment",
                                },
                            },
                            "required": [
                                "summary",
                                "action_items",
                                "key_people",
                                "key_dates",
                                "priority_score",
                                "requires_response",
                                "sentiment",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                temperature=0.3,
            )

            # Parse response
            result = response.choices[0].message.content
            if result:
                import json

                data = json.loads(result)
                return EmailSummary(**data)

            return None

        except Exception as e:
            logger.error(f"Error generating summary with LLM: {e}", exc_info=True)
            return None

    @staticmethod
    def should_summarize_eagerly(email: Email) -> bool:
        """Determine if email should be summarized immediately during sync.

        Args:
            email: Email document

        Returns:
            True if should summarize eagerly, False for lazy summarization
        """
        # Skip categories
        if email.email_category in EmailSummarizer.SKIP_CATEGORIES:
            return False

        # Eagerly summarize important categories
        if email.email_category in EmailSummarizer.EAGER_CATEGORIES:
            return True

        # Eagerly summarize unread emails from non-promotional sources
        if not email.is_read and email.email_category not in ["promotional"]:
            return True

        # Otherwise, lazy summarization
        return False

    @staticmethod
    async def batch_summarize(
        emails: List[Email], integration: Integration
    ) -> Dict[str, int]:
        """Batch summarize multiple emails.

        Args:
            emails: List of email documents
            integration: User's email integration

        Returns:
            Statistics: {summarized: int, skipped: int, failed: int}
        """
        stats = {"summarized": 0, "skipped": 0, "failed": 0}

        for email in emails:
            try:
                result = await EmailSummarizer.summarize_email(email, integration)
                if result:
                    stats["summarized"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Failed to summarize email {email.id}: {e}")
                stats["failed"] += 1

        logger.info(
            f"Batch summarization complete: {stats['summarized']} summarized, "
            f"{stats['skipped']} skipped, {stats['failed']} failed"
        )

        return stats
