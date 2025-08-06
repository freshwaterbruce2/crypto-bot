"""
WebSocket Trading Engine Example
===============================

Example demonstrating how to integrate and use the WebSocket-native trading engine
with the existing crypto trading bot architecture.

This example shows:
1. Setting up WebSocket trading integration
2. Placing orders via WebSocket with REST fallback
3. Monitoring real-time execution updates
4. Performance comparison between WebSocket and REST execution
5. Order lifecycle management
"""

import asyncio
import logging
import time

# Import bot components
from src.core.bot import KrakenTradingBot
from src.integration.websocket_trading_integration import (
    create_websocket_trading_config,
    setup_websocket_trading,
)
from src.trading.websocket_native_trading_engine import OrderStatus, OrderType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebSocketTradingExample:
    """
    Example class demonstrating WebSocket trading integration.
    """

    def __init__(self):
        self.bot = None
        self.websocket_integration = None
        self.execution_log = []

    async def initialize_bot(self) -> bool:
        """Initialize the crypto trading bot"""
        try:
            logger.info("[EXAMPLE] Initializing crypto trading bot...")

            # Create bot instance (you would use your actual bot initialization here)
            self.bot = KrakenTradingBot()

            # Initialize bot components
            await self.bot.initialize()

            # Wait for WebSocket connection
            if hasattr(self.bot, 'websocket_manager'):
                await self.bot.websocket_manager.connect()
                await asyncio.sleep(3)  # Wait for connection to stabilize

                if not self.bot.websocket_manager.is_connected:
                    logger.error("[EXAMPLE] WebSocket connection failed")
                    return False

            logger.info("[EXAMPLE] ✅ Bot initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[EXAMPLE] Error initializing bot: {e}")
            return False

    async def setup_websocket_trading(self) -> bool:
        """Set up WebSocket trading integration"""
        try:
            logger.info("[EXAMPLE] Setting up WebSocket trading integration...")

            # Create WebSocket trading configuration
            ws_config = create_websocket_trading_config(
                enabled=True,
                prefer_websocket=True,
                max_concurrent_orders=5,
                order_timeout_seconds=30,
                auto_fallback_on_failure=True,
                performance_monitoring=True
            )

            # Set up WebSocket trading integration
            self.websocket_integration = await setup_websocket_trading(self.bot, ws_config)

            if not self.websocket_integration:
                logger.error("[EXAMPLE] Failed to set up WebSocket trading")
                return False

            # Set up execution monitoring
            if self.bot.websocket_trading_engine:
                self.bot.websocket_trading_engine.add_execution_callback(self._log_execution)

            logger.info("[EXAMPLE] ✅ WebSocket trading integration complete")
            return True

        except Exception as e:
            logger.error(f"[EXAMPLE] Error setting up WebSocket trading: {e}")
            return False

    async def _log_execution(self, execution_update) -> None:
        """Log execution updates for monitoring"""
        try:
            self.execution_log.append({
                'timestamp': time.time(),
                'order_id': execution_update.order_id,
                'symbol': execution_update.symbol,
                'side': execution_update.side,
                'amount': execution_update.amount,
                'price': execution_update.price,
                'execution_id': execution_update.execution_id
            })

            logger.info(
                f"[EXAMPLE] 🎯 Execution: {execution_update.symbol} "
                f"{execution_update.side} {execution_update.amount} @ ${execution_update.price}"
            )

        except Exception as e:
            logger.error(f"[EXAMPLE] Error logging execution: {e}")

    async def demonstrate_websocket_order_placement(self) -> None:
        """Demonstrate WebSocket order placement"""
        try:
            logger.info("[EXAMPLE] Demonstrating WebSocket order placement...")

            if not self.bot.websocket_trading_engine:
                logger.error("[EXAMPLE] WebSocket trading engine not available")
                return

            engine = self.bot.websocket_trading_engine

            # Example 1: Market buy order
            logger.info("[EXAMPLE] Placing market buy order...")
            buy_order = await engine.place_buy_order(
                symbol="SHIB/USDT",
                quantity="100000",  # 100k SHIB tokens
                order_type=OrderType.MARKET
            )

            if buy_order:
                logger.info(f"[EXAMPLE] ✅ Market buy order placed: {buy_order.id}")
                await self._monitor_order_completion(buy_order.id)
            else:
                logger.error("[EXAMPLE] ❌ Market buy order failed")

            # Wait a moment between orders
            await asyncio.sleep(2)

            # Example 2: Limit sell order with IOC
            logger.info("[EXAMPLE] Placing IOC limit sell order...")

            # Get current market price for limit order
            ticker = self.bot.websocket_manager.get_ticker("SHIB/USDT")
            if ticker and ticker.get('bid'):
                # Place limit order slightly above bid for quick execution
                limit_price = ticker['bid'] * 1.002  # 0.2% above bid

                sell_order = await engine.place_sell_order(
                    symbol="SHIB/USDT",
                    quantity="50000",  # 50k SHIB tokens
                    price=str(limit_price),
                    order_type=OrderType.IOC
                )

                if sell_order:
                    logger.info(f"[EXAMPLE] ✅ IOC limit sell order placed: {sell_order.id}")
                    await self._monitor_order_completion(sell_order.id)
                else:
                    logger.error("[EXAMPLE] ❌ IOC limit sell order failed")
            else:
                logger.warning("[EXAMPLE] No market price available for limit order")

        except Exception as e:
            logger.error(f"[EXAMPLE] Error in order placement demonstration: {e}")

    async def _monitor_order_completion(self, order_id: str, timeout: int = 30) -> None:
        """Monitor order until completion or timeout"""
        try:
            start_time = time.time()

            while time.time() - start_time < timeout:
                order = await self.bot.websocket_trading_engine.get_order_status(order_id)

                if not order:
                    logger.warning(f"[EXAMPLE] Order {order_id} not found")
                    break

                logger.info(f"[EXAMPLE] 📊 Order {order_id} status: {order.status.value}")

                if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.EXPIRED, OrderStatus.REJECTED]:
                    if order.status == OrderStatus.FILLED:
                        logger.info(
                            f"[EXAMPLE] ✅ Order {order_id} filled: "
                            f"{order.filled_amount} @ ${order.avg_fill_price:.6f}"
                        )
                    else:
                        logger.info(f"[EXAMPLE] 📋 Order {order_id} final status: {order.status.value}")
                    break

                await asyncio.sleep(1)
            else:
                logger.warning(f"[EXAMPLE] ⏰ Order {order_id} monitoring timeout")

        except Exception as e:
            logger.error(f"[EXAMPLE] Error monitoring order {order_id}: {e}")

    async def demonstrate_performance_comparison(self) -> None:
        """Demonstrate performance comparison between WebSocket and REST"""
        try:
            logger.info("[EXAMPLE] Demonstrating performance comparison...")

            if not self.websocket_integration:
                logger.error("[EXAMPLE] WebSocket integration not available")
                return

            # Test WebSocket execution time
            logger.info("[EXAMPLE] Testing WebSocket execution performance...")

            ws_start_time = time.time()
            await self.websocket_integration.force_websocket_preference(True)

            # Place a small test order via WebSocket
            test_params = {
                'symbol': 'SHIB/USDT',
                'side': 'buy',
                'amount': 2.0,  # $2 worth
                'signal': {'strategy': 'test', 'confidence': 85}
            }

            ws_result = await self.bot.trade_executor.execute_trade(test_params)
            ws_execution_time = (time.time() - ws_start_time) * 1000  # ms

            if ws_result.get('success'):
                logger.info(f"[EXAMPLE] ✅ WebSocket execution time: {ws_execution_time:.1f}ms")
            else:
                logger.error(f"[EXAMPLE] ❌ WebSocket execution failed: {ws_result.get('error')}")

            # Wait a moment
            await asyncio.sleep(5)

            # Test REST execution time
            logger.info("[EXAMPLE] Testing REST execution performance...")

            rest_start_time = time.time()
            await self.websocket_integration.force_websocket_preference(False)

            # Place a small test order via REST
            rest_result = await self.bot.trade_executor.execute_trade(test_params)
            rest_execution_time = (time.time() - rest_start_time) * 1000  # ms

            if rest_result.get('success'):
                logger.info(f"[EXAMPLE] ✅ REST execution time: {rest_execution_time:.1f}ms")
            else:
                logger.error(f"[EXAMPLE] ❌ REST execution failed: {rest_result.get('error')}")

            # Compare performance
            if ws_result.get('success') and rest_result.get('success'):
                performance_improvement = ((rest_execution_time - ws_execution_time) / rest_execution_time) * 100
                logger.info(
                    f"[EXAMPLE] 📈 Performance comparison: "
                    f"WebSocket: {ws_execution_time:.1f}ms, REST: {rest_execution_time:.1f}ms, "
                    f"Improvement: {performance_improvement:.1f}%"
                )

            # Restore WebSocket preference
            await self.websocket_integration.force_websocket_preference(True)

        except Exception as e:
            logger.error(f"[EXAMPLE] Error in performance comparison: {e}")

    async def demonstrate_order_management(self) -> None:
        """Demonstrate advanced order management features"""
        try:
            logger.info("[EXAMPLE] Demonstrating order management...")

            if not self.bot.websocket_trading_engine:
                logger.error("[EXAMPLE] WebSocket trading engine not available")
                return

            engine = self.bot.websocket_trading_engine

            # Place a limit order that we can manage
            ticker = self.bot.websocket_manager.get_ticker("SHIB/USDT")
            if not ticker or not ticker.get('bid'):
                logger.warning("[EXAMPLE] No market price available")
                return

            # Place limit buy order below market (unlikely to fill immediately)
            limit_price = ticker['bid'] * 0.98  # 2% below bid

            logger.info(f"[EXAMPLE] Placing limit buy order at ${limit_price:.8f} (2% below market)...")

            buy_order = await engine.place_buy_order(
                symbol="SHIB/USDT",
                quantity="100000",
                price=str(limit_price),
                order_type=OrderType.LIMIT
            )

            if not buy_order:
                logger.error("[EXAMPLE] Failed to place limit order")
                return

            logger.info(f"[EXAMPLE] ✅ Limit buy order placed: {buy_order.id}")

            # Wait a moment
            await asyncio.sleep(5)

            # Check order status
            order_status = await engine.get_order_status(buy_order.id)
            if order_status:
                logger.info(f"[EXAMPLE] 📊 Order status: {order_status.status.value}")

            # Modify the order (cancel and replace with new price)
            new_price = ticker['bid'] * 0.99  # 1% below bid
            logger.info(f"[EXAMPLE] Modifying order to new price: ${new_price:.8f}")

            modify_success = await engine.modify_order(
                buy_order.id,
                new_price=str(new_price)
            )

            if modify_success:
                logger.info("[EXAMPLE] ✅ Order modified successfully")
            else:
                logger.error("[EXAMPLE] ❌ Order modification failed")

            # Wait a moment
            await asyncio.sleep(5)

            # Cancel the order
            logger.info("[EXAMPLE] Cancelling order...")
            cancel_success = await engine.cancel_order(buy_order.id)

            if cancel_success:
                logger.info("[EXAMPLE] ✅ Order cancelled successfully")
            else:
                logger.error("[EXAMPLE] ❌ Order cancellation failed")

        except Exception as e:
            logger.error(f"[EXAMPLE] Error in order management demonstration: {e}")

    async def show_integration_status(self) -> None:
        """Show detailed integration status"""
        try:
            logger.info("[EXAMPLE] Integration Status Report:")
            logger.info("=" * 50)

            if self.websocket_integration:
                status = self.websocket_integration.get_status()

                # Integration status
                integration_status = status['integration_status']
                logger.info(f"WebSocket Available: {integration_status['websocket_available']}")
                logger.info(f"WebSocket Initialized: {integration_status['websocket_initialized']}")
                logger.info(f"Adapter Created: {integration_status['adapter_created']}")
                logger.info(f"Integration Active: {integration_status['integration_active']}")

                # Performance metrics
                perf_metrics = status['performance_metrics']
                logger.info(f"WebSocket Trades: {perf_metrics['websocket_trades']}")
                logger.info(f"REST Trades: {perf_metrics['rest_trades']}")
                logger.info(f"Fallback Events: {perf_metrics['fallback_events']}")
                logger.info(f"WebSocket Success Rate: {perf_metrics['websocket_success_rate']:.2%}")

                # WebSocket engine metrics
                engine_metrics = status['websocket_engine_metrics']
                if engine_metrics:
                    logger.info(f"Orders Placed: {engine_metrics.get('orders_placed', 0)}")
                    logger.info(f"Orders Filled: {engine_metrics.get('orders_filled', 0)}")
                    logger.info(f"Orders Cancelled: {engine_metrics.get('orders_cancelled', 0)}")
                    logger.info(f"Active Orders: {engine_metrics.get('active_orders_count', 0)}")
                    logger.info(f"Execution Updates: {engine_metrics.get('execution_updates_received', 0)}")
            else:
                logger.warning("WebSocket integration not available")

            # Execution log summary
            if self.execution_log:
                logger.info(f"Total Executions Logged: {len(self.execution_log)}")

                # Show recent executions
                recent_executions = self.execution_log[-5:]  # Last 5
                logger.info("Recent Executions:")
                for execution in recent_executions:
                    logger.info(
                        f"  {execution['symbol']} {execution['side']} "
                        f"{execution['amount']} @ ${execution['price']}"
                    )

            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"[EXAMPLE] Error showing integration status: {e}")

    async def run_complete_example(self) -> None:
        """Run the complete WebSocket trading example"""
        try:
            logger.info("[EXAMPLE] Starting WebSocket Trading Engine Example")
            logger.info("=" * 60)

            # Step 1: Initialize bot
            if not await self.initialize_bot():
                logger.error("[EXAMPLE] Bot initialization failed, exiting")
                return

            # Step 2: Set up WebSocket trading
            if not await self.setup_websocket_trading():
                logger.error("[EXAMPLE] WebSocket trading setup failed, exiting")
                return

            # Step 3: Show initial status
            await self.show_integration_status()

            # Step 4: Demonstrate order placement
            await self.demonstrate_websocket_order_placement()

            # Step 5: Demonstrate performance comparison
            await self.demonstrate_performance_comparison()

            # Step 6: Demonstrate order management
            await self.demonstrate_order_management()

            # Step 7: Show final status
            await self.show_integration_status()

            logger.info("[EXAMPLE] ✅ WebSocket Trading Engine Example Complete")

        except Exception as e:
            logger.error(f"[EXAMPLE] Error in complete example: {e}")
        finally:
            # Cleanup
            if self.websocket_integration:
                await self.websocket_integration.shutdown()

            if self.bot:
                await self.bot.shutdown()


async def main():
    """Main function to run the example"""
    example = WebSocketTradingExample()
    await example.run_complete_example()


if __name__ == "__main__":
    asyncio.run(main())
