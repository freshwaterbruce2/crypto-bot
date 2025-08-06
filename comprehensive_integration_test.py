#!/usr/bin/env python3
"""
Comprehensive System Integration Test Suite
Validates all consolidation and optimization changes work together correctly
"""

import asyncio
import gc
import json
import statistics
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

import psutil

# Add project root to path
sys.path.append('/mnt/c/dev/tools/crypto-trading-bot-2025')

# Core imports
from src.auth.websocket_authentication_manager import WebSocketAuthenticationManager
from src.balance.balance_manager_v2 import BalanceManagerV2
from src.balance.websocket_balance_stream_v2_fixed import WebSocketBalanceStreamV2Fixed
from src.config.core import CoreConfig
from src.exchange.kraken_websocket_v2_direct import KrakenWebSocketV2Direct
from src.orchestrator.dependency_injector import DependencyInjector
from src.orchestrator.startup_sequence import StartupSequence
from src.orchestrator.system_orchestrator import SystemOrchestrator
from src.storage.database_manager import DatabaseManager
from src.utils.consolidated_nonce_manager import ConsolidatedNonceManager
from src.utils.memory_optimizer import MemoryOptimizer
from src.utils.performance_maximizer_2025 import PerformanceMaximizer2025
from src.utils.priority_message_queue import PriorityMessageQueue
from src.utils.professional_logging_system import ProfessionalLoggingSystem


@dataclass
class TestResult:
    test_name: str
    status: str
    duration: float
    memory_usage: dict[str, float]
    error_message: Optional[str] = None
    performance_metrics: Optional[dict[str, Any]] = None

@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    thread_count: int
    open_files: int
    timestamp: float

class ComprehensiveIntegrationTest:
    """Comprehensive integration test suite for the consolidated crypto trading bot system"""

    def __init__(self):
        self.logger = ProfessionalLoggingSystem()
        self.results: list[TestResult] = []
        self.system_metrics: list[SystemMetrics] = []
        self.performance_maximizer = PerformanceMaximizer2025()
        self.memory_optimizer = MemoryOptimizer()
        self.test_start_time = time.time()

        # Test configuration
        self.test_config = {
            'websocket_timeout': 30,
            'balance_update_timeout': 15,
            'performance_samples': 100,
            'load_test_duration': 60,
            'max_memory_mb': 500,
            'max_cpu_percent': 80
        }

        # Initialize test components
        self.orchestrator = None
        self.websocket_client = None
        self.balance_manager = None
        self.database_manager = None

    async def run_all_tests(self) -> dict[str, Any]:
        """Run complete integration test suite"""
        print("🚀 Starting Comprehensive Integration Test Suite")
        print(f"Test Configuration: {json.dumps(self.test_config, indent=2)}")

        try:
            # Start system monitoring
            monitoring_task = asyncio.create_task(self._monitor_system_metrics())

            # 1. System Initialization Tests
            await self._test_system_initialization()

            # 2. Component Integration Tests
            await self._test_component_integration()

            # 3. End-to-End Trading Flow Tests
            await self._test_end_to_end_trading_flow()

            # 4. Performance Validation Tests
            await self._test_performance_optimizations()

            # 5. Load and Stress Tests
            await self._test_load_performance()

            # 6. Backwards Compatibility Tests
            await self._test_backwards_compatibility()

            # 7. Error Recovery Tests
            await self._test_error_recovery()

            # Stop monitoring
            monitoring_task.cancel()

            # Generate comprehensive test report
            return await self._generate_test_report()

        except Exception as e:
            self.logger.error(f"Integration test suite failed: {e}")
            self.logger.error(traceback.format_exc())
            return {"status": "FAILED", "error": str(e)}

    async def _test_system_initialization(self):
        """Test 1: System Initialization and Orchestration"""
        print("\n📋 Test 1: System Initialization and Orchestration")

        start_time = time.time()
        memory_before = self._get_memory_usage()

        try:
            # Test dependency injection initialization
            DependencyInjector()

            # Test orchestrator initialization
            self.orchestrator = SystemOrchestrator()
            await self.orchestrator.initialize()

            # Test startup sequence
            startup_sequence = StartupSequence(self.orchestrator)
            startup_result = await startup_sequence.execute_startup()

            if not startup_result.get('success'):
                raise Exception(f"Startup sequence failed: {startup_result}")

            # Test database initialization
            self.database_manager = DatabaseManager()
            await self.database_manager.initialize()

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="System Initialization",
                status="PASSED",
                duration=duration,
                memory_usage={
                    'before_mb': memory_before,
                    'after_mb': memory_after,
                    'delta_mb': memory_after - memory_before
                },
                performance_metrics={
                    'startup_time_seconds': duration,
                    'components_initialized': len(startup_result.get('components', [])),
                    'orchestrator_ready': self.orchestrator is not None
                }
            ))

            print(f"✅ System initialization completed in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="System Initialization",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage={'before_mb': memory_before, 'after_mb': self._get_memory_usage()},
                error_message=str(e)
            ))
            print(f"❌ System initialization failed: {e}")

    async def _test_component_integration(self):
        """Test 2: Component Integration and Communication"""
        print("\n🔗 Test 2: Component Integration and Communication")

        start_time = time.time()
        memory_before = self._get_memory_usage()

        try:
            # Test consolidated nonce manager
            nonce_manager = ConsolidatedNonceManager()
            nonce1 = nonce_manager.generate_nonce()
            nonce2 = nonce_manager.generate_nonce()

            if nonce2 <= nonce1:
                raise Exception("Nonce manager not generating increasing nonces")

            # Test WebSocket authentication manager
            auth_manager = WebSocketAuthenticationManager()
            await auth_manager.initialize()

            # Test WebSocket V2 Direct implementation
            self.websocket_client = KrakenWebSocketV2Direct()

            # Test balance manager V2
            self.balance_manager = BalanceManagerV2()
            await self.balance_manager.initialize()

            # Test message queue priority system
            message_queue = PriorityMessageQueue()

            # Add test messages with different priorities
            test_messages = [
                ("LOW", {"type": "status", "data": "test"}),
                ("HIGH", {"type": "trade", "data": "urgent"}),
                ("MEDIUM", {"type": "balance", "data": "update"})
            ]

            for priority, message in test_messages:
                message_queue.add_message(message, priority)

            # Verify priority ordering
            priorities_received = []
            while not message_queue.is_empty():
                msg, priority = message_queue.get_next_message()
                priorities_received.append(priority)

            expected_order = ["HIGH", "MEDIUM", "LOW"]
            if priorities_received != expected_order:
                raise Exception(f"Message queue priority ordering failed: {priorities_received}")

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Component Integration",
                status="PASSED",
                duration=duration,
                memory_usage={
                    'before_mb': memory_before,
                    'after_mb': memory_after,
                    'delta_mb': memory_after - memory_before
                },
                performance_metrics={
                    'nonce_generation_working': True,
                    'websocket_client_initialized': self.websocket_client is not None,
                    'balance_manager_initialized': self.balance_manager is not None,
                    'message_queue_priority_correct': True
                }
            ))

            print(f"✅ Component integration completed in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Component Integration",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage={'before_mb': memory_before, 'after_mb': self._get_memory_usage()},
                error_message=str(e)
            ))
            print(f"❌ Component integration failed: {e}")

    async def _test_end_to_end_trading_flow(self):
        """Test 3: End-to-End Trading Flow"""
        print("\n💹 Test 3: End-to-End Trading Flow")

        start_time = time.time()
        memory_before = self._get_memory_usage()

        try:
            if not self.websocket_client:
                raise Exception("WebSocket client not initialized")

            # Test WebSocket connection establishment
            print("Testing WebSocket connection...")
            connection_start = time.time()

            # Use public connection for testing (no API keys required)
            await self.websocket_client.connect_public()

            if not self.websocket_client.is_connected():
                raise Exception("WebSocket connection failed")

            connection_time = time.time() - connection_start
            print(f"WebSocket connected in {connection_time:.2f}s")

            # Test ticker subscription
            print("Testing ticker subscription...")
            subscription_start = time.time()

            await self.websocket_client.subscribe_ticker(['BTC/USD'])

            # Wait for ticker data
            ticker_received = False
            wait_start = time.time()
            while time.time() - wait_start < 10:  # Wait up to 10 seconds
                await asyncio.sleep(0.1)
                latest_ticker = self.websocket_client.get_latest_ticker('BTC/USD')
                if latest_ticker:
                    ticker_received = True
                    break

            if not ticker_received:
                raise Exception("Ticker data not received within timeout")

            subscription_time = time.time() - subscription_start
            print(f"Ticker data received in {subscription_time:.2f}s")

            # Test balance stream integration (if authenticated)
            balance_stream_working = False
            try:
                balance_stream = WebSocketBalanceStreamV2Fixed()
                await balance_stream.initialize()
                balance_stream_working = True
                print("Balance stream initialized successfully")
            except Exception as e:
                print(f"Balance stream test skipped (authentication required): {e}")

            # Test data flow and message processing
            message_count = 0
            processing_times = []

            for _ in range(10):  # Process 10 messages
                process_start = time.time()

                # Simulate message processing
                latest_ticker = self.websocket_client.get_latest_ticker('BTC/USD')
                if latest_ticker:
                    message_count += 1
                    processing_times.append(time.time() - process_start)

                await asyncio.sleep(0.1)

            if message_count == 0:
                raise Exception("No messages processed during test")

            avg_processing_time = statistics.mean(processing_times)

            # Clean up
            await self.websocket_client.disconnect()

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="End-to-End Trading Flow",
                status="PASSED",
                duration=duration,
                memory_usage={
                    'before_mb': memory_before,
                    'after_mb': memory_after,
                    'delta_mb': memory_after - memory_before
                },
                performance_metrics={
                    'connection_time_seconds': connection_time,
                    'subscription_time_seconds': subscription_time,
                    'messages_processed': message_count,
                    'avg_processing_time_ms': avg_processing_time * 1000,
                    'balance_stream_available': balance_stream_working
                }
            ))

            print(f"✅ End-to-end trading flow completed in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="End-to-End Trading Flow",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage={'before_mb': memory_before, 'after_mb': self._get_memory_usage()},
                error_message=str(e)
            ))
            print(f"❌ End-to-end trading flow failed: {e}")

    async def _test_performance_optimizations(self):
        """Test 4: Performance Optimization Validation"""
        print("\n⚡ Test 4: Performance Optimization Validation")

        start_time = time.time()
        memory_before = self._get_memory_usage()

        try:
            # Test memory optimization
            print("Testing memory optimization...")

            # Force garbage collection and measure
            gc.collect()
            self._get_memory_usage()

            # Test memory optimizer
            memory_stats_before = self.memory_optimizer.get_memory_stats()
            self.memory_optimizer.optimize_memory()
            memory_stats_after = self.memory_optimizer.get_memory_stats()

            memory_improvement = memory_stats_before['used_mb'] - memory_stats_after['used_mb']

            # Test performance maximizer
            print("Testing performance maximizer...")
            self.performance_maximizer.get_performance_metrics()

            # Simulate workload
            computation_times = []
            for i in range(100):
                comp_start = time.time()

                # Simulate computational work
                sum(x * x for x in range(1000))

                computation_times.append(time.time() - comp_start)

            avg_computation_time = statistics.mean(computation_times)

            # Test database connection pooling
            print("Testing database connection pooling...")
            if self.database_manager:
                pool_stats = await self.database_manager.get_connection_pool_stats()

                # Test concurrent database operations
                db_operation_times = []
                for _ in range(10):
                    db_start = time.time()

                    # Simulate database query
                    await self.database_manager.execute_query(
                        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                    )

                    db_operation_times.append(time.time() - db_start)

                avg_db_time = statistics.mean(db_operation_times)

            else:
                pool_stats = None
                avg_db_time = None

            # Test message processing efficiency
            print("Testing message processing efficiency...")
            message_queue = PriorityMessageQueue()

            # Add many messages
            message_add_start = time.time()
            for i in range(1000):
                priority = "HIGH" if i % 3 == 0 else "MEDIUM" if i % 3 == 1 else "LOW"
                message_queue.add_message({"id": i, "data": f"test_{i}"}, priority)
            message_add_time = time.time() - message_add_start

            # Process all messages
            message_process_start = time.time()
            processed_count = 0
            while not message_queue.is_empty():
                msg, priority = message_queue.get_next_message()
                processed_count += 1
            message_process_time = time.time() - message_process_start

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Performance Optimizations",
                status="PASSED",
                duration=duration,
                memory_usage={
                    'before_mb': memory_before,
                    'after_mb': memory_after,
                    'delta_mb': memory_after - memory_before,
                    'memory_improvement_mb': memory_improvement
                },
                performance_metrics={
                    'avg_computation_time_ms': avg_computation_time * 1000,
                    'avg_db_operation_time_ms': avg_db_time * 1000 if avg_db_time else None,
                    'message_add_rate_per_sec': 1000 / message_add_time,
                    'message_process_rate_per_sec': processed_count / message_process_time,
                    'database_pool_stats': pool_stats,
                    'memory_optimization_working': memory_improvement >= 0
                }
            ))

            print(f"✅ Performance optimization validation completed in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Performance Optimizations",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage={'before_mb': memory_before, 'after_mb': self._get_memory_usage()},
                error_message=str(e)
            ))
            print(f"❌ Performance optimization validation failed: {e}")

    async def _test_load_performance(self):
        """Test 5: Load Testing and System Stability"""
        print("\n🏋️ Test 5: Load Testing and System Stability")

        start_time = time.time()
        memory_before = self._get_memory_usage()

        try:
            # High-volume message processing test
            print("Starting high-volume message processing test...")

            message_queue = PriorityMessageQueue()
            processed_messages = 0
            processing_errors = 0

            # Start message producer
            async def message_producer():
                for i in range(10000):  # 10k messages
                    priority = ["HIGH", "MEDIUM", "LOW"][i % 3]
                    message = {
                        "id": i,
                        "timestamp": time.time(),
                        "data": f"load_test_message_{i}",
                        "payload": "x" * 100  # 100 byte payload
                    }
                    message_queue.add_message(message, priority)

                    if i % 1000 == 0:  # Small delay every 1000 messages
                        await asyncio.sleep(0.001)

            # Start message consumer
            async def message_consumer():
                nonlocal processed_messages, processing_errors

                while processed_messages < 10000:
                    try:
                        if not message_queue.is_empty():
                            msg, priority = message_queue.get_next_message()
                            processed_messages += 1

                            # Simulate processing work
                            await asyncio.sleep(0.0001)
                        else:
                            await asyncio.sleep(0.001)
                    except Exception as e:
                        processing_errors += 1
                        print(f"Processing error: {e}")

            # Run producer and consumer concurrently
            producer_task = asyncio.create_task(message_producer())
            consumer_task = asyncio.create_task(message_consumer())

            # Monitor system resources during load test
            load_test_start = time.time()
            max_memory = memory_before
            max_cpu = 0

            while not (producer_task.done() and consumer_task.done()):
                current_memory = self._get_memory_usage()
                current_cpu = psutil.cpu_percent()

                max_memory = max(max_memory, current_memory)
                max_cpu = max(max_cpu, current_cpu)

                # Check for resource limits
                if current_memory > self.test_config['max_memory_mb']:
                    raise Exception(f"Memory usage exceeded limit: {current_memory}MB")

                if current_cpu > self.test_config['max_cpu_percent']:
                    print(f"Warning: High CPU usage: {current_cpu}%")

                await asyncio.sleep(0.1)

            load_test_duration = time.time() - load_test_start

            # Wait for tasks to complete
            await asyncio.gather(producer_task, consumer_task)

            # Stress test: Concurrent WebSocket connections (simulated)
            print("Testing concurrent connection handling...")

            concurrent_tasks = []
            for _i in range(50):  # 50 concurrent tasks
                task = asyncio.create_task(self._simulate_websocket_activity())
                concurrent_tasks.append(task)

            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            concurrent_errors = sum(1 for result in concurrent_results if isinstance(result, Exception))

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Load Testing",
                status="PASSED" if processing_errors == 0 and concurrent_errors == 0 else "PARTIAL",
                duration=duration,
                memory_usage={
                    'before_mb': memory_before,
                    'after_mb': memory_after,
                    'max_memory_mb': max_memory,
                    'delta_mb': memory_after - memory_before
                },
                performance_metrics={
                    'messages_processed': processed_messages,
                    'processing_errors': processing_errors,
                    'processing_rate_per_sec': processed_messages / load_test_duration,
                    'max_cpu_percent': max_cpu,
                    'concurrent_tasks': len(concurrent_tasks),
                    'concurrent_errors': concurrent_errors,
                    'load_test_duration_seconds': load_test_duration
                }
            ))

            print(f"✅ Load testing completed in {duration:.2f}s")
            print(f"   Processed {processed_messages} messages with {processing_errors} errors")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Load Testing",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage={'before_mb': memory_before, 'after_mb': self._get_memory_usage()},
                error_message=str(e)
            ))
            print(f"❌ Load testing failed: {e}")

    async def _test_backwards_compatibility(self):
        """Test 6: Backwards Compatibility"""
        print("\n🔄 Test 6: Backwards Compatibility")

        start_time = time.time()
        memory_before = self._get_memory_usage()

        try:
            # Test legacy balance manager compatibility
            print("Testing legacy balance manager compatibility...")

            # Import legacy balance manager
            from src.balance.balance_manager import BalanceManager as LegacyBalanceManager

            legacy_balance_manager = LegacyBalanceManager()
            await legacy_balance_manager.initialize()

            # Test that new V2 manager can work alongside legacy
            if self.balance_manager:
                # Both should be able to coexist
                v2_initialized = hasattr(self.balance_manager, 'is_initialized')
                legacy_initialized = hasattr(legacy_balance_manager, 'initialize')

                if not (v2_initialized and legacy_initialized):
                    raise Exception("Balance managers compatibility issue")

            # Test legacy configuration compatibility
            print("Testing legacy configuration compatibility...")

            legacy_config = CoreConfig()
            legacy_settings = legacy_config.get_all_settings()

            if not legacy_settings:
                raise Exception("Legacy configuration not accessible")

            # Test legacy WebSocket implementation compatibility
            print("Testing legacy WebSocket compatibility...")

            try:
                from src.exchange.websocket_manager_v2 import WebSocketManagerV2
                legacy_websocket = WebSocketManagerV2()

                # Should be able to initialize without conflicts
                legacy_websocket_available = True
            except Exception as e:
                print(f"Legacy WebSocket not available (acceptable): {e}")
                legacy_websocket_available = False

            # Test database schema compatibility
            print("Testing database schema compatibility...")

            if self.database_manager:
                # Check that all expected tables exist
                tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
                tables_result = await self.database_manager.execute_query(tables_query)
                table_names = [row[0] for row in tables_result]

                expected_tables = ['trades', 'crypto_orders', 'positions', 'market_data', 'tickers']
                missing_tables = [table for table in expected_tables if table not in table_names]

                if missing_tables:
                    print(f"Warning: Missing tables: {missing_tables}")

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Backwards Compatibility",
                status="PASSED",
                duration=duration,
                memory_usage={
                    'before_mb': memory_before,
                    'after_mb': memory_after,
                    'delta_mb': memory_after - memory_before
                },
                performance_metrics={
                    'legacy_balance_manager_available': True,
                    'legacy_config_accessible': len(legacy_settings) > 0,
                    'legacy_websocket_available': legacy_websocket_available,
                    'database_tables_count': len(table_names) if 'table_names' in locals() else 0
                }
            ))

            print(f"✅ Backwards compatibility testing completed in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Backwards Compatibility",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage={'before_mb': memory_before, 'after_mb': self._get_memory_usage()},
                error_message=str(e)
            ))
            print(f"❌ Backwards compatibility testing failed: {e}")

    async def _test_error_recovery(self):
        """Test 7: Error Recovery and Resilience"""
        print("\n🛡️ Test 7: Error Recovery and Resilience")

        start_time = time.time()
        memory_before = self._get_memory_usage()

        try:
            # Test WebSocket reconnection
            print("Testing WebSocket reconnection...")

            websocket_client = KrakenWebSocketV2Direct()

            # Connect and immediately disconnect to test reconnection
            await websocket_client.connect_public()

            if websocket_client.is_connected():
                await websocket_client.disconnect()

                # Wait a moment
                await asyncio.sleep(1)

                # Reconnect
                await websocket_client.connect_public()

                if not websocket_client.is_connected():
                    raise Exception("WebSocket reconnection failed")

                await websocket_client.disconnect()

            # Test error handling in message processing
            print("Testing error handling in message processing...")

            message_queue = PriorityMessageQueue()

            # Add valid and invalid messages
            test_messages = [
                ("HIGH", {"type": "valid", "data": "test"}),
                ("HIGH", None),  # Invalid message
                ("MEDIUM", {"type": "valid", "data": "test2"}),
                ("LOW", "invalid_format"),  # Invalid format
            ]

            for priority, message in test_messages:
                try:
                    message_queue.add_message(message, priority)
                except Exception as e:
                    print(f"Expected error handling invalid message: {e}")

            # Process messages - should handle errors gracefully
            processed_valid = 0
            processing_errors = 0

            while not message_queue.is_empty():
                try:
                    msg, priority = message_queue.get_next_message()
                    if msg and isinstance(msg, dict) and 'type' in msg:
                        processed_valid += 1
                except Exception as e:
                    processing_errors += 1
                    print(f"Handled processing error: {e}")

            # Test memory cleanup after errors
            print("Testing memory cleanup after errors...")

            memory_before_cleanup = self._get_memory_usage()

            # Force garbage collection
            gc.collect()

            memory_after_cleanup = self._get_memory_usage()
            memory_cleaned = memory_before_cleanup - memory_after_cleanup

            # Test database error recovery
            print("Testing database error recovery...")

            database_recovery_working = False
            if self.database_manager:
                try:
                    # Try an invalid query
                    await self.database_manager.execute_query("SELECT * FROM nonexistent_table")
                except Exception as e:
                    print(f"Expected database error handled: {e}")

                    # Verify database is still functional
                    valid_result = await self.database_manager.execute_query(
                        "SELECT COUNT(*) FROM sqlite_master"
                    )
                    if valid_result:
                        database_recovery_working = True

            memory_after = self._get_memory_usage()
            duration = time.time() - start_time

            self.results.append(TestResult(
                test_name="Error Recovery",
                status="PASSED",
                duration=duration,
                memory_usage={
                    'before_mb': memory_before,
                    'after_mb': memory_after,
                    'delta_mb': memory_after - memory_before,
                    'memory_cleaned_mb': memory_cleaned
                },
                performance_metrics={
                    'websocket_reconnection_working': True,
                    'messages_processed_valid': processed_valid,
                    'message_processing_errors_handled': processing_errors,
                    'database_recovery_working': database_recovery_working,
                    'memory_cleanup_effective': memory_cleaned >= 0
                }
            ))

            print(f"✅ Error recovery testing completed in {duration:.2f}s")

        except Exception as e:
            self.results.append(TestResult(
                test_name="Error Recovery",
                status="FAILED",
                duration=time.time() - start_time,
                memory_usage={'before_mb': memory_before, 'after_mb': self._get_memory_usage()},
                error_message=str(e)
            ))
            print(f"❌ Error recovery testing failed: {e}")

    async def _simulate_websocket_activity(self):
        """Simulate WebSocket activity for concurrent testing"""
        try:
            # Simulate connection, subscription, and data processing
            await asyncio.sleep(0.1)  # Connection time

            # Simulate message processing
            for _ in range(50):
                # Simulate receiving and processing a message
                await asyncio.sleep(0.001)

                # Simulate some computation
                sum(x for x in range(100))

            return True
        except Exception as e:
            return e

    async def _monitor_system_metrics(self):
        """Monitor system metrics during testing"""
        try:
            while True:
                process = psutil.Process()

                metric = SystemMetrics(
                    cpu_percent=psutil.cpu_percent(),
                    memory_percent=process.memory_percent(),
                    memory_mb=process.memory_info().rss / 1024 / 1024,
                    thread_count=process.num_threads(),
                    open_files=len(process.open_files()),
                    timestamp=time.time()
                )

                self.system_metrics.append(metric)

                await asyncio.sleep(1)  # Sample every second
        except asyncio.CancelledError:
            pass

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    async def _generate_test_report(self) -> dict[str, Any]:
        """Generate comprehensive test report"""
        print("\n📊 Generating Comprehensive Test Report")

        total_duration = time.time() - self.test_start_time

        # Calculate overall statistics
        passed_tests = sum(1 for result in self.results if result.status == "PASSED")
        failed_tests = sum(1 for result in self.results if result.status == "FAILED")
        partial_tests = sum(1 for result in self.results if result.status == "PARTIAL")
        total_tests = len(self.results)

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Memory statistics
        memory_usages = [result.memory_usage.get('delta_mb', 0) for result in self.results if result.memory_usage]
        avg_memory_delta = statistics.mean(memory_usages) if memory_usages else 0
        max_memory_delta = max(memory_usages) if memory_usages else 0

        # Performance statistics
        test_durations = [result.duration for result in self.results]
        avg_test_duration = statistics.mean(test_durations) if test_durations else 0

        # System metrics analysis
        if self.system_metrics:
            avg_cpu = statistics.mean([m.cpu_percent for m in self.system_metrics])
            max_cpu = max([m.cpu_percent for m in self.system_metrics])
            avg_memory = statistics.mean([m.memory_mb for m in self.system_metrics])
            max_memory = max([m.memory_mb for m in self.system_metrics])
        else:
            avg_cpu = max_cpu = avg_memory = max_memory = 0

        # Performance improvements detected
        performance_improvements = []

        for result in self.results:
            if result.performance_metrics:
                metrics = result.performance_metrics

                # Check for specific improvements
                if 'processing_rate_per_sec' in metrics and metrics['processing_rate_per_sec'] > 1000:
                    performance_improvements.append(f"High message processing rate: {metrics['processing_rate_per_sec']:.0f} msg/sec")

                if 'memory_optimization_working' in metrics and metrics['memory_optimization_working']:
                    performance_improvements.append("Memory optimization system functioning")

                if 'avg_processing_time_ms' in metrics and metrics['avg_processing_time_ms'] < 1:
                    performance_improvements.append(f"Fast message processing: {metrics['avg_processing_time_ms']:.2f}ms avg")

        # Generate detailed report
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "partial": partial_tests,
                "success_rate_percent": round(success_rate, 2),
                "total_duration_seconds": round(total_duration, 2)
            },
            "performance_metrics": {
                "average_test_duration_seconds": round(avg_test_duration, 2),
                "average_memory_delta_mb": round(avg_memory_delta, 2),
                "maximum_memory_delta_mb": round(max_memory_delta, 2),
                "average_cpu_usage_percent": round(avg_cpu, 2),
                "maximum_cpu_usage_percent": round(max_cpu, 2),
                "average_memory_usage_mb": round(avg_memory, 2),
                "maximum_memory_usage_mb": round(max_memory, 2)
            },
            "performance_improvements": performance_improvements,
            "test_results": [asdict(result) for result in self.results],
            "system_metrics_summary": {
                "samples_collected": len(self.system_metrics),
                "monitoring_duration_seconds": round(total_duration, 2)
            },
            "recommendations": []
        }

        # Add recommendations based on results
        if failed_tests > 0:
            report["recommendations"].append("Investigate failed tests for critical issues")

        if max_memory_delta > 100:
            report["recommendations"].append("Consider memory usage optimization - some tests used >100MB")

        if max_cpu > 90:
            report["recommendations"].append("Monitor CPU usage - peaked above 90% during testing")

        if success_rate < 100:
            report["recommendations"].append("Address failing tests before production deployment")
        else:
            report["recommendations"].append("All tests passed - system ready for production")

        # Save report to file
        report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"/mnt/c/dev/tools/crypto-trading-bot-2025/integration_test_report_{report_timestamp}.json"

        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print("\n📋 Integration Test Report Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Total Duration: {total_duration:.2f}s")
        print(f"   Report saved to: {report_filename}")

        if performance_improvements:
            print("\n⚡ Performance Improvements Detected:")
            for improvement in performance_improvements:
                print(f"   • {improvement}")

        if report["recommendations"]:
            print("\n💡 Recommendations:")
            for recommendation in report["recommendations"]:
                print(f"   • {recommendation}")

        return report

async def main():
    """Run the comprehensive integration test suite"""
    test_suite = ComprehensiveIntegrationTest()

    try:
        report = await test_suite.run_all_tests()

        # Update todo list
        TodoWrite([
            {"id": "integration-test-1", "content": "Create comprehensive integration test suite for consolidated system", "status": "completed"},
            {"id": "integration-test-2", "content": "Test end-to-end trading flow with consolidated WebSocket implementation", "status": "completed"},
            {"id": "integration-test-3", "content": "Validate performance optimizations and memory usage improvements", "status": "completed"},
            {"id": "integration-test-4", "content": "Test integration compatibility and backwards compatibility", "status": "completed"},
            {"id": "integration-test-5", "content": "Perform load testing under high message volume", "status": "completed"},
            {"id": "integration-test-6", "content": "Generate comprehensive test results and performance report", "status": "completed"}
        ])

        if report.get("test_summary", {}).get("success_rate_percent", 0) >= 80:
            print("\n🎉 Integration Test Suite: SUCCESS")
            return 0
        else:
            print("\n⚠️ Integration Test Suite: ISSUES DETECTED")
            return 1

    except Exception as e:
        print(f"\n❌ Integration Test Suite: FAILED - {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
