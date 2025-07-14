"""
Configuration Validator
Handles configuration validation and auto-fixing
"""

import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Configuration validator"""
    
    def __init__(self):
        """Initialize config validator"""
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate complete configuration
        
        Returns:
            Tuple of (is_valid, errors, fixes_applied)
        """
        errors = []
        fixes = []
        
        # Validate core config
        if 'core' in config:
            core_errors, core_fixes = self._validate_core_config(config['core'])
            errors.extend(core_errors)
            fixes.extend(core_fixes)
        
        # Validate trading config
        if 'trading' in config:
            trading_errors, trading_fixes = self._validate_trading_config(config['trading'])
            errors.extend(trading_errors)
            fixes.extend(trading_fixes)
        
        # Validate risk config
        if 'risk' in config:
            risk_errors, risk_fixes = self._validate_risk_config(config['risk'])
            errors.extend(risk_errors)
            fixes.extend(risk_fixes)
        
        is_valid = len(errors) == 0
        return is_valid, errors, fixes
    
    def _validate_core_config(self, config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate core configuration"""
        errors = []
        fixes = []
        
        # Check position size
        if config.get('position_size_usdt', 0) < 1.0:
            errors.append("Position size must be at least 1.0 USDT")
        
        # Check API tier
        valid_tiers = ['starter', 'intermediate', 'pro']
        if config.get('kraken_api_tier') not in valid_tiers:
            fixes.append("Set kraken_api_tier to 'starter' (was invalid)")
            config['kraken_api_tier'] = 'starter'
        
        return errors, fixes
    
    def _validate_trading_config(self, config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate trading configuration"""
        errors = []
        fixes = []
        
        # Check trading pairs
        if not config.get('trading_pairs'):
            errors.append("No trading pairs configured")
        
        # Check profit target
        profit_target = config.get('profit_target_pct', 0)
        if profit_target <= 0 or profit_target > 10:
            errors.append("Profit target must be between 0.1% and 10%")
        
        return errors, fixes
    
    def _validate_risk_config(self, config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate risk configuration"""
        errors = []
        fixes = []
        
        # Check max position percentage
        max_pos = config.get('max_position_pct', 0)
        if max_pos <= 0 or max_pos > 1:
            errors.append("Max position percentage must be between 0.1 and 1.0")
        
        # Check daily loss limit
        max_loss = config.get('max_daily_loss', 0)
        if max_loss <= 0:
            errors.append("Max daily loss must be positive")
        
        return errors, fixes