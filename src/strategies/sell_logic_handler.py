"""
Sell Logic Handler - Centralized sell decision making

This module consolidates all sell-side logic from various strategies,
providing a unified interface for making sell decisions.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SellReason(Enum):
    """Reasons for selling"""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    TECHNICAL_SIGNAL = "technical_signal"
    RISK_REDUCTION = "risk_reduction"
    REBALANCING = "rebalancing"
    TIME_EXIT = "time_exit"
    EMERGENCY = "emergency"


class SellUrgency(Enum):
    """Urgency levels for sell orders"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SellSignal:
    """Structured sell signal with metadata"""
    symbol: str
    action: str  # 'sell' or 'hold'
    reason: SellReason
    urgency: SellUrgency
    confidence: float  # 0.0 to 1.0
    reasons_detail: list[str]
    suggested_percentage: float  # Percentage of position to sell
    limit_price: Optional[float] = None
    metadata: dict[str, Any] = None


class SellLogicHandler:
    """
    Centralized handler for all sell-side trading logic.
    Manages profit taking, stop losses, and strategic exits.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize sell logic handler"""
        self.config = config

        # Unified profit taking parameters from config (micro-profit optimized)
        self.take_profit_levels = config.get('take_profit_levels', [0.001, 0.002, 0.003, 0.005])  # 0.1%, 0.2%, 0.3%, 0.5%
        self.take_profit_percentages = config.get('take_profit_percentages', [0.25, 0.25, 0.25, 0.25])  # Equal distribution

        # Enhanced stop loss parameters aligned with config
        self.stop_loss_percentage = config.get('stop_loss_pct', 0.008)  # 0.8% from config
        self.micro_stop_loss = config.get('fee_free_scalping', {}).get('stop_loss_pct', 0.001)  # 0.1% for micro trades
        self.trailing_stop_distance = config.get('risk_management', {}).get('trailing_stop_distance_pct', 0.003) / 100  # 0.3%
        self.trailing_stop_activation = config.get('risk_management', {}).get('trailing_stop_activation_pct', 0.005) / 100  # 0.5%
        self.use_trailing_stop = config.get('use_trailing_stop', True)

        # Dynamic stop loss based on position value
        self.use_dynamic_stops = config.get('ultra_tight_stops', True)

        # Time-based exits
        self.max_hold_time_hours = config.get('max_hold_time_hours', 24)
        self.stale_position_hours = config.get('stale_position_hours', 72)

        # Risk management
        self.max_position_loss = config.get('max_position_loss', 0.05)  # 5% max loss
        self.portfolio_risk_threshold = config.get('portfolio_risk_threshold', 0.10)  # 10% portfolio risk

        # Signal thresholds - Optimized for fast execution
        self.min_sell_confidence = config.get('advanced_strategy_params', {}).get('confidence_thresholds', {}).get('sell', 0.2)
        self.emergency_sell_confidence = config.get('advanced_strategy_params', {}).get('confidence_thresholds', {}).get('emergency', 0.1)

        # Performance optimization settings
        self.batch_price_updates = config.get('micro_profit_optimization', {}).get('batch_processing', True)
        self.target_latency_ms = config.get('micro_profit_optimization', {}).get('target_latency_ms', 100)
        self.parallel_validation = config.get('micro_profit_optimization', {}).get('parallel_validation', True)

        # Position tracking
        self.position_high_water_marks = {}  # Track highest price for trailing stops

        logger.info(f"[SELL_HANDLER] Initialized with stop_loss={self.stop_loss_percentage}, "
                   f"take_profit_levels={self.take_profit_levels}")

    async def evaluate_sell_opportunity(self, position_data: dict[str, Any]) -> SellSignal:
        """
        Evaluate whether to sell based on comprehensive analysis

        Args:
            position_data: Current position and market data

        Returns:
            SellSignal with decision and metadata
        """
        try:
            symbol = position_data.get('symbol', 'UNKNOWN')
            entry_price = position_data.get('entry_price', 0)
            current_price = position_data.get('current_price', 0)
            position_size = position_data.get('position_size', 0)
            entry_time = position_data.get('entry_time')

            if not all([entry_price, current_price, position_size]):
                return SellSignal(
                    symbol=symbol,
                    action='hold',
                    reason=SellReason.TECHNICAL_SIGNAL,
                    urgency=SellUrgency.LOW,
                    confidence=0,
                    reasons_detail=['Invalid position data'],
                    suggested_percentage=0
                )

            # Calculate position metrics
            pnl_percentage = (current_price - entry_price) / entry_price
            position_age_hours = self._calculate_position_age(entry_time)

            # Update high water mark for trailing stop
            self._update_high_water_mark(symbol, current_price)

            # Check various sell conditions in order of priority

            # 1. Emergency conditions (stop loss, risk limits)
            emergency_signal = self._check_emergency_conditions(
                symbol, pnl_percentage, position_data
            )
            if emergency_signal and emergency_signal.action == 'sell':
                return emergency_signal

            # 2. Profit taking conditions
            profit_signal = self._check_profit_conditions(
                symbol, pnl_percentage, current_price, entry_price, position_age_hours
            )
            if profit_signal and profit_signal.action == 'sell':
                return profit_signal

            # 3. Trailing stop
            if self.use_trailing_stop:
                trailing_signal = self._check_trailing_stop(
                    symbol, current_price, entry_price
                )
                if trailing_signal and trailing_signal.action == 'sell':
                    return trailing_signal

            # 4. Technical indicators
            technical_signal = self._check_technical_indicators(position_data)
            if technical_signal and technical_signal.action == 'sell':
                return technical_signal

            # 5. Time-based exits
            time_signal = self._check_time_exits(
                symbol, position_age_hours, pnl_percentage
            )
            if time_signal and time_signal.action == 'sell':
                return time_signal

            # 6. Portfolio rebalancing
            rebalance_signal = self._check_rebalancing_needs(position_data)
            if rebalance_signal and rebalance_signal.action == 'sell':
                return rebalance_signal

            # No sell conditions met
            return SellSignal(
                symbol=symbol,
                action='hold',
                reason=SellReason.TECHNICAL_SIGNAL,
                urgency=SellUrgency.LOW,
                confidence=0,
                reasons_detail=['No sell conditions met'],
                suggested_percentage=0
            )

        except Exception as e:
            logger.error(f"[SELL_HANDLER] Error evaluating {position_data.get('symbol')}: {e}")
            return SellSignal(
                symbol=position_data.get('symbol', 'UNKNOWN'),
                action='hold',
                reason=SellReason.TECHNICAL_SIGNAL,
                urgency=SellUrgency.LOW,
                confidence=0,
                reasons_detail=[f'Evaluation error: {str(e)}'],
                suggested_percentage=0
            )

    def _calculate_position_age(self, entry_time: Optional[datetime]) -> float:
        """Calculate position age in hours"""
        if not entry_time:
            return 0

        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)

        age = datetime.now() - entry_time
        return age.total_seconds() / 3600

    def _update_high_water_mark(self, symbol: str, current_price: float) -> None:
        """Update high water mark for trailing stop calculation"""
        if symbol not in self.position_high_water_marks:
            self.position_high_water_marks[symbol] = current_price
        else:
            self.position_high_water_marks[symbol] = max(
                self.position_high_water_marks[symbol],
                current_price
            )

    def _check_emergency_conditions(self, symbol: str, pnl_percentage: float,
                                  position_data: dict[str, Any]) -> Optional[SellSignal]:
        """Check for emergency sell conditions with dynamic stops"""
        position_value = position_data.get('position_value', 0)

        # Dynamic stop loss based on position size and age
        stop_loss_threshold = self._calculate_dynamic_stop_loss(position_data)

        # Hard stop loss
        if pnl_percentage <= -stop_loss_threshold:
            # Emergency market order for immediate execution
            return SellSignal(
                symbol=symbol,
                action='sell',
                reason=SellReason.STOP_LOSS,
                urgency=SellUrgency.CRITICAL,
                confidence=1.0,
                reasons_detail=[f'Dynamic stop loss at {pnl_percentage:.3%} (threshold: {stop_loss_threshold:.3%})'],
                suggested_percentage=1.0,
                limit_price=None,  # Market order for immediate execution
                metadata={
                    'pnl_percentage': pnl_percentage,
                    'stop_loss_threshold': stop_loss_threshold,
                    'position_value': position_value,
                    'emergency_exit': True
                }
            )

        # Circuit breaker for excessive losses
        circuit_breaker_loss = self.config.get('circuit_breaker_drawdown', 3.0) / 100
        if pnl_percentage <= -circuit_breaker_loss:
            return SellSignal(
                symbol=symbol,
                action='sell',
                reason=SellReason.EMERGENCY,
                urgency=SellUrgency.CRITICAL,
                confidence=1.0,
                reasons_detail=[f'Circuit breaker triggered: {pnl_percentage:.3%} > {circuit_breaker_loss:.3%}'],
                suggested_percentage=1.0,
                limit_price=None,  # Emergency market order
                metadata={
                    'pnl_percentage': pnl_percentage,
                    'circuit_breaker': True,
                    'emergency_liquidation': True
                }
            )

        # Portfolio risk threshold
        portfolio_risk = position_data.get('portfolio_risk', 0)
        if portfolio_risk > self.portfolio_risk_threshold:
            return SellSignal(
                symbol=symbol,
                action='sell',
                reason=SellReason.RISK_REDUCTION,
                urgency=SellUrgency.HIGH,
                confidence=0.8,
                reasons_detail=[f'Portfolio risk too high: {portfolio_risk:.1%}'],
                suggested_percentage=0.5,  # Sell half to reduce risk
                metadata={'portfolio_risk': portfolio_risk}
            )

        return None

    def _check_profit_conditions(self, symbol: str, pnl_percentage: float,
                               current_price: float, entry_price: float,
                               position_age_hours: float) -> Optional[SellSignal]:
        """Check profit taking conditions with micro-profit optimization"""
        # Fast path for micro-profits (0.1-0.5%)
        if 0.001 <= pnl_percentage <= 0.005:
            # Micro-profit fast execution
            urgency = SellUrgency.HIGH if position_age_hours < 0.5 else SellUrgency.MEDIUM
            confidence = 0.9  # High confidence for quick micro-profits

            return SellSignal(
                symbol=symbol,
                action='sell',
                reason=SellReason.TAKE_PROFIT,
                urgency=urgency,
                confidence=confidence,
                reasons_detail=[f'Micro-profit target: {pnl_percentage:.3%} in {position_age_hours:.1f}h'],
                suggested_percentage=1.0,  # Full position for micro-profits
                limit_price=None,  # Market order for speed
                metadata={
                    'pnl_percentage': pnl_percentage,
                    'micro_profit': True,
                    'hold_time_hours': position_age_hours
                }
            )

        # Progressive profit taking for larger gains
        for i, (threshold, percentage) in enumerate(zip(self.take_profit_levels,
                                                       self.take_profit_percentages)):
            if pnl_percentage >= threshold:
                # Dynamic urgency based on profit size and time
                if pnl_percentage >= 0.01:  # 1%+
                    urgency = SellUrgency.HIGH
                    confidence = 0.95
                elif pnl_percentage >= 0.005:  # 0.5%+
                    urgency = SellUrgency.MEDIUM
                    confidence = 0.9
                else:
                    urgency = SellUrgency.LOW
                    confidence = 0.8

                # Time-based confidence boost
                if position_age_hours < 0.25:  # Quick profit under 15 minutes
                    confidence = min(confidence + 0.1, 1.0)

                return SellSignal(
                    symbol=symbol,
                    action='sell',
                    reason=SellReason.TAKE_PROFIT,
                    urgency=urgency,
                    confidence=confidence,
                    reasons_detail=[f'Profit target {pnl_percentage:.3%} (L{i+1}) in {position_age_hours:.1f}h'],
                    suggested_percentage=percentage,
                    limit_price=current_price * 0.9995 if pnl_percentage < 0.01 else None,  # Market for larger profits
                    metadata={
                        'pnl_percentage': pnl_percentage,
                        'profit_level': i + 1,
                        'threshold': threshold,
                        'hold_time_hours': position_age_hours,
                        'fast_execution': pnl_percentage >= 0.01
                    }
                )

        return None

    def _check_trailing_stop(self, symbol: str, current_price: float,
                           entry_price: float) -> Optional[SellSignal]:
        """Enhanced trailing stop with profit-based activation"""
        if symbol not in self.position_high_water_marks:
            return None

        high_water_mark = self.position_high_water_marks[symbol]
        profit_from_entry = (current_price - entry_price) / entry_price
        drawdown = (high_water_mark - current_price) / high_water_mark

        # Only activate trailing stop after minimum profit threshold
        if profit_from_entry < self.trailing_stop_activation:
            return None

        # Dynamic trailing distance based on profit level
        dynamic_trailing_distance = self._calculate_dynamic_trailing_distance(profit_from_entry)

        if drawdown >= dynamic_trailing_distance:
            return SellSignal(
                symbol=symbol,
                action='sell',
                reason=SellReason.TRAILING_STOP,
                urgency=SellUrgency.HIGH,
                confidence=0.9,
                reasons_detail=[
                    f'Trailing stop: {drawdown:.3%} drawdown from ${high_water_mark:.6f}',
                    f'Profit secured: {profit_from_entry:.3%}'
                ],
                suggested_percentage=1.0,
                limit_price=None,  # Market order for immediate execution
                metadata={
                    'high_water_mark': high_water_mark,
                    'drawdown': drawdown,
                    'profit_from_entry': profit_from_entry,
                    'trailing_distance_used': dynamic_trailing_distance,
                    'profit_protection': True
                }
            )

        return None

    def _check_technical_indicators(self, position_data: dict[str, Any]) -> Optional[SellSignal]:
        """Check technical indicators for sell signals"""
        indicators = position_data.get('indicators', {})
        symbol = position_data.get('symbol')

        sell_signals = []

        # RSI overbought
        rsi = indicators.get('rsi', 50)
        if rsi > 70:
            sell_signals.append({
                'reason': f'RSI overbought at {rsi:.1f}',
                'strength': min((rsi - 70) / 10, 1.0)
            })

        # MACD bearish crossover
        macd_signal = indicators.get('macd_signal', 'neutral')
        if macd_signal == 'bearish':
            sell_signals.append({
                'reason': 'MACD bearish crossover',
                'strength': 0.7
            })

        # Moving average breakdown
        price = position_data.get('current_price', 0)
        ma_50 = indicators.get('ma_50', price)
        if price < ma_50 * 0.98:  # 2% below MA
            sell_signals.append({
                'reason': 'Price broke below 50-period MA',
                'strength': 0.6
            })

        # Volume decline
        volume_trend = indicators.get('volume_trend', 'neutral')
        if volume_trend == 'declining' and position_data.get('pnl_percentage', 0) > 0:
            sell_signals.append({
                'reason': 'Declining volume on profitable position',
                'strength': 0.5
            })

        if not sell_signals:
            return None

        # Aggregate signals
        avg_strength = sum(s['strength'] for s in sell_signals) / len(sell_signals)
        confidence = min(avg_strength * 0.8, 0.9)

        if confidence >= self.min_sell_confidence:
            reasons = [s['reason'] for s in sell_signals]

            return SellSignal(
                symbol=symbol,
                action='sell',
                reason=SellReason.TECHNICAL_SIGNAL,
                urgency=SellUrgency.MEDIUM,
                confidence=confidence,
                reasons_detail=reasons,
                suggested_percentage=min(confidence, 0.75),  # Partial sell based on confidence
                metadata={'signal_count': len(sell_signals)}
            )

        return None

    def _check_time_exits(self, symbol: str, position_age_hours: float,
                         pnl_percentage: float) -> Optional[SellSignal]:
        """Check time-based exit conditions"""
        # Stale losing position
        if position_age_hours > self.stale_position_hours and pnl_percentage < 0:
            return SellSignal(
                symbol=symbol,
                action='sell',
                reason=SellReason.TIME_EXIT,
                urgency=SellUrgency.MEDIUM,
                confidence=0.7,
                reasons_detail=[f'Stale losing position ({position_age_hours:.0f} hours old)'],
                suggested_percentage=1.0,
                metadata={'position_age_hours': position_age_hours}
            )

        # Maximum hold time (even for profitable positions)
        if position_age_hours > self.max_hold_time_hours * 3:  # 3x max hold time
            return SellSignal(
                symbol=symbol,
                action='sell',
                reason=SellReason.TIME_EXIT,
                urgency=SellUrgency.LOW,
                confidence=0.6,
                reasons_detail=[f'Position held too long ({position_age_hours:.0f} hours)'],
                suggested_percentage=0.5,  # Partial exit
                metadata={'position_age_hours': position_age_hours}
            )

        return None

    def _check_rebalancing_needs(self, position_data: dict[str, Any]) -> Optional[SellSignal]:
        """Check if position needs rebalancing"""
        portfolio_data = position_data.get('portfolio', {})
        symbol = position_data.get('symbol')

        # Check position concentration
        position_weight = position_data.get('position_weight', 0)
        target_weight = portfolio_data.get('target_weights', {}).get(symbol, 0.05)

        if position_weight > target_weight * 1.5:  # 50% over target
            return SellSignal(
                symbol=symbol,
                action='sell',
                reason=SellReason.REBALANCING,
                urgency=SellUrgency.LOW,
                confidence=0.65,
                reasons_detail=[f'Position overweight: {position_weight:.1%} vs {target_weight:.1%} target'],
                suggested_percentage=(position_weight - target_weight) / position_weight,
                metadata={
                    'current_weight': position_weight,
                    'target_weight': target_weight
                }
            )

        return None

    def reset_high_water_mark(self, symbol: str) -> None:
        """Reset high water mark for a symbol (call after position closed)"""
        if symbol in self.position_high_water_marks:
            del self.position_high_water_marks[symbol]

    def _calculate_dynamic_stop_loss(self, position_data: dict[str, Any]) -> float:
        """Calculate dynamic stop loss based on position characteristics"""
        position_value = position_data.get('position_value', 0)
        hold_time_hours = position_data.get('hold_time_hours', 0)

        # Use tighter stops for smaller positions (micro-trades)
        if position_value <= 5.0:  # Small positions
            base_stop = self.micro_stop_loss  # 0.1%
        else:
            base_stop = self.stop_loss_percentage  # 0.8%

        # Tighten stops for longer hold times
        if hold_time_hours > 1.0:
            base_stop *= 0.8  # 20% tighter
        elif hold_time_hours > 0.5:
            base_stop *= 0.9  # 10% tighter

        return base_stop

    def _calculate_dynamic_trailing_distance(self, profit_pct: float) -> float:
        """Calculate dynamic trailing distance based on profit level"""
        if profit_pct >= 0.02:  # 2%+ profit - wider trailing stop
            return self.trailing_stop_distance * 1.5
        elif profit_pct >= 0.01:  # 1%+ profit - normal trailing stop
            return self.trailing_stop_distance
        else:  # Small profits - tighter trailing stop
            return self.trailing_stop_distance * 0.7

    def _batch_update_market_data(self, symbols: list[str]) -> dict[str, float]:
        """Batch update market data for multiple symbols"""
        prices = {}
        try:
            # Try to get prices from WebSocket manager first
            if hasattr(self.bot, 'websocket_manager') and self.bot.websocket_manager:
                for symbol in symbols:
                    try:
                        ticker_data = self.bot.websocket_manager.get_latest_ticker(symbol)
                        if ticker_data and 'last' in ticker_data:
                            prices[symbol] = float(ticker_data['last'])
                        else:
                            # Fallback to exchange client
                            prices[symbol] = self._get_fallback_price(symbol)
                    except Exception:
                        prices[symbol] = self._get_fallback_price(symbol)
            else:
                # Fallback to individual price fetches
                for symbol in symbols:
                    prices[symbol] = self._get_fallback_price(symbol)

        except Exception as e:
            logger.error(f"[SELL_HANDLER] Error in batch price update: {e}")
            # Return zero prices on complete failure
            prices = dict.fromkeys(symbols, 0.0)

        return prices

    def _get_fallback_price(self, symbol: str) -> float:
        """Get fallback price for a symbol when WebSocket data is unavailable"""
        try:
            # Try to get from exchange balance manager or position data
            if hasattr(self.bot, 'balance_manager') and self.bot.balance_manager:
                # Check if we have recent price data in balance manager
                base_asset = symbol.replace('/USDT', '').replace('/USD', '')
                balance_data = self.bot.balance_manager.get_asset_balance(base_asset)
                if balance_data and 'last_price' in balance_data:
                    return float(balance_data['last_price'])

            # Try to get from position data
            if hasattr(self.bot, 'position_tracker') and self.bot.position_tracker:
                position = self.bot.position_tracker.get_position(symbol)
                if position and 'entry_price' in position:
                    # Use entry price as rough estimate (not ideal but better than 0)
                    return float(position['entry_price'])

            # Last resort: return a small positive value to indicate unknown price
            logger.warning(f"[SELL_HANDLER] No price data available for {symbol}, using fallback")
            return 0.01  # Small fallback value

        except Exception as e:
            logger.warning(f"[SELL_HANDLER] Error getting fallback price for {symbol}: {e}")
            return 0.01

    def get_sell_summary(self) -> dict[str, Any]:
        """Get enhanced summary of sell handler state"""
        return {
            'active_high_water_marks': len(self.position_high_water_marks),
            'take_profit_levels': self.take_profit_levels,
            'stop_loss_percentage': self.stop_loss_percentage,
            'micro_stop_loss': self.micro_stop_loss,
            'trailing_stop_active': self.use_trailing_stop,
            'trailing_stop_distance': self.trailing_stop_distance,
            'trailing_stop_activation': self.trailing_stop_activation,
            'dynamic_stops_enabled': self.use_dynamic_stops,
            'min_sell_confidence': self.min_sell_confidence,
            'performance_optimization': {
                'batch_processing': self.batch_price_updates,
                'target_latency_ms': self.target_latency_ms,
                'parallel_validation': self.parallel_validation
            }
        }
