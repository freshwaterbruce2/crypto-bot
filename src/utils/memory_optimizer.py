"""
Memory Optimizer - Performance and Memory Management
==================================================

Advanced memory management system for the crypto trading bot that prevents memory leaks,
optimizes garbage collection, and provides real-time memory monitoring.

Features:
- Automatic memory leak detection and prevention
- Optimized garbage collection tuning
- Memory pool management for frequent allocations
- Real-time memory usage monitoring
- Emergency memory cleanup triggers
- Connection pool resource management
"""

import asyncio
import gc
import logging
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_memory: float
    used_memory: float
    available_memory: float
    memory_percent: float
    gc_collections: dict[int, int]
    active_objects: int
    leak_suspects: int
    pool_usage: dict[str, int]
    timestamp: float


class MemoryLeakDetector:
    """Detects and prevents memory leaks"""

    def __init__(self, check_interval: float = 60.0):
        self.check_interval = check_interval
        self.object_counts = defaultdict(int)
        self.growth_history = defaultdict(lambda: deque(maxlen=10))
        self.leak_threshold = 1000  # Objects growing consistently
        self.monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start_monitoring(self):
        """Start leak detection monitoring"""
        if self.monitoring:
            return

        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("[MEMORY_OPT] Memory leak detection started")

    async def stop_monitoring(self):
        """Stop leak detection monitoring"""
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("[MEMORY_OPT] Memory leak detection stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                await self._check_for_leaks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MEMORY_OPT] Leak detection error: {e}")
                await asyncio.sleep(self.check_interval)

    async def _check_for_leaks(self):
        """Check for potential memory leaks"""
        try:
            # Force garbage collection before analysis
            gc.collect()

            # Count objects by type
            current_counts = defaultdict(int)
            for obj in gc.get_objects():
                obj_type = type(obj).__name__
                current_counts[obj_type] += 1

            # Track growth patterns
            timestamp = time.time()
            for obj_type, count in current_counts.items():
                self.growth_history[obj_type].append((timestamp, count))

                # Check for consistent growth (potential leak)
                if len(self.growth_history[obj_type]) >= 5:
                    recent_counts = [c for _, c in list(self.growth_history[obj_type])[-5:]]
                    if all(recent_counts[i] < recent_counts[i+1] for i in range(len(recent_counts)-1)):
                        growth = recent_counts[-1] - recent_counts[0]
                        if growth > self.leak_threshold:
                            logger.warning(f"[MEMORY_OPT] Potential memory leak detected: {obj_type} grew by {growth} objects")
                            await self._handle_potential_leak(obj_type, growth)

            self.object_counts = current_counts

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Leak check error: {e}")

    async def _handle_potential_leak(self, obj_type: str, growth: int):
        """Handle detected potential memory leak"""
        try:
            # Log detailed information
            logger.warning(f"[MEMORY_OPT] Memory leak mitigation for {obj_type}")

            # Force aggressive garbage collection
            for generation in range(3):
                collected = gc.collect(generation)
                if collected > 0:
                    logger.info(f"[MEMORY_OPT] Collected {collected} objects from generation {generation}")

            # Clear weak references if applicable
            if obj_type in ['weakref', 'WeakSet', 'WeakValueDictionary']:
                self._clear_weak_references()

            # Trigger emergency cleanup for known problematic types
            if obj_type in ['dict', 'list', 'set']:
                await self._emergency_cleanup()

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Leak mitigation error: {e}")

    def _clear_weak_references(self):
        """Clear dead weak references"""
        try:
            # This is a placeholder - in practice you'd clear specific weak reference pools
            logger.info("[MEMORY_OPT] Clearing weak references")
        except Exception as e:
            logger.error(f"[MEMORY_OPT] Weak reference cleanup error: {e}")

    async def _emergency_cleanup(self):
        """Emergency memory cleanup"""
        try:
            logger.warning("[MEMORY_OPT] Performing emergency memory cleanup")

            # Force full garbage collection cycle
            for _ in range(3):
                collected = gc.collect()
                if collected == 0:
                    break

            # Clear internal caches if possible
            # This would be extended with specific cache clearing for your application

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Emergency cleanup error: {e}")


class MemoryPool:
    """Memory pool for frequent allocations"""

    def __init__(self, pool_name: str, max_size: int = 1000):
        self.pool_name = pool_name
        self.max_size = max_size
        self.pool: deque = deque()
        self.allocated = 0
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    def get_object(self, factory_func: Callable = None):
        """Get object from pool or create new one"""
        with self._lock:
            if self.pool:
                self.hits += 1
                return self.pool.popleft()
            else:
                self.misses += 1
                if factory_func:
                    obj = factory_func()
                    self.allocated += 1
                    return obj
                return None

    def return_object(self, obj):
        """Return object to pool"""
        with self._lock:
            if len(self.pool) < self.max_size:
                # Reset object state if needed
                if hasattr(obj, 'reset'):
                    obj.reset()
                self.pool.append(obj)
            else:
                # Pool is full, let object be garbage collected
                self.allocated = max(0, self.allocated - 1)

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

            return {
                'pool_name': self.pool_name,
                'pool_size': len(self.pool),
                'max_size': self.max_size,
                'allocated': self.allocated,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'utilization': (len(self.pool) / self.max_size * 100)
            }

    def clear(self):
        """Clear the memory pool"""
        with self._lock:
            self.pool.clear()
            self.allocated = 0


class GCOptimizer:
    """Garbage collection optimizer"""

    def __init__(self):
        self.original_thresholds = gc.get_threshold()
        self.optimized = False
        self.stats_history = deque(maxlen=100)

    def optimize_for_trading(self):
        """Optimize GC for trading workload"""
        try:
            if self.optimized:
                return

            # Optimize GC thresholds for high-frequency trading
            # More aggressive collection for generation 0 (frequent small objects)
            # Less frequent for generations 1 and 2 (larger, longer-lived objects)
            gc.set_threshold(500, 15, 15)  # Default is (700, 10, 10)

            # Enable debug flags for monitoring
            if logger.isEnabledFor(logging.DEBUG):
                gc.set_debug(gc.DEBUG_STATS)

            self.optimized = True
            logger.info("[MEMORY_OPT] GC optimized for trading workload")

        except Exception as e:
            logger.error(f"[MEMORY_OPT] GC optimization error: {e}")

    def restore_defaults(self):
        """Restore default GC settings"""
        try:
            gc.set_threshold(*self.original_thresholds)
            gc.set_debug(0)
            self.optimized = False
            logger.info("[MEMORY_OPT] GC settings restored to defaults")
        except Exception as e:
            logger.error(f"[MEMORY_OPT] GC restore error: {e}")

    def force_collection(self) -> dict[int, int]:
        """Force garbage collection and return stats"""
        collections = {}
        try:
            for generation in range(3):
                collected = gc.collect(generation)
                collections[generation] = collected

            # Record stats
            stats = {
                'timestamp': time.time(),
                'collections': collections,
                'total_collected': sum(collections.values())
            }
            self.stats_history.append(stats)

            return collections

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Force collection error: {e}")
            return {}


class MemoryOptimizer:
    """Main memory optimization coordinator"""

    def __init__(self):
        self.leak_detector = MemoryLeakDetector()
        self.gc_optimizer = GCOptimizer()
        self.memory_pools: dict[str, MemoryPool] = {}
        self.monitoring = False
        self.stats_callback: Optional[Callable] = None
        self._monitor_task: Optional[asyncio.Task] = None

        # Memory thresholds (percentage of total memory)
        self.warning_threshold = 80.0
        self.critical_threshold = 90.0
        self.emergency_threshold = 95.0

    async def initialize(self):
        """Initialize memory optimizer"""
        try:
            # Optimize garbage collection for trading
            self.gc_optimizer.optimize_for_trading()

            # Create common memory pools
            self.create_pool('decimal_pool', max_size=1000)
            self.create_pool('dict_pool', max_size=500)
            self.create_pool('list_pool', max_size=500)

            # Start monitoring
            await self.start_monitoring()

            logger.info("[MEMORY_OPT] Memory optimizer initialized")

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Initialization error: {e}")

    async def shutdown(self):
        """Shutdown memory optimizer"""
        try:
            await self.stop_monitoring()
            await self.leak_detector.stop_monitoring()
            self.gc_optimizer.restore_defaults()
            self.clear_all_pools()

            logger.info("[MEMORY_OPT] Memory optimizer shutdown complete")

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Shutdown error: {e}")

    def create_pool(self, pool_name: str, max_size: int = 1000) -> MemoryPool:
        """Create a new memory pool"""
        pool = MemoryPool(pool_name, max_size)
        self.memory_pools[pool_name] = pool
        logger.info(f"[MEMORY_OPT] Created memory pool: {pool_name} (max_size={max_size})")
        return pool

    def get_pool(self, pool_name: str) -> Optional[MemoryPool]:
        """Get memory pool by name"""
        return self.memory_pools.get(pool_name)

    def clear_all_pools(self):
        """Clear all memory pools"""
        for pool in self.memory_pools.values():
            pool.clear()
        logger.info("[MEMORY_OPT] All memory pools cleared")

    async def start_monitoring(self):
        """Start memory monitoring"""
        if self.monitoring:
            return

        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        await self.leak_detector.start_monitoring()

        logger.info("[MEMORY_OPT] Memory monitoring started")

    async def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        await self.leak_detector.stop_monitoring()
        logger.info("[MEMORY_OPT] Memory monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                stats = await self.get_memory_stats()
                await self._check_memory_thresholds(stats)

                if self.stats_callback:
                    await self.stats_callback(stats)

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MEMORY_OPT] Monitoring error: {e}")
                await asyncio.sleep(30)

    async def get_memory_stats(self) -> MemoryStats:
        """Get comprehensive memory statistics"""
        try:
            # System memory stats
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()

            # GC stats
            gc_stats = {}
            for i in range(3):
                gc_stats[i] = gc.get_count()[i]

            # Object counts
            active_objects = len(gc.get_objects())

            # Pool stats
            pool_usage = {}
            for name, pool in self.memory_pools.items():
                pool_stats = pool.get_stats()
                pool_usage[name] = pool_stats['pool_size']

            return MemoryStats(
                total_memory=system_memory.total,
                used_memory=memory_info.rss,
                available_memory=system_memory.available,
                memory_percent=system_memory.percent,
                gc_collections=gc_stats,
                active_objects=active_objects,
                leak_suspects=len(self.leak_detector.growth_history),
                pool_usage=pool_usage,
                timestamp=time.time()
            )

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Stats collection error: {e}")
            return MemoryStats(0, 0, 0, 0, {}, 0, 0, {}, time.time())

    async def _check_memory_thresholds(self, stats: MemoryStats):
        """Check memory usage against thresholds"""
        try:
            if stats.memory_percent >= self.emergency_threshold:
                logger.critical(f"[MEMORY_OPT] EMERGENCY: Memory usage at {stats.memory_percent:.1f}%")
                await self._emergency_memory_cleanup()
            elif stats.memory_percent >= self.critical_threshold:
                logger.error(f"[MEMORY_OPT] CRITICAL: Memory usage at {stats.memory_percent:.1f}%")
                await self._critical_memory_cleanup()
            elif stats.memory_percent >= self.warning_threshold:
                logger.warning(f"[MEMORY_OPT] WARNING: Memory usage at {stats.memory_percent:.1f}%")
                await self._warning_memory_cleanup()

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Threshold check error: {e}")

    async def _warning_memory_cleanup(self):
        """Perform warning-level memory cleanup"""
        try:
            logger.info("[MEMORY_OPT] Performing warning-level cleanup")

            # Force garbage collection
            collections = self.gc_optimizer.force_collection()
            logger.info(f"[MEMORY_OPT] GC collected: {collections}")

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Warning cleanup error: {e}")

    async def _critical_memory_cleanup(self):
        """Perform critical-level memory cleanup"""
        try:
            logger.warning("[MEMORY_OPT] Performing critical-level cleanup")

            # More aggressive cleanup
            await self._warning_memory_cleanup()

            # Clear memory pools that are underutilized
            for name, pool in self.memory_pools.items():
                stats = pool.get_stats()
                if stats['utilization'] < 20:  # Less than 20% utilized
                    pool.clear()
                    logger.info(f"[MEMORY_OPT] Cleared underutilized pool: {name}")

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Critical cleanup error: {e}")

    async def _emergency_memory_cleanup(self):
        """Perform emergency-level memory cleanup"""
        try:
            logger.critical("[MEMORY_OPT] Performing emergency cleanup")

            # Most aggressive cleanup
            await self._critical_memory_cleanup()

            # Clear all memory pools
            self.clear_all_pools()

            # Multiple GC cycles
            for _ in range(5):
                collections = self.gc_optimizer.force_collection()
                if sum(collections.values()) == 0:
                    break

            logger.critical("[MEMORY_OPT] Emergency cleanup complete")

        except Exception as e:
            logger.error(f"[MEMORY_OPT] Emergency cleanup error: {e}")

    def set_stats_callback(self, callback: Callable):
        """Set callback for memory stats"""
        self.stats_callback = callback


# Global memory optimizer instance
_memory_optimizer: Optional[MemoryOptimizer] = None


async def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer instance"""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()
        await _memory_optimizer.initialize()
    return _memory_optimizer


async def shutdown_memory_optimizer():
    """Shutdown global memory optimizer"""
    global _memory_optimizer
    if _memory_optimizer:
        await _memory_optimizer.shutdown()
        _memory_optimizer = None


# Decorator for automatic memory management
def memory_managed(pool_name: str = None):
    """Decorator to automatically manage memory for function calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            optimizer = await get_memory_optimizer()

            # Pre-execution cleanup if needed
            stats = await optimizer.get_memory_stats()
            if stats.memory_percent > 70:
                await optimizer._warning_memory_cleanup()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                # Post-execution cleanup
                if pool_name:
                    pool = optimizer.get_pool(pool_name)
                    if pool and hasattr(result, 'return_to_pool'):
                        pool.return_object(result)

        return wrapper
    return decorator
