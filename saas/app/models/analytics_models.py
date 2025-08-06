"""
Analytics and Reporting Models
==============================

Database models for analytics, metrics, reporting, and business intelligence.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from ..core.database import Base


class DailyMetrics(Base):
    """Daily aggregated metrics"""
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False, index=True)

    # User metrics
    new_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    total_users = Column(Integer, default=0)
    churned_users = Column(Integer, default=0)

    # Subscription metrics
    new_subscriptions = Column(Integer, default=0)
    active_subscriptions = Column(Integer, default=0)
    cancelled_subscriptions = Column(Integer, default=0)

    # Revenue metrics
    total_revenue = Column(Numeric(15, 2), default=0)
    subscription_revenue = Column(Numeric(15, 2), default=0)
    strategy_revenue = Column(Numeric(15, 2), default=0)
    api_revenue = Column(Numeric(15, 2), default=0)

    # Strategy marketplace metrics
    strategies_published = Column(Integer, default=0)
    strategy_downloads = Column(Integer, default=0)
    strategy_purchases = Column(Integer, default=0)

    # API metrics
    api_requests = Column(Integer, default=0)
    api_errors = Column(Integer, default=0)
    new_api_keys = Column(Integer, default=0)

    # Trading metrics
    total_trades = Column(Integer, default=0)
    successful_trades = Column(Integer, default=0)
    total_volume = Column(Numeric(20, 2), default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserAnalytics(Base):
    """Individual user analytics and behavior tracking"""
    __tablename__ = "user_analytics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Engagement metrics
    total_logins = Column(Integer, default=0)
    days_active = Column(Integer, default=0)
    last_activity = Column(DateTime, nullable=True)

    # Feature usage
    strategies_created = Column(Integer, default=0)
    strategies_purchased = Column(Integer, default=0)
    api_calls_made = Column(Integer, default=0)
    trades_executed = Column(Integer, default=0)

    # Revenue contribution
    total_spent = Column(Numeric(15, 2), default=0)
    total_earned = Column(Numeric(15, 2), default=0)  # From strategy sales
    lifetime_value = Column(Numeric(15, 2), default=0)

    # Subscription history
    subscription_start_date = Column(DateTime, nullable=True)
    subscription_tier_changes = Column(Integer, default=0)
    months_subscribed = Column(Integer, default=0)

    # Behavior scores
    engagement_score = Column(Numeric(5, 2), default=0)  # 0-100
    retention_risk = Column(Numeric(5, 2), default=0)    # 0-100
    upsell_potential = Column(Numeric(5, 2), default=0)  # 0-100

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")


class StrategyAnalytics(Base):
    """Strategy performance and marketplace analytics"""
    __tablename__ = "strategy_analytics"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False, unique=True)

    # Performance metrics
    total_return = Column(Numeric(10, 4), default=0)
    annualized_return = Column(Numeric(10, 4), default=0)
    max_drawdown = Column(Numeric(10, 4), default=0)
    sharpe_ratio = Column(Numeric(10, 4), default=0)
    sortino_ratio = Column(Numeric(10, 4), default=0)

    # Trading metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Numeric(5, 2), default=0)
    average_win = Column(Numeric(10, 4), default=0)
    average_loss = Column(Numeric(10, 4), default=0)

    # Marketplace metrics
    total_views = Column(Integer, default=0)
    total_downloads = Column(Integer, default=0)
    total_purchases = Column(Integer, default=0)
    total_revenue = Column(Numeric(15, 2), default=0)

    # User engagement
    active_users = Column(Integer, default=0)
    user_retention_rate = Column(Numeric(5, 2), default=0)

    # Rating and reviews
    average_rating = Column(Numeric(3, 2), default=0)
    total_reviews = Column(Integer, default=0)

    # Market position
    category_rank = Column(Integer, nullable=True)
    trending_score = Column(Numeric(5, 2), default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    strategy = relationship("Strategy")


class RevenueReport(Base):
    """Revenue reports and financial analytics"""
    __tablename__ = "revenue_reports"

    id = Column(Integer, primary_key=True, index=True)

    # Report details
    report_type = Column(String(20), nullable=False)  # daily, weekly, monthly, yearly
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Revenue breakdown
    subscription_revenue = Column(Numeric(15, 2), default=0)
    strategy_marketplace_revenue = Column(Numeric(15, 2), default=0)
    api_usage_revenue = Column(Numeric(15, 2), default=0)
    white_label_revenue = Column(Numeric(15, 2), default=0)
    other_revenue = Column(Numeric(15, 2), default=0)
    total_revenue = Column(Numeric(15, 2), default=0)

    # Costs
    payment_processing_fees = Column(Numeric(15, 2), default=0)
    strategy_commissions = Column(Numeric(15, 2), default=0)
    operational_costs = Column(Numeric(15, 2), default=0)
    total_costs = Column(Numeric(15, 2), default=0)

    # Metrics
    net_revenue = Column(Numeric(15, 2), default=0)
    profit_margin = Column(Numeric(5, 2), default=0)

    # Subscription details
    free_tier_users = Column(Integer, default=0)
    pro_tier_users = Column(Integer, default=0)
    enterprise_tier_users = Column(Integer, default=0)

    # Growth metrics
    new_customers = Column(Integer, default=0)
    churned_customers = Column(Integer, default=0)
    customer_growth_rate = Column(Numeric(5, 2), default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    @hybrid_property
    def average_revenue_per_user(self) -> float:
        """Calculate ARPU"""
        total_users = self.free_tier_users + self.pro_tier_users + self.enterprise_tier_users
        if total_users == 0:
            return 0.0
        return float(self.total_revenue / total_users)


class SystemMetrics(Base):
    """System performance and operational metrics"""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # API performance
    api_response_time_avg = Column(Numeric(8, 2), default=0)  # milliseconds
    api_success_rate = Column(Numeric(5, 2), default=100)     # percentage
    api_requests_per_second = Column(Numeric(8, 2), default=0)

    # Database performance
    db_query_time_avg = Column(Numeric(8, 2), default=0)
    db_connection_pool_usage = Column(Numeric(5, 2), default=0)

    # Trading bot performance
    active_bots = Column(Integer, default=0)
    trades_per_minute = Column(Numeric(8, 2), default=0)
    bot_uptime_percentage = Column(Numeric(5, 2), default=100)

    # System resources
    cpu_usage = Column(Numeric(5, 2), default=0)
    memory_usage = Column(Numeric(5, 2), default=0)
    disk_usage = Column(Numeric(5, 2), default=0)

    # Error rates
    error_rate = Column(Numeric(5, 2), default=0)
    critical_errors = Column(Integer, default=0)
    warnings = Column(Integer, default=0)


class UserEvent(Base):
    """Track user events for analytics and personalization"""
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Can be null for anonymous events

    # Event details
    event_type = Column(String(50), nullable=False)  # login, signup, purchase, etc.
    event_category = Column(String(50), nullable=False)  # user, subscription, strategy, api

    # Event data
    properties = Column(JSON, default=dict)
    value = Column(Numeric(15, 2), nullable=True)  # Monetary value if applicable

    # Session and context
    session_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Referral information
    referrer = Column(String(500), nullable=True)
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")


class CohortAnalysis(Base):
    """Cohort analysis for user retention"""
    __tablename__ = "cohort_analysis"

    id = Column(Integer, primary_key=True, index=True)

    # Cohort definition
    cohort_month = Column(Date, nullable=False, index=True)  # Month when users joined
    period_number = Column(Integer, nullable=False)  # 0 = first month, 1 = second, etc.

    # Metrics
    users_in_cohort = Column(Integer, nullable=False)
    active_users = Column(Integer, nullable=False)
    retention_rate = Column(Numeric(5, 2), nullable=False)

    # Revenue metrics
    revenue_per_user = Column(Numeric(10, 2), default=0)
    cumulative_revenue = Column(Numeric(15, 2), default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class ABTest(Base):
    """A/B testing experiments"""
    __tablename__ = "ab_tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Test configuration
    test_type = Column(String(50), nullable=False)  # pricing, ui, feature
    variants = Column(JSON, nullable=False)  # {control: {}, variant_a: {}, variant_b: {}}

    # Targeting
    target_percentage = Column(Numeric(5, 2), default=100)  # Percentage of users to include
    target_criteria = Column(JSON, default=dict)

    # Status
    status = Column(String(20), default="draft")  # draft, running, paused, completed

    # Results
    conversion_metric = Column(String(50), nullable=False)
    statistical_significance = Column(Numeric(5, 2), nullable=True)
    winning_variant = Column(String(50), nullable=True)

    # Dates
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ABTestParticipant(Base):
    """Track A/B test participants"""
    __tablename__ = "ab_test_participants"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("ab_tests.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Assignment
    variant = Column(String(50), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    # Conversion tracking
    converted = Column(Boolean, default=False)
    converted_at = Column(DateTime, nullable=True)
    conversion_value = Column(Numeric(15, 2), nullable=True)

    # Relationships
    test = relationship("ABTest")
    user = relationship("User")
