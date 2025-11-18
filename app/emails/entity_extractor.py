"""Email entity extraction for relationship intelligence."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.emails.models import Email


class EmailEntity(BaseModel):
    """Extracted entities from email content."""

    # Identifiers
    tracking_numbers: List[str] = Field(default_factory=list)
    order_numbers: List[str] = Field(default_factory=list)
    invoice_numbers: List[str] = Field(default_factory=list)

    # Parties
    merchant_name: Optional[str] = None
    merchant_domain: Optional[str] = None
    courier_service: Optional[str] = None

    # Financial
    amounts: List[Dict[str, Any]] = Field(
        default_factory=list
    )  # [{amount: 150.00, currency: "USD", type: "total"}]
    refund_amount: Optional[float] = None

    # Dates
    order_date: Optional[datetime] = None
    ship_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None

    # Status indicators
    is_refund: bool = False
    is_cancellation: bool = False
    is_return: bool = False
    is_exception: bool = False

    # Extracted text
    product_names: List[str] = Field(default_factory=list)
    key_phrases: List[str] = Field(
        default_factory=list
    )  # ["tariff unexpected", "delivery refused"]

    class Config:
        json_schema_extra = {
            "example": {
                "tracking_numbers": ["1ZB9033F6762347268"],
                "order_numbers": ["NS652158"],
                "merchant_name": "NOSO",
                "amounts": [
                    {"amount": 80.00, "currency": "USD", "type": "tariff"}
                ],
                "is_exception": True,
                "key_phrases": ["tariff unexpected", "delivery refused"],
            }
        }


class EmailEntityExtractor:
    """Extract structured entities from emails."""

    @staticmethod
    def extract_entities(email: Email) -> EmailEntity:
        """Extract all entities from an email.

        Args:
            email: Email document to analyze

        Returns:
            EmailEntity with extracted data
        """
        # Combine all text sources
        text = " ".join(
            filter(
                None,
                [
                    email.subject or "",
                    email.body_text or "",
                    email.snippet or "",
                ],
            )
        )

        entities = EmailEntity()

        # Extract tracking numbers
        entities.tracking_numbers = (
            EmailEntityExtractor._extract_tracking_numbers(text)
        )

        # Extract order numbers
        entities.order_numbers = EmailEntityExtractor._extract_order_numbers(text)

        # Extract merchant info
        entities.merchant_name = EmailEntityExtractor._extract_merchant_name(
            email.from_email, text
        )
        entities.merchant_domain = EmailEntityExtractor._extract_domain(
            email.from_email
        )

        # Extract amounts
        entities.amounts = EmailEntityExtractor._extract_amounts(text)
        if entities.amounts:
            # Check for refund amount
            for amount_info in entities.amounts:
                if amount_info.get("type") == "refund":
                    entities.refund_amount = amount_info.get("amount")
                    break

        # Detect status indicators
        entities.is_refund = EmailEntityExtractor._is_refund_email(text)
        entities.is_cancellation = EmailEntityExtractor._is_cancellation(text)
        entities.is_return = EmailEntityExtractor._is_return_email(text)
        entities.is_exception = EmailEntityExtractor._is_exception(text)

        # Extract products
        entities.product_names = EmailEntityExtractor._extract_products(text)

        # Extract key phrases
        entities.key_phrases = EmailEntityExtractor._extract_key_phrases(text)

        return entities

    @staticmethod
    def _extract_tracking_numbers(text: str) -> List[str]:
        """Extract tracking numbers using regex patterns.

        Supports: UPS, FedEx, USPS, Amazon, DHL, OnTrac, LaserShip

        Args:
            text: Text to search

        Returns:
            List of tracking numbers
        """
        patterns = {
            "ups": r"\b1Z[A-Z0-9]{16}\b",
            "fedex": r"\b\d{12,14}\b(?![A-Z])",  # 12-14 digits not followed by letter
            "usps": r"\b(94|93|92|94|95)\d{20}\b",
            "amazon": r"\bTBA\d{12}\b",
            "dhl": r"\b\d{10,11}\b",
            "ontrac": r"\bC\d{14}\b",
        }

        tracking_numbers = []
        text_upper = text.upper()

        for courier, pattern in patterns.items():
            matches = re.findall(pattern, text_upper, re.IGNORECASE)
            tracking_numbers.extend(matches)

        return list(set(tracking_numbers))

    @staticmethod
    def _extract_order_numbers(text: str) -> List[str]:
        """Extract order numbers from text.

        Looks for patterns like: Order #123, Order: ABC123, #NS652158

        Args:
            text: Text to search

        Returns:
            List of order numbers
        """
        patterns = [
            r"Order[:\s#]+([A-Z0-9\-]{5,})",
            r"#([A-Z]{2,}\d{5,})",  # #NS652158
            r"Order Number[:\s]+([A-Z0-9\-]{5,})",
            r"Order ID[:\s]+([A-Z0-9\-]{5,})",
        ]

        order_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            order_numbers.extend(matches)

        # Remove duplicates and filter out tracking numbers
        unique_orders = list(set(order_numbers))

        # Filter: order numbers shouldn't look like tracking numbers
        filtered = []
        for order in unique_orders:
            # Skip if it's all digits (likely tracking number)
            if order.isdigit() and len(order) > 10:
                continue
            filtered.append(order)

        return filtered

    @staticmethod
    def _extract_merchant_name(from_email: str, text: str) -> Optional[str]:
        """Extract merchant name from email sender or content.

        Args:
            from_email: Sender email address
            text: Email text

        Returns:
            Merchant name if found
        """
        # Check if email has name in "Name <email>" format
        name_match = re.match(r"(.+?)\s*<.+?>", from_email)
        if name_match:
            merchant_name = name_match.group(1).strip()

            # Common merchant patterns to clean up
            merchant_name = re.sub(r"\b(Inc|LLC|Ltd|AB|Corp)\b\.?", "", merchant_name, flags=re.IGNORECASE).strip()

            # Skip common courier names
            couriers = ["UPS", "FEDEX", "USPS", "DHL", "ONTRAC"]
            if not any(courier in merchant_name.upper() for courier in couriers):
                return merchant_name

        # Try to find merchant in signature
        # Look for company names before email addresses
        signature_pattern = r"([A-Z][A-Za-z\s&]+?)\s*(?:e:|w:|email:)"
        sig_match = re.search(signature_pattern, text)
        if sig_match:
            return sig_match.group(1).strip()

        return None

    @staticmethod
    def _extract_domain(email_address: str) -> Optional[str]:
        """Extract domain from email address.

        Args:
            email_address: Email address

        Returns:
            Domain (e.g., "amazon.com")
        """
        # Extract email from "Name <email>" format
        email_match = re.search(r"<(.+?)>", email_address)
        if email_match:
            email_address = email_match.group(1)

        # Extract domain
        domain_match = re.search(r"@(.+)$", email_address)
        if domain_match:
            return domain_match.group(1).lower()

        return None

    @staticmethod
    def _extract_amounts(text: str) -> List[Dict[str, Any]]:
        """Extract monetary amounts with context.

        Args:
            text: Text to search

        Returns:
            List of amount dictionaries
        """
        # Pattern: $80, $150.00, USD 200, 80 USD
        pattern = r"(?:[\$€£]|USD|EUR|GBP)?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)\s?(?:USD|EUR|GBP|[\$€£])?"

        amounts = []
        for match in re.finditer(pattern, text):
            amount_str = match.group(1)
            amount = float(amount_str.replace(",", ""))

            # Only include amounts > $5 to avoid noise
            if amount < 5:
                continue

            # Get context around the amount
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end].lower()

            # Determine amount type from context
            amount_type = "unknown"
            if any(
                word in context
                for word in ["total", "subtotal", "price", "cost"]
            ):
                amount_type = "total"
            elif "refund" in context:
                amount_type = "refund"
            elif any(
                word in context for word in ["tariff", "duty", "tax", "customs"]
            ):
                amount_type = "tariff"
            elif any(word in context for word in ["shipping", "delivery"]):
                amount_type = "shipping"

            # Detect currency
            currency = "USD"  # Default
            if "€" in match.group(0) or "EUR" in match.group(0):
                currency = "EUR"
            elif "£" in match.group(0) or "GBP" in match.group(0):
                currency = "GBP"

            amounts.append(
                {
                    "amount": amount,
                    "currency": currency,
                    "type": amount_type,
                    "context": context.strip(),
                }
            )

        return amounts

    @staticmethod
    def _is_refund_email(text: str) -> bool:
        """Detect if email is about a refund.

        Args:
            text: Email text

        Returns:
            True if refund detected
        """
        refund_keywords = [
            "refund issued",
            "refunded",
            "refund processed",
            "money back",
            "credited",
            "credit issued",
            "issued a refund",
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in refund_keywords)

    @staticmethod
    def _is_cancellation(text: str) -> bool:
        """Detect if email is about a cancellation.

        Args:
            text: Email text

        Returns:
            True if cancellation detected
        """
        cancel_keywords = [
            "order cancelled",
            "order canceled",
            "cancellation",
            "has been cancelled",
            "has been canceled",
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in cancel_keywords)

    @staticmethod
    def _is_return_email(text: str) -> bool:
        """Detect if email is about a return.

        Args:
            text: Email text

        Returns:
            True if return detected
        """
        return_keywords = [
            "return request",
            "return submitted",
            "return portal",
            "return instructions",
            "returning",
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in return_keywords)

    @staticmethod
    def _is_exception(text: str) -> bool:
        """Detect if email is about a delivery exception.

        Args:
            text: Email text

        Returns:
            True if exception detected
        """
        exception_keywords = [
            "exception",
            "delivery refused",
            "refused the delivery",
            "delivery failed",
            "could not deliver",
            "delivery attempt",
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in exception_keywords)

    @staticmethod
    def _extract_products(text: str) -> List[str]:
        """Extract product names from email.

        Args:
            text: Email text

        Returns:
            List of product names
        """
        products = []

        # Look for "Product:", "Item:", "Merchandise Description:" patterns
        product_patterns = [
            r"Product[:\s]+([A-Za-z0-9\s\-]+)",
            r"Item[:\s]+([A-Za-z0-9\s\-]+)",
            r"Merchandise Description[:\s]+([A-Z\s]+)",
            r"Description[:\s]+([A-Z\s]{5,30})",
        ]

        for pattern in product_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            products.extend([m.strip() for m in matches])

        # Clean up: remove duplicates and common non-product terms
        cleaned = []
        for product in products:
            if len(product) > 3 and product.upper() not in [
                "ORDER",
                "TRACKING",
                "SHIPMENT",
            ]:
                cleaned.append(product)

        return list(set(cleaned))[:5]  # Limit to 5

    @staticmethod
    def _extract_key_phrases(text: str) -> List[str]:
        """Extract important phrases using keyword-based heuristics.

        Args:
            text: Email text

        Returns:
            List of key phrases
        """
        # Keywords that indicate important context
        important_contexts = [
            "refused",
            "unexpected",
            "issue",
            "problem",
            "delay",
            "exception",
            "sorry",
            "apologize",
            "unfortunately",
        ]

        phrases = []
        sentences = re.split(r"[.!?]", text)

        for keyword in important_contexts:
            for sentence in sentences:
                if keyword in sentence.lower() and len(sentence.strip()) > 10:
                    # Clean up the sentence
                    clean_sentence = sentence.strip()
                    # Limit length
                    if len(clean_sentence) > 150:
                        clean_sentence = clean_sentence[:147] + "..."

                    if clean_sentence not in phrases:
                        phrases.append(clean_sentence)

                    if len(phrases) >= 5:  # Limit to 5 phrases
                        break

            if len(phrases) >= 5:
                break

        return phrases
