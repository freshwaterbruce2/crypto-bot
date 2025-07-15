#!/usr/bin/env python3
"""
Test WebSocket V2 Balance Streaming Implementation
=================================================

Test script to verify the WebSocket V2 balance streaming with proper format conversion.
Tests the critical 163.94 MANA balance detection and real-time streaming capabilities.
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockExchange:
    """Mock exchange for testing"""
    
    async def get_websocket_token(self):
        """Mock token for testing"""
        return {'token': 'test_token_12345'}


class MockBalanceManager:
    """Mock balance manager for testing"""
    
    def __init__(self):
        self.balances = {}
        self.websocket_balances = {}
        self.last_update = 0
        self.circuit_breaker_active = False
        self.consecutive_failures = 0
        self.backoff_multiplier = 1.0
        self.circuit_breaker_reset_time = 0
    
    async def process_websocket_update(self, balance_data):
        """Mock process method"""
        logger.info(f"Mock balance manager received {len(balance_data)} balance updates")
        for asset, balance_info in balance_data.items():
            logger.info(f"  {asset}: {balance_info}")


class MockManager:
    """Mock manager with balance manager"""
    
    def __init__(self):
        self.balance_manager = MockBalanceManager()


async def test_websocket_v2_balance_streaming():
    """Test the WebSocket V2 balance streaming implementation"""
    
    logger.info("=== Testing WebSocket V2 Balance Streaming ===")
    
    try:
        # Create WebSocket V2 manager with mock exchange
        mock_exchange = MockExchange()
        symbols = ['MANA/USDT', 'BTC/USDT', 'ETH/USDT']
        
        ws_manager = KrakenProWebSocketManager(
            exchange_client=mock_exchange,
            symbols=symbols,
            connection_id="test_ws_v2"
        )
        
        # Set up mock manager reference
        mock_manager = MockManager()
        ws_manager.set_manager(mock_manager)
        
        logger.info("1. Testing WebSocket V2 format conversion...")
        
        # Test format conversion with WebSocket V2 array format
        test_result = await ws_manager.test_balance_format_conversion()
        
        if test_result:
            logger.info("✓ Format conversion test PASSED")
        else:
            logger.error("✗ Format conversion test FAILED")
            return False
        
        logger.info("2. Testing MANA balance detection...")
        
        # Test specific MANA balance detection
        mana_balance = ws_manager.get_balance('MANA')
        if mana_balance and mana_balance.get('free') == 163.94:
            logger.info(f"✓ MANA balance detection PASSED: {mana_balance}")
        else:
            logger.error(f"✗ MANA balance detection FAILED: {mana_balance}")
            return False
        
        logger.info("3. Testing balance streaming status...")
        
        # Test balance streaming status
        status = ws_manager.get_balance_streaming_status()
        logger.info(f"Balance streaming status: {status}")
        
        # Verify status shows MANA is available
        if status['mana_balance_available'] and status['mana_balance_value'] == 163.94:
            logger.info("✓ Balance streaming status PASSED")
        else:
            logger.error("✗ Balance streaming status FAILED")
            return False
        
        logger.info("4. Testing integration with unified balance manager...")
        
        # Test integration with balance manager
        balance_manager = mock_manager.balance_manager
        if 'MANA' in balance_manager.balances:
            mana_data = balance_manager.balances['MANA']
            if mana_data.get('free') == 163.94:
                logger.info(f"✓ Balance manager integration PASSED: {mana_data}")
            else:
                logger.error(f"✗ Balance manager integration FAILED: {mana_data}")
                return False
        else:
            logger.error("✗ MANA not found in balance manager")
            return False
        
        logger.info("5. Testing different balance message formats...")
        
        # Test dict format (legacy)
        dict_balance_data = {
            'MANA': {'free': 100.0, 'used': 0, 'total': 100.0},
            'USDT': {'free': 50.0, 'used': 0, 'total': 50.0}
        }
        
        await ws_manager._handle_balance_message(dict_balance_data)
        
        # Verify dict format was processed
        mana_balance_after_dict = ws_manager.get_balance('MANA')
        if mana_balance_after_dict and mana_balance_after_dict.get('free') == 100.0:
            logger.info("✓ Dict format handling PASSED")
        else:
            logger.error(f"✗ Dict format handling FAILED: {mana_balance_after_dict}")
            return False
        
        logger.info("=== All Tests PASSED ===")
        logger.info("WebSocket V2 balance streaming implementation is working correctly!")
        logger.info("Key features verified:")
        logger.info("  - WebSocket V2 array format conversion: ✓")
        logger.info("  - MANA balance detection (163.94): ✓") 
        logger.info("  - Real-time balance manager integration: ✓")
        logger.info("  - Legacy dict format support: ✓")
        logger.info("  - Balance streaming status monitoring: ✓")
        
        return True
        
    except Exception as e:
        logger.error(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    
    logger.info("Starting WebSocket V2 Balance Streaming Tests...")
    
    success = await test_websocket_v2_balance_streaming()
    
    if success:
        logger.info("🎉 All tests completed successfully!")
        logger.info("The WebSocket V2 balance streaming implementation is ready for production use.")
        return 0
    else:
        logger.error("❌ Tests failed!")
        logger.error("Please review the implementation and fix any issues.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)