"""
WebSocket Connection Manager
============================

Manages WebSocket connection lifecycle, reconnection logic, and connection health.
Provides robust connection management with automatic healing and failure recovery.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from .data_models import ConnectionStatus

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionConfig:
    """WebSocket connection configuration"""

    url: str
    auth_url: Optional[str] = None
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    close_timeout: float = 10.0
    max_reconnect_attempts: int = 10
    reconnect_delay: float = 1.0
    reconnect_backoff: float = 2.0
    max_reconnect_delay: float = 60.0
    message_queue_size: int = 1000
    heartbeat_timeout: float = 60.0
    connection_timeout: float = 30.0


@dataclass
class ReconnectState:
    """Reconnection state tracking"""

    attempt_count: int = 0
    next_delay: float = 1.0
    last_attempt_time: float = 0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0

    def reset(self):
        """Reset reconnect state after successful connection"""
        self.attempt_count = 0
        self.next_delay = 1.0
        self.last_attempt_time = 0

    def increment(self):
        """Increment attempt count and calculate next delay"""
        self.attempt_count += 1
        self.last_attempt_time = time.time()
        self.next_delay = min(self.next_delay * self.backoff_multiplier, self.max_delay)


class ConnectionManager:
    """
    WebSocket connection manager with automatic reconnection and health monitoring
    """

    def __init__(self, config: ConnectionConfig):
        """Initialize connection manager"""
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        self.status = ConnectionStatus()
        self.reconnect_state = ReconnectState()

        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connection_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.message_handler_task: Optional[asyncio.Task] = None

        # Message handling
        self.message_queue: asyncio.Queue = asyncio.Queue(maxsize=config.message_queue_size)
        self.pending_messages: list[dict[str, Any]] = []

        # Callbacks
        self.on_message: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_authenticated: Optional[Callable] = None

        # Connection tracking
        self.last_message_time = 0
        self.last_ping_time = 0
        self.connection_start_time = 0

        # Shutdown flag
        self._shutdown = False

        logger.info(f"[CONNECTION_MANAGER] Initialized with config: {config.url}")

    async def connect(self, auth_token: Optional[str] = None) -> bool:
        """
        Establish WebSocket connection with optional authentication

        Args:
            auth_token: Authentication token for private channels

        Returns:
            bool: True if connection successful
        """
        if self.state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            logger.warning("[CONNECTION_MANAGER] Connection already active")
            return True

        self.state = ConnectionState.CONNECTING
        logger.info(f"[CONNECTION_MANAGER] Connecting to {self.config.url}")

        try:
            # Determine WebSocket URL (use auth URL if token provided)
            ws_url = (
                self.config.auth_url if auth_token and self.config.auth_url else self.config.url
            )

            # Additional headers for authentication if needed
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            # Create WebSocket connection with timeout
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    ws_url,
                    ping_interval=self.config.ping_interval,
                    ping_timeout=self.config.ping_timeout,
                    close_timeout=self.config.close_timeout,
                    extra_headers=headers if headers else None,
                ),
                timeout=self.config.connection_timeout,
            )

            # Update connection state
            self.state = ConnectionState.CONNECTED
            self.status.connected = True
            self.status.connection_time = time.time()
            self.connection_start_time = time.time()
            self.last_message_time = time.time()

            # Reset reconnect state on successful connection
            self.reconnect_state.reset()

            # Start background tasks
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.message_handler_task = asyncio.create_task(self._message_handler_loop())

            # Call connection callback
            if self.on_connected:
                try:
                    await self.on_connected()
                except Exception as e:
                    logger.error(f"[CONNECTION_MANAGER] Connection callback error: {e}")

            logger.info("[CONNECTION_MANAGER] Connection established successfully")

            # Send pending authentication if token provided
            if auth_token:
                await self._authenticate(auth_token)

            return True

        except asyncio.TimeoutError:
            logger.error(
                f"[CONNECTION_MANAGER] Connection timeout after {self.config.connection_timeout}s"
            )
            self.state = ConnectionState.FAILED
            return False

        except Exception as e:
            logger.error(f"[CONNECTION_MANAGER] Connection failed: {e}")
            self.state = ConnectionState.FAILED
            self.status.error_count += 1
            self.status.last_error = str(e)

            # Call error callback
            if self.on_error:
                try:
                    await self.on_error(e)
                except Exception as callback_error:
                    logger.error(f"[CONNECTION_MANAGER] Error callback failed: {callback_error}")

            return False

    async def disconnect(self):
        """Gracefully disconnect WebSocket"""
        logger.info("[CONNECTION_MANAGER] Initiating graceful disconnect")

        self._shutdown = True

        # Cancel background tasks
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.message_handler_task and not self.message_handler_task.done():
            self.message_handler_task.cancel()
            try:
                await self.message_handler_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket connection
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"[CONNECTION_MANAGER] Error closing WebSocket: {e}")

        # Update state
        self.state = ConnectionState.DISCONNECTED
        self.status.connected = False
        self.status.authenticated = False
        self.websocket = None

        # Call disconnection callback
        if self.on_disconnected:
            try:
                await self.on_disconnected()
            except Exception as e:
                logger.error(f"[CONNECTION_MANAGER] Disconnection callback error: {e}")

        logger.info("[CONNECTION_MANAGER] Disconnected successfully")

    async def send_message(self, message: dict[str, Any]) -> bool:
        """
        Send message to WebSocket with queuing for offline scenarios

        Args:
            message: Message dictionary to send

        Returns:
            bool: True if sent successfully
        """
        if self.state != ConnectionState.CONNECTED or not self.websocket:
            # Queue message for later sending
            if len(self.pending_messages) < self.config.message_queue_size:
                self.pending_messages.append(message)
                logger.debug(
                    f"[CONNECTION_MANAGER] Queued message: {message.get('method', 'unknown')}"
                )
            else:
                logger.warning("[CONNECTION_MANAGER] Message queue full, dropping message")
            return False

        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            logger.debug(f"[CONNECTION_MANAGER] Sent message: {message.get('method', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"[CONNECTION_MANAGER] Failed to send message: {e}")
            # Re-queue message if connection is lost
            if len(self.pending_messages) < self.config.message_queue_size:
                self.pending_messages.append(message)
            return False

    async def _authenticate(self, auth_token: str):
        """Send authentication message"""
        auth_message = {"method": "authenticate", "params": {"token": auth_token}}

        success = await self.send_message(auth_message)
        if success:
            logger.info("[CONNECTION_MANAGER] Authentication message sent")
        else:
            logger.error("[CONNECTION_MANAGER] Failed to send authentication message")

    async def _message_handler_loop(self):
        """Main message handling loop"""
        logger.info("[CONNECTION_MANAGER] Starting message handler loop")

        while not self._shutdown and self.websocket and not self.websocket.closed:
            try:
                # Receive message with timeout
                message_raw = await asyncio.wait_for(
                    self.websocket.recv(), timeout=self.config.heartbeat_timeout
                )

                # Update last message time
                self.last_message_time = time.time()

                # Parse JSON message
                try:
                    message = json.loads(message_raw)
                except json.JSONDecodeError as e:
                    logger.error(f"[CONNECTION_MANAGER] Invalid JSON received: {e}")
                    continue

                # Handle heartbeat messages
                if message.get("channel") == "heartbeat":
                    self.status.last_heartbeat = time.time()
                    logger.debug("[CONNECTION_MANAGER] Heartbeat received")
                    continue

                # Handle authentication responses
                if message.get("method") == "authenticate":
                    if message.get("success"):
                        self.state = ConnectionState.AUTHENTICATED
                        self.status.authenticated = True
                        logger.info("[CONNECTION_MANAGER] Authentication successful")

                        if self.on_authenticated:
                            try:
                                await self.on_authenticated()
                            except Exception as e:
                                logger.error(
                                    f"[CONNECTION_MANAGER] Authentication callback error: {e}"
                                )
                    else:
                        error = message.get("error", "Unknown authentication error")
                        logger.error(f"[CONNECTION_MANAGER] Authentication failed: {error}")
                        self.status.last_error = error
                    continue

                # Queue message for processing
                try:
                    self.message_queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning("[CONNECTION_MANAGER] Message queue full, dropping message")

                # Call message callback
                if self.on_message:
                    try:
                        await self.on_message(message)
                    except Exception as e:
                        logger.error(f"[CONNECTION_MANAGER] Message callback error: {e}")

            except asyncio.TimeoutError:
                logger.warning(
                    f"[CONNECTION_MANAGER] No message received for {self.config.heartbeat_timeout}s"
                )
                # Connection might be stale, trigger reconnection
                if not self._shutdown:
                    asyncio.create_task(self._handle_connection_loss())
                break

            except ConnectionClosed:
                logger.warning("[CONNECTION_MANAGER] WebSocket connection closed")
                if not self._shutdown:
                    asyncio.create_task(self._handle_connection_loss())
                break

            except Exception as e:
                logger.error(f"[CONNECTION_MANAGER] Message handler error: {e}")
                self.status.error_count += 1
                self.status.last_error = str(e)

                if not self._shutdown:
                    await asyncio.sleep(1)  # Brief pause before continuing

    async def _heartbeat_loop(self):
        """Heartbeat monitoring loop"""
        logger.info("[CONNECTION_MANAGER] Starting heartbeat loop")

        while not self._shutdown and self.state == ConnectionState.CONNECTED:
            try:
                current_time = time.time()

                # Check if we should send a ping
                if current_time - self.last_ping_time > self.config.ping_interval:
                    if self.websocket and not self.websocket.closed:
                        try:
                            await self.websocket.ping()
                            self.last_ping_time = current_time
                            logger.debug("[CONNECTION_MANAGER] Ping sent")
                        except Exception as e:
                            logger.warning(f"[CONNECTION_MANAGER] Ping failed: {e}")

                # Check for stale connection
                if current_time - self.last_message_time > self.config.heartbeat_timeout:
                    logger.warning(
                        f"[CONNECTION_MANAGER] Connection appears stale (no messages for {self.config.heartbeat_timeout}s)"
                    )
                    if not self._shutdown:
                        asyncio.create_task(self._handle_connection_loss())
                    break

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"[CONNECTION_MANAGER] Heartbeat loop error: {e}")
                await asyncio.sleep(5)

    async def _handle_connection_loss(self):
        """Handle connection loss and initiate reconnection"""
        if self._shutdown:
            return

        logger.warning("[CONNECTION_MANAGER] Handling connection loss")

        # Update state
        self.state = ConnectionState.RECONNECTING
        self.status.connected = False
        self.status.authenticated = False

        # Call disconnection callback
        if self.on_disconnected:
            try:
                await self.on_disconnected()
            except Exception as e:
                logger.error(f"[CONNECTION_MANAGER] Disconnection callback error: {e}")

        # Start reconnection process
        await self._reconnect_loop()

    async def _reconnect_loop(self):
        """Automatic reconnection loop with exponential backoff"""
        logger.info("[CONNECTION_MANAGER] Starting reconnection loop")

        while (
            not self._shutdown
            and self.reconnect_state.attempt_count < self.config.max_reconnect_attempts
        ):
            # Wait for reconnect delay
            await asyncio.sleep(self.reconnect_state.next_delay)

            if self._shutdown:
                break

            # Increment attempt count
            self.reconnect_state.increment()

            logger.info(
                f"[CONNECTION_MANAGER] Reconnection attempt {self.reconnect_state.attempt_count}/{self.config.max_reconnect_attempts}"
            )

            try:
                # Clean up existing connection
                if self.websocket and not self.websocket.closed:
                    await self.websocket.close()

                # Attempt reconnection
                success = await self.connect()

                if success:
                    logger.info("[CONNECTION_MANAGER] Reconnection successful")

                    # Send any pending messages
                    await self._send_pending_messages()

                    self.status.reconnect_count += 1
                    return  # Exit reconnection loop
                else:
                    logger.warning(
                        f"[CONNECTION_MANAGER] Reconnection attempt {self.reconnect_state.attempt_count} failed"
                    )

            except Exception as e:
                logger.error(f"[CONNECTION_MANAGER] Reconnection error: {e}")
                self.status.error_count += 1
                self.status.last_error = str(e)

        # Max attempts reached
        if self.reconnect_state.attempt_count >= self.config.max_reconnect_attempts:
            logger.error(
                f"[CONNECTION_MANAGER] Max reconnection attempts ({self.config.max_reconnect_attempts}) reached"
            )
            self.state = ConnectionState.FAILED

    async def _send_pending_messages(self):
        """Send any queued messages after reconnection"""
        if not self.pending_messages:
            return

        logger.info(f"[CONNECTION_MANAGER] Sending {len(self.pending_messages)} pending messages")

        # Send pending messages
        messages_to_send = self.pending_messages.copy()
        self.pending_messages.clear()

        for message in messages_to_send:
            success = await self.send_message(message)
            if not success:
                # Re-queue if send failed
                self.pending_messages.append(message)

        if self.pending_messages:
            logger.warning(
                f"[CONNECTION_MANAGER] {len(self.pending_messages)} messages remain queued"
            )

    async def get_queued_message(self) -> Optional[dict[str, Any]]:
        """Get next queued message for processing"""
        try:
            return await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def set_callback(self, callback_type: str, callback: Callable):
        """Set callback for connection events"""
        if callback_type == "message":
            self.on_message = callback
        elif callback_type == "connected":
            self.on_connected = callback
        elif callback_type == "disconnected":
            self.on_disconnected = callback
        elif callback_type == "error":
            self.on_error = callback
        elif callback_type == "authenticated":
            self.on_authenticated = callback
        else:
            logger.warning(f"[CONNECTION_MANAGER] Unknown callback type: {callback_type}")

    def get_status(self) -> dict[str, Any]:
        """Get detailed connection status"""
        return {
            "state": self.state.value,
            "status": self.status.to_dict(),
            "reconnect_state": {
                "attempt_count": self.reconnect_state.attempt_count,
                "next_delay": self.reconnect_state.next_delay,
                "last_attempt_time": self.reconnect_state.last_attempt_time,
            },
            "pending_messages": len(self.pending_messages),
            "queue_size": self.message_queue.qsize(),
        }

    @property
    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self.state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]

    @property
    def is_authenticated(self) -> bool:
        """Check if connection is authenticated"""
        return self.state == ConnectionState.AUTHENTICATED
