"""OAuth state storage for handling OAuth flow state management."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class OAuthStateStorage:
    """
    Simple in-memory OAuth state storage.

    NOTE: This is a simple MVP implementation using in-memory storage.
    For production, this should be replaced with Redis to support:
    - Multiple backend instances
    - Persistent storage across restarts
    - Automatic TTL/expiration
    """

    _storage: Dict[str, Dict] = {}

    @classmethod
    def store(
        cls,
        state: str,
        user_id: str,
        scopes: list[str],
        ttl_minutes: int = 10,
    ) -> None:
        """
        Store OAuth state data.

        Args:
            state: OAuth state parameter
            user_id: User ID initiating the OAuth flow
            scopes: List of requested OAuth scopes
            ttl_minutes: Time to live in minutes (default 10)
        """
        expiry = datetime.utcnow() + timedelta(minutes=ttl_minutes)

        cls._storage[state] = {
            "user_id": user_id,
            "scopes": scopes,
            "expiry": expiry,
        }

        logger.info(f"Stored OAuth state for user {user_id}, expires at {expiry}")

        # Clean up expired entries
        cls._cleanup_expired()

    @classmethod
    def get(cls, state: str) -> Optional[Dict]:
        """
        Retrieve OAuth state data.

        Args:
            state: OAuth state parameter

        Returns:
            Dictionary with user_id and scopes, or None if not found/expired
        """
        data = cls._storage.get(state)

        if not data:
            logger.warning(f"OAuth state not found: {state}")
            return None

        # Check if expired
        if data["expiry"] < datetime.utcnow():
            logger.warning(f"OAuth state expired: {state}")
            del cls._storage[state]
            return None

        return data

    @classmethod
    def delete(cls, state: str) -> None:
        """
        Delete OAuth state data.

        Args:
            state: OAuth state parameter
        """
        if state in cls._storage:
            del cls._storage[state]
            logger.info(f"Deleted OAuth state: {state}")

    @classmethod
    def _cleanup_expired(cls) -> None:
        """Remove expired state entries."""
        now = datetime.utcnow()
        expired_states = [
            state for state, data in cls._storage.items() if data["expiry"] < now
        ]

        for state in expired_states:
            del cls._storage[state]

        if expired_states:
            logger.info(f"Cleaned up {len(expired_states)} expired OAuth states")
