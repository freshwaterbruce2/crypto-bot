"""
Startup and Shutdown Sequence Manager

Manages ordered initialization and graceful shutdown of all systems.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class StartupPhase(Enum):
    """Startup phases - updated for WebSocket-first architecture"""
    CORE = "core"                    # Core services (config, logging)
    INFRASTRUCTURE = "infra"          # Infrastructure (database, cache)
    WEBSOCKET_AUTH = "websocket_auth" # WebSocket authentication (before REST)
    WEBSOCKET_INIT = "websocket_init" # WebSocket connection initialization
    AUTHENTICATION = "auth"           # REST authentication and credentials
    NETWORKING = "network"            # Network connections (REST fallback)
    SERVICES = "services"             # Business services
    STRATEGIES = "strategies"         # Trading strategies
    MONITORING = "monitoring"         # Monitoring and health checks
    READY = "ready"                  # System ready


class ShutdownPriority(Enum):
    """Shutdown priorities (higher = shutdown first)"""
    MONITORING = 10
    STRATEGIES = 20
    SERVICES = 30
    NETWORKING = 40
    AUTHENTICATION = 50
    INFRASTRUCTURE = 60
    CORE = 70


@dataclass
class StartupStep:
    """Individual startup step"""
    name: str
    phase: StartupPhase
    handler: Callable
    dependencies: Set[str] = field(default_factory=set)
    timeout: int = 30
    retry_count: int = 3
    critical: bool = True
    rollback_handler: Optional[Callable] = None


@dataclass
class StartupResult:
    """Result of a startup step"""
    step_name: str
    success: bool
    duration: timedelta
    error: Optional[Exception] = None
    retry_count: int = 0


class StartupSequence:
    """Manages system startup and shutdown sequences"""

    def __init__(self):
        self.steps: Dict[str, StartupStep] = {}
        self.completed_steps: Set[str] = set()
        self.results: List[StartupResult] = []
        self.shutdown_handlers: List[tuple[Callable, ShutdownPriority]] = []
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()

        # Register signal handlers
        self._register_signal_handlers()

    def _register_signal_handlers(self):
        """Register system signal handlers"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        logger.info(f"Received signal {signum}, initiating shutdown")
        asyncio.create_task(self.shutdown())

    def register_step(
        self,
        name: str,
        phase: StartupPhase,
        handler: Callable,
        dependencies: List[str] = None,
        timeout: int = 30,
        retry_count: int = 3,
        critical: bool = True,
        rollback_handler: Callable = None
    ):
        """Register a startup step"""
        step = StartupStep(
            name=name,
            phase=phase,
            handler=handler,
            dependencies=set(dependencies or []),
            timeout=timeout,
            retry_count=retry_count,
            critical=critical,
            rollback_handler=rollback_handler
        )

        self.steps[name] = step
        logger.info(f"Registered startup step: {name} (phase: {phase.value})")

    def register_shutdown_handler(self, handler: Callable, priority: ShutdownPriority):
        """Register a shutdown handler"""
        self.shutdown_handlers.append((handler, priority))

    async def startup(self) -> bool:
        """Execute startup sequence"""
        async with self._lock:
            if self.is_running:
                logger.warning("System already running")
                return True

            logger.info("Starting system initialization sequence")
            start_time = datetime.now()

            try:
                # Execute phases in order
                executed_phases = set()
                for phase in StartupPhase:
                    if phase == StartupPhase.READY:
                        continue

                    # Get steps for this phase
                    phase_steps = [
                        step for step in self.steps.values()
                        if step.phase == phase
                    ]

                    # Skip phases with no steps
                    if not phase_steps:
                        logger.debug(f"Skipping phase {phase.value} (no steps registered)")
                        continue

                    logger.info(f"Starting phase: {phase.value} ({len(phase_steps)} steps)")

                    # Execute steps respecting dependencies
                    if not await self._execute_phase(phase_steps):
                        logger.error(f"Phase {phase.value} failed")
                        await self._rollback()
                        return False

                    executed_phases.add(phase)
                    logger.info(f"Phase {phase.value} completed successfully")

                logger.info(f"Executed {len(executed_phases)} phases successfully")

                self.is_running = True

                duration = datetime.now() - start_time
                logger.info(f"System startup completed in {duration.total_seconds():.2f} seconds")

                # Log startup summary
                self._log_startup_summary()

                return True

            except Exception as e:
                logger.error(f"Startup sequence failed: {e}")
                await self._rollback()
                return False

    async def _execute_phase(self, steps: List[StartupStep]) -> bool:
        """Execute steps in a phase"""
        # Sort steps by dependencies
        sorted_steps = self._topological_sort(steps)

        for step in sorted_steps:
            # Check dependencies
            if not all(dep in self.completed_steps for dep in step.dependencies):
                logger.error(f"Dependencies not met for step: {step.name}")
                return False

            # Execute step with retries
            result = await self._execute_step(step)
            self.results.append(result)

            if not result.success:
                if step.critical:
                    logger.error(f"Critical step failed: {step.name}")
                    return False
                else:
                    logger.warning(f"Non-critical step failed: {step.name}")

        return True

    async def _execute_step(self, step: StartupStep) -> StartupResult:
        """Execute a single startup step"""
        logger.info(f"Executing step: {step.name}")
        start_time = datetime.now()

        for attempt in range(step.retry_count):
            try:
                # Execute with timeout
                if asyncio.iscoroutinefunction(step.handler):
                    await asyncio.wait_for(step.handler(), timeout=step.timeout)
                else:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, step.handler),
                        timeout=step.timeout
                    )

                self.completed_steps.add(step.name)
                duration = datetime.now() - start_time

                logger.info(f"Step {step.name} completed in {duration.total_seconds():.2f}s")

                return StartupResult(
                    step_name=step.name,
                    success=True,
                    duration=duration,
                    retry_count=attempt
                )

            except asyncio.TimeoutError:
                logger.error(f"Step {step.name} timed out (attempt {attempt + 1}/{step.retry_count})")

            except Exception as e:
                logger.error(f"Step {step.name} failed (attempt {attempt + 1}/{step.retry_count}): {e}")

                if attempt == step.retry_count - 1:
                    return StartupResult(
                        step_name=step.name,
                        success=False,
                        duration=datetime.now() - start_time,
                        error=e,
                        retry_count=attempt + 1
                    )

            # Wait before retry
            if attempt < step.retry_count - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return StartupResult(
            step_name=step.name,
            success=False,
            duration=datetime.now() - start_time,
            retry_count=step.retry_count
        )

    def _topological_sort(self, steps: List[StartupStep]) -> List[StartupStep]:
        """Sort steps by dependencies"""
        # Create dependency graph, filtering out already completed dependencies
        graph = {}
        in_degree = {}

        for step in steps:
            # Only count dependencies that haven't been completed yet
            remaining_deps = step.dependencies - self.completed_steps
            graph[step.name] = remaining_deps
            in_degree[step.name] = len(remaining_deps)

        # Find steps with no remaining dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            name = queue.pop(0)
            step = next(s for s in steps if s.name == name)
            result.append(step)

            # Update dependencies - reduce in-degree for steps that depend on this step
            for other_name, deps in graph.items():
                if name in deps:
                    in_degree[other_name] -= 1
                    if in_degree[other_name] == 0:
                        queue.append(other_name)

        return result

    async def _rollback(self):
        """Rollback completed steps"""
        logger.info("Initiating rollback sequence")

        # Rollback in reverse order
        for step_name in reversed(list(self.completed_steps)):
            step = self.steps.get(step_name)
            if step and step.rollback_handler:
                try:
                    logger.info(f"Rolling back step: {step_name}")

                    if asyncio.iscoroutinefunction(step.rollback_handler):
                        await step.rollback_handler()
                    else:
                        await asyncio.get_event_loop().run_in_executor(
                            None, step.rollback_handler
                        )

                except Exception as e:
                    logger.error(f"Rollback failed for {step_name}: {e}")

        self.completed_steps.clear()

    async def shutdown(self):
        """Execute shutdown sequence"""
        async with self._lock:
            if not self.is_running:
                logger.warning("System not running")
                return

            logger.info("Starting system shutdown sequence")
            start_time = datetime.now()

            # Set shutdown event
            self.shutdown_event.set()

            # Sort handlers by priority
            sorted_handlers = sorted(
                self.shutdown_handlers,
                key=lambda x: x[1].value,
                reverse=True
            )

            # Execute shutdown handlers
            for handler, priority in sorted_handlers:
                try:
                    logger.info(f"Executing shutdown handler (priority: {priority.name})")

                    if asyncio.iscoroutinefunction(handler):
                        await asyncio.wait_for(handler(), timeout=30)
                    else:
                        await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(None, handler),
                            timeout=30
                        )

                except asyncio.TimeoutError:
                    logger.error("Shutdown handler timed out")
                except Exception as e:
                    logger.error(f"Shutdown handler failed: {e}")

            self.is_running = False
            self.completed_steps.clear()

            duration = datetime.now() - start_time
            logger.info(f"System shutdown completed in {duration.total_seconds():.2f} seconds")

    def _log_startup_summary(self):
        """Log startup summary"""
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        total_time = sum(r.duration.total_seconds() for r in self.results)

        logger.info(f"Startup Summary: {successful} successful, {failed} failed, "
                   f"Total time: {total_time:.2f}s")

        # Log failed steps
        for result in self.results:
            if not result.success:
                logger.error(f"Failed step: {result.step_name} - {result.error}")

    def get_startup_report(self) -> Dict[str, Any]:
        """Get detailed startup report"""
        return {
            'is_running': self.is_running,
            'completed_steps': list(self.completed_steps),
            'total_steps': len(self.steps),
            'results': [
                {
                    'step': r.step_name,
                    'success': r.success,
                    'duration': r.duration.total_seconds(),
                    'retry_count': r.retry_count,
                    'error': str(r.error) if r.error else None
                }
                for r in self.results
            ],
            'phases': {
                phase.value: {
                    'steps': [
                        s.name for s in self.steps.values()
                        if s.phase == phase
                    ]
                }
                for phase in StartupPhase
            }
        }

    @asynccontextmanager
    async def managed_startup(self):
        """Context manager for managed startup/shutdown"""
        try:
            success = await self.startup()
            if not success:
                raise RuntimeError("Startup sequence failed")
            yield
        finally:
            await self.shutdown()

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get startup sequence diagnostics"""
        return {
            'is_running': self.is_running,
            'registered_steps': len(self.steps),
            'completed_steps': len(self.completed_steps),
            'shutdown_handlers': len(self.shutdown_handlers),
            'startup_report': self.get_startup_report() if self.results else None
        }

    def register_websocket_first_steps(self):
        """Register WebSocket-first startup steps to bypass REST authentication issues"""
        logger.info("Registering WebSocket-first startup sequence")

        # WebSocket authentication step (minimal REST call for token)
        self.register_step(
            name='websocket_token_generation',
            phase=StartupPhase.WEBSOCKET_AUTH,
            handler=self._generate_websocket_token,
            dependencies=[],
            timeout=30,
            retry_count=3,
            critical=True
        )

        # WebSocket connection initialization
        self.register_step(
            name='websocket_connection_init',
            phase=StartupPhase.WEBSOCKET_INIT,
            handler=self._initialize_websocket_connection,
            dependencies=['websocket_token_generation'],
            timeout=45,
            retry_count=3,
            critical=True
        )

        # WebSocket balance stream initialization
        self.register_step(
            name='websocket_balance_stream',
            phase=StartupPhase.WEBSOCKET_INIT,
            handler=self._initialize_balance_stream,
            dependencies=['websocket_connection_init'],
            timeout=30,
            retry_count=2,
            critical=True
        )

        # WebSocket data pipeline initialization
        self.register_step(
            name='websocket_data_pipeline',
            phase=StartupPhase.WEBSOCKET_INIT,
            handler=self._initialize_data_pipeline,
            dependencies=['websocket_balance_stream'],
            timeout=30,
            retry_count=2,
            critical=False
        )

    async def _generate_websocket_token(self):
        """Generate WebSocket authentication token with minimal REST API usage"""
        logger.info("Generating WebSocket authentication token")
        # Implementation will be provided by the orchestrator
        # For now, return success to allow startup to continue
        logger.info("WebSocket token generation completed (placeholder)")
        return True

    async def _initialize_websocket_connection(self):
        """Initialize WebSocket connection with authentication"""
        logger.info("Initializing WebSocket connection")
        # Implementation will be provided by the orchestrator
        # For now, return success to allow startup to continue
        logger.info("WebSocket connection initialization completed (placeholder)")
        return True

    async def _initialize_balance_stream(self):
        """Initialize WebSocket balance stream"""
        logger.info("Initializing WebSocket balance stream")
        # Implementation will be provided by the orchestrator
        # For now, return success to allow startup to continue
        logger.info("WebSocket balance stream initialization completed (placeholder)")
        return True

    async def _initialize_data_pipeline(self):
        """Initialize unified data pipeline for WebSocket streams"""
        logger.info("Initializing WebSocket data pipeline")
        # Implementation will be provided by the orchestrator
        # For now, return success to allow startup to continue
        logger.info("WebSocket data pipeline initialization completed (placeholder)")
        return True
