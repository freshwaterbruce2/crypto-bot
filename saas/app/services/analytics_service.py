"""
Analytics Service
================

Service layer for business analytics, metrics tracking, and reporting.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.database import get_db_session
from ..models.analytics_models import DailyMetrics, RevenueReport, UserAnalytics, UserEvent
from ..models.api_models import APIUsageLog
from ..models.payment_models import Payment
from ..models.strategy_models import Strategy, StrategyPurchase
from ..models.subscription_models import Subscription, SubscriptionTier
from ..models.user_models import User

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalyticsService:
    """Analytics and reporting service"""

    def __init__(self):
        self.settings = get_settings()

    async def track_user_event(
        self,
        user_id: Optional[int],
        event_type: str,
        event_category: str,
        properties: Dict[str, Any] = None,
        value: float = None,
        session_id: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> UserEvent:
        """Track user event for analytics"""
        async with get_db_session() as session:
            event = UserEvent(
                user_id=user_id,
                event_type=event_type,
                event_category=event_category,
                properties=properties or {},
                value=Decimal(str(value)) if value else None,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )

            session.add(event)
            await session.commit()
            return event

    async def generate_daily_metrics(self, target_date: date = None) -> DailyMetrics:
        """Generate daily metrics for a specific date"""
        if not target_date:
            target_date = date.today() - timedelta(days=1)  # Previous day

        async with get_db_session() as session:
            # Check if metrics already exist for this date
            existing_metrics = await session.scalar(
                select(DailyMetrics).where(DailyMetrics.date == target_date)
            )

            if existing_metrics:
                # Update existing metrics
                metrics = existing_metrics
            else:
                # Create new metrics
                metrics = DailyMetrics(date=target_date)
                session.add(metrics)

            # Date range for the day
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)

            # User metrics
            new_users = await session.scalar(
                select(func.count(User.id)).where(
                    and_(
                        User.created_at >= start_datetime,
                        User.created_at < end_datetime
                    )
                )
            ) or 0

            active_users = await session.scalar(
                select(func.count(func.distinct(UserEvent.user_id))).where(
                    and_(
                        UserEvent.timestamp >= start_datetime,
                        UserEvent.timestamp < end_datetime,
                        UserEvent.user_id.isnot(None)
                    )
                )
            ) or 0

            total_users = await session.scalar(
                select(func.count(User.id)).where(User.created_at < end_datetime)
            ) or 0

            # Subscription metrics
            new_subscriptions = await session.scalar(
                select(func.count(Subscription.id)).where(
                    and_(
                        Subscription.created_at >= start_datetime,
                        Subscription.created_at < end_datetime,
                        Subscription.status == "active"
                    )
                )
            ) or 0

            active_subscriptions = await session.scalar(
                select(func.count(Subscription.id)).where(
                    and_(
                        Subscription.status == "active",
                        Subscription.current_period_end >= start_datetime
                    )
                )
            ) or 0

            cancelled_subscriptions = await session.scalar(
                select(func.count(Subscription.id)).where(
                    and_(
                        Subscription.cancelled_at >= start_datetime,
                        Subscription.cancelled_at < end_datetime
                    )
                )
            ) or 0

            # Revenue metrics
            total_revenue = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(
                        Payment.completed_at >= start_datetime,
                        Payment.completed_at < end_datetime,
                        Payment.status == "completed"
                    )
                )
            ) or Decimal("0")

            subscription_revenue = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(
                        Payment.completed_at >= start_datetime,
                        Payment.completed_at < end_datetime,
                        Payment.status == "completed",
                        Payment.payment_type == "subscription"
                    )
                )
            ) or Decimal("0")

            strategy_revenue = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(
                        Payment.completed_at >= start_datetime,
                        Payment.completed_at < end_datetime,
                        Payment.status == "completed",
                        Payment.payment_type == "strategy_purchase"
                    )
                )
            ) or Decimal("0")

            # Strategy marketplace metrics
            strategies_published = await session.scalar(
                select(func.count(Strategy.id)).where(
                    and_(
                        Strategy.published_at >= start_datetime,
                        Strategy.published_at < end_datetime,
                        Strategy.status == "approved"
                    )
                )
            ) or 0

            strategy_purchases = await session.scalar(
                select(func.count(StrategyPurchase.id)).where(
                    and_(
                        StrategyPurchase.created_at >= start_datetime,
                        StrategyPurchase.created_at < end_datetime,
                        StrategyPurchase.status == "completed"
                    )
                )
            ) or 0

            # API metrics
            api_requests = await session.scalar(
                select(func.count(APIUsageLog.id)).where(
                    and_(
                        APIUsageLog.created_at >= start_datetime,
                        APIUsageLog.created_at < end_datetime
                    )
                )
            ) or 0

            api_errors = await session.scalar(
                select(func.count(APIUsageLog.id)).where(
                    and_(
                        APIUsageLog.created_at >= start_datetime,
                        APIUsageLog.created_at < end_datetime,
                        APIUsageLog.status_code >= 400
                    )
                )
            ) or 0

            # Update metrics
            metrics.new_users = new_users
            metrics.active_users = active_users
            metrics.total_users = total_users
            metrics.new_subscriptions = new_subscriptions
            metrics.active_subscriptions = active_subscriptions
            metrics.cancelled_subscriptions = cancelled_subscriptions
            metrics.total_revenue = total_revenue
            metrics.subscription_revenue = subscription_revenue
            metrics.strategy_revenue = strategy_revenue
            metrics.strategies_published = strategies_published
            metrics.strategy_purchases = strategy_purchases
            metrics.api_requests = api_requests
            metrics.api_errors = api_errors
            metrics.updated_at = datetime.utcnow()

            await session.commit()
            return metrics

    async def get_dashboard_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get dashboard metrics for the last N days"""
        async with get_db_session() as session:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # Get daily metrics for the period
            daily_metrics = await session.execute(
                select(DailyMetrics).where(
                    and_(
                        DailyMetrics.date >= start_date,
                        DailyMetrics.date <= end_date
                    )
                ).order_by(DailyMetrics.date)
            )

            metrics_list = daily_metrics.scalars().all()

            if not metrics_list:
                return self._get_empty_dashboard_metrics()

            # Calculate totals and trends
            latest_metrics = metrics_list[-1] if metrics_list else None
            previous_period_metrics = metrics_list[-days-1:-1] if len(metrics_list) > days else []

            # Current period totals
            total_new_users = sum(m.new_users for m in metrics_list)
            total_revenue = sum(m.total_revenue for m in metrics_list)
            total_api_requests = sum(m.api_requests for m in metrics_list)
            total_strategy_purchases = sum(m.strategy_purchases for m in metrics_list)

            # Calculate growth rates
            prev_new_users = sum(m.new_users for m in previous_period_metrics) if previous_period_metrics else 1
            prev_revenue = sum(m.total_revenue for m in previous_period_metrics) if previous_period_metrics else 1

            user_growth_rate = ((total_new_users - prev_new_users) / prev_new_users * 100) if prev_new_users > 0 else 0
            revenue_growth_rate = ((float(total_revenue) - float(prev_revenue)) / float(prev_revenue) * 100) if prev_revenue > 0 else 0

            return {
                "period_days": days,
                "summary": {
                    "total_users": latest_metrics.total_users if latest_metrics else 0,
                    "new_users": total_new_users,
                    "active_subscriptions": latest_metrics.active_subscriptions if latest_metrics else 0,
                    "total_revenue": float(total_revenue),
                    "user_growth_rate": round(user_growth_rate, 2),
                    "revenue_growth_rate": round(revenue_growth_rate, 2)
                },
                "daily_metrics": [
                    {
                        "date": m.date.isoformat(),
                        "new_users": m.new_users,
                        "active_users": m.active_users,
                        "revenue": float(m.total_revenue),
                        "api_requests": m.api_requests,
                        "strategy_purchases": m.strategy_purchases
                    }
                    for m in metrics_list
                ],
                "subscription_breakdown": await self._get_subscription_breakdown(),
                "top_performing_strategies": await self._get_top_strategies(),
                "api_usage_stats": await self._get_api_usage_stats(days)
            }

    async def update_user_analytics(self, user_id: int) -> UserAnalytics:
        """Update analytics for a specific user"""
        async with get_db_session() as session:
            # Get or create user analytics
            user_analytics = await session.scalar(
                select(UserAnalytics).where(UserAnalytics.user_id == user_id)
            )

            if not user_analytics:
                user_analytics = UserAnalytics(user_id=user_id)
                session.add(user_analytics)

            # Get user data
            user = await session.get(User, user_id, options=[selectinload(User.subscription)])
            if not user:
                return user_analytics

            # Calculate engagement metrics
            total_logins = await session.scalar(
                select(func.count(UserEvent.id)).where(
                    and_(
                        UserEvent.user_id == user_id,
                        UserEvent.event_type == "login"
                    )
                )
            ) or 0

            # Days active (distinct days with events)
            days_active = await session.scalar(
                select(func.count(func.distinct(func.date(UserEvent.timestamp)))).where(
                    UserEvent.user_id == user_id
                )
            ) or 0

            # Last activity
            last_activity = await session.scalar(
                select(func.max(UserEvent.timestamp)).where(UserEvent.user_id == user_id)
            )

            # Feature usage
            strategies_created = await session.scalar(
                select(func.count(Strategy.id)).where(Strategy.owner_id == user_id)
            ) or 0

            strategies_purchased = await session.scalar(
                select(func.count(StrategyPurchase.id)).where(
                    and_(
                        StrategyPurchase.buyer_id == user_id,
                        StrategyPurchase.status == "completed"
                    )
                )
            ) or 0

            # Revenue contribution
            total_spent = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(
                        Payment.user_id == user_id,
                        Payment.status == "completed"
                    )
                )
            ) or Decimal("0")

            total_earned = await session.scalar(
                select(func.sum(StrategyPurchase.price_paid - StrategyPurchase.commission_amount)).where(
                    StrategyPurchase.strategy_id.in_(
                        select(Strategy.id).where(Strategy.owner_id == user_id)
                    )
                )
            ) or Decimal("0")

            # Subscription metrics
            subscription_start_date = user.subscription.created_at if user.subscription else None
            months_subscribed = 0
            if subscription_start_date:
                months_subscribed = (datetime.utcnow() - subscription_start_date).days // 30

            # Calculate behavioral scores (simplified)
            engagement_score = min(100, (days_active * 2) + (total_logins * 0.5))
            retention_risk = max(0, 100 - engagement_score - (months_subscribed * 5))
            upsell_potential = min(100, (strategies_created * 10) + (float(total_spent) / 10))

            # Update analytics
            user_analytics.total_logins = total_logins
            user_analytics.days_active = days_active
            user_analytics.last_activity = last_activity
            user_analytics.strategies_created = strategies_created
            user_analytics.strategies_purchased = strategies_purchased
            user_analytics.total_spent = total_spent
            user_analytics.total_earned = total_earned
            user_analytics.lifetime_value = total_spent + total_earned
            user_analytics.subscription_start_date = subscription_start_date
            user_analytics.months_subscribed = months_subscribed
            user_analytics.engagement_score = Decimal(str(round(engagement_score, 2)))
            user_analytics.retention_risk = Decimal(str(round(retention_risk, 2)))
            user_analytics.upsell_potential = Decimal(str(round(upsell_potential, 2)))
            user_analytics.updated_at = datetime.utcnow()

            await session.commit()
            return user_analytics

    async def generate_revenue_report(
        self,
        report_type: str = "monthly",
        period_start: date = None,
        period_end: date = None
    ) -> RevenueReport:
        """Generate revenue report for a specific period"""
        if not period_start:
            if report_type == "daily":
                period_start = date.today() - timedelta(days=1)
                period_end = date.today()
            elif report_type == "weekly":
                period_start = date.today() - timedelta(weeks=1)
                period_end = date.today()
            elif report_type == "monthly":
                today = date.today()
                period_start = today.replace(day=1) - timedelta(days=1) # Previous month
                period_start = period_start.replace(day=1)
                period_end = today.replace(day=1) - timedelta(days=1)
            else:  # yearly
                today = date.today()
                period_start = date(today.year - 1, 1, 1)
                period_end = date(today.year - 1, 12, 31)

        async with get_db_session() as session:
            start_datetime = datetime.combine(period_start, datetime.min.time())
            end_datetime = datetime.combine(period_end, datetime.max.time())

            # Revenue breakdown
            subscription_revenue = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(
                        Payment.completed_at >= start_datetime,
                        Payment.completed_at <= end_datetime,
                        Payment.status == "completed",
                        Payment.payment_type == "subscription"
                    )
                )
            ) or Decimal("0")

            strategy_revenue = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(
                        Payment.completed_at >= start_datetime,
                        Payment.completed_at <= end_datetime,
                        Payment.status == "completed",
                        Payment.payment_type == "strategy_purchase"
                    )
                )
            ) or Decimal("0")

            # Commission earned from strategy marketplace
            commission_earned = await session.scalar(
                select(func.sum(StrategyPurchase.commission_amount)).where(
                    and_(
                        StrategyPurchase.created_at >= start_datetime,
                        StrategyPurchase.created_at <= end_datetime,
                        StrategyPurchase.status == "completed"
                    )
                )
            ) or Decimal("0")

            total_revenue = subscription_revenue + strategy_revenue

            # Subscription tier breakdown
            tier_counts = await session.execute(
                select(
                    SubscriptionTier.name,
                    func.count(Subscription.id).label("count")
                ).select_from(Subscription)
                .join(SubscriptionTier)
                .where(
                    and_(
                        Subscription.status == "active",
                        Subscription.current_period_start <= end_datetime,
                        Subscription.current_period_end >= start_datetime
                    )
                )
                .group_by(SubscriptionTier.name)
            )

            free_tier_users = 0
            pro_tier_users = 0
            enterprise_tier_users = 0

            for row in tier_counts:
                if row.name == "free":
                    free_tier_users = row.count
                elif row.name == "pro":
                    pro_tier_users = row.count
                elif row.name == "enterprise":
                    enterprise_tier_users = row.count

            # New customers in period
            new_customers = await session.scalar(
                select(func.count(User.id)).where(
                    and_(
                        User.created_at >= start_datetime,
                        User.created_at <= end_datetime
                    )
                )
            ) or 0

            # Create revenue report
            report = RevenueReport(
                report_type=report_type,
                period_start=period_start,
                period_end=period_end,
                subscription_revenue=subscription_revenue,
                strategy_marketplace_revenue=strategy_revenue,
                total_revenue=total_revenue,
                strategy_commissions=commission_earned,
                net_revenue=total_revenue - commission_earned,
                free_tier_users=free_tier_users,
                pro_tier_users=pro_tier_users,
                enterprise_tier_users=enterprise_tier_users,
                new_customers=new_customers
            )

            async with get_db_session() as session:
                session.add(report)
                await session.commit()

            return report

    async def get_user_segmentation(self) -> Dict[str, Any]:
        """Get user segmentation analysis"""
        async with get_db_session() as session:
            # Segment by subscription tier
            tier_segments = await session.execute(
                select(
                    SubscriptionTier.name,
                    SubscriptionTier.display_name,
                    func.count(User.id).label("user_count"),
                    func.avg(UserAnalytics.engagement_score).label("avg_engagement"),
                    func.sum(UserAnalytics.total_spent).label("total_spent")
                ).select_from(User)
                .outerjoin(Subscription, User.id == Subscription.user_id)
                .outerjoin(SubscriptionTier, Subscription.tier_id == SubscriptionTier.id)
                .outerjoin(UserAnalytics, User.id == UserAnalytics.user_id)
                .group_by(SubscriptionTier.name, SubscriptionTier.display_name)
            )

            # Segment by engagement level
            engagement_segments = await session.execute(
                select(
                    func.case(
                        (UserAnalytics.engagement_score >= 80, "High"),
                        (UserAnalytics.engagement_score >= 50, "Medium"),
                        else_="Low"
                    ).label("engagement_level"),
                    func.count(UserAnalytics.id).label("user_count"),
                    func.avg(UserAnalytics.total_spent).label("avg_spent")
                ).select_from(UserAnalytics)
                .group_by("engagement_level")
            )

            return {
                "by_subscription_tier": [
                    {
                        "tier": row.name or "free",
                        "display_name": row.display_name or "Free",
                        "user_count": row.user_count,
                        "avg_engagement": float(row.avg_engagement or 0),
                        "total_spent": float(row.total_spent or 0)
                    }
                    for row in tier_segments
                ],
                "by_engagement_level": [
                    {
                        "level": row.engagement_level,
                        "user_count": row.user_count,
                        "avg_spent": float(row.avg_spent or 0)
                    }
                    for row in engagement_segments
                ]
            }

    def _get_empty_dashboard_metrics(self) -> Dict[str, Any]:
        """Return empty dashboard metrics structure"""
        return {
            "period_days": 30,
            "summary": {
                "total_users": 0,
                "new_users": 0,
                "active_subscriptions": 0,
                "total_revenue": 0.0,
                "user_growth_rate": 0.0,
                "revenue_growth_rate": 0.0
            },
            "daily_metrics": [],
            "subscription_breakdown": [],
            "top_performing_strategies": [],
            "api_usage_stats": {}
        }

    async def _get_subscription_breakdown(self) -> List[Dict[str, Any]]:
        """Get current subscription tier breakdown"""
        async with get_db_session() as session:
            breakdown = await session.execute(
                select(
                    SubscriptionTier.name,
                    SubscriptionTier.display_name,
                    func.count(Subscription.id).label("count")
                ).select_from(SubscriptionTier)
                .outerjoin(Subscription, and_(
                    Subscription.tier_id == SubscriptionTier.id,
                    Subscription.status == "active"
                ))
                .group_by(SubscriptionTier.id, SubscriptionTier.name, SubscriptionTier.display_name)
                .order_by(SubscriptionTier.sort_order)
            )

            return [
                {
                    "tier": row.name,
                    "display_name": row.display_name,
                    "count": row.count or 0
                }
                for row in breakdown
            ]

    async def _get_top_strategies(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top performing strategies"""
        async with get_db_session() as session:
            strategies = await session.execute(
                select(
                    Strategy.name,
                    Strategy.total_revenue,
                    Strategy.purchases,
                    Strategy.rating
                ).where(Strategy.status == "approved")
                .order_by(desc(Strategy.total_revenue))
                .limit(limit)
            )

            return [
                {
                    "name": row.name,
                    "revenue": float(row.total_revenue or 0),
                    "purchases": row.purchases,
                    "rating": float(row.rating or 0)
                }
                for row in strategies
            ]

    async def _get_api_usage_stats(self, days: int) -> Dict[str, Any]:
        """Get API usage statistics"""
        async with get_db_session() as session:
            since_date = datetime.utcnow() - timedelta(days=days)

            total_requests = await session.scalar(
                select(func.count(APIUsageLog.id)).where(
                    APIUsageLog.created_at >= since_date
                )
            ) or 0

            avg_response_time = await session.scalar(
                select(func.avg(APIUsageLog.response_time_ms)).where(
                    APIUsageLog.created_at >= since_date
                )
            ) or 0

            error_rate = 0
            if total_requests > 0:
                error_count = await session.scalar(
                    select(func.count(APIUsageLog.id)).where(
                        and_(
                            APIUsageLog.created_at >= since_date,
                            APIUsageLog.status_code >= 400
                        )
                    )
                ) or 0
                error_rate = (error_count / total_requests) * 100

            return {
                "total_requests": total_requests,
                "avg_response_time_ms": float(avg_response_time),
                "error_rate_percent": round(error_rate, 2)
            }
