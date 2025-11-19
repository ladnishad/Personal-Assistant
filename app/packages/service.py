"""Package tracking service layer."""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from beanie import PydanticObjectId

from app.packages.models import CourierService, Package, PackageStatus, TrackingEvent
from app.packages.schemas import PackageCreate, PackageUpdate

logger = logging.getLogger(__name__)


class PackageService:
    """Package tracking service."""

    @staticmethod
    async def create_package(
        user_id: PydanticObjectId, package_data: PackageCreate
    ) -> Package:
        """Create a new package tracking entry.

        Args:
            user_id: User ID who owns the package
            package_data: Package creation data

        Returns:
            Created package

        Raises:
            ValueError: If package with same tracking number already exists
        """
        # Check if package already exists for this user
        existing = await Package.find_one(
            Package.tracking_number == package_data.tracking_number,
            Package.courier_service == package_data.courier_service,
        )

        if existing:
            logger.warning(
                f"Package {package_data.tracking_number} already exists for user {user_id}"
            )
            raise ValueError(
                f"Package with tracking number {package_data.tracking_number} already exists"
            )

        # Convert email_id string to ObjectId if provided
        email_id = None
        if package_data.email_id:
            try:
                email_id = PydanticObjectId(package_data.email_id)
            except Exception:
                logger.warning(f"Invalid email_id: {package_data.email_id}")

        # Create package
        package = Package(
            user_id=user_id,
            email_id=email_id,
            tracking_number=package_data.tracking_number,
            courier_service=package_data.courier_service,
            status=package_data.status,
            product_name=package_data.product_name,
            product_description=package_data.product_description,
            merchant=package_data.merchant,
            order_number=package_data.order_number,
            estimated_delivery=package_data.estimated_delivery,
            detection_confidence=package_data.detection_confidence,
            detection_source=package_data.detection_source,
        )

        await package.insert()
        logger.info(
            f"Created package {package.id} for user {user_id}: {package.tracking_number}"
        )

        return package

    @staticmethod
    async def get_package(
        package_id: str, user_id: PydanticObjectId
    ) -> Optional[Package]:
        """Get a package by ID.

        Args:
            package_id: Package ID
            user_id: User ID (for authorization)

        Returns:
            Package if found and belongs to user, None otherwise
        """
        try:
            package = await Package.get(PydanticObjectId(package_id))
            if package and package.user_id == user_id:
                return package
            return None
        except Exception as e:
            logger.error(f"Error getting package {package_id}: {e}")
            return None

    @staticmethod
    async def get_user_packages(
        user_id: PydanticObjectId,
        status: Optional[PackageStatus] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Package], int]:
        """Get packages for a user with filters.

        Args:
            user_id: User ID
            status: Filter by package status
            is_active: Filter by active/inactive
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (packages list, total count)
        """
        # Build query
        query = {"user_id": user_id}

        if status is not None:
            query["status"] = status

        if is_active is not None:
            query["is_active"] = is_active

        # Get packages
        packages = (
            await Package.find(query)
            .sort(-Package.created_at)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        # Get total count
        total = await Package.find(query).count()

        return packages, total

    @staticmethod
    async def get_active_packages(
        user_id: Optional[PydanticObjectId] = None,
    ) -> List[Package]:
        """Get all active packages (optionally filtered by user).

        Args:
            user_id: Optional user ID to filter by

        Returns:
            List of active packages
        """
        query = {"is_active": True}
        if user_id:
            query["user_id"] = user_id

        packages = await Package.find(query).to_list()
        return packages

    @staticmethod
    async def get_packages_needing_update() -> List[Package]:
        """Get packages that need status update (based on check interval).

        Returns:
            List of packages that should be checked
        """
        packages = await Package.find(Package.is_active == True).to_list()

        # Filter to only those that should be checked
        return [p for p in packages if p.should_check_status()]

    @staticmethod
    async def update_package(
        package_id: str, user_id: PydanticObjectId, update_data: PackageUpdate
    ) -> Optional[Package]:
        """Update a package.

        Args:
            package_id: Package ID
            user_id: User ID (for authorization)
            update_data: Update data

        Returns:
            Updated package if found and belongs to user, None otherwise
        """
        package = await PackageService.get_package(package_id, user_id)
        if not package:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(package, field, value)

        package.update_timestamp()
        await package.save()

        logger.info(f"Updated package {package_id}")
        return package

    @staticmethod
    async def add_tracking_event(
        package_id: str, user_id: PydanticObjectId, event: TrackingEvent
    ) -> Optional[Package]:
        """Add a tracking event to a package.

        Args:
            package_id: Package ID
            user_id: User ID (for authorization)
            event: Tracking event to add

        Returns:
            Updated package if found and belongs to user, None otherwise
        """
        package = await PackageService.get_package(package_id, user_id)
        if not package:
            return None

        package.add_event(event)
        await package.save()

        logger.info(f"Added tracking event to package {package_id}")
        return package

    @staticmethod
    async def update_package_status(
        tracking_number: str,
        courier_service: CourierService,
        status: PackageStatus,
        events: List[TrackingEvent],
        current_location: Optional[str] = None,
        estimated_delivery: Optional[datetime] = None,
    ) -> Optional[Package]:
        """Update package status from courier API.

        Args:
            tracking_number: Tracking number
            courier_service: Courier service
            status: New status
            events: List of tracking events
            current_location: Current location
            estimated_delivery: Estimated delivery date

        Returns:
            Updated package if found, None otherwise
        """
        package = await Package.find_one(
            Package.tracking_number == tracking_number,
            Package.courier_service == courier_service,
        )

        if not package:
            logger.warning(
                f"Package not found for tracking update: {tracking_number}"
            )
            return None

        # Update status
        package.status = status
        package.last_checked_at = datetime.utcnow()

        if current_location:
            package.current_location = current_location

        if estimated_delivery:
            package.estimated_delivery = estimated_delivery

        # Add new events
        for event in events:
            package.add_event(event)

        # Handle delivered status
        if status == PackageStatus.DELIVERED:
            package.mark_delivered()

        # Handle exception status
        elif status == PackageStatus.EXCEPTION:
            package.mark_exception()

        await package.save()

        logger.info(
            f"Updated package status for {tracking_number}: {status.value}"
        )
        return package

    @staticmethod
    async def delete_package(package_id: str, user_id: PydanticObjectId) -> bool:
        """Delete a package.

        Args:
            package_id: Package ID
            user_id: User ID (for authorization)

        Returns:
            True if deleted, False otherwise
        """
        package = await PackageService.get_package(package_id, user_id)
        if not package:
            return False

        await package.delete()
        logger.info(f"Deleted package {package_id}")
        return True

    @staticmethod
    async def get_package_by_tracking(
        tracking_number: str, courier_service: Optional[CourierService] = None
    ) -> Optional[Package]:
        """Get package by tracking number and optionally courier.

        Args:
            tracking_number: Tracking number
            courier_service: Optional courier service. If not provided, searches by tracking number only.

        Returns:
            Package if found, None otherwise
        """
        if courier_service:
            package = await Package.find_one(
                Package.tracking_number == tracking_number,
                Package.courier_service == courier_service,
            )
        else:
            # Search by tracking number only
            package = await Package.find_one(
                Package.tracking_number == tracking_number,
            )
        return package
