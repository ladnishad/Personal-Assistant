"""Package tracking database models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed
from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel


class CourierService(str, Enum):
    """Supported courier services."""

    USPS = "usps"
    FEDEX = "fedex"
    UPS = "ups"
    AMAZON = "amazon"
    DHL = "dhl"
    ONTRAC = "ontrac"
    LASERSHIP = "lasership"
    UNKNOWN = "unknown"


class PackageStatus(str, Enum):
    """Package delivery status."""

    ORDERED = "ordered"  # Order placed but not shipped
    LABEL_CREATED = "label_created"  # Shipping label created
    SHIPPED = "shipped"  # Package shipped
    IN_TRANSIT = "in_transit"  # Package in transit
    OUT_FOR_DELIVERY = "out_for_delivery"  # Out for delivery today
    DELIVERED = "delivered"  # Successfully delivered
    ATTEMPTED_DELIVERY = "attempted_delivery"  # Delivery attempt failed
    EXCEPTION = "exception"  # Delivery exception (delayed, damaged, etc.)
    RETURNED = "returned"  # Package returned to sender
    CANCELLED = "cancelled"  # Order/shipment cancelled


class TrackingEvent(BaseModel):
    """Individual tracking event in package journey."""

    timestamp: datetime
    status: str
    location: Optional[str] = None
    description: str
    city: Optional[str] = None
    state: Optional[str] = None
    country_iso3: Optional[str] = None  # ISO 3166-1 alpha-3 country code (e.g., "USA")
    zip: Optional[str] = None  # Postal/ZIP code

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-15T10:30:00",
                "status": "in_transit",
                "location": "Memphis, TN",
                "description": "Package arrived at FedEx facility",
                "city": "Memphis",
                "state": "TN",
                "country_iso3": "USA",
                "zip": "38118",
            }
        }


class Package(Document):
    """Package tracking document model."""

    user_id: Indexed(PydanticObjectId)

    # Email relationships
    email_id: Optional[Indexed(PydanticObjectId)] = None  # Primary detection email
    related_email_ids: List[PydanticObjectId] = Field(
        default_factory=list
    )  # All related emails (merchant, user, etc.)

    # Core tracking info
    tracking_number: str  # Unique index defined in Settings.indexes
    courier_service: CourierService
    status: PackageStatus = Field(default=PackageStatus.ORDERED)

    # Package details
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    merchant: Optional[str] = None  # Amazon, Best Buy, etc.
    order_number: Optional[str] = None

    # Location tracking
    current_location: Optional[str] = None
    origin_location: Optional[str] = None
    destination_location: Optional[str] = None

    # Delivery information
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    recipient_name: Optional[str] = None
    delivery_instructions: Optional[str] = None

    # Tracking events
    events: List[TrackingEvent] = Field(default_factory=list)

    # Detection metadata
    detection_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0
    )  # How confident we are this is a package
    detection_source: str = Field(
        default="email"
    )  # "email", "manual", "api", "email_thread", etc.

    # Email-specific metadata (from thread analysis)
    email_metadata: Dict[str, Any] = Field(default_factory=dict)
    # Example: {
    #   "refund_status": "issued",
    #   "refund_email_id": "...",
    #   "merchant_email_ids": ["...", "..."],
    #   "user_context": "Refused due to $80 tariff",
    #   "total_related_emails": 3
    # }

    # Status tracking
    is_active: bool = Field(
        default=True
    )  # False if delivered, cancelled, or returned
    last_checked_at: Optional[datetime] = None  # Last time we checked courier API
    check_interval_minutes: int = Field(
        default=120
    )  # How often to check (adaptive based on status)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Notification tracking
    user_notified_delivered: bool = Field(default=False)
    user_notified_exception: bool = Field(default=False)

    class Settings:
        name = "packages"
        indexes = [
            [("user_id", 1), ("created_at", -1)],
            [("user_id", 1), ("status", 1)],
            [("user_id", 1), ("is_active", 1)],
            IndexModel(
                [("tracking_number", 1), ("courier_service", 1)],
                name="package_tracking_unique_idx",
                unique=True,
            ),
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "tracking_number": "1Z999AA10123456784",
                "courier_service": "ups",
                "status": "in_transit",
                "product_name": "MacBook Pro 16-inch",
                "merchant": "Apple",
                "estimated_delivery": "2024-01-20T17:00:00",
                "current_location": "Louisville, KY",
                "is_active": True,
            }
        }

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def add_event(self, event: TrackingEvent):
        """Add a tracking event and update status."""
        # Avoid duplicate events (same timestamp and description)
        if not any(
            e.timestamp == event.timestamp and e.description == event.description
            for e in self.events
        ):
            self.events.append(event)
            # Sort events by timestamp (newest first)
            self.events.sort(key=lambda e: e.timestamp, reverse=True)
            self.update_timestamp()

    def mark_delivered(self):
        """Mark package as delivered and inactive."""
        self.status = PackageStatus.DELIVERED
        self.is_active = False
        self.actual_delivery = datetime.utcnow()
        self.update_timestamp()

    def mark_exception(self):
        """Mark package as having an exception."""
        self.status = PackageStatus.EXCEPTION
        self.update_timestamp()

    def should_check_status(self) -> bool:
        """Determine if package status should be checked based on interval."""
        if not self.is_active:
            return False

        if self.last_checked_at is None:
            return True

        minutes_since_check = (
            datetime.utcnow() - self.last_checked_at
        ).total_seconds() / 60
        return minutes_since_check >= self.check_interval_minutes

    def get_latest_event(self) -> Optional[TrackingEvent]:
        """Get the most recent tracking event."""
        return self.events[0] if self.events else None
