"""
Production Monitor - Comprehensive Real-time Monitoring System
============================================================

Advanced production monitoring system for the crypto trading bot with:
- Real-time metric collection and analysis
- Health check system with 5-minute intervals
- Alert system with configurable thresholds
- Performance tracking and historical storage
- Web dashboard integration
- Emergency shutdown triggers

Features:
- Monitor trades_executed, success_rate, total_pnl
- Track nonce_failures, websocket_reconnects, api_errors
- Monitor log_rotation_count, memory usage
- Track balance_manager health, websocket status
- Automated health checks every 5 minutes
- Alert notifications for threshold breaches
"""

import asyncio
import json
import logging
import time
import traceback
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiofiles
import psutil

logger = logging.getLogger(__name__)


@dataclass
class MetricThresholds:
    """Configurable alert thresholds for production metrics"""
    memory_usage_mb: float = 500.0           # Alert if >500MB
    log_file_size_mb: float = 8.0            # Alert if >8MB
    nonce_generation_rate: float = 1000.0    # Alert if <1000/sec
    websocket_reconnects_per_hour: int = 5    # Alert if >5/hour
    api_error_rate_percent: float = 0.1       # Alert if >0.1%
    trading_success_rate_percent: float = 85.0  # Alert if <85%
    daily_pnl_loss_limit: float = -50.0      # Alert if daily P&L < -$50
    balance_manager_response_time: float = 2.0  # Alert if >2 seconds
    websocket_latency_ms: float = 1000.0      # Alert if >1000ms
    trade_execution_time_ms: float = 5000.0   # Alert if >5 seconds


@dataclass
class ProductionMetrics:
    """Current production metrics snapshot"""
    timestamp: float

    # Trading metrics
    trades_executed: int = 0
    trades_successful: int = 0
    trades_failed: int = 0
    success_rate: float = 0.0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0

    # System health metrics
    nonce_failures: int = 0
    nonce_generation_rate: float = 0.0
    websocket_reconnects: int = 0
    websocket_latency_ms: float = 0.0
    api_errors: int = 0
    api_error_rate: float = 0.0

    # Resource metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    log_file_size_mb: float = 0.0
    log_rotation_count: int = 0

    # Component health
    balance_manager_health: str = "unknown"
    balance_manager_response_time: float = 0.0
    websocket_status: str = "unknown"
    websocket_connection_count: int = 0

    # Performance metrics
    trade_execution_time_ms: float = 0.0
    balance_check_time_ms: float = 0.0
    order_processing_time_ms: float = 0.0


@dataclass
class AlertConfig:
    """Alert configuration and notification settings"""
    enabled: bool = True
    email_notifications: bool = False
    webhook_notifications: bool = False
    console_alerts: bool = True
    log_alerts: bool = True

    # Notification endpoints
    webhook_url: Optional[str] = None
    email_smtp_server: Optional[str] = None
    email_recipients: List[str] = None


class MetricCollector:
    """Collects metrics from various bot components"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.trading_data_path = project_root / "D:" / "trading_data"
        self.logs_path = self.trading_data_path / "logs"
        self.learning_path = self.trading_data_path / "learning"

        # Metric history for trend analysis
        self.metric_history: deque = deque(maxlen=1440)  # 24 hours of 1-minute samples

        # Component references (set by bot integration)
        self.balance_manager = None
        self.websocket_manager = None
        self.exchange_client = None
        self.nonce_manager = None

    async def collect_trading_metrics(self) -> Dict[str, Any]:
        """Collect trading performance metrics"""
        metrics = {
            'trades_executed': 0,
            'trades_successful': 0,
            'trades_failed': 0,
            'success_rate': 0.0,
            'total_pnl': 0.0,
            'daily_pnl': 0.0
        }

        try:
            # Read trading data from logs and files
            today = datetime.now().strftime("%Y%m%d")
            log_file = self.logs_path / f"bot_{today}.log"

            if log_file.exists():
                trades_today = await self._parse_trades_from_log(log_file)
                metrics['trades_executed'] = len(trades_today)
                metrics['trades_successful'] = sum(1 for t in trades_today if t.get('status') == 'success')
                metrics['trades_failed'] = metrics['trades_executed'] - metrics['trades_successful']

                if metrics['trades_executed'] > 0:
                    metrics['success_rate'] = (metrics['trades_successful'] / metrics['trades_executed']) * 100

                # Calculate P&L
                metrics['daily_pnl'] = sum(t.get('pnl', 0) for t in trades_today)

            # Read total P&L from insights file
            insights_file = self.learning_path / "autonomous_insights.json"
            if insights_file.exists():
                async with aiofiles.open(insights_file) as f:
                    insights = json.loads(await f.read())
                    metrics['total_pnl'] = insights.get('total_pnl', 0.0)

        except Exception as e:
            logger.error(f"Error collecting trading metrics: {e}")

        return metrics

    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system health and resource metrics"""
        metrics = {
            'memory_usage_mb': 0.0,
            'cpu_usage_percent': 0.0,
            'log_file_size_mb': 0.0,
            'log_rotation_count': 0,
            'nonce_failures': 0,
            'nonce_generation_rate': 0.0,
            'websocket_reconnects': 0,
            'websocket_latency_ms': 0.0,
            'api_errors': 0,
            'api_error_rate': 0.0
        }

        try:
            # Memory and CPU usage
            process = psutil.Process()
            metrics['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024
            metrics['cpu_usage_percent'] = process.cpu_percent()

            # Log file metrics
            log_files = list(self.logs_path.glob("*.log"))
            if log_files:
                total_size = sum(f.stat().st_size for f in log_files)
                metrics['log_file_size_mb'] = total_size / 1024 / 1024
                metrics['log_rotation_count'] = len(log_files)

            # Nonce manager metrics
            if self.nonce_manager:
                nonce_stats = getattr(self.nonce_manager, 'get_statistics', lambda: {})()
                metrics['nonce_failures'] = nonce_stats.get('failures', 0)
                metrics['nonce_generation_rate'] = nonce_stats.get('generation_rate', 0.0)

            # WebSocket metrics
            if self.websocket_manager:
                ws_stats = getattr(self.websocket_manager, 'get_connection_stats', lambda: {})()
                metrics['websocket_reconnects'] = ws_stats.get('reconnect_count', 0)
                metrics['websocket_latency_ms'] = ws_stats.get('latency_ms', 0.0)

            # API error metrics from recent logs
            today_errors = await self._count_api_errors_today()
            metrics['api_errors'] = today_errors

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

        return metrics

    async def collect_component_health(self) -> Dict[str, Any]:
        """Collect health status of critical components"""
        health = {
            'balance_manager_health': 'unknown',
            'balance_manager_response_time': 0.0,
            'websocket_status': 'unknown',
            'websocket_connection_count': 0,
            'trade_execution_time_ms': 0.0,
            'balance_check_time_ms': 0.0,
            'order_processing_time_ms': 0.0
        }

        try:
            # Balance manager health check
            if self.balance_manager:
                start_time = time.time()
                try:
                    # Perform a quick balance check
                    await self._test_balance_manager()
                    health['balance_manager_health'] = 'healthy'
                    health['balance_manager_response_time'] = (time.time() - start_time) * 1000
                except Exception as e:
                    health['balance_manager_health'] = f'error: {str(e)[:50]}'
                    health['balance_manager_response_time'] = (time.time() - start_time) * 1000

            # WebSocket status
            if self.websocket_manager:
                ws_status = getattr(self.websocket_manager, 'is_connected', lambda: False)()
                health['websocket_status'] = 'connected' if ws_status else 'disconnected'
                health['websocket_connection_count'] = getattr(self.websocket_manager, 'connection_count', 0)

        except Exception as e:
            logger.error(f"Error collecting component health: {e}")

        return health

    async def _parse_trades_from_log(self, log_file: Path) -> List[Dict]:
        """Parse trading data from log files"""
        trades = []
        try:
            async with aiofiles.open(log_file) as f:
                content = await f.read()
                # Simple parsing logic - would need to match your log format
                for line in content.split('\n'):
                    if 'TRADE_EXECUTED' in line or 'Order filled' in line:
                        # Parse trade information from log line
                        trade = {'status': 'success', 'pnl': 0.0}  # Simplified
                        trades.append(trade)
        except Exception as e:
            logger.error(f"Error parsing trades from log: {e}")
        return trades

    async def _count_api_errors_today(self) -> int:
        """Count API errors from today's logs"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            log_file = self.logs_path / f"bot_{today}.log"

            if not log_file.exists():
                return 0

            error_count = 0
            async with aiofiles.open(log_file) as f:
                content = await f.read()
                for line in content.split('\n'):
                    if any(keyword in line.lower() for keyword in ['error', 'exception', 'failed', 'timeout']):
                        if any(api_keyword in line.lower() for api_keyword in ['api', 'request', 'response', 'http']):
                            error_count += 1

            return error_count
        except Exception:
            return 0

    async def _test_balance_manager(self):
        """Quick health test for balance manager"""
        if hasattr(self.balance_manager, 'get_balance'):
            await self.balance_manager.get_balance('USDT')
        elif hasattr(self.balance_manager, 'get_balances'):
            await self.balance_manager.get_balances()


class AlertManager:
    """Manages alerts and notifications for threshold breaches"""

    def __init__(self, config: AlertConfig, thresholds: MetricThresholds):
        self.config = config
        self.thresholds = thresholds
        self.alert_history = deque(maxlen=1000)
        self.alert_cooldowns = {}  # Prevent spam alerts

    async def check_thresholds(self, metrics: ProductionMetrics) -> List[Dict[str, Any]]:
        """Check all metrics against thresholds and generate alerts"""
        alerts = []

        if not self.config.enabled:
            return alerts

        # Memory usage alert
        if metrics.memory_usage_mb > self.thresholds.memory_usage_mb:
            alerts.append(self._create_alert(
                'memory_usage',
                f'High memory usage: {metrics.memory_usage_mb:.1f}MB > {self.thresholds.memory_usage_mb}MB',
                'warning',
                metrics.memory_usage_mb
            ))

        # Log file size alert
        if metrics.log_file_size_mb > self.thresholds.log_file_size_mb:
            alerts.append(self._create_alert(
                'log_file_size',
                f'Large log files: {metrics.log_file_size_mb:.1f}MB > {self.thresholds.log_file_size_mb}MB',
                'warning',
                metrics.log_file_size_mb
            ))

        # Nonce generation rate alert
        if metrics.nonce_generation_rate > 0 and metrics.nonce_generation_rate < self.thresholds.nonce_generation_rate:
            alerts.append(self._create_alert(
                'nonce_generation_rate',
                f'Low nonce generation rate: {metrics.nonce_generation_rate:.0f}/sec < {self.thresholds.nonce_generation_rate}/sec',
                'critical',
                metrics.nonce_generation_rate
            ))

        # WebSocket reconnects alert
        if metrics.websocket_reconnects > self.thresholds.websocket_reconnects_per_hour:
            alerts.append(self._create_alert(
                'websocket_reconnects',
                f'High WebSocket reconnects: {metrics.websocket_reconnects} > {self.thresholds.websocket_reconnects_per_hour}/hour',
                'warning',
                metrics.websocket_reconnects
            ))

        # API error rate alert
        if metrics.api_error_rate > self.thresholds.api_error_rate_percent:
            alerts.append(self._create_alert(
                'api_error_rate',
                f'High API error rate: {metrics.api_error_rate:.2f}% > {self.thresholds.api_error_rate_percent}%',
                'critical',
                metrics.api_error_rate
            ))

        # Trading success rate alert
        if metrics.success_rate > 0 and metrics.success_rate < self.thresholds.trading_success_rate_percent:
            alerts.append(self._create_alert(
                'trading_success_rate',
                f'Low trading success rate: {metrics.success_rate:.1f}% < {self.thresholds.trading_success_rate_percent}%',
                'critical',
                metrics.success_rate
            ))

        # Daily P&L alert
        if metrics.daily_pnl < self.thresholds.daily_pnl_loss_limit:
            alerts.append(self._create_alert(
                'daily_pnl',
                f'High daily losses: ${metrics.daily_pnl:.2f} < ${self.thresholds.daily_pnl_loss_limit}',
                'critical',
                metrics.daily_pnl
            ))

        # Balance manager response time alert
        if metrics.balance_manager_response_time > self.thresholds.balance_manager_response_time * 1000:  # Convert to ms
            alerts.append(self._create_alert(
                'balance_manager_response_time',
                f'Slow balance manager: {metrics.balance_manager_response_time:.0f}ms > {self.thresholds.balance_manager_response_time * 1000:.0f}ms',
                'warning',
                metrics.balance_manager_response_time
            ))

        # WebSocket latency alert
        if metrics.websocket_latency_ms > self.thresholds.websocket_latency_ms:
            alerts.append(self._create_alert(
                'websocket_latency',
                f'High WebSocket latency: {metrics.websocket_latency_ms:.0f}ms > {self.thresholds.websocket_latency_ms:.0f}ms',
                'warning',
                metrics.websocket_latency_ms
            ))

        # Trade execution time alert
        if metrics.trade_execution_time_ms > self.thresholds.trade_execution_time_ms:
            alerts.append(self._create_alert(
                'trade_execution_time',
                f'Slow trade execution: {metrics.trade_execution_time_ms:.0f}ms > {self.thresholds.trade_execution_time_ms:.0f}ms',
                'warning',
                metrics.trade_execution_time_ms
            ))

        # Process and deduplicate alerts
        filtered_alerts = []
        for alert in alerts:
            if self._should_send_alert(alert):
                filtered_alerts.append(alert)
                await self._send_alert(alert)

        return filtered_alerts

    def _create_alert(self, metric: str, message: str, severity: str, value: float) -> Dict[str, Any]:
        """Create standardized alert object"""
        return {
            'id': f"{metric}_{int(time.time())}",
            'metric': metric,
            'message': message,
            'severity': severity,  # info, warning, critical
            'value': value,
            'timestamp': time.time(),
            'resolved': False
        }

    def _should_send_alert(self, alert: Dict[str, Any]) -> bool:
        """Check if alert should be sent (cooldown logic)"""
        metric = alert['metric']
        now = time.time()

        # Cooldown periods based on severity
        cooldown_periods = {
            'info': 300,      # 5 minutes
            'warning': 600,   # 10 minutes
            'critical': 1800  # 30 minutes
        }

        cooldown = cooldown_periods.get(alert['severity'], 600)

        if metric in self.alert_cooldowns:
            if now - self.alert_cooldowns[metric] < cooldown:
                return False

        self.alert_cooldowns[metric] = now
        return True

    async def _send_alert(self, alert: Dict[str, Any]):
        """Send alert through configured channels"""
        try:
            # Console alerts
            if self.config.console_alerts:
                severity_colors = {
                    'info': '\033[94m',      # Blue
                    'warning': '\033[93m',   # Yellow
                    'critical': '\033[91m'   # Red
                }
                color = severity_colors.get(alert['severity'], '')
                reset_color = '\033[0m'
                print(f"{color}[ALERT {alert['severity'].upper()}]{reset_color} {alert['message']}")

            # Log alerts
            if self.config.log_alerts:
                log_method = getattr(logger, alert['severity'].lower(), logger.warning)
                log_method(f"Production Alert: {alert['message']}")

            # Store in history
            self.alert_history.append(alert)

            # TODO: Implement email and webhook notifications
            # if self.config.email_notifications and self.config.email_recipients:
            #     await self._send_email_alert(alert)
            #
            # if self.config.webhook_notifications and self.config.webhook_url:
            #     await self._send_webhook_alert(alert)

        except Exception as e:
            logger.error(f"Error sending alert: {e}")


class ProductionMonitor:
    """
    Main production monitoring system for crypto trading bot
    
    Provides comprehensive real-time monitoring with:
    - Automated health checks every 5 minutes
    - Configurable alert thresholds
    - Historical metric storage
    - Web dashboard integration
    - Emergency shutdown capabilities
    """

    def __init__(self,
                 project_root: Optional[Path] = None,
                 thresholds: Optional[MetricThresholds] = None,
                 alert_config: Optional[AlertConfig] = None):
        """
        Initialize production monitor
        
        Args:
            project_root: Root directory of trading bot project
            thresholds: Alert threshold configuration
            alert_config: Alert notification configuration
        """
        self.project_root = project_root or Path.cwd()
        self.thresholds = thresholds or MetricThresholds()
        self.alert_config = alert_config or AlertConfig()

        # Core components
        self.collector = MetricCollector(self.project_root)
        self.alert_manager = AlertManager(self.alert_config, self.thresholds)

        # State management
        self.running = False
        self.health_check_task = None
        self.monitoring_task = None

        # Current metrics
        self.current_metrics: Optional[ProductionMetrics] = None
        self.metric_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals

        # Dashboard integration
        self.dashboard_callbacks: List[Callable] = []

        # Emergency controls
        self.emergency_shutdown_callback: Optional[Callable] = None

        logger.info("Production Monitor initialized")

    def set_bot_components(self,
                          balance_manager=None,
                          websocket_manager=None,
                          exchange_client=None,
                          nonce_manager=None):
        """Set references to bot components for monitoring"""
        self.collector.balance_manager = balance_manager
        self.collector.websocket_manager = websocket_manager
        self.collector.exchange_client = exchange_client
        self.collector.nonce_manager = nonce_manager

        logger.info("Bot components connected to production monitor")

    def register_dashboard_callback(self, callback: Callable):
        """Register callback for dashboard updates"""
        self.dashboard_callbacks.append(callback)

    def set_emergency_shutdown_callback(self, callback: Callable):
        """Set callback for emergency shutdown trigger"""
        self.emergency_shutdown_callback = callback

    async def start_monitoring(self):
        """Start the production monitoring system"""
        if self.running:
            logger.warning("Production monitor is already running")
            return

        self.running = True
        logger.info("Starting production monitoring system...")

        # Start health check task (every 5 minutes)
        self.health_check_task = asyncio.create_task(self._health_check_loop())

        # Start continuous monitoring task (every 30 seconds)
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Production monitor started successfully")

    async def stop_monitoring(self):
        """Stop the production monitoring system"""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping production monitoring system...")

        # Cancel tasks
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Production monitor stopped")

    async def _health_check_loop(self):
        """Health check loop running every 5 minutes"""
        while self.running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(300)  # 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute on error

    async def _monitoring_loop(self):
        """Continuous monitoring loop running every 30 seconds"""
        while self.running:
            try:
                await self._collect_and_analyze_metrics()
                await asyncio.sleep(30)  # 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)

    async def _perform_health_check(self):
        """Perform comprehensive health check"""
        logger.info("Performing health check...")

        try:
            # Collect current metrics
            await self._collect_and_analyze_metrics()

            if self.current_metrics:
                # Check for critical issues
                critical_alerts = []

                # Check for emergency conditions
                if (self.current_metrics.memory_usage_mb > self.thresholds.memory_usage_mb * 2 or
                    self.current_metrics.api_error_rate > self.thresholds.api_error_rate_percent * 10 or
                    self.current_metrics.daily_pnl < self.thresholds.daily_pnl_loss_limit * 2):

                    critical_alerts.append("Emergency conditions detected")

                if critical_alerts and self.emergency_shutdown_callback:
                    logger.critical("EMERGENCY: Triggering shutdown due to critical conditions")
                    for alert in critical_alerts:
                        logger.critical(f"Emergency condition: {alert}")

                    # Trigger emergency shutdown
                    try:
                        await self.emergency_shutdown_callback()
                    except Exception as e:
                        logger.error(f"Emergency shutdown failed: {e}")

                logger.info(f"Health check completed - Memory: {self.current_metrics.memory_usage_mb:.1f}MB, "
                           f"Success Rate: {self.current_metrics.success_rate:.1f}%, "
                           f"API Errors: {self.current_metrics.api_errors}")

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            logger.error(traceback.format_exc())

    async def _collect_and_analyze_metrics(self):
        """Collect metrics and perform analysis"""
        try:
            # Collect all metrics
            trading_metrics = await self.collector.collect_trading_metrics()
            system_metrics = await self.collector.collect_system_metrics()
            health_metrics = await self.collector.collect_component_health()

            # Create metrics object
            self.current_metrics = ProductionMetrics(
                timestamp=time.time(),
                **trading_metrics,
                **system_metrics,
                **health_metrics
            )

            # Add to history
            self.metric_history.append(self.current_metrics)

            # Check thresholds and generate alerts
            alerts = await self.alert_manager.check_thresholds(self.current_metrics)

            # Notify dashboard callbacks
            for callback in self.dashboard_callbacks:
                try:
                    await callback(self.current_metrics, alerts)
                except Exception as e:
                    logger.error(f"Dashboard callback error: {e}")

        except Exception as e:
            logger.error(f"Metric collection failed: {e}")
            logger.error(traceback.format_exc())

    def get_current_metrics(self) -> Optional[ProductionMetrics]:
        """Get current metrics snapshot"""
        return self.current_metrics

    def get_metric_history(self, minutes: int = 60) -> List[ProductionMetrics]:
        """Get metric history for specified time period"""
        if not self.metric_history:
            return []

        cutoff_time = time.time() - (minutes * 60)
        return [m for m in self.metric_history if m.timestamp >= cutoff_time]

    def get_alert_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        if not self.alert_manager.alert_history:
            return []

        cutoff_time = time.time() - (minutes * 60)
        return [a for a in self.alert_manager.alert_history if a['timestamp'] >= cutoff_time]

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status summary"""
        if not self.current_metrics:
            return {
                'status': 'unknown',
                'message': 'No metrics available',
                'last_update': None
            }

        # Determine overall status
        status = 'healthy'
        issues = []

        # Check critical thresholds
        if self.current_metrics.memory_usage_mb > self.thresholds.memory_usage_mb:
            status = 'warning'
            issues.append(f'High memory usage: {self.current_metrics.memory_usage_mb:.1f}MB')

        if self.current_metrics.api_error_rate > self.thresholds.api_error_rate_percent:
            status = 'critical'
            issues.append(f'High API error rate: {self.current_metrics.api_error_rate:.2f}%')

        if (self.current_metrics.success_rate > 0 and
            self.current_metrics.success_rate < self.thresholds.trading_success_rate_percent):
            status = 'critical'
            issues.append(f'Low success rate: {self.current_metrics.success_rate:.1f}%')

        if self.current_metrics.daily_pnl < self.thresholds.daily_pnl_loss_limit:
            status = 'critical'
            issues.append(f'High daily losses: ${self.current_metrics.daily_pnl:.2f}')

        return {
            'status': status,
            'message': '; '.join(issues) if issues else 'All systems operating normally',
            'last_update': datetime.fromtimestamp(self.current_metrics.timestamp).isoformat(),
            'uptime_minutes': (time.time() - self.current_metrics.timestamp) / 60 if self.current_metrics else 0,
            'metrics_summary': {
                'memory_mb': self.current_metrics.memory_usage_mb,
                'success_rate': self.current_metrics.success_rate,
                'daily_pnl': self.current_metrics.daily_pnl,
                'api_errors': self.current_metrics.api_errors,
                'websocket_status': self.current_metrics.websocket_status,
                'balance_manager_health': self.current_metrics.balance_manager_health
            }
        }

    async def trigger_emergency_shutdown(self, reason: str = "Manual trigger"):
        """Trigger emergency shutdown"""
        logger.critical(f"EMERGENCY SHUTDOWN TRIGGERED: {reason}")

        if self.emergency_shutdown_callback:
            try:
                await self.emergency_shutdown_callback()
                logger.info("Emergency shutdown completed successfully")
            except Exception as e:
                logger.error(f"Emergency shutdown failed: {e}")
        else:
            logger.warning("No emergency shutdown callback configured")

    def to_dict(self) -> Dict[str, Any]:
        """Convert current state to dictionary for API/dashboard"""
        return {
            'running': self.running,
            'current_metrics': asdict(self.current_metrics) if self.current_metrics else None,
            'system_status': self.get_system_status(),
            'recent_alerts': self.get_alert_history(60),
            'thresholds': asdict(self.thresholds),
            'config': asdict(self.alert_config)
        }


# Singleton instance for global access
_production_monitor: Optional[ProductionMonitor] = None


def get_production_monitor(project_root: Optional[Path] = None) -> ProductionMonitor:
    """Get or create production monitor singleton"""
    global _production_monitor

    if _production_monitor is None:
        _production_monitor = ProductionMonitor(project_root)

    return _production_monitor


# Example usage and integration
if __name__ == "__main__":
    import asyncio

    async def main():
        # Initialize monitor
        monitor = get_production_monitor()

        # Configure custom thresholds
        thresholds = MetricThresholds(
            memory_usage_mb=400.0,
            trading_success_rate_percent=90.0
        )
        monitor.thresholds = thresholds

        # Start monitoring
        await monitor.start_monitoring()

        # Run for 5 minutes as demonstration
        await asyncio.sleep(300)

        # Stop monitoring
        await monitor.stop_monitoring()

    asyncio.run(main())
