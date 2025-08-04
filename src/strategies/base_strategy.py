"""
Base Strategy - 2025 Optimized Abstract Base Class with Portfolio Intelligence

Provides a modern, type-safe foundation for all trading strategies with:
- Portfolio Intelligence integration for deployed capital awareness
- Learning Manager integration for minimum trade validation
- Self-healing and self-optimizing capabilities
- Comprehensive error handling and validation
- Performance monitoring and lifecycle management
"""

import asyncio
import time
import pandas as pd
import numpy as np
from ..signal_generation_mixin import SignalGenerationMixin
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import logging
import traceback
import math
import random

# Custom imports
from ..utils.alert_manager import AlertManager, AlertCategory
from ..utils.custom_logging import configure_logging
logger = configure_logging()


class BaseStrategy(SignalGenerationMixin, ABC):
    """
    Abstract base class that all trading strategies must inherit from.
    
    Enhanced with:
    - Portfolio Intelligence for capital deployment awareness
    - Learning Manager for trade validation
    - Self-healing error recovery
    - Dynamic risk adjustment
    """

    POSSIBLE_STATUSES = [
        "Initializing",
        "Ready",
        "Active",
        "Paused",
        "Error",
        "Stopped",
        "FundsDeployed",  # New status for when capital is working elsewhere
        "FundsFreed",     # New status for when capital has been freed through reallocation
        "LowBalance"      # New status for truly insufficient funds
    ]

    def __init__(
        self,
        name: str,
        exchange: Any,
        symbol: str,
        stop_loss_pct: float = 0.008,   # 0.8% stop loss for $5+ positions (2025 update)
        take_profit_pct: float = 0.005,  # 0.5% default optimized for Pro fee-free accounts
        position_side: str = "long_only",
        order_size_usdt: float = 5.0,  # Updated for 2025 Kraken $5 minimum compliance
        min_candles: int = 5,
        status_update_callback: Optional[Callable[[str, str, str, Dict], None]] = None,
        bot_reference: Optional[Any] = None,  # Reference to main bot for component access
        **kwargs,
    ):
        """
        Initialize the base strategy with portfolio intelligence.

        Args:
            name: Name of the strategy
            exchange: Exchange client instance
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            stop_loss_pct: Stop loss percentage (default: 0.8% for micro-profits)
            take_profit_pct: Take profit percentage (default: 0.5% for quick wins)
            position_side: Type of positions to take ('long_only', 'short_only', 'both')
            order_size_usdt: Default order size in USDT
            min_candles: Minimum number of candles required for strategy to be ready
            status_update_callback: Optional callback for status changes
            bot_reference: Reference to main bot for accessing shared components
        """
        self.name = name
        self.exchange = exchange
        self.symbol = symbol
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.position_side = position_side
        self.order_size_usdt = order_size_usdt
        self.min_candles = min_candles
        self.status_update_callback = status_update_callback
        self.bot_reference = bot_reference
        self._last_price = None
        self.trade_size_multiplier = 1.0

        # Portfolio Intelligence Integration
        self.portfolio_intelligence = None
        self.balance_manager = None
        self.learning_manager = None
        self.analytics_assistant = None
        self.websocket_manager = None  # WebSocket V2 for real-time prices
        self._initialize_components()

        # Enhanced state tracking
        self.status = "Unknown"
        self.data = []
        self.deployed_capital = {}  # Track where capital is deployed
        self.minimum_requirements = {}  # Learned minimum trade requirements
        self.error_recovery_attempts = 0
        self.max_error_recovery_attempts = 3
        
        # Alert management
        self.alert_manager = AlertManager(max_alerts=1000)

        self._waiting_for_data = True
        self._has_sufficient_data = False
        self._last_update_time = None
        self._last_portfolio_check = 0
        self._portfolio_check_interval = 30  # Check every 30 seconds

        self._change_status("Initializing")
        self._on_initialized()

    def _initialize_components(self) -> None:
        """Initialize connections to shared components through bot reference."""
        if self.bot_reference:
            try:
                # Access components through bot reference
                if hasattr(self.bot_reference, 'components'):
                    components = self.bot_reference.components
                    
                    # Portfolio Intelligence
                    if hasattr(components, 'portfolio_intelligence'):
                        self.portfolio_intelligence = components.portfolio_intelligence
                        logger.info(f"[{self.symbol}] Connected to Portfolio Intelligence")
                    
                    # Balance Manager
                    if hasattr(components, 'balance_manager'):
                        self.balance_manager = components.balance_manager
                        logger.info(f"[{self.symbol}] Connected to Balance Manager")
                    
                    # Learning Manager
                    if hasattr(components, 'learning_manager'):
                        self.learning_manager = components.learning_manager
                        logger.info(f"[{self.symbol}] Connected to Learning Manager")
                    
                    # Analytics Assistant
                    if hasattr(components, 'analytics_assistant'):
                        self.analytics_assistant = components.analytics_assistant
                        logger.info(f"[{self.symbol}] Connected to Analytics Assistant")
                
                # WebSocket Manager (not in components, but in bot directly)
                if hasattr(self.bot_reference, 'websocket_manager'):
                    self.websocket_manager = self.bot_reference.websocket_manager
                    logger.info(f"[{self.symbol}] Connected to WebSocket V2 Manager")
                        
            except Exception as e:
                logger.warning(f"[{self.symbol}] Error initializing components: {e}")

    def _on_initialized(self) -> None:
        """Lifecycle hook called after strategy is initialized."""
        logger.info(f"[{self.symbol}] Strategy '{self.name}' initialized with portfolio intelligence.")
        
        # Load learned minimum requirements if available
        if self.learning_manager:
            self._load_learned_minimums()
        
        # For sell engines, immediately transition to Ready since they don't need OHLC history
        if "SellEngine" in self.name and len(self.data) == 0:
            logger.info(f"[{self.symbol}] Sell engine transitioning directly to Ready")
            self._change_status("Ready")

    def _load_learned_minimums(self) -> None:
        """Load learned minimum trade requirements from learning manager."""
        try:
            if self.learning_manager and hasattr(self.learning_manager, 'get_learned_minimums'):
                self.minimum_requirements = self.learning_manager.get_learned_minimums(self.symbol)
                logger.info(f"[{self.symbol}] Loaded minimum requirements: {self.minimum_requirements}")
        except Exception as e:
            logger.warning(f"[{self.symbol}] Error loading learned minimums: {e}")

    def _on_data_sufficient(self) -> None:
        """Lifecycle hook called when sufficient data is available and strategy becomes Ready."""
        logger.info(
            f"[{self.symbol}] Strategy '{self.name}' has sufficient data and is now Ready."
        )
        
        # Perform initial portfolio check
        asyncio.create_task(self._check_portfolio_status())

    def _on_status_changed(self, old_status: str, new_status: str) -> None:
        """Lifecycle hook called when strategy status changes."""
        logger.info(
            f"[{self.symbol}] Strategy '{self.name}' status changed: {old_status} -> {new_status}"
        )
        
        # Track status changes for learning
        if self.learning_manager:
            try:
                self.learning_manager.record_event(
                    event_type="strategy_status_change",
                    component=self.name,
                    success=True,
                    details={
                        "symbol": self.symbol,
                        "old_status": old_status,
                        "new_status": new_status,
                        "timestamp": time.time()
                    }
                )
            except Exception as e:
                logger.debug(f"[{self.symbol}] Error recording status change: {e}")
        
        if self.status_update_callback:
            try:
                self.status_update_callback(
                    self.symbol, old_status, new_status, self.get_status()
                )
            except Exception as e:
                logger.error(
                    f"[{self.symbol}] Error in status_update_callback: {e}",
                    exc_info=True,
                )

    def _change_status(self, new_status: str):
        """Centralized method to change strategy status and trigger hooks."""
        if new_status not in self.POSSIBLE_STATUSES:
            logger.error(
                f"[{self.symbol}] Attempted to set invalid status: {new_status}"
            )
            return

        old_status = self.status
        if old_status != new_status:
            self.status = new_status
            self._on_status_changed(old_status, new_status)
            if new_status == "Ready":
                self._on_data_sufficient()
            elif new_status == "Error":
                asyncio.create_task(self._handle_error_state())

    async def _handle_error_state(self) -> None:
        """Handle error state with self-healing capabilities."""
        if self.error_recovery_attempts < self.max_error_recovery_attempts:
            self.error_recovery_attempts += 1
            logger.info(
                f"[{self.symbol}] Attempting error recovery "
                f"({self.error_recovery_attempts}/{self.max_error_recovery_attempts})"
            )
            
            await asyncio.sleep(5 * self.error_recovery_attempts)  # Exponential backoff
            
            # Try to reinitialize
            self._initialize_components()
            self._change_status("Initializing")
        else:
            logger.error(
                f"[{self.symbol}] Max error recovery attempts reached. "
                "Manual intervention required."
            )

    def _check_and_update_status(self):
        """Checks if conditions are met to change status (e.g., Initializing -> Ready)."""
        if self.status == "Initializing" and not self._has_sufficient_data:
            # For sell engines, no historical data needed - transition immediately
            if "SellEngine" in self.name:
                self._has_sufficient_data = True
                self._change_status("Ready")
                logger.info(f"[{self.symbol}] Sell engine ready without historical data requirement")
            # For trading strategies, need minimum candles
            elif len(self.data) >= self.min_candles:
                self._has_sufficient_data = True
                self._change_status("Ready")
                logger.info(f"[{self.symbol}] Trading strategy ready with {len(self.data)} candles")

    async def _check_portfolio_status(self) -> None:
        """Check portfolio status to determine if funds are deployed or truly insufficient."""
        try:
            current_time = time.time()
            if current_time - self._last_portfolio_check < self._portfolio_check_interval:
                return
                
            self._last_portfolio_check = current_time
            
            if self.balance_manager:
                # Get USDT balance
                usdt_balance = await self.get_balance("USDT")
                
                if usdt_balance < 10.0:  # Below typical minimum
                    # Check if funds are deployed
                    deployment_status = await self.balance_manager.get_deployment_status("USDT")
                    
                    if deployment_status == 'funds_deployed':
                        self._change_status("FundsDeployed")
                        
                        # Get reallocation opportunities
                        realloc_opps = await self.balance_manager.get_reallocation_opportunities("USDT")
                        
                        if realloc_opps:
                            logger.info(
                                f"[{self.symbol}] Capital deployed. "
                                f"Found {len(realloc_opps)} reallocation opportunities."
                            )
                            
                            # Alert about deployed capital
                            self.alert_manager.info(
                                category=AlertCategory.STRATEGY,
                                message=f"Capital deployed in {len(realloc_opps)} positions",
                                data={"reallocation_opportunities": len(realloc_opps), "symbol": self.symbol}
                            )
                            
                            # Execute strategic reallocation if autonomous sell engine is available
                            if hasattr(self, 'autonomous_sell_engine') and self.autonomous_sell_engine:
                                reallocation_plan = []
                                for i, opp in enumerate(realloc_opps[:3]):  # Top 3 opportunities
                                    reallocation_plan.append({
                                        'action_type': 'reallocation_sell',
                                        'symbol': f"{opp['asset']}/USDT",
                                        'priority': i + 1,
                                        'reason': f"Strategic reallocation for better opportunities",
                                        'target_proceeds': opp['value_in_currency'],
                                        'urgency': 'medium'
                                    })
                                
                                if reallocation_plan:
                                    logger.info(f"[{self.symbol}] Executing reallocation plan with {len(reallocation_plan)} actions")
                                    try:
                                        realloc_result = await self.autonomous_sell_engine.execute_reallocation_plan(reallocation_plan)
                                        
                                        if realloc_result.get('successful_sales', 0) > 0:
                                            logger.info(f"[{self.symbol}] [OK] Reallocated ${realloc_result.get('total_proceeds', 0):.2f} from underperforming assets")
                                            # Update status to reflect successful reallocation
                                            self._change_status("FundsFreed")
                                        else:
                                            logger.warning(f"[{self.symbol}] Reallocation execution failed")
                                    except Exception as e:
                                        logger.error(f"[{self.symbol}] Error executing reallocation plan: {e}")
                            else:
                                logger.debug(f"[{self.symbol}] No autonomous sell engine available for reallocation")
                    else:
                        self._change_status("LowBalance")
                        logger.warning(f"[{self.symbol}] Truly insufficient funds. Deposits needed.")
                        
        except Exception as e:
            logger.error(f"[{self.symbol}] Error checking portfolio status: {e}")

    async def receive_market_data(self, data_point: Any):
        """
        Method for the strategy to receive new market data points.
        Enhanced with portfolio status checks.
        """
        if isinstance(self.data, list):
            self.data.append(data_point)
            
            # Keep only recent data to prevent memory issues
            if len(self.data) > 1000:
                self.data = self.data[-500:]  # Keep last 500 points
        else:
            logger.warning(
                f"[{self.symbol}] self.data is not a list. Data point not appended by BaseStrategy."
            )

        # Update timestamp
        if hasattr(data_point, "get") and data_point.get("timestamp"):
            self._last_update_time = data_point.get("timestamp")
        elif hasattr(data_point, "timestamp"):
            self._last_update_time = data_point.timestamp
        else:
            self._last_update_time = time.time()

        self._check_and_update_status()
        
        # Periodic portfolio check
        await self._check_portfolio_status()

    async def process_ohlc(self, ohlc_data: Any) -> Any:
        """
        Process OHLC data for strategy analysis with error recovery.
        """
        try:
            logger.debug(
                f"[{self.symbol}] BaseStrategy.process_ohlc called with data type: {type(ohlc_data)}"
            )

            # Update internal state for compatibility
            if hasattr(ohlc_data, "iloc") and len(ohlc_data) > 0:
                try:
                    last_row = ohlc_data.iloc[-1]
                    data_point = {
                        "timestamp": getattr(last_row, "name", time.time()),
                        "close": (
                            last_row.get("close", 0) if hasattr(last_row, "get") else 0
                        ),
                        "volume": (
                            last_row.get("volume", 0) if hasattr(last_row, "get") else 0
                        ),
                        "high": (
                            last_row.get("high", 0) if hasattr(last_row, "get") else 0
                        ),
                        "low": (
                            last_row.get("low", 0) if hasattr(last_row, "get") else 0
                        ),
                    }
                    await self.receive_market_data(data_point)
                except Exception as e:
                    logger.debug(
                        f"[{self.symbol}] Error extracting data point from OHLC: {e}"
                    )

            # Reset error counter on successful processing
            if self.error_recovery_attempts > 0:
                self.error_recovery_attempts = 0

            return ohlc_data
            
        except Exception as e:
            logger.error(f"[{self.symbol}] Error processing OHLC data: {e}")
            self._change_status("Error")
            return None

    @abstractmethod
    async def generate_signals(
        self, market_data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Generate trading signals based on market data.
        Must be implemented by subclasses.
        """
        pass

    async def validate_signal_with_portfolio(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate signal with portfolio intelligence before execution.
        
        Args:
            signal: Trading signal to validate
            
        Returns:
            Enhanced signal with portfolio validation
        """
        try:
            if not signal or signal.get("action") is None:
                return signal
                
            # Check if we're in FundsDeployed state
            if self.status == "FundsDeployed":
                # Check signal confidence
                confidence = signal.get("strength", 0.0)
                
                if confidence < 0.75:  # High confidence threshold for reallocation
                    logger.info(
                        f"[{self.symbol}] Signal confidence {confidence:.2f} "
                        "too low for capital reallocation"
                    )
                    signal["metadata"]["portfolio_blocked"] = True
                    signal["metadata"]["reason"] = "Low confidence for reallocation"
                    signal["action"] = None  # Block the signal
                else:
                    signal["metadata"]["reallocation_candidate"] = True
                    
            # Validate minimum requirements
            if self.portfolio_intelligence and signal.get("action") == "BUY":
                validation = await self.portfolio_intelligence.validate_trade_minimums(
                    symbol=self.symbol,
                    quote_amount=signal.get("size", self.order_size_usdt),
                    current_price=signal.get("price", self._last_price)
                )
                
                if validation and validation.get("needs_adjustment"):
                    signal["size"] = validation["safe_quote_cost"]
                    signal["metadata"]["size_adjusted"] = True
                    signal["metadata"]["original_size"] = self.order_size_usdt
                    
            return signal
            
        except Exception as e:
            logger.error(f"[{self.symbol}] Error validating signal with portfolio: {e}")
            return signal

    def get_risk_params(self) -> Tuple[float, float]:
        """Get the risk parameters for this strategy."""
        return (self.stop_loss_pct, self.take_profit_pct)

    def set_risk_params(
        self,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
    ) -> None:
        """Update the risk parameters for this strategy."""
        if stop_loss_pct is not None:
            self.stop_loss_pct = stop_loss_pct
        if take_profit_pct is not None:
            self.take_profit_pct = take_profit_pct

        logger.info(
            f"Updated risk parameters for {self.name}: "
            f"SL={self.stop_loss_pct:.2%}, TP={self.take_profit_pct:.2%}"
        )
        
        # Record parameter update for learning
        if self.learning_manager:
            self.learning_manager.record_event(
                event_type="risk_params_updated",
                component=self.name,
                success=True,
                details={
                    "symbol": self.symbol,
                    "stop_loss_pct": self.stop_loss_pct,
                    "take_profit_pct": self.take_profit_pct
                }
            )

    async def get_balance(self, currency: str) -> float:
        """
        Get balance for a specific currency with caching.
        """
        try:
            # Use balance manager if available for cached results
            if self.balance_manager and hasattr(self.balance_manager, 'get_cached_balance'):
                cached = self.balance_manager.get_cached_balance(currency)
                if cached is not None:
                    return cached
                    
            # Fallback to direct exchange query
            balance = await self.exchange.fetch_balance()
            if currency in balance:
                return float(balance[currency]["free"])
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching {currency} balance: {e}")
            return 0.0

    async def get_price(self, symbol: Optional[str] = None) -> Optional[float]:
        """Get the current price for the trading pair from WebSocket V2."""
        try:
            symbol = symbol or self.symbol
            
            # Try WebSocket V2 first
            if self.websocket_manager:
                ticker = await self.websocket_manager.get_ticker(symbol)
                if ticker and 'last' in ticker:
                    self._last_price = float(ticker['last'])
                    return self._last_price
                else:
                    logger.debug(f"[{self.symbol}] No WebSocket price for {symbol}")
            
            # NO FALLBACK to REST API - only use real-time data
            logger.warning(f"[{self.symbol}] No real-time price available for {symbol}")
            return self._last_price
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return self._last_price

    def cleanup(self) -> None:
        """
        Perform cleanup operations when shutting down the strategy.
        """
        logger.info(f"Cleaning up resources for strategy: {self.name}")
        
        # Save learned parameters
        if self.learning_manager and self.minimum_requirements:
            try:
                self.learning_manager.save_learned_minimums(
                    self.symbol, 
                    self.minimum_requirements
                )
            except Exception as e:
                logger.error(f"Error saving learned minimums: {e}")
        
        # Clear data to free memory
        self.data = []
        self.deployed_capital = {}
        
        # Update final status
        self._change_status("Stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the strategy with enhanced portfolio info."""
        status = {
            "name": self.name,
            "symbol": self.symbol,
            "status": self.status,
            "position_side": self.position_side,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "order_size_usdt": self.order_size_usdt,
            "trade_size_multiplier": self.trade_size_multiplier,
            "_has_sufficient_data": self._has_sufficient_data,
            "data_points_collected": len(self.data) if isinstance(self.data, list) else -1,
            "min_data_points_required": self.min_candles,
            "last_update": (
                datetime.fromtimestamp(self._last_update_time).isoformat()
                if isinstance(self._last_update_time, (int, float))
                else str(self._last_update_time)
            ),
            "error_recovery_attempts": self.error_recovery_attempts,
            "portfolio_aware": self.portfolio_intelligence is not None,
            "balance_manager_connected": self.balance_manager is not None,
            "learning_enabled": self.learning_manager is not None
        }
        
        # Add portfolio-specific status if in FundsDeployed state
        if self.status == "FundsDeployed":
            status["deployed_capital_info"] = {
                "status": "Capital deployed in other positions",
                "recommendation": "Wait for profitable exits or high-confidence signals"
            }
        elif self.status == "LowBalance":
            status["low_balance_info"] = {
                "status": "Insufficient funds for trading",
                "recommendation": "Deposit funds to resume trading"
            }
            
        return status
    
    def is_ready(self) -> bool:
        """
        Check if strategy is ready to trade.
        
        Returns:
            bool: True if strategy is ready, False otherwise
        """
        return self.status == "Ready"

    def log_price_movement(self, movement_pct: float):
        """Log significant price movements using AlertManager."""
        message = f"MAJOR PRICE MOVEMENT: {movement_pct:.2f}%"
        self.alert_manager.info(
            category=AlertCategory.TRADING,
            message=message,
            data={"movement_percentage": round(movement_pct, 2), "symbol": self.symbol}
        )

    def set_trade_size_multiplier(self, multiplier: float) -> None:
        """Set the trade size multiplier for dynamic risk adjustment."""
        self.trade_size_multiplier = float(multiplier)
        logger.info(
            f"[RISK] Trade size multiplier for {self.name} set to "
            f"{self.trade_size_multiplier:.2f}"
        )

    def get_trade_size(self, base_size: float) -> float:
        """Return the adjusted trade size based on the multiplier."""
        adjusted_size = base_size * self.trade_size_multiplier
        
        # Ensure minimum trade size requirements
        if self.minimum_requirements:
            min_cost = self.minimum_requirements.get("min_cost", 0)
            if adjusted_size < min_cost:
                logger.info(
                    f"[{self.symbol}] Adjusting trade size from {adjusted_size:.2f} "
                    f"to minimum {min_cost:.2f}"
                )
                adjusted_size = min_cost
                
        return adjusted_size

    def update_risk_parameters(
        self,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        trade_size_multiplier: Optional[float] = None,
    ) -> None:
        """Update risk parameters dynamically with validation."""
        if stop_loss_pct is not None:
            # Validate stop loss is reasonable
            if 0.001 <= stop_loss_pct <= 0.1:  # 0.1% to 10%
                self.stop_loss_pct = stop_loss_pct
            else:
                logger.warning(f"Invalid stop_loss_pct: {stop_loss_pct}, keeping current value")
                
        if take_profit_pct is not None:
            # Validate take profit is reasonable
            if 0.001 <= take_profit_pct <= 0.2:  # 0.1% to 20%
                self.take_profit_pct = take_profit_pct
            else:
                logger.warning(f"Invalid take_profit_pct: {take_profit_pct}, keeping current value")
                
        if trade_size_multiplier is not None:
            # Validate multiplier is reasonable
            if 0.1 <= trade_size_multiplier <= 3.0:  # 10% to 300%
                self.set_trade_size_multiplier(trade_size_multiplier)
            else:
                logger.warning(
                    f"Invalid trade_size_multiplier: {trade_size_multiplier}, "
                    "keeping current value"
                )
                
        logger.info(
            f"[RISK] Updated risk parameters for {self.name}: "
            f"SL={self.stop_loss_pct:.2%}, TP={self.take_profit_pct:.2%}, "
            f"Multiplier={self.trade_size_multiplier:.2f}"
        )

    async def should_trade(self) -> bool:
        """
        Determine if the strategy should be allowed to trade.
        Checks various conditions including portfolio status.
        """
        # Basic checks
        if self.status not in ["Ready", "Active", "FundsDeployed"]:
            return False
            
        # If funds are deployed, only trade on high confidence signals
        if self.status == "FundsDeployed":
            # This will be evaluated when generate_signals is called
            return True
            
        # Check if we have sufficient balance
        usdt_balance = await self.get_balance("USDT")
        if usdt_balance < self.order_size_usdt * 0.5:  # Need at least half the order size
            await self._check_portfolio_status()  # Update status
            return self.status == "FundsDeployed"  # Can still trade if funds deployed
            
        return True

    def record_trade_attempt(self, success: bool, details: Dict[str, Any]) -> None:
        """Record trade attempt for learning purposes."""
        if self.learning_manager:
            try:
                self.learning_manager.record_event(
                    event_type="trade_attempt",
                    component=self.name,
                    success=success,
                    details={
                        "symbol": self.symbol,
                        "timestamp": time.time(),
                        **details
                    }
                )
            except Exception as e:
                logger.debug(f"Error recording trade attempt: {e}")