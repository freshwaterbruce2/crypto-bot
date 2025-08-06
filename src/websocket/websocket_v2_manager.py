"""
Enhanced WebSocket V2 Connection Manager
======================================

Comprehensive WebSocket V2 manager that implements Kraken's official WebSocket V2 API
with advanced connection management, authentication, and real-time data streaming.

Features:
- WebSocket V2 protocol compliance
- Advanced connection lifecycle management
- Proactive authentication token refresh
- Automatic reconnection with exponential backoff
- Channel subscription management
- Message routing and processing
- Health monitoring and diagnostics
- Integration with existing exchange infrastructure
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Optional

import websockets

from ..auth.websocket_authentication_manager import (
    WebSocketAuthenticationManager,
)
from ..utils.secure_transport import create_secure_websocket_ssl_context

logger = logging.getLogger(__name__)


@dataclass
class WebSocketV2Config:
    """Configuration for WebSocket V2 connections"""
    public_url: str = "wss://ws.kraken.com/v2"
    private_url: str = "wss://ws-auth.kraken.com/v2"

    # Connection settings
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    reconnect_delay: float = 1.0
    max_reconnect_attempts: int = 10
    reconnect_backoff: float = 2.0
    max_reconnect_delay: float = 60.0
    connection_timeout: float = 30.0

    # Message settings
    message_queue_size: int = 10000
    heartbeat_timeout: float = 60.0

    # Rate limiting
    subscription_rate_limit: int = 5
    subscription_rate_window: float = 60.0

    # Authentication
    token_refresh_interval: float = 13 * 60  # 13 minutes


@dataclass
class ConnectionStatus:
    """WebSocket connection status information"""
    is_connected: bool = False
    is_authenticated: bool = False
    connection_start_time: Optional[float] = None
    last_message_time: Optional[float] = None
    reconnect_count: int = 0
    active_subscriptions: set[str] = None

    def __post_init__(self):
        if self.active_subscriptions is None:
            self.active_subscriptions = set()


class WebSocketV2Manager:
    """
    Enhanced WebSocket V2 connection manager for Kraken exchange.

    Provides comprehensive WebSocket V2 connectivity with advanced features:
    - Automatic connection management and reconnection
    - Authentication token management
    - Channel subscription handling
    - Message routing and processing
    - Health monitoring and diagnostics
    """

    def __init__(
        self,
        exchange_client: Any,
        api_key: Optional[str] = None,
        private_key: Optional[str] = None,
        config: Optional[WebSocketV2Config] = None,
        enable_debug: bool = False
    ):
        """
        Initialize WebSocket V2 manager.

        Args:
            exchange_client: Exchange client for token requests and fallback
            api_key: Kraken API key for authentication
            private_key: Base64-encoded private key
            config: WebSocket configuration
            enable_debug: Enable detailed debug logging
        """
        self.exchange_client = exchange_client
        self.api_key = api_key
        self.private_key = private_key
        self.config = config or WebSocketV2Config()
        self.enable_debug = enable_debug

        # Connection state
        self.status = ConnectionStatus()
        self._websocket_public: Optional[websockets.WebSocketServerProtocol] = None
        self._websocket_private: Optional[websockets.WebSocketServerProtocol] = None
        self._connection_lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._running = False

        # Authentication
        self._auth_manager: Optional[WebSocketAuthenticationManager] = None
        self._current_token: Optional[str] = None
        self._token_refresh_task: Optional[asyncio.Task] = None

        # Message handling
        self._message_handlers: dict[str, list[Callable]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.message_queue_size)
        self._processing_task: Optional[asyncio.Task] = None

        # Subscription management
        self._subscriptions: dict[str, dict[str, Any]] = {}
        self._subscription_lock = asyncio.Lock()
        self._subscription_rate_tracker: list[float] = []

        # Channel processors
        from .websocket_v2_channels import WebSocketV2ChannelProcessor
        self._channel_processor = WebSocketV2ChannelProcessor(self)

        # Order management
        from .websocket_v2_orders import WebSocketV2OrderManager
        self._order_manager = WebSocketV2OrderManager(self)

        # Performance tracking
        self._stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'subscription_requests': 0,
            'reconnections': 0,
            'authentication_attempts': 0,
            'last_heartbeat': 0.0
        }

        logger.info(f"[WS_V2_MGR] Initialized WebSocket V2 manager with config: {self.config}")

    async def start(self) -> bool:
        """
        Start the WebSocket V2 manager.

        Returns:
            True if started successfully
        """
        try:
            logger.info("[WS_V2_MGR] Starting WebSocket V2 manager...")

            # Initialize authentication if credentials provided
            if self.api_key and self.private_key:
                self._auth_manager = WebSocketAuthenticationManager(
                    exchange_client=self.exchange_client,
                    api_key=self.api_key,
                    private_key=self.private_key,
                    enable_debug=self.enable_debug
                )

                auth_success = await self._auth_manager.start()
                if not auth_success:
                    logger.warning("[WS_V2_MGR] Authentication manager failed to start - private channels disabled")
                else:
                    logger.info("[WS_V2_MGR] Authentication manager started successfully")

            # Start message processing
            self._running = True
            self._processing_task = asyncio.create_task(self._message_processing_loop())

            # Connect to public WebSocket
            public_connected = await self._connect_public()
            if not public_connected:
                logger.error("[WS_V2_MGR] Failed to connect to public WebSocket")
                await self.stop()
                return False

            # Connect to private WebSocket if authentication available
            if self._auth_manager:
                private_connected = await self._connect_private()
                if not private_connected:
                    logger.warning("[WS_V2_MGR] Failed to connect to private WebSocket - balance updates disabled")
                else:
                    logger.info("[WS_V2_MGR] Private WebSocket connected successfully")

            # Start monitoring tasks
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
            self._health_task = asyncio.create_task(self._health_monitor())

            # Start token refresh if authentication available
            if self._auth_manager:
                self._token_refresh_task = asyncio.create_task(self._token_refresh_loop())

            self.status.is_connected = True
            self.status.connection_start_time = time.time()

            logger.info("[WS_V2_MGR] WebSocket V2 manager started successfully")
            return True

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Failed to start: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """Stop the WebSocket V2 manager and cleanup resources"""
        try:
            logger.info("[WS_V2_MGR] Stopping WebSocket V2 manager...")

            self._running = False
            self._shutdown_event.set()

            # Cancel background tasks
            tasks = [
                self._processing_task,
                self._heartbeat_task,
                self._health_task,
                self._token_refresh_task
            ]

            for task in tasks:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Close WebSocket connections
            if self._websocket_public and not self._websocket_public.closed:
                await self._websocket_public.close()

            if self._websocket_private and not self._websocket_private.closed:
                await self._websocket_private.close()

            # Stop authentication manager
            if self._auth_manager:
                await self._auth_manager.stop()

            # Reset status
            self.status = ConnectionStatus()

            logger.info("[WS_V2_MGR] WebSocket V2 manager stopped")

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Error stopping manager: {e}")

    async def _connect_public(self) -> bool:
        """Connect to public WebSocket endpoint"""
        try:
            logger.info(f"[WS_V2_MGR] Connecting to public WebSocket: {self.config.public_url}")

            # Create enterprise-grade secure SSL context
            ssl_context = create_secure_websocket_ssl_context(enable_fallback=False)

            # Connect with timeout
            self._websocket_public = await asyncio.wait_for(
                websockets.connect(
                    self.config.public_url,
                    ssl=ssl_context,
                    ping_interval=self.config.ping_interval,
                    ping_timeout=self.config.ping_timeout
                ),
                timeout=self.config.connection_timeout
            )

            # Start message listener
            asyncio.create_task(self._message_listener(self._websocket_public, "public"))

            logger.info("[WS_V2_MGR] Public WebSocket connected successfully")
            return True

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Public WebSocket connection failed: {e}")
            return False

    async def _connect_private(self) -> bool:
        """Connect to private WebSocket endpoint with authentication"""
        try:
            if not self._auth_manager:
                logger.warning("[WS_V2_MGR] No authentication manager - skipping private connection")
                return False

            # Get authentication token
            token = await self._auth_manager.get_websocket_token()
            if not token:
                logger.error("[WS_V2_MGR] Failed to get authentication token")
                return False

            self._current_token = token

            logger.info(f"[WS_V2_MGR] Connecting to private WebSocket: {self.config.private_url}")

            # Create enterprise-grade secure SSL context
            ssl_context = create_secure_websocket_ssl_context(enable_fallback=False)

            # Connect with timeout
            self._websocket_private = await asyncio.wait_for(
                websockets.connect(
                    self.config.private_url,
                    ssl=ssl_context,
                    ping_interval=self.config.ping_interval,
                    ping_timeout=self.config.ping_timeout
                ),
                timeout=self.config.connection_timeout
            )

            # Authenticate connection
            auth_message = {
                "method": "subscribe",
                "params": {
                    "channel": "status",
                    "token": token
                }
            }

            await self._websocket_private.send(json.dumps(auth_message))

            # Start message listener
            asyncio.create_task(self._message_listener(self._websocket_private, "private"))

            self.status.is_authenticated = True
            self._stats['authentication_attempts'] += 1

            logger.info("[WS_V2_MGR] Private WebSocket connected and authenticated successfully")
            return True

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Private WebSocket connection failed: {e}")
            return False

    async def _message_listener(self, websocket: websockets.WebSocketServerProtocol, connection_type: str) -> None:
        """Listen for messages from WebSocket connection"""
        try:
            logger.info(f"[WS_V2_MGR] Starting message listener for {connection_type} connection")

            async for message in websocket:
                try:
                    self._stats['messages_received'] += 1
                    self.status.last_message_time = time.time()

                    # Parse message
                    data = json.loads(message)

                    # Add connection type for routing
                    data['_connection_type'] = connection_type

                    # Queue message for processing
                    try:
                        self._message_queue.put_nowait(data)
                    except asyncio.QueueFull:
                        logger.warning(f"[WS_V2_MGR] Message queue full, dropping {connection_type} message")
                        self._stats['messages_failed'] += 1

                except json.JSONDecodeError as e:
                    logger.warning(f"[WS_V2_MGR] Invalid JSON from {connection_type}: {e}")
                    self._stats['messages_failed'] += 1
                except Exception as e:
                    logger.error(f"[WS_V2_MGR] Error processing {connection_type} message: {e}")
                    self._stats['messages_failed'] += 1

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"[WS_V2_MGR] {connection_type.title()} WebSocket connection closed: {e}")
        except Exception as e:
            logger.error(f"[WS_V2_MGR] {connection_type.title()} message listener error: {e}")
        finally:
            logger.info(f"[WS_V2_MGR] {connection_type.title()} message listener stopped")

    async def _message_processing_loop(self) -> None:
        """Main message processing loop"""
        logger.info("[WS_V2_MGR] Starting message processing loop")

        while self._running:
            try:
                # Get message with timeout
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process message
                await self._process_message(message)
                self._stats['messages_processed'] += 1

            except Exception as e:
                logger.error(f"[WS_V2_MGR] Error in message processing loop: {e}")
                self._stats['messages_failed'] += 1
                await asyncio.sleep(0.1)

        logger.info("[WS_V2_MGR] Message processing loop stopped")

    async def _process_message(self, message: dict[str, Any]) -> None:
        """Process incoming WebSocket message"""
        try:
            message_type = message.get('channel')
            connection_type = message.get('_connection_type', 'unknown')

            if self.enable_debug:
                logger.debug(f"[WS_V2_MGR] Processing {connection_type} message: {message_type}")

            # Handle heartbeat
            if message_type == 'heartbeat':
                self._stats['last_heartbeat'] = time.time()
                return

            # Handle subscription status
            if message.get('method') == 'subscribe':
                await self._handle_subscription_response(message)
                return

            # Route to channel processor
            if message_type:
                await self._channel_processor.process_message(message)
            else:
                logger.warning(f"[WS_V2_MGR] Unknown message format: {message}")

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Error processing message: {e}")
            logger.debug(f"[WS_V2_MGR] Failed message: {message}")

    async def _handle_subscription_response(self, message: dict[str, Any]) -> None:
        """Handle subscription confirmation/error responses"""
        try:
            success = message.get('success', False)
            result = message.get('result', {})
            channel = result.get('channel')

            if success:
                self.status.active_subscriptions.add(channel)
                logger.info(f"[WS_V2_MGR] Successfully subscribed to {channel}")

                # Notify handlers
                await self._notify_handlers('subscription_success', {
                    'channel': channel,
                    'result': result
                })
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"[WS_V2_MGR] Subscription failed for {channel}: {error}")

                # Notify handlers
                await self._notify_handlers('subscription_error', {
                    'channel': channel,
                    'error': error,
                    'result': result
                })

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Error handling subscription response: {e}")

    async def subscribe_channel(
        self,
        channel: str,
        params: Optional[dict[str, Any]] = None,
        private: bool = False
    ) -> bool:
        """
        Subscribe to WebSocket channel.

        Args:
            channel: Channel name (e.g., 'ticker', 'book', 'balances')
            params: Additional subscription parameters
            private: Whether to use private WebSocket connection

        Returns:
            True if subscription request sent successfully
        """
        try:
            # Check rate limiting
            if not await self._check_subscription_rate_limit():
                logger.warning(f"[WS_V2_MGR] Subscription rate limit exceeded for {channel}")
                return False

            # Build subscription message
            subscription = {
                "method": "subscribe",
                "params": {
                    "channel": channel,
                    **(params or {})
                }
            }

            # Add authentication token for private channels
            if private and self._current_token:
                subscription["params"]["token"] = self._current_token

            # Choose appropriate WebSocket connection
            websocket = self._websocket_private if private and self._websocket_private else self._websocket_public

            if not websocket or websocket.closed:
                logger.error(f"[WS_V2_MGR] No active WebSocket connection for {channel} subscription")
                return False

            # Send subscription
            await websocket.send(json.dumps(subscription))

            # Track subscription
            async with self._subscription_lock:
                self._subscriptions[channel] = {
                    'params': params,
                    'private': private,
                    'timestamp': time.time()
                }

            self._stats['subscription_requests'] += 1
            logger.info(f"[WS_V2_MGR] Sent subscription request for {channel}")

            return True

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Failed to subscribe to {channel}: {e}")
            return False

    async def unsubscribe_channel(self, channel: str, private: bool = False) -> bool:
        """
        Unsubscribe from WebSocket channel.

        Args:
            channel: Channel name
            private: Whether to use private WebSocket connection

        Returns:
            True if unsubscription request sent successfully
        """
        try:
            # Build unsubscription message
            unsubscription = {
                "method": "unsubscribe",
                "params": {
                    "channel": channel
                }
            }

            # Choose appropriate WebSocket connection
            websocket = self._websocket_private if private and self._websocket_private else self._websocket_public

            if not websocket or websocket.closed:
                logger.error(f"[WS_V2_MGR] No active WebSocket connection for {channel} unsubscription")
                return False

            # Send unsubscription
            await websocket.send(json.dumps(unsubscription))

            # Remove from tracking
            async with self._subscription_lock:
                self._subscriptions.pop(channel, None)
                self.status.active_subscriptions.discard(channel)

            logger.info(f"[WS_V2_MGR] Sent unsubscription request for {channel}")
            return True

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Failed to unsubscribe from {channel}: {e}")
            return False

    async def _check_subscription_rate_limit(self) -> bool:
        """Check if subscription rate limit allows new request"""
        current_time = time.time()
        window_start = current_time - self.config.subscription_rate_window

        # Remove old requests outside window
        self._subscription_rate_tracker = [
            timestamp for timestamp in self._subscription_rate_tracker
            if timestamp >= window_start
        ]

        # Check if under limit
        if len(self._subscription_rate_tracker) >= self.config.subscription_rate_limit:
            return False

        # Add current request
        self._subscription_rate_tracker.append(current_time)
        return True

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection heartbeat and detect stale connections"""
        logger.info("[WS_V2_MGR] Starting heartbeat monitor")

        while self._running:
            try:
                current_time = time.time()

                # Check if we've received messages recently
                if (self.status.last_message_time and
                    current_time - self.status.last_message_time > self.config.heartbeat_timeout):

                    logger.warning("[WS_V2_MGR] Heartbeat timeout detected - triggering reconnection")
                    await self._handle_connection_loss()

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"[WS_V2_MGR] Heartbeat monitor error: {e}")
                await asyncio.sleep(30)

        logger.info("[WS_V2_MGR] Heartbeat monitor stopped")

    async def _health_monitor(self) -> None:
        """Monitor overall connection health and performance"""
        logger.info("[WS_V2_MGR] Starting health monitor")

        while self._running:
            try:
                # Monitor queue size
                queue_size = self._message_queue.qsize()
                if queue_size > self.config.message_queue_size * 0.8:
                    logger.warning(f"[WS_V2_MGR] Message queue high: {queue_size}/{self.config.message_queue_size}")

                # Monitor message processing rate
                if self._stats['messages_received'] > 0:
                    processing_rate = self._stats['messages_processed'] / self._stats['messages_received']
                    if processing_rate < 0.95:  # Less than 95% processed
                        logger.warning(f"[WS_V2_MGR] Message processing rate low: {processing_rate:.2%}")

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"[WS_V2_MGR] Health monitor error: {e}")
                await asyncio.sleep(60)

        logger.info("[WS_V2_MGR] Health monitor stopped")

    async def _token_refresh_loop(self) -> None:
        """Background token refresh loop"""
        if not self._auth_manager:
            return

        logger.info("[WS_V2_MGR] Starting token refresh loop")

        while self._running:
            try:
                # Check if token needs refresh
                auth_status = self._auth_manager.get_authentication_status()
                if auth_status.get('needs_refresh', False):
                    logger.info("[WS_V2_MGR] Token refresh needed")

                    # Refresh token
                    success = await self._auth_manager.refresh_token_proactively()
                    if success:
                        # Update current token
                        new_token = await self._auth_manager.get_websocket_token()
                        if new_token:
                            self._current_token = new_token
                            logger.info("[WS_V2_MGR] Token refreshed successfully")
                    else:
                        logger.error("[WS_V2_MGR] Token refresh failed")

                # Sleep until next check
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"[WS_V2_MGR] Token refresh loop error: {e}")
                await asyncio.sleep(60)

        logger.info("[WS_V2_MGR] Token refresh loop stopped")

    async def _handle_connection_loss(self) -> None:
        """Handle connection loss and attempt reconnection"""
        logger.warning("[WS_V2_MGR] Handling connection loss")

        try:
            # Close existing connections
            if self._websocket_public and not self._websocket_public.closed:
                await self._websocket_public.close()

            if self._websocket_private and not self._websocket_private.closed:
                await self._websocket_private.close()

            # Reset connection status
            self.status.is_connected = False
            self.status.is_authenticated = False

            # Attempt reconnection with exponential backoff
            reconnect_delay = self.config.reconnect_delay

            for attempt in range(self.config.max_reconnect_attempts):
                logger.info(f"[WS_V2_MGR] Reconnection attempt {attempt + 1}/{self.config.max_reconnect_attempts}")

                # Wait before reconnecting
                await asyncio.sleep(reconnect_delay)

                # Try to reconnect
                public_connected = await self._connect_public()
                if public_connected:
                    logger.info("[WS_V2_MGR] Public WebSocket reconnected")

                    # Try private connection if auth available
                    if self._auth_manager:
                        private_connected = await self._connect_private()
                        if private_connected:
                            logger.info("[WS_V2_MGR] Private WebSocket reconnected")

                    # Resubscribe to channels
                    await self._resubscribe_channels()

                    self.status.is_connected = True
                    self.status.reconnect_count += 1
                    self._stats['reconnections'] += 1

                    logger.info("[WS_V2_MGR] Reconnection successful")
                    return

                # Exponential backoff
                reconnect_delay = min(
                    reconnect_delay * self.config.reconnect_backoff,
                    self.config.max_reconnect_delay
                )

            logger.error("[WS_V2_MGR] All reconnection attempts failed")

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Error handling connection loss: {e}")

    async def _resubscribe_channels(self) -> None:
        """Resubscribe to all previously subscribed channels"""
        try:
            logger.info("[WS_V2_MGR] Resubscribing to channels...")

            async with self._subscription_lock:
                subscriptions = dict(self._subscriptions)

            # Clear current subscriptions
            self.status.active_subscriptions.clear()

            # Resubscribe to each channel
            for channel, config in subscriptions.items():
                success = await self.subscribe_channel(
                    channel=channel,
                    params=config.get('params'),
                    private=config.get('private', False)
                )

                if success:
                    logger.info(f"[WS_V2_MGR] Resubscribed to {channel}")
                else:
                    logger.warning(f"[WS_V2_MGR] Failed to resubscribe to {channel}")

                # Small delay between subscriptions
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"[WS_V2_MGR] Error resubscribing to channels: {e}")

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """Register event handler"""
        if event_type not in self._message_handlers:
            self._message_handlers[event_type] = []

        self._message_handlers[event_type].append(handler)
        logger.info(f"[WS_V2_MGR] Registered handler for {event_type}")

    def unregister_handler(self, event_type: str, handler: Callable) -> None:
        """Unregister event handler"""
        if event_type in self._message_handlers:
            try:
                self._message_handlers[event_type].remove(handler)
                logger.info(f"[WS_V2_MGR] Unregistered handler for {event_type}")
            except ValueError:
                logger.warning(f"[WS_V2_MGR] Handler not found for {event_type}")

    async def _notify_handlers(self, event_type: str, data: Any) -> None:
        """Notify registered handlers of events"""
        handlers = self._message_handlers.get(event_type, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"[WS_V2_MGR] Error in {event_type} handler: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive connection status"""
        current_time = time.time()

        status = asdict(self.status)
        status['active_subscriptions'] = list(self.status.active_subscriptions)

        # Add uptime
        if self.status.connection_start_time:
            status['uptime'] = current_time - self.status.connection_start_time
        else:
            status['uptime'] = 0

        # Add statistics
        status['statistics'] = dict(self._stats)

        # Add queue status
        status['message_queue_size'] = self._message_queue.qsize()
        status['max_queue_size'] = self.config.message_queue_size

        # Add authentication status
        if self._auth_manager:
            status['authentication'] = self._auth_manager.get_authentication_status()

        return status

    def get_channel_processor(self):
        """Get channel processor for direct access"""
        return self._channel_processor

    def get_order_manager(self):
        """Get order manager for trading operations"""
        return self._order_manager

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.status.is_connected

    @property
    def is_authenticated(self) -> bool:
        """Check if WebSocket is authenticated"""
        return self.status.is_authenticated

    @property
    def has_private_access(self) -> bool:
        """Check if private WebSocket access is available"""
        return self._auth_manager is not None and self.status.is_authenticated
