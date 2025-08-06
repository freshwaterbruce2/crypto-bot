"""
Signal Generation Mixin
Provides signal generation capabilities for trading strategies
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types for trading"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


@dataclass
class TradingSignal:
    """Trading signal with metadata"""
    symbol: str
    signal_type: SignalType
    confidence: float
    price: float
    timestamp: float
    reason: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SignalGenerationMixin:
    """Mixin providing signal generation capabilities"""

    def __init__(self):
        """Initialize signal generation mixin"""
        self.signal_history = []
        self.max_signal_history = 1000

        # Signal parameters
        self.min_confidence_threshold = 0.6
        self.signal_cooldown = {}  # Track per-symbol cooldowns
        self.default_cooldown_seconds = 10

        logger.debug("[SIGNAL_MIXIN] Signal generation mixin initialized")

    def generate_momentum_signal(self, symbol: str, price_data: List[float],
                                volume_data: Optional[List[float]] = None) -> Optional[TradingSignal]:
        """Generate momentum-based trading signal"""
        try:
            if len(price_data) < 5:
                return None

            # Calculate price momentum
            recent_prices = price_data[-5:]
            price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]

            # Calculate short-term trend
            short_trend = (recent_prices[-1] - recent_prices[-3]) / recent_prices[-3]

            # Generate signal based on momentum
            confidence = min(abs(price_change) * 100, 1.0)  # Scale to 0-1

            if price_change > 0.002 and short_trend > 0.001:  # 0.2% price move, 0.1% short trend
                signal_type = SignalType.BUY
                reason = f"Positive momentum: {price_change:.4f}, trend: {short_trend:.4f}"
            elif price_change < -0.002 and short_trend < -0.001:
                signal_type = SignalType.SELL
                reason = f"Negative momentum: {price_change:.4f}, trend: {short_trend:.4f}"
            else:
                return None  # No clear signal

            # Check confidence threshold
            if confidence < self.min_confidence_threshold:
                return None

            # Check cooldown
            if not self._check_signal_cooldown(symbol):
                return None

            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=recent_prices[-1],
                timestamp=time.time(),
                reason=reason,
                metadata={
                    'price_change': price_change,
                    'short_trend': short_trend,
                    'data_points': len(price_data)
                }
            )

            self._record_signal(signal)
            return signal

        except Exception as e:
            logger.error(f"[SIGNAL_MIXIN] Error generating momentum signal for {symbol}: {e}")
            return None

    def generate_mean_reversion_signal(self, symbol: str, price_data: List[float],
                                     window: int = 20, std_dev: float = 2.0) -> Optional[TradingSignal]:
        """Generate mean reversion signal using Bollinger Bands logic"""
        try:
            if len(price_data) < window:
                return None

            # Calculate moving average and standard deviation
            recent_data = price_data[-window:]
            mean_price = sum(recent_data) / len(recent_data)
            variance = sum((x - mean_price) ** 2 for x in recent_data) / len(recent_data)
            std_price = variance ** 0.5

            current_price = price_data[-1]

            # Calculate position relative to bands
            upper_band = mean_price + (std_dev * std_price)
            lower_band = mean_price - (std_dev * std_price)

            # Generate signal based on band position
            if current_price <= lower_band:
                signal_type = SignalType.BUY
                confidence = min((lower_band - current_price) / lower_band, 1.0)
                reason = f"Price below lower band: {current_price:.6f} < {lower_band:.6f}"
            elif current_price >= upper_band:
                signal_type = SignalType.SELL
                confidence = min((current_price - upper_band) / upper_band, 1.0)
                reason = f"Price above upper band: {current_price:.6f} > {upper_band:.6f}"
            else:
                return None  # Price within bands

            # Check confidence threshold
            if confidence < self.min_confidence_threshold:
                return None

            # Check cooldown
            if not self._check_signal_cooldown(symbol):
                return None

            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                timestamp=time.time(),
                reason=reason,
                metadata={
                    'mean_price': mean_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'std_dev': std_price,
                    'window': window
                }
            )

            self._record_signal(signal)
            return signal

        except Exception as e:
            logger.error(f"[SIGNAL_MIXIN] Error generating mean reversion signal for {symbol}: {e}")
            return None

    def generate_breakout_signal(self, symbol: str, price_data: List[float],
                               volume_data: Optional[List[float]] = None) -> Optional[TradingSignal]:
        """Generate breakout signal based on price action"""
        try:
            if len(price_data) < 10:
                return None

            # Calculate support and resistance levels
            recent_data = price_data[-10:]
            high_price = max(recent_data)
            low_price = min(recent_data)
            current_price = price_data[-1]

            # Calculate breakout thresholds
            price_range = high_price - low_price
            breakout_threshold = 0.001  # 0.1% breakout

            # Check for breakouts
            if current_price > high_price * (1 + breakout_threshold):
                signal_type = SignalType.STRONG_BUY
                confidence = min((current_price - high_price) / high_price * 100, 1.0)
                reason = f"Upward breakout: {current_price:.6f} > {high_price:.6f}"
            elif current_price < low_price * (1 - breakout_threshold):
                signal_type = SignalType.STRONG_SELL
                confidence = min((low_price - current_price) / low_price * 100, 1.0)
                reason = f"Downward breakout: {current_price:.6f} < {low_price:.6f}"
            else:
                return None  # No breakout

            # Volume confirmation if available
            if volume_data and len(volume_data) >= 5:
                recent_volume = volume_data[-1]
                avg_volume = sum(volume_data[-5:]) / 5
                if recent_volume < avg_volume * 0.8:  # Low volume breakout
                    confidence *= 0.7  # Reduce confidence

            # Check confidence threshold
            if confidence < self.min_confidence_threshold:
                return None

            # Check cooldown
            if not self._check_signal_cooldown(symbol):
                return None

            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                timestamp=time.time(),
                reason=reason,
                metadata={
                    'high_price': high_price,
                    'low_price': low_price,
                    'price_range': price_range,
                    'breakout_threshold': breakout_threshold
                }
            )

            self._record_signal(signal)
            return signal

        except Exception as e:
            logger.error(f"[SIGNAL_MIXIN] Error generating breakout signal for {symbol}: {e}")
            return None

    def generate_micro_scalping_signal(self, symbol: str, tick_data: List[float]) -> Optional[TradingSignal]:
        """Generate micro-scalping signal for very short-term trades"""
        try:
            if len(tick_data) < 3:
                return None

            # Look for very small price movements
            current_price = tick_data[-1]
            prev_price = tick_data[-2]

            price_change = (current_price - prev_price) / prev_price

            # Micro-scalping thresholds (very small)
            if price_change > 0.0005:  # 0.05% upward movement
                signal_type = SignalType.BUY
                confidence = min(abs(price_change) * 200, 1.0)
                reason = f"Micro uptrend: {price_change:.6f}"
            elif price_change < -0.0005:  # 0.05% downward movement
                signal_type = SignalType.SELL
                confidence = min(abs(price_change) * 200, 1.0)
                reason = f"Micro downtrend: {price_change:.6f}"
            else:
                return None

            # Lower confidence threshold for micro-scalping
            if confidence < 0.4:  # Lower threshold for micro signals
                return None

            # Shorter cooldown for micro-scalping
            if not self._check_signal_cooldown(symbol, cooldown_seconds=5):
                return None

            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                timestamp=time.time(),
                reason=reason,
                metadata={
                    'price_change': price_change,
                    'tick_count': len(tick_data),
                    'strategy': 'micro_scalping'
                }
            )

            self._record_signal(signal)
            return signal

        except Exception as e:
            logger.error(f"[SIGNAL_MIXIN] Error generating micro-scalping signal for {symbol}: {e}")
            return None

    def _check_signal_cooldown(self, symbol: str, cooldown_seconds: Optional[int] = None) -> bool:
        """Check if enough time has passed since last signal for symbol"""
        if cooldown_seconds is None:
            cooldown_seconds = self.default_cooldown_seconds

        current_time = time.time()
        last_signal_time = self.signal_cooldown.get(symbol, 0)

        if current_time - last_signal_time >= cooldown_seconds:
            self.signal_cooldown[symbol] = current_time
            return True

        return False

    def _record_signal(self, signal: TradingSignal):
        """Record signal in history"""
        self.signal_history.append(signal)

        # Limit history size
        if len(self.signal_history) > self.max_signal_history:
            self.signal_history = self.signal_history[-self.max_signal_history:]

        logger.debug(f"[SIGNAL_MIXIN] Recorded {signal.signal_type.value} signal for {signal.symbol} (confidence: {signal.confidence:.3f})")

    def get_signal_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[TradingSignal]:
        """Get signal history, optionally filtered by symbol"""
        if symbol:
            filtered_signals = [s for s in self.signal_history if s.symbol == symbol]
        else:
            filtered_signals = self.signal_history

        return filtered_signals[-limit:] if limit else filtered_signals

    def get_signal_stats(self) -> Dict[str, Any]:
        """Get signal generation statistics"""
        if not self.signal_history:
            return {'total_signals': 0}

        signal_types = {}
        symbols = set()

        for signal in self.signal_history:
            signal_types[signal.signal_type.value] = signal_types.get(signal.signal_type.value, 0) + 1
            symbols.add(signal.symbol)

        return {
            'total_signals': len(self.signal_history),
            'unique_symbols': len(symbols),
            'signal_types': signal_types,
            'avg_confidence': sum(s.confidence for s in self.signal_history) / len(self.signal_history)
        }
