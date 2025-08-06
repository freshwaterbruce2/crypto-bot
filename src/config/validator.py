"""
Configuration Validator
Handles configuration validation and auto-fixing
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Configuration validator"""

    def __init__(self):
        """Initialize config validator"""
        self.default_config = {
            'core': {
                'position_size_usdt': 10.0,
                'kraken_api_tier': 'starter',
                'max_concurrent_positions': 5,
                'trading_mode': 'live'
            },
            'trading': {
                'trading_pairs': ['SHIBUSDT', 'DOGEUSDT'],
                'profit_target_pct': 0.5,
                'stop_loss_pct': 2.0,
                'time_in_force': 'GTC'
            },
            'risk': {
                'max_position_pct': 0.2,
                'max_daily_loss': 50.0,
                'max_drawdown': 0.1,
                'emergency_stop_loss': 0.05
            }
        }

        logger.info("Config validator initialized with default values")

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
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

    def _validate_core_config(self, config: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Validate core configuration"""
        errors = []
        fixes = []

        # Check position size
        if config.get('position_size_usdt', 0) < 0.1:
            errors.append("Position size must be at least 0.1 USDT")

        # Check API tier
        valid_tiers = ['starter', 'intermediate', 'pro']
        if config.get('kraken_api_tier') not in valid_tiers:
            fixes.append("Set kraken_api_tier to 'starter' (was invalid)")
            config['kraken_api_tier'] = 'starter'

        return errors, fixes

    def _validate_trading_config(self, config: dict[str, Any]) -> tuple[list[str], list[str]]:
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

    def _validate_risk_config(self, config: dict[str, Any]) -> tuple[list[str], list[str]]:
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

    def apply_defaults(self, config: dict[str, Any]) -> dict[str, Any]:
        """Apply default values to missing configuration keys"""
        complete_config = self.default_config.copy()

        # Deep merge provided config
        for section, values in config.items():
            if section in complete_config:
                if isinstance(values, dict):
                    complete_config[section].update(values)
                else:
                    complete_config[section] = values
            else:
                complete_config[section] = values

        return complete_config

    def sanitize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Sanitize configuration values to safe ranges"""
        sanitized = config.copy()

        # Ensure position size is reasonable
        if 'core' in sanitized and 'position_size_usdt' in sanitized['core']:
            pos_size = sanitized['core']['position_size_usdt']
            if pos_size < 0.1:
                sanitized['core']['position_size_usdt'] = 0.1
            elif pos_size > 1000:
                sanitized['core']['position_size_usdt'] = 1000

        # Ensure profit target is reasonable
        if 'trading' in sanitized and 'profit_target_pct' in sanitized['trading']:
            profit = sanitized['trading']['profit_target_pct']
            if profit < 0.1:
                sanitized['trading']['profit_target_pct'] = 0.1
            elif profit > 10:
                sanitized['trading']['profit_target_pct'] = 10

        return sanitized

    def get_validation_summary(self, config: dict[str, Any]) -> dict[str, Any]:
        """Get comprehensive validation summary"""
        is_valid, errors, fixes = self.validate_config(config)

        return {
            'is_valid': is_valid,
            'errors': errors,
            'fixes_applied': fixes,
            'config_sections': list(config.keys()),
            'missing_sections': [
                section for section in self.default_config.keys()
                if section not in config
            ],
            'validation_timestamp': 'validation_completed'
        }
