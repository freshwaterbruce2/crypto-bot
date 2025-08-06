#!/usr/bin/env python3
"""
Performance Benchmark Test Suite
Validates specific performance optimizations and measures improvements
"""

import asyncio
import gc
import json
import statistics
import sys
import threading
import time
import traceback
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil

# Add project root to path
sys.path.append('/mnt/c/dev/tools/crypto-trading-bot-2025')

# Performance-related imports
from src.exchange.kraken_websocket_v2_direct import KrakenWebSocketV2Direct
from src.storage.database_manager import DatabaseManager
from src.utils.batch_processor import BatchProcessor
from src.utils.bounded_cache import BoundedCache
from src.utils.memory_optimizer import MemoryOptimizer
from src.utils.optimized_calculations import OptimizedCalculations
from src.utils.performance_maximizer_2025 import PerformanceMaximizer2025
from src.utils.priority_message_queue import PriorityMessageQueue
from src.utils.vectorized_math import VectorizedMath


@dataclass
class BenchmarkResult:
    test_name: str
    operations_per_second: float
    average_latency_ms: float
    memory_efficiency_mb_per_op: float
    cpu_efficiency_percent: float
    throughput_improvement_percent: float
    baseline_ops_per_sec: Optional[float] = None

@dataclass
class PerformanceMetrics:
    start_time: float
    end_time: float
    operations_count: int
    memory_start_mb: float
    memory_end_mb: float
    cpu_samples: List[float]

class PerformanceBenchmarkTest:
    """Performance benchmark test suite for optimization validation"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.memory_optimizer = MemoryOptimizer()
        self.performance_maximizer = PerformanceMaximizer2025()
        self.vectorized_math = VectorizedMath()
        self.optimized_calc = OptimizedCalculations()

        # Benchmark configuration
        self.benchmark_config = {
            'message_queue_operations': 100000,
            'memory_optimization_cycles': 1000,
            'database_operations': 10000,
            'websocket_message_count': 50000,
            'calculation_iterations': 100000,
            'concurrent_connections': 100
        }

    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all performance benchmarks"""
        print("🏎️ Starting Performance Benchmark Suite")
        print(f"Benchmark Configuration: {json.dumps(self.benchmark_config, indent=2)}")

        try:
            # 1. Message Queue Performance
            await self._benchmark_message_queue_performance()

            # 2. Memory Optimization Performance
            await self._benchmark_memory_optimization()

            # 3. Database Connection Pooling Performance
            await self._benchmark_database_performance()

            # 4. WebSocket Message Processing Performance
            await self._benchmark_websocket_performance()

            # 5. Mathematical Calculations Performance
            await self._benchmark_calculation_performance()

            # 6. Concurrent Operations Performance
            await self._benchmark_concurrent_performance()

            # 7. Cache Performance
            await self._benchmark_cache_performance()

            # 8. Batch Processing Performance
            await self._benchmark_batch_processing()

            # Generate benchmark report
            return await self._generate_benchmark_report()

        except Exception as e:
            print(f"Benchmark suite failed: {e}")
            print(traceback.format_exc())
            return {"status": "FAILED", "error": str(e)}

    async def _benchmark_message_queue_performance(self):
        """Benchmark message queue performance improvements"""
        print("\n📦 Benchmarking Message Queue Performance")

        # Test priority message queue
        print("Testing Priority Message Queue...")

        message_queue = PriorityMessageQueue()
        operations = self.benchmark_config['message_queue_operations']

        # Benchmark message addition
        metrics = await self._measure_performance(
            lambda: self._add_messages_to_queue(message_queue, operations),
            operations,
            "Message Queue Addition"
        )

        add_ops_per_sec = operations / (metrics.end_time - metrics.start_time)
        add_latency_ms = ((metrics.end_time - metrics.start_time) / operations) * 1000

        # Benchmark message processing
        process_metrics = await self._measure_performance(
            lambda: self._process_messages_from_queue(message_queue),
            operations,
            "Message Queue Processing"
        )

        process_ops_per_sec = operations / (process_metrics.end_time - process_metrics.start_time)
        process_latency_ms = ((process_metrics.end_time - process_metrics.start_time) / operations) * 1000

        # Calculate memory efficiency
        memory_per_op = (metrics.memory_end_mb - metrics.memory_start_mb) / operations if operations > 0 else 0
        cpu_efficiency = statistics.mean(metrics.cpu_samples) if metrics.cpu_samples else 0

        self.results.append(BenchmarkResult(
            test_name="Priority Message Queue - Addition",
            operations_per_second=add_ops_per_sec,
            average_latency_ms=add_latency_ms,
            memory_efficiency_mb_per_op=memory_per_op,
            cpu_efficiency_percent=cpu_efficiency,
            throughput_improvement_percent=0  # Baseline
        ))

        self.results.append(BenchmarkResult(
            test_name="Priority Message Queue - Processing",
            operations_per_second=process_ops_per_sec,
            average_latency_ms=process_latency_ms,
            memory_efficiency_mb_per_op=(process_metrics.memory_end_mb - process_metrics.memory_start_mb) / operations,
            cpu_efficiency_percent=statistics.mean(process_metrics.cpu_samples) if process_metrics.cpu_samples else 0,
            throughput_improvement_percent=0  # Baseline
        ))

        print(f"✅ Message Queue - Add: {add_ops_per_sec:.0f} ops/sec, {add_latency_ms:.3f}ms latency")
        print(f"✅ Message Queue - Process: {process_ops_per_sec:.0f} ops/sec, {process_latency_ms:.3f}ms latency")

    async def _benchmark_memory_optimization(self):
        """Benchmark memory optimization improvements"""
        print("\n🧠 Benchmarking Memory Optimization Performance")

        cycles = self.benchmark_config['memory_optimization_cycles']

        # Create memory pressure
        memory_hogs = []
        for i in range(1000):
            memory_hogs.append([j * j for j in range(1000)])  # Create memory pressure

        # Benchmark memory optimization
        metrics = await self._measure_performance(
            lambda: self._run_memory_optimization_cycles(cycles),
            cycles,
            "Memory Optimization"
        )

        ops_per_sec = cycles / (metrics.end_time - metrics.start_time)
        latency_ms = ((metrics.end_time - metrics.start_time) / cycles) * 1000
        memory_freed = metrics.memory_start_mb - metrics.memory_end_mb
        memory_efficiency = memory_freed / cycles if cycles > 0 else 0

        self.results.append(BenchmarkResult(
            test_name="Memory Optimization",
            operations_per_second=ops_per_sec,
            average_latency_ms=latency_ms,
            memory_efficiency_mb_per_op=memory_efficiency,
            cpu_efficiency_percent=statistics.mean(metrics.cpu_samples) if metrics.cpu_samples else 0,
            throughput_improvement_percent=0  # Will be calculated against baseline
        ))

        print(f"✅ Memory Optimization: {ops_per_sec:.0f} cycles/sec, {memory_freed:.2f}MB freed")

        # Clean up
        del memory_hogs
        gc.collect()

    async def _benchmark_database_performance(self):
        """Benchmark database connection pooling performance"""
        print("\n🗄️ Benchmarking Database Performance")

        operations = self.benchmark_config['database_operations']

        try:
            # Initialize database manager with connection pooling
            db_manager = DatabaseManager()
            await db_manager.initialize()

            # Benchmark database operations with pooling
            metrics = await self._measure_performance(
                lambda: self._run_database_operations(db_manager, operations),
                operations,
                "Database Operations with Pooling"
            )

            ops_per_sec = operations / (metrics.end_time - metrics.start_time)
            latency_ms = ((metrics.end_time - metrics.start_time) / operations) * 1000
            memory_per_op = (metrics.memory_end_mb - metrics.memory_start_mb) / operations

            # Get pool statistics
            pool_stats = await db_manager.get_connection_pool_stats()

            self.results.append(BenchmarkResult(
                test_name="Database Operations (Pooled)",
                operations_per_second=ops_per_sec,
                average_latency_ms=latency_ms,
                memory_efficiency_mb_per_op=memory_per_op,
                cpu_efficiency_percent=statistics.mean(metrics.cpu_samples) if metrics.cpu_samples else 0,
                throughput_improvement_percent=0  # Baseline
            ))

            print(f"✅ Database (Pooled): {ops_per_sec:.0f} ops/sec, {latency_ms:.3f}ms latency")
            print(f"   Pool Stats: {pool_stats}")

        except Exception as e:
            print(f"⚠️ Database benchmark skipped: {e}")

    async def _benchmark_websocket_performance(self):
        """Benchmark WebSocket message processing performance"""
        print("\n🌐 Benchmarking WebSocket Performance")

        message_count = self.benchmark_config['websocket_message_count']

        # Simulate WebSocket message processing
        websocket_client = KrakenWebSocketV2Direct()

        # Benchmark message processing
        metrics = await self._measure_performance(
            lambda: self._simulate_websocket_message_processing(websocket_client, message_count),
            message_count,
            "WebSocket Message Processing"
        )

        ops_per_sec = message_count / (metrics.end_time - metrics.start_time)
        latency_ms = ((metrics.end_time - metrics.start_time) / message_count) * 1000
        memory_per_op = (metrics.memory_end_mb - metrics.memory_start_mb) / message_count

        self.results.append(BenchmarkResult(
            test_name="WebSocket Message Processing",
            operations_per_second=ops_per_sec,
            average_latency_ms=latency_ms,
            memory_efficiency_mb_per_op=memory_per_op,
            cpu_efficiency_percent=statistics.mean(metrics.cpu_samples) if metrics.cpu_samples else 0,
            throughput_improvement_percent=0  # Baseline
        ))

        print(f"✅ WebSocket Processing: {ops_per_sec:.0f} msgs/sec, {latency_ms:.3f}ms latency")

    async def _benchmark_calculation_performance(self):
        """Benchmark mathematical calculation optimizations"""
        print("\n🧮 Benchmarking Calculation Performance")

        iterations = self.benchmark_config['calculation_iterations']

        # Test vectorized math operations
        print("Testing Vectorized Math...")

        # Generate test data
        test_data = [i * 0.001 for i in range(1000)]

        # Benchmark vectorized operations
        vectorized_metrics = await self._measure_performance(
            lambda: self._run_vectorized_calculations(test_data, iterations),
            iterations,
            "Vectorized Calculations"
        )

        vectorized_ops_per_sec = iterations / (vectorized_metrics.end_time - vectorized_metrics.start_time)
        vectorized_latency_ms = ((vectorized_metrics.end_time - vectorized_metrics.start_time) / iterations) * 1000

        # Benchmark standard operations (for comparison)
        standard_metrics = await self._measure_performance(
            lambda: self._run_standard_calculations(test_data, iterations),
            iterations,
            "Standard Calculations"
        )

        standard_ops_per_sec = iterations / (standard_metrics.end_time - standard_metrics.start_time)
        improvement_percent = ((vectorized_ops_per_sec - standard_ops_per_sec) / standard_ops_per_sec) * 100

        self.results.append(BenchmarkResult(
            test_name="Vectorized Math Operations",
            operations_per_second=vectorized_ops_per_sec,
            average_latency_ms=vectorized_latency_ms,
            memory_efficiency_mb_per_op=(vectorized_metrics.memory_end_mb - vectorized_metrics.memory_start_mb) / iterations,
            cpu_efficiency_percent=statistics.mean(vectorized_metrics.cpu_samples) if vectorized_metrics.cpu_samples else 0,
            throughput_improvement_percent=improvement_percent,
            baseline_ops_per_sec=standard_ops_per_sec
        ))

        print(f"✅ Vectorized Math: {vectorized_ops_per_sec:.0f} ops/sec ({improvement_percent:+.1f}% vs standard)")

        # Test optimized calculations
        print("Testing Optimized Calculations...")

        optimized_metrics = await self._measure_performance(
            lambda: self._run_optimized_calculations(iterations),
            iterations,
            "Optimized Calculations"
        )

        optimized_ops_per_sec = iterations / (optimized_metrics.end_time - optimized_metrics.start_time)
        optimized_latency_ms = ((optimized_metrics.end_time - optimized_metrics.start_time) / iterations) * 1000

        self.results.append(BenchmarkResult(
            test_name="Optimized Calculations",
            operations_per_second=optimized_ops_per_sec,
            average_latency_ms=optimized_latency_ms,
            memory_efficiency_mb_per_op=(optimized_metrics.memory_end_mb - optimized_metrics.memory_start_mb) / iterations,
            cpu_efficiency_percent=statistics.mean(optimized_metrics.cpu_samples) if optimized_metrics.cpu_samples else 0,
            throughput_improvement_percent=0  # Baseline for optimized calcs
        ))

        print(f"✅ Optimized Calculations: {optimized_ops_per_sec:.0f} ops/sec, {optimized_latency_ms:.3f}ms latency")

    async def _benchmark_concurrent_performance(self):
        """Benchmark concurrent operations performance"""
        print("\n⚡ Benchmarking Concurrent Performance")

        concurrent_ops = self.benchmark_config['concurrent_connections']

        # Benchmark concurrent task execution
        metrics = await self._measure_performance(
            lambda: self._run_concurrent_operations(concurrent_ops),
            concurrent_ops,
            "Concurrent Operations"
        )

        ops_per_sec = concurrent_ops / (metrics.end_time - metrics.start_time)
        latency_ms = ((metrics.end_time - metrics.start_time) / concurrent_ops) * 1000

        self.results.append(BenchmarkResult(
            test_name="Concurrent Operations",
            operations_per_second=ops_per_sec,
            average_latency_ms=latency_ms,
            memory_efficiency_mb_per_op=(metrics.memory_end_mb - metrics.memory_start_mb) / concurrent_ops,
            cpu_efficiency_percent=statistics.mean(metrics.cpu_samples) if metrics.cpu_samples else 0,
            throughput_improvement_percent=0  # Baseline
        ))

        print(f"✅ Concurrent Operations: {ops_per_sec:.0f} ops/sec")

    async def _benchmark_cache_performance(self):
        """Benchmark cache performance"""
        print("\n💾 Benchmarking Cache Performance")

        cache_operations = 50000

        # Test bounded cache
        cache = BoundedCache(max_size=10000)

        # Benchmark cache operations
        metrics = await self._measure_performance(
            lambda: self._run_cache_operations(cache, cache_operations),
            cache_operations,
            "Cache Operations"
        )

        ops_per_sec = cache_operations / (metrics.end_time - metrics.start_time)
        latency_ms = ((metrics.end_time - metrics.start_time) / cache_operations) * 1000

        # Get cache statistics
        cache_stats = cache.get_stats()

        self.results.append(BenchmarkResult(
            test_name="Bounded Cache Operations",
            operations_per_second=ops_per_sec,
            average_latency_ms=latency_ms,
            memory_efficiency_mb_per_op=(metrics.memory_end_mb - metrics.memory_start_mb) / cache_operations,
            cpu_efficiency_percent=statistics.mean(metrics.cpu_samples) if metrics.cpu_samples else 0,
            throughput_improvement_percent=0  # Baseline
        ))

        print(f"✅ Cache Operations: {ops_per_sec:.0f} ops/sec")
        print(f"   Cache Stats: {cache_stats}")

    async def _benchmark_batch_processing(self):
        """Benchmark batch processing performance"""
        print("\n📊 Benchmarking Batch Processing Performance")

        batch_size = 1000
        batches = 100
        total_items = batch_size * batches

        # Test batch processor
        batch_processor = BatchProcessor(batch_size=batch_size)

        # Generate test data
        test_items = [{"id": i, "value": i * 2} for i in range(total_items)]

        # Benchmark batch processing
        metrics = await self._measure_performance(
            lambda: self._run_batch_processing(batch_processor, test_items),
            total_items,
            "Batch Processing"
        )

        ops_per_sec = total_items / (metrics.end_time - metrics.start_time)
        latency_ms = ((metrics.end_time - metrics.start_time) / total_items) * 1000

        self.results.append(BenchmarkResult(
            test_name="Batch Processing",
            operations_per_second=ops_per_sec,
            average_latency_ms=latency_ms,
            memory_efficiency_mb_per_op=(metrics.memory_end_mb - metrics.memory_start_mb) / total_items,
            cpu_efficiency_percent=statistics.mean(metrics.cpu_samples) if metrics.cpu_samples else 0,
            throughput_improvement_percent=0  # Baseline
        ))

        print(f"✅ Batch Processing: {ops_per_sec:.0f} items/sec")

    # Helper methods for running specific benchmarks

    def _add_messages_to_queue(self, queue: PriorityMessageQueue, count: int):
        """Add messages to priority queue"""
        priorities = ["HIGH", "MEDIUM", "LOW"]
        for i in range(count):
            priority = priorities[i % 3]
            message = {"id": i, "data": f"message_{i}"}
            queue.add_message(message, priority)

    def _process_messages_from_queue(self, queue: PriorityMessageQueue):
        """Process all messages from queue"""
        processed = 0
        while not queue.is_empty():
            msg, priority = queue.get_next_message()
            processed += 1
            # Simulate processing
            if msg and "id" in msg:
                pass  # Minimal processing
        return processed

    def _run_memory_optimization_cycles(self, cycles: int):
        """Run memory optimization cycles"""
        for _ in range(cycles):
            self.memory_optimizer.optimize_memory()
            # Force some garbage collection
            if _ % 100 == 0:
                gc.collect()

    async def _run_database_operations(self, db_manager: DatabaseManager, operations: int):
        """Run database operations"""
        for i in range(operations):
            try:
                # Simple query that should be fast
                result = await db_manager.execute_query(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                )
                # Simulate some processing
                if result:
                    pass
            except Exception as e:
                print(f"Database operation {i} failed: {e}")

    def _simulate_websocket_message_processing(self, client: KrakenWebSocketV2Direct, count: int):
        """Simulate WebSocket message processing"""
        for i in range(count):
            # Simulate message processing
            message = {
                "channel": "ticker",
                "type": "update",
                "data": {
                    "symbol": "BTC/USD",
                    "price": 50000 + (i % 1000),
                    "volume": 100
                }
            }

            # Simulate processing the message
            if message["type"] == "update":
                symbol = message["data"]["symbol"]
                price = message["data"]["price"]
                # Minimal processing simulation
                processed_price = float(price) * 1.0001

    def _run_vectorized_calculations(self, data: List[float], iterations: int):
        """Run vectorized mathematical calculations"""
        for _ in range(iterations):
            # Use vectorized operations
            result = self.vectorized_math.calculate_moving_average(data, 10)
            volatility = self.vectorized_math.calculate_volatility(data)
            correlation = self.vectorized_math.calculate_correlation(data, data)

    def _run_standard_calculations(self, data: List[float], iterations: int):
        """Run standard mathematical calculations for comparison"""
        for _ in range(iterations):
            # Standard moving average
            window = 10
            if len(data) >= window:
                ma = sum(data[-window:]) / window

            # Standard volatility calculation
            if len(data) > 1:
                mean = sum(data) / len(data)
                variance = sum((x - mean) ** 2 for x in data) / len(data)
                volatility = variance ** 0.5

    def _run_optimized_calculations(self, iterations: int):
        """Run optimized calculations"""
        for _ in range(iterations):
            # Use optimized calculation methods
            result = self.optimized_calc.fast_rsi([50, 51, 49, 52, 48])
            bollinger = self.optimized_calc.bollinger_bands([50, 51, 49, 52, 48], 5, 2)
            ema = self.optimized_calc.exponential_moving_average([50, 51, 49, 52, 48], 0.1)

    async def _run_concurrent_operations(self, count: int):
        """Run concurrent operations"""

        async def concurrent_task(task_id: int):
            """Simulate a concurrent task"""
            await asyncio.sleep(0.001)  # Small delay

            # Simulate some work
            result = sum(x * x for x in range(100))
            return result

        # Run tasks concurrently
        tasks = [concurrent_task(i) for i in range(count)]
        results = await asyncio.gather(*tasks)

        return len(results)

    def _run_cache_operations(self, cache: BoundedCache, operations: int):
        """Run cache operations"""

        # Mix of set and get operations
        for i in range(operations):
            if i % 3 == 0:
                # Set operation
                cache.set(f"key_{i}", f"value_{i}")
            else:
                # Get operation
                cache.get(f"key_{i % 100}")  # Get from existing keys

    def _run_batch_processing(self, processor: BatchProcessor, items: List[Dict]):
        """Run batch processing"""

        def process_batch(batch):
            """Process a batch of items"""
            return [{"processed_id": item["id"], "result": item["value"] * 2} for item in batch]

        # Process all items in batches
        results = processor.process_in_batches(items, process_batch)
        return len(results)

    @asynccontextmanager
    async def _cpu_monitor(self):
        """Monitor CPU usage during operation"""
        cpu_samples = []
        monitoring = True

        def monitor_cpu():
            while monitoring:
                cpu_samples.append(psutil.cpu_percent())
                time.sleep(0.1)

        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()

        try:
            yield cpu_samples
        finally:
            monitoring = False
            monitor_thread.join()

    async def _measure_performance(self, operation_func, operation_count: int, operation_name: str) -> PerformanceMetrics:
        """Measure performance metrics for an operation"""
        print(f"   Running {operation_name}...")

        # Get initial metrics
        gc.collect()  # Clean up before measurement
        process = psutil.Process()
        memory_start = process.memory_info().rss / 1024 / 1024  # MB

        cpu_samples = []

        # Start CPU monitoring
        async with self._cpu_monitor() as samples:
            start_time = time.time()

            # Run the operation
            if asyncio.iscoroutinefunction(operation_func):
                await operation_func()
            else:
                operation_func()

            end_time = time.time()
            cpu_samples = samples.copy()

        # Get final metrics
        memory_end = process.memory_info().rss / 1024 / 1024  # MB

        return PerformanceMetrics(
            start_time=start_time,
            end_time=end_time,
            operations_count=operation_count,
            memory_start_mb=memory_start,
            memory_end_mb=memory_end,
            cpu_samples=cpu_samples
        )

    async def _generate_benchmark_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report"""
        print("\n📊 Generating Performance Benchmark Report")

        # Calculate overall statistics
        total_operations = sum(result.operations_per_second for result in self.results)
        avg_latency = statistics.mean([result.average_latency_ms for result in self.results])
        avg_memory_efficiency = statistics.mean([abs(result.memory_efficiency_mb_per_op) for result in self.results])
        avg_cpu_efficiency = statistics.mean([result.cpu_efficiency_percent for result in self.results])

        # Find performance improvements
        improvements = [r for r in self.results if r.throughput_improvement_percent > 0]
        avg_improvement = statistics.mean([r.throughput_improvement_percent for r in improvements]) if improvements else 0

        # Performance categories
        high_performers = [r for r in self.results if r.operations_per_second > 10000]
        memory_efficient = [r for r in self.results if abs(r.memory_efficiency_mb_per_op) < 0.001]
        low_latency = [r for r in self.results if r.average_latency_ms < 1.0]

        # Generate report
        report = {
            "benchmark_summary": {
                "total_benchmarks": len(self.results),
                "high_performance_tests": len(high_performers),
                "memory_efficient_tests": len(memory_efficient),
                "low_latency_tests": len(low_latency),
                "average_improvement_percent": round(avg_improvement, 2)
            },
            "performance_metrics": {
                "average_operations_per_second": round(total_operations / len(self.results), 2),
                "average_latency_ms": round(avg_latency, 3),
                "average_memory_efficiency_mb_per_op": round(avg_memory_efficiency, 6),
                "average_cpu_efficiency_percent": round(avg_cpu_efficiency, 2)
            },
            "benchmark_results": [asdict(result) for result in self.results],
            "configuration": self.benchmark_config,
            "performance_insights": []
        }

        # Add performance insights
        if high_performers:
            report["performance_insights"].append(f"High throughput achieved in {len(high_performers)} tests (>10K ops/sec)")

        if memory_efficient:
            report["performance_insights"].append(f"Memory efficient processing in {len(memory_efficient)} tests (<0.001MB/op)")

        if low_latency:
            report["performance_insights"].append(f"Low latency achieved in {len(low_latency)} tests (<1ms avg)")

        if avg_improvement > 0:
            report["performance_insights"].append(f"Average performance improvement: {avg_improvement:.1f}%")

        # Save report
        report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"/mnt/c/dev/tools/crypto-trading-bot-2025/performance_benchmark_report_{report_timestamp}.json"

        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Print summary
        print("\n📋 Performance Benchmark Summary:")
        print(f"   Total Benchmarks: {len(self.results)}")
        print(f"   High Performance Tests: {len(high_performers)}")
        print(f"   Memory Efficient Tests: {len(memory_efficient)}")
        print(f"   Low Latency Tests: {len(low_latency)}")
        print(f"   Average Improvement: {avg_improvement:.1f}%")
        print(f"   Report saved to: {report_filename}")

        return report

async def main():
    """Run the performance benchmark suite"""
    benchmark = PerformanceBenchmarkTest()

    try:
        report = await benchmark.run_all_benchmarks()

        if report.get("benchmark_summary", {}).get("total_benchmarks", 0) > 0:
            print("\n🎉 Performance Benchmark Suite: SUCCESS")
            return 0
        else:
            print("\n⚠️ Performance Benchmark Suite: NO BENCHMARKS COMPLETED")
            return 1

    except Exception as e:
        print(f"\n❌ Performance Benchmark Suite: FAILED - {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
