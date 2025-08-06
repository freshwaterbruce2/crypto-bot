"""
REST Fallback Manager for Crypto Trading Bot
===========================================

Emergency fallback system that handles critical operations when WebSocket V2 fails.
Provides service degradation management and coordinated recovery strategies.

Key Features:
- Emergency fallback when WebSocket fails
- Critical operation handling with prioritization
- Service degradation levels and recovery coordination
- Automatic failover and failback mechanisms
- Recovery status monitoring and reporting

Usage:
    fallback_manager = RestFallbackManager(strategic_client, websocket_manager)
    await fallback_manager.initialize()

    # Handle WebSocket failure
    await fallback_manager.handle_websocket_failure()

    # Emergency operations
    balance = await fallback_manager.emergency_get_balance()
    result = await fallback_manager.emergency_cancel_order(txid)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .strategic_rest_client import StrategicRestClient

logger = logging.getLogger(__name__)


class ServiceLevel(Enum):
    """Service degradation levels."""
    FULL_SERVICE = "full_service"           # WebSocket + REST both working
    DEGRADED_SERVICE = "degraded_service"   # WebSocket issues, REST backup
    EMERGENCY_ONLY = "emergency_only"       # Only critical operations
    SERVICE_OUTAGE = "service_outage"       # Both sources failed


class OperationPriority(Enum):
    """Operation priority levels."""
    CRITICAL = 1    # Account safety, order cancellation
    HIGH = 2        # Balance checks, position management
    MEDIUM = 3      # Market data, non-critical queries
    LOW = 4         # Historical data, analytics


@dataclass
class FallbackOperation:
    """Represents a fallback operation."""
    operation_id: str
    priority: OperationPriority
    endpoint: str
    params: dict[str, Any]
    callback: Optional[Callable] = None
    timeout: float = 30.0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)


@dataclass
class ServiceStatus:
    """Current service status."""
    level: ServiceLevel
    websocket_healthy: bool
    rest_healthy: bool
    last_websocket_data: Optional[float] = None
    last_rest_success: Optional[float] = None
    failure_reason: Optional[str] = None
    recovery_attempts: int = 0
    degradation_start: Optional[float] = None


@dataclass
class FallbackStats:
    """Statistics for fallback operations."""
    total_fallbacks: int = 0
    websocket_failures: int = 0
    emergency_operations: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    average_degradation_time: float = 0.0
    critical_operations_completed: int = 0

    def update_recovery(self, success: bool, degradation_time: float):
        """Update recovery statistics."""
        if success:
            self.successful_recoveries += 1
        else:
            self.failed_recoveries += 1

        # Update average degradation time
        total_degradations = self.successful_recoveries + self.failed_recoveries
        if total_degradations > 0:
            self.average_degradation_time = (
                (self.average_degradation_time * (total_degradations - 1) + degradation_time) /
                total_degradations
            )


class RestFallbackManager:
    """
    Manages fallback operations and service degradation when primary data sources fail.

    Provides coordinated fallback strategies, emergency operation handling,
    and automatic recovery management for critical trading operations.
    """

    def __init__(
        self,
        strategic_client: StrategicRestClient,
        websocket_manager: Optional[Any] = None,
        health_check_interval: float = 30.0,
        recovery_timeout: float = 300.0,
        max_recovery_attempts: int = 5
    ):
        """
        Initialize REST fallback manager.

        Args:
            strategic_client: Strategic REST client instance
            websocket_manager: WebSocket manager to monitor
            health_check_interval: Seconds between health checks
            recovery_timeout: Maximum time to attempt recovery
            max_recovery_attempts: Maximum recovery attempts before giving up
        """
        self.strategic_client = strategic_client
        self.websocket_manager = websocket_manager
        self.health_check_interval = health_check_interval
        self.recovery_timeout = recovery_timeout
        self.max_recovery_attempts = max_recovery_attempts

        # Service status tracking
        self.service_status = ServiceStatus(
            level=ServiceLevel.FULL_SERVICE,
            websocket_healthy=True,
            rest_healthy=True
        )

        # Operation management
        self._pending_operations: list[FallbackOperation] = []
        self._operation_lock = asyncio.Lock()
        self._operation_counter = 0

        # Recovery management
        self._recovery_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._is_recovering = False

        # Statistics
        self.stats = FallbackStats()

        # Configuration
        self._critical_endpoints = {
            'Balance', 'TradeBalance', 'OpenOrders',
            'CancelOrder', 'CancelAllOrders', 'AddOrder'
        }

        self._degraded_service_endpoints = {
            'Balance', 'TradeBalance', 'OpenOrders', 'ClosedOrders',
            'CancelOrder', 'CancelAllOrders', 'Ticker', 'SystemStatus'
        }

        # Callbacks for service level changes
        self._service_level_callbacks: list[Callable] = []

        # State
        self._initialized = False
        self._running = False

        logger.info(
            f"[FALLBACK_MANAGER] Initialized: "
            f"health_interval={health_check_interval}s, recovery_timeout={recovery_timeout}s"
        )

    async def initialize(self) -> None:
        """Initialize the fallback manager."""
        if self._initialized:
            return

        # Ensure strategic client is ready
        if not self.strategic_client._initialized:
            await self.strategic_client.initialize()

        # Start health monitoring
        await self.start_monitoring()

        self._initialized = True
        logger.info("[FALLBACK_MANAGER] Fallback manager initialized")

    async def start_monitoring(self) -> None:
        """Start health monitoring and recovery tasks."""
        if self._running:
            return

        self._running = True

        # Start health monitor
        self._health_monitor_task = asyncio.create_task(self._health_monitor())

        logger.info("[FALLBACK_MANAGER] Health monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop health monitoring and recovery tasks."""
        self._running = False

        # Cancel monitoring tasks
        if self._health_monitor_task and not self._health_monitor_task.done():
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass

        # Cancel recovery task
        if self._recovery_task and not self._recovery_task.done():
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass

        logger.info("[FALLBACK_MANAGER] Health monitoring stopped")

    async def shutdown(self) -> None:
        """Shutdown the fallback manager."""
        await self.stop_monitoring()

        # Complete any pending operations
        await self._complete_pending_operations()

        self._initialized = False
        logger.info("[FALLBACK_MANAGER] Fallback manager shutdown complete")

    # ====== HEALTH MONITORING ======

    async def _health_monitor(self) -> None:
        """Background health monitoring task."""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_service_health()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[FALLBACK_MANAGER] Health monitor error: {e}")
                await asyncio.sleep(10.0)

    async def _check_service_health(self) -> None:
        """Check health of WebSocket and REST services."""
        time.time()

        # Check WebSocket health
        websocket_healthy = await self._check_websocket_health()

        # Check REST health
        rest_healthy = await self._check_rest_health()

        # Update service status
        old_level = self.service_status.level

        self.service_status.websocket_healthy = websocket_healthy
        self.service_status.rest_healthy = rest_healthy

        # Determine service level
        if websocket_healthy and rest_healthy:
            self.service_status.level = ServiceLevel.FULL_SERVICE
        elif rest_healthy:
            self.service_status.level = ServiceLevel.DEGRADED_SERVICE
        elif websocket_healthy:
            self.service_status.level = ServiceLevel.DEGRADED_SERVICE
        else:
            self.service_status.level = ServiceLevel.SERVICE_OUTAGE

        # Handle service level changes
        if old_level != self.service_status.level:
            await self._handle_service_level_change(old_level, self.service_status.level)

    async def _check_websocket_health(self) -> bool:
        """Check WebSocket health."""
        if not self.websocket_manager:
            return False

        try:
            # Check if WebSocket manager has health check method
            if hasattr(self.websocket_manager, 'is_healthy'):
                is_healthy = await self.websocket_manager.is_healthy()
                if is_healthy:
                    self.service_status.last_websocket_data = time.time()
                return is_healthy

            # Check if WebSocket manager is connected
            if hasattr(self.websocket_manager, 'is_connected'):
                is_connected = self.websocket_manager.is_connected()
                if is_connected:
                    self.service_status.last_websocket_data = time.time()
                return is_connected

            # Fallback: assume healthy if manager exists
            return True

        except Exception as e:
            logger.error(f"[FALLBACK_MANAGER] WebSocket health check error: {e}")
            return False

    async def _check_rest_health(self) -> bool:
        """Check REST API health."""
        try:
            # Use strategic client health check
            health = await self.strategic_client.health_check()
            is_healthy = health['overall_status'] in ['healthy', 'degraded']

            if is_healthy:
                self.service_status.last_rest_success = time.time()

            return is_healthy

        except Exception as e:
            logger.error(f"[FALLBACK_MANAGER] REST health check error: {e}")
            return False

    async def _handle_service_level_change(
        self,
        old_level: ServiceLevel,
        new_level: ServiceLevel
    ) -> None:
        """Handle service level changes."""
        logger.info(f"[FALLBACK_MANAGER] Service level changed: {old_level.value} -> {new_level.value}")

        # Update degradation tracking
        current_time = time.time()

        if old_level == ServiceLevel.FULL_SERVICE and new_level != ServiceLevel.FULL_SERVICE:
            self.service_status.degradation_start = current_time
            self.stats.total_fallbacks += 1

            if new_level == ServiceLevel.SERVICE_OUTAGE:
                logger.critical("[FALLBACK_MANAGER] SERVICE OUTAGE: Both WebSocket and REST failed")

        elif old_level != ServiceLevel.FULL_SERVICE and new_level == ServiceLevel.FULL_SERVICE:
            # Recovery detected
            if self.service_status.degradation_start:
                degradation_time = current_time - self.service_status.degradation_start
                self.stats.update_recovery(True, degradation_time)
                logger.info(f"[FALLBACK_MANAGER] Service recovered after {degradation_time:.1f}s")

            self.service_status.degradation_start = None
            self.service_status.recovery_attempts = 0

        # Configure strategic client based on service level
        if new_level == ServiceLevel.EMERGENCY_ONLY:
            self.strategic_client.set_emergency_mode(True)
        elif new_level == ServiceLevel.FULL_SERVICE:
            self.strategic_client.set_emergency_mode(False)

        # Start recovery if needed
        if new_level in [ServiceLevel.DEGRADED_SERVICE, ServiceLevel.SERVICE_OUTAGE]:
            await self._start_recovery()

        # Notify callbacks
        for callback in self._service_level_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(old_level, new_level)
                else:
                    callback(old_level, new_level)
            except Exception as e:
                logger.error(f"[FALLBACK_MANAGER] Callback error: {e}")

    # ====== EMERGENCY OPERATIONS ======

    async def handle_websocket_failure(self, reason: str = "Unknown") -> None:
        """
        Handle WebSocket failure event.

        Args:
            reason: Reason for the failure
        """
        logger.warning(f"[FALLBACK_MANAGER] WebSocket failure reported: {reason}")

        self.service_status.failure_reason = reason
        self.service_status.websocket_healthy = False
        self.stats.websocket_failures += 1

        # Force health check and service level update
        await self._check_service_health()

    async def emergency_get_balance(self) -> dict[str, Any]:
        """
        Emergency balance retrieval via REST.

        Returns:
            Account balance data
        """
        self.stats.emergency_operations += 1
        self.stats.critical_operations_completed += 1

        logger.warning("[FALLBACK_MANAGER] Emergency balance retrieval")

        return await self.strategic_client.emergency_balance_check()

    async def emergency_get_open_orders(self) -> dict[str, Any]:
        """
        Emergency open orders retrieval via REST.

        Returns:
            Open orders data
        """
        self.stats.emergency_operations += 1
        self.stats.critical_operations_completed += 1

        logger.warning("[FALLBACK_MANAGER] Emergency open orders retrieval")

        return await self.strategic_client.emergency_open_orders()

    async def emergency_cancel_order(self, txid: str) -> dict[str, Any]:
        """
        Emergency order cancellation via REST.

        Args:
            txid: Transaction ID to cancel

        Returns:
            Cancellation result
        """
        self.stats.emergency_operations += 1
        self.stats.critical_operations_completed += 1

        logger.warning(f"[FALLBACK_MANAGER] Emergency order cancellation: {txid}")

        return await self.strategic_client.emergency_cancel_order(txid)

    async def emergency_cancel_all_orders(self) -> dict[str, Any]:
        """
        Emergency cancellation of all orders via REST.

        Returns:
            Cancellation result
        """
        self.stats.emergency_operations += 1
        self.stats.critical_operations_completed += 1

        logger.critical("[FALLBACK_MANAGER] EMERGENCY: Cancelling all orders")

        return await self.strategic_client._execute_strategic_request(
            'CancelAllOrders',
            priority="emergency"
        )

    async def emergency_system_status(self) -> dict[str, Any]:
        """
        Emergency system status check via REST.

        Returns:
            System status data
        """
        logger.warning("[FALLBACK_MANAGER] Emergency system status check")

        return await self.strategic_client.emergency_system_status()

    # ====== OPERATION QUEUING ======

    async def queue_operation(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        priority: OperationPriority = OperationPriority.MEDIUM,
        callback: Optional[Callable] = None,
        timeout: float = 30.0
    ) -> str:
        """
        Queue an operation for fallback execution.

        Args:
            endpoint: API endpoint name
            params: Request parameters
            priority: Operation priority
            callback: Completion callback
            timeout: Operation timeout

        Returns:
            Operation ID
        """
        async with self._operation_lock:
            self._operation_counter += 1
            operation_id = f"op_{self._operation_counter}_{int(time.time())}"

            operation = FallbackOperation(
                operation_id=operation_id,
                priority=priority,
                endpoint=endpoint,
                params=params or {},
                callback=callback,
                timeout=timeout
            )

            self._pending_operations.append(operation)

            # Sort by priority
            self._pending_operations.sort(key=lambda op: op.priority.value)

            logger.debug(f"[FALLBACK_MANAGER] Queued operation {operation_id}: {endpoint}")

            return operation_id

    async def _complete_pending_operations(self) -> None:
        """Complete all pending operations."""
        async with self._operation_lock:
            operations = self._pending_operations.copy()
            self._pending_operations.clear()

        if not operations:
            return

        logger.info(f"[FALLBACK_MANAGER] Completing {len(operations)} pending operations")

        for operation in operations:
            try:
                # Check if operation is allowed at current service level
                if not self._is_operation_allowed(operation):
                    logger.warning(
                        f"[FALLBACK_MANAGER] Operation {operation.operation_id} "
                        f"not allowed at service level {self.service_status.level.value}"
                    )
                    continue

                # Execute operation
                result = await self.strategic_client._execute_strategic_request(
                    operation.endpoint,
                    operation.params,
                    priority="emergency" if operation.priority == OperationPriority.CRITICAL else "normal"
                )

                # Call callback if provided
                if operation.callback:
                    try:
                        if asyncio.iscoroutinefunction(operation.callback):
                            await operation.callback(result)
                        else:
                            operation.callback(result)
                    except Exception as e:
                        logger.error(f"[FALLBACK_MANAGER] Operation callback error: {e}")

                logger.debug(f"[FALLBACK_MANAGER] Completed operation {operation.operation_id}")

            except Exception as e:
                logger.error(f"[FALLBACK_MANAGER] Operation {operation.operation_id} failed: {e}")

    def _is_operation_allowed(self, operation: FallbackOperation) -> bool:
        """Check if operation is allowed at current service level."""
        if self.service_status.level == ServiceLevel.FULL_SERVICE:
            return True
        elif self.service_status.level == ServiceLevel.DEGRADED_SERVICE:
            return operation.endpoint in self._degraded_service_endpoints
        elif self.service_status.level == ServiceLevel.EMERGENCY_ONLY:
            return operation.endpoint in self._critical_endpoints
        else:  # SERVICE_OUTAGE
            return operation.priority == OperationPriority.CRITICAL

    # ====== RECOVERY MANAGEMENT ======

    async def _start_recovery(self) -> None:
        """Start recovery process if not already running."""
        if self._is_recovering:
            return

        self._is_recovering = True

        if self._recovery_task and not self._recovery_task.done():
            self._recovery_task.cancel()

        self._recovery_task = asyncio.create_task(self._recovery_process())
        logger.info("[FALLBACK_MANAGER] Recovery process started")

    async def _recovery_process(self) -> None:
        """Recovery process to restore full service."""
        start_time = time.time()

        try:
            while (self._running and
                   self.service_status.level != ServiceLevel.FULL_SERVICE and
                   self.service_status.recovery_attempts < self.max_recovery_attempts and
                   time.time() - start_time < self.recovery_timeout):

                self.service_status.recovery_attempts += 1

                logger.info(
                    f"[FALLBACK_MANAGER] Recovery attempt {self.service_status.recovery_attempts} "
                    f"of {self.max_recovery_attempts}"
                )

                # Try to recover WebSocket if needed
                if not self.service_status.websocket_healthy and self.websocket_manager:
                    await self._attempt_websocket_recovery()

                # Try to recover REST if needed
                if not self.service_status.rest_healthy:
                    await self._attempt_rest_recovery()

                # Check if recovery succeeded
                await self._check_service_health()

                if self.service_status.level == ServiceLevel.FULL_SERVICE:
                    logger.info("[FALLBACK_MANAGER] Recovery successful")
                    break

                # Wait before next attempt
                await asyncio.sleep(min(30.0, 5.0 * self.service_status.recovery_attempts))

            if self.service_status.level != ServiceLevel.FULL_SERVICE:
                logger.error(
                    f"[FALLBACK_MANAGER] Recovery failed after {self.service_status.recovery_attempts} attempts"
                )
                self.stats.failed_recoveries += 1

        except asyncio.CancelledError:
            logger.info("[FALLBACK_MANAGER] Recovery process cancelled")
        except Exception as e:
            logger.error(f"[FALLBACK_MANAGER] Recovery process error: {e}")
        finally:
            self._is_recovering = False

    async def _attempt_websocket_recovery(self) -> None:
        """Attempt to recover WebSocket connection."""
        if not self.websocket_manager:
            return

        try:
            logger.info("[FALLBACK_MANAGER] Attempting WebSocket recovery")

            # Try to reconnect if method exists
            if hasattr(self.websocket_manager, 'reconnect'):
                await self.websocket_manager.reconnect()
            elif hasattr(self.websocket_manager, 'restart'):
                await self.websocket_manager.restart()

            # Give it time to establish connection
            await asyncio.sleep(5.0)

        except Exception as e:
            logger.error(f"[FALLBACK_MANAGER] WebSocket recovery failed: {e}")

    async def _attempt_rest_recovery(self) -> None:
        """Attempt to recover REST API connectivity."""
        try:
            logger.info("[FALLBACK_MANAGER] Attempting REST recovery")

            # Test basic connectivity
            test_result = await self.strategic_client.emergency_system_status()

            if test_result:
                logger.info("[FALLBACK_MANAGER] REST recovery successful")

        except Exception as e:
            logger.error(f"[FALLBACK_MANAGER] REST recovery failed: {e}")

    # ====== CALLBACKS AND NOTIFICATIONS ======

    def add_service_level_callback(self, callback: Callable) -> None:
        """
        Add callback for service level changes.

        Args:
            callback: Function to call on service level change
        """
        self._service_level_callbacks.append(callback)
        logger.debug("[FALLBACK_MANAGER] Added service level callback")

    def remove_service_level_callback(self, callback: Callable) -> None:
        """
        Remove service level callback.

        Args:
            callback: Function to remove
        """
        try:
            self._service_level_callbacks.remove(callback)
            logger.debug("[FALLBACK_MANAGER] Removed service level callback")
        except ValueError:
            pass

    # ====== STATUS AND MONITORING ======

    def get_service_status(self) -> dict[str, Any]:
        """Get current service status."""
        return {
            'service_level': self.service_status.level.value,
            'websocket_healthy': self.service_status.websocket_healthy,
            'rest_healthy': self.service_status.rest_healthy,
            'last_websocket_data': self.service_status.last_websocket_data,
            'last_rest_success': self.service_status.last_rest_success,
            'failure_reason': self.service_status.failure_reason,
            'recovery_attempts': self.service_status.recovery_attempts,
            'degradation_start': self.service_status.degradation_start,
            'is_recovering': self._is_recovering,
            'pending_operations': len(self._pending_operations)
        }

    def get_fallback_stats(self) -> dict[str, Any]:
        """Get fallback statistics."""
        return {
            'total_fallbacks': self.stats.total_fallbacks,
            'websocket_failures': self.stats.websocket_failures,
            'emergency_operations': self.stats.emergency_operations,
            'successful_recoveries': self.stats.successful_recoveries,
            'failed_recoveries': self.stats.failed_recoveries,
            'average_degradation_time': self.stats.average_degradation_time,
            'critical_operations_completed': self.stats.critical_operations_completed,
            'recovery_success_rate': (
                self.stats.successful_recoveries /
                max(1, self.stats.successful_recoveries + self.stats.failed_recoveries)
            )
        }

    async def health_check(self) -> dict[str, Any]:
        """
        Perform fallback manager health check.

        Returns:
            Health status
        """
        health = {
            'timestamp': time.time(),
            'status': 'healthy',
            'checks': {}
        }

        # Check service level
        if self.service_status.level == ServiceLevel.SERVICE_OUTAGE:
            health['status'] = 'critical'
            health['checks']['service_level'] = {
                'status': 'critical',
                'level': self.service_status.level.value
            }
        elif self.service_status.level in [ServiceLevel.DEGRADED_SERVICE, ServiceLevel.EMERGENCY_ONLY]:
            health['status'] = 'degraded'
            health['checks']['service_level'] = {
                'status': 'degraded',
                'level': self.service_status.level.value
            }
        else:
            health['checks']['service_level'] = {
                'status': 'healthy',
                'level': self.service_status.level.value
            }

        # Check recovery status
        if self._is_recovering:
            health['checks']['recovery'] = {
                'status': 'degraded',
                'attempts': self.service_status.recovery_attempts
            }
            if health['status'] == 'healthy':
                health['status'] = 'degraded'
        else:
            health['checks']['recovery'] = {
                'status': 'healthy',
                'attempts': self.service_status.recovery_attempts
            }

        # Check pending operations
        if len(self._pending_operations) > 10:
            health['checks']['pending_operations'] = {
                'status': 'degraded',
                'count': len(self._pending_operations)
            }
            if health['status'] == 'healthy':
                health['status'] = 'degraded'
        else:
            health['checks']['pending_operations'] = {
                'status': 'healthy',
                'count': len(self._pending_operations)
            }

        return health
