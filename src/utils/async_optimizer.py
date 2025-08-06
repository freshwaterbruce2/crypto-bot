"""
Async Pattern Optimizer - High-Performance Async Operations
==========================================================

Advanced async optimization patterns for the crypto trading bot that replace
inefficient async/await patterns with high-performance alternatives.

Features:
- Optimized async task management and batching
- Efficient concurrent execution patterns
- Smart async context managers
- Performance-optimized async iterators
- Deadlock prevention and resource management
- Async semaphore and rate limiting optimizations
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import wraps
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class TaskMetrics:
    """Metrics for async task performance"""
    tasks_created: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_cancelled: int = 0
    avg_execution_time: float = 0.0
    total_execution_time: float = 0.0
    concurrent_tasks: int = 0
    max_concurrent_tasks: int = 0


class OptimizedTaskManager:
    """High-performance async task manager with resource optimization"""

    def __init__(self, max_concurrent_tasks: int = 1000):
        self.max_concurrent_tasks = max_concurrent_tasks
        self._active_tasks: set[asyncio.Task] = set()
        self._task_metrics = TaskMetrics()
        self._task_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._cleanup_interval = 60.0  # Cleanup every minute
        self._last_cleanup = time.time()

        # Task result cache for frequently executed tasks
        self._result_cache: dict[str, Any] = {}
        self._cache_timestamps: dict[str, float] = {}
        self._cache_ttl = 300.0  # 5 minutes default TTL

    async def create_task(self,
                         coro: Coroutine,
                         name: Optional[str] = None,
                         timeout: Optional[float] = None) -> asyncio.Task:
        """Create and track optimized async task"""
        async with self._semaphore:  # Rate limit task creation
            task = asyncio.create_task(coro, name=name)

            async with self._task_lock:
                self._active_tasks.add(task)
                self._task_metrics.tasks_created += 1
                self._task_metrics.concurrent_tasks += 1
                self._task_metrics.max_concurrent_tasks = max(
                    self._task_metrics.max_concurrent_tasks,
                    self._task_metrics.concurrent_tasks
                )

            # Add completion callback
            task.add_done_callback(self._task_completed_callback)

            # Apply timeout if specified
            if timeout:
                task = asyncio.wait_for(task, timeout)

            return task

    def _task_completed_callback(self, task: asyncio.Task):
        """Callback for task completion"""
        asyncio.create_task(self._handle_task_completion(task))

    async def _handle_task_completion(self, task: asyncio.Task):
        """Handle task completion asynchronously"""
        async with self._task_lock:
            self._active_tasks.discard(task)
            self._task_metrics.concurrent_tasks -= 1

            if task.cancelled():
                self._task_metrics.tasks_cancelled += 1
            elif task.exception():
                self._task_metrics.tasks_failed += 1
            else:
                self._task_metrics.tasks_completed += 1

        # Periodic cleanup
        await self._periodic_cleanup()

    async def _periodic_cleanup(self):
        """Periodic cleanup of completed tasks and cache"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            # Clean up completed tasks
            completed_tasks = [task for task in self._active_tasks if task.done()]
            for task in completed_tasks:
                self._active_tasks.discard(task)

            # Clean up expired cache entries
            expired_keys = [
                key for key, timestamp in self._cache_timestamps.items()
                if current_time - timestamp > self._cache_ttl
            ]
            for key in expired_keys:
                self._result_cache.pop(key, None)
                self._cache_timestamps.pop(key, None)

            self._last_cleanup = current_time

            if completed_tasks or expired_keys:
                logger.debug(f"[ASYNC_OPT] Cleaned up {len(completed_tasks)} tasks, {len(expired_keys)} cache entries")

    async def gather_with_concurrency_limit(self,
                                           *awaitables: Awaitable[T],
                                           limit: int = 50,
                                           return_exceptions: bool = False) -> list[T]:
        """Optimized gather with concurrency limiting"""
        semaphore = asyncio.Semaphore(limit)

        async def limited_awaitable(awaitable):
            async with semaphore:
                return await awaitable

        limited_awaitables = [limited_awaitable(aw) for aw in awaitables]
        return await asyncio.gather(*limited_awaitables, return_exceptions=return_exceptions)

    async def batch_execute(self,
                           tasks: list[Callable[[], Awaitable[T]]],
                           batch_size: int = 10,
                           delay_between_batches: float = 0.1) -> list[T]:
        """Execute tasks in batches for better resource management"""
        results = []

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[task() for task in batch],
                return_exceptions=True
            )
            results.extend(batch_results)

            # Small delay between batches to prevent resource exhaustion
            if i + batch_size < len(tasks):
                await asyncio.sleep(delay_between_batches)

        return results

    def get_metrics(self) -> TaskMetrics:
        """Get current task metrics"""
        return self._task_metrics

    async def wait_for_completion(self, timeout: Optional[float] = None):
        """Wait for all active tasks to complete"""
        if not self._active_tasks:
            return

        try:
            await asyncio.wait_for(
                asyncio.gather(*self._active_tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"[ASYNC_OPT] Timeout waiting for {len(self._active_tasks)} tasks")

    async def cancel_all_tasks(self):
        """Cancel all active tasks"""
        for task in self._active_tasks.copy():
            if not task.done():
                task.cancel()

        # Wait briefly for cancellations to process
        await asyncio.sleep(0.1)


class OptimizedAsyncIterator(Generic[T]):
    """High-performance async iterator with prefetching and caching"""

    def __init__(self,
                 source: AsyncIterator[T],
                 prefetch_size: int = 10,
                 cache_size: int = 100):
        self.source = source
        self.prefetch_size = prefetch_size
        self.cache_size = cache_size
        self._prefetch_queue: asyncio.Queue = asyncio.Queue(maxsize=prefetch_size)
        self._cache: deque = deque(maxlen=cache_size)
        self._prefetch_task: Optional[asyncio.Task] = None
        self._exhausted = False

    async def __aiter__(self):
        """Start prefetching and return self"""
        if self._prefetch_task is None:
            self._prefetch_task = asyncio.create_task(self._prefetch_loop())
        return self

    async def __anext__(self):
        """Get next item with prefetching optimization"""
        if self._exhausted and self._prefetch_queue.empty():
            raise StopAsyncIteration

        try:
            # Get from prefetch queue with timeout
            item = await asyncio.wait_for(self._prefetch_queue.get(), timeout=1.0)
            self._cache.append(item)
            return item
        except asyncio.TimeoutError:
            if self._exhausted:
                raise StopAsyncIteration
            raise

    async def _prefetch_loop(self):
        """Background prefetching loop"""
        try:
            async for item in self.source:
                await self._prefetch_queue.put(item)
        except StopAsyncIteration:
            pass
        finally:
            self._exhausted = True

    def get_cached_items(self) -> list[T]:
        """Get recently cached items"""
        return list(self._cache)


class OptimizedRateLimiter:
    """High-performance rate limiter for async operations"""

    def __init__(self,
                 rate_limit: int,
                 time_window: float = 1.0,
                 burst_size: Optional[int] = None):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.burst_size = burst_size or rate_limit

        self._timestamps: deque = deque()
        self._lock = asyncio.Lock()
        self._burst_tokens = self.burst_size
        self._last_refill = time.time()

    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire rate limit tokens"""
        async with self._lock:
            current_time = time.time()

            # Refill burst tokens
            time_passed = current_time - self._last_refill
            if time_passed > 0:
                tokens_to_add = int(time_passed * self.rate_limit / self.time_window)
                self._burst_tokens = min(self.burst_size, self._burst_tokens + tokens_to_add)
                self._last_refill = current_time

            # Clean old timestamps
            cutoff_time = current_time - self.time_window
            while self._timestamps and self._timestamps[0] < cutoff_time:
                self._timestamps.popleft()

            # Check if we can process (either burst tokens or rate limit)
            if self._burst_tokens >= tokens:
                self._burst_tokens -= tokens
                self._timestamps.extend([current_time] * tokens)
                return True
            elif len(self._timestamps) + tokens <= self.rate_limit:
                self._timestamps.extend([current_time] * tokens)
                return True
            else:
                return False

    async def wait_for_capacity(self, tokens: int = 1):
        """Wait until capacity is available"""
        while not await self.acquire(tokens):
            # Calculate wait time based on oldest timestamp
            if self._timestamps:
                wait_time = self.time_window - (time.time() - self._timestamps[0])
                if wait_time > 0:
                    await asyncio.sleep(min(wait_time, 0.1))  # Max 100ms sleep
                else:
                    await asyncio.sleep(0.01)  # Small sleep to prevent busy waiting
            else:
                await asyncio.sleep(0.01)


@asynccontextmanager
async def optimized_timeout(timeout: float):
    """Optimized timeout context manager"""
    task = asyncio.current_task()
    if task is None:
        raise RuntimeError("No current task")

    # Create timeout task
    timeout_task = asyncio.create_task(asyncio.sleep(timeout))

    try:
        # Race between timeout and main execution
        done, pending = await asyncio.wait(
            [timeout_task],
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED
        )

        if timeout_task in done:
            raise asyncio.TimeoutError("Operation timed out")

        yield

    finally:
        # Clean up timeout task
        if not timeout_task.done():
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass


class OptimizedAsyncCache:
    """High-performance async cache with TTL and LRU eviction"""

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: dict[str, Any] = {}
        self._timestamps: dict[str, float] = {}
        self._access_order: deque = deque()
        self._lock = asyncio.Lock()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get cached value"""
        async with self._lock:
            current_time = time.time()

            if key in self._cache:
                # Check TTL
                if current_time - self._timestamps[key] <= self.default_ttl:
                    # Move to end for LRU
                    self._access_order.remove(key)
                    self._access_order.append(key)
                    return self._cache[key]
                else:
                    # Expired, remove
                    await self._remove_key(key)

            return default

    async def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set cached value"""
        async with self._lock:
            current_time = time.time()
            ttl = ttl or self.default_ttl

            # Remove if already exists
            if key in self._cache:
                await self._remove_key(key)

            # Check size limit
            while len(self._cache) >= self.max_size:
                # Remove LRU item
                oldest_key = self._access_order.popleft()
                await self._remove_key(oldest_key)

            # Add new item
            self._cache[key] = value
            self._timestamps[key] = current_time
            self._access_order.append(key)

    async def _remove_key(self, key: str):
        """Remove key from all data structures"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        try:
            self._access_order.remove(key)
        except ValueError:
            pass  # Key not in deque

    async def clear_expired(self):
        """Clear all expired entries"""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, timestamp in self._timestamps.items()
                if current_time - timestamp > self.default_ttl
            ]

            for key in expired_keys:
                await self._remove_key(key)

            return len(expired_keys)


# Decorators for async optimization

def async_cached(ttl: float = 300.0, max_size: int = 100):
    """Decorator for caching async function results"""
    cache = OptimizedAsyncCache(max_size=max_size, default_ttl=ttl)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # Try to get from cache
            result = await cache.get(key)
            if result is not None:
                return result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(key, result)

            return result

        # Add cache management methods
        wrapper.clear_cache = cache.clear_expired
        wrapper.get_cache_stats = lambda: {
            'size': len(cache._cache),
            'max_size': cache.max_size,
            'ttl': cache.default_ttl
        }

        return wrapper
    return decorator


def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for async function retry with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(f"[ASYNC_OPT] {func.__name__} failed (attempt {attempt + 1}), retrying in {current_delay}s: {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"[ASYNC_OPT] {func.__name__} failed after {max_retries + 1} attempts: {e}")

            raise last_exception

        return wrapper
    return decorator


def async_rate_limited(rate: int, window: float = 1.0):
    """Decorator for async function rate limiting"""
    limiter = OptimizedRateLimiter(rate, window)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.wait_for_capacity()
            return await func(*args, **kwargs)

        wrapper.get_rate_stats = lambda: {
            'rate_limit': limiter.rate_limit,
            'time_window': limiter.time_window,
            'current_usage': len(limiter._timestamps)
        }

        return wrapper
    return decorator


def async_timeout(timeout: float):
    """Decorator for async function timeout"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with optimized_timeout(timeout):
                return await func(*args, **kwargs)

        return wrapper
    return decorator


# Global instances
_task_manager: Optional[OptimizedTaskManager] = None


async def get_task_manager() -> OptimizedTaskManager:
    """Get global optimized task manager"""
    global _task_manager
    if _task_manager is None:
        _task_manager = OptimizedTaskManager(max_concurrent_tasks=1000)
    return _task_manager


# Utility functions for common async patterns

async def async_chunk_processor(items: list[T],
                               processor: Callable[[T], Awaitable[R]],
                               chunk_size: int = 10,
                               max_concurrency: int = 5) -> list[R]:
    """Process items in chunks with concurrency control"""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def process_chunk(chunk):
        async with semaphore:
            return await asyncio.gather(*[processor(item) for item in chunk])

    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    chunk_results = await asyncio.gather(*[process_chunk(chunk) for chunk in chunks])

    # Flatten results
    results = []
    for chunk_result in chunk_results:
        results.extend(chunk_result)

    return results


async def async_map_with_limit(func: Callable[[T], Awaitable[R]],
                              items: list[T],
                              limit: int = 10) -> list[R]:
    """Async map with concurrency limit"""
    semaphore = asyncio.Semaphore(limit)

    async def limited_func(item):
        async with semaphore:
            return await func(item)

    return await asyncio.gather(*[limited_func(item) for item in items])


class AsyncResourcePool(Generic[T]):
    """Generic async resource pool for database connections, HTTP clients, etc."""

    def __init__(self,
                 factory: Callable[[], Awaitable[T]],
                 max_size: int = 10,
                 min_size: int = 2):
        self.factory = factory
        self.max_size = max_size
        self.min_size = min_size
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._created_count = 0
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize pool with minimum resources"""
        for _ in range(self.min_size):
            resource = await self.factory()
            await self._pool.put(resource)
            self._created_count += 1

    async def acquire(self) -> T:
        """Acquire resource from pool"""
        try:
            # Try to get from pool immediately
            resource = self._pool.get_nowait()
            return resource
        except asyncio.QueueEmpty:
            # Create new resource if under limit
            async with self._lock:
                if self._created_count < self.max_size:
                    resource = await self.factory()
                    self._created_count += 1
                    return resource

            # Wait for resource to become available
            return await self._pool.get()

    async def release(self, resource: T):
        """Release resource back to pool"""
        try:
            self._pool.put_nowait(resource)
        except asyncio.QueueFull:
            # Pool is full, discard resource
            self._created_count -= 1
