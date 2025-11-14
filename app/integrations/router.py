"""Integration API routes."""

import logging
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.integrations.google_service import GoogleService
from app.integrations.microsoft_service import MicrosoftService
from app.integrations.models import Integration, IntegrationType
from app.integrations.schemas import (
    IntegrationConnectRequest,
    IntegrationConnectResponse,
    IntegrationListResponse,
    IntegrationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/google/connect", response_model=IntegrationConnectResponse)
async def connect_google(
    request: IntegrationConnectRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Initiate Google OAuth connection."""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session or cache (simplified for MVP)
    # In production, store this in Redis with expiration

    # Get authorization URL
    auth_url = GoogleService.get_authorization_url(state, request.scopes)

    return IntegrationConnectResponse(authorization_url=auth_url, state=state)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    current_user: User = Depends(get_current_active_user),
):
    """Handle Google OAuth callback."""
    try:
        # Exchange code for tokens
        token_data = await GoogleService.exchange_code_for_tokens(code)

        # Check if integration already exists
        existing = await Integration.find_one(
            Integration.user_id == current_user.id,
            Integration.integration_type == IntegrationType.GOOGLE,
        )

        if existing:
            # Update existing integration
            existing.access_token = token_data["access_token"]
            existing.refresh_token = token_data["refresh_token"]
            existing.token_expiry = token_data["token_expiry"]
            existing.scope = token_data["scope"]
            existing.email = token_data["email"]
            existing.account_id = token_data["account_id"]
            existing.is_active = True
            await existing.save()
            integration = existing
        else:
            # Create new integration
            integration = Integration(
                user_id=current_user.id,
                integration_type=IntegrationType.GOOGLE,
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_expiry=token_data["token_expiry"],
                scope=token_data["scope"],
                email=token_data["email"],
                account_id=token_data["account_id"],
            )
            await integration.insert()

        logger.info(f"Google integration connected for user {current_user.email}")

        return {"message": "Google account connected successfully", "integration_id": str(integration.id)}

    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect Google account: {str(e)}",
        )


@router.post("/microsoft/connect", response_model=IntegrationConnectResponse)
async def connect_microsoft(
    request: IntegrationConnectRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Initiate Microsoft OAuth connection."""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Get authorization URL
    auth_url = MicrosoftService.get_authorization_url(state, request.scopes)

    return IntegrationConnectResponse(authorization_url=auth_url, state=state)


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str = Query(...),
    state: str = Query(...),
    current_user: User = Depends(get_current_active_user),
):
    """Handle Microsoft OAuth callback."""
    try:
        # Exchange code for tokens
        token_data = await MicrosoftService.exchange_code_for_tokens(code)

        # Check if integration already exists
        existing = await Integration.find_one(
            Integration.user_id == current_user.id,
            Integration.integration_type == IntegrationType.MICROSOFT,
        )

        if existing:
            # Update existing integration
            existing.access_token = token_data["access_token"]
            existing.refresh_token = token_data["refresh_token"]
            existing.token_expiry = token_data["token_expiry"]
            existing.scope = token_data["scope"]
            existing.email = token_data["email"]
            existing.account_id = token_data["account_id"]
            existing.is_active = True
            await existing.save()
            integration = existing
        else:
            # Create new integration
            integration = Integration(
                user_id=current_user.id,
                integration_type=IntegrationType.MICROSOFT,
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_expiry=token_data["token_expiry"],
                scope=token_data["scope"],
                email=token_data["email"],
                account_id=token_data["account_id"],
            )
            await integration.insert()

        logger.info(f"Microsoft integration connected for user {current_user.email}")

        return {"message": "Microsoft account connected successfully", "integration_id": str(integration.id)}

    except Exception as e:
        logger.error(f"Error in Microsoft OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect Microsoft account: {str(e)}",
        )


@router.get("/", response_model=IntegrationListResponse)
async def list_integrations(current_user: User = Depends(get_current_active_user)):
    """List all integrations for the current user."""
    integrations = await Integration.find(Integration.user_id == current_user.id).to_list()

    integration_responses = [
        IntegrationResponse(
            _id=str(i.id),
            user_id=str(i.user_id),
            integration_type=i.integration_type,
            is_active=i.is_active,
            email=i.email,
            scope=i.scope,
            last_email_sync=i.last_email_sync,
            last_calendar_sync=i.last_calendar_sync,
            created_at=i.created_at,
        )
        for i in integrations
    ]

    return IntegrationListResponse(
        integrations=integration_responses, total=len(integration_responses)
    )


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Delete an integration."""
    integration = await Integration.get(integration_id)

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    if integration.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this integration",
        )

    await integration.delete()
    logger.info(f"Integration {integration_id} deleted for user {current_user.email}")

    return None
