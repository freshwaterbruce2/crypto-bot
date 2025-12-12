"""Risk configuration manager."""

from __future__ import annotations

from typing import Any


class RiskConfigManager:
    """Manage risk-related parameters such as limits and buffers."""

    def __init__(self, core_config: dict[str, Any]):
        self.core_config = core_config
        self.risk_config = self._build_risk_config()

    def _build_risk_config(self) -> dict[str, Any]:
        return {
            "max_daily_loss": float(self.core_config.get("max_daily_loss", 50.0)),
            "min_order_size_usdt": float(self.core_config.get("min_order_size_usdt", 1.0)),
            "circuit_breaker_threshold": 0.02,
            "cooldown_minutes": 5,
        }

    def get_all_settings(self) -> dict[str, Any]:
        """Return the risk configuration dictionary."""
        return self.risk_config
