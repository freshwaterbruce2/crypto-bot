#!/usr/bin/env python3
"""
Unified State Manager for Kraken Trading System
Eliminates current_position duplication with centralized state persistence
"""

import asyncio
import json
import logging
import shutil
import threading
import time
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from ..config.config_manager import ConfigManager
from ..trading.trading_config import TradingConfig

logger = logging.getLogger(__name__)


class StateManager:
    """
    Unified state management system that eliminates current_position duplication
    Provides centralized state persistence, synchronization, and integrity validation
    """

    # State structure constants
    REQUIRED_STATE_KEYS = {"positions", "orders", "performance", "metadata"}
    MAX_HISTORY_SIZE = 10000
    COMPRESSION_THRESHOLD = 1000
    AUTO_SAVE_DEBOUNCE_SECONDS = 1.0

    def __init__(
        self,
        state_file: str,
        trading_config: TradingConfig,
        config_manager: ConfigManager,
    ):
        """
        Initialize the unified state manager

        Args:
            state_file: Path to the state file for persistence
            trading_config: Trading configuration
            config_manager: Configuration manager
        """
        self.state_file = Path(state_file)
        self.trading_config = trading_config
        self.config_manager = config_manager

        # State storage
        self.state: Dict[str, Any] = {}
        self.state_lock = threading.RLock()
        self.state_callbacks: List[Callable] = []

        # Auto-save settings
        self.auto_save_interval = 30.0  # 30 seconds default
        self.auto_save_task: Optional[asyncio.Task] = None
        self.last_auto_save = 0
        self.pending_changes = False

        # State versioning
        self.current_version = "1.0"
        self.migration_functions = {
            "0.9": self._migrate_from_0_9,
        }

        # Initialize state
        self._initialize_state()
        logger.info(f"StateManager initialized with file: {state_file}")

    def _initialize_state(self):
        """Initialize the state structure with default values"""
        self.state = {
            "positions": {},
            "orders": {},
            "performance": {
                "total_trades": 0,
                "winning_trades": 0,
                "total_pnl": Decimal("0.0"),
                "win_rate": 0.0,
                "avg_trade_pnl": Decimal("0.0"),
                "max_drawdown": Decimal("0.0"),
                "sharpe_ratio": 0.0,
                "best_trade": Decimal("0.0"),
                "worst_trade": Decimal("0.0"),
                "trading_days": 0,
                "avg_daily_pnl": Decimal("0.0"),
            },
            "risk": {
                "daily_pnl": Decimal("0.0"),
                "consecutive_losses": 0,
                "max_daily_loss": Decimal("-50.0"),
                "circuit_breaker_active": False,
                "current_drawdown": Decimal("0.0"),
                "peak_balance": Decimal("0.0"),
                "risk_level": "low",
            },
            "market_data": {
                "last_price": Decimal("0.0"),
                "bid": Decimal("0.0"),
                "ask": Decimal("0.0"),
                "spread": Decimal("0.0"),
                "volume": Decimal("0.0"),
                "volatility": Decimal("0.0"),
                "trend": "unknown",
                "last_update": 0,
            },
            "metadata": {
                "version": self.current_version,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "trading_pair": self.trading_config.pair,
                "total_updates": 0,
                "last_backup": None,
                "integrity_check": True,
            },
        }

    async def load_state(self) -> bool:
        """
        Load state from file with integrity validation and migration

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not self.state_file.exists():
                logger.info("State file does not exist, using default state")
                return True

            # Load state from file
            with open(self.state_file, "r", encoding="utf-8") as f:
                loaded_state = json.load(f)

            # Validate state integrity
            if not self._validate_state_integrity(loaded_state):
                logger.warning("State file corrupted, attempting recovery")
                if not self._recover_from_corruption():
                    logger.error("State recovery failed, using default state")
                    return False

            # Check if migration is needed
            state_version = loaded_state.get("metadata", {}).get("version", "0.0")
            if state_version != self.current_version:
                logger.info(
                    f"Migrating state from version {state_version} to {self.current_version}"
                )
                if not self._migrate_state(loaded_state):
                    logger.error("State migration failed, using default state")
                    return False

            # Load the state
            with self.state_lock:
                self.state = loaded_state

            # Normalize numeric fields that were serialized as strings back to Decimal
            try:
                market_data = self.state.get("market_data", {})
                for k in ["last_price", "bid", "ask", "volume", "volatility"]:
                    if k in market_data and market_data.get(k) is not None:
                        try:
                            market_data[k] = Decimal(str(market_data.get(k)))
                        except Exception:
                            # leave as-is if cannot convert
                            pass

                perf = self.state.get("performance", {})
                for k in ["total_pnl", "avg_trade_pnl", "best_trade", "worst_trade"]:
                    if k in perf and perf.get(k) is not None:
                        try:
                            perf[k] = Decimal(str(perf.get(k)))
                        except Exception:
                            pass

                risk = self.state.get("risk", {})
                if "daily_pnl" in risk and risk.get("daily_pnl") is not None:
                    try:
                        risk["daily_pnl"] = Decimal(str(risk.get("daily_pnl")))
                    except Exception:
                        pass
            except Exception:
                # Best-effort normalization; do not fail load if conversion errors occur
                pass

            logger.info(f"State loaded successfully from {self.state_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False

    async def persist_state(self) -> bool:
        """
        Persist current state to file with backup creation

        Returns:
            True if persisted successfully, False otherwise
        """
        try:
            with self.state_lock:
                # Update metadata
                self.state["metadata"]["last_updated"] = datetime.now().isoformat()
                self.state["metadata"]["total_updates"] += 1

                # Create backup before saving
                if self.state_file.exists():
                    self._create_state_backup()

                # Ensure directory exists
                self.state_file.parent.mkdir(parents=True, exist_ok=True)

                # Persist state
                with open(self.state_file, "w", encoding="utf-8") as f:
                    json.dump(self.state, f, indent=2, default=str)

                self.pending_changes = False
                logger.debug(f"State persisted to {self.state_file}")
                return True

        except Exception as e:
            logger.error(f"Failed to persist state: {e}")
            return False

    def update_position_state(self, position_id: str, position_data: Dict[str, Any]):
        """
        Update position state in the unified state

        Args:
            position_id: Unique position identifier
            position_data: Position data to update
        """
        with self.state_lock:
            # Ensure positions section exists
            if "positions" not in self.state:
                self.state["positions"] = {}

            # Update position
            self.state["positions"][position_id] = position_data.copy()

            # Update metadata
            self.state["metadata"]["total_updates"] += 1

            self.pending_changes = True
            self._notify_callbacks("position_updated", position_data)

    def update_order_state(self, order_id: str, order_data: Dict[str, Any]):
        """
        Update order state in the unified state

        Args:
            order_id: Unique order identifier
            order_data: Order data to update
        """
        with self.state_lock:
            # Ensure orders section exists
            if "orders" not in self.state:
                self.state["orders"] = {}

            # Update order
            self.state["orders"][order_id] = order_data.copy()

            # Update metadata
            self.state["metadata"]["total_updates"] += 1

            self.pending_changes = True
            self._notify_callbacks("order_updated", order_data)

    def update_performance_state(self, performance_data: Dict[str, Any]):
        """
        Update performance metrics in the unified state

        Args:
            performance_data: Performance data to update
        """
        with self.state_lock:
            # Ensure performance section exists
            if "performance" not in self.state:
                self.state["performance"] = {}

            # Update performance metrics
            self.state["performance"].update(performance_data)

            # Update metadata
            self.state["metadata"]["total_updates"] += 1

            self.pending_changes = True
            self._notify_callbacks("performance_updated", performance_data)

    def update_risk_state(self, risk_data: Dict[str, Any]):
        """
        Update risk metrics in the unified state

        Args:
            risk_data: Risk data to update
        """
        with self.state_lock:
            # Ensure risk section exists
            if "risk" not in self.state:
                self.state["risk"] = {}

            # Update risk metrics
            self.state["risk"].update(risk_data)

            # Update metadata
            self.state["metadata"]["total_updates"] += 1

            self.pending_changes = True
            self._notify_callbacks("risk_updated", risk_data)

    async def update_market_data_state(self, market_data: Dict[str, Any]):
        """
        Update market data in the unified state

        Args:
            market_data: Market data to update
        """
        with self.state_lock:
            # Ensure market_data section exists
            if "market_data" not in self.state:
                self.state["market_data"] = {}

            # Update market data
            self.state["market_data"].update(market_data)
            self.state["market_data"]["last_update"] = time.time()

            # Update metadata
            self.state["metadata"]["total_updates"] += 1

            self.pending_changes = True
            self._notify_callbacks("market_data_updated", market_data)
        # Function is async for compatibility with callers that await it; return immediately
        return None

    def get_position_state(self, position_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get position state(s) from unified state

        Args:
            position_id: Specific position ID, or None for all positions

        Returns:
            Position state data
        """
        with self.state_lock:
            if position_id:
                return self.state.get("positions", {}).get(position_id, {})
            else:
                return self.state.get("positions", {})

    def get_order_state(self, order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get order state(s) from unified state

        Args:
            order_id: Specific order ID, or None for all orders

        Returns:
            Order state data
        """
        with self.state_lock:
            if order_id:
                return self.state.get("orders", {}).get(order_id, {})
            else:
                return self.state.get("orders", {})

    def get_performance_state(self) -> Dict[str, Any]:
        """
        Get performance state from unified state

        Returns:
            Performance state data
        """
        with self.state_lock:
            return self.state.get("performance", {})

    def get_risk_state(self) -> Dict[str, Any]:
        """
        Get risk state from unified state

        Returns:
            Risk state data
        """
        with self.state_lock:
            return self.state.get("risk", {})

    async def get_market_data_state(self) -> Dict[str, Any]:
        """
        Get market data state from unified state (async for test compatibility)

        Returns:
            Market data state
        """
        with self.state_lock:
            # Return a shallow copy to avoid external mutation
            return dict(self.state.get("market_data", {}))

    def register_state_change_callback(self, callback: Callable):
        """
        Register a callback for state change notifications

        Args:
            callback: Callback function that takes (change_type, data)
        """
        self.state_callbacks.append(callback)

    def unregister_state_change_callback(self, callback: Callable):
        """
        Unregister a state change callback

        Args:
            callback: Callback function to remove
        """
        if callback in self.state_callbacks:
            self.state_callbacks.remove(callback)

    def _notify_callbacks(self, change_type: str, data: Dict[str, Any]):
        """
        Notify all registered callbacks of state changes

        Args:
            change_type: Type of change (e.g., 'position_updated')
            data: Change data
        """
        for callback in self.state_callbacks:
            try:
                callback(change_type, data)
            except Exception as e:
                logger.error(f"State callback error: {e}")

    async def start_auto_save(self):
        """Start automatic state saving"""
        if self.auto_save_task and not self.auto_save_task.done():
            return

        self.auto_save_task = asyncio.create_task(self._auto_save_loop())
        logger.info(f"Auto-save started with {self.auto_save_interval}s interval")

    async def stop_auto_save(self):
        """Stop automatic state saving"""
        if self.auto_save_task:
            self.auto_save_task.cancel()
            try:
                await self.auto_save_task
            except asyncio.CancelledError:
                pass
            self.auto_save_task = None
            logger.info("Auto-save stopped")

    async def _auto_save_loop(self):
        """Auto-save loop with debouncing"""
        while True:
            try:
                await asyncio.sleep(self.auto_save_interval)

                # Check if there are pending changes
                if (
                    self.pending_changes
                    and (time.time() - self.last_auto_save)
                    >= self.AUTO_SAVE_DEBOUNCE_SECONDS
                ):
                    await self.persist_state()
                    self.last_auto_save = time.time()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-save error: {e}")

    def _validate_state_integrity(self, state: Dict[str, Any]) -> bool:
        """
        Validate state structure integrity

        Args:
            state: State dictionary to validate

        Returns:
            True if state is valid, False otherwise
        """
        try:
            # Check required keys
            if not all(key in state for key in self.REQUIRED_STATE_KEYS):
                return False

            # Validate metadata
            metadata = state.get("metadata", {})
            if not isinstance(metadata, dict):
                return False

            # Validate version
            version = metadata.get("version")
            if not version or not isinstance(version, str):
                return False

            # Validate positions
            positions = state.get("positions", {})
            if not isinstance(positions, dict):
                return False

            # Validate orders
            orders = state.get("orders", {})
            if not isinstance(orders, dict):
                return False

            # Validate performance
            performance = state.get("performance", {})
            if not isinstance(performance, dict):
                return False

            return True

        except Exception as e:
            logger.error(f"State integrity validation error: {e}")
            return False

    def _recover_from_corruption(self) -> bool:
        """
        Attempt to recover from corrupted state file

        Returns:
            True if recovery successful, False otherwise
        """
        try:
            # Try to load from backup
            backup_files = list(
                self.state_file.parent.glob(f"{self.state_file.stem}*backup*.json")
            )
            if backup_files:
                # Sort by modification time, get most recent
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_backup = backup_files[0]

                logger.info(f"Attempting recovery from backup: {latest_backup}")
                with open(latest_backup, "r", encoding="utf-8") as f:
                    backup_state = json.load(f)

                if self._validate_state_integrity(backup_state):
                    # Copy backup to main state file
                    shutil.copy2(latest_backup, self.state_file)
                    logger.info("State recovered from backup")
                    return True

            # If no valid backup, reinitialize
            logger.warning("No valid backup found, reinitializing state")
            self._initialize_state()
            return True

        except Exception as e:
            logger.error(f"State recovery error: {e}")
            return False

    def _migrate_state(self, state: Dict[str, Any]) -> bool:
        """
        Migrate state from older version to current version

        Args:
            state: State to migrate

        Returns:
            True if migration successful, False otherwise
        """
        try:
            current_version = state.get("metadata", {}).get("version", "0.0")

            # Apply migrations in order
            while current_version != self.current_version:
                if current_version in self.migration_functions:
                    migration_func = self.migration_functions[current_version]
                    state = migration_func(state)
                    current_version = state.get("metadata", {}).get("version", "0.0")
                else:
                    logger.error(f"No migration function for version {current_version}")
                    return False

            return True

        except Exception as e:
            logger.error(f"State migration error: {e}")
            return False

    def _migrate_from_0_9(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate state from version 0.9 to 1.0

        Args:
            state: State in version 0.9 format

        Returns:
            State in version 1.0 format
        """
        # Add missing sections
        if "metadata" not in state:
            state["metadata"] = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "trading_pair": self.trading_config.pair,
                "total_updates": 0,
            }
        else:
            state["metadata"]["version"] = "1.0"

        # Add risk section if missing
        if "risk" not in state:
            state["risk"] = {
                "daily_pnl": Decimal("0.0"),
                "consecutive_losses": 0,
                "max_daily_loss": Decimal("-50.0"),
                "circuit_breaker_active": False,
            }

        # Add market_data section if missing
        if "market_data" not in state:
            state["market_data"] = {
                "last_price": Decimal("0.0"),
                "bid": Decimal("0.0"),
                "ask": Decimal("0.0"),
                "spread": Decimal("0.0"),
                "volume": Decimal("0.0"),
                "last_update": 0,
            }

        return state

    def _create_state_backup(self) -> str:
        """
        Create a backup of the current state file

        Returns:
            Path to the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{self.state_file.stem}_backup_{timestamp}.json"
        backup_path = self.state_file.parent / backup_filename

        shutil.copy2(self.state_file, backup_path)

        # Update metadata
        self.state["metadata"]["last_backup"] = datetime.now().isoformat()

        logger.debug(f"State backup created: {backup_path}")
        return str(backup_path)

    def _compress_old_state(self, max_orders: int = 1000):
        """
        Compress old state data to prevent file size bloat

        Args:
            max_orders: Maximum number of orders to keep
        """
        with self.state_lock:
            orders = self.state.get("orders", {})

            if len(orders) > max_orders:
                # Sort orders by timestamp, keep most recent
                sorted_orders = sorted(
                    orders.items(), key=lambda x: x[1].get("timestamp", 0), reverse=True
                )

                # Keep only the most recent orders
                compressed_orders = dict(sorted_orders[:max_orders])
                self.state["orders"] = compressed_orders

                logger.info(
                    f"Compressed orders from {len(orders)} to {len(compressed_orders)}"
                )

    def generate_state_analytics(self) -> Dict[str, Any]:
        """
        Generate analytics and insights from current state

        Returns:
            Analytics dictionary
        """
        with self.state_lock:
            analytics = {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_trade_pnl": Decimal("0.0"),
                "total_pnl": Decimal("0.0"),
                "best_trade": Decimal("0.0"),
                "worst_trade": Decimal("0.0"),
                "active_positions": len(self.state.get("positions", {})),
                "pending_orders": len(
                    [
                        o
                        for o in self.state.get("orders", {}).values()
                        if o.get("status") == "pending"
                    ]
                ),
                "best_performing_pair": self.trading_config.pair,
                "current_risk_level": self.state.get("risk", {}).get(
                    "risk_level", "unknown"
                ),
                "market_condition": self.state.get("market_data", {}).get(
                    "trend", "unknown"
                ),
            }

            # Calculate trade statistics
            orders = self.state.get("orders", {})
            completed_trades = [
                o
                for o in orders.values()
                if o.get("status") == "filled" and "pnl_usd" in o
            ]

            if completed_trades:
                analytics["total_trades"] = len(completed_trades)

                pnls = [Decimal(str(t.get("pnl_usd", "0"))) for t in completed_trades]
                winning_trades = [p for p in pnls if p > 0]

                analytics["win_rate"] = len(winning_trades) / len(completed_trades)
                analytics["total_pnl"] = sum(pnls)
                analytics["avg_trade_pnl"] = analytics["total_pnl"] / len(
                    completed_trades
                )
                analytics["best_trade"] = max(pnls)
                analytics["worst_trade"] = min(pnls)

            return analytics

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current state

        Returns:
            State summary dictionary
        """
        with self.state_lock:
            return {
                "positions_count": len(self.state.get("positions", {})),
                "orders_count": len(self.state.get("orders", {})),
                "total_pnl": self.state.get("performance", {}).get(
                    "total_pnl", Decimal("0.0")
                ),
                "win_rate": self.state.get("performance", {}).get("win_rate", 0.0),
                "risk_level": self.state.get("risk", {}).get("risk_level", "unknown"),
                "last_updated": self.state.get("metadata", {}).get("last_updated"),
                "version": self.state.get("metadata", {}).get("version"),
                "pending_changes": self.pending_changes,
            }

    def clear_state(self, preserve_metadata: bool = True):
        """
        Clear the state, optionally preserving metadata

        Args:
            preserve_metadata: Whether to preserve metadata section
        """
        with self.state_lock:
            metadata = self.state.get("metadata", {}) if preserve_metadata else {}

            # Reinitialize state
            self._initialize_state()

            # Restore metadata if requested
            if preserve_metadata and metadata:
                self.state["metadata"] = metadata

            self.pending_changes = True
            logger.info("State cleared")

    def export_state(self, export_path: str) -> bool:
        """
        Export current state to a file

        Args:
            export_path: Path to export state to

        Returns:
            True if exported successfully, False otherwise
        """
        try:
            with self.state_lock:
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(self.state, f, indent=2, default=str)

            logger.info(f"State exported to {export_path}")
            return True

        except Exception as e:
            logger.error(f"State export error: {e}")
            return False

    def import_state(self, import_path: str) -> bool:
        """
        Import state from a file

        Args:
            import_path: Path to import state from

        Returns:
            True if imported successfully, False otherwise
        """
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                imported_state = json.load(f)

            if self._validate_state_integrity(imported_state):
                with self.state_lock:
                    self.state = imported_state
                    self.pending_changes = True

                logger.info(f"State imported from {import_path}")
                return True
            else:
                logger.error("Imported state failed integrity validation")
                return False

        except Exception as e:
            logger.error(f"State import error: {e}")
            return False
