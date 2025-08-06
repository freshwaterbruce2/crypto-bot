"""
Volatility Calculator
Real-time volatility calculation and analysis for trading optimization
"""

import logging
import math
import statistics
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VolatilityPeriod(Enum):
    """Volatility calculation periods"""
    SHORT = "short"      # 5-minute volatility
    MEDIUM = "medium"    # 15-minute volatility
    LONG = "long"        # 1-hour volatility
    INTRADAY = "intraday"  # Daily volatility


@dataclass
class VolatilityReading:
    """Volatility reading with metadata"""
    symbol: str
    volatility: float
    period: VolatilityPeriod
    timestamp: float
    data_points: int
    price_range: float
    mean_price: float
    confidence: float = 1.0

    def age_seconds(self) -> float:
        """Get reading age in seconds"""
        return time.time() - self.timestamp


class VolatilityCalculator:
    """Advanced volatility calculator for trading optimization"""

    def __init__(self, config: dict[str, Any] = None):
        """Initialize volatility calculator"""
        self.config = config or {}

        # Price history storage
        self.price_history = {}
        self.max_history_size = 1000

        # Volatility cache
        self.volatility_cache = {}
        self.cache_ttl = 30  # 30 seconds cache TTL

        # Calculation parameters
        self.min_data_points = {
            VolatilityPeriod.SHORT: 5,
            VolatilityPeriod.MEDIUM: 15,
            VolatilityPeriod.LONG: 60,
            VolatilityPeriod.INTRADAY: 100
        }

        # Volatility thresholds
        self.volatility_thresholds = {
            'low': 1.0,
            'medium': 3.0,
            'high': 5.0,
            'extreme': 10.0
        }

        logger.info("[VOLATILITY] Volatility calculator initialized")

    async def calculate_volatility(self, symbol: str, prices: list[float],
                                 period: VolatilityPeriod = VolatilityPeriod.SHORT) -> Optional[VolatilityReading]:
        """Calculate volatility for given price data"""
        try:
            if not prices or len(prices) < 2:
                return None

            # Check minimum data points
            min_points = self.min_data_points.get(period, 5)
            if len(prices) < min_points:
                logger.debug(f"[VOLATILITY] Insufficient data for {symbol}: {len(prices)} < {min_points}")
                return None

            # Calculate price returns
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    return_pct = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(return_pct)

            if not returns:
                return None

            # Calculate volatility metrics
            volatility = self._calculate_standard_deviation(returns) * 100  # Convert to percentage
            mean_price = statistics.mean(prices)
            price_range = (max(prices) - min(prices)) / mean_price * 100

            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(len(prices), min_points)

            reading = VolatilityReading(
                symbol=symbol,
                volatility=volatility,
                period=period,
                timestamp=time.time(),
                data_points=len(prices),
                price_range=price_range,
                mean_price=mean_price,
                confidence=confidence
            )

            # Cache the reading
            cache_key = f"{symbol}_{period.value}"
            self.volatility_cache[cache_key] = reading

            logger.debug(f"[VOLATILITY] Calculated for {symbol}: {volatility:.3f}% ({period.value})")
            return reading

        except Exception as e:
            logger.error(f"[VOLATILITY] Error calculating volatility for {symbol}: {e}")
            return None

    async def get_real_time_volatility(self, symbol: str, exchange=None) -> Optional[VolatilityReading]:
        """Get real-time volatility using live price data"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{VolatilityPeriod.SHORT.value}"
            if cache_key in self.volatility_cache:
                cached = self.volatility_cache[cache_key]
                if cached.age_seconds() < self.cache_ttl:
                    return cached

            # Get recent price history
            prices = self._get_recent_prices(symbol, exchange)
            if not prices:
                return None

            return await self.calculate_volatility(symbol, prices, VolatilityPeriod.SHORT)

        except Exception as e:
            logger.error(f"[VOLATILITY] Error getting real-time volatility for {symbol}: {e}")
            return None

    def update_price_history(self, symbol: str, price: float):
        """Update price history for symbol"""
        try:
            if symbol not in self.price_history:
                self.price_history[symbol] = []

            self.price_history[symbol].append({
                'price': price,
                'timestamp': time.time()
            })

            # Limit history size
            if len(self.price_history[symbol]) > self.max_history_size:
                self.price_history[symbol] = self.price_history[symbol][-self.max_history_size:]

        except Exception as e:
            logger.error(f"[VOLATILITY] Error updating price history for {symbol}: {e}")

    def get_volatility_classification(self, volatility: float) -> str:
        """Classify volatility level"""
        try:
            if volatility >= self.volatility_thresholds['extreme']:
                return 'extreme'
            elif volatility >= self.volatility_thresholds['high']:
                return 'high'
            elif volatility >= self.volatility_thresholds['medium']:
                return 'medium'
            elif volatility >= self.volatility_thresholds['low']:
                return 'low'
            else:
                return 'very_low'

        except Exception:
            return 'unknown'

    def get_position_size_adjustment(self, volatility: float) -> float:
        """Get position size adjustment based on volatility"""
        try:
            classification = self.get_volatility_classification(volatility)

            adjustments = {
                'very_low': 1.2,   # Increase position size for low volatility
                'low': 1.1,
                'medium': 1.0,     # Normal position size
                'high': 0.8,       # Reduce position size for high volatility
                'extreme': 0.5     # Significantly reduce for extreme volatility
            }

            return adjustments.get(classification, 1.0)

        except Exception:
            return 1.0

    def calculate_dynamic_stop_loss(self, volatility: float, base_stop_loss: float = 0.008) -> float:
        """Calculate dynamic stop loss based on volatility"""
        try:
            # Adjust stop loss based on volatility
            if volatility > 5.0:  # High volatility
                multiplier = 1.5
            elif volatility > 3.0:  # Medium volatility
                multiplier = 1.2
            elif volatility < 1.0:  # Low volatility
                multiplier = 0.8
            else:
                multiplier = 1.0

            return base_stop_loss * multiplier

        except Exception:
            return base_stop_loss

    def _calculate_standard_deviation(self, returns: list[float]) -> float:
        """Calculate standard deviation of returns"""
        try:
            if len(returns) < 2:
                return 0.0

            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = math.sqrt(variance)

            # Annualize volatility (assuming 1-minute intervals)
            # 525600 minutes in a year
            annualized_vol = std_dev * math.sqrt(525600)

            return annualized_vol

        except Exception as e:
            logger.error(f"[VOLATILITY] Error calculating standard deviation: {e}")
            return 0.0

    def _calculate_confidence(self, data_points: int, min_points: int) -> float:
        """Calculate confidence score for volatility reading"""
        try:
            if data_points < min_points:
                return 0.0

            # Confidence increases with more data points, up to a maximum
            max_confidence_points = min_points * 3
            confidence = min(1.0, data_points / max_confidence_points)

            return confidence

        except Exception:
            return 0.5

    def _get_recent_prices(self, symbol: str, exchange=None) -> list[float]:
        """Get recent prices for volatility calculation"""
        try:
            # Try to get from internal history first
            if symbol in self.price_history:
                history = self.price_history[symbol]
                recent_history = history[-60:]  # Last 60 price points
                return [entry['price'] for entry in recent_history]

            # If no internal history and exchange provided, fetch from exchange
            if exchange:
                try:
                    # Get recent OHLCV data
                    ohlcv = exchange.fetch_ohlcv(symbol, '1m', limit=60)
                    if ohlcv:
                        prices = [candle[4] for candle in ohlcv]  # Close prices
                        return prices
                except Exception as e:
                    logger.debug(f"[VOLATILITY] Could not fetch OHLCV for {symbol}: {e}")

            return []

        except Exception as e:
            logger.error(f"[VOLATILITY] Error getting recent prices for {symbol}: {e}")
            return []

    def get_volatility_stats(self) -> dict[str, Any]:
        """Get volatility calculator statistics"""
        return {
            'symbols_tracked': len(self.price_history),
            'cached_readings': len(self.volatility_cache),
            'cache_ttl': self.cache_ttl,
            'max_history_size': self.max_history_size,
            'volatility_thresholds': self.volatility_thresholds,
            'min_data_points': {k.value: v for k, v in self.min_data_points.items()}
        }

    def clear_cache(self):
        """Clear volatility cache"""
        self.volatility_cache.clear()
        logger.info("[VOLATILITY] Cache cleared")

    def clear_old_data(self, max_age_hours: int = 24):
        """Clear old price history data"""
        try:
            cutoff_time = time.time() - (max_age_hours * 3600)
            cleared_count = 0

            for symbol in list(self.price_history.keys()):
                history = self.price_history[symbol]
                # Keep only recent data
                recent_history = [
                    entry for entry in history
                    if entry['timestamp'] > cutoff_time
                ]

                if len(recent_history) != len(history):
                    self.price_history[symbol] = recent_history
                    cleared_count += len(history) - len(recent_history)

                # Remove empty histories
                if not recent_history:
                    del self.price_history[symbol]

            if cleared_count > 0:
                logger.info(f"[VOLATILITY] Cleared {cleared_count} old price entries")

        except Exception as e:
            logger.error(f"[VOLATILITY] Error clearing old data: {e}")


# Global volatility calculator instance
_global_volatility_calculator = None


def get_volatility_calculator() -> VolatilityCalculator:
    """Get global volatility calculator instance"""
    global _global_volatility_calculator
    if _global_volatility_calculator is None:
        _global_volatility_calculator = VolatilityCalculator()
    return _global_volatility_calculator


async def calculate_symbol_volatility(symbol: str, prices: list[float]) -> Optional[float]:
    """Global function to calculate symbol volatility"""
    calculator = get_volatility_calculator()
    reading = await calculator.calculate_volatility(symbol, prices)
    return reading.volatility if reading else None
