"""
SaaS Platform Configuration
==========================

Centralized configuration management for the SaaS platform.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./saas_platform.db",
        env="DATABASE_URL"
    )

    # Security
    SECRET_KEY: str = Field(env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        env="ALLOWED_HOSTS"
    )

    # Stripe Payment Processing
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(default=None, env="STRIPE_PUBLISHABLE_KEY")
    STRIPE_SECRET_KEY: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")

    # Cryptocurrency Payment
    CRYPTO_PAYMENT_ENABLED: bool = Field(default=False, env="CRYPTO_PAYMENT_ENABLED")
    BTC_WALLET_ADDRESS: Optional[str] = Field(default=None, env="BTC_WALLET_ADDRESS")
    ETH_WALLET_ADDRESS: Optional[str] = Field(default=None, env="ETH_WALLET_ADDRESS")

    # Trading Bot Integration
    TRADING_BOT_API_URL: str = Field(
        default="http://localhost:8001",
        env="TRADING_BOT_API_URL"
    )
    TRADING_BOT_API_KEY: Optional[str] = Field(default=None, env="TRADING_BOT_API_KEY")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    DEFAULT_RATE_LIMIT: str = Field(default="100/minute", env="DEFAULT_RATE_LIMIT")

    # Email
    SMTP_SERVER: Optional[str] = Field(default=None, env="SMTP_SERVER")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    FROM_EMAIL: str = Field(default="noreply@cryptotradingbot.com", env="FROM_EMAIL")

    # File Storage
    UPLOAD_DIR: str = Field(default="uploads", env="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = Field(default=10485760, env="MAX_UPLOAD_SIZE")  # 10MB

    # Redis Cache
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")  # 1 hour

    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # API Versioning
    API_VERSION: str = Field(default="v1", env="API_VERSION")

    # Subscription Tiers
    FREE_TIER_LIMITS: dict = {
        "max_strategies": 1,
        "max_api_calls": 1000,
        "max_trading_pairs": 0,  # Paper trading only
        "features": ["paper_trading", "basic_strategies", "community_support"]
    }

    PRO_TIER_LIMITS: dict = {
        "max_strategies": 10,
        "max_api_calls": 50000,
        "max_trading_pairs": 5,
        "features": [
            "live_trading", "advanced_strategies", "priority_support",
            "custom_indicators", "backtesting", "risk_management"
        ]
    }

    ENTERPRISE_TIER_LIMITS: dict = {
        "max_strategies": -1,  # Unlimited
        "max_api_calls": -1,   # Unlimited
        "max_trading_pairs": -1,  # Unlimited
        "features": [
            "unlimited_trading", "custom_strategies", "dedicated_support",
            "white_label", "api_access", "custom_integrations", "priority_execution",
            "advanced_analytics", "multi_exchange", "institutional_features"
        ]
    }

    # Pricing (in cents)
    PRO_TIER_PRICE: int = Field(default=9900, env="PRO_TIER_PRICE")  # $99.00
    ENTERPRISE_TIER_PRICE: int = Field(default=99900, env="ENTERPRISE_TIER_PRICE")  # $999.00
    WHITE_LABEL_BASE_PRICE: int = Field(default=1000000, env="WHITE_LABEL_BASE_PRICE")  # $10,000.00

    # Strategy Marketplace
    MARKETPLACE_COMMISSION: float = Field(default=0.30, env="MARKETPLACE_COMMISSION")  # 30%
    MIN_STRATEGY_PRICE: int = Field(default=999, env="MIN_STRATEGY_PRICE")  # $9.99
    MAX_STRATEGY_PRICE: int = Field(default=99999, env="MAX_STRATEGY_PRICE")  # $999.99

    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if not v:
            raise ValueError("SECRET_KEY is required")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
