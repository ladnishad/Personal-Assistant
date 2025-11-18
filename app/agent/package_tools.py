"""Package tracking tools for AI agents."""

import contextvars
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import function_tool
from beanie import PydanticObjectId

from app.emails.models import Email
from app.packages.courier_detector import CourierDetector
from app.packages.models import CourierService
from app.packages.schemas import PackageCreate
from app.packages.service import PackageService

logger = logging.getLogger(__name__)


# Use contextvars for proper async context management (Python best practice)
_package_user_context: contextvars.ContextVar[Optional[PydanticObjectId]] = (
    contextvars.ContextVar("package_user_id", default=None)
)


def set_package_user_id(user_id: PydanticObjectId):
    """Set the current user ID for package tool execution context.

    Uses contextvars for thread-safe async context management.

    Args:
        user_id: The user ID to set in the current context
    """
    _package_user_context.set(user_id)


def get_package_user_id() -> PydanticObjectId:
    """Get the current user ID from execution context.

    Returns:
        The user ID from the current context

    Raises:
        RuntimeError: If user ID not set in context
    """
    user_id = _package_user_context.get()
    if user_id is None:
        raise RuntimeError("User ID not set in package tool execution context")
    return user_id


@function_tool
async def detect_tracking_email(email_id: str) -> Dict[str, Any]:
    """Analyze an email to detect if it contains package tracking information.

    Use this tool when:
    - Processing emails to find package shipments
    - User mentions an email about a package or delivery
    - Automatically scanning emails for tracking info

    Args:
        email_id: The ID of the email to analyze

    Returns:
        Dictionary with detection results including:
        - is_tracking_email: Boolean indicating if email contains tracking
        - confidence: Confidence score 0.0-1.0
        - courier_service: Detected courier (if found)
        - tracking_numbers: List of detected tracking numbers
        - merchant: Detected merchant/seller
        - product_name: Detected product name (if available)
    """
    try:
        # Get email from database
        email = await Email.get(PydanticObjectId(email_id))
        if not email:
            return {"error": "Email not found", "is_tracking_email": False}

        # Analyze email
        body = email.body_text or email.body_html or email.snippet or ""
        analysis = CourierDetector.analyze_email(
            from_email=email.from_email,
            subject=email.subject or "",
            body=body,
        )

        # Extract product name from subject
        product_name = None
        if "order" in email.subject.lower():
            # Try to extract product name
            words = email.subject.split()
            if len(words) > 3:
                product_name = " ".join(words[:5])

        result = {
            "is_tracking_email": analysis["is_tracking_email"],
            "confidence": analysis["confidence"],
            "courier_service": (
                analysis["courier_service"].value
                if analysis["courier_service"]
                else None
            ),
            "tracking_numbers": [
                {"number": num, "courier": courier.value}
                for num, courier in analysis["tracking_numbers"]
            ],
            "merchant": analysis["merchant"],
            "order_number": analysis["order_number"],
            "product_name": product_name,
        }

        logger.info(
            f"Analyzed email {email_id}: is_tracking={result['is_tracking_email']}, confidence={result['confidence']}"
        )

        return result

    except Exception as e:
        logger.error(f"Error detecting tracking email: {e}")
        return {"error": str(e), "is_tracking_email": False}


@function_tool
async def create_package_from_email(
    email_id: str,
    tracking_number: str,
    courier_service: str,
    product_name: str = None,
    merchant: str = None,
    order_number: str = None,
) -> Dict[str, Any]:
    """Create a package tracking entry from an email.

    Use this tool when:
    - You've detected a tracking email and want to start tracking the package
    - User asks to track a package from their email
    - Automatically creating package records from shipping notifications

    Args:
        email_id: Email ID containing the tracking info
        tracking_number: Package tracking number
        courier_service: Courier service name (usps, fedex, ups, amazon, dhl)
        product_name: Optional product name
        merchant: Optional merchant/seller name
        order_number: Optional order number

    Returns:
        Dictionary with package creation result including package_id
    """
    try:
        user_id = get_package_user_id()

        # Parse courier service
        try:
            courier = CourierService(courier_service.lower())
        except ValueError:
            return {
                "error": f"Invalid courier service: {courier_service}",
                "created": False,
            }

        # Create package
        package_data = PackageCreate(
            tracking_number=tracking_number,
            courier_service=courier,
            email_id=email_id,
            product_name=product_name,
            merchant=merchant,
            order_number=order_number,
            detection_source="email",
            detection_confidence=0.9,
        )

        package = await PackageService.create_package(user_id, package_data)

        logger.info(
            f"Created package {package.id} from email {email_id}: {tracking_number}"
        )

        return {
            "created": True,
            "package_id": str(package.id),
            "tracking_number": package.tracking_number,
            "courier": package.courier_service.value,
            "status": package.status.value,
        }

    except ValueError as e:
        # Package already exists
        logger.warning(f"Package creation failed: {e}")
        return {"error": str(e), "created": False}
    except Exception as e:
        logger.error(f"Error creating package: {e}")
        return {"error": str(e), "created": False}


@function_tool
async def get_user_packages(
    status: str = None, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get user's tracked packages.

    Use this tool when:
    - User asks "Where are my packages?"
    - User wants to see all deliveries
    - Checking status of active shipments

    Args:
        status: Filter by status (ordered, shipped, in_transit, out_for_delivery, delivered)
        limit: Maximum number of packages to return (default: 10)

    Returns:
        List of packages with tracking details
    """
    try:
        user_id = get_package_user_id()

        # Parse status filter
        from app.packages.models import PackageStatus

        package_status = None
        if status:
            try:
                package_status = PackageStatus(status.lower())
            except ValueError:
                pass

        # Get packages
        packages, _ = await PackageService.get_user_packages(
            user_id=user_id,
            status=package_status,
            is_active=True if not status == "delivered" else None,
            limit=limit,
        )

        # Format response
        result = []
        for pkg in packages:
            latest_event = pkg.get_latest_event()
            result.append(
                {
                    "package_id": str(pkg.id),
                    "tracking_number": pkg.tracking_number,
                    "courier": pkg.courier_service.value,
                    "status": pkg.status.value,
                    "product_name": pkg.product_name,
                    "merchant": pkg.merchant,
                    "current_location": pkg.current_location,
                    "estimated_delivery": (
                        pkg.estimated_delivery.isoformat()
                        if pkg.estimated_delivery
                        else None
                    ),
                    "latest_update": (
                        latest_event.description if latest_event else None
                    ),
                }
            )

        logger.info(f"Retrieved {len(result)} packages for user {user_id}")
        return result

    except Exception as e:
        logger.error(f"Error getting packages: {e}")
        return []


@function_tool
async def track_package_status(tracking_number: str) -> Dict[str, Any]:
    """Get real-time tracking status for a package from courier API via AfterShip.

    Use this tool when:
    - User asks for current package status
    - Updating package information
    - Checking delivery progress

    AfterShip automatically detects the courier from the tracking number,
    so you don't need to specify which courier service to use.

    Args:
        tracking_number: Package tracking number

    Returns:
        Dictionary with current package status and tracking events
    """
    try:
        from app.config import settings
        from app.packages.courier_apis.aftership_client import AfterShipClient

        # Check if AfterShip API key is configured
        if not settings.aftership_api_key:
            return {
                "error": "Package tracking not configured. AfterShip API key required."
            }

        # Create AfterShip client (auto-detects courier)
        client = AfterShipClient(api_key=settings.aftership_api_key)

        # Track package
        tracking_response = await client.track_package(tracking_number)

        # Format response
        result = {
            "tracking_number": tracking_response.tracking_number,
            "courier": tracking_response.courier_service.value,
            "status": tracking_response.status.value,
            "current_location": tracking_response.current_location,
            "estimated_delivery": (
                tracking_response.estimated_delivery.isoformat()
                if tracking_response.estimated_delivery
                else None
            ),
            "actual_delivery": (
                tracking_response.actual_delivery.isoformat()
                if tracking_response.actual_delivery
                else None
            ),
            "events": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "location": event.location,
                    "description": event.description,
                }
                for event in tracking_response.events
            ],
        }

        # Update package in database if it exists
        package = await PackageService.get_package_by_tracking(
            tracking_number, tracking_response.courier_service
        )
        if package:
            await PackageService.update_package_status(
                tracking_number=tracking_number,
                courier_service=tracking_response.courier_service,
                status=tracking_response.status,
                events=tracking_response.events,
                current_location=tracking_response.current_location,
                estimated_delivery=tracking_response.estimated_delivery,
            )

        logger.info(f"Tracked package {tracking_number}: {result['status']}")
        return result

    except Exception as e:
        logger.error(f"Error tracking package: {e}")
        return {"error": str(e)}


@function_tool
async def get_package_with_context(tracking_number: str) -> Dict[str, Any]:
    """Get complete package details with full email context and relationship history.

    Use this when user asks about a specific package or order and wants detailed information.
    Returns the complete story including:
    - Package tracking status
    - All related emails (merchant, user correspondence, courier updates)
    - Refund status if applicable
    - User's notes and context
    - Full conversation history about the package

    Args:
        tracking_number: Package tracking number or order number

    Returns:
        Complete package information with email context and conversation history
    """
    try:
        from app.emails.entity_extractor import EmailEntity
        from app.emails.models import Email

        user_id = get_package_user_id()

        # Find package by tracking number
        package = await PackageService.get_package_by_tracking(tracking_number)

        if not package:
            # Try to find by order number
            all_packages = await PackageService.get_user_packages(
                user_id=user_id, limit=100
            )
            package = next(
                (
                    p[0]
                    for p in all_packages
                    if p[0].order_number and tracking_number in p[0].order_number
                ),
                None,
            )

        if not package:
            return {"error": f"Package not found: {tracking_number}"}

        logger.info(
            f"Getting package context for {package.tracking_number} with {len(package.related_email_ids)} related emails"
        )

        # Get all related emails
        related_emails = []
        if package.related_email_ids:
            related_emails = await Email.find(
                Email.id.in_(package.related_email_ids)
            ).to_list()

        logger.info(f"Found {len(related_emails)} related emails")

        # Build email context
        email_context = []
        for email in related_emails:
            entities = None
            if email.extracted_entities:
                entities = EmailEntity(**email.extracted_entities)

            # Determine email type
            email_type = "other"
            if entities:
                if entities.tracking_numbers:
                    email_type = "courier"
                elif entities.merchant_domain:
                    email_type = "merchant"
                elif entities.is_refund:
                    email_type = "refund"

            # Check if user sent email
            if any(label in ["sent", "SENT"] for label in getattr(email, "labels", [])):
                email_type = "user_sent"

            email_context.append(
                {
                    "type": email_type,
                    "from": email.from_email,
                    "subject": email.subject,
                    "date": email.received_at.isoformat(),
                    "snippet": email.snippet[:200] if email.snippet else None,
                    "is_refund": entities.is_refund if entities else False,
                    "key_info": entities.key_phrases[:3] if entities else [],
                    "amounts": entities.amounts[:2] if entities else [],
                }
            )

        # Sort emails by date
        email_context.sort(key=lambda x: x["date"])

        # Build comprehensive response
        result = {
            "package_id": str(package.id),
            "tracking_number": package.tracking_number,
            "courier": package.courier_service.value,
            "status": package.status.value,
            "merchant": package.merchant,
            "order_number": package.order_number,
            "product": package.product_name,
            "current_location": package.current_location,
            "estimated_delivery": (
                package.estimated_delivery.isoformat()
                if package.estimated_delivery
                else None
            ),
            "actual_delivery": (
                package.actual_delivery.isoformat() if package.actual_delivery else None
            ),
            "latest_event": (
                package.get_latest_event().description
                if package.get_latest_event()
                else None
            ),
            "metadata": package.email_metadata,
            "related_emails": email_context,
            "email_count": len(related_emails),
            "email_summary": {
                "total": len(email_context),
                "courier": sum(1 for e in email_context if e["type"] == "courier"),
                "merchant": sum(1 for e in email_context if e["type"] == "merchant"),
                "user_sent": sum(1 for e in email_context if e["type"] == "user_sent"),
                "refund": sum(1 for e in email_context if e["type"] == "refund"),
            },
        }

        logger.info(
            f"Built context for package {package.tracking_number}: {len(email_context)} emails"
        )

        return result

    except Exception as e:
        logger.error(f"Error getting package with context: {e}", exc_info=True)
        return {"error": str(e)}


# List of all package tools
PACKAGE_TOOLS = [
    detect_tracking_email,
    create_package_from_email,
    get_user_packages,
    track_package_status,
    get_package_with_context,  # New: comprehensive package + email context
]
