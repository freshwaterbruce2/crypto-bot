"""
Bounded Cache System for Memory-Safe Trading Operations
======================================================

High-performance caching with automatic memory management to prevent
memory leaks in long-running trading bots.
"""

import time
import threading
import weakref
from typing import Dict, Any, Optional, Callable, Generic, TypeVar, Tuple
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

K = TypeVar('K')  # Key type
V = TypeVar('V')  # Value type


class EvictionPolicy(Enum):
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    SIZE = "size"  # Size-based eviction


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    size_bytes: int = 0
    
    def is_expired(self, ttl: float) -> bool:
        """Check if entry has expired"""
        return time.time() - self.created_at > ttl


class BoundedCache(Generic[K, V]):
    """High-performance bounded cache with multiple eviction policies"""
    
    def __init__(self, 
                 max_size: int = 1000,
                 ttl: float = 3600.0,  # 1 hour default TTL
                 eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
                 max_memory_mb: float = 100.0,
                 cleanup_interval: float = 300.0):  # 5 minutes
        
        self.max_size = max_size
        self.ttl = ttl
        self.eviction_policy = eviction_policy
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.cleanup_interval = cleanup_interval
        
        self._cache: OrderedDict[K, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._total_memory = 0
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expired_entries = 0
        
        # Background cleanup
        self._cleanup_timer: Optional[threading.Timer] = None
        self._start_cleanup_timer()
        
        logger.info(f"[CACHE] Initialized bounded cache: max_size={max_size}, "
                   f"ttl={ttl}s, policy={eviction_policy.value}, "
                   f"max_memory={max_memory_mb}MB")
    
    def get(self, key: K, default: V = None) -> Optional[V]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return default
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired(self.ttl):
                del self._cache[key]
                self._total_memory -= entry.size_bytes
                self.expired_entries += 1
                self.misses += 1
                return default
            
            # Update access metadata
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            # Move to end for LRU
            if self.eviction_policy == EvictionPolicy.LRU:
                self._cache.move_to_end(key)
            
            self.hits += 1
            return entry.value
    
    def put(self, key: K, value: V, size_hint: int = None) -> bool:
        """Put value in cache with optional size hint"""
        with self._lock:
            current_time = time.time()
            
            # Estimate size if not provided
            if size_hint is None:
                size_hint = self._estimate_size(value)
            
            # Check if single item exceeds memory limit
            if size_hint > self.max_memory_bytes:
                logger.warning(f"[CACHE] Item too large for cache: {size_hint} bytes")
                return False
            
            # Remove existing entry if updating
            if key in self._cache:
                old_entry = self._cache[key]
                self._total_memory -= old_entry.size_bytes
            
            # Create new entry
            entry = CacheEntry(
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                access_count=1,
                size_bytes=size_hint
            )
            
            # Ensure we have space
            while (len(self._cache) >= self.max_size or 
                   self._total_memory + size_hint > self.max_memory_bytes):
                if not self._evict_one():
                    logger.warning("[CACHE] Failed to evict entry for new item")
                    return False
            
            # Add new entry
            self._cache[key] = entry
            self._total_memory += size_hint
            
            return True
    
    def _evict_one(self) -> bool:
        """Evict one entry based on policy"""
        if not self._cache:
            return False
        
        key_to_evict = None
        
        if self.eviction_policy == EvictionPolicy.LRU:
            # First item is least recently used
            key_to_evict = next(iter(self._cache))
            
        elif self.eviction_policy == EvictionPolicy.LFU:
            # Find least frequently used
            min_access_count = float('inf')
            for k, entry in self._cache.items():
                if entry.access_count < min_access_count:
                    min_access_count = entry.access_count
                    key_to_evict = k
                    
        elif self.eviction_policy == EvictionPolicy.TTL:
            # Find oldest entry
            oldest_time = float('inf')
            for k, entry in self._cache.items():
                if entry.created_at < oldest_time:
                    oldest_time = entry.created_at
                    key_to_evict = k
                    
        elif self.eviction_policy == EvictionPolicy.SIZE:
            # Find largest entry
            max_size = 0
            for k, entry in self._cache.items():
                if entry.size_bytes > max_size:
                    max_size = entry.size_bytes
                    key_to_evict = k
        
        if key_to_evict is not None:
            entry = self._cache[key_to_evict]
            del self._cache[key_to_evict]
            self._total_memory -= entry.size_bytes
            self.evictions += 1
            return True
        
        return False
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value"""
        try:
            import sys
            return sys.getsizeof(value)
        except:
            # Fallback estimation
            if isinstance(value, str):
                return len(value) * 2  # Unicode characters
            elif isinstance(value, (list, tuple)):
                return len(value) * 64  # Rough estimate
            elif isinstance(value, dict):
                return len(value) * 128  # Rough estimate
            else:
                return 64  # Default estimate
    
    def remove(self, key: K) -> bool:
        """Remove entry from cache"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                self._total_memory -= entry.size_bytes
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._total_memory = 0
            logger.info("[CACHE] Cache cleared")
    
    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        with self._lock:
            expired_keys = []
            current_time = time.time()
            
            for key, entry in self._cache.items():
                if entry.is_expired(self.ttl):
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self._cache[key]
                del self._cache[key]
                self._total_memory -= entry.size_bytes
            
            self.expired_entries += len(expired_keys)
            
            if expired_keys:
                logger.debug(f"[CACHE] Cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def _start_cleanup_timer(self):
        """Start background cleanup timer"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
        
        self._cleanup_timer = threading.Timer(self.cleanup_interval, self._cleanup_and_reschedule)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()
    
    def _cleanup_and_reschedule(self):
        """Cleanup and reschedule timer"""
        try:
            self.cleanup_expired()
        except Exception as e:
            logger.error(f"[CACHE] Cleanup error: {e}")
        finally:
            self._start_cleanup_timer()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "memory_usage_mb": self._total_memory / (1024 * 1024),
                "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
                "memory_utilization": (self._total_memory / self.max_memory_bytes * 100) if self.max_memory_bytes > 0 else 0,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "evictions": self.evictions,
                "expired_entries": self.expired_entries,
                "eviction_policy": self.eviction_policy.value
            }
    
    def resize(self, new_max_size: int, new_max_memory_mb: float = None):
        """Resize cache limits"""
        with self._lock:
            self.max_size = new_max_size
            
            if new_max_memory_mb is not None:
                self.max_memory_bytes = int(new_max_memory_mb * 1024 * 1024)
            
            # Evict entries if over new limits
            while (len(self._cache) > self.max_size or 
                   self._total_memory > self.max_memory_bytes):
                if not self._evict_one():
                    break
            
            logger.info(f"[CACHE] Resized to max_size={new_max_size}, "
                       f"max_memory={self.max_memory_bytes / (1024*1024):.1f}MB")
    
    def close(self):
        """Close cache and cleanup resources"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
            self._cleanup_timer = None
        
        with self._lock:
            self._cache.clear()
            self._total_memory = 0
        
        logger.info("[CACHE] Cache closed")


class TradingDataCache:
    """Specialized cache for trading data"""
    
    def __init__(self):
        # Different caches for different data types with appropriate settings
        self.price_cache = BoundedCache[str, float](
            max_size=1000, 
            ttl=30.0,  # 30 seconds for price data
            eviction_policy=EvictionPolicy.LRU,
            max_memory_mb=10.0
        )
        
        self.balance_cache = BoundedCache[str, Dict[str, Any]](
            max_size=100,
            ttl=60.0,  # 1 minute for balance data
            eviction_policy=EvictionPolicy.LRU,
            max_memory_mb=5.0
        )
        
        self.signal_cache = BoundedCache[str, Dict[str, Any]](
            max_size=500,
            ttl=300.0,  # 5 minutes for signals
            eviction_policy=EvictionPolicy.LFU,
            max_memory_mb=20.0
        )
        
        self.calculation_cache = BoundedCache[str, Any](
            max_size=2000,
            ttl=3600.0,  # 1 hour for calculations
            eviction_policy=EvictionPolicy.LRU,
            max_memory_mb=50.0
        )
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get cached price"""
        return self.price_cache.get(symbol)
    
    def cache_price(self, symbol: str, price: float):
        """Cache price data"""
        self.price_cache.put(symbol, price)
    
    def get_balance(self, asset: str) -> Optional[Dict[str, Any]]:
        """Get cached balance"""
        return self.balance_cache.get(asset)
    
    def cache_balance(self, asset: str, balance_data: Dict[str, Any]):
        """Cache balance data"""
        self.balance_cache.put(asset, balance_data)
    
    def get_signal(self, signal_key: str) -> Optional[Dict[str, Any]]:
        """Get cached signal"""
        return self.signal_cache.get(signal_key)
    
    def cache_signal(self, signal_key: str, signal_data: Dict[str, Any]):
        """Cache signal data"""
        self.signal_cache.put(signal_key, signal_data)
    
    def get_calculation(self, calc_key: str) -> Optional[Any]:
        """Get cached calculation"""
        return self.calculation_cache.get(calc_key)
    
    def cache_calculation(self, calc_key: str, result: Any):
        """Cache calculation result"""
        self.calculation_cache.put(calc_key, result)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches"""
        return {
            "price_cache": self.price_cache.get_stats(),
            "balance_cache": self.balance_cache.get_stats(),
            "signal_cache": self.signal_cache.get_stats(),
            "calculation_cache": self.calculation_cache.get_stats()
        }
    
    def close_all(self):
        """Close all caches"""
        self.price_cache.close()
        self.balance_cache.close()
        self.signal_cache.close()
        self.calculation_cache.close()


# Global trading cache instance
_global_trading_cache: Optional[TradingDataCache] = None

def get_trading_cache() -> TradingDataCache:
    """Get or create global trading cache"""
    global _global_trading_cache
    if _global_trading_cache is None:
        _global_trading_cache = TradingDataCache()
    return _global_trading_cache