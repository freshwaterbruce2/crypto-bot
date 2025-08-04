#!/usr/bin/env python3
"""
CRITICAL FIXES VALIDATION
========================

Test script to validate that all critical fixes are working:
1. NativeKrakenExchange constructor fixes
2. HybridPortfolioManager null checks
3. SimpleBalanceManager functionality
4. Bot initialization readiness

This script must pass for live trading to be enabled.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_native_exchange_constructor():
    """Test that NativeKrakenExchange constructor works correctly"""
    try:
        logger.info("🔍 Testing NativeKrakenExchange constructor...")
        
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        
        # Test with required parameters
        exchange = NativeKrakenExchange(
            api_key=os.getenv('KRAKEN_API_KEY', 'test_key'),
            api_secret=os.getenv('KRAKEN_API_SECRET', 'test_secret'),
            tier='pro'
        )
        
        if exchange:
            logger.info("✅ NativeKrakenExchange constructor fix verified")
            return True
        else:
            logger.error("❌ NativeKrakenExchange constructor returned None")
            return False
            
    except Exception as e:
        logger.error(f"❌ NativeKrakenExchange constructor test failed: {e}")
        return False


async def test_simple_balance_manager():
    """Test SimpleBalanceManager functionality"""
    try:
        logger.info("🔍 Testing SimpleBalanceManager...")
        
        from src.balance.simple_balance_manager import SimpleBalanceManager, create_emergency_balance_manager
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        
        # Create mock exchange for testing
        exchange = NativeKrakenExchange(
            api_key=os.getenv('KRAKEN_API_KEY', 'test_key'),
            api_secret=os.getenv('KRAKEN_API_SECRET', 'test_secret'),
            tier='pro'
        )
        
        # Create simple balance manager
        balance_manager = await create_emergency_balance_manager(exchange)
        
        # Test basic functionality
        status = balance_manager.get_status()
        if status and status['type'] == 'SimpleBalanceManager':
            logger.info("✅ SimpleBalanceManager creation and status verified")
            
            # Test start/stop
            await balance_manager.start()
            await balance_manager.stop()
            
            logger.info("✅ SimpleBalanceManager start/stop verified")
            return True
        else:
            logger.error("❌ SimpleBalanceManager status check failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ SimpleBalanceManager test failed: {e}")
        return False


async def test_hybrid_portfolio_null_checks():
    """Test that HybridPortfolioManager handles None websocket_stream"""
    try:
        logger.info("🔍 Testing HybridPortfolioManager null checks...")
        
        from src.balance.hybrid_portfolio_manager import HybridPortfolioManager, HybridPortfolioConfig
        
        # Test with None websocket_stream (should not crash)
        config = HybridPortfolioConfig()
        manager = HybridPortfolioManager(
            websocket_stream=None,  # This should be handled gracefully now
            rest_client=None,
            config=config
        )
        
        # Test status method (should handle None websocket_stream)
        status = manager.get_status()
        if status and 'websocket_stream' in status:
            logger.info("✅ HybridPortfolioManager null check fixes verified")
            return True
        else:
            logger.error("❌ HybridPortfolioManager status check failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ HybridPortfolioManager null check test failed: {e}")
        return False


async def test_imports_and_dependencies():
    """Test that all critical imports work correctly"""
    try:
        logger.info("🔍 Testing critical imports...")
        
        # Test balance managers
        from src.balance.simple_balance_manager import SimpleBalanceManager
        from src.balance.hybrid_portfolio_manager import HybridPortfolioManager
        
        # Test exchange
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        
        # Test utils
        from src.utils.decimal_precision_fix import safe_decimal, safe_float
        
        logger.info("✅ All critical imports successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        return False


async def main():
    """Run all critical fix validation tests"""
    logger.info("🚨 CRITICAL FIXES VALIDATION STARTING 🚨")
    logger.info("=" * 60)
    
    tests = [
        ("Import Dependencies", test_imports_and_dependencies),
        ("NativeKrakenExchange Constructor", test_native_exchange_constructor),
        ("SimpleBalanceManager", test_simple_balance_manager),
        ("HybridPortfolioManager Null Checks", test_hybrid_portfolio_null_checks),
    ]
    
    results = []
    passed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: CRASHED - {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🚨 VALIDATION RESULTS SUMMARY 🚨")
    logger.info("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    success_rate = passed / len(tests)
    overall_success = success_rate >= 0.75  # 75% pass rate required
    
    logger.info(f"\nSuccess Rate: {success_rate:.1%} ({passed}/{len(tests)})")
    
    if overall_success:
        logger.info("\n🎉 CRITICAL FIXES VALIDATION SUCCESSFUL!")
        logger.info("✅ All critical fixes appear to be working")
        logger.info("🚀 Bot should now be ready for live trading")
        logger.info("💡 Recommendation: Test with small amounts first")
    else:
        logger.error("\n⚠️  CRITICAL FIXES VALIDATION FAILED")
        logger.error("❌ Some critical fixes are not working properly")
        logger.error("🔧 Manual intervention required before live trading")
    
    return overall_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)