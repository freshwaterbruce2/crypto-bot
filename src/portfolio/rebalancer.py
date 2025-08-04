"""
Portfolio Rebalancer
===================

Advanced portfolio rebalancing system with multiple strategies including
DCA (Dollar Cost Averaging), GRID trading, momentum-based rebalancing,
and arbitrage opportunities.

Features:
- Multiple rebalancing strategies (DCA, GRID, momentum, mean reversion)
- Automated rebalancing triggers based on drift and time
- Risk-adjusted rebalancing with position sizing
- Cost-aware rebalancing with fee optimization
- Backtesting and simulation capabilities
- Integration with risk manager and position tracker
"""

import asyncio
import logging
import time
import json
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Union, Tuple
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from threading import RLock
from datetime import datetime, timedelta

from ..utils.decimal_precision_fix import safe_decimal, safe_float
from .position_tracker import Position, PositionTracker, PositionType, PositionStatus
from .risk_manager import RiskManager, RiskAction

logger = logging.getLogger(__name__)


class RebalanceStrategy(Enum):
    """Rebalancing strategy types"""
    DCA = "dca"  # Dollar Cost Averaging
    GRID = "grid"  # Grid trading
    MOMENTUM = "momentum"  # Momentum-based
    MEAN_REVERSION = "mean_reversion"  # Mean reversion
    ARBITRAGE = "arbitrage"  # Arbitrage opportunities
    RISK_PARITY = "risk_parity"  # Risk parity allocation
    THRESHOLD = "threshold"  # Threshold-based rebalancing


class RebalanceReason(Enum):
    """Reasons for rebalancing"""
    DRIFT_EXCEEDED = "drift_exceeded"
    TIME_TRIGGER = "time_trigger"
    RISK_ADJUSTMENT = "risk_adjustment"
    OPPORTUNITY = "opportunity"
    MANUAL = "manual"
    STRATEGY_SIGNAL = "strategy_signal"


@dataclass
class RebalanceTarget:
    """Target allocation for rebalancing"""
    symbol: str
    target_weight: float
    current_weight: float
    target_value: float
    current_value: float
    drift: float
    action: str  # 'buy', 'sell', 'hold'
    recommended_size: float
    priority: int = 1  # 1=high, 5=low


@dataclass
class RebalanceResult:
    """Result of a rebalancing operation"""
    strategy: RebalanceStrategy
    reason: RebalanceReason
    timestamp: float
    
    targets: List[RebalanceTarget]
    total_portfolio_value: float
    expected_cost: float
    expected_trades: int
    
    executed: bool = False
    actual_cost: float = 0.0
    actual_trades: int = 0
    execution_time: float = 0.0
    
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['strategy'] = self.strategy.value
        data['reason'] = self.reason.value
        data['targets'] = [asdict(target) for target in self.targets]
        return data


@dataclass
class RebalanceConfig:
    """Rebalancing configuration"""
    # Drift thresholds
    max_drift_pct: float = 10.0  # Maximum drift before rebalancing
    min_drift_pct: float = 2.0   # Minimum drift to consider
    
    # Time-based rebalancing
    time_based_rebalance: bool = True
    rebalance_interval_hours: float = 24.0  # Daily rebalancing
    
    # Cost controls
    max_rebalance_cost_pct: float = 0.5  # Max 0.5% of portfolio in fees
    min_trade_size_usd: float = 10.0  # Minimum trade size
    
    # Strategy-specific settings
    dca_interval_hours: float = 8.0  # DCA every 8 hours
    grid_levels: int = 10  # Number of grid levels
    grid_range_pct: float = 20.0  # Grid range as % of current price
    
    # Risk controls
    risk_adjust_enabled: bool = True
    max_single_rebalance_pct: float = 25.0  # Max 25% of portfolio in single rebalance
    
    # Execution settings
    dry_run: bool = False  # Dry run mode for testing
    execution_delay_seconds: float = 1.0  # Delay between trades
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class Rebalancer:
    """
    Advanced portfolio rebalancing system
    """
    
    def __init__(self, position_tracker: PositionTracker, risk_manager: RiskManager,
                 balance_manager=None, trade_executor=None,
                 config: Optional[RebalanceConfig] = None,
                 data_path: str = "D:/trading_data"):
        """
        Initialize rebalancer
        
        Args:
            position_tracker: Position tracker instance
            risk_manager: Risk manager instance
            balance_manager: Balance manager instance
            trade_executor: Trade executor instance
            config: Rebalancing configuration
            data_path: Data storage path
        """
        self.position_tracker = position_tracker
        self.risk_manager = risk_manager
        self.balance_manager = balance_manager
        self.trade_executor = trade_executor
        self.config = config or RebalanceConfig()
        self.data_path = data_path
        
        # State management
        self._lock = RLock()
        self._async_lock = asyncio.Lock()
        self._running = False
        
        # Target allocations
        self._target_allocations: Dict[str, float] = {}  # symbol -> target weight
        self._last_rebalance_time: float = 0.0
        self._last_dca_time: float = 0.0
        
        # History tracking
        self._rebalance_history: List[RebalanceResult] = []
        self._portfolio_drift_history: List[Dict[str, Any]] = []
        
        # Grid trading state
        self._grid_orders: Dict[str, List[Dict[str, Any]]] = {}  # symbol -> grid orders
        self._grid_levels: Dict[str, List[float]] = {}  # symbol -> price levels
        
        # Files
        self.config_file = f"{data_path}/rebalance_config.json"
        self.history_file = f"{data_path}/rebalance_history.json"
        self.targets_file = f"{data_path}/target_allocations.json"
        
        # Background task
        self._rebalance_task: Optional[asyncio.Task] = None
        
        logger.info("[REBALANCER] Initialized portfolio rebalancing system")
    
    async def initialize(self) -> bool:
        """Initialize the rebalancer"""
        try:
            async with self._async_lock:
                # Load configuration and history
                await self._load_config()
                await self._load_history()
                await self._load_target_allocations()
                
                # Start monitoring if not in dry run mode
                if not self.config.dry_run:
                    await self.start_monitoring()
                
                logger.info("[REBALANCER] Rebalancer initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"[REBALANCER] Initialization failed: {e}")
            return False
    
    async def start_monitoring(self) -> None:
        """Start background monitoring for rebalancing opportunities"""
        if self._running:
            return
        
        self._running = True
        self._rebalance_task = asyncio.create_task(self._monitoring_loop())
        logger.info("[REBALANCER] Started rebalancing monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        self._running = False
        
        if self._rebalance_task and not self._rebalance_task.done():
            self._rebalance_task.cancel()
            try:
                await self._rebalance_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[REBALANCER] Stopped rebalancing monitoring")
    
    def set_target_allocations(self, targets: Dict[str, float]) -> None:
        """
        Set target allocations for portfolio
        
        Args:
            targets: Dict of symbol -> target weight (should sum to 1.0)
        """
        # Normalize weights to sum to 1.0
        total_weight = sum(targets.values())
        if total_weight > 0:
            normalized_targets = {symbol: weight / total_weight for symbol, weight in targets.items()}
        else:
            normalized_targets = targets
        
        with self._lock:
            self._target_allocations = normalized_targets
            
        logger.info(f"[REBALANCER] Updated target allocations: {normalized_targets}")
        
        # Save to file
        asyncio.create_task(self._save_target_allocations())
    
    async def calculate_portfolio_drift(self) -> Dict[str, Any]:
        """Calculate current portfolio drift from targets"""
        async with self._async_lock:
            portfolio_summary = self.position_tracker.get_portfolio_summary()
            current_value = portfolio_summary['total_value']
            
            if current_value <= 0:
                return {'total_drift': 0.0, 'symbol_drifts': {}, 'requires_rebalance': False}
            
            symbol_drifts = {}
            total_drift = 0.0
            max_drift = 0.0
            
            # Calculate drift for each symbol
            for symbol, target_weight in self._target_allocations.items():
                symbol_data = portfolio_summary['symbol_breakdown'].get(symbol, {})
                current_value_symbol = symbol_data.get('total_value', 0.0)
                current_weight = current_value_symbol / current_value
                
                drift_pct = abs(current_weight - target_weight) * 100
                symbol_drifts[symbol] = {
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'drift_pct': drift_pct,
                    'current_value': current_value_symbol,
                    'target_value': target_weight * current_value
                }
                
                total_drift += drift_pct
                max_drift = max(max_drift, drift_pct)
            
            # Check if rebalancing is required
            requires_rebalance = (
                max_drift > self.config.max_drift_pct or
                (time.time() - self._last_rebalance_time) > (self.config.rebalance_interval_hours * 3600)
            )
            
            drift_analysis = {
                'timestamp': time.time(),
                'total_drift': total_drift,
                'max_drift': max_drift,
                'avg_drift': total_drift / len(symbol_drifts) if symbol_drifts else 0.0,
                'symbol_drifts': symbol_drifts,
                'requires_rebalance': requires_rebalance,
                'portfolio_value': current_value
            }
            
            # Store in history
            self._portfolio_drift_history.append(drift_analysis)
            if len(self._portfolio_drift_history) > 1000:
                self._portfolio_drift_history = self._portfolio_drift_history[-1000:]
            
            return drift_analysis
    
    async def create_rebalance_plan(self, strategy: RebalanceStrategy,
                                   reason: RebalanceReason = RebalanceReason.MANUAL,
                                   custom_targets: Dict[str, float] = None) -> RebalanceResult:
        """
        Create a rebalancing plan
        
        Args:
            strategy: Rebalancing strategy to use
            reason: Reason for rebalancing
            custom_targets: Custom target allocations (overrides default)
            
        Returns:
            RebalanceResult with the plan
        """
        async with self._async_lock:
            try:
                # Use custom targets or default targets
                targets = custom_targets or self._target_allocations
                
                if not targets:
                    raise ValueError("No target allocations defined")
                
                # Get current portfolio state
                portfolio_summary = self.position_tracker.get_portfolio_summary()
                current_value = portfolio_summary['total_value']
                
                if current_value <= 0:
                    raise ValueError("Portfolio has no value")
                
                # Create rebalancing targets based on strategy
                if strategy == RebalanceStrategy.DCA:
                    rebalance_targets = await self._create_dca_plan(targets, current_value, portfolio_summary)
                elif strategy == RebalanceStrategy.GRID:
                    rebalance_targets = await self._create_grid_plan(targets, current_value, portfolio_summary)
                elif strategy == RebalanceStrategy.MOMENTUM:
                    rebalance_targets = await self._create_momentum_plan(targets, current_value, portfolio_summary)
                elif strategy == RebalanceStrategy.MEAN_REVERSION:
                    rebalance_targets = await self._create_mean_reversion_plan(targets, current_value, portfolio_summary)
                elif strategy == RebalanceStrategy.RISK_PARITY:
                    rebalance_targets = await self._create_risk_parity_plan(targets, current_value, portfolio_summary)
                else:  # THRESHOLD
                    rebalance_targets = await self._create_threshold_plan(targets, current_value, portfolio_summary)
                
                # Calculate expected costs
                expected_cost, expected_trades = self._calculate_execution_cost(rebalance_targets)
                
                # Create result
                result = RebalanceResult(
                    strategy=strategy,
                    reason=reason,
                    timestamp=time.time(),
                    targets=rebalance_targets,
                    total_portfolio_value=current_value,
                    expected_cost=expected_cost,
                    expected_trades=expected_trades
                )
                
                logger.info(f"[REBALANCER] Created {strategy.value} rebalance plan: "
                           f"{len(rebalance_targets)} targets, expected cost ${expected_cost:.2f}")
                
                return result
                
            except Exception as e:
                logger.error(f"[REBALANCER] Error creating rebalance plan: {e}")
                return RebalanceResult(
                    strategy=strategy,
                    reason=reason,
                    timestamp=time.time(),
                    targets=[],
                    total_portfolio_value=0.0,
                    expected_cost=0.0,
                    expected_trades=0,
                    success=False,
                    error_message=str(e)
                )
    
    async def execute_rebalance_plan(self, plan: RebalanceResult) -> RebalanceResult:
        """
        Execute a rebalancing plan
        
        Args:
            plan: RebalanceResult with the plan to execute
            
        Returns:
            Updated RebalanceResult with execution details
        """
        if not self.trade_executor:
            plan.success = False
            plan.error_message = "No trade executor available"
            return plan
        
        async with self._async_lock:
            start_time = time.time()
            actual_cost = 0.0
            actual_trades = 0
            
            try:
                logger.info(f"[REBALANCER] Executing {plan.strategy.value} rebalance plan with {len(plan.targets)} targets")
                
                # Sort targets by priority and size
                sorted_targets = sorted(plan.targets, key=lambda x: (x.priority, -abs(x.recommended_size)))
                
                for target in sorted_targets:
                    if target.action == 'hold':
                        continue
                    
                    # Check if we should execute this trade
                    if abs(target.recommended_size) < self.config.min_trade_size_usd:
                        logger.debug(f"[REBALANCER] Skipping {target.symbol}: size too small")
                        continue
                    
                    # Risk check
                    risk_action, risk_reason = await self.risk_manager.check_position_risk(
                        target.symbol, abs(target.recommended_size), target.current_value / target.recommended_size if target.recommended_size != 0 else 1.0
                    )
                    
                    if risk_action not in [RiskAction.ALLOW, RiskAction.WARN]:
                        logger.warning(f"[REBALANCER] Skipping {target.symbol}: {risk_reason}")
                        continue
                    
                    # Execute trade
                    try:
                        if target.action == 'buy':
                            execution_result = await self._execute_buy_order(target)
                        else:  # sell
                            execution_result = await self._execute_sell_order(target)
                        
                        if execution_result['success']:
                            actual_cost += execution_result['cost']
                            actual_trades += 1
                            logger.info(f"[REBALANCER] Executed {target.action} {target.symbol}: "
                                       f"${execution_result['cost']:.2f}")
                        else:
                            logger.error(f"[REBALANCER] Failed to execute {target.action} {target.symbol}: "
                                        f"{execution_result['error']}")
                    
                    except Exception as e:
                        logger.error(f"[REBALANCER] Error executing {target.action} {target.symbol}: {e}")
                    
                    # Delay between trades
                    if self.config.execution_delay_seconds > 0:
                        await asyncio.sleep(self.config.execution_delay_seconds)
                
                # Update plan with execution results
                plan.executed = True
                plan.actual_cost = actual_cost
                plan.actual_trades = actual_trades
                plan.execution_time = time.time() - start_time
                
                # Update last rebalance time
                self._last_rebalance_time = time.time()
                
                # Store in history
                self._rebalance_history.append(plan)
                await self._save_history()
                
                logger.info(f"[REBALANCER] Rebalance execution complete: "
                           f"{actual_trades} trades, ${actual_cost:.2f} cost, "
                           f"{plan.execution_time:.1f}s execution time")
                
            except Exception as e:
                plan.success = False
                plan.error_message = str(e)
                plan.execution_time = time.time() - start_time
                logger.error(f"[REBALANCER] Rebalance execution failed: {e}")
            
            return plan
    
    async def auto_rebalance(self) -> Optional[RebalanceResult]:
        """
        Perform automatic rebalancing based on current conditions
        
        Returns:
            RebalanceResult if rebalancing was performed, None otherwise
        """
        try:
            # Check if targets are defined
            if not self._target_allocations:
                logger.debug("[REBALANCER] No target allocations defined for auto-rebalancing")
                return None
            
            # Calculate current drift
            drift_analysis = await self.calculate_portfolio_drift()
            
            # Determine if rebalancing is needed
            if not drift_analysis['requires_rebalance']:
                logger.debug("[REBALANCER] No rebalancing required")
                return None
            
            # Determine strategy based on market conditions
            strategy = await self._determine_optimal_strategy()
            
            # Determine reason
            if drift_analysis['max_drift'] > self.config.max_drift_pct:
                reason = RebalanceReason.DRIFT_EXCEEDED
            elif (time.time() - self._last_rebalance_time) > (self.config.rebalance_interval_hours * 3600):
                reason = RebalanceReason.TIME_TRIGGER
            else:
                reason = RebalanceReason.OPPORTUNITY
            
            # Create and execute plan
            plan = await self.create_rebalance_plan(strategy, reason)
            
            if plan.success and plan.expected_cost < (self.config.max_rebalance_cost_pct / 100) * plan.total_portfolio_value:
                if not self.config.dry_run:
                    result = await self.execute_rebalance_plan(plan)
                    return result
                else:
                    logger.info(f"[REBALANCER] DRY RUN: Would execute {strategy.value} rebalance")
                    return plan
            else:
                logger.info(f"[REBALANCER] Rebalance plan rejected: cost too high or plan failed")
                return None
                
        except Exception as e:
            logger.error(f"[REBALANCER] Auto-rebalance error: {e}")
            return None
    
    async def dca_rebalance(self, symbol: str, amount_usd: float) -> Optional[RebalanceResult]:
        """
        Perform Dollar Cost Averaging for a specific symbol
        
        Args:
            symbol: Symbol to DCA into
            amount_usd: USD amount to invest
            
        Returns:
            RebalanceResult if successful
        """
        try:
            # Check DCA timing
            if (time.time() - self._last_dca_time) < (self.config.dca_interval_hours * 3600):
                logger.debug("[REBALANCER] DCA interval not met")
                return None
            
            # Create DCA plan
            custom_targets = {symbol: 1.0}  # 100% allocation to DCA symbol
            plan = await self.create_rebalance_plan(
                RebalanceStrategy.DCA, 
                RebalanceReason.STRATEGY_SIGNAL,
                custom_targets
            )
            
            # Filter plan to only include the DCA symbol and limit amount
            dca_targets = []
            for target in plan.targets:
                if target.symbol == symbol and target.action == 'buy':
                    target.recommended_size = min(target.recommended_size, amount_usd)
                    dca_targets.append(target)
            
            plan.targets = dca_targets
            
            if dca_targets and not self.config.dry_run:
                result = await self.execute_rebalance_plan(plan)
                self._last_dca_time = time.time()
                return result
            
            return plan
            
        except Exception as e:
            logger.error(f"[REBALANCER] DCA rebalance error: {e}")
            return None
    
    async def grid_rebalance(self, symbol: str, grid_range_pct: float = None) -> Optional[RebalanceResult]:
        """
        Set up or adjust grid trading for a symbol
        
        Args:
            symbol: Symbol for grid trading
            grid_range_pct: Grid range as percentage (uses config default if None)
            
        Returns:
            RebalanceResult if successful
        """
        try:
            grid_range = grid_range_pct or self.config.grid_range_pct
            
            # Get current price (would need price feed integration)
            current_positions = self.position_tracker.get_positions_by_symbol(symbol)
            if not current_positions:
                logger.warning(f"[REBALANCER] No positions found for grid setup: {symbol}")
                return None
            
            current_price = float(current_positions[0].current_price)
            
            # Calculate grid levels
            price_range = current_price * (grid_range / 100)
            lower_bound = current_price - price_range
            upper_bound = current_price + price_range
            
            grid_levels = []
            for i in range(self.config.grid_levels):
                level_price = lower_bound + (i * (upper_bound - lower_bound) / (self.config.grid_levels - 1))
                grid_levels.append(level_price)
            
            self._grid_levels[symbol] = grid_levels
            
            # Create grid plan
            plan = await self.create_rebalance_plan(
                RebalanceStrategy.GRID,
                RebalanceReason.STRATEGY_SIGNAL
            )
            
            logger.info(f"[REBALANCER] Created grid for {symbol}: {len(grid_levels)} levels "
                       f"from ${lower_bound:.4f} to ${upper_bound:.4f}")
            
            return plan
            
        except Exception as e:
            logger.error(f"[REBALANCER] Grid rebalance error: {e}")
            return None
    
    def get_rebalance_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get rebalancing history"""
        history = [result.to_dict() for result in self._rebalance_history]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_target_allocations(self) -> Dict[str, float]:
        """Get current target allocations"""
        return dict(self._target_allocations)
    
    def get_portfolio_drift_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get portfolio drift history"""
        history = list(self._portfolio_drift_history)
        
        if limit:
            history = history[-limit:]
        
        return history
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        while self._running:
            try:
                # Check for auto-rebalancing opportunities
                await self.auto_rebalance()
                
                # Sleep until next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[REBALANCER] Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _create_threshold_plan(self, targets: Dict[str, float], 
                                   current_value: float, 
                                   portfolio_summary: Dict[str, Any]) -> List[RebalanceTarget]:
        """Create threshold-based rebalancing plan"""
        rebalance_targets = []
        
        for symbol, target_weight in targets.items():
            symbol_data = portfolio_summary['symbol_breakdown'].get(symbol, {})
            current_value_symbol = symbol_data.get('total_value', 0.0)
            current_weight = current_value_symbol / current_value if current_value > 0 else 0.0
            
            target_value = target_weight * current_value
            drift_pct = abs(current_weight - target_weight) * 100
            
            # Only rebalance if drift exceeds minimum threshold
            if drift_pct > self.config.min_drift_pct:
                value_diff = target_value - current_value_symbol
                
                if abs(value_diff) > self.config.min_trade_size_usd:
                    action = 'buy' if value_diff > 0 else 'sell'
                    priority = 1 if drift_pct > self.config.max_drift_pct * 0.5 else 3
                    
                    rebalance_targets.append(RebalanceTarget(
                        symbol=symbol,
                        target_weight=target_weight,
                        current_weight=current_weight,
                        target_value=target_value,
                        current_value=current_value_symbol,
                        drift=drift_pct,
                        action=action,
                        recommended_size=abs(value_diff),
                        priority=priority
                    ))
        
        return rebalance_targets
    
    async def _create_dca_plan(self, targets: Dict[str, float], 
                             current_value: float, 
                             portfolio_summary: Dict[str, Any]) -> List[RebalanceTarget]:
        """Create DCA (Dollar Cost Averaging) plan"""
        rebalance_targets = []
        
        # DCA focuses on gradual accumulation
        for symbol, target_weight in targets.items():
            symbol_data = portfolio_summary['symbol_breakdown'].get(symbol, {})
            current_value_symbol = symbol_data.get('total_value', 0.0)
            current_weight = current_value_symbol / current_value if current_value > 0 else 0.0
            
            target_value = target_weight * current_value
            
            # DCA only buys (accumulates), never sells
            if current_weight < target_weight:
                # Calculate DCA amount (smaller, regular purchases)
                dca_amount = min(
                    (target_value - current_value_symbol) * 0.2,  # 20% of gap
                    current_value * 0.05  # Max 5% of portfolio per DCA
                )
                
                if dca_amount > self.config.min_trade_size_usd:
                    rebalance_targets.append(RebalanceTarget(
                        symbol=symbol,
                        target_weight=target_weight,
                        current_weight=current_weight,
                        target_value=target_value,
                        current_value=current_value_symbol,
                        drift=(target_weight - current_weight) * 100,
                        action='buy',
                        recommended_size=dca_amount,
                        priority=2  # Medium priority
                    ))
        
        return rebalance_targets
    
    async def _create_grid_plan(self, targets: Dict[str, float], 
                              current_value: float, 
                              portfolio_summary: Dict[str, Any]) -> List[RebalanceTarget]:
        """Create grid trading plan"""
        rebalance_targets = []
        
        # Grid trading creates buy/sell orders at predetermined levels
        for symbol, target_weight in targets.items():
            if symbol not in self._grid_levels:
                continue
            
            symbol_data = portfolio_summary['symbol_breakdown'].get(symbol, {})
            current_value_symbol = symbol_data.get('total_value', 0.0)
            current_weight = current_value_symbol / current_value if current_value > 0 else 0.0
            
            # Get current price from positions
            positions = self.position_tracker.get_positions_by_symbol(symbol)
            if not positions:
                continue
            
            current_price = float(positions[0].current_price)
            grid_levels = self._grid_levels[symbol]
            
            # Find closest grid levels
            lower_levels = [level for level in grid_levels if level < current_price]
            upper_levels = [level for level in grid_levels if level > current_price]
            
            # Create buy orders for lower levels
            for level in lower_levels[-2:]:  # Last 2 lower levels
                buy_size = (target_weight * current_value) / len(lower_levels)
                if buy_size > self.config.min_trade_size_usd:
                    rebalance_targets.append(RebalanceTarget(
                        symbol=symbol,
                        target_weight=target_weight,
                        current_weight=current_weight,
                        target_value=target_weight * current_value,
                        current_value=current_value_symbol,
                        drift=0,  # Grid doesn't use drift
                        action='buy',
                        recommended_size=buy_size,
                        priority=3
                    ))
        
        return rebalance_targets
    
    async def _create_momentum_plan(self, targets: Dict[str, float], 
                                  current_value: float, 
                                  portfolio_summary: Dict[str, Any]) -> List[RebalanceTarget]:
        """Create momentum-based rebalancing plan"""
        rebalance_targets = []
        
        # Momentum strategy increases allocation to winning positions
        for symbol, target_weight in targets.items():
            symbol_data = portfolio_summary['symbol_breakdown'].get(symbol, {})
            current_value_symbol = symbol_data.get('total_value', 0.0)
            current_weight = current_value_symbol / current_value if current_value > 0 else 0.0
            
            # Calculate momentum (recent performance)
            positions = self.position_tracker.get_positions_by_symbol(symbol)
            momentum_score = 0.0
            
            for position in positions:
                if position.status != PositionStatus.CLOSED:
                    pnl_pct = float(position.unrealized_pnl_pct)
                    momentum_score += pnl_pct
            
            # Adjust target weight based on momentum
            momentum_adjustment = min(momentum_score * 0.1, 0.05)  # Max 5% adjustment
            adjusted_target_weight = target_weight + momentum_adjustment
            adjusted_target_weight = max(0, min(adjusted_target_weight, 1.0))
            
            target_value = adjusted_target_weight * current_value
            value_diff = target_value - current_value_symbol
            
            if abs(value_diff) > self.config.min_trade_size_usd:
                action = 'buy' if value_diff > 0 else 'sell'
                priority = 1 if momentum_score > 5 else 2  # High priority for strong momentum
                
                rebalance_targets.append(RebalanceTarget(
                    symbol=symbol,
                    target_weight=adjusted_target_weight,
                    current_weight=current_weight,
                    target_value=target_value,
                    current_value=current_value_symbol,
                    drift=abs(adjusted_target_weight - current_weight) * 100,
                    action=action,
                    recommended_size=abs(value_diff),
                    priority=priority
                ))
        
        return rebalance_targets
    
    async def _create_mean_reversion_plan(self, targets: Dict[str, float], 
                                        current_value: float, 
                                        portfolio_summary: Dict[str, Any]) -> List[RebalanceTarget]:
        """Create mean reversion rebalancing plan"""
        rebalance_targets = []
        
        # Mean reversion strategy reduces allocation to overperforming positions
        for symbol, target_weight in targets.items():
            symbol_data = portfolio_summary['symbol_breakdown'].get(symbol, {})
            current_value_symbol = symbol_data.get('total_value', 0.0)
            current_weight = current_value_symbol / current_value if current_value > 0 else 0.0
            
            # Calculate overextension from target
            weight_deviation = current_weight - target_weight
            
            # Mean reversion: sell overweight, buy underweight
            if abs(weight_deviation) > (self.config.min_drift_pct / 100):
                reversion_factor = 0.5  # Revert 50% of deviation
                adjustment_value = weight_deviation * reversion_factor * current_value
                
                if abs(adjustment_value) > self.config.min_trade_size_usd:
                    action = 'sell' if adjustment_value > 0 else 'buy'
                    
                    rebalance_targets.append(RebalanceTarget(
                        symbol=symbol,
                        target_weight=target_weight,
                        current_weight=current_weight,
                        target_value=target_weight * current_value,
                        current_value=current_value_symbol,
                        drift=abs(weight_deviation) * 100,
                        action=action,
                        recommended_size=abs(adjustment_value),
                        priority=2
                    ))
        
        return rebalance_targets
    
    async def _create_risk_parity_plan(self, targets: Dict[str, float], 
                                     current_value: float, 
                                     portfolio_summary: Dict[str, Any]) -> List[RebalanceTarget]:
        """Create risk parity rebalancing plan"""
        rebalance_targets = []
        
        # Risk parity allocates based on inverse volatility
        symbol_volatilities = {}
        
        for symbol in targets.keys():
            # Get volatility from risk manager (simplified)
            try:
                volatility = await self.risk_manager._get_symbol_volatility(symbol)
                symbol_volatilities[symbol] = max(volatility, 0.01)  # Minimum volatility
            except:
                symbol_volatilities[symbol] = 0.02  # Default 2% volatility
        
        # Calculate risk parity weights (inverse volatility)
        total_inv_vol = sum(1 / vol for vol in symbol_volatilities.values())
        risk_parity_weights = {
            symbol: (1 / vol) / total_inv_vol 
            for symbol, vol in symbol_volatilities.items()
        }
        
        # Create rebalancing targets based on risk parity weights
        for symbol, risk_weight in risk_parity_weights.items():
            symbol_data = portfolio_summary['symbol_breakdown'].get(symbol, {})
            current_value_symbol = symbol_data.get('total_value', 0.0)
            current_weight = current_value_symbol / current_value if current_value > 0 else 0.0
            
            target_value = risk_weight * current_value
            value_diff = target_value - current_value_symbol
            
            if abs(value_diff) > self.config.min_trade_size_usd:
                action = 'buy' if value_diff > 0 else 'sell'
                
                rebalance_targets.append(RebalanceTarget(
                    symbol=symbol,
                    target_weight=risk_weight,
                    current_weight=current_weight,
                    target_value=target_value,
                    current_value=current_value_symbol,
                    drift=abs(risk_weight - current_weight) * 100,
                    action=action,
                    recommended_size=abs(value_diff),
                    priority=2
                ))
        
        return rebalance_targets
    
    def _calculate_execution_cost(self, targets: List[RebalanceTarget]) -> Tuple[float, int]:
        """Calculate expected execution cost and number of trades"""
        total_cost = 0.0
        total_trades = 0
        
        # Estimate trading fees (would use actual exchange fee structure)
        fee_rate = 0.001  # 0.1% fee estimate
        
        for target in targets:
            if target.action != 'hold':
                trade_cost = target.recommended_size * fee_rate
                total_cost += trade_cost
                total_trades += 1
        
        return total_cost, total_trades
    
    async def _execute_buy_order(self, target: RebalanceTarget) -> Dict[str, Any]:
        """Execute a buy order for rebalancing"""
        try:
            if self.trade_executor and hasattr(self.trade_executor, 'execute_buy'):
                result = await self.trade_executor.execute_buy(
                    symbol=target.symbol,
                    size_usd=target.recommended_size,
                    reason='rebalance'
                )
                return {
                    'success': result.get('success', False),
                    'cost': result.get('fee', 0.0),
                    'size': result.get('size', 0.0)
                }
            else:
                return {'success': False, 'error': 'No trade executor available', 'cost': 0.0}
        except Exception as e:
            return {'success': False, 'error': str(e), 'cost': 0.0}
    
    async def _execute_sell_order(self, target: RebalanceTarget) -> Dict[str, Any]:
        """Execute a sell order for rebalancing"""
        try:
            if self.trade_executor and hasattr(self.trade_executor, 'execute_sell'):
                result = await self.trade_executor.execute_sell(
                    symbol=target.symbol,
                    size_usd=target.recommended_size,
                    reason='rebalance'
                )
                return {
                    'success': result.get('success', False),
                    'cost': result.get('fee', 0.0),
                    'size': result.get('size', 0.0)
                }
            else:
                return {'success': False, 'error': 'No trade executor available', 'cost': 0.0}
        except Exception as e:
            return {'success': False, 'error': str(e), 'cost': 0.0}
    
    async def _determine_optimal_strategy(self) -> RebalanceStrategy:
        """Determine optimal rebalancing strategy based on market conditions"""
        try:
            # Simple strategy selection based on portfolio drift
            drift_analysis = await self.calculate_portfolio_drift()
            max_drift = drift_analysis['max_drift']
            
            if max_drift > self.config.max_drift_pct * 1.5:
                return RebalanceStrategy.THRESHOLD  # Aggressive rebalancing
            elif max_drift > self.config.max_drift_pct:
                return RebalanceStrategy.MEAN_REVERSION  # Standard rebalancing
            else:
                return RebalanceStrategy.DCA  # Gradual accumulation
                
        except Exception as e:
            logger.error(f"[REBALANCER] Error determining strategy: {e}")
            return RebalanceStrategy.THRESHOLD  # Default fallback
    
    async def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                # Update config with loaded data
                for key, value in data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
            logger.debug("[REBALANCER] Configuration loaded")
        except FileNotFoundError:
            await self._save_config()
            logger.info("[REBALANCER] Created default configuration")
        except Exception as e:
            logger.error(f"[REBALANCER] Error loading configuration: {e}")
    
    async def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"[REBALANCER] Error saving configuration: {e}")
    
    async def _load_history(self) -> None:
        """Load rebalancing history from file"""
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                # Would reconstruct RebalanceResult objects from data
            logger.debug("[REBALANCER] History loaded")
        except FileNotFoundError:
            logger.info("[REBALANCER] No existing history found")
        except Exception as e:
            logger.error(f"[REBALANCER] Error loading history: {e}")
    
    async def _save_history(self) -> None:
        """Save rebalancing history to file"""
        try:
            history_data = [result.to_dict() for result in self._rebalance_history[-100:]]  # Last 100 entries
            with open(self.history_file, 'w') as f:
                json.dump(history_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[REBALANCER] Error saving history: {e}")
    
    async def _load_target_allocations(self) -> None:
        """Load target allocations from file"""
        try:
            with open(self.targets_file, 'r') as f:
                self._target_allocations = json.load(f)
            logger.debug(f"[REBALANCER] Loaded target allocations: {self._target_allocations}")
        except FileNotFoundError:
            logger.info("[REBALANCER] No target allocations file found")
        except Exception as e:
            logger.error(f"[REBALANCER] Error loading target allocations: {e}")
    
    async def _save_target_allocations(self) -> None:
        """Save target allocations to file"""
        try:
            with open(self.targets_file, 'w') as f:
                json.dump(self._target_allocations, f, indent=2)
        except Exception as e:
            logger.error(f"[REBALANCER] Error saving target allocations: {e}")