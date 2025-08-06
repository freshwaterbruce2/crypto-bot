"""
Security Configuration
======================

Authentication, authorization, and security middleware for the SaaS platform.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from passlib.context import CryptContext

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
security = HTTPBearer()


class SecurityManager:
    """Centralized security management"""

    def __init__(self):
        self.settings = get_settings()

    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.settings.SECRET_KEY, algorithms=[ALGORITHM])

            if payload.get("type") != token_type:
                raise HTTPException(status_code=401, detail="Invalid token type")

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")


# Global security manager instance
security_manager = SecurityManager()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials

    try:
        payload = security_manager.verify_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get user from database
        from ..services.user_service import UserService
        user_service = UserService()
        user = await user_service.get_user_by_id(user_id)

        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        if not user.is_active:
            raise HTTPException(status_code=401, detail="User account is disabled")

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_active_user(current_user=Depends(get_current_user)):
    """Get current active user (alias for backward compatibility)"""
    return current_user


def require_subscription(tier: str):
    """Decorator to require specific subscription tier"""
    async def subscription_checker(current_user=Depends(get_current_user)):
        from ..services.subscription_service import SubscriptionService

        subscription_service = SubscriptionService()
        user_subscription = await subscription_service.get_user_subscription(current_user.id)

        if not user_subscription:
            raise HTTPException(
                status_code=403,
                detail="Subscription required"
            )

        if not user_subscription.is_active:
            raise HTTPException(
                status_code=403,
                detail="Active subscription required"
            )

        # Check tier hierarchy: enterprise > pro > free
        tier_hierarchy = {"free": 0, "pro": 1, "enterprise": 2}
        required_level = tier_hierarchy.get(tier.lower(), 0)
        user_level = tier_hierarchy.get(user_subscription.tier.lower(), 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"{tier.title()} subscription required"
            )

        return current_user

    return subscription_checker


def require_admin():
    """Decorator to require admin access"""
    async def admin_checker(current_user=Depends(get_current_user)):
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        return current_user

    return admin_checker


async def setup_security(app: FastAPI):
    """Setup security middleware and rate limiting"""

    # Setup rate limiting if Redis is available
    if settings.REDIS_URL and settings.RATE_LIMIT_ENABLED:
        try:
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            await FastAPILimiter.init(redis_client)
            logger.info("Rate limiting enabled with Redis")
        except Exception as e:
            logger.warning(f"Failed to setup Redis rate limiting: {e}")

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


class APIKeyManager:
    """Manage API keys for third-party integrations"""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key"""
        import secrets
        return f"ctb_{secrets.token_urlsafe(32)}"

    @staticmethod
    async def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return associated user/permissions"""
        try:
            # Get API key from database
            from ..services.api_service import APIService
            api_service = APIService()
            api_key_obj = await api_service.get_api_key(api_key)

            if not api_key_obj or not api_key_obj.is_active:
                return None

            # Check rate limits
            if api_key_obj.is_rate_limited():
                raise HTTPException(
                    status_code=429,
                    detail="API rate limit exceeded"
                )

            # Update usage statistics
            await api_service.record_api_usage(api_key_obj.id)

            return {
                "user_id": api_key_obj.user_id,
                "permissions": api_key_obj.permissions,
                "rate_limit": api_key_obj.rate_limit
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return None


async def verify_api_key(request: Request) -> Dict[str, Any]:
    """Verify API key from request headers"""
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required"
        )

    key_data = await APIKeyManager.validate_api_key(api_key)

    if not key_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return key_data


def get_rate_limiter(requests_per_minute: int = 60):
    """Get rate limiter with specified limits"""
    if settings.RATE_LIMIT_ENABLED:
        return RateLimiter(times=requests_per_minute, seconds=60)
    else:
        # No-op rate limiter for development
        async def no_limit():
            pass
        return no_limit
