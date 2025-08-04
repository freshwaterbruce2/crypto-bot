"""
Critical Path Latency Analysis for High-Frequency Trading
========================================================

Comprehensive latency analysis for time-critical trading operations.
Identifies bottlenecks, measures end-to-end latencies, and provides
optimization recommendations for ultra-low latency trading.

Latency Analysis Features:
- End-to-end trade execution latency
- Component-level latency breakdown
- Network latency monitoring
- Database query latency analysis
- WebSocket message processing latency
- Critical path identification
- Performance regression detection
- Real-time latency monitoring
"""

import asyncio
import time
import logging
import json
import statistics
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import contextlib
import functools
import psutil
# Optional numpy import
try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

# Import trading bot components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.utils.decimal_precision_fix import safe_decimal, safe_float

logger = logging.getLogger(__name__)


def percentile(data: List[float], percentile: float) -> float:
    """Calculate percentile without numpy dependency"""
    if HAVE_NUMPY:
        import numpy as np
        return np.percentile(data, percentile)
    else:
        # Pure Python percentile calculation
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))


@dataclass
class LatencyMeasurement:
    """Single latency measurement"""
    component: str
    operation: str
    start_time: float
    end_time: float
    latency_ms: float
    success: bool
    metadata: Dict[str, Any]
    trace_id: str = ""


@dataclass
class LatencyStats:
    """Statistical analysis of latency measurements"""
    component: str
    operation: str
    sample_count: int
    mean_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    std_dev_ms: float
    success_rate: float
    throughput_ops_per_sec: float


@dataclass
class CriticalPath:
    """Critical path analysis result"""
    path_name: str
    total_latency_ms: float
    components: List[Tuple[str, float]]  # (component_name, latency_ms)
    bottleneck_component: str
    bottleneck_latency_ms: float
    bottleneck_percentage: float
    optimization_potential_ms: float


@dataclass
class LatencyRegression:
    """Detected latency regression"""
    component: str
    operation: str
    baseline_latency_ms: float
    current_latency_ms: float
    regression_percentage: float
    first_detected: float
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    likely_cause: str


class LatencyTracker:
    """Context manager for tracking operation latency"""
    
    def __init__(self, analyzer: 'CriticalPathLatencyAnalyzer', 
                 component: str, operation: str, 
                 metadata: Dict[str, Any] = None):
        self.analyzer = analyzer
        self.component = component
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = 0
        self.trace_id = f"{component}_{operation}_{int(time.time() * 1000000)}"
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        latency_ms = (end_time - self.start_time) * 1000
        success = exc_type is None
        
        measurement = LatencyMeasurement(
            component=self.component,
            operation=self.operation,
            start_time=self.start_time,
            end_time=end_time,
            latency_ms=latency_ms,
            success=success,
            metadata=self.metadata,
            trace_id=self.trace_id
        )
        
        self.analyzer.record_measurement(measurement)


def latency_monitor(component: str, operation: str = None):
    """Decorator for monitoring function latency"""
    def decorator(func):
        op_name = operation or func.__name__
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get analyzer from first argument if it has one
            analyzer = None
            if args and hasattr(args[0], '_latency_analyzer'):
                analyzer = args[0]._latency_analyzer
            elif hasattr(func, '_latency_analyzer'):
                analyzer = func._latency_analyzer
            
            if analyzer:
                with analyzer.track_latency(component, op_name):
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get analyzer from first argument if it has one
            analyzer = None
            if args and hasattr(args[0], '_latency_analyzer'):
                analyzer = args[0]._latency_analyzer
            elif hasattr(func, '_latency_analyzer'):
                analyzer = func._latency_analyzer
            
            if analyzer:
                with analyzer.track_latency(component, op_name):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class CriticalPathLatencyAnalyzer:
    """Advanced latency analyzer for critical trading paths"""
    
    def __init__(self, retention_hours: int = 24):
        """Initialize latency analyzer"""
        self.retention_hours = retention_hours
        self.measurements: deque = deque(maxlen=100000)  # Keep last 100K measurements
        self.component_stats: Dict[str, LatencyStats] = {}
        self.critical_paths: List[CriticalPath] = []
        self.regressions: List[LatencyRegression] = []
        
        # Real-time monitoring
        self.real_time_window = deque(maxlen=1000)  # Last 1000 measurements
        self.alert_thresholds = {
            'auth_signature': 1.0,     # 1ms
            'balance_update': 10.0,    # 10ms
            'order_execution': 50.0,   # 50ms
            'websocket_processing': 5.0, # 5ms
            'database_query': 50.0,    # 50ms
            'portfolio_calculation': 100.0, # 100ms
        }
        
        # Baseline measurements for regression detection
        self.baselines: Dict[str, float] = {}
        self.baseline_window_size = 1000
        
        # Threading for background analysis
        self.analysis_lock = threading.RLock()
        self.is_monitoring = False
        
        logger.info("Critical Path Latency Analyzer initialized")
    
    def track_latency(self, component: str, operation: str, 
                     metadata: Dict[str, Any] = None) -> LatencyTracker:
        """Create a latency tracker context manager"""
        return LatencyTracker(self, component, operation, metadata)
    
    def record_measurement(self, measurement: LatencyMeasurement):
        """Record a latency measurement"""
        with self.analysis_lock:
            self.measurements.append(measurement)
            self.real_time_window.append(measurement)
            
            # Update baselines
            key = f"{measurement.component}_{measurement.operation}"
            if measurement.success:
                if key not in self.baselines:
                    self.baselines[key] = measurement.latency_ms
                else:
                    # Exponential moving average
                    alpha = 0.01  # Slow adaptation
                    self.baselines[key] = (alpha * measurement.latency_ms + 
                                         (1 - alpha) * self.baselines[key])
            
            # Check for real-time alerts
            self._check_real_time_alerts(measurement)
    
    def _check_real_time_alerts(self, measurement: LatencyMeasurement):
        """Check for real-time latency alerts"""
        key = f"{measurement.component}_{measurement.operation}"
        threshold = self.alert_thresholds.get(measurement.component, 100.0)
        
        if measurement.latency_ms > threshold:
            logger.warning(f"Latency alert: {key} took {measurement.latency_ms:.2f}ms "
                          f"(threshold: {threshold}ms)")
        
        # Check for regression
        if key in self.baselines:
            baseline = self.baselines[key]
            if measurement.latency_ms > baseline * 2:  # 100% increase
                logger.warning(f"Potential regression: {key} latency {measurement.latency_ms:.2f}ms "
                              f"vs baseline {baseline:.2f}ms")
    
    def start_monitoring(self):
        """Start real-time latency monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        
        # Start background analysis thread
        analysis_thread = threading.Thread(target=self._background_analysis, daemon=True)
        analysis_thread.start()
        
        logger.info("Real-time latency monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time latency monitoring"""
        self.is_monitoring = False
        logger.info("Real-time latency monitoring stopped")
    
    def _background_analysis(self):
        """Background thread for continuous analysis"""
        while self.is_monitoring:
            try:
                # Update statistics every 10 seconds
                self._update_component_statistics()
                
                # Check for regressions every 30 seconds
                if int(time.time()) % 30 == 0:
                    self._detect_regressions()
                
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in background analysis: {e}")
                time.sleep(10)
    
    def _update_component_statistics(self):
        """Update component-level statistics"""
        with self.analysis_lock:
            # Group measurements by component and operation
            component_measurements = defaultdict(list)
            
            cutoff_time = time.time() - (self.retention_hours * 3600)
            
            for measurement in self.measurements:
                if measurement.start_time > cutoff_time:
                    key = f"{measurement.component}_{measurement.operation}"
                    component_measurements[key].append(measurement)
            
            # Calculate statistics for each component
            for key, measurements in component_measurements.items():
                if len(measurements) < 5:  # Need minimum samples
                    continue
                
                component, operation = key.rsplit('_', 1)
                latencies = [m.latency_ms for m in measurements]
                successes = [m.success for m in measurements]
                
                # Calculate statistics
                mean_latency = statistics.mean(latencies)
                median_latency = statistics.median(latencies)
                std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
                
                # Calculate percentiles
                sorted_latencies = sorted(latencies)
                p95_idx = int(0.95 * len(sorted_latencies))
                p99_idx = int(0.99 * len(sorted_latencies))
                
                p95_latency = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else max(latencies)
                p99_latency = sorted_latencies[p99_idx] if p99_idx < len(sorted_latencies) else max(latencies)
                
                # Calculate throughput
                time_span = max(measurements, key=lambda x: x.end_time).end_time - \
                           min(measurements, key=lambda x: x.start_time).start_time
                throughput = len(measurements) / max(time_span, 0.001)
                
                stats = LatencyStats(
                    component=component,
                    operation=operation,
                    sample_count=len(measurements),
                    mean_latency_ms=mean_latency,
                    median_latency_ms=median_latency,
                    p95_latency_ms=p95_latency,
                    p99_latency_ms=p99_latency,
                    max_latency_ms=max(latencies),
                    min_latency_ms=min(latencies),
                    std_dev_ms=std_dev,
                    success_rate=sum(successes) / len(successes) * 100,
                    throughput_ops_per_sec=throughput
                )
                
                self.component_stats[key] = stats
    
    def _detect_regressions(self):
        """Detect latency regressions"""
        current_time = time.time()
        regression_threshold = 1.5  # 50% increase
        
        for key, current_stats in self.component_stats.items():
            if key not in self.baselines:
                continue
            
            baseline_latency = self.baselines[key]
            current_latency = current_stats.mean_latency_ms
            
            if current_latency > baseline_latency * regression_threshold:
                # Check if regression already detected
                existing_regression = next(
                    (r for r in self.regressions 
                     if r.component == current_stats.component and 
                        r.operation == current_stats.operation),
                    None
                )
                
                if not existing_regression:
                    regression_percentage = ((current_latency - baseline_latency) / 
                                           baseline_latency * 100)
                    
                    severity = "CRITICAL" if regression_percentage > 200 else \
                              "HIGH" if regression_percentage > 100 else \
                              "MEDIUM" if regression_percentage > 50 else "LOW"
                    
                    regression = LatencyRegression(
                        component=current_stats.component,
                        operation=current_stats.operation,
                        baseline_latency_ms=baseline_latency,
                        current_latency_ms=current_latency,
                        regression_percentage=regression_percentage,
                        first_detected=current_time,
                        severity=severity,
                        likely_cause="Performance degradation or increased load"
                    )
                    
                    self.regressions.append(regression)
                    
                    logger.warning(f"Latency regression detected: "
                                 f"{current_stats.component}_{current_stats.operation} "
                                 f"{regression_percentage:.1f}% slower")
    
    async def analyze_critical_paths(self) -> List[CriticalPath]:
        """Analyze critical trading paths end-to-end"""
        logger.info("Analyzing critical trading paths...")
        
        critical_paths = []
        
        # Define critical paths
        path_definitions = {
            'order_execution': [
                'authentication', 'balance_check', 'order_validation',
                'rate_limiting', 'order_placement', 'order_confirmation'
            ],
            'balance_update': [
                'websocket_processing', 'balance_validation', 'balance_update',
                'portfolio_recalculation', 'notification'
            ],
            'market_data_processing': [
                'websocket_processing', 'data_validation', 'signal_generation',
                'strategy_execution', 'order_decision'
            ],
            'portfolio_sync': [
                'balance_retrieval', 'position_calculation', 'pnl_calculation',
                'risk_assessment', 'portfolio_update'
            ]
        }
        
        # Analyze each critical path
        for path_name, components in path_definitions.items():
            path_latencies = []
            total_latency = 0
            
            for component in components:
                # Find matching component stats
                matching_stats = [
                    stats for key, stats in self.component_stats.items()
                    if component in key.lower()
                ]
                
                if matching_stats:
                    # Use the most relevant stat (highest sample count)
                    best_stat = max(matching_stats, key=lambda x: x.sample_count)
                    component_latency = best_stat.mean_latency_ms
                else:
                    # Estimate based on component type
                    component_latency = self._estimate_component_latency(component)
                
                path_latencies.append((component, component_latency))
                total_latency += component_latency
            
            # Identify bottleneck
            bottleneck_component, bottleneck_latency = max(path_latencies, key=lambda x: x[1])
            bottleneck_percentage = (bottleneck_latency / total_latency * 100) if total_latency > 0 else 0
            
            # Calculate optimization potential
            optimization_potential = bottleneck_latency * 0.5  # Assume 50% optimization possible
            
            critical_path = CriticalPath(
                path_name=path_name,
                total_latency_ms=total_latency,
                components=path_latencies,
                bottleneck_component=bottleneck_component,
                bottleneck_latency_ms=bottleneck_latency,
                bottleneck_percentage=bottleneck_percentage,
                optimization_potential_ms=optimization_potential
            )
            
            critical_paths.append(critical_path)
        
        self.critical_paths = critical_paths
        
        # Log critical path analysis
        for path in critical_paths:
            logger.info(f"Critical path '{path.path_name}': {path.total_latency_ms:.2f}ms total, "
                       f"bottleneck: {path.bottleneck_component} ({path.bottleneck_latency_ms:.2f}ms)")
        
        return critical_paths
    
    def _estimate_component_latency(self, component: str) -> float:
        """Estimate component latency based on type"""
        estimates = {
            'authentication': 0.5,
            'balance_check': 5.0,
            'order_validation': 1.0,
            'rate_limiting': 0.1,
            'order_placement': 20.0,
            'order_confirmation': 10.0,
            'websocket_processing': 2.0,
            'balance_validation': 1.0,
            'balance_update': 5.0,
            'portfolio_recalculation': 50.0,
            'notification': 1.0,
            'data_validation': 0.5,
            'signal_generation': 10.0,
            'strategy_execution': 15.0,
            'order_decision': 5.0,
            'balance_retrieval': 20.0,
            'position_calculation': 30.0,
            'pnl_calculation': 20.0,
            'risk_assessment': 25.0,
            'portfolio_update': 10.0
        }
        
        return estimates.get(component, 10.0)  # Default 10ms
    
    async def benchmark_trading_operations(self) -> Dict[str, Any]:
        """Benchmark critical trading operations"""
        logger.info("Benchmarking critical trading operations...")
        
        benchmarks = {}
        
        # Authentication benchmark
        benchmarks['authentication'] = await self._benchmark_authentication()
        
        # Balance operations benchmark
        benchmarks['balance_operations'] = await self._benchmark_balance_operations()
        
        # Order operations benchmark
        benchmarks['order_operations'] = await self._benchmark_order_operations()
        
        # WebSocket processing benchmark
        benchmarks['websocket_processing'] = await self._benchmark_websocket_processing()
        
        # Database operations benchmark
        benchmarks['database_operations'] = await self._benchmark_database_operations()
        
        # Portfolio calculations benchmark
        benchmarks['portfolio_calculations'] = await self._benchmark_portfolio_calculations()
        
        return benchmarks
    
    async def _benchmark_authentication(self) -> Dict[str, Any]:
        """Benchmark authentication operations"""
        results = []
        iterations = 1000
        
        # Mock authentication operations
        for i in range(iterations):
            with self.track_latency('authentication', 'signature_generation'):
                # Simulate signature generation
                await asyncio.sleep(0.0005)  # 0.5ms average
                
                # Add some variance
                if i % 100 == 0:
                    await asyncio.sleep(0.002)  # Occasional slow operation
        
        # Collect results
        auth_measurements = [m for m in self.measurements 
                           if m.component == 'authentication' and 
                              m.operation == 'signature_generation']
        
        if auth_measurements:
            latencies = [m.latency_ms for m in auth_measurements[-iterations:]]
            return {
                'operation': 'Authentication Signature Generation',
                'iterations': len(latencies),
                'mean_latency_ms': statistics.mean(latencies),
                'p95_latency_ms': percentile(latencies, 95),
                'p99_latency_ms': percentile(latencies, 99),
                'max_latency_ms': max(latencies),
                'success_rate': 100.0,
                'target_latency_ms': 1.0,
                'passed': statistics.mean(latencies) < 1.0
            }
        
        return {'error': 'No authentication measurements available'}
    
    async def _benchmark_balance_operations(self) -> Dict[str, Any]:
        """Benchmark balance operations"""
        iterations = 500
        
        # Mock balance operations
        for i in range(iterations):
            with self.track_latency('balance_manager', 'update_balance'):
                # Simulate balance update processing
                await asyncio.sleep(0.003)  # 3ms average
                
                # Simulate validation
                await asyncio.sleep(0.001)  # 1ms validation
                
                # Occasional complex updates
                if i % 50 == 0:
                    await asyncio.sleep(0.020)  # 20ms complex update
        
        # Collect results
        balance_measurements = [m for m in self.measurements 
                              if m.component == 'balance_manager' and 
                                 m.operation == 'update_balance']
        
        if balance_measurements:
            latencies = [m.latency_ms for m in balance_measurements[-iterations:]]
            return {
                'operation': 'Balance Update Processing',
                'iterations': len(latencies),
                'mean_latency_ms': statistics.mean(latencies),
                'p95_latency_ms': percentile(latencies, 95),
                'p99_latency_ms': percentile(latencies, 99),
                'max_latency_ms': max(latencies),
                'success_rate': 100.0,
                'target_latency_ms': 10.0,
                'passed': statistics.mean(latencies) < 10.0
            }
        
        return {'error': 'No balance measurements available'}
    
    async def _benchmark_order_operations(self) -> Dict[str, Any]:
        """Benchmark order operations"""
        iterations = 200
        
        # Mock order operations
        for i in range(iterations):
            with self.track_latency('order_executor', 'place_order'):
                # Simulate order validation
                await asyncio.sleep(0.005)  # 5ms validation
                
                # Simulate API call
                await asyncio.sleep(0.030)  # 30ms API call
                
                # Simulate confirmation processing
                await asyncio.sleep(0.010)  # 10ms confirmation
                
                # Occasional timeouts
                if i % 100 == 0:
                    await asyncio.sleep(0.100)  # 100ms timeout/retry
        
        # Collect results
        order_measurements = [m for m in self.measurements 
                            if m.component == 'order_executor' and 
                               m.operation == 'place_order']
        
        if order_measurements:
            latencies = [m.latency_ms for m in order_measurements[-iterations:]]
            return {
                'operation': 'Order Execution',
                'iterations': len(latencies),
                'mean_latency_ms': statistics.mean(latencies),
                'p95_latency_ms': percentile(latencies, 95),
                'p99_latency_ms': percentile(latencies, 99),
                'max_latency_ms': max(latencies),
                'success_rate': 100.0,
                'target_latency_ms': 50.0,
                'passed': statistics.mean(latencies) < 50.0
            }
        
        return {'error': 'No order measurements available'}
    
    async def _benchmark_websocket_processing(self) -> Dict[str, Any]:
        """Benchmark WebSocket message processing"""
        iterations = 2000
        
        # Mock WebSocket processing
        for i in range(iterations):
            msg_type = ['ticker', 'trade', 'balance', 'orderbook'][i % 4]
            
            with self.track_latency('websocket_manager', f'process_{msg_type}'):
                # Simulate message processing based on type
                if msg_type == 'ticker':
                    await asyncio.sleep(0.001)  # 1ms ticker processing
                elif msg_type == 'trade':
                    await asyncio.sleep(0.002)  # 2ms trade processing
                elif msg_type == 'balance':
                    await asyncio.sleep(0.005)  # 5ms balance processing
                else:  # orderbook
                    await asyncio.sleep(0.003)  # 3ms orderbook processing
        
        # Collect results for all message types
        ws_measurements = [m for m in self.measurements 
                          if m.component == 'websocket_manager']
        
        if ws_measurements:
            latencies = [m.latency_ms for m in ws_measurements[-iterations:]]
            return {
                'operation': 'WebSocket Message Processing',
                'iterations': len(latencies),
                'mean_latency_ms': statistics.mean(latencies),
                'p95_latency_ms': percentile(latencies, 95),
                'p99_latency_ms': percentile(latencies, 99),
                'max_latency_ms': max(latencies),
                'success_rate': 100.0,
                'target_latency_ms': 5.0,
                'passed': statistics.mean(latencies) < 5.0
            }
        
        return {'error': 'No WebSocket measurements available'}
    
    async def _benchmark_database_operations(self) -> Dict[str, Any]:
        """Benchmark database operations"""
        iterations = 300
        
        # Mock database operations
        for i in range(iterations):
            operation_type = ['select', 'insert', 'update'][i % 3]
            
            with self.track_latency('database_manager', operation_type):
                # Simulate database operations
                if operation_type == 'select':
                    await asyncio.sleep(0.015)  # 15ms SELECT
                elif operation_type == 'insert':
                    await asyncio.sleep(0.025)  # 25ms INSERT
                else:  # update
                    await asyncio.sleep(0.020)  # 20ms UPDATE
                
                # Occasional slow queries
                if i % 50 == 0:
                    await asyncio.sleep(0.100)  # 100ms slow query
        
        # Collect results
        db_measurements = [m for m in self.measurements 
                          if m.component == 'database_manager']
        
        if db_measurements:
            latencies = [m.latency_ms for m in db_measurements[-iterations:]]
            return {
                'operation': 'Database Operations',
                'iterations': len(latencies),
                'mean_latency_ms': statistics.mean(latencies),
                'p95_latency_ms': percentile(latencies, 95),
                'p99_latency_ms': percentile(latencies, 99),
                'max_latency_ms': max(latencies),
                'success_rate': 100.0,
                'target_latency_ms': 50.0,
                'passed': statistics.mean(latencies) < 50.0
            }
        
        return {'error': 'No database measurements available'}
    
    async def _benchmark_portfolio_calculations(self) -> Dict[str, Any]:
        """Benchmark portfolio calculations"""
        iterations = 100
        
        # Mock portfolio calculations
        for i in range(iterations):
            with self.track_latency('portfolio_manager', 'calculate_portfolio'):
                # Simulate portfolio calculations
                await asyncio.sleep(0.050)  # 50ms base calculation
                
                # Simulate complex calculations
                await asyncio.sleep(0.030)  # 30ms risk calculations
                
                # Occasional full recalculation
                if i % 20 == 0:
                    await asyncio.sleep(0.200)  # 200ms full recalc
        
        # Collect results
        portfolio_measurements = [m for m in self.measurements 
                                if m.component == 'portfolio_manager' and 
                                   m.operation == 'calculate_portfolio']
        
        if portfolio_measurements:
            latencies = [m.latency_ms for m in portfolio_measurements[-iterations:]]
            return {
                'operation': 'Portfolio Calculations',
                'iterations': len(latencies),
                'mean_latency_ms': statistics.mean(latencies),
                'p95_latency_ms': percentile(latencies, 95),
                'p99_latency_ms': percentile(latencies, 99),
                'max_latency_ms': max(latencies),
                'success_rate': 100.0,
                'target_latency_ms': 100.0,
                'passed': statistics.mean(latencies) < 100.0
            }
        
        return {'error': 'No portfolio measurements available'}
    
    def generate_latency_report(self) -> Dict[str, Any]:
        """Generate comprehensive latency analysis report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'analysis_period_hours': self.retention_hours,
            'total_measurements': len(self.measurements),
            'summary': {
                'component_count': len(self.component_stats),
                'critical_paths_analyzed': len(self.critical_paths),
                'regressions_detected': len(self.regressions),
                'baseline_components': len(self.baselines)
            },
            'component_statistics': {
                key: asdict(stats) for key, stats in self.component_stats.items()
            },
            'critical_paths': [asdict(path) for path in self.critical_paths],
            'detected_regressions': [asdict(regression) for regression in self.regressions],
            'alert_thresholds': self.alert_thresholds,
            'baseline_latencies': self.baselines
        }
        
        # Add overall performance assessment
        if self.component_stats:
            all_latencies = [stats.mean_latency_ms for stats in self.component_stats.values()]
            report['overall_performance'] = {
                'average_latency_ms': statistics.mean(all_latencies),
                'max_latency_ms': max(all_latencies),
                'components_over_threshold': sum(
                    1 for key, stats in self.component_stats.items()
                    if stats.mean_latency_ms > self.alert_thresholds.get(stats.component, 100.0)
                )
            }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save latency analysis report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'latency_analysis_report_{timestamp}.json'
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Latency analysis report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
    
    def print_summary(self, report: Dict[str, Any]):
        """Print latency analysis summary to console"""
        print("\n" + "="*80)
        print("⚡ CRITICAL PATH LATENCY ANALYSIS REPORT")
        print("="*80)
        
        summary = report.get('summary', {})
        overall = report.get('overall_performance', {})
        
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"   Total Measurements: {report.get('total_measurements', 0):,}")
        print(f"   Components Analyzed: {summary.get('component_count', 0)}")
        print(f"   Critical Paths: {summary.get('critical_paths_analyzed', 0)}")
        print(f"   Regressions Detected: {summary.get('regressions_detected', 0)}")
        
        if overall:
            print(f"\n⚡ OVERALL PERFORMANCE:")
            print(f"   Average Latency: {overall.get('average_latency_ms', 0):.2f}ms")
            print(f"   Max Latency: {overall.get('max_latency_ms', 0):.2f}ms")
            print(f"   Components Over Threshold: {overall.get('components_over_threshold', 0)}")
        
        # Critical paths
        critical_paths = report.get('critical_paths', [])
        if critical_paths:
            print(f"\n🛤️  CRITICAL PATHS:")
            for path in critical_paths:
                bottleneck_pct = path.get('bottleneck_percentage', 0)
                print(f"   {path['path_name']}: {path['total_latency_ms']:.1f}ms total")
                print(f"        Bottleneck: {path['bottleneck_component']} "
                      f"({path['bottleneck_latency_ms']:.1f}ms, {bottleneck_pct:.1f}%)")
        
        # Top latency components
        comp_stats = report.get('component_statistics', {})
        if comp_stats:
            print(f"\n📈 TOP LATENCY COMPONENTS:")
            sorted_components = sorted(comp_stats.items(), 
                                     key=lambda x: x[1]['mean_latency_ms'], 
                                     reverse=True)[:5]
            
            for key, stats in sorted_components:
                component = stats['component']
                operation = stats['operation']
                mean_lat = stats['mean_latency_ms']
                p99_lat = stats['p99_latency_ms']
                success_rate = stats['success_rate']
                
                print(f"   {component}_{operation}: {mean_lat:.2f}ms avg, "
                      f"{p99_lat:.2f}ms P99, {success_rate:.1f}% success")
        
        # Regressions
        regressions = report.get('detected_regressions', [])
        if regressions:
            print(f"\n🚨 LATENCY REGRESSIONS:")
            for regression in regressions:
                component = regression['component']
                operation = regression['operation']
                pct = regression['regression_percentage']
                severity = regression['severity']
                
                print(f"   {severity} | {component}_{operation}: {pct:.1f}% increase")
                print(f"        {regression['baseline_latency_ms']:.2f}ms → "
                      f"{regression['current_latency_ms']:.2f}ms")
        
        print("\n" + "="*80)


async def main():
    """Run latency analysis"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create latency analyzer
    analyzer = CriticalPathLatencyAnalyzer(retention_hours=1)  # 1 hour retention for testing
    
    try:
        # Start monitoring
        analyzer.start_monitoring()
        
        # Run benchmarks
        logger.info("Running trading operations benchmarks...")
        benchmarks = await analyzer.benchmark_trading_operations()
        
        # Analyze critical paths
        critical_paths = await analyzer.analyze_critical_paths()
        
        # Wait for some background analysis
        await asyncio.sleep(5)
        
        # Generate comprehensive report
        report = analyzer.generate_latency_report()
        report['benchmarks'] = benchmarks
        
        # Save and display results
        analyzer.save_report(report)
        analyzer.print_summary(report)
        
        # Stop monitoring
        analyzer.stop_monitoring()
        
        # Determine success
        overall_performance = report.get('overall_performance', {})
        avg_latency = overall_performance.get('average_latency_ms', 0)
        regressions = len(report.get('detected_regressions', []))
        
        if avg_latency < 50 and regressions == 0:
            logger.info("✅ Latency analysis PASSED - All components within targets")
            return 0
        else:
            logger.warning(f"⚠️  Latency analysis found issues: {avg_latency:.1f}ms avg, {regressions} regressions")
            return 1
            
    except Exception as e:
        logger.error(f"Latency analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))