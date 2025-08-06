"""
Learning Configuration Manager
Handles intelligent learning and adaptation system
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LearningConfigManager:
    """Learning configuration manager"""

    def __init__(self, core_config: dict[str, Any]):
        """Initialize learning config manager"""
        self.core_config = core_config
        self.learning_config = self._get_learning_defaults()

    def _get_learning_defaults(self) -> dict[str, Any]:
        """Get default learning configuration"""
        return {
            # Learning settings
            "enabled": True,
            "learning_rate": 0.1,
            "memory_retention_days": 30,

            # Adaptation
            "adaptive_position_sizing": True,
            "adaptive_profit_targets": True,
            "strategy_switching": False,

            # Data collection
            "collect_trade_data": True,
            "collect_market_data": True,
            "data_storage_path": self.core_config.get("data_directory", "data/"),

            # Analysis
            "analyze_patterns": True,
            "min_samples_for_learning": 10,
            "confidence_threshold": 0.7
        }

    def get_all_settings(self) -> dict[str, Any]:
        """Get all learning settings"""
        return self.learning_config

    def is_learning_enabled(self) -> bool:
        """Check if learning is enabled"""
        return self.learning_config["enabled"]
