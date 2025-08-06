#!/usr/bin/env python3
"""
Launch Crypto Trading Bot with Production Monitoring
==================================================

Main launcher script that starts the crypto trading bot with comprehensive
production monitoring enabled. Provides real-time dashboard, health checks,
and emergency controls.

Usage:
    python launch_with_monitoring.py [--config CONFIG] [--dashboard-port PORT] [--no-dashboard]

Features:
- Full production monitoring with 5-minute health checks
- Real-time web dashboard on http://localhost:8000
- Configurable alert thresholds
- Emergency shutdown capabilities
- Integration with existing bot architecture
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import load_config
from src.core.bot import KrakenTradingBot
from src.monitoring.bot_integration import add_monitoring_to_bot
from src.monitoring.monitoring_config import get_config_by_name, setup_monitoring_from_config

logger = logging.getLogger(__name__)


class MonitoredBotLauncher:
    """Launch trading bot with production monitoring"""

    def __init__(self, args):
        self.args = args
        self.bot = None
        self.monitoring = None
        self.running = False

    async def start(self):
        """Start bot with monitoring"""
        try:
            logger.info("Starting Crypto Trading Bot with Production Monitoring...")

            # Load bot configuration
            bot_config = load_config()
            logger.info("Bot configuration loaded")

            # Load monitoring configuration
            monitoring_config = await self._load_monitoring_config()
            logger.info(f"Monitoring configuration loaded: {self.args.config or 'default'}")

            # Create bot instance
            self.bot = KrakenTradingBot(bot_config)
            logger.info("Bot instance created")

            # Setup monitoring integration
            self.monitoring = add_monitoring_to_bot(self.bot, monitoring_config)
            await self.monitoring.setup_integration()
            logger.info("Monitoring integration setup complete")

            # Display monitoring info
            self._display_monitoring_info()

            # Setup signal handlers
            self._setup_signal_handlers()

            # Start bot
            self.running = True
            logger.info("Starting trading bot...")

            # Start bot main loop
            if hasattr(self.bot, 'run'):
                await self.bot.run()
            elif hasattr(self.bot, 'start'):
                await self.bot.start()
                # Keep running
                while self.running:
                    await asyncio.sleep(1)
            else:
                logger.error("Bot does not have run() or start() method")
                return

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error starting monitored bot: {e}")
            raise
        finally:
            await self.shutdown()

    async def _load_monitoring_config(self):
        """Load monitoring configuration"""
        config_type = self.args.config or "default"

        # Check if it's a predefined config type
        if config_type in ['default', 'production', 'development', 'minimal']:
            config = get_config_by_name(config_type)
        else:
            # Try to load from file
            config_path = Path(config_type)
            if not config_path.exists():
                logger.warning(f"Config file {config_path} not found, using default")
                config = get_config_by_name('default')
            else:
                config = setup_monitoring_from_config(config_path)

        # Override dashboard port if specified
        if self.args.dashboard_port:
            config['dashboard']['port'] = self.args.dashboard_port

        # Disable dashboard if requested
        if self.args.no_dashboard:
            config['dashboard']['enabled'] = False

        return config

    def _display_monitoring_info(self):
        """Display monitoring information"""
        if not self.monitoring:
            return

        status = self.monitoring.get_monitoring_status()

        print("\n" + "="*60)
        print("🚀 CRYPTO TRADING BOT WITH PRODUCTION MONITORING")
        print("="*60)
        print(f"✅ Integration Complete: {status['integration_complete']}")
        print(f"📊 Monitoring Active: {status['monitoring_active']}")

        if status['dashboard_enabled']:
            dashboard_url = f"http://localhost:{status['dashboard_port']}"
            print(f"🌐 Dashboard Available: {dashboard_url}")
            print("📱 Mobile Friendly: Access from any device")
        else:
            print("🚫 Dashboard Disabled")

        print("\n📈 MONITORING FEATURES:")
        print("• Real-time health checks every 5 minutes")
        print("• Comprehensive metric tracking")
        print("• Configurable alert thresholds")
        print("• Emergency shutdown capabilities")
        print("• Performance trend analysis")
        print("• WebSocket connection monitoring")
        print("• Balance manager health tracking")
        print("• Nonce system performance")

        print("\n⚡ TRACKED METRICS:")
        print("• Trades executed and success rate")
        print("• Total P&L and daily performance")
        print("• Memory usage and system resources")
        print("• API errors and response times")
        print("• WebSocket latency and reconnects")
        print("• Balance manager response times")
        print("• Log file sizes and rotation")

        if status['dashboard_enabled']:
            print(f"\n🔗 Access your dashboard: {dashboard_url}")
            print("   Dashboard updates in real-time via WebSocket")
            print("   Emergency controls available in dashboard")

        print("\n🛡️  EMERGENCY CONTROLS:")
        print("• Automatic emergency shutdown on critical conditions")
        print("• Manual emergency stop via dashboard")
        print("• Configurable alert thresholds")
        print("• Circuit breaker integration")

        print("="*60)
        print("Bot is starting with full monitoring enabled...")
        print("="*60 + "\n")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            self.running = False
            # Create task to shutdown gracefully
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def shutdown(self):
        """Shutdown bot and monitoring"""
        if not self.running:
            return

        self.running = False
        logger.info("Shutting down monitored bot...")

        try:
            # Shutdown monitoring first
            if self.monitoring:
                await self.monitoring.shutdown_integration()
                logger.info("Monitoring system shutdown")

            # Shutdown bot
            if self.bot:
                if hasattr(self.bot, 'stop'):
                    await self.bot.stop()
                elif hasattr(self.bot, 'shutdown'):
                    await self.bot.shutdown()
                logger.info("Bot shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Launch Crypto Trading Bot with Production Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_with_monitoring.py                    # Default monitoring
  python launch_with_monitoring.py --config production # Production config
  python launch_with_monitoring.py --dashboard-port 8001 # Custom port
  python launch_with_monitoring.py --no-dashboard     # No web dashboard
  python launch_with_monitoring.py --config config.json # Custom config file

Config Types:
  default     - Balanced monitoring for general use
  production  - Aggressive monitoring for live trading
  development - Relaxed monitoring for testing
  minimal     - Basic monitoring with minimal overhead
        """
    )

    parser.add_argument(
        '--config', '-c',
        help='Monitoring config type (default/production/development/minimal) or path to config file',
        default='default'
    )

    parser.add_argument(
        '--dashboard-port', '-p',
        type=int,
        help='Dashboard server port (default: 8000)'
    )

    parser.add_argument(
        '--no-dashboard',
        action='store_true',
        help='Disable web dashboard'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and run launcher
    launcher = MonitoredBotLauncher(args)

    try:
        # Run with proper event loop handling
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(launcher.start())
    except KeyboardInterrupt:
        print("\nReceived interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
