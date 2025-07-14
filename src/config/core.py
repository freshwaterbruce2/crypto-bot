"""
Core Configuration Manager
Handles base configuration loading and validation
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CoreConfigManager:
    """Core configuration manager for base settings"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize core config manager"""
        self.config_path = config_path
        self.config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file with fallback defaults"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"[CORE_CONFIG] Loaded configuration from {self.config_path}")
                return config
            else:
                logger.warning(f"[CORE_CONFIG] Config file {self.config_path} not found, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"[CORE_CONFIG] Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            # Core settings
            "position_size_usdt": 2.0,
            "tier_1_trade_limit": 3.5,
            "kraken_api_tier": "starter",
            
            # Risk management
            "max_position_pct": 0.8,
            "max_daily_loss": 50.0,
            "min_order_size_usdt": 1.0,
            
            # Trading pairs
            "trading_pairs": [
                "AI16Z/USDT", "ALGO/USDT", "ADA/USDT", "AVAX/USDT",
                "DOGE/USDT", "DOT/USDT", "LINK/USDT", "MATIC/USDT",
                "XRP/USDT", "ATOM/USDT", "APE/USDT", "CRO/USDT"
            ],
            
            # Environment
            "environment": "production",
            "logging_level": "INFO",
            "data_directory": "D:/trading_bot_data"
        }
    
    def get_core_config(self) -> Dict[str, Any]:
        """Get core configuration"""
        return self.config_data
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all core settings"""
        return self.config_data
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get specific setting with fallback"""
        return self.config_data.get(key, default)
    
    def update_setting(self, key: str, value: Any) -> None:
        """Update specific setting"""
        self.config_data[key] = value
        self._save_config()
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
            logger.info(f"[CORE_CONFIG] Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"[CORE_CONFIG] Error saving config: {e}")