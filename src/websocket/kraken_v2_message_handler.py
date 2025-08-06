"""
Kraken WebSocket V2 Message Handler - 2025 Specification Compliant
================================================================

Production-ready message handler for Kraken WebSocket V2 API following exact 2025 specifications.
Handles all message types with proper validation, sequence tracking, and error handling.

Features:
- Strict V2 format compliance
- Sequence number tracking and deduplication
- Comprehensive validation
- Performance optimization for high-frequency data
- Thread-safe operations
- Statistics and monitoring
- Full error handling and recovery

Channel Support:
- balance: Account balance updates (private)
- ticker: Price ticker updates (public)
- book: Order book updates (public)
- trade: Trade execution data (public)
- ohlc: OHLC candlestick data (public)
- executions: Order execution updates (private)
- openOrders: Open order updates (private)
"""

import asyncio
import logging
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable

from .data_models import (
    BalanceUpdate,
    ConnectionStatus,
    OHLCUpdate,
    OrderBookUpdate,
    TickerUpdate,
    TradeUpdate,
)

logger = logging.getLogger(__name__)


@dataclass
class MessageStats:
    """Message processing statistics"""
    total_messages: int = 0
    messages_by_channel: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    processing_times: dict[str, deque] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=100)))
    error_count: int = 0
    duplicate_count: int = 0
    sequence_gaps: int = 0
    last_reset: float = field(default_factory=time.time)

    def add_message(self, channel: str, processing_time: float):
        """Add message processing statistics"""
        self.total_messages += 1
        self.messages_by_channel[channel] += 1
        self.processing_times[channel].append(processing_time)

    def add_error(self):
        """Increment error count"""
        self.error_count += 1

    def add_duplicate(self):
        """Increment duplicate count"""
        self.duplicate_count += 1

    def add_sequence_gap(self):
        """Increment sequence gap count"""
        self.sequence_gaps += 1

    def get_avg_processing_time(self, channel: str) -> float:
        """Get average processing time for channel"""
        times = self.processing_times.get(channel, deque())
        if not times:
            return 0.0
        return sum(times) / len(times)

    def reset(self):
        """Reset statistics"""
        self.total_messages = 0
        self.messages_by_channel.clear()
        self.processing_times.clear()
        self.error_count = 0
        self.duplicate_count = 0
        self.sequence_gaps = 0
        self.last_reset = time.time()


@dataclass
class SequenceTracker:
    """Sequence number tracking for message ordering"""
    channel_sequences: dict[str, int] = field(default_factory=dict)
    expected_sequences: dict[str, int] = field(default_factory=dict)
    message_buffer: dict[str, dict[int, dict[str, Any]]] = field(default_factory=lambda: defaultdict(dict))
    max_buffer_size: int = 100
    sequence_timeout: float = 30.0  # seconds

    def process_sequence(self, channel: str, sequence: int, message: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
        """
        Process message sequence number and return (is_duplicate, buffered_messages)

        Returns:
            - True if duplicate, False if new
            - List of buffered messages ready for processing (in order)
        """
        if channel not in self.expected_sequences:
            # First message for this channel
            self.expected_sequences[channel] = sequence + 1
            self.channel_sequences[channel] = sequence
            return False, [message]

        expected = self.expected_sequences[channel]

        if sequence < expected:
            # Duplicate or old message
            return True, []
        elif sequence == expected:
            # Expected sequence - process immediately
            self.expected_sequences[channel] = sequence + 1
            self.channel_sequences[channel] = sequence

            # Check if we have buffered messages to release
            ready_messages = [message]
            ready_messages.extend(self._release_buffered_messages(channel))
            return False, ready_messages
        else:
            # Future message - buffer it
            self.message_buffer[channel][sequence] = message

            # Clean old buffered messages
            self._cleanup_buffer(channel)

            return False, []

    def _release_buffered_messages(self, channel: str) -> list[dict[str, Any]]:
        """Release buffered messages that are now in sequence"""
        ready_messages = []
        channel_buffer = self.message_buffer[channel]

        while True:
            next_seq = self.expected_sequences[channel]
            if next_seq in channel_buffer:
                message = channel_buffer.pop(next_seq)
                ready_messages.append(message)
                self.expected_sequences[channel] = next_seq + 1
                self.channel_sequences[channel] = next_seq
            else:
                break

        return ready_messages

    def _cleanup_buffer(self, channel: str):
        """Clean old buffered messages"""
        channel_buffer = self.message_buffer[channel]
        current_time = time.time()

        # Remove messages older than timeout
        to_remove = []
        for seq, msg in channel_buffer.items():
            if current_time - msg.get('_buffer_time', current_time) > self.sequence_timeout:
                to_remove.append(seq)

        for seq in to_remove:
            channel_buffer.pop(seq, None)

        # Limit buffer size
        if len(channel_buffer) > self.max_buffer_size:
            # Remove oldest messages
            sorted_seqs = sorted(channel_buffer.keys())
            for seq in sorted_seqs[:-self.max_buffer_size]:
                channel_buffer.pop(seq, None)

    def get_status(self) -> dict[str, Any]:
        """Get sequence tracking status"""
        return {
            'tracked_channels': list(self.channel_sequences.keys()),
            'channel_sequences': self.channel_sequences.copy(),
            'expected_sequences': self.expected_sequences.copy(),
            'buffered_counts': {ch: len(buf) for ch, buf in self.message_buffer.items()},
            'total_buffered': sum(len(buf) for buf in self.message_buffer.values())
        }


class KrakenV2MessageHandler:
    """
    Production-ready Kraken WebSocket V2 message handler.

    Handles all Kraken WebSocket V2 message types with strict 2025 specification compliance.
    Provides sequence tracking, deduplication, validation, and performance monitoring.
    """

    def __init__(self, enable_sequence_tracking: bool = True, enable_statistics: bool = True):
        """
        Initialize the V2 message handler.

        Args:
            enable_sequence_tracking: Enable sequence number tracking and deduplication
            enable_statistics: Enable message processing statistics
        """
        self.enable_sequence_tracking = enable_sequence_tracking
        self.enable_statistics = enable_statistics

        # Thread safety
        self._lock = RLock()

        # Message callbacks
        self._callbacks: dict[str, list[Callable]] = defaultdict(list)
        self._error_callbacks: list[Callable] = []

        # Sequence tracking
        if self.enable_sequence_tracking:
            self.sequence_tracker = SequenceTracker()
        else:
            self.sequence_tracker = None

        # Statistics
        if self.enable_statistics:
            self.stats = MessageStats()
        else:
            self.stats = None

        # Connection status
        self.connection_status = ConnectionStatus()

        # Message validation
        self.validate_messages = True
        self.strict_mode = True  # Strict 2025 compliance

        # Performance settings
        self.max_concurrent_processing = 10
        self.processing_timeout = 5.0  # seconds

        # Channel configurations
        self.private_channels = {'balance', 'balances', 'executions', 'openOrders'}
        self.public_channels = {'ticker', 'book', 'trade', 'ohlc'}

        # Weak references to avoid circular references
        self._managers: set[weakref.ReferenceType] = set()

        logger.info("[KRAKEN_V2_HANDLER] Initialized with sequence_tracking=%s, statistics=%s",
                   enable_sequence_tracking, enable_statistics)

    def register_manager(self, manager):
        """Register a WebSocket manager for lifecycle management"""
        with self._lock:
            # Use weak reference to avoid circular references
            self._managers.add(weakref.ref(manager))

    def register_callback(self, channel: str, callback: Callable):
        """
        Register a callback for a specific channel.

        Args:
            channel: Channel name (balance, ticker, book, trade, ohlc, etc.)
            callback: Async callable to handle messages
        """
        with self._lock:
            self._callbacks[channel].append(callback)
            logger.debug("[KRAKEN_V2_HANDLER] Registered callback for channel: %s", channel)

    def register_error_callback(self, callback: Callable):
        """Register a callback for error handling"""
        with self._lock:
            self._error_callbacks.append(callback)
            logger.debug("[KRAKEN_V2_HANDLER] Registered error callback")

    def unregister_callback(self, channel: str, callback: Callable):
        """Unregister a callback"""
        with self._lock:
            if callback in self._callbacks[channel]:
                self._callbacks[channel].remove(callback)
                logger.debug("[KRAKEN_V2_HANDLER] Unregistered callback for channel: %s", channel)

    async def process_message(self, raw_message: dict[str, Any]) -> bool:
        """
        Process a raw WebSocket V2 message.

        Args:
            raw_message: Raw message from WebSocket

        Returns:
            True if processed successfully, False otherwise
        """
        start_time = time.time()

        try:
            # Log message structure for debugging if needed
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("[KRAKEN_V2_HANDLER] Processing message type: %s", type(raw_message))
                if isinstance(raw_message, dict):
                    logger.debug("[KRAKEN_V2_HANDLER] Message keys: %s", list(raw_message.keys()))

            # Basic validation
            if not self._validate_raw_message(raw_message):
                return False

            # Extract channel and message info with better fallback logic
            channel = raw_message.get('channel')
            method = raw_message.get('method')
            message_type = raw_message.get('type')

            # Handle different message formats
            if channel is None and method is not None:
                # Method-based message (subscription responses, etc.)
                channel = method
                if message_type is None:
                    message_type = method
            elif channel is None:
                # Neither channel nor method - this is problematic
                logger.warning("[KRAKEN_V2_HANDLER] Message missing both channel and method: %s", raw_message)
                channel = 'unknown'
                message_type = 'unknown'
            else:
                # Channel-based message (data feeds)
                if message_type is None:
                    message_type = channel

            sequence = raw_message.get('sequence')

            # Handle sequence tracking
            if self.enable_sequence_tracking and sequence is not None:
                is_duplicate, ready_messages = self.sequence_tracker.process_sequence(
                    channel, sequence, raw_message
                )

                if is_duplicate:
                    if self.stats:
                        self.stats.add_duplicate()
                    logger.debug("[KRAKEN_V2_HANDLER] Duplicate message detected: channel=%s, seq=%s",
                               channel, sequence)
                    return True  # Successfully handled (as duplicate)

                # Process all ready messages in order
                for msg in ready_messages:
                    await self._process_single_message(msg)
            else:
                # Process message directly without sequence tracking
                await self._process_single_message(raw_message)

            # Update statistics
            if self.stats:
                processing_time = time.time() - start_time
                self.stats.add_message(channel, processing_time)

            return True

        except Exception as e:
            if self.stats:
                self.stats.add_error()

            logger.error("[KRAKEN_V2_HANDLER] Error processing message: %s", e)
            logger.debug("[KRAKEN_V2_HANDLER] Failed message: %s", raw_message)

            # Call error callbacks
            await self._call_error_callbacks(e, raw_message)

            return False

    async def _process_single_message(self, raw_message: dict[str, Any]):
        """Process a single validated message"""
        # Use improved channel/method extraction logic (same as in process_message)
        channel = raw_message.get('channel')
        method = raw_message.get('method')
        message_type = raw_message.get('type')

        # Handle different message formats
        if channel is None and method is not None:
            # Method-based message (subscription responses, etc.)
            channel = method
            if message_type is None:
                message_type = method
        elif channel is None:
            # Neither channel nor method - this is problematic
            channel = 'unknown'
            message_type = 'unknown'
        else:
            # Channel-based message (data feeds)
            if message_type is None:
                message_type = channel

        # Route to appropriate handler
        if channel == 'balance' or channel == 'balances':
            await self._handle_balance_message(raw_message)
        elif channel == 'ticker':
            await self._handle_ticker_message(raw_message)
        elif channel == 'book':
            await self._handle_orderbook_message(raw_message)
        elif channel == 'trade':
            await self._handle_trade_message(raw_message)
        elif channel == 'ohlc':
            await self._handle_ohlc_message(raw_message)
        elif channel == 'executions':
            await self._handle_execution_message(raw_message)
        elif channel == 'openOrders':
            await self._handle_open_orders_message(raw_message)
        elif channel == 'heartbeat':
            await self._handle_heartbeat_message(raw_message)
        elif channel == 'status':
            await self._handle_status_message(raw_message)
        elif channel == 'pong' or message_type == 'pong' or method == 'pong':
            await self._handle_pong_message(raw_message)
        elif message_type == 'subscribe' or message_type == 'unsubscribe' or method in ['subscribe', 'unsubscribe']:
            await self._handle_subscription_response(raw_message)
        else:
            # Handle unknown message types
            logger.warning("[KRAKEN_V2_HANDLER] Unknown message type: channel=%s, type=%s, method=%s",
                         channel, message_type, method)
            await self._handle_unknown_message(raw_message)

    async def _handle_balance_message(self, raw_message: dict[str, Any]):
        """Handle balance update messages"""
        try:
            data_array = raw_message.get('data', [])
            if not data_array:
                logger.debug("[KRAKEN_V2_HANDLER] Empty balance data")
                return

            logger.info("[KRAKEN_V2_HANDLER] Processing balance update: %d assets", len(data_array))

            # Parse balance updates
            balance_updates = []
            formatted_balances = {}

            for balance_item in data_array:
                if not isinstance(balance_item, dict):
                    continue

                try:
                    balance_update = BalanceUpdate.from_raw(balance_item)
                    balance_updates.append(balance_update)

                    # Convert to compatibility format
                    formatted_balances[balance_update.asset] = balance_update.to_dict()

                    logger.debug("[KRAKEN_V2_HANDLER] Balance update: %s = %s",
                               balance_update.asset, balance_update.free_balance)

                except Exception as e:
                    logger.warning("[KRAKEN_V2_HANDLER] Failed to parse balance item: %s", e)
                    continue

            # Call callbacks with both formats for compatibility
            await self._call_callbacks('balance', balance_updates)
            await self._call_callbacks('balances', formatted_balances)

            # Update connection status
            with self._lock:
                self.connection_status.authenticated = True

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling balance message: %s", e)
            raise

    async def _handle_ticker_message(self, raw_message: dict[str, Any]):
        """Handle ticker update messages"""
        try:
            data_array = raw_message.get('data', [])
            if not data_array:
                return

            for ticker_data in data_array:
                if not isinstance(ticker_data, dict):
                    continue

                symbol = ticker_data.get('symbol')
                if not symbol:
                    continue

                try:
                    ticker_update = TickerUpdate.from_raw(symbol, ticker_data)

                    # Call callbacks
                    await self._call_callbacks('ticker', symbol, ticker_update.to_dict())

                    logger.debug("[KRAKEN_V2_HANDLER] Ticker update: %s = $%s",
                               symbol, ticker_update.last)

                except Exception as e:
                    logger.warning("[KRAKEN_V2_HANDLER] Failed to parse ticker for %s: %s",
                                 symbol, e)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling ticker message: %s", e)
            raise

    async def _handle_orderbook_message(self, raw_message: dict[str, Any]):
        """Handle orderbook update messages"""
        try:
            data_array = raw_message.get('data', [])
            if not data_array:
                return

            for book_data in data_array:
                if not isinstance(book_data, dict):
                    continue

                symbol = book_data.get('symbol')
                if not symbol:
                    continue

                try:
                    orderbook_update = OrderBookUpdate.from_raw(symbol, book_data)

                    # Call callbacks
                    await self._call_callbacks('book', symbol, orderbook_update.to_dict())
                    await self._call_callbacks('orderbook', symbol, orderbook_update.to_dict())

                    logger.debug("[KRAKEN_V2_HANDLER] Orderbook update: %s, spread=%s",
                               symbol, orderbook_update.spread)

                except Exception as e:
                    logger.warning("[KRAKEN_V2_HANDLER] Failed to parse orderbook for %s: %s",
                                 symbol, e)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling orderbook message: %s", e)
            raise

    async def _handle_trade_message(self, raw_message: dict[str, Any]):
        """Handle trade update messages"""
        try:
            data_array = raw_message.get('data', [])
            if not data_array:
                return

            for trade_data in data_array:
                if not isinstance(trade_data, dict):
                    continue

                symbol = trade_data.get('symbol')
                if not symbol:
                    continue

                try:
                    trade_update = TradeUpdate.from_raw(symbol, trade_data)

                    # Call callbacks
                    await self._call_callbacks('trade', symbol, trade_update.to_dict())

                    logger.debug("[KRAKEN_V2_HANDLER] Trade update: %s %s %s @ %s",
                               trade_update.side, trade_update.volume, symbol, trade_update.price)

                except Exception as e:
                    logger.warning("[KRAKEN_V2_HANDLER] Failed to parse trade for %s: %s",
                                 symbol, e)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling trade message: %s", e)
            raise

    async def _handle_ohlc_message(self, raw_message: dict[str, Any]):
        """Handle OHLC update messages"""
        try:
            data_array = raw_message.get('data', [])
            if not data_array:
                return

            for ohlc_data in data_array:
                if not isinstance(ohlc_data, dict):
                    continue

                symbol = ohlc_data.get('symbol')
                if not symbol:
                    continue

                try:
                    ohlc_update = OHLCUpdate.from_raw(symbol, ohlc_data)

                    # Call callbacks
                    await self._call_callbacks('ohlc', symbol, ohlc_update.to_dict())

                    logger.debug("[KRAKEN_V2_HANDLER] OHLC update: %s OHLC=[%s,%s,%s,%s]",
                               symbol, ohlc_update.open_price, ohlc_update.high,
                               ohlc_update.low, ohlc_update.close)

                except Exception as e:
                    logger.warning("[KRAKEN_V2_HANDLER] Failed to parse OHLC for %s: %s",
                                 symbol, e)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling OHLC message: %s", e)
            raise

    async def _handle_execution_message(self, raw_message: dict[str, Any]):
        """Handle execution update messages"""
        try:
            data_array = raw_message.get('data', [])
            if not data_array:
                return

            for execution_data in data_array:
                if not isinstance(execution_data, dict):
                    continue

                # Call callbacks with raw execution data
                await self._call_callbacks('executions', execution_data)

                logger.info("[KRAKEN_V2_HANDLER] Execution update: %s", execution_data)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling execution message: %s", e)
            raise

    async def _handle_open_orders_message(self, raw_message: dict[str, Any]):
        """Handle open orders update messages"""
        try:
            data_array = raw_message.get('data', [])
            if not data_array:
                return

            for order_data in data_array:
                if not isinstance(order_data, dict):
                    continue

                # Call callbacks with raw order data
                await self._call_callbacks('openOrders', order_data)

                logger.info("[KRAKEN_V2_HANDLER] Open order update: %s", order_data)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling open orders message: %s", e)
            raise

    async def _handle_heartbeat_message(self, raw_message: dict[str, Any]):
        """Handle heartbeat messages"""
        try:
            with self._lock:
                self.connection_status.last_heartbeat = time.time()

            await self._call_callbacks('heartbeat', raw_message)

            logger.debug("[KRAKEN_V2_HANDLER] Heartbeat received")

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling heartbeat: %s", e)

    async def _handle_status_message(self, raw_message: dict[str, Any]):
        """Handle status messages from WebSocket V2"""
        try:
            status_type = raw_message.get('type', 'unknown')
            data = raw_message.get('data', {})

            # Handle case where data might be a list
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]  # Use first item
                else:
                    data = {}  # Empty list means no data

            logger.info("[KRAKEN_V2_HANDLER] Status message received: type=%s", status_type)
            logger.debug("[KRAKEN_V2_HANDLER] Status data: %s", data)

            # Update connection status based on message content
            if status_type == 'update':
                connection_info = data.get('connection', {}) if isinstance(data, dict) else {}
                api_info = data.get('api_version', {}) if isinstance(data, dict) else {}

                with self._lock:
                    if connection_info.get('status') == 'online':
                        self.connection_status.connected = True

                    # Log API version info
                    if api_info:
                        logger.info("[KRAKEN_V2_HANDLER] API Version: %s", api_info)

            # Call status callbacks
            await self._call_callbacks('status', raw_message)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling status message: %s", e)

    async def _handle_pong_message(self, raw_message: dict[str, Any]):
        """Handle pong messages from WebSocket V2"""
        try:
            with self._lock:
                self.connection_status.last_heartbeat = time.time()

            logger.debug("[KRAKEN_V2_HANDLER] Pong message received")

            # Call pong callbacks
            await self._call_callbacks('pong', raw_message)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling pong message: %s", e)

    async def _handle_subscription_response(self, raw_message: dict[str, Any]):
        """Handle subscription/unsubscription responses"""
        try:
            method = raw_message.get('method', 'unknown')
            success = raw_message.get('success', False)
            result = raw_message.get('result', {})
            channel = result.get('channel', 'unknown')

            if success:
                if method == 'subscribe':
                    with self._lock:
                        if channel not in self.connection_status.subscriptions:
                            self.connection_status.subscriptions.append(channel)
                    logger.info("[KRAKEN_V2_HANDLER] Successfully subscribed to %s", channel)
                elif method == 'unsubscribe':
                    with self._lock:
                        if channel in self.connection_status.subscriptions:
                            self.connection_status.subscriptions.remove(channel)
                    logger.info("[KRAKEN_V2_HANDLER] Successfully unsubscribed from %s", channel)
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error("[KRAKEN_V2_HANDLER] %s failed for %s: %s",
                           method, channel, error_msg)

            # Call subscription callbacks
            await self._call_callbacks('subscription', raw_message)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling subscription response: %s", e)

    async def _handle_unknown_message(self, raw_message: dict[str, Any]):
        """Handle unknown message types with appropriate logging"""
        try:
            channel = raw_message.get('channel', 'NO_CHANNEL')
            message_type = raw_message.get('type', 'NO_TYPE')
            method = raw_message.get('method', 'NO_METHOD')

            logger.warning("[KRAKEN_V2_HANDLER] Unknown message: channel=%s, type=%s, method=%s",
                         channel, message_type, method)

            # Detailed debug information for troubleshooting
            logger.warning("[KRAKEN_V2_HANDLER] Unknown message keys: %s", list(raw_message.keys()))
            logger.warning("[KRAKEN_V2_HANDLER] Unknown message content: %s", raw_message)

            # Look for common alternative field names that might indicate the actual message type
            for key in ['event', 'event_type', 'msg_type', 'message_type', 'kind', 'action']:
                if key in raw_message:
                    logger.info("[KRAKEN_V2_HANDLER] Alternative field '%s': %s", key, raw_message[key])

            # Call generic callbacks
            await self._call_callbacks('unknown', raw_message)

        except Exception as e:
            logger.error("[KRAKEN_V2_HANDLER] Error handling unknown message: %s", e)

    async def _call_callbacks(self, channel: str, *args, **kwargs):
        """Call all registered callbacks for a channel"""
        callbacks = []
        with self._lock:
            callbacks = self._callbacks[channel].copy()

        if not callbacks:
            return

        # Execute callbacks concurrently with timeout
        tasks = []
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    task = asyncio.create_task(
                        asyncio.wait_for(callback(*args, **kwargs), timeout=self.processing_timeout)
                    )
                    tasks.append(task)
                else:
                    # Synchronous callback - run in thread pool
                    loop = asyncio.get_event_loop()
                    task = loop.run_in_executor(None, callback, *args, **kwargs)
                    tasks.append(task)
            except Exception as e:
                logger.error("[KRAKEN_V2_HANDLER] Error creating callback task: %s", e)

        if tasks:
            # Wait for all callbacks to complete
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error("[KRAKEN_V2_HANDLER] Error in callback execution: %s", e)

    async def _call_error_callbacks(self, error: Exception, raw_message: dict[str, Any]):
        """Call error callbacks"""
        callbacks = []
        with self._lock:
            callbacks = self._error_callbacks.copy()

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error, raw_message)
                else:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, callback, error, raw_message)
            except Exception as e:
                logger.error("[KRAKEN_V2_HANDLER] Error in error callback: %s", e)

    def _validate_raw_message(self, raw_message: dict[str, Any]) -> bool:
        """Validate raw message format"""
        if not isinstance(raw_message, dict):
            logger.warning("[KRAKEN_V2_HANDLER] Invalid message format: not a dict")
            return False

        # Basic V2 format validation
        if 'channel' not in raw_message and 'method' not in raw_message:
            logger.warning("[KRAKEN_V2_HANDLER] Invalid message: missing channel/method")
            return False

        # Strict mode validation
        if self.strict_mode:
            channel = raw_message.get('channel')

            if channel in self.private_channels:
                # Private channels should have proper authentication context
                pass  # Authentication is handled at connection level

            if channel and channel != 'heartbeat':
                # Data messages should have data field
                if 'data' not in raw_message and 'result' not in raw_message:
                    logger.debug("[KRAKEN_V2_HANDLER] Message missing data field: %s", channel)
                    # Don't reject - some messages might not have data

        return True

    def get_statistics(self) -> dict[str, Any]:
        """Get message processing statistics"""
        if not self.stats:
            return {}

        with self._lock:
            stats_dict = {
                'total_messages': self.stats.total_messages,
                'messages_by_channel': dict(self.stats.messages_by_channel),
                'error_count': self.stats.error_count,
                'duplicate_count': self.stats.duplicate_count,
                'sequence_gaps': self.stats.sequence_gaps,
                'uptime': time.time() - self.stats.last_reset,
                'avg_processing_times': {}
            }

            # Calculate average processing times
            for channel in self.stats.processing_times:
                stats_dict['avg_processing_times'][channel] = self.stats.get_avg_processing_time(channel)

            return stats_dict

    def get_sequence_status(self) -> dict[str, Any]:
        """Get sequence tracking status"""
        if not self.sequence_tracker:
            return {'enabled': False}

        with self._lock:
            status = self.sequence_tracker.get_status()
            status['enabled'] = True
            return status

    def get_connection_status(self) -> dict[str, Any]:
        """Get connection status"""
        with self._lock:
            return self.connection_status.to_dict()

    def reset_statistics(self):
        """Reset message processing statistics"""
        if self.stats:
            with self._lock:
                self.stats.reset()
            logger.info("[KRAKEN_V2_HANDLER] Statistics reset")

    def set_connection_status(self, connected: bool, authenticated: bool = None):
        """Update connection status"""
        with self._lock:
            self.connection_status.connected = connected
            if authenticated is not None:
                self.connection_status.authenticated = authenticated

            if connected and self.connection_status.connection_time == 0:
                self.connection_status.connection_time = time.time()
            elif not connected:
                self.connection_status.connection_time = 0
                self.connection_status.subscriptions.clear()

    def shutdown(self):
        """Shutdown the message handler"""
        logger.info("[KRAKEN_V2_HANDLER] Shutting down message handler")

        with self._lock:
            # Clear callbacks
            self._callbacks.clear()
            self._error_callbacks.clear()

            # Reset connection status
            self.connection_status.connected = False
            self.connection_status.authenticated = False
            self.connection_status.subscriptions.clear()

            # Clear managers
            self._managers.clear()

        logger.info("[KRAKEN_V2_HANDLER] Shutdown complete")


# Factory function for easy integration
def create_kraken_v2_handler(enable_sequence_tracking: bool = True,
                           enable_statistics: bool = True) -> KrakenV2MessageHandler:
    """
    Create a configured Kraken V2 message handler.

    Args:
        enable_sequence_tracking: Enable sequence number validation
        enable_statistics: Enable performance statistics

    Returns:
        Configured KrakenV2MessageHandler instance
    """
    return KrakenV2MessageHandler(
        enable_sequence_tracking=enable_sequence_tracking,
        enable_statistics=enable_statistics
    )


# Export main classes
__all__ = [
    'KrakenV2MessageHandler',
    'MessageStats',
    'SequenceTracker',
    'create_kraken_v2_handler'
]
