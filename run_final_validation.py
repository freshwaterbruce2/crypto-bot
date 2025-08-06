#!/usr/bin/env python3
"""
Final Validation Script - Production Readiness Assessment
========================================================

This script runs the comprehensive test suite and generates the final
production readiness assessment for the crypto trading bot.

Usage:
    python run_final_validation.py [--quick] [--verbose] [--html]

Features:
- Complete validation of all critical fixes
- Performance benchmarking
- Security assessment  
- Production readiness determination
- Detailed reporting with recommendations
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'tests'))
sys.path.insert(0, str(current_dir / 'src'))

from tests.automated_test_runner import AutomatedTestRunner, TestRunConfig


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'final_validation_{int(time.time())}.log')
        ]
    )


def print_banner():
    """Print validation banner"""
    print("=" * 80)
    print("CRYPTO TRADING BOT - FINAL VALIDATION & PRODUCTION ASSESSMENT")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {Path.cwd()}")
    print("=" * 80)
    print()


def print_validation_criteria():
    """Print the validation criteria"""
    print("VALIDATION CRITERIA:")
    print("=" * 40)
    print("✅ 100% critical component initialization success")
    print("✅ Zero security vulnerabilities detected")
    print("✅ <10MB total log file size with rotation")
    print("✅ >99% nonce generation success rate")
    print("✅ <100ms average response times")
    print("✅ Clean shutdown with zero resource leaks")
    print("✅ >4700 nonces/sec generation performance")
    print("✅ All Balance Manager V2 modes operational")
    print("✅ Professional logging system functional")
    print("✅ Circuit breaker and error recovery working")
    print()


def analyze_validation_results(results):
    """Analyze validation results and provide detailed assessment"""

    print("DETAILED VALIDATION ANALYSIS")
    print("=" * 60)

    # Overall assessment
    summary = results.get_summary()
    overall_success = summary.get('overall_success', False)

    print(f"Overall Status: {'✅ PRODUCTION READY' if overall_success else '❌ NOT PRODUCTION READY'}")
    print(f"Test Duration: {summary.get('duration_minutes', 0):.1f} minutes")
    print()

    # Validation results analysis
    if 'validation' in summary:
        val = summary['validation']
        print("COMPONENT VALIDATION:")
        print(f"  Tests Passed: {val['passed_tests']}/{val['total_tests']} ({val['success_rate']:.1f}%)")
        print(f"  Production Ready: {'Yes' if val['production_ready'] else 'No'}")

        # Detailed validation metrics
        if hasattr(results, 'validation_results') and results.validation_results:
            val_results = results.validation_results

            print("\n  Critical Component Status:")
            critical_components = [
                "balance_manager_v2_init",
                "consolidated_nonce_manager",
                "professional_logging_system",
                "websocket_authentication",
                "circuit_breaker"
            ]

            for component in critical_components:
                if component in val_results.performance_metrics:
                    print(f"    ✅ {component.replace('_', ' ').title()}")
                else:
                    print(f"    ❌ {component.replace('_', ' ').title()}")

            if val_results.security_issues:
                print(f"\n  ⚠️  Security Issues: {len(val_results.security_issues)}")
                for issue in val_results.security_issues[:3]:  # Show first 3
                    print(f"    - {issue}")

            if val_results.memory_leaks:
                print(f"\n  🧠 Memory Issues: {len(val_results.memory_leaks)}")
                for leak in val_results.memory_leaks:
                    print(f"    - {leak}")

        print()

    # Performance benchmarks analysis
    if 'benchmarks' in summary:
        bench = summary['benchmarks']
        print("PERFORMANCE BENCHMARKS:")
        print(f"  Metrics Passed: {bench['passed_metrics']}/{bench['total_metrics']} ({bench['success_rate']:.1f}%)")
        print(f"  Bottlenecks Found: {bench['bottlenecks_count']}")
        print(f"  Optimization Recommendations: {bench['high_priority_recommendations']} high priority")

        # Key performance metrics
        if hasattr(results, 'benchmark_results') and results.benchmark_results:
            bench_results = results.benchmark_results

            print("\n  Key Performance Metrics:")
            key_metrics = [
                ('nonce_generation', 'throughput_batch_10000', 'Nonce Generation'),
                ('logging_system', 'sync_throughput_50000', 'Logging Throughput'),
                ('memory_usage', 'peak_memory_increase', 'Memory Usage'),
                ('balance_manager', 'avg_response_time_1000', 'Response Time')
            ]

            for category, metric_name, display_name in key_metrics:
                if category in bench_results.metrics and metric_name in bench_results.metrics[category]:
                    metric = bench_results.metrics[category][metric_name]
                    status = "✅" if metric['meets_target'] else "❌"
                    target_info = f" (target: {metric['target']}{metric['unit']})" if metric['target'] else ""
                    print(f"    {status} {display_name}: {metric['value']}{metric['unit']}{target_info}")

        print()

    # Security analysis
    if 'security' in summary:
        sec = summary['security']
        print("SECURITY ASSESSMENT:")
        print(f"  Issues Found: {sec['issues_found']}")
        print(f"  Critical Issues: {sec['critical_issues']}")

        if sec['issues_found'] == 0:
            print("  ✅ No security vulnerabilities detected")
        elif sec['critical_issues'] > 0:
            print(f"  🔴 CRITICAL: {sec['critical_issues']} critical security issues require immediate attention")
        else:
            print(f"  🟡 {sec['issues_found']} non-critical security issues found")

        print()

    # Errors analysis
    if summary.get('errors_count', 0) > 0:
        print("ERRORS ENCOUNTERED:")
        print(f"  Total Errors: {summary['errors_count']}")

        if hasattr(results, 'errors') and results.errors:
            for i, error in enumerate(results.errors[:5], 1):  # Show first 5 errors
                print(f"    {i}. {error}")

            if len(results.errors) > 5:
                print(f"    ... and {len(results.errors) - 5} more errors")

        print()


def generate_production_recommendation(results):
    """Generate final production deployment recommendation"""

    print("PRODUCTION DEPLOYMENT RECOMMENDATION")
    print("=" * 60)

    summary = results.get_summary()
    overall_success = summary.get('overall_success', False)

    if overall_success:
        print("🚀 RECOMMENDATION: APPROVED FOR PRODUCTION DEPLOYMENT")
        print()
        print("✅ All critical validation criteria have been met:")
        print("   - Component initialization: 100% success")
        print("   - Security vulnerabilities: None detected")
        print("   - Performance targets: All met")
        print("   - Memory management: No leaks detected")
        print("   - Error recovery: Fully functional")
        print()
        print("The trading bot is ready for live trading operations.")

    else:
        print("⛔ RECOMMENDATION: NOT APPROVED FOR PRODUCTION")
        print()
        print("❌ Critical issues must be resolved before deployment:")

        # Identify specific blocking issues
        blocking_issues = []

        if 'validation' in summary and not summary['validation']['production_ready']:
            blocking_issues.append("Core component validation failures")

        if 'benchmarks' in summary and summary['benchmarks']['success_rate'] < 80:
            blocking_issues.append(f"Performance targets not met ({summary['benchmarks']['success_rate']:.1f}% success rate)")

        if 'security' in summary and summary['security']['critical_issues'] > 0:
            blocking_issues.append(f"{summary['security']['critical_issues']} critical security vulnerabilities")

        if summary.get('errors_count', 0) > 0:
            blocking_issues.append(f"{summary['errors_count']} system errors encountered")

        for i, issue in enumerate(blocking_issues, 1):
            print(f"   {i}. {issue}")

        print()
        print("🔧 REQUIRED ACTIONS:")
        print("   1. Resolve all critical issues listed above")
        print("   2. Re-run validation suite until all tests pass")
        print("   3. Verify performance targets are consistently met")
        print("   4. Complete security audit and remediation")
        print("   5. Test error recovery scenarios thoroughly")

    print()


def save_certification_report(results, output_file: str):
    """Save production certification report"""

    summary = results.get_summary()

    certification = {
        "certification_date": datetime.now().isoformat(),
        "system_name": "Crypto Trading Bot 2025",
        "version": "4.0.0",
        "production_ready": summary.get('overall_success', False),
        "validation_summary": summary,
        "certification_criteria": {
            "component_initialization": "100% success required",
            "security_vulnerabilities": "Zero critical issues required",
            "performance_targets": ">99% success rate required",
            "memory_management": "No leaks permitted",
            "error_recovery": "Full functionality required"
        },
        "test_execution": {
            "duration_minutes": summary.get('duration_minutes', 0),
            "total_tests_run": summary.get('validation', {}).get('total_tests', 0),
            "performance_metrics_evaluated": summary.get('benchmarks', {}).get('total_metrics', 0),
            "security_scan_completed": 'security' in summary
        },
        "next_validation_due": (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) +
                              timedelta(days=30)).isoformat(),
        "certification_authority": "Automated Test Suite v1.0"
    }

    with open(output_file, 'w') as f:
        json.dump(certification, f, indent=2)

    print(f"📋 Production certification report saved to: {output_file}")


async def main():
    """Main validation execution"""

    import argparse

    parser = argparse.ArgumentParser(description="Final Production Validation")
    parser.add_argument("--quick", action="store_true", help="Run quick validation (skip benchmarks)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--output-dir", default="validation_results", help="Output directory")

    args = parser.parse_args()

    # Setup
    setup_logging(args.verbose)
    print_banner()
    print_validation_criteria()

    # Configure test run
    config = TestRunConfig(
        run_validation=True,
        run_benchmarks=not args.quick,
        run_security_scan=True,
        generate_html_report=args.html,
        verbose=args.verbose,
        timeout_minutes=45 if not args.quick else 15,
        output_dir=args.output_dir
    )

    print("EXECUTING VALIDATION SUITE...")
    print("=" * 40)

    try:
        # Run validation
        runner = AutomatedTestRunner(config)
        results = await runner.run_all_tests()

        print("\n" + "=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80)

        # Analyze results
        analyze_validation_results(results)

        # Generate recommendation
        generate_production_recommendation(results)

        # Save certification report
        cert_file = f"{args.output_dir}/production_certification_{int(time.time())}.json"
        save_certification_report(results, cert_file)

        print("=" * 80)
        print(f"Final Status: {'✅ VALIDATION PASSED' if results.overall_success else '❌ VALIDATION FAILED'}")
        print("=" * 80)

        return results.overall_success

    except Exception as e:
        print(f"\n❌ VALIDATION FAILED WITH ERROR: {str(e)}")
        logging.error(f"Validation failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
