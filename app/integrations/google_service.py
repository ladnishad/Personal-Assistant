"""Google OAuth and API service."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import settings
from app.integrations.models import Integration, IntegrationType

logger = logging.getLogger(__name__)


class GoogleService:
    """Google OAuth and API service."""

    # OAuth scopes
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]
    CALENDAR_SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    @staticmethod
    def get_authorization_url(state: str, scopes: list[str]) -> str:
        """Generate Google OAuth authorization URL."""
        # Map scope names to actual Google scopes
        scope_mapping = {
            "email": GoogleService.GMAIL_SCOPES,
            "gmail": GoogleService.GMAIL_SCOPES,
            "calendar": GoogleService.CALENDAR_SCOPES,
        }

        # Build full scopes list
        full_scopes = []
        for scope in scopes:
            if scope.lower() in scope_mapping:
                full_scopes.extend(scope_mapping[scope.lower()])
            else:
                full_scopes.append(scope)

        # Remove duplicates
        full_scopes = list(set(full_scopes))

        # Create flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.google_redirect_uri],
                }
            },
            scopes=full_scopes,
            redirect_uri=settings.google_redirect_uri,
        )

        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",  # Force to get refresh token
        )

        return authorization_url

    @staticmethod
    async def exchange_code_for_tokens(code: str) -> dict:
        """Exchange authorization code for access and refresh tokens."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.google_redirect_uri],
                }
            },
            scopes=[],
            redirect_uri=settings.google_redirect_uri,
        )

        flow.fetch_token(code=code)

        credentials = flow.credentials

        # Get user email
        user_info = await GoogleService._get_user_info(credentials)

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_expiry": credentials.expiry,
            "scope": credentials.scopes,
            "email": user_info.get("email"),
            "account_id": user_info.get("id"),
        }

    @staticmethod
    async def _get_user_info(credentials: Credentials) -> dict:
        """Get user information from Google."""
        try:
            service = build("oauth2", "v2", credentials=credentials)
            user_info = service.userinfo().get().execute()
            return user_info
        except Exception as e:
            logger.error(f"Error getting Google user info: {e}")
            return {}

    @staticmethod
    async def refresh_access_token(integration: Integration) -> Integration:
        """Refresh Google access token."""
        try:
            credentials = Credentials(
                token=integration.access_token,
                refresh_token=integration.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )

            # Refresh the token
            credentials.refresh(Request())

            # Update integration
            integration.access_token = credentials.token
            integration.token_expiry = credentials.expiry
            integration.updated_at = datetime.utcnow()

            await integration.save()

            logger.info(f"Refreshed Google access token for integration {integration.id}")

            return integration

        except Exception as e:
            logger.error(f"Error refreshing Google access token: {e}")
            raise

    @staticmethod
    def get_credentials(integration: Integration) -> Credentials:
        """Get Google credentials from integration."""
        return Credentials(
            token=integration.access_token,
            refresh_token=integration.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=integration.scope,
        )

    @staticmethod
    async def check_and_refresh_token(integration: Integration) -> Integration:
        """Check token expiry and refresh if needed."""
        if integration.token_expiry:
            # Refresh if token expires in less than 5 minutes
            if integration.token_expiry < datetime.utcnow() + timedelta(minutes=5):
                integration = await GoogleService.refresh_access_token(integration)

        return integration
