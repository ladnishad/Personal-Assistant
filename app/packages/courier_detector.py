"""Courier service detection from emails and tracking numbers."""

import logging
import re
from typing import Dict, List, Optional, Tuple

from app.packages.models import CourierService

logger = logging.getLogger(__name__)


class CourierDetector:
    """Detect courier service from email content and tracking numbers."""

    # Email domain patterns for courier services
    COURIER_DOMAINS = {
        CourierService.USPS: [
            "usps.com",
            "usps.gov",
            "uspis.gov",
            "email.usps.com",
        ],
        CourierService.FEDEX: [
            "fedex.com",
            "email.fedex.com",
            "fedexemail.com",
            "ground.fedex.com",
        ],
        CourierService.UPS: [
            "ups.com",
            "email.ups.com",
            "quantum.ups.com",
        ],
        CourierService.AMAZON: [
            "amazon.com",
            "shipment-tracking.amazon.com",
            "ship-confirm@amazon.com",
            "amazon.ca",
            "amazon.co.uk",
        ],
        CourierService.DHL: [
            "dhl.com",
            "dhl.de",
            "email.dhl.com",
        ],
        CourierService.ONTRAC: [
            "ontrac.com",
            "ontracemail.com",
        ],
        CourierService.LASERSHIP: [
            "lasership.com",
        ],
    }

    # Tracking number regex patterns
    TRACKING_PATTERNS = {
        # USPS: 20-22 digits, various formats
        CourierService.USPS: [
            r"\b9[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\s?[0-9]{2}\b",  # 20 digits
            r"\b9[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\b",  # 18 digits
            r"\b[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\b",  # 20 digits generic
            r"\b94[0-9]{20}\b",  # 22 digits starting with 94
            r"\b[A-Z]{2}[0-9]{9}US\b",  # International format
        ],
        # FedEx: 12-15 digits
        CourierService.FEDEX: [
            r"\b[0-9]{12}\b",  # 12 digits
            r"\b[0-9]{14}\b",  # 14 digits
            r"\b[0-9]{15}\b",  # 15 digits
            r"\b96[0-9]{20}\b",  # Ground 96
        ],
        # UPS: 1Z + 16 alphanumeric (18 total)
        CourierService.UPS: [
            r"\b1Z[0-9A-Z]{16}\b",  # Standard 1Z format
        ],
        # Amazon: TBA + 12-13 digits
        CourierService.AMAZON: [
            r"\bTBA[0-9]{12,13}\b",  # TBA tracking
        ],
        # DHL: 10-11 digits
        CourierService.DHL: [
            r"\b[0-9]{10,11}\b",  # 10-11 digits
            r"\b[A-Z]{3}[0-9]{7}\b",  # 3 letters + 7 digits
        ],
        # OnTrac: C + 14 digits
        CourierService.ONTRAC: [
            r"\bC[0-9]{14}\b",
        ],
        # LaserShip: 1LS + digits or LX + digits
        CourierService.LASERSHIP: [
            r"\b1LS[0-9]{8,}\b",
            r"\bLX[0-9]{8,}\b",
        ],
    }

    # Keywords that indicate shipping/tracking emails
    SHIPPING_KEYWORDS = [
        "tracking",
        "shipment",
        "shipped",
        "delivery",
        "package",
        "order shipped",
        "tracking number",
        "track your",
        "your order has shipped",
        "out for delivery",
        "delivered",
        "in transit",
    ]

    # Merchant-specific patterns
    MERCHANT_PATTERNS = {
        "Amazon": [r"amazon\.com", r"amazon\.ca", r"amazon\.co\.uk"],
        "eBay": [r"ebay\.com", r"ebay\.ca"],
        "Walmart": [r"walmart\.com"],
        "Target": [r"target\.com"],
        "Best Buy": [r"bestbuy\.com"],
        "Apple": [r"apple\.com"],
        "Newegg": [r"newegg\.com"],
    }

    @classmethod
    def detect_courier_from_email(
        cls, from_email: str, subject: str, body: str
    ) -> Optional[CourierService]:
        """Detect courier service from email metadata.

        Args:
            from_email: Sender email address
            subject: Email subject
            body: Email body text

        Returns:
            Detected courier service or None
        """
        from_email_lower = from_email.lower()

        # Check email domain
        for courier, domains in cls.COURIER_DOMAINS.items():
            for domain in domains:
                if domain in from_email_lower:
                    logger.info(
                        f"Detected {courier.value} from email domain: {from_email}"
                    )
                    return courier

        # Check subject and body for courier mentions
        content = (subject + " " + body).lower()

        # Count mentions of each courier
        courier_mentions = {
            CourierService.USPS: content.count("usps")
            + content.count("united states postal"),
            CourierService.FEDEX: content.count("fedex")
            + content.count("federal express"),
            CourierService.UPS: content.count("ups")
            + content.count("united parcel"),
            CourierService.AMAZON: content.count("amazon"),
            CourierService.DHL: content.count("dhl"),
            CourierService.ONTRAC: content.count("ontrac"),
            CourierService.LASERSHIP: content.count("lasership"),
        }

        # Return courier with most mentions
        max_courier = max(courier_mentions, key=courier_mentions.get)
        if courier_mentions[max_courier] > 0:
            logger.info(
                f"Detected {max_courier.value} from content mentions"
            )
            return max_courier

        return None

    @classmethod
    def detect_courier_from_tracking_number(
        cls, tracking_number: str
    ) -> Optional[CourierService]:
        """Detect courier from tracking number pattern.

        Args:
            tracking_number: Tracking number string

        Returns:
            Detected courier service or None
        """
        # Clean tracking number (remove spaces, hyphens)
        clean_tracking = tracking_number.replace(" ", "").replace("-", "").upper()

        # Check patterns in order of specificity
        # UPS (most specific - starts with 1Z)
        if clean_tracking.startswith("1Z"):
            return CourierService.UPS

        # Amazon TBA
        if clean_tracking.startswith("TBA"):
            return CourierService.AMAZON

        # OnTrac (starts with C)
        if clean_tracking.startswith("C") and len(clean_tracking) == 15:
            return CourierService.ONTRAC

        # LaserShip
        if clean_tracking.startswith("1LS") or clean_tracking.startswith("LX"):
            return CourierService.LASERSHIP

        # USPS (starts with 9 and 20-22 digits)
        if clean_tracking.startswith("9") and len(clean_tracking) in [20, 22]:
            return CourierService.USPS

        # USPS international
        if re.match(r"^[A-Z]{2}[0-9]{9}US$", clean_tracking):
            return CourierService.USPS

        # FedEx (12-15 digits)
        if clean_tracking.isdigit() and len(clean_tracking) in [12, 14, 15]:
            # Could be FedEx or DHL, check for more specific patterns
            if clean_tracking.startswith("96"):
                return CourierService.FEDEX
            return CourierService.FEDEX  # Default to FedEx for these lengths

        # DHL (10-11 digits or pattern)
        if clean_tracking.isdigit() and len(clean_tracking) in [10, 11]:
            return CourierService.DHL

        if re.match(r"^[A-Z]{3}[0-9]{7}$", clean_tracking):
            return CourierService.DHL

        return None

    @classmethod
    def extract_tracking_numbers(
        cls, text: str, courier: Optional[CourierService] = None
    ) -> List[Tuple[str, CourierService]]:
        """Extract all tracking numbers from text.

        Args:
            text: Text to search for tracking numbers
            courier: Optional courier to filter patterns

        Returns:
            List of (tracking_number, courier_service) tuples
        """
        results = []

        # Clean up text
        text = text.replace("\n", " ").replace("\r", " ")

        # Determine which patterns to check
        patterns_to_check = {}
        if courier:
            patterns_to_check[courier] = cls.TRACKING_PATTERNS.get(courier, [])
        else:
            patterns_to_check = cls.TRACKING_PATTERNS

        # Search for each courier's patterns
        for courier_service, patterns in patterns_to_check.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    tracking_num = match.group(0).replace(" ", "")
                    # Verify with tracking number detection
                    detected_courier = cls.detect_courier_from_tracking_number(
                        tracking_num
                    )
                    if detected_courier:
                        results.append((tracking_num, detected_courier))

        # Remove duplicates
        unique_results = list(set(results))

        return unique_results

    @classmethod
    def is_shipping_email(cls, subject: str, body: str) -> bool:
        """Determine if email is related to shipping/tracking.

        Args:
            subject: Email subject
            body: Email body

        Returns:
            True if email appears to be shipping-related
        """
        content = (subject + " " + body).lower()

        # Check for shipping keywords
        keyword_count = sum(
            1 for keyword in cls.SHIPPING_KEYWORDS if keyword in content
        )

        # Consider it a shipping email if it has 2+ shipping keywords
        return keyword_count >= 2

    @classmethod
    def extract_merchant(cls, from_email: str, subject: str, body: str) -> Optional[str]:
        """Extract merchant/seller name from email.

        Args:
            from_email: Sender email
            subject: Email subject
            body: Email body

        Returns:
            Merchant name if detected, None otherwise
        """
        content = from_email + " " + subject + " " + body

        for merchant, patterns in cls.MERCHANT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return merchant

        # Try to extract from "from_email" domain
        match = re.search(r"@([a-z0-9-]+)\.", from_email, re.IGNORECASE)
        if match:
            domain = match.group(1)
            # Capitalize first letter
            return domain.capitalize()

        return None

    @classmethod
    def extract_order_number(cls, subject: str, body: str) -> Optional[str]:
        """Extract order number from email.

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Order number if found, None otherwise
        """
        content = subject + " " + body

        # Common order number patterns
        patterns = [
            r"Order\s*#?\s*:?\s*([A-Z0-9-]{6,20})",
            r"Order\s*Number\s*:?\s*([A-Z0-9-]{6,20})",
            r"Order\s*ID\s*:?\s*([A-Z0-9-]{6,20})",
            r"#([A-Z0-9-]{6,20})",  # Generic # pattern
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    @classmethod
    def analyze_email(cls, from_email: str, subject: str, body: str) -> Dict:
        """Comprehensive email analysis for package tracking.

        Args:
            from_email: Sender email
            subject: Email subject
            body: Email body

        Returns:
            Dictionary with detection results
        """
        is_shipping = cls.is_shipping_email(subject, body)

        result = {
            "is_tracking_email": is_shipping,
            "confidence": 0.0,
            "courier_service": None,
            "tracking_numbers": [],
            "merchant": None,
            "order_number": None,
        }

        if not is_shipping:
            return result

        # Detect courier
        courier = cls.detect_courier_from_email(from_email, subject, body)
        result["courier_service"] = courier

        # Extract tracking numbers
        tracking_numbers = cls.extract_tracking_numbers(body, courier)
        result["tracking_numbers"] = tracking_numbers

        # Extract merchant and order number
        result["merchant"] = cls.extract_merchant(from_email, subject, body)
        result["order_number"] = cls.extract_order_number(subject, body)

        # Calculate confidence
        confidence = 0.0
        if is_shipping:
            confidence += 0.3
        if courier:
            confidence += 0.3
        if tracking_numbers:
            confidence += 0.4

        result["confidence"] = min(confidence, 1.0)

        return result
