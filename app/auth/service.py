"""Authentication service layer."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status

from app.auth.models import User
from app.auth.schemas import PasswordChange, UserLogin, UserRegister
from app.auth.utils import (
    create_token_pair,
    decode_token,
    get_password_hash,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service."""

    @staticmethod
    async def register_user(user_data: UserRegister) -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = await User.find_one(User.email == user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create new user
        user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            timezone=user_data.timezone,
        )

        await user.insert()
        logger.info(f"New user registered: {user.email}")

        return user

    @staticmethod
    async def authenticate_user(login_data: UserLogin) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await User.find_one(User.email == login_data.email)

        if not user:
            return None

        if not verify_password(login_data.password, user.hashed_password):
            return None

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        return user

    @staticmethod
    async def login(login_data: UserLogin) -> dict:
        """Login user and return tokens."""
        user = await AuthService.authenticate_user(login_data)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create token pair
        tokens = create_token_pair(str(user.id))

        logger.info(f"User logged in: {user.email}")

        return tokens

    @staticmethod
    async def refresh_access_token(refresh_token: str) -> dict:
        """Refresh access token using refresh token."""
        # Decode refresh token
        payload = decode_token(refresh_token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # Get user ID
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        # Verify user exists
        user = await User.get(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Create new token pair
        tokens = create_token_pair(user_id)

        return tokens

    @staticmethod
    async def change_password(user: User, password_data: PasswordChange) -> bool:
        """Change user password."""
        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password",
            )

        # Update password
        user.hashed_password = get_password_hash(password_data.new_password)
        user.updated_at = datetime.utcnow()
        await user.save()

        logger.info(f"Password changed for user: {user.email}")

        return True
