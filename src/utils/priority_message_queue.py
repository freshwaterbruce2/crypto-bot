"""
Priority Message Queue System for WebSocket Processing
=====================================================

High-performance message queue system with priority-based processing for WebSocket messages.
Ensures critical trading messages are processed first while maintaining order for similar priorities.

Features:
- Priority-based message processing (CRITICAL > HIGH > NORMAL > LOW)
- FIFO within same priority level
- Backpressure handling to prevent memory overflow
- Performance monitoring and metrics
- Configurable queue sizes and processing rates
- Dead letter queue for failed messages
- Batch processing capabilities
"""

import asyncio
import heapq
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MessagePriority(IntEnum):
    """Message priority levels (lower number = higher priority)"""
    CRITICAL = 0    # Balance updates, order executions
    HIGH = 1        # Price updates for active positions
    NORMAL = 2      # Regular market data
    LOW = 3         # Historical data, heartbeats


@dataclass
class QueuedMessage:
    """Message wrapper with priority and timing information"""
    priority: MessagePriority
    timestamp: float
    sequence: int
    message_type: str
    payload: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    processing_deadline: Optional[float] = None

    def __lt__(self, other):
        """Priority queue comparison - lower priority number processes first"""
        if self.priority != other.priority:
            return self.priority < other.priority
        # Within same priority, FIFO based on sequence number
        return self.sequence < other.sequence

    def is_expired(self) -> bool:
        """Check if message has exceeded processing deadline"""
        if self.processing_deadline is None:
            return False
        return time.time() > self.processing_deadline

    def can_retry(self) -> bool:
        """Check if message can be retried"""
        return self.retry_count < self.max_retries


@dataclass
class QueueStats:
    """Queue performance statistics"""
    messages_processed: int = 0
    messages_dropped: int = 0
    messages_retried: int = 0
    avg_processing_time: float = 0.0
    queue_sizes: Dict[MessagePriority, int] = field(default_factory=dict)
    backpressure_events: int = 0
    dead_letter_count: int = 0
    throughput_per_second: float = 0.0
    last_update: float = field(default_factory=time.time)


class PriorityMessageQueue:
    """High-performance priority message queue for WebSocket processing"""

    def __init__(self,
                 max_queue_size: int = 10000,
                 max_processing_rate: int = 1000,  # messages per second
                 enable_backpressure: bool = True,
                 enable_dead_letter: bool = True):
        """
        Initialize priority message queue
        
        Args:
            max_queue_size: Maximum total messages in queue
            max_processing_rate: Maximum messages processed per second
            enable_backpressure: Enable backpressure handling
            enable_dead_letter: Enable dead letter queue for failed messages
        """
        self.max_queue_size = max_queue_size
        self.max_processing_rate = max_processing_rate
        self.enable_backpressure = enable_backpressure
        self.enable_dead_letter = enable_dead_letter

        # Priority queues - one heap per priority level for better performance
        self.priority_queues: Dict[MessagePriority, List[QueuedMessage]] = {
            priority: [] for priority in MessagePriority
        }

        # Global sequence counter for FIFO within priority
        self._sequence_counter = 0
        self._sequence_lock = threading.Lock()

        # Processing control
        self._processing = False
        self._processor_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Message handlers
        self._handlers: Dict[str, Callable] = {}
        self._batch_handlers: Dict[str, Callable] = {}

        # Performance tracking
        self.stats = QueueStats()
        self._processing_times: deque = deque(maxlen=1000)
        self._last_stats_update = time.time()

        # Dead letter queue
        self.dead_letter_queue: deque = deque(maxlen=1000)

        # Locks for thread safety
        self._queue_lock = asyncio.Lock()
        self._handler_lock = asyncio.Lock()

        # Rate limiting
        self._rate_limiter = asyncio.Semaphore(max_processing_rate)
        self._rate_limit_window = deque(maxlen=max_processing_rate)

        logger.info(f"[PRIORITY_QUEUE] Initialized with max_size={max_queue_size}, max_rate={max_processing_rate}")

    async def start_processing(self):
        """Start message processing"""
        if self._processing:
            return

        self._processing = True
        self._stop_event.clear()
        self._processor_task = asyncio.create_task(self._processing_loop())

        logger.info("[PRIORITY_QUEUE] Message processing started")

    async def stop_processing(self):
        """Stop message processing gracefully"""
        if not self._processing:
            return

        self._processing = False
        self._stop_event.set()

        if self._processor_task:
            await self._processor_task

        logger.info("[PRIORITY_QUEUE] Message processing stopped")

    async def enqueue(self,
                     message_type: str,
                     payload: Dict[str, Any],
                     priority: MessagePriority = MessagePriority.NORMAL,
                     processing_deadline: Optional[float] = None) -> bool:
        """
        Enqueue a message for processing
        
        Args:
            message_type: Type of message (used for handler routing)
            payload: Message data
            priority: Message priority level
            processing_deadline: Optional deadline for processing
            
        Returns:
            bool: True if message was enqueued, False if dropped due to backpressure
        """
        async with self._queue_lock:
            # Check queue size limits
            total_size = sum(len(queue) for queue in self.priority_queues.values())

            if total_size >= self.max_queue_size:
                if self.enable_backpressure:
                    self.stats.backpressure_events += 1

                    # Try to drop low-priority messages to make room
                    if priority in [MessagePriority.CRITICAL, MessagePriority.HIGH]:
                        dropped = await self._drop_low_priority_messages(1)
                        if dropped == 0:
                            logger.warning(f"[PRIORITY_QUEUE] Queue full, dropping {priority.name} message")
                            self.stats.messages_dropped += 1
                            return False
                    else:
                        # Drop the current message if it's low priority
                        logger.debug(f"[PRIORITY_QUEUE] Queue full, dropping {priority.name} message")
                        self.stats.messages_dropped += 1
                        return False
                else:
                    logger.warning("[PRIORITY_QUEUE] Queue full, message dropped")
                    self.stats.messages_dropped += 1
                    return False

            # Create queued message
            with self._sequence_lock:
                sequence = self._sequence_counter
                self._sequence_counter += 1

            queued_message = QueuedMessage(
                priority=priority,
                timestamp=time.time(),
                sequence=sequence,
                message_type=message_type,
                payload=payload,
                processing_deadline=processing_deadline
            )

            # Add to appropriate priority queue
            heapq.heappush(self.priority_queues[priority], queued_message)

            logger.debug(f"[PRIORITY_QUEUE] Enqueued {priority.name} message: {message_type}")
            return True

    async def _drop_low_priority_messages(self, count: int) -> int:
        """Drop low-priority messages to make room"""
        dropped = 0

        # Drop from LOW priority first, then NORMAL
        for priority in [MessagePriority.LOW, MessagePriority.NORMAL]:
            queue = self.priority_queues[priority]
            while queue and dropped < count:
                heapq.heappop(queue)
                dropped += 1
                self.stats.messages_dropped += 1

        if dropped > 0:
            logger.info(f"[PRIORITY_QUEUE] Dropped {dropped} low-priority messages for backpressure")

        return dropped

    def register_handler(self, message_type: str, handler: Callable):
        """Register message handler for specific message type"""
        self._handlers[message_type] = handler
        logger.info(f"[PRIORITY_QUEUE] Registered handler for: {message_type}")

    def register_batch_handler(self, message_type: str, handler: Callable):
        """Register batch handler for processing multiple messages of same type"""
        self._batch_handlers[message_type] = handler
        logger.info(f"[PRIORITY_QUEUE] Registered batch handler for: {message_type}")

    async def _processing_loop(self):
        """Main message processing loop"""
        while self._processing and not self._stop_event.is_set():
            try:
                # Rate limiting check
                await self._enforce_rate_limit()

                # Get next message to process
                message = await self._get_next_message()

                if message is None:
                    # No messages available, sleep briefly
                    await asyncio.sleep(0.001)  # 1ms
                    continue

                # Check if message is expired
                if message.is_expired():
                    logger.warning(f"[PRIORITY_QUEUE] Message expired: {message.message_type}")
                    await self._handle_expired_message(message)
                    continue

                # Process message
                start_time = time.time()
                success = await self._process_message(message)
                processing_time = time.time() - start_time

                # Update statistics
                self._processing_times.append(processing_time)
                self.stats.messages_processed += 1

                if not success and message.can_retry():
                    # Retry failed message
                    message.retry_count += 1
                    await self._retry_message(message)
                elif not success:
                    # Move to dead letter queue
                    await self._handle_dead_letter(message)

                # Update throughput statistics
                await self._update_stats()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PRIORITY_QUEUE] Processing loop error: {e}")
                await asyncio.sleep(0.1)

    async def _get_next_message(self) -> Optional[QueuedMessage]:
        """Get next message to process based on priority"""
        async with self._queue_lock:
            # Check queues in priority order
            for priority in MessagePriority:
                queue = self.priority_queues[priority]
                if queue:
                    return heapq.heappop(queue)

            return None

    async def _process_message(self, message: QueuedMessage) -> bool:
        """Process a single message"""
        try:
            handler = self._handlers.get(message.message_type)

            if handler is None:
                logger.warning(f"[PRIORITY_QUEUE] No handler for message type: {message.message_type}")
                return False

            # Call handler
            if asyncio.iscoroutinefunction(handler):
                await handler(message.payload)
            else:
                handler(message.payload)

            return True

        except Exception as e:
            logger.error(f"[PRIORITY_QUEUE] Message processing error: {e}")
            logger.error(f"[PRIORITY_QUEUE] Message type: {message.message_type}")
            return False

    async def _retry_message(self, message: QueuedMessage):
        """Retry failed message"""
        async with self._queue_lock:
            # Add back to queue with same priority
            heapq.heappush(self.priority_queues[message.priority], message)
            self.stats.messages_retried += 1

            logger.debug(f"[PRIORITY_QUEUE] Retrying message: {message.message_type} (attempt {message.retry_count})")

    async def _handle_expired_message(self, message: QueuedMessage):
        """Handle expired message"""
        if self.enable_dead_letter:
            self.dead_letter_queue.append(message)
            self.stats.dead_letter_count += 1

        self.stats.messages_dropped += 1
        logger.warning(f"[PRIORITY_QUEUE] Message expired and moved to dead letter: {message.message_type}")

    async def _handle_dead_letter(self, message: QueuedMessage):
        """Handle message that failed all retries"""
        if self.enable_dead_letter:
            self.dead_letter_queue.append(message)
            self.stats.dead_letter_count += 1

        logger.error(f"[PRIORITY_QUEUE] Message moved to dead letter after {message.retry_count} retries: {message.message_type}")

    async def _enforce_rate_limit(self):
        """Enforce processing rate limit"""
        current_time = time.time()

        # Clean old timestamps from rate limit window
        while self._rate_limit_window and current_time - self._rate_limit_window[0] > 1.0:
            self._rate_limit_window.popleft()

        # Check if we're at rate limit
        if len(self._rate_limit_window) >= self.max_processing_rate:
            # Wait until we can process more
            sleep_time = 1.0 - (current_time - self._rate_limit_window[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        # Add current timestamp
        self._rate_limit_window.append(current_time)

    async def _update_stats(self):
        """Update performance statistics"""
        current_time = time.time()

        # Update every second
        if current_time - self._last_stats_update >= 1.0:
            # Calculate average processing time
            if self._processing_times:
                self.stats.avg_processing_time = sum(self._processing_times) / len(self._processing_times)

            # Calculate throughput
            window_size = current_time - self._last_stats_update
            messages_in_window = len([t for t in self._processing_times if current_time - t <= window_size])
            self.stats.throughput_per_second = messages_in_window / window_size if window_size > 0 else 0

            # Update queue sizes
            async with self._queue_lock:
                for priority in MessagePriority:
                    self.stats.queue_sizes[priority] = len(self.priority_queues[priority])

            self.stats.last_update = current_time
            self._last_stats_update = current_time

    def get_stats(self) -> QueueStats:
        """Get current queue statistics"""
        return self.stats

    async def get_queue_sizes(self) -> Dict[str, int]:
        """Get current queue sizes by priority"""
        async with self._queue_lock:
            return {
                priority.name: len(self.priority_queues[priority])
                for priority in MessagePriority
            }

    async def clear_dead_letter_queue(self) -> List[QueuedMessage]:
        """Clear and return dead letter queue contents"""
        messages = list(self.dead_letter_queue)
        self.dead_letter_queue.clear()
        self.stats.dead_letter_count = 0

        logger.info(f"[PRIORITY_QUEUE] Cleared {len(messages)} messages from dead letter queue")
        return messages

    async def flush_all_queues(self) -> int:
        """Flush all queues and return count of dropped messages"""
        async with self._queue_lock:
            total_dropped = 0

            for priority in MessagePriority:
                queue_size = len(self.priority_queues[priority])
                self.priority_queues[priority].clear()
                total_dropped += queue_size

            self.stats.messages_dropped += total_dropped
            logger.warning(f"[PRIORITY_QUEUE] Flushed all queues, dropped {total_dropped} messages")

            return total_dropped

    # Batch processing methods

    async def process_batch(self,
                           message_type: str,
                           batch_size: int = 100,
                           timeout: float = 1.0) -> int:
        """Process messages in batches for better throughput"""
        if message_type not in self._batch_handlers:
            logger.error(f"[PRIORITY_QUEUE] No batch handler for: {message_type}")
            return 0

        batch = []
        processed = 0
        start_time = time.time()

        while len(batch) < batch_size and time.time() - start_time < timeout:
            message = await self._get_next_message_by_type(message_type)
            if message is None:
                break

            if not message.is_expired():
                batch.append(message)
            else:
                await self._handle_expired_message(message)

        if batch:
            try:
                handler = self._batch_handlers[message_type]
                payloads = [msg.payload for msg in batch]

                if asyncio.iscoroutinefunction(handler):
                    await handler(payloads)
                else:
                    handler(payloads)

                processed = len(batch)
                self.stats.messages_processed += processed

                logger.debug(f"[PRIORITY_QUEUE] Batch processed {processed} {message_type} messages")

            except Exception as e:
                logger.error(f"[PRIORITY_QUEUE] Batch processing error: {e}")

                # Retry failed messages individually
                for message in batch:
                    if message.can_retry():
                        await self._retry_message(message)
                    else:
                        await self._handle_dead_letter(message)

        return processed

    async def _get_next_message_by_type(self, message_type: str) -> Optional[QueuedMessage]:
        """Get next message of specific type"""
        async with self._queue_lock:
            # Check all priority queues for matching message type
            for priority in MessagePriority:
                queue = self.priority_queues[priority]

                # Find message with matching type
                for i, message in enumerate(queue):
                    if message.message_type == message_type:
                        # Remove from heap (this is O(n) but necessary for type filtering)
                        queue.pop(i)
                        heapq.heapify(queue)  # Restore heap property
                        return message

            return None


# Global priority queue instance for WebSocket processing
_websocket_queue: Optional[PriorityMessageQueue] = None


async def get_websocket_queue() -> PriorityMessageQueue:
    """Get global WebSocket message queue"""
    global _websocket_queue
    if _websocket_queue is None:
        _websocket_queue = PriorityMessageQueue(
            max_queue_size=50000,  # Large queue for high-frequency trading
            max_processing_rate=2000,  # 2000 messages per second
            enable_backpressure=True,
            enable_dead_letter=True
        )
        await _websocket_queue.start_processing()

    return _websocket_queue


async def shutdown_websocket_queue():
    """Shutdown global WebSocket message queue"""
    global _websocket_queue
    if _websocket_queue:
        await _websocket_queue.stop_processing()
        _websocket_queue = None


# Decorator for automatic message queuing
def queue_message(message_type: str, priority: MessagePriority = MessagePriority.NORMAL):
    """Decorator to automatically queue function calls as messages"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            queue = await get_websocket_queue()

            # Convert function call to message payload
            payload = {
                'function': func.__name__,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            }

            # Enqueue the message
            await queue.enqueue(message_type, payload, priority)

        return wrapper
    return decorator
