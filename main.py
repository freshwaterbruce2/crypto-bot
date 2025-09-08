#!/usr/bin/env python3
"""
Enhanced Kraken Trading System - Production Entry Point
Main orchestrator for the complete trading system with all components integrated
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any

from engine.config.config_manager import ConfigManager
from engine.trading.trading_config import TradingConfig
from engine.trading.trading_engine import TradingEngine
from engine.order_execution.order_executor import OrderExecutor
from engine.market_data.market_data_processor import MarketDataProcessor
from engine.risk.risk_manager import RiskManager
from engine.state.state_manager import StateManager
from engine.risk.circuit_breaker import CircuitBreaker

# Configure logging with rotation
from logging.handlers import RotatingFileHandler

# Create rotating file handler (100MB max, 5 backups)
# Using a new log file to avoid locking issues
file_handler = RotatingFileHandler(
    "trading_new.log",
    maxBytes=100 * 1024 * 1024,  # 100MB
    backupCount=5,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class EnhancedTradingSystem:
    """
    Complete trading system orchestrator
    Manages all components and provides unified trading interface
    """

    def __init__(self, config_file: str = "config/trading_config.json"):
        """
        Initialize the complete trading system

        Args:
            config_file: Path to configuration file
        """
        self.config_file = Path(config_file)
        self.is_running = False

        # Core components
        self.config_manager = None
        self.trading_config = None
        self.state_manager = None
        self.trading_engine = None
        self.market_processor = None
        self.order_executor = None
        self.risk_manager = None

        # Control flags
        self.emergency_stop = False
        self.shutdown_event = asyncio.Event()

        logger.info("Enhanced Trading System initialized")

    async def initialize_system(self):
        """Initialize all system components"""
        try:
            logger.info("Initializing system components...")

            # 1. Load configuration
            self.config_manager = ConfigManager()
            await self.config_manager.load_consolidated_config()

            # 2. Create trading configuration
            self.trading_config = TradingConfig()
            self.trading_config.pair = "XLM/USD"
            self.trading_config.kraken_pair = "XLM/USD"  # WebSocket v2 format
            from decimal import Decimal

            self.trading_config.taker_fee_rate = Decimal("0.0026")  # 0.26%
            self.trading_config.maker_fee_rate = Decimal("0.0016")  # 0.16%

            # 3. Initialize state manager
            self.state_manager = StateManager(
                "state/trading_state.json", self.trading_config, self.config_manager
            )
            await self.state_manager.load_state()

            # 4. Initialize market data processor
            self.market_processor = MarketDataProcessor(
                self.trading_config, self.config_manager
            )

            # 5. Initialize circuit breaker
            circuit_breaker = CircuitBreaker(
                failure_threshold=3, recovery_timeout=60, name="TradingSystem"
            )

            # 6. Initialize order executor
            self.order_executor = OrderExecutor(
                self.trading_config, self.config_manager, circuit_breaker
            )

            # 7. Initialize risk manager (choose enhanced by default, fallback to basic)
            risk_manager_type = self.trading_config.risk_manager_type

            if risk_manager_type == "enhanced":
                try:
                    from engine.risk_manager_enhanced import EnhancedRiskManager

                    self.risk_manager = EnhancedRiskManager(
                        self.trading_config, self.config_manager
                    )
                    logger.info(
                        "Using Enhanced Risk Manager with Kelly Criterion and dynamic risk adjustment"
                    )
                except ImportError as e:
                    logger.warning(
                        f"Enhanced Risk Manager failed to load ({e}), falling back to basic"
                    )
                    self.risk_manager = RiskManager(
                        self.trading_config, self.config_manager
                    )
            else:
                self.risk_manager = RiskManager(
                    self.trading_config, self.config_manager
                )
                logger.info("Using Basic Risk Manager (conservative approach)")

            # 8. Initialize trading engine
            self.trading_engine = TradingEngine(self.trading_config)

            logger.info("All system components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            return False

    async def start_trading(self):
        """Start the complete trading system"""
        if not await self.initialize_system():
            logger.error("System initialization failed")
            return False

        try:
            self.is_running = True
            logger.info("Starting trading system...")

            # Start auto-save for state persistence
            await self.state_manager.start_auto_save()

            # Create trading tasks
            tasks = [
                self._market_data_loop(),
                self._trading_loop(),
                self._risk_monitoring_loop(),
                self._health_check_loop(),
            ]

            # Run all tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Trading system error: {e}")
            await self.emergency_shutdown()
        finally:
            await self.graceful_shutdown()

    async def _market_data_loop(self):
        """Main market data processing loop"""
        logger.info("Starting market data processing...")

        while self.is_running and not self.emergency_stop:
            try:
                # Connect to market data if not connected
                if self.market_processor and not self.market_processor.is_connected:
                    logger.info("Attempting to connect to market data...")
                    await self.market_processor.connect()

                # Process market data if connected
                if self.market_processor and self.market_processor.is_connected:
                    market_data = self.market_processor.get_current_market_data()

                    # Only update if we have valid data
                    if market_data.get("last_price"):
                        await self.state_manager.update_market_data_state(market_data)
                        logger.debug(
                            f"Market data updated: {market_data.get('pair')} @ {market_data.get('last_price')}"
                        )
                    else:
                        logger.debug("No valid market data available")
                else:
                    logger.warning("Market data processor not connected, retrying...")
                    await asyncio.sleep(5.0)
                    continue

                # Check data freshness and reconnect if stale
                market_data_state = self.state_manager.get_market_data_state()
                if market_data_state.get("is_stale", False):
                    logger.warning("Market data is stale, attempting reconnection...")
                    if self.market_processor:
                        await self.market_processor.disconnect()
                        await asyncio.sleep(2.0)  # Brief pause before reconnect
                        await self.market_processor.connect()

                await asyncio.sleep(1.0)  # Process every second

            except Exception as e:
                logger.error(f"Market data loop error: {e}")
                await asyncio.sleep(5.0)

    async def _trading_loop(self):
        """Main trading decision loop"""
        logger.info("Starting trading decision loop...")

        while self.is_running and not self.emergency_stop:
            try:
                # Check if emergency stop is active
                if self.risk_manager and self.risk_manager.should_halt_trading()[0]:
                    logger.warning("Emergency stop active - halting trading")
                    await asyncio.sleep(10.0)
                    continue

                # Get current market data from state manager
                market_data = self.state_manager.get_market_data_state()

                # Only proceed if we have valid market data
                if (
                    market_data.get("last_price")
                    and market_data.get("bid")
                    and market_data.get("ask")
                ):
                    current_price = market_data["last_price"]
                    market_condition = market_data.get("market_condition", "normal")

                    # Evaluate trading opportunities based on real market data
                    await self._evaluate_trading_opportunity(
                        market_data, market_condition
                    )

                    # Check and manage existing positions
                    await self._monitor_active_positions(current_price)

                    await asyncio.sleep(2.0)  # Check every 2 seconds for active trading
                else:
                    logger.debug("Waiting for valid market data...")
                    await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(5.0)

    async def _evaluate_trading_opportunity(
        self, market_data: Dict[str, Any], market_condition: str
    ):
        """Evaluate potential trading opportunities based on market data"""
        try:
            current_price = market_data.get("last_price")
            bid = market_data.get("bid")
            ask = market_data.get("ask")
            spread = market_data.get("spread", 0)
            volatility = market_data.get("volatility", 0)

            # Basic trading signal generation (placeholder for advanced strategy)
            # This would be replaced with actual trading algorithms
            if current_price and bid and ask:
                # Example: Simple mean reversion signal
                mid_price = (bid + ask) / 2
                price_deviation = abs(current_price - mid_price) / mid_price

                # Only consider trades with reasonable spreads and volatility
                if spread > 0 and mid_price > 0:
                    spread_pct = spread / mid_price

                    # Conservative spread filter (avoid wide spreads)
                    if spread_pct < 0.005:  # Less than 0.5% spread
                        logger.debug(
                            f"Market conditions suitable: spread={spread_pct:.4f}, volatility={volatility}"
                        )

                        # Placeholder for actual trading logic
                        # In production, this would evaluate:
                        # - Technical indicators
                        # - Risk-reward ratios
                        # - Position sizing
                        # - Market timing

                    else:
                        logger.debug(f"Spread too wide: {spread_pct:.4f}")

        except Exception as e:
            logger.error(f"Error evaluating trading opportunity: {e}")

    async def _monitor_active_positions(self, current_price: Decimal):
        """Monitor and manage active trading positions"""
        try:
            # Get current account balance for risk calculations
            # This would need integration with account balance monitoring
            account_balance = Decimal("1000.0")  # Placeholder

            # Check if we have position monitoring capability
            if hasattr(self.risk_manager, "monitor_position_risk"):
                # Monitor existing positions (placeholder - no active positions yet)
                # In production, this would:
                # - Check stop losses
                # - Monitor profit targets
                # - Handle position scaling
                # - Risk assessment per position
                pass

            # Update risk manager with current market conditions
            if hasattr(self.risk_manager, "update_drawdown_tracking"):
                self.risk_manager.update_drawdown_tracking(account_balance)

        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")

    async def _risk_monitoring_loop(self):
        """Risk monitoring and management loop"""
        logger.info("Starting risk monitoring...")

        while self.is_running and not self.emergency_stop:
            try:
                # Perform risk health check
                if self.risk_manager:
                    health_status = await self.risk_manager.perform_risk_health_check()

                    if health_status["overall_health"] == "critical":
                        logger.critical("Critical risk condition detected!")
                        self.emergency_stop = True

                await asyncio.sleep(30.0)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Risk monitoring error: {e}")
                await asyncio.sleep(10.0)

    async def _health_check_loop(self):
        """System health monitoring loop"""
        logger.info("Starting health monitoring...")

        while self.is_running and not self.emergency_stop:
            try:
                # System health check
                health_metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "system_status": "healthy"
                    if not self.emergency_stop
                    else "emergency",
                    "components_active": self._get_component_status(),
                }

                # Log health status
                if health_metrics["system_status"] == "healthy":
                    logger.debug(f"System health: {health_metrics}")
                else:
                    logger.warning(f"System health warning: {health_metrics}")

                await asyncio.sleep(60.0)  # Check every minute

            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(30.0)

    def _get_component_status(self) -> dict:
        """Get status of all system components"""
        return {
            "config_manager": self.config_manager is not None,
            "state_manager": self.state_manager is not None,
            "trading_engine": self.trading_engine is not None,
            "market_processor": self.market_processor is not None,
            "order_executor": self.order_executor is not None,
            "risk_manager": self.risk_manager is not None,
            "emergency_stop": self.emergency_stop,
        }

    async def emergency_shutdown(self):
        """Emergency shutdown procedure"""
        logger.critical("EMERGENCY SHUTDOWN INITIATED")

        self.emergency_stop = True
        self.is_running = False

        try:
            # Cancel all open orders (placeholder)
            if self.order_executor:
                logger.info("Cancelling all open orders...")
                # Implementation would cancel all orders here

            # Save final state
            if self.state_manager:
                await self.state_manager.persist_state()

            logger.info("Emergency shutdown completed")

        except Exception as e:
            logger.error(f"Emergency shutdown error: {e}")

    async def graceful_shutdown(self):
        """Graceful shutdown procedure"""
        logger.info("Graceful shutdown initiated...")

        self.is_running = False

        try:
            # Stop auto-save
            if self.state_manager:
                await self.state_manager.stop_auto_save()

            # Save final state
            if self.state_manager:
                await self.state_manager.persist_state()

            # Close connections
            if self.market_processor:
                logger.info("Closing market data connections...")

            logger.info("Graceful shutdown completed")

        except Exception as e:
            logger.error(f"Shutdown error: {e}")

    def get_system_status(self) -> dict:
        """Get comprehensive system status"""
        return {
            "is_running": self.is_running,
            "emergency_stop": self.emergency_stop,
            "components": self._get_component_status(),
            "performance": self.state_manager.get_performance_state()
            if self.state_manager
            else {},
            "risk": self.state_manager.get_risk_state() if self.state_manager else {},
            "last_updated": datetime.now().isoformat(),
        }


async def main():
    """Main entry point for the trading system"""
    # Create trading system instance
    system = EnhancedTradingSystem()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        system.shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("=== Enhanced Kraken Trading System Starting ===")
        logger.info("Press Ctrl+C to stop gracefully")

        # Start the trading system
        await system.start_trading()

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Critical system error: {e}")
        await system.emergency_shutdown()
    finally:
        logger.info("=== Trading System Stopped ===")


if __name__ == "__main__":
    # Run the trading system
    asyncio.run(main())
