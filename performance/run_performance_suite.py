#!/usr/bin/env python3
"""
Master Performance Testing Suite
===============================

Orchestrates comprehensive performance testing for the crypto trading bot.
Runs all performance analysis modules and generates unified reports.

Usage:
    python run_performance_suite.py [--mode MODE] [--output OUTPUT_DIR] [--config CONFIG_FILE]

Modes:
    quick   - Quick performance check (10 minutes)
    full    - Complete performance analysis (60 minutes)  
    stress  - Extended stress testing (120 minutes)
    custom  - Custom configuration from file

Output:
    - Comprehensive performance report
    - Optimization recommendations
    - Implementation roadmap
    - Performance visualizations
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add performance modules to path
sys.path.append(os.path.dirname(__file__))

from benchmark_suite import HFTBenchmarkSuite
from latency_analyzer import CriticalPathLatencyAnalyzer
from load_testing import HFTLoadTester, LoadTestConfig
from memory_profiler import AdvancedMemoryProfiler
from optimization_report import PerformanceOptimizationReporter

logger = logging.getLogger(__name__)


class PerformanceTestSuite:
    """Master performance testing suite coordinator"""

    def __init__(self, mode: str = 'full', output_dir: str = None, config_file: str = None):
        """Initialize performance test suite"""
        self.mode = mode
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent / 'results'
        self.output_dir.mkdir(exist_ok=True)

        # Load configuration
        self.config = self._load_configuration(config_file)

        # Initialize components
        self.benchmark_suite = HFTBenchmarkSuite()
        self.load_tester = HFTLoadTester(self._create_load_test_config())
        self.memory_profiler = AdvancedMemoryProfiler(sampling_interval=0.5)
        self.latency_analyzer = CriticalPathLatencyAnalyzer()
        self.optimization_reporter = PerformanceOptimizationReporter(str(self.output_dir))

        # Test results
        self.results = {}
        self.start_time = time.time()

        logger.info(f"Performance Test Suite initialized - Mode: {mode}")

    def _load_configuration(self, config_file: str = None) -> Dict[str, Any]:
        """Load test configuration"""
        default_config = {
            'quick': {
                'benchmark_iterations': {
                    'auth_signature': 1000,
                    'rate_limiting': 10000,
                    'websocket_msg': 2000,
                    'balance_update': 1000,
                    'portfolio_calc': 200
                },
                'load_test_duration': 120,  # 2 minutes
                'memory_profiling_duration': 180,  # 3 minutes
                'latency_analysis_duration': 120,  # 2 minutes
            },
            'full': {
                'benchmark_iterations': {
                    'auth_signature': 10000,
                    'rate_limiting': 50000,
                    'websocket_msg': 10000,
                    'balance_update': 5000,
                    'portfolio_calc': 1000
                },
                'load_test_duration': 300,  # 5 minutes
                'memory_profiling_duration': 600,  # 10 minutes
                'latency_analysis_duration': 300,  # 5 minutes
            },
            'stress': {
                'benchmark_iterations': {
                    'auth_signature': 50000,
                    'rate_limiting': 100000,
                    'websocket_msg': 50000,
                    'balance_update': 20000,
                    'portfolio_calc': 5000
                },
                'load_test_duration': 900,  # 15 minutes
                'memory_profiling_duration': 1800,  # 30 minutes
                'latency_analysis_duration': 600,  # 10 minutes
            }
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file) as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    config = default_config.get(self.mode, default_config['full'])
                    config.update(user_config)
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")

        return default_config.get(self.mode, default_config['full'])

    def _create_load_test_config(self) -> LoadTestConfig:
        """Create load test configuration based on mode"""
        base_config = LoadTestConfig()

        if self.mode == 'quick':
            base_config.duration_seconds = 120
            base_config.target_operations_per_second = 1000
            base_config.burst_operations_per_second = 3000
        elif self.mode == 'full':
            base_config.duration_seconds = 300
            base_config.target_operations_per_second = 2000
            base_config.burst_operations_per_second = 8000
        elif self.mode == 'stress':
            base_config.duration_seconds = 900
            base_config.target_operations_per_second = 5000
            base_config.burst_operations_per_second = 15000

        return base_config

    async def run_complete_suite(self) -> Dict[str, Any]:
        """Run complete performance testing suite"""
        logger.info("="*80)
        logger.info("🚀 STARTING COMPREHENSIVE PERFORMANCE TESTING SUITE")
        logger.info("="*80)
        logger.info(f"Mode: {self.mode.upper()}")
        logger.info(f"Output Directory: {self.output_dir}")
        logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)

        try:
            # Phase 1: Benchmark Testing
            await self._run_benchmark_phase()

            # Phase 2: Load Testing
            await self._run_load_testing_phase()

            # Phase 3: Memory Profiling
            await self._run_memory_profiling_phase()

            # Phase 4: Latency Analysis
            await self._run_latency_analysis_phase()

            # Phase 5: Generate Comprehensive Report
            await self._generate_final_report()

            # Phase 6: Performance Summary
            self._print_final_summary()

            return self.results

        except Exception as e:
            logger.error(f"Performance testing suite failed: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _run_benchmark_phase(self):
        """Run benchmark testing phase"""
        logger.info("\n" + "="*60)
        logger.info("📊 PHASE 1: BENCHMARK TESTING")
        logger.info("="*60)

        phase_start = time.time()

        try:
            # Configure benchmarks based on mode
            if hasattr(self.benchmark_suite, 'config'):
                self.benchmark_suite.config['iterations'].update(
                    self.config.get('benchmark_iterations', {})
                )

            # Run benchmark suite
            logger.info("Running comprehensive HFT benchmark suite...")
            benchmark_results = await self.benchmark_suite.run_all_benchmarks()

            self.results['benchmark_results'] = benchmark_results

            # Print phase summary
            phase_duration = time.time() - phase_start
            summary = benchmark_results.get('summary', {})

            logger.info(f"\n✅ BENCHMARK PHASE COMPLETED ({phase_duration:.1f}s)")
            logger.info(f"   Tests: {summary.get('total_tests', 0)}")
            logger.info(f"   Passed: {summary.get('passed_tests', 0)}")
            logger.info(f"   Success Rate: {summary.get('success_rate', 0):.1f}%")

        except Exception as e:
            logger.error(f"Benchmark phase failed: {e}")
            raise

    async def _run_load_testing_phase(self):
        """Run load testing phase"""
        logger.info("\n" + "="*60)
        logger.info("⚡ PHASE 2: LOAD TESTING")
        logger.info("="*60)

        phase_start = time.time()

        try:
            # Run load testing suite
            logger.info("Running comprehensive HFT load testing...")
            load_test_results = await self.load_tester.run_comprehensive_load_tests()

            self.results['load_test_results'] = load_test_results

            # Print phase summary
            phase_duration = time.time() - phase_start
            summary = load_test_results.get('summary', {})

            logger.info(f"\n✅ LOAD TESTING PHASE COMPLETED ({phase_duration:.1f}s)")
            logger.info(f"   Scenarios: {summary.get('total_scenarios', 0)}")
            logger.info(f"   Operations: {summary.get('total_operations', 0):,}")
            logger.info(f"   Success Rate: {summary.get('overall_success_rate', 0):.1f}%")
            logger.info(f"   Avg Throughput: {summary.get('avg_operations_per_second', 0):.0f} ops/sec")

        except Exception as e:
            logger.error(f"Load testing phase failed: {e}")
            raise

    async def _run_memory_profiling_phase(self):
        """Run memory profiling phase"""
        logger.info("\n" + "="*60)
        logger.info("🧠 PHASE 3: MEMORY PROFILING")
        logger.info("="*60)

        phase_start = time.time()

        try:
            # Run memory profiling
            duration = self.config.get('memory_profiling_duration', 600)
            logger.info(f"Running memory profiling for {duration}s...")

            # Start profiling
            await self.memory_profiler.start_profiling(duration=duration)

            # Generate report
            memory_analysis = self.memory_profiler.generate_comprehensive_report()
            self.results['memory_analysis'] = memory_analysis

            # Print phase summary
            phase_duration = time.time() - phase_start
            memory_summary = memory_analysis.get('memory_summary', {})

            logger.info(f"\n✅ MEMORY PROFILING PHASE COMPLETED ({phase_duration:.1f}s)")
            logger.info(f"   Peak Memory: {memory_summary.get('peak_memory_mb', 0):.1f}MB")
            logger.info(f"   Memory Growth: {memory_summary.get('total_growth_mb', 0):.1f}MB")
            logger.info(f"   Growth Rate: {memory_summary.get('growth_rate_mb_per_minute', 0):.2f}MB/min")
            logger.info(f"   Detected Leaks: {len(memory_analysis.get('detected_leaks', []))}")

        except Exception as e:
            logger.error(f"Memory profiling phase failed: {e}")
            raise

    async def _run_latency_analysis_phase(self):
        """Run latency analysis phase"""
        logger.info("\n" + "="*60)
        logger.info("⚡ PHASE 4: LATENCY ANALYSIS")
        logger.info("="*60)

        phase_start = time.time()

        try:
            # Start latency monitoring
            self.latency_analyzer.start_monitoring()

            # Run latency benchmarks
            logger.info("Running trading operations latency benchmarks...")
            benchmark_results = await self.latency_analyzer.benchmark_trading_operations()

            # Analyze critical paths
            logger.info("Analyzing critical trading paths...")
            critical_paths = await self.latency_analyzer.analyze_critical_paths()

            # Generate analysis report
            latency_analysis = self.latency_analyzer.generate_latency_report()
            latency_analysis['benchmarks'] = benchmark_results

            self.results['latency_analysis'] = latency_analysis

            # Stop monitoring
            self.latency_analyzer.stop_monitoring()

            # Print phase summary
            phase_duration = time.time() - phase_start
            overall = latency_analysis.get('overall_performance', {})

            logger.info(f"\n✅ LATENCY ANALYSIS PHASE COMPLETED ({phase_duration:.1f}s)")
            logger.info(f"   Avg Latency: {overall.get('average_latency_ms', 0):.2f}ms")
            logger.info(f"   Max Latency: {overall.get('max_latency_ms', 0):.2f}ms")
            logger.info(f"   Critical Paths: {len(critical_paths)}")
            logger.info(f"   Regressions: {len(latency_analysis.get('detected_regressions', []))}")

        except Exception as e:
            logger.error(f"Latency analysis phase failed: {e}")
            raise

    async def _generate_final_report(self):
        """Generate comprehensive final report"""
        logger.info("\n" + "="*60)
        logger.info("📊 PHASE 5: GENERATING COMPREHENSIVE REPORT")
        logger.info("="*60)

        phase_start = time.time()

        try:
            # Generate optimization report
            logger.info("Analyzing results and generating optimization report...")

            comprehensive_report = await self.optimization_reporter.generate_comprehensive_report(
                benchmark_results=self.results.get('benchmark_results'),
                load_test_results=self.results.get('load_test_results'),
                memory_analysis=self.results.get('memory_analysis'),
                latency_analysis=self.results.get('latency_analysis')
            )

            self.results['comprehensive_report'] = comprehensive_report

            # Save master results file
            await self._save_master_results()

            # Print phase summary
            phase_duration = time.time() - phase_start
            executive_summary = comprehensive_report.get('executive_summary', {})

            logger.info(f"\n✅ REPORT GENERATION COMPLETED ({phase_duration:.1f}s)")
            logger.info(f"   Performance Score: {executive_summary.get('overall_performance_score', 0):.1f}/100")
            logger.info(f"   Optimization Opportunities: {executive_summary.get('total_optimization_opportunities', 0)}")
            logger.info(f"   Critical Issues: {executive_summary.get('issues_by_severity', {}).get('critical', 0)}")

        except Exception as e:
            logger.error(f"Report generation phase failed: {e}")
            raise

    async def _save_master_results(self):
        """Save master results file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Create master results with metadata
        master_results = {
            'metadata': {
                'suite_version': '2.0',
                'test_mode': self.mode,
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'end_time': datetime.now().isoformat(),
                'total_duration_seconds': time.time() - self.start_time,
                'configuration': self.config
            },
            'results': self.results,
            'summary': self._generate_master_summary()
        }

        # Save master results
        master_file = self.output_dir / f'master_performance_results_{timestamp}.json'
        with open(master_file, 'w') as f:
            json.dump(master_results, f, indent=2, default=str)

        logger.info(f"Master results saved to: {master_file}")

    def _generate_master_summary(self) -> Dict[str, Any]:
        """Generate master summary of all test results"""
        summary = {
            'overall_status': 'PASSED',
            'phase_results': {},
            'key_metrics': {},
            'critical_issues': [],
            'recommendations': []
        }

        # Benchmark summary
        if 'benchmark_results' in self.results:
            benchmark_summary = self.results['benchmark_results'].get('summary', {})
            summary['phase_results']['benchmarks'] = {
                'status': 'PASSED' if benchmark_summary.get('success_rate', 0) >= 90 else 'FAILED',
                'success_rate': benchmark_summary.get('success_rate', 0),
                'total_tests': benchmark_summary.get('total_tests', 0)
            }

            if benchmark_summary.get('success_rate', 0) < 90:
                summary['overall_status'] = 'FAILED'
                summary['critical_issues'].append('Benchmark success rate below 90%')

        # Load test summary
        if 'load_test_results' in self.results:
            load_summary = self.results['load_test_results'].get('summary', {})
            summary['phase_results']['load_tests'] = {
                'status': 'PASSED' if load_summary.get('overall_success_rate', 0) >= 95 else 'FAILED',
                'success_rate': load_summary.get('overall_success_rate', 0),
                'avg_throughput': load_summary.get('avg_operations_per_second', 0)
            }

            if load_summary.get('overall_success_rate', 0) < 95:
                summary['overall_status'] = 'FAILED'
                summary['critical_issues'].append('Load test success rate below 95%')

        # Memory analysis summary
        if 'memory_analysis' in self.results:
            memory_summary = self.results['memory_analysis'].get('memory_summary', {})
            growth_rate = memory_summary.get('growth_rate_mb_per_minute', 0)
            leaks = len(self.results['memory_analysis'].get('detected_leaks', []))

            summary['phase_results']['memory_analysis'] = {
                'status': 'PASSED' if growth_rate < 5 and leaks == 0 else 'WARNING' if growth_rate < 10 else 'FAILED',
                'growth_rate_mb_per_minute': growth_rate,
                'detected_leaks': leaks,
                'peak_memory_mb': memory_summary.get('peak_memory_mb', 0)
            }

            if growth_rate > 10 or leaks > 0:
                summary['critical_issues'].append(f'Memory issues: {growth_rate:.1f}MB/min growth, {leaks} leaks')

        # Latency analysis summary
        if 'latency_analysis' in self.results:
            latency_overall = self.results['latency_analysis'].get('overall_performance', {})
            regressions = len(self.results['latency_analysis'].get('detected_regressions', []))
            avg_latency = latency_overall.get('average_latency_ms', 0)

            summary['phase_results']['latency_analysis'] = {
                'status': 'PASSED' if avg_latency < 50 and regressions == 0 else 'WARNING',
                'average_latency_ms': avg_latency,
                'regressions_detected': regressions
            }

            if avg_latency > 100 or regressions > 2:
                summary['critical_issues'].append(f'Latency issues: {avg_latency:.1f}ms avg, {regressions} regressions')

        # Overall key metrics
        if 'comprehensive_report' in self.results:
            exec_summary = self.results['comprehensive_report'].get('executive_summary', {})
            summary['key_metrics'] = {
                'performance_score': exec_summary.get('overall_performance_score', 0),
                'performance_grade': exec_summary.get('performance_grade', 'F'),
                'optimization_opportunities': exec_summary.get('total_optimization_opportunities', 0),
                'critical_issues_count': exec_summary.get('issues_by_severity', {}).get('critical', 0),
                'estimated_improvement_weeks': exec_summary.get('estimated_implementation_time_weeks', 0)
            }

            # Add top recommendations
            recommendations = self.results['comprehensive_report'].get('recommendations', [])
            summary['recommendations'] = [rec['recommendation'] for rec in recommendations[:3]]

        return summary

    def _print_final_summary(self):
        """Print final performance testing summary"""
        total_duration = time.time() - self.start_time

        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE PERFORMANCE TESTING COMPLETED")
        print("="*80)

        print("\n⏱️  EXECUTION SUMMARY:")
        print(f"   Mode: {self.mode.upper()}")
        print(f"   Total Duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        print(f"   Start Time: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Phase results
        if 'comprehensive_report' in self.results:
            exec_summary = self.results['comprehensive_report']['executive_summary']

            print("\n📊 OVERALL RESULTS:")
            print(f"   Performance Score: {exec_summary['overall_performance_score']:.1f}/100")
            print(f"   Performance Grade: {exec_summary['performance_grade']}")
            print(f"   Optimization Opportunities: {exec_summary['total_optimization_opportunities']}")

            issues = exec_summary['issues_by_severity']
            print(f"   Critical Issues: {issues['critical']}")
            print(f"   High Priority Issues: {issues['high']}")
            print(f"   Medium Priority Issues: {issues['medium']}")

            if exec_summary['immediate_actions_required']:
                print("\n🚨 IMMEDIATE ACTION REQUIRED")
                print("   Critical performance issues detected that need immediate attention!")

            print("\n💡 TOP RECOMMENDATIONS:")
            recommendations = self.results['comprehensive_report'].get('recommendations', [])
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec['category']}: {rec['recommendation']}")
                print(f"      Expected: {rec['expected_improvement']}")
                print(f"      Timeline: {rec['estimated_timeline']}")

        # Individual phase results
        master_summary = self._generate_master_summary()

        print("\n📋 PHASE RESULTS:")
        for phase, result in master_summary['phase_results'].items():
            status_icon = "✅" if result['status'] == 'PASSED' else "⚠️" if result['status'] == 'WARNING' else "❌"
            print(f"   {status_icon} {phase.title()}: {result['status']}")

        # Critical issues
        if master_summary['critical_issues']:
            print("\n🚨 CRITICAL ISSUES DETECTED:")
            for issue in master_summary['critical_issues']:
                print(f"   • {issue}")

        print("\n📂 OUTPUT FILES:")
        print(f"   Results Directory: {self.output_dir}")
        print("   • Master Results: master_performance_results_*.json")
        print("   • Optimization Report: performance_optimization_report_*.json")
        print("   • Executive Summary: executive_summary_*.json")
        print("   • Implementation Roadmap: implementation_roadmap_*.json")
        print("   • Performance Charts: *.png visualizations")

        # Final status
        overall_status = master_summary['overall_status']
        status_icon = "✅" if overall_status == 'PASSED' else "❌"

        print(f"\n{status_icon} FINAL RESULT: {overall_status}")
        if overall_status == 'PASSED':
            print("   System performance meets high-frequency trading requirements!")
        else:
            print("   Performance optimization required before production deployment.")

        print("\n" + "="*80)


async def main():
    """Main entry point for performance testing suite"""

    # Command line argument parsing
    parser = argparse.ArgumentParser(
        description='Comprehensive Performance Testing Suite for HFT Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_performance_suite.py --mode quick
  python run_performance_suite.py --mode full --output ./results
  python run_performance_suite.py --mode stress --config stress_config.json
        """
    )

    parser.add_argument(
        '--mode',
        choices=['quick', 'full', 'stress', 'custom'],
        default='full',
        help='Testing mode (default: full)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output directory for results (default: ./performance/results)'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Custom configuration file path'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                Path(args.output) / 'performance_test_suite.log' if args.output
                else 'performance_test_suite.log'
            )
        ]
    )

    try:
        # Create and run performance test suite
        suite = PerformanceTestSuite(
            mode=args.mode,
            output_dir=args.output,
            config_file=args.config
        )

        # Run complete suite
        results = await suite.run_complete_suite()

        # Determine exit code based on results
        master_summary = suite._generate_master_summary()
        overall_status = master_summary['overall_status']

        if overall_status == 'PASSED':
            logger.info("✅ Performance testing suite PASSED")
            return 0
        else:
            logger.error("❌ Performance testing suite FAILED")
            return 1

    except KeyboardInterrupt:
        logger.warning("Performance testing interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Performance testing suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
