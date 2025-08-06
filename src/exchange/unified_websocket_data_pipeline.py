"""
Unified WebSocket V2 Data Pipeline
=================================

High-performance data routing system that efficiently distributes all WebSocket V2 streams
to appropriate bot components with priority-based routing, message queuing, and real-time
data transformation. Designed for maximum throughput and minimal latency.

Features:
- Priority-based message routing with configurable queues
- Real-time data transformation and format conversion
- Component coordination with balance managers and trading engines
- Memory-efficient processing with configurable buffer limits
- Comprehensive error handling and circuit breaker integration
- Performance monitoring and metrics collection
- Message deduplication and validation
- Async processing with backpressure management
"""

import asyncio
import logging
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from threading import RLock
from typing import Any, Optional

from ..utils.decimal_precision_fix import safe_decimal, safe_float
from ..utils.performance_integration import PerformanceTracker

logger = logging.getLogger(__name__)


class MessagePriority(IntEnum):
    """Message priority levels (lower number = higher priority)"""
    CRITICAL = 0    # Balance updates, order executions
    HIGH = 1        # Price updates, order book changes
    MEDIUM = 2      # OHLC data, trade history
    LOW = 3         # Heartbeats, status updates


class DataChannel(Enum):
    """WebSocket V2 data channels"""
    BALANCE = "balances"
    EXECUTION = "executions"
    TICKER = "ticker"
    ORDERBOOK = "book"
    OHLC = "ohlc"
    TRADES = "trade"
    HEARTBEAT = "heartbeat"
    STATUS = "status"


@dataclass
class MessageQueueConfig:
    """Configuration for message queues"""
    max_size: int = 1000
    timeout_seconds: float = 1.0
    priority_multiplier: float = 2.0  # Higher priority queues get more processing cycles
    enable_deduplication: bool = True
    dedup_window_seconds: float = 0.1


@dataclass
class PerformanceConfig:
    """Performance monitoring configuration"""
    enable_metrics: bool = True
    metrics_interval_seconds: float = 30.0
    max_processing_time_ms: float = 5.0  # Alert if processing takes longer
    enable_latency_tracking: bool = True
    memory_usage_threshold_mb: float = 100.0


@dataclass
class PipelineMessage:
    """Internal message structure for pipeline processing"""
    channel: DataChannel
    priority: MessagePriority
    data: dict[str, Any]
    timestamp: float
    message_id: str
    source_symbol: Optional[str] = None
    processed: bool = False
    retry_count: int = 0
    processing_start_time: Optional[float] = field(default=None)


class ComponentRegistry:
    """Registry for pipeline components with weak references"""

    def __init__(self):
        self._components = {}
        self._callbacks = defaultdict(list)
        self._lock = RLock()

    def register_component(self, name: str, component: Any, channels: list[DataChannel]):
        """Register a component for specific channels"""
        with self._lock:
            self._components[name] = weakref.ref(component)
            for channel in channels:
                self._callbacks[channel].append((name, weakref.ref(component)))
            logger.info(f"[PIPELINE] Registered component '{name}' for channels: {[c.value for c in channels]}")

    def unregister_component(self, name: str):
        """Unregister a component"""
        with self._lock:
            if name in self._components:
                del self._components[name]
                # Remove from callbacks
                for channel, callbacks in self._callbacks.items():
                    self._callbacks[channel] = [(n, ref) for n, ref in callbacks if n != name]
                logger.info(f"[PIPELINE] Unregistered component '{name}'")

    def get_components_for_channel(self, channel: DataChannel) -> list[tuple[str, Any]]:
        """Get active components for a channel"""
        active_components = []
        with self._lock:
            for name, ref in self._callbacks[channel]:
                component = ref()
                if component is not None:
                    active_components.append((name, component))
                else:
                    # Clean up dead reference
                    self._callbacks[channel] = [(n, r) for n, r in self._callbacks[channel]
                                              if r() is not None]
        return active_components


class UnifiedWebSocketDataPipeline:
    """
    High-performance WebSocket V2 data pipeline with priority routing and real-time processing

    Routes all WebSocket streams to appropriate components with configurable priorities,
    message queuing, and comprehensive error handling.
    """

    def __init__(self,
                 websocket_manager,
                 queue_config: Optional[MessageQueueConfig] = None,
                 performance_config: Optional[PerformanceConfig] = None):
        """
        Initialize the unified data pipeline

        Args:
            websocket_manager: WebSocket V2 manager instance
            queue_config: Queue configuration
            performance_config: Performance monitoring configuration
        """
        self.websocket_manager = websocket_manager
        self.queue_config = queue_config or MessageQueueConfig()
        self.performance_config = performance_config or PerformanceConfig()

        # Message queues by priority
        self.message_queues = {
            priority: asyncio.Queue(maxsize=self.queue_config.max_size)
            for priority in MessagePriority
        }

        # Component registry
        self.registry = ComponentRegistry()

        # Processing state
        self._running = False
        self._processor_tasks = []
        self._stats_task = None

        # Message deduplication
        self._message_hashes = deque(maxlen=1000)
        self._dedup_window = {}

        # Performance tracking
        if self.performance_config.enable_metrics:
            self.performance_tracker = PerformanceTracker("websocket_pipeline")
        else:
            self.performance_tracker = None

        # Statistics
        self.stats = {
            'messages_processed': defaultdict(int),
            'messages_dropped': defaultdict(int),
            'processing_times': defaultdict(list),
            'errors': defaultdict(int),
            'queue_sizes': defaultdict(int),
            'component_calls': defaultdict(int),
            'last_stats_reset': time.time()
        }

        # Data transformation handlers
        self._transformers = {
            DataChannel.BALANCE: self._transform_balance_data,
            DataChannel.TICKER: self._transform_ticker_data,
            DataChannel.ORDERBOOK: self._transform_orderbook_data,
            DataChannel.EXECUTION: self._transform_execution_data,
            DataChannel.OHLC: self._transform_ohlc_data,
            DataChannel.TRADES: self._transform_trade_data,
            DataChannel.HEARTBEAT: self._transform_heartbeat_data
        }

        logger.info("[PIPELINE] Unified WebSocket V2 data pipeline initialized")

    def register_balance_manager(self, balance_manager, manager_name: str = "primary"):
        """Register balance manager for balance updates"""
        self.registry.register_component(
            f"balance_manager_{manager_name}",
            balance_manager,
            [DataChannel.BALANCE, DataChannel.EXECUTION]
        )

    def register_trading_engine(self, trading_engine, engine_name: str = "primary"):
        """Register trading engine for market data and executions"""
        self.registry.register_component(
            f"trading_engine_{engine_name}",
            trading_engine,
            [DataChannel.TICKER, DataChannel.ORDERBOOK, DataChannel.EXECUTION, DataChannel.TRADES]
        )

    def register_strategy_manager(self, strategy_manager, manager_name: str = "primary"):
        """Register strategy manager for market data"""
        self.registry.register_component(
            f"strategy_manager_{manager_name}",
            strategy_manager,
            [DataChannel.TICKER, DataChannel.OHLC, DataChannel.ORDERBOOK]
        )

    def register_risk_manager(self, risk_manager, manager_name: str = "primary"):
        """Register risk manager for all relevant data"""
        self.registry.register_component(
            f"risk_manager_{manager_name}",
            risk_manager,
            [DataChannel.BALANCE, DataChannel.EXECUTION, DataChannel.TICKER]
        )

    def register_custom_component(self, name: str, component: Any, channels: list[DataChannel]):
        """Register custom component for specific channels"""
        self.registry.register_component(name, component, channels)

    async def start(self):
        """Start the data pipeline"""
        if self._running:
            logger.warning("[PIPELINE] Already running")
            return

        logger.info("[PIPELINE] Starting unified data pipeline...")
        self._running = True

        # Start message processors for each priority level
        for priority in MessagePriority:
            processor_count = max(1, int(self.queue_config.priority_multiplier ** (3 - priority)))
            for i in range(processor_count):
                task = asyncio.create_task(
                    self._message_processor(priority, f"processor_{priority.name.lower()}_{i}")
                )
                self._processor_tasks.append(task)

        # Start statistics collection
        if self.performance_config.enable_metrics:
            self._stats_task = asyncio.create_task(self._stats_collector())

        # Register with WebSocket manager
        if hasattr(self.websocket_manager, 'set_callback'):
            self.websocket_manager.set_callback('ticker', self._handle_ticker_callback)
            self.websocket_manager.set_callback('balance', self._handle_balance_callback)
            self.websocket_manager.set_callback('orderbook', self._handle_orderbook_callback)
            self.websocket_manager.set_callback('ohlc', self._handle_ohlc_callback)
            self.websocket_manager.set_callback('trade', self._handle_trade_callback)

        logger.info(f"[PIPELINE] Started with {len(self._processor_tasks)} processors")

    async def stop(self):
        """Stop the data pipeline"""
        if not self._running:
            return

        logger.info("[PIPELINE] Stopping unified data pipeline...")
        self._running = False

        # Cancel all tasks
        for task in self._processor_tasks:
            task.cancel()

        if self._stats_task:
            self._stats_task.cancel()

        # Wait for tasks to complete
        if self._processor_tasks:
            await asyncio.gather(*self._processor_tasks, return_exceptions=True)

        if self._stats_task:
            try:
                await self._stats_task
            except asyncio.CancelledError:
                pass

        # Clear queues
        for queue in self.message_queues.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        logger.info("[PIPELINE] Stopped successfully")

    async def process_raw_message(self, message: dict[str, Any]) -> bool:
        """
        Process raw WebSocket message and route to appropriate components

        Args:
            message: Raw WebSocket message

        Returns:
            True if message was processed successfully
        """
        try:
            start_time = time.time()

            # Determine channel and priority
            channel = self._identify_channel(message)
            if not channel:
                self.stats['messages_dropped']['unknown_channel'] += 1
                return False

            priority = self._get_message_priority(channel)

            # Create pipeline message
            message_id = self._generate_message_id(message, channel)

            # Check for duplicates
            if self.queue_config.enable_deduplication and self._is_duplicate(message_id):
                self.stats['messages_dropped']['duplicate'] += 1
                return True  # Not an error, just a duplicate

            pipeline_message = PipelineMessage(
                channel=channel,
                priority=priority,
                data=message,
                timestamp=start_time,
                message_id=message_id,
                source_symbol=self._extract_symbol(message)
            )

            # Add to appropriate queue
            queue = self.message_queues[priority]
            try:
                queue.put_nowait(pipeline_message)
                self.stats['messages_processed'][channel.value] += 1

                # Track performance
                if self.performance_tracker:
                    self.performance_tracker.record_event(
                        'message_queued',
                        duration=time.time() - start_time,
                        metadata={'channel': channel.value, 'priority': priority.name}
                    )

                return True

            except asyncio.QueueFull:
                self.stats['messages_dropped']['queue_full'] += 1
                logger.warning(f"[PIPELINE] Queue full for priority {priority.name}, dropping message")
                return False

        except Exception as e:
            self.stats['errors']['process_raw_message'] += 1
            logger.error(f"[PIPELINE] Error processing raw message: {e}")
            return False

    async def route_balance_update(self, balance_data: dict[str, Any]) -> bool:
        """Route balance update to registered balance managers"""
        return await self._route_channel_data(DataChannel.BALANCE, balance_data)

    async def route_execution_update(self, execution_data: dict[str, Any]) -> bool:
        """Route execution update to registered components"""
        return await self._route_channel_data(DataChannel.EXECUTION, execution_data)

    async def route_ticker_update(self, ticker_data: dict[str, Any]) -> bool:
        """Route ticker update to registered components"""
        return await self._route_channel_data(DataChannel.TICKER, ticker_data)

    async def route_orderbook_update(self, orderbook_data: dict[str, Any]) -> bool:
        """Route orderbook update to registered components"""
        return await self._route_channel_data(DataChannel.ORDERBOOK, orderbook_data)

    async def _route_channel_data(self, channel: DataChannel, data: dict[str, Any]) -> bool:
        """Generic method to route data to channel components"""
        # Create synthetic message for direct routing
        message = {
            'channel': channel.value,
            'data': data if isinstance(data, list) else [data],
            'timestamp': time.time()
        }
        return await self.process_raw_message(message)

    async def _message_processor(self, priority: MessagePriority, processor_name: str):
        """Process messages from a specific priority queue"""
        queue = self.message_queues[priority]

        logger.info(f"[PIPELINE] Started {processor_name} for priority {priority.name}")

        while self._running:
            try:
                # Get message with timeout
                try:
                    message = await asyncio.wait_for(
                        queue.get(),
                        timeout=self.queue_config.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    continue

                # Process the message
                await self._process_message(message, processor_name)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats['errors'][f'processor_{priority.name}'] += 1
                logger.error(f"[PIPELINE] Error in {processor_name}: {e}")
                await asyncio.sleep(0.1)  # Brief pause to prevent tight error loops

        logger.info(f"[PIPELINE] Stopped {processor_name}")

    async def _process_message(self, message: PipelineMessage, processor_name: str):
        """Process a single pipeline message"""
        try:
            message.processing_start_time = time.time()

            # Transform the data
            transformed_data = await self._transform_message_data(message)
            if not transformed_data:
                self.stats['messages_dropped']['transform_failed'] += 1
                return

            # Get components for this channel
            components = self.registry.get_components_for_channel(message.channel)
            if not components:
                self.stats['messages_dropped']['no_components'] += 1
                return

            # Route to all registered components
            for component_name, component in components:
                try:
                    await self._route_to_component(
                        component_name, component, message.channel, transformed_data
                    )
                    self.stats['component_calls'][component_name] += 1

                except Exception as e:
                    self.stats['errors'][f'component_{component_name}'] += 1
                    logger.error(f"[PIPELINE] Error routing to {component_name}: {e}")

            # Track processing time
            processing_time = time.time() - message.processing_start_time
            self.stats['processing_times'][message.channel.value].append(processing_time)

            # Alert on slow processing
            if processing_time > (self.performance_config.max_processing_time_ms / 1000):
                logger.warning(
                    f"[PIPELINE] Slow processing: {message.channel.value} took {processing_time*1000:.2f}ms"
                )

            message.processed = True

        except Exception as e:
            self.stats['errors']['process_message'] += 1
            logger.error(f"[PIPELINE] Error processing message: {e}")

    async def _transform_message_data(self, message: PipelineMessage) -> Optional[dict[str, Any]]:
        """Transform raw message data using channel-specific transformers"""
        try:
            transformer = self._transformers.get(message.channel)
            if transformer:
                return await transformer(message.data)
            else:
                # Return data as-is if no transformer
                return message.data
        except Exception as e:
            logger.error(f"[PIPELINE] Error transforming {message.channel.value} data: {e}")
            return None

    async def _route_to_component(self, component_name: str, component: Any,
                                 channel: DataChannel, data: dict[str, Any]):
        """Route transformed data to a specific component"""
        try:
            # Balance managers
            if 'balance_manager' in component_name:
                if channel == DataChannel.BALANCE:
                    if hasattr(component, 'process_websocket_update'):
                        await component.process_websocket_update(data)
                    elif hasattr(component, '_handle_balance_message'):
                        await component._handle_balance_message(data.get('balances', []))

                elif channel == DataChannel.EXECUTION:
                    if hasattr(component, 'process_execution_update'):
                        await component.process_execution_update(data)

            # Trading engines
            elif 'trading_engine' in component_name:
                if channel == DataChannel.TICKER:
                    if hasattr(component, 'update_ticker'):
                        await component.update_ticker(data.get('symbol'), data)

                elif channel == DataChannel.ORDERBOOK:
                    if hasattr(component, 'update_orderbook'):
                        await component.update_orderbook(data.get('symbol'), data)

                elif channel == DataChannel.EXECUTION:
                    if hasattr(component, 'process_execution'):
                        await component.process_execution(data)

            # Strategy managers
            elif 'strategy_manager' in component_name:
                if channel == DataChannel.TICKER:
                    if hasattr(component, 'on_ticker_update'):
                        await component.on_ticker_update(data.get('symbol'), data)

                elif channel == DataChannel.OHLC:
                    if hasattr(component, 'on_ohlc_update'):
                        await component.on_ohlc_update(data.get('symbol'), data)

            # Risk managers
            elif 'risk_manager' in component_name:
                if hasattr(component, 'process_market_data'):
                    await component.process_market_data(channel.value, data)

            # Custom components - try generic callback methods
            else:
                callback_method = f"on_{channel.value}_update"
                if hasattr(component, callback_method):
                    await getattr(component, callback_method)(data)
                elif hasattr(component, 'process_websocket_data'):
                    await component.process_websocket_data(channel.value, data)

        except Exception as e:
            logger.error(f"[PIPELINE] Error routing to {component_name}: {e}")
            raise

    # Data transformation methods
    async def _transform_balance_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform balance data to standardized format"""
        try:
            # Handle WebSocket V2 balance format
            balances = {}
            balance_array = data.get('data', [])

            if isinstance(balance_array, list):
                for balance_item in balance_array:
                    if isinstance(balance_item, dict):
                        asset = balance_item.get('asset')
                        if asset:
                            free_balance = safe_float(safe_decimal(balance_item.get('balance', '0')))
                            used_balance = safe_float(safe_decimal(balance_item.get('hold_trade', '0')))

                            balances[asset] = {
                                'free': free_balance,
                                'used': used_balance,
                                'total': free_balance + used_balance,
                                'timestamp': time.time()
                            }

            return {
                'balances': balances,
                'source': 'websocket_v2',
                'timestamp': time.time()
            }

        except Exception as e:
            logger.error(f"[PIPELINE] Error transforming balance data: {e}")
            return {}

    async def _transform_ticker_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform ticker data to standardized format"""
        try:
            ticker_data = {}
            data_array = data.get('data', [])

            if isinstance(data_array, list):
                for ticker_item in data_array:
                    if isinstance(ticker_item, dict):
                        symbol = ticker_item.get('symbol')
                        if symbol:
                            ticker_data[symbol] = {
                                'symbol': symbol,
                                'bid': safe_float(safe_decimal(ticker_item.get('bid', '0'))),
                                'ask': safe_float(safe_decimal(ticker_item.get('ask', '0'))),
                                'last': safe_float(safe_decimal(ticker_item.get('last', '0'))),
                                'volume': safe_float(safe_decimal(ticker_item.get('volume', '0'))),
                                'high': safe_float(safe_decimal(ticker_item.get('high', '0'))),
                                'low': safe_float(safe_decimal(ticker_item.get('low', '0'))),
                                'vwap': safe_float(safe_decimal(ticker_item.get('vwap', '0'))),
                                'timestamp': time.time()
                            }

            return ticker_data

        except Exception as e:
            logger.error(f"[PIPELINE] Error transforming ticker data: {e}")
            return {}

    async def _transform_orderbook_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform orderbook data to standardized format"""
        try:
            orderbook_data = {}
            data_array = data.get('data', [])

            if isinstance(data_array, list):
                for book_item in data_array:
                    if isinstance(book_item, dict):
                        symbol = book_item.get('symbol')
                        if symbol:
                            bids = []
                            asks = []

                            # Process bids
                            for bid in book_item.get('bids', [])[:10]:
                                if isinstance(bid, dict):
                                    price = safe_float(safe_decimal(bid.get('price', '0')))
                                    volume = safe_float(safe_decimal(bid.get('qty', '0')))
                                    if price > 0 and volume > 0:
                                        bids.append({'price': price, 'volume': volume})

                            # Process asks
                            for ask in book_item.get('asks', [])[:10]:
                                if isinstance(ask, dict):
                                    price = safe_float(safe_decimal(ask.get('price', '0')))
                                    volume = safe_float(safe_decimal(ask.get('qty', '0')))
                                    if price > 0 and volume > 0:
                                        asks.append({'price': price, 'volume': volume})

                            # Calculate spread and mid price
                            spread = 0.0
                            mid_price = 0.0
                            if bids and asks:
                                best_bid = safe_decimal(bids[0]['price'])
                                best_ask = safe_decimal(asks[0]['price'])
                                spread = safe_float((best_ask - best_bid) / best_bid)
                                mid_price = safe_float((best_bid + best_ask) / safe_decimal('2'))

                            orderbook_data[symbol] = {
                                'symbol': symbol,
                                'bids': bids,
                                'asks': asks,
                                'spread': spread,
                                'mid_price': mid_price,
                                'timestamp': time.time()
                            }

            return orderbook_data

        except Exception as e:
            logger.error(f"[PIPELINE] Error transforming orderbook data: {e}")
            return {}

    async def _transform_execution_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform execution data to standardized format"""
        try:
            executions = []
            data_array = data.get('data', [])

            if isinstance(data_array, list):
                for exec_item in data_array:
                    if isinstance(exec_item, dict):
                        executions.append({
                            'order_id': exec_item.get('order_id'),
                            'symbol': exec_item.get('symbol'),
                            'side': exec_item.get('side'),
                            'quantity': safe_float(safe_decimal(exec_item.get('qty', '0'))),
                            'price': safe_float(safe_decimal(exec_item.get('price', '0'))),
                            'fee': safe_float(safe_decimal(exec_item.get('fee', '0'))),
                            'timestamp': time.time()
                        })

            return {'executions': executions}

        except Exception as e:
            logger.error(f"[PIPELINE] Error transforming execution data: {e}")
            return {}

    async def _transform_ohlc_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform OHLC data to standardized format"""
        try:
            ohlc_data = {}
            data_array = data.get('data', [])

            if isinstance(data_array, list):
                for ohlc_item in data_array:
                    if isinstance(ohlc_item, dict):
                        symbol = ohlc_item.get('symbol')
                        if symbol:
                            ohlc_data[symbol] = {
                                'symbol': symbol,
                                'open': safe_float(safe_decimal(ohlc_item.get('open', '0'))),
                                'high': safe_float(safe_decimal(ohlc_item.get('high', '0'))),
                                'low': safe_float(safe_decimal(ohlc_item.get('low', '0'))),
                                'close': safe_float(safe_decimal(ohlc_item.get('close', '0'))),
                                'volume': safe_float(safe_decimal(ohlc_item.get('volume', '0'))),
                                'timestamp': time.time()
                            }

            return ohlc_data

        except Exception as e:
            logger.error(f"[PIPELINE] Error transforming OHLC data: {e}")
            return {}

    async def _transform_trade_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform trade data to standardized format"""
        try:
            # Similar to ticker but for individual trades
            return await self._transform_ticker_data(data)
        except Exception as e:
            logger.error(f"[PIPELINE] Error transforming trade data: {e}")
            return {}

    async def _transform_heartbeat_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform heartbeat data to standardized format"""
        return {
            'type': 'heartbeat',
            'timestamp': time.time(),
            'status': 'alive'
        }

    # WebSocket callback handlers
    async def _handle_ticker_callback(self, symbol: str, ticker_data: dict[str, Any]):
        """Handle ticker callback from WebSocket manager"""
        message = {
            'channel': 'ticker',
            'data': [{'symbol': symbol, **ticker_data}]
        }
        await self.process_raw_message(message)

    async def _handle_balance_callback(self, balance_data: dict[str, Any]):
        """Handle balance callback from WebSocket manager"""
        # Convert to array format expected by transformer
        if isinstance(balance_data, dict):
            balance_array = []
            for asset, balance_info in balance_data.items():
                balance_array.append({
                    'asset': asset,
                    'balance': str(balance_info.get('free', 0)),
                    'hold_trade': str(balance_info.get('used', 0))
                })
            message = {
                'channel': 'balances',
                'data': balance_array
            }
        else:
            message = {
                'channel': 'balances',
                'data': balance_data
            }
        await self.process_raw_message(message)

    async def _handle_orderbook_callback(self, symbol: str, orderbook_data: dict[str, Any]):
        """Handle orderbook callback from WebSocket manager"""
        message = {
            'channel': 'book',
            'data': [{'symbol': symbol, **orderbook_data}]
        }
        await self.process_raw_message(message)

    async def _handle_ohlc_callback(self, symbol: str, ohlc_data: dict[str, Any]):
        """Handle OHLC callback from WebSocket manager"""
        message = {
            'channel': 'ohlc',
            'data': [{'symbol': symbol, **ohlc_data}]
        }
        await self.process_raw_message(message)

    async def _handle_trade_callback(self, trade_data: dict[str, Any]):
        """Handle trade callback from WebSocket manager"""
        message = {
            'channel': 'trade',
            'data': [trade_data]
        }
        await self.process_raw_message(message)

    # Utility methods
    def _identify_channel(self, message: dict[str, Any]) -> Optional[DataChannel]:
        """Identify the channel from a raw WebSocket message"""
        channel_str = message.get('channel', '').lower()

        channel_mapping = {
            'balances': DataChannel.BALANCE,
            'executions': DataChannel.EXECUTION,
            'ticker': DataChannel.TICKER,
            'book': DataChannel.ORDERBOOK,
            'ohlc': DataChannel.OHLC,
            'trade': DataChannel.TRADES,
            'heartbeat': DataChannel.HEARTBEAT
        }

        return channel_mapping.get(channel_str)

    def _get_message_priority(self, channel: DataChannel) -> MessagePriority:
        """Get priority level for a channel"""
        priority_mapping = {
            DataChannel.BALANCE: MessagePriority.CRITICAL,
            DataChannel.EXECUTION: MessagePriority.CRITICAL,
            DataChannel.TICKER: MessagePriority.HIGH,
            DataChannel.ORDERBOOK: MessagePriority.HIGH,
            DataChannel.OHLC: MessagePriority.MEDIUM,
            DataChannel.TRADES: MessagePriority.MEDIUM,
            DataChannel.HEARTBEAT: MessagePriority.LOW,
            DataChannel.STATUS: MessagePriority.LOW
        }

        return priority_mapping.get(channel, MessagePriority.MEDIUM)

    def _generate_message_id(self, message: dict[str, Any], channel: DataChannel) -> str:
        """Generate unique message ID for deduplication"""
        # Create hash based on channel, timestamp, and key data
        key_data = f"{channel.value}_{message.get('timestamp', time.time())}"

        if channel == DataChannel.TICKER:
            data_array = message.get('data', [])
            if data_array:
                symbol = data_array[0].get('symbol', '')
                last_price = data_array[0].get('last', '')
                key_data += f"_{symbol}_{last_price}"

        return str(hash(key_data))

    def _is_duplicate(self, message_id: str) -> bool:
        """Check if message is a duplicate within the dedup window"""
        current_time = time.time()

        # Clean old entries
        cutoff_time = current_time - self.queue_config.dedup_window_seconds
        self._dedup_window = {
            msg_id: timestamp for msg_id, timestamp in self._dedup_window.items()
            if timestamp > cutoff_time
        }

        # Check for duplicate
        if message_id in self._dedup_window:
            return True

        # Record this message
        self._dedup_window[message_id] = current_time
        return False

    def _extract_symbol(self, message: dict[str, Any]) -> Optional[str]:
        """Extract symbol from message if available"""
        data_array = message.get('data', [])
        if isinstance(data_array, list) and data_array:
            return data_array[0].get('symbol')
        return None

    async def _stats_collector(self):
        """Collect and log performance statistics"""
        while self._running:
            try:
                await asyncio.sleep(self.performance_config.metrics_interval_seconds)

                if not self._running:
                    break

                # Calculate queue sizes
                for priority, queue in self.message_queues.items():
                    self.stats['queue_sizes'][priority.name] = queue.qsize()

                # Log statistics
                total_processed = sum(self.stats['messages_processed'].values())
                total_dropped = sum(self.stats['messages_dropped'].values())
                total_errors = sum(self.stats['errors'].values())

                logger.info(
                    f"[PIPELINE] Stats: {total_processed} processed, "
                    f"{total_dropped} dropped, {total_errors} errors"
                )

                # Log processing times
                for channel, times in self.stats['processing_times'].items():
                    if times:
                        avg_time = sum(times) / len(times)
                        max_time = max(times)
                        logger.debug(
                            f"[PIPELINE] {channel}: avg {avg_time*1000:.2f}ms, "
                            f"max {max_time*1000:.2f}ms"
                        )
                        # Clear old times
                        self.stats['processing_times'][channel] = times[-100:]

                # Reset some counters periodically
                if time.time() - self.stats['last_stats_reset'] > 3600:  # 1 hour
                    self.stats['messages_processed'].clear()
                    self.stats['messages_dropped'].clear()
                    self.stats['errors'].clear()
                    self.stats['last_stats_reset'] = time.time()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PIPELINE] Error in stats collector: {e}")

    def get_pipeline_stats(self) -> dict[str, Any]:
        """Get current pipeline statistics"""
        return {
            'running': self._running,
            'processor_count': len(self._processor_tasks),
            'queue_sizes': {
                priority.name: queue.qsize()
                for priority, queue in self.message_queues.items()
            },
            'messages_processed': dict(self.stats['messages_processed']),
            'messages_dropped': dict(self.stats['messages_dropped']),
            'errors': dict(self.stats['errors']),
            'component_calls': dict(self.stats['component_calls']),
            'registered_components': len(self.registry._components)
        }

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics"""
        if not self.performance_tracker:
            return {}

        return self.performance_tracker.get_metrics()
