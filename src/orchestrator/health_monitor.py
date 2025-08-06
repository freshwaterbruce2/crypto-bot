"""
System Health Monitoring

Monitors all components for health, performance, and automatic recovery.
"""

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

import psutil

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Component health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: Any
    unit: str = ""
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def get_status(self) -> HealthStatus:
        """Determine status based on thresholds"""
        if self.threshold_critical and isinstance(self.value, (int, float)):
            if self.value >= self.threshold_critical:
                return HealthStatus.CRITICAL
        if self.threshold_warning and isinstance(self.value, (int, float)):
            if self.value >= self.threshold_warning:
                return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY


@dataclass
class ComponentHealth:
    """Health information for a component"""
    name: str
    status: HealthStatus
    metrics: dict[str, HealthMetric] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)
    error_count: int = 0
    consecutive_failures: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_metric(self, metric: HealthMetric):
        """Add or update a health metric"""
        self.metrics[metric.name] = metric

    def get_overall_status(self) -> HealthStatus:
        """Calculate overall status from metrics"""
        if not self.metrics:
            return self.status

        statuses = [metric.get_status() for metric in self.metrics.values()]

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY


@dataclass
class HealthAlert:
    """Health alert notification"""
    component: str
    level: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metrics: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            'component': self.component,
            'level': self.level.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'metrics': self.metrics,
            'resolved': self.resolved
        }


class HealthCheck:
    """Base class for health checks"""

    def __init__(self, name: str):
        self.name = name

    async def check(self) -> ComponentHealth:
        """Perform health check"""
        # Default implementation returns unknown status
        return ComponentHealth(
            name=self.name,
            status=HealthStatus.UNKNOWN,
            metadata={"error": "Health check not implemented"}
        )


class SystemHealthCheck(HealthCheck):
    """System resource health check"""

    def __init__(self):
        super().__init__("system")

    async def check(self) -> ComponentHealth:
        """Check system resources"""
        health = ComponentHealth(name=self.name, status=HealthStatus.HEALTHY)

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            health.add_metric(HealthMetric(
                name="cpu_usage",
                value=cpu_percent,
                unit="%",
                threshold_warning=80,
                threshold_critical=95
            ))

            # Memory usage
            memory = psutil.virtual_memory()
            health.add_metric(HealthMetric(
                name="memory_usage",
                value=memory.percent,
                unit="%",
                threshold_warning=85,
                threshold_critical=95
            ))

            # Disk usage
            disk = psutil.disk_usage('/')
            health.add_metric(HealthMetric(
                name="disk_usage",
                value=disk.percent,
                unit="%",
                threshold_warning=85,
                threshold_critical=95
            ))

            # Network connections
            connections = len(psutil.net_connections())
            health.add_metric(HealthMetric(
                name="network_connections",
                value=connections,
                unit="count",
                threshold_warning=1000,
                threshold_critical=5000
            ))

            health.status = health.get_overall_status()

        except Exception as e:
            logger.error(f"System health check failed: {e}")
            health.status = HealthStatus.UNKNOWN
            health.error_count += 1

        return health


class HealthMonitor:
    """Centralized health monitoring system"""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.components: dict[str, ComponentHealth] = {}
        self.health_checks: dict[str, HealthCheck] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_handlers: list[Callable] = []
        self.recovery_handlers: dict[str, Callable] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Thresholds for automatic recovery
        self.recovery_thresholds = {
            'consecutive_failures': 3,
            'error_rate': 0.1,
            'degraded_duration': 300  # 5 minutes
        }

        # Component dependencies for cascading checks
        self.dependencies: dict[str, set[str]] = {}

        # System health check
        self.register_health_check(SystemHealthCheck())

    async def initialize(self):
        """Initialize health monitor"""
        logger.info("Initializing health monitor")

        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitor_loop())

        logger.info("Health monitor initialized")

    async def shutdown(self):
        """Shutdown health monitor"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    def register_component(self, name: str, dependencies: list[str] = None):
        """Register a component for monitoring"""
        self.components[name] = ComponentHealth(name=name, status=HealthStatus.UNKNOWN)

        if dependencies:
            self.dependencies[name] = set(dependencies)

        logger.info(f"Registered component for monitoring: {name}")

    def register_health_check(self, health_check: HealthCheck):
        """Register a health check"""
        self.health_checks[health_check.name] = health_check

    def register_alert_handler(self, handler: Callable):
        """Register an alert handler"""
        self.alert_handlers.append(handler)

    def register_recovery_handler(self, component: str, handler: Callable):
        """Register a recovery handler for a component"""
        self.recovery_handlers[component] = handler

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)

    async def _perform_health_checks(self):
        """Perform all health checks"""
        async with self._lock:
            # Run registered health checks
            for check in self.health_checks.values():
                try:
                    health = await check.check()
                    await self._update_component_health(health)
                except Exception as e:
                    logger.error(f"Health check {check.name} failed: {e}")

            # Check for recovery needs
            await self._check_recovery_needed()

    async def _update_component_health(self, health: ComponentHealth):
        """Update component health and trigger alerts"""
        old_health = self.components.get(health.name)
        self.components[health.name] = health

        # Check for status changes
        if old_health and old_health.status != health.status:
            await self._handle_status_change(health.name, old_health.status, health.status)

        # Check for critical metrics
        for metric in health.metrics.values():
            if metric.get_status() in (HealthStatus.CRITICAL, HealthStatus.UNHEALTHY):
                await self._create_alert(
                    component=health.name,
                    level=AlertLevel.ERROR if metric.get_status() == HealthStatus.UNHEALTHY else AlertLevel.CRITICAL,
                    message=f"{metric.name} is {metric.get_status().value}: {metric.value}{metric.unit}",
                    metrics={metric.name: metric.value}
                )

    async def _handle_status_change(self, component: str, old_status: HealthStatus, new_status: HealthStatus):
        """Handle component status changes"""
        if new_status == HealthStatus.HEALTHY and old_status != HealthStatus.HEALTHY:
            # Component recovered
            await self._create_alert(
                component=component,
                level=AlertLevel.INFO,
                message=f"Component recovered: {old_status.value} -> {new_status.value}"
            )

        elif new_status in (HealthStatus.CRITICAL, HealthStatus.UNHEALTHY):
            # Component degraded
            await self._create_alert(
                component=component,
                level=AlertLevel.CRITICAL if new_status == HealthStatus.CRITICAL else AlertLevel.ERROR,
                message=f"Component degraded: {old_status.value} -> {new_status.value}"
            )

    async def _create_alert(self, component: str, level: AlertLevel, message: str, metrics: dict[str, Any] = None):
        """Create and dispatch an alert"""
        alert = HealthAlert(
            component=component,
            level=level,
            message=message,
            metrics=metrics or {}
        )

        self.alert_history.append(alert)

        # Notify handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")

    async def _check_recovery_needed(self):
        """Check if any components need recovery"""
        for name, health in self.components.items():
            if health.consecutive_failures >= self.recovery_thresholds['consecutive_failures']:
                await self._attempt_recovery(name)

    async def _attempt_recovery(self, component: str):
        """Attempt to recover a component"""
        if component in self.recovery_handlers:
            logger.info(f"Attempting recovery for component: {component}")

            try:
                handler = self.recovery_handlers[component]
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()

                # Reset failure count on successful recovery
                self.components[component].consecutive_failures = 0

                await self._create_alert(
                    component=component,
                    level=AlertLevel.INFO,
                    message="Recovery attempt completed"
                )

            except Exception as e:
                logger.error(f"Recovery failed for {component}: {e}")
                await self._create_alert(
                    component=component,
                    level=AlertLevel.ERROR,
                    message=f"Recovery failed: {str(e)}"
                )

    async def update_component_status(self, name: str, status: HealthStatus, metrics: dict[str, Any] = None):
        """Manually update component status"""
        async with self._lock:
            if name not in self.components:
                self.register_component(name)

            health = self.components[name]
            old_status = health.status
            health.status = status
            health.last_check = datetime.now()

            # Update metrics if provided
            if metrics:
                for metric_name, value in metrics.items():
                    health.add_metric(HealthMetric(name=metric_name, value=value))

            # Handle status change
            if old_status != status:
                await self._handle_status_change(name, old_status, status)

    def get_component_health(self, name: str) -> Optional[ComponentHealth]:
        """Get health information for a component"""
        return self.components.get(name)

    def get_all_health(self) -> dict[str, ComponentHealth]:
        """Get health information for all components"""
        return self.components.copy()

    def get_system_status(self) -> HealthStatus:
        """Get overall system health status"""
        if not self.components:
            return HealthStatus.UNKNOWN

        statuses = [c.status for c in self.components.values()]

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY

    def get_recent_alerts(self, limit: int = 100) -> list[HealthAlert]:
        """Get recent alerts"""
        return list(self.alert_history)[-limit:]

    def get_diagnostics(self) -> dict[str, Any]:
        """Get health monitoring diagnostics"""
        system_status = self.get_system_status()

        return {
            'system_status': system_status.value,
            'check_interval': self.check_interval,
            'components': {
                name: {
                    'status': health.status.value,
                    'last_check': health.last_check.isoformat(),
                    'error_count': health.error_count,
                    'consecutive_failures': health.consecutive_failures,
                    'metrics': {
                        m_name: {
                            'value': metric.value,
                            'unit': metric.unit,
                            'status': metric.get_status().value
                        }
                        for m_name, metric in health.metrics.items()
                    }
                }
                for name, health in self.components.items()
            },
            'recent_alerts': [
                alert.to_dict()
                for alert in self.get_recent_alerts(20)
            ],
            'recovery_handlers': list(self.recovery_handlers.keys()),
            'dependencies': {
                comp: list(deps)
                for comp, deps in self.dependencies.items()
            }
        }

    async def export_health_report(self) -> str:
        """Export health report as JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_status': self.get_system_status().value,
            'diagnostics': self.get_diagnostics()
        }

        return json.dumps(report, indent=2)
