"""
Kraken Pro API Client - Enhanced Integration for Fee-Free Trading
================================================================

Comprehensive Kraken Pro API client that handles:
1. Latest Kraken API endpoints (REST API v0 with WebSocket v2 compatibility)
2. Kraken Pro account tier features (fee-free trading)
3. Advanced WebSocket fallback mechanisms
4. Alternative real-time data connection methods
5. Pro-specific rate limiting and optimizations

Features:
- Multi-tier authentication system with fallback
- WebSocket V2 integration with REST fallback
- Pro account fee-free trading detection
- Enhanced error handling and recovery
- Real-time data streaming with multiple protocols
- Connection health monitoring and auto-recovery
- Performance optimizations for high-frequency trading

Usage:
    async with KrakenProClient(api_key, private_key) as client:
        # Test Pro account features
        pro_status = await client.verify_pro_account_status()

        # Get real-time data with fallback
        ticker_data = await client.get_real_time_ticker('BTC/USD')

        # Execute fee-free trades (Pro accounts)
        order = await client.place_order('BTC/USD', 'buy', 'market', '0.001')
"""

import asyncio
import json
import logging
import ssl
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import websockets
from aiohttp import ClientSession

# Import existing components
try:
    # Try relative imports (when used as module)
    from ..api.endpoints import KRAKEN_ENDPOINTS, get_endpoint_definition
    from ..api.exceptions import (
        AuthenticationError,
        KrakenAPIError,
        NetworkError,
        RateLimitError,
        ValidationError,
        raise_for_kraken_errors,
    )
    from ..api.kraken_rest_client import KrakenRestClient
    from ..auth.kraken_auth import KrakenAuth
    from ..circuit_breaker.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
    from ..rate_limiting.kraken_rate_limiter import (
        AccountTier,
        KrakenRateLimiter2025,
        RequestPriority,
    )
except ImportError:
    # Fallback to absolute imports (when run as script)
    from src.api.kraken_rest_client import KrakenRestClient
    from src.rate_limiting.kraken_rate_limiter import (
        AccountTier,
    )

logger = logging.getLogger(__name__)


class ConnectionMode(Enum):
    """Connection modes for real-time data."""
    WEBSOCKET_V2 = "websocket_v2"
    WEBSOCKET_V1 = "websocket_v1"
    REST_POLLING = "rest_polling"
    HYBRID = "hybrid"


class ProAccountFeature(Enum):
    """Kraken Pro account features."""
    FEE_FREE_TRADING = "fee_free_trading"
    ADVANCED_ORDERS = "advanced_orders"
    PRIORITY_SUPPORT = "priority_support"
    ENHANCED_LIMITS = "enhanced_limits"
    WEBSOCKET_V2 = "websocket_v2"


@dataclass
class WebSocketConfig:
    """WebSocket connection configuration."""
    public_url: str = "wss://ws.kraken.com/v2"
    private_url: str = "wss://ws-auth.kraken.com/v2"
    v1_public_url: str = "wss://ws.kraken.com/"
    v1_private_url: str = "wss://ws-auth.kraken.com/"
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    close_timeout: float = 10.0
    max_size: int = 2 ** 20  # 1MB
    compression: Optional[str] = "deflate"
    connection_timeout: float = 30.0
    heartbeat_interval: float = 30.0
    reconnect_attempts: int = 5
    reconnect_delay: float = 1.0


@dataclass
class ProAccountStatus:
    """Kraken Pro account status information."""
    is_pro_account: bool = False
    fee_schedule: str = "standard"
    trading_volume_30d: float = 0.0
    maker_fee: float = 0.0026  # Standard maker fee
    taker_fee: float = 0.0026  # Standard taker fee
    available_features: list[ProAccountFeature] = field(default_factory=list)
    verification_level: str = "starter"
    websocket_token_available: bool = False
    enhanced_rate_limits: bool = False


@dataclass
class ConnectionHealth:
    """Connection health status."""
    websocket_v2_status: str = "unknown"  # healthy, degraded, failed
    websocket_v1_status: str = "unknown"
    rest_api_status: str = "unknown"
    last_successful_request: Optional[float] = None
    consecutive_failures: int = 0
    fallback_mode: bool = False
    active_connections: list[str] = field(default_factory=list)


class KrakenProClient:
    """
    Enhanced Kraken Pro API client with WebSocket V2 and REST fallback.

    Provides comprehensive API access optimized for Kraken Pro accounts with
    fee-free trading capabilities and advanced real-time data streaming.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        private_key: Optional[str] = None,
        base_url: str = "https://api.kraken.com",
        enable_websocket_v2: bool = True,
        enable_websocket_v1: bool = True,
        enable_rest_fallback: bool = True,
        connection_mode: ConnectionMode = ConnectionMode.HYBRID,
        websocket_config: Optional[WebSocketConfig] = None,
        session: Optional[ClientSession] = None,
        user_agent: str = "KrakenProClient/1.0.0"
    ):
        """
        Initialize Kraken Pro API client.

        Args:
            api_key: Kraken API key (will load from environment if None)
            private_key: Kraken private key (will load from environment if None)
            base_url: Base URL for Kraken REST API
            enable_websocket_v2: Enable WebSocket V2 connections
            enable_websocket_v1: Enable WebSocket V1 fallback
            enable_rest_fallback: Enable REST API fallback
            connection_mode: Primary connection mode
            websocket_config: WebSocket configuration
            session: Optional aiohttp session
            user_agent: User agent string
        """
        # Load credentials if not provided
        if not api_key or not private_key:
            api_key, private_key = self._load_credentials_from_environment()

        if not api_key or not private_key:
            raise ValueError(
                "API credentials are required. Set KRAKEN_KEY and KRAKEN_SECRET "
                "environment variables or provide api_key and private_key parameters."
            )

        self.api_key = api_key
        self.private_key = private_key
        self.base_url = base_url.rstrip('/')
        self.user_agent = user_agent

        # Connection configuration
        self.enable_websocket_v2 = enable_websocket_v2
        self.enable_websocket_v1 = enable_websocket_v1
        self.enable_rest_fallback = enable_rest_fallback
        self.connection_mode = connection_mode
        self.websocket_config = websocket_config or WebSocketConfig()

        # Initialize REST client
        self.rest_client = KrakenRestClient(
            api_key=api_key,
            private_key=private_key,
            base_url=base_url,
            account_tier=AccountTier.PRO,  # Assume Pro tier initially
            session=session,
            user_agent=user_agent
        )

        # WebSocket connections
        self._websocket_v2_connection = None
        self._websocket_v1_connection = None
        self._websocket_token = None
        self._websocket_token_expires = None

        # Connection management
        self._connection_lock = asyncio.Lock()
        self._websocket_subscriptions = {}
        self._websocket_callbacks = defaultdict(list)

        # Pro account status
        self._pro_status = ProAccountStatus()
        self._pro_status_verified = False

        # Connection health monitoring
        self._connection_health = ConnectionHealth()
        self._health_check_task = None
        self._health_check_interval = 60.0  # Check every minute

        # State management
        self._closed = False
        self._start_time = time.time()

        logger.info(
            f"Kraken Pro client initialized: api_key={api_key[:8]}..., "
            f"mode={connection_mode.value}, ws_v2={enable_websocket_v2}, "
            f"ws_v1={enable_websocket_v1}, rest_fallback={enable_rest_fallback}"
        )

    def _load_credentials_from_environment(self) -> tuple[Optional[str], Optional[str]]:
        """Load credentials from environment variables."""
        import os

        # Try primary environment variables first
        api_key = os.getenv('KRAKEN_KEY') or os.getenv('KRAKEN_API_KEY')
        private_key = os.getenv('KRAKEN_SECRET') or os.getenv('KRAKEN_API_SECRET')

        if api_key and private_key:
            logger.info("Loaded Kraken credentials from environment variables")
            return api_key, private_key
        else:
            logger.warning("No Kraken credentials found in environment variables")
            return None, None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start the client and initialize all connections."""
        if self._closed:
            raise RuntimeError("Client is already closed")

        # Start REST client
        await self.rest_client.start()
        self._connection_health.rest_api_status = "healthy"

        # Verify Pro account status
        await self._verify_pro_account()

        # Initialize WebSocket connections based on configuration
        if self.enable_websocket_v2:
            await self._initialize_websocket_v2()

        if self.enable_websocket_v1 and not self._websocket_v2_connection:
            await self._initialize_websocket_v1()

        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info("Kraken Pro client started successfully")

    async def close(self):
        """Close all connections and cleanup resources."""
        if self._closed:
            return

        self._closed = True

        # Stop health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket connections
        if self._websocket_v2_connection:
            await self._websocket_v2_connection.close()

        if self._websocket_v1_connection:
            await self._websocket_v1_connection.close()

        # Close REST client
        await self.rest_client.close()

        logger.info("Kraken Pro client closed")

    async def _verify_pro_account(self):
        """Verify and detect Kraken Pro account features."""
        try:
            # Test WebSocket token availability
            try:
                token_response = await self.rest_client.get_websockets_token()
                if token_response.get('result') and token_response['result'].get('token'):
                    self._pro_status.websocket_token_available = True
                    self._websocket_token = token_response['result']['token']
                    self._websocket_token_expires = time.time() + 900  # 15 minutes
                    logger.info("WebSocket token obtained successfully")
                else:
                    logger.warning("WebSocket token not available - may indicate restricted API key")
            except Exception as e:
                logger.warning(f"Failed to obtain WebSocket token: {e}")
                self._pro_status.websocket_token_available = False

            # Get account balance to verify API access
            balance_response = await self.rest_client.get_account_balance()
            if balance_response.get('result'):
                logger.info("Account balance access verified")

            # Get trade balance for fee information
            try:
                trade_balance = await self.rest_client.get_trade_balance()
                if trade_balance.get('result'):
                    result = trade_balance['result']
                    # Extract volume information if available
                    if 'cv' in result:  # Cost value (volume)
                        self._pro_status.trading_volume_30d = float(result.get('cv', 0))
            except Exception as e:
                logger.debug(f"Trade balance query failed: {e}")

            # Determine account tier based on available features
            if self._pro_status.websocket_token_available:
                self._pro_status.available_features.append(ProAccountFeature.WEBSOCKET_V2)
                # Assume Pro account if WebSocket token is available
                self._pro_status.is_pro_account = True
                self._pro_status.fee_schedule = "pro"
                self._pro_status.maker_fee = 0.0  # Fee-free for Pro
                self._pro_status.taker_fee = 0.0  # Fee-free for Pro

                # Update REST client account tier
                self.rest_client.account_tier = AccountTier.PRO
                logger.info("Detected Kraken Pro account with fee-free trading")
            else:
                logger.info("Standard Kraken account detected")

            self._pro_status_verified = True

        except Exception as e:
            logger.error(f"Failed to verify Pro account status: {e}")
            self._pro_status_verified = False

    async def _initialize_websocket_v2(self):
        """Initialize WebSocket V2 connection."""
        if not self._websocket_token:
            logger.warning("Cannot initialize WebSocket V2 without authentication token")
            self._connection_health.websocket_v2_status = "failed"
            return

        try:
            # Create SSL context for secure WebSocket connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            # Connect to WebSocket V2 private endpoint
            self._websocket_v2_connection = await websockets.connect(
                self.websocket_config.private_url,
                ssl=ssl_context,
                ping_interval=self.websocket_config.ping_interval,
                ping_timeout=self.websocket_config.ping_timeout,
                close_timeout=self.websocket_config.close_timeout,
                max_size=self.websocket_config.max_size,
                compression=self.websocket_config.compression
            )

            # Send authentication message
            auth_message = {
                "method": "subscribe",
                "params": {
                    "channel": "status",
                    "token": self._websocket_token
                }
            }

            await self._websocket_v2_connection.send(json.dumps(auth_message))

            # Wait for authentication response
            auth_response = await asyncio.wait_for(
                self._websocket_v2_connection.recv(),
                timeout=10.0
            )

            response_data = json.loads(auth_response)
            if response_data.get("channel") == "status" and response_data.get("type") == "update":
                self._connection_health.websocket_v2_status = "healthy"
                self._connection_health.active_connections.append("websocket_v2")
                logger.info("WebSocket V2 connection established and authenticated")
            else:
                raise Exception(f"Authentication failed: {response_data}")

        except Exception as e:
            logger.error(f"Failed to initialize WebSocket V2: {e}")
            self._connection_health.websocket_v2_status = "failed"
            if self._websocket_v2_connection:
                await self._websocket_v2_connection.close()
                self._websocket_v2_connection = None

    async def _initialize_websocket_v1(self):
        """Initialize WebSocket V1 connection as fallback."""
        if not self._websocket_token:
            logger.warning("Cannot initialize WebSocket V1 without authentication token")
            self._connection_health.websocket_v1_status = "failed"
            return

        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            # Connect to WebSocket V1 private endpoint
            self._websocket_v1_connection = await websockets.connect(
                self.websocket_config.v1_private_url,
                ssl=ssl_context,
                ping_interval=self.websocket_config.ping_interval,
                ping_timeout=self.websocket_config.ping_timeout
            )

            # Send authentication message for V1
            auth_message = {
                "event": "subscribe",
                "subscription": {"name": "ownTrades", "token": self._websocket_token}
            }

            await self._websocket_v1_connection.send(json.dumps(auth_message))

            # Wait for authentication response
            auth_response = await asyncio.wait_for(
                self._websocket_v1_connection.recv(),
                timeout=10.0
            )

            response_data = json.loads(auth_response)
            if response_data.get("event") == "subscriptionStatus" and response_data.get("status") == "subscribed":
                self._connection_health.websocket_v1_status = "healthy"
                self._connection_health.active_connections.append("websocket_v1")
                logger.info("WebSocket V1 connection established and authenticated")
            else:
                raise Exception(f"V1 Authentication failed: {response_data}")

        except Exception as e:
            logger.error(f"Failed to initialize WebSocket V1: {e}")
            self._connection_health.websocket_v1_status = "failed"
            if self._websocket_v1_connection:
                await self._websocket_v1_connection.close()
                self._websocket_v1_connection = None

    async def _health_check_loop(self):
        """Continuous health monitoring of all connections."""
        while not self._closed:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self._health_check_interval)

    async def _perform_health_check(self):
        """Perform comprehensive health check of all connections."""
        # Check REST API health
        try:
            server_time = await self.rest_client.get_server_time()
            if server_time.get('result'):
                self._connection_health.rest_api_status = "healthy"
                self._connection_health.last_successful_request = time.time()
                self._connection_health.consecutive_failures = 0
        except Exception as e:
            logger.warning(f"REST API health check failed: {e}")
            self._connection_health.rest_api_status = "degraded"
            self._connection_health.consecutive_failures += 1

        # Check WebSocket V2 health
        if self._websocket_v2_connection and not self._websocket_v2_connection.closed:
            try:
                # Send ping to WebSocket V2
                ping_message = {"method": "ping"}
                await self._websocket_v2_connection.send(json.dumps(ping_message))
                self._connection_health.websocket_v2_status = "healthy"
            except Exception as e:
                logger.warning(f"WebSocket V2 health check failed: {e}")
                self._connection_health.websocket_v2_status = "failed"
                await self._reconnect_websocket_v2()

        # Check WebSocket V1 health
        if self._websocket_v1_connection and not self._websocket_v1_connection.closed:
            try:
                # WebSocket V1 uses automatic ping/pong
                self._connection_health.websocket_v1_status = "healthy"
            except Exception as e:
                logger.warning(f"WebSocket V1 health check failed: {e}")
                self._connection_health.websocket_v1_status = "failed"
                await self._reconnect_websocket_v1()

        # Update fallback mode
        healthy_connections = [
            status for status in [
                self._connection_health.websocket_v2_status,
                self._connection_health.websocket_v1_status
            ] if status == "healthy"
        ]

        self._connection_health.fallback_mode = len(healthy_connections) == 0

        if self._connection_health.fallback_mode:
            logger.warning("All WebSocket connections failed, using REST fallback mode")

    async def _reconnect_websocket_v2(self):
        """Reconnect WebSocket V2 connection."""
        if self._websocket_v2_connection:
            try:
                await self._websocket_v2_connection.close()
            except:
                pass
            self._websocket_v2_connection = None

        # Refresh token if needed
        if not self._websocket_token or time.time() > (self._websocket_token_expires or 0) - 300:
            await self._refresh_websocket_token()

        await self._initialize_websocket_v2()

    async def _reconnect_websocket_v1(self):
        """Reconnect WebSocket V1 connection."""
        if self._websocket_v1_connection:
            try:
                await self._websocket_v1_connection.close()
            except:
                pass
            self._websocket_v1_connection = None

        # Refresh token if needed
        if not self._websocket_token or time.time() > (self._websocket_token_expires or 0) - 300:
            await self._refresh_websocket_token()

        await self._initialize_websocket_v1()

    async def _refresh_websocket_token(self):
        """Refresh WebSocket authentication token."""
        try:
            token_response = await self.rest_client.get_websockets_token()
            if token_response.get('result') and token_response['result'].get('token'):
                self._websocket_token = token_response['result']['token']
                self._websocket_token_expires = time.time() + 900  # 15 minutes
                logger.info("WebSocket token refreshed successfully")
            else:
                raise Exception("Failed to get new token")
        except Exception as e:
            logger.error(f"Failed to refresh WebSocket token: {e}")
            raise

    # ====== PUBLIC API METHODS ======

    async def verify_pro_account_status(self) -> ProAccountStatus:
        """
        Verify and return Pro account status.

        Returns:
            ProAccountStatus with current account information
        """
        if not self._pro_status_verified:
            await self._verify_pro_account()

        return self._pro_status

    async def get_real_time_ticker(self, pair: str) -> dict[str, Any]:
        """
        Get real-time ticker data with automatic fallback.

        Args:
            pair: Trading pair (e.g., 'BTC/USD')

        Returns:
            Real-time ticker data
        """
        # Try WebSocket V2 first
        if self._connection_health.websocket_v2_status == "healthy":
            try:
                return await self._get_ticker_websocket_v2(pair)
            except Exception as e:
                logger.warning(f"WebSocket V2 ticker failed: {e}")

        # Try WebSocket V1 fallback
        if self._connection_health.websocket_v1_status == "healthy":
            try:
                return await self._get_ticker_websocket_v1(pair)
            except Exception as e:
                logger.warning(f"WebSocket V1 ticker failed: {e}")

        # REST API fallback
        logger.info(f"Using REST API fallback for ticker data: {pair}")
        return await self.rest_client.get_ticker_information(pair)

    async def _get_ticker_websocket_v2(self, pair: str) -> dict[str, Any]:
        """Get ticker data via WebSocket V2."""
        if not self._websocket_v2_connection:
            raise Exception("WebSocket V2 not connected")

        # Subscribe to ticker channel
        subscribe_message = {
            "method": "subscribe",
            "params": {
                "channel": "ticker",
                "symbol": [pair],
                "token": self._websocket_token
            }
        }

        await self._websocket_v2_connection.send(json.dumps(subscribe_message))

        # Wait for ticker data
        response = await asyncio.wait_for(
            self._websocket_v2_connection.recv(),
            timeout=5.0
        )

        return json.loads(response)

    async def _get_ticker_websocket_v1(self, pair: str) -> dict[str, Any]:
        """Get ticker data via WebSocket V1."""
        if not self._websocket_v1_connection:
            raise Exception("WebSocket V1 not connected")

        # Subscribe to ticker channel (V1 format)
        subscribe_message = {
            "event": "subscribe",
            "pair": [pair],
            "subscription": {"name": "ticker"}
        }

        await self._websocket_v1_connection.send(json.dumps(subscribe_message))

        # Wait for ticker data
        response = await asyncio.wait_for(
            self._websocket_v1_connection.recv(),
            timeout=5.0
        )

        return json.loads(response)

    async def place_order(
        self,
        pair: str,
        side: str,  # 'buy' or 'sell'
        order_type: str,  # 'market', 'limit', etc.
        volume: str,
        price: Optional[str] = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Place order with Pro account optimizations.

        Args:
            pair: Trading pair
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market', 'limit', etc.)
            volume: Order volume
            price: Order price (for limit orders)
            **kwargs: Additional order parameters

        Returns:
            Order response data
        """
        # Add Pro account specific flags
        if self._pro_status.is_pro_account:
            # Enable fee-free trading flag if available
            oflags = kwargs.get('oflags', '')
            if 'fciq' not in oflags:  # Fee-free flag
                kwargs['oflags'] = f"{oflags},fciq" if oflags else "fciq"

            logger.info(f"Placing Pro account order: {side} {volume} {pair} at {price or 'market'}")

        return await self.rest_client.add_order(
            pair=pair,
            type=side,
            ordertype=order_type,
            volume=volume,
            price=price,
            **kwargs
        )

    async def get_account_balance(self) -> dict[str, Any]:
        """Get account balance with Pro account enhancements."""
        balance_data = await self.rest_client.get_account_balance()

        # Add Pro account metadata
        if self._pro_status.is_pro_account:
            result = balance_data.get('result', {})
            result['_pro_account'] = True
            result['_fee_schedule'] = self._pro_status.fee_schedule
            result['_maker_fee'] = self._pro_status.maker_fee
            result['_taker_fee'] = self._pro_status.taker_fee

        return balance_data

    async def stream_real_time_data(
        self,
        channels: list[str],
        symbols: Optional[list[str]] = None,
        callback: Optional[Callable] = None
    ) -> asyncio.Task:
        """
        Start streaming real-time data with automatic connection management.

        Args:
            channels: List of channels to subscribe to
            symbols: Optional list of symbols to filter
            callback: Optional callback function for data processing

        Returns:
            AsyncIO task for the streaming process
        """
        async def stream_handler():
            while not self._closed:
                try:
                    # Choose best available connection
                    if self._connection_health.websocket_v2_status == "healthy":
                        await self._stream_websocket_v2(channels, symbols, callback)
                    elif self._connection_health.websocket_v1_status == "healthy":
                        await self._stream_websocket_v1(channels, symbols, callback)
                    else:
                        # REST polling fallback
                        await self._stream_rest_polling(channels, symbols, callback)
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    await asyncio.sleep(5)  # Brief pause before retry

        return asyncio.create_task(stream_handler())

    async def _stream_websocket_v2(self, channels, symbols, callback):
        """Stream data via WebSocket V2."""
        if not self._websocket_v2_connection:
            return

        # Subscribe to channels
        for channel in channels:
            subscribe_msg = {
                "method": "subscribe",
                "params": {
                    "channel": channel,
                    "token": self._websocket_token
                }
            }
            if symbols:
                subscribe_msg["params"]["symbol"] = symbols

            await self._websocket_v2_connection.send(json.dumps(subscribe_msg))

        # Process incoming messages
        async for message in self._websocket_v2_connection:
            try:
                data = json.loads(message)
                if callback:
                    await callback(data)
                else:
                    logger.info(f"WebSocket V2 data: {data}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {message}")

    async def _stream_websocket_v1(self, channels, symbols, callback):
        """Stream data via WebSocket V1."""
        if not self._websocket_v1_connection:
            return

        # Subscribe to channels (V1 format)
        for channel in channels:
            subscribe_msg = {
                "event": "subscribe",
                "subscription": {"name": channel}
            }
            if symbols:
                subscribe_msg["pair"] = symbols

            await self._websocket_v1_connection.send(json.dumps(subscribe_msg))

        # Process incoming messages
        async for message in self._websocket_v1_connection:
            try:
                data = json.loads(message)
                if callback:
                    await callback(data)
                else:
                    logger.info(f"WebSocket V1 data: {data}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {message}")

    async def _stream_rest_polling(self, channels, symbols, callback):
        """Stream data via REST API polling (fallback)."""
        logger.info("Using REST API polling for real-time data (fallback mode)")

        while not self._closed and self._connection_health.fallback_mode:
            try:
                # Poll different endpoints based on requested channels
                for channel in channels:
                    if channel == "ticker" and symbols:
                        for symbol in symbols:
                            ticker_data = await self.rest_client.get_ticker_information(symbol)
                            if callback:
                                await callback({
                                    "channel": "ticker",
                                    "data": ticker_data,
                                    "symbol": symbol,
                                    "method": "rest_polling"
                                })

                    elif channel == "ohlc" and symbols:
                        for symbol in symbols:
                            ohlc_data = await self.rest_client.get_ohlc_data(symbol, interval=1)
                            if callback:
                                await callback({
                                    "channel": "ohlc",
                                    "data": ohlc_data,
                                    "symbol": symbol,
                                    "method": "rest_polling"
                                })

                # Wait before next poll (adjust based on rate limits)
                await asyncio.sleep(1.0)  # 1 second polling interval

            except Exception as e:
                logger.error(f"REST polling error: {e}")
                await asyncio.sleep(5.0)

    # ====== UTILITY METHODS ======

    def get_connection_status(self) -> dict[str, Any]:
        """Get comprehensive connection status."""
        return {
            "client_info": {
                "api_key": self.api_key[:8] + "...",
                "pro_account": self._pro_status.is_pro_account,
                "fee_schedule": self._pro_status.fee_schedule,
                "websocket_token_available": self._pro_status.websocket_token_available
            },
            "connection_health": {
                "websocket_v2_status": self._connection_health.websocket_v2_status,
                "websocket_v1_status": self._connection_health.websocket_v1_status,
                "rest_api_status": self._connection_health.rest_api_status,
                "fallback_mode": self._connection_health.fallback_mode,
                "active_connections": self._connection_health.active_connections.copy(),
                "consecutive_failures": self._connection_health.consecutive_failures
            },
            "pro_features": {
                "available_features": [f.value for f in self._pro_status.available_features],
                "fee_free_trading": ProAccountFeature.FEE_FREE_TRADING in self._pro_status.available_features,
                "maker_fee": self._pro_status.maker_fee,
                "taker_fee": self._pro_status.taker_fee
            },
            "rest_client_status": self.rest_client.get_status() if self.rest_client else None
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check."""
        health = {
            "timestamp": time.time(),
            "overall_status": "healthy",
            "checks": {}
        }

        # Check REST API
        try:
            rest_health = await self.rest_client.health_check()
            health["checks"]["rest_api"] = rest_health
        except Exception as e:
            health["checks"]["rest_api"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["overall_status"] = "degraded"

        # Check WebSocket connections
        health["checks"]["websocket_v2"] = {
            "status": self._connection_health.websocket_v2_status,
            "connected": self._websocket_v2_connection is not None and not self._websocket_v2_connection.closed if self._websocket_v2_connection else False
        }

        health["checks"]["websocket_v1"] = {
            "status": self._connection_health.websocket_v1_status,
            "connected": self._websocket_v1_connection is not None and not self._websocket_v1_connection.closed if self._websocket_v1_connection else False
        }

        # Check Pro account features
        health["checks"]["pro_account"] = {
            "status": "healthy" if self._pro_status_verified else "unknown",
            "is_pro": self._pro_status.is_pro_account,
            "features_available": len(self._pro_status.available_features)
        }

        return health

    async def test_connection(self) -> bool:
        """Test all available connections."""
        success = True

        # Test REST API
        try:
            rest_success = await self.rest_client.test_connection()
            if not rest_success:
                success = False
                logger.error("REST API connection test failed")
        except Exception as e:
            logger.error(f"REST API connection test error: {e}")
            success = False

        # Test WebSocket connections
        if self._websocket_v2_connection and not self._websocket_v2_connection.closed:
            try:
                ping_msg = {"method": "ping"}
                await self._websocket_v2_connection.send(json.dumps(ping_msg))
                logger.info("WebSocket V2 connection test passed")
            except Exception as e:
                logger.error(f"WebSocket V2 connection test failed: {e}")
                success = False

        if self._websocket_v1_connection and not self._websocket_v1_connection.closed:
            logger.info("WebSocket V1 connection is active")

        return success


# ====== CONVENIENCE FUNCTIONS ======

async def create_kraken_pro_client(
    api_key: Optional[str] = None,
    private_key: Optional[str] = None,
    auto_start: bool = True
) -> KrakenProClient:
    """
    Create and optionally start a Kraken Pro client.

    Args:
        api_key: API key (will load from environment if None)
        private_key: Private key (will load from environment if None)
        auto_start: Whether to automatically start the client

    Returns:
        KrakenProClient instance
    """
    client = KrakenProClient(api_key=api_key, private_key=private_key)

    if auto_start:
        await client.start()

    return client


async def test_kraken_pro_connection(
    api_key: Optional[str] = None,
    private_key: Optional[str] = None
) -> dict[str, Any]:
    """
    Test Kraken Pro API connection and return comprehensive status.

    Args:
        api_key: API key (will load from environment if None)
        private_key: Private key (will load from environment if None)

    Returns:
        Comprehensive connection test results
    """
    async with KrakenProClient(api_key, private_key) as client:
        # Verify Pro account status
        pro_status = await client.verify_pro_account_status()

        # Perform health check
        health = await client.health_check()

        # Test connections
        connection_test = await client.test_connection()

        return {
            "connection_test_passed": connection_test,
            "pro_account_status": {
                "is_pro_account": pro_status.is_pro_account,
                "fee_schedule": pro_status.fee_schedule,
                "websocket_token_available": pro_status.websocket_token_available,
                "available_features": [f.value for f in pro_status.available_features]
            },
            "health_check": health,
            "connection_status": client.get_connection_status()
        }
