"""
WebSocket Pipeline Integration Example
=====================================

Example script demonstrating how to integrate and use the unified WebSocket V2
data pipeline with the crypto trading bot. Shows basic setup, advanced configuration,
and monitoring capabilities.

This example can be used as a reference for integrating the pipeline into
existing bot architectures or for testing the pipeline functionality.
"""

import asyncio
import logging
import time
from typing import Dict, Any

# Import pipeline components
from src.exchange.unified_websocket_data_pipeline import (
    UnifiedWebSocketDataPipeline,
    MessageQueueConfig,
    PerformanceConfig,
    DataChannel
)
from src.exchange.websocket_pipeline_integration import WebSocketPipelineIntegrator
from src.exchange.websocket_pipeline_monitor import WebSocketPipelineMonitor, AlertConfig
from src.exchange.websocket_pipeline_init import (
    WebSocketPipelineInitializer,
    initialize_websocket_pipeline,
    quick_setup_pipeline
)

# Import existing bot components (mock if not available)
try:
    from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager
    from src.core.bot import CryptoTradingBot
    from src.balance.balance_manager_v2 import BalanceManagerV2
except ImportError as e:
    print(f"Some imports not available: {e}")
    # Mock classes for demonstration
    class KrakenProWebSocketManager:
        def __init__(self, *args, **kwargs):
            self.is_connected = True
    
    class CryptoTradingBot:
        def __init__(self):
            self.balance_manager = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockBalanceManager:
    """Mock balance manager for testing"""
    
    def __init__(self):
        self.balances = {}
        self.websocket_balances = {}
        self.circuit_breaker_active = False
        self.last_update = time.time()
    
    async def process_websocket_update(self, balance_data: Dict[str, Any]):
        """Process WebSocket balance update"""
        logger.info(f"[MOCK_BALANCE] Received update for {len(balance_data.get('balances', {}))} assets")
        for asset, balance_info in balance_data.get('balances', {}).items():
            self.balances[asset] = balance_info
            logger.info(f"[MOCK_BALANCE] Updated {asset}: {balance_info.get('free', 0):.6f}")


class MockTradingEngine:
    """Mock trading engine for testing"""
    
    def __init__(self):
        self.ticker_updates = 0
        self.orderbook_updates = 0
        self.execution_updates = 0
    
    async def update_ticker(self, symbol: str, ticker_data: Dict[str, Any]):
        """Process ticker update"""
        self.ticker_updates += 1
        logger.info(f"[MOCK_TRADING] Ticker update for {symbol}: ${ticker_data.get('last', 0):.6f}")
    
    async def update_orderbook(self, symbol: str, orderbook_data: Dict[str, Any]):
        """Process orderbook update"""
        self.orderbook_updates += 1
        spread = orderbook_data.get('spread', 0)
        logger.info(f"[MOCK_TRADING] Orderbook update for {symbol}: {spread:.4%} spread")
    
    async def process_execution(self, execution_data: Dict[str, Any]):
        """Process execution update"""
        self.execution_updates += 1
        logger.info(f"[MOCK_TRADING] Execution update: {execution_data}")


class MockBot:
    """Mock bot instance for testing"""
    
    def __init__(self):
        self.balance_manager = MockBalanceManager()
        self.trade_executor = MockTradingEngine()
        self.strategy_manager = None
        self.learning_manager = None


async def example_basic_setup():
    """Example 1: Basic pipeline setup"""
    logger.info("=== Example 1: Basic Pipeline Setup ===")
    
    # Create mock components
    websocket_manager = KrakenProWebSocketManager(None, ['BTC/USDT', 'ETH/USDT'])
    bot_instance = MockBot()
    
    # Quick setup
    success, initializer = await quick_setup_pipeline(websocket_manager, bot_instance)
    
    if success:
        logger.info("✓ Basic pipeline setup successful")
        
        # Get system status
        status = initializer.get_system_status()
        logger.info(f"System healthy: {initializer.is_healthy()}")
        logger.info(f"Components discovered: {status.get('integration_status', {}).get('components_discovered', 0)}")
        
        # Simulate some data processing
        await simulate_websocket_data(initializer.integrator.pipeline)
        
        # Shutdown
        await initializer.shutdown()
        logger.info("✓ Basic pipeline shutdown complete")
    else:
        logger.error("✗ Basic pipeline setup failed")


async def example_advanced_setup():
    """Example 2: Advanced pipeline setup with custom configuration"""
    logger.info("=== Example 2: Advanced Pipeline Setup ===")
    
    # Create mock components
    websocket_manager = KrakenProWebSocketManager(None, ['BTC/USDT', 'ETH/USDT', 'SHIB/USDT'])
    bot_instance = MockBot()
    
    # Custom configurations
    queue_config = MessageQueueConfig(
        max_size=3000,
        timeout_seconds=0.2,
        priority_multiplier=1.8,
        enable_deduplication=True,
        dedup_window_seconds=0.05
    )
    
    performance_config = PerformanceConfig(
        enable_metrics=True,
        metrics_interval_seconds=15.0,
        max_processing_time_ms=8.0,
        enable_latency_tracking=True,
        memory_usage_threshold_mb=300.0
    )
    
    alert_config = AlertConfig(
        max_latency_ms=30.0,
        max_memory_mb=500.0,
        max_error_rate_percent=3.0,
        max_drop_rate_percent=1.0,
        min_throughput_msgs_per_sec=2.0
    )
    
    # Initialize with custom configuration
    initializer = WebSocketPipelineInitializer(websocket_manager, bot_instance)
    success = await initializer.initialize_complete_pipeline(
        queue_config=queue_config,
        performance_config=performance_config,
        alert_config=alert_config,
        enable_monitoring=True
    )
    
    if success:
        logger.info("✓ Advanced pipeline setup successful")
        
        # Test pipeline functionality
        await test_pipeline_functionality(initializer)
        
        # Get performance report
        if initializer.monitor:
            await asyncio.sleep(20)  # Let it collect some data
            report = initializer.monitor.get_performance_report()
            logger.info(f"Performance report: {report.get('status')}")
            
            # Export performance data
            initializer.monitor.export_performance_data('/tmp/pipeline_performance.json')
        
        # Shutdown
        await initializer.shutdown()
        logger.info("✓ Advanced pipeline shutdown complete")
    else:
        logger.error("✗ Advanced pipeline setup failed")


async def example_high_performance_setup():
    """Example 3: High-performance pipeline setup"""
    logger.info("=== Example 3: High-Performance Pipeline Setup ===")
    
    # Create mock components
    websocket_manager = KrakenProWebSocketManager(None, ['BTC/USDT', 'ETH/USDT', 'SHIB/USDT', 'MATIC/USDT'])
    bot_instance = MockBot()
    
    # Initialize high-performance pipeline
    initializer = await initialize_websocket_pipeline(
        websocket_manager, 
        bot_instance, 
        "high_performance"
    )
    
    if initializer:
        logger.info("✓ High-performance pipeline setup successful")
        
        # Stress test the pipeline
        await stress_test_pipeline(initializer)
        
        # Monitor performance during stress test
        if initializer.monitor:
            report = initializer.monitor.get_performance_report()
            current_metrics = report.get('current_metrics', {})
            logger.info(
                f"Stress test results - "
                f"Throughput: {current_metrics.get('throughput_msgs_per_sec', 0):.1f} msg/s, "
                f"Latency: {current_metrics.get('avg_latency_ms', 0):.2f}ms, "
                f"Memory: {current_metrics.get('memory_usage_mb', 0):.1f}MB"
            )
        
        # Shutdown
        await initializer.shutdown()
        logger.info("✓ High-performance pipeline shutdown complete")
    else:
        logger.error("✗ High-performance pipeline setup failed")


async def example_custom_component_integration():
    """Example 4: Custom component integration"""
    logger.info("=== Example 4: Custom Component Integration ===")
    
    class CustomAnalyzer:
        """Custom analysis component"""
        
        def __init__(self):
            self.ticker_count = 0
            self.balance_count = 0
        
        async def on_ticker_update(self, data: Dict[str, Any]):
            self.ticker_count += 1
            logger.info(f"[CUSTOM] Ticker analysis #{self.ticker_count}")
        
        async def on_balances_update(self, data: Dict[str, Any]):
            self.balance_count += 1
            logger.info(f"[CUSTOM] Balance analysis #{self.balance_count}")
    
    # Setup pipeline
    websocket_manager = KrakenProWebSocketManager(None, ['BTC/USDT'])
    bot_instance = MockBot()
    
    success, initializer = await quick_setup_pipeline(websocket_manager, bot_instance)
    
    if success:
        # Register custom component
        custom_analyzer = CustomAnalyzer()
        success = initializer.integrator.register_additional_component(
            "custom_analyzer",
            custom_analyzer,
            ["ticker", "balances"]
        )
        
        if success:
            logger.info("✓ Custom component registered")
            
            # Test custom component integration
            await simulate_websocket_data(initializer.integrator.pipeline)
            
            logger.info(f"Custom analyzer processed {custom_analyzer.ticker_count} tickers, {custom_analyzer.balance_count} balances")
        
        await initializer.shutdown()
    else:
        logger.error("✗ Custom component integration failed")


async def simulate_websocket_data(pipeline):
    """Simulate WebSocket data for testing"""
    logger.info("[SIMULATE] Simulating WebSocket data...")
    
    # Simulate ticker update
    ticker_message = {
        'channel': 'ticker',
        'data': [{
            'symbol': 'BTC/USDT',
            'bid': '45000.00',
            'ask': '45010.00',
            'last': '45005.00',
            'volume': '1234.56'
        }]
    }
    await pipeline.process_raw_message(ticker_message)
    
    # Simulate balance update
    balance_message = {
        'channel': 'balances',
        'data': [{
            'asset': 'USDT',
            'balance': '1000.00',
            'hold_trade': '50.00'
        }, {
            'asset': 'BTC',
            'balance': '0.5',
            'hold_trade': '0.0'
        }]
    }
    await pipeline.process_raw_message(balance_message)
    
    # Simulate orderbook update
    orderbook_message = {
        'channel': 'book',
        'data': [{
            'symbol': 'BTC/USDT',
            'bids': [{'price': '45000.00', 'qty': '1.0'}],
            'asks': [{'price': '45010.00', 'qty': '1.5'}]
        }]
    }
    await pipeline.process_raw_message(orderbook_message)
    
    # Wait for processing
    await asyncio.sleep(2.0)
    logger.info("[SIMULATE] Data simulation complete")


async def test_pipeline_functionality(initializer):
    """Test pipeline functionality"""
    logger.info("[TEST] Testing pipeline functionality...")
    
    pipeline = initializer.integrator.pipeline
    
    # Test different message types
    test_messages = [
        {
            'channel': 'ticker',
            'data': [{'symbol': 'ETH/USDT', 'last': '3000.00'}]
        },
        {
            'channel': 'balances',
            'data': [{'asset': 'ETH', 'balance': '10.0', 'hold_trade': '0.0'}]
        },
        {
            'channel': 'heartbeat',
            'data': [{'type': 'heartbeat', 'timestamp': time.time()}]
        }
    ]
    
    success_count = 0
    for i, message in enumerate(test_messages):
        success = await pipeline.process_raw_message(message)
        if success:
            success_count += 1
        logger.info(f"[TEST] Message {i+1}: {'✓' if success else '✗'}")
    
    # Get pipeline stats
    stats = pipeline.get_pipeline_stats()
    logger.info(f"[TEST] Pipeline stats: {stats}")
    
    logger.info(f"[TEST] Functionality test complete: {success_count}/{len(test_messages)} messages processed")


async def stress_test_pipeline(initializer):
    """Stress test the pipeline"""
    logger.info("[STRESS] Starting pipeline stress test...")
    
    pipeline = initializer.integrator.pipeline
    
    # Generate high-frequency messages
    async def generate_messages():
        for i in range(1000):
            message = {
                'channel': 'ticker',
                'data': [{
                    'symbol': 'BTC/USDT',
                    'last': str(45000 + (i % 100)),
                    'timestamp': time.time()
                }]
            }
            await pipeline.process_raw_message(message)
            
            if i % 100 == 0:
                logger.info(f"[STRESS] Generated {i} messages")
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.001)
    
    # Run stress test
    start_time = time.time()
    await generate_messages()
    duration = time.time() - start_time
    
    # Get final stats
    stats = pipeline.get_pipeline_stats()
    total_processed = sum(stats.get('messages_processed', {}).values())
    
    logger.info(
        f"[STRESS] Stress test complete: "
        f"{total_processed} messages in {duration:.2f}s "
        f"({total_processed/duration:.1f} msg/s)"
    )


async def main():
    """Run all examples"""
    logger.info("Starting WebSocket Pipeline Examples")
    
    try:
        # Run examples
        await example_basic_setup()
        await asyncio.sleep(2)
        
        await example_advanced_setup()
        await asyncio.sleep(2)
        
        await example_high_performance_setup()
        await asyncio.sleep(2)
        
        await example_custom_component_integration()
        
        logger.info("All examples completed successfully!")
    
    except Exception as e:
        logger.error(f"Example execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())