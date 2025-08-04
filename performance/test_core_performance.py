#!/usr/bin/env python3
"""
Core Performance Testing Framework Validation
=============================================

Tests the core performance testing framework components without dependencies on
the actual trading bot components (which may have API interface differences).

This validates that the performance testing infrastructure is working correctly.
"""

import asyncio
import time
import logging
from pathlib import Path
import sys
import os

# Add performance module to path
sys.path.append(str(Path(__file__).parent))

# Import core performance components
from latency_analyzer import CriticalPathLatencyAnalyzer
from memory_profiler_simple import AdvancedMemoryProfiler

logger = logging.getLogger(__name__)


async def test_latency_tracking():
    """Test latency tracking functionality"""
    print("Testing latency tracking...")
    
    analyzer = CriticalPathLatencyAnalyzer()
    
    # Test basic latency tracking
    with analyzer.track_latency('test_component', 'test_operation'):
        await asyncio.sleep(0.01)  # 10ms operation
    
    # Test concurrent latency tracking
    async def tracked_operation(operation_id: int):
        with analyzer.track_latency('concurrent_test', f'operation_{operation_id}'):
            await asyncio.sleep(0.005)  # 5ms operation
    
    # Run 10 concurrent operations
    tasks = [tracked_operation(i) for i in range(10)]
    await asyncio.gather(*tasks)
    
    # Validate measurements
    measurements = analyzer.measurements
    print(f"✅ Recorded {len(measurements)} latency measurements")
    
    if len(measurements) >= 11:  # 1 + 10 operations
        avg_latency = sum(m.latency_ms for m in measurements) / len(measurements)
        print(f"✅ Average latency: {avg_latency:.2f}ms")
        return True
    else:
        print("❌ Expected at least 11 measurements")
        return False


async def test_memory_profiling():
    """Test memory profiling functionality"""
    print("Testing memory profiling...")
    
    profiler = AdvancedMemoryProfiler(sampling_interval=0.1)
    
    # Start profiling
    profiling_task = asyncio.create_task(profiler.start_profiling())
    
    # Simulate memory usage
    data = []
    for i in range(1000):
        data.append({
            'id': i,
            'data': list(range(50)),
            'timestamp': time.time()
        })
        
        if i % 100 == 0:
            await asyncio.sleep(0.01)
    
    # Let profiling run for a bit
    await asyncio.sleep(1.0)
    
    # Stop profiling
    await profiler.stop_profiling()
    
    # Get report
    report = profiler.get_analysis_report()
    
    if 'memory_statistics' in report and report['snapshot_count'] > 0:
        print(f"✅ Memory profiling completed: {report['snapshot_count']} snapshots")
        print(f"✅ Peak memory: {report['memory_statistics']['peak_mb']:.1f}MB")
        return True
    else:
        print("❌ Memory profiling failed")
        return False


async def test_performance_patterns():
    """Test performance pattern detection"""
    print("Testing performance pattern detection...")
    
    analyzer = CriticalPathLatencyAnalyzer()
    
    # Simulate different performance patterns
    
    # Fast operations
    for i in range(10):
        with analyzer.track_latency('fast_ops', 'quick_calculation'):
            await asyncio.sleep(0.001)  # 1ms
    
    # Medium operations
    for i in range(5):
        with analyzer.track_latency('medium_ops', 'moderate_calculation'):
            await asyncio.sleep(0.01)  # 10ms
    
    # Slow operations
    for i in range(2):
        with analyzer.track_latency('slow_ops', 'heavy_calculation'):
            await asyncio.sleep(0.05)  # 50ms
    
    # Analyze patterns
    critical_paths = await analyzer.analyze_critical_paths()
    
    if len(critical_paths) > 0:
        print(f"✅ Identified {len(critical_paths)} critical paths")
        
        for path in critical_paths:
            print(f"  - {path.path_name}: {path.total_latency_ms:.2f}ms total")
        
        return True
    else:
        print("❌ No critical paths identified")
        return False


async def test_concurrent_performance():
    """Test concurrent performance monitoring"""
    print("Testing concurrent performance monitoring...")
    
    analyzer = CriticalPathLatencyAnalyzer()
    
    async def worker(worker_id: int, ops_count: int):
        """Worker function that performs operations"""
        for i in range(ops_count):
            with analyzer.track_latency(f'worker_{worker_id}', f'operation_{i}'):
                # Simulate variable processing time
                processing_time = 0.002 + (i % 5) * 0.001  # 2-6ms
                await asyncio.sleep(processing_time)
    
    # Run multiple workers concurrently
    workers = [
        worker(0, 20),  # Worker 0: 20 operations
        worker(1, 15),  # Worker 1: 15 operations
        worker(2, 25),  # Worker 2: 25 operations
    ]
    
    start_time = time.perf_counter()
    await asyncio.gather(*workers)
    end_time = time.perf_counter()
    
    total_time = end_time - start_time
    total_measurements = len(analyzer.measurements)
    
    print(f"✅ Processed {total_measurements} operations in {total_time:.3f}s")
    print(f"✅ Throughput: {total_measurements / total_time:.1f} ops/sec")
    
    # Validate that we got all expected measurements
    expected_measurements = 20 + 15 + 25  # 60 total
    if total_measurements == expected_measurements:
        print(f"✅ All {expected_measurements} measurements recorded correctly")
        return True
    else:
        print(f"❌ Expected {expected_measurements} measurements, got {total_measurements}")
        return False


async def test_error_handling():
    """Test error handling in performance monitoring"""
    print("Testing error handling...")
    
    analyzer = CriticalPathLatencyAnalyzer()
    
    # Test operation that raises an exception
    try:
        with analyzer.track_latency('error_test', 'failing_operation'):
            await asyncio.sleep(0.005)
            raise ValueError("Simulated error")
    except ValueError:
        pass  # Expected
    
    # Test that measurement was still recorded despite the error
    measurements = analyzer.measurements
    
    if len(measurements) == 1 and measurements[0].component == 'error_test':
        print("✅ Error handling works correctly - measurement recorded despite exception")
        return True
    else:
        print("❌ Error handling failed")
        return False


async def main():
    """Run all core performance tests"""
    print("="*80)
    print("🔧 CORE PERFORMANCE TESTING FRAMEWORK VALIDATION")
    print("="*80)
    
    # Configure logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    
    tests = [
        ("Latency Tracking", test_latency_tracking),
        ("Memory Profiling", test_memory_profiling),
        ("Performance Patterns", test_performance_patterns),
        ("Concurrent Performance", test_concurrent_performance),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 50)
        
        try:
            start_time = time.perf_counter()
            result = await test_func()
            end_time = time.perf_counter()
            
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED ({end_time - start_time:.2f}s)")
            else:
                print(f"❌ {test_name} FAILED ({end_time - start_time:.2f}s)")
                
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print(f"🎯 CORE PERFORMANCE TESTING RESULTS: {passed}/{total} PASSED")
    
    if passed == total:
        print("✅ All core performance tests PASSED!")
        print("\n🚀 Performance testing framework is ready for use:")
        print("   - Latency tracking system working correctly")
        print("   - Memory profiling system functional")
        print("   - Concurrent performance monitoring operational")
        print("   - Error handling robust")
        print("   - Performance pattern detection active")
        return 0
    else:
        print(f"❌ {total - passed} core performance tests FAILED")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))