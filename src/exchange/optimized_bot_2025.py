"""
Optimized Bot Pattern - Kraken 2025 Compliance
===============================================

Implements the optimal dual-API pattern from the 2025 guide.
Uses WebSocket V2 for real-time data and REST for admin tasks.
"""

import asyncio
import logging
from typing import Optional

from ..utils.kraken_rate_limit_pro import get_rate_limiter
from ..utils.symbol_converter import convert_symbol_format
from .websocket_priority_manager import OperationType, WebSocketPriorityManager

logger = logging.getLogger(__name__)


class OptimizedBot2025:
    """Optimized bot with dual-API pattern for maximum performance"""

    def __init__(self, api_key: str, api_secret: str, config: dict = None):
        """
        Initialize optimized bot

        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
            config: Bot configuration
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = config or {}

        # WebSocket for real-time data
        self.ws = None  # WebSocketV2 instance
        self.ws_connected = False

        # REST for historical/admin
        self.rest = None  # REST API instance

        # Priority manager for optimal routing
        self.priority_manager = None

        # Rate limiter
        self.rate_limiter = get_rate_limiter()

        # Symbols we're tracking
        self.symbols = []

        # Performance metrics
        self.ws_operations = 0
        self.rest_operations = 0

        logger.info("[OPTIMIZED_BOT] Initialized with dual-API pattern")

    async def initialize(self, ws_manager, rest_client):
        """
        Initialize with API clients

        Args:
            ws_manager: WebSocket V2 manager instance
            rest_client: REST API client instance
        """
        self.ws = ws_manager
        self.rest = rest_client

        # Initialize priority manager
        self.priority_manager = WebSocketPriorityManager(
            websocket_manager=self.ws,
            rest_client=self.rest
        )

        logger.info("[OPTIMIZED_BOT] API clients initialized")

    async def start(self, symbols: list[str]):
        """
        Start the optimized bot

        Args:
            symbols: List of trading pairs to track
        """
        try:
            # Convert symbols to WebSocket format
            self.symbols = [convert_symbol_format(s, to_ws=True) for s in symbols]

            logger.info(f"[OPTIMIZED_BOT] Starting with symbols: {self.symbols}")

            # Connect WebSocket for live data
            await self._setup_websocket()

            # Use REST for one-time setup
            await self._setup_account_info()

            # Start main loop
            await self.run()

        except Exception as e:
            logger.error(f"[OPTIMIZED_BOT] Start error: {e}")
            raise

    async def _setup_websocket(self):
        """Setup WebSocket for real-time data"""
        try:
            logger.info("[OPTIMIZED_BOT] Setting up WebSocket V2 for real-time data")

            # Connect with retry logic
            if hasattr(self.ws, 'connect_with_retry'):
                connected = await self.ws.connect_with_retry()
            else:
                connected = await self.ws.connect()

            if not connected:
                logger.error("[OPTIMIZED_BOT] Failed to connect WebSocket")
                return False

            # Subscribe to real-time channels
            subscriptions = []

            # Ticker updates
            subscriptions.append(
                self._subscribe_channel('ticker', self.symbols)
            )

            # Order book updates
            subscriptions.append(
                self._subscribe_channel('book', self.symbols, depth=10)
            )

            # Trade updates
            subscriptions.append(
                self._subscribe_channel('trades', self.symbols)
            )

            # Balance updates (private)
            if self.api_key and self.api_secret:
                subscriptions.append(
                    self._subscribe_channel('balances')
                )

            # Wait for all subscriptions
            results = await asyncio.gather(*subscriptions, return_exceptions=True)

            successful = sum(1 for r in results if r and not isinstance(r, Exception))
            logger.info(f"[OPTIMIZED_BOT] WebSocket subscriptions: {successful}/{len(subscriptions)} successful")

            self.ws_connected = True
            self.ws_operations += len(subscriptions)

            return True

        except Exception as e:
            logger.error(f"[OPTIMIZED_BOT] WebSocket setup error: {e}")
            return False

    async def _subscribe_channel(self, channel: str, symbols: list[str] = None, **kwargs):
        """Subscribe to WebSocket channel"""
        try:
            if channel == 'ticker' and symbols:
                if hasattr(self.ws, 'subscribe_ticker'):
                    return await self.ws.subscribe_ticker(symbols)
            elif channel == 'book' and symbols:
                depth = kwargs.get('depth', 10)
                if hasattr(self.ws, 'subscribe_orderbook'):
                    return await self.ws.subscribe_orderbook(symbols, depth)
            elif channel == 'trades' and symbols:
                if hasattr(self.ws, 'subscribe_trades'):
                    return await self.ws.subscribe_trades(symbols)
            elif channel == 'balances':
                if hasattr(self.ws, 'subscribe_balance'):
                    return await self.ws.subscribe_balance()

            return True

        except Exception as e:
            logger.error(f"[OPTIMIZED_BOT] Error subscribing to {channel}: {e}")
            return False

    async def _setup_account_info(self):
        """Use REST API for one-time account setup"""
        try:
            logger.info("[OPTIMIZED_BOT] Getting account info via REST (one-time)")

            # Get account info once at startup
            if self.rest and hasattr(self.rest, 'get_account_info'):
                await self.rate_limiter.smart_acquire('account')
                account_info = await self.rest.get_account_info()
                self.rest_operations += 1

                logger.info(f"[OPTIMIZED_BOT] Account info retrieved: {account_info.get('result', {}).get('username', 'N/A')}")

            # Get trading fees once
            if self.rest and hasattr(self.rest, 'get_trading_fees'):
                await self.rate_limiter.smart_acquire('fees')
                await self.rest.get_trading_fees()
                self.rest_operations += 1

                logger.info("[OPTIMIZED_BOT] Trading fees retrieved")

            return True

        except Exception as e:
            logger.error(f"[OPTIMIZED_BOT] Account setup error: {e}")
            return False

    async def run(self):
        """Main bot loop - process real-time data from WebSocket"""
        logger.info("[OPTIMIZED_BOT] Starting main loop with WebSocket priority")

        while self.ws_connected:
            try:
                # Process WebSocket data (real-time)
                await self._process_websocket_data()

                # Minimal REST usage (only for required operations)
                if asyncio.get_event_loop().time() % 300 < 1:  # Every 5 minutes
                    await self._periodic_rest_tasks()

                # Short sleep to prevent CPU spinning
                await asyncio.sleep(0.1)

            except KeyboardInterrupt:
                logger.info("[OPTIMIZED_BOT] Stopping on user request")
                break
            except Exception as e:
                logger.error(f"[OPTIMIZED_BOT] Main loop error: {e}")
                await asyncio.sleep(1)

    async def _process_websocket_data(self):
        """Process real-time WebSocket data"""
        if not self.ws:
            return

        # Get latest ticker data
        for symbol in self.symbols:
            if hasattr(self.ws, 'get_ticker'):
                ticker = self.ws.get_ticker(symbol)
                if ticker:
                    self.ws_operations += 1
                    # Process ticker data
                    await self._handle_ticker_update(symbol, ticker)

    async def _handle_ticker_update(self, symbol: str, ticker: dict):
        """Handle ticker update from WebSocket"""
        # Implement your trading logic here
        pass

    async def _periodic_rest_tasks(self):
        """Periodic tasks using REST API"""
        try:
            # Only use REST for tasks that can't be done via WebSocket
            if self.rest and hasattr(self.rest, 'get_historical_trades'):
                # Example: Get historical data for analysis
                await self.rate_limiter.smart_acquire('history')
                # historical = await self.rest.get_historical_trades(self.symbols[0])
                self.rest_operations += 1

        except Exception as e:
            logger.error(f"[OPTIMIZED_BOT] Periodic REST task error: {e}")

    def get_statistics(self) -> dict:
        """Get bot performance statistics"""
        total_ops = self.ws_operations + self.rest_operations

        stats = {
            'total_operations': total_ops,
            'websocket_operations': self.ws_operations,
            'rest_operations': self.rest_operations,
            'ws_percentage': (self.ws_operations / total_ops * 100) if total_ops > 0 else 0,
            'rest_percentage': (self.rest_operations / total_ops * 100) if total_ops > 0 else 0,
            'websocket_connected': self.ws_connected,
            'symbols_tracked': len(self.symbols)
        }

        # Add priority manager stats if available
        if self.priority_manager:
            stats['routing_stats'] = self.priority_manager.get_statistics()

        # Add rate limiter stats
        stats['rate_limit_stats'] = self.rate_limiter.get_statistics()

        return stats

    async def place_order_optimized(self, symbol: str, side: str, quantity: str, price: Optional[str] = None):
        """Place order using optimal routing"""
        if not self.priority_manager:
            logger.error("[OPTIMIZED_BOT] Priority manager not initialized")
            return None

        # Convert symbol to appropriate format
        ws_symbol = convert_symbol_format(symbol, to_ws=True)

        # Use priority manager for optimal routing
        result = await self.priority_manager.execute_operation(
            OperationType.ORDER_PLACE,
            symbol=ws_symbol,
            side=side,
            quantity=quantity,
            price=price
        )

        return result

    async def shutdown(self):
        """Gracefully shutdown the bot"""
        logger.info("[OPTIMIZED_BOT] Shutting down...")

        self.ws_connected = False

        if self.ws:
            await self.ws.disconnect()

        stats = self.get_statistics()
        logger.info(f"[OPTIMIZED_BOT] Final stats: WS={stats['ws_percentage']:.1f}%, REST={stats['rest_percentage']:.1f}%")
        logger.info("[OPTIMIZED_BOT] Shutdown complete")
