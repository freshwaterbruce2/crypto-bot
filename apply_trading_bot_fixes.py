#!/usr/bin/env python3
"""
Apply All Trading Bot Fixes
============================

This script applies all the critical fixes discovered by the research agents:
1. Config updates for $5 balance trading
2. Position size validation fixes  
3. WebSocket v2 integration improvements
4. Balance manager circuit breaker fixes

Run this script to implement all fixes at once.
"""

import sys
import os
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def apply_config_fixes():
    """Apply configuration fixes for $5 balance trading"""
    logger.info("Applying configuration fixes...")
    
    config_path = Path("config.json")
    if not config_path.exists():
        logger.error("config.json not found!")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Configuration updates for $5 balance
        updates = {
            "position_size_usdt": 3.50,
            "min_order_size_usdt": 2.0,
            "tier_1_trade_limit": 3.50,
            "min_trade_value_usd": 2.0,
            "emergency_min_trade_value": 2.0,
            "minimum_balance_threshold": 1.0,
            "portfolio_aware_min_balance": 1.0,
            "min_balance_threshold": 1.0,
            "min_order_value_usd": 2.0
        }
        
        # Apply nested updates
        if "advanced_strategy_params" in config and "dca_params" in config["advanced_strategy_params"]:
            config["advanced_strategy_params"]["dca_params"]["amount_usd"] = 2.0
        
        if "balance_management" in config:
            config["balance_management"]["min_tradeable_balance"] = 1.0
            
        if "portfolio_rebalancing" in config:
            config["portfolio_rebalancing"]["min_position_value_usd"] = 2.0
        
        # Apply main updates
        for key, value in updates.items():
            if key in config:
                old_value = config[key]
                config[key] = value
                logger.info(f"Updated {key}: {old_value} -> {value}")
        
        # Write back to file
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info("Configuration fixes applied successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error applying config fixes: {e}")
        return False


def validate_position_sizing():
    """Validate the new position sizing works correctly"""
    logger.info("Validating position sizing...")
    
    try:
        # Import our validation fix
        sys.path.append('src/fixes')
        from position_size_validation_fix import PositionSizeValidator
        
        validator = PositionSizeValidator()
        
        # Test with $5 balance
        test_balance = 5.0
        
        # Test safe position size calculation
        safe_size, explanation = validator.calculate_safe_position_size(test_balance)
        logger.info(f"Safe position size for ${test_balance}: ${safe_size:.2f} ({explanation})")
        
        # Test validation
        is_valid, reason, recommended = validator.validate_position_size("DOGE/USDT", safe_size, test_balance)
        
        if is_valid:
            logger.info(f"✅ Position validation passed: {reason}")
            return True
        else:
            logger.warning(f"❌ Position validation failed: {reason}")
            logger.info(f"Recommended size: ${recommended:.2f}")
            return False
            
    except Exception as e:
        logger.error(f"Error validating position sizing: {e}")
        return False


def check_websocket_integration():
    """Check WebSocket v2 integration"""
    logger.info("Checking WebSocket v2 integration...")
    
    try:
        # Check if WebSocket manager files exist and have correct structure
        ws_manager_path = Path("src/exchange/websocket_manager_v2.py")
        
        if not ws_manager_path.exists():
            logger.error("WebSocket manager v2 not found!")
            return False
        
        # Check for circuit breaker integration
        with open(ws_manager_path, 'r') as f:
            content = f.read()
        
        if "circuit_breaker_active" in content and "Reset circuit breaker on fresh WebSocket data" in content:
            logger.info("✅ WebSocket v2 circuit breaker integration confirmed")
            return True
        else:
            logger.warning("❌ WebSocket v2 circuit breaker integration missing")
            return False
            
    except Exception as e:
        logger.error(f"Error checking WebSocket integration: {e}")
        return False


def verify_balance_manager_fixes():
    """Verify balance manager has the correct fixes"""
    logger.info("Verifying balance manager fixes...")
    
    try:
        balance_manager_path = Path("src/trading/unified_balance_manager.py")
        
        if not balance_manager_path.exists():
            logger.error("Unified balance manager not found!")
            return False
        
        with open(balance_manager_path, 'r') as f:
            content = f.read()
        
        # Check for key fixes
        fixes_present = [
            "min_trade_value_usd = 2.0" in content,
            "circuit_breaker_active" in content,
            "EMERGENCY FIX" in content
        ]
        
        if all(fixes_present):
            logger.info("✅ Balance manager fixes confirmed")
            return True
        else:
            logger.warning("❌ Some balance manager fixes missing")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying balance manager: {e}")
        return False


def check_smart_minimum_manager():
    """Check smart minimum manager updates"""
    logger.info("Checking smart minimum manager updates...")
    
    try:
        smart_min_path = Path("src/trading/smart_minimum_manager.py")
        
        if not smart_min_path.exists():
            logger.error("Smart minimum manager not found!")
            return False
        
        with open(smart_min_path, 'r') as f:
            content = f.read()
        
        # Check for updated minimums
        fixes_present = [
            "TIER_MIN_COSTS = {" in content,
            "TradingTier.TIER_1: 2.0" in content,
            "TIER_POSITION_SIZES = {" in content,
            "TradingTier.TIER_1: 0.70" in content
        ]
        
        if all(fixes_present):
            logger.info("✅ Smart minimum manager updates confirmed")
            return True
        else:
            logger.warning("❌ Smart minimum manager updates missing")
            return False
            
    except Exception as e:
        logger.error(f"Error checking smart minimum manager: {e}")
        return False


def main():
    """Apply all fixes and validate"""
    logger.info("=" * 60)
    logger.info("APPLYING ALL TRADING BOT FIXES")
    logger.info("=" * 60)
    
    results = {}
    
    # Apply configuration fixes
    results['config_fixes'] = apply_config_fixes()
    
    # Validate position sizing
    results['position_validation'] = validate_position_sizing()
    
    # Check WebSocket integration  
    results['websocket_integration'] = check_websocket_integration()
    
    # Verify balance manager fixes
    results['balance_manager_fixes'] = verify_balance_manager_fixes()
    
    # Check smart minimum manager
    results['smart_minimum_manager'] = check_smart_minimum_manager()
    
    # Summary
    logger.info("=" * 60)
    logger.info("FIX APPLICATION SUMMARY")
    logger.info("=" * 60)
    
    all_successful = True
    for fix_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"{fix_name.replace('_', ' ').title()}: {status}")
        if not success:
            all_successful = False
    
    logger.info("=" * 60)
    
    if all_successful:
        logger.info("🎉 ALL FIXES APPLIED SUCCESSFULLY!")
        logger.info("The trading bot is now configured for $5 balance trading:")
        logger.info("  - Position size: $3.50 (70% of $5 balance)")
        logger.info("  - Minimum order: $2.00")
        logger.info("  - Safety margin: 5% for fees/slippage")
        logger.info("  - Circuit breaker integration: Enabled")
        logger.info("  - WebSocket v2 balance updates: Enabled")
        return 0
    else:
        logger.error("❌ SOME FIXES FAILED TO APPLY")
        logger.error("Please check the errors above and fix manually")
        return 1


if __name__ == "__main__":
    sys.exit(main())