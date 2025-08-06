"""
Subscription Management Models
=============================

Database models for subscription tiers, billing, and feature access.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from ..core.config import get_settings
from ..core.database import Base

settings = get_settings()


class SubscriptionTier(Base):
    """Subscription tier definitions"""
    __tablename__ = "subscription_tiers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # free, pro, enterprise
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    price_monthly = Column(Numeric(10, 2), nullable=False, default=0)
    price_yearly = Column(Numeric(10, 2), nullable=False, default=0)
    stripe_price_id_monthly = Column(String(100), nullable=True)
    stripe_price_id_yearly = Column(String(100), nullable=True)

    # Limits and features
    max_strategies = Column(Integer, default=-1)  # -1 = unlimited
    max_api_calls = Column(Integer, default=-1)  # -1 = unlimited
    max_trading_pairs = Column(Integer, default=-1)  # -1 = unlimited
    features = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True)
    is_popular = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="tier")

    def to_dict(self) -> dict:
        """Convert tier to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "price_monthly": float(self.price_monthly or 0),
            "price_yearly": float(self.price_yearly or 0),
            "max_strategies": self.max_strategies,
            "max_api_calls": self.max_api_calls,
            "max_trading_pairs": self.max_trading_pairs,
            "features": self.features or [],
            "is_popular": self.is_popular,
            "sort_order": self.sort_order
        }


class Subscription(Base):
    """User subscription model"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    tier_id = Column(Integer, ForeignKey("subscription_tiers.id"), nullable=False)

    # Billing details
    billing_cycle = Column(String(20), nullable=False, default="monthly")  # monthly, yearly
    status = Column(String(20), nullable=False, default="active")  # active, cancelled, expired, past_due

    # Stripe integration
    stripe_subscription_id = Column(String(100), unique=True, nullable=True)
    stripe_customer_id = Column(String(100), nullable=True)

    # Dates
    current_period_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    current_period_end = Column(DateTime, nullable=False)
    trial_end = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Usage tracking
    api_calls_used = Column(Integer, default=0)
    strategies_used = Column(Integer, default=0)
    trading_pairs_used = Column(Integer, default=0)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscription")
    tier = relationship("SubscriptionTier", back_populates="subscriptions")
    usage_records = relationship("UsageRecord", back_populates="subscription")

    @hybrid_property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        if self.status != "active":
            return False

        now = datetime.utcnow()
        if self.current_period_end < now:
            return False

        return True

    @hybrid_property
    def is_trial(self) -> bool:
        """Check if subscription is in trial period"""
        if not self.trial_end:
            return False

        now = datetime.utcnow()
        return now < self.trial_end

    @hybrid_property
    def days_until_renewal(self) -> int:
        """Days until subscription renewal"""
        if not self.is_active:
            return 0

        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)

    def can_use_feature(self, feature: str) -> bool:
        """Check if user can use a specific feature"""
        if not self.is_active:
            return False

        return feature in (self.tier.features or [])

    def check_limit(self, resource: str) -> dict:
        """Check usage against limits for a resource"""
        limits = {
            "api_calls": self.tier.max_api_calls,
            "strategies": self.tier.max_strategies,
            "trading_pairs": self.tier.max_trading_pairs
        }

        used = {
            "api_calls": self.api_calls_used,
            "strategies": self.strategies_used,
            "trading_pairs": self.trading_pairs_used
        }

        limit = limits.get(resource, 0)
        current_usage = used.get(resource, 0)

        return {
            "limit": limit,
            "used": current_usage,
            "remaining": max(0, limit - current_usage) if limit != -1 else -1,
            "unlimited": limit == -1,
            "exceeded": limit != -1 and current_usage >= limit
        }

    def to_dict(self) -> dict:
        """Convert subscription to dictionary"""
        return {
            "id": self.id,
            "tier": self.tier.to_dict() if self.tier else None,
            "billing_cycle": self.billing_cycle,
            "status": self.status,
            "is_active": self.is_active,
            "is_trial": self.is_trial,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "days_until_renewal": self.days_until_renewal,
            "usage": {
                "api_calls": self.check_limit("api_calls"),
                "strategies": self.check_limit("strategies"),
                "trading_pairs": self.check_limit("trading_pairs")
            }
        }


class UsageRecord(Base):
    """Track resource usage for billing and limits"""
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)

    # Usage details
    resource_type = Column(String(50), nullable=False)  # api_calls, strategies, trading_pairs
    quantity = Column(Integer, nullable=False, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Relationships
    subscription = relationship("Subscription", back_populates="usage_records")


class SubscriptionEvent(Base):
    """Track subscription lifecycle events"""
    __tablename__ = "subscription_events"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)

    # Event details
    event_type = Column(String(50), nullable=False)  # created, upgraded, downgraded, cancelled, renewed
    from_tier = Column(String(50), nullable=True)
    to_tier = Column(String(50), nullable=True)

    # Pricing info
    amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="USD")

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subscription = relationship("Subscription")


class WhiteLabelConfig(Base):
    """White-label configuration for enterprise clients"""
    __tablename__ = "white_label_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Branding
    company_name = Column(String(100), nullable=False)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color
    secondary_color = Column(String(7), nullable=True)
    custom_domain = Column(String(255), nullable=True)

    # Features
    enabled_features = Column(JSON, default=list)
    custom_integrations = Column(JSON, default=dict)

    # Pricing
    monthly_fee = Column(Numeric(10, 2), nullable=False)
    setup_fee = Column(Numeric(10, 2), default=0)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
