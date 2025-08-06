"""
WebSocket V2 Integration Example
==============================

Comprehensive example demonstrating how to integrate the new WebSocket V2 processors
with the existing trading bot infrastructure.

Features demonstrated:
- WebSocket V2 manager setup and configuration
- Channel subscription and data processing
- Order management via WebSocket
- Unified data feed with fallback
- Integration with existing balance management
- Real-time trading with WebSocket V2
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any

from ..data.unified_data_feed import UnifiedDataFeed
from .data_models import BalanceUpdate, OrderBookUpdate, TickerUpdate

# Import WebSocket V2 components
from .websocket_v2_manager import WebSocketV2Config, WebSocketV2Manager

logger = logging.getLogger(__name__)


class WebSocketV2TradingIntegration:
    """
    Example integration class showing how to use WebSocket V2 for trading.

    This example demonstrates:
    - Real-time balance monitoring
    - Market data streaming
    - Order placement and tracking
    - Integration with existing trading logic
    """

    def __init__(
        self,
        exchange_client,
        symbols: list[str],
        api_key: str,
        private_key: str
    ):
        """
        Initialize WebSocket V2 trading integration.

        Args:
            exchange_client: Existing exchange client
            symbols: Trading symbols to monitor
            api_key: Kraken API key
            private_key: Kraken private key
        """
        self.exchange_client = exchange_client
        self.symbols = symbols
        self.api_key = api_key
        self.private_key = private_key

        # WebSocket V2 configuration
        self.websocket_config = WebSocketV2Config(
            ping_interval=20.0,
            heartbeat_timeout=60.0,
            message_queue_size=10000,
            subscription_rate_limit=5,
            token_refresh_interval=13 * 60  # 13 minutes
        )

        # Components
        self.websocket_manager: WebSocketV2Manager = None
        self.unified_data_feed: UnifiedDataFeed = None

        # Trading state
        self.current_balances: dict[str, BalanceUpdate] = {}
        self.current_tickers: dict[str, TickerUpdate] = {}
        self.active_orders: dict[str, Any] = {}

        # Configuration
        self.min_profit_percentage = Decimal('0.5')  # 0.5% minimum profit
        self.max_position_size = Decimal('100.0')   # Maximum $100 position

        logger.info(f"[WS_V2_INTEGRATION] Initialized for {len(symbols)} symbols")

    async def start(self) -> bool:
        """Start the WebSocket V2 integration"""
        try:
            logger.info("[WS_V2_INTEGRATION] Starting WebSocket V2 trading integration...")

            # Initialize WebSocket V2 manager
            self.websocket_manager = WebSocketV2Manager(
                exchange_client=self.exchange_client,
                api_key=self.api_key,
                private_key=self.private_key,
                config=self.websocket_config,
                enable_debug=True
            )

            # Register event handlers
            self._register_event_handlers()

            # Start WebSocket manager
            started = await self.websocket_manager.start()
            if not started:
                logger.error("[WS_V2_INTEGRATION] Failed to start WebSocket V2 manager")
                return False

            # Subscribe to channels
            await self._setup_subscriptions()

            # Initialize unified data feed
            self.unified_data_feed = UnifiedDataFeed(
                exchange_client=self.exchange_client,
                symbols=self.symbols,
                api_key=self.api_key,
                private_key=self.private_key,
                websocket_config=self.websocket_config,
                enable_debug=True
            )

            # Start unified data feed
            feed_started = await self.unified_data_feed.start()
            if not feed_started:
                logger.warning("[WS_V2_INTEGRATION] Unified data feed failed to start - using WebSocket only")

            logger.info("[WS_V2_INTEGRATION] WebSocket V2 integration started successfully")
            return True

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Failed to start: {e}")
            return False

    async def stop(self) -> None:
        """Stop the WebSocket V2 integration"""
        try:
            logger.info("[WS_V2_INTEGRATION] Stopping WebSocket V2 integration...")

            if self.unified_data_feed:
                await self.unified_data_feed.stop()

            if self.websocket_manager:
                await self.websocket_manager.stop()

            logger.info("[WS_V2_INTEGRATION] WebSocket V2 integration stopped")

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error stopping integration: {e}")

    def _register_event_handlers(self) -> None:
        """Register WebSocket event handlers"""
        if not self.websocket_manager:
            return

        # Register data handlers
        self.websocket_manager.register_handler('balance', self._handle_balance_updates)
        self.websocket_manager.register_handler('ticker', self._handle_ticker_updates)
        self.websocket_manager.register_handler('orderbook', self._handle_orderbook_updates)
        self.websocket_manager.register_handler('order_update', self._handle_order_updates)

        # Register connection handlers
        self.websocket_manager.register_handler('subscription_success', self._handle_subscription_success)
        self.websocket_manager.register_handler('subscription_error', self._handle_subscription_error)

        logger.info("[WS_V2_INTEGRATION] Event handlers registered")

    async def _setup_subscriptions(self) -> None:
        """Setup WebSocket subscriptions"""
        if not self.websocket_manager:
            return

        try:
            # Subscribe to balance updates (private channel)
            if self.websocket_manager.has_private_access:
                await self.websocket_manager.subscribe_channel('balances', private=True)
                logger.info("[WS_V2_INTEGRATION] Subscribed to balance updates")

            # Subscribe to ticker for all symbols
            await self.websocket_manager.subscribe_channel(
                'ticker',
                {'symbol': self.symbols}
            )
            logger.info(f"[WS_V2_INTEGRATION] Subscribed to ticker for {len(self.symbols)} symbols")

            # Subscribe to orderbook for all symbols
            await self.websocket_manager.subscribe_channel(
                'book',
                {'symbol': self.symbols, 'depth': 10}
            )
            logger.info(f"[WS_V2_INTEGRATION] Subscribed to orderbook for {len(self.symbols)} symbols")

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error setting up subscriptions: {e}")

    # Event handlers
    async def _handle_balance_updates(self, balance_updates: list[BalanceUpdate]) -> None:
        """Handle real-time balance updates"""
        try:
            for balance_update in balance_updates:
                asset = balance_update.asset

                # Store current balance
                self.current_balances[asset] = balance_update

                # Log significant balance changes
                if balance_update.free_balance > Decimal('1.0') or asset in ['USDT', 'BTC', 'ETH']:
                    logger.info(f"[WS_V2_INTEGRATION] Balance update: {asset} = {balance_update.free_balance}")

                # Trigger trading logic for USDT balance changes
                if asset == 'USDT':
                    await self._check_trading_opportunities()

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error handling balance updates: {e}")

    async def _handle_ticker_updates(self, ticker_updates: list[TickerUpdate]) -> None:
        """Handle real-time ticker updates"""
        try:
            for ticker_update in ticker_updates:
                symbol = ticker_update.symbol

                # Store current ticker
                self.current_tickers[symbol] = ticker_update

                # Check for trading opportunities on significant price changes
                await self._analyze_price_movement(ticker_update)

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error handling ticker updates: {e}")

    async def _handle_orderbook_updates(self, orderbook_updates: list[OrderBookUpdate]) -> None:
        """Handle real-time orderbook updates"""
        try:
            for orderbook_update in orderbook_updates:
                symbol = orderbook_update.symbol

                # Analyze spread for micro-scalping opportunities
                if orderbook_update.best_bid and orderbook_update.best_ask:
                    spread_pct = (orderbook_update.spread / orderbook_update.best_bid.price) * 100

                    # Log tight spreads that might indicate good liquidity
                    if spread_pct < 0.1:  # Less than 0.1% spread
                        logger.debug(f"[WS_V2_INTEGRATION] Tight spread for {symbol}: {spread_pct:.3f}%")

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error handling orderbook updates: {e}")

    async def _handle_order_updates(self, order_update) -> None:
        """Handle order status updates"""
        try:
            order_id = order_update.order_id
            status = order_update.status

            # Update order tracking
            if order_id in self.active_orders:
                self.active_orders[order_id].update({
                    'status': status,
                    'volume_exec': float(order_update.volume_exec),
                    'cost': float(order_update.cost),
                    'fee': float(order_update.fee)
                })

            # Log important order events
            if status in ['closed', 'canceled']:
                symbol = order_update.symbol
                side = order_update.side
                volume_exec = order_update.volume_exec

                logger.info(f"[WS_V2_INTEGRATION] Order {status}: {symbol} {side} {volume_exec}")

                # Remove from active orders if closed/canceled
                if order_id in self.active_orders:
                    del self.active_orders[order_id]

                # Check for new opportunities after order completion
                if status == 'closed':
                    await self._check_trading_opportunities()

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error handling order update: {e}")

    async def _handle_subscription_success(self, data: dict[str, Any]) -> None:
        """Handle successful subscription"""
        channel = data.get('channel')
        logger.info(f"[WS_V2_INTEGRATION] Successfully subscribed to {channel}")

    async def _handle_subscription_error(self, data: dict[str, Any]) -> None:
        """Handle subscription error"""
        channel = data.get('channel')
        error = data.get('error')
        logger.error(f"[WS_V2_INTEGRATION] Subscription error for {channel}: {error}")

    # Trading logic
    async def _check_trading_opportunities(self) -> None:
        """Check for trading opportunities based on current data"""
        try:
            # Get USDT balance
            usdt_balance = self.current_balances.get('USDT')
            if not usdt_balance or usdt_balance.free_balance < Decimal('10.0'):
                logger.debug("[WS_V2_INTEGRATION] Insufficient USDT balance for trading")
                return

            # Check each symbol for opportunities
            for symbol in self.symbols:
                ticker = self.current_tickers.get(symbol)
                if not ticker:
                    continue

                # Simple trading logic: buy low, sell high
                await self._evaluate_symbol_opportunity(symbol, ticker, usdt_balance)

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error checking trading opportunities: {e}")

    async def _evaluate_symbol_opportunity(
        self,
        symbol: str,
        ticker: TickerUpdate,
        usdt_balance: BalanceUpdate
    ) -> None:
        """Evaluate trading opportunity for a specific symbol"""
        try:
            # Calculate position size (limited to max_position_size)
            available_usdt = min(usdt_balance.free_balance, self.max_position_size)
            position_size = available_usdt / ticker.last

            # Minimum position size check
            if position_size < Decimal('0.001'):
                return

            # Check if we have existing position in this asset
            base_asset = symbol.split('/')[0]
            current_position = self.current_balances.get(base_asset)

            # Simple mean reversion strategy
            if current_position and current_position.free_balance > Decimal('0'):
                # We have position - check for sell opportunity
                await self._check_sell_opportunity(symbol, ticker, current_position)
            else:
                # No position - check for buy opportunity
                await self._check_buy_opportunity(symbol, ticker, position_size)

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error evaluating {symbol}: {e}")

    async def _check_buy_opportunity(self, symbol: str, ticker: TickerUpdate, position_size: Decimal) -> None:
        """Check for buy opportunity"""
        try:
            # Simple buy logic: buy if price dropped significantly
            # In real implementation, you'd use more sophisticated indicators

            # For demonstration, we'll use a simple threshold
            if ticker.last < ticker.vwap * Decimal('0.995'):  # 0.5% below VWAP
                logger.info(f"[WS_V2_INTEGRATION] Buy opportunity detected for {symbol}")

                # Place buy order via WebSocket
                await self._place_buy_order(symbol, position_size, ticker.ask)

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error checking buy opportunity for {symbol}: {e}")

    async def _check_sell_opportunity(
        self,
        symbol: str,
        ticker: TickerUpdate,
        position: BalanceUpdate
    ) -> None:
        """Check for sell opportunity"""
        try:
            # Simple sell logic: sell if price increased sufficiently
            # Calculate potential profit
            sell_price = ticker.bid
            # We'd need to track the average buy price in real implementation
            # For demo, assume we bought at current VWAP
            avg_buy_price = ticker.vwap

            if avg_buy_price > 0:
                profit_pct = ((sell_price - avg_buy_price) / avg_buy_price) * 100

                if profit_pct >= self.min_profit_percentage:
                    logger.info(f"[WS_V2_INTEGRATION] Sell opportunity detected for {symbol} "
                               f"(profit: {profit_pct:.2f}%)")

                    # Place sell order via WebSocket
                    await self._place_sell_order(symbol, position.free_balance, sell_price)

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error checking sell opportunity for {symbol}: {e}")

    async def _place_buy_order(self, symbol: str, volume: Decimal, price: Decimal) -> None:
        """Place buy order via WebSocket V2"""
        try:
            order_manager = self.websocket_manager.get_order_manager()

            # Place limit buy order
            response = await order_manager.place_order(
                symbol=symbol,
                side='buy',
                order_type='limit',
                volume=volume,
                price=price,
                time_in_force='GTC',
                order_flags=['fciq'],  # Fee in quote currency
                validate=True
            )

            if response.error:
                logger.error(f"[WS_V2_INTEGRATION] Buy order failed for {symbol}: {response.error}")
            else:
                logger.info(f"[WS_V2_INTEGRATION] Buy order placed for {symbol}: "
                           f"{volume} @ ${price} (ID: {response.order_id})")

                # Track active order
                if response.order_id:
                    self.active_orders[response.order_id] = {
                        'symbol': symbol,
                        'side': 'buy',
                        'volume': float(volume),
                        'price': float(price),
                        'status': 'open',
                        'timestamp': response.timestamp
                    }

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error placing buy order for {symbol}: {e}")

    async def _place_sell_order(self, symbol: str, volume: Decimal, price: Decimal) -> None:
        """Place sell order via WebSocket V2"""
        try:
            order_manager = self.websocket_manager.get_order_manager()

            # Place limit sell order
            response = await order_manager.place_order(
                symbol=symbol,
                side='sell',
                order_type='limit',
                volume=volume,
                price=price,
                time_in_force='GTC',
                order_flags=['fciq'],  # Fee in quote currency
                validate=True
            )

            if response.error:
                logger.error(f"[WS_V2_INTEGRATION] Sell order failed for {symbol}: {response.error}")
            else:
                logger.info(f"[WS_V2_INTEGRATION] Sell order placed for {symbol}: "
                           f"{volume} @ ${price} (ID: {response.order_id})")

                # Track active order
                if response.order_id:
                    self.active_orders[response.order_id] = {
                        'symbol': symbol,
                        'side': 'sell',
                        'volume': float(volume),
                        'price': float(price),
                        'status': 'open',
                        'timestamp': response.timestamp
                    }

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error placing sell order for {symbol}: {e}")

    async def _analyze_price_movement(self, ticker: TickerUpdate) -> None:
        """Analyze price movement for trading signals"""
        try:
            symbol = ticker.symbol

            # Calculate price change from VWAP
            if ticker.vwap > 0:
                price_change_pct = ((ticker.last - ticker.vwap) / ticker.vwap) * 100

                # Log significant movements
                if abs(price_change_pct) > 1.0:  # More than 1% movement
                    direction = "UP" if price_change_pct > 0 else "DOWN"
                    logger.info(f"[WS_V2_INTEGRATION] {symbol} {direction} {abs(price_change_pct):.2f}% "
                               f"from VWAP (${ticker.last:.6f})")

            # Check spread for liquidity
            spread_pct = (ticker.spread_percentage)
            if spread_pct > 0.5:  # Wide spread warning
                logger.warning(f"[WS_V2_INTEGRATION] Wide spread for {symbol}: {spread_pct:.3f}%")

        except Exception as e:
            logger.error(f"[WS_V2_INTEGRATION] Error analyzing price movement: {e}")

    # Unified data feed examples
    async def get_real_time_balance(self, asset: str) -> dict[str, Any]:
        """Get real-time balance using unified data feed"""
        if self.unified_data_feed:
            return await self.unified_data_feed.get_balance(asset)
        else:
            # Fallback to direct WebSocket data
            balance_update = self.current_balances.get(asset)
            return balance_update.to_dict() if balance_update else None

    async def get_real_time_ticker(self, symbol: str) -> dict[str, Any]:
        """Get real-time ticker using unified data feed"""
        if self.unified_data_feed:
            return await self.unified_data_feed.get_ticker(symbol)
        else:
            # Fallback to direct WebSocket data
            ticker_update = self.current_tickers.get(symbol)
            return ticker_update.to_dict() if ticker_update else None

    async def get_real_time_orderbook(self, symbol: str) -> dict[str, Any]:
        """Get real-time orderbook using unified data feed"""
        if self.unified_data_feed:
            return await self.unified_data_feed.get_orderbook(symbol)
        else:
            # Fallback to WebSocket channel processor
            channel_processor = self.websocket_manager.get_channel_processor()
            orderbook_update = channel_processor.get_latest_orderbook(symbol)
            return orderbook_update.to_dict() if orderbook_update else None

    # Status and monitoring
    def get_integration_status(self) -> dict[str, Any]:
        """Get comprehensive integration status"""
        status = {
            'websocket_manager': self.websocket_manager.get_status() if self.websocket_manager else None,
            'unified_data_feed': self.unified_data_feed.get_status() if self.unified_data_feed else None,
            'active_orders': len(self.active_orders),
            'monitored_symbols': len(self.symbols),
            'balance_updates': len(self.current_balances),
            'ticker_updates': len(self.current_tickers)
        }

        return status

    def get_current_positions(self) -> dict[str, dict[str, Any]]:
        """Get current positions based on balance data"""
        positions = {}

        for asset, balance_update in self.current_balances.items():
            if balance_update.free_balance > Decimal('0.0001'):
                positions[asset] = {
                    'free_balance': float(balance_update.free_balance),
                    'used_balance': float(balance_update.hold_trade),
                    'total_balance': float(balance_update.total_balance),
                    'last_update': balance_update.timestamp
                }

        return positions


# Example usage function
async def run_websocket_v2_example():
    """
    Example function showing how to use WebSocket V2 integration.

    This would typically be called from your main bot initialization.
    """
    try:
        # Configuration
        symbols = ['SHIB/USDT', 'MATIC/USDT', 'AI16Z/USDT', 'BERA/USDT']
        api_key = "your_api_key"
        private_key = "your_private_key"

        # Mock exchange client (replace with your actual exchange client)
        class MockExchangeClient:
            async def get_balance(self, asset):
                return {'free': 100.0, 'used': 0.0, 'total': 100.0}

        exchange_client = MockExchangeClient()

        # Initialize integration
        integration = WebSocketV2TradingIntegration(
            exchange_client=exchange_client,
            symbols=symbols,
            api_key=api_key,
            private_key=private_key
        )

        # Start integration
        started = await integration.start()
        if not started:
            logger.error("Failed to start WebSocket V2 integration")
            return

        logger.info("WebSocket V2 integration started successfully")

        # Run for demonstration (in real bot, this would run indefinitely)
        await asyncio.sleep(60)  # Run for 1 minute

        # Get status
        status = integration.get_integration_status()
        logger.info(f"Integration status: {status}")

        # Get current positions
        positions = integration.get_current_positions()
        logger.info(f"Current positions: {positions}")

        # Stop integration
        await integration.stop()
        logger.info("WebSocket V2 integration stopped")

    except Exception as e:
        logger.error(f"Error in WebSocket V2 example: {e}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run example
    asyncio.run(run_websocket_v2_example())
