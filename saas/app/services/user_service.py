"""
User Management Service
======================

Service layer for user operations, authentication, and profile management.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.database import get_db_session
from ..core.security import security_manager
from ..models.subscription_models import Subscription
from ..models.user_models import AuditLog, Notification, User
from ..schemas.user_schemas import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """User management service"""

    def __init__(self):
        self.security = security_manager

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user account"""
        async with get_db_session() as session:
            # Check if user already exists
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                raise ValueError("User with this email already exists")

            existing_username = await self.get_user_by_username(user_data.username)
            if existing_username:
                raise ValueError("Username already taken")

            # Hash password
            password_hash = self.security.hash_password(user_data.password)

            # Create user
            user = User(
                email=user_data.email.lower(),
                username=user_data.username,
                full_name=user_data.full_name,
                password_hash=password_hash,
                company=user_data.company,
                phone=user_data.phone,
                timezone=user_data.timezone or "UTC",
                preferences=user_data.preferences or {}
            )

            session.add(user)
            await session.flush()  # Get the user ID

            # Create free tier subscription by default
            from .subscription_service import SubscriptionService
            subscription_service = SubscriptionService()
            await subscription_service.create_free_subscription(user.id)

            # Log user creation
            await self._log_user_action(
                user_id=user.id,
                action="user_created",
                session=session
            )

            # Send welcome notification
            await self.create_notification(
                user_id=user.id,
                title="Welcome to Crypto Trading Bot!",
                message="Your account has been created successfully. Start exploring our trading strategies!",
                type="success",
                session=session
            )

            await session.commit()
            return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        async with get_db_session() as session:
            stmt = select(User).options(
                selectinload(User.subscription),
                selectinload(User.subscription.tier)
            ).where(User.id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        async with get_db_session() as session:
            stmt = select(User).options(
                selectinload(User.subscription),
                selectinload(User.subscription.tier)
            ).where(User.email == email.lower())
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        async with get_db_session() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.get_user_by_email(email)

        if not user:
            return None

        if not user.is_active:
            return None

        if not self.security.verify_password(password, user.password_hash):
            return None

        # Update last login
        await self.update_last_login(user.id)

        return user

    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user profile"""
        async with get_db_session() as session:
            user = await session.get(User, user_id)
            if not user:
                return None

            # Track changes
            old_values = {}
            new_values = {}

            # Update fields
            for field, value in user_data.dict(exclude_unset=True).items():
                if hasattr(user, field) and value is not None:
                    old_values[field] = getattr(user, field)
                    setattr(user, field, value)
                    new_values[field] = value

            user.updated_at = datetime.utcnow()

            # Log the update
            await self._log_user_action(
                user_id=user_id,
                action="user_updated",
                old_values=old_values,
                new_values=new_values,
                session=session
            )

            await session.commit()
            return user

    async def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        async with get_db_session() as session:
            stmt = update(User).where(User.id == user_id).values(
                last_login=datetime.utcnow()
            )
            await session.execute(stmt)
            await session.commit()

    async def deactivate_user(self, user_id: int, reason: str = None) -> bool:
        """Deactivate user account"""
        async with get_db_session() as session:
            user = await session.get(User, user_id)
            if not user:
                return False

            user.is_active = False
            user.updated_at = datetime.utcnow()

            # Log deactivation
            await self._log_user_action(
                user_id=user_id,
                action="user_deactivated",
                metadata={"reason": reason},
                session=session
            )

            # Cancel subscription
            from .subscription_service import SubscriptionService
            subscription_service = SubscriptionService()
            await subscription_service.cancel_subscription(user_id, reason="account_deactivated")

            await session.commit()
            return True

    async def verify_user(self, user_id: int) -> bool:
        """Verify user account"""
        async with get_db_session() as session:
            user = await session.get(User, user_id)
            if not user:
                return False

            user.is_verified = True
            user.updated_at = datetime.utcnow()

            # Log verification
            await self._log_user_action(
                user_id=user_id,
                action="user_verified",
                session=session
            )

            # Send verification notification
            await self.create_notification(
                user_id=user_id,
                title="Account Verified",
                message="Your account has been successfully verified!",
                type="success",
                session=session
            )

            await session.commit()
            return True

    async def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        type: str = "info",
        priority: str = "normal",
        data: Dict[str, Any] = None,
        action_url: str = None,
        session: AsyncSession = None
    ) -> Notification:
        """Create a notification for user"""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            priority=priority,
            data=data or {},
            action_url=action_url
        )

        if session:
            session.add(notification)
            await session.flush()
        else:
            async with get_db_session() as db_session:
                db_session.add(notification)
                await db_session.commit()

        return notification

    async def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get user notifications"""
        async with get_db_session() as session:
            stmt = select(Notification).where(Notification.user_id == user_id)

            if unread_only:
                stmt = stmt.where(Notification.is_read == False)

            stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        async with get_db_session() as session:
            stmt = update(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            ).values(
                is_read=True,
                read_at=datetime.utcnow()
            )

            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str = None,
        subscription_tier: str = None,
        is_active: bool = None
    ) -> List[User]:
        """Get list of users with filtering"""
        async with get_db_session() as session:
            stmt = select(User).options(
                selectinload(User.subscription),
                selectinload(User.subscription.tier)
            )

            # Apply filters
            if search:
                search_term = f"%{search}%"
                stmt = stmt.where(
                    or_(
                        User.email.ilike(search_term),
                        User.username.ilike(search_term),
                        User.full_name.ilike(search_term)
                    )
                )

            if is_active is not None:
                stmt = stmt.where(User.is_active == is_active)

            if subscription_tier:
                stmt = stmt.join(Subscription).join(Subscription.tier).where(
                    Subscription.tier.name == subscription_tier
                )

            stmt = stmt.offset(skip).limit(limit).order_by(User.created_at.desc())

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        async with get_db_session() as session:
            user = await session.get(User, user_id)
            if not user:
                return {}

            # Get related statistics
            from sqlalchemy import func

            from ..models.api_models import APIKey, Trade
            from ..models.payment_models import Payment
            from ..models.strategy_models import Strategy, StrategyPurchase

            # Strategy stats
            strategies_created = await session.scalar(
                select(func.count(Strategy.id)).where(Strategy.owner_id == user_id)
            )

            strategies_purchased = await session.scalar(
                select(func.count(StrategyPurchase.id)).where(StrategyPurchase.buyer_id == user_id)
            )

            # API stats
            api_keys_count = await session.scalar(
                select(func.count(APIKey.id)).where(APIKey.user_id == user_id)
            )

            # Trading stats
            total_trades = await session.scalar(
                select(func.count(Trade.id)).join(Trade.bot).where(Trade.bot.user_id == user_id)
            )

            # Payment stats
            total_spent = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(Payment.user_id == user_id, Payment.status == "completed")
                )
            ) or 0

            return {
                "strategies_created": strategies_created or 0,
                "strategies_purchased": strategies_purchased or 0,
                "api_keys": api_keys_count or 0,
                "total_trades": total_trades or 0,
                "total_spent": float(total_spent),
                "member_since": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }

    async def _log_user_action(
        self,
        user_id: int,
        action: str,
        old_values: Dict[str, Any] = None,
        new_values: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
        session: AsyncSession = None
    ):
        """Log user action to audit log"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type="user",
            resource_id=str(user_id),
            old_values=old_values or {},
            new_values=new_values or {},
            status="success"
        )

        if metadata:
            audit_log.new_values.update(metadata)

        if session:
            session.add(audit_log)
        else:
            async with get_db_session() as db_session:
                db_session.add(audit_log)
                await db_session.commit()
