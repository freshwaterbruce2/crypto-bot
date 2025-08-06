"""
Risk Configuration Manager
Handles risk management and circuit breaker settings
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class RiskConfigManager:
    """Risk configuration manager"""

    def __init__(self, core_config: Dict[str, Any]):
        """Initialize risk config manager"""
        self.core_config = core_config
        self.risk_config = self._get_risk_defaults()

    def _get_risk_defaults(self) -> Dict[str, Any]:
        """Get default risk configuration"""
        return {
            # Position risk
            "max_position_pct": self.core_config.get("max_position_pct", 0.8),
            "max_daily_loss": self.core_config.get("max_daily_loss", 50.0),
            "max_open_positions": 5,

            # Stop losses
            "use_stop_loss": True,
            "stop_loss_pct": 0.3,
            "trailing_stop": False,

            # Circuit breakers
            "circuit_breaker_enabled": True,
            "max_consecutive_losses": 3,
            "cooldown_period_minutes": 15,

            # Portfolio risk
            "max_portfolio_risk_pct": 10.0,
            "risk_per_trade_pct": 2.0
        }

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all risk settings"""
        return self.risk_config

    def get_max_position_pct(self) -> float:
        """Get maximum position percentage"""
        return self.risk_config["max_position_pct"]

    def get_max_daily_loss(self) -> float:
        """Get maximum daily loss"""
        return self.risk_config["max_daily_loss"]
