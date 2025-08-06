"""
Enhanced performance monitoring system for the crypto trading bot.
"""

import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import psutil

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to monitor."""
    PERFORMANCE = "performance"
    TRADING = "trading"
    SYSTEM = "system"
    RISK = "risk"
    CUSTOM = "custom"


@dataclass
class PerformanceMetric:
    """Performance metric data point."""
    name: str
    value: float
    timestamp: datetime
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Performance alert."""
    level: AlertLevel
    message: str
    metric_name: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: float
    network_recv: float
    process_count: int
    thread_count: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TradingMetrics:
    """Trading performance metrics."""
    total_trades: int
    successful_trades: int
    failed_trades: int
    win_rate: float
    total_pnl: float
    avg_trade_duration: float
    max_drawdown: float
    sharpe_ratio: float
    timestamp: datetime = field(default_factory=datetime.now)


class EnhancedPerformanceMonitor:
    """
    Enhanced performance monitoring system with real-time metrics collection,
    alerting, and comprehensive analysis capabilities.
    """

    def __init__(self,
                 collection_interval: int = 60,
                 max_history_size: int = 10000,
                 enable_system_monitoring: bool = True,
                 enable_alerts: bool = True):
        """
        Initialize the enhanced performance monitor.
        
        Args:
            collection_interval: Interval in seconds for metric collection
            max_history_size: Maximum number of data points to store
            enable_system_monitoring: Whether to collect system metrics
            enable_alerts: Whether to enable alerting
        """
        self.collection_interval = collection_interval
        self.max_history_size = max_history_size
        self.enable_system_monitoring = enable_system_monitoring
        self.enable_alerts = enable_alerts

        # Metric storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self.system_metrics: deque = deque(maxlen=max_history_size)
        self.trading_metrics: deque = deque(maxlen=max_history_size)

        # Alert system
        self.alerts: List[Alert] = []
        self.alert_thresholds: Dict[str, Dict[str, float]] = {}
        self.alert_callbacks: Dict[str, Callable] = {}

        # Performance tracking
        self.execution_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)

        # Threading for continuous monitoring
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        self.lock = threading.Lock()

        # Benchmarks and baselines
        self.benchmarks: Dict[str, float] = {}
        self.baseline_metrics: Dict[str, float] = {}

        # Custom metric handlers
        self.custom_metric_handlers: Dict[str, Callable] = {}

        logger.info("EnhancedPerformanceMonitor initialized")

    def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop continuous performance monitoring."""
        self.monitoring_active = False

        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                if self.enable_system_monitoring:
                    self._collect_system_metrics()

                # Collect custom metrics
                self._collect_custom_metrics()

                # Check alerts
                if self.enable_alerts:
                    self._check_alerts()

                # Sleep until next collection
                time.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.collection_interval)

    def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        try:
            # CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Network statistics
            network = psutil.net_io_counters()

            # Process information
            process = psutil.Process()
            process_count = len(psutil.pids())
            thread_count = process.num_threads()

            # Create system metrics object
            sys_metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                network_sent=network.bytes_sent,
                network_recv=network.bytes_recv,
                process_count=process_count,
                thread_count=thread_count
            )

            # Store metrics
            with self.lock:
                self.system_metrics.append(sys_metrics)

                # Also store individual metrics for alerting
                self.record_metric("system.cpu_percent", cpu_percent, MetricType.SYSTEM)
                self.record_metric("system.memory_percent", memory.percent, MetricType.SYSTEM)
                self.record_metric("system.disk_percent", disk.percent, MetricType.SYSTEM)
                self.record_metric("system.thread_count", thread_count, MetricType.SYSTEM)

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    def _collect_custom_metrics(self) -> None:
        """Collect custom metrics using registered handlers."""
        for metric_name, handler in self.custom_metric_handlers.items():
            try:
                value = handler()
                if value is not None:
                    self.record_metric(metric_name, value, MetricType.CUSTOM)
            except Exception as e:
                logger.error(f"Error collecting custom metric {metric_name}: {e}")

    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.CUSTOM,
                     tags: Optional[Dict[str, str]] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags for the metric
            metadata: Optional metadata
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            metric_type=metric_type,
            tags=tags or {},
            metadata=metadata or {}
        )

        with self.lock:
            self.metrics[name].append(metric)

        logger.debug(f"Recorded metric: {name} = {value}")

    def time_function(self, func_name: str):
        """
        Decorator to time function execution.
        
        Args:
            func_name: Name of the function for tracking
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    self.call_counts[func_name] += 1
                    return result
                except Exception:
                    self.error_counts[func_name] += 1
                    raise
                finally:
                    execution_time = time.time() - start_time
                    self.execution_times[func_name].append(execution_time)
                    self.record_metric(f"execution_time.{func_name}", execution_time, MetricType.PERFORMANCE)
            return wrapper
        return decorator

    def set_alert_threshold(self, metric_name: str, warning_threshold: float,
                          critical_threshold: float, comparison: str = "greater") -> None:
        """
        Set alert thresholds for a metric.
        
        Args:
            metric_name: Name of the metric
            warning_threshold: Warning threshold value
            critical_threshold: Critical threshold value
            comparison: Comparison operator ('greater', 'less', 'equal')
        """
        self.alert_thresholds[metric_name] = {
            'warning': warning_threshold,
            'critical': critical_threshold,
            'comparison': comparison
        }

        logger.info(f"Set alert thresholds for {metric_name}: warning={warning_threshold}, critical={critical_threshold}")

    def add_alert_callback(self, alert_level: AlertLevel, callback: Callable[[Alert], None]) -> None:
        """
        Add callback function for alerts.
        
        Args:
            alert_level: Alert level to trigger callback
            callback: Callback function to execute
        """
        self.alert_callbacks[alert_level.value] = callback
        logger.info(f"Added alert callback for {alert_level.value} level")

    def _check_alerts(self) -> None:
        """Check metrics against alert thresholds."""
        for metric_name, thresholds in self.alert_thresholds.items():
            if metric_name not in self.metrics or not self.metrics[metric_name]:
                continue

            # Get latest metric value
            latest_metric = self.metrics[metric_name][-1]
            value = latest_metric.value

            # Check thresholds
            comparison = thresholds.get('comparison', 'greater')
            warning_threshold = thresholds['warning']
            critical_threshold = thresholds['critical']

            alert_level = None
            threshold_value = None

            if comparison == 'greater':
                if value >= critical_threshold:
                    alert_level = AlertLevel.CRITICAL
                    threshold_value = critical_threshold
                elif value >= warning_threshold:
                    alert_level = AlertLevel.WARNING
                    threshold_value = warning_threshold
            elif comparison == 'less':
                if value <= critical_threshold:
                    alert_level = AlertLevel.CRITICAL
                    threshold_value = critical_threshold
                elif value <= warning_threshold:
                    alert_level = AlertLevel.WARNING
                    threshold_value = warning_threshold

            # Create alert if threshold exceeded
            if alert_level:
                alert = Alert(
                    level=alert_level,
                    message=f"Metric {metric_name} {comparison} threshold: {value:.2f} {comparison} {threshold_value:.2f}",
                    metric_name=metric_name,
                    value=value,
                    threshold=threshold_value
                )

                self.alerts.append(alert)

                # Execute callback if registered
                if alert_level.value in self.alert_callbacks:
                    try:
                        self.alert_callbacks[alert_level.value](alert)
                    except Exception as e:
                        logger.error(f"Error executing alert callback: {e}")

                logger.warning(f"Alert triggered: {alert.message}")

    def get_metric_statistics(self, metric_name: str, window_minutes: int = 60) -> Dict[str, float]:
        """
        Get statistical summary of a metric over a time window.
        
        Args:
            metric_name: Name of the metric
            window_minutes: Time window in minutes
            
        Returns:
            Dictionary with statistical measures
        """
        if metric_name not in self.metrics:
            return {}

        # Filter metrics within time window
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_metrics = [
            m for m in self.metrics[metric_name]
            if m.timestamp >= cutoff_time
        ]

        if not recent_metrics:
            return {}

        values = [m.value for m in recent_metrics]

        return {
            'count': len(values),
            'mean': np.mean(values),
            'median': np.median(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'p95': np.percentile(values, 95),
            'p99': np.percentile(values, 99),
            'current': values[-1] if values else 0.0
        }

    def get_function_performance(self, func_name: str) -> Dict[str, Any]:
        """
        Get performance statistics for a function.
        
        Args:
            func_name: Name of the function
            
        Returns:
            Dictionary with performance statistics
        """
        if func_name not in self.execution_times:
            return {}

        times = list(self.execution_times[func_name])
        if not times:
            return {}

        return {
            'total_calls': self.call_counts[func_name],
            'total_errors': self.error_counts[func_name],
            'error_rate': self.error_counts[func_name] / max(self.call_counts[func_name], 1),
            'avg_execution_time': np.mean(times),
            'median_execution_time': np.median(times),
            'min_execution_time': np.min(times),
            'max_execution_time': np.max(times),
            'p95_execution_time': np.percentile(times, 95),
            'p99_execution_time': np.percentile(times, 99),
            'total_time': np.sum(times)
        }

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health summary.
        
        Returns:
            Dictionary with system health metrics
        """
        if not self.system_metrics:
            return {}

        latest_metrics = self.system_metrics[-1]

        # Calculate averages over last hour
        recent_metrics = [
            m for m in self.system_metrics
            if m.timestamp >= datetime.now() - timedelta(hours=1)
        ]

        if recent_metrics:
            avg_cpu = np.mean([m.cpu_percent for m in recent_metrics])
            avg_memory = np.mean([m.memory_percent for m in recent_metrics])
            avg_disk = np.mean([m.disk_percent for m in recent_metrics])
        else:
            avg_cpu = avg_memory = avg_disk = 0.0

        # Determine health status
        health_score = 100.0
        health_issues = []

        if avg_cpu > 80:
            health_score -= 20
            health_issues.append("High CPU usage")

        if avg_memory > 80:
            health_score -= 20
            health_issues.append("High memory usage")

        if avg_disk > 90:
            health_score -= 30
            health_issues.append("High disk usage")

        if len(self.alerts) > 10:
            health_score -= 15
            health_issues.append("Multiple active alerts")

        health_status = "excellent" if health_score >= 90 else \
                       "good" if health_score >= 70 else \
                       "fair" if health_score >= 50 else "poor"

        return {
            'health_score': max(0, health_score),
            'health_status': health_status,
            'health_issues': health_issues,
            'current_metrics': {
                'cpu_percent': latest_metrics.cpu_percent,
                'memory_percent': latest_metrics.memory_percent,
                'disk_percent': latest_metrics.disk_percent,
                'thread_count': latest_metrics.thread_count
            },
            'average_metrics': {
                'cpu_percent': avg_cpu,
                'memory_percent': avg_memory,
                'disk_percent': avg_disk
            },
            'active_alerts': len([a for a in self.alerts if not a.resolved])
        }

    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Args:
            hours: Number of hours to include in report
            
        Returns:
            Dictionary with performance report
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # System metrics summary
        system_health = self.get_system_health()

        # Function performance summary
        function_performance = {}
        for func_name in self.execution_times.keys():
            function_performance[func_name] = self.get_function_performance(func_name)

        # Metric statistics
        metric_stats = {}
        for metric_name in self.metrics.keys():
            metric_stats[metric_name] = self.get_metric_statistics(metric_name, hours * 60)

        # Alert summary
        recent_alerts = [a for a in self.alerts if a.timestamp >= cutoff_time]
        alert_summary = {
            'total_alerts': len(recent_alerts),
            'by_level': {
                level.value: len([a for a in recent_alerts if a.level == level])
                for level in AlertLevel
            },
            'active_alerts': len([a for a in recent_alerts if not a.resolved])
        }

        return {
            'report_period': f"{hours} hours",
            'generated_at': datetime.now().isoformat(),
            'system_health': system_health,
            'function_performance': function_performance,
            'metric_statistics': metric_stats,
            'alert_summary': alert_summary,
            'monitoring_active': self.monitoring_active,
            'total_metrics_collected': sum(len(deque_obj) for deque_obj in self.metrics.values())
        }

    def register_custom_metric_handler(self, metric_name: str, handler: Callable[[], float]) -> None:
        """
        Register a custom metric collection handler.
        
        Args:
            metric_name: Name of the metric
            handler: Function that returns the metric value
        """
        self.custom_metric_handlers[metric_name] = handler
        logger.info(f"Registered custom metric handler: {metric_name}")

    def set_benchmark(self, metric_name: str, benchmark_value: float) -> None:
        """
        Set a benchmark value for a metric.
        
        Args:
            metric_name: Name of the metric
            benchmark_value: Benchmark value to compare against
        """
        self.benchmarks[metric_name] = benchmark_value
        logger.info(f"Set benchmark for {metric_name}: {benchmark_value}")

    def get_benchmark_comparison(self, metric_name: str) -> Dict[str, Any]:
        """
        Compare current metric performance against benchmark.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Dictionary with benchmark comparison
        """
        if metric_name not in self.benchmarks or metric_name not in self.metrics:
            return {}

        benchmark = self.benchmarks[metric_name]
        current_stats = self.get_metric_statistics(metric_name, 60)

        if not current_stats:
            return {}

        current_value = current_stats['current']
        performance_ratio = current_value / benchmark if benchmark != 0 else float('inf')

        return {
            'benchmark_value': benchmark,
            'current_value': current_value,
            'performance_ratio': performance_ratio,
            'performance_delta': current_value - benchmark,
            'performance_percent': ((current_value - benchmark) / benchmark * 100) if benchmark != 0 else 0.0,
            'meets_benchmark': current_value >= benchmark
        }

    def export_metrics(self, filepath: str, format: str = "json") -> None:
        """
        Export metrics to file.
        
        Args:
            filepath: Path to export file
            format: Export format ('json', 'csv')
        """
        try:
            if format == "json":
                data = {
                    'exported_at': datetime.now().isoformat(),
                    'metrics': {
                        name: [
                            {
                                'name': m.name,
                                'value': m.value,
                                'timestamp': m.timestamp.isoformat(),
                                'metric_type': m.metric_type.value,
                                'tags': m.tags,
                                'metadata': m.metadata
                            }
                            for m in metric_list
                        ]
                        for name, metric_list in self.metrics.items()
                    },
                    'system_metrics': [
                        {
                            'cpu_percent': m.cpu_percent,
                            'memory_percent': m.memory_percent,
                            'disk_percent': m.disk_percent,
                            'network_sent': m.network_sent,
                            'network_recv': m.network_recv,
                            'process_count': m.process_count,
                            'thread_count': m.thread_count,
                            'timestamp': m.timestamp.isoformat()
                        }
                        for m in self.system_metrics
                    ]
                }

                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)

            logger.info(f"Metrics exported to {filepath}")

        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        with self.lock:
            self.metrics.clear()
            self.system_metrics.clear()
            self.trading_metrics.clear()
            self.alerts.clear()
            self.execution_times.clear()
            self.call_counts.clear()
            self.error_counts.clear()

        logger.info("All metrics reset")

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop_monitoring()
