"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.auth.schemas import (
    PasswordChange,
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.auth.service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """Register a new user."""
    user = await AuthService.register_user(user_data)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        timezone=user.timezone,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Login and receive access and refresh tokens."""
    tokens = await AuthService.login(login_data)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: TokenRefresh):
    """Refresh access token using refresh token."""
    tokens = await AuthService.refresh_access_token(token_data.refresh_token)
    return TokenResponse(**tokens)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        timezone=current_user.timezone,
        created_at=current_user.created_at,
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
):
    """Change user password."""
    await AuthService.change_password(current_user, password_data)
    return None


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout user (client should delete tokens)."""
    # In a stateless JWT system, logout is handled client-side
    # by deleting the tokens. This endpoint is here for completeness
    # and could be extended to implement token blacklisting if needed.
    return None
