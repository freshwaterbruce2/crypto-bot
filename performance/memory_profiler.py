"""
Advanced Memory Usage Analysis and Optimization
==============================================

Comprehensive memory profiling for high-frequency trading bot.
Analyzes memory usage patterns, identifies leaks, optimizes allocations,
and provides recommendations for memory-efficient operations.

Memory Analysis Features:
- Real-time memory usage monitoring
- Memory leak detection and analysis
- Object allocation tracking
- Garbage collection optimization
- Memory usage predictions
- Performance impact analysis
- Memory pool optimization recommendations
"""

import asyncio
import gc
import json
import logging
import os
import sys
import time
import tracemalloc
import weakref
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

import psutil

# Optional memory profiling dependencies
try:
    import memory_profiler
    HAVE_MEMORY_PROFILER = True
except ImportError:
    HAVE_MEMORY_PROFILER = False

try:
    import objgraph
    HAVE_OBJGRAPH = True
except ImportError:
    HAVE_OBJGRAPH = False

try:
    import pympler
    from pympler import muppy, summary, tracker
    HAVE_PYMPLER = True
except ImportError:
    HAVE_PYMPLER = False

# Import trading bot components
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time"""
    timestamp: float
    rss_mb: float
    vms_mb: float
    heap_mb: float
    available_mb: float
    percent_used: float
    objects_count: int
    gc_count: tuple[int, int, int]  # Generation 0, 1, 2 collection counts
    top_allocations: list[dict[str, Any]]


@dataclass
class MemoryLeak:
    """Detected memory leak information"""
    object_type: str
    count_increase: int
    size_increase_mb: float
    rate_per_minute: float
    first_detected: float
    last_observed: float
    stack_trace: list[str]
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class OptimizationRecommendation:
    """Memory optimization recommendation"""
    category: str
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL
    issue: str
    recommendation: str
    expected_savings_mb: float
    implementation_effort: str  # LOW, MEDIUM, HIGH
    code_examples: list[str]


class AdvancedMemoryProfiler:
    """Advanced memory profiler for trading bot"""

    def __init__(self, sampling_interval: float = 1.0):
        """Initialize memory profiler"""
        self.sampling_interval = sampling_interval
        self.is_profiling = False
        self.snapshots: list[MemorySnapshot] = []
        self.detected_leaks: list[MemoryLeak] = []
        self.recommendations: list[OptimizationRecommendation] = []

        # Memory tracking
        if HAVE_PYMPLER:
            self.object_tracker = tracker.SummaryTracker()
        else:
            self.object_tracker = None
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

        logger.info("Advanced Memory Profiler initialized")

    async def start_profiling(self, duration: Optional[float] = None):
        """Start memory profiling session"""
        if self.is_profiling:
            logger.warning("Profiling already in progress")
            return

        logger.info("Starting memory profiling session...")

        # Initialize tracking
        tracemalloc.start(10)  # Track top 10 stack frames
        if HAVE_PYMPLER:
            self.object_tracker = tracker.SummaryTracker()
        gc.set_debug(gc.DEBUG_STATS)

        self.is_profiling = True
        self.start_time = time.time()
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024

        # Start monitoring tasks
        monitoring_tasks = [
            asyncio.create_task(self._continuous_monitoring()),
            asyncio.create_task(self._leak_detection_loop()),
            asyncio.create_task(self._gc_monitoring_loop()),
            asyncio.create_task(self._object_growth_tracking())
        ]

        try:
            if duration:
                await asyncio.wait_for(
                    asyncio.gather(*monitoring_tasks),
                    timeout=duration
                )
            else:
                await asyncio.gather(*monitoring_tasks)
        except asyncio.TimeoutError:
            logger.info(f"Profiling completed after {duration}s")
        finally:
            await self.stop_profiling()

    async def stop_profiling(self):
        """Stop memory profiling session"""
        if not self.is_profiling:
            return

        logger.info("Stopping memory profiling session...")

        self.is_profiling = False

        # Final analysis
        await self._final_analysis()

        # Generate recommendations
        self._generate_optimization_recommendations()

        # Cleanup
        tracemalloc.stop()
        gc.set_debug(0)

        logger.info("Memory profiling session completed")

    async def _continuous_monitoring(self):
        """Continuous memory usage monitoring"""
        while self.is_profiling:
            try:
                snapshot = await self._take_memory_snapshot()
                self.snapshots.append(snapshot)

                # Update peak memory
                self.peak_memory = max(self.peak_memory, snapshot.rss_mb)

                # Calculate growth rate
                if len(self.snapshots) >= 2:
                    time_diff = snapshot.timestamp - self.snapshots[-2].timestamp
                    memory_diff = snapshot.rss_mb - self.snapshots[-2].rss_mb
                    self.memory_growth_rate = memory_diff / max(time_diff, 0.001) * 60  # MB/minute

                # Keep last 1000 snapshots
                if len(self.snapshots) > 1000:
                    self.snapshots = self.snapshots[-1000:]

                await asyncio.sleep(self.sampling_interval)

            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(1)

    async def _leak_detection_loop(self):
        """Memory leak detection loop"""
        object_counts = defaultdict(list)
        check_interval = 30  # Check every 30 seconds

        while self.is_profiling:
            try:
                # Get current object counts
                current_objects = muppy.get_objects()
                current_summary = summary.summarize(current_objects)

                # Track object count changes
                for row in current_summary:
                    obj_type = row[0].__name__ if hasattr(row[0], '__name__') else str(row[0])
                    count = row[1]
                    size_mb = row[2] / 1024 / 1024

                    object_counts[obj_type].append({
                        'timestamp': time.time(),
                        'count': count,
                        'size_mb': size_mb
                    })

                    # Keep last 20 measurements (10 minutes)
                    if len(object_counts[obj_type]) > 20:
                        object_counts[obj_type] = object_counts[obj_type][-20:]

                # Analyze for leaks
                await self._analyze_potential_leaks(object_counts)

                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in leak detection: {e}")
                await asyncio.sleep(check_interval)

    async def _gc_monitoring_loop(self):
        """Garbage collection monitoring loop"""
        while self.is_profiling:
            try:
                # Get GC stats
                gc_counts = gc.get_count()
                gc_stats = gc.get_stats()

                # Force GC and measure time
                gc_start = time.perf_counter()
                collected = gc.collect()
                gc_time = (time.perf_counter() - gc_start) * 1000  # milliseconds

                self.gc_stats = {
                    'collections': sum(gc_counts),
                    'collected': collected,
                    'gc_time_ms': gc_time,
                    'gen0_count': gc_counts[0],
                    'gen1_count': gc_counts[1],
                    'gen2_count': gc_counts[2],
                    'stats': gc_stats
                }

                # Log excessive GC activity
                if gc_time > 100:  # >100ms GC time
                    logger.warning(f"Long GC collection: {gc_time:.1f}ms, collected {collected} objects")

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in GC monitoring: {e}")
                await asyncio.sleep(60)

    async def _object_growth_tracking(self):
        """Track object growth patterns"""
        while self.is_profiling:
            try:
                # Track specific object types that commonly leak
                tracked_types = [
                    'dict', 'list', 'tuple', 'str', 'int', 'float',
                    'function', 'weakref', 'cell', 'frame'
                ]

                for obj_type in tracked_types:
                    count = len(objgraph.by_type(obj_type))

                    if obj_type not in self.allocation_tracker:
                        self.allocation_tracker[obj_type] = deque(maxlen=100)

                    self.allocation_tracker[obj_type].append({
                        'timestamp': time.time(),
                        'count': count
                    })

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Error in object growth tracking: {e}")
                await asyncio.sleep(10)

    async def _take_memory_snapshot(self) -> MemorySnapshot:
        """Take a comprehensive memory snapshot"""
        try:
            # System memory info
            memory_info = self.process.memory_info()
            system_memory = psutil.virtual_memory()

            # Tracemalloc info
            current, peak = tracemalloc.get_traced_memory()
            top_stats = tracemalloc.take_snapshot().statistics('lineno')[:10]

            # Object count
            objects = muppy.get_objects()
            summary.summarize(objects)

            # Format top allocations
            top_allocations = []
            for stat in top_stats:
                top_allocations.append({
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count,
                    'filename': stat.traceback.format()[-1] if stat.traceback else 'unknown',
                    'line': str(stat.traceback.format()[-1]) if stat.traceback else 'unknown'
                })

            return MemorySnapshot(
                timestamp=time.time(),
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                heap_mb=current / 1024 / 1024,
                available_mb=system_memory.available / 1024 / 1024,
                percent_used=system_memory.percent,
                objects_count=len(objects),
                gc_count=gc.get_count(),
                top_allocations=top_allocations
            )

        except Exception as e:
            logger.error(f"Error taking memory snapshot: {e}")
            # Return minimal snapshot
            memory_info = self.process.memory_info()
            return MemorySnapshot(
                timestamp=time.time(),
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                heap_mb=0,
                available_mb=0,
                percent_used=0,
                objects_count=0,
                gc_count=(0, 0, 0),
                top_allocations=[]
            )

    async def _analyze_potential_leaks(self, object_counts):
        """Analyze object count patterns for potential leaks"""
        current_time = time.time()

        for obj_type, measurements in object_counts.items():
            if len(measurements) < 5:  # Need minimum data points
                continue

            # Calculate trend
            first_measurement = measurements[0]
            last_measurement = measurements[-1]

            time_diff = last_measurement['timestamp'] - first_measurement['timestamp']
            count_diff = last_measurement['count'] - first_measurement['count']
            size_diff = last_measurement['size_mb'] - first_measurement['size_mb']

            if time_diff < 60:  # Need at least 1 minute of data
                continue

            # Calculate rates
            count_rate = count_diff / (time_diff / 60)  # per minute
            size_rate = size_diff / (time_diff / 60)  # MB per minute

            # Detect potential leaks
            if count_rate > 100 and size_rate > 1:  # >100 objects/min and >1MB/min
                severity = "CRITICAL" if size_rate > 10 else "HIGH" if size_rate > 5 else "MEDIUM"

                # Check if already detected
                existing_leak = next((leak for leak in self.detected_leaks
                                    if leak.object_type == obj_type), None)

                if existing_leak:
                    existing_leak.last_observed = current_time
                    existing_leak.count_increase += count_diff
                    existing_leak.size_increase_mb += size_diff
                else:
                    # Get stack trace for this object type
                    try:
                        sample_objects = objgraph.by_type(obj_type)[:5]
                        stack_trace = []
                        if sample_objects:
                            refs = objgraph.get_referrers(sample_objects[0])
                            stack_trace = [str(ref) for ref in refs[:10]]
                    except:
                        stack_trace = ["Stack trace unavailable"]

                    leak = MemoryLeak(
                        object_type=obj_type,
                        count_increase=count_diff,
                        size_increase_mb=size_diff,
                        rate_per_minute=size_rate,
                        first_detected=current_time,
                        last_observed=current_time,
                        stack_trace=stack_trace,
                        severity=severity
                    )
                    self.detected_leaks.append(leak)

                    logger.warning(f"Potential memory leak detected: {obj_type} "
                                 f"({count_rate:.0f} objects/min, {size_rate:.2f} MB/min)")

    async def _final_analysis(self):
        """Perform final memory analysis"""
        if not self.snapshots:
            return

        duration = time.time() - self.start_time
        final_memory = self.snapshots[-1].rss_mb
        memory_growth = final_memory - self.baseline_memory

        logger.info("Memory Analysis Summary:")
        logger.info(f"  Duration: {duration:.1f}s")
        logger.info(f"  Baseline Memory: {self.baseline_memory:.1f}MB")
        logger.info(f"  Final Memory: {final_memory:.1f}MB")
        logger.info(f"  Peak Memory: {self.peak_memory:.1f}MB")
        logger.info(f"  Memory Growth: {memory_growth:.1f}MB")
        logger.info(f"  Growth Rate: {self.memory_growth_rate:.2f}MB/min")
        logger.info(f"  Detected Leaks: {len(self.detected_leaks)}")

    def _generate_optimization_recommendations(self):
        """Generate memory optimization recommendations"""
        self.recommendations.clear()

        # Analyze memory growth
        if self.memory_growth_rate > 10:  # >10MB/min growth
            self.recommendations.append(OptimizationRecommendation(
                category="Memory Growth",
                priority="HIGH",
                issue=f"Excessive memory growth rate: {self.memory_growth_rate:.2f}MB/min",
                recommendation="Implement object pooling and reduce allocations in hot paths",
                expected_savings_mb=self.memory_growth_rate * 5,  # 5 minutes worth
                implementation_effort="MEDIUM",
                code_examples=[
                    "# Use object pools for frequently created objects",
                    "class ObjectPool:",
                    "    def __init__(self): self._objects = []",
                    "    def get(self): return self._objects.pop() if self._objects else self._create()",
                    "    def release(self, obj): self._objects.append(obj)"
                ]
            ))

        # Analyze detected leaks
        for leak in self.detected_leaks:
            if leak.severity in ["HIGH", "CRITICAL"]:
                self.recommendations.append(OptimizationRecommendation(
                    category="Memory Leak",
                    priority=leak.severity,
                    issue=f"Memory leak in {leak.object_type}: {leak.rate_per_minute:.2f}MB/min",
                    recommendation=f"Review {leak.object_type} lifecycle and ensure proper cleanup",
                    expected_savings_mb=leak.size_increase_mb,
                    implementation_effort="HIGH",
                    code_examples=[
                        f"# Review {leak.object_type} references and ensure cleanup",
                        "# Use weak references where appropriate",
                        "import weakref",
                        "self._cache = weakref.WeakValueDictionary()"
                    ]
                ))

        # Analyze GC performance
        if self.gc_stats.get('gc_time_ms', 0) > 50:
            self.recommendations.append(OptimizationRecommendation(
                category="Garbage Collection",
                priority="MEDIUM",
                issue=f"Long GC pauses: {self.gc_stats['gc_time_ms']:.1f}ms",
                recommendation="Optimize object allocation patterns and reduce circular references",
                expected_savings_mb=0,  # Performance improvement, not memory
                implementation_effort="MEDIUM",
                code_examples=[
                    "# Avoid circular references",
                    "# Use __slots__ to reduce memory overhead",
                    "class OptimizedClass:",
                    "    __slots__ = ['attr1', 'attr2']"
                ]
            ))

        # Analyze peak memory usage
        if self.peak_memory > 2048:  # >2GB
            self.recommendations.append(OptimizationRecommendation(
                category="Peak Memory",
                priority="HIGH",
                issue=f"High peak memory usage: {self.peak_memory:.1f}MB",
                recommendation="Implement streaming processing and data pagination",
                expected_savings_mb=self.peak_memory * 0.3,  # 30% savings
                implementation_effort="HIGH",
                code_examples=[
                    "# Use generators for large datasets",
                    "def process_data_stream(data):",
                    "    for chunk in chunks(data, 1000):",
                    "        yield process_chunk(chunk)"
                ]
            ))

        # Analyze object counts
        if self.snapshots:
            avg_objects = sum(s.objects_count for s in self.snapshots) / len(self.snapshots)
            if avg_objects > 1000000:  # >1M objects
                self.recommendations.append(OptimizationRecommendation(
                    category="Object Count",
                    priority="MEDIUM",
                    issue=f"High object count: {avg_objects:.0f} objects",
                    recommendation="Consolidate objects and use more efficient data structures",
                    expected_savings_mb=100,  # Estimated savings
                    implementation_effort="MEDIUM",
                    code_examples=[
                        "# Use numpy arrays for numerical data",
                        "import numpy as np",
                        "data = np.array(large_list, dtype=np.float32)",
                        "# Use namedtuples instead of classes for simple data"
                    ]
                ))

    def analyze_specific_component(self, component_name: str,
                                 test_function: callable,
                                 iterations: int = 1000) -> dict[str, Any]:
        """Analyze memory usage of a specific component"""
        logger.info(f"Analyzing memory usage of component: {component_name}")

        # Baseline measurement
        gc.collect()
        baseline_memory = self.process.memory_info().rss / 1024 / 1024
        baseline_objects = len(muppy.get_objects())

        # Start tracking
        tracemalloc.start()

        # Run test function
        start_time = time.perf_counter()

        for i in range(iterations):
            test_function()

            # Periodic GC to get accurate measurements
            if i % 100 == 0:
                gc.collect()

        end_time = time.perf_counter()

        # Final measurements
        final_memory = self.process.memory_info().rss / 1024 / 1024
        final_objects = len(muppy.get_objects())

        # Get memory allocation stats
        current, peak = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')[:10]

        tracemalloc.stop()

        # Calculate metrics
        memory_per_iteration = (final_memory - baseline_memory) / iterations
        objects_per_iteration = (final_objects - baseline_objects) / iterations
        execution_time = end_time - start_time
        operations_per_second = iterations / execution_time

        # Format results
        analysis = {
            'component': component_name,
            'iterations': iterations,
            'execution_time': execution_time,
            'operations_per_second': operations_per_second,
            'baseline_memory_mb': baseline_memory,
            'final_memory_mb': final_memory,
            'memory_growth_mb': final_memory - baseline_memory,
            'memory_per_iteration_kb': memory_per_iteration * 1024,
            'baseline_objects': baseline_objects,
            'final_objects': final_objects,
            'objects_per_iteration': objects_per_iteration,
            'peak_traced_memory_mb': peak / 1024 / 1024,
            'current_traced_memory_mb': current / 1024 / 1024,
            'top_allocations': [
                {
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count,
                    'filename': stat.traceback.format()[-1] if stat.traceback else 'unknown'
                }
                for stat in top_stats
            ]
        }

        logger.info("Component analysis completed:")
        logger.info(f"  Memory per iteration: {memory_per_iteration * 1024:.2f}KB")
        logger.info(f"  Objects per iteration: {objects_per_iteration:.1f}")
        logger.info(f"  Operations per second: {operations_per_second:.0f}")

        return analysis

    def profile_trading_operations(self) -> dict[str, Any]:
        """Profile memory usage of common trading operations"""
        logger.info("Profiling trading operations memory usage...")

        results = {}

        # Test order creation
        def create_orders():
            orders = []
            for i in range(100):
                order = {
                    'id': f'order_{i}',
                    'symbol': 'BTC/USDT',
                    'side': 'buy',
                    'amount': 1.0 + i * 0.01,
                    'price': 50000 + i,
                    'timestamp': time.time()
                }
                orders.append(order)
            return orders

        results['order_creation'] = self.analyze_specific_component(
            'Order Creation',
            create_orders,
            iterations=100
        )

        # Test balance updates
        def update_balances():
            balances = {}
            for i in range(50):
                asset = f'ASSET{i % 10}'
                balances[asset] = {
                    'free': 1000.0 + i,
                    'used': i * 0.1,
                    'total': 1000.0 + i + (i * 0.1),
                    'timestamp': time.time()
                }
            return balances

        results['balance_updates'] = self.analyze_specific_component(
            'Balance Updates',
            update_balances,
            iterations=200
        )

        # Test market data processing
        def process_market_data():
            market_data = {}
            for symbol in ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']:
                market_data[symbol] = {
                    'ticker': {
                        'bid': 50000.0,
                        'ask': 50010.0,
                        'last': 50005.0,
                        'volume': 1000.0
                    },
                    'orderbook': {
                        'bids': [[50000 - i, 1.0] for i in range(20)],
                        'asks': [[50010 + i, 1.0] for i in range(20)]
                    },
                    'trades': [
                        {'price': 50000 + i, 'amount': 1.0, 'timestamp': time.time()}
                        for i in range(50)
                    ]
                }
            return market_data

        results['market_data_processing'] = self.analyze_specific_component(
            'Market Data Processing',
            process_market_data,
            iterations=100
        )

        # Test portfolio calculations
        def calculate_portfolio():
            positions = {}
            for i in range(20):
                symbol = f'PAIR{i}'
                positions[symbol] = {
                    'amount': 100.0 + i,
                    'avg_price': 1000.0 + i * 10,
                    'current_price': 1000.0 + i * 10 + (i % 20),
                    'pnl': (i % 40) - 20,
                    'percentage': (i % 40) - 20 / 1000.0
                }

            # Portfolio metrics
            total_value = sum(pos['amount'] * pos['current_price'] for pos in positions.values())
            total_pnl = sum(pos['pnl'] for pos in positions.values())

            return {
                'positions': positions,
                'total_value': total_value,
                'total_pnl': total_pnl,
                'timestamp': time.time()
            }

        results['portfolio_calculations'] = self.analyze_specific_component(
            'Portfolio Calculations',
            calculate_portfolio,
            iterations=500
        )

        return results

    def generate_comprehensive_report(self) -> dict[str, Any]:
        """Generate comprehensive memory analysis report"""
        if not self.snapshots:
            logger.warning("No memory snapshots available for report")
            return {}

        # Calculate summary statistics
        memory_values = [s.rss_mb for s in self.snapshots]
        object_counts = [s.objects_count for s in self.snapshots]

        import statistics

        report = {
            'profiling_session': {
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'duration_seconds': time.time() - self.start_time if self.start_time else 0,
                'snapshots_count': len(self.snapshots),
                'sampling_interval': self.sampling_interval
            },
            'memory_summary': {
                'baseline_memory_mb': self.baseline_memory,
                'peak_memory_mb': self.peak_memory,
                'final_memory_mb': memory_values[-1] if memory_values else 0,
                'total_growth_mb': (memory_values[-1] - self.baseline_memory) if memory_values else 0,
                'growth_rate_mb_per_minute': self.memory_growth_rate,
                'average_memory_mb': statistics.mean(memory_values) if memory_values else 0,
                'memory_std_dev_mb': statistics.stdev(memory_values) if len(memory_values) > 1 else 0
            },
            'object_analysis': {
                'average_object_count': statistics.mean(object_counts) if object_counts else 0,
                'peak_object_count': max(object_counts) if object_counts else 0,
                'object_growth': (object_counts[-1] - object_counts[0]) if len(object_counts) > 1 else 0
            },
            'garbage_collection': self.gc_stats,
            'detected_leaks': [asdict(leak) for leak in self.detected_leaks],
            'optimization_recommendations': [asdict(rec) for rec in self.recommendations],
            'memory_timeline': [asdict(snapshot) for snapshot in self.snapshots[-100:]]  # Last 100 snapshots
        }

        return report

    def save_report(self, report: dict[str, Any], filename: str = None):
        """Save memory analysis report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'memory_analysis_report_{timestamp}.json'

        filepath = os.path.join(os.path.dirname(__file__), filename)

        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Memory analysis report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

    def print_summary(self, report: dict[str, Any]):
        """Print memory analysis summary to console"""
        print("\n" + "="*80)
        print("🧠 MEMORY USAGE ANALYSIS REPORT")
        print("="*80)

        session = report.get('profiling_session', {})
        memory = report.get('memory_summary', {})
        objects = report.get('object_analysis', {})

        print("\n📊 PROFILING SESSION:")
        print(f"   Duration: {session.get('duration_seconds', 0):.1f}s")
        print(f"   Snapshots: {session.get('snapshots_count', 0)}")
        print(f"   Sampling: {session.get('sampling_interval', 0):.1f}s intervals")

        print("\n💾 MEMORY SUMMARY:")
        print(f"   Baseline: {memory.get('baseline_memory_mb', 0):.1f}MB")
        print(f"   Peak: {memory.get('peak_memory_mb', 0):.1f}MB")
        print(f"   Final: {memory.get('final_memory_mb', 0):.1f}MB")
        print(f"   Growth: {memory.get('total_growth_mb', 0):.1f}MB")
        print(f"   Growth Rate: {memory.get('growth_rate_mb_per_minute', 0):.2f}MB/min")
        print(f"   Average: {memory.get('average_memory_mb', 0):.1f}MB")

        print("\n🔢 OBJECT ANALYSIS:")
        print(f"   Average Objects: {objects.get('average_object_count', 0):.0f}")
        print(f"   Peak Objects: {objects.get('peak_object_count', 0):.0f}")
        print(f"   Object Growth: {objects.get('object_growth', 0):.0f}")

        # Memory leaks
        leaks = report.get('detected_leaks', [])
        if leaks:
            print(f"\n🚨 DETECTED MEMORY LEAKS ({len(leaks)}):")
            for leak in leaks[:5]:  # Show top 5
                print(f"   {leak['severity']} | {leak['object_type']}")
                print(f"        Rate: {leak['rate_per_minute']:.2f}MB/min")
                print(f"        Size: {leak['size_increase_mb']:.1f}MB increase")

        # Recommendations
        recommendations = report.get('optimization_recommendations', [])
        if recommendations:
            print("\n💡 OPTIMIZATION RECOMMENDATIONS:")
            for rec in recommendations[:3]:  # Show top 3
                print(f"   {rec['priority']} | {rec['category']}")
                print(f"        Issue: {rec['issue']}")
                print(f"        Fix: {rec['recommendation']}")
                print(f"        Savings: {rec['expected_savings_mb']:.1f}MB")

        # GC stats
        gc_stats = report.get('garbage_collection', {})
        if gc_stats:
            print("\n🗑️  GARBAGE COLLECTION:")
            print(f"   Collections: {gc_stats.get('collections', 0)}")
            print(f"   Objects Collected: {gc_stats.get('collected', 0)}")
            print(f"   GC Time: {gc_stats.get('gc_time_ms', 0):.1f}ms")

        print("\n" + "="*80)


async def main():
    """Run memory profiling analysis"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create memory profiler
    profiler = AdvancedMemoryProfiler(sampling_interval=0.5)  # 0.5s sampling

    try:
        # Profile trading operations
        logger.info("Starting trading operations memory profiling...")
        trading_results = profiler.profile_trading_operations()

        # Start continuous profiling for 5 minutes
        logger.info("Starting continuous memory profiling...")
        await profiler.start_profiling(duration=300)  # 5 minutes

        # Generate comprehensive report
        report = profiler.generate_comprehensive_report()
        report['trading_operations_analysis'] = trading_results

        # Save and display results
        profiler.save_report(report)
        profiler.print_summary(report)

        # Determine success
        memory_growth = report['memory_summary']['growth_rate_mb_per_minute']
        detected_leaks = len(report['detected_leaks'])

        if memory_growth < 5 and detected_leaks == 0:
            logger.info("✅ Memory profiling PASSED - No significant issues detected")
            return 0
        else:
            logger.warning(f"⚠️  Memory profiling found issues: {memory_growth:.1f}MB/min growth, {detected_leaks} leaks")
            return 1

    except Exception as e:
        logger.error(f"Memory profiling failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
