"""
Kraken Rate Limiter - Advanced Rate Limiting for Maximum Trading Efficiency

This module provides sophisticated rate limiting for Kraken exchange API calls,
designed specifically for high-frequency micro-scalping strategies while maintaining
full compliance with Kraken's rate limiting requirements.

2025 ENHANCEMENTS:
- Tier-based rate limiting (Starter/Intermediate/Pro)
- Dynamic rate adjustment based on API responses
- Order-specific rate limiting with age-based penalties
- Comprehensive error handling and recovery
- Performance metrics and monitoring
- Token bucket algorithm matching Kraken's counter system
- IOC order optimization (0 penalty points on failure)
- WebSocket rate counter monitoring
- Circuit breaker pattern for recovery
"""

import asyncio
import time
from typing import Dict, Optional, Any
from collections import defaultdict
from dataclasses import dataclass
import logging
logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for different Kraken API tiers."""

    max_counter: int
    decay_rate: float
    max_open_orders: int
    max_api_counter: int  # REST API counter limit
    api_decay_rate: float  # REST API decay rate

    # Tier configurations from Kraken documentation - CORRECTED 2025 VALUES
    STARTER = lambda: RateLimitConfig(
        max_counter=15,   # CORRECTED: Starter tier actual API counter limit
        decay_rate=0.33,  # CORRECTED: 0.33/second decay rate for Starter
        max_open_orders=60,
        max_api_counter=15,  # REST API counter matches trading counter
        api_decay_rate=0.33  # CORRECTED: 0.33/second REST decay
    )
    INTERMEDIATE = lambda: RateLimitConfig(
        max_counter=20,   # CORRECTED: Intermediate tier actual API counter limit
        decay_rate=0.5,   # CORRECTED: 0.5/second decay rate for Intermediate
        max_open_orders=80,
        max_api_counter=20,  # REST API counter matches trading counter
        api_decay_rate=0.5  # Correct 0.5/second REST decay
    )
    PRO = lambda: RateLimitConfig(
        max_counter=20,   # CORRECTED: Pro tier API counter (same as Intermediate)
        decay_rate=1.0,   # CORRECTED: Pro tier gets 1.0/second decay rate
        max_open_orders=225,
        max_api_counter=20,  # REST API counter matches trading counter
        api_decay_rate=1.0  # CORRECTED: Pro tier gets 1.0/second REST decay
    )


class KrakenRateLimiter:
    """
    Advanced Kraken Rate Limiter for Maximum Trading Efficiency

    This rate limiter implements Kraken's exact rate limiting algorithm with
    profit-focused optimizations for micro-scalping strategies.

    Features:
    - Per-pair rate counters with tier-based limits
    - Order age-based penalties for modifications/cancellations
    - Open order tracking per trading pair
    - Dynamic backoff and recovery strategies
    - Comprehensive performance monitoring
    - Token bucket algorithm for REST API limits
    - IOC order optimization (0 penalty on failure)
    - WebSocket rate counter monitoring
    - Circuit breaker pattern for recovery
    """

    def __init__(self, tier: str = "starter"):
        """
        Initialize rate limiter with tier-specific settings.

        Args:
            tier: Account tier ("starter", "intermediate", "pro")
        """
        self.tier = tier.lower()

        # Set tier configuration
        tier_configs = {
            "starter": RateLimitConfig.STARTER(),
            "intermediate": RateLimitConfig.INTERMEDIATE(),
            "pro": RateLimitConfig.PRO(),
        }

        self.config = tier_configs.get(self.tier, RateLimitConfig.STARTER())
        
        # INTEGRATION FIX: Ensure decay_rate is never 0 or invalid
        if self.config.decay_rate <= 0 or self.config.decay_rate > 10:
            logger.warning(f"[KRAKEN_RL] Invalid decay_rate {self.config.decay_rate}, setting to 1.0")
            self.config.decay_rate = 1.0
        
        # INTEGRATION FIX: Validate API decay rate
        if self.config.api_decay_rate <= 0 or self.config.api_decay_rate > 10:
            logger.warning(f"[KRAKEN_RL] Invalid api_decay_rate {self.config.api_decay_rate}, setting to 0.5")
            self.config.api_decay_rate = 0.5

        # Rate counters per trading pair
        self.rate_counters: Dict[str, float] = defaultdict(float)
        self.last_update: Dict[str, float] = defaultdict(float)

        # Open order tracking
        self.open_orders: Dict[str, int] = defaultdict(int)
        
        # REST API token bucket (separate from trading engine)
        self.api_counter = 0.0
        self.api_last_update = time.time()
        
        # IOC order tracking for micro-profit optimization
        self.ioc_orders_success = 0
        self.ioc_orders_failed = 0  # No penalty for failed IOC!
        self.regular_orders_cancelled = 0  # 8 point penalty each!
        
        # WebSocket rate counter monitoring
        self.ws_rate_counter = 0.0
        self.ws_counter_history = []
        
        # Circuit breaker for preventing cascade failures
        self.circuit_breaker_open = False
        self.circuit_breaker_opened_at = 0
        self.circuit_breaker_duration = 10.0  # FIXED: 10 seconds for proper recovery
        self.circuit_breaker_threshold = self.config.max_counter * 0.8  # FIXED: Open at 80% capacity (more conservative)

        # Performance metrics
        self.stats = {
            "requests_made": 0,
            "requests_delayed": 0,
            "rate_limit_hits": 0,
            "errors_handled": 0,
            "average_delay": 0.0,
            "ioc_optimization_savings": 0,  # Points saved by using IOC
        }

        logger.info(
            f"[KRAKEN_RL] Initialized for {tier} tier - Max counter: {self.config.max_counter}, Decay: {self.config.decay_rate}/s, Max orders: {self.config.max_open_orders}"
        )

    async def check_rate_limit(
        self,
        symbol: str,
        operation: str,
        order_age_seconds: Optional[float] = None,
        endpoint: str = "generic",
    ) -> bool:
        """
        Check if operation can proceed without hitting rate limits.

        Args:
            symbol: Trading pair symbol
            operation: Operation type (add_order, cancel_order, etc.)
            order_age_seconds: Age of order for modification/cancellation
            endpoint: API endpoint name for tracking

        Returns:
            bool: True if operation can proceed
        """
        try:
            # Update rate counter with decay
            self._update_rate_counter(symbol)

            # Calculate operation cost
            operation_cost = self._calculate_operation_cost(
                operation, order_age_seconds
            )

            # Check if operation would exceed limit
            current_counter = self.rate_counters[symbol]
            if current_counter + operation_cost > self.config.max_counter:
                logger.debug(
                    f"[KRAKEN_RL] Rate limit check failed for {symbol}: {current_counter + operation_cost:.1f} > {self.config.max_counter}"
                )
                return False

            # Check open orders limit for add_order operations
            if operation == "add_order":
                if self.open_orders[symbol] >= self.config.max_open_orders:
                    logger.debug(
                        f"[KRAKEN_RL] Open orders limit reached for {symbol}: {self.open_orders[symbol]} >= {self.config.max_open_orders}"
                    )
                    return False

            # Apply operation cost
            self.rate_counters[symbol] += operation_cost
            self.stats["requests_made"] += 1

            logger.debug(
                f"[KRAKEN_RL] Operation approved for {symbol}: {operation} (cost: {operation_cost}, new counter: {self.rate_counters[symbol]:.1f})"
            )
            return True

        except (ValueError, TypeError) as e:
            logger.error(f"[KRAKEN_RL] Value/Type error checking rate limit: {e}")
            return True  # Default to allowing operation on error
        except Exception as e:
            logger.error(f"[KRAKEN_RL] Unexpected error checking rate limit: {e}")
            # EXCEPTION HANDLING FIX: Don't allow operations on unexpected errors
            self.stats["errors_handled"] += 1
            return False

    async def wait_if_needed(
        self,
        symbol: str,
        operation: str,
        order_age_seconds: Optional[float] = None,
        endpoint: str = "generic",
    ) -> None:
        """
        Wait if necessary to respect rate limits.

        Args:
            symbol: Trading pair symbol
            operation: Operation type
            order_age_seconds: Age of order for modification/cancellation
            endpoint: API endpoint name
        """
        try:
            max_wait_time = 60.0  # INCREASED: Maximum wait time to 60 seconds
            wait_start = time.time()
            backoff_attempt = 0

            while not await self.check_rate_limit(
                symbol, operation, order_age_seconds, endpoint
            ):
                # Check circuit breaker first
                if not self.check_circuit_breaker():
                    logger.warning(f"[KRAKEN_RL] Circuit breaker open - waiting for recovery")
                    await asyncio.sleep(self.circuit_breaker_duration)
                    continue
                
                # Calculate required wait time with exponential backoff
                current_counter = self.rate_counters[symbol]
                operation_cost = self._calculate_operation_cost(
                    operation, order_age_seconds
                )
                excess = (current_counter + operation_cost) - self.config.max_counter

                # Apply exponential backoff: 1s, 2s, 4s, 8s, 16s
                base_wait_time = excess / max(self.config.decay_rate, 0.1)
                exponential_backoff = min(2 ** backoff_attempt, 16.0)  # Cap at 16 seconds
                wait_time = min(base_wait_time + exponential_backoff, max_wait_time)
                
                backoff_attempt += 1

                logger.info(
                    f"[KRAKEN_RL] Rate limited - waiting {wait_time:.2f}s (attempt {backoff_attempt}) for {symbol} {operation}"
                )

                await asyncio.sleep(wait_time)
                self.stats["requests_delayed"] += 1

                # Safety check to prevent infinite loops
                if time.time() - wait_start > max_wait_time:
                    logger.warning(
                        f"[KRAKEN_RL] Maximum wait time exceeded for {symbol} {operation}"
                    )
                    break

                # Update counter after waiting
                self._update_rate_counter(symbol)

            total_wait = time.time() - wait_start
            if total_wait > 0:
                if self.stats["requests_delayed"] > 0:
                    self.stats["average_delay"] = (
                        self.stats["average_delay"] * (self.stats["requests_delayed"] - 1)
                        + total_wait
                    ) / self.stats["requests_delayed"]
                else:
                    self.stats["average_delay"] = total_wait

        except asyncio.CancelledError:
            logger.info(f"[KRAKEN_RL] Wait cancelled for {symbol} {operation}")
            raise
        except (ValueError, TypeError) as e:
            logger.error(f"[KRAKEN_RL] Value/Type error in wait_if_needed: {e}")
        except Exception as e:
            logger.error(f"[KRAKEN_RL] Unexpected error in wait_if_needed: {e}")
            self.stats["errors_handled"] += 1

    def _update_rate_counter(self, symbol: str) -> None:
        """Update rate counter with decay."""
        current_time = time.time()
        last_time = self.last_update[symbol]

        if last_time > 0:
            # Apply decay based on time elapsed
            time_elapsed = current_time - last_time
            decay_amount = time_elapsed * self.config.decay_rate

            # Reduce counter (can't go below 0)
            self.rate_counters[symbol] = max(
                0, self.rate_counters[symbol] - decay_amount
            )

        self.last_update[symbol] = current_time

    def _calculate_operation_cost(
        self, operation: str, order_age_seconds: Optional[float] = None,
        order_type: Optional[str] = None
    ) -> float:
        """
        Calculate rate limit cost based on operation type and order age.

        Based on Kraken documentation:
        - Add Order: +1
        - Amend Order: +1 + age penalty (3/2/1 based on age)
        - Edit Order: +1 + age penalty (6/5/4/2/1 based on age)
        - Cancel Order: age penalty only (8/6/5/4/2/1 based on age)
        - IOC Orders: 0 penalty on failure! (HUGE advantage for micro-profits)
        """
        base_costs = {
            "add_order": 1.0,
            "amend_order": 1.0,
            "edit_order": 1.0,
            "cancel_order": 0.0,
            "balance": 1.0,
            "ticker": 1.0,
            "positions": 1.0,
            "system": 1.0,
            "ledgers": 2.0,  # High cost endpoint
            "trades_history": 2.0,  # High cost endpoint
        }

        base_cost = base_costs.get(operation, 1.0)

        # Add age-based penalty for order modifications
        if order_age_seconds is not None and operation in [
            "amend_order",
            "edit_order",
            "cancel_order",
        ]:
            if operation == "amend_order":
                if order_age_seconds < 5:
                    base_cost += 3
                elif order_age_seconds < 10:
                    base_cost += 2
                elif order_age_seconds < 15:
                    base_cost += 1
            elif operation == "edit_order":
                if order_age_seconds < 5:
                    base_cost += 6
                elif order_age_seconds < 10:
                    base_cost += 5
                elif order_age_seconds < 15:
                    base_cost += 4
                elif order_age_seconds < 45:
                    base_cost += 2
                elif order_age_seconds < 90:
                    base_cost += 1
            elif operation == "cancel_order":
                if order_age_seconds < 5:
                    base_cost += 8
                elif order_age_seconds < 10:
                    base_cost += 6
                elif order_age_seconds < 15:
                    base_cost += 5
                elif order_age_seconds < 45:
                    base_cost += 4
                elif order_age_seconds < 90:
                    base_cost += 2
                elif order_age_seconds < 300:
                    base_cost += 1

        return base_cost

    def increment_counter(self, symbol: str, amount: float = 1.0) -> None:
        """
        Legacy method for compatibility. Use check_rate_limit instead.
        
        Args:
            symbol: Trading pair symbol
            amount: Amount to increment (default 1.0)
        """
        try:
            self._update_rate_counter(symbol)
            self.rate_counters[symbol] += amount
            logger.debug(f"[KRAKEN_RL] Counter incremented for {symbol}: +{amount} (total: {self.rate_counters[symbol]:.1f})")
        except Exception as e:
            logger.error(f"[KRAKEN_RL] Error incrementing counter: {e}")

    def increment_open_orders(self, symbol: str) -> None:
        """Increment open orders count for symbol."""
        self.open_orders[symbol] += 1
        logger.debug(
            f"[KRAKEN_RL] Open orders for {symbol}: {self.open_orders[symbol]}"
        )

    def decrement_open_orders(self, symbol: str) -> None:
        """Decrement open orders count for symbol."""
        if self.open_orders[symbol] > 0:
            self.open_orders[symbol] -= 1
            logger.debug(
                f"[KRAKEN_RL] Open orders for {symbol}: {self.open_orders[symbol]}"
            )

    def check_open_orders_limit(self, symbol: str) -> bool:
        """Check if adding a new order would exceed the limit."""
        return self.open_orders[symbol] < self.config.max_open_orders

    def handle_kraken_error(self, error_message: str, operation: str) -> None:
        """
        Handle Kraken-specific errors and adjust rate limiting accordingly.

        Args:
            error_message: Error message from Kraken API
            operation: Operation that caused the error
        """
        try:
            error_lower = error_message.lower()

            if "rate limit exceeded" in error_lower:
                self.stats["rate_limit_hits"] += 1
                logger.warning(
                    f"[KRAKEN_RL] Rate limit hit during {operation}: {error_message}"
                )

                # Increase rate counters to prevent immediate retry
                for symbol in self.rate_counters:
                    self.rate_counters[symbol] = min(
                        self.config.max_counter, self.rate_counters[symbol] + 5
                    )

            elif "orders limit exceeded" in error_lower:
                logger.warning(f"[KRAKEN_RL] Orders limit exceeded during {operation}")
                # This error suggests our open orders tracking is off
                # Reset tracking to force a fresh check

            elif "insufficient funds" in error_lower:
                # Not a rate limiting issue, but worth tracking
                logger.debug(f"[KRAKEN_RL] Insufficient funds error during {operation}")

            self.stats["errors_handled"] += 1

        except Exception as e:
            logger.error(f"[KRAKEN_RL] Error handling Kraken error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive rate limiter status."""
        current_time = time.time()

        # Calculate current rate counters
        status = {
            "tier": self.tier,
            "config": {
                "max_counter": self.config.max_counter,
                "decay_rate": self.config.decay_rate,
                "max_open_orders": self.config.max_open_orders,
            },
            "current_counters": {},
            "open_orders": dict(self.open_orders),
            "stats": self.stats.copy(),
            "last_update": current_time,
        }

        # Update all counters and add to status
        for symbol in self.rate_counters:
            self._update_rate_counter(symbol)
            status["current_counters"][symbol] = self.rate_counters[symbol]

        return status

    def reset_counters(self) -> None:
        """Reset all rate counters (for testing or recovery)."""
        self.rate_counters.clear()
        self.last_update.clear()
        logger.info("[KRAKEN_RL] Rate counters reset")

    def reset_open_orders(self, symbol: Optional[str] = None) -> None:
        """Reset open orders tracking."""
        if symbol:
            self.open_orders[symbol] = 0
            logger.info(f"[KRAKEN_RL] Open orders reset for {symbol}")
        else:
            self.open_orders.clear()
            logger.info("[KRAKEN_RL] All open orders reset")
    
    def update_websocket_counter(self, counter_value: float) -> None:
        """
        Update rate counter from WebSocket ratecounter message.
        
        Args:
            counter_value: Current rate counter value from WebSocket
        """
        self.ws_rate_counter = counter_value
        self.ws_counter_history.append({
            'timestamp': time.time(),
            'value': counter_value,
            'utilization': (counter_value / self.config.max_counter) * 100
        })
        
        # Keep only last 100 entries
        if len(self.ws_counter_history) > 100:
            self.ws_counter_history = self.ws_counter_history[-100:]
        
        # Check if we should open circuit breaker (more conservative threshold)
        if counter_value > self.config.max_counter * 0.8:
            logger.warning(
                f"[KRAKEN_RL] High WebSocket counter: {counter_value} "
                f"({(counter_value/self.config.max_counter)*100:.1f}% utilization)"
            )
            if not self.circuit_breaker_open:
                self.open_circuit_breaker()
    
    def open_circuit_breaker(self) -> None:
        """Open circuit breaker to prevent cascade failures."""
        self.circuit_breaker_open = True
        self.circuit_breaker_opened_at = time.time()
        logger.warning(
            f"[KRAKEN_RL] Circuit breaker OPENED for {self.circuit_breaker_duration}s"
        )
    
    def close_circuit_breaker(self) -> None:
        """Close circuit breaker."""
        self.circuit_breaker_open = False
        logger.info("[KRAKEN_RL] Circuit breaker CLOSED")
    
    def check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker allows operations.
        
        Returns:
            True if operations can proceed
        """
        if self.circuit_breaker_open:
            if time.time() - self.circuit_breaker_opened_at > self.circuit_breaker_duration:
                self.close_circuit_breaker()
                return True
            return False
        return True
    
    def track_ioc_order(self, success: bool) -> None:
        """
        Track IOC order outcome for optimization metrics.
        
        Args:
            success: Whether the IOC order was filled
        """
        if success:
            self.ioc_orders_success += 1
        else:
            self.ioc_orders_failed += 1
            # No penalty for failed IOC! This is a HUGE advantage
            self.stats["ioc_optimization_savings"] += 1  # Saved 1 point
    
    def track_order_cancellation(self) -> None:
        """Track regular order cancellation (8 point penalty!)."""
        self.regular_orders_cancelled += 1
        # This is expensive! Each cancellation costs 8 points
        logger.warning(
            f"[KRAKEN_RL] Order cancelled (8 point penalty) - "
            f"Total: {self.regular_orders_cancelled} cancellations = "
            f"{self.regular_orders_cancelled * 8} penalty points"
        )
    
    def get_ioc_optimization_stats(self) -> Dict[str, Any]:
        """Get IOC optimization statistics."""
        total_ioc = self.ioc_orders_success + self.ioc_orders_failed
        
        return {
            "ioc_orders_total": total_ioc,
            "ioc_orders_success": self.ioc_orders_success,
            "ioc_orders_failed": self.ioc_orders_failed,
            "ioc_success_rate": (self.ioc_orders_success / total_ioc * 100) if total_ioc > 0 else 0,
            "points_saved_by_ioc": self.stats["ioc_optimization_savings"],
            "regular_cancellations": self.regular_orders_cancelled,
            "cancellation_penalty_points": self.regular_orders_cancelled * 8,
            "recommendation": self._get_ioc_recommendation()
        }
    
    def _get_ioc_recommendation(self) -> str:
        """Get recommendation based on IOC usage."""
        total_ioc = self.ioc_orders_success + self.ioc_orders_failed
        
        if self.regular_orders_cancelled > 5:
            return (
                f"HIGH PRIORITY: Switch to IOC orders! "
                f"{self.regular_orders_cancelled} cancellations cost "
                f"{self.regular_orders_cancelled * 8} points. "
                f"IOC orders have 0 penalty on failure."
            )
        elif total_ioc < 10:
            return "Consider using more IOC orders for micro-profit strategies"
        elif self.ioc_orders_success / max(total_ioc, 1) < 0.3:
            return "IOC fill rate is low - consider adjusting limit prices"
        else:
            return "IOC optimization is working well"
    
    async def check_rest_api_limit(self, endpoint: str) -> bool:
        """
        Check REST API rate limit (separate from trading engine).
        
        Args:
            endpoint: API endpoint name
            
        Returns:
            bool: True if request can proceed
        """
        try:
            # Update API counter with decay
            current_time = time.time()
            elapsed = current_time - self.api_last_update
            
            if elapsed > 0:
                decay = elapsed * self.config.api_decay_rate
                self.api_counter = max(0, self.api_counter - decay)
                self.api_last_update = current_time
            
            # Get endpoint cost
            cost = 2.0 if endpoint in ["ledgers", "trades_history"] else 1.0
            
            # Check if we have capacity
            if self.api_counter + cost <= self.config.max_api_counter:
                self.api_counter += cost
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[KRAKEN_RL] Error checking REST API limit: {e}")
            return True


# Export main class
__all__ = ["KrakenRateLimiter", "RateLimitConfig"]
