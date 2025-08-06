"""
Request Queue Management System

Implements priority-based request queuing with advanced scheduling algorithms
for optimal rate limit compliance and trading performance. Supports different
priority levels, queue management strategies, and integration with circuit breakers.
"""

import asyncio
import heapq
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RequestPriority(IntEnum):
    """
    Request priority levels for queue management.
    Lower numbers = higher priority.
    """
    CRITICAL = 0      # Emergency orders, liquidations
    HIGH = 1          # Trade execution, order management
    NORMAL = 2        # Regular trading operations
    LOW = 3           # Data fetching, analysis
    BACKGROUND = 4    # Cleanup, maintenance operations


class QueueStrategy(Enum):
    """Queue processing strategies."""
    FIFO = "fifo"                    # First In, First Out
    PRIORITY_FIFO = "priority_fifo"  # Priority-based with FIFO within priority
    WEIGHTED_FAIR = "weighted_fair"  # Weighted fair queuing
    ADAPTIVE = "adaptive"            # Adaptive based on conditions


@dataclass
class QueuedRequest:
    """Represents a queued API request."""

    # Request identification
    request_id: str
    endpoint: str
    method: str
    priority: RequestPriority

    # Request data
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    callback: Optional[Callable] = None

    # Timing information
    created_at: float = field(default_factory=time.time)
    scheduled_at: Optional[float] = None
    expires_at: Optional[float] = None

    # Rate limiting
    penalty_points: int = 1
    weight: int = 1
    requires_auth: bool = True

    # Retry configuration
    max_retries: int = 3
    retry_count: int = 0
    backoff_multiplier: float = 2.0

    # Status
    is_cancelled: bool = False
    future: Optional[asyncio.Future] = None

    def __post_init__(self):
        """Initialize future if not provided."""
        if self.future is None:
            self.future = asyncio.Future()

    def __lt__(self, other):
        """Compare requests for priority queue ordering."""
        if not isinstance(other, QueuedRequest):
            return NotImplemented  # Correct for comparison operators

        # Primary sort: priority (lower is higher priority)
        if self.priority != other.priority:
            return self.priority < other.priority

        # Secondary sort: creation time (earlier is higher priority)
        return self.created_at < other.created_at

    @property
    def age_seconds(self) -> float:
        """Get age of request in seconds."""
        return time.time() - self.created_at

    @property
    def is_expired(self) -> bool:
        """Check if request has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def cancel(self, reason: str = "Cancelled"):
        """Cancel the request."""
        self.is_cancelled = True
        if self.future and not self.future.done():
            self.future.cancel()
        logger.debug(f"Request {self.request_id} cancelled: {reason}")


class RequestQueue:
    """
    Advanced request queue with priority management and rate limit compliance.

    Features:
    - Priority-based scheduling
    - Adaptive queue strategies
    - Circuit breaker integration
    - Request expiration handling
    - Comprehensive metrics
    """

    def __init__(
        self,
        max_size: int = 1000,
        strategy: QueueStrategy = QueueStrategy.PRIORITY_FIFO,
        cleanup_interval: float = 30.0,
        max_age_seconds: float = 300.0
    ):
        """
        Initialize request queue.

        Args:
            max_size: Maximum queue size
            strategy: Queue processing strategy
            cleanup_interval: Interval for cleanup operations
            max_age_seconds: Maximum age before request expires
        """
        self.max_size = max_size
        self.strategy = strategy
        self.cleanup_interval = cleanup_interval
        self.max_age_seconds = max_age_seconds

        # Priority queues for each priority level
        self._queues: dict[RequestPriority, list[QueuedRequest]] = {
            priority: [] for priority in RequestPriority
        }

        # Request tracking
        self._requests: dict[str, QueuedRequest] = {}
        self._processing: dict[str, QueuedRequest] = {}

        # Queue statistics
        self.stats = {
            'total_queued': 0,
            'total_processed': 0,
            'total_cancelled': 0,
            'total_expired': 0,
            'total_failed': 0,
            'current_size': 0,
            'average_wait_time': 0.0,
            'max_wait_time': 0.0,
            'priority_distribution': dict.fromkeys(RequestPriority, 0)
        }

        # Queue management
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._shutdown = False

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

        # Weighted fair queuing state
        self._wfq_credits: dict[RequestPriority, float] = {
            RequestPriority.CRITICAL: 10.0,
            RequestPriority.HIGH: 5.0,
            RequestPriority.NORMAL: 2.0,
            RequestPriority.LOW: 1.0,
            RequestPriority.BACKGROUND: 0.5
        }

        logger.info(f"Request queue initialized: max_size={max_size}, strategy={strategy.value}")

    async def start(self):
        """Start the queue management system."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Request queue cleanup task started")

    async def stop(self):
        """Stop the queue management system."""
        self._shutdown = True

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Cancel all pending requests
        async with self._lock:
            for request in list(self._requests.values()):
                request.cancel("Queue shutdown")

            self._requests.clear()
            for queue in self._queues.values():
                queue.clear()

        logger.info("Request queue stopped")

    async def enqueue(
        self,
        request_id: str,
        endpoint: str,
        method: str,
        priority: RequestPriority = RequestPriority.NORMAL,
        args: tuple = (),
        kwargs: dict = None,
        callback: Optional[Callable] = None,
        timeout_seconds: Optional[float] = None,
        penalty_points: int = 1,
        weight: int = 1,
        requires_auth: bool = True,
        max_retries: int = 3
    ) -> QueuedRequest:
        """
        Enqueue a request for processing.

        Args:
            request_id: Unique identifier for the request
            endpoint: API endpoint name
            method: HTTP method or operation
            priority: Request priority level
            args: Positional arguments for the request
            kwargs: Keyword arguments for the request
            callback: Optional callback function
            timeout_seconds: Request timeout
            penalty_points: Rate limit penalty points
            weight: Request weight for rate limiting
            requires_auth: Whether request requires authentication
            max_retries: Maximum retry attempts

        Returns:
            QueuedRequest object

        Raises:
            ValueError: If queue is full or request already exists
        """
        if kwargs is None:
            kwargs = {}

        async with self._lock:
            # Check if queue is full
            if self.stats['current_size'] >= self.max_size:
                raise ValueError(f"Queue is full (size: {self.stats['current_size']})")

            # Check for duplicate request ID
            if request_id in self._requests:
                raise ValueError(f"Request {request_id} already exists in queue")

            # Create request object
            expires_at = None
            if timeout_seconds:
                expires_at = time.time() + timeout_seconds

            request = QueuedRequest(
                request_id=request_id,
                endpoint=endpoint,
                method=method,
                priority=priority,
                args=args,
                kwargs=kwargs,
                callback=callback,
                expires_at=expires_at,
                penalty_points=penalty_points,
                weight=weight,
                requires_auth=requires_auth,
                max_retries=max_retries
            )

            # Add to appropriate queue
            heapq.heappush(self._queues[priority], request)
            self._requests[request_id] = request

            # Update statistics
            self.stats['total_queued'] += 1
            self.stats['current_size'] += 1
            self.stats['priority_distribution'][priority] += 1

            # Notify waiting consumers
            self._not_empty.notify()

            logger.debug(
                f"Request {request_id} queued: endpoint={endpoint}, "
                f"priority={priority.name}, queue_size={self.stats['current_size']}"
            )

            return request

    async def dequeue(self, timeout_seconds: Optional[float] = None) -> Optional[QueuedRequest]:
        """
        Dequeue the next request for processing.

        Args:
            timeout_seconds: Maximum time to wait for a request

        Returns:
            Next request to process, or None if timeout/shutdown
        """
        async with self._not_empty:
            # Wait for requests or timeout
            start_time = time.time()

            while self.stats['current_size'] == 0 and not self._shutdown:
                if timeout_seconds:
                    remaining = timeout_seconds - (time.time() - start_time)
                    if remaining <= 0:
                        return None

                    try:
                        await asyncio.wait_for(self._not_empty.wait(), timeout=remaining)
                    except asyncio.TimeoutError:
                        return None
                else:
                    await self._not_empty.wait()

            if self._shutdown:
                return None

            # Get next request based on strategy
            request = self._get_next_request()
            if request is None:
                return None

            # Move to processing state
            del self._requests[request.request_id]
            self._processing[request.request_id] = request
            request.scheduled_at = time.time()

            # Update statistics
            self.stats['current_size'] -= 1
            wait_time = request.scheduled_at - request.created_at
            self._update_wait_time_stats(wait_time)

            logger.debug(
                f"Request {request.request_id} dequeued: "
                f"wait_time={wait_time:.2f}s, queue_size={self.stats['current_size']}"
            )

            return request

    def _get_next_request(self) -> Optional[QueuedRequest]:
        """Get next request based on queue strategy."""
        if self.strategy == QueueStrategy.FIFO:
            return self._get_fifo_request()
        elif self.strategy == QueueStrategy.PRIORITY_FIFO:
            return self._get_priority_fifo_request()
        elif self.strategy == QueueStrategy.WEIGHTED_FAIR:
            return self._get_weighted_fair_request()
        elif self.strategy == QueueStrategy.ADAPTIVE:
            return self._get_adaptive_request()
        else:
            return self._get_priority_fifo_request()  # Default

    def _get_fifo_request(self) -> Optional[QueuedRequest]:
        """Get next request using FIFO strategy."""
        oldest_request = None
        oldest_time = float('inf')

        for priority in RequestPriority:
            queue = self._queues[priority]
            while queue:
                request = heapq.heappop(queue)
                if not request.is_cancelled and not request.is_expired:
                    if request.created_at < oldest_time:
                        if oldest_request:
                            heapq.heappush(self._queues[oldest_request.priority], oldest_request)
                        oldest_request = request
                        oldest_time = request.created_at
                    else:
                        heapq.heappush(self._queues[request.priority], request)
                        break

        return oldest_request

    def _get_priority_fifo_request(self) -> Optional[QueuedRequest]:
        """Get next request using priority-FIFO strategy."""
        for priority in RequestPriority:
            queue = self._queues[priority]
            while queue:
                request = heapq.heappop(queue)
                if not request.is_cancelled and not request.is_expired:
                    return request

        return None

    def _get_weighted_fair_request(self) -> Optional[QueuedRequest]:
        """Get next request using weighted fair queuing."""
        # Find priority with highest credits that has requests
        best_priority = None
        best_credits = -1

        for priority in RequestPriority:
            if self._queues[priority] and self._wfq_credits[priority] > best_credits:
                best_priority = priority
                best_credits = self._wfq_credits[priority]

        if best_priority is None:
            return None

        # Get request from best priority queue
        queue = self._queues[best_priority]
        while queue:
            request = heapq.heappop(queue)
            if not request.is_cancelled and not request.is_expired:
                # Deduct credits and refresh others
                self._wfq_credits[best_priority] -= 1.0
                for p in RequestPriority:
                    if p != best_priority:
                        self._wfq_credits[p] += 0.1  # Slow credit refresh

                return request

        return None

    def _get_adaptive_request(self) -> Optional[QueuedRequest]:
        """Get next request using adaptive strategy."""
        # Use weighted fair queuing but adapt credits based on queue sizes
        total_requests = sum(len(q) for q in self._queues.values())

        if total_requests == 0:
            return None

        # Adjust credits based on queue sizes
        for priority in RequestPriority:
            queue_size = len(self._queues[priority])
            if queue_size > 0:
                ratio = queue_size / total_requests
                base_credit = self._wfq_credits[priority]
                # Increase credits for fuller queues (up to 2x)
                self._wfq_credits[priority] = base_credit * (1.0 + ratio)

        return self._get_weighted_fair_request()

    def _update_wait_time_stats(self, wait_time: float):
        """Update wait time statistics."""
        if self.stats['total_processed'] == 0:
            self.stats['average_wait_time'] = wait_time
        else:
            # Running average
            n = self.stats['total_processed']
            self.stats['average_wait_time'] = (
                (self.stats['average_wait_time'] * n + wait_time) / (n + 1)
            )

        self.stats['max_wait_time'] = max(self.stats['max_wait_time'], wait_time)
        self.stats['total_processed'] += 1

    async def complete_request(self, request_id: str, success: bool = True):
        """
        Mark a request as completed.

        Args:
            request_id: ID of the completed request
            success: Whether the request was successful
        """
        async with self._lock:
            request = self._processing.pop(request_id, None)
            if request is None:
                logger.warning(f"Completed request {request_id} not found in processing")
                return

            if success:
                if request.callback:
                    try:
                        if asyncio.iscoroutinefunction(request.callback):
                            await request.callback()
                        else:
                            request.callback()
                    except Exception as e:
                        logger.error(f"Request callback error for {request_id}: {e}")
            else:
                self.stats['total_failed'] += 1

            logger.debug(f"Request {request_id} completed successfully: {success}")

    async def cancel_request(self, request_id: str, reason: str = "Cancelled") -> bool:
        """
        Cancel a queued or processing request.

        Args:
            request_id: ID of the request to cancel
            reason: Cancellation reason

        Returns:
            True if request was cancelled, False if not found
        """
        async with self._lock:
            # Check queued requests
            request = self._requests.get(request_id)
            if request:
                request.cancel(reason)
                del self._requests[request_id]
                self.stats['current_size'] -= 1
                self.stats['total_cancelled'] += 1
                return True

            # Check processing requests
            request = self._processing.get(request_id)
            if request:
                request.cancel(reason)
                # Note: Don't remove from processing as it may be in progress
                self.stats['total_cancelled'] += 1
                return True

        return False

    async def _cleanup_loop(self):
        """Background cleanup of expired and cancelled requests."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_requests()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    async def _cleanup_expired_requests(self):
        """Remove expired and cancelled requests from queues."""
        async with self._lock:
            removed_count = 0
            time.time()

            # Clean up queued requests
            for priority in RequestPriority:
                queue = self._queues[priority]
                valid_requests = []

                while queue:
                    request = heapq.heappop(queue)

                    if request.is_cancelled:
                        removed_count += 1
                        self.stats['total_cancelled'] += 1
                        continue

                    if request.is_expired:
                        request.cancel("Expired")
                        removed_count += 1
                        self.stats['total_expired'] += 1
                        continue

                    # Check max age
                    if request.age_seconds > self.max_age_seconds:
                        request.cancel("Max age exceeded")
                        removed_count += 1
                        self.stats['total_expired'] += 1
                        continue

                    valid_requests.append(request)

                # Rebuild heap with valid requests
                self._queues[priority] = valid_requests
                heapq.heapify(self._queues[priority])

            # Update request tracking
            valid_requests = {}
            for request_id, request in self._requests.items():
                if not request.is_cancelled and not request.is_expired:
                    valid_requests[request_id] = request

            removed_from_tracking = len(self._requests) - len(valid_requests)
            self._requests = valid_requests

            # Update statistics
            self.stats['current_size'] = len(self._requests)

            if removed_count > 0 or removed_from_tracking > 0:
                logger.debug(
                    f"Cleanup removed {removed_count} queued and "
                    f"{removed_from_tracking} tracked requests"
                )

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive queue statistics."""
        stats = self.stats.copy()

        # Add real-time queue sizes
        stats['queue_sizes'] = {
            priority.name: len(self._queues[priority])
            for priority in RequestPriority
        }

        stats['processing_count'] = len(self._processing)
        stats['wfq_credits'] = {
            priority.name: credits
            for priority, credits in self._wfq_credits.items()
        }

        return stats

    def get_queue_size(self, priority: Optional[RequestPriority] = None) -> int:
        """
        Get queue size for specific priority or total.

        Args:
            priority: Priority level to check, or None for total

        Returns:
            Queue size
        """
        if priority is None:
            return self.stats['current_size']
        return len(self._queues[priority])

    def is_full(self) -> bool:
        """Check if queue is at capacity."""
        return self.stats['current_size'] >= self.max_size

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.stats['current_size'] == 0

    @asynccontextmanager
    async def request_context(self, request: QueuedRequest):
        """
        Context manager for processing requests.

        Args:
            request: Request to process
        """
        try:
            yield request
            await self.complete_request(request.request_id, success=True)
        except Exception as e:
            logger.error(f"Request {request.request_id} failed: {e}")
            await self.complete_request(request.request_id, success=False)
            raise

    def __len__(self) -> int:
        """Get total queue size."""
        return self.stats['current_size']

    def __bool__(self) -> bool:
        """Check if queue has requests."""
        return not self.is_empty()
