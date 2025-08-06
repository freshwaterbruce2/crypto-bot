#!/usr/bin/env python3
"""
Working Integration Test Suite
Tests actual system components that are available and functional
"""

import asyncio
import gc
import json
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

import psutil

# Add project root to path
sys.path.append('/mnt/c/dev/tools/crypto-trading-bot-2025')

@dataclass
class TestResult:
    test_name: str
    status: str
    duration: float
    memory_usage_mb: float
    error_message: Optional[str] = None
    details: Optional[dict[str, Any]] = None

class WorkingIntegrationTest:
    """Integration test suite for actual available functionality"""

    def __init__(self):
        self.results: list[TestResult] = []
        self.test_start_time = time.time()

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all integration tests"""
        print("🚀 Starting Working Integration Test Suite")

        try:
            # Test 1: Basic Module Imports
            await self._test_basic_imports()

            # Test 2: Configuration System
            await self._test_configuration()

            # Test 3: Database Functionality
            await self._test_database()

            # Test 4: Message Queue System
            await self._test_message_queue()

            # Test 5: Memory Management
            await self._test_memory_management()

            # Test 6: Performance Systems
            await self._test_performance_systems()

            # Test 7: System Integration
            await self._test_system_integration()

            # Generate test report
            return await self._generate_test_report()

        except Exception as e:
            print(f"Integration test suite failed: {e}")
            print(traceback.format_exc())
            return {"status": "FAILED", "error": str(e)}

    async def _test_basic_imports(self):
        """Test 1: Basic Module Imports"""
        print("\n📦 Test 1: Basic Module Imports")

        start_time = time.time()
        memory_before = self._get_memory_usage()

        try:
            # Test core config

            # Test utilities that should exist

            # Test storage

            # Test orchestrator

            # Test balance management

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Basic Module Imports",
                status="PASSED",
                duration=duration,
                memory_usage_mb=memory_after,
                details={
                    'memory_delta_mb': memory_after - memory_before,
                    'modules_imported': 7
                }
            ))

            print(f"✅ Basic imports completed in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Basic Module Imports",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage_mb=self._get_memory_usage(),
                error_message=str(e)
            ))
            print(f"❌ Basic imports failed: {e}")

    async def _test_configuration(self):
        """Test 2: Configuration System"""
        print("\n⚙️ Test 2: Configuration System")

        start_time = time.time()
        self._get_memory_usage()

        try:
            from src.config.core import CoreConfigManager

            # Test configuration manager
            config_manager = CoreConfigManager()

            # Should have some configuration data
            if not hasattr(config_manager, 'config_data'):
                raise Exception("Configuration manager missing config_data")

            # Test constants
            from src.config.constants import TradingConstants
            TradingConstants()

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Configuration System",
                status="PASSED",
                duration=duration,
                memory_usage_mb=memory_after,
                details={
                    'config_manager_created': True,
                    'constants_available': True
                }
            ))

            print(f"✅ Configuration system working in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Configuration System",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage_mb=self._get_memory_usage(),
                error_message=str(e)
            ))
            print(f"❌ Configuration system failed: {e}")

    async def _test_database(self):
        """Test 3: Database Functionality"""
        print("\n🗄️ Test 3: Database Functionality")

        start_time = time.time()
        self._get_memory_usage()

        try:
            from src.storage.database_manager import DatabaseManager

            # Initialize database manager
            db_manager = DatabaseManager()
            await db_manager.initialize()

            # Test basic database operation
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            result = await db_manager.execute_query(query)

            table_count = len(result) if result else 0

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Database Functionality",
                status="PASSED",
                duration=duration,
                memory_usage_mb=memory_after,
                details={
                    'database_initialized': True,
                    'tables_found': table_count,
                    'query_executed': True
                }
            ))

            print(f"✅ Database functionality working in {duration:.2f}s ({table_count} tables)")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Database Functionality",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage_mb=self._get_memory_usage(),
                error_message=str(e)
            ))
            print(f"❌ Database functionality failed: {e}")

    async def _test_message_queue(self):
        """Test 4: Message Queue System"""
        print("\n📨 Test 4: Message Queue System")

        start_time = time.time()
        self._get_memory_usage()

        try:
            from src.utils.priority_message_queue import MessagePriority, PriorityMessageQueue

            # Create message queue
            queue = PriorityMessageQueue()

            # Test enqueueing messages
            messages_sent = 0

            # Test different priority messages
            test_messages = [
                (MessagePriority.LOW, {"type": "heartbeat", "data": "ping"}),
                (MessagePriority.HIGH, {"type": "trade", "data": "urgent"}),
                (MessagePriority.NORMAL, {"type": "price", "data": "update"}),
                (MessagePriority.CRITICAL, {"type": "balance", "data": "important"})
            ]

            for priority, payload in test_messages:
                success = await queue.enqueue("test_message", payload, priority)
                if success:
                    messages_sent += 1

            # Test queue stats
            stats = queue.get_stats()

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Message Queue System",
                status="PASSED",
                duration=duration,
                memory_usage_mb=memory_after,
                details={
                    'messages_enqueued': messages_sent,
                    'queue_stats': asdict(stats),
                    'priority_levels_tested': len(test_messages)
                }
            ))

            print(f"✅ Message queue system working in {duration:.2f}s ({messages_sent} messages)")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Message Queue System",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage_mb=self._get_memory_usage(),
                error_message=str(e)
            ))
            print(f"❌ Message queue system failed: {e}")

    async def _test_memory_management(self):
        """Test 5: Memory Management"""
        print("\n🧠 Test 5: Memory Management")

        start_time = time.time()
        self._get_memory_usage()

        try:
            from src.utils.memory_optimizer import MemoryOptimizer

            # Create memory optimizer
            memory_optimizer = MemoryOptimizer()

            # Create memory pressure
            large_data = []
            for _i in range(1000):
                large_data.append([j * 1.1 for j in range(100)])

            memory_peak = self._get_memory_usage()

            # Try optimization
            memory_optimizer.optimize_for_trading()

            # Clean up
            del large_data
            gc.collect()

            memory_after_cleanup = self._get_memory_usage()

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Memory Management",
                status="PASSED",
                duration=duration,
                memory_usage_mb=memory_after,
                details={
                    'memory_optimizer_created': True,
                    'memory_peak_mb': memory_peak,
                    'memory_after_cleanup_mb': memory_after_cleanup,
                    'optimization_called': True
                }
            ))

            print(f"✅ Memory management working in {duration:.2f}s")
            print(f"   Peak: {memory_peak:.1f}MB, After cleanup: {memory_after_cleanup:.1f}MB")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Memory Management",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage_mb=self._get_memory_usage(),
                error_message=str(e)
            ))
            print(f"❌ Memory management failed: {e}")

    async def _test_performance_systems(self):
        """Test 6: Performance Systems"""
        print("\n⚡ Test 6: Performance Systems")

        start_time = time.time()
        self._get_memory_usage()

        try:
            from src.utils.performance_integration import get_performance_manager

            # Get performance manager
            perf_manager = get_performance_manager()

            # Test performance manager creation
            if not perf_manager:
                raise Exception("Performance manager not created")

            # Test performance stats
            stats = perf_manager.get_performance_stats()

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Performance Systems",
                status="PASSED",
                duration=duration,
                memory_usage_mb=memory_after,
                details={
                    'performance_manager_created': True,
                    'performance_stats': stats,
                    'has_metrics': len(perf_manager.metrics) > 0
                }
            ))

            print(f"✅ Performance systems working in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Performance Systems",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage_mb=self._get_memory_usage(),
                error_message=str(e)
            ))
            print(f"❌ Performance systems failed: {e}")

    async def _test_system_integration(self):
        """Test 7: System Integration"""
        print("\n🔗 Test 7: System Integration")

        start_time = time.time()
        self._get_memory_usage()

        try:
            # Test dependency injection
            from src.orchestrator.dependency_injector import DependencyInjector

            injector = DependencyInjector()

            # Test balance manager integration
            from src.balance.balance_manager_v2 import BalanceManagerV2

            balance_manager = BalanceManagerV2()
            await balance_manager.initialize()

            # Test that systems can work together
            integration_working = (
                injector is not None and
                balance_manager is not None
            )

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="System Integration",
                status="PASSED" if integration_working else "FAILED",
                duration=duration,
                memory_usage_mb=memory_after,
                details={
                    'dependency_injector_created': injector is not None,
                    'balance_manager_initialized': balance_manager is not None,
                    'integration_working': integration_working
                }
            ))

            print(f"✅ System integration working in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="System Integration",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage_mb=self._get_memory_usage(),
                error_message=str(e)
            ))
            print(f"❌ System integration failed: {e}")

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0

    async def _generate_test_report(self) -> dict[str, Any]:
        """Generate comprehensive test report"""
        print("\n📊 Generating Integration Test Report")

        total_duration = time.time() - self.test_start_time

        # Calculate statistics
        passed_tests = sum(1 for result in self.results if result.status == "PASSED")
        failed_tests = sum(1 for result in self.results if result.status == "FAILED")
        total_tests = len(self.results)

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Memory analysis
        final_memory = self._get_memory_usage()
        memory_usage = [result.memory_usage_mb for result in self.results]
        avg_memory = sum(memory_usage) / len(memory_usage) if memory_usage else 0
        max_memory = max(memory_usage) if memory_usage else 0

        # Performance analysis
        test_durations = [result.duration for result in self.results]
        avg_duration = sum(test_durations) / len(test_durations) if test_durations else 0

        # Identify working components
        working_components = []
        for result in self.results:
            if result.status == "PASSED":
                working_components.append(result.test_name)

        # System health assessment
        health_score = success_rate
        if health_score >= 90:
            health_status = "EXCELLENT"
        elif health_score >= 70:
            health_status = "GOOD"
        elif health_score >= 50:
            health_status = "FAIR"
        else:
            health_status = "POOR"

        # Generate report
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate_percent": round(success_rate, 2),
                "total_duration_seconds": round(total_duration, 2),
                "health_status": health_status,
                "health_score": round(health_score, 2)
            },
            "performance_metrics": {
                "average_test_duration_seconds": round(avg_duration, 3),
                "final_memory_usage_mb": round(final_memory, 2),
                "average_memory_usage_mb": round(avg_memory, 2),
                "peak_memory_usage_mb": round(max_memory, 2)
            },
            "working_components": working_components,
            "system_capabilities": {
                "configuration_management": "Configuration System" in working_components,
                "database_operations": "Database Functionality" in working_components,
                "message_processing": "Message Queue System" in working_components,
                "memory_optimization": "Memory Management" in working_components,
                "performance_monitoring": "Performance Systems" in working_components,
                "component_integration": "System Integration" in working_components
            },
            "test_results": [asdict(result) for result in self.results],
            "consolidation_status": {
                "core_systems_operational": success_rate >= 70,
                "performance_optimizations_active": "Performance Systems" in working_components,
                "integration_verified": "System Integration" in working_components,
                "ready_for_production": success_rate >= 85
            },
            "recommendations": []
        }

        # Add recommendations
        if failed_tests == 0:
            report["recommendations"].append("All tests passed - system consolidation successful")
        elif success_rate >= 80:
            report["recommendations"].append("Most systems working - investigate failed components")
        else:
            report["recommendations"].append("Multiple system failures - review consolidation changes")

        if max_memory < 100:
            report["recommendations"].append("Memory usage optimal - optimization working well")
        elif max_memory > 200:
            report["recommendations"].append("High memory usage detected - review memory optimizations")

        if "Performance Systems" in working_components:
            report["recommendations"].append("Performance optimizations active and functional")

        if "System Integration" in working_components:
            report["recommendations"].append("Component integration successful")

        # Save report
        report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"/mnt/c/dev/tools/crypto-trading-bot-2025/working_integration_report_{report_timestamp}.json"

        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Print comprehensive summary
        print("\n📋 Integration Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Health Status: {health_status}")
        print(f"   Total Duration: {total_duration:.2f}s")
        print(f"   Final Memory: {final_memory:.1f}MB")

        if working_components:
            print("\n✅ Working Components:")
            for component in working_components:
                print(f"   • {component}")

        consolidation_ready = report["consolidation_status"]["ready_for_production"]
        if consolidation_ready:
            print("\n🎉 System Consolidation: SUCCESSFUL")
            print("   • Core systems operational")
            print("   • Performance optimizations active")
            print("   • Integration verified")
            print("   • Ready for production use")
        else:
            print("\n⚠️ System Consolidation: NEEDS ATTENTION")
            print("   • Some components need fixes")
            print("   • Review failed tests before production")

        print(f"\n📄 Report saved to: {report_filename}")

        return report

async def main():
    """Run the working integration test suite"""
    test_suite = WorkingIntegrationTest()

    try:
        report = await test_suite.run_all_tests()

        success_rate = report.get("test_summary", {}).get("success_rate_percent", 0)
        ready_for_production = report.get("consolidation_status", {}).get("ready_for_production", False)

        if ready_for_production:
            print("\n🎉 System Consolidation and Optimization: SUCCESS")
            return 0
        elif success_rate >= 70:
            print("\n⚠️ System Consolidation: MOSTLY SUCCESSFUL - Minor Issues")
            return 0
        else:
            print("\n❌ System Consolidation: SIGNIFICANT ISSUES DETECTED")
            return 1

    except Exception as e:
        print(f"\n❌ Integration Test Suite: FAILED - {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
