"""
API Routes
==========

Main API router that includes all endpoint modules.
"""

from fastapi import APIRouter

from .admin import router as admin_router
from .analytics import router as analytics_router
from .api_management import router as api_router
from .auth import router as auth_router
from .payments import router as payments_router
from .strategies import router as strategies_router
from .subscriptions import router as subscriptions_router
from .users import router as users_router

# Main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    subscriptions_router,
    prefix="/subscriptions",
    tags=["subscriptions"]
)

api_router.include_router(
    strategies_router,
    prefix="/strategies",
    tags=["strategies"]
)

api_router.include_router(
    payments_router,
    prefix="/payments",
    tags=["payments"]
)

api_router.include_router(
    api_router,
    prefix="/api-management",
    tags=["api-management"]
)

api_router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["analytics"]
)

api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["admin"]
)
