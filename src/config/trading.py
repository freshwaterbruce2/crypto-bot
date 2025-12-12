"""Trading configuration manager."""

from __future__ import annotations

from typing import Any


class TradingConfigManager:
    """Manage trading parameters derived from the core configuration."""

    def __init__(self, core_config: dict[str, Any]):
        self.core_config = core_config
        self.trading_config = self._build_trading_config()

    def _build_trading_config(self) -> dict[str, Any]:
        base_pairs = self.core_config.get("trading_pairs", [])
        position_size = float(self.core_config.get("position_size_usdt", 2.0))
        max_position_pct = float(self.core_config.get("max_position_pct", 0.8))

        return {
            "trading_pairs": base_pairs,
            "position_size_usdt": position_size,
            "max_position_pct": max_position_pct,
            "take_profit_percent": 0.002,
            "stop_loss_percent": 0.005,
            "use_fee_free": self.core_config.get("environment", "production") != "sandbox",
        }

    def get_all_settings(self) -> dict[str, Any]:
        """Return the trading configuration dictionary."""
        return self.trading_config
