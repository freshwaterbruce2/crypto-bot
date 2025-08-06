"""
Revenue generation model for the crypto trading bot.
Implements subscription tiers, API access, and monetization features.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"
    BASIC = "basic"
    PRO = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionFeatures(BaseModel):
    """Features available for each subscription tier."""
    tier: SubscriptionTier
    max_api_calls_per_month: int
    max_trading_pairs: int
    max_strategies: int
    backtesting_enabled: bool
    realtime_alerts: bool
    custom_indicators: bool
    priority_support: bool
    white_label: bool
    dedicated_server: bool
    price_per_month: float


# Define subscription tiers and their features
SUBSCRIPTION_TIERS: dict[SubscriptionTier, SubscriptionFeatures] = {
    SubscriptionTier.FREE: SubscriptionFeatures(
        tier=SubscriptionTier.FREE,
        max_api_calls_per_month=1000,
        max_trading_pairs=2,
        max_strategies=1,
        backtesting_enabled=False,
        realtime_alerts=False,
        custom_indicators=False,
        priority_support=False,
        white_label=False,
        dedicated_server=False,
        price_per_month=0.0,
    ),
    SubscriptionTier.BASIC: SubscriptionFeatures(
        tier=SubscriptionTier.BASIC,
        max_api_calls_per_month=10000,
        max_trading_pairs=5,
        max_strategies=3,
        backtesting_enabled=True,
        realtime_alerts=True,
        custom_indicators=False,
        priority_support=False,
        white_label=False,
        dedicated_server=False,
        price_per_month=49.99,
    ),
    SubscriptionTier.PRO: SubscriptionFeatures(
        tier=SubscriptionTier.PRO,
        max_api_calls_per_month=100000,
        max_trading_pairs=20,
        max_strategies=10,
        backtesting_enabled=True,
        realtime_alerts=True,
        custom_indicators=True,
        priority_support=True,
        white_label=False,
        dedicated_server=False,
        price_per_month=199.99,
    ),
    SubscriptionTier.ENTERPRISE: SubscriptionFeatures(
        tier=SubscriptionTier.ENTERPRISE,
        max_api_calls_per_month=-1,  # Unlimited
        max_trading_pairs=-1,  # Unlimited
        max_strategies=-1,  # Unlimited
        backtesting_enabled=True,
        realtime_alerts=True,
        custom_indicators=True,
        priority_support=True,
        white_label=True,
        dedicated_server=True,
        price_per_month=999.99,
    ),
}


class User(BaseModel):
    """User model for subscription management."""
    id: str
    email: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    api_key: Optional[str] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    api_calls_this_month: int = 0
    last_api_reset: datetime = Field(default_factory=datetime.utcnow)


class PaymentInfo(BaseModel):
    """Payment information for subscriptions."""
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    payment_method: Optional[str] = None
    last_payment_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None


class RevenueMetrics(BaseModel):
    """Revenue metrics for business analytics."""
    total_users: int
    paying_users: int
    mrr: float  # Monthly Recurring Revenue
    arr: float  # Annual Recurring Revenue
    churn_rate: float
    ltv: float  # Lifetime Value
    revenue_by_tier: dict[SubscriptionTier, float]


class SubscriptionManager:
    """Manages user subscriptions and revenue."""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.security = HTTPBearer()

    def create_api_key(self, user_id: str, tier: SubscriptionTier) -> str:
        """Generate API key for user."""
        payload = {
            "user_id": user_id,
            "tier": tier,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=365),
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verify_api_key(self, credentials: HTTPAuthorizationCredentials) -> dict:
        """Verify API key and return user info."""
        token = credentials.credentials
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

    def check_rate_limit(self, user: User) -> bool:
        """Check if user has exceeded rate limits."""
        features = SUBSCRIPTION_TIERS[user.subscription_tier]

        # Reset monthly counter if needed
        if user.last_api_reset.month != datetime.utcnow().month:
            user.api_calls_this_month = 0
            user.last_api_reset = datetime.utcnow()

        # Check limit (-1 means unlimited)
        if features.max_api_calls_per_month == -1:
            return True

        return user.api_calls_this_month < features.max_api_calls_per_month

    def upgrade_subscription(
        self, user: User, new_tier: SubscriptionTier, payment_info: PaymentInfo
    ) -> User:
        """Upgrade user subscription."""
        old_tier = user.subscription_tier
        user.subscription_tier = new_tier
        user.subscription_start = datetime.utcnow()
        user.subscription_end = datetime.utcnow() + timedelta(days=30)

        # Log upgrade for analytics
        self._log_subscription_change(user.id, old_tier, new_tier)

        return user

    def calculate_revenue_metrics(self, users: list[User]) -> RevenueMetrics:
        """Calculate revenue metrics."""
        total_users = len(users)
        paying_users = len([u for u in users if u.subscription_tier != SubscriptionTier.FREE])

        # Calculate MRR
        mrr = 0.0
        revenue_by_tier = dict.fromkeys(SubscriptionTier, 0.0)

        for user in users:
            tier_price = SUBSCRIPTION_TIERS[user.subscription_tier].price_per_month
            mrr += tier_price
            revenue_by_tier[user.subscription_tier] += tier_price

        # Calculate other metrics
        arr = mrr * 12
        churn_rate = self._calculate_churn_rate(users)
        ltv = self._calculate_ltv(mrr, paying_users, churn_rate)

        return RevenueMetrics(
            total_users=total_users,
            paying_users=paying_users,
            mrr=mrr,
            arr=arr,
            churn_rate=churn_rate,
            ltv=ltv,
            revenue_by_tier=revenue_by_tier,
        )

    def _calculate_churn_rate(self, users: list[User]) -> float:
        """Calculate monthly churn rate."""
        # Simplified calculation - in production, track actual cancellations
        return 0.05  # 5% monthly churn as baseline

    def _calculate_ltv(self, mrr: float, paying_users: int, churn_rate: float) -> float:
        """Calculate customer lifetime value."""
        if paying_users == 0 or churn_rate == 0:
            return 0.0

        avg_revenue_per_user = mrr / paying_users
        return avg_revenue_per_user / churn_rate

    def _log_subscription_change(
        self, user_id: str, old_tier: SubscriptionTier, new_tier: SubscriptionTier
    ):
        """Log subscription changes for analytics."""
        # In production, log to analytics service
        pass


class WebhookService:
    """Handle webhooks for automated trading signals."""

    def __init__(self):
        self.webhook_subscriptions = {}

    def create_webhook(self, user_id: str, url: str, events: list[str]) -> str:
        """Create webhook subscription."""
        webhook_id = f"webhook_{user_id}_{datetime.utcnow().timestamp()}"
        self.webhook_subscriptions[webhook_id] = {
            "user_id": user_id,
            "url": url,
            "events": events,
            "created_at": datetime.utcnow(),
            "active": True,
        }
        return webhook_id

    async def send_webhook(self, event_type: str, data: dict):
        """Send webhook notifications to subscribers."""
        import aiohttp

        for _webhook_id, config in self.webhook_subscriptions.items():
            if event_type in config["events"] and config["active"]:
                async with aiohttp.ClientSession() as session:
                    try:
                        await session.post(
                            config["url"],
                            json={
                                "event": event_type,
                                "data": data,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                            timeout=aiohttp.ClientTimeout(total=10),
                        )
                    except Exception:
                        # Log failed webhook
                        pass


class MarketplaceService:
    """Marketplace for trading strategies and indicators."""

    def __init__(self):
        self.strategies = {}
        self.indicators = {}

    def publish_strategy(
        self, author_id: str, strategy_name: str, description: str, price: float
    ) -> str:
        """Publish strategy to marketplace."""
        strategy_id = f"strategy_{datetime.utcnow().timestamp()}"
        self.strategies[strategy_id] = {
            "author_id": author_id,
            "name": strategy_name,
            "description": description,
            "price": price,
            "purchases": 0,
            "rating": 0.0,
            "published_at": datetime.utcnow(),
        }
        return strategy_id

    def purchase_strategy(self, user_id: str, strategy_id: str) -> bool:
        """Purchase strategy from marketplace."""
        if strategy_id not in self.strategies:
            return False

        # Process payment (integrate with payment provider)
        # Grant access to strategy
        self.strategies[strategy_id]["purchases"] += 1
        return True

    def calculate_author_revenue(self, author_id: str) -> float:
        """Calculate revenue for strategy author."""
        total_revenue = 0.0
        for strategy in self.strategies.values():
            if strategy["author_id"] == author_id:
                # 70% revenue share with authors
                total_revenue += strategy["price"] * strategy["purchases"] * 0.7
        return total_revenue
