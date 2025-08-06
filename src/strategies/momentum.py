"""
Momentum scalping strategy implementation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MomentumSignal(Enum):
    """Momentum trading signals."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class MomentumDirection(Enum):
    """Momentum direction."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class MomentumIndicators:
    """Momentum indicators calculation results."""
    rsi: float
    rsi_signal: str
    price_momentum: float
    volume_momentum: float
    moving_average_trend: str
    bollinger_position: float
    macd_histogram: float
    stochastic_k: float
    stochastic_d: float
    williams_r: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ScalpingSignal:
    """Scalping signal information."""
    signal: MomentumSignal
    strength: float  # 0-1 confidence score
    direction: MomentumDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    timeframe: str
    indicators: MomentumIndicators
    metadata: Dict[str, Any] = field(default_factory=dict)


class MomentumScalping:
    """
    Momentum scalping strategy that identifies short-term momentum shifts
    and generates scalping signals for quick profits.
    """

    def __init__(self,
                 timeframe: str = "1m",
                 rsi_period: int = 14,
                 rsi_oversold: float = 30.0,
                 rsi_overbought: float = 70.0,
                 bb_period: int = 20,
                 bb_std: float = 2.0,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 volume_threshold: float = 1.5,
                 momentum_threshold: float = 0.002,
                 stop_loss_pct: float = 0.005,
                 take_profit_pct: float = 0.01,
                 min_risk_reward: float = 1.5):
        """
        Initialize the momentum scalping strategy.
        
        Args:
            timeframe: Trading timeframe
            rsi_period: RSI calculation period
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands standard deviation
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            volume_threshold: Volume spike threshold
            momentum_threshold: Minimum momentum for signals
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            min_risk_reward: Minimum risk-reward ratio
        """
        self.timeframe = timeframe
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.volume_threshold = volume_threshold
        self.momentum_threshold = momentum_threshold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.min_risk_reward = min_risk_reward

        # Data storage
        self.price_data: List[float] = []
        self.volume_data: List[float] = []
        self.high_data: List[float] = []
        self.low_data: List[float] = []
        self.timestamp_data: List[datetime] = []

        # Indicator history
        self.rsi_history: List[float] = []
        self.macd_history: List[float] = []
        self.signal_history: List[ScalpingSignal] = []

        # Strategy state
        self.current_signal: Optional[ScalpingSignal] = None
        self.last_signal_time: Optional[datetime] = None
        self.signal_cooldown = timedelta(minutes=1)  # Prevent signal spam

        # Performance tracking
        self.signals_generated = 0
        self.successful_signals = 0
        self.total_pnl = 0.0

        logger.info(f"MomentumScalping strategy initialized for {timeframe} timeframe")

    def update_data(self, price: float, volume: float, high: float, low: float,
                   timestamp: Optional[datetime] = None) -> None:
        """
        Update strategy with new market data.
        
        Args:
            price: Current price (close price)
            volume: Current volume
            high: Period high price
            low: Period low price
            timestamp: Data timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Add new data
        self.price_data.append(price)
        self.volume_data.append(volume)
        self.high_data.append(high)
        self.low_data.append(low)
        self.timestamp_data.append(timestamp)

        # Keep reasonable history size
        max_history = 500
        if len(self.price_data) > max_history:
            self.price_data = self.price_data[-max_history:]
            self.volume_data = self.volume_data[-max_history:]
            self.high_data = self.high_data[-max_history:]
            self.low_data = self.low_data[-max_history:]
            self.timestamp_data = self.timestamp_data[-max_history:]

        logger.debug(f"Updated data: price={price}, volume={volume}")

    def calculate_indicators(self) -> Optional[MomentumIndicators]:
        """
        Calculate momentum indicators.
        
        Returns:
            MomentumIndicators object or None if insufficient data
        """
        if len(self.price_data) < max(self.rsi_period, self.bb_period, self.macd_slow):
            return None

        try:
            # Convert to numpy arrays
            prices = np.array(self.price_data)
            volumes = np.array(self.volume_data)
            highs = np.array(self.high_data)
            lows = np.array(self.low_data)

            # Calculate RSI
            rsi = self._calculate_rsi(prices)
            rsi_signal = self._interpret_rsi(rsi)

            # Calculate price momentum
            price_momentum = self._calculate_price_momentum(prices)

            # Calculate volume momentum
            volume_momentum = self._calculate_volume_momentum(volumes)

            # Calculate moving average trend
            ma_trend = self._calculate_ma_trend(prices)

            # Calculate Bollinger Bands position
            bb_position = self._calculate_bollinger_position(prices)

            # Calculate MACD
            macd_histogram = self._calculate_macd(prices)

            # Calculate Stochastic
            stoch_k, stoch_d = self._calculate_stochastic(prices, highs, lows)

            # Calculate Williams %R
            williams_r = self._calculate_williams_r(prices, highs, lows)

            indicators = MomentumIndicators(
                rsi=rsi,
                rsi_signal=rsi_signal,
                price_momentum=price_momentum,
                volume_momentum=volume_momentum,
                moving_average_trend=ma_trend,
                bollinger_position=bb_position,
                macd_histogram=macd_histogram,
                stochastic_k=stoch_k,
                stochastic_d=stoch_d,
                williams_r=williams_r
            )

            return indicators

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return None

    def _calculate_rsi(self, prices: np.ndarray) -> float:
        """Calculate RSI indicator."""
        if len(prices) < self.rsi_period + 1:
            return 50.0  # Neutral RSI

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Calculate average gains and losses
        avg_gain = np.mean(gains[-self.rsi_period:])
        avg_loss = np.mean(losses[-self.rsi_period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _interpret_rsi(self, rsi: float) -> str:
        """Interpret RSI value."""
        if rsi <= self.rsi_oversold:
            return "oversold"
        elif rsi >= self.rsi_overbought:
            return "overbought"
        else:
            return "neutral"

    def _calculate_price_momentum(self, prices: np.ndarray) -> float:
        """Calculate price momentum."""
        if len(prices) < 10:
            return 0.0

        # Calculate rate of change over last 10 periods
        current_price = prices[-1]
        past_price = prices[-10]

        momentum = (current_price - past_price) / past_price
        return momentum

    def _calculate_volume_momentum(self, volumes: np.ndarray) -> float:
        """Calculate volume momentum."""
        if len(volumes) < 20:
            return 1.0

        # Compare recent volume to average volume
        recent_volume = np.mean(volumes[-5:])
        avg_volume = np.mean(volumes[-20:])

        if avg_volume == 0:
            return 1.0

        volume_momentum = recent_volume / avg_volume
        return volume_momentum

    def _calculate_ma_trend(self, prices: np.ndarray) -> str:
        """Calculate moving average trend."""
        if len(prices) < 20:
            return "neutral"

        # Calculate short and long moving averages
        short_ma = np.mean(prices[-10:])
        long_ma = np.mean(prices[-20:])

        if short_ma > long_ma * 1.001:  # 0.1% threshold
            return "bullish"
        elif short_ma < long_ma * 0.999:
            return "bearish"
        else:
            return "neutral"

    def _calculate_bollinger_position(self, prices: np.ndarray) -> float:
        """Calculate position relative to Bollinger Bands."""
        if len(prices) < self.bb_period:
            return 0.5  # Neutral position

        # Calculate Bollinger Bands
        sma = np.mean(prices[-self.bb_period:])
        std = np.std(prices[-self.bb_period:])

        upper_band = sma + (self.bb_std * std)
        lower_band = sma - (self.bb_std * std)

        current_price = prices[-1]

        # Calculate position (0 = lower band, 1 = upper band)
        if upper_band == lower_band:
            return 0.5

        position = (current_price - lower_band) / (upper_band - lower_band)
        return max(0.0, min(1.0, position))

    def _calculate_macd(self, prices: np.ndarray) -> float:
        """Calculate MACD histogram."""
        if len(prices) < self.macd_slow + self.macd_signal:
            return 0.0

        # Calculate EMAs
        ema_fast = self._calculate_ema(prices, self.macd_fast)
        ema_slow = self._calculate_ema(prices, self.macd_slow)

        # Calculate MACD line
        macd_line = ema_fast - ema_slow

        # Calculate signal line (EMA of MACD line)
        macd_values = [macd_line]  # Simplified for this example
        signal_line = macd_line  # Would be EMA of MACD line in full implementation

        # Calculate histogram
        histogram = macd_line - signal_line

        return histogram

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return np.mean(prices)

        # Simplified EMA calculation
        alpha = 2.0 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema

        return ema

    def _calculate_stochastic(self, prices: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> Tuple[float, float]:
        """Calculate Stochastic oscillator."""
        if len(prices) < 14:
            return 50.0, 50.0

        # Calculate %K
        period = 14
        lowest_low = np.min(lows[-period:])
        highest_high = np.max(highs[-period:])
        current_close = prices[-1]

        if highest_high == lowest_low:
            k_percent = 50.0
        else:
            k_percent = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100

        # Calculate %D (3-period SMA of %K)
        # Simplified - in full implementation would use actual %K history
        d_percent = k_percent

        return k_percent, d_percent

    def _calculate_williams_r(self, prices: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> float:
        """Calculate Williams %R."""
        if len(prices) < 14:
            return -50.0

        period = 14
        lowest_low = np.min(lows[-period:])
        highest_high = np.max(highs[-period:])
        current_close = prices[-1]

        if highest_high == lowest_low:
            return -50.0

        williams_r = ((highest_high - current_close) / (highest_high - lowest_low)) * -100

        return williams_r

    def generate_signal(self) -> Optional[ScalpingSignal]:
        """
        Generate scalping signal based on momentum indicators.
        
        Returns:
            ScalpingSignal or None if no signal
        """
        # Check signal cooldown
        if (self.last_signal_time and
            datetime.now() - self.last_signal_time < self.signal_cooldown):
            return None

        # Calculate indicators
        indicators = self.calculate_indicators()

        if not indicators:
            return None

        try:
            # Analyze signal strength and direction
            signal_strength = self._calculate_signal_strength(indicators)
            signal_direction = self._determine_signal_direction(indicators)

            # Generate signal if strong enough
            if signal_strength >= 0.6:  # 60% confidence threshold
                current_price = self.price_data[-1]

                # Determine signal type
                if signal_direction == MomentumDirection.BULLISH:
                    if signal_strength >= 0.8:
                        signal_type = MomentumSignal.STRONG_BUY
                    else:
                        signal_type = MomentumSignal.BUY
                elif signal_direction == MomentumDirection.BEARISH:
                    if signal_strength >= 0.8:
                        signal_type = MomentumSignal.STRONG_SELL
                    else:
                        signal_type = MomentumSignal.SELL
                else:
                    signal_type = MomentumSignal.HOLD

                # Calculate entry, stop loss, and take profit
                entry_price = current_price

                if signal_direction == MomentumDirection.BULLISH:
                    stop_loss = entry_price * (1 - self.stop_loss_pct)
                    take_profit = entry_price * (1 + self.take_profit_pct)
                else:
                    stop_loss = entry_price * (1 + self.stop_loss_pct)
                    take_profit = entry_price * (1 - self.take_profit_pct)

                # Calculate risk-reward ratio
                risk = abs(entry_price - stop_loss)
                reward = abs(take_profit - entry_price)
                risk_reward_ratio = reward / risk if risk > 0 else 0

                # Only generate signal if risk-reward is acceptable
                if risk_reward_ratio >= self.min_risk_reward:
                    signal = ScalpingSignal(
                        signal=signal_type,
                        strength=signal_strength,
                        direction=signal_direction,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        risk_reward_ratio=risk_reward_ratio,
                        timeframe=self.timeframe,
                        indicators=indicators,
                        metadata={
                            'timestamp': datetime.now(),
                            'strategy': 'momentum_scalping',
                            'version': '1.0'
                        }
                    )

                    # Update state
                    self.current_signal = signal
                    self.last_signal_time = datetime.now()
                    self.signals_generated += 1

                    # Store in history
                    self.signal_history.append(signal)
                    if len(self.signal_history) > 1000:
                        self.signal_history = self.signal_history[-1000:]

                    logger.info(f"Generated signal: {signal_type.value} at {entry_price:.2f} "
                              f"(strength: {signal_strength:.2f}, RR: {risk_reward_ratio:.2f})")

                    return signal

            return None

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None

    def _calculate_signal_strength(self, indicators: MomentumIndicators) -> float:
        """Calculate overall signal strength."""
        strength_factors = []

        # RSI strength
        if indicators.rsi_signal == "oversold":
            strength_factors.append(0.8)
        elif indicators.rsi_signal == "overbought":
            strength_factors.append(0.8)
        else:
            strength_factors.append(0.3)

        # Momentum strength
        momentum_strength = min(abs(indicators.price_momentum) / self.momentum_threshold, 1.0)
        strength_factors.append(momentum_strength)

        # Volume strength
        volume_strength = min(indicators.volume_momentum / self.volume_threshold, 1.0)
        strength_factors.append(volume_strength)

        # MACD strength
        macd_strength = min(abs(indicators.macd_histogram) * 100, 1.0)
        strength_factors.append(macd_strength)

        # Bollinger Bands strength
        bb_strength = abs(indicators.bollinger_position - 0.5) * 2  # Distance from center
        strength_factors.append(bb_strength)

        # Calculate weighted average
        weights = [0.25, 0.25, 0.2, 0.15, 0.15]
        total_strength = sum(f * w for f, w in zip(strength_factors, weights))

        return min(total_strength, 1.0)

    def _determine_signal_direction(self, indicators: MomentumIndicators) -> MomentumDirection:
        """Determine signal direction based on indicators."""
        bullish_signals = 0
        bearish_signals = 0

        # RSI signals
        if indicators.rsi_signal == "oversold":
            bullish_signals += 1
        elif indicators.rsi_signal == "overbought":
            bearish_signals += 1

        # Price momentum
        if indicators.price_momentum > self.momentum_threshold:
            bullish_signals += 1
        elif indicators.price_momentum < -self.momentum_threshold:
            bearish_signals += 1

        # Moving average trend
        if indicators.moving_average_trend == "bullish":
            bullish_signals += 1
        elif indicators.moving_average_trend == "bearish":
            bearish_signals += 1

        # MACD
        if indicators.macd_histogram > 0:
            bullish_signals += 1
        elif indicators.macd_histogram < 0:
            bearish_signals += 1

        # Stochastic
        if indicators.stochastic_k < 20:
            bullish_signals += 1
        elif indicators.stochastic_k > 80:
            bearish_signals += 1

        # Determine overall direction
        if bullish_signals > bearish_signals:
            return MomentumDirection.BULLISH
        elif bearish_signals > bullish_signals:
            return MomentumDirection.BEARISH
        else:
            return MomentumDirection.NEUTRAL

    def update_signal_result(self, signal_id: str, success: bool, pnl: float) -> None:
        """
        Update signal result for performance tracking.
        
        Args:
            signal_id: Signal identifier
            success: Whether signal was successful
            pnl: Profit/loss from the signal
        """
        if success:
            self.successful_signals += 1

        self.total_pnl += pnl

        logger.info(f"Signal result updated: success={success}, pnl={pnl:.4f}")

    def get_current_signal(self) -> Optional[ScalpingSignal]:
        """Get current active signal."""
        return self.current_signal

    def get_signal_history(self, limit: int = 100) -> List[ScalpingSignal]:
        """Get signal history."""
        return self.signal_history[-limit:]

    def get_strategy_statistics(self) -> Dict[str, Any]:
        """Get strategy performance statistics."""
        win_rate = self.successful_signals / max(self.signals_generated, 1)

        return {
            'signals_generated': self.signals_generated,
            'successful_signals': self.successful_signals,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'average_pnl': self.total_pnl / max(self.signals_generated, 1),
            'timeframe': self.timeframe,
            'current_signal': self.current_signal.signal.value if self.current_signal else None,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'data_points': len(self.price_data)
        }

    def reset_strategy(self) -> None:
        """Reset strategy state."""
        self.price_data.clear()
        self.volume_data.clear()
        self.high_data.clear()
        self.low_data.clear()
        self.timestamp_data.clear()
        self.rsi_history.clear()
        self.macd_history.clear()
        self.signal_history.clear()

        self.current_signal = None
        self.last_signal_time = None
        self.signals_generated = 0
        self.successful_signals = 0
        self.total_pnl = 0.0

        logger.info("Strategy reset")

    def optimize_parameters(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Optimize strategy parameters based on historical data.
        
        Args:
            historical_data: List of historical price/volume data
            
        Returns:
            Dictionary with optimized parameters
        """
        # This would implement parameter optimization logic
        # For now, return current parameters

        return {
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'momentum_threshold': self.momentum_threshold,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'volume_threshold': self.volume_threshold
        }
