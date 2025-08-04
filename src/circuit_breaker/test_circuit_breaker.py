"""
Circuit Breaker System Test Suite
=================================

Comprehensive test suite for the circuit breaker pattern system.
Includes unit tests, integration tests, and performance tests.
"""

import asyncio
import json
import logging
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Circuit breaker imports
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitBreakerConfig,
    CircuitBreakerState,
    BreakerOpenError,
    BreakerTimeoutError
)
from .health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthCheckResult,
    ServiceHealth
)
from .failure_detector import (
    FailureDetector,
    FailureClassifier,
    FailureCategory,
    FailureSeverity,
    FailureEvent
)

logger = logging.getLogger(__name__)


class TestCircuitBreaker(unittest.TestCase):
    """Test cases for CircuitBreaker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            success_threshold=2,
            timeout=0.5
        )
        self.circuit_breaker = CircuitBreaker("test_service", self.config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'circuit_breaker'):
            self.circuit_breaker.cleanup()
    
    def test_initial_state(self):
        """Test initial circuit breaker state."""
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertTrue(self.circuit_breaker.is_closed)
        self.assertFalse(self.circuit_breaker.is_open)
        self.assertFalse(self.circuit_breaker.is_half_open)
        self.assertTrue(self.circuit_breaker.can_execute())
    
    def test_successful_execution(self):
        """Test successful function execution."""
        def successful_function(x, y):
            return x + y
        
        result = self.circuit_breaker.execute(successful_function, 2, 3)
        self.assertEqual(result, 5)
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.circuit_breaker.metrics.successful_requests, 1)
    
    def test_failed_execution(self):
        """Test failed function execution."""
        def failing_function():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            self.circuit_breaker.execute(failing_function)
        
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.circuit_breaker.metrics.failed_requests, 1)
    
    def test_circuit_opening(self):
        """Test circuit breaker opening after threshold failures."""
        def failing_function():
            raise Exception("Failure")
        
        # Execute failures up to threshold
        for i in range(self.config.failure_threshold):
            with self.assertRaises(Exception):
                self.circuit_breaker.execute(failing_function)
        
        # Circuit should now be open
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.OPEN)
        self.assertTrue(self.circuit_breaker.is_open)
        self.assertFalse(self.circuit_breaker.can_execute())
        
        # Next execution should be blocked
        with self.assertRaises(BreakerOpenError):
            self.circuit_breaker.execute(failing_function)
    
    def test_circuit_recovery(self):
        """Test circuit breaker recovery process."""
        def failing_function():
            raise Exception("Failure")
        
        def successful_function():
            return "success"
        
        # Open the circuit
        for i in range(self.config.failure_threshold):
            with self.assertRaises(Exception):
                self.circuit_breaker.execute(failing_function)
        
        self.assertTrue(self.circuit_breaker.is_open)
        
        # Wait for recovery timeout
        time.sleep(self.config.recovery_timeout + 0.1)
        
        # Circuit should allow execution (half-open)
        self.assertTrue(self.circuit_breaker.can_execute())
        
        # Execute successful calls to close circuit
        for i in range(self.config.success_threshold):
            result = self.circuit_breaker.execute(successful_function)
            self.assertEqual(result, "success")
        
        # Circuit should be closed now
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertTrue(self.circuit_breaker.is_closed)
    
    def test_reset(self):
        """Test circuit breaker reset functionality."""
        def failing_function():
            raise Exception("Failure")
        
        # Generate some failures
        for i in range(2):
            with self.assertRaises(Exception):
                self.circuit_breaker.execute(failing_function)
        
        self.assertEqual(self.circuit_breaker.metrics.failed_requests, 2)
        
        # Reset circuit breaker
        self.circuit_breaker.reset()
        
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.circuit_breaker.metrics.failed_requests, 0)
        self.assertEqual(self.circuit_breaker.metrics.total_requests, 0)
    
    def test_force_open_close(self):
        """Test force open and close functionality."""
        # Force open
        self.circuit_breaker.force_open()
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.OPEN)
        
        # Force close
        self.circuit_breaker.force_close()
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
    
    def test_status_reporting(self):
        """Test status reporting functionality."""
        status = self.circuit_breaker.get_status()
        
        self.assertIn('name', status)
        self.assertIn('state', status)
        self.assertIn('can_execute', status)
        self.assertIn('metrics', status)
        self.assertIn('config', status)
        
        self.assertEqual(status['name'], 'test_service')
        self.assertEqual(status['state'], 'CLOSED')
        self.assertTrue(status['can_execute'])


class TestCircuitBreakerAsync(unittest.IsolatedAsyncioTestCase):
    """Test cases for async CircuitBreaker functionality."""
    
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.5,
            success_threshold=2,
            timeout=0.2
        )
        self.circuit_breaker = CircuitBreaker("async_test_service", self.config)
    
    async def asyncTearDown(self):
        """Clean up async test fixtures."""
        if hasattr(self, 'circuit_breaker'):
            self.circuit_breaker.cleanup()
    
    async def test_async_successful_execution(self):
        """Test successful async function execution."""
        async def async_successful_function(x, y):
            await asyncio.sleep(0.01)
            return x * y
        
        result = await self.circuit_breaker.execute_async(async_successful_function, 3, 4)
        self.assertEqual(result, 12)
        self.assertEqual(self.circuit_breaker.metrics.successful_requests, 1)
    
    async def test_async_failed_execution(self):
        """Test failed async function execution."""
        async def async_failing_function():
            await asyncio.sleep(0.01)
            raise ValueError("Async test error")
        
        with self.assertRaises(ValueError):
            await self.circuit_breaker.execute_async(async_failing_function)
        
        self.assertEqual(self.circuit_breaker.metrics.failed_requests, 1)
    
    async def test_async_timeout(self):
        """Test async function timeout."""
        async def slow_function():
            await asyncio.sleep(1.0)  # Longer than timeout
            return "should not reach here"
        
        with self.assertRaises(BreakerTimeoutError):
            await self.circuit_breaker.execute_async(slow_function, timeout=0.1)
        
        self.assertEqual(self.circuit_breaker.metrics.failed_requests, 1)
    
    async def test_async_circuit_opening(self):
        """Test async circuit breaker opening."""
        async def async_failing_function():
            await asyncio.sleep(0.01)
            raise Exception("Async failure")
        
        # Execute failures up to threshold
        for i in range(self.config.failure_threshold):
            with self.assertRaises(Exception):
                await self.circuit_breaker.execute_async(async_failing_function)
        
        # Circuit should now be open
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.OPEN)
        
        # Next execution should be blocked
        with self.assertRaises(BreakerOpenError):
            await self.circuit_breaker.execute_async(async_failing_function)
    
    async def test_half_open_concurrent_requests(self):
        """Test half-open state with concurrent requests."""
        async def slow_successful_function():
            await asyncio.sleep(0.1)
            return "success"
        
        async def failing_function():
            raise Exception("Failure")
        
        # Open the circuit
        for i in range(self.config.failure_threshold):
            with self.assertRaises(Exception):
                await self.circuit_breaker.execute_async(failing_function)
        
        # Wait for recovery timeout
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        
        # Circuit should be in half-open state and allow limited requests
        self.assertTrue(self.circuit_breaker.can_execute())
        
        # Execute multiple concurrent requests (should be limited)
        tasks = []
        for i in range(5):  # More than max_half_open_requests
            task = asyncio.create_task(
                self.circuit_breaker.execute_async(slow_successful_function)
            )
            tasks.append(task)
        
        # Some should succeed, some should be blocked
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successes = sum(1 for r in results if r == "success")
        failures = sum(1 for r in results if isinstance(r, BreakerOpenError))
        
        self.assertGreaterEqual(successes, 1)
        self.assertGreaterEqual(failures, 1)


class TestCircuitBreakerManager(unittest.IsolatedAsyncioTestCase):
    """Test cases for CircuitBreakerManager."""
    
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.5)
        self.manager = CircuitBreakerManager(
            default_config=self.config,
            storage_dir=self.temp_dir
        )
    
    async def asyncTearDown(self):
        """Clean up async test fixtures."""
        if hasattr(self, 'manager'):
            await self.manager.stop_monitoring()
            self.manager.cleanup()
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_breaker(self):
        """Test circuit breaker creation."""
        breaker = self.manager.create_breaker("test_service")
        
        self.assertIsInstance(breaker, CircuitBreaker)
        self.assertEqual(breaker.name, "test_service")
        self.assertEqual(breaker.config.failure_threshold, self.config.failure_threshold)
        
        # Creating same breaker should return existing one
        breaker2 = self.manager.create_breaker("test_service")
        self.assertIs(breaker, breaker2)
    
    def test_get_breaker(self):
        """Test getting existing circuit breaker."""
        # Non-existent breaker
        self.assertIsNone(self.manager.get_breaker("nonexistent"))
        
        # Create and get breaker
        created_breaker = self.manager.create_breaker("test_service")
        retrieved_breaker = self.manager.get_breaker("test_service")
        
        self.assertIs(created_breaker, retrieved_breaker)
    
    def test_remove_breaker(self):
        """Test circuit breaker removal."""
        # Remove non-existent breaker
        self.assertFalse(self.manager.remove_breaker("nonexistent"))
        
        # Create and remove breaker
        self.manager.create_breaker("test_service")
        self.assertTrue(self.manager.remove_breaker("test_service"))
        self.assertIsNone(self.manager.get_breaker("test_service"))
    
    def test_aggregate_status(self):
        """Test aggregate status reporting."""
        # Empty manager
        status = self.manager.get_aggregate_status()
        self.assertEqual(status['total_breakers'], 0)
        self.assertEqual(status['health_summary'], 'No breakers')
        
        # Create breakers
        breaker1 = self.manager.create_breaker("service1")
        breaker2 = self.manager.create_breaker("service2")
        
        status = self.manager.get_aggregate_status()
        self.assertEqual(status['total_breakers'], 2)
        self.assertEqual(status['states']['CLOSED'], 2)
        self.assertEqual(status['health_summary'], 'Healthy')
        
        # Open one breaker
        breaker1.force_open()
        
        status = self.manager.get_aggregate_status()
        self.assertEqual(status['states']['OPEN'], 1)
        self.assertEqual(status['states']['CLOSED'], 1)
        self.assertEqual(status['health_summary'], 'Degraded')
    
    async def test_monitoring(self):
        """Test background monitoring."""
        # Start monitoring
        await self.manager.start_monitoring(interval=0.1)
        
        # Create a breaker
        breaker = self.manager.create_breaker("monitored_service")
        
        # Wait for monitoring cycle
        await asyncio.sleep(0.2)
        
        # Stop monitoring
        await self.manager.stop_monitoring()
        
        # Monitoring should have saved state
        storage_path = Path(self.temp_dir) / "monitored_service_state.json"
        self.assertTrue(storage_path.exists())
    
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with self.manager.get_breaker_context("context_service") as breaker:
            self.assertIsInstance(breaker, CircuitBreaker)
            self.assertEqual(breaker.name, "context_service")
        
        # Breaker should still exist after context
        retrieved_breaker = self.manager.get_breaker("context_service")
        self.assertIsNotNone(retrieved_breaker)


class TestHealthMonitor(unittest.IsolatedAsyncioTestCase):
    """Test cases for HealthMonitor."""
    
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.health_monitor = HealthMonitor(
            check_interval=0.1,
            alert_threshold=2,
            recovery_threshold=1,
            storage_path=str(Path(self.temp_dir) / "health_state.json")
        )
    
    async def asyncTearDown(self):
        """Clean up async test fixtures."""
        if hasattr(self, 'health_monitor'):
            await self.health_monitor.stop()
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_service_registration(self):
        """Test service registration and unregistration."""
        # Register service
        self.health_monitor.register_service("test_service")
        
        service = self.health_monitor.get_service_health("test_service")
        self.assertIsNotNone(service)
        self.assertEqual(service.name, "test_service")
        self.assertEqual(service.status, HealthStatus.UNKNOWN)
        
        # Unregister service
        self.health_monitor.unregister_service("test_service")
        
        service = self.health_monitor.get_service_health("test_service")
        self.assertIsNone(service)
    
    async def test_health_check(self):
        """Test individual health checks."""
        async def healthy_check():
            return HealthCheckResult(
                service_name="test_service",
                status=HealthStatus.HEALTHY,
                response_time_ms=50.0
            )
        
        self.health_monitor.register_service("test_service", healthy_check)
        
        result = await self.health_monitor.check_service_health("test_service")
        
        self.assertEqual(result.service_name, "test_service")
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertEqual(result.response_time_ms, 50.0)
    
    async def test_bulk_health_checks(self):
        """Test bulk health checks for all services."""
        async def healthy_check():
            return HealthCheckResult(
                service_name="healthy_service",
                status=HealthStatus.HEALTHY,
                response_time_ms=30.0
            )
        
        async def unhealthy_check():
            return HealthCheckResult(
                service_name="unhealthy_service",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0.0,
                error_message="Service down"
            )
        
        self.health_monitor.register_service("healthy_service", healthy_check)
        self.health_monitor.register_service("unhealthy_service", unhealthy_check)
        
        results = await self.health_monitor.check_all_services()
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results["healthy_service"].status, HealthStatus.HEALTHY)
        self.assertEqual(results["unhealthy_service"].status, HealthStatus.UNHEALTHY)
    
    def test_global_health_status(self):
        """Test global health status calculation."""
        # No services
        status = self.health_monitor.get_global_health_status()
        self.assertEqual(status['overall_status'], HealthStatus.UNKNOWN.value)
        self.assertEqual(status['total_services'], 0)
        
        # Add healthy service
        self.health_monitor.register_service("healthy_service")
        service = self.health_monitor.get_service_health("healthy_service")
        service.status = HealthStatus.HEALTHY
        service.metrics.response_time_ms = 25.0
        
        status = self.health_monitor.get_global_health_status()
        self.assertEqual(status['overall_status'], HealthStatus.HEALTHY.value)
        self.assertEqual(status['total_services'], 1)
        self.assertEqual(status['healthy_services'], 1)
        
        # Add unhealthy service
        self.health_monitor.register_service("unhealthy_service")
        service = self.health_monitor.get_service_health("unhealthy_service")
        service.status = HealthStatus.UNHEALTHY
        
        status = self.health_monitor.get_global_health_status()
        self.assertEqual(status['overall_status'], HealthStatus.UNHEALTHY.value)
        self.assertEqual(status['unhealthy_services'], 1)
    
    async def test_monitoring_loop(self):
        """Test background monitoring loop."""
        check_count = 0
        
        async def counting_check():
            nonlocal check_count
            check_count += 1
            return HealthCheckResult(
                service_name="monitored_service",
                status=HealthStatus.HEALTHY,
                response_time_ms=10.0
            )
        
        self.health_monitor.register_service(
            "monitored_service",
            counting_check,
            check_interval=0.05  # Very frequent for testing
        )
        
        # Start monitoring
        await self.health_monitor.start()
        
        # Wait for a few check cycles
        await asyncio.sleep(0.2)
        
        # Stop monitoring
        await self.health_monitor.stop()
        
        # Should have performed multiple checks
        self.assertGreater(check_count, 0)


class TestFailureDetector(unittest.TestCase):
    """Test cases for FailureDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.failure_detector = FailureDetector(
            analysis_window=60.0,
            max_events_per_service=100,
            storage_path=str(Path(self.temp_dir) / "failures.json")
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'failure_detector'):
            self.failure_detector.cleanup()
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_failure_recording(self):
        """Test failure event recording."""
        failure_event = self.failure_detector.record_failure(
            service_name="test_service",
            error_message="Connection timeout",
            exception_type="TimeoutError",
            http_status_code=504,
            response_time_ms=5000.0
        )
        
        self.assertIsInstance(failure_event, FailureEvent)
        self.assertEqual(failure_event.service_name, "test_service")
        self.assertEqual(failure_event.error_message, "Connection timeout")
        self.assertEqual(failure_event.exception_type, "TimeoutError")
        self.assertEqual(failure_event.http_status_code, 504)
    
    def test_failure_analysis(self):
        """Test failure analysis functionality."""
        # Record multiple failures
        for i in range(5):
            self.failure_detector.record_failure(
                service_name="test_service",
                error_message=f"Error {i}: Connection failed",
                exception_type="ConnectionError"
            )
        
        # Analyze failures
        analysis = self.failure_detector.analyze_failures("test_service")
        
        self.assertEqual(analysis.service_name, "test_service")
        self.assertEqual(analysis.total_failures, 5)
        self.assertGreater(analysis.failure_rate, 0)
        self.assertIn("connection_refused", analysis.detected_patterns)
        self.assertIn("NETWORK", analysis.category_distribution)
    
    def test_circuit_opening_decision(self):
        """Test circuit breaker opening decision logic."""
        # Record many critical failures
        for i in range(10):
            self.failure_detector.record_failure(
                service_name="critical_service",
                error_message="Internal server error",
                http_status_code=500,
                exception_type="ServerError"
            )
        
        should_open, reason, analysis = self.failure_detector.should_open_circuit(
            "critical_service",
            failure_threshold=5
        )
        
        self.assertTrue(should_open)
        self.assertIn("failure rate", reason.lower())
        self.assertEqual(analysis.total_failures, 10)
    
    def test_failure_statistics(self):
        """Test failure statistics collection."""
        # Record failures for multiple services
        self.failure_detector.record_failure(
            "service1", "Timeout error", "TimeoutError")
        self.failure_detector.record_failure(
            "service1", "Connection error", "ConnectionError")
        self.failure_detector.record_failure(
            "service2", "Auth error", "AuthError", http_status_code=401)
        
        # Get statistics
        stats = self.failure_detector.get_failure_statistics()
        
        self.assertEqual(stats['global_stats']['total_failures'], 3)
        self.assertEqual(stats['global_stats']['total_services'], 2)
        self.assertIn('service1', stats['services'])
        self.assertIn('service2', stats['services'])
        
        # Service-specific statistics
        service1_stats = stats['services']['service1']
        self.assertEqual(service1_stats['failure_count'], 2)
        
        service2_stats = stats['services']['service2']
        self.assertEqual(service2_stats['failure_count'], 1)
    
    def test_failure_classification(self):
        """Test failure classification."""
        classifier = FailureClassifier()
        
        # Test network failure
        failure_event = FailureEvent(
            timestamp=time.time(),
            service_name="test_service",
            error_message="Connection timeout occurred",
            exception_type="TimeoutError"
        )
        
        category, severity, patterns = classifier.classify_failure(failure_event)
        
        self.assertEqual(category, FailureCategory.NETWORK)
        self.assertEqual(severity, FailureSeverity.HIGH)
        self.assertIn("connection_timeout", patterns)
        
        # Test authentication failure
        auth_failure = FailureEvent(
            timestamp=time.time(),
            service_name="test_service",
            error_message="Invalid credentials provided",
            http_status_code=401
        )
        
        category, severity, patterns = classifier.classify_failure(auth_failure)
        
        self.assertEqual(category, FailureCategory.AUTHENTICATION)
        self.assertEqual(severity, FailureSeverity.HIGH)
        self.assertIn("auth_failure", patterns)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for the complete circuit breaker system."""
    
    async def asyncSetUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Circuit breaker configuration
        self.cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.5,
            success_threshold=2
        )
        
        # Initialize components
        self.cb_manager = CircuitBreakerManager(
            default_config=self.cb_config,
            storage_dir=str(Path(self.temp_dir) / "circuit_breaker")
        )
        
        self.health_monitor = HealthMonitor(
            check_interval=0.1,
            storage_path=str(Path(self.temp_dir) / "health.json")
        )
        
        self.failure_detector = FailureDetector(
            analysis_window=60.0,
            storage_path=str(Path(self.temp_dir) / "failures.json")
        )
    
    async def asyncTearDown(self):
        """Clean up integration test fixtures."""
        await self.cb_manager.stop_monitoring()
        await self.health_monitor.stop()
        
        self.cb_manager.cleanup()
        self.failure_detector.cleanup()
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_full_integration(self):
        """Test full integration of all components."""
        # Start monitoring
        await self.cb_manager.start_monitoring(interval=0.1)
        await self.health_monitor.start()
        
        # Create circuit breaker
        circuit_breaker = self.cb_manager.create_breaker("integration_service")
        
        # Register health check
        async def integration_health_check():
            return HealthCheckResult(
                service_name="integration_service",
                status=HealthStatus.HEALTHY,
                response_time_ms=25.0
            )
        
        self.health_monitor.register_service(
            "integration_service",
            integration_health_check
        )
        
        # Simulate API function
        call_count = 0
        failure_mode = False
        
        async def api_function():
            nonlocal call_count, failure_mode
            call_count += 1
            
            if failure_mode:
                # Record failure in detector
                self.failure_detector.record_failure(
                    service_name="integration_service",
                    error_message="Simulated API failure",
                    exception_type="APIError"
                )
                raise Exception("API failure")
            
            return {"result": "success", "call_number": call_count}
        
        # Test successful calls
        for i in range(3):
            result = await circuit_breaker.execute_async(api_function)
            self.assertEqual(result["result"], "success")
        
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED)
        
        # Switch to failure mode
        failure_mode = True
        
        # Generate failures to open circuit
        for i in range(self.cb_config.failure_threshold):
            with self.assertRaises(Exception):
                await circuit_breaker.execute_async(api_function)
        
        # Circuit should be open
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.OPEN)
        
        # Analyze failures
        analysis = self.failure_detector.analyze_failures("integration_service")
        self.assertEqual(analysis.total_failures, self.cb_config.failure_threshold)
        
        should_open, reason, _ = self.failure_detector.should_open_circuit(
            "integration_service",
            failure_threshold=2
        )
        self.assertTrue(should_open)
        
        # Wait for recovery timeout
        await asyncio.sleep(self.cb_config.recovery_timeout + 0.1)
        
        # Switch back to success mode
        failure_mode = False
        
        # Recovery attempts should succeed
        for i in range(self.cb_config.success_threshold):
            result = await circuit_breaker.execute_async(api_function)
            self.assertEqual(result["result"], "success")
        
        # Circuit should be closed
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED)
        
        # Check health status
        health_results = await self.health_monitor.check_all_services()
        self.assertIn("integration_service", health_results)
        self.assertEqual(
            health_results["integration_service"].status,
            HealthStatus.HEALTHY
        )
        
        # Check aggregate status
        cb_status = self.cb_manager.get_aggregate_status()
        self.assertEqual(cb_status["health_summary"], "Healthy")
        
        # Wait for monitoring cycles
        await asyncio.sleep(0.2)


def run_tests():
    """Run all circuit breaker tests."""
    # Configure logging for tests
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during tests
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestCircuitBreaker,
        TestCircuitBreakerAsync,
        TestCircuitBreakerManager,
        TestHealthMonitor,
        TestFailureDetector,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
