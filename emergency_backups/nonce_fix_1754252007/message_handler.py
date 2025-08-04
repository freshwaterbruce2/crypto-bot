"""
WebSocket Message Handler
=========================

Processes and routes WebSocket messages with type safety and validation.
Handles message parsing, validation, and routing to appropriate callbacks.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque

from .data_models import (
    WebSocketMessage, MessageType, BalanceUpdate, TickerUpdate,
    OrderBookUpdate, TradeUpdate, OHLCUpdate, SubscriptionResponse
)

logger = logging.getLogger(__name__)


@dataclass
class MessageStats:
    """Message processing statistics"""
    total_messages: int = 0
    messages_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    processing_times: Dict[str, deque] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=100)))
    error_count: int = 0
    last_error: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    
    def add_message(self, message_type: str, processing_time: float):
        """Add message processing statistics"""
        self.total_messages += 1
        self.messages_by_type[message_type] += 1
        self.processing_times[message_type].append(processing_time)
    
    def add_error(self, error: str):
        """Add error statistics"""
        self.error_count += 1
        self.last_error = error
    
    def get_average_processing_time(self, message_type: str) -> float:
        """Get average processing time for message type"""
        times = self.processing_times.get(message_type, [])
        return sum(times) / len(times) if times else 0.0
    
    def get_message_rate(self, message_type: str = None) -> float:
        """Get messages per second"""
        elapsed = time.time() - self.start_time
        if elapsed <= 0:
            return 0.0
        
        if message_type:
            count = self.messages_by_type.get(message_type, 0)
        else:
            count = self.total_messages
        
        return count / elapsed


class MessageHandler:
    """
    High-performance message handler for WebSocket V2 messages
    """
    
    def __init__(self, max_queue_size: int = 10000):
        """Initialize message handler"""
        self.max_queue_size = max_queue_size
        self.message_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.stats = MessageStats()
        
        # Callback registry
        self.callbacks: Dict[MessageType, List[Callable]] = defaultdict(list)
        
        # Processing control
        self.running = False
        self.processor_task: Optional[asyncio.Task] = None
        
        # Message validation
        self.validate_messages = True
        self.drop_invalid_messages = True
        
        # Rate limiting
        self.rate_limiter: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.rate_limit_window = 60.0  # 1 minute window
        
        logger.info(f"[MESSAGE_HANDLER] Initialized with queue size: {max_queue_size}")
    
    def register_callback(self, message_type: MessageType, callback: Callable):
        """
        Register callback for specific message type
        
        Args:
            message_type: Type of message to handle
            callback: Async callback function
        """
        self.callbacks[message_type].append(callback)
        logger.info(f"[MESSAGE_HANDLER] Registered callback for {message_type.value}")
    
    def unregister_callback(self, message_type: MessageType, callback: Callable):
        """Remove callback for message type"""
        if callback in self.callbacks[message_type]:
            self.callbacks[message_type].remove(callback)
            logger.info(f"[MESSAGE_HANDLER] Unregistered callback for {message_type.value}")
    
    async def start_processing(self):
        """Start message processing loop"""
        if self.running:
            logger.warning("[MESSAGE_HANDLER] Already running")
            return
        
        self.running = True
        self.processor_task = asyncio.create_task(self._message_processor_loop())
        logger.info("[MESSAGE_HANDLER] Message processing started")
    
    async def stop_processing(self):
        """Stop message processing loop"""
        if not self.running:
            return
        
        self.running = False
        
        if self.processor_task and not self.processor_task.done():
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[MESSAGE_HANDLER] Message processing stopped")
    
    async def handle_raw_message(self, raw_message: Dict[str, Any]):
        """
        Handle raw WebSocket message
        
        Args:
            raw_message: Raw message dictionary from WebSocket
        """
        try:
            # Queue message for processing
            if self.message_queue.qsize() >= self.max_queue_size:
                logger.warning("[MESSAGE_HANDLER] Message queue full, dropping message")
                return
            
            await self.message_queue.put(raw_message)
            
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Error queuing message: {e}")
            self.stats.add_error(str(e))
    
    async def _message_processor_loop(self):
        """Main message processing loop"""
        logger.info("[MESSAGE_HANDLER] Starting message processor loop")
        
        while self.running:
            try:
                # Get message from queue with timeout
                raw_message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                
                # Process message with timing
                start_time = time.time()
                await self._process_message(raw_message)
                processing_time = time.time() - start_time
                
                # Update statistics
                message_type = raw_message.get('channel', 'unknown')
                self.stats.add_message(message_type, processing_time)
                
                # Rate limiting check
                self._check_rate_limits(message_type)
                
                # Mark task as done
                self.message_queue.task_done()
                
            except asyncio.TimeoutError:
                # No message received, continue loop
                continue
                
            except Exception as e:
                logger.error(f"[MESSAGE_HANDLER] Error processing message: {e}")
                self.stats.add_error(str(e))
                await asyncio.sleep(0.1)  # Brief pause on error
    
    async def _process_message(self, raw_message: Dict[str, Any]):
        """Process individual message"""
        try:
            # Create WebSocket message object
            ws_message = WebSocketMessage.from_raw(raw_message)
            
            # Validate message if enabled
            if self.validate_messages and not self._validate_message(ws_message):
                if self.drop_invalid_messages:
                    logger.debug(f"[MESSAGE_HANDLER] Dropping invalid message: {ws_message.channel}")
                    return
                else:
                    logger.warning(f"[MESSAGE_HANDLER] Processing invalid message: {ws_message.channel}")
            
            # Route message based on type
            await self._route_message(ws_message, raw_message)
            
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Error in message processing: {e}")
            self.stats.add_error(str(e))
    
    def _validate_message(self, message: WebSocketMessage) -> bool:
        """Validate WebSocket message structure"""
        try:
            # Basic validation
            if not message.channel:
                return False
            
            # Type-specific validation
            if message.type == MessageType.BALANCE:
                return self._validate_balance_message(message.data)
            elif message.type == MessageType.TICKER:
                return self._validate_ticker_message(message.data)
            elif message.type == MessageType.ORDERBOOK:
                return self._validate_orderbook_message(message.data)
            elif message.type == MessageType.TRADE:
                return self._validate_trade_message(message.data)
            elif message.type == MessageType.OHLC:
                return self._validate_ohlc_message(message.data)
            
            return True
            
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Validation error: {e}")
            return False
    
    def _validate_balance_message(self, data: Dict[str, Any]) -> bool:
        """Validate balance message data"""
        if isinstance(data, list):
            # V2 format: array of balance objects
            for item in data:
                if not isinstance(item, dict):
                    return False
                if 'asset' not in item or 'balance' not in item:
                    return False
        elif isinstance(data, dict):
            # Legacy format validation
            pass
        else:
            return False
        
        return True
    
    def _validate_ticker_message(self, data: Dict[str, Any]) -> bool:
        """Validate ticker message data"""
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    return False
                if 'symbol' not in item:
                    return False
                # Check for required price fields
                required_fields = ['bid', 'ask', 'last']
                if not any(field in item for field in required_fields):
                    return False
        
        return True
    
    def _validate_orderbook_message(self, data: Dict[str, Any]) -> bool:
        """Validate orderbook message data"""
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    return False
                if 'symbol' not in item:
                    return False
        
        return True
    
    def _validate_trade_message(self, data: Dict[str, Any]) -> bool:
        """Validate trade message data"""
        return isinstance(data, (list, dict))
    
    def _validate_ohlc_message(self, data: Dict[str, Any]) -> bool:
        """Validate OHLC message data"""
        return isinstance(data, (list, dict))
    
    async def _route_message(self, ws_message: WebSocketMessage, raw_data: Dict[str, Any]):
        """Route message to appropriate handlers"""
        try:
            if ws_message.type == MessageType.BALANCE:
                await self._handle_balance_message(ws_message, raw_data)
            elif ws_message.type == MessageType.TICKER:
                await self._handle_ticker_message(ws_message, raw_data)
            elif ws_message.type == MessageType.ORDERBOOK:
                await self._handle_orderbook_message(ws_message, raw_data)
            elif ws_message.type == MessageType.TRADE:
                await self._handle_trade_message(ws_message, raw_data)
            elif ws_message.type == MessageType.OHLC:
                await self._handle_ohlc_message(ws_message, raw_data)
            elif ws_message.type == MessageType.HEARTBEAT:
                await self._handle_heartbeat_message(ws_message, raw_data)
            elif ws_message.type == MessageType.SUBSCRIBE:
                await self._handle_subscription_response(ws_message, raw_data)
            else:
                logger.debug(f"[MESSAGE_HANDLER] Unhandled message type: {ws_message.type}")
                
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Error routing message: {e}")
            self.stats.add_error(str(e))
    
    async def _handle_balance_message(self, ws_message: WebSocketMessage, raw_data: Dict[str, Any]):
        """Handle balance update messages"""
        try:
            # Extract balance data from raw message
            balance_data = raw_data.get('data', [])
            
            if not balance_data:
                logger.debug("[MESSAGE_HANDLER] Empty balance data received")
                return
            
            # Parse balance updates
            balance_updates = []
            
            if isinstance(balance_data, list):
                for item in balance_data:
                    if isinstance(item, dict) and 'asset' in item:
                        balance_update = BalanceUpdate.from_raw(item)
                        balance_updates.append(balance_update)
            
            if balance_updates:
                logger.debug(f"[MESSAGE_HANDLER] Processing {len(balance_updates)} balance updates")
                
                # Call registered callbacks
                callbacks = self.callbacks.get(MessageType.BALANCE, [])
                for callback in callbacks:
                    try:
                        await callback(balance_updates)
                    except Exception as e:
                        logger.error(f"[MESSAGE_HANDLER] Balance callback error: {e}")
                        
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Error handling balance message: {e}")
    
    async def _handle_ticker_message(self, ws_message: WebSocketMessage, raw_data: Dict[str, Any]):
        """Handle ticker update messages"""
        try:
            ticker_data = raw_data.get('data', [])
            
            if not ticker_data:
                return
            
            # Parse ticker updates
            ticker_updates = []
            
            if isinstance(ticker_data, list):
                for item in ticker_data:
                    if isinstance(item, dict) and 'symbol' in item:
                        symbol = item['symbol']
                        ticker_update = TickerUpdate.from_raw(symbol, item)
                        ticker_updates.append(ticker_update)
            
            if ticker_updates:
                logger.debug(f"[MESSAGE_HANDLER] Processing {len(ticker_updates)} ticker updates")
                
                # Call registered callbacks
                callbacks = self.callbacks.get(MessageType.TICKER, [])
                for callback in callbacks:
                    try:
                        await callback(ticker_updates)
                    except Exception as e:
                        logger.error(f"[MESSAGE_HANDLER] Ticker callback error: {e}")
                        
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Error handling ticker message: {e}")
    
    async def _handle_orderbook_message(self, ws_message: WebSocketMessage, raw_data: Dict[str, Any]):
        """Handle orderbook update messages"""
        try:
            orderbook_data = raw_data.get('data', [])
            
            if not orderbook_data:
                return
            
            # Parse orderbook updates
            orderbook_updates = []
            
            if isinstance(orderbook_data, list):
                for item in orderbook_data:
                    if isinstance(item, dict) and 'symbol' in item:
                        symbol = item['symbol']
                        orderbook_update = OrderBookUpdate.from_raw(symbol, item)
                        orderbook_updates.append(orderbook_update)
            
            if orderbook_updates:
                logger.debug(f"[MESSAGE_HANDLER] Processing {len(orderbook_updates)} orderbook updates")
                
                # Call registered callbacks
                callbacks = self.callbacks.get(MessageType.ORDERBOOK, [])
                for callback in callbacks:
                    try:
                        await callback(orderbook_updates)
                    except Exception as e:
                        logger.error(f"[MESSAGE_HANDLER] Orderbook callback error: {e}")
                        
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Error handling orderbook message: {e}")
    
    async def _handle_trade_message(self, ws_message: WebSocketMessage, raw_data: Dict[str, Any]):
        """Handle trade update messages"""
        try:
            trade_data = raw_data.get('data', [])
            
            if not trade_data:
                return
            
            # Parse trade updates
            trade_updates = []
            
            if isinstance(trade_data, list):
                for item in trade_data:
                    if isinstance(item, dict) and 'symbol' in item:
                        symbol = item['symbol']
                        trade_update = TradeUpdate.from_raw(symbol, item)
                        trade_updates.append(trade_update)
            
            if trade_updates:
                logger.debug(f"[MESSAGE_HANDLER] Processing {len(trade_updates)} trade updates")
                
                # Call registered callbacks
                callbacks = self.callbacks.get(MessageType.TRADE, [])
                for callback in callbacks:
                    try:
                        await callback(trade_updates)
                    except Exception as e:
                        logger.error(f"[MESSAGE_HANDLER] Trade callback error: {e}")
                        
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Error handling trade message: {e}")
    
    async def _handle_ohlc_message(self, ws_message: WebSocketMessage, raw_data: Dict[str, Any]):
        """Handle OHLC update messages"""
        try:
            ohlc_data = raw_data.get('data', [])
            
            if not ohlc_data:
                return
            
            # Parse OHLC updates
            ohlc_updates = []
            
            if isinstance(ohlc_data, list):
                for item in ohlc_data:
                    if isinstance(item, dict) and 'symbol' in item:
                        symbol = item['symbol']
                        ohlc_update = OHLCUpdate.from_raw(symbol, item)
                        ohlc_updates.append(ohlc_update)
            
            if ohlc_updates:
                logger.debug(f"[MESSAGE_HANDLER] Processing {len(ohlc_updates)} OHLC updates")
                
                # Call registered callbacks
                callbacks = self.callbacks.get(MessageType.OHLC, [])
                for callback in callbacks:
                    try:
                        await callback(ohlc_updates)
                    except Exception as e:
                        logger.error(f"[MESSAGE_HANDLER] OHLC callback error: {e}")
                        
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Error handling OHLC message: {e}")
    
    async def _handle_heartbeat_message(self, ws_message: WebSocketMessage, raw_data: Dict[str, Any]):
        """Handle heartbeat messages"""
        logger.debug("[MESSAGE_HANDLER] Heartbeat received")
        
        # Call registered callbacks
        callbacks = self.callbacks.get(MessageType.HEARTBEAT, [])
        for callback in callbacks:
            try:
                await callback(raw_data)
            except Exception as e:
                logger.error(f"[MESSAGE_HANDLER] Heartbeat callback error: {e}")
    
    async def _handle_subscription_response(self, ws_message: WebSocketMessage, raw_data: Dict[str, Any]):
        """Handle subscription response messages"""
        try:
            response = SubscriptionResponse.from_raw(raw_data)
            
            if response.success:
                logger.info(f"[MESSAGE_HANDLER] Subscription successful: {response.result.get('channel', 'unknown')}")
            else:
                logger.error(f"[MESSAGE_HANDLER] Subscription failed: {response.error}")
            
            # Call registered callbacks
            callbacks = self.callbacks.get(MessageType.SUBSCRIBE, [])
            for callback in callbacks:
                try:
                    await callback(response)
                except Exception as e:
                    logger.error(f"[MESSAGE_HANDLER] Subscription callback error: {e}")
                    
        except Exception as e:
            logger.error(f"[MESSAGE_HANDLER] Error handling subscription response: {e}")
    
    def _check_rate_limits(self, message_type: str):
        """Check and log rate limiting information"""
        current_time = time.time()
        
        # Add timestamp to rate limiter
        self.rate_limiter[message_type].append(current_time)
        
        # Clean old timestamps
        cutoff_time = current_time - self.rate_limit_window
        while (self.rate_limiter[message_type] and 
               self.rate_limiter[message_type][0] < cutoff_time):
            self.rate_limiter[message_type].popleft()
        
        # Log high rate warnings
        message_count = len(self.rate_limiter[message_type])
        if message_count > 1000:  # More than 1000 messages per minute
            logger.warning(f"[MESSAGE_HANDLER] High message rate for {message_type}: {message_count}/min")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get message processing statistics"""
        stats_dict = {
            'total_messages': self.stats.total_messages,
            'error_count': self.stats.error_count,
            'last_error': self.stats.last_error,
            'uptime': time.time() - self.stats.start_time,
            'queue_size': self.message_queue.qsize(),
            'queue_max_size': self.max_queue_size,
            'messages_by_type': dict(self.stats.messages_by_type),
            'processing_rates': {},
            'average_processing_times': {}
        }
        
        # Calculate rates and average processing times
        for msg_type in self.stats.messages_by_type:
            stats_dict['processing_rates'][msg_type] = self.stats.get_message_rate(msg_type)
            stats_dict['average_processing_times'][msg_type] = self.stats.get_average_processing_time(msg_type)
        
        # Overall processing rate
        stats_dict['overall_message_rate'] = self.stats.get_message_rate()
        
        return stats_dict
    
    def reset_statistics(self):
        """Reset message processing statistics"""
        self.stats = MessageStats()
        logger.info("[MESSAGE_HANDLER] Statistics reset")
    
    async def flush_queue(self) -> int:
        """Flush remaining messages in queue"""
        processed = 0
        
        while not self.message_queue.empty():
            try:
                raw_message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=0.1
                )
                await self._process_message(raw_message)
                self.message_queue.task_done()
                processed += 1
                
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"[MESSAGE_HANDLER] Error flushing queue: {e}")
                break
        
        if processed > 0:
            logger.info(f"[MESSAGE_HANDLER] Flushed {processed} messages from queue")
        
        return processed