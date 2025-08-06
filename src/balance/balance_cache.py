"""
Balance Cache System
===================

Intelligent caching system for balance data with TTL (Time To Live) and LRU 
(Least Recently Used) eviction policies. Provides thread-safe operations and
integration with WebSocket streaming and REST API fallback.

Features:
- TTL-based expiration for cache entries
- LRU eviction when cache reaches capacity
- Thread-safe operations with async locks
- Configurable cache size and TTL values
- Statistics and monitoring capabilities
- Cache invalidation and refresh mechanisms
"""

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from decimal import Decimal
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Union

from ..utils.decimal_precision_fix import safe_decimal

logger = logging.getLogger(__name__)


@dataclass
class BalanceCacheEntry:
    """Individual cache entry with metadata"""
    asset: str
    balance: Decimal
    hold_trade: Decimal
    free_balance: Decimal
    timestamp: float
    source: str  # 'websocket', 'rest_api', 'manual'
    ttl_seconds: float = 300.0  # 5 minutes default TTL
    access_count: int = 0
    last_access: float = field(default_factory=time.time)

    def __post_init__(self):
        """Ensure decimal types and calculate free balance"""
        self.balance = safe_decimal(self.balance)
        self.hold_trade = safe_decimal(self.hold_trade)
        self.free_balance = self.balance - self.hold_trade

        if self.timestamp == 0:
            self.timestamp = time.time()

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.timestamp > self.ttl_seconds

    def access(self):
        """Record access to this entry"""
        self.access_count += 1
        self.last_access = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'asset': self.asset,
            'balance': float(self.balance),
            'hold_trade': float(self.hold_trade),
            'free': float(self.free_balance),
            'timestamp': self.timestamp,
            'source': self.source,
            'ttl_seconds': self.ttl_seconds,
            'access_count': self.access_count,
            'last_access': self.last_access,
            'expired': self.is_expired(),
            'age_seconds': time.time() - self.timestamp
        }


class BalanceCache:
    """
    Thread-safe balance cache with TTL and LRU eviction
    """

    def __init__(self,
                 max_size: int = 1000,
                 default_ttl: float = 300.0,  # 5 minutes
                 cleanup_interval: float = 60.0):  # 1 minute
        """
        Initialize balance cache
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default TTL for cache entries in seconds
            cleanup_interval: How often to run cleanup in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        # Thread-safe cache storage using OrderedDict for LRU
        self._cache: OrderedDict[str, BalanceCacheEntry] = OrderedDict()
        self._lock = RLock()

        # Async lock for async operations
        self._async_lock = asyncio.Lock()

        # Statistics
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_evictions': 0,
            'cache_expirations': 0,
            'cache_invalidations': 0,
            'total_accesses': 0,
            'cleanup_runs': 0
        }

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Callbacks for cache events
        self._callbacks: Dict[str, List[Callable]] = {
            'hit': [],
            'miss': [],
            'eviction': [],
            'expiration': [],
            'invalidation': [],
            'update': []
        }

        logger.info(f"[BALANCE_CACHE] Initialized with max_size={max_size}, ttl={default_ttl}s")

    async def start(self):
        """Start the cache and cleanup task"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("[BALANCE_CACHE] Cache started with cleanup task")

    async def stop(self):
        """Stop the cache and cleanup task"""
        if not self._running:
            return

        self._running = False

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        await self.clear()
        logger.info("[BALANCE_CACHE] Cache stopped")

    async def get(self, asset: str) -> Optional[BalanceCacheEntry]:
        """
        Get balance entry from cache
        
        Args:
            asset: Asset symbol to retrieve
            
        Returns:
            Cache entry if found and not expired, None otherwise
        """
        async with self._async_lock:
            with self._lock:
                self._stats['total_accesses'] += 1

                entry = self._cache.get(asset)

                if entry is None:
                    self._stats['cache_misses'] += 1
                    await self._call_callbacks('miss', asset)
                    return None

                # Check if expired
                if entry.is_expired():
                    self._stats['cache_expirations'] += 1
                    del self._cache[asset]
                    await self._call_callbacks('expiration', entry)
                    return None

                # Update access info and move to end (LRU)
                entry.access()
                self._cache.move_to_end(asset)

                self._stats['cache_hits'] += 1
                await self._call_callbacks('hit', entry)

                return entry

    async def put(self,
                  asset: str,
                  balance: Union[Decimal, float, str],
                  hold_trade: Union[Decimal, float, str] = 0,
                  source: str = 'unknown',
                  ttl_seconds: Optional[float] = None) -> BalanceCacheEntry:
        """
        Put balance entry into cache
        
        Args:
            asset: Asset symbol
            balance: Total balance
            hold_trade: Amount held in trades
            source: Source of balance data
            ttl_seconds: TTL for this entry (uses default if None)
            
        Returns:
            The created cache entry
        """
        async with self._async_lock:
            with self._lock:
                # Create new entry
                entry = BalanceCacheEntry(
                    asset=asset,
                    balance=safe_decimal(balance),
                    hold_trade=safe_decimal(hold_trade),
                    free_balance=safe_decimal(balance) - safe_decimal(hold_trade),
                    timestamp=time.time(),
                    source=source,
                    ttl_seconds=ttl_seconds or self.default_ttl
                )

                # Check if we need to evict entries to make room
                while len(self._cache) >= self.max_size:
                    # Remove oldest entry (LRU)
                    oldest_asset, oldest_entry = self._cache.popitem(last=False)
                    self._stats['cache_evictions'] += 1
                    await self._call_callbacks('eviction', oldest_entry)
                    logger.debug(f"[BALANCE_CACHE] Evicted {oldest_asset} (LRU)")

                # Add or update entry
                old_entry = self._cache.get(asset)
                self._cache[asset] = entry

                # Move to end (most recently used)
                self._cache.move_to_end(asset)

                await self._call_callbacks('update', entry)

                if old_entry:
                    logger.debug(f"[BALANCE_CACHE] Updated {asset}: {old_entry.balance} -> {entry.balance}")
                else:
                    logger.debug(f"[BALANCE_CACHE] Added {asset}: {entry.balance}")

                return entry

    async def invalidate(self, asset: str) -> bool:
        """
        Invalidate (remove) cache entry
        
        Args:
            asset: Asset symbol to invalidate
            
        Returns:
            True if entry was removed, False if not found
        """
        async with self._async_lock:
            with self._lock:
                entry = self._cache.pop(asset, None)

                if entry:
                    self._stats['cache_invalidations'] += 1
                    await self._call_callbacks('invalidation', entry)
                    logger.debug(f"[BALANCE_CACHE] Invalidated {asset}")
                    return True

                return False

    async def clear(self):
        """Clear all cache entries"""
        async with self._async_lock:
            with self._lock:
                count = len(self._cache)
                self._cache.clear()
                self._stats['cache_invalidations'] += count
                logger.info(f"[BALANCE_CACHE] Cleared {count} entries")

    def get_all_sync(self) -> Dict[str, BalanceCacheEntry]:
        """
        Get all cache entries (synchronous)
        
        Returns:
            Dictionary of all non-expired cache entries
        """
        with self._lock:
            current_time = time.time()
            valid_entries = {}
            expired_assets = []

            for asset, entry in self._cache.items():
                if entry.is_expired():
                    expired_assets.append(asset)
                else:
                    entry.access()
                    valid_entries[asset] = entry

            # Remove expired entries
            for asset in expired_assets:
                del self._cache[asset]
                self._stats['cache_expirations'] += 1

            return valid_entries

    async def get_all(self) -> Dict[str, BalanceCacheEntry]:
        """
        Get all cache entries (async)
        
        Returns:
            Dictionary of all non-expired cache entries
        """
        async with self._async_lock:
            return self.get_all_sync()

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['cache_hits'] + self._stats['cache_misses']
            hit_rate = (self._stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0.0

            return {
                'cache_size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate_percent': hit_rate,
                'statistics': dict(self._stats),
                'oldest_entry_age': self._get_oldest_entry_age(),
                'memory_usage_estimate': self._estimate_memory_usage()
            }

    def _get_oldest_entry_age(self) -> Optional[float]:
        """Get age of oldest cache entry"""
        with self._lock:
            if not self._cache:
                return None

            oldest_entry = next(iter(self._cache.values()))
            return time.time() - oldest_entry.timestamp

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes"""
        with self._lock:
            # Rough estimate: each entry ~500 bytes
            return len(self._cache) * 500

    async def _cleanup_loop(self):
        """Background cleanup task to remove expired entries"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)

                if not self._running:
                    break

                await self._cleanup_expired()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[BALANCE_CACHE] Cleanup error: {e}")
                await asyncio.sleep(5)  # Wait before retry

    async def _cleanup_expired(self):
        """Remove expired cache entries"""
        async with self._async_lock:
            with self._lock:
                current_time = time.time()
                expired_assets = []

                for asset, entry in self._cache.items():
                    if entry.is_expired():
                        expired_assets.append(asset)

                for asset in expired_assets:
                    entry = self._cache.pop(asset)
                    self._stats['cache_expirations'] += 1
                    await self._call_callbacks('expiration', entry)

                if expired_assets:
                    logger.debug(f"[BALANCE_CACHE] Cleaned up {len(expired_assets)} expired entries")

                self._stats['cleanup_runs'] += 1

    def register_callback(self, event_type: str, callback: Callable):
        """
        Register callback for cache events
        
        Args:
            event_type: Type of event ('hit', 'miss', 'eviction', 'expiration', 'invalidation', 'update')
            callback: Async callback function
        """
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
            logger.debug(f"[BALANCE_CACHE] Registered callback for {event_type}")
        else:
            logger.warning(f"[BALANCE_CACHE] Unknown event type: {event_type}")

    def unregister_callback(self, event_type: str, callback: Callable):
        """Remove callback for event type"""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)
            logger.debug(f"[BALANCE_CACHE] Unregistered callback for {event_type}")

    async def _call_callbacks(self, event_type: str, data: Any):
        """Call registered callbacks for event type"""
        callbacks = self._callbacks.get(event_type, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"[BALANCE_CACHE] Callback error for {event_type}: {e}")

    # Context manager support
    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
