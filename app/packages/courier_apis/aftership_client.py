"""AfterShip tracking API client using official Python SDK."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import tracking
from tracking import auth

from app.packages.courier_apis.base_courier import (
    AuthenticationError,
    BaseCourierClient,
    CourierAPIError,
    RateLimitError,
    TrackingNotFoundError,
)
from app.packages.models import CourierService, PackageStatus, TrackingEvent
from app.packages.schemas import CourierTrackingResponse

logger = logging.getLogger(__name__)


class AfterShipClient(BaseCourierClient):
    """AfterShip tracking API client for unified multi-carrier tracking.

    Supports 1,100+ carriers worldwide through a single API.
    Uses official AfterShip Python SDK.

    API Documentation: https://github.com/AfterShip/tracking-sdk-python
    """

    # Map AfterShip tags to our PackageStatus enum
    TAG_STATUS_MAP = {
        "Pending": PackageStatus.LABEL_CREATED,
        "InfoReceived": PackageStatus.LABEL_CREATED,
        "InTransit": PackageStatus.IN_TRANSIT,
        "OutForDelivery": PackageStatus.OUT_FOR_DELIVERY,
        "AttemptFail": PackageStatus.ATTEMPTED_DELIVERY,
        "Delivered": PackageStatus.DELIVERED,
        "AvailableForPickup": PackageStatus.IN_TRANSIT,
        "Exception": PackageStatus.EXCEPTION,
        "Expired": PackageStatus.EXCEPTION,
    }

    # Map our CourierService enum to AfterShip slugs
    COURIER_SLUG_MAP = {
        CourierService.USPS: "usps",
        CourierService.FEDEX: "fedex",
        CourierService.UPS: "ups",
        CourierService.AMAZON: "amazon",
        CourierService.DHL: "dhl-global-mail",
        CourierService.ONTRAC: "ontrac",
        CourierService.LASERSHIP: "lasership",
        CourierService.UNKNOWN: None,
    }

    def __init__(self, api_key: str, max_retry: int = 3, timeout: int = 10000):
        """Initialize AfterShip client.

        Args:
            api_key: AfterShip API key
            max_retry: Number of request retries (default: 3, max: 10)
            timeout: Request timeout in milliseconds (default: 10000 = 10 seconds)
        """
        super().__init__(api_key)

        if not api_key:
            raise ValueError("AfterShip API key is required")

        # Initialize AfterShip SDK
        self.sdk = tracking.Client(
            tracking.Configuration(
                api_key=api_key,
                authentication_type=auth.ApiKey,
                max_retry=min(max_retry, 10),  # Max 10 retries
                timeout=timeout,
            )
        )

        logger.info("AfterShip client initialized successfully")

    async def track_package(self, tracking_number: str) -> CourierTrackingResponse:
        """Track a package using AfterShip API.

        AfterShip auto-detects the courier from the tracking number.
        If tracking doesn't exist in AfterShip, it will be created automatically.

        Args:
            tracking_number: Package tracking number

        Returns:
            CourierTrackingResponse with tracking details

        Raises:
            TrackingNotFoundError: If tracking number is invalid
            RateLimitError: If API rate limit exceeded
            AuthenticationError: If API key is invalid
            CourierAPIError: For other API errors
        """
        logger.info(f"Tracking package via AfterShip: {tracking_number}")

        try:
            # Try to get existing tracking first
            # Wrap synchronous SDK calls in asyncio.to_thread to prevent blocking
            try:
                result = await asyncio.to_thread(
                    self.sdk.tracking.get_tracking_by_id, tracking_id=tracking_number
                )
                logger.debug(f"Retrieved existing tracking: {tracking_number}")
            except Exception:
                # Tracking doesn't exist - create it
                req = tracking.CreateTrackingRequest()
                req.tracking_number = tracking_number
                # Let AfterShip auto-detect the courier (don't specify slug)

                result = await asyncio.to_thread(
                    self.sdk.tracking.create_tracking, req
                )
                logger.info(f"Created new tracking: {tracking_number}")

            # Parse AfterShip response to our format
            return self._parse_aftership_response(result)

        except tracking.RateLimitExceedError as e:
            logger.error(f"AfterShip rate limit exceeded: {e}")
            raise RateLimitError("AfterShip API rate limit exceeded (10 req/sec)")

        except tracking.InvalidRequestError as e:
            logger.error(f"Invalid tracking request: {e}")
            raise TrackingNotFoundError(f"Invalid tracking number: {tracking_number}")

        except tracking.UnauthorizedError as e:
            logger.error(f"AfterShip authentication failed: {e}")
            raise AuthenticationError("Invalid AfterShip API key")

        except Exception as e:
            logger.error(f"AfterShip API error: {e}")
            raise CourierAPIError(f"AfterShip API error: {str(e)}")

    def _parse_aftership_response(
        self, result: tracking.TrackingResponse
    ) -> CourierTrackingResponse:
        """Parse AfterShip API response to our CourierTrackingResponse format.

        Args:
            result: AfterShip TrackingResponse object

        Returns:
            CourierTrackingResponse with parsed data
        """
        tracking_data = result.data.tracking

        # Parse courier slug to our CourierService enum
        courier_service = self._parse_courier_slug(tracking_data.slug)

        # Parse status tag
        status = self._parse_aftership_tag(tracking_data.tag)

        # Parse delivery time
        estimated_delivery = None
        if tracking_data.expected_delivery:
            estimated_delivery = self._parse_iso_datetime(
                tracking_data.expected_delivery
            )

        actual_delivery = None
        if status == PackageStatus.DELIVERED and tracking_data.delivery_time:
            actual_delivery = self._parse_iso_datetime(tracking_data.delivery_time)

        # Parse checkpoints (tracking events)
        events = []
        if tracking_data.checkpoints:
            for checkpoint in tracking_data.checkpoints:
                event = TrackingEvent(
                    timestamp=self._parse_iso_datetime(checkpoint.checkpoint_time),
                    status=checkpoint.tag or "unknown",
                    location=self._format_location(checkpoint),
                    description=checkpoint.message or "No details",
                    city=checkpoint.city,
                    state=checkpoint.state,
                    country_iso3=checkpoint.country_iso3,
                    zip=checkpoint.zip,
                )
                events.append(event)

        # Get current location from latest checkpoint
        current_location = None
        if events:
            current_location = events[0].location

        response = CourierTrackingResponse(
            tracking_number=tracking_data.tracking_number,
            courier_service=courier_service,
            status=status,
            current_location=current_location,
            estimated_delivery=estimated_delivery,
            actual_delivery=actual_delivery,
            events=events,
            raw_data={
                "aftership_id": tracking_data.id,
                "slug": tracking_data.slug,
                "tag": tracking_data.tag,
                "subtag": tracking_data.subtag,
            },
        )

        logger.debug(
            f"Parsed AfterShip response: {tracking_data.tracking_number} - {status.value}"
        )

        return response

    def _parse_courier_slug(self, slug: str) -> CourierService:
        """Parse AfterShip courier slug to our CourierService enum.

        Args:
            slug: AfterShip courier slug (e.g., "ups", "fedex")

        Returns:
            CourierService enum value
        """
        # Reverse lookup in our slug map
        slug_lower = slug.lower()

        for courier, aftership_slug in self.COURIER_SLUG_MAP.items():
            if aftership_slug == slug_lower:
                return courier

        # If not found, return UNKNOWN
        logger.warning(f"Unknown courier slug: {slug}")
        return CourierService.UNKNOWN

    def _parse_aftership_tag(self, tag: str) -> PackageStatus:
        """Parse AfterShip tag to our PackageStatus enum.

        Args:
            tag: AfterShip status tag

        Returns:
            PackageStatus enum value
        """
        return self.TAG_STATUS_MAP.get(tag, PackageStatus.IN_TRANSIT)

    def _parse_iso_datetime(self, datetime_str: str) -> datetime:
        """Parse ISO 8601 datetime string.

        Args:
            datetime_str: ISO datetime string

        Returns:
            Parsed datetime object
        """
        try:
            # Try parsing with timezone
            if "+" in datetime_str or datetime_str.endswith("Z"):
                return datetime.fromisoformat(
                    datetime_str.replace("Z", "+00:00")
                )
            # Parse without timezone
            return datetime.fromisoformat(datetime_str)
        except Exception:
            # Fallback to parent class method
            return self.parse_timestamp(datetime_str)

    def _format_location(self, checkpoint) -> str:
        """Format checkpoint location as human-readable string.

        Args:
            checkpoint: AfterShip checkpoint object

        Returns:
            Formatted location string
        """
        parts = []

        if checkpoint.city:
            parts.append(checkpoint.city)
        if checkpoint.state:
            parts.append(checkpoint.state)
        if checkpoint.country_name:
            parts.append(checkpoint.country_name)
        elif checkpoint.country_iso3:
            parts.append(checkpoint.country_iso3)

        return ", ".join(parts) if parts else "Unknown location"

    def get_courier_name(self) -> str:
        """Get courier name.

        Returns:
            Courier service name
        """
        return "AfterShip (Multi-Carrier)"

    def parse_status(self, status_code: str) -> PackageStatus:
        """Parse AfterShip tag to PackageStatus.

        Args:
            status_code: AfterShip tag

        Returns:
            PackageStatus enum
        """
        return self._parse_aftership_tag(status_code)
