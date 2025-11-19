"""Thread-aware package building from email clusters."""

import logging
from typing import List, Optional

from beanie import PydanticObjectId

from app.emails.entity_extractor import EmailEntity
from app.emails.models import Email
from app.packages.courier_detector import CourierDetector
from app.packages.models import CourierService, Package, PackageStatus
from app.packages.schemas import PackageCreate

logger = logging.getLogger(__name__)


class ThreadAwarePackageBuilder:
    """Build packages from email threads and related emails."""

    @staticmethod
    async def build_package_from_emails(
        user_id: PydanticObjectId, email_cluster: List[Email]
    ) -> Optional[Package]:
        """Build a comprehensive package from a cluster of related emails.

        This method analyzes all related emails to extract complete package information:
        - Tracking number from courier emails
        - Merchant name and order number from merchant emails
        - User context from sent emails
        - Refund status from merchant responses

        Args:
            user_id: User ID who owns these emails
            email_cluster: List of related emails

        Returns:
            Package object with enriched data, or None if no tracking info
        """
        if not email_cluster:
            return None

        logger.info(
            f"Building package from {len(email_cluster)} emails for user {user_id}"
        )

        # 1. Categorize emails by type
        courier_email = None
        merchant_emails = []
        user_emails = []

        for email in email_cluster:
            # Ensure entities are extracted
            if not email.extracted_entities:
                logger.warning(
                    f"Email {email.id} missing entities - should be extracted first"
                )
                continue

            entities = EmailEntity(**email.extracted_entities)

            # Has tracking number? It's a courier email
            if entities.tracking_numbers:
                if not courier_email:  # Take first one with tracking
                    courier_email = email

            # Has merchant domain? It's a merchant email
            if entities.merchant_domain:
                merchant_emails.append(email)

            # Check if sent by user
            # TODO: Improve user email detection by matching against user's actual email address
            # Current implementation relies on email labels which may not always be present
            if email.from_email and user_id:
                # User's sent emails (from their email address)
                # Note: This is simplified - in production, match against user's email
                if any(
                    label in ["sent", "SENT"]
                    for label in getattr(email, "labels", [])
                ):
                    user_emails.append(email)

        # Must have courier email with tracking
        if not courier_email:
            logger.info("No courier email with tracking number found in cluster")
            return None

        logger.info(
            f"Categorized: 1 courier, {len(merchant_emails)} merchant, {len(user_emails)} user emails"
        )

        # 2. Extract package data from courier email
        courier_entities = EmailEntity(**courier_email.extracted_entities)

        tracking_number = courier_entities.tracking_numbers[0]

        # Detect courier service
        courier_service = CourierDetector.detect_courier_from_tracking_number(tracking_number)

        # Fallback: try email domain
        if courier_service == CourierService.UNKNOWN:
            analysis = CourierDetector.analyze_email(
                from_email=courier_email.from_email,
                subject=courier_email.subject or "",
                body=courier_email.body_text or courier_email.snippet or "",
            )
            if analysis["courier_service"]:
                courier_service = analysis["courier_service"]

        logger.info(f"Detected courier: {courier_service.value}")

        # 3. Enrich with merchant data
        merchant_name = None
        order_number = None
        product_name = None

        for merchant_email in merchant_emails:
            m_entities = EmailEntity(**merchant_email.extracted_entities)

            # Get merchant name
            if m_entities.merchant_name and not merchant_name:
                merchant_name = m_entities.merchant_name
                logger.info(f"Found merchant: {merchant_name}")

            # Get order number
            if m_entities.order_numbers and not order_number:
                order_number = m_entities.order_numbers[0]
                logger.info(f"Found order number: {order_number}")

            # Get product names
            if m_entities.product_names and not product_name:
                product_name = ", ".join(m_entities.product_names[:3])
                logger.info(f"Found products: {product_name}")

        # 4. Extract user context (why they contacted merchant, etc.)
        user_context = None
        for user_email in user_emails:
            u_entities = EmailEntity(**user_email.extracted_entities)
            if u_entities.key_phrases:
                user_context = " | ".join(u_entities.key_phrases[:3])
                logger.info(f"Found user context: {user_context}")
                break

        # 5. Check for refund status
        refund_status = None
        refund_email_id = None
        for email in email_cluster:
            e_entities = EmailEntity(**email.extracted_entities)
            if e_entities.is_refund:
                refund_status = "issued"
                refund_email_id = str(email.id)
                if e_entities.refund_amount:
                    refund_status = f"issued (${e_entities.refund_amount:.2f})"
                logger.info(f"Found refund: {refund_status}")
                break

        # 6. Detect package status from courier email
        c_entities = EmailEntity(**courier_email.extracted_entities)
        status = PackageStatus.IN_TRANSIT  # Default

        if c_entities.is_exception:
            status = PackageStatus.EXCEPTION
        elif "delivered" in (courier_email.subject or "").lower():
            status = PackageStatus.DELIVERED
        elif "out for delivery" in (courier_email.subject or "").lower():
            status = PackageStatus.OUT_FOR_DELIVERY

        # 7. Use product from courier email if not found in merchant emails
        if not product_name and c_entities.product_names:
            product_name = ", ".join(c_entities.product_names[:3])

        # 8. Build email metadata
        email_metadata = {
            "total_related_emails": len(email_cluster),
            "merchant_email_ids": [str(e.id) for e in merchant_emails],
        }

        if refund_status:
            email_metadata["refund_status"] = refund_status
            email_metadata["refund_email_id"] = refund_email_id

        if user_context:
            email_metadata["user_context"] = user_context

        # Categorization summary
        email_metadata["email_types"] = {
            "courier": 1,
            "merchant": len(merchant_emails),
            "user": len(user_emails),
        }

        # 9. Create package
        package = Package(
            user_id=user_id,
            email_id=courier_email.id,
            related_email_ids=[email.id for email in email_cluster],
            tracking_number=tracking_number,
            courier_service=courier_service,
            status=status,
            merchant=merchant_name,
            order_number=order_number,
            product_name=product_name,
            detection_source="email_thread",
            detection_confidence=0.95,  # High confidence from thread analysis
            email_metadata=email_metadata,
        )

        logger.info(
            f"Built package: {tracking_number} from {merchant_name or 'unknown merchant'}"
        )

        return package

    @staticmethod
    async def enrich_existing_package(
        package: Package, email_cluster: List[Email]
    ) -> Package:
        """Enrich an existing package with data from newly discovered related emails.

        Args:
            package: Existing package to enrich
            email_cluster: All related emails (including new ones)

        Returns:
            Enriched package (not saved)
        """
        logger.info(
            f"Enriching package {package.tracking_number} with {len(email_cluster)} emails"
        )

        # Re-categorize all emails
        merchant_emails = []
        user_emails = []

        for email in email_cluster:
            if not email.extracted_entities:
                continue

            entities = EmailEntity(**email.extracted_entities)

            if entities.merchant_domain:
                merchant_emails.append(email)

            # Check if user email
            # TODO: Improve user email detection by matching against user's actual email address
            if any(
                label in ["sent", "SENT"] for label in getattr(email, "labels", [])
            ):
                user_emails.append(email)

        # Update merchant if not set
        if not package.merchant:
            for merchant_email in merchant_emails:
                m_entities = EmailEntity(**merchant_email.extracted_entities)
                if m_entities.merchant_name:
                    package.merchant = m_entities.merchant_name
                    logger.info(f"Added merchant: {package.merchant}")
                    break

        # Update order number if not set
        if not package.order_number:
            for merchant_email in merchant_emails:
                m_entities = EmailEntity(**merchant_email.extracted_entities)
                if m_entities.order_numbers:
                    package.order_number = m_entities.order_numbers[0]
                    logger.info(f"Added order number: {package.order_number}")
                    break

        # Update related emails
        package.related_email_ids = [email.id for email in email_cluster]

        # Update metadata - always update both total count and merchant email list
        package.email_metadata["total_related_emails"] = len(email_cluster)
        package.email_metadata["merchant_email_ids"] = [str(e.id) for e in merchant_emails]

        # Check for refund status update
        for email in email_cluster:
            e_entities = EmailEntity(**email.extracted_entities)
            if e_entities.is_refund and "refund_status" not in package.email_metadata:
                package.email_metadata["refund_status"] = "issued"
                package.email_metadata["refund_email_id"] = str(email.id)
                logger.info("Added refund status")
                break

        # Add user context if not present
        if "user_context" not in package.email_metadata:
            for user_email in user_emails:
                u_entities = EmailEntity(**user_email.extracted_entities)
                if u_entities.key_phrases:
                    package.email_metadata["user_context"] = " | ".join(
                        u_entities.key_phrases[:3]
                    )
                    logger.info("Added user context")
                    break

        logger.info(f"Package enrichment complete")

        return package
