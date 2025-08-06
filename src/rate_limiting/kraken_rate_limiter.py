"""
Kraken 2025 Rate Limiter

Advanced rate limiting system implementing Kraken's 2025 API specifications.
Features token bucket algorithms, sliding window rate limiting, penalty point
system, circuit breaker patterns, and comprehensive monitoring.

Key Features:
- Private endpoints: 15 requests per minute compliance
- Public endpoints: 20 requests per minute compliance
- Token bucket algorithm with refill rates
- Sliding window for accurate rate tracking
- Per-API-key rate limit tracking
- Automatic backoff on rate limit exceeded
- Integration with circuit breaker pattern
- Comprehensive monitoring and logging
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union

from .rate_limit_config import (
    AccountTier,
    EndpointType,
    calculate_age_penalty,
    calculate_backoff_delay,
    get_endpoint_config,
    get_tier_config,
)
from .request_queue import RequestPriority, RequestQueue

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting with precise timing.

    Implements the token bucket algorithm with configurable capacity,
    refill rate, and burst handling.
    """
    capacity: int                    # Maximum tokens
    refill_rate: float              # Tokens per second
    tokens: float = field(init=False)  # Current token count
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize token count to capacity."""
        self.tokens = float(self.capacity)

    def refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        if elapsed > 0:
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_available_tokens(self) -> int:
        """Get current available token count."""
        self.refill()
        return int(self.tokens)

    def time_until_available(self, tokens: int = 1) -> float:
        """
        Calculate time until specified tokens are available.

        Args:
            tokens: Tokens needed

        Returns:
            Time in seconds until tokens available
        """
        self.refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


@dataclass
class SlidingWindow:
    """
    Sliding window for accurate rate limit tracking.

    Maintains a time-based sliding window of requests to provide
    precise rate limiting over specific time periods.
    """
    window_size: float              # Window size in seconds
    max_requests: int               # Maximum requests in window
    requests: deque = field(default_factory=deque)  # Request timestamps

    def add_request(self, timestamp: Optional[float] = None):
        """
        Add a request to the sliding window.

        Args:
            timestamp: Request timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()

        self.requests.append(timestamp)
        self._cleanup_old_requests(timestamp)

    def can_make_request(self, timestamp: Optional[float] = None) -> bool:
        """
        Check if a request can be made without exceeding rate limit.

        Args:
            timestamp: Check timestamp (defaults to current time)

        Returns:
            True if request can be made
        """
        if timestamp is None:
            timestamp = time.time()

        self._cleanup_old_requests(timestamp)
        return len(self.requests) < self.max_requests

    def get_request_count(self, timestamp: Optional[float] = None) -> int:
        """
        Get current request count in the window.

        Args:
            timestamp: Reference timestamp (defaults to current time)

        Returns:
            Number of requests in window
        """
        if timestamp is None:
            timestamp = time.time()

        self._cleanup_old_requests(timestamp)
        return len(self.requests)

    def time_until_available(self, timestamp: Optional[float] = None) -> float:
        """
        Calculate time until next request can be made.

        Args:
            timestamp: Reference timestamp (defaults to current time)

        Returns:
            Time in seconds until next request available
        """
        if timestamp is None:
            timestamp = time.time()

        self._cleanup_old_requests(timestamp)

        if len(self.requests) < self.max_requests:
            return 0.0

        # Find oldest request that would need to expire
        oldest_request = self.requests[0]
        return (oldest_request + self.window_size) - timestamp

    def _cleanup_old_requests(self, current_time: float):
        """Remove requests outside the sliding window."""
        cutoff_time = current_time - self.window_size

        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()


@dataclass
class PenaltyTracker:
    """
    Tracks penalty points with decay over time.

    Implements Kraken's penalty point system with tier-based
    maximum limits and decay rates.
    """
    max_points: int                 # Maximum penalty points
    decay_rate: float               # Points per second decay
    points: float = 0.0             # Current penalty points
    last_update: float = field(default_factory=time.time)

    def add_penalty(self, points: int):
        """
        Add penalty points.

        Args:
            points: Penalty points to add
        """
        self.update_decay()
        self.points = min(self.max_points, self.points + points)
        logger.debug(f"Added {points} penalty points, total: {self.points:.1f}")

    def update_decay(self):
        """Apply decay to penalty points."""
        now = time.time()
        elapsed = now - self.last_update

        if elapsed > 0:
            decay_amount = elapsed * self.decay_rate
            self.points = max(0.0, self.points - decay_amount)
            self.last_update = now

    def get_current_points(self) -> float:
        """Get current penalty points after decay."""
        self.update_decay()
        return self.points

    def can_add_points(self, points: int) -> bool:
        """
        Check if penalty points can be added without exceeding limit.

        Args:
            points: Points to add

        Returns:
            True if points can be added
        """
        current = self.get_current_points()
        return (current + points) <= self.max_points

    def time_until_available(self, points: int) -> float:
        """
        Calculate time until points can be added.

        Args:
            points: Points needed

        Returns:
            Time in seconds until points available
        """
        current = self.get_current_points()
        excess = (current + points) - self.max_points

        if excess <= 0:
            return 0.0

        return excess / self.decay_rate


class CircuitBreaker:
    """
    Circuit breaker for rate limit protection.

    Implements the circuit breaker pattern to prevent cascade failures
    when rate limits are consistently exceeded.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 3
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Time before attempting recovery
            success_threshold: Successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0

        logger.info(f"Circuit breaker initialized: threshold={failure_threshold}, timeout={recovery_timeout}s")

    def can_proceed(self) -> bool:
        """
        Check if requests can proceed through circuit breaker.

        Returns:
            True if requests can proceed
        """
        current_time = time.time()

        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if current_time - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.success_count = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True

        return False

    def record_success(self):
        """Record a successful operation."""
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED after successful recovery")

    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"
            logger.warning("Circuit breaker returned to OPEN during recovery")

    def get_state(self) -> dict[str, Any]:
        """Get circuit breaker state information."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "time_since_last_failure": time.time() - self.last_failure_time,
            "can_proceed": self.can_proceed()
        }


class KrakenRateLimiter2025:
    """
    Advanced Kraken Rate Limiter for 2025 API Specifications.

    Comprehensive rate limiting system that enforces Kraken's 2025 API limits
    using token bucket algorithms, sliding windows, penalty point tracking,
    and circuit breaker patterns.

    Features:
    - Private endpoints: 15 requests per minute
    - Public endpoints: 20 requests per minute
    - Penalty point system with tier-based limits
    - Per-endpoint tracking and limits
    - Queue management with priority
    - Circuit breaker pattern integration
    - Automatic recovery and cooldown
    - Comprehensive monitoring and metrics
    """

    def __init__(
        self,
        account_tier: Union[AccountTier, str] = AccountTier.INTERMEDIATE,
        api_key: Optional[str] = None,
        enable_queue: bool = True,
        enable_circuit_breaker: bool = True,
        persistence_path: Optional[str] = None
    ):
        """
        Initialize Kraken rate limiter.

        Args:
            account_tier: Kraken account tier
            api_key: API key for tracking (optional)
            enable_queue: Enable request queuing
            enable_circuit_breaker: Enable circuit breaker protection
            persistence_path: Path to save/load state
        """
        # Configuration
        if isinstance(account_tier, str):
            account_tier = AccountTier(account_tier.lower())

        self.account_tier = account_tier
        self.api_key = api_key
        self.config = get_tier_config(account_tier)

        # Rate limiting components
        self._init_token_buckets()
        self._init_sliding_windows()
        self._init_penalty_trackers()

        # Circuit breaker
        self.circuit_breaker = None
        if enable_circuit_breaker:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=30.0
            )

        # Request queue
        self.request_queue = None
        if enable_queue:
            self.request_queue = RequestQueue(
                max_size=self.config.max_queue_size,
                cleanup_interval=30.0
            )

        # Order tracking for age-based penalties
        self.order_times: dict[str, float] = {}

        # Statistics and monitoring
        self.stats = {
            'requests_made': 0,
            'requests_blocked': 0,
            'requests_queued': 0,
            'penalty_points_added': 0,
            'circuit_breaker_trips': 0,
            'average_response_time': 0.0,
            'endpoint_stats': defaultdict(lambda: {
                'requests': 0,
                'blocks': 0,
                'penalties': 0,
                'average_time': 0.0
            })
        }

        # Persistence
        self.persistence_path = Path(persistence_path) if persistence_path else None

        # Background tasks
        self._background_tasks: list[asyncio.Task] = []
        self._shutdown = False

        logger.info(
            f"Kraken Rate Limiter 2025 initialized: "
            f"tier={account_tier.value}, "
            f"private_limit={self.config.private_limit}rpm, "
            f"public_limit={self.config.public_limit}rpm, "
            f"max_penalty={self.config.max_penalty_points}"
        )

    def _init_token_buckets(self):
        """Initialize token buckets for different endpoint types."""
        self.token_buckets = {
            EndpointType.PRIVATE: TokenBucket(
                capacity=self.config.private_limit,
                refill_rate=self.config.private_limit / 60.0  # per second
            ),
            EndpointType.PUBLIC: TokenBucket(
                capacity=self.config.public_limit,
                refill_rate=self.config.public_limit / 60.0  # per second
            ),
            EndpointType.WEBSOCKET: TokenBucket(
                capacity=60,  # Higher limit for WebSocket
                refill_rate=1.0  # 60 per minute
            )
        }

    def _init_sliding_windows(self):
        """Initialize sliding windows for accurate rate tracking."""
        self.sliding_windows = {
            EndpointType.PRIVATE: SlidingWindow(
                window_size=60.0,  # 1 minute window
                max_requests=self.config.private_limit
            ),
            EndpointType.PUBLIC: SlidingWindow(
                window_size=60.0,  # 1 minute window
                max_requests=self.config.public_limit
            ),
            EndpointType.WEBSOCKET: SlidingWindow(
                window_size=60.0,  # 1 minute window
                max_requests=60
            )
        }

    def _init_penalty_trackers(self):
        """Initialize penalty point trackers."""
        # Global penalty tracker
        self.penalty_tracker = PenaltyTracker(
            max_points=self.config.max_penalty_points,
            decay_rate=self.config.penalty_decay_rate
        )

        # Per-endpoint penalty tracking
        self.endpoint_penalties: dict[str, PenaltyTracker] = {}

    async def start(self):
        """Start the rate limiter and background tasks."""
        if self.request_queue:
            await self.request_queue.start()

        # Start background cleanup task
        cleanup_task = asyncio.create_task(self._background_cleanup())
        self._background_tasks.append(cleanup_task)

        # Load persistent state
        if self.persistence_path:
            await self._load_state()

        logger.info("Kraken Rate Limiter 2025 started")

    async def stop(self):
        """Stop the rate limiter and cleanup."""
        self._shutdown = True

        # Stop request queue
        if self.request_queue:
            await self.request_queue.stop()

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Save persistent state
        if self.persistence_path:
            await self._save_state()

        logger.info("Kraken Rate Limiter 2025 stopped")

    async def check_rate_limit(
        self,
        endpoint: str,
        weight: Optional[int] = None,
        order_age_seconds: Optional[float] = None,
        priority: RequestPriority = RequestPriority.NORMAL
    ) -> tuple[bool, str, float]:
        """
        Check if request can proceed within rate limits.

        Args:
            endpoint: API endpoint name
            weight: Request weight (defaults to endpoint config)
            order_age_seconds: Age of order for penalty calculation
            priority: Request priority for queuing

        Returns:
            Tuple of (can_proceed, reason, wait_time_seconds)
        """
        start_time = time.time()

        try:
            # Get endpoint configuration
            endpoint_config = get_endpoint_config(endpoint)
            if weight is None:
                weight = endpoint_config.weight

            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_proceed():
                self.stats['requests_blocked'] += 1
                return False, "Circuit breaker open", 30.0

            # Calculate penalty points
            penalty_points = endpoint_config.penalty_points
            if endpoint_config.has_age_penalty and order_age_seconds is not None:
                penalty_points += calculate_age_penalty(endpoint, order_age_seconds)

            # Check global penalty limit
            if not self.penalty_tracker.can_add_points(penalty_points):
                wait_time = self.penalty_tracker.time_until_available(penalty_points)
                self.stats['requests_blocked'] += 1
                return False, f"Penalty limit exceeded ({self.penalty_tracker.get_current_points():.1f}/{self.config.max_penalty_points})", wait_time

            # Check token bucket
            token_bucket = self.token_buckets[endpoint_config.endpoint_type]
            if not token_bucket.consume(weight):
                wait_time = token_bucket.time_until_available(weight)
                self.stats['requests_blocked'] += 1
                return False, f"Token bucket depleted ({token_bucket.get_available_tokens()}/{token_bucket.capacity})", wait_time

            # Check sliding window
            sliding_window = self.sliding_windows[endpoint_config.endpoint_type]
            if not sliding_window.can_make_request():
                wait_time = sliding_window.time_until_available()
                self.stats['requests_blocked'] += 1
                # Return tokens since we can't proceed
                token_bucket.tokens = min(token_bucket.capacity, token_bucket.tokens + weight)
                return False, f"Sliding window limit exceeded ({sliding_window.get_request_count()}/{sliding_window.max_requests})", wait_time

            # All checks passed - record the request
            sliding_window.add_request()
            self.penalty_tracker.add_penalty(penalty_points)

            # Update statistics
            self.stats['requests_made'] += 1
            self.stats['penalty_points_added'] += penalty_points
            self.stats['endpoint_stats'][endpoint]['requests'] += 1
            self.stats['endpoint_stats'][endpoint]['penalties'] += penalty_points

            processing_time = time.time() - start_time
            self._update_response_time_stats(endpoint, processing_time)

            logger.debug(
                f"Rate limit check passed: {endpoint} "
                f"(weight={weight}, penalty={penalty_points}, "
                f"tokens={token_bucket.get_available_tokens()}, "
                f"penalty_total={self.penalty_tracker.get_current_points():.1f})"
            )

            return True, "OK", 0.0

        except Exception as e:
            logger.error(f"Rate limit check error for {endpoint}: {e}")
            # Default to allowing request on error
            return True, "Error - defaulting to allow", 0.0

    async def wait_for_rate_limit(
        self,
        endpoint: str,
        weight: Optional[int] = None,
        order_age_seconds: Optional[float] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout_seconds: Optional[float] = None
    ) -> bool:
        """
        Wait until request can proceed within rate limits.

        Args:
            endpoint: API endpoint name
            weight: Request weight
            order_age_seconds: Age of order for penalty calculation
            priority: Request priority
            timeout_seconds: Maximum time to wait

        Returns:
            True if request can proceed, False if timeout/shutdown
        """
        start_time = time.time()
        attempt = 0

        while not self._shutdown:
            can_proceed, reason, wait_time = await self.check_rate_limit(
                endpoint, weight, order_age_seconds, priority
            )

            if can_proceed:
                return True

            # Check timeout
            if timeout_seconds:
                elapsed = time.time() - start_time
                if elapsed >= timeout_seconds:
                    logger.warning(f"Rate limit wait timeout for {endpoint} after {elapsed:.1f}s")
                    return False

            # Calculate backoff delay
            backoff_delay = calculate_backoff_delay(
                attempt,
                self.config.base_backoff_seconds,
                self.config.backoff_multiplier,
                min(wait_time, self.config.max_backoff_seconds)
            )

            logger.info(
                f"Rate limited {endpoint}: {reason} - "
                f"waiting {backoff_delay:.1f}s (attempt {attempt + 1})"
            )

            try:
                await asyncio.sleep(backoff_delay)
            except asyncio.CancelledError:
                return False

            attempt += 1

        return False

    async def execute_with_rate_limit(
        self,
        endpoint: str,
        func: Callable,
        *args,
        weight: Optional[int] = None,
        order_age_seconds: Optional[float] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with automatic rate limit handling.

        Args:
            endpoint: API endpoint name
            func: Function to execute
            *args: Function arguments
            weight: Request weight
            order_age_seconds: Age of order for penalty calculation
            priority: Request priority
            timeout_seconds: Maximum time to wait
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If function fails or rate limit timeout
        """
        # Wait for rate limit clearance
        if not await self.wait_for_rate_limit(
            endpoint, weight, order_age_seconds, priority, timeout_seconds
        ):
            raise Exception(f"Rate limit timeout for {endpoint}")

        # Execute function
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            if self.circuit_breaker:
                self.circuit_breaker.record_success()

            execution_time = time.time() - start_time
            self._update_response_time_stats(endpoint, execution_time)

            return result

        except Exception as e:
            # Record failure
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
                self.stats['circuit_breaker_trips'] += 1

            self.stats['endpoint_stats'][endpoint]['blocks'] += 1
            logger.error(f"Function execution failed for {endpoint}: {e}")
            raise

    def record_order_time(self, order_id: str, timestamp: Optional[float] = None):
        """
        Record order creation time for age-based penalty calculation.

        Args:
            order_id: Order identifier
            timestamp: Order creation time (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()

        self.order_times[order_id] = timestamp
        logger.debug(f"Recorded order time for {order_id}: {timestamp}")

    def get_order_age(self, order_id: str) -> Optional[float]:
        """
        Get order age in seconds.

        Args:
            order_id: Order identifier

        Returns:
            Order age in seconds, or None if not found
        """
        order_time = self.order_times.get(order_id)
        if order_time is None:
            return None

        return time.time() - order_time

    def remove_order_time(self, order_id: str):
        """
        Remove order time tracking.

        Args:
            order_id: Order identifier
        """
        self.order_times.pop(order_id, None)
        logger.debug(f"Removed order time tracking for {order_id}")

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive rate limiter status."""
        status = {
            'account_tier': self.account_tier.value,
            'api_key': self.api_key[:8] + "..." if self.api_key else None,
            'uptime_seconds': time.time() - getattr(self, '_start_time', time.time()),

            # Token bucket status
            'token_buckets': {
                endpoint_type.value: {
                    'available': bucket.get_available_tokens(),
                    'capacity': bucket.capacity,
                    'utilization': 1.0 - (bucket.get_available_tokens() / bucket.capacity)
                }
                for endpoint_type, bucket in self.token_buckets.items()
            },

            # Sliding window status
            'sliding_windows': {
                endpoint_type.value: {
                    'current_requests': window.get_request_count(),
                    'max_requests': window.max_requests,
                    'utilization': window.get_request_count() / window.max_requests
                }
                for endpoint_type, window in self.sliding_windows.items()
            },

            # Penalty tracker status
            'penalty_tracker': {
                'current_points': round(self.penalty_tracker.get_current_points(), 1),
                'max_points': self.penalty_tracker.max_points,
                'utilization': self.penalty_tracker.get_current_points() / self.penalty_tracker.max_points,
                'decay_rate': self.penalty_tracker.decay_rate
            },

            # Circuit breaker status
            'circuit_breaker': self.circuit_breaker.get_state() if self.circuit_breaker else None,

            # Queue status
            'request_queue': self.request_queue.get_stats() if self.request_queue else None,

            # Order tracking
            'tracked_orders': len(self.order_times),

            # Statistics
            'statistics': self.stats.copy()
        }

        return status

    def get_endpoint_stats(self, endpoint: Optional[str] = None) -> dict[str, Any]:
        """
        Get statistics for specific endpoint or all endpoints.

        Args:
            endpoint: Endpoint name (None for all)

        Returns:
            Endpoint statistics
        """
        if endpoint:
            return self.stats['endpoint_stats'].get(endpoint, {})
        return dict(self.stats['endpoint_stats'])

    def reset_stats(self):
        """Reset all statistics."""
        self.stats = {
            'requests_made': 0,
            'requests_blocked': 0,
            'requests_queued': 0,
            'penalty_points_added': 0,
            'circuit_breaker_trips': 0,
            'average_response_time': 0.0,
            'endpoint_stats': defaultdict(lambda: {
                'requests': 0,
                'blocks': 0,
                'penalties': 0,
                'average_time': 0.0
            })
        }
        logger.info("Rate limiter statistics reset")

    def _update_response_time_stats(self, endpoint: str, response_time: float):
        """Update response time statistics."""
        # Global average
        total_requests = self.stats['requests_made']
        if total_requests == 1:
            self.stats['average_response_time'] = response_time
        else:
            self.stats['average_response_time'] = (
                (self.stats['average_response_time'] * (total_requests - 1) + response_time) /
                total_requests
            )

        # Endpoint-specific average
        endpoint_stats = self.stats['endpoint_stats'][endpoint]
        endpoint_requests = endpoint_stats['requests']
        if endpoint_requests == 1:
            endpoint_stats['average_time'] = response_time
        else:
            endpoint_stats['average_time'] = (
                (endpoint_stats['average_time'] * (endpoint_requests - 1) + response_time) /
                endpoint_requests
            )

    async def _background_cleanup(self):
        """Background task for cleanup operations."""
        while not self._shutdown:
            try:
                await asyncio.sleep(60.0)  # Run every minute

                # Cleanup old order times
                current_time = time.time()
                cutoff_time = current_time - 3600  # Remove orders older than 1 hour

                old_orders = [
                    order_id for order_id, timestamp in self.order_times.items()
                    if timestamp < cutoff_time
                ]

                for order_id in old_orders:
                    del self.order_times[order_id]

                if old_orders:
                    logger.debug(f"Cleaned up {len(old_orders)} old order timestamps")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background cleanup error: {e}")

    async def _save_state(self):
        """Save rate limiter state to disk."""
        if not self.persistence_path:
            return

        try:
            state = {
                'account_tier': self.account_tier.value,
                'api_key': self.api_key,
                'timestamp': time.time(),
                'penalty_points': self.penalty_tracker.get_current_points(),
                'order_times': self.order_times.copy(),
                'statistics': self.stats.copy()
            }

            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.persistence_path, 'w') as f:
                json.dump(state, f, indent=2)

            logger.debug(f"Rate limiter state saved to {self.persistence_path}")

        except Exception as e:
            logger.error(f"Failed to save rate limiter state: {e}")

    async def _load_state(self):
        """Load rate limiter state from disk."""
        if not self.persistence_path or not self.persistence_path.exists():
            return

        try:
            with open(self.persistence_path) as f:
                state = json.load(f)

            # Restore order times (only recent ones)
            current_time = time.time()
            saved_time = state.get('timestamp', current_time)
            age_limit = 3600  # 1 hour

            if (current_time - saved_time) < age_limit:
                self.order_times = state.get('order_times', {})

                # Apply penalty decay since last save
                elapsed = current_time - saved_time
                saved_penalty = state.get('penalty_points', 0)
                decayed_penalty = max(0, saved_penalty - (elapsed * self.penalty_tracker.decay_rate))
                self.penalty_tracker.points = decayed_penalty
                self.penalty_tracker.last_update = current_time

                logger.info(f"Rate limiter state loaded: penalty_points={decayed_penalty:.1f}, orders={len(self.order_times)}")

        except Exception as e:
            logger.error(f"Failed to load rate limiter state: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Note: Cannot use async in __exit__, cleanup should be done elsewhere
        pass
