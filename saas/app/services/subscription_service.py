"""
Subscription Management Service
==============================

Service layer for subscription tiers, billing, and feature access management.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.database import get_db_session
from ..models.subscription_models import (
    Subscription,
    SubscriptionEvent,
    SubscriptionTier,
    UsageRecord,
    WhiteLabelConfig,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class SubscriptionService:
    """Subscription management service"""

    def __init__(self):
        self.settings = get_settings()

    async def initialize_default_tiers(self):
        """Initialize default subscription tiers"""
        async with get_db_session() as session:
            # Check if tiers already exist
            existing_tiers = await session.execute(select(SubscriptionTier))
            if existing_tiers.scalars().first():
                return  # Tiers already exist

            # Create default tiers
            free_tier = SubscriptionTier(
                name="free",
                display_name="Free",
                description="Perfect for getting started with paper trading",
                price_monthly=Decimal("0.00"),
                price_yearly=Decimal("0.00"),
                max_strategies=1,
                max_api_calls=1000,
                max_trading_pairs=0,  # Paper trading only
                features=settings.FREE_TIER_LIMITS["features"],
                sort_order=0
            )

            pro_tier = SubscriptionTier(
                name="pro",
                display_name="Pro",
                description="Advanced features for serious traders",
                price_monthly=Decimal(str(settings.PRO_TIER_PRICE / 100)),
                price_yearly=Decimal(str(settings.PRO_TIER_PRICE * 10 / 100)),  # 2 months free
                max_strategies=10,
                max_api_calls=50000,
                max_trading_pairs=5,
                features=settings.PRO_TIER_LIMITS["features"],
                is_popular=True,
                sort_order=1
            )

            enterprise_tier = SubscriptionTier(
                name="enterprise",
                display_name="Enterprise",
                description="Unlimited access for institutions and power users",
                price_monthly=Decimal(str(settings.ENTERPRISE_TIER_PRICE / 100)),
                price_yearly=Decimal(str(settings.ENTERPRISE_TIER_PRICE * 10 / 100)),
                max_strategies=-1,  # Unlimited
                max_api_calls=-1,   # Unlimited
                max_trading_pairs=-1,  # Unlimited
                features=settings.ENTERPRISE_TIER_LIMITS["features"],
                sort_order=2
            )

            session.add_all([free_tier, pro_tier, enterprise_tier])
            await session.commit()

            logger.info("Default subscription tiers created successfully")

    async def get_subscription_tiers(self, active_only: bool = True) -> List[SubscriptionTier]:
        """Get all subscription tiers"""
        async with get_db_session() as session:
            stmt = select(SubscriptionTier)

            if active_only:
                stmt = stmt.where(SubscriptionTier.is_active == True)

            stmt = stmt.order_by(SubscriptionTier.sort_order)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_subscription_tier(self, tier_name: str) -> Optional[SubscriptionTier]:
        """Get subscription tier by name"""
        async with get_db_session() as session:
            stmt = select(SubscriptionTier).where(SubscriptionTier.name == tier_name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_free_subscription(self, user_id: int) -> Subscription:
        """Create a free subscription for new users"""
        async with get_db_session() as session:
            # Get free tier
            free_tier = await self.get_subscription_tier("free")
            if not free_tier:
                raise ValueError("Free tier not found")

            # Create subscription
            subscription = Subscription(
                user_id=user_id,
                tier_id=free_tier.id,
                billing_cycle="monthly",
                status="active",
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=365 * 10)  # Free forever
            )

            session.add(subscription)
            await session.flush()

            # Log subscription event
            await self._log_subscription_event(
                subscription_id=subscription.id,
                event_type="created",
                to_tier="free",
                amount=Decimal("0.00"),
                session=session
            )

            await session.commit()
            return subscription

    async def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get user's current subscription"""
        async with get_db_session() as session:
            stmt = select(Subscription).options(
                selectinload(Subscription.tier),
                selectinload(Subscription.user)
            ).where(Subscription.user_id == user_id)

            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def upgrade_subscription(
        self,
        user_id: int,
        new_tier_name: str,
        billing_cycle: str = "monthly",
        stripe_subscription_id: str = None
    ) -> Subscription:
        """Upgrade user subscription"""
        async with get_db_session() as session:
            # Get current subscription
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                raise ValueError("User has no subscription")

            # Get new tier
            new_tier = await self.get_subscription_tier(new_tier_name)
            if not new_tier:
                raise ValueError(f"Tier '{new_tier_name}' not found")

            # Store old tier for logging
            old_tier_name = subscription.tier.name if subscription.tier else "unknown"

            # Calculate new period
            now = datetime.utcnow()
            if billing_cycle == "yearly":
                period_end = now + timedelta(days=365)
                amount = new_tier.price_yearly
            else:
                period_end = now + timedelta(days=30)
                amount = new_tier.price_monthly

            # Update subscription
            subscription.tier_id = new_tier.id
            subscription.billing_cycle = billing_cycle
            subscription.status = "active"
            subscription.current_period_start = now
            subscription.current_period_end = period_end
            subscription.stripe_subscription_id = stripe_subscription_id
            subscription.updated_at = now

            # Reset usage counters for new tier
            subscription.api_calls_used = 0
            subscription.strategies_used = 0
            subscription.trading_pairs_used = 0

            # Log subscription event
            await self._log_subscription_event(
                subscription_id=subscription.id,
                event_type="upgraded",
                from_tier=old_tier_name,
                to_tier=new_tier_name,
                amount=amount,
                session=session
            )

            await session.commit()
            return subscription

    async def downgrade_subscription(
        self,
        user_id: int,
        new_tier_name: str,
        reason: str = None
    ) -> Subscription:
        """Downgrade user subscription"""
        async with get_db_session() as session:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                raise ValueError("User has no subscription")

            new_tier = await self.get_subscription_tier(new_tier_name)
            if not new_tier:
                raise ValueError(f"Tier '{new_tier_name}' not found")

            old_tier_name = subscription.tier.name if subscription.tier else "unknown"

            # Update subscription
            subscription.tier_id = new_tier.id
            # Keep current period end to avoid immediate billing changes
            subscription.updated_at = datetime.utcnow()

            # Log subscription event
            await self._log_subscription_event(
                subscription_id=subscription.id,
                event_type="downgraded",
                from_tier=old_tier_name,
                to_tier=new_tier_name,
                metadata={"reason": reason},
                session=session
            )

            await session.commit()
            return subscription

    async def cancel_subscription(
        self,
        user_id: int,
        reason: str = None,
        immediate: bool = False
    ) -> bool:
        """Cancel user subscription"""
        async with get_db_session() as session:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return False

            if immediate:
                # Immediate cancellation - downgrade to free
                free_tier = await self.get_subscription_tier("free")
                if free_tier:
                    subscription.tier_id = free_tier.id
                    subscription.current_period_end = datetime.utcnow() + timedelta(days=365 * 10)

            subscription.status = "cancelled"
            subscription.cancelled_at = datetime.utcnow()
            subscription.updated_at = datetime.utcnow()

            # Log cancellation
            await self._log_subscription_event(
                subscription_id=subscription.id,
                event_type="cancelled",
                metadata={"reason": reason, "immediate": immediate},
                session=session
            )

            await session.commit()
            return True

    async def check_subscription_limits(
        self,
        user_id: int,
        resource_type: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """Check if user can use a resource within subscription limits"""
        subscription = await self.get_user_subscription(user_id)

        if not subscription or not subscription.is_active:
            return {
                "allowed": False,
                "reason": "No active subscription",
                "limit": 0,
                "used": 0,
                "remaining": 0
            }

        limit_info = subscription.check_limit(resource_type)

        if limit_info["exceeded"] or (
            limit_info["limit"] != -1 and
            limit_info["remaining"] < quantity
        ):
            return {
                "allowed": False,
                "reason": f"{resource_type.replace('_', ' ').title()} limit exceeded",
                **limit_info
            }

        return {
            "allowed": True,
            "reason": "Within limits",
            **limit_info
        }

    async def record_usage(
        self,
        user_id: int,
        resource_type: str,
        quantity: int = 1,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Record resource usage for a user"""
        async with get_db_session() as session:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return False

            # Check limits first
            limits_check = await self.check_subscription_limits(user_id, resource_type, quantity)
            if not limits_check["allowed"]:
                return False

            # Record usage
            usage_record = UsageRecord(
                subscription_id=subscription.id,
                resource_type=resource_type,
                quantity=quantity,
                metadata=metadata or {}
            )
            session.add(usage_record)

            # Update subscription counters
            if resource_type == "api_calls":
                subscription.api_calls_used += quantity
            elif resource_type == "strategies":
                subscription.strategies_used += quantity
            elif resource_type == "trading_pairs":
                subscription.trading_pairs_used += quantity

            subscription.updated_at = datetime.utcnow()

            await session.commit()
            return True

    async def get_subscription_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get subscription analytics for a user"""
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return {}

        async with get_db_session() as session:
            # Get usage history for the current period
            usage_stmt = select(UsageRecord).where(
                and_(
                    UsageRecord.subscription_id == subscription.id,
                    UsageRecord.timestamp >= subscription.current_period_start,
                    UsageRecord.timestamp <= subscription.current_period_end
                )
            ).order_by(UsageRecord.timestamp.desc())

            usage_result = await session.execute(usage_stmt)
            usage_records = usage_result.scalars().all()

            # Aggregate usage by resource type
            usage_by_type = {}
            for record in usage_records:
                if record.resource_type not in usage_by_type:
                    usage_by_type[record.resource_type] = 0
                usage_by_type[record.resource_type] += record.quantity

            return {
                "subscription": subscription.to_dict(),
                "current_period": {
                    "start": subscription.current_period_start.isoformat(),
                    "end": subscription.current_period_end.isoformat(),
                    "days_remaining": subscription.days_until_renewal
                },
                "usage": {
                    "api_calls": subscription.check_limit("api_calls"),
                    "strategies": subscription.check_limit("strategies"),
                    "trading_pairs": subscription.check_limit("trading_pairs"),
                    "by_type": usage_by_type
                },
                "features": subscription.tier.features if subscription.tier else [],
                "total_usage_records": len(usage_records)
            }

    async def create_white_label_config(
        self,
        user_id: int,
        config_data: Dict[str, Any]
    ) -> WhiteLabelConfig:
        """Create white-label configuration for enterprise client"""
        async with get_db_session() as session:
            # Verify user has enterprise subscription
            subscription = await self.get_user_subscription(user_id)
            if not subscription or subscription.tier.name != "enterprise":
                raise ValueError("Enterprise subscription required for white-label")

            config = WhiteLabelConfig(
                user_id=user_id,
                company_name=config_data["company_name"],
                logo_url=config_data.get("logo_url"),
                primary_color=config_data.get("primary_color"),
                secondary_color=config_data.get("secondary_color"),
                custom_domain=config_data.get("custom_domain"),
                enabled_features=config_data.get("enabled_features", []),
                custom_integrations=config_data.get("custom_integrations", {}),
                monthly_fee=Decimal(str(config_data.get("monthly_fee", settings.WHITE_LABEL_BASE_PRICE / 100))),
                setup_fee=Decimal(str(config_data.get("setup_fee", 0)))
            )

            session.add(config)
            await session.commit()
            return config

    async def get_subscription_stats(self) -> Dict[str, Any]:
        """Get overall subscription statistics"""
        async with get_db_session() as session:
            # Total subscriptions by tier
            tier_stats = await session.execute(
                select(
                    SubscriptionTier.name,
                    SubscriptionTier.display_name,
                    func.count(Subscription.id).label("count")
                )
                .select_from(SubscriptionTier)
                .outerjoin(Subscription, and_(
                    Subscription.tier_id == SubscriptionTier.id,
                    Subscription.status == "active"
                ))
                .group_by(SubscriptionTier.id, SubscriptionTier.name, SubscriptionTier.display_name)
                .order_by(SubscriptionTier.sort_order)
            )

            tier_distribution = []
            total_active = 0

            for row in tier_stats:
                count = row.count or 0
                total_active += count
                tier_distribution.append({
                    "tier": row.name,
                    "display_name": row.display_name,
                    "count": count
                })

            # Revenue calculations
            monthly_revenue = await session.scalar(
                select(func.sum(SubscriptionTier.price_monthly))
                .select_from(Subscription)
                .join(SubscriptionTier)
                .where(
                    and_(
                        Subscription.status == "active",
                        Subscription.billing_cycle == "monthly"
                    )
                )
            ) or Decimal("0")

            yearly_revenue = await session.scalar(
                select(func.sum(SubscriptionTier.price_yearly))
                .select_from(Subscription)
                .join(SubscriptionTier)
                .where(
                    and_(
                        Subscription.status == "active",
                        Subscription.billing_cycle == "yearly"
                    )
                )
            ) or Decimal("0")

            return {
                "total_active_subscriptions": total_active,
                "tier_distribution": tier_distribution,
                "estimated_monthly_revenue": float(monthly_revenue + (yearly_revenue / 12)),
                "estimated_yearly_revenue": float((monthly_revenue * 12) + yearly_revenue)
            }

    async def _log_subscription_event(
        self,
        subscription_id: int,
        event_type: str,
        from_tier: str = None,
        to_tier: str = None,
        amount: Decimal = None,
        metadata: Dict[str, Any] = None,
        session: AsyncSession = None
    ):
        """Log subscription lifecycle event"""
        event = SubscriptionEvent(
            subscription_id=subscription_id,
            event_type=event_type,
            from_tier=from_tier,
            to_tier=to_tier,
            amount=amount,
            metadata=metadata or {}
        )

        if session:
            session.add(event)
        else:
            async with get_db_session() as db_session:
                db_session.add(event)
                await db_session.commit()

    async def cleanup_expired_subscriptions(self):
        """Cleanup expired subscriptions (run as scheduled task)"""
        async with get_db_session() as session:
            now = datetime.utcnow()

            # Find expired subscriptions
            expired_stmt = select(Subscription).where(
                and_(
                    Subscription.status == "active",
                    Subscription.current_period_end < now
                )
            )

            expired_result = await session.execute(expired_stmt)
            expired_subscriptions = expired_result.scalars().all()

            free_tier = await self.get_subscription_tier("free")

            for subscription in expired_subscriptions:
                # Downgrade to free tier
                if free_tier:
                    subscription.tier_id = free_tier.id
                    subscription.current_period_end = now + timedelta(days=365 * 10)

                subscription.status = "expired"
                subscription.updated_at = now

                # Log expiration
                await self._log_subscription_event(
                    subscription_id=subscription.id,
                    event_type="expired",
                    to_tier="free",
                    session=session
                )

            await session.commit()

            logger.info(f"Processed {len(expired_subscriptions)} expired subscriptions")
