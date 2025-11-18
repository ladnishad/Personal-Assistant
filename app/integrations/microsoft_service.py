"""Microsoft OAuth and API service."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import msal
import requests

from app.config import settings
from app.integrations.models import Integration

logger = logging.getLogger(__name__)


class MicrosoftService:
    """Microsoft OAuth and API service."""

    # OAuth scopes
    OUTLOOK_SCOPES = [
        "https://graph.microsoft.com/Mail.Read",
        "https://graph.microsoft.com/Mail.ReadWrite",
    ]
    CALENDAR_SCOPES = [
        "https://graph.microsoft.com/Calendars.Read",
        "https://graph.microsoft.com/Calendars.ReadWrite",
    ]
    USER_SCOPES = ["https://graph.microsoft.com/User.Read"]

    AUTHORITY = "https://login.microsoftonline.com/"

    @staticmethod
    def _get_msal_app():
        """Get MSAL confidential client application."""
        return msal.ConfidentialClientApplication(
            settings.microsoft_client_id,
            authority=f"{MicrosoftService.AUTHORITY}{settings.microsoft_tenant_id}",
            client_credential=settings.microsoft_client_secret,
        )

    @staticmethod
    def get_authorization_url(state: str, scopes: list[str]) -> str:
        """Generate Microsoft OAuth authorization URL."""
        # Map scope names to actual Microsoft scopes
        scope_mapping = {
            "email": MicrosoftService.OUTLOOK_SCOPES,
            "outlook": MicrosoftService.OUTLOOK_SCOPES,
            "calendar": MicrosoftService.CALENDAR_SCOPES,
        }

        # Build full scopes list
        full_scopes = MicrosoftService.USER_SCOPES.copy()
        for scope in scopes:
            if scope.lower() in scope_mapping:
                full_scopes.extend(scope_mapping[scope.lower()])
            else:
                full_scopes.append(scope)

        # Remove duplicates
        full_scopes = list(set(full_scopes))

        # Get authorization URL
        app = MicrosoftService._get_msal_app()
        auth_url = app.get_authorization_request_url(
            scopes=full_scopes,
            state=state,
            redirect_uri=settings.microsoft_redirect_uri,
        )

        return auth_url

    @staticmethod
    async def exchange_code_for_tokens(code: str, scopes: list[str] = None) -> dict:
        """Exchange authorization code for access and refresh tokens."""
        app = MicrosoftService._get_msal_app()

        # Use provided scopes or default to USER_SCOPES
        if scopes is None:
            scopes = MicrosoftService.USER_SCOPES

        result = app.acquire_token_by_authorization_code(
            code=code,
            scopes=scopes,
            redirect_uri=settings.microsoft_redirect_uri,
        )

        if "error" in result:
            logger.error(f"Error exchanging code: {result.get('error_description')}")
            raise Exception(result.get("error_description"))

        # Get user email
        user_info = await MicrosoftService._get_user_info(result["access_token"])

        # Calculate token expiry
        expires_in = result.get("expires_in", 3600)
        token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        return {
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token"),
            "token_expiry": token_expiry,
            "scope": result.get("scope", "").split(),
            "email": user_info.get("mail") or user_info.get("userPrincipalName"),
            "account_id": user_info.get("id"),
        }

    @staticmethod
    async def _get_user_info(access_token: str) -> dict:
        """Get user information from Microsoft Graph."""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me", headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting Microsoft user info: {e}")
            return {}

    @staticmethod
    async def refresh_access_token(integration: Integration) -> Integration:
        """Refresh Microsoft access token."""
        try:
            app = MicrosoftService._get_msal_app()

            result = app.acquire_token_by_refresh_token(
                refresh_token=integration.refresh_token,
                scopes=integration.scope or MicrosoftService.USER_SCOPES,
            )

            if "error" in result:
                logger.error(f"Error refreshing token: {result.get('error_description')}")
                raise Exception(result.get("error_description"))

            # Calculate token expiry
            expires_in = result.get("expires_in", 3600)
            token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

            # Update integration
            integration.access_token = result["access_token"]
            if "refresh_token" in result:
                integration.refresh_token = result["refresh_token"]
            integration.token_expiry = token_expiry
            integration.updated_at = datetime.utcnow()

            await integration.save()

            logger.info(f"Refreshed Microsoft access token for integration {integration.id}")

            return integration

        except Exception as e:
            logger.error(f"Error refreshing Microsoft access token: {e}")
            raise

    @staticmethod
    async def check_and_refresh_token(integration: Integration) -> Integration:
        """Check token expiry and refresh if needed."""
        if integration.token_expiry:
            # Refresh if token expires in less than 5 minutes
            if integration.token_expiry < datetime.utcnow() + timedelta(minutes=5):
                integration = await MicrosoftService.refresh_access_token(integration)

        return integration
