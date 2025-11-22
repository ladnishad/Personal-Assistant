"""LLM-based email classification system using OpenAI Agents SDK."""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from agents import Agent, ModelSettings, Runner
from pydantic import BaseModel, Field

from app.config import settings
from app.emails.models import Email

logger = logging.getLogger(__name__)


class EmailCategory(str, Enum):
    """Email classification categories."""

    PACKAGE_SHIPPING = "package_shipping"  # UPS, FedEx, tracking emails
    ECOMMERCE_ORDER = "ecommerce_order"  # Order confirmations, receipts
    PROMOTIONAL = "promotional"  # Marketing, newsletters, deals
    FINANCIAL = "financial"  # Bank statements, investment updates
    CALENDAR_EVENT = "calendar_event"  # Meeting invites, RSVPs
    TRAVEL = "travel"  # Flight confirmations, hotel bookings
    RECEIPT = "receipt"  # Purchase receipts, transaction confirmations
    PERSONAL = "personal"  # Personal correspondence, replies
    NOTIFICATION = "notification"  # App notifications, alerts
    SUPPORT = "support"  # Customer support, help desk
    SOCIAL = "social"  # Social media notifications
    UNKNOWN = "unknown"  # Cannot determine


class EmailClassification(BaseModel):
    """Email classification result."""

    category: EmailCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    indicators: list[str] = Field(default_factory=list)
    should_process: bool = True  # Should we do deep entity extraction?


def _should_process_category(category: EmailCategory) -> bool:
    """Determine if category needs deep entity extraction.

    Args:
        category: Email category

    Returns:
        True if should do deep processing, False to skip
    """
    # Categories that need deep processing
    process_categories = {
        EmailCategory.PACKAGE_SHIPPING,  # Need tracking numbers, status
        EmailCategory.ECOMMERCE_ORDER,  # Need order numbers, merchant
        EmailCategory.TRAVEL,  # Need flight numbers, dates
        EmailCategory.RECEIPT,  # Need amounts, merchant
        EmailCategory.FINANCIAL,  # Need amounts, accounts
        EmailCategory.UNKNOWN,  # Process unknown to be safe (defensive approach)
    }

    # Skip processing for these categories (explicitly documented)
    skip_categories = {
        EmailCategory.PROMOTIONAL,  # No value in extracting
        EmailCategory.NOTIFICATION,  # Usually automated, low value
        EmailCategory.SOCIAL,  # Not relevant for personal assistant
        EmailCategory.CALENDAR_EVENT,  # Handled by calendar sync
        EmailCategory.PERSONAL,  # Low priority for entity extraction
        EmailCategory.SUPPORT,  # Usually part of threads, low value
    }

    return category in process_categories


def _build_classification_prompt(email: Email) -> str:
    """Build classification prompt for LLM.

    Args:
        email: Email to classify

    Returns:
        Formatted prompt string
    """
    # Use subject + snippet for classification (fast, no full body needed)
    subject = email.subject or "No subject"
    sender = email.from_email or "Unknown sender"
    snippet = email.snippet or email.body_text[:200] if email.body_text else "No content"

    return f"""Classify this email into ONE category based on its purpose and content.

**Email Details:**
Subject: {subject}
From: {sender}
Preview: {snippet[:300]}

**Categories:**
- package_shipping: Package tracking, shipping notifications, delivery updates from couriers (UPS, FedEx, USPS, DHL, etc.)
- ecommerce_order: Order confirmations, purchase receipts from merchants (NOT shipping updates)
- promotional: Marketing emails, newsletters, deals, advertisements, promotions
- financial: Bank statements, investment updates, payment confirmations, credit card alerts
- calendar_event: Meeting invites, event RSVPs, calendar notifications
- travel: Flight confirmations, hotel bookings, travel itineraries, rental cars
- receipt: Purchase receipts, transaction confirmations, payment confirmations
- personal: Personal correspondence, replies to conversations, one-to-one communication
- notification: App notifications, automated alerts, system notifications
- support: Customer support emails, help desk responses, support tickets
- social: Social media notifications, friend requests, likes, mentions
- unknown: Cannot determine category with confidence

**Classification Rules:**
1. If from courier domain (ups.com, fedex.com, usps.com, dhl.com) → package_shipping
2. If contains tracking numbers (1Z..., 9400...) → package_shipping
3. If subject contains "order confirmation" but NOT shipping → ecommerce_order
4. If subject contains "unsubscribe" link or promotional language → promotional
5. If from noreply@, no-reply@, marketing@, deals@ → likely promotional
6. Personal emails usually have real person's name in sender

Respond with ONLY these fields:
- category: one of the categories above
- confidence: float between 0.0 and 1.0
- reasoning: brief explanation (1-2 sentences)
- indicators: list of specific signals detected"""


def _create_classifier_agent() -> Agent:
    """Create the email classifier agent.

    Factory function for creating a reusable classifier agent instance.
    Follows the same pattern as package_agent.py for consistency.

    Returns:
        Configured Agent instance for email classification
    """
    return Agent(
        name="Email Classifier",
        instructions="You are an expert email classifier. Analyze emails and categorize them accurately based on their purpose and content.",
        model="gpt-5-nano",  # Explicitly use nano for fast, cheap classification
        output_type=EmailClassification,  # Structured output via Pydantic
        model_settings=ModelSettings(
            # GPT-5 nano settings for fast, lightweight classification
            # Note: temperature is NOT supported with GPT-5 models
            reasoning_effort="low",
            verbosity="low",
        ),
    )


# Create reusable classifier agent instance
_classifier_agent = _create_classifier_agent()


async def classify_email(email: Email) -> EmailClassification:
    """Classify email using OpenAI Agents SDK.

    Args:
        email: Email to classify

    Returns:
        EmailClassification with category, confidence, and reasoning
    """
    try:
        # Build classification prompt
        prompt = _build_classification_prompt(email)

        # Run classifier agent
        result = await Runner.run(_classifier_agent, prompt)

        # Extract classification from structured output
        classification = result.final_output

        # Set should_process based on category
        classification.should_process = _should_process_category(classification.category)

        logger.info(
            f"Classified email '{email.subject[:50] if email.subject else 'No subject'}...' "
            f"as {classification.category.value} (confidence: {classification.confidence:.2f})"
        )

        return classification

    except Exception as e:
        logger.error(f"Error classifying email {email.id}: {e}", exc_info=True)

        # Fallback to unknown category (defensive approach - process rather than skip)
        return EmailClassification(
            category=EmailCategory.UNKNOWN,
            confidence=0.0,
            reasoning=f"Classification failed: {str(e)}",
            indicators=[],
            should_process=True,  # Process unknown emails to be safe
        )
