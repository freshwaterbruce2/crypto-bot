#!/usr/bin/env python3
"""
Test script for Kraken WebSocket V2 Message Handler
==================================================

Tests the V2 message handler with sample Kraken WebSocket V2 messages
to ensure proper validation, processing, and integration.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from src.websocket.kraken_v2_message_handler import create_kraken_v2_handler


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def pass_test(self, test_name: str):
        self.passed += 1
        logger.info(f"✅ PASS: {test_name}")
    
    def fail_test(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        logger.error(f"❌ FAIL: {test_name} - {error}")
    
    def summary(self):
        total = self.passed + self.failed
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST SUMMARY: {self.passed}/{total} tests passed")
        if self.failed > 0:
            logger.error(f"FAILED TESTS:")
            for error in self.errors:
                logger.error(f"  - {error}")
        logger.info(f"{'='*60}")


# Sample Kraken WebSocket V2 messages for testing
SAMPLE_MESSAGES = {
    'balance_update': {
        "channel": "balances",
        "type": "update",
        "data": [
            {"asset": "USDT", "balance": "18.99", "hold_trade": "0"},
            {"asset": "MANA", "balance": "163.94", "hold_trade": "0"},
            {"asset": "BTC", "balance": "0.001", "hold_trade": "0.0005"}
        ],
        "sequence": 12345,
        "timestamp": "2025-08-03T15:30:45.123Z"
    },
    
    'ticker_update': {
        "channel": "ticker",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USDT",
                "bid": "65000.50",
                "ask": "65001.50", 
                "last": "65001.00",
                "volume": "1234.567",
                "high": "66000.00",
                "low": "64000.00",
                "vwap": "65123.45",
                "open": "64500.00"
            }
        ],
        "sequence": 12346,
        "timestamp": "2025-08-03T15:30:46.456Z"
    },
    
    'orderbook_update': {
        "channel": "book",
        "type": "update", 
        "data": [
            {
                "symbol": "ETH/USDT",
                "bids": [
                    {"price": "3500.50", "qty": "10.5"},
                    {"price": "3500.25", "qty": "5.2"}
                ],
                "asks": [
                    {"price": "3501.00", "qty": "8.3"},
                    {"price": "3501.25", "qty": "12.1"}
                ]
            }
        ],
        "sequence": 12347,
        "timestamp": "2025-08-03T15:30:47.789Z"
    },
    
    'trade_update': {
        "channel": "trade",
        "type": "update",
        "data": [
            {
                "symbol": "SHIB/USDT",
                "side": "buy",
                "price": "0.00002540",
                "qty": "1000000",
                "trade_id": "12345678"
            }
        ],
        "sequence": 12348,
        "timestamp": "2025-08-03T15:30:48.012Z"
    },
    
    'ohlc_update': {
        "channel": "ohlc",
        "type": "update",
        "data": [
            {
                "symbol": "MATIC/USDT",
                "open": "0.8500",
                "high": "0.8650",
                "low": "0.8450",
                "close": "0.8600",
                "volume": "50000.123",
                "interval": 1,
                "timestamp": "2025-08-03T15:30:00.000Z"
            }
        ],
        "sequence": 12349,
        "timestamp": "2025-08-03T15:30:49.345Z"
    },
    
    'heartbeat': {
        "channel": "heartbeat",
        "timestamp": "2025-08-03T15:30:50.678Z"
    },
    
    'subscription_response': {
        "method": "subscribe",
        "success": True,
        "result": {
            "channel": "ticker",
            "symbols": ["BTC/USDT", "ETH/USDT"]
        },
        "req_id": 1001,
        "timestamp": "2025-08-03T15:30:51.901Z"
    },
    
    'duplicate_message': {
        "channel": "ticker",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USDT",
                "bid": "65000.50",
                "ask": "65001.50",
                "last": "65001.00"
            }
        ],
        "sequence": 12346,  # Same sequence as ticker_update above
        "timestamp": "2025-08-03T15:30:52.234Z"
    },
    
    'malformed_message': {
        "invalid": "message",
        "missing": "required_fields"
    }
}


class TestCallbackHandler:
    """Test callback handler to verify message processing"""
    
    def __init__(self):
        self.received_messages = []
        self.balance_updates = []
        self.ticker_updates = []
        self.orderbook_updates = []
        self.trade_updates = []
        self.ohlc_updates = []
        self.errors = []
    
    async def balance_callback(self, balance_data):
        self.balance_updates.append(balance_data)
        logger.info(f"Received balance update: {len(balance_data) if isinstance(balance_data, list) else type(balance_data)}")
    
    async def ticker_callback(self, symbol: str, ticker_data: dict):
        self.ticker_updates.append((symbol, ticker_data))
        logger.info(f"Received ticker update for {symbol}: last=${ticker_data.get('last', 'N/A')}")
    
    async def orderbook_callback(self, symbol: str, orderbook_data: dict):
        self.orderbook_updates.append((symbol, orderbook_data))
        logger.info(f"Received orderbook update for {symbol}: {len(orderbook_data.get('bids', []))} bids")
    
    async def trade_callback(self, symbol: str, trade_data: dict):
        self.trade_updates.append((symbol, trade_data))
        logger.info(f"Received trade update for {symbol}: {trade_data.get('side')} {trade_data.get('volume')}")
    
    async def ohlc_callback(self, symbol: str, ohlc_data: dict):
        self.ohlc_updates.append((symbol, ohlc_data))
        logger.info(f"Received OHLC update for {symbol}: OHLC=[{ohlc_data.get('open')},{ohlc_data.get('high')},{ohlc_data.get('low')},{ohlc_data.get('close')}]")
    
    async def error_callback(self, error: Exception, raw_message: dict):
        self.errors.append((error, raw_message))
        logger.info(f"Received error callback: {error}")


async def test_message_handler():
    """Main test function"""
    results = TestResults()
    
    try:
        # Create V2 message handler
        handler = create_kraken_v2_handler(
            enable_sequence_tracking=True,
            enable_statistics=True
        )
        
        # Create test callback handler
        callback_handler = TestCallbackHandler()
        
        # Register callbacks
        handler.register_callback('balance', callback_handler.balance_callback)
        handler.register_callback('balances', callback_handler.balance_callback)
        handler.register_callback('ticker', callback_handler.ticker_callback)
        handler.register_callback('book', callback_handler.orderbook_callback)
        handler.register_callback('orderbook', callback_handler.orderbook_callback)
        handler.register_callback('trade', callback_handler.trade_callback)
        handler.register_callback('ohlc', callback_handler.ohlc_callback)
        handler.register_error_callback(callback_handler.error_callback)
        
        # Test 1: Balance message processing
        logger.info("\n=== Testing Balance Message Processing ===")
        success = await handler.process_message(SAMPLE_MESSAGES['balance_update'])
        if success and len(callback_handler.balance_updates) > 0:
            results.pass_test("Balance message processing")
        else:
            results.fail_test("Balance message processing", "No balance updates received")
        
        # Test 2: Ticker message processing
        logger.info("\n=== Testing Ticker Message Processing ===")
        success = await handler.process_message(SAMPLE_MESSAGES['ticker_update'])
        if success and len(callback_handler.ticker_updates) > 0:
            symbol, ticker_data = callback_handler.ticker_updates[0]
            if symbol == "BTC/USDT" and ticker_data.get('last') == 65001.00:
                results.pass_test("Ticker message processing")
            else:
                results.fail_test("Ticker message processing", f"Incorrect ticker data: {ticker_data}")
        else:
            results.fail_test("Ticker message processing", "No ticker updates received")
        
        # Test 3: Orderbook message processing
        logger.info("\n=== Testing Orderbook Message Processing ===")
        success = await handler.process_message(SAMPLE_MESSAGES['orderbook_update'])
        if success and len(callback_handler.orderbook_updates) > 0:
            symbol, orderbook_data = callback_handler.orderbook_updates[0]
            if symbol == "ETH/USDT" and len(orderbook_data.get('bids', [])) > 0:
                results.pass_test("Orderbook message processing")
            else:
                results.fail_test("Orderbook message processing", f"Incorrect orderbook data: {orderbook_data}")
        else:
            results.fail_test("Orderbook message processing", "No orderbook updates received")
        
        # Test 4: Trade message processing
        logger.info("\n=== Testing Trade Message Processing ===")
        success = await handler.process_message(SAMPLE_MESSAGES['trade_update'])
        if success and len(callback_handler.trade_updates) > 0:
            symbol, trade_data = callback_handler.trade_updates[0]
            if symbol == "SHIB/USDT" and trade_data.get('side') == 'buy':
                results.pass_test("Trade message processing")
            else:
                results.fail_test("Trade message processing", f"Incorrect trade data: {trade_data}")
        else:
            results.fail_test("Trade message processing", "No trade updates received")
        
        # Test 5: OHLC message processing
        logger.info("\n=== Testing OHLC Message Processing ===")
        success = await handler.process_message(SAMPLE_MESSAGES['ohlc_update'])
        if success and len(callback_handler.ohlc_updates) > 0:
            symbol, ohlc_data = callback_handler.ohlc_updates[0]
            if symbol == "MATIC/USDT" and ohlc_data.get('open') == 0.85:
                results.pass_test("OHLC message processing")
            else:
                results.fail_test("OHLC message processing", f"Incorrect OHLC data: {ohlc_data}")
        else:
            results.fail_test("OHLC message processing", "No OHLC updates received")
        
        # Test 6: Heartbeat message processing
        logger.info("\n=== Testing Heartbeat Message Processing ===")
        success = await handler.process_message(SAMPLE_MESSAGES['heartbeat'])
        if success:
            results.pass_test("Heartbeat message processing")
        else:
            results.fail_test("Heartbeat message processing", "Heartbeat processing failed")
        
        # Test 7: Subscription response processing
        logger.info("\n=== Testing Subscription Response Processing ===")
        success = await handler.process_message(SAMPLE_MESSAGES['subscription_response'])
        if success:
            results.pass_test("Subscription response processing")
        else:
            results.fail_test("Subscription response processing", "Subscription response processing failed")
        
        # Test 8: Sequence tracking and duplicate detection
        logger.info("\n=== Testing Sequence Tracking and Duplicate Detection ===")
        initial_ticker_count = len(callback_handler.ticker_updates)
        success = await handler.process_message(SAMPLE_MESSAGES['duplicate_message'])
        final_ticker_count = len(callback_handler.ticker_updates)
        
        # Should process successfully but not add to callback count due to duplicate detection
        if success and final_ticker_count == initial_ticker_count:
            results.pass_test("Duplicate message detection")
        else:
            results.fail_test("Duplicate message detection", f"Duplicate not detected: {initial_ticker_count} -> {final_ticker_count}")
        
        # Test 9: Malformed message handling
        logger.info("\n=== Testing Malformed Message Handling ===")
        success = await handler.process_message(SAMPLE_MESSAGES['malformed_message'])
        if not success:  # Should fail gracefully
            results.pass_test("Malformed message handling")
        else:
            results.fail_test("Malformed message handling", "Malformed message was incorrectly accepted")
        
        # Test 10: Statistics reporting
        logger.info("\n=== Testing Statistics Reporting ===")
        stats = handler.get_statistics()
        if stats and stats.get('total_messages', 0) > 0:
            results.pass_test("Statistics reporting")
            logger.info(f"Statistics: {json.dumps(stats, indent=2)}")
        else:
            results.fail_test("Statistics reporting", f"No statistics available: {stats}")
        
        # Test 11: Sequence status reporting
        logger.info("\n=== Testing Sequence Status Reporting ===")
        sequence_status = handler.get_sequence_status()
        if sequence_status and sequence_status.get('enabled', False):
            results.pass_test("Sequence status reporting")
            logger.info(f"Sequence Status: {json.dumps(sequence_status, indent=2)}")
        else:
            results.fail_test("Sequence status reporting", f"Sequence tracking not enabled: {sequence_status}")
        
        # Test 12: Connection status management
        logger.info("\n=== Testing Connection Status Management ===")
        handler.set_connection_status(connected=True, authenticated=True)
        connection_status = handler.get_connection_status()
        if connection_status.get('connected') and connection_status.get('authenticated'):
            results.pass_test("Connection status management")
        else:
            results.fail_test("Connection status management", f"Connection status incorrect: {connection_status}")
        
        # Performance test: Process multiple messages rapidly
        logger.info("\n=== Performance Test: Rapid Message Processing ===")
        start_time = time.time()
        
        for i in range(100):
            # Create modified ticker message with different sequence
            ticker_msg = SAMPLE_MESSAGES['ticker_update'].copy()
            ticker_msg['sequence'] = 20000 + i
            ticker_msg['data'][0]['last'] = f"{65000 + i}.00"
            await handler.process_message(ticker_msg)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if processing_time < 1.0:  # Should process 100 messages in under 1 second
            results.pass_test(f"Performance test (100 messages in {processing_time:.3f}s)")
        else:
            results.fail_test("Performance test", f"Too slow: {processing_time:.3f}s for 100 messages")
        
        # Cleanup
        handler.shutdown()
        
    except Exception as e:
        results.fail_test("Overall test execution", str(e))
        logger.exception("Test execution failed")
    
    finally:
        results.summary()
        return results.failed == 0


if __name__ == "__main__":
    logger.info("Starting Kraken WebSocket V2 Message Handler Tests")
    success = asyncio.run(test_message_handler())
    exit(0 if success else 1)