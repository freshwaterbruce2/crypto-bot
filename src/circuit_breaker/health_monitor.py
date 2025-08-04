"""
Health Monitor and Metrics Collection
====================================

Comprehensive health monitoring system for circuit breakers with
real-time metrics collection, health checks, and alerting capabilities.

Features:
- Real-time health status monitoring
- Configurable health check endpoints
- Metrics aggregation and analysis
- Alert generation for health degradation
- Integration with circuit breaker state management
- Historical health data tracking
- Performance trend analysis
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
import aiohttp
import threading

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class HealthMetrics:
    """
    Health metrics for a service or component.
    
    Attributes:
        response_time_ms: Average response time in milliseconds
        success_rate: Success rate (0.0 to 1.0)
        error_rate: Error rate (0.0 to 1.0)
        throughput_rps: Requests per second
        availability: Availability percentage (0.0 to 100.0)
        latency_p50: 50th percentile latency
        latency_p95: 95th percentile latency
        latency_p99: 99th percentile latency
        cpu_usage: CPU usage percentage
        memory_usage: Memory usage percentage
        active_connections: Number of active connections
        queue_depth: Current queue depth
        last_updated: Timestamp of last update
    """
    response_time_ms: float = 0.0
    success_rate: float = 1.0
    error_rate: float = 0.0
    throughput_rps: float = 0.0
    availability: float = 100.0
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_connections: int = 0
    queue_depth: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class HealthCheckResult:
    """
    Result of a health check operation.
    
    Attributes:
        service_name: Name of the service checked
        status: Health status
        response_time_ms: Response time in milliseconds
        timestamp: Check timestamp
        details: Additional details about the check
        error_message: Error message if check failed
        metrics: Health metrics collected
    """
    service_name: str
    status: HealthStatus
    response_time_ms: float
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    metrics: Optional[HealthMetrics] = None


@dataclass
class ServiceHealth:
    """
    Health information for a service.
    
    Attributes:
        name: Service name
        status: Current health status
        metrics: Current health metrics
        last_check: Timestamp of last health check
        check_interval: Health check interval in seconds
        failure_count: Consecutive failure count
        recovery_count: Consecutive recovery count
        alerts: Active alerts for this service
        history: Historical health check results
    """
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    metrics: HealthMetrics = field(default_factory=HealthMetrics)
    last_check: float = 0.0
    check_interval: float = 30.0
    failure_count: int = 0
    recovery_count: int = 0
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    history: deque = field(default_factory=lambda: deque(maxlen=100))


@dataclass
class HealthAlert:
    """
    Health alert information.
    
    Attributes:
        id: Unique alert ID
        service_name: Service that triggered the alert
        severity: Alert severity
        message: Alert message
        timestamp: Alert timestamp
        acknowledged: Whether alert has been acknowledged
        resolved: Whether alert has been resolved
        resolution_time: Alert resolution timestamp
        metadata: Additional alert metadata
    """
    id: str
    service_name: str
    severity: AlertSeverity
    message: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """
    Comprehensive health monitoring system.
    
    Monitors the health of services and components, collects metrics,
    and generates alerts when health degrades.
    """
    
    def __init__(
        self,
        check_interval: float = 30.0,
        alert_threshold: int = 3,
        recovery_threshold: int = 2,
        storage_path: Optional[str] = None
    ):
        """
        Initialize health monitor.
        
        Args:
            check_interval: Default health check interval in seconds
            alert_threshold: Number of failures before alerting
            recovery_threshold: Number of successes before recovery
            storage_path: Path for persistent storage
        """
        self.check_interval = check_interval
        self.alert_threshold = alert_threshold
        self.recovery_threshold = recovery_threshold
        self.storage_path = Path(storage_path) if storage_path else None
        
        # Service tracking
        self.services: Dict[str, ServiceHealth] = {}
        self.health_checks: Dict[str, Callable] = {}
        
        # Metrics and history
        self.global_metrics = HealthMetrics()
        self.metrics_history = deque(maxlen=1000)
        self.alerts: Dict[str, HealthAlert] = {}
        
        # Monitoring control
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._lock = threading.RLock()
        
        # HTTP session for health checks
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"Health monitor initialized with {check_interval}s check interval")
    
    async def start(self) -> None:
        """
        Start the health monitoring system.
        """
        if self._monitoring_active:
            return
        
        # Create HTTP session
        self._http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10.0)
        )
        
        # Load persistent state
        if self.storage_path:
            await self._load_state()
        
        # Start monitoring loop
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Health monitor started")
    
    async def stop(self) -> None:
        """
        Stop the health monitoring system.
        """
        self._monitoring_active = False
        
        # Stop monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Close HTTP session
        if self._http_session:
            await self._http_session.close()
        
        # Save persistent state
        if self.storage_path:
            await self._save_state()
        
        logger.info("Health monitor stopped")
    
    def register_service(
        self,
        name: str,
        health_check: Optional[Callable] = None,
        check_interval: Optional[float] = None
    ) -> None:
        """
        Register a service for health monitoring.
        
        Args:
            name: Service name
            health_check: Health check function (async or sync)
            check_interval: Custom check interval for this service
        """
        with self._lock:
            service = ServiceHealth(
                name=name,
                check_interval=check_interval or self.check_interval
            )
            
            self.services[name] = service
            
            if health_check:
                self.health_checks[name] = health_check
            
            logger.info(f"Registered service for health monitoring: {name}")
    
    def unregister_service(self, name: str) -> None:
        """
        Unregister a service from health monitoring.
        
        Args:
            name: Service name
        """
        with self._lock:
            self.services.pop(name, None)
            self.health_checks.pop(name, None)
            
            # Remove related alerts
            alerts_to_remove = [
                alert_id for alert_id, alert in self.alerts.items()
                if alert.service_name == name
            ]
            
            for alert_id in alerts_to_remove:
                del self.alerts[alert_id]
            
            logger.info(f"Unregistered service from health monitoring: {name}")
    
    def register_http_health_check(
        self,
        name: str,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
        timeout: float = 5.0,
        check_interval: Optional[float] = None
    ) -> None:
        """
        Register an HTTP-based health check.
        
        Args:
            name: Service name
            url: Health check URL
            method: HTTP method
            headers: Optional HTTP headers
            expected_status: Expected HTTP status code
            timeout: Request timeout
            check_interval: Custom check interval
        """
        async def http_health_check() -> HealthCheckResult:
            if not self._http_session:
                return HealthCheckResult(
                    service_name=name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0.0,
                    error_message="HTTP session not available"
                )
            
            start_time = time.time()
            
            try:
                async with self._http_session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == expected_status:
                        status = HealthStatus.HEALTHY
                        error_message = None
                    else:
                        status = HealthStatus.UNHEALTHY
                        error_message = f"HTTP {response.status}"
                    
                    return HealthCheckResult(
                        service_name=name,
                        status=status,
                        response_time_ms=response_time,
                        error_message=error_message,
                        details={
                            'url': url,
                            'method': method,
                            'status_code': response.status,
                            'expected_status': expected_status
                        }
                    )
            
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                
                return HealthCheckResult(
                    service_name=name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    error_message=str(e),
                    details={'url': url, 'method': method}
                )
        
        self.register_service(name, http_health_check, check_interval)
    
    async def check_service_health(self, name: str) -> HealthCheckResult:
        """
        Perform health check for a specific service.
        
        Args:
            name: Service name
            
        Returns:
            Health check result
        """
        health_check = self.health_checks.get(name)
        
        if not health_check:
            return HealthCheckResult(
                service_name=name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0.0,
                error_message="No health check function registered"
            )
        
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(health_check):
                result = await health_check()
            else:
                result = health_check()
            
            # Ensure result is a HealthCheckResult
            if not isinstance(result, HealthCheckResult):
                # Convert simple return values
                if isinstance(result, bool):
                    status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                elif isinstance(result, dict):
                    status = HealthStatus(result.get('status', 'UNKNOWN'))
                else:
                    status = HealthStatus.UNKNOWN
                
                response_time = (time.time() - start_time) * 1000
                result = HealthCheckResult(
                    service_name=name,
                    status=status,
                    response_time_ms=response_time
                )
            
            return result
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                service_name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def check_all_services(self) -> Dict[str, HealthCheckResult]:
        """
        Perform health checks for all registered services.
        
        Returns:
            Dictionary of health check results
        """
        results = {}
        
        # Create tasks for all health checks
        tasks = [
            self.check_service_health(name)
            for name in self.services.keys()
        ]
        
        if tasks:
            try:
                check_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(check_results):
                    service_name = list(self.services.keys())[i]
                    
                    if isinstance(result, Exception):
                        results[service_name] = HealthCheckResult(
                            service_name=service_name,
                            status=HealthStatus.UNHEALTHY,
                            response_time_ms=0.0,
                            error_message=str(result)
                        )
                    else:
                        results[service_name] = result
            
            except Exception as e:
                logger.error(f"Error during bulk health checks: {e}")
        
        return results
    
    def update_service_health(self, result: HealthCheckResult) -> None:
        """
        Update service health based on check result.
        
        Args:
            result: Health check result
        """
        with self._lock:
            service = self.services.get(result.service_name)
            if not service:
                return
            
            # Update service status
            old_status = service.status
            service.status = result.status
            service.last_check = result.timestamp
            
            # Update metrics if provided
            if result.metrics:
                service.metrics = result.metrics
            else:
                # Update basic metrics from result
                service.metrics.response_time_ms = result.response_time_ms
                service.metrics.last_updated = result.timestamp
            
            # Update failure/recovery counts
            if result.status == HealthStatus.UNHEALTHY:
                service.failure_count += 1
                service.recovery_count = 0
            elif result.status == HealthStatus.HEALTHY:
                service.recovery_count += 1
                if service.failure_count > 0:
                    service.failure_count = max(0, service.failure_count - 1)
            
            # Add to history
            service.history.append({
                'timestamp': result.timestamp,
                'status': result.status.value,
                'response_time_ms': result.response_time_ms,
                'error_message': result.error_message
            })
            
            # Check for alerts
            self._check_alerts(service, old_status)
            
            logger.debug(
                f"Updated health for {result.service_name}: "
                f"{old_status.value} → {result.status.value} "
                f"(failures: {service.failure_count}, recoveries: {service.recovery_count})"
            )
    
    def _check_alerts(self, service: ServiceHealth, old_status: HealthStatus) -> None:
        """
        Check if alerts should be generated for service health changes.
        
        Args:
            service: Service health information
            old_status: Previous health status
        """
        current_time = time.time()
        
        # Check for degradation alerts
        if (service.status == HealthStatus.UNHEALTHY and 
            service.failure_count >= self.alert_threshold):
            
            alert_id = f"{service.name}_unhealthy_{int(current_time)}"
            
            if not any(a.service_name == service.name and not a.resolved 
                      for a in self.alerts.values()):
                
                alert = HealthAlert(
                    id=alert_id,
                    service_name=service.name,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Service {service.name} is unhealthy after {service.failure_count} consecutive failures",
                    metadata={
                        'failure_count': service.failure_count,
                        'last_error': service.history[-1].get('error_message') if service.history else None,
                        'response_time_ms': service.metrics.response_time_ms
                    }
                )
                
                self.alerts[alert_id] = alert
                service.alerts.append(asdict(alert))
                
                logger.critical(
                    f"HEALTH ALERT: {alert.message} "
                    f"(response_time: {service.metrics.response_time_ms:.2f}ms)"
                )
        
        # Check for recovery alerts
        elif (service.status == HealthStatus.HEALTHY and 
              old_status != HealthStatus.HEALTHY and 
              service.recovery_count >= self.recovery_threshold):
            
            # Resolve existing alerts
            for alert in self.alerts.values():
                if (alert.service_name == service.name and 
                    not alert.resolved and 
                    alert.severity == AlertSeverity.CRITICAL):
                    
                    alert.resolved = True
                    alert.resolution_time = current_time
                    
                    logger.info(
                        f"HEALTH RECOVERY: Service {service.name} recovered after {service.recovery_count} consecutive successes"
                    )
        
        # Check for performance degradation
        if service.status == HealthStatus.HEALTHY:
            response_times = [
                h.get('response_time_ms', 0) for h in list(service.history)[-10:]
                if h.get('status') == 'HEALTHY'
            ]
            
            if len(response_times) >= 5:
                avg_response_time = statistics.mean(response_times)
                
                # Alert if response time is significantly higher than normal
                if avg_response_time > 1000:  # 1 second threshold
                    alert_id = f"{service.name}_slow_{int(current_time)}"
                    
                    if not any(a.service_name == service.name and 
                              a.severity == AlertSeverity.WARNING and 
                              not a.resolved and 
                              'slow' in a.id
                              for a in self.alerts.values()):
                        
                        alert = HealthAlert(
                            id=alert_id,
                            service_name=service.name,
                            severity=AlertSeverity.WARNING,
                            message=f"Service {service.name} has high response times (avg: {avg_response_time:.2f}ms)",
                            metadata={
                                'avg_response_time_ms': avg_response_time,
                                'recent_response_times': response_times
                            }
                        )
                        
                        self.alerts[alert_id] = alert
                        service.alerts.append(asdict(alert))
                        
                        logger.warning(alert.message)
    
    def get_service_health(self, name: str) -> Optional[ServiceHealth]:
        """
        Get health information for a specific service.
        
        Args:
            name: Service name
            
        Returns:
            Service health information or None if not found
        """
        with self._lock:
            return self.services.get(name)
    
    def get_all_service_health(self) -> Dict[str, ServiceHealth]:
        """
        Get health information for all services.
        
        Returns:
            Dictionary of service health information
        """
        with self._lock:
            return self.services.copy()
    
    def get_global_health_status(self) -> Dict[str, Any]:
        """
        Get global health status across all services.
        
        Returns:
            Global health status information
        """
        with self._lock:
            services = list(self.services.values())
        
        if not services:
            return {
                'overall_status': HealthStatus.UNKNOWN.value,
                'total_services': 0,
                'healthy_services': 0,
                'degraded_services': 0,
                'unhealthy_services': 0,
                'active_alerts': 0,
                'avg_response_time_ms': 0.0
            }
        
        # Count services by status
        status_counts = defaultdict(int)
        total_response_time = 0.0
        
        for service in services:
            status_counts[service.status.value] += 1
            total_response_time += service.metrics.response_time_ms
        
        # Determine overall status
        unhealthy_count = status_counts.get('UNHEALTHY', 0)
        degraded_count = status_counts.get('DEGRADED', 0)
        
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Count active alerts
        active_alerts = sum(1 for alert in self.alerts.values() if not alert.resolved)
        
        return {
            'overall_status': overall_status.value,
            'total_services': len(services),
            'healthy_services': status_counts.get('HEALTHY', 0),
            'degraded_services': status_counts.get('DEGRADED', 0),
            'unhealthy_services': status_counts.get('UNHEALTHY', 0),
            'unknown_services': status_counts.get('UNKNOWN', 0),
            'active_alerts': active_alerts,
            'total_alerts': len(self.alerts),
            'avg_response_time_ms': total_response_time / len(services) if services else 0.0,
            'last_check': max(service.last_check for service in services) if services else 0.0
        }
    
    def get_alerts(self, service_name: Optional[str] = None, active_only: bool = True) -> List[HealthAlert]:
        """
        Get health alerts.
        
        Args:
            service_name: Filter by service name (None for all)
            active_only: Only return active (unresolved) alerts
            
        Returns:
            List of health alerts
        """
        alerts = list(self.alerts.values())
        
        if service_name:
            alerts = [a for a in alerts if a.service_name == service_name]
        
        if active_only:
            alerts = [a for a in alerts if not a.resolved]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge a health alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if alert was acknowledged, False if not found
        """
        with self._lock:
            alert = self.alerts.get(alert_id)
            if alert:
                alert.acknowledged = True
                logger.info(f"Health alert acknowledged: {alert_id}")
                return True
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve a health alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if alert was resolved, False if not found
        """
        with self._lock:
            alert = self.alerts.get(alert_id)
            if alert:
                alert.resolved = True
                alert.resolution_time = time.time()
                logger.info(f"Health alert resolved: {alert_id}")
                return True
            return False
    
    async def _monitoring_loop(self) -> None:
        """
        Main monitoring loop that performs periodic health checks.
        """
        while self._monitoring_active:
            try:
                current_time = time.time()
                
                # Determine which services need checking
                services_to_check = []
                
                with self._lock:
                    for name, service in self.services.items():
                        time_since_check = current_time - service.last_check
                        if time_since_check >= service.check_interval:
                            services_to_check.append(name)
                
                # Perform health checks
                if services_to_check:
                    logger.debug(f"Checking health for {len(services_to_check)} services")
                    
                    results = await self.check_all_services()
                    
                    # Update service health
                    for result in results.values():
                        self.update_service_health(result)
                    
                    # Update global metrics
                    self._update_global_metrics()
                
                # Sleep until next check cycle
                await asyncio.sleep(min(5.0, self.check_interval / 2))
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(5.0)
    
    def _update_global_metrics(self) -> None:
        """
        Update global health metrics.
        """
        with self._lock:
            services = list(self.services.values())
        
        if not services:
            return
        
        # Calculate global metrics
        total_response_time = sum(s.metrics.response_time_ms for s in services)
        healthy_services = sum(1 for s in services if s.status == HealthStatus.HEALTHY)
        
        self.global_metrics.response_time_ms = total_response_time / len(services)
        self.global_metrics.availability = (healthy_services / len(services)) * 100
        self.global_metrics.last_updated = time.time()
        
        # Add to history
        self.metrics_history.append({
            'timestamp': time.time(),
            'avg_response_time_ms': self.global_metrics.response_time_ms,
            'availability': self.global_metrics.availability,
            'healthy_services': healthy_services,
            'total_services': len(services)
        })
    
    async def _save_state(self) -> None:
        """
        Save health monitoring state to persistent storage.
        """
        if not self.storage_path:
            return
        
        try:
            state_data = {
                'services': {
                    name: {
                        'name': service.name,
                        'status': service.status.value,
                        'metrics': asdict(service.metrics),
                        'last_check': service.last_check,
                        'failure_count': service.failure_count,
                        'recovery_count': service.recovery_count,
                        'history': list(service.history)[-50:]  # Save last 50 entries
                    }
                    for name, service in self.services.items()
                },
                'global_metrics': asdict(self.global_metrics),
                'alerts': {
                    alert_id: asdict(alert)
                    for alert_id, alert in self.alerts.items()
                    if not alert.resolved or (time.time() - alert.timestamp) < 86400  # Keep for 24 hours
                },
                'timestamp': time.time()
            }
            
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.storage_path, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            logger.debug(f"Health monitor state saved to {self.storage_path}")
        
        except Exception as e:
            logger.error(f"Failed to save health monitor state: {e}")
    
    async def _load_state(self) -> None:
        """
        Load health monitoring state from persistent storage.
        """
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                state_data = json.load(f)
            
            # Check if state is recent (within 1 hour)
            current_time = time.time()
            saved_time = state_data.get('timestamp', 0)
            
            if (current_time - saved_time) < 3600:  # 1 hour
                # Restore services
                if 'services' in state_data:
                    for name, service_data in state_data['services'].items():
                        if name in self.services:  # Only restore if service is still registered
                            service = self.services[name]
                            service.status = HealthStatus(service_data.get('status', 'UNKNOWN'))
                            service.last_check = service_data.get('last_check', 0)
                            service.failure_count = service_data.get('failure_count', 0)
                            service.recovery_count = service_data.get('recovery_count', 0)
                            
                            # Restore metrics
                            if 'metrics' in service_data:
                                metrics_data = service_data['metrics']
                                for key, value in metrics_data.items():
                                    if hasattr(service.metrics, key):
                                        setattr(service.metrics, key, value)
                            
                            # Restore history
                            if 'history' in service_data:
                                service.history.extend(service_data['history'])
                
                # Restore global metrics
                if 'global_metrics' in state_data:
                    metrics_data = state_data['global_metrics']
                    for key, value in metrics_data.items():
                        if hasattr(self.global_metrics, key):
                            setattr(self.global_metrics, key, value)
                
                # Restore alerts
                if 'alerts' in state_data:
                    for alert_id, alert_data in state_data['alerts'].items():
                        alert = HealthAlert(
                            id=alert_data['id'],
                            service_name=alert_data['service_name'],
                            severity=AlertSeverity(alert_data['severity']),
                            message=alert_data['message'],
                            timestamp=alert_data['timestamp'],
                            acknowledged=alert_data.get('acknowledged', False),
                            resolved=alert_data.get('resolved', False),
                            resolution_time=alert_data.get('resolution_time'),
                            metadata=alert_data.get('metadata', {})
                        )
                        self.alerts[alert_id] = alert
                
                logger.info(f"Health monitor state loaded: {len(self.services)} services, {len(self.alerts)} alerts")
            else:
                logger.info("Health monitor state too old, starting fresh")
        
        except Exception as e:
            logger.error(f"Failed to load health monitor state: {e}")
    
    def cleanup(self) -> None:
        """
        Cleanup health monitor resources.
        """
        logger.info("Health monitor cleanup completed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
