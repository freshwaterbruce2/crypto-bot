"""
Market regime detection component for identifying market conditions.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime types."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


@dataclass
class RegimeMetrics:
    """Metrics for market regime analysis."""
    trend_strength: float
    volatility: float
    momentum: float
    volume_ratio: float
    confidence: float
    regime: MarketRegime
    timestamp: datetime


class RegimeDetector:
    """
    Market regime detector using multiple indicators to identify market conditions.
    """

    def __init__(self,
                 lookback_period: int = 50,
                 volatility_threshold: float = 0.02,
                 trend_threshold: float = 0.01,
                 confidence_threshold: float = 0.7):
        """
        Initialize the regime detector.

        Args:
            lookback_period: Number of periods to look back for analysis
            volatility_threshold: Threshold for high/low volatility classification
            trend_threshold: Threshold for trend strength classification
            confidence_threshold: Minimum confidence for regime classification
        """
        self.lookback_period = lookback_period
        self.volatility_threshold = volatility_threshold
        self.trend_threshold = trend_threshold
        self.confidence_threshold = confidence_threshold

        # Historical data storage
        self.price_history: list[float] = []
        self.volume_history: list[float] = []
        self.regime_history: list[RegimeMetrics] = []

        # Current regime state
        self.current_regime: Optional[MarketRegime] = None
        self.current_metrics: Optional[RegimeMetrics] = None

        logger.info(f"RegimeDetector initialized with lookback_period={lookback_period}")

    def update_data(self, price: float, volume: float = 0.0) -> None:
        """
        Update the detector with new price and volume data.

        Args:
            price: Current price
            volume: Current volume
        """
        self.price_history.append(price)
        self.volume_history.append(volume)

        # Keep only the required lookback period
        if len(self.price_history) > self.lookback_period * 2:
            self.price_history = self.price_history[-self.lookback_period * 2:]
            self.volume_history = self.volume_history[-self.lookback_period * 2:]

        # Update regime if we have enough data
        if len(self.price_history) >= self.lookback_period:
            self._update_regime()

    def _update_regime(self) -> None:
        """Update the current market regime based on latest data."""
        try:
            metrics = self._calculate_metrics()

            # Determine regime based on metrics
            regime = self._classify_regime(metrics)

            # Update current state
            self.current_regime = regime.regime
            self.current_metrics = regime

            # Store in history
            self.regime_history.append(regime)

            # Keep history manageable
            if len(self.regime_history) > 1000:
                self.regime_history = self.regime_history[-1000:]

            logger.debug(f"Regime updated: {regime.regime.value} (confidence: {regime.confidence:.2f})")

        except Exception as e:
            logger.error(f"Error updating regime: {e}")
            self.current_regime = MarketRegime.UNKNOWN

    def _calculate_metrics(self) -> RegimeMetrics:
        """Calculate regime metrics from price and volume data."""
        prices = np.array(self.price_history[-self.lookback_period:])
        volumes = np.array(self.volume_history[-self.lookback_period:])

        # Calculate returns
        returns = np.diff(prices) / prices[:-1]

        # Trend strength (using linear regression slope)
        x = np.arange(len(prices))
        trend_slope = np.polyfit(x, prices, 1)[0]
        trend_strength = abs(trend_slope) / np.mean(prices)

        # Volatility (standard deviation of returns)
        volatility = np.std(returns) if len(returns) > 1 else 0.0

        # Momentum (rate of change)
        momentum = (prices[-1] - prices[0]) / prices[0] if len(prices) > 1 else 0.0

        # Volume ratio (recent vs average)
        recent_volume = np.mean(volumes[-10:]) if len(volumes) >= 10 else 0.0
        avg_volume = np.mean(volumes) if len(volumes) > 0 else 1.0
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0

        # Calculate confidence based on consistency of indicators
        confidence = self._calculate_confidence(trend_strength, volatility, momentum)

        return RegimeMetrics(
            trend_strength=trend_strength,
            volatility=volatility,
            momentum=momentum,
            volume_ratio=volume_ratio,
            confidence=confidence,
            regime=MarketRegime.UNKNOWN,  # Will be set by _classify_regime
            timestamp=datetime.now()
        )

    def _classify_regime(self, metrics: RegimeMetrics) -> RegimeMetrics:
        """Classify the market regime based on calculated metrics."""
        # Determine primary regime
        if metrics.volatility > self.volatility_threshold:
            if abs(metrics.momentum) > self.trend_threshold:
                if metrics.momentum > 0:
                    regime = MarketRegime.TRENDING_UP
                else:
                    regime = MarketRegime.TRENDING_DOWN
            else:
                regime = MarketRegime.HIGH_VOLATILITY
        else:
            if abs(metrics.momentum) > self.trend_threshold:
                if metrics.momentum > 0:
                    regime = MarketRegime.TRENDING_UP
                else:
                    regime = MarketRegime.TRENDING_DOWN
            else:
                if metrics.volatility < self.volatility_threshold / 2:
                    regime = MarketRegime.LOW_VOLATILITY
                else:
                    regime = MarketRegime.SIDEWAYS

        # Update regime in metrics
        metrics.regime = regime

        return metrics

    def _calculate_confidence(self, trend_strength: float, volatility: float, momentum: float) -> float:
        """Calculate confidence score for regime classification."""
        # Combine multiple factors for confidence
        trend_confidence = min(abs(trend_strength) / self.trend_threshold, 1.0)
        volatility_confidence = min(abs(volatility - self.volatility_threshold) / self.volatility_threshold, 1.0)
        momentum_confidence = min(abs(momentum) / self.trend_threshold, 1.0)

        # Weighted average
        confidence = (trend_confidence * 0.4 + volatility_confidence * 0.3 + momentum_confidence * 0.3)

        return min(confidence, 1.0)

    def get_current_regime(self) -> tuple[MarketRegime, float]:
        """
        Get the current market regime and confidence.

        Returns:
            Tuple of (regime, confidence)
        """
        if self.current_metrics is None:
            return MarketRegime.UNKNOWN, 0.0

        return self.current_metrics.regime, self.current_metrics.confidence

    def get_regime_metrics(self) -> Optional[RegimeMetrics]:
        """Get the current regime metrics."""
        return self.current_metrics

    def is_regime_stable(self, periods: int = 5) -> bool:
        """
        Check if the current regime has been stable for the specified periods.

        Args:
            periods: Number of periods to check for stability

        Returns:
            True if regime has been stable
        """
        if len(self.regime_history) < periods:
            return False

        recent_regimes = [r.regime for r in self.regime_history[-periods:]]
        return len(set(recent_regimes)) == 1

    def get_regime_transition_probability(self) -> dict[MarketRegime, float]:
        """
        Calculate transition probabilities to different regimes.

        Returns:
            Dictionary mapping regimes to transition probabilities
        """
        if len(self.regime_history) < 10:
            return dict.fromkeys(MarketRegime, 0.2)

        # Count transitions
        transitions = {}
        current_regime = self.current_regime

        for i in range(1, len(self.regime_history)):
            prev_regime = self.regime_history[i-1].regime
            curr_regime = self.regime_history[i].regime

            if prev_regime == current_regime:
                if curr_regime not in transitions:
                    transitions[curr_regime] = 0
                transitions[curr_regime] += 1

        # Calculate probabilities
        total_transitions = sum(transitions.values())
        if total_transitions == 0:
            return dict.fromkeys(MarketRegime, 0.2)

        probabilities = {}
        for regime in MarketRegime:
            probabilities[regime] = transitions.get(regime, 0) / total_transitions

        return probabilities

    def get_regime_statistics(self) -> dict[str, any]:
        """Get comprehensive regime statistics."""
        if not self.regime_history:
            return {}

        # Count regime occurrences
        regime_counts = {}
        for metrics in self.regime_history:
            regime = metrics.regime
            if regime not in regime_counts:
                regime_counts[regime] = 0
            regime_counts[regime] += 1

        # Calculate average metrics by regime
        regime_avg_metrics = {}
        for regime in MarketRegime:
            regime_metrics = [m for m in self.regime_history if m.regime == regime]
            if regime_metrics:
                regime_avg_metrics[regime] = {
                    'avg_volatility': np.mean([m.volatility for m in regime_metrics]),
                    'avg_momentum': np.mean([m.momentum for m in regime_metrics]),
                    'avg_confidence': np.mean([m.confidence for m in regime_metrics]),
                    'count': len(regime_metrics)
                }

        return {
            'current_regime': self.current_regime.value if self.current_regime else 'unknown',
            'current_confidence': self.current_metrics.confidence if self.current_metrics else 0.0,
            'regime_counts': {r.value: c for r, c in regime_counts.items()},
            'regime_statistics': {r.value: stats for r, stats in regime_avg_metrics.items()},
            'total_observations': len(self.regime_history)
        }

    def reset(self) -> None:
        """Reset the detector state."""
        self.price_history.clear()
        self.volume_history.clear()
        self.regime_history.clear()
        self.current_regime = None
        self.current_metrics = None

        logger.info("RegimeDetector reset")
