"""
Mean Reversion Strategy
Statistical mean reversion trading using Bollinger Bands and price deviation
"""

import logging
import statistics
from typing import Any, Dict

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using statistical analysis"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize mean reversion strategy"""
        super().__init__("mean_reversion", config)

        # Mean reversion parameters
        mean_config = config.get('mean_reversion_config', {})
        self.window = mean_config.get('window', 20)
        self.deviation = mean_config.get('deviation', 2.0)
        self.stop_loss_pct = mean_config.get('stop_loss_pct', 0.008)
        self.take_profit_pct = mean_config.get('take_profit_pct', 0.015)
        self.trailing_stop_pct = mean_config.get('trailing_stop_pct', 0.005)

        # Price data cache
        self.price_history = {}
        self.max_history = 100

        logger.info(f"[MEAN_REV] Strategy initialized with {self.window} period window")

    async def analyze(self, symbol: str, timeframe: str = '1m') -> Dict[str, Any]:
        """Analyze symbol for mean reversion opportunities"""
        try:
            # Get current ticker
            ticker = await self.exchange.fetch_ticker(symbol) if self.exchange else {}

            if not ticker:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'No ticker data'}

            current_price = ticker.get('last', 0)
            if current_price <= 0:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'Invalid price'}

            # Update price history
            self._update_price_history(symbol, current_price)

            # Get price history for analysis
            prices = self.price_history.get(symbol, [])
            if len(prices) < self.window:
                return {'action': 'HOLD', 'confidence': 0.3, 'reason': 'Insufficient price history'}

            # Calculate Bollinger Bands
            recent_prices = prices[-self.window:]
            mean_price = statistics.mean(recent_prices)
            std_dev = statistics.stdev(recent_prices) if len(recent_prices) > 1 else 0

            upper_band = mean_price + (self.deviation * std_dev)
            lower_band = mean_price - (self.deviation * std_dev)

            # Calculate position relative to bands
            band_position = 0.5  # Neutral
            if upper_band != lower_band:
                band_position = (current_price - lower_band) / (upper_band - lower_band)

            # Generate signals
            confidence = 0.5
            action = 'HOLD'
            reason = 'Price within bands'

            # Oversold condition (potential buy)
            if band_position <= 0.1:  # Near lower band
                action = 'BUY'
                confidence = min(0.9, 0.6 + (0.1 - band_position) * 3)
                reason = f'Oversold: {band_position:.3f} band position'

            # Overbought condition (potential sell)
            elif band_position >= 0.9:  # Near upper band
                action = 'SELL'
                confidence = min(0.9, 0.6 + (band_position - 0.9) * 3)
                reason = f'Overbought: {band_position:.3f} band position'

            # Volume confirmation
            volume = ticker.get('quoteVolume', 0)
            if volume > 500000:  # Good volume
                confidence += 0.1

            # Price momentum check
            if len(prices) >= 3:
                momentum = (prices[-1] - prices[-3]) / prices[-3]
                if abs(momentum) > 0.002:  # 0.2% momentum
                    confidence += 0.05

            return {
                'action': action,
                'confidence': min(confidence, 1.0),
                'reason': reason,
                'price': current_price,
                'metadata': {
                    'mean_price': mean_price,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'band_position': band_position,
                    'std_dev': std_dev,
                    'window_size': len(recent_prices)
                }
            }

        except Exception as e:
            logger.error(f"[MEAN_REV] Error analyzing {symbol}: {e}")
            return {'action': 'HOLD', 'confidence': 0, 'reason': f'Analysis error: {e}'}

    async def should_buy(self, symbol: str, analysis: Dict[str, Any]) -> bool:
        """Check if should buy based on mean reversion"""
        try:
            if analysis.get('action') != 'BUY':
                return False

            confidence = analysis.get('confidence', 0)
            if confidence < 0.6:
                return False

            # Check oversold condition
            metadata = analysis.get('metadata', {})
            band_position = metadata.get('band_position', 0.5)

            if band_position > 0.2:  # Not oversold enough
                return False

            # Check available balance
            if self.balance_manager:
                usdt_balance = await self.balance_manager.get_balance_for_asset('USDT')
                if usdt_balance < 2.0:
                    return False

            logger.info(f"[MEAN_REV] Buy signal for {symbol} at {band_position:.3f} band position")
            return True

        except Exception as e:
            logger.error(f"[MEAN_REV] Error in buy decision for {symbol}: {e}")
            return False

    async def should_sell(self, symbol: str, analysis: Dict[str, Any]) -> bool:
        """Check if should sell based on mean reversion"""
        try:
            if analysis.get('action') != 'SELL':
                return False

            confidence = analysis.get('confidence', 0)
            if confidence < 0.6:
                return False

            # Check overbought condition
            metadata = analysis.get('metadata', {})
            band_position = metadata.get('band_position', 0.5)

            if band_position < 0.8:  # Not overbought enough
                return False

            # Check if we have position
            if self.balance_manager:
                asset = symbol.split('/')[0]
                balance = await self.balance_manager.get_balance_for_asset(asset)
                if balance <= 0:
                    return False

            logger.info(f"[MEAN_REV] Sell signal for {symbol} at {band_position:.3f} band position")
            return True

        except Exception as e:
            logger.error(f"[MEAN_REV] Error in sell decision for {symbol}: {e}")
            return False

    def _update_price_history(self, symbol: str, price: float):
        """Update price history for symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []

        self.price_history[symbol].append(price)

        # Limit history size
        if len(self.price_history[symbol]) > self.max_history:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history:]

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        return {
            'name': 'MeanReversionStrategy',
            'version': '1.0.0',
            'type': 'mean_reversion',
            'timeframe': '1m',
            'window': self.window,
            'deviation': self.deviation,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'trailing_stop_pct': self.trailing_stop_pct
        }
