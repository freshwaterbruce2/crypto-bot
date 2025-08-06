"""
Production Monitor Integration with Trading Bot
==============================================

Integration layer that connects the production monitoring system
with the existing crypto trading bot architecture.

Features:
- Seamless integration with KrakenTradingBot
- Component monitoring setup
- Emergency shutdown integration
- Real-time metric collection from bot components
- Non-intrusive monitoring that doesn't affect trading performance
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .dashboard_server import DashboardServer
from .production_monitor import (
    AlertConfig,
    MetricThresholds,
    get_production_monitor,
)

logger = logging.getLogger(__name__)


class ProductionMonitorIntegration:
    """
    Integration layer for production monitoring with trading bot

    Provides seamless integration without modifying existing bot code,
    using composition and event-driven architecture.
    """

    def __init__(self, bot_instance, monitor_config: Optional[dict] = None):
        """
        Initialize monitoring integration

        Args:
            bot_instance: Instance of KrakenTradingBot
            monitor_config: Optional monitoring configuration
        """
        self.bot = bot_instance
        self.config = monitor_config or {}

        # Initialize production monitor
        project_root = Path(__file__).parent.parent.parent
        self.monitor = get_production_monitor(project_root)

        # Configure thresholds if provided
        if 'thresholds' in self.config:
            self.monitor.thresholds = MetricThresholds(**self.config['thresholds'])

        # Configure alerts if provided
        if 'alerts' in self.config:
            self.monitor.alert_config = AlertConfig(**self.config['alerts'])

        # Dashboard server
        self.dashboard_server: Optional[DashboardServer] = None
        self.dashboard_port = self.config.get('dashboard_port', 8000)

        # State
        self.monitoring_active = False
        self.integration_complete = False

        logger.info("Production monitor integration initialized")

    async def setup_integration(self):
        """Setup integration with bot components"""
        try:
            # Connect to bot components
            await self._connect_bot_components()

            # Setup emergency shutdown callback
            self._setup_emergency_shutdown()

            # Start monitoring
            await self.monitor.start_monitoring()

            # Start dashboard server if enabled
            if self.config.get('enable_dashboard', True):
                await self._start_dashboard_server()

            self.integration_complete = True
            self.monitoring_active = True

            logger.info("Production monitoring integration setup complete")

        except Exception as e:
            logger.error(f"Failed to setup monitoring integration: {e}")
            raise

    async def shutdown_integration(self):
        """Shutdown monitoring integration"""
        try:
            self.monitoring_active = False

            # Stop monitoring
            await self.monitor.stop_monitoring()

            # Stop dashboard server
            if self.dashboard_server:
                # Dashboard server shutdown would need to be implemented
                pass

            logger.info("Production monitoring integration shutdown complete")

        except Exception as e:
            logger.error(f"Error shutting down monitoring integration: {e}")

    async def _connect_bot_components(self):
        """Connect to bot components for monitoring"""
        try:
            # Connect to balance manager
            balance_manager = None
            if hasattr(self.bot, 'balance_manager'):
                balance_manager = self.bot.balance_manager
            elif hasattr(self.bot, 'balance_tracker'):
                balance_manager = self.bot.balance_tracker

            # Connect to WebSocket manager
            websocket_manager = None
            if hasattr(self.bot, 'websocket_manager'):
                websocket_manager = self.bot.websocket_manager
            elif hasattr(self.bot, 'ws_manager'):
                websocket_manager = self.bot.ws_manager

            # Connect to exchange client
            exchange_client = None
            if hasattr(self.bot, 'exchange'):
                exchange_client = self.bot.exchange
            elif hasattr(self.bot, 'exchange_client'):
                exchange_client = self.bot.exchange_client

            # Connect to nonce manager
            nonce_manager = None
            if hasattr(self.bot, 'nonce_manager'):
                nonce_manager = self.bot.nonce_manager
            elif hasattr(exchange_client, 'nonce_manager'):
                nonce_manager = exchange_client.nonce_manager

            # Set component references in monitor
            self.monitor.set_bot_components(
                balance_manager=balance_manager,
                websocket_manager=websocket_manager,
                exchange_client=exchange_client,
                nonce_manager=nonce_manager
            )

            logger.info("Bot components connected to monitoring system")

        except Exception as e:
            logger.error(f"Error connecting bot components: {e}")
            raise

    def _setup_emergency_shutdown(self):
        """Setup emergency shutdown callback"""
        async def emergency_shutdown():
            """Emergency shutdown procedure"""
            try:
                logger.critical("EMERGENCY SHUTDOWN INITIATED BY PRODUCTION MONITOR")

                # Stop trading loops
                if hasattr(self.bot, 'stop_trading'):
                    await self.bot.stop_trading()
                elif hasattr(self.bot, 'stop'):
                    await self.bot.stop()

                # Cancel all open orders if method exists
                if hasattr(self.bot, 'cancel_all_orders'):
                    await self.bot.cancel_all_orders()

                # Liquidate positions if method exists
                if hasattr(self.bot, 'liquidate_all_positions'):
                    await self.bot.liquidate_all_positions()

                # Set emergency mode flag
                if hasattr(self.bot, 'emergency_mode'):
                    self.bot.emergency_mode = True

                logger.critical("Emergency shutdown completed")

            except Exception as e:
                logger.error(f"Emergency shutdown failed: {e}")
                raise

        self.monitor.set_emergency_shutdown_callback(emergency_shutdown)

    async def _start_dashboard_server(self):
        """Start dashboard server in background"""
        try:
            self.dashboard_server = DashboardServer(self.monitor, self.dashboard_port)

            # Start server in background task
            asyncio.create_task(self.dashboard_server.start())

            logger.info(f"Dashboard server started on port {self.dashboard_port}")
            logger.info(f"Dashboard available at: http://localhost:{self.dashboard_port}")

        except Exception as e:
            logger.error(f"Failed to start dashboard server: {e}")
            # Don't raise - dashboard is optional

    def get_monitoring_status(self) -> dict:
        """Get current monitoring status"""
        return {
            'integration_complete': self.integration_complete,
            'monitoring_active': self.monitoring_active,
            'dashboard_enabled': self.dashboard_server is not None,
            'dashboard_port': self.dashboard_port,
            'system_status': self.monitor.get_system_status() if self.monitoring_active else None,
            'current_metrics': self.monitor.get_current_metrics() if self.monitoring_active else None
        }


def add_monitoring_to_bot(bot_instance, config: Optional[dict] = None) -> ProductionMonitorIntegration:
    """
    Add production monitoring to an existing bot instance

    Args:
        bot_instance: KrakenTradingBot instance
        config: Optional monitoring configuration

    Returns:
        ProductionMonitorIntegration instance

    Example:
        >>> bot = KrakenTradingBot()
        >>> monitoring = add_monitoring_to_bot(bot, {
        ...     'enable_dashboard': True,
        ...     'dashboard_port': 8000,
        ...     'thresholds': {
        ...         'memory_usage_mb': 400.0,
        ...         'trading_success_rate_percent': 90.0
        ...     }
        ... })
        >>> await monitoring.setup_integration()
    """
    integration = ProductionMonitorIntegration(bot_instance, config)
    return integration


class MonitoringMixin:
    """
    Mixin class to add monitoring capabilities to trading bot

    Can be mixed into KrakenTradingBot class for built-in monitoring.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.production_monitor: Optional[ProductionMonitorIntegration] = None
        self.monitoring_config = kwargs.get('monitoring_config', {})

    async def enable_production_monitoring(self, config: Optional[dict] = None):
        """Enable production monitoring for this bot instance"""
        if self.production_monitor:
            logger.warning("Production monitoring already enabled")
            return

        monitoring_config = config or self.monitoring_config
        self.production_monitor = add_monitoring_to_bot(self, monitoring_config)
        await self.production_monitor.setup_integration()

        logger.info("Production monitoring enabled for bot")

    async def disable_production_monitoring(self):
        """Disable production monitoring"""
        if not self.production_monitor:
            return

        await self.production_monitor.shutdown_integration()
        self.production_monitor = None

        logger.info("Production monitoring disabled for bot")

    def get_monitoring_status(self) -> Optional[dict]:
        """Get monitoring status"""
        if not self.production_monitor:
            return None

        return self.production_monitor.get_monitoring_status()


# Enhanced bot class with built-in monitoring
class MonitoredKrakenTradingBot:
    """
    Enhanced KrakenTradingBot with built-in production monitoring

    This is a wrapper that adds monitoring capabilities to any existing bot.
    """

    def __init__(self, bot_instance, monitoring_config: Optional[dict] = None):
        """
        Initialize monitored bot wrapper

        Args:
            bot_instance: Existing KrakenTradingBot instance
            monitoring_config: Monitoring configuration
        """
        self.bot = bot_instance
        self.monitoring = ProductionMonitorIntegration(bot_instance, monitoring_config)

        # Proxy all bot methods and attributes
        self._proxy_bot_interface()

    def _proxy_bot_interface(self):
        """Proxy all bot methods and attributes to maintain compatibility"""
        # Get all public attributes and methods from bot
        for attr_name in dir(self.bot):
            if not attr_name.startswith('_'):
                attr = getattr(self.bot, attr_name)
                if not hasattr(self, attr_name):
                    setattr(self, attr_name, attr)

    async def start_with_monitoring(self):
        """Start bot with production monitoring enabled"""
        # Setup monitoring first
        await self.monitoring.setup_integration()

        # Start bot
        if hasattr(self.bot, 'start'):
            await self.bot.start()
        elif hasattr(self.bot, 'run'):
            await self.bot.run()

        logger.info("Monitored bot started successfully")

    async def stop_with_monitoring(self):
        """Stop bot and monitoring"""
        # Stop bot first
        if hasattr(self.bot, 'stop'):
            await self.bot.stop()

        # Shutdown monitoring
        await self.monitoring.shutdown_integration()

        logger.info("Monitored bot stopped successfully")

    def get_monitoring_dashboard_url(self) -> Optional[str]:
        """Get dashboard URL if available"""
        if self.monitoring.dashboard_server:
            return f"http://localhost:{self.monitoring.dashboard_port}"
        return None


# Example integration patterns
class MonitoringBootstrap:
    """Bootstrap class for easy monitoring setup"""

    @staticmethod
    async def create_monitored_bot(bot_class, bot_config: dict, monitoring_config: dict):
        """
        Create a bot instance with monitoring pre-configured

        Args:
            bot_class: KrakenTradingBot class
            bot_config: Bot configuration
            monitoring_config: Monitoring configuration

        Returns:
            MonitoredKrakenTradingBot instance
        """
        # Create bot instance
        bot = bot_class(bot_config)

        # Wrap with monitoring
        monitored_bot = MonitoredKrakenTradingBot(bot, monitoring_config)

        return monitored_bot

    @staticmethod
    def get_default_monitoring_config() -> dict:
        """Get default monitoring configuration"""
        return {
            'enable_dashboard': True,
            'dashboard_port': 8000,
            'thresholds': {
                'memory_usage_mb': 500.0,
                'log_file_size_mb': 8.0,
                'nonce_generation_rate': 1000.0,
                'websocket_reconnects_per_hour': 5,
                'api_error_rate_percent': 0.1,
                'trading_success_rate_percent': 85.0,
                'daily_pnl_loss_limit': -50.0,
                'balance_manager_response_time': 2.0,
                'websocket_latency_ms': 1000.0,
                'trade_execution_time_ms': 5000.0
            },
            'alerts': {
                'enabled': True,
                'console_alerts': True,
                'log_alerts': True,
                'email_notifications': False,
                'webhook_notifications': False
            }
        }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Example 1: Add monitoring to existing bot
        # from src.core.bot import KrakenTradingBot
        # bot = KrakenTradingBot()
        # monitoring = add_monitoring_to_bot(bot)
        # await monitoring.setup_integration()

        # Example 2: Use monitored bot wrapper
        # monitored_bot = MonitoredKrakenTradingBot(bot)
        # await monitored_bot.start_with_monitoring()

        print("Production monitoring integration examples")
        print("See docstrings for usage patterns")

    asyncio.run(main())
