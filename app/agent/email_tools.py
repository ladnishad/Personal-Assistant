"""Email management tools for AI agents."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents import function_tool
from beanie import PydanticObjectId

from app.emails.classifier import classify_email
from app.emails.entity_extractor import EmailEntityExtractor
from app.emails.models import Email, EmailLabel
from app.emails.relationships import EmailRelationshipDetector
from app.emails.service import EmailService

logger = logging.getLogger(__name__)


# Import user context from tools.py
def get_current_user_id() -> PydanticObjectId:
    """Get the current user ID from execution context."""
    from app.agent.tools import get_current_user_id as _get_user_id

    return _get_user_id()


def _format_email_summary(email: Email) -> Dict[str, Any]:
    """Format email into concise summary for list responses.

    Used for list endpoints to avoid context overflow.

    Args:
        email: Email document

    Returns:
        Concise email summary
    """
    return {
        "email_id": str(email.id),
        "from": email.from_email,
        "from_name": email.from_name,
        "subject": email.subject,
        "snippet": email.snippet[:200] if email.snippet else None,  # Short snippet
        "received_at": email.received_at.isoformat(),
        "is_read": email.is_read,
        "category": email.email_category,
    }


def _format_email_response(email: Email) -> Dict[str, Any]:
    """Format email into structured response for agent.

    Args:
        email: Email document

    Returns:
        Structured dictionary with email data
    """
    # Extract key entities only (avoid full dict)
    key_entities = {}
    if email.extracted_entities:
        entities = email.extracted_entities
        if entities.get("tracking_numbers"):
            key_entities["tracking_numbers"] = entities["tracking_numbers"][:2]  # Max 2
        if entities.get("amounts"):
            key_entities["amounts"] = entities["amounts"][:2]  # Max 2
        if entities.get("merchant_domain"):
            key_entities["merchant"] = entities["merchant_domain"]
        if entities.get("order_number"):
            key_entities["order_number"] = entities["order_number"]

    return {
        "email_id": str(email.id),
        "from": email.from_email,
        "from_name": email.from_name,
        "to": email.to,
        "subject": email.subject,
        "snippet": email.snippet,
        "body_text": email.body_text[:1000] if email.body_text else None,  # Limit size
        "received_at": email.received_at.isoformat(),
        "is_read": email.is_read,
        "is_starred": email.is_starred,
        "labels": [label.value for label in email.labels],
        "has_attachments": email.has_attachments,
        "category": email.email_category,
        "category_confidence": email.category_confidence,
        "key_entities": key_entities,  # Only key extracted entities
    }


@function_tool
async def get_email_details(email_id: str) -> Dict[str, Any]:
    """Get full details of a specific email with all metadata and extracted information.

    Use this when:
    - User asks to read a specific email
    - User references "that email" or "the email from X"
    - You need full email content to answer a question

    Args:
        email_id: The ID of the email to retrieve

    Returns:
        Complete email details including:
        - Full content (subject, body, sender)
        - Classification category and confidence
        - Extracted entities (tracking numbers, amounts, dates, etc.)
        - Email metadata (read status, labels, attachments)
    """
    try:
        user_id = get_current_user_id()

        # Get email
        email = await Email.get(PydanticObjectId(email_id))

        if not email:
            return {"error": "Email not found"}

        # Verify ownership
        if email.user_id != user_id:
            return {"error": "Not authorized to access this email"}

        # Classify if not already classified
        if not email.email_category:
            classification = await classify_email(email)
            email.email_category = classification.category.value
            email.category_confidence = classification.confidence
            email.category_reasoning = classification.reasoning
            email.classified_at = datetime.utcnow()
            await email.save()

        # Extract entities if not already extracted
        if not email.extracted_entities:
            entities = EmailEntityExtractor.extract_entities(email)
            email.extracted_entities = entities.model_dump()
            email.entities_extracted_at = datetime.utcnow()
            await email.save()

        return _format_email_response(email)

    except Exception as e:
        logger.error(f"Error getting email details: {e}", exc_info=True)
        return {"error": str(e)}


@function_tool
async def get_recent_emails(
    limit: int = 10,
    category: str = None,
    is_read: bool = None,
    from_date: str = None,
) -> List[Dict[str, Any]]:
    """Get recent emails with optional filters.

    Use this when:
    - User asks "What emails did I get today/recently?"
    - "Show me my emails"
    - "Any new emails?"
    - User wants emails filtered by category or read status

    Args:
        limit: Maximum number of emails to return (default: 10, max: 50)
        category: Filter by category (promotional, package_shipping, financial, personal, etc.)
        is_read: Filter by read status (True for read, False for unread, None for all)
        from_date: ISO date string to filter emails from (e.g., "2025-01-19" or "today")

    Returns:
        List of emails with structured data for each
    """
    try:
        user_id = get_current_user_id()

        # Limit to reasonable maximum
        limit = min(limit, 50)

        # Parse from_date
        date_filter = None
        if from_date:
            if from_date.lower() == "today":
                date_filter = datetime.utcnow().replace(hour=0, minute=0, second=0)
            elif from_date.lower() == "yesterday":
                date_filter = (datetime.utcnow() - timedelta(days=1)).replace(
                    hour=0, minute=0, second=0
                )
            else:
                try:
                    date_filter = datetime.fromisoformat(from_date)
                except ValueError:
                    logger.warning(f"Invalid date format: {from_date}")

        # Build query
        query_filters = {"user_id": user_id}

        if is_read is not None:
            query_filters["is_read"] = is_read

        if category:
            query_filters["email_category"] = category

        if date_filter:
            query_filters["received_at"] = {"$gte": date_filter}

        # Get emails
        emails = (
            await Email.find(query_filters)
            .sort(-Email.received_at)
            .limit(limit)
            .to_list()
        )

        # Format responses
        results = []
        for email in emails:
            # Auto-classify if needed
            if not email.email_category:
                classification = await classify_email(email)
                email.email_category = classification.category.value
                email.category_confidence = classification.confidence
                email.classified_at = datetime.utcnow()
                await email.save()

            # Auto-extract entities for relevant categories
            if not email.extracted_entities and email.email_category in [
                "package_shipping",
                "ecommerce_order",
                "travel",
                "financial",
            ]:
                entities = EmailEntityExtractor.extract_entities(email)
                email.extracted_entities = entities.model_dump()
                email.entities_extracted_at = datetime.utcnow()
                await email.save()

            results.append(_format_email_summary(email))

        logger.info(f"Retrieved {len(results)} emails for user {user_id}")
        return results

    except Exception as e:
        logger.error(f"Error getting recent emails: {e}", exc_info=True)
        return []


@function_tool
async def search_emails(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search user's emails by query string.

    Use this when:
    - User asks to find emails from a specific person or company
    - User searches for emails about a topic
    - "Find emails from Amazon"
    - "Search for emails about refund"

    Args:
        query: Search query (searches in subject, body, and sender)
        limit: Maximum number of results (default: 10, max: 30)

    Returns:
        List of matching emails with full structured data
    """
    try:
        user_id = get_current_user_id()
        limit = min(limit, 30)

        # Use existing EmailService
        emails, _ = await EmailService.get_user_emails(
            user_id=user_id, search=query, limit=limit
        )

        # Format responses with classification
        results = []
        for email in emails:
            # Auto-classify if needed
            if not email.email_category:
                classification = await classify_email(email)
                email.email_category = classification.category.value
                email.category_confidence = classification.confidence
                email.classified_at = datetime.utcnow()
                await email.save()

            results.append(_format_email_summary(email))

        logger.info(f"Found {len(results)} emails matching '{query}'")
        return results

    except Exception as e:
        logger.error(f"Error searching emails: {e}", exc_info=True)
        return []


@function_tool
async def get_emails_by_category(
    category: str, limit: int = 10, is_read: bool = None
) -> List[Dict[str, Any]]:
    """Get emails filtered by classification category.

    Use this when:
    - User asks for specific types of emails
    - "Show me package tracking emails"
    - "Any promotional emails?"
    - "Get my financial emails"

    Args:
        category: Email category - one of:
            - package_shipping: Courier tracking emails
            - ecommerce_order: Order confirmations
            - promotional: Marketing emails
            - financial: Bank statements, payments
            - calendar_event: Meeting invites
            - travel: Flight/hotel confirmations
            - receipt: Purchase receipts
            - personal: Personal correspondence
            - notification: App notifications
            - support: Customer support
            - social: Social media notifications
        limit: Maximum number of emails (default: 10, max: 30)
        is_read: Filter by read status (optional)

    Returns:
        List of emails in the specified category
    """
    try:
        user_id = get_current_user_id()
        limit = min(limit, 30)

        # Build query
        query_filters = {"user_id": user_id, "email_category": category}

        if is_read is not None:
            query_filters["is_read"] = is_read

        # Get emails
        emails = (
            await Email.find(query_filters)
            .sort(-Email.received_at)
            .limit(limit)
            .to_list()
        )

        # Format responses
        results = [_format_email_summary(email) for email in emails]

        logger.info(f"Retrieved {len(results)} {category} emails")
        return results

    except Exception as e:
        logger.error(f"Error getting emails by category: {e}", exc_info=True)
        return []


@function_tool
async def find_emails_from_sender(
    sender_email: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Find all emails from a specific sender.

    Use this when:
    - User asks for emails from a specific person or company
    - "Show me emails from mom"
    - "Get all Amazon emails"
    - "Find emails from support@company.com"

    Args:
        sender_email: Email address or partial email to search for
        limit: Maximum number of emails (default: 10, max: 30)

    Returns:
        List of emails from the specified sender
    """
    try:
        user_id = get_current_user_id()
        limit = min(limit, 30)

        # Search using regex for partial matches
        emails = (
            await Email.find(
                {
                    "user_id": user_id,
                    "from_email": {"$regex": sender_email, "$options": "i"},
                }
            )
            .sort(-Email.received_at)
            .limit(limit)
            .to_list()
        )

        # Format responses
        results = [_format_email_summary(email) for email in emails]

        logger.info(f"Found {len(results)} emails from {sender_email}")
        return results

    except Exception as e:
        logger.error(f"Error finding emails from sender: {e}", exc_info=True)
        return []


@function_tool
async def get_unread_emails(limit: int = 20) -> List[Dict[str, Any]]:
    """Get unread emails, prioritized by category importance.

    Use this when:
    - User asks "Any unread emails?"
    - "What haven't I read yet?"
    - "Show me new emails"

    Args:
        limit: Maximum number of emails (default: 20, max: 50)

    Returns:
        List of unread emails, sorted by importance and recency
    """
    try:
        user_id = get_current_user_id()
        limit = min(limit, 50)

        # Get unread emails
        emails = (
            await Email.find({"user_id": user_id, "is_read": False})
            .sort(-Email.received_at)
            .limit(limit)
            .to_list()
        )

        # Auto-classify unread emails if needed
        for email in emails:
            if not email.email_category:
                classification = await classify_email(email)
                email.email_category = classification.category.value
                email.category_confidence = classification.confidence
                email.classified_at = datetime.utcnow()
                await email.save()

        # Priority order for categories
        category_priority = {
            "package_shipping": 1,
            "financial": 2,
            "travel": 3,
            "ecommerce_order": 4,
            "personal": 5,
            "calendar_event": 6,
            "receipt": 7,
            "support": 8,
            "notification": 9,
            "social": 10,
            "promotional": 11,
            "unknown": 12,
        }

        # Sort by priority then by date
        emails.sort(
            key=lambda e: (
                category_priority.get(e.email_category or "unknown", 99),
                -e.received_at.timestamp(),
            )
        )

        # Format responses
        results = [_format_email_summary(email) for email in emails]

        logger.info(f"Retrieved {len(results)} unread emails")
        return results

    except Exception as e:
        logger.error(f"Error getting unread emails: {e}", exc_info=True)
        return []


@function_tool
async def mark_emails_read(email_ids: List[str], is_read: bool = True) -> Dict[str, Any]:
    """Mark one or more emails as read or unread.

    Use this when:
    - User asks to mark emails as read
    - "Mark that email as read"
    - "Mark all Amazon emails as read"
    - After reading emails to user

    Args:
        email_ids: List of email IDs to mark
        is_read: True to mark as read, False to mark as unread

    Returns:
        Result with count of emails updated
    """
    try:
        user_id = get_current_user_id()

        # Convert to ObjectIds and verify ownership
        updated_count = 0
        for email_id in email_ids:
            try:
                email = await Email.get(PydanticObjectId(email_id))
                if email and email.user_id == user_id:
                    email.is_read = is_read
                    await email.save()
                    updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to update email {email_id}: {e}")
                continue

        logger.info(f"Marked {updated_count} emails as {'read' if is_read else 'unread'}")
        return {
            "updated": updated_count,
            "total_requested": len(email_ids),
            "is_read": is_read,
        }

    except Exception as e:
        logger.error(f"Error marking emails: {e}", exc_info=True)
        return {"error": str(e), "updated": 0}


@function_tool
async def star_email(email_id: str, starred: bool = True) -> Dict[str, Any]:
    """Star or unstar an email.

    Use this when:
    - User asks to star an important email
    - "Star that email"
    - "Mark this as important"

    Args:
        email_id: Email ID to star
        starred: True to star, False to unstar

    Returns:
        Result indicating success
    """
    try:
        user_id = get_current_user_id()

        email = await Email.get(PydanticObjectId(email_id))

        if not email:
            return {"error": "Email not found"}

        if email.user_id != user_id:
            return {"error": "Not authorized to access this email"}

        email.is_starred = starred
        await email.save()

        logger.info(f"{'Starred' if starred else 'Unstarred'} email {email_id}")
        return {"starred": starred, "email_id": email_id}

    except Exception as e:
        logger.error(f"Error starring email: {e}", exc_info=True)
        return {"error": str(e), "starred": False}


@function_tool
async def sync_emails() -> Dict[str, Any]:
    """Trigger email sync from connected email providers (Gmail, etc.).

    Use this when:
    - User asks to check for new emails
    - "Sync my emails"
    - "Check for new messages"
    - Before searching if results seem outdated

    Returns:
        Sync statistics (synced count, new emails, updated emails)
    """
    try:
        user_id = get_current_user_id()

        # Trigger sync
        result = await EmailService.sync_emails(user_id)

        logger.info(
            f"Email sync complete: {result['new_emails']} new, {result['updated_emails']} updated"
        )
        return result

    except Exception as e:
        logger.error(f"Error syncing emails: {e}", exc_info=True)
        return {"error": str(e), "synced_count": 0}


@function_tool
async def get_email_thread(email_id: str) -> List[Dict[str, Any]]:
    """Get all emails in the same conversation thread.

    Use this when:
    - User asks about an email conversation
    - "Show me the full thread"
    - "What was the conversation about?"
    - Need context from related messages

    Args:
        email_id: ID of any email in the thread

    Returns:
        List of all emails in the thread, sorted chronologically
    """
    try:
        user_id = get_current_user_id()

        # Get the email
        email = await Email.get(PydanticObjectId(email_id))

        if not email:
            return []

        if email.user_id != user_id:
            return []

        # Get all emails with same thread_id
        if not email.thread_id:
            # No thread, return just this email
            return [_format_email_summary(email)]

        thread_emails = (
            await Email.find({"user_id": user_id, "thread_id": email.thread_id})
            .sort(Email.received_at)
            .to_list()
        )

        # Format responses
        results = [_format_email_summary(e) for e in thread_emails]

        logger.info(f"Retrieved thread with {len(results)} emails")
        return results

    except Exception as e:
        logger.error(f"Error getting email thread: {e}", exc_info=True)
        return []


@function_tool
async def get_related_emails(email_id: str) -> List[Dict[str, Any]]:
    """Find emails related to this one (same order, tracking number, or merchant).

    Use this when:
    - User asks about related emails for an order
    - "Show me all emails about this order"
    - "What else did they send about this?"
    - Need full context about a purchase or shipment

    Args:
        email_id: Email ID to find relationships for

    Returns:
        List of related emails with relationship context
    """
    try:
        user_id = get_current_user_id()

        # Get the email
        email = await Email.get(PydanticObjectId(email_id))

        if not email:
            return []

        if email.user_id != user_id:
            return []

        # Use relationship detector to find related emails
        cluster = await EmailRelationshipDetector.get_email_cluster(email.id, user_id)

        # Format responses
        results = [_format_email_summary(e) for e in cluster if e.id != email.id]

        logger.info(f"Found {len(results)} related emails")
        return results

    except Exception as e:
        logger.error(f"Error getting related emails: {e}", exc_info=True)
        return []


@function_tool
async def scan_emails_for_packages(
    days_back: int = 7, limit: int = 50
) -> Dict[str, Any]:
    """Scan recent emails to detect package tracking information and auto-create package records.

    Use this when:
    - User asks "Check my emails for packages"
    - "Any deliveries coming?"
    - "Do I have any packages?"
    - Proactively detecting packages from new emails

    This tool:
    1. Scans recent emails (past 7 days by default)
    2. Detects package tracking emails using classification
    3. Extracts tracking numbers and merchant info
    4. Creates package tracking records automatically
    5. Returns summary of packages found

    Args:
        days_back: How many days back to scan (default: 7, max: 30)
        limit: Maximum emails to scan (default: 50, max: 100)

    Returns:
        Summary of packages detected and created
    """
    try:
        from app.packages.courier_detector import CourierDetector
        from app.packages.models import CourierService
        from app.packages.schemas import PackageCreate
        from app.packages.service import PackageService

        user_id = get_current_user_id()

        # Limit parameters
        days_back = min(days_back, 30)
        limit = min(limit, 100)

        # Get recent emails
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        emails = (
            await Email.find(
                {"user_id": user_id, "received_at": {"$gte": cutoff_date}}
            )
            .sort(-Email.received_at)
            .limit(limit)
            .to_list()
        )

        packages_found = []
        packages_created = 0
        emails_scanned = len(emails)

        for email in emails:
            # Classify if not already
            if not email.email_category:
                classification = await classify_email(email)
                email.email_category = classification.category.value
                email.category_confidence = classification.confidence
                email.classified_at = datetime.utcnow()
                await email.save()

            # Only process shipping-related emails
            if email.email_category not in ["package_shipping", "ecommerce_order"]:
                continue

            # Extract entities if not already
            if not email.extracted_entities:
                entities = EmailEntityExtractor.extract_entities(email)
                email.extracted_entities = entities.model_dump()
                email.entities_extracted_at = datetime.utcnow()
                await email.save()

            # Check for tracking numbers
            entities = email.extracted_entities
            if not entities.get("tracking_numbers"):
                continue

            # Analyze email with courier detector
            body = email.body_text or email.snippet or ""
            analysis = CourierDetector.analyze_email(
                from_email=email.from_email,
                subject=email.subject or "",
                body=body,
            )

            # Create packages for detected tracking numbers
            for tracking_number, courier in analysis["tracking_numbers"]:
                try:
                    # Check if package already exists
                    existing = await PackageService.get_package_by_tracking(
                        tracking_number, courier
                    )
                    if existing:
                        continue

                    # Create new package
                    package_data = PackageCreate(
                        tracking_number=tracking_number,
                        courier_service=courier,
                        email_id=str(email.id),
                        merchant=entities.get("merchant_name"),
                        order_number=entities.get("order_numbers", [None])[0],
                        detection_source="email_scan",
                        detection_confidence=analysis["confidence"],
                    )

                    package = await PackageService.create_package(user_id, package_data)
                    packages_created += 1

                    packages_found.append(
                        {
                            "tracking_number": tracking_number,
                            "courier": courier.value,
                            "merchant": entities.get("merchant_name"),
                            "email_subject": email.subject,
                            "package_id": str(package.id),
                        }
                    )

                except Exception as e:
                    logger.warning(f"Failed to create package {tracking_number}: {e}")
                    continue

        logger.info(
            f"Scanned {emails_scanned} emails, found {len(packages_found)} packages, created {packages_created} new records"
        )

        return {
            "emails_scanned": emails_scanned,
            "packages_found": len(packages_found),
            "packages_created": packages_created,
            "packages": packages_found,
        }

    except Exception as e:
        logger.error(f"Error scanning emails for packages: {e}", exc_info=True)
        return {"error": str(e), "packages_found": 0}
