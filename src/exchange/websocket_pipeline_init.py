"""
WebSocket Pipeline Initialization
================================

Initialization script that sets up the complete unified WebSocket V2 data pipeline
with all components, monitoring, and integration layers. Provides a simple interface
to initialize the entire pipeline system.

Features:
- Automatic pipeline setup and configuration
- Component discovery and registration
- Performance monitoring initialization
- Health check setup
- Error recovery mechanisms
- Configuration validation
- Integration testing
"""

import asyncio
import logging
from typing import Any, Optional

from .unified_websocket_data_pipeline import (
    MessageQueueConfig,
    PerformanceConfig,
    UnifiedWebSocketDataPipeline,
)
from .websocket_pipeline_integration import WebSocketPipelineIntegrator
from .websocket_pipeline_monitor import AlertConfig, WebSocketPipelineMonitor

logger = logging.getLogger(__name__)


class WebSocketPipelineInitializer:
    """
    Complete WebSocket pipeline initialization and management system

    Handles setup, configuration, monitoring, and lifecycle management
    of the unified WebSocket V2 data pipeline.
    """

    def __init__(self, websocket_manager, bot_instance=None):
        """
        Initialize the pipeline system

        Args:
            websocket_manager: WebSocket V2 manager instance
            bot_instance: Bot instance for component discovery
        """
        self.websocket_manager = websocket_manager
        self.bot_instance = bot_instance

        # Pipeline components
        self.integrator: Optional[WebSocketPipelineIntegrator] = None
        self.monitor: Optional[WebSocketPipelineMonitor] = None

        # System state
        self._initialized = False
        self._running = False

        logger.info("[INIT] WebSocket pipeline initializer created")

    async def initialize_complete_pipeline(self,
                                         queue_config: Optional[MessageQueueConfig] = None,
                                         performance_config: Optional[PerformanceConfig] = None,
                                         alert_config: Optional[AlertConfig] = None,
                                         enable_monitoring: bool = True) -> bool:
        """
        Initialize the complete WebSocket pipeline system

        Args:
            queue_config: Message queue configuration
            performance_config: Performance monitoring configuration
            alert_config: Alert configuration
            enable_monitoring: Whether to enable performance monitoring

        Returns:
            True if initialization successful
        """
        try:
            logger.info("[INIT] Initializing complete WebSocket pipeline system...")

            # Validate prerequisites
            if not await self._validate_prerequisites():
                return False

            # Setup integrator with pipeline
            self.integrator = WebSocketPipelineIntegrator(
                self.websocket_manager,
                self.bot_instance
            )

            # Override pipeline configuration if provided
            if queue_config or performance_config:
                self.integrator.pipeline = UnifiedWebSocketDataPipeline(
                    websocket_manager=self.websocket_manager,
                    queue_config=queue_config,
                    performance_config=performance_config
                )

            # Integrate with bot
            success = await self.integrator.integrate_with_bot()
            if not success:
                logger.error("[INIT] Failed to integrate pipeline with bot")
                return False

            # Setup monitoring if enabled
            if enable_monitoring:
                self.monitor = WebSocketPipelineMonitor(
                    self.integrator.pipeline,
                    alert_config
                )
                await self.monitor.start_monitoring()
                logger.info("[INIT] Performance monitoring enabled")

            # Run integration tests
            if not await self._run_integration_tests():
                logger.warning("[INIT] Integration tests failed, but continuing...")

            self._initialized = True
            self._running = True

            logger.info("[INIT] Complete WebSocket pipeline system initialized successfully")

            # Log system status
            await self._log_system_status()

            return True

        except Exception as e:
            logger.error(f"[INIT] Failed to initialize pipeline system: {e}")
            await self._cleanup_partial_initialization()
            return False

    async def initialize_basic_pipeline(self) -> bool:
        """
        Initialize basic pipeline without monitoring (lightweight setup)

        Returns:
            True if initialization successful
        """
        return await self.initialize_complete_pipeline(
            enable_monitoring=False
        )

    async def initialize_high_performance_pipeline(self) -> bool:
        """
        Initialize high-performance pipeline with optimized settings

        Returns:
            True if initialization successful
        """
        # High-performance configurations
        queue_config = MessageQueueConfig(
            max_size=5000,  # Large buffers
            timeout_seconds=0.1,  # Fast processing
            priority_multiplier=2.0,  # More processors for high priority
            enable_deduplication=True,
            dedup_window_seconds=0.02  # Very short dedup window
        )

        performance_config = PerformanceConfig(
            enable_metrics=True,
            metrics_interval_seconds=30.0,  # Frequent monitoring
            max_processing_time_ms=5.0,  # Strict latency requirements
            enable_latency_tracking=True,
            memory_usage_threshold_mb=1000.0  # Higher memory limit
        )

        alert_config = AlertConfig(
            max_latency_ms=20.0,  # Strict latency alerts
            max_memory_mb=1000.0,
            max_error_rate_percent=1.0,  # Low error tolerance
            max_drop_rate_percent=0.5,  # Very low drop tolerance
            min_throughput_msgs_per_sec=10.0,  # High throughput expectation
            queue_size_warning_threshold=3000,
            queue_size_critical_threshold=4000
        )

        return await self.initialize_complete_pipeline(
            queue_config=queue_config,
            performance_config=performance_config,
            alert_config=alert_config,
            enable_monitoring=True
        )

    async def shutdown(self):
        """Shutdown the complete pipeline system"""
        if not self._initialized:
            return

        logger.info("[INIT] Shutting down WebSocket pipeline system...")

        try:
            # Stop monitoring
            if self.monitor:
                await self.monitor.stop_monitoring()
                self.monitor = None

            # Shutdown integrator
            if self.integrator:
                await self.integrator.shutdown()
                self.integrator = None

            self._running = False
            self._initialized = False

            logger.info("[INIT] Pipeline system shutdown complete")

        except Exception as e:
            logger.error(f"[INIT] Error during shutdown: {e}")

    async def _validate_prerequisites(self) -> bool:
        """Validate that prerequisites are met"""
        try:
            # Check WebSocket manager
            if not self.websocket_manager:
                logger.error("[INIT] No WebSocket manager provided")
                return False

            if not hasattr(self.websocket_manager, 'is_connected'):
                logger.error("[INIT] WebSocket manager missing connection status")
                return False

            # Check bot instance
            if not self.bot_instance:
                logger.warning("[INIT] No bot instance provided - limited component discovery")

            # Check WebSocket connection
            if hasattr(self.websocket_manager, 'is_connected'):
                if not self.websocket_manager.is_connected:
                    logger.warning("[INIT] WebSocket not connected - pipeline will start when connected")

            logger.info("[INIT] Prerequisites validation passed")
            return True

        except Exception as e:
            logger.error(f"[INIT] Error validating prerequisites: {e}")
            return False

    async def _run_integration_tests(self) -> bool:
        """Run basic integration tests"""
        try:
            logger.info("[INIT] Running integration tests...")

            # Test 1: Pipeline is running
            if not self.integrator or not self.integrator.pipeline._running:
                logger.error("[INIT] Test failed: Pipeline not running")
                return False

            # Test 2: Components are registered
            integration_status = self.integrator.get_integration_status()
            if integration_status['components_discovered'] == 0:
                logger.warning("[INIT] Test warning: No components discovered")

            # Test 3: Queue system is working
            pipeline_stats = self.integrator.pipeline.get_pipeline_stats()
            if not pipeline_stats.get('running'):
                logger.error("[INIT] Test failed: Pipeline stats indicate not running")
                return False

            # Test 4: Try processing a test message
            test_message = {
                'channel': 'heartbeat',
                'data': [{'type': 'test', 'timestamp': 'test'}],
                'timestamp': 'test'
            }

            success = await self.integrator.pipeline.process_raw_message(test_message)
            if not success:
                logger.warning("[INIT] Test warning: Failed to process test message")

            logger.info("[INIT] Integration tests completed successfully")
            return True

        except Exception as e:
            logger.error(f"[INIT] Integration tests failed: {e}")
            return False

    async def _log_system_status(self):
        """Log comprehensive system status"""
        try:
            if not self.integrator:
                return

            # Get integration status
            integration_status = self.integrator.get_integration_status()

            logger.info(
                f"[INIT] System Status - "
                f"Integrated: {integration_status['integrated']}, "
                f"Components: {integration_status['components_discovered']}, "
                f"Pipeline: {integration_status['pipeline_running']}, "
                f"WebSocket: {integration_status['websocket_connected']}"
            )

            # Log component status
            for name, status in integration_status.get('components', {}).items():
                logger.info(f"[INIT] Component {name}: {'✓' if status['alive'] else '✗'} ({status['type']})")

            # Log pipeline stats
            pipeline_stats = integration_status.get('pipeline_stats', {})
            if pipeline_stats:
                logger.info(
                    f"[INIT] Pipeline Stats - "
                    f"Processors: {pipeline_stats.get('processor_count', 0)}, "
                    f"Registered: {pipeline_stats.get('registered_components', 0)}, "
                    f"Queue Sizes: {pipeline_stats.get('queue_sizes', {})}"
                )

            # Log monitoring status
            if self.monitor:
                logger.info("[INIT] Performance monitoring: ✓ Active")
            else:
                logger.info("[INIT] Performance monitoring: ✗ Disabled")

        except Exception as e:
            logger.error(f"[INIT] Error logging system status: {e}")

    async def _cleanup_partial_initialization(self):
        """Clean up partial initialization on failure"""
        try:
            logger.info("[INIT] Cleaning up partial initialization...")

            if self.monitor:
                try:
                    await self.monitor.stop_monitoring()
                except Exception as e:
                    logger.error(f"[INIT] Error stopping monitor during cleanup: {e}")
                self.monitor = None

            if self.integrator:
                try:
                    await self.integrator.shutdown()
                except Exception as e:
                    logger.error(f"[INIT] Error shutting down integrator during cleanup: {e}")
                self.integrator = None

            self._initialized = False
            self._running = False

        except Exception as e:
            logger.error(f"[INIT] Error during cleanup: {e}")

    def get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            'initialized': self._initialized,
            'running': self._running,
            'integrator_available': self.integrator is not None,
            'monitor_available': self.monitor is not None
        }

        if self.integrator:
            status['integration_status'] = self.integrator.get_integration_status()

        if self.monitor:
            status['performance_report'] = self.monitor.get_performance_report()

        return status

    def is_healthy(self) -> bool:
        """Check if the pipeline system is healthy"""
        if not self._initialized or not self._running:
            return False

        if not self.integrator:
            return False

        integration_status = self.integrator.get_integration_status()
        if not integration_status.get('integrated') or not integration_status.get('pipeline_running'):
            return False

        # Check for any critical alerts if monitoring is enabled
        if self.monitor:
            performance_report = self.monitor.get_performance_report()
            recent_alerts = performance_report.get('recent_alerts', [])
            critical_alerts = [a for a in recent_alerts if a.get('level') == 'CRITICAL']
            if critical_alerts:
                return False

        return True

    async def restart_pipeline(self) -> bool:
        """Restart the pipeline system"""
        logger.info("[INIT] Restarting pipeline system...")

        # Store current configuration
        queue_config = None
        performance_config = None
        alert_config = None
        enable_monitoring = self.monitor is not None

        if self.integrator and self.integrator.pipeline:
            queue_config = self.integrator.pipeline.queue_config
            performance_config = self.integrator.pipeline.performance_config

        if self.monitor:
            alert_config = self.monitor.alert_config

        # Shutdown current system
        await self.shutdown()

        # Wait a moment
        await asyncio.sleep(1.0)

        # Reinitialize
        return await self.initialize_complete_pipeline(
            queue_config=queue_config,
            performance_config=performance_config,
            alert_config=alert_config,
            enable_monitoring=enable_monitoring
        )


# Convenience functions for easy setup
async def initialize_websocket_pipeline(websocket_manager, bot_instance,
                                      performance_mode: str = "balanced") -> Optional[WebSocketPipelineInitializer]:
    """
    Convenience function to initialize WebSocket pipeline

    Args:
        websocket_manager: WebSocket V2 manager
        bot_instance: Bot instance
        performance_mode: "basic", "balanced", or "high_performance"

    Returns:
        WebSocketPipelineInitializer if successful, None otherwise
    """
    try:
        initializer = WebSocketPipelineInitializer(websocket_manager, bot_instance)

        if performance_mode == "basic":
            success = await initializer.initialize_basic_pipeline()
        elif performance_mode == "high_performance":
            success = await initializer.initialize_high_performance_pipeline()
        else:  # balanced (default)
            success = await initializer.initialize_complete_pipeline()

        if success:
            logger.info(f"[INIT] WebSocket pipeline initialized in {performance_mode} mode")
            return initializer
        else:
            logger.error(f"[INIT] Failed to initialize pipeline in {performance_mode} mode")
            return None

    except Exception as e:
        logger.error(f"[INIT] Error initializing pipeline: {e}")
        return None


async def quick_setup_pipeline(websocket_manager, bot_instance) -> tuple[bool, Optional[WebSocketPipelineInitializer]]:
    """
    Quick setup function with error handling

    Args:
        websocket_manager: WebSocket V2 manager
        bot_instance: Bot instance

    Returns:
        Tuple of (success, initializer)
    """
    try:
        initializer = await initialize_websocket_pipeline(
            websocket_manager,
            bot_instance,
            "balanced"
        )

        if initializer and initializer.is_healthy():
            return True, initializer
        else:
            return False, initializer

    except Exception as e:
        logger.error(f"[INIT] Quick setup failed: {e}")
        return False, None
