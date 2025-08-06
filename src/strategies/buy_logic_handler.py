"""
Buy Logic Handler - Centralized buy decision making

This module consolidates all buy-side logic from various strategies,
providing a unified interface for making buy decisions.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BuySignalStrength(Enum):
    """Buy signal strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class BuySignal:
    """Structured buy signal with metadata"""
    symbol: str
    action: str  # 'buy' or 'hold'
    strength: BuySignalStrength
    confidence: float  # 0.0 to 1.0
    reasons: list[str]
    suggested_amount: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_horizon: Optional[str] = None  # 'scalp', 'short', 'medium', 'long'
    metadata: dict[str, Any] = None


class BuyLogicHandler:
    """
    Centralized handler for all buy-side trading logic.
    Consolidates signals from multiple sources and strategies.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize buy logic handler"""
        self.config = config

        # Signal thresholds
        self.min_confidence = config.get('min_buy_confidence', 0.6)
        self.min_strength = config.get('min_buy_strength', BuySignalStrength.MODERATE)

        # Risk parameters
        self.max_position_size = config.get('max_position_size', 0.1)  # 10% of portfolio
        self.max_concurrent_buys = config.get('max_concurrent_buys', 5)

        # Timing parameters
        self.cooldown_period = config.get('buy_cooldown_minutes', 5)
        self.signal_validity = config.get('signal_validity_seconds', 30)

        # Market conditions
        self.require_volume = config.get('require_volume', True)
        self.min_volume_ratio = config.get('min_volume_ratio', 1.5)  # 1.5x average

        # Technical indicators weights
        self.indicator_weights = {
            'momentum': config.get('momentum_weight', 0.3),
            'mean_reversion': config.get('mean_reversion_weight', 0.25),
            'volume': config.get('volume_weight', 0.2),
            'support_resistance': config.get('support_resistance_weight', 0.15),
            'pattern': config.get('pattern_weight', 0.1)
        }

        # Recent trades tracking
        self.recent_buys = {}  # symbol -> timestamp

        logger.info(f"[BUY_HANDLER] Initialized with min_confidence={self.min_confidence}, "
                   f"max_position_size={self.max_position_size}")

    async def evaluate_buy_opportunity(self, data: dict[str, Any]) -> BuySignal:
        """
        Evaluate whether to buy based on comprehensive analysis

        Args:
            data: Market data including price, volume, indicators

        Returns:
            BuySignal with decision and metadata
        """
        try:
            symbol = data.get('symbol', 'UNKNOWN')
            current_price = data.get('current_price', 0)

            # Check cooldown
            if self._is_in_cooldown(symbol):
                return BuySignal(
                    symbol=symbol,
                    action='hold',
                    strength=BuySignalStrength.WEAK,
                    confidence=0,
                    reasons=['In cooldown period']
                )

            # Collect signals from different analysis methods
            signals = []

            # Technical analysis
            tech_signal = self._analyze_technicals(data)
            if tech_signal:
                signals.append(tech_signal)

            # Volume analysis
            volume_signal = self._analyze_volume(data)
            if volume_signal:
                signals.append(volume_signal)

            # Support/Resistance analysis
            sr_signal = self._analyze_support_resistance(data)
            if sr_signal:
                signals.append(sr_signal)

            # Pattern recognition
            pattern_signal = self._analyze_patterns(data)
            if pattern_signal:
                signals.append(pattern_signal)

            # Market structure
            structure_signal = self._analyze_market_structure(data)
            if structure_signal:
                signals.append(structure_signal)

            # Aggregate signals
            final_signal = self._aggregate_signals(signals, symbol, current_price)

            # Apply risk filters
            final_signal = self._apply_risk_filters(final_signal, data)

            # Record if buying
            if final_signal.action == 'buy':
                self.recent_buys[symbol] = datetime.now()
                logger.info(f"[BUY_HANDLER] Buy signal generated for {symbol}: "
                           f"strength={final_signal.strength.value}, "
                           f"confidence={final_signal.confidence:.2f}")

            return final_signal

        except Exception as e:
            logger.error(f"[BUY_HANDLER] Error evaluating {symbol}: {e}")
            return BuySignal(
                symbol=symbol,
                action='hold',
                strength=BuySignalStrength.WEAK,
                confidence=0,
                reasons=[f'Evaluation error: {str(e)}']
            )

    def _is_in_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in buy cooldown period"""
        if symbol not in self.recent_buys:
            return False

        last_buy = self.recent_buys[symbol]
        cooldown_end = last_buy + timedelta(minutes=self.cooldown_period)

        return datetime.now() < cooldown_end

    def _analyze_technicals(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Analyze technical indicators for buy signals"""
        try:
            indicators = data.get('indicators', {})
            price_data = data.get('price_data', [])

            if not price_data or len(price_data) < 20:
                return None

            current_price = price_data[-1]
            signals = []

            # RSI analysis
            rsi = indicators.get('rsi', 50)
            if rsi < 30:
                signals.append({
                    'type': 'oversold',
                    'strength': 0.8,
                    'reason': f'RSI oversold at {rsi:.1f}'
                })
            elif rsi < 40:
                signals.append({
                    'type': 'approaching_oversold',
                    'strength': 0.5,
                    'reason': f'RSI approaching oversold at {rsi:.1f}'
                })

            # Moving average crossovers
            ma_short = indicators.get('ma_10', 0)
            ma_long = indicators.get('ma_50', 0)

            if ma_short > ma_long and current_price > ma_short:
                signals.append({
                    'type': 'bullish_ma_cross',
                    'strength': 0.7,
                    'reason': 'Price above short MA, bullish crossover'
                })

            # Momentum
            momentum = (current_price - price_data[-10]) / price_data[-10]
            if momentum > 0.02:  # 2% positive momentum
                signals.append({
                    'type': 'positive_momentum',
                    'strength': min(momentum * 10, 1.0),
                    'reason': f'Positive momentum: {momentum:.1%}'
                })

            if not signals:
                return None

            # Aggregate technical signals
            avg_strength = sum(s['strength'] for s in signals) / len(signals)
            reasons = [s['reason'] for s in signals]

            return {
                'confidence': avg_strength * self.indicator_weights['momentum'],
                'reasons': reasons,
                'strength': avg_strength
            }

        except Exception as e:
            logger.error(f"[BUY_HANDLER] Technical analysis error: {e}")
            return None

    def _analyze_volume(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Analyze volume patterns for buy signals"""
        try:
            volume_data = data.get('volume_data', [])
            current_volume = data.get('current_volume', 0)

            if not volume_data or len(volume_data) < 20:
                return None

            avg_volume = sum(volume_data[-20:]) / 20
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

            if volume_ratio < self.min_volume_ratio:
                return None

            # Volume spike with price increase
            price_change = data.get('price_change_24h', 0)
            if volume_ratio > 2.0 and price_change > 0:
                return {
                    'confidence': min(volume_ratio / 3, 1.0) * self.indicator_weights['volume'],
                    'reasons': [f'Volume spike {volume_ratio:.1f}x average with positive price action'],
                    'strength': min(volume_ratio / 2, 1.0)
                }

            return None

        except Exception as e:
            logger.error(f"[BUY_HANDLER] Volume analysis error: {e}")
            return None

    def _analyze_support_resistance(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Analyze support and resistance levels"""
        try:
            price_data = data.get('price_data', [])
            current_price = data.get('current_price', 0)

            if not price_data or len(price_data) < 50:
                return None

            # Find recent lows (support levels)
            recent_lows = []
            for i in range(10, len(price_data) - 10):
                if price_data[i] < price_data[i-1] and price_data[i] < price_data[i+1]:
                    recent_lows.append(price_data[i])

            if not recent_lows:
                return None

            # Check if price is near support
            nearest_support = min(recent_lows, key=lambda x: abs(x - current_price))
            distance_to_support = abs(current_price - nearest_support) / current_price

            if distance_to_support < 0.02:  # Within 2% of support
                return {
                    'confidence': (1 - distance_to_support) * self.indicator_weights['support_resistance'],
                    'reasons': [f'Price near support level at {nearest_support:.2f}'],
                    'strength': 0.7
                }

            return None

        except Exception as e:
            logger.error(f"[BUY_HANDLER] Support/resistance analysis error: {e}")
            return None

    def _analyze_patterns(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Analyze chart patterns for buy signals"""
        try:
            price_data = data.get('price_data', [])

            if not price_data or len(price_data) < 30:
                return None

            # Simple pattern: Double bottom
            if self._detect_double_bottom(price_data):
                return {
                    'confidence': 0.7 * self.indicator_weights['pattern'],
                    'reasons': ['Double bottom pattern detected'],
                    'strength': 0.8
                }

            # Bullish flag pattern
            if self._detect_bullish_flag(price_data):
                return {
                    'confidence': 0.6 * self.indicator_weights['pattern'],
                    'reasons': ['Bullish flag pattern forming'],
                    'strength': 0.7
                }

            return None

        except Exception as e:
            logger.error(f"[BUY_HANDLER] Pattern analysis error: {e}")
            return None

    def _detect_double_bottom(self, prices: list[float]) -> bool:
        """Detect double bottom pattern"""
        if len(prices) < 30:
            return False

        # Simplified double bottom detection
        # Look for two similar lows with a peak between them
        min_price = min(prices[-30:])
        min_indices = [i for i, p in enumerate(prices[-30:]) if abs(p - min_price) / min_price < 0.02]

        if len(min_indices) >= 2:
            # Check if there's a peak between the lows
            first_low = min_indices[0]
            last_low = min_indices[-1]
            if last_low - first_low > 5:  # At least 5 periods apart
                peak = max(prices[-30:][first_low:last_low])
                if peak > min_price * 1.03:  # At least 3% higher
                    return True

        return False

    def _detect_bullish_flag(self, prices: list[float]) -> bool:
        """Detect bullish flag pattern"""
        if len(prices) < 20:
            return False

        # Look for strong upward move followed by consolidation
        initial_move = (prices[-20] - prices[-30]) / prices[-30] if len(prices) > 30 else 0

        if initial_move > 0.05:  # 5% upward move
            # Check for consolidation in last 10 periods
            consolidation_range = max(prices[-10:]) - min(prices[-10:])
            avg_price = sum(prices[-10:]) / 10

            if consolidation_range / avg_price < 0.02:  # Tight 2% range
                return True

        return False

    def _analyze_market_structure(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Analyze overall market structure"""
        try:
            market_data = data.get('market_data', {})

            # Check if market is in uptrend
            market_trend = market_data.get('trend', 'neutral')
            if market_trend == 'bullish':
                return {
                    'confidence': 0.3,  # Lower weight for market structure
                    'reasons': ['Overall market structure is bullish'],
                    'strength': 0.5
                }

            return None

        except Exception as e:
            logger.error(f"[BUY_HANDLER] Market structure analysis error: {e}")
            return None

    def _aggregate_signals(self, signals: list[dict[str, Any]], symbol: str,
                          current_price: float) -> BuySignal:
        """Aggregate multiple signals into final buy decision"""
        if not signals:
            return BuySignal(
                symbol=symbol,
                action='hold',
                strength=BuySignalStrength.WEAK,
                confidence=0,
                reasons=['No buy signals detected']
            )

        # Calculate weighted confidence
        total_confidence = sum(s.get('confidence', 0) for s in signals)
        avg_strength = sum(s.get('strength', 0) for s in signals) / len(signals)

        # Determine signal strength
        if avg_strength >= 0.8:
            strength = BuySignalStrength.VERY_STRONG
        elif avg_strength >= 0.6:
            strength = BuySignalStrength.STRONG
        elif avg_strength >= 0.4:
            strength = BuySignalStrength.MODERATE
        else:
            strength = BuySignalStrength.WEAK

        # Collect all reasons
        all_reasons = []
        for signal in signals:
            all_reasons.extend(signal.get('reasons', []))

        # Determine action
        action = 'buy' if total_confidence >= self.min_confidence else 'hold'

        # Calculate position sizing
        suggested_amount = None
        if action == 'buy':
            # Scale position size with confidence
            base_size = 0.02  # 2% base position
            suggested_amount = base_size * (1 + (total_confidence - self.min_confidence))
            suggested_amount = min(suggested_amount, self.max_position_size)

        # Calculate stop loss and take profit
        stop_loss = current_price * 0.98 if action == 'buy' else None  # 2% stop loss
        take_profit = current_price * 1.03 if action == 'buy' else None  # 3% take profit

        return BuySignal(
            symbol=symbol,
            action=action,
            strength=strength,
            confidence=total_confidence,
            reasons=all_reasons,
            suggested_amount=suggested_amount,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_horizon='short' if strength == BuySignalStrength.VERY_STRONG else 'medium',
            metadata={
                'signal_count': len(signals),
                'avg_strength': avg_strength
            }
        )

    def _apply_risk_filters(self, signal: BuySignal, data: dict[str, Any]) -> BuySignal:
        """Apply final risk management filters to buy signal"""
        if signal.action != 'buy':
            return signal

        # Check concurrent positions
        open_positions = data.get('open_positions', 0)
        if open_positions >= self.max_concurrent_buys:
            signal.action = 'hold'
            signal.reasons.append(f'Max concurrent positions ({self.max_concurrent_buys}) reached')

        # Check portfolio allocation
        portfolio_value = data.get('portfolio_value', 0)
        if portfolio_value > 0 and signal.suggested_amount:
            position_value = signal.suggested_amount * portfolio_value
            min_position_value = data.get('min_position_value', 10)

            if position_value < min_position_value:
                signal.action = 'hold'
                signal.reasons.append(f'Position size too small (${position_value:.2f})')

        # Volatility check
        volatility = data.get('volatility', 0)
        if volatility > 0.1:  # 10% volatility
            signal.suggested_amount = signal.suggested_amount * 0.5 if signal.suggested_amount else None
            signal.reasons.append('Position size reduced due to high volatility')

        return signal

    def get_active_cooldowns(self) -> dict[str, datetime]:
        """Get symbols currently in cooldown"""
        now = datetime.now()
        active = {}

        for symbol, last_buy in self.recent_buys.items():
            cooldown_end = last_buy + timedelta(minutes=self.cooldown_period)
            if now < cooldown_end:
                active[symbol] = cooldown_end

        return active
