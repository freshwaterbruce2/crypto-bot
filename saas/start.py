#!/usr/bin/env python3
"""
SaaS Platform Startup Script
============================

Development and production startup script with database initialization.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.core.database import create_tables
from app.services.subscription_service import SubscriptionService


async def initialize_platform():
    """Initialize the SaaS platform"""
    print("🚀 Initializing Crypto Trading Bot SaaS Platform...")

    settings = get_settings()

    try:
        # Create database tables
        print("📊 Creating database tables...")
        await create_tables()
        print("✅ Database tables created successfully")

        # Initialize default subscription tiers
        print("💳 Setting up subscription tiers...")
        subscription_service = SubscriptionService()
        await subscription_service.initialize_default_tiers()
        print("✅ Subscription tiers initialized")

        print("🎉 Platform initialization complete!")
        print(f"🌐 Environment: {settings.ENVIRONMENT}")
        print(f"🔗 Database: {settings.DATABASE_URL}")
        print(f"🏃 Ready to start server on {settings.HOST}:{settings.PORT}")

        return True

    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


async def main():
    """Main startup function"""
    print("=" * 60)
    print("CRYPTO TRADING BOT SAAS PLATFORM")
    print("=" * 60)

    # Initialize platform
    success = await initialize_platform()

    if not success:
        print("❌ Platform initialization failed. Please check the logs.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🚀 STARTING SAAS PLATFORM SERVER")
    print("=" * 60)

    # Import and run the main application
    import uvicorn

    settings = get_settings()

    # Run the server
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        sys.exit(1)
