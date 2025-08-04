#!/usr/bin/env python3
"""
Test script for Balance Manager V2 fixes
==========================================

Tests the initialization improvements and error handling
to ensure the bot can start even when components are missing.

The fixes include:
1. Enhanced error handling in initialization
2. Graceful fallback to minimal mode
3. Better logging and diagnostics
4. Null-safe operations
"""

import asyncio
import logging
import sys
import traceback
from typing import Optional, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from balance.balance_manager_v2 import BalanceManagerV2, BalanceManagerV2Config, create_balance_manager_v2
except ImportError as e:
    logger.error(f"Failed to import Balance Manager V2: {e}")
    logger.error(f"Current working directory: {os.getcwd()}")
    logger.error(f"Python path: {sys.path}")
    sys.exit(1)


class MockWebSocketClient:
    """Mock WebSocket client for testing"""
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.is_connected = False
        self.last_message_time = 0
        
    async def connect(self):
        if self.should_fail:
            raise Exception("Mock WebSocket connection failed")
        self.is_connected = True
        return True
        
    def set_callback(self, event_type: str, callback):
        pass
        
    def set_manager(self, manager):
        pass


class MockExchangeClient:
    """Mock exchange client for testing"""
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        
    async def get_account_balance(self):
        if self.should_fail:
            raise Exception("Mock REST API failed")
        return {
            'result': {
                'USDT': '100.50',
                'BTC': '0.001'
            }
        }
        
    async def get_websocket_token(self):
        if self.should_fail:
            raise Exception("Mock token generation failed")
        return {'token': 'mock_token_12345'}


async def test_scenario(name: str, websocket_client, exchange_client) -> bool:
    """Test a specific initialization scenario"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing: {name}")
    logger.info(f"{'='*60}")
    
    try:
        config = BalanceManagerV2Config()
        manager = BalanceManagerV2(websocket_client, exchange_client, config)
        
        # Test initialization
        result = await manager.initialize()
        logger.info(f"Initialization result: {result}")
        
        if result:
            # Test basic operations
            status = manager.get_status()
            logger.info(f"Status: initialized={status['initialized']}, mode={status['mode']}")
            
            # Test balance operations
            usdt_balance = await manager.get_balance('USDT')
            logger.info(f"USDT balance: {usdt_balance}")
            
            all_balances = await manager.get_all_balances()
            logger.info(f"All balances count: {len(all_balances)}")
            
            usdt_total = await manager.get_usdt_total()
            logger.info(f"USDT total: {usdt_total}")
            
            # Test force refresh
            refresh_result = await manager.force_refresh()
            logger.info(f"Force refresh result: {refresh_result}")
            
            # Shutdown
            await manager.shutdown()
            logger.info("Shutdown completed")
            
        return result
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        traceback.print_exc()
        return False


async def test_factory_function() -> bool:
    """Test the factory function that was failing"""
    logger.info(f"\n{'='*60}")
    logger.info("Testing: Factory Function (create_balance_manager_v2)")
    logger.info(f"{'='*60}")
    
    try:
        # Test with working components
        websocket_client = MockWebSocketClient(should_fail=False)
        exchange_client = MockExchangeClient(should_fail=False)
        config = BalanceManagerV2Config()
        
        manager = await create_balance_manager_v2(websocket_client, exchange_client, config)
        logger.info("Factory function succeeded with working components")
        
        status = manager.get_status()
        logger.info(f"Factory created manager: mode={status['mode']}, initialized={status['initialized']}")
        
        await manager.shutdown()
        
        # Test with failing components (should still work in minimal mode)
        websocket_client = MockWebSocketClient(should_fail=True)
        exchange_client = MockExchangeClient(should_fail=True)
        
        manager = await create_balance_manager_v2(websocket_client, exchange_client, config)
        logger.info("Factory function succeeded even with failing components")
        
        status = manager.get_status()
        logger.info(f"Factory created manager: mode={status['mode']}, initialized={status['initialized']}")
        
        await manager.shutdown()
        
        return True
        
    except Exception as e:
        logger.error(f"Factory function test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    logger.info("Starting Balance Manager V2 fix validation tests...")
    
    test_results = []
    
    # Test 1: Both WebSocket and REST working
    result1 = await test_scenario(
        "Full functionality (WebSocket + REST)",
        MockWebSocketClient(should_fail=False),
        MockExchangeClient(should_fail=False)
    )
    test_results.append(("Full functionality", result1))
    
    # Test 2: WebSocket fails, REST works
    result2 = await test_scenario(
        "REST fallback (WebSocket fails, REST works)",
        MockWebSocketClient(should_fail=True),
        MockExchangeClient(should_fail=False)
    )
    test_results.append(("REST fallback", result2))
    
    # Test 3: No WebSocket, REST works
    result3 = await test_scenario(
        "REST only mode (No WebSocket client)",
        None,
        MockExchangeClient(should_fail=False)
    )
    test_results.append(("REST only", result3))
    
    # Test 4: Both fail - should use minimal mode
    result4 = await test_scenario(
        "Minimal mode (Both WebSocket and REST fail)",
        MockWebSocketClient(should_fail=True),
        MockExchangeClient(should_fail=True)
    )
    test_results.append(("Minimal mode", result4))
    
    # Test 5: No clients at all
    result5 = await test_scenario(
        "No clients (Minimal mode with None clients)",
        None,
        None
    )
    test_results.append(("No clients", result5))
    
    # Test 6: Factory function
    result6 = await test_factory_function()
    test_results.append(("Factory function", result6))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST RESULTS SUMMARY")
    logger.info(f"{'='*60}")
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\nTotal: {len(test_results)} tests")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    
    if failed == 0:
        logger.info("\n✅ ALL TESTS PASSED! Balance Manager V2 initialization is fixed.")
        return True
    else:
        logger.error(f"\n❌ {failed} tests failed. Some issues remain.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        traceback.print_exc()
        sys.exit(1)