"""
API Management Service
=====================

Service layer for API key management, rate limiting, usage tracking,
and API monetization.
"""

import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.database import get_db_session
from ..models.api_models import (
    APIKey,
    APIUsageLog,
    TradingBot,
    WebhookDelivery,
    WebhookEndpoint,
)
from ..models.user_models import User
from ..schemas.api_schemas import (
    APIKeyCreate,
    APIKeyUpdate,
    TradingBotCreate,
    TradingBotUpdate,
    WebhookEndpointCreate,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class APIService:
    """API management service"""

    def __init__(self):
        self.settings = get_settings()

    async def create_api_key(
        self,
        user_id: int,
        api_key_data: APIKeyCreate
    ) -> Tuple[APIKey, str]:
        """Create a new API key for user"""
        async with get_db_session() as session:
            # Check user's subscription limits
            from .subscription_service import SubscriptionService
            subscription_service = SubscriptionService()
            subscription = await subscription_service.get_user_subscription(user_id)

            if not subscription or not subscription.is_active:
                raise ValueError("Active subscription required for API access")

            # Generate API key
            raw_key = self._generate_api_key()
            key_hash = self._hash_api_key(raw_key)

            # Determine rate limits based on subscription tier
            rate_limits = self._get_rate_limits_for_tier(subscription.tier.name)

            api_key = APIKey(
                user_id=user_id,
                key_hash=key_hash,
                name=api_key_data.name,
                description=api_key_data.description,
                scopes=api_key_data.scopes or ["read"],
                permissions=api_key_data.permissions or {},
                rate_limit_per_minute=rate_limits["per_minute"],
                rate_limit_per_hour=rate_limits["per_hour"],
                rate_limit_per_day=rate_limits["per_day"],
                allowed_ips=api_key_data.allowed_ips or [],
                expires_at=api_key_data.expires_at
            )

            session.add(api_key)
            await session.commit()

            return api_key, raw_key

    async def get_api_key(self, api_key: str) -> Optional[APIKey]:
        """Get API key by key value"""
        key_hash = self._hash_api_key(api_key)

        async with get_db_session() as session:
            stmt = select(APIKey).options(
                selectinload(APIKey.user).selectinload(User.subscription)
            ).where(
                and_(
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == True
                )
            )

            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_user_api_keys(self, user_id: int) -> List[APIKey]:
        """Get all API keys for a user"""
        async with get_db_session() as session:
            stmt = select(APIKey).where(APIKey.user_id == user_id).order_by(desc(APIKey.created_at))
            result = await session.execute(stmt)
            return result.scalars().all()

    async def update_api_key(
        self,
        api_key_id: int,
        user_id: int,
        update_data: APIKeyUpdate
    ) -> Optional[APIKey]:
        """Update API key settings"""
        async with get_db_session() as session:
            api_key = await session.get(APIKey, api_key_id)

            if not api_key or api_key.user_id != user_id:
                return None

            # Update allowed fields
            for field, value in update_data.dict(exclude_unset=True).items():
                if hasattr(api_key, field) and value is not None:
                    setattr(api_key, field, value)

            api_key.updated_at = datetime.utcnow()
            await session.commit()
            return api_key

    async def deactivate_api_key(self, api_key_id: int, user_id: int) -> bool:
        """Deactivate an API key"""
        async with get_db_session() as session:
            api_key = await session.get(APIKey, api_key_id)

            if not api_key or api_key.user_id != user_id:
                return False

            api_key.is_active = False
            api_key.updated_at = datetime.utcnow()
            await session.commit()
            return True

    async def record_api_usage(
        self,
        api_key_id: int,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        ip_address: str = None,
        user_agent: str = None,
        request_size: int = 0,
        response_size: int = 0,
        billable_units: int = 1
    ) -> APIUsageLog:
        """Record API usage for billing and analytics"""
        async with get_db_session() as session:
            # Update API key usage counters
            api_key = await session.get(APIKey, api_key_id)
            if api_key:
                api_key.total_requests += 1
                api_key.last_used = datetime.utcnow()

                # Update daily counter (reset if new day)
                today = datetime.utcnow().date()
                if api_key.last_used and api_key.last_used.date() != today:
                    api_key.requests_today = 0

                api_key.requests_today += 1

            # Create usage log
            usage_log = APIUsageLog(
                api_key_id=api_key_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                ip_address=ip_address,
                user_agent=user_agent,
                request_size=request_size,
                response_size=response_size,
                billable_units=billable_units
            )

            session.add(usage_log)
            await session.commit()
            return usage_log

    async def check_rate_limits(self, api_key_id: int) -> Dict[str, Any]:
        """Check current rate limit status for API key"""
        async with get_db_session() as session:
            api_key = await session.get(APIKey, api_key_id)
            if not api_key:
                return {"allowed": False, "reason": "API key not found"}

            if not api_key.is_active:
                return {"allowed": False, "reason": "API key inactive"}

            if api_key.is_expired:
                return {"allowed": False, "reason": "API key expired"}

            now = datetime.utcnow()

            # Check daily limit
            if api_key.requests_today >= api_key.rate_limit_per_day:
                return {
                    "allowed": False,
                    "reason": "Daily rate limit exceeded",
                    "reset_time": (now + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
                }

            # Check hourly limit
            hour_ago = now - timedelta(hours=1)
            hourly_requests = await session.scalar(
                select(func.count(APIUsageLog.id)).where(
                    and_(
                        APIUsageLog.api_key_id == api_key_id,
                        APIUsageLog.created_at >= hour_ago
                    )
                )
            ) or 0

            if hourly_requests >= api_key.rate_limit_per_hour:
                return {
                    "allowed": False,
                    "reason": "Hourly rate limit exceeded",
                    "reset_time": (hour_ago + timedelta(hours=1)).isoformat()
                }

            # Check minute limit
            minute_ago = now - timedelta(minutes=1)
            minute_requests = await session.scalar(
                select(func.count(APIUsageLog.id)).where(
                    and_(
                        APIUsageLog.api_key_id == api_key_id,
                        APIUsageLog.created_at >= minute_ago
                    )
                )
            ) or 0

            if minute_requests >= api_key.rate_limit_per_minute:
                return {
                    "allowed": False,
                    "reason": "Rate limit exceeded",
                    "reset_time": (minute_ago + timedelta(minutes=1)).isoformat()
                }

            return {
                "allowed": True,
                "limits": {
                    "per_minute": {
                        "limit": api_key.rate_limit_per_minute,
                        "used": minute_requests,
                        "remaining": api_key.rate_limit_per_minute - minute_requests
                    },
                    "per_hour": {
                        "limit": api_key.rate_limit_per_hour,
                        "used": hourly_requests,
                        "remaining": api_key.rate_limit_per_hour - hourly_requests
                    },
                    "per_day": {
                        "limit": api_key.rate_limit_per_day,
                        "used": api_key.requests_today,
                        "remaining": api_key.rate_limit_per_day - api_key.requests_today
                    }
                }
            }

    async def get_api_usage_analytics(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get API usage analytics for user"""
        async with get_db_session() as session:
            since_date = datetime.utcnow() - timedelta(days=days)

            # Get user's API keys
            api_keys = await session.execute(
                select(APIKey).where(APIKey.user_id == user_id)
            )
            api_key_ids = [key.id for key in api_keys.scalars().all()]

            if not api_key_ids:
                return {"total_requests": 0, "usage_by_endpoint": {}, "usage_by_day": {}}

            # Total requests
            total_requests = await session.scalar(
                select(func.count(APIUsageLog.id)).where(
                    and_(
                        APIUsageLog.api_key_id.in_(api_key_ids),
                        APIUsageLog.created_at >= since_date
                    )
                )
            ) or 0

            # Usage by endpoint
            endpoint_usage = await session.execute(
                select(
                    APIUsageLog.endpoint,
                    func.count(APIUsageLog.id).label("count"),
                    func.avg(APIUsageLog.response_time_ms).label("avg_response_time")
                ).where(
                    and_(
                        APIUsageLog.api_key_id.in_(api_key_ids),
                        APIUsageLog.created_at >= since_date
                    )
                ).group_by(APIUsageLog.endpoint)
                .order_by(desc("count"))
            )

            # Usage by day
            daily_usage = await session.execute(
                select(
                    func.date(APIUsageLog.created_at).label("date"),
                    func.count(APIUsageLog.id).label("count")
                ).where(
                    and_(
                        APIUsageLog.api_key_id.in_(api_key_ids),
                        APIUsageLog.created_at >= since_date
                    )
                ).group_by(func.date(APIUsageLog.created_at))
                .order_by("date")
            )

            return {
                "period_days": days,
                "total_requests": total_requests,
                "usage_by_endpoint": [
                    {
                        "endpoint": row.endpoint,
                        "requests": row.count,
                        "avg_response_time": float(row.avg_response_time or 0)
                    }
                    for row in endpoint_usage
                ],
                "usage_by_day": [
                    {
                        "date": row.date.isoformat(),
                        "requests": row.count
                    }
                    for row in daily_usage
                ]
            }

    async def create_trading_bot(
        self,
        user_id: int,
        bot_data: TradingBotCreate
    ) -> TradingBot:
        """Create a new trading bot instance"""
        async with get_db_session() as session:
            # Check subscription limits
            from .subscription_service import SubscriptionService
            subscription_service = SubscriptionService()

            limits_check = await subscription_service.check_subscription_limits(
                user_id, "trading_pairs", len(bot_data.trading_pairs or [])
            )

            if not limits_check["allowed"]:
                raise ValueError(f"Trading pair limit exceeded: {limits_check['reason']}")

            bot = TradingBot(
                user_id=user_id,
                name=bot_data.name,
                description=bot_data.description,
                strategy_id=bot_data.strategy_id,
                exchange=bot_data.exchange,
                trading_pairs=bot_data.trading_pairs or [],
                base_currency=bot_data.base_currency or "USDT",
                initial_balance=Decimal(str(bot_data.initial_balance)),
                max_position_size=Decimal(str(bot_data.max_position_size)) if bot_data.max_position_size else Decimal("10"),
                stop_loss=Decimal(str(bot_data.stop_loss)) if bot_data.stop_loss else None,
                take_profit=Decimal(str(bot_data.take_profit)) if bot_data.take_profit else None,
                is_paper_trading=bot_data.is_paper_trading,
                config=bot_data.config or {}
            )

            session.add(bot)

            # Record trading pair usage
            if bot_data.trading_pairs:
                await subscription_service.record_usage(
                    user_id, "trading_pairs", len(bot_data.trading_pairs),
                    {"bot_id": bot.id, "pairs": bot_data.trading_pairs}
                )

            await session.commit()
            return bot

    async def get_user_trading_bots(self, user_id: int) -> List[TradingBot]:
        """Get user's trading bots"""
        async with get_db_session() as session:
            stmt = select(TradingBot).where(TradingBot.user_id == user_id).order_by(desc(TradingBot.created_at))
            result = await session.execute(stmt)
            return result.scalars().all()

    async def update_trading_bot(
        self,
        bot_id: int,
        user_id: int,
        update_data: TradingBotUpdate
    ) -> Optional[TradingBot]:
        """Update trading bot configuration"""
        async with get_db_session() as session:
            bot = await session.get(TradingBot, bot_id)

            if not bot or bot.user_id != user_id:
                return None

            # Update fields
            for field, value in update_data.dict(exclude_unset=True).items():
                if hasattr(bot, field) and value is not None:
                    if field in ["initial_balance", "max_position_size", "stop_loss", "take_profit"]:
                        setattr(bot, field, Decimal(str(value)))
                    else:
                        setattr(bot, field, value)

            bot.updated_at = datetime.utcnow()
            await session.commit()
            return bot

    async def create_webhook_endpoint(
        self,
        user_id: int,
        webhook_data: WebhookEndpointCreate
    ) -> WebhookEndpoint:
        """Create webhook endpoint for API events"""
        async with get_db_session() as session:
            # Generate webhook secret
            secret = secrets.token_urlsafe(32)

            webhook = WebhookEndpoint(
                user_id=user_id,
                url=webhook_data.url,
                description=webhook_data.description,
                secret=secret,
                enabled_events=webhook_data.enabled_events or []
            )

            session.add(webhook)
            await session.commit()
            return webhook

    async def trigger_webhook(
        self,
        user_id: int,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """Trigger webhooks for user events"""
        async with get_db_session() as session:
            # Get active webhooks for this user and event type
            webhooks = await session.execute(
                select(WebhookEndpoint).where(
                    and_(
                        WebhookEndpoint.user_id == user_id,
                        WebhookEndpoint.is_active == True,
                        WebhookEndpoint.enabled_events.contains([event_type])
                    )
                )
            )

            for webhook in webhooks.scalars().all():
                # Create delivery record
                delivery = WebhookDelivery(
                    endpoint_id=webhook.id,
                    event_type=event_type,
                    event_id=f"{event_type}_{datetime.utcnow().timestamp()}",
                    payload=event_data
                )

                session.add(delivery)

                # Schedule webhook delivery (in production, this would be async)
                asyncio.create_task(self._deliver_webhook(webhook, delivery))

            await session.commit()

    def _generate_api_key(self) -> str:
        """Generate a new API key"""
        return f"ctb_{secrets.token_urlsafe(32)}"

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _get_rate_limits_for_tier(self, tier_name: str) -> Dict[str, int]:
        """Get rate limits based on subscription tier"""
        limits = {
            "free": {"per_minute": 10, "per_hour": 100, "per_day": 1000},
            "pro": {"per_minute": 100, "per_hour": 5000, "per_day": 50000},
            "enterprise": {"per_minute": 1000, "per_hour": 50000, "per_day": 500000}
        }

        return limits.get(tier_name, limits["free"])

    async def _deliver_webhook(self, webhook: WebhookEndpoint, delivery: WebhookDelivery):
        """Deliver webhook (would be implemented with proper HTTP client)"""
        # This would make HTTP POST request to webhook.url with signed payload
        # For now, just mark as delivered
        async with get_db_session() as session:
            delivery_obj = await session.get(WebhookDelivery, delivery.id)
            if delivery_obj:
                delivery_obj.status = "delivered"
                delivery_obj.status_code = 200
                delivery_obj.delivered_at = datetime.utcnow()
                await session.commit()
