#!/usr/bin/env python3
"""
CRYPTO TRADING BOT SAAS PLATFORM
================================

FastAPI-based SaaS platform for cryptocurrency trading bot services.
Provides subscription-based access to trading strategies, API services,
and white-label solutions.

Features:
- Multi-tenant architecture with subscription tiers
- Strategy marketplace with revenue sharing
- API monetization with usage tracking
- Payment processing (Stripe + Crypto)
- White-label solutions for institutions
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows event loop
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

import logging
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from app.api.routes import api_router
from app.core.config import get_settings
from app.core.database import close_database, create_tables
from app.core.security import setup_security
from app.services.analytics_service import AnalyticsService
from app.services.payment_service import PaymentService
from app.services.strategy_marketplace import StrategyMarketplace
from app.services.subscription_service import SubscriptionService
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger.info("Starting Crypto Trading Bot SaaS Platform...")

    # Initialize database
    await create_tables()

    # Initialize services
    app.state.subscription_service = SubscriptionService()
    app.state.payment_service = PaymentService()
    app.state.strategy_marketplace = StrategyMarketplace()
    app.state.analytics_service = AnalyticsService()

    logger.info("SaaS platform initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down SaaS platform...")
    await close_database()


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="Crypto Trading Bot SaaS",
        description="Enterprise-grade cryptocurrency trading bot platform",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )

    # Security middleware
    setup_security(app)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware
    if settings.ALLOWED_HOSTS:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )

    # API routes
    app.include_router(api_router, prefix="/api/v1")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "service": "crypto-trading-bot-saas"
        }

    # Global error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler"""
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred"
            }
        )

    # Rate limiting error handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP exception handler with enhanced error responses"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    """Run the SaaS platform"""
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("CRYPTO TRADING BOT SAAS PLATFORM")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    logger.info(f"Host: {settings.HOST}")
    logger.info(f"Port: {settings.PORT}")
    logger.info("=" * 60)

    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG
    )
