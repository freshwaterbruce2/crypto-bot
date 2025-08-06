"""
Kraken Configuration Manager
Handles Kraken API compliance and rate limiting
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class KrakenConfigManager:
    """Kraken configuration manager"""

    def __init__(self, core_config: Dict[str, Any]):
        """Initialize Kraken config manager"""
        self.core_config = core_config
        self.kraken_config = self._get_kraken_defaults()

    def _get_kraken_defaults(self) -> Dict[str, Any]:
        """Get default Kraken configuration with Pro account optimizations"""
        api_tier = self.core_config.get("kraken_api_tier", "starter")
        is_pro_account = api_tier == "pro"

        # Base configuration
        config = {
            # API settings
            "api_tier": api_tier,
            "sandbox": False,
            "timeout": 30,

            # Rate limiting (Pro optimized)
            "rate_limit_calls_per_second": 3.75 if is_pro_account else 1,
            "rate_limit_burst": 180 if is_pro_account else 60,
            "rate_limit_window_seconds": 60,

            # Order settings (Pro optimized)
            "minimum_order_size": 0.5 if is_pro_account else 1.0,
            "order_type_preference": "limit" if is_pro_account else "market",
            "validate_only": False,

            # WebSocket (Pro enhanced)
            "websocket_enabled": True,
            "websocket_timeout": 10,
            "auto_reconnect": True,
            "websocket_priority": is_pro_account,  # Pro accounts get priority
        }

        # Pro account specific features
        if is_pro_account:
            config.update({
                # Fee-free trading features
                "fee_free_trading": True,
                "micro_scalping_enabled": True,
                "ioc_orders_enabled": True,
                "advanced_order_types": True,

                # Enhanced rate limits
                "rate_limit_threshold": 180,
                "rate_decay_per_second": 3.75,
                "burst_allowance": 1.2,

                # Pro optimizations
                "capital_velocity_mode": True,
                "compound_growth_optimization": True,
                "rapid_rebalancing_enabled": True,
                "max_trades_per_minute": 30,

                # Performance tracking
                "track_fee_savings": True,
                "monitor_capital_velocity": True,
                "calculate_compound_growth": True,
            })

            from src.utils.custom_logging import logger
            logger.info("[KRAKEN_CONFIG] Pro account detected - Enhanced features enabled:")
            logger.info("  - Fee-free trading: ENABLED")
            logger.info("  - Rate limit: 180 calls/counter (3.75/s decay)")
            logger.info("  - Micro-scalping: ENABLED")
            logger.info("  - IOC orders: ENABLED")
            logger.info("  - Max trades/minute: 30")

        return config

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all Kraken settings"""
        return self.kraken_config

    def get_api_tier(self) -> str:
        """Get API tier"""
        return self.kraken_config["api_tier"]

    def get_minimum_order_size(self) -> float:
        """Get minimum order size"""
        return self.kraken_config["minimum_order_size"]
