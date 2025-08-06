"""
Strategy Marketplace Models
==========================

Database models for trading strategies, marketplace, and revenue sharing.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from ..core.database import Base


class Strategy(Base):
    """Trading strategy model"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Basic information
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(255), nullable=True)
    version = Column(String(20), default="1.0.0")

    # Strategy code and configuration
    strategy_code = Column(Text, nullable=False)
    parameters = Column(JSON, default=dict)
    default_config = Column(JSON, default=dict)

    # Marketplace information
    is_public = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    price = Column(Numeric(10, 2), default=0)
    currency = Column(String(3), default="USD")

    # Performance metrics
    total_return = Column(Numeric(10, 4), default=0)
    max_drawdown = Column(Numeric(10, 4), default=0)
    win_rate = Column(Numeric(5, 2), default=0)
    sharpe_ratio = Column(Numeric(10, 4), default=0)

    # Trading requirements
    min_balance = Column(Numeric(15, 2), default=0)
    supported_exchanges = Column(JSON, default=list)
    supported_pairs = Column(JSON, default=list)
    timeframes = Column(JSON, default=list)

    # Marketplace metrics
    downloads = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    rating = Column(Numeric(3, 2), default=0)
    review_count = Column(Integer, default=0)

    # Revenue tracking
    total_revenue = Column(Numeric(15, 2), default=0)
    commission_earned = Column(Numeric(15, 2), default=0)

    # Status and approval
    status = Column(String(20), default="draft")  # draft, pending, approved, rejected, suspended
    approval_notes = Column(Text, nullable=True)

    # Tags and categories
    tags = Column(JSON, default=list)
    category = Column(String(50), nullable=True)
    risk_level = Column(String(20), default="medium")  # low, medium, high

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="strategies")
    purchases = relationship("StrategyPurchase", back_populates="strategy")
    reviews = relationship("StrategyReview", back_populates="strategy")
    backtests = relationship("StrategyBacktest", back_populates="strategy")

    @hybrid_property
    def is_free(self) -> bool:
        """Check if strategy is free"""
        return not self.is_premium or self.price == 0

    @hybrid_property
    def average_rating(self) -> float:
        """Calculate average rating"""
        if self.review_count == 0:
            return 0.0
        return float(self.rating or 0)

    def to_dict(self, include_code: bool = False) -> dict:
        """Convert strategy to dictionary"""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "short_description": self.short_description,
            "version": self.version,
            "is_public": self.is_public,
            "is_premium": self.is_premium,
            "is_free": self.is_free,
            "price": float(self.price or 0),
            "currency": self.currency,
            "performance": {
                "total_return": float(self.total_return or 0),
                "max_drawdown": float(self.max_drawdown or 0),
                "win_rate": float(self.win_rate or 0),
                "sharpe_ratio": float(self.sharpe_ratio or 0)
            },
            "requirements": {
                "min_balance": float(self.min_balance or 0),
                "supported_exchanges": self.supported_exchanges or [],
                "supported_pairs": self.supported_pairs or [],
                "timeframes": self.timeframes or []
            },
            "marketplace": {
                "downloads": self.downloads,
                "purchases": self.purchases,
                "rating": self.average_rating,
                "review_count": self.review_count
            },
            "tags": self.tags or [],
            "category": self.category,
            "risk_level": self.risk_level,
            "status": self.status,
            "owner": {
                "id": self.owner.id,
                "username": self.owner.username
            } if self.owner else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None
        }

        if include_code:
            data.update({
                "strategy_code": self.strategy_code,
                "parameters": self.parameters or {},
                "default_config": self.default_config or {}
            })

        return data


class StrategyPurchase(Base):
    """Strategy purchase records"""
    __tablename__ = "strategy_purchases"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Purchase details
    price_paid = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    commission_rate = Column(Numeric(5, 4), nullable=False)  # 0.30 = 30%
    commission_amount = Column(Numeric(10, 2), nullable=False)

    # Payment information
    payment_method = Column(String(50), nullable=False)
    transaction_id = Column(String(100), nullable=True)
    stripe_payment_intent_id = Column(String(100), nullable=True)

    # Status
    status = Column(String(20), default="completed")  # pending, completed, refunded
    refund_reason = Column(Text, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    strategy = relationship("Strategy", back_populates="purchases")
    buyer = relationship("User")


class StrategyReview(Base):
    """Strategy reviews and ratings"""
    __tablename__ = "strategy_reviews"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Review content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)

    # Performance feedback
    actual_return = Column(Numeric(10, 4), nullable=True)
    usage_period_days = Column(Integer, nullable=True)

    # Status
    is_verified = Column(Boolean, default=False)  # Verified purchase
    is_helpful = Column(Integer, default=0)  # Helpful votes

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    strategy = relationship("Strategy", back_populates="reviews")
    reviewer = relationship("User")


class StrategyBacktest(Base):
    """Strategy backtest results"""
    __tablename__ = "strategy_backtests"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Backtest parameters
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_balance = Column(Numeric(15, 2), nullable=False)
    trading_pairs = Column(JSON, default=list)

    # Results
    final_balance = Column(Numeric(15, 2), nullable=False)
    total_return = Column(Numeric(10, 4), nullable=False)
    max_drawdown = Column(Numeric(10, 4), nullable=False)
    win_rate = Column(Numeric(5, 2), nullable=False)
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)

    # Advanced metrics
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    sortino_ratio = Column(Numeric(10, 4), nullable=True)
    calmar_ratio = Column(Numeric(10, 4), nullable=True)

    # Detailed results
    trade_history = Column(JSON, default=list)
    equity_curve = Column(JSON, default=list)
    monthly_returns = Column(JSON, default=dict)

    # Status
    status = Column(String(20), default="completed")  # running, completed, failed
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    strategy = relationship("Strategy", back_populates="backtests")
    user = relationship("User")


class StrategyCategory(Base):
    """Strategy categories for organization"""
    __tablename__ = "strategy_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)

    # Hierarchy
    parent_id = Column(Integer, ForeignKey("strategy_categories.id"), nullable=True)
    sort_order = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    parent = relationship("StrategyCategory", remote_side=[id])
    children = relationship("StrategyCategory")


class StrategyTemplate(Base):
    """Pre-built strategy templates"""
    __tablename__ = "strategy_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Template code
    template_code = Column(Text, nullable=False)
    parameters = Column(JSON, default=dict)

    # Classification
    category = Column(String(50), nullable=True)
    difficulty = Column(String(20), default="beginner")  # beginner, intermediate, advanced
    tags = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
