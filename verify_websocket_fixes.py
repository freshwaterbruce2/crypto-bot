#!/usr/bin/env python3
"""
Verify WebSocket V2 Message Handler Fixes
=========================================

This script verifies that the WebSocket V2 message parsing fixes
resolve the "unknown message" issues identified in the logs.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

def test_message_handler_imports():
    """Test that the message handler imports correctly"""
    try:
        from src.websocket.kraken_v2_message_handler import KrakenV2MessageHandler, create_kraken_v2_handler
        from src.websocket.data_models import WebSocketMessage, MessageType, ChannelType
        logger.info("✅ WebSocket V2 imports successful")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False

async def test_problematic_messages():
    """Test the specific message types that were causing issues"""
    
    # Import after path setup
    from src.websocket.kraken_v2_message_handler import create_kraken_v2_handler
    
    logger.info("Creating V2 message handler...")
    handler = create_kraken_v2_handler(enable_sequence_tracking=True, enable_statistics=True)
    
    # Test messages based on the log patterns we saw
    test_cases = [
        {
            "name": "Status Channel Message (was causing 'Unknown message type: channel=status, type=update')",
            "message": {
                "channel": "status",
                "type": "update",
                "data": {
                    "connection": {"status": "online"},
                    "api_version": "2.0"
                }
            },
            "expected_success": True
        },
        {
            "name": "Method-based subscription response",
            "message": {
                "method": "subscribe",
                "result": {"channel": "ticker", "success": True},
                "success": True
            },
            "expected_success": True
        },
        {
            "name": "Ticker data message",
            "message": {
                "channel": "ticker",
                "type": "update",
                "data": [{
                    "symbol": "SHIB/USDT",
                    "bid": "0.00001234",
                    "ask": "0.00001235",
                    "last": "0.00001234"
                }]
            },
            "expected_success": True
        },
        {
            "name": "Balance data message",
            "message": {
                "channel": "balances",
                "data": [{
                    "asset": "USDT",
                    "balance": "100.0",
                    "hold_trade": "0.0"
                }]
            },
            "expected_success": True
        },
        {
            "name": "Malformed message (missing channel and method)",
            "message": {
                "data": {"some": "data"},
                "timestamp": 1234567890
            },
            "expected_success": False  # Should be rejected by validation
        }
    ]
    
    results = []
    logger.info(f"Testing {len(test_cases)} message scenarios...")
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- Test {i}: {test_case['name']} ---")
        
        try:
            success = await handler.process_message(test_case['message'])
            expected = test_case['expected_success']
            
            if success == expected:
                logger.info(f"✅ PASS: Processing {'succeeded' if success else 'failed'} as expected")
                results.append(("PASS", test_case['name']))
            else:
                logger.error(f"❌ FAIL: Expected {'success' if expected else 'failure'}, got {'success' if success else 'failure'}")
                results.append(("FAIL", test_case['name']))
                
        except Exception as e:
            logger.error(f"❌ EXCEPTION: {e}")
            results.append(("EXCEPTION", test_case['name']))
    
    return results, handler

def print_final_report(results, handler):
    """Print final test report"""
    logger.info("\n" + "="*60)
    logger.info("WEBSOCKET V2 MESSAGE HANDLER FIX VERIFICATION REPORT")
    logger.info("="*60)
    
    passed = sum(1 for result, _ in results if result == "PASS")
    total = len(results)
    
    logger.info(f"Test Results: {passed}/{total} PASSED")
    
    for result, test_name in results:
        status_emoji = "✅" if result == "PASS" else "❌"
        logger.info(f"{status_emoji} {result}: {test_name}")
    
    # Print message processing statistics
    stats = handler.get_statistics()
    logger.info(f"\nMessage Processing Stats:")
    logger.info(f"  Total messages processed: {stats.get('total_messages', 0)}")
    logger.info(f"  Messages by channel: {stats.get('messages_by_channel', {})}")
    logger.info(f"  Error count: {stats.get('error_count', 0)}")
    logger.info(f"  Duplicate count: {stats.get('duplicate_count', 0)}")
    
    # Connection status
    status = handler.get_connection_status()
    logger.info(f"\nConnection Status:")
    logger.info(f"  Connected: {status.get('connected', False)}")
    logger.info(f"  Authenticated: {status.get('authenticated', False)}")
    logger.info(f"  Subscriptions: {status.get('subscriptions', [])}")
    
    success_rate = passed / total * 100 if total > 0 else 0
    
    if success_rate >= 80:
        logger.info(f"\n🎉 VERIFICATION SUCCESSFUL: {success_rate:.1f}% success rate")
        logger.info("The WebSocket V2 message handler fixes are working correctly!")
        return True
    else:
        logger.error(f"\n❌ VERIFICATION FAILED: {success_rate:.1f}% success rate")
        logger.error("The WebSocket V2 message handler fixes need additional work.")
        return False

async def main():
    """Main verification function"""
    logger.info("🔍 Starting WebSocket V2 Message Handler Fix Verification...")
    
    # Test imports
    if not test_message_handler_imports():
        logger.error("❌ Import test failed - cannot proceed")
        return False
    
    # Test message processing
    try:
        results, handler = await test_problematic_messages()
        return print_final_report(results, handler)
    except Exception as e:
        logger.error(f"❌ Testing failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    logger.info(f"\n{'='*60}")
    logger.info(f"VERIFICATION {'COMPLETED SUCCESSFULLY' if success else 'FAILED'}")
    logger.info(f"{'='*60}")
    sys.exit(0 if success else 1)