"""
Portfolio Manager
================

Main portfolio management system that orchestrates position tracking,
risk management, rebalancing, and analytics for comprehensive portfolio management.

Features:
- Unified portfolio management interface
- Real-time position and P&L tracking
- Automated risk management and limits
- Portfolio rebalancing with multiple strategies
- Performance analytics and reporting
- Integration with balance manager and trading systems
- Thread-safe operations for concurrent access
- Configurable portfolio strategies and limits
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Any, Callable, Optional, Union

from ..utils.decimal_precision_fix import safe_decimal
from .analytics import AnalyticsConfig, MetricPeriod, PortfolioAnalytics
from .position_tracker import Position, PositionStatus, PositionTracker, PositionType
from .rebalancer import RebalanceConfig, Rebalancer, RebalanceResult, RebalanceStrategy
from .risk_manager import RiskAction, RiskLimits, RiskManager

logger = logging.getLogger(__name__)


class PortfolioStrategy(Enum):
    """Portfolio management strategies"""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    GROWTH = "growth"
    INCOME = "income"
    CUSTOM = "custom"


class PortfolioStatus(Enum):
    """Portfolio status"""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    LIQUIDATING = "liquidating"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class PortfolioConfig:
    """Portfolio manager configuration"""

    # Strategy settings
    strategy: PortfolioStrategy = PortfolioStrategy.BALANCED
    target_allocations: dict[str, float] = None  # symbol -> weight

    # Risk settings
    max_portfolio_risk_pct: float = 2.0
    max_single_position_pct: float = 20.0
    max_drawdown_pct: float = 15.0

    # Rebalancing settings
    rebalance_enabled: bool = True
    rebalance_threshold_pct: float = 10.0
    rebalance_interval_hours: float = 24.0

    # Performance settings
    benchmark_symbol: str = "BTC"
    performance_tracking: bool = True
    analytics_enabled: bool = True

    # Integration settings
    balance_manager_enabled: bool = True
    auto_position_tracking: bool = True
    real_time_pnl: bool = True

    # Data persistence
    data_path: str = "D:/trading_data"
    backup_enabled: bool = True
    backup_interval_hours: float = 6.0

    def __post_init__(self):
        if self.target_allocations is None:
            # Default balanced allocation
            self.target_allocations = {
                "BTC/USDT": 0.4,
                "ETH/USDT": 0.3,
                "SHIB/USDT": 0.2,
                "ADA/USDT": 0.1,
            }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["strategy"] = self.strategy.value
        return data


class PortfolioManager:
    """
    Main portfolio management system
    """

    def __init__(
        self,
        balance_manager=None,
        trade_executor=None,
        config: Optional[PortfolioConfig] = None,
        exchange=None,
        account_tier=None,
    ):
        """
        Initialize portfolio manager

        Args:
            balance_manager: Balance manager instance
            trade_executor: Trade executor instance
            config: Portfolio configuration
            exchange: Exchange instance (for backward compatibility)
            account_tier: Account tier configuration (for backward compatibility)
        """
        self.balance_manager = balance_manager
        self.trade_executor = trade_executor
        self.config = config or PortfolioConfig()
        self.exchange = exchange
        self.account_tier = account_tier

        # Status and state
        self._status = PortfolioStatus.INITIALIZING
        self._lock = RLock()
        self._async_lock = asyncio.Lock()
        self._initialized = False
        self._running = False

        # Core components
        self.position_tracker = PositionTracker(
            balance_manager=balance_manager, data_path=self.config.data_path
        )

        # Risk manager with portfolio-specific limits
        risk_limits = RiskLimits(
            max_portfolio_risk_pct=self.config.max_portfolio_risk_pct,
            max_single_position_pct=self.config.max_single_position_pct,
            max_total_drawdown_pct=self.config.max_drawdown_pct,
        )

        self.risk_manager = RiskManager(
            position_tracker=self.position_tracker,
            balance_manager=balance_manager,
            limits=risk_limits,
            data_path=self.config.data_path,
        )

        # Rebalancer with portfolio-specific config
        rebalance_config = RebalanceConfig(
            max_drift_pct=self.config.rebalance_threshold_pct,
            rebalance_interval_hours=self.config.rebalance_interval_hours,
            dry_run=False,
        )

        self.rebalancer = Rebalancer(
            position_tracker=self.position_tracker,
            risk_manager=self.risk_manager,
            balance_manager=balance_manager,
            trade_executor=trade_executor,
            config=rebalance_config,
            data_path=self.config.data_path,
        )

        # Analytics system
        analytics_config = AnalyticsConfig(
            benchmark_symbol=self.config.benchmark_symbol,
            export_path=f"{self.config.data_path}/analytics",
        )

        self.analytics = PortfolioAnalytics(
            position_tracker=self.position_tracker,
            risk_manager=self.risk_manager,
            balance_manager=balance_manager,
            config=analytics_config,
            data_path=self.config.data_path,
        )

        # Event callbacks
        self._callbacks: dict[str, list[Callable]] = {
            "position_opened": [],
            "position_closed": [],
            "risk_limit_exceeded": [],
            "rebalance_completed": [],
            "performance_update": [],
            "status_changed": [],
            "error": [],
        }

        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._backup_task: Optional[asyncio.Task] = None

        # Files
        self.config_file = f"{self.config.data_path}/portfolio_config.json"
        self.status_file = f"{self.config.data_path}/portfolio_status.json"

        logger.info("[PORTFOLIO_MANAGER] Initialized portfolio management system")

    @property
    def positions(self):
        """Get all positions from position tracker"""
        if hasattr(self.position_tracker, "get_all_positions"):
            return self.position_tracker.get_all_positions()
        return {}

    async def initialize(self) -> bool:
        """Initialize the portfolio manager and all components"""
        if self._initialized:
            logger.warning("[PORTFOLIO_MANAGER] Already initialized")
            return True

        try:
            async with self._async_lock:
                self._status = PortfolioStatus.INITIALIZING
                logger.info("[PORTFOLIO_MANAGER] Starting initialization...")

                # Load configuration
                await self._load_config()

                # Initialize core components
                await self.position_tracker.initialize()
                await self.risk_manager.initialize()
                await self.rebalancer.initialize()

                if self.config.analytics_enabled:
                    await self.analytics.initialize()

                # Set target allocations for rebalancing
                if self.config.target_allocations:
                    self.rebalancer.set_target_allocations(self.config.target_allocations)

                # Start monitoring
                await self._start_monitoring()

                self._status = PortfolioStatus.ACTIVE
                self._initialized = True

                await self._save_status()
                await self._call_callbacks("status_changed", self._status)

                logger.info("[PORTFOLIO_MANAGER] Initialization complete")
                return True

        except Exception as e:
            self._status = PortfolioStatus.ERROR
            logger.error(f"[PORTFOLIO_MANAGER] Initialization failed: {e}")
            await self._call_callbacks("error", e)
            return False

    async def shutdown(self) -> None:
        """Shutdown the portfolio manager"""
        if not self._running:
            return

        logger.info("[PORTFOLIO_MANAGER] Shutting down...")

        self._running = False
        self._status = PortfolioStatus.MAINTENANCE

        # Stop monitoring tasks
        await self._stop_monitoring()

        # Shutdown components
        await self.rebalancer.stop_monitoring()

        if self.config.analytics_enabled:
            await self.analytics.stop_analytics()

        # Save final state
        await self._save_config()
        await self._save_status()

        self._initialized = False
        logger.info("[PORTFOLIO_MANAGER] Shutdown complete")

    async def create_position(
        self,
        symbol: str,
        position_type: PositionType,
        size: Union[float, Decimal],
        entry_price: Union[float, Decimal],
        strategy: str = None,
        tags: list[str] = None,
    ) -> Optional[Position]:
        """
        Create a new position with risk checking

        Args:
            symbol: Trading pair symbol
            position_type: LONG or SHORT
            size: Position size
            entry_price: Entry price
            strategy: Strategy name
            tags: Optional tags

        Returns:
            Created position or None if rejected
        """
        if not self._initialized:
            raise RuntimeError("Portfolio manager not initialized")

        try:
            # Risk check
            float(size) * float(entry_price)
            risk_action, risk_reason = await self.risk_manager.check_position_risk(
                symbol, float(size), float(entry_price), position_type.value
            )

            if risk_action not in [RiskAction.ALLOW, RiskAction.WARN]:
                logger.warning(f"[PORTFOLIO_MANAGER] Position rejected: {risk_reason}")
                return None

            # Create position
            position = await self.position_tracker.create_position(
                symbol, position_type, size, entry_price, strategy, tags
            )

            # Record trade for risk tracking
            self.risk_manager.record_trade(symbol, float(size), float(entry_price))

            # Call callbacks
            await self._call_callbacks("position_opened", position)

            logger.info(f"[PORTFOLIO_MANAGER] Created position {position.position_id}")
            return position

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error creating position: {e}")
            await self._call_callbacks("error", e)
            return None

    async def close_position(
        self,
        position_id: str,
        price: Union[float, Decimal],
        size: Union[float, Decimal] = None,
        fees: Union[float, Decimal] = 0,
    ) -> bool:
        """
        Close a position (partial or full)

        Args:
            position_id: Position ID to close
            price: Exit price
            size: Size to close (None for full close)
            fees: Trading fees

        Returns:
            True if successful
        """
        try:
            position = self.position_tracker.get_position(position_id)
            if not position:
                logger.warning(f"[PORTFOLIO_MANAGER] Position not found: {position_id}")
                return False

            # Determine close size
            close_size = size if size is not None else position.current_size

            # Close position
            realized_pnl = await self.position_tracker.close_position_partial(
                position_id, close_size, price, fees
            )

            if realized_pnl is not None:
                # Update analytics
                if self.config.analytics_enabled:
                    current_value = await self._get_portfolio_value()
                    self.analytics.record_portfolio_value(current_value)

                # Call callbacks
                await self._call_callbacks(
                    "position_closed",
                    {
                        "position": position,
                        "realized_pnl": float(realized_pnl),
                        "close_size": float(close_size),
                    },
                )

                logger.info(
                    f"[PORTFOLIO_MANAGER] Closed position {position_id}: ${realized_pnl:.2f} P&L"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error closing position: {e}")
            await self._call_callbacks("error", e)
            return False

    async def update_position_price(self, symbol: str, price: Union[float, Decimal]) -> list[str]:
        """
        Update price for all positions of a symbol

        Args:
            symbol: Symbol to update
            price: New price

        Returns:
            List of updated position IDs
        """
        try:
            updated_positions = await self.position_tracker.update_position_price(symbol, price)

            if updated_positions and self.config.real_time_pnl:
                # Update analytics
                if self.config.analytics_enabled:
                    current_value = await self._get_portfolio_value()
                    self.analytics.record_portfolio_value(current_value)

            return updated_positions

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error updating position price: {e}")
            return []

    async def get_portfolio_summary(self) -> dict[str, Any]:
        """Get comprehensive portfolio summary"""
        try:
            # Base portfolio summary
            base_summary = self.position_tracker.get_portfolio_summary()

            # Risk metrics
            risk_metrics = await self.risk_manager.calculate_risk_metrics()

            # Performance metrics
            performance_metrics = None
            if self.config.analytics_enabled:
                performance_metrics = await self.analytics.calculate_performance_metrics(
                    MetricPeriod.DAILY
                )

            # Portfolio value
            total_value = await self._get_portfolio_value()

            # Rebalancing status
            drift_analysis = await self.rebalancer.calculate_portfolio_drift()

            return {
                "timestamp": time.time(),
                "status": self._status.value,
                "total_value": total_value,
                "positions": base_summary,
                "risk_metrics": risk_metrics.to_dict(),
                "performance_metrics": performance_metrics.to_dict()
                if performance_metrics
                else None,
                "drift_analysis": drift_analysis,
                "target_allocations": self.config.target_allocations,
                "strategy": self.config.strategy.value,
            }

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error getting portfolio summary: {e}")
            return {"error": str(e), "timestamp": time.time()}

    async def get_performance_report(self, periods: list[MetricPeriod] = None) -> dict[str, Any]:
        """Get comprehensive performance report"""
        if not self.config.analytics_enabled:
            return {"error": "Analytics not enabled"}

        try:
            return await self.analytics.generate_performance_report(periods)
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error generating performance report: {e}")
            return {"error": str(e)}

    async def get_risk_report(self) -> dict[str, Any]:
        """Get comprehensive risk report"""
        try:
            return await self.risk_manager.get_risk_report()
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error generating risk report: {e}")
            return {"error": str(e)}

    async def rebalance_portfolio(
        self, strategy: RebalanceStrategy = None, custom_targets: dict[str, float] = None
    ) -> Optional[RebalanceResult]:
        """
        Manually trigger portfolio rebalancing

        Args:
            strategy: Rebalancing strategy (uses config default if None)
            custom_targets: Custom target allocations

        Returns:
            RebalanceResult if successful
        """
        if not self.config.rebalance_enabled:
            logger.warning("[PORTFOLIO_MANAGER] Rebalancing is disabled")
            return None

        try:
            # Determine strategy
            if strategy is None:
                if self.config.strategy == PortfolioStrategy.CONSERVATIVE:
                    strategy = RebalanceStrategy.DCA
                elif self.config.strategy == PortfolioStrategy.AGGRESSIVE:
                    strategy = RebalanceStrategy.MOMENTUM
                else:
                    strategy = RebalanceStrategy.THRESHOLD

            # Create and execute rebalance plan
            plan = await self.rebalancer.create_rebalance_plan(
                strategy, reason="manual", custom_targets=custom_targets
            )

            if plan.success:
                result = await self.rebalancer.execute_rebalance_plan(plan)

                if result.success:
                    await self._call_callbacks("rebalance_completed", result)
                    logger.info(
                        f"[PORTFOLIO_MANAGER] Rebalancing completed: "
                        f"{result.actual_trades} trades, ${result.actual_cost:.2f} cost"
                    )

                return result

            return plan

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error rebalancing portfolio: {e}")
            await self._call_callbacks("error", e)
            return None

    async def set_target_allocations(self, targets: dict[str, float]) -> bool:
        """
        Set new target allocations

        Args:
            targets: New target allocations (symbol -> weight)

        Returns:
            True if successful
        """
        try:
            # Validate targets
            total_weight = sum(targets.values())
            if abs(total_weight - 1.0) > 0.01:  # Allow 1% tolerance
                logger.warning(
                    f"[PORTFOLIO_MANAGER] Target allocations sum to {total_weight:.3f}, not 1.0"
                )
                # Normalize
                targets = {symbol: weight / total_weight for symbol, weight in targets.items()}

            # Update configuration
            self.config.target_allocations = targets

            # Update rebalancer
            self.rebalancer.set_target_allocations(targets)

            # Save configuration
            await self._save_config()

            logger.info(f"[PORTFOLIO_MANAGER] Updated target allocations: {targets}")
            return True

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error setting target allocations: {e}")
            return False

    async def pause_portfolio(self) -> bool:
        """Pause portfolio operations"""
        try:
            self._status = PortfolioStatus.PAUSED
            await self.rebalancer.stop_monitoring()
            await self._save_status()
            await self._call_callbacks("status_changed", self._status)
            logger.info("[PORTFOLIO_MANAGER] Portfolio paused")
            return True
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error pausing portfolio: {e}")
            return False

    async def resume_portfolio(self) -> bool:
        """Resume portfolio operations"""
        try:
            self._status = PortfolioStatus.ACTIVE
            if self.config.rebalance_enabled:
                await self.rebalancer.start_monitoring()
            await self._save_status()
            await self._call_callbacks("status_changed", self._status)
            logger.info("[PORTFOLIO_MANAGER] Portfolio resumed")
            return True
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error resuming portfolio: {e}")
            return False

    async def liquidate_portfolio(self, emergency: bool = False) -> dict[str, Any]:
        """
        Liquidate all positions

        Args:
            emergency: If True, use market orders for immediate liquidation

        Returns:
            Liquidation results
        """
        try:
            self._status = PortfolioStatus.LIQUIDATING
            await self._save_status()

            open_positions = self.position_tracker.get_all_open_positions()

            if not open_positions:
                logger.info("[PORTFOLIO_MANAGER] No positions to liquidate")
                return {"success": True, "liquidated_positions": 0}

            liquidation_results = []

            for position_id, position in open_positions.items():
                try:
                    # Get current price (simplified - would use real price feed)
                    current_price = position.current_price

                    # Close position
                    success = await self.close_position(position_id, current_price)

                    liquidation_results.append(
                        {
                            "position_id": position_id,
                            "symbol": position.symbol,
                            "success": success,
                            "size": float(position.current_size),
                            "pnl": float(position.unrealized_pnl),
                        }
                    )

                except Exception as e:
                    logger.error(f"[PORTFOLIO_MANAGER] Error liquidating {position_id}: {e}")
                    liquidation_results.append(
                        {
                            "position_id": position_id,
                            "symbol": position.symbol,
                            "success": False,
                            "error": str(e),
                        }
                    )

            successful_liquidations = sum(1 for result in liquidation_results if result["success"])
            total_pnl = sum(
                result.get("pnl", 0) for result in liquidation_results if result["success"]
            )

            self._status = PortfolioStatus.ACTIVE
            await self._save_status()

            result = {
                "success": True,
                "liquidated_positions": successful_liquidations,
                "total_positions": len(liquidation_results),
                "total_pnl": total_pnl,
                "details": liquidation_results,
            }

            logger.info(
                f"[PORTFOLIO_MANAGER] Liquidation complete: "
                f"{successful_liquidations}/{len(liquidation_results)} positions, "
                f"${total_pnl:.2f} total P&L"
            )

            return result

        except Exception as e:
            self._status = PortfolioStatus.ERROR
            logger.error(f"[PORTFOLIO_MANAGER] Liquidation error: {e}")
            await self._call_callbacks("error", e)
            return {"success": False, "error": str(e)}

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register callback for portfolio events"""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
            logger.debug(f"[PORTFOLIO_MANAGER] Registered callback for {event_type}")
        else:
            logger.warning(f"[PORTFOLIO_MANAGER] Unknown event type: {event_type}")

    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """Unregister callback for event type"""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)
            logger.debug(f"[PORTFOLIO_MANAGER] Unregistered callback for {event_type}")

    def get_status(self) -> PortfolioStatus:
        """Get current portfolio status"""
        return self._status

    def get_config(self) -> PortfolioConfig:
        """Get current configuration"""
        return self.config

    async def update_config(self, new_config: PortfolioConfig) -> bool:
        """Update portfolio configuration"""
        try:
            # Update configuration
            old_strategy = self.config.strategy
            self.config = new_config

            # Update component configurations if needed
            if new_config.target_allocations != old_strategy:
                self.rebalancer.set_target_allocations(new_config.target_allocations)

            # Save configuration
            await self._save_config()

            logger.info("[PORTFOLIO_MANAGER] Configuration updated")
            return True

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error updating configuration: {e}")
            return False

    async def export_data(self, format_type: str = "json") -> str:
        """Export portfolio data"""
        try:
            # Get comprehensive data
            summary = await self.get_portfolio_summary()
            performance_report = await self.get_performance_report()
            risk_report = await self.get_risk_report()

            export_data = {
                "timestamp": time.time(),
                "portfolio_summary": summary,
                "performance_report": performance_report,
                "risk_report": risk_report,
                "configuration": self.config.to_dict(),
            }

            # Export based on format
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

            if format_type == "json":
                filepath = f"{self.config.data_path}/portfolio_export_{timestamp_str}.json"
                with open(filepath, "w") as f:
                    json.dump(export_data, f, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")

            logger.info(f"[PORTFOLIO_MANAGER] Data exported to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error exporting data: {e}")
            raise

    async def _start_monitoring(self) -> None:
        """Start background monitoring tasks"""
        self._running = True

        # Start component monitoring
        if self.config.rebalance_enabled:
            await self.rebalancer.start_monitoring()

        if self.config.analytics_enabled:
            await self.analytics.start_analytics()

        # Start portfolio monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        # Start backup task if enabled
        if self.config.backup_enabled:
            self._backup_task = asyncio.create_task(self._backup_loop())

        logger.info("[PORTFOLIO_MANAGER] Monitoring started")

    async def _stop_monitoring(self) -> None:
        """Stop background monitoring tasks"""
        self._running = False

        # Stop monitoring tasks
        tasks = [self._monitoring_task, self._backup_task]

        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("[PORTFOLIO_MANAGER] Monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            try:
                # Update portfolio analytics
                if self.config.analytics_enabled and self.config.real_time_pnl:
                    current_value = await self._get_portfolio_value()
                    self.analytics.record_portfolio_value(current_value)

                # Check risk limits
                risk_metrics = await self.risk_manager.calculate_risk_metrics()

                if risk_metrics.overall_risk_level.value in ["high", "critical"]:
                    await self._call_callbacks("risk_limit_exceeded", risk_metrics)

                # Performance update callback
                if self.config.analytics_enabled:
                    performance_metrics = await self.analytics.calculate_performance_metrics(
                        MetricPeriod.DAILY
                    )
                    await self._call_callbacks("performance_update", performance_metrics)

                # Sleep until next check
                await asyncio.sleep(300)  # 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PORTFOLIO_MANAGER] Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _backup_loop(self) -> None:
        """Background backup loop"""
        while self._running:
            try:
                await asyncio.sleep(self.config.backup_interval_hours * 3600)

                if not self._running:
                    break

                # Create backup
                await self._create_backup()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PORTFOLIO_MANAGER] Backup loop error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def _create_backup(self) -> None:
        """Create data backup"""
        try:
            backup_path = await self.export_data("json")
            logger.info(f"[PORTFOLIO_MANAGER] Backup created: {backup_path}")
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Backup creation failed: {e}")

    async def _get_portfolio_value(self) -> float:
        """Get current total portfolio value"""
        try:
            if self.balance_manager:
                balances = await self.balance_manager.get_all_balances()
                return sum(balance_data.get("balance", 0) for balance_data in balances.values())
            else:
                summary = self.position_tracker.get_portfolio_summary()
                return summary.get("total_value", 0.0)
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error getting portfolio value: {e}")
            return 0.0

    async def _call_callbacks(self, event_type: str, data: Any = None) -> None:
        """Call registered callbacks for event type"""
        callbacks = self._callbacks.get(event_type, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    if data is not None:
                        await callback(data)
                    else:
                        await callback()
                else:
                    if data is not None:
                        callback(data)
                    else:
                        callback()
            except Exception as e:
                logger.error(f"[PORTFOLIO_MANAGER] Callback error for {event_type}: {e}")

    async def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            with open(self.config_file) as f:
                data = json.load(f)

                # Update config attributes
                for key, value in data.items():
                    if hasattr(self.config, key):
                        if key == "strategy":
                            self.config.strategy = PortfolioStrategy(value)
                        else:
                            setattr(self.config, key, value)

            logger.debug("[PORTFOLIO_MANAGER] Configuration loaded")

        except FileNotFoundError:
            await self._save_config()
            logger.info("[PORTFOLIO_MANAGER] Created default configuration")
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error loading configuration: {e}")

    async def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error saving configuration: {e}")

    async def _save_status(self) -> None:
        """Save status to file"""
        try:
            status_data = {
                "status": self._status.value,
                "timestamp": time.time(),
                "initialized": self._initialized,
                "running": self._running,
            }

            with open(self.status_file, "w") as f:
                json.dump(status_data, f, indent=2)

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error saving status: {e}")

    async def get_balances(self) -> dict[str, Decimal]:
        """
        Get all account balances through exchange

        Returns:
            Dict mapping symbol to balance amount
        """
        try:
            if hasattr(self, "exchange") and self.exchange:
                balances = await self.exchange.fetch_balance()
                return {
                    k: safe_decimal(v.get("free", 0))
                    for k, v in balances.items()
                    if v.get("free", 0) > 0
                }
            else:
                logger.warning(
                    "[PORTFOLIO_MANAGER] No exchange instance available for balance fetch"
                )
                return {}
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error fetching balances: {e}")
            return {}

    async def get_balance(self, symbol: str = "USDT") -> Decimal:
        """
        Get balance for specific symbol

        Args:
            symbol: Symbol to get balance for

        Returns:
            Balance amount as Decimal
        """
        try:
            balances = await self.get_balances()
            return balances.get(symbol, Decimal("0"))
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error getting balance for {symbol}: {e}")
            return Decimal("0")

    async def get_portfolio_value(self) -> Decimal:
        """
        Get total portfolio value in USDT

        Returns:
            Total portfolio value
        """
        try:
            if hasattr(self, "exchange") and self.exchange:
                balances = await self.get_balances()
                total_value = Decimal("0")

                for symbol, balance in balances.items():
                    if balance > 0:
                        if symbol == "USDT":
                            total_value += balance
                        else:
                            # Convert to USDT value
                            try:
                                pair = f"{symbol}/USDT"
                                ticker = await self.exchange.fetch_ticker(pair)
                                price = safe_decimal(ticker.get("last", 0))
                                total_value += balance * price
                            except Exception:
                                # Skip if can't get price
                                pass

                return total_value
            else:
                return Decimal("0")
        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error calculating portfolio value: {e}")
            return Decimal("0")

    async def get_open_positions(self) -> dict[str, Any]:
        """
        Get all open positions from position tracker

        Returns:
            Dictionary of open positions keyed by position ID
        """
        try:
            if hasattr(self.position_tracker, "get_all_open_positions"):
                return self.position_tracker.get_all_open_positions()
            elif hasattr(self.position_tracker, "get_open_positions"):
                return self.position_tracker.get_open_positions()
            else:
                # Fallback: get all positions and filter for open ones
                all_positions = self.position_tracker.get_all_positions()
                open_positions = {}

                for pos_id, position in all_positions.items():
                    if hasattr(position, "status") and position.status == PositionStatus.OPEN:
                        open_positions[pos_id] = position

                return open_positions

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error getting open positions: {e}")
            return {}

    def get_open_positions_sync(self) -> dict[str, Any]:
        """
        Synchronous version of get_open_positions for compatibility

        Returns:
            Dictionary of open positions keyed by position ID
        """
        try:
            if hasattr(self.position_tracker, "get_all_open_positions"):
                return self.position_tracker.get_all_open_positions()
            elif hasattr(self.position_tracker, "get_open_positions"):
                return self.position_tracker.get_open_positions()
            else:
                # Fallback: get all positions and filter for open ones
                all_positions = self.position_tracker.get_all_positions()
                open_positions = {}

                for pos_id, position in all_positions.items():
                    if hasattr(position, "status") and position.status == PositionStatus.OPEN:
                        open_positions[pos_id] = position

                return open_positions

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error getting open positions (sync): {e}")
            return {}

    async def force_sync_with_exchange(self, exchange=None, balance_manager=None) -> bool:
        """
        Force synchronization with exchange data

        Args:
            exchange: Exchange instance (optional, for compatibility)
            balance_manager: Balance manager instance (optional, for compatibility)

        Returns:
            True if sync successful
        """
        try:
            logger.info("[PORTFOLIO_MANAGER] Force syncing with exchange...")

            # Use provided exchange and balance manager if available, otherwise use instance variables
            sync_exchange = exchange or self.exchange
            sync_balance_manager = balance_manager or self.balance_manager

            # Sync balances if balance manager available
            if sync_balance_manager and hasattr(sync_balance_manager, "force_refresh"):
                await sync_balance_manager.force_refresh()

            # Update position tracker with current exchange data
            if hasattr(self.position_tracker, "sync_with_exchange"):
                if sync_exchange:
                    await self.position_tracker.sync_with_exchange(sync_exchange)
                else:
                    await self.position_tracker.sync_with_exchange()

            # Update portfolio value
            current_value = await self._get_portfolio_value()
            if self.config.analytics_enabled:
                self.analytics.record_portfolio_value(current_value)

            logger.info("[PORTFOLIO_MANAGER] Exchange sync completed successfully")
            return True

        except Exception as e:
            logger.error(f"[PORTFOLIO_MANAGER] Error syncing with exchange: {e}")
            return False

    # Context manager support
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()
