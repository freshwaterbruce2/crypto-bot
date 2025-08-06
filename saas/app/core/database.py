"""
Database Configuration and Models
=================================

SQLAlchemy database setup with async support for the SaaS platform.
"""

import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base

from .config import get_settings

logger = logging.getLogger(__name__)

# Database base class
Base = declarative_base()

# Settings
settings = get_settings()

# Create async engine
if settings.DATABASE_URL.startswith("sqlite"):
    # For SQLite, we need to enable foreign keys and use aiosqlite
    database_url = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        future=True,
        connect_args={"check_same_thread": False}
    )
else:
    # For PostgreSQL or other databases
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        pool_recycle=300
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def create_tables():
    """Create database tables"""
    try:
        logger.info("Creating database tables...")

        # Import all models to ensure they are registered

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def close_database():
    """Close database connections"""
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


@asynccontextmanager
async def get_db_session():
    """Get database session context manager"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db():
    """Dependency to get database session"""
    async with get_db_session() as session:
        yield session


class DatabaseManager:
    """Database management utilities"""

    @staticmethod
    async def health_check() -> bool:
        """Check database connectivity"""
        try:
            async with get_db_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @staticmethod
    async def get_stats() -> dict:
        """Get database statistics"""
        try:
            async with get_db_session() as session:
                # Import models
                # Get counts
                from sqlalchemy import func, select

                from ..models.payment_models import Payment
                from ..models.strategy_models import Strategy
                from ..models.subscription_models import Subscription
                from ..models.user_models import User

                user_count = await session.scalar(select(func.count(User.id)))
                subscription_count = await session.scalar(select(func.count(Subscription.id)))
                strategy_count = await session.scalar(select(func.count(Strategy.id)))
                payment_count = await session.scalar(select(func.count(Payment.id)))

                return {
                    "users": user_count or 0,
                    "subscriptions": subscription_count or 0,
                    "strategies": strategy_count or 0,
                    "payments": payment_count or 0
                }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {
                "users": 0,
                "subscriptions": 0,
                "strategies": 0,
                "payments": 0
            }
