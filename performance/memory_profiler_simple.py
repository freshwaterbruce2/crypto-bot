"""
Simple Memory Usage Analysis
============================

Lightweight memory profiling for high-frequency trading bot.
Basic memory usage monitoring without external dependencies.

Memory Analysis Features:
- Basic memory usage monitoring
- Memory leak detection
- Garbage collection analysis
- Memory usage recommendations
"""

import asyncio
import gc
import logging
import os
import sys
import time
import tracemalloc
import weakref
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

import psutil

# Import trading bot components
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time"""
    timestamp: float
    rss_mb: float
    vms_mb: float
    percent: float
    available_mb: float
    gc_objects: int
    gc_generation_0: int
    gc_generation_1: int
    gc_generation_2: int
    tracemalloc_current: Optional[float] = None
    tracemalloc_peak: Optional[float] = None


@dataclass
class MemoryLeak:
    """Detected memory leak information"""
    detection_time: float
    object_type: str
    growth_rate_mb_per_minute: float
    severity: str
    description: str
    stack_trace: Optional[str] = None


@dataclass
class OptimizationRecommendation:
    """Memory optimization recommendation"""
    category: str
    priority: str
    issue: str
    recommendation: str
    expected_improvement: str
    implementation_difficulty: str


class AdvancedMemoryProfiler:
    """Simple memory profiler for trading bot"""

    def __init__(self, sampling_interval: float = 1.0):
        """Initialize memory profiler"""
        self.sampling_interval = sampling_interval
        self.is_profiling = False
        self.snapshots: list[MemorySnapshot] = []
        self.detected_leaks: list[MemoryLeak] = []
        self.recommendations: list[OptimizationRecommendation] = []

        # Memory tracking
        self.reference_tracker = weakref.WeakSet()
        self.allocation_tracker = {}

        # Performance monitoring
        self.process = psutil.Process()
        self.gc_stats = {'collections': 0, 'collected': 0, 'uncollectable': 0}

        # Profiling state
        self.start_time = 0
        self.baseline_memory = 0
        self.peak_memory = 0
        self.memory_growth_rate = 0

        logger.info("Simple Memory Profiler initialized")

    async def start_profiling(self, duration: Optional[float] = None):
        """Start memory profiling session"""
        if self.is_profiling:
            logger.warning("Profiling already in progress")
            return

        logger.info("Starting memory profiling session...")

        # Initialize tracking
        tracemalloc.start(10)  # Track top 10 stack frames
        gc.set_debug(gc.DEBUG_STATS)

        self.is_profiling = True
        self.start_time = time.time()
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024

        # Start monitoring tasks
        monitoring_tasks = [
            asyncio.create_task(self._continuous_monitoring()),
            asyncio.create_task(self._leak_detection()),
            asyncio.create_task(self._gc_monitoring())
        ]

        try:
            if duration:
                await asyncio.sleep(duration)
                await self.stop_profiling()
            else:
                # Run until stopped
                await asyncio.gather(*monitoring_tasks)
        except asyncio.CancelledError:
            logger.info("Memory profiling cancelled")
        finally:
            for task in monitoring_tasks:
                if not task.done():
                    task.cancel()

    async def stop_profiling(self):
        """Stop memory profiling session"""
        if not self.is_profiling:
            logger.warning("No profiling session in progress")
            return

        logger.info("Stopping memory profiling session...")

        self.is_profiling = False

        # Final snapshot
        await self._take_snapshot()

        # Analyze results
        await self._analyze_memory_patterns()
        await self._generate_recommendations()

        # Cleanup
        tracemalloc.stop()
        gc.set_debug(0)

        logger.info(f"Memory profiling completed. "
                   f"Took {len(self.snapshots)} snapshots over "
                   f"{time.time() - self.start_time:.1f} seconds")

    async def _continuous_monitoring(self):
        """Continuously monitor memory usage"""
        while self.is_profiling:
            await self._take_snapshot()
            await asyncio.sleep(self.sampling_interval)

    async def _take_snapshot(self):
        """Take a memory usage snapshot"""
        try:
            # System memory info
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            virtual_memory = psutil.virtual_memory()

            # Garbage collector stats
            gc_objects = len(gc.get_objects())
            gc_counts = gc.get_count()

            # Tracemalloc stats (if available)
            tracemalloc_current = None
            tracemalloc_peak = None
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc_current = current / 1024 / 1024  # MB
                tracemalloc_peak = peak / 1024 / 1024  # MB

            snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=memory_percent,
                available_mb=virtual_memory.available / 1024 / 1024,
                gc_objects=gc_objects,
                gc_generation_0=gc_counts[0],
                gc_generation_1=gc_counts[1],
                gc_generation_2=gc_counts[2],
                tracemalloc_current=tracemalloc_current,
                tracemalloc_peak=tracemalloc_peak
            )

            self.snapshots.append(snapshot)

            # Update peak memory
            if snapshot.rss_mb > self.peak_memory:
                self.peak_memory = snapshot.rss_mb

        except Exception as e:
            logger.error(f"Error taking memory snapshot: {e}")

    async def _leak_detection(self):
        """Monitor for memory leaks"""
        leak_detection_window = 60  # seconds

        while self.is_profiling:
            await asyncio.sleep(leak_detection_window)

            if len(self.snapshots) < 5:  # Need some history
                continue

            # Check memory growth over time
            recent_snapshots = self.snapshots[-5:]

            # Calculate memory growth rate
            time_span = recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp
            memory_growth = recent_snapshots[-1].rss_mb - recent_snapshots[0].rss_mb

            if time_span > 0:
                growth_rate = (memory_growth / time_span) * 60  # MB per minute

                # Detect concerning growth rates
                if growth_rate > 5.0:  # > 5MB/min growth
                    severity = "HIGH" if growth_rate > 20.0 else "MEDIUM"

                    leak = MemoryLeak(
                        detection_time=time.time(),
                        object_type="unknown",
                        growth_rate_mb_per_minute=growth_rate,
                        severity=severity,
                        description=f"Memory growing at {growth_rate:.1f} MB/min"
                    )

                    self.detected_leaks.append(leak)
                    logger.warning(f"Potential memory leak detected: {growth_rate:.1f} MB/min growth")

    async def _gc_monitoring(self):
        """Monitor garbage collection performance"""
        while self.is_profiling:
            # Force garbage collection and measure time
            start_time = time.perf_counter()
            collected = gc.collect()
            gc_time = (time.perf_counter() - start_time) * 1000  # ms

            self.gc_stats['collections'] += 1
            self.gc_stats['collected'] += collected

            if gc_time > 100:  # > 100ms GC time
                logger.warning(f"Long garbage collection: {gc_time:.1f}ms, collected {collected} objects")

            await asyncio.sleep(30)  # Check every 30 seconds

    async def _analyze_memory_patterns(self):
        """Analyze memory usage patterns"""
        if len(self.snapshots) < 2:
            return

        # Calculate overall statistics
        total_growth = self.snapshots[-1].rss_mb - self.snapshots[0].rss_mb
        total_time = self.snapshots[-1].timestamp - self.snapshots[0].timestamp

        if total_time > 0:
            self.memory_growth_rate = (total_growth / total_time) * 60  # MB per minute

        # Analyze patterns
        memory_values = [s.rss_mb for s in self.snapshots]
        gc_object_counts = [s.gc_objects for s in self.snapshots]

        # Check for memory spikes
        avg_memory = sum(memory_values) / len(memory_values)
        max_spike = max(memory_values) - avg_memory

        if max_spike > avg_memory * 0.3:  # Spike > 30% of average
            logger.warning(f"Large memory spike detected: {max_spike:.1f}MB above average")

        # Check for steadily growing object count
        if len(gc_object_counts) > 10:
            recent_growth = gc_object_counts[-1] - gc_object_counts[-10]
            if recent_growth > 10000:  # > 10K new objects
                logger.warning(f"High object growth: {recent_growth} new objects in recent samples")

    async def _generate_recommendations(self):
        """Generate optimization recommendations"""
        self.recommendations.clear()

        # High memory usage recommendation
        if self.peak_memory > 1000:  # > 1GB
            self.recommendations.append(OptimizationRecommendation(
                category="Memory Usage",
                priority="HIGH",
                issue=f"Peak memory usage: {self.peak_memory:.1f}MB",
                recommendation="Consider implementing object pooling for frequently created objects",
                expected_improvement="20-40% memory reduction",
                implementation_difficulty="MEDIUM"
            ))

        # Memory growth recommendation
        if self.memory_growth_rate > 10:  # > 10MB/min
            self.recommendations.append(OptimizationRecommendation(
                category="Memory Leaks",
                priority="HIGH",
                issue=f"High memory growth rate: {self.memory_growth_rate:.1f}MB/min",
                recommendation="Review object lifecycle management and implement weak references",
                expected_improvement="Stabilize memory usage",
                implementation_difficulty="HIGH"
            ))

        # GC frequency recommendation
        if self.gc_stats['collections'] > 100:
            self.recommendations.append(OptimizationRecommendation(
                category="Garbage Collection",
                priority="MEDIUM",
                issue=f"High GC frequency: {self.gc_stats['collections']} collections",
                recommendation="Reduce object churn by reusing objects and using generators",
                expected_improvement="30-50% reduction in GC overhead",
                implementation_difficulty="MEDIUM"
            ))

        # Object count recommendation
        if any(s.gc_objects > 100000 for s in self.snapshots):
            self.recommendations.append(OptimizationRecommendation(
                category="Object Management",
                priority="MEDIUM",
                issue="High object count detected",
                recommendation="Implement data structure optimization and cleanup unused objects",
                expected_improvement="Reduced memory fragmentation",
                implementation_difficulty="LOW"
            ))

    def get_analysis_report(self) -> dict[str, Any]:
        """Get comprehensive memory analysis report"""
        if not self.snapshots:
            return {"error": "No profiling data available"}

        # Calculate statistics
        memory_values = [s.rss_mb for s in self.snapshots]

        report = {
            "profiling_duration": time.time() - self.start_time,
            "snapshot_count": len(self.snapshots),
            "memory_statistics": {
                "baseline_mb": self.baseline_memory,
                "peak_mb": self.peak_memory,
                "final_mb": self.snapshots[-1].rss_mb,
                "total_growth_mb": self.snapshots[-1].rss_mb - self.baseline_memory,
                "growth_rate_mb_per_minute": self.memory_growth_rate,
                "average_mb": sum(memory_values) / len(memory_values),
                "min_mb": min(memory_values),
                "max_mb": max(memory_values)
            },
            "garbage_collection": {
                "total_collections": self.gc_stats['collections'],
                "total_collected": self.gc_stats['collected'],
                "avg_objects_per_collection": (
                    self.gc_stats['collected'] / self.gc_stats['collections']
                    if self.gc_stats['collections'] > 0 else 0
                )
            },
            "detected_leaks": [asdict(leak) for leak in self.detected_leaks],
            "recommendations": [asdict(rec) for rec in self.recommendations],
            "snapshots": [asdict(snapshot) for snapshot in self.snapshots[-10:]]  # Last 10 snapshots
        }

        return report

    def export_report(self, filename: str = None) -> str:
        """Export analysis report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'memory_analysis_{timestamp}.json'

        filepath = os.path.join(os.path.dirname(__file__), filename)

        try:
            import json
            report = self.get_analysis_report()

            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"Memory analysis report saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            raise


async def main():
    """Example usage of memory profiler"""
    profiler = AdvancedMemoryProfiler(sampling_interval=0.5)

    # Start profiling
    asyncio.create_task(profiler.start_profiling())

    # Simulate some memory-intensive operations
    data = []
    for i in range(10000):
        data.append({
            'id': i,
            'data': list(range(100)),
            'timestamp': time.time()
        })

        if i % 1000 == 0:
            await asyncio.sleep(0.1)

    # Stop profiling after 10 seconds
    await asyncio.sleep(10)
    await profiler.stop_profiling()

    # Get and display report
    report = profiler.get_analysis_report()
    print("Memory Analysis Report:")
    print(f"Peak Memory: {report['memory_statistics']['peak_mb']:.1f}MB")
    print(f"Growth Rate: {report['memory_statistics']['growth_rate_mb_per_minute']:.1f}MB/min")
    print(f"Detected Leaks: {len(report['detected_leaks'])}")
    print(f"Recommendations: {len(report['recommendations'])}")


if __name__ == "__main__":
    asyncio.run(main())
