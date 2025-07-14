"""
High-Frequency Trading Memory Optimizer
=====================================

Memory optimizations for HFT trading bot:
- Efficient data structures with bounded memory usage
- Object pooling for frequent allocations
- Cache optimization with LRU eviction
- Memory-mapped data structures for large datasets
- Garbage collection optimization
"""

import gc
import time
import weakref
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from collections import deque, OrderedDict
from dataclasses import dataclass, field
from threading import RLock
import sys
import tracemalloc

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_allocated: int = 0
    peak_memory: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    object_pool_hits: int = 0
    object_pool_misses: int = 0
    gc_collections: int = 0
    last_gc_time: float = 0.0

class BoundedCache:
    """Memory-bounded LRU cache optimized for HFT"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 50):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = OrderedDict()
        self.memory_usage = 0
        self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        self._lock = RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache with LRU update"""
        with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.stats['hits'] += 1
                return value
            
            self.stats['misses'] += 1
            return None
    
    def put(self, key: str, value: Any, estimated_size: int = None) -> bool:
        """Put item in cache with memory management"""
        with self._lock:
            # Estimate size if not provided
            if estimated_size is None:
                estimated_size = sys.getsizeof(value)
            
            # Check if we can fit this item
            if estimated_size > self.max_memory_bytes:
                return False  # Too large for cache
            
            # Remove existing item if updating
            if key in self.cache:
                old_size = getattr(self.cache[key], '_cache_size', sys.getsizeof(self.cache[key]))
                self.memory_usage -= old_size
                del self.cache[key]
            
            # Evict items if necessary
            while (len(self.cache) >= self.max_size or 
                   self.memory_usage + estimated_size > self.max_memory_bytes):
                if not self.cache:
                    break
                
                oldest_key, oldest_value = self.cache.popitem(last=False)
                old_size = getattr(oldest_value, '_cache_size', sys.getsizeof(oldest_value))
                self.memory_usage -= old_size
                self.stats['evictions'] += 1
            
            # Add new item
            self.cache[key] = value
            setattr(value, '_cache_size', estimated_size)
            self.memory_usage += estimated_size
            return True
    
    def clear(self):
        """Clear cache and reset memory usage"""
        with self._lock:
            self.cache.clear()
            self.memory_usage = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            hit_rate = self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0
            return {
                'size': len(self.cache),
                'memory_usage_mb': self.memory_usage / (1024 * 1024),
                'max_size': self.max_size,
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'hit_rate': hit_rate,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'evictions': self.stats['evictions']
            }

class ObjectPool:
    """Object pool for frequent allocations"""
    
    def __init__(self, factory_func, max_size: int = 100):
        self.factory_func = factory_func
        self.max_size = max_size
        self.pool = deque()
        self.stats = {'created': 0, 'reused': 0, 'returned': 0}
        self._lock = RLock()
    
    def get(self):
        """Get object from pool or create new one"""
        with self._lock:
            if self.pool:
                obj = self.pool.popleft()
                self.stats['reused'] += 1
                return obj
            else:
                obj = self.factory_func()
                self.stats['created'] += 1
                return obj
    
    def return_object(self, obj):
        """Return object to pool"""
        with self._lock:
            if len(self.pool) < self.max_size:
                # Reset object state if it has a reset method
                if hasattr(obj, 'reset'):
                    obj.reset()
                self.pool.append(obj)
                self.stats['returned'] += 1
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            reuse_rate = self.stats['reused'] / (self.stats['created'] + self.stats['reused']) if (self.stats['created'] + self.stats['reused']) > 0 else 0
            return {
                'pool_size': len(self.pool),
                'max_size': self.max_size,
                'created': self.stats['created'],
                'reused': self.stats['reused'],
                'returned': self.stats['returned'],
                'reuse_rate': reuse_rate
            }

class CircularBuffer:
    """Memory-efficient circular buffer for time series data"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.buffer = [None] * max_size
        self.head = 0
        self.tail = 0
        self.size = 0
        self._lock = RLock()
    
    def append(self, item):
        """Add item to buffer"""
        with self._lock:
            self.buffer[self.tail] = item
            self.tail = (self.tail + 1) % self.max_size
            
            if self.size < self.max_size:
                self.size += 1
            else:
                # Buffer is full, move head
                self.head = (self.head + 1) % self.max_size
    
    def get_latest(self, count: int = 1) -> List[Any]:
        """Get latest N items"""
        with self._lock:
            if count > self.size:
                count = self.size
            
            items = []
            for i in range(count):
                index = (self.tail - 1 - i) % self.max_size
                if self.buffer[index] is not None:
                    items.append(self.buffer[index])
            
            return items
    
    def get_all(self) -> List[Any]:
        """Get all items in order"""
        with self._lock:
            items = []
            for i in range(self.size):
                index = (self.head + i) % self.max_size
                if self.buffer[index] is not None:
                    items.append(self.buffer[index])
            return items
    
    def clear(self):
        """Clear buffer"""
        with self._lock:
            self.buffer = [None] * self.max_size
            self.head = 0
            self.tail = 0
            self.size = 0

class HFTMemoryOptimizer:
    """Main memory optimizer for HFT trading"""
    
    def __init__(self):
        self.stats = MemoryStats()
        self.caches = {}
        self.object_pools = {}
        self.circular_buffers = {}
        
        # Memory monitoring
        self.monitoring_enabled = False
        self.memory_snapshots = deque(maxlen=100)
        self.gc_threshold_mb = 100  # Trigger GC at 100MB
        
        # Object pools for common objects
        self._init_object_pools()
        
        # Caches for frequent data
        self._init_caches()
        
        logger.info("[HFT_MEMORY] Memory optimizer initialized")
    
    def _init_object_pools(self):
        """Initialize object pools for common objects"""
        # Pool for price data dictionaries
        def create_price_dict():
            return {'symbol': '', 'price': 0.0, 'timestamp': 0.0, 'volume': 0.0}
        
        # Pool for trade signal dictionaries
        def create_signal_dict():
            return {
                'symbol': '', 'side': '', 'amount': 0.0, 'price': 0.0,
                'confidence': 0.0, 'timestamp': 0.0, 'signal_type': ''
            }
        
        # Pool for order dictionaries
        def create_order_dict():
            return {
                'id': '', 'symbol': '', 'side': '', 'amount': 0.0,
                'price': 0.0, 'status': '', 'timestamp': 0.0
            }
        
        self.object_pools['price_data'] = ObjectPool(create_price_dict, max_size=200)
        self.object_pools['signal_data'] = ObjectPool(create_signal_dict, max_size=100)
        self.object_pools['order_data'] = ObjectPool(create_order_dict, max_size=100)
    
    def _init_caches(self):
        """Initialize caches for frequent data"""
        # Cache for market data
        self.caches['market_data'] = BoundedCache(max_size=1000, max_memory_mb=30)
        
        # Cache for calculated indicators
        self.caches['indicators'] = BoundedCache(max_size=500, max_memory_mb=20)
        
        # Cache for symbol metadata
        self.caches['symbol_meta'] = BoundedCache(max_size=200, max_memory_mb=10)
        
        # Cache for rate limit data
        self.caches['rate_limits'] = BoundedCache(max_size=100, max_memory_mb=5)
    
    def get_price_data_object(self) -> Dict[str, Any]:
        """Get reusable price data object"""
        obj = self.object_pools['price_data'].get()
        self.stats.object_pool_hits += 1
        return obj
    
    def return_price_data_object(self, obj: Dict[str, Any]):
        """Return price data object to pool"""
        # Clear sensitive data
        for key in obj:
            if isinstance(obj[key], (int, float)):
                obj[key] = 0.0
            else:
                obj[key] = ''
        self.object_pools['price_data'].return_object(obj)
    
    def get_signal_data_object(self) -> Dict[str, Any]:
        """Get reusable signal data object"""
        obj = self.object_pools['signal_data'].get()
        self.stats.object_pool_hits += 1
        return obj
    
    def return_signal_data_object(self, obj: Dict[str, Any]):
        """Return signal data object to pool"""
        # Clear sensitive data
        for key in obj:
            if isinstance(obj[key], (int, float)):
                obj[key] = 0.0
            else:
                obj[key] = ''
        self.object_pools['signal_data'].return_object(obj)
    
    def cache_market_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """Cache market data with memory management"""
        key = f"market_{symbol}_{int(time.time())}"
        estimated_size = sys.getsizeof(data) + len(str(data))
        success = self.caches['market_data'].put(key, data, estimated_size)
        
        if success:
            self.stats.cache_hits += 1
        else:
            self.stats.cache_misses += 1
        
        return success
    
    def get_cached_market_data(self, symbol: str, max_age: float = 1.0) -> Optional[Dict[str, Any]]:
        """Get cached market data within age limit"""
        current_time = int(time.time())
        
        # Search recent entries
        for age in range(int(max_age) + 1):
            key = f"market_{symbol}_{current_time - age}"
            data = self.caches['market_data'].get(key)
            if data:
                return data
        
        return None
    
    def cache_indicator(self, symbol: str, indicator_name: str, value: float, period: int = 0):
        """Cache calculated indicator value"""
        key = f"ind_{symbol}_{indicator_name}_{period}_{int(time.time() / 5) * 5}"  # 5-second buckets
        self.caches['indicators'].put(key, value, sys.getsizeof(value))
    
    def get_cached_indicator(self, symbol: str, indicator_name: str, period: int = 0, max_age: float = 30.0) -> Optional[float]:
        """Get cached indicator value"""
        current_bucket = int(time.time() / 5) * 5
        
        # Search recent buckets
        for age_buckets in range(int(max_age / 5) + 1):
            bucket_time = current_bucket - (age_buckets * 5)
            key = f"ind_{symbol}_{indicator_name}_{period}_{bucket_time}"
            value = self.caches['indicators'].get(key)
            if value is not None:
                return value
        
        return None
    
    def create_circular_buffer(self, name: str, max_size: int) -> CircularBuffer:
        """Create or get circular buffer with validation"""
        try:
            # VALIDATION FIX: Validate parameters
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Buffer name must be a non-empty string")
            if not isinstance(max_size, int) or max_size <= 0 or max_size > 100000:
                raise ValueError(f"Invalid max_size: {max_size}. Must be positive integer <= 100000")
            
            name = name.strip()
            if name not in self.circular_buffers:
                self.circular_buffers[name] = CircularBuffer(max_size)
            return self.circular_buffers[name]
        except Exception as e:
            logger.error(f"[HFT_MEMORY] Error creating circular buffer '{name}': {e}")
            # Return a default small buffer to prevent crashes
            return CircularBuffer(100)
    
    def optimize_garbage_collection(self):
        """Optimize garbage collection for HFT with memory leak prevention"""
        try:
            # Get current memory usage
            if self.monitoring_enabled and tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                current_mb = current / (1024 * 1024)
                
                # MEMORY MANAGEMENT FIX: Force GC if memory usage is high
                if current_mb > self.gc_threshold_mb:
                    gc_start = time.time()
                    
                    # MEMORY MANAGEMENT FIX: Collect all generations
                    collected_0 = gc.collect(0)  # Collect generation 0
                    collected_1 = gc.collect(1)  # Collect generation 1
                    collected_2 = gc.collect(2)  # Collect generation 2
                    total_collected = collected_0 + collected_1 + collected_2
                    
                    gc_time = time.time() - gc_start
                    
                    self.stats.gc_collections += 1
                    self.stats.last_gc_time = gc_time
                    
                    logger.info(f"[HFT_MEMORY] GC collected {total_collected} objects in {gc_time*1000:.1f}ms")
                    
                    # Update stats
                    if self.monitoring_enabled:
                        new_current, _ = tracemalloc.get_traced_memory()
                        freed_mb = (current - new_current) / (1024 * 1024)
                        logger.info(f"[HFT_MEMORY] Freed {freed_mb:.1f}MB of memory")
                        
                        # MEMORY MANAGEMENT FIX: Check for memory leaks
                        if freed_mb < 0.1 and current_mb > self.gc_threshold_mb * 2:
                            logger.warning(f"[HFT_MEMORY] Potential memory leak detected - {current_mb:.1f}MB used, minimal freed")
            else:
                # Fallback GC without monitoring
                gc.collect()
                self.stats.gc_collections += 1
                
        except Exception as e:
            logger.error(f"[HFT_MEMORY] Error during garbage collection: {e}")
    
    def start_memory_monitoring(self):
        """Start memory monitoring"""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        self.monitoring_enabled = True
        logger.info("[HFT_MEMORY] Memory monitoring started")
    
    def stop_memory_monitoring(self):
        """Stop memory monitoring"""
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        self.monitoring_enabled = False
        logger.info("[HFT_MEMORY] Memory monitoring stopped")
    
    def take_memory_snapshot(self) -> Dict[str, Any]:
        """Take memory snapshot for analysis"""
        if not self.monitoring_enabled:
            return {}
        
        current, peak = tracemalloc.get_traced_memory()
        snapshot = {
            'timestamp': time.time(),
            'current_mb': current / (1024 * 1024),
            'peak_mb': peak / (1024 * 1024),
            'gc_collections': self.stats.gc_collections
        }
        
        self.memory_snapshots.append(snapshot)
        return snapshot
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        stats = {
            'optimizer_stats': {
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses,
                'object_pool_hits': self.stats.object_pool_hits,
                'object_pool_misses': self.stats.object_pool_misses,
                'gc_collections': self.stats.gc_collections,
                'last_gc_time_ms': self.stats.last_gc_time * 1000
            },
            'caches': {},
            'object_pools': {},
            'circular_buffers': {}
        }
        
        # Cache stats
        for name, cache in self.caches.items():
            stats['caches'][name] = cache.get_stats()
        
        # Object pool stats
        for name, pool in self.object_pools.items():
            stats['object_pools'][name] = pool.get_stats()
        
        # Circular buffer stats
        for name, buffer in self.circular_buffers.items():
            stats['circular_buffers'][name] = {
                'size': buffer.size,
                'max_size': buffer.max_size,
                'utilization': buffer.size / buffer.max_size if buffer.max_size > 0 else 0
            }
        
        # Memory monitoring stats
        if self.monitoring_enabled and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            stats['memory_monitoring'] = {
                'current_mb': current / (1024 * 1024),
                'peak_mb': peak / (1024 * 1024),
                'monitoring_enabled': True
            }
        else:
            stats['memory_monitoring'] = {'monitoring_enabled': False}
        
        return stats
    
    def clear_all_caches(self):
        """Clear all caches to free memory with error handling"""
        try:
            cleared_count = 0
            for name, cache in self.caches.items():
                try:
                    cache.clear()
                    cleared_count += 1
                except Exception as e:
                    logger.error(f"[HFT_MEMORY] Error clearing cache '{name}': {e}")
            
            logger.info(f"[HFT_MEMORY] {cleared_count}/{len(self.caches)} caches cleared")
            
            # MEMORY MANAGEMENT FIX: Force immediate garbage collection after cache clear
            gc.collect()
            
        except Exception as e:
            logger.error(f"[HFT_MEMORY] Error during cache clearing: {e}")
    
    def optimize_for_hft_burst(self):
        """Optimize memory for HFT burst mode"""
        # Clear old cached data
        self.clear_all_caches()
        
        # Force garbage collection
        self.optimize_garbage_collection()
        
        # Increase cache sizes for burst mode
        self.caches['market_data'].max_size = 2000
        self.caches['indicators'].max_size = 1000
        
        logger.info("[HFT_MEMORY] Optimized for HFT burst mode")
    
    def restore_normal_mode(self):
        """Restore normal memory settings"""
        # Restore normal cache sizes
        self.caches['market_data'].max_size = 1000
        self.caches['indicators'].max_size = 500
        
        # Clean up excess entries
        for cache in self.caches.values():
            while len(cache.cache) > cache.max_size:
                cache.cache.popitem(last=False)
        
        logger.info("[HFT_MEMORY] Restored normal memory mode")

# Global instance
hft_memory_optimizer = HFTMemoryOptimizer()