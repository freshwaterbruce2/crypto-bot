"""
Component Compatibility Testing Framework
Tests compatibility between all system components and their interfaces
"""

import asyncio
import json
import logging
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.auth.kraken_auth import KrakenAuth
from src.balance.balance_manager import BalanceManager
from src.circuit_breaker.circuit_breaker import CircuitBreaker
from src.config.config import Config as TradingConfig
from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager as WebSocketManagerV2
from src.portfolio.portfolio_manager import PortfolioManager
from src.rate_limiting.kraken_rate_limiter import KrakenRateLimiter2025 as KrakenRateLimiter
from src.storage.database_manager import DatabaseManager
from src.utils.decimal_precision_fix import DecimalHandler


@dataclass
class CompatibilityTest:
    """Individual compatibility test"""
    name: str
    description: str
    components: List[str]
    test_function: str
    expected_result: Any
    critical: bool = False


@dataclass
class CompatibilityResult:
    """Compatibility test result"""
    test_name: str
    passed: bool
    duration: float
    components_tested: List[str]
    interface_mismatches: List[str]
    version_conflicts: List[str]
    dependency_issues: List[str]
    recommendations: List[str]
    details: Dict[str, Any]


@dataclass
class ComponentInterface:
    """Component interface specification"""
    component_name: str
    class_name: str
    required_methods: List[str]
    optional_methods: List[str]
    required_attributes: List[str]
    dependencies: List[str]
    version: str


class ComponentCompatibilityTester:
    """Component compatibility testing framework"""

    def __init__(self):
        self.config = TradingConfig()
        self.logger = self._setup_logging()
        self.results: List[CompatibilityResult] = []

        # Component registry
        self.components = {}
        self.interfaces = {}

        # Test registry
        self.compatibility_tests = []

        self._register_components()
        self._register_interfaces()
        self._register_tests()

    def _setup_logging(self) -> logging.Logger:
        """Setup compatibility testing logging"""
        logger = logging.getLogger('compatibility_tester')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _register_components(self):
        """Register all system components"""
        self.components = {
            'auth': KrakenAuth,
            'rate_limiter': KrakenRateLimiter,
            'circuit_breaker': CircuitBreaker,
            'websocket_manager': WebSocketManagerV2,
            'balance_manager': BalanceManager,
            'portfolio_manager': PortfolioManager,
            'database_manager': DatabaseManager,
            'decimal_handler': DecimalHandler,
            'config': TradingConfig
        }

    def _register_interfaces(self):
        """Register component interface specifications"""
        self.interfaces = {
            'auth': ComponentInterface(
                component_name='auth',
                class_name='KrakenAuth',
                required_methods=['generate_signature', 'get_headers'],
                optional_methods=['validate_credentials'],
                required_attributes=['api_key', 'secret_key'],
                dependencies=[],
                version='1.0'
            ),
            'rate_limiter': ComponentInterface(
                component_name='rate_limiter',
                class_name='KrakenRateLimiter',
                required_methods=['acquire', 'release', 'is_available'],
                optional_methods=['reset', 'get_stats'],
                required_attributes=['limits'],
                dependencies=[],
                version='1.0'
            ),
            'circuit_breaker': ComponentInterface(
                component_name='circuit_breaker',
                class_name='CircuitBreaker',
                required_methods=['is_open', 'record_success', 'record_failure'],
                optional_methods=['reset', 'get_stats'],
                required_attributes=['failure_threshold'],
                dependencies=[],
                version='1.0'
            ),
            'websocket_manager': ComponentInterface(
                component_name='websocket_manager',
                class_name='WebSocketManagerV2',
                required_methods=['connect', 'disconnect', 'subscribe'],
                optional_methods=['handle_error', 'reconnect'],
                required_attributes=[],
                dependencies=['auth', 'balance_manager'],
                version='2.0'
            ),
            'balance_manager': ComponentInterface(
                component_name='balance_manager',
                class_name='BalanceManager',
                required_methods=['get_balance', 'refresh_balance'],
                optional_methods=['_update_cached_balance', '_get_cached_balance'],
                required_attributes=[],
                dependencies=['auth', 'rate_limiter'],
                version='1.0'
            ),
            'portfolio_manager': ComponentInterface(
                component_name='portfolio_manager',
                class_name='PortfolioManager',
                required_methods=['get_total_balance', 'get_current_positions'],
                optional_methods=['calculate_risk_metrics', 'rebalance'],
                required_attributes=[],
                dependencies=['balance_manager', 'database_manager'],
                version='1.0'
            ),
            'database_manager': ComponentInterface(
                component_name='database_manager',
                class_name='DatabaseManager',
                required_methods=['initialize', 'store_trade_data', 'get_trade_data'],
                optional_methods=['close', 'test_connection', 'cleanup'],
                required_attributes=[],
                dependencies=[],
                version='1.0'
            )
        }

    def _register_tests(self):
        """Register compatibility tests"""
        self.compatibility_tests = [
            CompatibilityTest(
                name="auth_rate_limiter_compatibility",
                description="Test authentication and rate limiter compatibility",
                components=['auth', 'rate_limiter'],
                test_function='_test_auth_rate_limiter_compatibility',
                expected_result=True,
                critical=True
            ),
            CompatibilityTest(
                name="balance_manager_dependencies",
                description="Test balance manager dependency injection",
                components=['balance_manager', 'auth', 'rate_limiter'],
                test_function='_test_balance_manager_dependencies',
                expected_result=True,
                critical=True
            ),
            CompatibilityTest(
                name="portfolio_manager_dependencies",
                description="Test portfolio manager dependency injection",
                components=['portfolio_manager', 'balance_manager', 'database_manager'],
                test_function='_test_portfolio_manager_dependencies',
                expected_result=True,
                critical=True
            ),
            CompatibilityTest(
                name="websocket_integration_compatibility",
                description="Test WebSocket manager integration compatibility",
                components=['websocket_manager', 'auth', 'balance_manager'],
                test_function='_test_websocket_integration_compatibility',
                expected_result=True,
                critical=True
            ),
            CompatibilityTest(
                name="circuit_breaker_integration",
                description="Test circuit breaker integration with other components",
                components=['circuit_breaker', 'balance_manager', 'portfolio_manager'],
                test_function='_test_circuit_breaker_integration',
                expected_result=True,
                critical=False
            ),
            CompatibilityTest(
                name="decimal_precision_compatibility",
                description="Test decimal precision handling across components",
                components=['decimal_handler', 'balance_manager', 'portfolio_manager'],
                test_function='_test_decimal_precision_compatibility',
                expected_result=True,
                critical=True
            ),
            CompatibilityTest(
                name="async_await_compatibility",
                description="Test async/await compatibility across components",
                components=['balance_manager', 'portfolio_manager', 'websocket_manager', 'database_manager'],
                test_function='_test_async_await_compatibility',
                expected_result=True,
                critical=True
            ),
            CompatibilityTest(
                name="error_handling_compatibility",
                description="Test error handling compatibility across components",
                components=['auth', 'rate_limiter', 'circuit_breaker', 'balance_manager'],
                test_function='_test_error_handling_compatibility',
                expected_result=True,
                critical=True
            ),
            CompatibilityTest(
                name="configuration_compatibility",
                description="Test configuration compatibility across components",
                components=['config', 'auth', 'rate_limiter', 'balance_manager'],
                test_function='_test_configuration_compatibility',
                expected_result=True,
                critical=True
            ),
            CompatibilityTest(
                name="data_flow_compatibility",
                description="Test data flow compatibility between components",
                components=['websocket_manager', 'balance_manager', 'portfolio_manager', 'database_manager'],
                test_function='_test_data_flow_compatibility',
                expected_result=True,
                critical=True
            )
        ]

    async def run_compatibility_tests(self) -> List[CompatibilityResult]:
        """Run all compatibility tests"""
        self.logger.info("Starting component compatibility testing")

        for test in self.compatibility_tests:
            self.logger.info(f"Running test: {test.name}")

            try:
                result = await self._run_compatibility_test(test)
                self.results.append(result)

                if result.passed:
                    self.logger.info(f"✅ {test.name} PASSED")
                else:
                    level = "ERROR" if test.critical else "WARNING"
                    self.logger.log(
                        logging.ERROR if test.critical else logging.WARNING,
                        f"❌ {test.name} FAILED"
                    )

            except Exception as e:
                self.logger.error(f"Test {test.name} crashed: {e}")
                self._add_crash_result(test, e)

        self.logger.info(f"Compatibility testing completed: {len(self.results)} tests run")
        return self.results

    async def _run_compatibility_test(self, test: CompatibilityTest) -> CompatibilityResult:
        """Run individual compatibility test"""
        start_time = time.time()

        # Get test method
        test_method = getattr(self, test.test_function, None)
        if not test_method:
            raise ValueError(f"Test method {test.test_function} not found")

        # Run the test
        try:
            if asyncio.iscoroutinefunction(test_method):
                result = await test_method()
            else:
                result = test_method()

            duration = time.time() - start_time

            return CompatibilityResult(
                test_name=test.name,
                passed=result is True,
                duration=duration,
                components_tested=test.components,
                interface_mismatches=[],
                version_conflicts=[],
                dependency_issues=[],
                recommendations=[],
                details={"result": result}
            )

        except Exception as e:
            duration = time.time() - start_time

            return CompatibilityResult(
                test_name=test.name,
                passed=False,
                duration=duration,
                components_tested=test.components,
                interface_mismatches=[],
                version_conflicts=[],
                dependency_issues=[f"Test execution error: {str(e)}"],
                recommendations=[f"Fix test execution error in {test.name}"],
                details={"error": str(e), "traceback": traceback.format_exc()}
            )

    def _add_crash_result(self, test: CompatibilityTest, error: Exception):
        """Add result for crashed test"""
        result = CompatibilityResult(
            test_name=test.name,
            passed=False,
            duration=0,
            components_tested=test.components,
            interface_mismatches=[],
            version_conflicts=[],
            dependency_issues=[f"Test crashed: {str(error)}"],
            recommendations=[f"Fix critical error in {test.name}"],
            details={"crash_error": str(error)}
        )
        self.results.append(result)

    # Individual compatibility tests

    async def _test_auth_rate_limiter_compatibility(self) -> bool:
        """Test authentication and rate limiter compatibility"""
        try:
            # Test that rate limiter and auth can work together
            auth = KrakenAuth()
            rate_limiter = KrakenRateLimiter()

            # Test that auth doesn't interfere with rate limiting
            await rate_limiter.acquire('private')

            # Test that rate limiter doesn't break auth
            test_signature = auth.generate_signature("/test", "123", "")

            rate_limiter.release('private')

            return test_signature is not None and len(test_signature) > 0

        except Exception as e:
            self.logger.error(f"Auth/Rate limiter compatibility error: {e}")
            return False

    async def _test_balance_manager_dependencies(self) -> bool:
        """Test balance manager dependency injection"""
        try:
            # Test proper dependency injection
            auth = KrakenAuth()
            rate_limiter = KrakenRateLimiter()

            balance_manager = BalanceManager(
                auth=auth,
                rate_limiter=rate_limiter
            )

            # Test that dependencies are properly injected
            if balance_manager.auth != auth:
                self.logger.error("Auth dependency not properly injected")
                return False

            if balance_manager.rate_limiter != rate_limiter:
                self.logger.error("Rate limiter dependency not properly injected")
                return False

            # Test that balance manager can use dependencies
            test_balance = await balance_manager.get_balance()
            # Balance can be None in test environment

            return True

        except Exception as e:
            self.logger.error(f"Balance manager dependencies error: {e}")
            return False

    async def _test_portfolio_manager_dependencies(self) -> bool:
        """Test portfolio manager dependency injection"""
        try:
            # Setup dependencies
            auth = KrakenAuth()
            rate_limiter = KrakenRateLimiter()
            database_manager = DatabaseManager()
            await database_manager.initialize()

            balance_manager = BalanceManager(
                auth=auth,
                rate_limiter=rate_limiter
            )

            portfolio_manager = PortfolioManager(
                balance_manager=balance_manager,
                database_manager=database_manager
            )

            # Test dependency injection
            if portfolio_manager.balance_manager != balance_manager:
                self.logger.error("Balance manager dependency not properly injected")
                return False

            if portfolio_manager.database_manager != database_manager:
                self.logger.error("Database manager dependency not properly injected")
                return False

            # Test that portfolio manager can use dependencies
            total_balance = await portfolio_manager.get_total_balance()
            positions = await portfolio_manager.get_current_positions()

            await database_manager.close()

            return True

        except Exception as e:
            self.logger.error(f"Portfolio manager dependencies error: {e}")
            return False

    async def _test_websocket_integration_compatibility(self) -> bool:
        """Test WebSocket manager integration compatibility"""
        try:
            # Setup dependencies
            auth = KrakenAuth()
            rate_limiter = KrakenRateLimiter()

            balance_manager = BalanceManager(
                auth=auth,
                rate_limiter=rate_limiter
            )

            websocket_manager = WebSocketManagerV2(
                auth=auth,
                balance_manager=balance_manager
            )

            # Test that WebSocket manager has proper dependencies
            if websocket_manager.auth != auth:
                self.logger.error("Auth dependency not properly injected in WebSocket manager")
                return False

            if websocket_manager.balance_manager != balance_manager:
                self.logger.error("Balance manager dependency not properly injected in WebSocket manager")
                return False

            # Test interface compatibility (without actually connecting)
            if not hasattr(websocket_manager, 'connect'):
                self.logger.error("WebSocket manager missing connect method")
                return False

            if not hasattr(websocket_manager, 'disconnect'):
                self.logger.error("WebSocket manager missing disconnect method")
                return False

            return True

        except Exception as e:
            self.logger.error(f"WebSocket integration compatibility error: {e}")
            return False

    async def _test_circuit_breaker_integration(self) -> bool:
        """Test circuit breaker integration with other components"""
        try:
            # Test circuit breaker integration
            circuit_breaker = CircuitBreaker()

            # Test basic functionality
            if circuit_breaker.is_open():
                await circuit_breaker.reset()

            # Record some failures
            for i in range(3):
                await circuit_breaker.record_failure()

            # Test that circuit breaker state can be checked
            is_open = circuit_breaker.is_open()

            # Reset for clean state
            await circuit_breaker.reset()

            return True

        except Exception as e:
            self.logger.error(f"Circuit breaker integration error: {e}")
            return False

    async def _test_decimal_precision_compatibility(self) -> bool:
        """Test decimal precision handling across components"""
        try:
            # Test decimal handler
            decimal_handler = DecimalHandler()

            # Test decimal conversion
            test_values = ["100.123456789", "0.000001", "1000000.0"]

            for value in test_values:
                decimal_value = decimal_handler.to_decimal(value)
                if decimal_value is None:
                    self.logger.error(f"Failed to convert {value} to decimal")
                    return False

            # Test that balance manager can handle decimals
            auth = KrakenAuth()
            rate_limiter = KrakenRateLimiter()
            balance_manager = BalanceManager(auth=auth, rate_limiter=rate_limiter)

            # Test decimal precision in balance updates
            test_balance = {"USDT": decimal_handler.to_decimal("100.123456")}
            await balance_manager._update_cached_balance(test_balance)

            return True

        except Exception as e:
            self.logger.error(f"Decimal precision compatibility error: {e}")
            return False

    async def _test_async_await_compatibility(self) -> bool:
        """Test async/await compatibility across components"""
        try:
            # Test that all async components work together
            auth = KrakenAuth()
            rate_limiter = KrakenRateLimiter()
            database_manager = DatabaseManager()

            await database_manager.initialize()

            balance_manager = BalanceManager(
                auth=auth,
                rate_limiter=rate_limiter
            )

            portfolio_manager = PortfolioManager(
                balance_manager=balance_manager,
                database_manager=database_manager
            )

            # Test concurrent async operations
            tasks = [
                rate_limiter.acquire('private'),
                balance_manager.get_balance(),
                portfolio_manager.get_total_balance(),
                database_manager.test_connection()
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check that no exceptions occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Async operation {i} failed: {result}")
                    return False

            await database_manager.close()

            return True

        except Exception as e:
            self.logger.error(f"Async/await compatibility error: {e}")
            return False

    async def _test_error_handling_compatibility(self) -> bool:
        """Test error handling compatibility across components"""
        try:
            # Test that components handle errors consistently
            auth = KrakenAuth()
            rate_limiter = KrakenRateLimiter()
            circuit_breaker = CircuitBreaker()

            balance_manager = BalanceManager(
                auth=auth,
                rate_limiter=rate_limiter
            )

            # Test error propagation (without causing actual errors)
            # This tests that error handling mechanisms are in place

            # Test circuit breaker error recording
            await circuit_breaker.record_failure()

            # Test that components can handle None values gracefully
            await balance_manager._update_cached_balance(None)

            return True

        except Exception as e:
            self.logger.error(f"Error handling compatibility error: {e}")
            return False

    async def _test_configuration_compatibility(self) -> bool:
        """Test configuration compatibility across components"""
        try:
            # Test that all components can use shared configuration
            config = TradingConfig()

            # Test that components can access configuration
            auth = KrakenAuth()
            rate_limiter = KrakenRateLimiter()

            # Test configuration values are accessible
            if hasattr(config, 'trading_pairs'):
                trading_pairs = config.trading_pairs

            if hasattr(config, 'position_size_percent'):
                position_size = config.position_size_percent

            return True

        except Exception as e:
            self.logger.error(f"Configuration compatibility error: {e}")
            return False

    async def _test_data_flow_compatibility(self) -> bool:
        """Test data flow compatibility between components"""
        try:
            # Test data flow: WebSocket -> Balance Manager -> Portfolio Manager -> Database
            auth = KrakenAuth()
            rate_limiter = KrakenRateLimiter()
            database_manager = DatabaseManager()

            await database_manager.initialize()

            balance_manager = BalanceManager(
                auth=auth,
                rate_limiter=rate_limiter
            )

            portfolio_manager = PortfolioManager(
                balance_manager=balance_manager,
                database_manager=database_manager
            )

            websocket_manager = WebSocketManagerV2(
                auth=auth,
                balance_manager=balance_manager
            )

            # Test data flow simulation
            # 1. Simulate balance update from WebSocket
            test_balance = {"USDT": 100.0, "BTC": 0.001}
            await balance_manager._update_cached_balance(test_balance)

            # 2. Test that portfolio manager can access updated balance
            total_balance = await portfolio_manager.get_total_balance()

            # 3. Test that data can be stored in database
            test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
            await database_manager.store_trade_data("test_flow", test_data)

            # 4. Test that data can be retrieved from database
            retrieved_data = await database_manager.get_trade_data("test_flow")

            await database_manager.close()

            return retrieved_data is not None

        except Exception as e:
            self.logger.error(f"Data flow compatibility error: {e}")
            return False

    def check_interface_compatibility(self, component_name: str) -> List[str]:
        """Check interface compatibility for a component"""
        issues = []

        if component_name not in self.interfaces:
            issues.append(f"No interface specification for {component_name}")
            return issues

        if component_name not in self.components:
            issues.append(f"Component {component_name} not registered")
            return issues

        interface = self.interfaces[component_name]
        component_class = self.components[component_name]

        # Check required methods
        for method in interface.required_methods:
            if not hasattr(component_class, method):
                issues.append(f"Missing required method: {method}")

        # Check required attributes (on instances)
        try:
            # Try to create instance to check attributes
            if component_name == 'balance_manager':
                # Special handling for components requiring dependencies
                auth = KrakenAuth()
                rate_limiter = KrakenRateLimiter()
                instance = component_class(auth=auth, rate_limiter=rate_limiter)
            elif component_name == 'portfolio_manager':
                auth = KrakenAuth()
                rate_limiter = KrakenRateLimiter()
                balance_manager = BalanceManager(auth=auth, rate_limiter=rate_limiter)
                database_manager = DatabaseManager()
                instance = component_class(balance_manager=balance_manager, database_manager=database_manager)
            elif component_name == 'websocket_manager':
                auth = KrakenAuth()
                rate_limiter = KrakenRateLimiter()
                balance_manager = BalanceManager(auth=auth, rate_limiter=rate_limiter)
                instance = component_class(auth=auth, balance_manager=balance_manager)
            else:
                instance = component_class()

            for attr in interface.required_attributes:
                if not hasattr(instance, attr):
                    issues.append(f"Missing required attribute: {attr}")

        except Exception as e:
            issues.append(f"Could not instantiate {component_name} to check attributes: {e}")

        return issues

    def generate_compatibility_report(self) -> Dict[str, Any]:
        """Generate comprehensive compatibility report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        critical_failures = [r for r in self.results if not r.passed and
                           any(test.critical for test in self.compatibility_tests
                               if test.name == r.test_name)]

        # Interface compatibility check
        interface_issues = {}
        for component_name in self.interfaces.keys():
            issues = self.check_interface_compatibility(component_name)
            if issues:
                interface_issues[component_name] = issues

        # Generate recommendations
        recommendations = []

        if critical_failures:
            recommendations.append(f"CRITICAL: Fix {len(critical_failures)} critical compatibility failures")

        if failed_tests > 0:
            recommendations.append(f"Address {failed_tests} compatibility issues before deployment")

        if interface_issues:
            recommendations.append(f"Fix interface mismatches in {len(interface_issues)} components")

        if not recommendations:
            recommendations.append("All compatibility tests passed - components are compatible")

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "critical_failures": len(critical_failures),
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0
            },
            "interface_issues": interface_issues,
            "test_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "duration": r.duration,
                    "components": r.components_tested,
                    "issues": r.interface_mismatches + r.version_conflicts + r.dependency_issues,
                    "recommendations": r.recommendations
                }
                for r in self.results
            ],
            "recommendations": recommendations,
            "component_matrix": self._generate_component_matrix()
        }

    def _generate_component_matrix(self) -> Dict[str, Any]:
        """Generate component compatibility matrix"""
        matrix = {}

        components = list(self.components.keys())

        for comp1 in components:
            matrix[comp1] = {}
            for comp2 in components:
                if comp1 == comp2:
                    matrix[comp1][comp2] = "self"
                else:
                    # Check if there are tests covering this combination
                    compatible_tests = [
                        test for test in self.compatibility_tests
                        if comp1 in test.components and comp2 in test.components
                    ]

                    if compatible_tests:
                        # Check if all tests passed
                        test_results = [
                            result for result in self.results
                            if result.test_name in [test.name for test in compatible_tests]
                        ]

                        if all(result.passed for result in test_results):
                            matrix[comp1][comp2] = "compatible"
                        else:
                            matrix[comp1][comp2] = "incompatible"
                    else:
                        matrix[comp1][comp2] = "untested"

        return matrix


async def main():
    """Run component compatibility testing"""
    tester = ComponentCompatibilityTester()

    try:
        # Run compatibility tests
        results = await tester.run_compatibility_tests()

        # Generate report
        report = tester.generate_compatibility_report()

        # Print summary
        print(f"\n{'='*60}")
        print("COMPONENT COMPATIBILITY REPORT")
        print(f"{'='*60}")
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed_tests']}")
        print(f"Failed: {report['summary']['failed_tests']}")
        print(f"Critical Failures: {report['summary']['critical_failures']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1%}")

        # Interface issues
        if report['interface_issues']:
            print(f"\n{'='*60}")
            print("INTERFACE ISSUES")
            print(f"{'='*60}")
            for component, issues in report['interface_issues'].items():
                print(f"{component}:")
                for issue in issues:
                    print(f"  • {issue}")

        # Recommendations
        print(f"\n{'='*60}")
        print("RECOMMENDATIONS")
        print(f"{'='*60}")
        for rec in report['recommendations']:
            print(f"• {rec}")

        # Failed tests
        failed_results = [r for r in results if not r.passed]
        if failed_results:
            print(f"\n{'='*60}")
            print("FAILED TESTS")
            print(f"{'='*60}")
            for result in failed_results:
                print(f"❌ {result.test_name}")
                for issue in result.dependency_issues:
                    print(f"   • {issue}")

        # Save report
        report_file = Path("validation/compatibility_report.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\nDetailed report saved to: {report_file}")

        # Return success code
        return 0 if report['summary']['failed_tests'] == 0 else 1

    except Exception as e:
        print(f"Compatibility testing failed: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
