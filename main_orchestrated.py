#!/usr/bin/env python3
"""
Orchestrated Trading Bot Main Entry Point

This version uses the full system orchestrator for initialization,
monitoring, and management of all components.
"""

import argparse
import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.orchestrator import SystemOrchestrator
from src.orchestrator.bot_integration import OrchestratedTradingBot
from src.orchestrator.diagnostics_dashboard import DiagnosticsDashboard, SimpleDiagnostics
from src.orchestrator.health_monitor import HealthStatus
from src.utils.custom_logging import configure_logging

# Configure logging first
logger = configure_logging()


class OrchestratedMain:
    """Main application with full orchestration and WebSocket-first support"""

    def __init__(self, config_path: str = "config.json", enable_dashboard: bool = False, websocket_first_mode: bool = True):
        self.config_path = config_path
        self.enable_dashboard = enable_dashboard
        self.websocket_first_mode = websocket_first_mode
        self.bot = None
        self.orchestrator = None
        self.shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize the orchestrated system"""
        logger.info("=" * 60)
        logger.info("ORCHESTRATED CRYPTO TRADING BOT")
        logger.info("=" * 60)
        logger.info(f"Starting at: {datetime.now().isoformat()}")
        logger.info(f"Config: {self.config_path}")
        logger.info(f"Dashboard: {'Enabled' if self.enable_dashboard else 'Disabled'}")
        logger.info(f"WebSocket-First: {'Enabled' if self.websocket_first_mode else 'Disabled'}")

        # Create orchestrated bot with WebSocket-first mode
        self.bot = OrchestratedTradingBot(self.config_path)
        self.bot.websocket_first_mode = self.websocket_first_mode
        self.orchestrator = self.bot.orchestrator

        # Register signal handlers
        self._setup_signal_handlers()

        # Initialize system
        logger.info("\nInitializing system components...")
        try:
            await self.bot.initialize()
            logger.info("System initialization complete!")

            # Print initial status
            self._print_status()

            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            await self._emergency_diagnostics()
            return False

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"\nReceived signal {signum}, initiating graceful shutdown...")
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _print_status(self):
        """Print current system status"""
        status = self.bot.get_status()

        logger.info("\n" + "=" * 40)
        logger.info("SYSTEM STATUS")
        logger.info("=" * 40)

        # Orchestrator status
        orch_status = status['orchestrator']
        logger.info(f"Health: {orch_status['health']}")
        logger.info(f"Uptime: {orch_status['uptime']:.1f}s")
        logger.info(f"Components: {sum(1 for v in orch_status['components'].values() if v)} active")

        # Bot status
        if status['bot']:
            logger.info(f"Bot: {status['bot'].get('status', 'Unknown')}")

        # Strategy status
        if status['strategy']:
            logger.info(f"Strategy: {status['strategy'].get('name', 'Unknown')}")

        logger.info("=" * 40 + "\n")

    async def _emergency_diagnostics(self):
        """Export emergency diagnostics on failure"""
        try:
            logger.error("Exporting emergency diagnostics...")

            if self.orchestrator:
                filename = f"emergency_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                await self.orchestrator.export_diagnostics(filename)
                logger.error(f"Diagnostics saved to: {filename}")

        except Exception as e:
            logger.error(f"Failed to export diagnostics: {e}")

    async def run_bot(self):
        """Run the trading bot"""
        logger.info("\nStarting trading bot...")

        try:
            # Start the bot
            await self.bot.start()

            logger.info("Trading bot is now active!")
            logger.info("Press Ctrl+C to stop\n")

            # Monitor health while running
            monitor_task = asyncio.create_task(self._monitor_health())

            # Wait for shutdown signal
            await self.shutdown_event.wait()

            # Cancel monitoring
            monitor_task.cancel()

        except Exception as e:
            logger.error(f"Bot runtime error: {e}")
            await self._emergency_diagnostics()
            raise

    async def run_dashboard(self):
        """Run with interactive dashboard"""
        logger.info("\nLaunching interactive dashboard...")

        try:
            # Start bot in background
            bot_task = asyncio.create_task(self.bot.start())

            # Wait a moment for startup
            await asyncio.sleep(2)

            # Run dashboard
            dashboard = DiagnosticsDashboard(self.orchestrator)
            await dashboard.run()

            # Dashboard exited, shutdown
            self.shutdown_event.set()

            # Wait for bot to stop
            bot_task.cancel()

        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            raise

    async def _monitor_health(self):
        """Monitor system health while running"""
        last_health = None

        while not self.shutdown_event.is_set():
            try:
                # Get current health
                health = self.orchestrator.health.get_system_status()

                # Log if health changed
                if health != last_health:
                    logger.info(f"System health: {health.value}")
                    last_health = health

                    # If critical, log more details
                    if health in (HealthStatus.CRITICAL, HealthStatus.UNHEALTHY):
                        components = self.orchestrator.health.get_all_health()
                        for name, comp_health in components.items():
                            if comp_health.status != HealthStatus.HEALTHY:
                                logger.warning(f"  {name}: {comp_health.status.value}")

                # Check every 30 seconds
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("\nInitiating graceful shutdown...")

        try:
            # Stop the bot
            if self.bot:
                await self.bot.stop()

            logger.info("Shutdown complete!")

        except Exception as e:
            logger.error(f"Shutdown error: {e}")

    async def run(self):
        """Main run method"""
        # Initialize
        if not await self.initialize():
            logger.error("Failed to initialize system")
            return 1

        try:
            # Run appropriate mode
            if self.enable_dashboard:
                await self.run_dashboard()
            else:
                await self.run_bot()

            return 0

        except Exception as e:
            logger.error(f"Runtime error: {e}")
            return 1

        finally:
            await self.shutdown()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Orchestrated Crypto Trading Bot')
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Enable interactive dashboard'
    )
    parser.add_argument(
        '--diagnostics',
        action='store_true',
        help='Print diagnostics and exit'
    )
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Run health check and exit'
    )
    parser.add_argument(
        '--websocket-first',
        action='store_true',
        default=True,
        help='Use WebSocket-first initialization (default: True)'
    )
    parser.add_argument(
        '--rest-only',
        action='store_true',
        help='Force REST-only mode, disable WebSocket-first initialization'
    )

    args = parser.parse_args()

    # Handle special modes
    if args.diagnostics:
        # Just print diagnostics
        orchestrator = SystemOrchestrator(args.config)
        await orchestrator.initialize()

        diag = SimpleDiagnostics(orchestrator)
        diag.print_status()
        await diag.export_report()

        await orchestrator.shutdown()
        return 0

    if args.health_check:
        # Run health check
        orchestrator = SystemOrchestrator(args.config)
        await orchestrator.initialize()

        health = await orchestrator.run_health_check()
        print("\nHealth Check Results:")
        for component, status in health.items():
            print(f"  {component}: {status.status.value}")

        await orchestrator.shutdown()
        return 0

    # Normal operation with WebSocket-first mode
    websocket_first_mode = args.websocket_first and not args.rest_only

    logger.info(f"Starting bot in {'WebSocket-first' if websocket_first_mode else 'REST-only'} mode")

    app = OrchestratedMain(args.config, args.dashboard, websocket_first_mode)
    return await app.run()


if __name__ == "__main__":
    # Run the orchestrated bot
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
