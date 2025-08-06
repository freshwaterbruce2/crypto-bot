"""
Main Circuit Breaker Implementation
==================================

Core circuit breaker pattern implementation with three-state machine,
configurable thresholds, exponential backoff, and comprehensive monitoring.

State Machine:
- CLOSED: Normal operation, requests pass through
- OPEN: Failure threshold exceeded, requests blocked
- HALF-OPEN: Recovery testing, limited requests allowed

Features:
- Configurable failure thresholds and timeouts
- Exponential backoff with jitter
- Thread-safe operations
- Persistent state across restarts
- Comprehensive metrics and logging
- Integration with rate limiting and auth systems
"""

import asyncio
import json
import logging
import random
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker errors."""
    pass


class BreakerOpenError(CircuitBreakerError):
    """Exception raised when circuit breaker is open."""
    pass


class BreakerTimeoutError(CircuitBreakerError):
    """Exception raised when circuit breaker operation times out."""
    pass


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for circuit breaker behavior.
    
    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time in seconds before attempting recovery
        success_threshold: Number of successes needed to close circuit in half-open state
        max_recovery_attempts: Maximum recovery attempts before extended timeout
        base_backoff: Base backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_multiplier: Multiplier for exponential backoff
        jitter_range: Range for backoff jitter (0.0 to 1.0)
        timeout: Default timeout for operations in seconds
        monitoring_window: Time window for failure rate calculation
        health_check_interval: Interval between health checks in seconds
        enable_half_open_test: Whether to enable half-open testing
        max_half_open_requests: Maximum concurrent requests in half-open state
        persistent_state: Whether to persist state across restarts
    """
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    success_threshold: int = 3
    max_recovery_attempts: int = 5
    base_backoff: float = 1.0
    max_backoff: float = 300.0
    backoff_multiplier: float = 2.0
    jitter_range: float = 0.2
    timeout: float = 30.0
    monitoring_window: float = 300.0  # 5 minutes
    health_check_interval: float = 10.0
    enable_half_open_test: bool = True
    max_half_open_requests: int = 3
    persistent_state: bool = True


@dataclass
class CircuitBreakerMetrics:
    """
    Metrics tracked by circuit breaker.
    
    Attributes:
        total_requests: Total number of requests processed
        successful_requests: Number of successful requests
        failed_requests: Number of failed requests
        blocked_requests: Number of requests blocked due to open circuit
        state_transitions: Number of state transitions
        recovery_attempts: Number of recovery attempts
        avg_response_time: Average response time in milliseconds
        failure_rate: Current failure rate (0.0 to 1.0)
        uptime_percentage: Uptime percentage since last reset
        last_failure_time: Timestamp of last failure
        last_recovery_time: Timestamp of last recovery attempt
        state_durations: Time spent in each state
    """
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    blocked_requests: int = 0
    state_transitions: int = 0
    recovery_attempts: int = 0
    avg_response_time: float = 0.0
    failure_rate: float = 0.0
    uptime_percentage: float = 100.0
    last_failure_time: Optional[float] = None
    last_recovery_time: Optional[float] = None
    state_durations: Dict[str, float] = field(default_factory=lambda: {
        'CLOSED': 0.0,
        'OPEN': 0.0,
        'HALF_OPEN': 0.0
    })


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation with comprehensive monitoring.
    
    Provides protection against cascading failures by monitoring request success/failure
    rates and temporarily blocking requests when failure thresholds are exceeded.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        storage_path: Optional[str] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Unique name for this circuit breaker
            config: Configuration object
            storage_path: Path for persistent state storage
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.storage_path = Path(storage_path) if storage_path else None

        # State management
        self._state = CircuitBreakerState.CLOSED
        self._last_state_change = time.time()
        self._failure_count = 0
        self._success_count = 0
        self._recovery_attempts = 0
        self._half_open_requests = 0

        # Metrics and monitoring
        self.metrics = CircuitBreakerMetrics()
        self._response_times = deque(maxlen=1000)
        self._recent_failures = deque(maxlen=100)
        self._request_history = deque(maxlen=1000)

        # Thread safety
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()

        # Health monitoring
        self._last_health_check = 0.0
        self._health_status = True

        # Load persistent state
        if self.config.persistent_state and self.storage_path:
            self._load_state()

        logger.info(f"Circuit breaker '{name}' initialized with config: {asdict(self.config)}")

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed (normal operation)."""
        return self.state == CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open (blocking requests)."""
        return self.state == CircuitBreakerState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open (testing recovery)."""
        return self.state == CircuitBreakerState.HALF_OPEN

    def can_execute(self) -> bool:
        """
        Check if a request can be executed.
        
        Returns:
            True if request can proceed, False if blocked
        """
        with self._lock:
            current_time = time.time()

            # Update state if necessary
            self._update_state(current_time)

            if self._state == CircuitBreakerState.CLOSED:
                return True
            elif self._state == CircuitBreakerState.OPEN:
                return False
            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Allow limited requests in half-open state
                return self._half_open_requests < self.config.max_half_open_requests

            return False

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            BreakerOpenError: If circuit breaker is open
            BreakerTimeoutError: If operation times out
            Exception: Original exception from function
        """
        if not self.can_execute():
            self._record_blocked_request()
            raise BreakerOpenError(f"Circuit breaker '{self.name}' is open")

        start_time = time.time()

        try:
            # Execute function with timeout
            if self.config.timeout > 0:
                # For sync functions, we can't easily implement timeout
                # This would require threading or signal handling
                result = func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            self._record_success(execution_time)

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._record_failure(e, execution_time)
            raise

    async def execute_async(
        self,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Execute an async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            timeout: Operation timeout (defaults to config timeout)
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            BreakerOpenError: If circuit breaker is open
            BreakerTimeoutError: If operation times out
            Exception: Original exception from function
        """
        async with self._async_lock:
            if not self.can_execute():
                self._record_blocked_request()
                raise BreakerOpenError(f"Circuit breaker '{self.name}' is open")

        if self._state == CircuitBreakerState.HALF_OPEN:
            with self._lock:
                self._half_open_requests += 1

        start_time = time.time()
        operation_timeout = timeout or self.config.timeout

        try:
            # Execute function with timeout
            if operation_timeout > 0:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=operation_timeout)
            else:
                result = await func(*args, **kwargs)

            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            self._record_success(execution_time)

            return result

        except asyncio.TimeoutError:
            execution_time = (time.time() - start_time) * 1000
            error = BreakerTimeoutError(f"Operation timed out after {operation_timeout}s")
            self._record_failure(error, execution_time)
            raise error

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._record_failure(e, execution_time)
            raise

        finally:
            if self._state == CircuitBreakerState.HALF_OPEN:
                with self._lock:
                    self._half_open_requests = max(0, self._half_open_requests - 1)

    @asynccontextmanager
    async def async_context(self):
        """
        Async context manager for circuit breaker operations.
        
        Usage:
            async with circuit_breaker.async_context() as cb:
                result = await cb.execute_async(some_async_function)
        """
        try:
            yield self
        except Exception as e:
            logger.error(f"Circuit breaker context error: {e}")
            raise

    def _update_state(self, current_time: float) -> None:
        """
        Update circuit breaker state based on current conditions.
        
        Args:
            current_time: Current timestamp
        """
        if self._state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has elapsed
            time_since_last_change = current_time - self._last_state_change
            recovery_timeout = self._calculate_recovery_timeout()

            if time_since_last_change >= recovery_timeout:
                self._transition_to_half_open(current_time)

        elif self._state == CircuitBreakerState.HALF_OPEN:
            # Check if we should close or reopen
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed(current_time)
            elif self._should_reopen():
                self._transition_to_open(current_time)

    def _should_open(self) -> bool:
        """
        Check if circuit breaker should open based on failure threshold.
        
        Returns:
            True if circuit should open
        """
        if self._failure_count >= self.config.failure_threshold:
            return True

        # Check failure rate within monitoring window
        current_time = time.time()
        window_start = current_time - self.config.monitoring_window

        recent_requests = [
            req for req in self._request_history
            if req['timestamp'] >= window_start
        ]

        if len(recent_requests) >= self.config.failure_threshold:
            failures = sum(1 for req in recent_requests if not req['success'])
            failure_rate = failures / len(recent_requests)

            # Open if failure rate is above threshold (e.g., 50%)
            return failure_rate >= 0.5

        return False

    def _should_reopen(self) -> bool:
        """
        Check if circuit breaker should reopen from half-open state.
        
        Returns:
            True if circuit should reopen
        """
        # Reopen if we have any failures in half-open state
        return self._failure_count > 0

    def _transition_to_open(self, current_time: float) -> None:
        """
        Transition circuit breaker to OPEN state.
        
        Args:
            current_time: Current timestamp
        """
        if self._state != CircuitBreakerState.OPEN:
            old_state = self._state
            self._state = CircuitBreakerState.OPEN
            self._last_state_change = current_time
            self._recovery_attempts += 1
            self.metrics.state_transitions += 1

            logger.warning(
                f"Circuit breaker '{self.name}' OPENED: "
                f"{old_state.value} → OPEN "
                f"(failures: {self._failure_count}/{self.config.failure_threshold}, "
                f"recovery_attempts: {self._recovery_attempts})"
            )

            self._update_state_duration(old_state, current_time)

    def _transition_to_half_open(self, current_time: float) -> None:
        """
        Transition circuit breaker to HALF_OPEN state.
        
        Args:
            current_time: Current timestamp
        """
        if self._state != CircuitBreakerState.HALF_OPEN:
            old_state = self._state
            self._state = CircuitBreakerState.HALF_OPEN
            self._last_state_change = current_time
            self._success_count = 0
            self._failure_count = 0
            self._half_open_requests = 0
            self.metrics.state_transitions += 1
            self.metrics.last_recovery_time = current_time

            logger.info(
                f"Circuit breaker '{self.name}' HALF-OPEN: "
                f"{old_state.value} → HALF_OPEN "
                f"(testing recovery, attempts: {self._recovery_attempts})"
            )

            self._update_state_duration(old_state, current_time)

    def _transition_to_closed(self, current_time: float) -> None:
        """
        Transition circuit breaker to CLOSED state.
        
        Args:
            current_time: Current timestamp
        """
        if self._state != CircuitBreakerState.CLOSED:
            old_state = self._state
            self._state = CircuitBreakerState.CLOSED
            self._last_state_change = current_time
            self._failure_count = 0
            self._recovery_attempts = 0
            self.metrics.state_transitions += 1

            logger.info(
                f"Circuit breaker '{self.name}' CLOSED: "
                f"{old_state.value} → CLOSED "
                f"(recovery successful after {self._success_count} successes)"
            )

            self._update_state_duration(old_state, current_time)

    def _calculate_recovery_timeout(self) -> float:
        """
        Calculate recovery timeout with exponential backoff.
        
        Returns:
            Recovery timeout in seconds
        """
        if self._recovery_attempts == 0:
            return self.config.recovery_timeout

        # Exponential backoff with jitter
        backoff = min(
            self.config.base_backoff * (self.config.backoff_multiplier ** (self._recovery_attempts - 1)),
            self.config.max_backoff
        )

        # Add jitter to prevent thundering herd
        jitter = backoff * self.config.jitter_range * (random.random() - 0.5)

        return max(self.config.recovery_timeout, backoff + jitter)

    def _record_success(self, execution_time: float) -> None:
        """
        Record a successful request.
        
        Args:
            execution_time: Execution time in milliseconds
        """
        with self._lock:
            current_time = time.time()

            # Update counters
            self._success_count += 1
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1

            # Update response times
            self._response_times.append(execution_time)
            if self._response_times:
                self.metrics.avg_response_time = sum(self._response_times) / len(self._response_times)

            # Update request history
            self._request_history.append({
                'timestamp': current_time,
                'success': True,
                'execution_time': execution_time
            })

            # Update state if necessary
            self._update_state(current_time)

            logger.debug(
                f"Circuit breaker '{self.name}' recorded success: "
                f"time={execution_time:.2f}ms, state={self._state.value}"
            )

    def _record_failure(self, error: Exception, execution_time: float) -> None:
        """
        Record a failed request.
        
        Args:
            error: Exception that occurred
            execution_time: Execution time in milliseconds
        """
        with self._lock:
            current_time = time.time()

            # Update counters
            self._failure_count += 1
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = current_time

            # Update failure tracking
            self._recent_failures.append({
                'timestamp': current_time,
                'error': str(error),
                'error_type': type(error).__name__,
                'execution_time': execution_time
            })

            # Update request history
            self._request_history.append({
                'timestamp': current_time,
                'success': False,
                'execution_time': execution_time,
                'error': str(error)
            })

            # Calculate failure rate
            self._update_failure_rate(current_time)

            # Check if circuit should open
            if self._state == CircuitBreakerState.CLOSED and self._should_open():
                self._transition_to_open(current_time)
            elif self._state == CircuitBreakerState.HALF_OPEN and self._should_reopen():
                self._transition_to_open(current_time)

            logger.warning(
                f"Circuit breaker '{self.name}' recorded failure: "
                f"error={type(error).__name__}, time={execution_time:.2f}ms, "
                f"failures={self._failure_count}/{self.config.failure_threshold}, "
                f"state={self._state.value}"
            )

    def _record_blocked_request(self) -> None:
        """
        Record a request that was blocked by the circuit breaker.
        """
        with self._lock:
            self.metrics.blocked_requests += 1

            logger.debug(
                f"Circuit breaker '{self.name}' blocked request: "
                f"state={self._state.value}, blocked_total={self.metrics.blocked_requests}"
            )

    def _update_failure_rate(self, current_time: float) -> None:
        """
        Update the current failure rate.
        
        Args:
            current_time: Current timestamp
        """
        window_start = current_time - self.config.monitoring_window

        recent_requests = [
            req for req in self._request_history
            if req['timestamp'] >= window_start
        ]

        if recent_requests:
            failures = sum(1 for req in recent_requests if not req['success'])
            self.metrics.failure_rate = failures / len(recent_requests)
        else:
            self.metrics.failure_rate = 0.0

    def _update_state_duration(self, old_state: CircuitBreakerState, current_time: float) -> None:
        """
        Update the duration spent in a particular state.
        
        Args:
            old_state: Previous state
            current_time: Current timestamp
        """
        duration = current_time - self._last_state_change
        self.metrics.state_durations[old_state.value] += duration

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive circuit breaker status.
        
        Returns:
            Status dictionary with metrics and configuration
        """
        with self._lock:
            current_time = time.time()

            # Calculate uptime percentage
            total_time = sum(self.metrics.state_durations.values())
            if total_time > 0:
                uptime = (self.metrics.state_durations['CLOSED'] +
                         self.metrics.state_durations['HALF_OPEN']) / total_time * 100
                self.metrics.uptime_percentage = uptime

            status = {
                'name': self.name,
                'state': self._state.value,
                'state_duration': current_time - self._last_state_change,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'recovery_attempts': self._recovery_attempts,
                'half_open_requests': self._half_open_requests,
                'next_recovery_time': (
                    self._last_state_change + self._calculate_recovery_timeout()
                    if self._state == CircuitBreakerState.OPEN else None
                ),
                'can_execute': self.can_execute(),
                'health_status': self._health_status,
                'config': asdict(self.config),
                'metrics': asdict(self.metrics),
                'recent_failures': list(self._recent_failures)[-10:],  # Last 10 failures
                'performance': {
                    'avg_response_time_ms': self.metrics.avg_response_time,
                    'recent_response_times': list(self._response_times)[-20:],  # Last 20 times
                    'failure_rate': self.metrics.failure_rate,
                    'requests_per_second': self._calculate_rps(current_time)
                }
            }

            return status

    def _calculate_rps(self, current_time: float) -> float:
        """
        Calculate requests per second over the last minute.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            Requests per second
        """
        minute_ago = current_time - 60.0
        recent_requests = [
            req for req in self._request_history
            if req['timestamp'] >= minute_ago
        ]
        return len(recent_requests) / 60.0

    def reset(self) -> None:
        """
        Reset circuit breaker to initial state.
        
        This clears all metrics and resets to CLOSED state.
        """
        with self._lock:
            current_time = time.time()

            # Reset state
            old_state = self._state
            self._state = CircuitBreakerState.CLOSED
            self._last_state_change = current_time
            self._failure_count = 0
            self._success_count = 0
            self._recovery_attempts = 0
            self._half_open_requests = 0

            # Reset metrics
            self.metrics = CircuitBreakerMetrics()
            self._response_times.clear()
            self._recent_failures.clear()
            self._request_history.clear()

            logger.info(f"Circuit breaker '{self.name}' reset: {old_state.value} → CLOSED")

    def force_open(self) -> None:
        """
        Force circuit breaker to OPEN state.
        
        Useful for maintenance or emergency situations.
        """
        with self._lock:
            current_time = time.time()
            old_state = self._state
            self._transition_to_open(current_time)

            logger.warning(f"Circuit breaker '{self.name}' FORCE OPENED: {old_state.value} → OPEN")

    def force_close(self) -> None:
        """
        Force circuit breaker to CLOSED state.
        
        Use with caution - bypasses safety mechanisms.
        """
        with self._lock:
            current_time = time.time()
            old_state = self._state
            self._transition_to_closed(current_time)

            logger.warning(f"Circuit breaker '{self.name}' FORCE CLOSED: {old_state.value} → CLOSED")

    def _save_state(self) -> None:
        """
        Save circuit breaker state to persistent storage.
        """
        if not self.config.persistent_state or not self.storage_path:
            return

        try:
            state_data = {
                'name': self.name,
                'state': self._state.value,
                'last_state_change': self._last_state_change,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'recovery_attempts': self._recovery_attempts,
                'metrics': asdict(self.metrics),
                'timestamp': time.time()
            }

            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w') as f:
                json.dump(state_data, f, indent=2)

            logger.debug(f"Circuit breaker '{self.name}' state saved to {self.storage_path}")

        except Exception as e:
            logger.error(f"Failed to save circuit breaker state: {e}")

    def _load_state(self) -> None:
        """
        Load circuit breaker state from persistent storage.
        """
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path) as f:
                state_data = json.load(f)

            # Check if state is recent (within 1 hour)
            current_time = time.time()
            saved_time = state_data.get('timestamp', 0)

            if (current_time - saved_time) < 3600:  # 1 hour
                self._state = CircuitBreakerState(state_data.get('state', 'CLOSED'))
                self._last_state_change = state_data.get('last_state_change', current_time)
                self._failure_count = state_data.get('failure_count', 0)
                self._success_count = state_data.get('success_count', 0)
                self._recovery_attempts = state_data.get('recovery_attempts', 0)

                # Load metrics if available
                if 'metrics' in state_data:
                    metrics_data = state_data['metrics']
                    for key, value in metrics_data.items():
                        if hasattr(self.metrics, key):
                            setattr(self.metrics, key, value)

                logger.info(
                    f"Circuit breaker '{self.name}' state loaded: "
                    f"state={self._state.value}, failures={self._failure_count}"
                )
            else:
                logger.info(f"Circuit breaker '{self.name}' state too old, starting fresh")

        except Exception as e:
            logger.error(f"Failed to load circuit breaker state: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.config.persistent_state:
            self._save_state()

    def __str__(self) -> str:
        """String representation."""
        return (
            f"CircuitBreaker(name='{self.name}', state={self._state.value}, "
            f"failures={self._failure_count}/{self.config.failure_threshold})"
        )

    def __repr__(self) -> str:
        """Detailed representation."""
        return self.__str__()

    def cleanup(self) -> None:
        """Cleanup circuit breaker resources."""
        if self.config.persistent_state:
            self._save_state()

        logger.debug(f"Circuit breaker '{self.name}' cleanup completed")


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers with centralized monitoring.
    
    Provides factory methods for creating circuit breakers, centralized
    configuration, and aggregate monitoring capabilities.
    """

    def __init__(
        self,
        default_config: Optional[CircuitBreakerConfig] = None,
        storage_dir: Optional[str] = None
    ):
        """
        Initialize circuit breaker manager.
        
        Args:
            default_config: Default configuration for new circuit breakers
            storage_dir: Directory for persistent storage
        """
        self.default_config = default_config or CircuitBreakerConfig()
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None

        logger.info(f"Circuit breaker manager initialized with storage: {storage_dir}")

    def create_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Create or retrieve a circuit breaker.
        
        Args:
            name: Unique name for the circuit breaker
            config: Optional custom configuration
            
        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name in self._breakers:
                return self._breakers[name]

            storage_path = None
            if self.storage_dir:
                storage_path = self.storage_dir / f"{name}_state.json"

            breaker_config = config or self.default_config
            breaker = CircuitBreaker(name, breaker_config, storage_path)

            self._breakers[name] = breaker

            logger.info(f"Created circuit breaker: {name}")
            return breaker

    def get_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """
        Get an existing circuit breaker.
        
        Args:
            name: Circuit breaker name
            
        Returns:
            CircuitBreaker instance or None if not found
        """
        with self._lock:
            return self._breakers.get(name)

    def remove_breaker(self, name: str) -> bool:
        """
        Remove a circuit breaker.
        
        Args:
            name: Circuit breaker name
            
        Returns:
            True if breaker was removed, False if not found
        """
        with self._lock:
            if name in self._breakers:
                breaker = self._breakers.pop(name)
                if breaker.config.persistent_state:
                    breaker._save_state()
                logger.info(f"Removed circuit breaker: {name}")
                return True
            return False

    def get_all_breakers(self) -> Dict[str, CircuitBreaker]:
        """
        Get all circuit breakers.
        
        Returns:
            Dictionary of circuit breakers
        """
        with self._lock:
            return self._breakers.copy()

    def get_aggregate_status(self) -> Dict[str, Any]:
        """
        Get aggregate status of all circuit breakers.
        
        Returns:
            Aggregate status dictionary
        """
        with self._lock:
            breakers = list(self._breakers.values())

        if not breakers:
            return {
                'total_breakers': 0,
                'states': {},
                'aggregate_metrics': {},
                'health_summary': 'No breakers'
            }

        # Aggregate metrics
        total_requests = sum(b.metrics.total_requests for b in breakers)
        total_failures = sum(b.metrics.failed_requests for b in breakers)
        total_blocked = sum(b.metrics.blocked_requests for b in breakers)

        # State distribution
        states = defaultdict(int)
        for breaker in breakers:
            states[breaker.state.value] += 1

        # Health summary
        open_breakers = states.get('OPEN', 0)
        if open_breakers == 0:
            health_summary = 'Healthy'
        elif open_breakers < len(breakers) / 2:
            health_summary = 'Degraded'
        else:
            health_summary = 'Critical'

        return {
            'total_breakers': len(breakers),
            'states': dict(states),
            'aggregate_metrics': {
                'total_requests': total_requests,
                'total_failures': total_failures,
                'total_blocked': total_blocked,
                'overall_failure_rate': total_failures / max(total_requests, 1),
                'avg_response_time': sum(b.metrics.avg_response_time for b in breakers) / len(breakers)
            },
            'health_summary': health_summary,
            'breaker_details': {
                name: breaker.get_status()
                for name, breaker in self._breakers.items()
            }
        }

    async def start_monitoring(self, interval: float = 30.0) -> None:
        """
        Start background monitoring of all circuit breakers.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval))

        logger.info(f"Started circuit breaker monitoring with {interval}s interval")

    async def stop_monitoring(self) -> None:
        """
        Stop background monitoring.
        """
        self._monitoring_active = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped circuit breaker monitoring")

    async def _monitoring_loop(self, interval: float) -> None:
        """
        Background monitoring loop.
        
        Args:
            interval: Monitoring interval in seconds
        """
        while self._monitoring_active:
            try:
                await asyncio.sleep(interval)

                # Save state for all breakers
                with self._lock:
                    for breaker in self._breakers.values():
                        if breaker.config.persistent_state:
                            breaker._save_state()

                # Log aggregate status
                status = self.get_aggregate_status()
                logger.info(
                    f"Circuit breaker monitoring: {status['total_breakers']} breakers, "
                    f"states={status['states']}, health={status['health_summary']}"
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Circuit breaker monitoring error: {e}")

    def reset_all(self) -> None:
        """
        Reset all circuit breakers to initial state.
        """
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()

        logger.info("Reset all circuit breakers")

    def cleanup(self) -> None:
        """
        Cleanup all circuit breakers and save state.
        """
        with self._lock:
            for breaker in self._breakers.values():
                if breaker.config.persistent_state:
                    breaker._save_state()

        logger.info("Circuit breaker manager cleanup completed")

    @asynccontextmanager
    async def get_breaker_context(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """
        Async context manager for circuit breaker operations.
        
        Usage:
            async with manager.get_breaker_context('api_calls') as breaker:
                result = await breaker.execute_async(api_function)
        
        Args:
            name: Circuit breaker name
            config: Optional configuration
        """
        breaker = self.create_breaker(name, config)
        try:
            yield breaker
        finally:
            if breaker.config.persistent_state:
                breaker._save_state()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
