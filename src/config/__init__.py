"""
Kraken-Compliant Intelligent Configuration Manager - Modular Architecture

This package provides a chunked configuration management system optimized for 
profitable micro-scalping on Kraken exchange with fee-free trading advantage.

Architecture:
- core.py: Base configuration loading and validation
- trading.py: Trading-specific parameters and optimization
- risk.py: Risk management and circuit breaker settings  
- kraken.py: Kraken API compliance and rate limiting
- learning.py: Intelligent learning and adaptation system
- validator.py: Configuration validation and auto-fixing

Usage:
    from src.config import ConfigManager
    config_manager = ConfigManager()
    config = config_manager.get_complete_config()
"""

from .core import CoreConfigManager
from .trading import TradingConfigManager  
from .risk import RiskConfigManager
from .kraken import KrakenConfigManager
from .learning import LearningConfigManager
from .validator import ConfigValidator

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Unified configuration manager that coordinates all config modules
    """
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize unified config manager"""
        # Initialize core config first
        self.core_manager = CoreConfigManager(config_path)
        core_config = self.core_manager.get_core_config()
        
        # Initialize specialized managers
        self.trading_manager = TradingConfigManager(core_config)
        self.risk_manager = RiskConfigManager(core_config)
        self.kraken_manager = KrakenConfigManager(core_config)
        self.learning_manager = LearningConfigManager(core_config)
        self.validator = ConfigValidator()
        
        # Validate complete configuration
        self._validate_config()
    
    def get_complete_config(self) -> Dict[str, Any]:
        """Get complete configuration from all managers"""
        return {
            'core': self.core_manager.get_all_settings(),
            'trading': self.trading_manager.get_all_settings(),
            'risk': self.risk_manager.get_all_settings(),
            'kraken': self.kraken_manager.get_all_settings(),
            'learning': self.learning_manager.get_all_settings()
        }
    
    def _validate_config(self):
        """Validate complete configuration"""
        complete_config = self.get_complete_config()
        is_valid, errors, fixes = self.validator.validate_config(complete_config)
        
        if fixes:
            logger.info(f"Applied {len(fixes)} configuration fixes")
            for fix in fixes:
                logger.info(f"  - {fix}")
        
        if errors:
            logger.warning(f"Found {len(errors)} configuration errors")
            for error in errors:
                logger.warning(f"  - {error}")


# Convenience function for backward compatibility
def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """Load complete configuration (backward compatibility)"""
    config_manager = ConfigManager(config_path)
    return config_manager.get_complete_config()


__all__ = [
    'ConfigManager',
    'CoreConfigManager', 
    'TradingConfigManager',
    'RiskConfigManager',
    'KrakenConfigManager', 
    'LearningConfigManager',
    'ConfigValidator',
    'load_config'
]
