"""
Configuration management for the crypto trading bot.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration class for the trading bot."""

    # Exchange configuration
    exchange_name: str = "kraken"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

    # Trading configuration
    base_currency: str = "USD"
    trading_pairs: list = field(default_factory=lambda: ["BTC/USD", "ETH/USD"])
    max_position_size: float = 1000.0
    stop_loss_percent: float = 0.02
    take_profit_percent: float = 0.04

    # Risk management
    max_daily_loss: float = 100.0
    max_open_positions: int = 5
    min_order_size: float = 10.0

    # Technical analysis
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    ma_short_period: int = 10
    ma_long_period: int = 20

    # Regime detection
    regime_lookback_period: int = 50
    volatility_threshold: float = 0.02
    trend_threshold: float = 0.01

    # Performance monitoring
    performance_window: int = 1000
    benchmark_symbol: str = "BTC/USD"

    # Logging
    log_level: str = "INFO"
    log_file: str = "trading_bot.log"

    # Database
    db_path: str = "trading_data.db"

    def __post_init__(self):
        """Post-initialization setup."""
        self.api_key = os.getenv("KRAKEN_API_KEY", self.api_key)
        self.api_secret = os.getenv("KRAKEN_API_SECRET", self.api_secret)

        # Validate required fields
        if not self.api_key or not self.api_secret:
            logger.warning("API credentials not found in environment variables")

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "exchange_name": self.exchange_name,
            "base_currency": self.base_currency,
            "trading_pairs": self.trading_pairs,
            "max_position_size": self.max_position_size,
            "stop_loss_percent": self.stop_loss_percent,
            "take_profit_percent": self.take_profit_percent,
            "max_daily_loss": self.max_daily_loss,
            "max_open_positions": self.max_open_positions,
            "min_order_size": self.min_order_size,
            "rsi_period": self.rsi_period,
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
            "ma_short_period": self.ma_short_period,
            "ma_long_period": self.ma_long_period,
            "regime_lookback_period": self.regime_lookback_period,
            "volatility_threshold": self.volatility_threshold,
            "trend_threshold": self.trend_threshold,
            "performance_window": self.performance_window,
            "benchmark_symbol": self.benchmark_symbol,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "db_path": self.db_path,
        }

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        return cls(**config_dict)

    def update(self, **kwargs) -> None:
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"Updated config: {key} = {value}")
            else:
                logger.warning(f"Unknown config parameter: {key}")

    def validate(self) -> bool:
        """Validate configuration parameters."""
        try:
            # Validate numeric ranges
            assert 0 < self.stop_loss_percent < 1, "Stop loss must be between 0 and 1"
            assert 0 < self.take_profit_percent < 1, "Take profit must be between 0 and 1"
            assert self.max_daily_loss > 0, "Max daily loss must be positive"
            assert self.max_open_positions > 0, "Max open positions must be positive"
            assert self.min_order_size > 0, "Min order size must be positive"

            # Validate RSI parameters
            assert 0 < self.rsi_oversold < 50, "RSI oversold must be between 0 and 50"
            assert 50 < self.rsi_overbought < 100, "RSI overbought must be between 50 and 100"

            # Validate MA periods
            assert self.ma_short_period < self.ma_long_period, (
                "Short MA period must be less than long MA period"
            )

            logger.info("Configuration validation passed")
            return True

        except AssertionError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            return False
