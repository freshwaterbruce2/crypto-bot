"""Configuration validator with simple sanity checks."""

from __future__ import annotations

from typing import Any, Tuple


class ConfigValidator:
    """Validate composed configuration sections and propose fixes."""

    def validate_config(self, config: dict[str, Any]) -> Tuple[bool, list[str], list[str]]:
        errors: list[str] = []
        fixes: list[str] = []

        core = config.get("core", {})
        trading = config.get("trading", {})
        risk = config.get("risk", {})
        kraken = config.get("kraken", {})

        if not core.get("trading_pairs"):
            fixes.append("Added default trading pairs")
            trading_pairs = ["BTC/USDT", "ETH/USDT"]
            core = {**core, "trading_pairs": trading_pairs}

        if risk.get("max_daily_loss", 0) <= 0:
            errors.append("max_daily_loss must be positive")

        if trading.get("position_size_usdt", 0) <= 0:
            errors.append("position_size_usdt must be positive")

        if kraken.get("rate_limit_calls_per_second", 1) <= 0:
            fixes.append("Reset Kraken rate limit to default")
            kraken = {**kraken, "rate_limit_calls_per_second": 1}

        is_valid = not errors
        updated_config = {
            "core": core,
            "trading": trading,
            "risk": risk,
            "kraken": kraken,
            "learning": config.get("learning", {}),
        }
        config.update(updated_config)
        return is_valid, errors, fixes
