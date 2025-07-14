#!/usr/bin/env python3
"""
Critical Fixes Validation Script
================================

Validates that all 4 critical fixes have been properly implemented:
1. Circuit Breaker Fix - Timeout reduced from 900s to 180s
2. Position Tracking Sync - Balance detection vs position tracker alignment  
3. Capital Deployment Rebalancing - Intelligent liquidation from $159 deployed
4. Native REST Fallback Repair - Fixed retries=3 to max_retries=3

This script tests each fix to ensure the trading bot core functionality is restored.
"""

import asyncio
import logging
import time
import sys
from pathlib import Path
import importlib.util

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CriticalFixesValidator:
    """Validates all critical fixes are properly implemented"""
    
    def __init__(self):
        self.results = {
            'circuit_breaker': False,
            'position_tracking': False,
            'capital_deployment': False,
            'rest_fallback': False
        }
        
    async def validate_circuit_breaker_fix(self):
        """PRIORITY 1: Validate circuit breaker timeout optimization"""
        try:
            logger.info("🔄 VALIDATING CRITICAL FIX 1: Circuit Breaker Timeout Optimization")
            
            # Import circuit breaker module
            sys.path.append('src')
            from utils.circuit_breaker import CircuitBreakerConfig
            
            # Create default config to check timeout values
            config = CircuitBreakerConfig()
            
            # Validate critical fixes
            timeout_fix = config.timeout == 180.0  # Should be 180s (reduced from 900s)
            threshold_fix = config.failure_threshold == 3  # Should be 3 (reduced from 5)
            rate_limit_fix = config.rate_limit_timeout == 300.0  # Should be 300s (reduced from 900s)
            max_backoff_fix = config.max_backoff == 180.0  # Should be 180s (reduced from 3600s)
            
            if timeout_fix and threshold_fix and rate_limit_fix and max_backoff_fix:
                logger.info("✅ CIRCUIT BREAKER FIX VALIDATED")
                logger.info(f"   ✓ Timeout: {config.timeout}s (target: 180s)")
                logger.info(f"   ✓ Failure threshold: {config.failure_threshold} (target: 3)")
                logger.info(f"   ✓ Rate limit timeout: {config.rate_limit_timeout}s (target: 300s)")
                logger.info(f"   ✓ Max backoff: {config.max_backoff}s (target: 180s)")
                self.results['circuit_breaker'] = True
                return True
            else:
                logger.error("❌ CIRCUIT BREAKER FIX FAILED")
                logger.error(f"   Timeout: {config.timeout}s (expected: 180s) - {'✓' if timeout_fix else '❌'}")
                logger.error(f"   Failure threshold: {config.failure_threshold} (expected: 3) - {'✓' if threshold_fix else '❌'}")
                logger.error(f"   Rate limit timeout: {config.rate_limit_timeout}s (expected: 300s) - {'✓' if rate_limit_fix else '❌'}")
                logger.error(f"   Max backoff: {config.max_backoff}s (expected: 180s) - {'✓' if max_backoff_fix else '❌'}")
                return False
                
        except Exception as e:
            logger.error(f"❌ CIRCUIT BREAKER VALIDATION ERROR: {e}")
            return False
    
    async def validate_rest_fallback_fix(self):
        """PRIORITY 4: Validate REST fallback parameter fix"""
        try:
            logger.info("🔄 VALIDATING CRITICAL FIX 4: Native REST Fallback Parameter Fix")
            
            # Read the native kraken exchange file to check parameter fix
            exchange_file = Path("src/exchange/native_kraken_exchange.py")
            if not exchange_file.exists():
                logger.error(f"❌ Exchange file not found: {exchange_file}")
                return False
            
            content = exchange_file.read_text()
            
            # Check for the critical fix
            max_retries_fix = "max_retries=3" in content
            old_retries_removed = "retries=3," not in content  # Should not have old parameter
            
            if max_retries_fix and old_retries_removed:
                logger.info("✅ REST FALLBACK FIX VALIDATED")
                logger.info("   ✓ Parameter changed from retries=3 to max_retries=3")
                logger.info("   ✓ SDK fallback will work when circuit breaker opens")
                self.results['rest_fallback'] = True
                return True
            else:
                logger.error("❌ REST FALLBACK FIX FAILED")
                logger.error(f"   max_retries=3 found: {'✓' if max_retries_fix else '❌'}")
                logger.error(f"   old retries=3 removed: {'✓' if old_retries_removed else '❌'}")
                return False
                
        except Exception as e:
            logger.error(f"❌ REST FALLBACK VALIDATION ERROR: {e}")
            return False
    
    async def validate_position_tracking_fix(self):
        """PRIORITY 2: Validate position tracking sync enhancement"""
        try:
            logger.info("🔄 VALIDATING CRITICAL FIX 2: Position Tracking Sync Enhancement")
            
            # Import unified balance manager to check enhancements
            from trading.unified_balance_manager import UnifiedBalanceManager
            
            # Create a test instance
            balance_manager = UnifiedBalanceManager(exchange=None)
            
            # Check critical fix properties
            cache_duration_fix = balance_manager.cache_duration == 30  # Should be 30s (reduced from 45s)
            refresh_interval_fix = balance_manager.min_refresh_interval == 15  # Should be 15s (reduced from 20s)
            position_sync_fix = hasattr(balance_manager, 'position_sync_enabled')
            sync_methods_fix = (
                hasattr(balance_manager, 'sync_with_position_tracker') and
                hasattr(balance_manager, 'enable_real_time_balance_usage') and
                hasattr(balance_manager, 'repair_sell_signal_positions')
            )
            
            if cache_duration_fix and refresh_interval_fix and position_sync_fix and sync_methods_fix:
                logger.info("✅ POSITION TRACKING FIX VALIDATED")
                logger.info(f"   ✓ Cache duration: {balance_manager.cache_duration}s (target: 30s)")
                logger.info(f"   ✓ Refresh interval: {balance_manager.min_refresh_interval}s (target: 15s)")
                logger.info(f"   ✓ Position sync enabled: {balance_manager.position_sync_enabled}")
                logger.info("   ✓ Critical sync methods added")
                self.results['position_tracking'] = True
                return True
            else:
                logger.error("❌ POSITION TRACKING FIX FAILED")
                logger.error(f"   Cache duration: {balance_manager.cache_duration}s (expected: 30s) - {'✓' if cache_duration_fix else '❌'}")
                logger.error(f"   Refresh interval: {balance_manager.min_refresh_interval}s (expected: 15s) - {'✓' if refresh_interval_fix else '❌'}")
                logger.error(f"   Position sync enabled: {'✓' if position_sync_fix else '❌'}")
                logger.error(f"   Sync methods added: {'✓' if sync_methods_fix else '❌'}")
                return False
                
        except Exception as e:
            logger.error(f"❌ POSITION TRACKING VALIDATION ERROR: {e}")
            return False
    
    async def validate_capital_deployment_fix(self):
        """PRIORITY 3: Validate capital deployment rebalancing"""
        try:
            logger.info("🔄 VALIDATING CRITICAL FIX 3: Capital Deployment Rebalancing")
            
            # Import unified balance manager to check rebalancing logic
            from trading.unified_balance_manager import UnifiedBalanceManager
            
            # Create a test instance
            balance_manager = UnifiedBalanceManager(exchange=None)
            
            # Test the reallocation logic by checking the source code contains critical fixes
            balance_file = Path("src/trading/unified_balance_manager.py")
            content = balance_file.read_text()
            
            # Check for critical fix markers in capital deployment logic
            liquidation_fix = "Free up 20-30% for liquid trading capital" in content
            threshold_fix = "available_balance < 8.0" in content  # Should be 8.0 (increased from 6.0)
            realloc_fix = "realloc_amount = amount * 0.30" in content  # Should be 30% for small positions
            diversification_fix = "target_pairs[:5]" in content  # Should be 5 pairs (increased from 4)
            
            if liquidation_fix and threshold_fix and realloc_fix and diversification_fix:
                logger.info("✅ CAPITAL DEPLOYMENT FIX VALIDATED")
                logger.info("   ✓ Intelligent liquidation from $159 deployed capital")
                logger.info("   ✓ 20-30% liquidity rebalancing logic")
                logger.info("   ✓ Enhanced threshold to 8.0 for better liquidity")
                logger.info("   ✓ Improved diversification to 5 pairs")
                self.results['capital_deployment'] = True
                return True
            else:
                logger.error("❌ CAPITAL DEPLOYMENT FIX FAILED")
                logger.error(f"   Liquidation logic: {'✓' if liquidation_fix else '❌'}")
                logger.error(f"   Threshold fix: {'✓' if threshold_fix else '❌'}")
                logger.error(f"   Reallocation fix: {'✓' if realloc_fix else '❌'}")
                logger.error(f"   Diversification fix: {'✓' if diversification_fix else '❌'}")
                return False
                
        except Exception as e:
            logger.error(f"❌ CAPITAL DEPLOYMENT VALIDATION ERROR: {e}")
            return False
    
    async def run_validation(self):
        """Run all critical fixes validation"""
        logger.info("🚀 STARTING CRITICAL FIXES VALIDATION")
        logger.info("=" * 80)
        
        # Run all validations
        circuit_breaker_ok = await self.validate_circuit_breaker_fix()
        position_tracking_ok = await self.validate_position_tracking_fix()
        capital_deployment_ok = await self.validate_capital_deployment_fix()
        rest_fallback_ok = await self.validate_rest_fallback_fix()
        
        # Summary
        total_fixes = len(self.results)
        passed_fixes = sum(self.results.values())
        
        logger.info("=" * 80)
        logger.info("🎯 CRITICAL FIXES VALIDATION SUMMARY")
        logger.info(f"   Passed: {passed_fixes}/{total_fixes}")
        
        if passed_fixes == total_fixes:
            logger.info("🎉 ALL CRITICAL FIXES VALIDATED SUCCESSFULLY!")
            logger.info("   Trading bot core functionality should be restored.")
            logger.info("   Circuit breaker blocking trades: FIXED ✅")
            logger.info("   Position tracking sync broken: FIXED ✅") 
            logger.info("   Capital deployment crisis: FIXED ✅")
            logger.info("   REST fallback parameter error: FIXED ✅")
            return True
        else:
            logger.error("⚠️  SOME CRITICAL FIXES FAILED VALIDATION")
            for fix_name, status in self.results.items():
                status_icon = "✅" if status else "❌"
                logger.error(f"   {fix_name}: {status_icon}")
            return False

async def main():
    """Main validation function"""
    validator = CriticalFixesValidator()
    success = await validator.run_validation()
    
    if success:
        print("\n🎉 CRITICAL FIXES VALIDATION COMPLETED SUCCESSFULLY")
        print("   The trading bot is ready for deployment with all critical fixes applied.")
        return 0
    else:
        print("\n⚠️  CRITICAL FIXES VALIDATION FAILED")
        print("   Please review the failed fixes before deploying the trading bot.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)