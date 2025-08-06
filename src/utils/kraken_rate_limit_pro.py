"""
Kraken Pro Rate Limiter - 2025 Compliance
==========================================

Advanced rate limiting for Kraken Pro accounts with 180 max counter and 3.75/sec decay.
Implements precise tracking and predictive throttling to prevent API rejections.

Features:
- Pro tier: 180 max counter, 3.75/sec decay rate
- Real-time counter tracking
- Predictive throttling
- WebSocket vs REST prioritization
- Automatic backoff on limits
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration for different tiers"""
    max_counter: int
    decay_rate: float  # Points per second
    burst_capacity: int  # Max requests in burst
    
    @classmethod
    def pro_tier(cls):
        """Kraken Pro tier configuration"""
        return cls(
            max_counter=180,
            decay_rate=3.75,
            burst_capacity=20
        )
    
    @classmethod
    def standard_tier(cls):
        """Standard tier configuration"""
        return cls(
            max_counter=60,
            decay_rate=1.0,
            burst_capacity=10
        )


class KrakenProRateLimiter:
    """Advanced rate limiter for Kraken Pro accounts"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter
        
        Args:
            config: Rate limit configuration (defaults to Pro tier)
        """
        self.config = config or RateLimitConfig.pro_tier()
        
        # Current counter value
        self.current_counter = 0.0
        self.last_update_time = time.time()
        
        # Request history for tracking
        self.request_history = deque(maxlen=1000)
        
        # Statistics
        self.total_requests = 0
        self.throttled_requests = 0
        self.rejected_requests = 0
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        logger.info(f"[RATE_LIMITER] Initialized with Pro tier: max={self.config.max_counter}, decay={self.config.decay_rate}/sec")
    
    async def acquire(self, cost: float = 1.0, priority: str = 'normal') -> bool:
        """
        Acquire rate limit tokens
        
        Args:
            cost: Cost of the request (1.0 for most, higher for expensive operations)
            priority: Request priority ('high', 'normal', 'low')
            
        Returns:
            bool: True if request can proceed, False if should be throttled
        """
        async with self.lock:
            # Update counter with decay
            self._update_counter()
            
            # Check if we have capacity
            if self.current_counter + cost > self.config.max_counter:
                # Would exceed limit
                if priority == 'high' and self.current_counter < self.config.max_counter * 0.9:
                    # Allow high priority if under 90% capacity
                    pass
                else:
                    self.throttled_requests += 1
                    wait_time = self._calculate_wait_time(cost)
                    
                    logger.warning(f"[RATE_LIMITER] Throttling request (counter={self.current_counter:.2f}/{self.config.max_counter})")
                    
                    if priority != 'low':
                        # Wait for capacity (except low priority)
                        await asyncio.sleep(wait_time)
                        self._update_counter()
                    else:
                        # Reject low priority requests when at limit
                        self.rejected_requests += 1
                        return False
            
            # Consume tokens
            self.current_counter += cost
            self.total_requests += 1
            
            # Record request
            self.request_history.append({
                'time': time.time(),
                'cost': cost,
                'counter': self.current_counter,
                'priority': priority
            })
            
            logger.debug(f"[RATE_LIMITER] Request approved (counter={self.current_counter:.2f}/{self.config.max_counter})")
            return True
    
    def _update_counter(self):
        """Update counter with decay"""
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        
        # Apply decay
        decay = elapsed * self.config.decay_rate
        self.current_counter = max(0, self.current_counter - decay)
        
        self.last_update_time = current_time
    
    def _calculate_wait_time(self, cost: float) -> float:
        """Calculate wait time for request to proceed"""
        # How much do we need to decay?
        needed_capacity = (self.current_counter + cost) - self.config.max_counter
        
        if needed_capacity <= 0:
            return 0
        
        # Time to decay enough
        wait_time = needed_capacity / self.config.decay_rate
        
        # Add small buffer
        return wait_time + 0.1
    
    async def wait_if_needed(self, cost: float = 1.0) -> None:
        """Wait if rate limit would be exceeded"""
        async with self.lock:
            self._update_counter()
            
            if self.current_counter + cost > self.config.max_counter:
                wait_time = self._calculate_wait_time(cost)
                logger.info(f"[RATE_LIMITER] Waiting {wait_time:.2f}s for capacity")
                
        if wait_time > 0:
            await asyncio.sleep(wait_time)
    
    def get_current_usage(self) -> Dict:
        """Get current rate limit usage"""
        self._update_counter()
        
        return {
            'current_counter': self.current_counter,
            'max_counter': self.config.max_counter,
            'usage_percent': (self.current_counter / self.config.max_counter) * 100,
            'decay_rate': self.config.decay_rate,
            'available_capacity': self.config.max_counter - self.current_counter
        }
    
    def get_statistics(self) -> Dict:
        """Get rate limiter statistics"""
        return {
            'total_requests': self.total_requests,
            'throttled_requests': self.throttled_requests,
            'rejected_requests': self.rejected_requests,
            'throttle_rate': (self.throttled_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            'current_usage': self.get_current_usage(),
            'recent_requests': len(self.request_history)
        }
    
    def reset(self):
        """Reset rate limiter state"""
        self.current_counter = 0
        self.last_update_time = time.time()
        self.request_history.clear()
        logger.info("[RATE_LIMITER] Reset rate limiter state")
    
    async def bulk_acquire(self, requests: list) -> list:
        """
        Acquire tokens for multiple requests efficiently
        
        Args:
            requests: List of (cost, priority) tuples
            
        Returns:
            List of booleans indicating which requests were approved
        """
        results = []
        
        for cost, priority in requests:
            approved = await self.acquire(cost, priority)
            results.append(approved)
            
            if not approved and priority == 'low':
                # Stop processing low priority if one is rejected
                break
        
        return results
    
    def should_use_websocket(self) -> bool:
        """
        Determine if WebSocket should be used over REST based on rate limits
        
        Returns:
            bool: True if WebSocket is preferred
        """
        usage = self.get_current_usage()
        
        # Prefer WebSocket when over 50% capacity
        if usage['usage_percent'] > 50:
            logger.info("[RATE_LIMITER] Recommending WebSocket due to high REST usage")
            return True
        
        # Also prefer WebSocket if we've had recent throttling
        if self.throttled_requests > 10 in the last minute:
            recent_throttles = sum(
                1 for req in self.request_history
                if time.time() - req['time'] < 60 and req.get('throttled', False)
            )
            if recent_throttles > 5:
                logger.info("[RATE_LIMITER] Recommending WebSocket due to recent throttling")
                return True
        
        return False
    
    async def smart_acquire(self, operation: str) -> bool:
        """
        Smart acquisition based on operation type
        
        Args:
            operation: Type of operation ('order', 'balance', 'ticker', 'history')
            
        Returns:
            bool: True if request should proceed
        """
        # Define costs and priorities for different operations
        operation_config = {
            'order': {'cost': 1.0, 'priority': 'high'},      # Orders are high priority
            'amend': {'cost': 0.5, 'priority': 'high'},      # Amends are cheaper
            'cancel': {'cost': 0.5, 'priority': 'high'},     # Cancels are important
            'balance': {'cost': 1.0, 'priority': 'normal'},  # Balance checks are normal
            'ticker': {'cost': 0.5, 'priority': 'low'},      # Tickers are low priority
            'history': {'cost': 2.0, 'priority': 'low'},     # History is expensive
            'positions': {'cost': 1.0, 'priority': 'normal'}, # Position checks
        }
        
        config = operation_config.get(operation, {'cost': 1.0, 'priority': 'normal'})
        
        return await self.acquire(
            cost=config['cost'],
            priority=config['priority']
        )


# Global instance for easy access
_global_rate_limiter = None


def get_rate_limiter() -> KrakenProRateLimiter:
    """Get global rate limiter instance"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = KrakenProRateLimiter()
    return _global_rate_limiter


async def with_rate_limit(operation: str = 'normal'):
    """
    Decorator for rate-limited operations
    
    Usage:
        @with_rate_limit('order')
        async def place_order(...):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            if await limiter.smart_acquire(operation):
                return await func(*args, **kwargs)
            else:
                logger.warning(f"[RATE_LIMITER] Operation {operation} rejected due to rate limits")
                return None
        return wrapper
    return decorator