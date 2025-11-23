"""API routes for user confirmations."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.confirmations.models import (
    ConfirmationResponse,
    PendingConfirmation,
    UserConfirmationDecision,
)
from app.confirmations.service import ConfirmationService

router = APIRouter()


@router.get("/pending", response_model=List[PendingConfirmation])
async def get_pending_confirmations(current_user: User = Depends(get_current_active_user)):
    """Get all pending confirmations for the current user.

    The iOS app should poll this endpoint periodically (e.g., every 2-3 seconds)
    to check for new confirmation requests from the agent.

    Returns:
        List of pending confirmations that need user approval/denial
    """
    confirmations = await ConfirmationService.get_pending_confirmations(str(current_user.id))
    return confirmations


@router.post("/{confirmation_id}/respond", response_model=ConfirmationResponse)
async def respond_to_confirmation(
    confirmation_id: str,
    decision: UserConfirmationDecision,
    current_user: User = Depends(get_current_active_user),
):
    """Respond to a confirmation request.

    The iOS app calls this when the user approves or denies an action.

    Args:
        confirmation_id: ID of the confirmation to respond to
        decision: User's decision (approved: true/false, optional note)

    Returns:
        ConfirmationResponse with the result
    """
    try:
        # Pass user_id for ownership validation
        result = await ConfirmationService.respond_to_confirmation(
            user_id=str(current_user.id),
            confirmation_id=confirmation_id,
            decision=decision
        )
        return result
    except ValueError as e:
        error_msg = str(e).lower()
        if "not authorized" in error_msg or "ownership" in error_msg:
            raise HTTPException(status_code=403, detail="Not authorized to modify this confirmation")
        elif "not found" in error_msg:
            raise HTTPException(status_code=404, detail="Confirmation not found")
        elif "already resolved" in error_msg or "expired" in error_msg:
            raise HTTPException(status_code=400, detail="Cannot respond to resolved confirmation")
        else:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/{confirmation_id}/status", response_model=ConfirmationResponse)
async def get_confirmation_status(
    confirmation_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get the current status of a specific confirmation.

    Args:
        confirmation_id: ID of the confirmation to check

    Returns:
        ConfirmationResponse with current status
    """
    result = await ConfirmationService.get_confirmation_status(
        user_id=str(current_user.id),
        confirmation_id=confirmation_id
    )

    if not result:
        raise HTTPException(status_code=404, detail="Confirmation not found")

    return result


@router.delete("/{confirmation_id}")
async def cancel_confirmation(
    confirmation_id: str, current_user: User = Depends(get_current_active_user)
):
    """Cancel a pending confirmation.

    Args:
        confirmation_id: ID of the confirmation to cancel

    Returns:
        Success message
    """
    success = await ConfirmationService.cancel_confirmation(
        user_id=str(current_user.id),
        confirmation_id=confirmation_id
    )

    if not success:
        raise HTTPException(
            status_code=400, detail="Confirmation not found or already resolved"
        )

    return {"message": "Confirmation cancelled successfully", "success": True}
