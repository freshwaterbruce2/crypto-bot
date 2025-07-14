"""
WebSocket manager for Kraken exchange real-time data feeds.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import threading
from enum import Enum
import time

logger = logging.getLogger(__name__)


class WebSocketStatus(Enum):
    """WebSocket connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class SubscriptionRequest:
    """WebSocket subscription request."""
    name: str
    pair: List[str]
    subscription: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebSocketMessage:
    """WebSocket message data."""
    channel: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    raw_message: Optional[str] = None


class KrakenWebSocketManager:
    """
    WebSocket manager for Kraken exchange real-time data feeds.
    Handles connections, subscriptions, and message processing.
    """
    
    def __init__(self, 
                 endpoint: str = "wss://ws.kraken.com",
                 reconnect_delay: int = 5,
                 max_reconnect_attempts: int = 10,
                 ping_interval: int = 30,
                 ping_timeout: int = 15):  # 2025 OPTIMIZATION: Increased for better Pro account performance
        """
        Initialize the WebSocket manager.
        
        Args:
            endpoint: WebSocket endpoint URL
            reconnect_delay: Delay between reconnection attempts (seconds)
            max_reconnect_attempts: Maximum number of reconnection attempts
            ping_interval: Ping interval (seconds)
            ping_timeout: Ping timeout (seconds)
        """
        self.endpoint = endpoint
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ping_interval = ping_interval
        self.ping_timeout = min(ping_timeout, 15)  # 2025 OPTIMIZATION: Max 15s timeout
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.status = WebSocketStatus.DISCONNECTED
        self.reconnect_attempts = 0
        self.last_ping = 0
        
        # Subscriptions
        self.subscriptions: Dict[str, SubscriptionRequest] = {}
        self.active_subscriptions: Set[str] = set()
        
        # Message handling
        self.message_handlers: Dict[str, Callable] = {}
        self.default_handler: Optional[Callable] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Threading
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.websocket_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Statistics
        self.messages_received = 0
        self.messages_sent = 0
        self.connection_time = None
        self.last_message_time = None
        
        logger.info("KrakenWebSocketManager initialized")
    
    def start(self) -> None:
        """Start the WebSocket manager."""
        if self.running:
            logger.warning("WebSocket manager already running")
            return
        
        self.running = True
        self.websocket_thread = threading.Thread(target=self._run_websocket_loop, daemon=True)
        self.websocket_thread.start()
        
        logger.info("WebSocket manager started")
    
    def stop(self) -> None:
        """Stop the WebSocket manager."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop the event loop
        if self.event_loop and self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        
        # Wait for thread to finish
        if self.websocket_thread and self.websocket_thread.is_alive():
            self.websocket_thread.join(timeout=5)
        
        logger.info("WebSocket manager stopped")
    
    def _run_websocket_loop(self) -> None:
        """Run the WebSocket event loop in a separate thread."""
        try:
            # Create new event loop for this thread
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            
            # Run the main WebSocket coroutine
            self.event_loop.run_until_complete(self._websocket_main())
            
        except Exception as e:
            logger.error(f"Error in WebSocket loop: {e}")
        finally:
            if self.event_loop:
                self.event_loop.close()
    
    async def _websocket_main(self) -> None:
        """Main WebSocket coroutine."""
        while self.running:
            try:
                await self._connect_and_run()
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.reconnect_attempts += 1
                    self.status = WebSocketStatus.RECONNECTING
                    
                    logger.info(f"Reconnecting in {self.reconnect_delay} seconds (attempt {self.reconnect_attempts})")
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    logger.error("Max reconnection attempts reached")
                    self.status = WebSocketStatus.ERROR
                    break
    
    async def _connect_and_run(self) -> None:
        """Connect to WebSocket and handle messages."""
        self.status = WebSocketStatus.CONNECTING
        
        try:
            async with websockets.connect(
                self.endpoint,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout
            ) as websocket:
                self.websocket = websocket
                self.status = WebSocketStatus.CONNECTED
                self.connection_time = datetime.now()
                self.reconnect_attempts = 0
                
                logger.info(f"Connected to WebSocket: {self.endpoint}")
                
                # Resubscribe to all active subscriptions
                await self._resubscribe_all()
                
                # Start message processing tasks
                receive_task = asyncio.create_task(self._receive_messages())
                process_task = asyncio.create_task(self._process_messages())
                
                # Wait for tasks to complete
                await asyncio.gather(receive_task, process_task)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.status = WebSocketStatus.DISCONNECTED
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.status = WebSocketStatus.ERROR
        finally:
            self.websocket = None
    
    async def _receive_messages(self) -> None:
        """Receive messages from WebSocket."""
        try:
            async for message in self.websocket:
                self.messages_received += 1
                self.last_message_time = datetime.now()
                
                try:
                    # Parse JSON message
                    data = json.loads(message)
                    
                    # Create message object
                    ws_message = WebSocketMessage(
                        channel=self._extract_channel(data),
                        data=data,
                        raw_message=message
                    )
                    
                    # Queue message for processing
                    await self.message_queue.put(ws_message)
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message: {message}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket receive loop closed")
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
    
    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while self.running:
            try:
                # Get message from queue with timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                # Handle the message
                await self._handle_message(message)
                
            except asyncio.TimeoutError:
                # Timeout is expected, continue processing
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def _handle_message(self, message: WebSocketMessage) -> None:
        """Handle a WebSocket message."""
        try:
            channel = message.channel
            
            # Check for specific handler
            if channel in self.message_handlers:
                handler = self.message_handlers[channel]
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            elif self.default_handler:
                # Use default handler
                if asyncio.iscoroutinefunction(self.default_handler):
                    await self.default_handler(message)
                else:
                    self.default_handler(message)
            else:
                logger.debug(f"No handler for channel: {channel}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def _extract_channel(self, data: Dict[str, Any]) -> str:
        """Extract channel name from message data."""
        # Handle different message formats
        if isinstance(data, dict):
            # System messages
            if "event" in data:
                return f"system.{data['event']}"
            
            # Channel data messages
            if "channelName" in data:
                return data["channelName"]
            
            # Array format messages
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[-1], dict) and "channelName" in data[-1]:
                    return data[-1]["channelName"]
                elif isinstance(data[-1], dict) and "pair" in data[-1]:
                    return f"data.{data[-1]['pair']}"
        
        return "unknown"
    
    async def subscribe(self, name: str, pairs: List[str], **kwargs) -> bool:
        """
        Subscribe to a WebSocket channel.
        
        Args:
            name: Subscription name (e.g., 'ticker', 'trade', 'book')
            pairs: List of trading pairs to subscribe to
            **kwargs: Additional subscription parameters
            
        Returns:
            True if subscription was successful
        """
        try:
            # Create subscription request
            subscription_request = SubscriptionRequest(
                name=name,
                pair=pairs,
                subscription=kwargs
            )
            
            # Store subscription
            sub_key = f"{name}:{','.join(pairs)}"
            self.subscriptions[sub_key] = subscription_request
            
            # Send subscription if connected
            if self.status == WebSocketStatus.CONNECTED and self.websocket:
                await self._send_subscription(subscription_request)
                self.active_subscriptions.add(sub_key)
                
                logger.info(f"Subscribed to {name} for pairs: {pairs}")
                return True
            else:
                logger.warning(f"Not connected - subscription queued: {name}")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to {name}: {e}")
            return False
    
    async def unsubscribe(self, name: str, pairs: List[str]) -> bool:
        """
        Unsubscribe from a WebSocket channel.
        
        Args:
            name: Subscription name
            pairs: List of trading pairs to unsubscribe from
            
        Returns:
            True if unsubscription was successful
        """
        try:
            sub_key = f"{name}:{','.join(pairs)}"
            
            # Remove from active subscriptions
            self.active_subscriptions.discard(sub_key)
            
            # Send unsubscription if connected
            if self.status == WebSocketStatus.CONNECTED and self.websocket:
                unsubscribe_msg = {
                    "event": "unsubscribe",
                    "pair": pairs,
                    "subscription": {"name": name}
                }
                
                await self._send_message(unsubscribe_msg)
                
                logger.info(f"Unsubscribed from {name} for pairs: {pairs}")
                return True
            else:
                logger.warning(f"Not connected - unsubscription queued: {name}")
                return False
                
        except Exception as e:
            logger.error(f"Error unsubscribing from {name}: {e}")
            return False
    
    async def _send_subscription(self, subscription: SubscriptionRequest) -> None:
        """Send a subscription request to the WebSocket."""
        message = {
            "event": "subscribe",
            "pair": subscription.pair,
            "subscription": {"name": subscription.name, **subscription.subscription}
        }
        
        await self._send_message(message)
    
    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the WebSocket."""
        if self.websocket and self.status == WebSocketStatus.CONNECTED:
            try:
                message_str = json.dumps(message)
                await self.websocket.send(message_str)
                self.messages_sent += 1
                
                logger.debug(f"Sent message: {message_str}")
                
            except Exception as e:
                logger.error(f"Error sending message: {e}")
    
    async def _resubscribe_all(self) -> None:
        """Resubscribe to all active subscriptions."""
        for sub_key in list(self.active_subscriptions):
            if sub_key in self.subscriptions:
                subscription = self.subscriptions[sub_key]
                await self._send_subscription(subscription)
                
                logger.debug(f"Resubscribed to: {sub_key}")
    
    def add_message_handler(self, channel: str, handler: Callable) -> None:
        """
        Add a message handler for a specific channel.
        
        Args:
            channel: Channel name to handle
            handler: Handler function (can be async)
        """
        self.message_handlers[channel] = handler
        logger.info(f"Added handler for channel: {channel}")
    
    def set_default_handler(self, handler: Callable) -> None:
        """
        Set the default message handler.
        
        Args:
            handler: Default handler function (can be async)
        """
        self.default_handler = handler
        logger.info("Set default message handler")
    
    def get_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status and statistics."""
        return {
            'status': self.status.value,
            'connected': self.status == WebSocketStatus.CONNECTED,
            'connection_time': self.connection_time.isoformat() if self.connection_time else None,
            'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
            'reconnect_attempts': self.reconnect_attempts,
            'messages_received': self.messages_received,
            'messages_sent': self.messages_sent,
            'active_subscriptions': len(self.active_subscriptions),
            'subscriptions': list(self.active_subscriptions),
            'queue_size': self.message_queue.qsize() if self.message_queue else 0
        }
    
    def get_subscriptions(self) -> Dict[str, SubscriptionRequest]:
        """Get all subscriptions."""
        return self.subscriptions.copy()
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.status == WebSocketStatus.CONNECTED
    
    def clear_subscriptions(self) -> None:
        """Clear all subscriptions."""
        self.subscriptions.clear()
        self.active_subscriptions.clear()
        
        logger.info("Cleared all subscriptions")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed WebSocket statistics."""
        uptime = None
        if self.connection_time:
            uptime = (datetime.now() - self.connection_time).total_seconds()
        
        return {
            'status': self.status.value,
            'uptime_seconds': uptime,
            'messages_received': self.messages_received,
            'messages_sent': self.messages_sent,
            'message_rate': self.messages_received / uptime if uptime and uptime > 0 else 0,
            'reconnect_attempts': self.reconnect_attempts,
            'active_subscriptions': len(self.active_subscriptions),
            'total_subscriptions': len(self.subscriptions),
            'queue_size': self.message_queue.qsize() if self.message_queue else 0,
            'handlers_registered': len(self.message_handlers),
            'has_default_handler': self.default_handler is not None
        }
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        if self.running:
            self.stop()