"""
Circuit Breaker Pattern Implementation
=====================================

Provides circuit breaker functionality to prevent cascading failures
and protect against repeated errors, especially for API rate limits.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failures exceeded threshold, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 250        # HFT OPTIMIZED: Ultra-high threshold for rapid trading
    success_threshold: int = 1          # HFT OPTIMIZED: Single success for faster recovery
    timeout: float = 0.5               # HFT OPTIMIZED: 500ms ultra-fast recovery
    excluded_exceptions: List[type] = field(default_factory=list)  # Don't count these
    
    # Rate limit specific - HFT OPTIMIZATIONS for ultra-fast trading
    rate_limit_threshold: int = 500    # HFT OPTIMIZED: Massive increase for burst trading
    rate_limit_timeout: float = 0.3    # HFT OPTIMIZED: 300ms for immediate recovery
    adaptive_threshold: bool = True     # HFT OPTIMIZED: Dynamic threshold adjustment
    burst_mode_enabled: bool = True     # HFT OPTIMIZED: Enable burst trading mode
    
    # Exponential backoff - HFT OPTIMIZATIONS for ultra-fast recovery
    backoff_multiplier: float = 1.1    # HFT OPTIMIZED: Minimal backoff for rapid recovery
    max_backoff: float = 10.0          # HFT OPTIMIZED: Maximum 10s backoff for immediate trading
    decay_factor: float = 0.95         # HFT OPTIMIZED: Fast decay for rapid normalization
    performance_mode: bool = True       # HFT OPTIMIZED: Enable performance optimizations


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rate_limit_hits: int = 0
    circuit_opens: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """
    High-frequency trading optimized circuit breaker with adaptive performance tuning
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        
        # PERFORMANCE FIX: Cache timestamp for hot path optimization
        self._state_changed_at = time.time()
        self._last_attempt_time = 0
        self._current_timeout = self.config.timeout
        self._cached_time = time.time()
        self._time_cache_expiry = 0
        
        # HFT Performance optimizations
        self._performance_cache = {}
        self._adaptive_threshold = self.config.failure_threshold
        self._burst_window = 60  # 1-minute burst window
        self._burst_count = 0
        self._burst_start_time = time.time()
        self._fast_recovery_mode = False
        
        # Callbacks
        self._on_state_change: Optional[Callable] = None
        self._on_rate_limit: Optional[Callable] = None
        
        # PERFORMANCE FIX: Reduce logging frequency in hot paths
        self._log_counter = 0
        self._last_log_time = time.time()
        
        # Only log initialization once per circuit breaker
        logger.info(f"[HFT_CIRCUIT_BREAKER] {name} initialized with adaptive threshold={self._adaptive_threshold}")
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking calls)"""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing)"""
        return self.state == CircuitState.HALF_OPEN
    
    def _get_cached_time(self) -> float:
        """PERFORMANCE FIX: Cache timestamp calculations for hot paths"""
        current_time = time.time()
        # Update cache every 100ms to balance accuracy and performance
        if current_time > self._time_cache_expiry:
            self._cached_time = current_time
            self._time_cache_expiry = current_time + 0.1
        return self._cached_time
    
    def can_execute(self, emergency_bypass: bool = False, high_priority: bool = False) -> bool:
        """HFT optimized execution check with adaptive performance tuning"""
        # EMERGENCY BYPASS: Always allow critical trades
        if emergency_bypass:
            # PERFORMANCE FIX: Reduce logging in hot paths
            if self._should_log():
                logger.warning(f"[HFT_CIRCUIT_BREAKER] {self.name} EMERGENCY BYPASS activated")
            return True
        
        # HFT OPTIMIZATION: High priority trades get preferential treatment
        if high_priority and self._can_handle_high_priority():
            return True
            
        # Adaptive threshold adjustment for burst trading
        self._update_adaptive_threshold()
        
        # Normal operation with performance caching
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # HFT OPTIMIZATION: Faster recovery with cached time
            cached_time = self._get_cached_time()
            time_since_open = cached_time - self._state_changed_at
            effective_timeout = self._get_adaptive_timeout()
            
            if time_since_open >= effective_timeout:
                self._transition_to_half_open()
                return True
            return False
        
        # Half-open: allow test calls with burst mode consideration
        return True
    
    def _can_handle_high_priority(self) -> bool:
        """Check if high priority trades can be executed even under stress"""
        return (self.stats.consecutive_failures < self._adaptive_threshold * 0.8 and 
                self._burst_count < 50)  # Allow up to 50 burst trades
    
    def _update_adaptive_threshold(self):
        """Dynamically adjust threshold based on performance"""
        if not hasattr(self.config, 'adaptive_threshold') or not self.config.adaptive_threshold:
            return
            
        current_time = time.time()
        
        # Reset burst window if needed
        if current_time - self._burst_start_time > self._burst_window:
            self._burst_count = 0
            self._burst_start_time = current_time
            
        # Increase threshold during good performance
        if self.stats.consecutive_successes > 10:
            self._adaptive_threshold = min(
                self.config.failure_threshold * 1.5,
                self._adaptive_threshold * 1.1
            )
        # Decrease threshold during poor performance
        elif self.stats.consecutive_failures > 5:
            self._adaptive_threshold = max(
                self.config.failure_threshold * 0.7,
                self._adaptive_threshold * 0.9
            )
    
    def _get_adaptive_timeout(self) -> float:
        """Calculate adaptive timeout based on current performance"""
        base_timeout = self._current_timeout
        
        # Fast recovery mode for high-frequency trading
        if self._fast_recovery_mode or (hasattr(self.config, 'performance_mode') and self.config.performance_mode):
            base_timeout *= 0.5  # 50% faster recovery
            
        # Burst mode reduces timeout even further
        if hasattr(self.config, 'burst_mode_enabled') and self.config.burst_mode_enabled:
            if self._burst_count < 20:  # First 20 in burst window
                base_timeout *= 0.3  # 70% faster recovery
                
        return max(0.1, base_timeout)  # Minimum 100ms timeout
    
    async def call(self, func: Callable, *args, emergency_bypass: bool = False, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker
        
        Args:
            func: Async function to call
            *args, **kwargs: Arguments for the function
            emergency_bypass: EMERGENCY FIX - bypass circuit breaker for critical operations
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open and timeout hasn't passed
            Original exception: If function fails
        """
        if not self.can_execute(emergency_bypass=emergency_bypass):
            self.stats.total_calls += 1
            raise CircuitBreakerOpen(
                f"Circuit breaker {self.name} is OPEN. "
                f"Wait {self._current_timeout - (time.time() - self._state_changed_at):.0f}s"
            )
        
        self.stats.total_calls += 1
        self._last_attempt_time = time.time()
        
        try:
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Success
            self._on_success()
            return result
            
        except Exception as e:
            # Check if this is a rate limit error
            if self._is_rate_limit_error(e):
                if self._on_rate_limit:
                    self._on_rate_limit(e)
            else:
                self._on_failure(e)
            raise
    
    def _on_success(self):
        """Handle successful call"""
        self.stats.successful_calls += 1
        self.stats.last_success_time = time.time()
        self.stats.consecutive_failures = 0
        self.stats.consecutive_successes += 1
        
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.consecutive_successes >= self.config.success_threshold:
                self._transition_to_closed()
        
        # Reset timeout on success
        if self.state == CircuitState.CLOSED:
            self._current_timeout = self.config.timeout
    
    def _should_log(self) -> bool:
        """PERFORMANCE FIX: Rate limit logging to prevent spam in hot paths"""
        current_time = time.time()
        self._log_counter += 1
        
        # Log every 100 calls or every 5 seconds, whichever comes first
        if (self._log_counter >= 100 or 
            current_time - self._last_log_time >= 5.0):
            self._log_counter = 0
            self._last_log_time = current_time
            return True
        return False
    
    def _on_failure(self, error: Exception):
        """Handle failed call with performance optimizations"""
        # Skip excluded exceptions with fast type check
        error_type = type(error)
        if error_type in self.config.excluded_exceptions:
            return
        
        self.stats.failed_calls += 1
        self.stats.last_failure_time = self._get_cached_time()
        self.stats.consecutive_failures += 1
        self.stats.consecutive_successes = 0
        
        # PERFORMANCE FIX: Reduce logging frequency
        if self._should_log():
            logger.warning(
                f"[CIRCUIT_BREAKER] {self.name} failure #{self.stats.consecutive_failures}: {error}"
            )
        
        if self.state == CircuitState.HALF_OPEN:
            # Single failure in half-open reopens circuit
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED:
            if self.stats.consecutive_failures >= self.config.failure_threshold:
                self._transition_to_open()
    
    def _on_rate_limit(self, error: Exception):
        """Handle rate limit error specifically"""
        self.stats.rate_limit_hits += 1
        self.stats.consecutive_failures += 1
        self.stats.consecutive_successes = 0
        
        logger.warning(f"[CIRCUIT_BREAKER] {self.name} rate limit hit #{self.stats.rate_limit_hits}")
        
        # Rate limits open circuit faster
        if self.stats.rate_limit_hits >= self.config.rate_limit_threshold:
            self._current_timeout = self.config.rate_limit_timeout
            self._transition_to_open()
            
            if self._on_rate_limit:
                asyncio.create_task(self._on_rate_limit(error))
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is rate limit related"""
        error_str = str(error).lower()
        return any(pattern in error_str for pattern in [
            'rate limit',
            'too many requests',
            'eapi:rate limit exceeded',
            '429',
            'throttle'
        ])
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self._state_changed_at = time.time()
            self.stats.circuit_opens += 1
            
            # Apply exponential backoff
            self._current_timeout = min(
                self._current_timeout * self.config.backoff_multiplier,
                self.config.max_backoff
            )
            
            logger.error(
                f"[CIRCUIT_BREAKER] {self.name} OPENED after "
                f"{self.stats.consecutive_failures} failures. "
                f"Timeout: {self._current_timeout:.0f}s"
            )
            
            if self._on_state_change:
                asyncio.create_task(
                    self._on_state_change(self.name, CircuitState.OPEN, self.stats)
                )
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        if self.state != CircuitState.HALF_OPEN:
            self.state = CircuitState.HALF_OPEN
            self._state_changed_at = time.time()
            self.stats.consecutive_successes = 0
            
            logger.info(f"[CIRCUIT_BREAKER] {self.name} HALF-OPEN for testing")
            
            if self._on_state_change:
                asyncio.create_task(
                    self._on_state_change(self.name, CircuitState.HALF_OPEN, self.stats)
                )
    
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED
            self._state_changed_at = time.time()
            self.stats.consecutive_failures = 0
            
            # Reset timeout
            self._current_timeout = self.config.timeout
            
            logger.info(f"[CIRCUIT_BREAKER] {self.name} CLOSED - service recovered")
            
            if self._on_state_change:
                asyncio.create_task(
                    self._on_state_change(self.name, CircuitState.CLOSED, self.stats)
                )
    
    def set_state_change_callback(self, callback: Callable):
        """Set callback for state changes"""
        self._on_state_change = callback
    
    def set_rate_limit_callback(self, callback: Callable):
        """Set callback for rate limit hits"""
        self._on_rate_limit = callback
    
    def reset(self):
        """Reset circuit breaker to closed state with claude-flow agent integration"""
        self.state = CircuitState.CLOSED
        self._state_changed_at = time.time()
        self._current_timeout = self.config.timeout
        self.stats.consecutive_failures = 0
        self.stats.consecutive_successes = 0
        
        # Reset adaptive performance metrics
        self._adaptive_threshold = self.config.failure_threshold
        self._burst_count = 0
        self._burst_start_time = time.time()
        self._fast_recovery_mode = True  # Enable fast recovery after reset
        
        logger.info(f"[CIRCUIT_BREAKER] {self.name} manually reset with claude-flow optimization")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        time_in_state = time.time() - self._state_changed_at
        
        status = {
            'name': self.name,
            'state': self.state.value,
            'time_in_state': time_in_state,
            'stats': {
                'total_calls': self.stats.total_calls,
                'successful_calls': self.stats.successful_calls,
                'failed_calls': self.stats.failed_calls,
                'rate_limit_hits': self.stats.rate_limit_hits,
                'circuit_opens': self.stats.circuit_opens,
                'consecutive_failures': self.stats.consecutive_failures,
                'success_rate': (
                    self.stats.successful_calls / self.stats.total_calls 
                    if self.stats.total_calls > 0 else 0
                )
            }
        }
        
        if self.state == CircuitState.OPEN:
            status['time_until_half_open'] = max(
                0, self._current_timeout - time_in_state
            )
        
        return status


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreakerManager:
    """
    Manages multiple circuit breakers for different services
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logger
        
        # Global callbacks
        self._on_any_state_change: Optional[Callable] = None
        
    def get_or_create(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker"""
        if name not in self.circuit_breakers:
            cb = CircuitBreaker(name, config)
            
            # Set manager callback
            cb.set_state_change_callback(self._handle_state_change)
            
            self.circuit_breakers[name] = cb
            self.logger.info(f"[CB_MANAGER] Created circuit breaker: {name}")
        
        return self.circuit_breakers[name]
    
    async def _handle_state_change(
        self, 
        name: str, 
        new_state: CircuitState, 
        stats: CircuitBreakerStats
    ):
        """Handle state change from any circuit breaker"""
        self.logger.info(
            f"[CB_MANAGER] {name} state changed to {new_state.value}"
        )
        
        # Notify global callback
        if self._on_any_state_change:
            await self._on_any_state_change(name, new_state, stats)
        
        # If circuit opened due to rate limits, check if we should slow down globally
        if new_state == CircuitState.OPEN and stats.rate_limit_hits > 0:
            self._check_global_rate_limit_impact()
    
    def _check_global_rate_limit_impact(self):
        """Check if multiple circuit breakers are hitting rate limits"""
        rate_limited_count = sum(
            1 for cb in self.circuit_breakers.values()
            if cb.stats.rate_limit_hits > 0 and cb.is_open
        )
        
        if rate_limited_count >= 2:
            self.logger.warning(
                f"[CB_MANAGER] Multiple services ({rate_limited_count}) "
                f"hitting rate limits - consider global slowdown"
            )
    
    def set_global_state_change_callback(self, callback: Callable):
        """Set callback for any circuit breaker state change"""
        self._on_any_state_change = callback
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {
            name: cb.get_status() 
            for name, cb in self.circuit_breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for name, cb in self.circuit_breakers.items():
            cb.reset()
        self.logger.info("[CB_MANAGER] All circuit breakers reset")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of circuit breaker states"""
        states = {'closed': 0, 'open': 0, 'half_open': 0}
        
        for cb in self.circuit_breakers.values():
            states[cb.state.value] += 1
        
        return {
            'total': len(self.circuit_breakers),
            'states': states,
            'rate_limit_impacted': sum(
                1 for cb in self.circuit_breakers.values()
                if cb.stats.rate_limit_hits > 0
            )
        }


# Global instance
circuit_breaker_manager = CircuitBreakerManager()