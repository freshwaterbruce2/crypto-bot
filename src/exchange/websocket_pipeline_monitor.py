"""
WebSocket Pipeline Performance Monitor
=====================================

Advanced monitoring and diagnostics system for the unified WebSocket V2 data pipeline.
Provides real-time performance metrics, bottleneck detection, and health diagnostics.

Features:
- Real-time throughput monitoring
- Latency tracking and analysis
- Memory usage monitoring
- Queue health diagnostics
- Component performance analysis
- Automatic alerts and recommendations
- Historical performance data
- Visual performance dashboard (optional)
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: float
    throughput_msgs_per_sec: float
    avg_latency_ms: float
    max_latency_ms: float
    memory_usage_mb: float
    queue_sizes: dict[str, int] = field(default_factory=dict)
    error_rate_percent: float = 0.0
    drop_rate_percent: float = 0.0
    component_health: dict[str, bool] = field(default_factory=dict)


@dataclass
class AlertConfig:
    """Configuration for performance alerts"""
    max_latency_ms: float = 50.0
    max_memory_mb: float = 500.0
    max_error_rate_percent: float = 5.0
    max_drop_rate_percent: float = 2.0
    min_throughput_msgs_per_sec: float = 1.0
    queue_size_warning_threshold: int = 1500
    queue_size_critical_threshold: int = 1800


class WebSocketPipelineMonitor:
    """
    Advanced monitoring system for WebSocket pipeline performance

    Provides comprehensive monitoring, alerting, and diagnostics for the
    unified WebSocket V2 data pipeline.
    """

    def __init__(self, pipeline, alert_config: Optional[AlertConfig] = None):
        """
        Initialize the pipeline monitor

        Args:
            pipeline: UnifiedWebSocketDataPipeline instance
            alert_config: Alert configuration
        """
        self.pipeline = pipeline
        self.alert_config = alert_config or AlertConfig()

        # Monitoring state
        self._monitoring = False
        self._monitor_task = None
        self._alert_task = None

        # Performance data storage
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 data points
        self.alert_history = deque(maxlen=100)     # Keep last 100 alerts

        # Latency tracking
        self.latency_samples = defaultdict(lambda: deque(maxlen=100))

        # Throughput tracking
        self.message_counts = defaultdict(int)
        self.last_message_counts = defaultdict(int)
        self.throughput_window = 60.0  # 1 minute window

        # Error tracking
        self.error_counts = defaultdict(int)
        self.last_error_counts = defaultdict(int)

        # Component health tracking
        self.component_response_times = defaultdict(lambda: deque(maxlen=50))
        self.component_error_counts = defaultdict(int)

        # System monitoring
        self.process = psutil.Process()

        # Performance insights
        self.performance_insights = []
        self.bottleneck_analysis = {}

        logger.info("[MONITOR] Pipeline performance monitor initialized")

    async def start_monitoring(self, interval_seconds: float = 10.0):
        """Start performance monitoring"""
        if self._monitoring:
            logger.warning("[MONITOR] Already monitoring")
            return

        logger.info(f"[MONITOR] Starting performance monitoring (interval: {interval_seconds}s)")
        self._monitoring = True

        # Start monitoring tasks
        self._monitor_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        self._alert_task = asyncio.create_task(
            self._alert_loop()
        )

    async def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self._monitoring:
            return

        logger.info("[MONITOR] Stopping performance monitoring")
        self._monitoring = False

        # Cancel tasks
        if self._monitor_task:
            self._monitor_task.cancel()
        if self._alert_task:
            self._alert_task.cancel()

        # Wait for tasks to complete
        try:
            if self._monitor_task:
                await self._monitor_task
        except asyncio.CancelledError:
            pass

        try:
            if self._alert_task:
                await self._alert_task
        except asyncio.CancelledError:
            pass

        logger.info("[MONITOR] Performance monitoring stopped")

    async def _monitoring_loop(self, interval_seconds: float):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()

                # Store metrics
                self.metrics_history.append(metrics)

                # Analyze performance
                await self._analyze_performance(metrics)

                # Log summary
                self._log_performance_summary(metrics)

                await asyncio.sleep(interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MONITOR] Error in monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)

    async def _alert_loop(self):
        """Alert monitoring loop"""
        while self._monitoring:
            try:
                await asyncio.sleep(5.0)  # Check alerts every 5 seconds

                if self.metrics_history:
                    latest_metrics = self.metrics_history[-1]
                    await self._check_alerts(latest_metrics)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MONITOR] Error in alert loop: {e}")
                await asyncio.sleep(5.0)

    async def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        current_time = time.time()

        # Get pipeline stats
        pipeline_stats = self.pipeline.get_pipeline_stats()

        # Calculate throughput
        throughput = self._calculate_throughput(pipeline_stats)

        # Calculate latency
        avg_latency, max_latency = self._calculate_latency()

        # Get memory usage
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        # Calculate error and drop rates
        error_rate = self._calculate_error_rate(pipeline_stats)
        drop_rate = self._calculate_drop_rate(pipeline_stats)

        # Get component health
        component_health = await self._assess_component_health()

        return PerformanceMetrics(
            timestamp=current_time,
            throughput_msgs_per_sec=throughput,
            avg_latency_ms=avg_latency,
            max_latency_ms=max_latency,
            memory_usage_mb=memory_mb,
            queue_sizes=pipeline_stats.get('queue_sizes', {}),
            error_rate_percent=error_rate,
            drop_rate_percent=drop_rate,
            component_health=component_health
        )

    def _calculate_throughput(self, pipeline_stats: dict[str, Any]) -> float:
        """Calculate message throughput"""
        try:
            current_total = sum(pipeline_stats.get('messages_processed', {}).values())
            last_total = sum(self.last_message_counts.values())

            messages_processed = current_total - last_total
            throughput = messages_processed / self.throughput_window

            # Update counters
            self.last_message_counts = pipeline_stats.get('messages_processed', {}).copy()

            return max(0.0, throughput)

        except Exception as e:
            logger.error(f"[MONITOR] Error calculating throughput: {e}")
            return 0.0

    def _calculate_latency(self) -> tuple[float, float]:
        """Calculate average and maximum latency"""
        try:
            all_latencies = []
            for channel_latencies in self.latency_samples.values():
                all_latencies.extend(channel_latencies)

            if not all_latencies:
                return 0.0, 0.0

            avg_latency = statistics.mean(all_latencies) * 1000  # Convert to ms
            max_latency = max(all_latencies) * 1000

            return avg_latency, max_latency

        except Exception as e:
            logger.error(f"[MONITOR] Error calculating latency: {e}")
            return 0.0, 0.0

    def _calculate_error_rate(self, pipeline_stats: dict[str, Any]) -> float:
        """Calculate error rate percentage"""
        try:
            total_processed = sum(pipeline_stats.get('messages_processed', {}).values())
            total_errors = sum(pipeline_stats.get('errors', {}).values())

            if total_processed == 0:
                return 0.0

            return (total_errors / total_processed) * 100

        except Exception as e:
            logger.error(f"[MONITOR] Error calculating error rate: {e}")
            return 0.0

    def _calculate_drop_rate(self, pipeline_stats: dict[str, Any]) -> float:
        """Calculate message drop rate percentage"""
        try:
            total_processed = sum(pipeline_stats.get('messages_processed', {}).values())
            total_dropped = sum(pipeline_stats.get('messages_dropped', {}).values())

            total_messages = total_processed + total_dropped
            if total_messages == 0:
                return 0.0

            return (total_dropped / total_messages) * 100

        except Exception as e:
            logger.error(f"[MONITOR] Error calculating drop rate: {e}")
            return 0.0

    async def _assess_component_health(self) -> dict[str, bool]:
        """Assess health of registered components"""
        try:
            component_health = {}

            # Check if components are responding
            if hasattr(self.pipeline, 'registry'):
                for name, ref in self.pipeline.registry._components.items():
                    component = ref()
                    component_health[name] = component is not None

            return component_health

        except Exception as e:
            logger.error(f"[MONITOR] Error assessing component health: {e}")
            return {}

    async def _analyze_performance(self, metrics: PerformanceMetrics):
        """Analyze performance and generate insights"""
        try:
            insights = []

            # Analyze throughput
            if metrics.throughput_msgs_per_sec < self.alert_config.min_throughput_msgs_per_sec:
                insights.append(
                    f"Low throughput: {metrics.throughput_msgs_per_sec:.1f} msg/s "
                    f"(expected >{self.alert_config.min_throughput_msgs_per_sec})"
                )

            # Analyze latency
            if metrics.avg_latency_ms > self.alert_config.max_latency_ms:
                insights.append(
                    f"High latency: {metrics.avg_latency_ms:.2f}ms average "
                    f"(threshold: {self.alert_config.max_latency_ms}ms)"
                )

            # Analyze memory usage
            if metrics.memory_usage_mb > self.alert_config.max_memory_mb:
                insights.append(
                    f"High memory usage: {metrics.memory_usage_mb:.1f}MB "
                    f"(threshold: {self.alert_config.max_memory_mb}MB)"
                )

            # Analyze queue sizes
            for queue_name, size in metrics.queue_sizes.items():
                if size > self.alert_config.queue_size_critical_threshold:
                    insights.append(
                        f"Critical queue size: {queue_name} has {size} messages "
                        f"(critical: {self.alert_config.queue_size_critical_threshold})"
                    )
                elif size > self.alert_config.queue_size_warning_threshold:
                    insights.append(
                        f"Warning queue size: {queue_name} has {size} messages "
                        f"(warning: {self.alert_config.queue_size_warning_threshold})"
                    )

            # Analyze error and drop rates
            if metrics.error_rate_percent > self.alert_config.max_error_rate_percent:
                insights.append(
                    f"High error rate: {metrics.error_rate_percent:.1f}% "
                    f"(threshold: {self.alert_config.max_error_rate_percent}%)"
                )

            if metrics.drop_rate_percent > self.alert_config.max_drop_rate_percent:
                insights.append(
                    f"High drop rate: {metrics.drop_rate_percent:.1f}% "
                    f"(threshold: {self.alert_config.max_drop_rate_percent}%)"
                )

            # Update insights
            self.performance_insights = insights

            # Perform bottleneck analysis
            await self._analyze_bottlenecks(metrics)

        except Exception as e:
            logger.error(f"[MONITOR] Error analyzing performance: {e}")

    async def _analyze_bottlenecks(self, metrics: PerformanceMetrics):
        """Analyze potential bottlenecks"""
        try:
            bottlenecks = {}

            # Queue bottlenecks
            max_queue_size = max(metrics.queue_sizes.values()) if metrics.queue_sizes else 0
            if max_queue_size > self.alert_config.queue_size_warning_threshold:
                bottleneck_queue = max(metrics.queue_sizes, key=metrics.queue_sizes.get)
                bottlenecks['queue'] = {
                    'type': 'queue_bottleneck',
                    'queue': bottleneck_queue,
                    'size': max_queue_size,
                    'recommendation': 'Consider increasing processor count for this priority level'
                }

            # Memory bottlenecks
            if metrics.memory_usage_mb > self.alert_config.max_memory_mb * 0.8:
                bottlenecks['memory'] = {
                    'type': 'memory_pressure',
                    'usage_mb': metrics.memory_usage_mb,
                    'recommendation': 'Consider reducing buffer sizes or implementing message batching'
                }

            # Latency bottlenecks
            if metrics.avg_latency_ms > self.alert_config.max_latency_ms * 0.7:
                bottlenecks['latency'] = {
                    'type': 'processing_latency',
                    'avg_latency_ms': metrics.avg_latency_ms,
                    'recommendation': 'Check component processing times and consider parallelization'
                }

            self.bottleneck_analysis = bottlenecks

        except Exception as e:
            logger.error(f"[MONITOR] Error analyzing bottlenecks: {e}")

    async def _check_alerts(self, metrics: PerformanceMetrics):
        """Check for alert conditions"""
        try:
            alerts = []

            # Critical alerts
            if metrics.error_rate_percent > self.alert_config.max_error_rate_percent:
                alerts.append({
                    'level': 'CRITICAL',
                    'type': 'high_error_rate',
                    'message': f"Error rate {metrics.error_rate_percent:.1f}% exceeds threshold",
                    'timestamp': metrics.timestamp
                })

            if metrics.memory_usage_mb > self.alert_config.max_memory_mb:
                alerts.append({
                    'level': 'CRITICAL',
                    'type': 'high_memory_usage',
                    'message': f"Memory usage {metrics.memory_usage_mb:.1f}MB exceeds threshold",
                    'timestamp': metrics.timestamp
                })

            # Warning alerts
            if metrics.avg_latency_ms > self.alert_config.max_latency_ms:
                alerts.append({
                    'level': 'WARNING',
                    'type': 'high_latency',
                    'message': f"Average latency {metrics.avg_latency_ms:.2f}ms exceeds threshold",
                    'timestamp': metrics.timestamp
                })

            # Log and store alerts
            for alert in alerts:
                logger.warning(f"[MONITOR] {alert['level']}: {alert['message']}")
                self.alert_history.append(alert)

        except Exception as e:
            logger.error(f"[MONITOR] Error checking alerts: {e}")

    def _log_performance_summary(self, metrics: PerformanceMetrics):
        """Log performance summary"""
        try:
            # Calculate trends if we have history
            trend_info = ""
            if len(self.metrics_history) > 1:
                prev_metrics = self.metrics_history[-2]
                throughput_trend = metrics.throughput_msgs_per_sec - prev_metrics.throughput_msgs_per_sec
                latency_trend = metrics.avg_latency_ms - prev_metrics.avg_latency_ms

                trend_info = f" (Δ throughput: {throughput_trend:+.1f}, Δ latency: {latency_trend:+.1f}ms)"

            logger.info(
                f"[MONITOR] Performance: {metrics.throughput_msgs_per_sec:.1f} msg/s, "
                f"{metrics.avg_latency_ms:.2f}ms avg latency, "
                f"{metrics.memory_usage_mb:.1f}MB memory, "
                f"{metrics.error_rate_percent:.1f}% errors, "
                f"{metrics.drop_rate_percent:.1f}% drops{trend_info}"
            )

            # Log insights if any
            if self.performance_insights:
                logger.warning(f"[MONITOR] Performance insights: {'; '.join(self.performance_insights)}")

        except Exception as e:
            logger.error(f"[MONITOR] Error logging performance summary: {e}")

    def get_performance_report(self) -> dict[str, Any]:
        """Get comprehensive performance report"""
        if not self.metrics_history:
            return {'status': 'no_data', 'message': 'No performance data available'}

        latest_metrics = self.metrics_history[-1]

        # Calculate statistics from history
        if len(self.metrics_history) > 1:
            throughputs = [m.throughput_msgs_per_sec for m in self.metrics_history]
            latencies = [m.avg_latency_ms for m in self.metrics_history]
            memory_usages = [m.memory_usage_mb for m in self.metrics_history]

            stats = {
                'throughput': {
                    'current': latest_metrics.throughput_msgs_per_sec,
                    'avg': statistics.mean(throughputs),
                    'min': min(throughputs),
                    'max': max(throughputs)
                },
                'latency': {
                    'current': latest_metrics.avg_latency_ms,
                    'avg': statistics.mean(latencies),
                    'min': min(latencies),
                    'max': max(latencies)
                },
                'memory': {
                    'current': latest_metrics.memory_usage_mb,
                    'avg': statistics.mean(memory_usages),
                    'min': min(memory_usages),
                    'max': max(memory_usages)
                }
            }
        else:
            stats = {
                'throughput': {'current': latest_metrics.throughput_msgs_per_sec},
                'latency': {'current': latest_metrics.avg_latency_ms},
                'memory': {'current': latest_metrics.memory_usage_mb}
            }

        return {
            'status': 'active',
            'timestamp': latest_metrics.timestamp,
            'current_metrics': {
                'throughput_msgs_per_sec': latest_metrics.throughput_msgs_per_sec,
                'avg_latency_ms': latest_metrics.avg_latency_ms,
                'max_latency_ms': latest_metrics.max_latency_ms,
                'memory_usage_mb': latest_metrics.memory_usage_mb,
                'error_rate_percent': latest_metrics.error_rate_percent,
                'drop_rate_percent': latest_metrics.drop_rate_percent,
                'queue_sizes': latest_metrics.queue_sizes,
                'component_health': latest_metrics.component_health
            },
            'statistics': stats,
            'insights': self.performance_insights,
            'bottlenecks': self.bottleneck_analysis,
            'recent_alerts': list(self.alert_history)[-10:],  # Last 10 alerts
            'monitoring_duration': time.time() - self.metrics_history[0].timestamp if self.metrics_history else 0
        }

    def export_performance_data(self, filepath: str, format: str = 'json') -> bool:
        """Export performance data to file"""
        try:
            report = self.get_performance_report()

            if format.lower() == 'json':
                with open(filepath, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
            else:
                logger.error(f"[MONITOR] Unsupported export format: {format}")
                return False

            logger.info(f"[MONITOR] Performance data exported to {filepath}")
            return True

        except Exception as e:
            logger.error(f"[MONITOR] Error exporting performance data: {e}")
            return False

    def record_component_latency(self, component_name: str, latency_seconds: float):
        """Record latency for a specific component"""
        self.component_response_times[component_name].append(latency_seconds)

    def record_processing_latency(self, channel: str, latency_seconds: float):
        """Record processing latency for a channel"""
        self.latency_samples[channel].append(latency_seconds)
