"""Base courier API client abstraction."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.packages.models import PackageStatus, TrackingEvent
from app.packages.schemas import CourierTrackingResponse


class BaseCourierClient(ABC):
    """Abstract base class for courier API clients."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize courier client.

        Args:
            api_key: Optional API key for courier service
        """
        self.api_key = api_key

    @abstractmethod
    async def track_package(self, tracking_number: str) -> CourierTrackingResponse:
        """Track a package using the courier's API.

        Args:
            tracking_number: Package tracking number

        Returns:
            CourierTrackingResponse with tracking details

        Raises:
            CourierAPIError: If API request fails
            TrackingNotFoundError: If tracking number not found
        """
        pass

    @abstractmethod
    def get_courier_name(self) -> str:
        """Get the courier service name.

        Returns:
            Courier service name
        """
        pass

    def parse_status(self, status_code: str) -> PackageStatus:
        """Parse courier-specific status code to PackageStatus enum.

        Args:
            status_code: Courier-specific status code

        Returns:
            PackageStatus enum value
        """
        # Default implementation - override in subclasses
        status_lower = status_code.lower()

        if any(
            keyword in status_lower
            for keyword in ["delivered", "delivery confirmed"]
        ):
            return PackageStatus.DELIVERED

        if any(
            keyword in status_lower
            for keyword in ["out for delivery", "out_for_delivery"]
        ):
            return PackageStatus.OUT_FOR_DELIVERY

        if any(
            keyword in status_lower
            for keyword in ["in transit", "in_transit", "on the way"]
        ):
            return PackageStatus.IN_TRANSIT

        if any(
            keyword in status_lower
            for keyword in ["shipped", "picked up", "departed"]
        ):
            return PackageStatus.SHIPPED

        if any(
            keyword in status_lower
            for keyword in [
                "label created",
                "label_created",
                "pre-shipment",
                "information received",
            ]
        ):
            return PackageStatus.LABEL_CREATED

        if any(
            keyword in status_lower
            for keyword in [
                "attempted",
                "delivery attempted",
                "notice left",
            ]
        ):
            return PackageStatus.ATTEMPTED_DELIVERY

        if any(
            keyword in status_lower
            for keyword in [
                "exception",
                "delayed",
                "held",
                "undeliverable",
            ]
        ):
            return PackageStatus.EXCEPTION

        if any(
            keyword in status_lower
            for keyword in ["returned", "return to sender"]
        ):
            return PackageStatus.RETURNED

        if any(keyword in status_lower for keyword in ["cancelled", "canceled"]):
            return PackageStatus.CANCELLED

        # Default to in_transit if unknown
        return PackageStatus.IN_TRANSIT

    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse courier-specific timestamp format.

        Args:
            timestamp_str: Timestamp string from courier

        Returns:
            Parsed datetime object
        """
        # Common timestamp formats
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
            "%Y-%m-%dT%H:%M:%S",  # ISO 8601 without timezone
            "%Y-%m-%d %H:%M:%S",  # Space-separated
            "%m/%d/%Y %H:%M:%S",  # US format
            "%d/%m/%Y %H:%M:%S",  # EU format
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # Fallback: return current time
        return datetime.utcnow()


class CourierAPIError(Exception):
    """Base exception for courier API errors."""

    pass


class TrackingNotFoundError(CourierAPIError):
    """Exception raised when tracking number is not found."""

    pass


class RateLimitError(CourierAPIError):
    """Exception raised when API rate limit is exceeded."""

    pass


class AuthenticationError(CourierAPIError):
    """Exception raised when API authentication fails."""

    pass
