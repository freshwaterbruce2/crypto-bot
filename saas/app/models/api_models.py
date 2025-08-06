"""
API Management Models
====================

Database models for API keys, rate limiting, usage tracking, and monetization.
"""

from datetime import datetime, timedelta

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from ..core.database import Base


class APIKey(Base):
    """API key management"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Key details
    key_hash = Column(String(255), unique=True, nullable=False)  # Hashed API key
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Permissions and scopes
    scopes = Column(JSON, default=list)  # read, write, trade, admin
    permissions = Column(JSON, default=dict)

    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    rate_limit_per_day = Column(Integer, default=10000)

    # Usage tracking
    total_requests = Column(Integer, default=0)
    requests_today = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)

    # IP restrictions
    allowed_ips = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("APIUsageLog", back_populates="api_key")

    @hybrid_property
    def is_expired(self) -> bool:
        """Check if API key is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_rate_limited(self) -> bool:
        """Check if API key has exceeded rate limits"""
        now = datetime.utcnow()

        # Check daily limit
        if self.requests_today >= self.rate_limit_per_day:
            return True

        # Check hourly limit (requires querying recent usage)
        hour_ago = now - timedelta(hours=1)
        minute_ago = now - timedelta(minutes=1)

        # This would need to be implemented with a query to usage_logs
        # For now, we'll use a simple check
        return False

    def can_access_scope(self, scope: str) -> bool:
        """Check if API key has access to a specific scope"""
        return scope in (self.scopes or [])

    def to_dict(self, include_key: bool = False) -> dict:
        """Convert API key to dictionary"""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "scopes": self.scopes or [],
            "permissions": self.permissions or {},
            "rate_limits": {
                "per_minute": self.rate_limit_per_minute,
                "per_hour": self.rate_limit_per_hour,
                "per_day": self.rate_limit_per_day
            },
            "usage": {
                "total_requests": self.total_requests,
                "requests_today": self.requests_today,
                "last_used": self.last_used.isoformat() if self.last_used else None
            },
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

        if include_key:
            # In practice, you'd return the actual key only once during creation
            data["key"] = "ctb_" + "x" * 40  # Masked key

        return data


class APIUsageLog(Base):
    """API usage logging for analytics and billing"""
    __tablename__ = "api_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False)

    # Request details
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)

    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_size = Column(Integer, default=0)
    response_size = Column(Integer, default=0)

    # Billing information
    billable_units = Column(Integer, default=1)  # Some endpoints may count as multiple units
    cost_per_unit = Column(Numeric(10, 6), default=0)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    api_key = relationship("APIKey", back_populates="usage_logs")


class APIProduct(Base):
    """API products and pricing tiers"""
    __tablename__ = "api_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    base_price = Column(Numeric(10, 2), default=0)  # Monthly base price
    price_per_request = Column(Numeric(10, 6), default=0)  # Per-request pricing

    # Limits
    included_requests = Column(Integer, default=0)  # Included in base price
    max_requests_per_minute = Column(Integer, default=60)
    max_requests_per_month = Column(Integer, default=100000)

    # Features
    features = Column(JSON, default=list)
    available_scopes = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class APISubscription(Base):
    """API subscription plans"""
    __tablename__ = "api_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("api_products.id"), nullable=False)

    # Subscription details
    status = Column(String(20), default="active")  # active, cancelled, expired

    # Billing period
    current_period_start = Column(DateTime, default=datetime.utcnow)
    current_period_end = Column(DateTime, nullable=False)

    # Usage tracking
    requests_used = Column(Integer, default=0)
    overage_charges = Column(Numeric(10, 2), default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    product = relationship("APIProduct")


class WebhookEndpoint(Base):
    """Webhook endpoints for API integrations"""
    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Endpoint details
    url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    secret = Column(String(255), nullable=False)  # For webhook signature verification

    # Event configuration
    enabled_events = Column(JSON, default=list)  # trade_executed, balance_updated, etc.

    # Status and reliability
    is_active = Column(Boolean, default=True)
    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    deliveries = relationship("WebhookDelivery", back_populates="endpoint")


class WebhookDelivery(Base):
    """Webhook delivery attempts"""
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("webhook_endpoints.id"), nullable=False)

    # Event details
    event_type = Column(String(50), nullable=False)
    event_id = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)

    # Delivery details
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, delivered, failed
    attempt_number = Column(Integer, default=1)
    next_retry = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)

    # Relationships
    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")


class TradingBot(Base):
    """User trading bot instances"""
    __tablename__ = "trading_bots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Bot configuration
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)

    # Trading configuration
    exchange = Column(String(50), nullable=False)
    trading_pairs = Column(JSON, default=list)
    base_currency = Column(String(10), default="USDT")
    initial_balance = Column(Numeric(15, 2), nullable=False)

    # Risk management
    max_position_size = Column(Numeric(5, 2), default=10)  # Percentage
    stop_loss = Column(Numeric(5, 2), nullable=True)
    take_profit = Column(Numeric(5, 2), nullable=True)

    # Status
    status = Column(String(20), default="stopped")  # stopped, running, paused, error
    is_paper_trading = Column(Boolean, default=True)

    # Performance tracking
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    current_balance = Column(Numeric(15, 2), nullable=True)
    total_pnl = Column(Numeric(15, 2), default=0)

    # Configuration
    config = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_trade = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="trading_bots")
    strategy = relationship("Strategy")
    trades = relationship("Trade", back_populates="bot")


class Trade(Base):
    """Trading records from bot instances"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("trading_bots.id"), nullable=False)

    # Trade details
    exchange_order_id = Column(String(100), nullable=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(4), nullable=False)  # buy, sell
    type = Column(String(20), nullable=False)  # market, limit, stop

    # Quantities and prices
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), default=0)

    # Status
    status = Column(String(20), default="pending")  # pending, filled, cancelled, failed

    # P&L tracking
    pnl = Column(Numeric(15, 2), nullable=True)
    pnl_percentage = Column(Numeric(8, 4), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)

    # Relationships
    bot = relationship("TradingBot", back_populates="trades")
