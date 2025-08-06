#!/usr/bin/env python3
"""
Paper Trading Test Runner
Automated test runner for comprehensive paper trading validation
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


class PaperTradingTestRunner:
    """Comprehensive test runner for paper trading validation"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.test_start_time = time.time()
        self.test_results = {}
        self.overall_status = "UNKNOWN"

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for test runner"""
        logger = logging.getLogger('paper_test_runner')
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # File handler
        log_file = Path(__file__).parent / 'logs' / 'paper_trading_test_runner.log'
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def setup_test_environment(self):
        """Setup environment for paper trading tests"""
        self.logger.info("Setting up paper trading test environment...")

        # Critical environment variables for paper trading
        paper_env = {
            'PAPER_TRADING_ENABLED': 'true',
            'LIVE_TRADING_DISABLED': 'true',
            'TRADING_MODE': 'paper',
            'SIMULATION_MODE': 'true',
            'FORCE_PAPER_MODE': 'true',
            'DISABLE_REAL_ORDERS': 'true',
            'BLOCK_LIVE_TRADING': 'true',
            'SAFETY_MODE': 'maximum',
            'API_READ_ONLY': 'true',
            'VALIDATION_MODE': 'true',
            'STRICT_SAFETY_CHECKS': 'true',
            'DEBUG_PAPER_TRADING': 'true',
            'LOG_LEVEL': 'INFO'
        }

        # Apply environment variables
        for key, value in paper_env.items():
            os.environ[key] = value

        self.logger.info("Paper trading environment configured")

        # Verify critical files exist
        required_files = [
            '.env.paper_trading',
            'paper_trading_config.json',
            'src/paper_trading/__init__.py'
        ]

        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            self.logger.warning(f"Missing files: {missing_files}")

        return paper_env

    async def run_startup_test(self) -> Dict[str, Any]:
        """Run paper trading startup test"""
        self.logger.info("Running paper trading startup test...")

        try:
            # Import and run startup test
            from test_paper_trading_startup import PaperTradingStartupTest

            startup_test = PaperTradingStartupTest()
            result = await startup_test.run_startup_test()

            self.test_results['startup_test'] = result
            self.logger.info(f"Startup test completed: {result['overall_status']}")

            return result

        except ImportError as e:
            self.logger.error(f"Could not import startup test: {e}")
            # Run as subprocess if import fails
            return await self._run_test_subprocess('test_paper_trading_startup.py')
        except Exception as e:
            self.logger.error(f"Startup test failed: {e}")
            return {'overall_status': 'FAIL', 'error': str(e)}

    async def run_validation_suite(self) -> Dict[str, Any]:
        """Run comprehensive validation suite"""
        self.logger.info("Running paper trading validation suite...")

        try:
            # Import and run validation suite
            from tests.paper_trading_validation_suite import PaperTradingValidator

            validator = PaperTradingValidator()
            result = await validator.run_comprehensive_validation()

            self.test_results['validation_suite'] = result
            self.logger.info(f"Validation suite completed: {result['overall_status']}")

            return result

        except ImportError as e:
            self.logger.error(f"Could not import validation suite: {e}")
            # Run as subprocess if import fails
            return await self._run_test_subprocess('tests/paper_trading_validation_suite.py')
        except Exception as e:
            self.logger.error(f"Validation suite failed: {e}")
            return {'overall_status': 'FAIL', 'error': str(e)}

    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run existing integration tests in paper mode"""
        self.logger.info("Running integration tests in paper mode...")

        integration_tests = [
            'tests/test_balance_manager_v2_fixes.py',
            'tests/test_websocket_v2_fixes.py',
            'tests/test_critical_fixes.py'
        ]

        results = {}

        for test_file in integration_tests:
            test_path = Path(test_file)
            if test_path.exists():
                self.logger.info(f"Running {test_file}...")
                result = await self._run_test_subprocess(test_file)
                results[test_path.stem] = result
            else:
                self.logger.warning(f"Test file not found: {test_file}")
                results[test_path.stem] = {'overall_status': 'SKIP', 'reason': 'File not found'}

        # Aggregate results
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get('overall_status') == 'PASS')

        aggregate_result = {
            'test_type': 'integration_tests',
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            'overall_status': 'PASS' if passed_tests == total_tests else 'FAIL',
            'individual_results': results
        }

        self.test_results['integration_tests'] = aggregate_result
        return aggregate_result

    async def _run_test_subprocess(self, test_file: str) -> Dict[str, Any]:
        """Run test as subprocess"""
        try:
            self.logger.debug(f"Running {test_file} as subprocess...")

            # Run test with timeout
            process = await asyncio.create_subprocess_exec(
                sys.executable, test_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300.0  # 5 minute timeout
                )

                return_code = process.returncode

                result = {
                    'test_file': test_file,
                    'return_code': return_code,
                    'overall_status': 'PASS' if return_code == 0 else 'FAIL',
                    'stdout': stdout.decode('utf-8', errors='ignore'),
                    'stderr': stderr.decode('utf-8', errors='ignore')
                }

                if return_code != 0:
                    self.logger.warning(f"Test {test_file} failed with code {return_code}")

                return result

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    'test_file': test_file,
                    'overall_status': 'TIMEOUT',
                    'error': 'Test timed out after 5 minutes'
                }

        except Exception as e:
            return {
                'test_file': test_file,
                'overall_status': 'ERROR',
                'error': str(e)
            }

    def check_prerequisites(self) -> Dict[str, Any]:
        """Check prerequisites for paper trading tests"""
        self.logger.info("Checking prerequisites...")

        checks = {}

        # Check Python version
        python_version = sys.version_info
        checks['python_version'] = {
            'version': f"{python_version.major}.{python_version.minor}.{python_version.micro}",
            'supported': python_version >= (3, 8),
            'status': 'PASS' if python_version >= (3, 8) else 'FAIL'
        }

        # Check required files
        required_files = [
            '.env.paper_trading',
            'paper_trading_config.json',
            'src/__init__.py'
        ]

        file_checks = {}
        for file_path in required_files:
            exists = Path(file_path).exists()
            file_checks[file_path] = {
                'exists': exists,
                'status': 'PASS' if exists else 'FAIL'
            }

        checks['files'] = file_checks

        # Check environment variables
        required_env_vars = [
            'PAPER_TRADING_ENABLED',
            'LIVE_TRADING_DISABLED',
            'TRADING_MODE'
        ]

        env_checks = {}
        for var in required_env_vars:
            value = os.environ.get(var)
            env_checks[var] = {
                'value': value,
                'set': value is not None,
                'status': 'PASS' if value is not None else 'FAIL'
            }

        checks['environment'] = env_checks

        # Check directories
        required_dirs = [
            'src/paper_trading',
            'tests',
            'logs'
        ]

        dir_checks = {}
        for dir_path in required_dirs:
            path = Path(dir_path)
            exists = path.exists()
            if not exists and dir_path == 'logs':
                # Create logs directory if it doesn't exist
                path.mkdir(exist_ok=True)
                exists = True

            dir_checks[dir_path] = {
                'exists': exists,
                'status': 'PASS' if exists else 'FAIL'
            }

        checks['directories'] = dir_checks

        # Overall prerequisite status
        all_passed = all(
            checks['python_version']['status'] == 'PASS',
            all(c['status'] == 'PASS' for c in file_checks.values()),
            all(c['status'] == 'PASS' for c in env_checks.values()),
            all(c['status'] == 'PASS' for c in dir_checks.values())
        )

        checks['overall_status'] = 'PASS' if all_passed else 'FAIL'

        return checks

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all paper trading tests"""
        self.logger.info("Starting comprehensive paper trading test run...")

        # Setup environment
        env_config = self.setup_test_environment()

        # Check prerequisites
        prerequisites = self.check_prerequisites()

        if prerequisites['overall_status'] != 'PASS':
            self.logger.error("Prerequisites check failed!")
            return {
                'overall_status': 'FAIL',
                'reason': 'Prerequisites not met',
                'prerequisites': prerequisites
            }

        # Run test sequence
        test_sequence = [
            ('startup_test', self.run_startup_test),
            ('validation_suite', self.run_validation_suite),
            ('integration_tests', self.run_integration_tests)
        ]

        for test_name, test_func in test_sequence:
            self.logger.info(f"Running {test_name}...")
            start_time = time.time()

            try:
                result = await test_func()
                duration = time.time() - start_time

                result['duration'] = duration
                self.test_results[test_name] = result

                status = result.get('overall_status', 'UNKNOWN')
                self.logger.info(f"{test_name} completed: {status} ({duration:.2f}s)")

            except Exception as e:
                duration = time.time() - start_time
                self.logger.error(f"{test_name} failed: {e}")

                self.test_results[test_name] = {
                    'overall_status': 'ERROR',
                    'error': str(e),
                    'duration': duration
                }

        # Generate final report
        final_report = self._generate_final_report(env_config, prerequisites)

        # Save comprehensive report
        report_file = Path(__file__).parent / 'paper_trading_comprehensive_report.json'
        with open(report_file, 'w') as f:
            json.dump(final_report, f, indent=2, default=str)

        self.logger.info(f"Comprehensive test run complete: {final_report['overall_status']}")
        return final_report

    def _generate_final_report(self, env_config: Dict[str, str], prerequisites: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive final report"""
        # Calculate overall statistics
        total_test_suites = len(self.test_results)
        passed_suites = sum(1 for r in self.test_results.values()
                           if r.get('overall_status') == 'PASS')

        overall_success_rate = (passed_suites / total_test_suites) * 100 if total_test_suites > 0 else 0
        overall_status = 'PASS' if overall_success_rate >= 85 else 'FAIL'

        # Aggregate all individual test results
        all_individual_tests = []
        for suite_name, suite_result in self.test_results.items():
            if 'test_results' in suite_result:
                for test in suite_result['test_results']:
                    test['suite'] = suite_name
                    all_individual_tests.append(test)

        total_individual_tests = len(all_individual_tests)
        passed_individual_tests = sum(1 for t in all_individual_tests if t.get('success', False))

        report = {
            'report_type': 'paper_trading_comprehensive_validation',
            'timestamp': time.time(),
            'test_duration': time.time() - self.test_start_time,
            'environment_config': {k: v for k, v in env_config.items() if 'API' not in k},
            'prerequisites': prerequisites,
            'test_suites': {
                'total': total_test_suites,
                'passed': passed_suites,
                'failed': total_test_suites - passed_suites,
                'success_rate': overall_success_rate
            },
            'individual_tests': {
                'total': total_individual_tests,
                'passed': passed_individual_tests,
                'failed': total_individual_tests - passed_individual_tests,
                'success_rate': (passed_individual_tests / total_individual_tests) * 100 if total_individual_tests > 0 else 0
            },
            'overall_status': overall_status,
            'detailed_results': self.test_results,
            'summary': self._generate_summary(),
            'recommendations': self._generate_recommendations(),
            'next_steps': self._generate_next_steps()
        }

        return report

    def _generate_summary(self) -> str:
        """Generate test run summary"""
        passed_suites = sum(1 for r in self.test_results.values()
                           if r.get('overall_status') == 'PASS')
        total_suites = len(self.test_results)

        if passed_suites == total_suites:
            return ("All paper trading validation tests passed successfully. "
                   "The system is ready for paper trading validation period.")
        elif passed_suites > 0:
            return (f"{passed_suites}/{total_suites} test suites passed. "
                   "Some issues need to be addressed before paper trading.")
        else:
            return ("All test suites failed. Critical issues must be resolved "
                   "before attempting paper trading.")

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        # Check each test suite
        for suite_name, result in self.test_results.items():
            if result.get('overall_status') != 'PASS':
                recommendations.append(f"Fix issues in {suite_name} test suite")

        # General recommendations
        if all(r.get('overall_status') == 'PASS' for r in self.test_results.values()):
            recommendations.extend([
                "All tests passed - ready for paper trading validation",
                "Start with 24-hour validation period",
                "Monitor system closely during first few hours",
                "Verify no real orders are being placed",
                "Keep detailed logs of all activities"
            ])
        else:
            recommendations.extend([
                "Do not start paper trading until all tests pass",
                "Review failed test details and fix underlying issues",
                "Re-run tests after making fixes",
                "Ensure all safety mechanisms are working properly"
            ])

        return recommendations

    def _generate_next_steps(self) -> List[str]:
        """Generate next steps based on results"""
        next_steps = []

        if all(r.get('overall_status') == 'PASS' for r in self.test_results.values()):
            next_steps.extend([
                "1. Start paper trading bot with monitoring",
                "2. Observe for 1-2 hours to ensure stability",
                "3. Check balance simulation is working",
                "4. Verify WebSocket data feeds are active",
                "5. Monitor for any error messages or warnings",
                "6. Run periodic validation checks (every 24 hours)",
                "7. Document any issues or observations",
                "8. After 72+ hours, evaluate for live trading readiness"
            ])
        else:
            next_steps.extend([
                "1. Review failed test results in detail",
                "2. Fix configuration or code issues",
                "3. Re-run failed tests individually",
                "4. Run comprehensive test suite again",
                "5. Only proceed when all tests pass"
            ])

        return next_steps


async def main():
    """Main test runner function"""
    runner = PaperTradingTestRunner()

    print("🧪 PAPER TRADING COMPREHENSIVE TEST RUNNER")
    print("=" * 60)

    try:
        report = await runner.run_all_tests()

        print(f"\n{'='*60}")
        print("PAPER TRADING TEST RESULTS")
        print(f"{'='*60}")
        print(f"Overall Status: {report['overall_status']}")
        print(f"Test Suites: {report['test_suites']['passed']}/{report['test_suites']['total']} passed")
        print(f"Individual Tests: {report['individual_tests']['passed']}/{report['individual_tests']['total']} passed")
        print(f"Total Duration: {report['test_duration']:.2f} seconds")

        print("\n📝 Summary:")
        print(f"  {report['summary']}")

        if report['overall_status'] == 'PASS':
            print("\n✅ ALL TESTS PASSED")
            print("✅ Paper trading system is validated and ready")
            print("✅ You can proceed with paper trading validation period")
        else:
            print("\n❌ SOME TESTS FAILED")
            print("❌ Fix issues before starting paper trading")

        print("\n📋 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")

        print("\n👉 Next Steps:")
        for step in report['next_steps']:
            print(f"  {step}")

        print("\n📊 Detailed report: paper_trading_comprehensive_report.json")

        return report['overall_status'] == 'PASS'

    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        runner.logger.error(f"Test runner failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
