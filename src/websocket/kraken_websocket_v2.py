"""
Kraken WebSocket V2 Client
===========================

High-performance WebSocket V2 implementation for Kraken exchange with:
- Authenticated balance streaming
- Real-time market data (ticker, orderbook, trades, OHLC)
- Automatic connection management and reconnection
- Message queuing and event-driven architecture
- Thread-safe operations and rate limiting
- Integration with existing authentication system
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..utils.decimal_precision_fix import safe_decimal
from .connection_manager import ConnectionConfig, ConnectionManager
from .data_models import (
    BalanceUpdate,
    OHLCUpdate,
    OrderBookUpdate,
    SubscriptionRequest,
    SubscriptionResponse,
    TickerUpdate,
    TradeUpdate,
)
from .kraken_v2_message_handler import KrakenV2MessageHandler

logger = logging.getLogger(__name__)


@dataclass
class KrakenWebSocketConfig:
    """Kraken WebSocket V2 configuration"""

    # WebSocket endpoints
    public_url: str = "wss://ws.kraken.com/v2"
    private_url: str = "wss://ws-auth.kraken.com/v2"

    # Connection settings
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    reconnect_delay: float = 1.0
    max_reconnect_attempts: int = 10

    # Message settings
    message_queue_size: int = 10000
    heartbeat_timeout: float = 60.0

    # Rate limiting
    subscription_rate_limit: int = 5  # Max subscriptions per second

    # Authentication
    token_refresh_interval: float = 10 * 60  # 10 minutes (5 min before expiry for safety)


class KrakenWebSocketV2:
    """
    Main WebSocket V2 client for Kraken exchange
    """

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        config: Optional[KrakenWebSocketConfig] = None,
    ):
        """
        Initialize Kraken WebSocket V2 client

        Args:
            api_key: Kraken API key for authentication
            api_secret: Kraken API secret for authentication
            config: WebSocket configuration
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = config or KrakenWebSocketConfig()

        # Connection managers for public and private channels
        self.public_connection: Optional[ConnectionManager] = None
        self.private_connection: Optional[ConnectionManager] = None

        # Message handler
        self.message_handler = KrakenV2MessageHandler(
            enable_sequence_tracking=True, enable_statistics=True
        )

        # Authentication
        self.auth_token: Optional[str] = None
        self.token_created_time: float = 0
        self.exchange_client: Optional[Any] = None  # Reference to exchange client for token refresh

        # Subscription tracking
        self.active_subscriptions: dict[str, dict[str, Any]] = {}
        self.subscription_lock = asyncio.Lock()

        # Data storage
        self.balance_data: dict[str, BalanceUpdate] = {}
        self.ticker_data: dict[str, TickerUpdate] = {}
        self.orderbook_data: dict[str, OrderBookUpdate] = {}
        self.trade_data: dict[str, list[TradeUpdate]] = {}
        self.ohlc_data: dict[str, list[OHLCUpdate]] = {}

        # Callbacks
        self.callbacks: dict[str, list[Callable]] = {
            "balance": [],
            "ticker": [],
            "orderbook": [],
            "trade": [],
            "ohlc": [],
            "connected": [],
            "disconnected": [],
            "error": [],
            "authenticated": [],
        }

        # Status tracking
        self.is_running = False
        self.last_message_time = 0
        self.connection_start_time = 0

        # Rate limiting for subscriptions
        self.subscription_timestamps: list[float] = []

        logger.info("[KRAKEN_WS_V2] Initialized WebSocket V2 client")

    def set_exchange_client(self, exchange_client):
        """Set reference to exchange client for token refresh"""
        self.exchange_client = exchange_client
        logger.info("[KRAKEN_WS_V2] Exchange client reference set")

    async def connect(self, private_channels: bool = True) -> bool:
        """
        Connect to Kraken WebSocket V2

        Args:
            private_channels: Whether to connect to private channels

        Returns:
            bool: True if connection successful
        """
        if self.is_running:
            logger.warning("[KRAKEN_WS_V2] Already connected")
            return True

        logger.info("[KRAKEN_WS_V2] Starting WebSocket V2 connection")

        try:
            # Initialize message handler for WebSocket V2 processing
            logger.debug("[KRAKEN_WS_V2] Initializing message handler for V2 processing")

            # Set up message handler callbacks
            self._setup_message_callbacks()

            # Connect to public channels
            success = await self._connect_public()
            if not success:
                logger.error("[KRAKEN_WS_V2] Failed to connect to public channels")
                return False

            # Connect to private channels if requested and credentials available
            if private_channels and self.api_key and self.api_secret:
                auth_success = await self._connect_private()
                if not auth_success:
                    logger.warning(
                        "[KRAKEN_WS_V2] Failed to connect to private channels, continuing with public only"
                    )

            self.is_running = True
            self.connection_start_time = time.time()

            logger.info("[KRAKEN_WS_V2] WebSocket V2 connection established")

            # Call connected callbacks
            await self._call_callbacks("connected")

            return True

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Connection error: {e}")
            await self._call_callbacks("error", e)
            return False

    async def disconnect(self):
        """Disconnect from WebSocket V2"""
        if not self.is_running:
            return

        logger.info("[KRAKEN_WS_V2] Disconnecting WebSocket V2")

        self.is_running = False

        # Disconnect connection managers
        if self.public_connection:
            await self.public_connection.disconnect()

        if self.private_connection:
            await self.private_connection.disconnect()

        # Shutdown message handler
        if self.message_handler:
            self.message_handler.shutdown()

        # Clear data
        self.active_subscriptions.clear()

        # Call disconnected callbacks
        await self._call_callbacks("disconnected")

        logger.info("[KRAKEN_WS_V2] WebSocket V2 disconnected")

    async def _connect_public(self) -> bool:
        """Connect to public WebSocket channels"""
        try:
            # Create connection config
            config = ConnectionConfig(
                url=self.config.public_url,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout,
                max_reconnect_attempts=self.config.max_reconnect_attempts,
                reconnect_delay=self.config.reconnect_delay,
                heartbeat_timeout=self.config.heartbeat_timeout,
            )

            # Create connection manager
            self.public_connection = ConnectionManager(config)

            # Set up callbacks
            self.public_connection.set_callback("message", self._handle_public_message)
            self.public_connection.set_callback("error", self._handle_connection_error)

            # Connect
            success = await self.public_connection.connect()

            if success:
                logger.info("[KRAKEN_WS_V2] Connected to public channels")
            else:
                logger.error("[KRAKEN_WS_V2] Failed to connect to public channels")

            return success

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error connecting to public channels: {e}")
            return False

    async def _connect_private(self) -> bool:
        """Connect to private WebSocket channels"""
        try:
            # Get authentication token
            if not await self._get_auth_token():
                logger.error("[KRAKEN_WS_V2] Failed to get authentication token")
                return False

            # Create connection config for private channels
            config = ConnectionConfig(
                url=self.config.private_url,
                auth_url=self.config.private_url,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout,
                max_reconnect_attempts=self.config.max_reconnect_attempts,
                reconnect_delay=self.config.reconnect_delay,
                heartbeat_timeout=self.config.heartbeat_timeout,
            )

            # Create connection manager
            self.private_connection = ConnectionManager(config)

            # Set up callbacks
            self.private_connection.set_callback("message", self._handle_private_message)
            self.private_connection.set_callback("authenticated", self._handle_authentication)
            self.private_connection.set_callback("error", self._handle_connection_error)

            # Connect with authentication token
            success = await self.private_connection.connect(self.auth_token)

            if success:
                logger.info("[KRAKEN_WS_V2] Connected to private channels")
            else:
                logger.error("[KRAKEN_WS_V2] Failed to connect to private channels")

            return success

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error connecting to private channels: {e}")
            return False

    async def _get_auth_token(self) -> bool:
        """Get WebSocket authentication token"""
        if not self.exchange_client:
            logger.error("[KRAKEN_WS_V2] No exchange client set for token retrieval")
            return False

        try:
            # Try different token methods
            if hasattr(self.exchange_client, "get_websocket_token"):
                token_response = await self.exchange_client.get_websocket_token()
                if isinstance(token_response, str):
                    self.auth_token = token_response
                elif isinstance(token_response, dict) and "token" in token_response:
                    self.auth_token = token_response["token"]
                else:
                    logger.error(f"[KRAKEN_WS_V2] Invalid token response: {token_response}")
                    return False
            elif hasattr(self.exchange_client, "get_websockets_token"):
                token_response = await self.exchange_client.get_websockets_token()
                if isinstance(token_response, dict) and "token" in token_response:
                    self.auth_token = token_response["token"]
                else:
                    logger.error(f"[KRAKEN_WS_V2] Invalid token response: {token_response}")
                    return False
            else:
                logger.error("[KRAKEN_WS_V2] Exchange client doesn't support WebSocket tokens")
                return False

            self.token_created_time = time.time()
            logger.info("[KRAKEN_WS_V2] Authentication token obtained successfully")

            # Schedule token refresh
            asyncio.create_task(self._token_refresh_loop())

            return True

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error getting auth token: {e}")
            return False

    async def _token_refresh_loop(self):
        """Background task to refresh authentication token and maintain connection"""
        while self.is_running and self.private_connection and self.private_connection.is_connected:
            try:
                # Wait until refresh is needed (10 minutes)
                await asyncio.sleep(self.config.token_refresh_interval)

                if not self.is_running:
                    break

                logger.info("[KRAKEN_WS_V2] Refreshing authentication token to maintain connection")

                # Get new token
                if await self._get_auth_token():
                    logger.info("[KRAKEN_WS_V2] Token refreshed successfully")

                    # Re-subscribe to maintain active subscriptions
                    if "balances" in self.active_subscriptions:
                        logger.info("[KRAKEN_WS_V2] Re-subscribing to balance updates")
                        await self.subscribe_balance()
                else:
                    logger.error("[KRAKEN_WS_V2] Token refresh failed - connection may be lost")
                    # Try to reconnect if token refresh fails
                    await self._connect_private()

            except Exception as e:
                logger.error(f"[KRAKEN_WS_V2] Token refresh error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

    def _setup_message_callbacks(self):
        """Set up message handler callbacks"""
        self.message_handler.register_callback("balance", self._handle_balance_updates)
        self.message_handler.register_callback("balances", self._handle_balance_updates)
        self.message_handler.register_callback("ticker", self._handle_ticker_updates)
        self.message_handler.register_callback("book", self._handle_orderbook_updates)
        self.message_handler.register_callback("orderbook", self._handle_orderbook_updates)
        self.message_handler.register_callback("trade", self._handle_trade_updates)
        self.message_handler.register_callback("ohlc", self._handle_ohlc_updates)
        self.message_handler.register_callback("subscription", self._handle_subscription_response)

    async def _handle_public_message(self, message: dict[str, Any]):
        """Handle public channel messages"""
        self.last_message_time = time.time()
        await self.message_handler.process_message(message)

    async def _handle_private_message(self, message: dict[str, Any]):
        """Handle private channel messages"""
        self.last_message_time = time.time()
        await self.message_handler.process_message(message)

    async def _handle_authentication(self):
        """Handle successful authentication"""
        logger.info("[KRAKEN_WS_V2] Authentication successful")
        await self._call_callbacks("authenticated")

    async def _handle_connection_error(self, error: Exception):
        """Handle connection errors"""
        logger.error(f"[KRAKEN_WS_V2] Connection error: {error}")
        await self._call_callbacks("error", error)

    async def _handle_balance_updates(self, balance_updates: list[BalanceUpdate]):
        """Handle balance update messages"""
        try:
            logger.info(f"[KRAKEN_WS_V2] Processing {len(balance_updates)} balance updates")

            # Update local balance data
            for balance_update in balance_updates:
                self.balance_data[balance_update.asset] = balance_update
                logger.debug(
                    f"[KRAKEN_WS_V2] Updated balance: {balance_update.asset} = {balance_update.free_balance}"
                )

            # Call balance callbacks
            await self._call_callbacks("balance", balance_updates)

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error handling balance updates: {e}")

    async def _handle_ticker_updates(self, ticker_updates: list[TickerUpdate]):
        """Handle ticker update messages"""
        try:
            # Update local ticker data
            for ticker_update in ticker_updates:
                self.ticker_data[ticker_update.symbol] = ticker_update
                logger.debug(
                    f"[KRAKEN_WS_V2] Updated ticker: {ticker_update.symbol} = ${ticker_update.last}"
                )

            # Call ticker callbacks
            await self._call_callbacks("ticker", ticker_updates)

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error handling ticker updates: {e}")

    async def _handle_orderbook_updates(self, orderbook_updates: list[OrderBookUpdate]):
        """Handle orderbook update messages"""
        try:
            # Update local orderbook data
            for orderbook_update in orderbook_updates:
                self.orderbook_data[orderbook_update.symbol] = orderbook_update
                logger.debug(f"[KRAKEN_WS_V2] Updated orderbook: {orderbook_update.symbol}")

            # Call orderbook callbacks
            await self._call_callbacks("orderbook", orderbook_updates)

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error handling orderbook updates: {e}")

    async def _handle_trade_updates(self, trade_updates: list[TradeUpdate]):
        """Handle trade update messages"""
        try:
            # Update local trade data
            for trade_update in trade_updates:
                if trade_update.symbol not in self.trade_data:
                    self.trade_data[trade_update.symbol] = []

                self.trade_data[trade_update.symbol].append(trade_update)

                # Keep only recent trades (last 100)
                if len(self.trade_data[trade_update.symbol]) > 100:
                    self.trade_data[trade_update.symbol] = self.trade_data[trade_update.symbol][
                        -100:
                    ]

                logger.debug(
                    f"[KRAKEN_WS_V2] New trade: {trade_update.symbol} {trade_update.side} {trade_update.volume} @ ${trade_update.price}"
                )

            # Call trade callbacks
            await self._call_callbacks("trade", trade_updates)

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error handling trade updates: {e}")

    async def _handle_ohlc_updates(self, ohlc_updates: list[OHLCUpdate]):
        """Handle OHLC update messages"""
        try:
            # Update local OHLC data
            for ohlc_update in ohlc_updates:
                if ohlc_update.symbol not in self.ohlc_data:
                    self.ohlc_data[ohlc_update.symbol] = []

                self.ohlc_data[ohlc_update.symbol].append(ohlc_update)

                # Keep only recent candles (last 1000)
                if len(self.ohlc_data[ohlc_update.symbol]) > 1000:
                    self.ohlc_data[ohlc_update.symbol] = self.ohlc_data[ohlc_update.symbol][-1000:]

                logger.debug(
                    f"[KRAKEN_WS_V2] New OHLC: {ohlc_update.symbol} close=${ohlc_update.close}"
                )

            # Call OHLC callbacks
            await self._call_callbacks("ohlc", ohlc_updates)

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error handling OHLC updates: {e}")

    async def _handle_subscription_response(self, response: SubscriptionResponse):
        """Handle subscription responses"""
        try:
            channel = response.result.get("channel", "unknown")

            if response.success:
                logger.info(f"[KRAKEN_WS_V2] Subscription successful: {channel}")
                # Track active subscription
                async with self.subscription_lock:
                    self.active_subscriptions[channel] = {
                        "timestamp": time.time(),
                        "req_id": response.req_id,
                        "params": response.result,
                    }
            else:
                logger.error(f"[KRAKEN_WS_V2] Subscription failed: {channel} - {response.error}")

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error handling subscription response: {e}")

    # Public API Methods

    def register_callback(self, event_type: str, callback: Callable):
        """
        Register callback for WebSocket events

        Args:
            event_type: Type of event ('balance', 'ticker', 'orderbook', 'trade', 'ohlc', 'connected', 'disconnected', 'error', 'authenticated')
            callback: Async callback function
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            logger.info(f"[KRAKEN_WS_V2] Registered callback for {event_type}")
        else:
            logger.warning(f"[KRAKEN_WS_V2] Unknown event type: {event_type}")

    def unregister_callback(self, event_type: str, callback: Callable):
        """Remove callback for event type"""
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            logger.info(f"[KRAKEN_WS_V2] Unregistered callback for {event_type}")

    async def subscribe_balance(self) -> bool:
        """Subscribe to balance updates (requires authentication)"""
        if not self.private_connection or not self.private_connection.is_authenticated:
            logger.error("[KRAKEN_WS_V2] Private connection required for balance subscription")
            return False

        subscription = SubscriptionRequest(method="subscribe", params={"channel": "balances"})

        return await self._send_subscription(subscription, private=True)

    async def subscribe_ticker(self, symbols: list[str]) -> bool:
        """
        Subscribe to ticker updates for symbols

        Args:
            symbols: List of trading pairs (e.g., ['BTC/USDT', 'ETH/USDT'])
        """
        subscription = SubscriptionRequest(
            method="subscribe", params={"channel": "ticker", "symbol": symbols}
        )

        return await self._send_subscription(subscription, private=False)

    async def subscribe_orderbook(self, symbols: list[str], depth: int = 10) -> bool:
        """
        Subscribe to orderbook updates for symbols

        Args:
            symbols: List of trading pairs
            depth: Orderbook depth (10, 25, 100, 500, 1000)
        """
        subscription = SubscriptionRequest(
            method="subscribe", params={"channel": "book", "symbol": symbols, "depth": depth}
        )

        return await self._send_subscription(subscription, private=False)

    async def subscribe_trades(self, symbols: list[str]) -> bool:
        """
        Subscribe to trade updates for symbols

        Args:
            symbols: List of trading pairs
        """
        subscription = SubscriptionRequest(
            method="subscribe", params={"channel": "trade", "symbol": symbols}
        )

        return await self._send_subscription(subscription, private=False)

    async def subscribe_ohlc(self, symbols: list[str], interval: int = 1) -> bool:
        """
        Subscribe to OHLC updates for symbols

        Args:
            symbols: List of trading pairs
            interval: OHLC interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
        """
        subscription = SubscriptionRequest(
            method="subscribe", params={"channel": "ohlc", "symbol": symbols, "interval": interval}
        )

        return await self._send_subscription(subscription, private=False)

    async def unsubscribe(self, channel: str, symbols: list[str] = None) -> bool:
        """
        Unsubscribe from channel

        Args:
            channel: Channel name to unsubscribe from
            symbols: Symbols to unsubscribe (if applicable)
        """
        params = {"channel": channel}
        if symbols:
            params["symbol"] = symbols

        subscription = SubscriptionRequest(method="unsubscribe", params=params)

        # Determine if private or public channel
        private_channels = ["balances", "executions", "openOrders"]
        is_private = channel in private_channels

        return await self._send_subscription(subscription, private=is_private)

    async def _send_subscription(
        self, subscription: SubscriptionRequest, private: bool = False
    ) -> bool:
        """Send subscription request"""
        try:
            # Rate limiting check
            if not await self._check_subscription_rate_limit():
                logger.warning("[KRAKEN_WS_V2] Subscription rate limit exceeded")
                return False

            # Choose connection
            connection = self.private_connection if private else self.public_connection

            if not connection or not connection.is_connected:
                logger.error(
                    f"[KRAKEN_WS_V2] No {'private' if private else 'public'} connection available"
                )
                return False

            # Send subscription
            success = await connection.send_message(subscription.to_dict())

            if success:
                logger.info(
                    f"[KRAKEN_WS_V2] Sent subscription: {subscription.params.get('channel', 'unknown')}"
                )
            else:
                logger.error(
                    f"[KRAKEN_WS_V2] Failed to send subscription: {subscription.params.get('channel', 'unknown')}"
                )

            return success

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Error sending subscription: {e}")
            return False

    async def _check_subscription_rate_limit(self) -> bool:
        """Check subscription rate limiting"""
        current_time = time.time()

        # Clean old timestamps
        self.subscription_timestamps = [
            ts
            for ts in self.subscription_timestamps
            if current_time - ts < 1.0  # 1 second window
        ]

        # Check rate limit
        if len(self.subscription_timestamps) >= self.config.subscription_rate_limit:
            return False

        # Add current timestamp
        self.subscription_timestamps.append(current_time)
        return True

    # Data Access Methods

    def get_balance(self, asset: str) -> Optional[dict[str, Any]]:
        """Get current balance for asset"""
        balance_update = self.balance_data.get(asset)
        if balance_update:
            return balance_update.to_dict()
        return None

    def get_all_balances(self) -> dict[str, dict[str, Any]]:
        """Get all current balances"""
        return {
            asset: balance_update.to_dict() for asset, balance_update in self.balance_data.items()
        }

    def get_ticker(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get current ticker for symbol"""
        ticker_update = self.ticker_data.get(symbol)
        if ticker_update:
            return ticker_update.to_dict()
        return None

    def get_orderbook(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get current orderbook for symbol"""
        orderbook_update = self.orderbook_data.get(symbol)
        if orderbook_update:
            return orderbook_update.to_dict()
        return None

    def get_recent_trades(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent trades for symbol"""
        trades = self.trade_data.get(symbol, [])
        recent_trades = trades[-limit:] if len(trades) > limit else trades
        return [trade.to_dict() for trade in recent_trades]

    def get_ohlc_data(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get OHLC data for symbol"""
        ohlc_list = self.ohlc_data.get(symbol, [])
        recent_ohlc = ohlc_list[-limit:] if len(ohlc_list) > limit else ohlc_list
        return [ohlc.to_dict() for ohlc in recent_ohlc]

    # Status and Monitoring

    def get_connection_status(self) -> dict[str, Any]:
        """Get detailed connection status"""
        status = {
            "is_running": self.is_running,
            "connection_start_time": self.connection_start_time,
            "uptime": time.time() - self.connection_start_time
            if self.connection_start_time > 0
            else 0,
            "last_message_time": self.last_message_time,
            "public_connection": None,
            "private_connection": None,
            "active_subscriptions": len(self.active_subscriptions),
            "subscription_details": dict(self.active_subscriptions),
            "message_handler_stats": self.message_handler.get_statistics(),
            "data_counts": {
                "balances": len(self.balance_data),
                "tickers": len(self.ticker_data),
                "orderbooks": len(self.orderbook_data),
                "trade_symbols": len(self.trade_data),
                "ohlc_symbols": len(self.ohlc_data),
            },
        }

        # Add connection manager status
        if self.public_connection:
            status["public_connection"] = self.public_connection.get_status()

        if self.private_connection:
            status["private_connection"] = self.private_connection.get_status()

        return status

    def is_connected(self) -> bool:
        """Check if any connection is active"""
        public_connected = self.public_connection and self.public_connection.is_connected
        private_connected = self.private_connection and self.private_connection.is_connected
        return public_connected or private_connected

    def is_authenticated(self) -> bool:
        """Check if private connection is authenticated"""
        return self.private_connection and self.private_connection.is_authenticated

    async def _call_callbacks(self, event_type: str, data: Any = None):
        """Call registered callbacks for event type"""
        callbacks = self.callbacks.get(event_type, [])

        for callback in callbacks:
            try:
                if data is not None:
                    await callback(data)
                else:
                    await callback()
            except Exception as e:
                logger.error(f"[KRAKEN_WS_V2] Callback error for {event_type}: {e}")

    # Integration Methods for Existing Code

    def get_balance_streaming_status(self) -> dict[str, Any]:
        """Get balance streaming status for compatibility with existing code"""
        return {
            "websocket_connected": self.is_connected(),
            "websocket_healthy": self.is_connected()
            and (time.time() - self.last_message_time) < 60,
            "auth_token_available": bool(self.auth_token),
            "balance_data_count": len(self.balance_data),
            "private_connection_available": bool(self.private_connection),
            "private_connection_authenticated": self.is_authenticated(),
            "last_message_time": self.last_message_time,
            "time_since_last_message": time.time() - self.last_message_time
            if self.last_message_time > 0
            else float("inf"),
            "streaming_healthy": self.is_connected() and self.is_authenticated(),
        }

    async def test_balance_format_conversion(self) -> bool:
        """Test balance format conversion for compatibility"""
        try:
            # Simulate test balance data
            test_data = [
                BalanceUpdate(
                    asset="USDT", balance=safe_decimal("100.50"), hold_trade=safe_decimal("0")
                ),
                BalanceUpdate(
                    asset="BTC", balance=safe_decimal("0.001"), hold_trade=safe_decimal("0.0005")
                ),
            ]

            # Process test data
            await self._handle_balance_updates(test_data)

            # Check if data was processed correctly
            usdt_balance = self.get_balance("USDT")
            if usdt_balance and usdt_balance["free"] == 100.50:
                logger.info("[KRAKEN_WS_V2] Balance format conversion test successful")
                return True
            else:
                logger.error("[KRAKEN_WS_V2] Balance format conversion test failed")
                return False

        except Exception as e:
            logger.error(f"[KRAKEN_WS_V2] Balance format test error: {e}")
            return False
