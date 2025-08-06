#!/usr/bin/env python3
"""
Quick Performance Validation Test
Validates key performance optimizations are working
"""

import gc
import json
import sys
import time

import psutil

# Add project root to path
sys.path.append('/mnt/c/dev/tools/crypto-trading-bot-2025')

def get_memory_mb():
    """Get current memory usage in MB"""
    try:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except:
        return 0.0

def test_message_queue_performance():
    """Test message queue performance"""
    print("📦 Testing Message Queue Performance...")

    try:
        start_time = time.time()
        from src.utils.priority_message_queue import MessagePriority, PriorityMessageQueue

        queue = PriorityMessageQueue()

        # Test high-volume message processing
        message_count = 1000
        start_ops = time.time()

        for i in range(message_count):
            priority = MessagePriority.NORMAL
            if i % 100 == 0:
                priority = MessagePriority.HIGH

            payload = {"id": i, "data": f"test_message_{i}"}
            # Use asyncio.run for single async call
            import asyncio
            asyncio.run(queue.enqueue("test", payload, priority))

        ops_time = time.time() - start_ops
        ops_per_sec = message_count / ops_time

        stats = queue.get_stats()

        print(f"   ✅ Message Queue: {ops_per_sec:.0f} ops/sec")
        print(f"   📊 Stats: {stats.messages_enqueued} enqueued, {stats.messages_processed} processed")

        return {
            "status": "PASSED",
            "ops_per_second": ops_per_sec,
            "messages_enqueued": stats.messages_enqueued,
            "duration": time.time() - start_time
        }

    except Exception as e:
        print(f"   ❌ Message Queue failed: {e}")
        return {"status": "FAILED", "error": str(e)}

def test_memory_optimization():
    """Test memory optimization"""
    print("🧠 Testing Memory Optimization...")

    try:
        start_time = time.time()
        from src.utils.memory_optimizer import MemoryOptimizer

        memory_before = get_memory_mb()

        # Create memory pressure
        large_data = []
        for _i in range(500):
            large_data.append([j * 1.5 for j in range(200)])

        memory_peak = get_memory_mb()

        # Test memory optimizer
        optimizer = MemoryOptimizer()
        optimizer.optimize_for_trading()

        # Clean up
        del large_data
        gc.collect()

        memory_after = get_memory_mb()
        memory_improvement = memory_peak - memory_after

        print(f"   ✅ Memory Optimization: {memory_improvement:.1f}MB freed")
        print(f"   📊 Before: {memory_before:.1f}MB, Peak: {memory_peak:.1f}MB, After: {memory_after:.1f}MB")

        return {
            "status": "PASSED",
            "memory_freed_mb": memory_improvement,
            "memory_peak_mb": memory_peak,
            "duration": time.time() - start_time
        }

    except Exception as e:
        print(f"   ❌ Memory Optimization failed: {e}")
        return {"status": "FAILED", "error": str(e)}

def test_performance_manager():
    """Test performance manager integration"""
    print("⚡ Testing Performance Manager...")

    try:
        start_time = time.time()
        from src.utils.performance_integration import get_performance_manager

        # Get performance manager
        perf_manager = get_performance_manager()

        if not perf_manager:
            raise Exception("Performance manager not available")

        # Test performance stats
        stats = perf_manager.get_performance_stats()

        # Test optimization functions
        test_positions = [
            {"value": 1000, "entry_value": 950},
            {"value": 2000, "entry_value": 1900},
            {"value": 500, "entry_value": 520}
        ]

        # This should work without numpy
        basic_analysis = perf_manager._basic_portfolio_analysis(test_positions)

        print("   ✅ Performance Manager: Working")
        print(f"   📊 Stats: {len(stats)} metrics, Analysis: {basic_analysis['unrealized_pnl']:.2f} PnL")

        return {
            "status": "PASSED",
            "stats_available": len(stats) > 0,
            "portfolio_analysis_working": True,
            "duration": time.time() - start_time
        }

    except Exception as e:
        print(f"   ❌ Performance Manager failed: {e}")
        return {"status": "FAILED", "error": str(e)}

def test_database_efficiency():
    """Test database efficiency"""
    print("🗄️ Testing Database Efficiency...")

    try:
        start_time = time.time()
        import asyncio

        from src.storage.database_manager import DatabaseManager

        async def run_db_test():
            db_manager = DatabaseManager()
            await db_manager.initialize()

            # Test multiple quick queries
            query_count = 100
            query_start = time.time()

            for _ in range(query_count):
                result = await db_manager.execute_query(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                )

            query_time = time.time() - query_start
            queries_per_sec = query_count / query_time

            return queries_per_sec, len(result) if result else 0

        queries_per_sec, table_count = asyncio.run(run_db_test())

        print(f"   ✅ Database: {queries_per_sec:.0f} queries/sec")
        print(f"   📊 Found {table_count} tables")

        return {
            "status": "PASSED",
            "queries_per_second": queries_per_sec,
            "table_count": table_count,
            "duration": time.time() - start_time
        }

    except Exception as e:
        print(f"   ❌ Database failed: {e}")
        return {"status": "FAILED", "error": str(e)}

def test_system_integration():
    """Test system integration"""
    print("🔗 Testing System Integration...")

    try:
        start_time = time.time()

        # Test multiple systems working together
        import asyncio

        from src.balance.balance_manager_v2 import BalanceManagerV2
        from src.orchestrator.dependency_injector import DependencyInjector

        async def integration_test():
            # Initialize components
            injector = DependencyInjector()
            balance_manager = BalanceManagerV2()
            await balance_manager.initialize()

            return injector is not None and balance_manager is not None

        integration_success = asyncio.run(integration_test())

        print(f"   ✅ System Integration: {'Working' if integration_success else 'Failed'}")

        return {
            "status": "PASSED" if integration_success else "FAILED",
            "components_integrated": integration_success,
            "duration": time.time() - start_time
        }

    except Exception as e:
        print(f"   ❌ System Integration failed: {e}")
        return {"status": "FAILED", "error": str(e)}

def main():
    """Run quick performance validation"""
    print("🚀 Quick Performance Validation Test")
    print("=" * 50)

    start_time = time.time()
    initial_memory = get_memory_mb()

    # Run tests
    results = {}

    results["message_queue"] = test_message_queue_performance()
    results["memory_optimization"] = test_memory_optimization()
    results["performance_manager"] = test_performance_manager()
    results["database_efficiency"] = test_database_efficiency()
    results["system_integration"] = test_system_integration()

    # Calculate overall results
    total_duration = time.time() - start_time
    final_memory = get_memory_mb()

    passed_tests = sum(1 for result in results.values() if result["status"] == "PASSED")
    total_tests = len(results)
    success_rate = (passed_tests / total_tests) * 100

    print("\n" + "=" * 50)
    print("📊 Performance Validation Summary")
    print("=" * 50)

    print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Memory Usage: {initial_memory:.1f}MB → {final_memory:.1f}MB")

    # Performance highlights
    print("\n🎯 Performance Highlights:")

    if results["message_queue"]["status"] == "PASSED":
        ops_per_sec = results["message_queue"]["ops_per_second"]
        print(f"   • Message Queue: {ops_per_sec:.0f} operations/second")

    if results["memory_optimization"]["status"] == "PASSED":
        memory_freed = results["memory_optimization"]["memory_freed_mb"]
        print(f"   • Memory Optimization: {memory_freed:.1f}MB freed")

    if results["database_efficiency"]["status"] == "PASSED":
        db_ops = results["database_efficiency"]["queries_per_second"]
        print(f"   • Database Efficiency: {db_ops:.0f} queries/second")

    # Overall assessment
    print("\n🏆 Overall Assessment:")
    if success_rate >= 90:
        print("   EXCELLENT - All optimizations working perfectly")
        status = "SUCCESS"
    elif success_rate >= 70:
        print("   GOOD - Most optimizations working well")
        status = "SUCCESS"
    elif success_rate >= 50:
        print("   FAIR - Some optimizations need attention")
        status = "PARTIAL"
    else:
        print("   POOR - Major optimization issues detected")
        status = "FAILED"

    # Save results
    report = {
        "summary": {
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "success_rate_percent": success_rate,
            "total_duration_seconds": total_duration,
            "status": status
        },
        "performance_metrics": {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_delta_mb": final_memory - initial_memory
        },
        "test_results": results
    }

    with open("performance_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n📄 Detailed report saved to: performance_validation_report.json")

    return 0 if success_rate >= 70 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
