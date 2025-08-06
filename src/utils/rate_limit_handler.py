"""
Rate Limit Handler
Safe API call wrapper with rate limit handling
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Rate limit specific error"""
    pass


def rate_limit_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for rate limit retry logic"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except RateLimitError as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"[RATE_LIMIT] Rate limit hit, waiting {delay}s (attempt {attempt + 1}/{max_retries + 1})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error("[RATE_LIMIT] Max retries reached for rate limit")
                        break
                except Exception as e:
                    # For non-rate-limit errors, don't retry
                    logger.error(f"[RATE_LIMIT] Non-rate-limit error: {e}")
                    raise

            # If we get here, all retries failed
            raise last_exception or RateLimitError("Rate limit retries exhausted")

        return wrapper
    return decorator


async def safe_exchange_call(func: Callable, *args, rate_limiter=None, method_name: str = "DEFAULT", **kwargs) -> Any:
    """
    Safely execute exchange API call with rate limiting
    
    Args:
        func: The function to call
        *args: Arguments for the function
        rate_limiter: Optional rate limiter instance
        method_name: Name of the API method for rate limiting
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result of the function call
    
    Raises:
        RateLimitError: If rate limit is exceeded
        Exception: Original exception from function
    """

    # Check rate limiter if provided
    if rate_limiter:
        # Wait if needed
        max_wait_attempts = 10
        wait_attempt = 0

        while not rate_limiter.can_proceed(method_name) and wait_attempt < max_wait_attempts:
            if rate_limiter.is_limited:
                remaining = rate_limiter.limit_until - time.time()
                if remaining > 300:  # If more than 5 minutes, give up
                    raise RateLimitError(f"Rate limit timeout too long: {remaining:.0f}s")

                logger.warning(f"[SAFE_CALL] Rate limit active, waiting {remaining:.1f}s")
                await asyncio.sleep(min(remaining, 30))  # Wait max 30s at a time
            else:
                # Just need to wait for counter to decay
                await asyncio.sleep(1)

            wait_attempt += 1

        if wait_attempt >= max_wait_attempts:
            raise RateLimitError("Rate limit wait timeout")

        # Acquire permission
        if not await rate_limiter.acquire(method_name):
            raise RateLimitError(f"Could not acquire rate limit permission for {method_name}")

    try:
        # Execute the function
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)

        logger.debug(f"[SAFE_CALL] Successfully executed {method_name}")
        return result

    except Exception as e:
        error_str = str(e).lower()

        # Check for rate limit errors
        rate_limit_indicators = [
            'rate limit',
            'too many requests',
            '429',
            'eapi:rate limit exceeded',
            'egeneral:rate limit exceeded'
        ]

        if any(indicator in error_str for indicator in rate_limit_indicators):
            logger.error(f"[SAFE_CALL] Rate limit error detected in {method_name}: {e}")

            # Notify rate limiter
            if rate_limiter:
                rate_limiter.handle_rate_limit_error()

            raise RateLimitError(f"Rate limit exceeded: {e}")
        else:
            # Not a rate limit error, re-raise original
            logger.error(f"[SAFE_CALL] Error in {method_name}: {e}")
            raise


@rate_limit_retry(max_retries=2, base_delay=2.0)
async def safe_api_call(api_func: Callable, *args, rate_limiter=None, method_name: str = "DEFAULT", **kwargs) -> Any:
    """
    High-level safe API call with automatic retry on rate limits
    
    This combines safe_exchange_call with retry logic
    """
    return await safe_exchange_call(api_func, *args, rate_limiter=rate_limiter, method_name=method_name, **kwargs)


def check_rate_limit_error(exception: Exception) -> bool:
    """Check if exception is a rate limit error"""
    error_str = str(exception).lower()
    rate_limit_indicators = [
        'rate limit',
        'too many requests',
        '429',
        'eapi:rate limit exceeded',
        'egeneral:rate limit exceeded'
    ]
    return any(indicator in error_str for indicator in rate_limit_indicators)


class RateLimitManager:
    """Manager for multiple rate limiters"""

    def __init__(self):
        """Initialize rate limit manager"""
        self.limiters: Dict[str, Any] = {}

    def add_limiter(self, name: str, limiter: Any):
        """Add a rate limiter"""
        self.limiters[name] = limiter
        logger.info(f"[RATE_LIMIT_MGR] Added limiter: {name}")

    def get_limiter(self, name: str) -> Optional[Any]:
        """Get rate limiter by name"""
        return self.limiters.get(name)

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all rate limiters"""
        status = {}
        for name, limiter in self.limiters.items():
            if hasattr(limiter, 'get_status'):
                status[name] = limiter.get_status()
            else:
                status[name] = {'status': 'unknown'}
        return status


# Global rate limit manager
_rate_limit_manager = RateLimitManager()


def get_rate_limit_manager() -> RateLimitManager:
    """Get global rate limit manager"""
    return _rate_limit_manager
