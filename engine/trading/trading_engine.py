#!/usr/bin/env python3
"""
Kraken-Optimized Trading Engine
Core trading logic with advanced order management and execution
"""

import logging
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any, Optional, List, Tuple
import time

from .trading_config import TradingConfig

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    Kraken-optimized trading engine with advanced order management
    Handles entry/exit logic, position management, and profit optimization
    """

    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Trading state
        self.current_position: Optional[Dict[str, Any]] = None
        self.last_trade_time: float = 0.0
        self.last_entry_time: float = 0.0
        self.consecutive_losses: int = 0
        self.session_trades: int = 0
        self.session_wins: int = 0

        # Gate tracking for entry conditions
        self._entry_gates: Dict[str, bool] = {}
        self._last_gate_report: float = 0.0

        # Performance tracking
        self._trade_history: List[Dict[str, Any]] = []
        self._profit_history: List[Decimal] = []

        # Timing controls
        self._cooldown_until: float = 0.0
        self._last_quick_profit_check: float = 0.0

        # Advanced features state
        self._trail_armed: bool = False
        self._trail_peak_price: Optional[Decimal] = None
        self._breakeven_armed: bool = False
        self._breakeven_level: Optional[Decimal] = None
        self._micro_momentum_buffer: List[Decimal] = []

        self.logger.info(f"TradingEngine initialized for {config.pair}")

    def evaluate_entry_conditions(
        self,
        market_data: Dict[str, Any],
        account_balance: Decimal,
        emergency_stop_active: bool = False,
    ) -> Tuple[bool, str]:
        """
        Evaluate conditions for entering a position with Kraken optimizations

        Args:
            market_data: Current market data (price, spread, volume, etc.)
            account_balance: Available USD balance
            emergency_stop_active: Whether emergency stop is active

        Returns:
            Tuple of (can_enter, reason)
        """
        if emergency_stop_active:
            return False, "emergency_stop_active"

        # Check cooldown periods
        if time.time() < self._cooldown_until:
            return False, "cooldown_active"

        # Check position exists
        if self.current_position:
            return False, "position_exists"

        # Check balance requirements
        if not self._has_sufficient_balance(account_balance, market_data):
            return False, "insufficient_balance"

        # Evaluate market conditions
        market_ok, market_reason = self._evaluate_market_conditions(market_data)
        if not market_ok:
            return False, market_reason

        # Check entry gates
        gates_ok, gate_reason = self._check_entry_gates(market_data)
        if not gates_ok:
            return False, gate_reason

        # All conditions met
        return True, "entry_conditions_met"

    def _has_sufficient_balance(
        self, balance: Decimal, market_data: Dict[str, Any]
    ) -> bool:
        """Check if sufficient balance for minimum position"""
        if balance < Decimal("1.0"):  # Minimum for any trade
            return False

        current_price = market_data.get("last_price")
        if not current_price:
            return False

        # Calculate minimum position cost
        min_volume = self.config.minimum_order
        min_cost = (
            min_volume * current_price * (Decimal("1") + self.config.taker_fee_rate)
        )

        # Apply balance utilization limit
        max_allowed_cost = balance * self.config.balance_utilization_pct

        return min_cost <= max_allowed_cost

    def _evaluate_market_conditions(
        self, market_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Evaluate market conditions for trading"""
        # Check spread
        bid = market_data.get("bid")
        ask = market_data.get("ask")
        if bid and ask:
            spread = (ask - bid) / bid
            if spread > self.config.spread_threshold:
                return False, f"spread_too_wide_{spread:.4f}"

        # Check momentum (if available)
        momentum = market_data.get("momentum", 0)
        if abs(momentum) < self.config.momentum_threshold:
            return False, f"insufficient_momentum_{momentum:.4f}"

        # Check volume confirmation
        if self.config.enable_volume_confirmation:
            volume_ratio = market_data.get("volume_ratio", 0)
            if volume_ratio < self.config.volume_confirmation_ratio:
                return False, f"volume_confirmation_failed_{volume_ratio:.2f}"

        return True, "market_conditions_ok"

    def _check_entry_gates(self, market_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check various entry gate conditions"""
        gates = {}

        # Balance gate
        current_price = market_data.get("last_price")
        if current_price:
            # Estimate position cost
            estimated_cost = self.config.minimum_order * current_price
            gates["balance_sufficient"] = (
                estimated_cost <= self.config.max_cost_usd_per_trade
            )

        # Spread gate
        bid = market_data.get("bid")
        ask = market_data.get("ask")
        if bid and ask:
            spread_pct = ((ask - bid) / bid) * 100
            gates["spread_reasonable"] = spread_pct <= (
                self.config.spread_threshold * 100
            )

        # Momentum gate
        momentum = market_data.get("momentum", 0)
        gates["momentum_sufficient"] = abs(momentum) >= self.config.momentum_threshold

        # Update gate tracking
        self._entry_gates.update(gates)

        # Check if all gates are open
        closed_gates = [gate for gate, open_status in gates.items() if not open_status]

        if closed_gates:
            # Report gates periodically
            now = time.time()
            if now - self._last_gate_report > 60:  # Report every minute
                self.logger.info(f"Entry gates closed: {', '.join(closed_gates)}")
                self._last_gate_report = now
            return False, f"gates_closed_{','.join(closed_gates)}"

        return True, "all_gates_open"

    def calculate_position_size(
        self, market_data: Dict[str, Any], account_balance: Decimal
    ) -> Tuple[Decimal, str]:
        """
        Calculate optimal position size with Kraken fee optimization

        Args:
            market_data: Current market data
            account_balance: Available USD balance

        Returns:
            Tuple of (position_size, reasoning)
        """
        current_price = market_data.get("last_price")
        if not current_price:
            return Decimal("0"), "no_price_available"

        # Base calculation
        max_by_balance = self._calculate_balance_based_size(
            account_balance, current_price
        )
        max_by_config = self.config.max_position_size_xlm

        # Apply size scaling based on win rate
        if self.config.enable_size_scaling:
            scaling_factor = self._calculate_scaling_factor()
            max_by_config = max_by_config * scaling_factor

        # Use minimum of balance/config constraints, then enforce minimum order size
        position_size = min(max_by_balance, max_by_config)

        # Ensure meets minimum order size
        if position_size < self.config.minimum_order:
            return Decimal("0"), f"below_minimum_order_{position_size}"

        # Check max cost limit
        estimated_cost = position_size * current_price
        if estimated_cost > self.config.max_cost_usd_per_trade:
            # Reduce to meet cost limit
            position_size = (
                self.config.max_cost_usd_per_trade / current_price
            ).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

        return position_size, "position_size_calculated"

    def _calculate_balance_based_size(
        self, balance: Decimal, price: Decimal
    ) -> Decimal:
        """Calculate position size based on available balance and utilization"""
        # Account for fees and slippage
        total_cost_multiplier = (
            Decimal("1") + self.config.taker_fee_rate + self.config.slippage_buffer_rate
        )

        # Apply utilization percentage
        usable_balance = balance * self.config.balance_utilization_pct

        # Calculate maximum affordable position
        max_position = usable_balance / (price * total_cost_multiplier)

        return max_position.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

    def _calculate_scaling_factor(self) -> Decimal:
        """Calculate position size scaling factor based on performance"""
        if not self._trade_history:
            return Decimal("1.0")

        # Calculate recent win rate
        recent_trades = self._trade_history[-self.config.autotune_window_trades :]
        if len(recent_trades) < 10:  # Need minimum sample
            return Decimal("1.0")

        wins = sum(1 for trade in recent_trades if trade.get("profit", 0) > 0)
        win_rate = wins / len(recent_trades)

        if win_rate >= (self.config.scaling_winrate_threshold / 100):
            # Scale up for good performance
            return Decimal("1") + self.config.scaling_increase_pct
        else:
            # Scale down for poor performance
            return Decimal("1") - (self.config.scaling_increase_pct / Decimal("2"))

    def evaluate_exit_conditions(
        self, market_data: Dict[str, Any], position_age_seconds: float
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluate conditions for exiting current position

        Args:
            market_data: Current market data
            position_age_seconds: How long position has been open

        Returns:
            Tuple of (should_exit, reason, exit_parameters)
        """
        if not self.current_position:
            return False, "no_position", {}

        current_price = market_data.get("last_price")
        if not current_price:
            return False, "no_price_available", {}

        entry_price = self.current_position.get("entry_price")
        if not entry_price:
            return False, "invalid_position_data", {}

        # Calculate profit/loss
        price_change_pct = (current_price - entry_price) / entry_price

        # Check profit targets
        if price_change_pct >= self.config.profit_target:
            return (
                True,
                "profit_target_reached",
                {
                    "exit_price": current_price,
                    "profit_pct": price_change_pct,
                    "exit_type": "take_profit",
                },
            )

        # Check stop loss
        if price_change_pct <= self.config.stop_loss:
            return (
                True,
                "stop_loss_triggered",
                {
                    "exit_price": current_price,
                    "loss_pct": price_change_pct,
                    "exit_type": "stop_loss",
                },
            )

        # Check quick profit (if enabled and within window)
        if self._should_take_quick_profit(price_change_pct, position_age_seconds):
            return (
                True,
                "quick_profit",
                {
                    "exit_price": current_price,
                    "profit_pct": price_change_pct,
                    "exit_type": "quick_profit",
                },
            )

        # Check trailing stop
        if self.config.enable_trailing_exit:
            trail_exit = self._evaluate_trailing_stop(current_price)
            if trail_exit:
                return (
                    True,
                    "trailing_stop",
                    {
                        "exit_price": current_price,
                        "profit_pct": price_change_pct,
                        "exit_type": "trailing_stop",
                    },
                )

        # Check breakeven stop
        if self.config.enable_breakeven_stop:
            breakeven_exit = self._evaluate_breakeven_stop(current_price)
            if breakeven_exit:
                return (
                    True,
                    "breakeven_stop",
                    {
                        "exit_price": current_price,
                        "profit_pct": price_change_pct,
                        "exit_type": "breakeven_stop",
                    },
                )

        # Check stale position
        if self._is_position_stale(position_age_seconds, price_change_pct):
            return (
                True,
                "stale_position",
                {
                    "exit_price": current_price,
                    "profit_pct": price_change_pct,
                    "exit_type": "stale_exit",
                },
            )

        return False, "hold_position", {}

    def _should_take_quick_profit(
        self, price_change_pct: float, age_seconds: float
    ) -> bool:
        """Check if quick profit conditions are met"""
        if not self.config.enable_maker_first_quick_tp:
            return False

        # Check if within quick profit window
        if age_seconds > self.config.quick_profit_window_secs:
            return False

        # Check if profit meets quick profit threshold
        return price_change_pct >= self.config.quick_profit

    def _evaluate_trailing_stop(self, current_price: Decimal) -> bool:
        """Evaluate trailing stop conditions"""
        if not self._trail_armed or not self._trail_peak_price:
            return False

        # Check if price has dropped below trail level
        trail_level = self._trail_peak_price * (
            Decimal("1") - self.config.trailing_step_pct
        )
        return current_price <= trail_level

    def _evaluate_breakeven_stop(self, current_price: Decimal) -> bool:
        """Evaluate breakeven stop conditions"""
        if not self._breakeven_armed or not self._breakeven_level:
            return False

        # Check if price has dropped to breakeven level
        return current_price <= self._breakeven_level

    def _is_position_stale(self, age_seconds: float, price_change_pct: float) -> bool:
        """Check if position is stale and should be closed"""
        # Check age limit
        if age_seconds > (self.config.position_check_interval * 100):  # Rough estimate
            return True

        # Check drawdown limit
        if price_change_pct <= -abs(self.config.stale_exit_max_drawdown):
            return True

        return False

    def execute_entry_order(
        self, position_size: Decimal, market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute entry order with Kraken optimization

        Args:
            position_size: Size of position to enter
            market_data: Current market data

        Returns:
            Order execution details
        """
        current_price = market_data.get("last_price")
        if not current_price:
            raise ValueError("No price available for order execution")

        # Calculate execution price (use bid for buy orders)
        execution_price = market_data.get("ask", current_price)

        # Create position record
        position = {
            "order_id": f"ENTRY_{int(time.time())}",
            "entry_price": execution_price,
            "volume": position_size,
            "entry_time": time.time(),
            "total_cost": execution_price * position_size,
            "status": "pending",
        }

        # Update trading state
        self.current_position = position
        self.last_entry_time = time.time()
        self.session_trades += 1

        # Set up trailing stop
        if self.config.enable_trailing_exit:
            self._arm_trailing_stop(execution_price)

        # Set up breakeven stop
        if self.config.enable_breakeven_stop:
            self._arm_breakeven_stop(execution_price)

        # Set cooldown
        self._cooldown_until = time.time() + float(
            self.config.cooldown_between_entries_secs
        )

        self.logger.info(f"Entry order executed: {position_size} @ {execution_price}")
        return position

    def execute_exit_order(
        self, exit_reason: str, market_data: Dict[str, Any], exit_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute exit order with profit/loss calculation

        Args:
            exit_reason: Reason for exiting position
            market_data: Current market data
            exit_params: Exit parameters from evaluation

        Returns:
            Exit execution details
        """
        if not self.current_position:
            raise ValueError("No position to exit")

        exit_price = exit_params.get("exit_price")
        if not exit_price:
            current_price = market_data.get("bid", market_data.get("last_price"))
            if not current_price:
                raise ValueError("No exit price available")
            exit_price = current_price

        # Calculate P&L
        entry_price = self.current_position["entry_price"]
        volume = self.current_position["volume"]
        price_change_pct = (exit_price - entry_price) / entry_price

        gross_profit = (exit_price - entry_price) * volume
        fee_cost = abs(gross_profit) * self.config.taker_fee_rate
        net_profit = gross_profit - fee_cost

        # Record trade
        trade_record = {
            "exit_time": time.time(),
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "gross_profit": gross_profit,
            "fee_cost": fee_cost,
            "net_profit": net_profit,
            "profit_pct": price_change_pct,
            "holding_time": time.time() - self.current_position["entry_time"],
            "volume": volume,
            "entry_price": entry_price,
        }

        # Update trading state
        self._trade_history.append(trade_record)
        self._profit_history.append(net_profit)

        if net_profit > 0:
            self.session_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

        self.last_trade_time = time.time()

        # Set exit cooldown
        self._cooldown_until = time.time() + self.config.cooldown_after_exit_secs

        # Clear position
        self.current_position = None
        self._trail_armed = False
        self._breakeven_armed = False

        self.logger.info(
            f"Exit order executed: {exit_reason} @ {exit_price}, P&L: {net_profit:.4f}"
        )
        return trade_record

    def _arm_trailing_stop(self, entry_price: Decimal):
        """Arm trailing stop mechanism"""
        self._trail_armed = True
        self._trail_peak_price = entry_price * (
            Decimal("1") + self.config.trailing_arm_pct
        )

    def _arm_breakeven_stop(self, entry_price: Decimal):
        """Arm breakeven stop mechanism"""
        self._breakeven_armed = True
        self._breakeven_level = entry_price * (
            Decimal("1") + self.config.breakeven_arm_pct
        )

    def update_position_state(self, current_price: Decimal):
        """Update position state for trailing stops"""
        if not self.current_position:
            return

        # Update trailing stop
        if self._trail_armed and current_price > self._trail_peak_price:
            self._trail_peak_price = current_price

        # Update breakeven stop
        if self._breakeven_armed and not self._breakeven_level:
            entry_price = self.current_position["entry_price"]
            self._breakeven_level = entry_price * (
                Decimal("1") + self.config.breakeven_arm_pct
            )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self._trade_history:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "avg_profit": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
            }

        total_trades = len(self._trade_history)
        wins = sum(1 for trade in self._trade_history if trade["net_profit"] > 0)
        win_rate = wins / total_trades if total_trades > 0 else 0

        total_profit = sum(trade["net_profit"] for trade in self._trade_history)
        avg_profit = total_profit / total_trades

        # Calculate drawdown
        cumulative_profit = 0
        peak = 0
        max_drawdown = 0

        for profit in self._profit_history:
            cumulative_profit += profit
            peak = max(peak, cumulative_profit)
            drawdown = peak - cumulative_profit
            max_drawdown = max(max_drawdown, drawdown)

        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "avg_profit": avg_profit,
            "max_drawdown": max_drawdown,
            "current_streak": self.consecutive_losses,
            "session_trades": self.session_trades,
            "session_wins": self.session_wins,
        }

    def reset_session_stats(self):
        """Reset session statistics"""
        self.session_trades = 0
        self.session_wins = 0
        self.logger.info("Session statistics reset")
