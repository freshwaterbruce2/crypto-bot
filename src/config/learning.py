"""Learning configuration manager."""

from __future__ import annotations

from typing import Any


class LearningConfigManager:
    """Handle adaptive learning and model tuning configuration."""

    def __init__(self, core_config: dict[str, Any]):
        self.core_config = core_config
        self.learning_config = self._build_learning_config()

    def _build_learning_config(self) -> dict[str, Any]:
        return {
            "adaptive_enabled": True,
            "lookback_window": 100,
            "confidence_threshold": 0.6,
            "max_models": 3,
            "data_directory": self.core_config.get("data_directory", "D:/trading_bot_data"),
        }

    def get_all_settings(self) -> dict[str, Any]:
        """Return the learning configuration dictionary."""
        return self.learning_config
