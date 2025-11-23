"""Service for managing user confirmations."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from beanie import PydanticObjectId

from app.confirmations.document import Confirmation
from app.confirmations.models import (
    ConfirmationRequest,
    ConfirmationResponse,
    ConfirmationStatus,
    PendingConfirmation,
    RiskLevel,
    UserConfirmationDecision,
)

logger = logging.getLogger(__name__)


class ConfirmationService:
    """Service for creating and managing user confirmations."""

    @staticmethod
    def _to_object_id(id_value: str) -> PydanticObjectId:
        """Convert string ID to PydanticObjectId.

        Args:
            id_value: String representation of ObjectId

        Returns:
            PydanticObjectId instance

        Raises:
            ValueError: If id_value is not a valid ObjectId
        """
        if isinstance(id_value, PydanticObjectId):
            return id_value
        try:
            return PydanticObjectId(id_value)
        except Exception as e:
            raise ValueError(f"Invalid confirmation ID format: {id_value}") from e

    @staticmethod
    async def create_confirmation(
        user_id: str,
        action_description: str,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        timeout_seconds: int = 300,
        conversation_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Create a new confirmation request.

        Args:
            user_id: ID of the user who needs to confirm
            action_description: Clear description of the action
            risk_level: Risk level of the action
            timeout_seconds: How long to wait for response
            conversation_id: Optional conversation ID
            metadata: Optional additional context

        Returns:
            Confirmation ID
        """
        expires_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        confirmation = Confirmation(
            user_id=user_id,
            conversation_id=conversation_id,
            action_description=action_description,
            risk_level=risk_level,
            expires_at=expires_at,
            metadata=metadata,
        )

        await confirmation.insert()

        logger.info(
            f"Created confirmation {confirmation.id} for user {user_id}: {action_description}"
        )

        return str(confirmation.id)

    @staticmethod
    async def wait_for_response(
        confirmation_id: str, poll_interval: float = 1.0, user_id: Optional[str] = None
    ) -> ConfirmationResponse:
        """Wait for user to respond to a confirmation request.

        This polls the database for updates to the confirmation status.
        Returns when the user responds or when the confirmation expires.

        Args:
            confirmation_id: ID of the confirmation to wait for
            poll_interval: How often to check for updates (seconds)
            user_id: Optional user ID for ownership validation

        Returns:
            ConfirmationResponse with the result
        """
        # Convert to ObjectId for consistent DB queries
        object_id = ConfirmationService._to_object_id(confirmation_id)

        while True:
            confirmation = await Confirmation.get(object_id)

            if not confirmation:
                raise ValueError(f"Confirmation {confirmation_id} not found")

            # Validate ownership if user_id provided
            if user_id and str(confirmation.user_id) != user_id:
                raise ValueError(f"Not authorized to access confirmation {confirmation_id}")

            # Check if expired
            if datetime.utcnow() > confirmation.expires_at:
                if confirmation.status == ConfirmationStatus.PENDING:
                    # Mark as expired
                    confirmation.status = ConfirmationStatus.EXPIRED
                    confirmation.resolved_at = datetime.utcnow()
                    await confirmation.save()

                    logger.info(f"Confirmation {confirmation_id} expired")

                return ConfirmationResponse(
                    confirmation_id=str(confirmation.id),
                    status=ConfirmationStatus.EXPIRED,
                    approved=False,
                    created_at=confirmation.created_at,
                    resolved_at=confirmation.resolved_at,
                )

            # Check if resolved
            if confirmation.status != ConfirmationStatus.PENDING:
                return ConfirmationResponse(
                    confirmation_id=str(confirmation.id),
                    status=confirmation.status,
                    approved=confirmation.approved,
                    user_note=confirmation.user_note,
                    created_at=confirmation.created_at,
                    resolved_at=confirmation.resolved_at,
                )

            # Wait before polling again
            await asyncio.sleep(poll_interval)

    @staticmethod
    async def get_pending_confirmations(user_id: str) -> List[PendingConfirmation]:
        """Get all pending confirmations for a user.

        Args:
            user_id: User ID to get confirmations for

        Returns:
            List of pending confirmations
        """
        confirmations = await Confirmation.find(
            Confirmation.user_id == user_id, Confirmation.status == ConfirmationStatus.PENDING
        ).to_list()

        # Filter out expired ones
        now = datetime.utcnow()
        pending = []

        for conf in confirmations:
            if now > conf.expires_at:
                # Use atomic update to avoid race conditions
                await Confirmation.find_one(
                    Confirmation.id == conf.id,
                    Confirmation.status == ConfirmationStatus.PENDING
                ).update(
                    {"$set": {
                        "status": ConfirmationStatus.EXPIRED,
                        "resolved_at": now
                    }}
                )
                # Skip adding to pending list
            else:
                pending.append(
                    PendingConfirmation(
                        confirmation_id=str(conf.id),
                        action_description=conf.action_description,
                        risk_level=conf.risk_level,
                        created_at=conf.created_at,
                        expires_at=conf.expires_at,
                        metadata=conf.metadata,
                    )
                )

        return pending

    @staticmethod
    async def respond_to_confirmation(
        user_id: str,
        confirmation_id: str,
        decision: UserConfirmationDecision
    ) -> ConfirmationResponse:
        """Process user's response to a confirmation request.

        Args:
            user_id: ID of the user responding (for ownership validation)
            confirmation_id: ID of the confirmation
            decision: User's decision

        Returns:
            ConfirmationResponse with the result
        """
        # Convert to ObjectId for consistent DB queries
        object_id = ConfirmationService._to_object_id(confirmation_id)
        confirmation = await Confirmation.get(object_id)

        if not confirmation:
            raise ValueError(f"Confirmation {confirmation_id} not found")

        # Validate ownership - CRITICAL SECURITY CHECK
        if str(confirmation.user_id) != user_id:
            raise ValueError("Not authorized to modify this confirmation")

        # Check if already resolved
        if confirmation.status != ConfirmationStatus.PENDING:
            raise ValueError(
                f"Confirmation {confirmation_id} already resolved with status: {confirmation.status}"
            )

        # Check if expired
        if datetime.utcnow() > confirmation.expires_at:
            # Use atomic update to avoid race conditions
            result = await Confirmation.find_one(
                Confirmation.id == object_id,
                Confirmation.status == ConfirmationStatus.PENDING
            ).update(
                {"$set": {
                    "status": ConfirmationStatus.EXPIRED,
                    "resolved_at": datetime.utcnow()
                }}
            )
            if result and result.modified_count > 0:
                raise ValueError(f"Confirmation {confirmation_id} has expired")
            else:
                # Already updated by another process, fetch latest
                confirmation = await Confirmation.get(object_id)
                if confirmation and confirmation.status == ConfirmationStatus.EXPIRED:
                    raise ValueError(f"Confirmation {confirmation_id} has expired")

        # Update confirmation
        confirmation.status = (
            ConfirmationStatus.APPROVED if decision.approved else ConfirmationStatus.DENIED
        )
        confirmation.approved = decision.approved
        confirmation.user_note = decision.note
        confirmation.resolved_at = datetime.utcnow()

        await confirmation.save()

        logger.info(
            f"Confirmation {confirmation_id} resolved: "
            f"{'approved' if decision.approved else 'denied'}"
        )

        return ConfirmationResponse(
            confirmation_id=str(confirmation.id),
            status=confirmation.status,
            approved=confirmation.approved,
            user_note=confirmation.user_note,
            created_at=confirmation.created_at,
            resolved_at=confirmation.resolved_at,
        )

    @staticmethod
    async def cancel_confirmation(user_id: str, confirmation_id: str) -> bool:
        """Cancel a pending confirmation.

        Args:
            user_id: ID of the user (for ownership validation)
            confirmation_id: ID of the confirmation to cancel

        Returns:
            True if cancelled successfully
        """
        # Convert to ObjectId for consistent DB queries
        try:
            object_id = ConfirmationService._to_object_id(confirmation_id)
        except ValueError:
            return False  # Invalid ID format

        confirmation = await Confirmation.get(object_id)

        if not confirmation:
            return False

        # Validate ownership
        if str(confirmation.user_id) != user_id:
            return False

        if confirmation.status != ConfirmationStatus.PENDING:
            return False

        confirmation.status = ConfirmationStatus.CANCELLED
        confirmation.resolved_at = datetime.utcnow()
        await confirmation.save()

        logger.info(f"Confirmation {confirmation_id} cancelled")
        return True

    @staticmethod
    async def get_confirmation_status(user_id: str, confirmation_id: str) -> Optional[ConfirmationResponse]:
        """Get the current status of a confirmation.

        Args:
            user_id: ID of the user (for ownership validation)
            confirmation_id: ID of the confirmation

        Returns:
            ConfirmationResponse or None if not found
        """
        # Convert to ObjectId for consistent DB queries
        try:
            object_id = ConfirmationService._to_object_id(confirmation_id)
        except ValueError:
            return None  # Invalid ID format

        confirmation = await Confirmation.get(object_id)

        if not confirmation:
            return None

        # Validate ownership
        if str(confirmation.user_id) != user_id:
            return None  # Return None if unauthorized (acts as not found)

        return ConfirmationResponse(
            confirmation_id=str(confirmation.id),
            status=confirmation.status,
            approved=confirmation.approved,
            user_note=confirmation.user_note,
            created_at=confirmation.created_at,
            resolved_at=confirmation.resolved_at,
        )
