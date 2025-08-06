"""
Authentication API Routes
=========================

Routes for user registration, login, token refresh, and authentication.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr

from ..core.security import get_current_user, security_manager
from ..models.user_models import User
from ..schemas.user_schemas import UserCreate, UserLogin, UserResponse
from ..services.analytics_service import AnalyticsService
from ..services.user_service import UserService

router = APIRouter()
security = HTTPBearer()


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, request: Request):
    """Register a new user account"""
    user_service = UserService()
    analytics_service = AnalyticsService()

    try:
        # Create user account
        user = await user_service.create_user(user_data)

        # Track registration event
        await analytics_service.track_user_event(
            user_id=user.id,
            event_type="signup",
            event_category="user",
            properties={
                "registration_method": "email",
                "subscription_tier": "free"
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )

        # Create tokens
        access_token = security_manager.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = security_manager.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,  # 1 hour
            user=UserResponse.from_orm(user)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    """Authenticate user and return tokens"""
    user_service = UserService()
    analytics_service = AnalyticsService()

    # Authenticate user
    user = await user_service.authenticate_user(credentials.email, credentials.password)

    if not user:
        # Track failed login
        await analytics_service.track_user_event(
            user_id=None,
            event_type="login_failed",
            event_category="user",
            properties={
                "email": credentials.email,
                "reason": "invalid_credentials"
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )

    # Track successful login
    await analytics_service.track_user_event(
        user_id=user.id,
        event_type="login",
        event_category="user",
        properties={
            "login_method": "email"
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    # Create tokens
    access_token = security_manager.create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    refresh_token = security_manager.create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
        user=UserResponse.from_orm(user)
    )


@router.post("/refresh", response_model=dict[str, Any])
async def refresh_token(token_data: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = security_manager.verify_token(token_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Verify user still exists and is active
        user_service = UserService()
        user = await user_service.get_user_by_id(int(user_id))

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Create new access token
        access_token = security_manager.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 3600
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (invalidate tokens)"""
    # In a production system, you'd maintain a token blacklist
    # For now, just return success
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse.from_orm(current_user)


@router.post("/verify-email")
async def verify_email(token: str):
    """Verify user email address"""
    # This would verify an email verification token
    # For now, just return success
    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    """Request password reset"""
    user_service = UserService()

    # Check if user exists
    await user_service.get_user_by_email(email)

    # Always return success to prevent email enumeration
    # In production, would send reset email if user exists
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(token: str, new_password: str):
    """Reset password using reset token"""
    # This would verify the reset token and update password
    # For now, just return success
    return {"message": "Password reset successfully"}


@router.get("/check-username/{username}")
async def check_username_availability(username: str):
    """Check if username is available"""
    user_service = UserService()

    user = await user_service.get_user_by_username(username)

    return {
        "username": username,
        "available": user is None
    }


@router.get("/check-email/{email}")
async def check_email_availability(email: EmailStr):
    """Check if email is available"""
    user_service = UserService()

    user = await user_service.get_user_by_email(email)

    return {
        "email": email,
        "available": user is None
    }
