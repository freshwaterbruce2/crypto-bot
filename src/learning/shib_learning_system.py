"""
SHIB/USDT Learning System
=========================

Specialized learning system optimized for single-pair SHIB/USDT micro-profit trading.
Focuses on 0.2% profit targets, low balance optimization, and safety system integration.

This system learns from trading patterns, adapts strategies in real-time, and ensures
all optimizations enhance rather than conflict with safety mechanisms.
"""

import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from ..utils.order_safety_system import OrderSafetySystem
from .universal_learning_manager import EventType, UniversalLearningManager

logger = logging.getLogger(__name__)


@dataclass
class SHIBTradingPattern:
    """Pattern specific to SHIB/USDT trading"""
    pattern_id: str
    symbol: str = 'SHIB/USDT'
    pattern_type: str = 'price_movement'
    confidence: float = 0.0
    success_rate: float = 0.0
    sample_size: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)


@dataclass
class MicroProfitMetrics:
    """Metrics for micro-profit trading optimization"""
    target_profit_pct: float = 0.002  # 0.2% default
    actual_profit_pct: float = 0.0
    success_rate: float = 0.0
    avg_hold_time: float = 0.0
    execution_reliability: float = 0.0
    risk_adjusted_return: float = 0.0
    total_trades: int = 0
    profitable_trades: int = 0


class SHIBLearningSystem:
    """
    Specialized learning system for SHIB/USDT micro-profit trading
    
    Key Features:
    - Learns optimal entry/exit patterns for SHIB price movements
    - Adapts to micro-profit targets (0.1% - 0.5%)
    - Integrates with Order Safety System
    - Optimizes for low balance accounts
    - Real-time strategy parameter adjustment
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logger

        # Core components
        try:
            self.universal_learning = UniversalLearningManager.get_instance()
        except Exception as e:
            self.logger.debug(f"[SHIB_LEARNING] Universal learning manager init error: {e}")
            self.universal_learning = None
        self.bot_instance = None

        # SHIB-specific learning data
        self.price_patterns: Dict[str, SHIBTradingPattern] = {}
        self.trade_history: deque = deque(maxlen=1000)
        self.performance_metrics: Dict[str, MicroProfitMetrics] = {}

        # Pattern analysis data
        self.market_conditions: Dict[str, Any] = {}
        self.timing_patterns: Dict[str, Dict[str, Any]] = {}
        self.failure_patterns: Dict[str, Dict[str, Any]] = {}

        # Strategy optimization
        self.current_strategy_params: Dict[str, Dict[str, Any]] = {}
        self.optimization_history: List[Dict[str, Any]] = []

        # Safety system integration
        self.safety_system: Optional[OrderSafetySystem] = None
        self.safety_constraints: Dict[str, Any] = {}

        # Real-time adaptation
        self.adaptation_triggers: Dict[str, float] = {}
        self.last_adaptation: Dict[str, float] = {}

        # Configuration
        self.primary_symbol = self.config.get('single_pair_focus', {}).get('primary_pair', 'SHIB/USDT')
        self.target_profit_pct = self.config.get('single_pair_focus', {}).get('target_profit_pct', 0.002)
        self.adaptation_frequency = self.config.get('adaptation_frequency', 300)

        self.logger.info(f"[SHIB_LEARNING] Initialized for {self.primary_symbol} with {self.target_profit_pct:.1%} targets")

    async def initialize(self):
        """Initialize the SHIB learning system"""
        try:
            # Initialize performance metrics for primary symbol
            self.performance_metrics[self.primary_symbol] = MicroProfitMetrics(
                target_profit_pct=self.target_profit_pct
            )

            # Set up safety constraints
            self.safety_constraints = {
                'min_order_size_usd': self.config.get('min_order_size_usdt', 1.0),
                'max_position_size_usd': self.config.get('single_pair_focus', {}).get('max_position_size_usd', 10.0),
                'min_tokens': self.config.get('single_pair_focus', {}).get('min_order_shib', 100000),
                'fee_free_trading': self.config.get('fee_free_trading', True)
            }

            # Initialize strategy parameters
            self.current_strategy_params[self.primary_symbol] = {
                'profit_target_pct': self.target_profit_pct,
                'stop_loss_pct': 0.008,  # 0.8% stop loss
                'position_size_pct': 0.1,  # 10% of balance
                'rsi_threshold': 35,
                'volume_spike': 1.5,
                'last_updated': time.time()
            }

            self.logger.info("[SHIB_LEARNING] System initialized successfully")

        except Exception as e:
            self.logger.error(f"[SHIB_LEARNING] Initialization error: {e}")
            raise

    async def set_bot_instance(self, bot):
        """Set bot instance for full integration"""
        self.bot_instance = bot

        # Initialize safety system integration
        if hasattr(bot, 'order_safety_system'):
            self.safety_system = bot.order_safety_system
        elif hasattr(bot, 'config'):
            self.safety_system = OrderSafetySystem(config=bot.config)

        self.logger.info("[SHIB_LEARNING] Bot instance set - full integration enabled")

    async def record_price_update(self, symbol: str, price: float, timestamp: float):
        """Record price update for pattern learning"""
        if symbol != self.primary_symbol:
            return

        # Store price data for pattern analysis
        if 'price_history' not in self.market_conditions:
            self.market_conditions['price_history'] = deque(maxlen=1000)

        self.market_conditions['price_history'].append({
            'price': price,
            'timestamp': timestamp
        })

        # Update current market state
        if len(self.market_conditions['price_history']) >= 2:
            prices = [p['price'] for p in list(self.market_conditions['price_history'])[-10:]]
            self.market_conditions['current_volatility'] = np.std(prices) / np.mean(prices) if prices else 0
            self.market_conditions['price_trend'] = self._calculate_trend(prices)

    def _calculate_trend(self, prices: List[float]) -> str:
        """Calculate price trend from recent prices"""
        if len(prices) < 3:
            return 'sideways'

        # Simple trend calculation
        start_price = statistics.mean(prices[:3])
        end_price = statistics.mean(prices[-3:])
        change_pct = (end_price - start_price) / start_price

        if change_pct > 0.01:
            return 'uptrend'
        elif change_pct < -0.01:
            return 'downtrend'
        else:
            return 'sideways'

    async def get_price_patterns(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get learned price patterns for symbol"""
        if symbol != self.primary_symbol:
            return None

        if 'price_history' not in self.market_conditions:
            return {
                'micro_movement_trend': 'sideways',
                'volatility_range': {'min': 0.00001234, 'max': 0.00001234, 'avg_volatility': 0},
                'optimal_entry_threshold': 0.000000001,
                'pattern_confidence': 0.1
            }

        price_data = list(self.market_conditions['price_history'])
        if len(price_data) < 2:
            return {
                'micro_movement_trend': 'sideways',
                'volatility_range': {'min': 0.00001234, 'max': 0.00001234, 'avg_volatility': 0},
                'optimal_entry_threshold': 0.000000001,
                'pattern_confidence': 0.1
            }

        prices = [p['price'] for p in price_data]

        # Calculate micro-movement patterns
        price_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        avg_change = statistics.mean(price_changes)
        volatility = statistics.stdev(price_changes) if len(price_changes) > 1 else 0

        return {
            'micro_movement_trend': self.market_conditions.get('price_trend', 'sideways'),
            'volatility_range': {
                'min': min(prices),
                'max': max(prices),
                'avg_volatility': volatility
            },
            'optimal_entry_threshold': abs(avg_change) * 1.5,  # 1.5x average movement
            'pattern_confidence': min(len(price_data) / 100.0, 1.0)  # Higher confidence with more data
        }

    async def record_trade_result(self, trade: Dict[str, Any]):
        """Record trade result for learning"""
        symbol = trade.get('symbol', self.primary_symbol)
        if symbol != self.primary_symbol:
            return

        # Add to trade history
        trade['recorded_at'] = time.time()
        self.trade_history.append(trade)

        # Update performance metrics
        metrics = self.performance_metrics.get(symbol, MicroProfitMetrics())
        metrics.total_trades += 1

        if trade.get('success', False):
            metrics.profitable_trades += 1
            if 'profit_pct' in trade:
                metrics.actual_profit_pct = (
                    (metrics.actual_profit_pct * (metrics.profitable_trades - 1) + trade['profit_pct'])
                    / metrics.profitable_trades
                )

        metrics.success_rate = metrics.profitable_trades / metrics.total_trades if metrics.total_trades > 0 else 0

        # Update timing data
        if 'execution_time_ms' in trade:
            if symbol not in self.timing_patterns:
                self.timing_patterns[symbol] = {'execution_times': deque(maxlen=100)}
            self.timing_patterns[symbol]['execution_times'].append(trade['execution_time_ms'])

        self.performance_metrics[symbol] = metrics

        # Record with universal learning manager
        if self.universal_learning:
            try:
                self.universal_learning.record_event(
                    EventType.TRADE_SUCCESS if trade.get('success') else EventType.TRADE_FAILURE,
                    'shib_learning_system',
                    trade.get('success', False),
                    trade
                )
            except Exception as e:
                self.logger.debug(f"[SHIB_LEARNING] Universal learning record error: {e}")

    async def get_optimal_trade_sizes(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get optimal trade sizes based on learned patterns"""
        if symbol != self.primary_symbol:
            return None

        # Analyze trade history for optimal sizes
        successful_trades = [t for t in self.trade_history if t.get('success', False)]
        if len(successful_trades) < 5:
            return {
                'min_tokens': self.safety_constraints['min_tokens'],
                'max_tokens': self.safety_constraints['min_tokens'] * 10,
                'success_rate_at_optimal': 0.5
            }

        # Group trades by size ranges
        token_amounts = [t.get('amount_tokens', 0) for t in successful_trades if 'amount_tokens' in t]
        if not token_amounts:
            return None

        # Find optimal range based on success rates
        min_tokens = max(min(token_amounts), self.safety_constraints['min_tokens'])
        max_tokens = min(max(token_amounts), self.safety_constraints['min_tokens'] * 20)  # Cap at 20x minimum

        # Calculate success rate in optimal range
        optimal_trades = [t for t in successful_trades
                         if min_tokens <= t.get('amount_tokens', 0) <= max_tokens]
        success_rate = len(optimal_trades) / len([t for t in self.trade_history
                                               if min_tokens <= t.get('amount_tokens', 0) <= max_tokens])

        return {
            'min_tokens': min_tokens,
            'max_tokens': max_tokens,
            'optimal_tokens': statistics.median(token_amounts),
            'success_rate_at_optimal': success_rate
        }

    async def get_optimal_profit_target(self, symbol: str) -> Optional[float]:
        """Get optimal profit target based on market analysis"""
        if symbol != self.primary_symbol:
            return None

        # Analyze different profit targets from trade history
        target_performance = defaultdict(list)

        for trade in self.trade_history:
            if 'target_profit_pct' in trade and 'achieved_target' in trade:
                target = trade['target_profit_pct']
                achieved = trade['achieved_target']
                target_performance[target].append(achieved)

        if not target_performance:
            return self.target_profit_pct  # Return default

        # Find target with best success rate
        best_target = self.target_profit_pct
        best_success_rate = 0

        for target, results in target_performance.items():
            success_rate = sum(results) / len(results)
            if success_rate > best_success_rate and len(results) >= 3:  # Minimum sample size
                best_success_rate = success_rate
                best_target = target

        return best_target

    async def get_timing_patterns(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get optimal timing patterns"""
        if symbol != self.primary_symbol or symbol not in self.timing_patterns:
            return None

        timing_data = self.timing_patterns[symbol]

        # Calculate optimal hold time
        execution_times = list(timing_data.get('execution_times', []))
        if execution_times:
            optimal_hold_time = statistics.median(execution_times) / 1000.0  # Convert to seconds
        else:
            optimal_hold_time = 60.0  # Default 1 minute

        # Analyze trading hours (simplified)
        trade_hours = [datetime.fromtimestamp(t.get('timestamp', time.time())).hour
                      for t in self.trade_history if 'timestamp' in t]

        if trade_hours:
            # Find most active hours
            hour_counts = defaultdict(int)
            for hour in trade_hours:
                hour_counts[hour] += 1
            best_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            best_trading_hours = [hour for hour, count in best_hours]
        else:
            best_trading_hours = [9, 14, 16]  # Default active hours

        return {
            'optimal_hold_time': optimal_hold_time,
            'best_trading_hours': best_trading_hours,
            'avg_execution_time_ms': statistics.mean(execution_times) if execution_times else 250
        }

    async def record_entry_condition_result(self, symbol: str, condition: Dict[str, Any], success_rate: float):
        """Record entry condition performance"""
        if symbol != self.primary_symbol:
            return

        condition_key = f"rsi_{condition.get('rsi_threshold', 0)}_vol_{condition.get('volume_spike', 0)}"

        if 'entry_conditions' not in self.market_conditions:
            self.market_conditions['entry_conditions'] = {}

        self.market_conditions['entry_conditions'][condition_key] = {
            **condition,
            'success_rate': success_rate,
            'last_updated': time.time()
        }

    async def get_optimal_entry_conditions(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get optimal entry conditions"""
        if symbol != self.primary_symbol or 'entry_conditions' not in self.market_conditions:
            return None

        conditions = self.market_conditions['entry_conditions']
        if not conditions:
            return None

        # Find condition with highest success rate
        best_condition = max(conditions.values(), key=lambda x: x.get('success_rate', 0))

        return {
            'rsi_threshold': best_condition.get('rsi_threshold', 35),
            'volume_spike': best_condition.get('volume_spike', 1.5),
            'expected_success_rate': best_condition.get('success_rate', 0.5)
        }

    async def record_risk_scenario_result(self, symbol: str, scenario: Dict[str, Any], drawdown: float):
        """Record risk management scenario results"""
        if symbol != self.primary_symbol:
            return

        scenario_key = f"pos_{scenario.get('max_position_pct', 0)}_sl_{scenario.get('stop_loss_pct', 0)}"

        if 'risk_scenarios' not in self.market_conditions:
            self.market_conditions['risk_scenarios'] = {}

        self.market_conditions['risk_scenarios'][scenario_key] = {
            **scenario,
            'observed_drawdown': drawdown,
            'last_updated': time.time()
        }

    async def get_optimal_risk_parameters(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get optimal risk management parameters"""
        if symbol != self.primary_symbol or 'risk_scenarios' not in self.market_conditions:
            return None

        scenarios = self.market_conditions['risk_scenarios']
        if not scenarios:
            return None

        # Find scenario with lowest drawdown
        best_scenario = min(scenarios.values(), key=lambda x: x.get('observed_drawdown', 1.0))

        return {
            'max_position_pct': best_scenario.get('max_position_pct', 0.1),
            'stop_loss_pct': best_scenario.get('stop_loss_pct', 0.5),
            'expected_drawdown': best_scenario.get('observed_drawdown', 0.02)
        }

    async def record_market_condition_performance(self, symbol: str, condition: Dict[str, Any]):
        """Record performance under different market conditions"""
        if symbol != self.primary_symbol:
            return

        condition_key = f"{condition.get('trend', 'sideways')}_{condition.get('volatility', 0.05):.2f}"

        if 'market_performance' not in self.market_conditions:
            self.market_conditions['market_performance'] = {}

        self.market_conditions['market_performance'][condition_key] = {
            **condition,
            'last_updated': time.time()
        }

    async def get_strategy_for_market_condition(self, symbol: str, current_condition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get recommended strategy for current market condition"""
        if symbol != self.primary_symbol:
            return None

        volatility = current_condition.get('volatility', 0.05)
        trend = current_condition.get('trend', 'sideways')

        # Simple strategy adaptation based on conditions
        if trend == 'uptrend' and volatility < 0.06:
            return {
                'aggressive_mode': True,
                'expected_success_rate': 0.85,
                'recommended_position_size': 0.15
            }
        elif trend == 'downtrend':
            return {
                'aggressive_mode': False,
                'expected_success_rate': 0.55,
                'recommended_position_size': 0.05
            }
        else:
            return {
                'aggressive_mode': False,
                'expected_success_rate': 0.7,
                'recommended_position_size': 0.1
            }

    async def get_performance_metrics(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive performance metrics"""
        if symbol != self.primary_symbol:
            return None

        metrics = self.performance_metrics.get(symbol, MicroProfitMetrics())

        # Calculate additional metrics from trade history
        symbol_trades = [t for t in self.trade_history if t.get('symbol') == symbol]

        if symbol_trades:
            total_profit = sum(t.get('profit_usd', 0) for t in symbol_trades)
            profitable_trades = [t for t in symbol_trades if t.get('profit_usd', 0) > 0]
            losing_trades = [t for t in symbol_trades if t.get('profit_usd', 0) < 0]

            avg_win = statistics.mean([t['profit_usd'] for t in profitable_trades]) if profitable_trades else 0
            avg_loss = abs(statistics.mean([t['profit_usd'] for t in losing_trades])) if losing_trades else 0
            profit_factor = avg_win / avg_loss if avg_loss > 0 else float('inf')
        else:
            total_profit = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 1.0

        return {
            'success_rate': metrics.success_rate,
            'total_trades': metrics.total_trades,
            'total_profit_usd': total_profit,
            'avg_profit_per_trade': total_profit / metrics.total_trades if metrics.total_trades > 0 else 0,
            'avg_winning_trade': avg_win,
            'avg_losing_trade': avg_loss,
            'profit_factor': profit_factor,
            'target_profit_pct': metrics.target_profit_pct,
            'actual_profit_pct': metrics.actual_profit_pct
        }

    async def get_execution_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get trade execution analysis"""
        if symbol != self.primary_symbol:
            return None

        execution_times = []
        successful_executions = 0
        total_executions = 0

        for trade in self.trade_history:
            if trade.get('symbol') == symbol and 'execution_time_ms' in trade:
                execution_times.append(trade['execution_time_ms'])
                total_executions += 1
                if trade.get('success', False):
                    successful_executions += 1

        if not execution_times:
            return {
                'avg_execution_time_ms': 250,
                'execution_reliability': 0.5
            }

        return {
            'avg_execution_time_ms': statistics.mean(execution_times),
            'execution_reliability': successful_executions / total_executions if total_executions > 0 else 0.5,
            'fastest_execution_ms': min(execution_times),
            'slowest_execution_ms': max(execution_times)
        }

    async def get_learning_progress(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get learning progress and effectiveness metrics"""
        if symbol != self.primary_symbol:
            return None

        # Analyze improvement over time
        symbol_trades = [t for t in self.trade_history if t.get('symbol') == symbol]
        if len(symbol_trades) < 10:
            return {
                'performance_trend': 'insufficient_data',
                'learning_effectiveness': 0.5
            }

        # Split into early and recent periods
        mid_point = len(symbol_trades) // 2
        early_trades = symbol_trades[:mid_point]
        recent_trades = symbol_trades[mid_point:]

        early_success_rate = sum(1 for t in early_trades if t.get('success', False)) / len(early_trades)
        recent_success_rate = sum(1 for t in recent_trades if t.get('success', False)) / len(recent_trades)

        improvement = recent_success_rate - early_success_rate

        return {
            'performance_trend': 'improving' if improvement > 0.05 else 'stable' if improvement > -0.05 else 'declining',
            'learning_effectiveness': max(0, min(1, 0.5 + improvement * 2)),  # Scale to 0-1
            'early_success_rate': early_success_rate,
            'recent_success_rate': recent_success_rate,
            'improvement': improvement
        }

    async def get_failure_patterns(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get identified failure patterns"""
        if symbol != self.primary_symbol:
            return None

        # Analyze failed trades for patterns
        failed_trades = [t for t in self.trade_history if not t.get('success', True)]

        if len(failed_trades) < 3:
            return {}

        # Group by failure reasons
        failure_reasons = defaultdict(list)
        for trade in failed_trades:
            reason = trade.get('failure_reason', 'unknown')
            failure_reasons[reason].append(trade)

        patterns = {}
        for reason, trades in failure_reasons.items():
            if len(trades) >= 2:  # Minimum pattern size
                patterns[reason] = {
                    'frequency': len(trades),
                    'avoidance_score': min(0.9, len(trades) / len(failed_trades) + 0.5),
                    'common_conditions': self._extract_common_conditions(trades)
                }

        return patterns

    def _extract_common_conditions(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract common conditions from failed trades"""
        conditions = {}

        # Extract RSI conditions if available
        rsi_values = [t.get('entry_condition', {}).get('rsi', 0) for t in trades
                     if 'entry_condition' in t and 'rsi' in t['entry_condition']]
        if rsi_values:
            conditions['avg_rsi'] = statistics.mean(rsi_values)

        # Extract volume conditions
        volume_spikes = [t.get('entry_condition', {}).get('volume_spike', 0) for t in trades
                        if 'entry_condition' in t and 'volume_spike' in t['entry_condition']]
        if volume_spikes:
            conditions['avg_volume_spike'] = statistics.mean(volume_spikes)

        return conditions

    async def get_failure_adjusted_conditions(self, symbol: str) -> Dict[str, Any]:
        """Get entry conditions adjusted to avoid failure patterns"""
        failure_patterns = await self.get_failure_patterns(symbol)

        # Default conservative conditions
        adjusted_conditions = {
            'rsi_min_threshold': 30,
            'rsi_max_threshold': 70,
            'volume_spike_min': 1.2,
            'volume_spike_max': 2.5
        }

        if not failure_patterns:
            return adjusted_conditions

        # Adjust based on failure patterns
        for pattern_name, pattern_data in failure_patterns.items():
            common_conditions = pattern_data.get('common_conditions', {})

            if 'avg_rsi' in common_conditions:
                # Avoid RSI ranges that commonly fail
                failed_rsi = common_conditions['avg_rsi']
                if failed_rsi < 30:
                    adjusted_conditions['rsi_min_threshold'] = 35
                elif failed_rsi > 70:
                    adjusted_conditions['rsi_max_threshold'] = 65

            if 'avg_volume_spike' in common_conditions:
                # Avoid extreme volume spikes
                failed_volume = common_conditions['avg_volume_spike']
                if failed_volume > 3.0:
                    adjusted_conditions['volume_spike_max'] = 2.8

        return adjusted_conditions

    # Safety system integration methods

    async def record_safety_system_performance(self, performance_data: Dict[str, Any]):
        """Record safety system performance for learning"""
        if 'safety_performance' not in self.market_conditions:
            self.market_conditions['safety_performance'] = []

        performance_entry = {
            **performance_data,
            'timestamp': time.time()
        }

        self.market_conditions['safety_performance'].append(performance_entry)

        # Keep only recent performance data
        if len(self.market_conditions['safety_performance']) > 100:
            self.market_conditions['safety_performance'] = self.market_conditions['safety_performance'][-100:]

    async def get_safety_system_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for safety system optimization"""
        safety_data = self.market_conditions.get('safety_performance', [])

        if not safety_data:
            return {
                'min_order_buffer': 1.0,
                'balance_check_frequency': 30,
                'validation_strictness': 'standard'
            }

        # Analyze safety performance
        recent_data = safety_data[-10:] if len(safety_data) > 10 else safety_data
        avg_success_rate = statistics.mean([d.get('min_order_validation_success_rate', 0.95) for d in recent_data])

        # Adjust recommendations based on performance
        recommendations = {
            'min_order_buffer': 1.5 if avg_success_rate < 0.9 else 1.0,
            'balance_check_frequency': 15 if avg_success_rate < 0.95 else 30,
            'validation_strictness': 'strict' if avg_success_rate < 0.9 else 'standard'
        }

        return recommendations

    async def record_balance_aware_trade(self, scenario: Dict[str, Any]):
        """Record balance-aware trading scenario"""
        if 'balance_scenarios' not in self.market_conditions:
            self.market_conditions['balance_scenarios'] = []

        scenario['timestamp'] = time.time()
        self.market_conditions['balance_scenarios'].append(scenario)

        # Keep recent data
        if len(self.market_conditions['balance_scenarios']) > 100:
            self.market_conditions['balance_scenarios'] = self.market_conditions['balance_scenarios'][-100:]

    async def get_balance_optimization_strategy(self) -> Dict[str, Any]:
        """Get balance utilization optimization strategy"""
        scenarios = self.market_conditions.get('balance_scenarios', [])

        if not scenarios:
            return {
                'optimal_utilization_pct': 0.2,  # 20% of balance
                'min_reserve_balance': 5.0,
                'max_single_trade_pct': 0.1
            }

        # Analyze successful scenarios
        successful_scenarios = [s for s in scenarios if s.get('success', False)]

        if successful_scenarios:
            utilization_rates = []
            for scenario in successful_scenarios:
                if scenario.get('usdt_balance', 0) > 0:
                    utilization_rate = scenario.get('trade_size', 0) / scenario['usdt_balance']
                    utilization_rates.append(utilization_rate)

            if utilization_rates:
                optimal_utilization = statistics.median(utilization_rates)
            else:
                optimal_utilization = 0.2
        else:
            optimal_utilization = 0.1  # Conservative if no successful data

        return {
            'optimal_utilization_pct': min(0.25, optimal_utilization),  # Cap at 25%
            'min_reserve_balance': 5.0,
            'max_single_trade_pct': min(0.15, optimal_utilization * 1.5)
        }

    async def resolve_safety_conflict(self, learning_rec: Dict[str, Any], safety_req: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflicts between learning recommendations and safety requirements"""
        resolution = {}

        for param, learning_value in learning_rec.items():
            if param in safety_req:
                safety_value = safety_req[param]

                # Always favor the more conservative (safer) value
                if param.startswith('min_'):
                    resolved_value = max(learning_value, safety_value)
                elif param.startswith('max_'):
                    resolved_value = min(learning_value, safety_value)
                else:
                    resolved_value = safety_value  # Default to safety requirement

                resolution[param] = resolved_value
            else:
                resolution[param] = learning_value

        return {
            'resolved_parameters': resolution,
            'resolved_value': list(resolution.values())[0] if len(resolution) == 1 else None,
            'safety_maintained': True,
            'conflicts_resolved': len([k for k in learning_rec.keys() if k in safety_req])
        }

    async def validate_learned_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate learned parameters against safety requirements"""
        violations = []
        corrected_params = params.copy()

        # Check minimum order size
        if 'min_order_size_usd' in params:
            min_required = self.safety_constraints['min_order_size_usd']
            if params['min_order_size_usd'] < min_required:
                violations.append(f"min_order_size_usd {params['min_order_size_usd']} < required {min_required}")
                corrected_params['min_order_size_usd'] = min_required

        # Check maximum position size
        if 'max_position_size_usd' in params:
            max_allowed = self.safety_constraints['max_position_size_usd']
            if params['max_position_size_usd'] > max_allowed:
                violations.append(f"max_position_size_usd {params['max_position_size_usd']} > allowed {max_allowed}")
                corrected_params['max_position_size_usd'] = max_allowed

        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'corrected_parameters': corrected_params,
            'safety_compliant': len(violations) == 0
        }

    # Real-time adaptation methods

    async def process_real_time_update(self, update: Dict[str, Any]):
        """Process real-time market update"""
        symbol = update.get('symbol')
        if symbol != self.primary_symbol:
            return

        # Update market conditions
        if 'price' in update:
            await self.record_price_update(symbol, update['price'], update.get('timestamp', time.time()))

        # Update current patterns with new data
        current_patterns = await self.get_current_patterns(symbol)
        if current_patterns:
            current_patterns['last_update'] = time.time()
            self.price_patterns[f"{symbol}_current"] = SHIBTradingPattern(
                pattern_id=f"{symbol}_current",
                symbol=symbol,
                data=current_patterns,
                last_updated=time.time()
            )

    async def get_current_patterns(self, symbol: str) -> Dict[str, Any]:
        """Get current trading patterns"""
        if symbol != self.primary_symbol:
            return {}

        # Get price patterns
        price_patterns = await self.get_price_patterns(symbol)

        # Combine with timing and performance data
        current_patterns = {
            'price_patterns': price_patterns or {},
            'performance_metrics': await self.get_performance_metrics(symbol) or {},
            'market_conditions': {
                'volatility': self.market_conditions.get('current_volatility', 0.05),
                'trend': self.market_conditions.get('price_trend', 'sideways')
            },
            'last_update': time.time()
        }

        return current_patterns

    async def set_strategy_parameters(self, symbol: str, params: Dict[str, Any]):
        """Set strategy parameters for symbol"""
        if symbol != self.primary_symbol:
            return

        params['last_updated'] = time.time()
        self.current_strategy_params[symbol] = params

    async def get_strategy_parameters(self, symbol: str) -> Dict[str, Any]:
        """Get current strategy parameters"""
        return self.current_strategy_params.get(symbol, {})

    async def record_performance_feedback(self, symbol: str, feedback: Dict[str, Any]):
        """Record performance feedback for adaptation"""
        if symbol != self.primary_symbol:
            return

        if 'performance_feedback' not in self.market_conditions:
            self.market_conditions['performance_feedback'] = deque(maxlen=50)

        feedback['timestamp'] = time.time()
        feedback['symbol'] = symbol
        self.market_conditions['performance_feedback'].append(feedback)

    async def trigger_adaptive_adjustment(self, symbol: str):
        """Trigger adaptive parameter adjustment"""
        if symbol != self.primary_symbol:
            return

        feedback_data = list(self.market_conditions.get('performance_feedback', []))
        if len(feedback_data) < 3:
            return  # Need minimum feedback

        # Analyze recent performance
        recent_feedback = feedback_data[-5:]  # Last 5 feedback entries
        poor_performance_count = sum(1 for f in recent_feedback if not f.get('target_hit', True))

        if poor_performance_count >= 3:  # Majority poor performance
            # Adjust parameters to be more conservative
            current_params = self.current_strategy_params.get(symbol, {})

            # Tighten stop loss
            if 'stop_loss_pct' in current_params:
                current_params['stop_loss_pct'] = max(0.003, current_params['stop_loss_pct'] * 0.8)

            # Reduce position size
            if 'position_size_pct' in current_params:
                current_params['position_size_pct'] = max(0.05, current_params['position_size_pct'] * 0.8)

            # Update parameters
            current_params['last_updated'] = time.time()
            current_params['adaptation_reason'] = 'poor_performance_detected'
            self.current_strategy_params[symbol] = current_params

            self.logger.info(f"[SHIB_LEARNING] Adapted parameters for {symbol} due to poor performance")

    # Comprehensive analysis methods

    async def analyze_patterns(self, symbol: str):
        """Perform comprehensive pattern analysis"""
        if symbol != self.primary_symbol:
            return

        # Analyze price patterns
        price_analysis = await self.get_price_patterns(symbol)

        # Analyze timing patterns
        timing_analysis = await self.get_timing_patterns(symbol)

        # Analyze failure patterns
        failure_analysis = await self.get_failure_patterns(symbol)

        # Store analysis results
        analysis_result = {
            'price_patterns': price_analysis,
            'timing_patterns': timing_analysis,
            'failure_patterns': failure_analysis,
            'analysis_timestamp': time.time()
        }

        self.price_patterns[f"{symbol}_analysis"] = SHIBTradingPattern(
            pattern_id=f"{symbol}_analysis",
            symbol=symbol,
            pattern_type='comprehensive_analysis',
            data=analysis_result,
            confidence=0.8,
            last_updated=time.time()
        )

        self.logger.info(f"[SHIB_LEARNING] Completed comprehensive pattern analysis for {symbol}")

    async def optimize_strategy_parameters(self, symbol: str) -> Dict[str, Any]:
        """Optimize strategy parameters based on learned patterns"""
        if symbol != self.primary_symbol:
            return {'success': False, 'error': 'Unsupported symbol'}

        try:
            # Get current analysis
            await self.analyze_patterns(symbol)

            # Get optimal parameters from different analyses
            optimal_entry = await self.get_optimal_entry_conditions(symbol)
            optimal_risk = await self.get_optimal_risk_parameters(symbol)
            optimal_profit_target = await self.get_optimal_profit_target(symbol)

            # Combine into optimized strategy
            optimized_params = self.current_strategy_params.get(symbol, {}).copy()

            if optimal_entry:
                optimized_params.update({
                    'rsi_threshold': optimal_entry.get('rsi_threshold', 35),
                    'volume_spike': optimal_entry.get('volume_spike', 1.5)
                })

            if optimal_risk:
                optimized_params.update({
                    'position_size_pct': optimal_risk.get('max_position_pct', 0.1),
                    'stop_loss_pct': optimal_risk.get('stop_loss_pct', 0.008)
                })

            if optimal_profit_target:
                optimized_params['profit_target_pct'] = optimal_profit_target

            optimized_params['optimization_timestamp'] = time.time()
            optimized_params['optimization_version'] = len(self.optimization_history) + 1

            # Store optimization history
            self.optimization_history.append({
                'timestamp': time.time(),
                'symbol': symbol,
                'previous_params': self.current_strategy_params.get(symbol, {}),
                'optimized_params': optimized_params,
                'optimization_reason': 'pattern_analysis'
            })

            return {
                'success': True,
                'optimized_parameters': optimized_params,
                'improvements_identified': len([k for k in optimized_params.keys()
                                               if k in self.current_strategy_params.get(symbol, {})]),
                'optimization_confidence': 0.8
            }

        except Exception as e:
            self.logger.error(f"[SHIB_LEARNING] Strategy optimization error: {e}")
            return {'success': False, 'error': str(e)}

    async def validate_optimized_strategy(self, symbol: str) -> Dict[str, Any]:
        """Validate optimized strategy against safety systems"""
        if symbol != self.primary_symbol:
            return {'safety_compliant': True}

        # Get latest optimization
        if not self.optimization_history:
            return {'safety_compliant': True, 'message': 'No optimization to validate'}

        latest_optimization = self.optimization_history[-1]
        optimized_params = latest_optimization.get('optimized_params', {})

        # Validate against safety constraints
        validation_result = await self.validate_learned_parameters(optimized_params)

        return {
            'safety_compliant': validation_result['valid'],
            'violations': validation_result.get('violations', []),
            'corrected_parameters': validation_result.get('corrected_parameters', {}),
            'validation_timestamp': time.time()
        }

    async def apply_learned_improvements(self, symbol: str) -> Dict[str, Any]:
        """Apply learned improvements to strategy"""
        if symbol != self.primary_symbol:
            return {'improvements_applied': 0}

        if not self.optimization_history:
            return {'improvements_applied': 0, 'message': 'No optimizations available'}

        # Get validated optimization
        validation_result = await self.validate_optimized_strategy(symbol)

        if validation_result['safety_compliant']:
            # Apply optimized parameters
            latest_optimization = self.optimization_history[-1]
            optimized_params = latest_optimization.get('optimized_params', {})

            await self.set_strategy_parameters(symbol, optimized_params)

            improvements_count = len([k for k in optimized_params.keys()
                                    if k not in ['optimization_timestamp', 'optimization_version']])

            self.logger.info(f"[SHIB_LEARNING] Applied {improvements_count} learned improvements for {symbol}")

            return {
                'improvements_applied': improvements_count,
                'applied_parameters': optimized_params,
                'application_timestamp': time.time()
            }
        else:
            # Apply corrected parameters instead
            corrected_params = validation_result.get('corrected_parameters', {})
            await self.set_strategy_parameters(symbol, corrected_params)

            return {
                'improvements_applied': len(corrected_params),
                'applied_parameters': corrected_params,
                'safety_corrections_made': len(validation_result.get('violations', [])),
                'application_timestamp': time.time()
            }

    async def get_comprehensive_performance_report(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive performance and learning effectiveness report"""
        if symbol != self.primary_symbol:
            return {}

        # Gather all metrics
        performance_metrics = await self.get_performance_metrics(symbol) or {}
        learning_progress = await self.get_learning_progress(symbol) or {}
        execution_analysis = await self.get_execution_analysis(symbol) or {}

        # Calculate learning effectiveness score
        learning_factors = [
            learning_progress.get('learning_effectiveness', 0.5),
            min(1.0, performance_metrics.get('success_rate', 0.5) * 1.2),
            min(1.0, execution_analysis.get('execution_reliability', 0.5) * 1.1),
            min(1.0, len(self.trade_history) / 50.0)  # Data sufficiency factor
        ]
        learning_effectiveness_score = statistics.mean(learning_factors)

        # Calculate safety integration score
        safety_factors = [
            1.0 if len(self.market_conditions.get('safety_performance', [])) > 0 else 0.5,
            1.0 if len(self.optimization_history) > 0 else 0.7,
            0.9  # Base score for safety-first design
        ]
        safety_integration_score = statistics.mean(safety_factors)

        # Calculate micro-profit optimization score
        target_profit = self.target_profit_pct
        actual_profit = performance_metrics.get('actual_profit_pct', 0)
        profit_target_effectiveness = 1.0 - min(1.0, abs(target_profit - actual_profit) / target_profit) if target_profit > 0 else 0.5

        micro_profit_factors = [
            profit_target_effectiveness,
            performance_metrics.get('success_rate', 0.5),
            min(1.0, performance_metrics.get('profit_factor', 1.0) / 1.5)
        ]
        micro_profit_optimization_score = statistics.mean(micro_profit_factors)

        return {
            'symbol': symbol,
            'learning_effectiveness_score': learning_effectiveness_score,
            'safety_integration_score': safety_integration_score,
            'micro_profit_optimization_score': micro_profit_optimization_score,
            'overall_performance': {
                **performance_metrics,
                'total_patterns_learned': len(self.price_patterns),
                'optimizations_performed': len(self.optimization_history),
                'adaptation_events': len(self.market_conditions.get('performance_feedback', []))
            },
            'learning_insights': {
                'primary_strengths': self._identify_strengths(),
                'improvement_areas': self._identify_improvement_areas(),
                'next_learning_priorities': self._get_learning_priorities()
            },
            'report_timestamp': time.time()
        }

    def _identify_strengths(self) -> List[str]:
        """Identify system strengths based on performance"""
        strengths = []

        metrics = self.performance_metrics.get(self.primary_symbol, MicroProfitMetrics())

        if metrics.success_rate > 0.7:
            strengths.append("High success rate in micro-profit trades")

        if len(self.trade_history) > 50:
            strengths.append("Sufficient data collection for pattern recognition")

        if len(self.optimization_history) > 0:
            strengths.append("Active strategy optimization and adaptation")

        if self.safety_system is not None:
            strengths.append("Integrated safety system validation")

        return strengths or ["Learning system operational"]

    def _identify_improvement_areas(self) -> List[str]:
        """Identify areas needing improvement"""
        improvement_areas = []

        metrics = self.performance_metrics.get(self.primary_symbol, MicroProfitMetrics())

        if metrics.success_rate < 0.6:
            improvement_areas.append("Success rate optimization needed")

        if len(self.trade_history) < 20:
            improvement_areas.append("More trade data needed for robust learning")

        if not self.market_conditions.get('safety_performance'):
            improvement_areas.append("Safety system performance tracking")

        execution_times = list(self.timing_patterns.get(self.primary_symbol, {}).get('execution_times', []))
        if execution_times and statistics.mean(execution_times) > 500:
            improvement_areas.append("Execution speed optimization")

        return improvement_areas or ["Continue current learning approach"]

    def _get_learning_priorities(self) -> List[str]:
        """Get next learning priorities"""
        priorities = []

        if len(self.trade_history) < 100:
            priorities.append("Expand trade data collection")

        if len(self.optimization_history) == 0:
            priorities.append("Implement strategy optimization")

        if not self.market_conditions.get('market_performance'):
            priorities.append("Market condition adaptation learning")

        if not self.failure_patterns:
            priorities.append("Failure pattern recognition")

        return priorities or ["Maintain current learning processes"]


# Utility functions for easy integration
async def create_shib_learning_system(config: Dict[str, Any] = None) -> SHIBLearningSystem:
    """Create and initialize SHIB learning system"""
    system = SHIBLearningSystem(config)
    await system.initialize()
    return system


async def optimize_for_shib_trading(learning_system: SHIBLearningSystem,
                                   trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Optimize system for SHIB trading using historical data"""
    symbol = 'SHIB/USDT'

    # Feed historical data
    for trade in trade_history:
        await learning_system.record_trade_result(trade)

    # Perform optimization
    optimization_result = await learning_system.optimize_strategy_parameters(symbol)
    validation_result = await learning_system.validate_optimized_strategy(symbol)

    if validation_result['safety_compliant']:
        application_result = await learning_system.apply_learned_improvements(symbol)
        return {
            'success': True,
            'optimization': optimization_result,
            'validation': validation_result,
            'application': application_result
        }
    else:
        return {
            'success': False,
            'optimization': optimization_result,
            'validation': validation_result,
            'safety_issues': validation_result.get('violations', [])
        }
