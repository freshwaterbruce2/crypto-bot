#!/usr/bin/env python3
"""
Test WebSocket V2 Message Handler Fixes
=======================================

This script tests the fixes applied to the WebSocket V2 message handler
to ensure unknown message types are now properly handled.
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup enhanced logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('websocket_v2_test.log')
    ]
)

logger = logging.getLogger(__name__)

# Import the updated message handler
from src.websocket.kraken_v2_message_handler import KrakenV2MessageHandler, create_kraken_v2_handler

async def test_message_handler_fixes():
    """Test the V2 message handler with various message formats"""
    logger.info("=== WebSocket V2 Message Handler Fix Testing ===")
    
    # Create message handler with debug enabled
    handler = create_kraken_v2_handler(
        enable_sequence_tracking=True,
        enable_statistics=True
    )
    
    # Test message formats that were previously causing "unknown" errors
    test_messages = [
        # Status message (was causing unknown errors)
        {
            "channel": "status",
            "type": "update",
            "data": {
                "connection": {"status": "online"},
                "api_version": "2.0"
            }
        },
        
        # Method-based subscription response
        {
            "method": "subscribe",
            "result": {
                "channel": "ticker",
                "success": True
            },
            "success": True
        },
        
        # Missing channel and type (problematic case)
        {
            "data": {"some": "data"},
            "timestamp": 1234567890
        },
        
        # Ticker message (should work)
        {
            "channel": "ticker",
            "type": "update", 
            "data": [{
                "symbol": "SHIB/USDT",
                "bid": "0.00001234",
                "ask": "0.00001235",
                "last": "0.00001234"
            }]
        },
        
        # Balance message (should work)
        {
            "channel": "balances",
            "data": [{
                "asset": "USDT",
                "balance": "100.0",
                "hold_trade": "0.0"
            }]
        }
    ]
    
    # Process each test message
    for i, message in enumerate(test_messages, 1):
        logger.info(f"\n--- Test Message {i} ---")
        logger.info(f"Input: {message}")
        
        try:
            success = await handler.process_message(message)
            logger.info(f"Processing result: {'SUCCESS' if success else 'FAILED'}")
        except Exception as e:
            logger.error(f"Exception during processing: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Print statistics
    logger.info("\n=== Message Processing Statistics ===")
    stats = handler.get_statistics()
    for key, value in stats.items():
        logger.info(f"{key}: {value}")
    
    # Print connection status
    logger.info("\n=== Connection Status ===")
    status = handler.get_connection_status()
    for key, value in status.items():
        logger.info(f"{key}: {value}")
    
    logger.info("=== WebSocket V2 Message Handler Fix Testing Complete ===")

async def main():
    """Main test function"""
    try:
        await test_message_handler_fixes()
        return True
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)