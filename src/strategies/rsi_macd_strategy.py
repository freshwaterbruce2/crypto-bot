"""
RSI MACD Strategy
Technical analysis strategy combining RSI and MACD indicators
"""

import logging
from typing import Any

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class RsiMacdStrategy(BaseStrategy):
    """RSI and MACD combined technical analysis strategy"""

    def __init__(self, config: dict[str, Any]):
        """Initialize RSI MACD strategy"""
        super().__init__("rsi_macd", config)

        # Technical indicator parameters
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70

        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9

        # Price and indicator data cache
        self.price_history = {}
        self.rsi_values = {}
        self.macd_values = {}
        self.max_history = 50

        logger.info("[RSI_MACD] Strategy initialized with RSI/MACD indicators")

    async def analyze(self, symbol: str, timeframe: str = '1m') -> dict[str, Any]:
        """Analyze symbol using RSI and MACD indicators"""
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

            # Get price history
            prices = self.price_history.get(symbol, [])
            if len(prices) < max(self.rsi_period, self.macd_slow):
                return {'action': 'HOLD', 'confidence': 0.3, 'reason': 'Insufficient price history'}

            # Calculate RSI
            rsi = self._calculate_rsi(prices)

            # Calculate MACD
            macd_line, signal_line, histogram = self._calculate_macd(prices)

            # Generate signals
            confidence = 0.5
            action = 'HOLD'
            reason = 'Neutral signals'

            # RSI signals
            rsi_signal = 'neutral'
            if rsi < self.rsi_oversold:
                rsi_signal = 'oversold'
                confidence += 0.2
            elif rsi > self.rsi_overbought:
                rsi_signal = 'overbought'
                confidence += 0.2

            # MACD signals
            macd_signal = 'neutral'
            if macd_line > signal_line and histogram > 0:
                macd_signal = 'bullish'
                confidence += 0.2
            elif macd_line < signal_line and histogram < 0:
                macd_signal = 'bearish'
                confidence += 0.2

            # Combined signals
            if rsi_signal == 'oversold' and macd_signal == 'bullish':
                action = 'BUY'
                confidence += 0.3
                reason = 'RSI oversold + MACD bullish crossover'
            elif rsi_signal == 'overbought' and macd_signal == 'bearish':
                action = 'SELL'
                confidence += 0.3
                reason = 'RSI overbought + MACD bearish crossover'
            elif rsi_signal == 'oversold':
                action = 'BUY'
                confidence += 0.1
                reason = 'RSI oversold condition'
            elif rsi_signal == 'overbought':
                action = 'SELL'
                confidence += 0.1
                reason = 'RSI overbought condition'
            elif macd_signal == 'bullish':
                action = 'BUY'
                confidence += 0.1
                reason = 'MACD bullish signal'
            elif macd_signal == 'bearish':
                action = 'SELL'
                confidence += 0.1
                reason = 'MACD bearish signal'

            # Volume confirmation
            volume = ticker.get('quoteVolume', 0)
            if volume > 1000000:
                confidence += 0.1

            return {
                'action': action,
                'confidence': min(confidence, 1.0),
                'reason': reason,
                'price': current_price,
                'metadata': {
                    'rsi': rsi,
                    'rsi_signal': rsi_signal,
                    'macd_line': macd_line,
                    'signal_line': signal_line,
                    'histogram': histogram,
                    'macd_signal': macd_signal,
                    'volume': volume
                }
            }

        except Exception as e:
            logger.error(f"[RSI_MACD] Error analyzing {symbol}: {e}")
            return {'action': 'HOLD', 'confidence': 0, 'reason': f'Analysis error: {e}'}

    async def should_buy(self, symbol: str, analysis: dict[str, Any]) -> bool:
        """Check if should buy based on RSI/MACD signals"""
        try:
            if analysis.get('action') != 'BUY':
                return False

            confidence = analysis.get('confidence', 0)
            if confidence < 0.6:
                return False

            # Check RSI oversold condition
            metadata = analysis.get('metadata', {})
            rsi = metadata.get('rsi', 50)

            if rsi > 40:  # Not oversold enough
                return False

            # Check available balance
            if self.balance_manager:
                usdt_balance = await self.balance_manager.get_balance_for_asset('USDT')
                if usdt_balance < 2.0:
                    return False

            logger.info(f"[RSI_MACD] Buy signal for {symbol} (RSI: {rsi:.1f})")
            return True

        except Exception as e:
            logger.error(f"[RSI_MACD] Error in buy decision for {symbol}: {e}")
            return False

    async def should_sell(self, symbol: str, analysis: dict[str, Any]) -> bool:
        """Check if should sell based on RSI/MACD signals"""
        try:
            if analysis.get('action') != 'SELL':
                return False

            confidence = analysis.get('confidence', 0)
            if confidence < 0.6:
                return False

            # Check RSI overbought condition
            metadata = analysis.get('metadata', {})
            rsi = metadata.get('rsi', 50)

            if rsi < 60:  # Not overbought enough
                return False

            # Check if we have position
            if self.balance_manager:
                asset = symbol.split('/')[0]
                balance = await self.balance_manager.get_balance_for_asset(asset)
                if balance <= 0:
                    return False

            logger.info(f"[RSI_MACD] Sell signal for {symbol} (RSI: {rsi:.1f})")
            return True

        except Exception as e:
            logger.error(f"[RSI_MACD] Error in sell decision for {symbol}: {e}")
            return False

    def _calculate_rsi(self, prices: list[float]) -> float:
        """Calculate RSI (Relative Strength Index)"""
        try:
            if len(prices) < self.rsi_period + 1:
                return 50.0  # Neutral RSI

            # Calculate price changes
            changes = []
            for i in range(1, len(prices)):
                changes.append(prices[i] - prices[i-1])

            # Get recent changes
            recent_changes = changes[-(self.rsi_period):]

            # Calculate gains and losses
            gains = [change if change > 0 else 0 for change in recent_changes]
            losses = [-change if change < 0 else 0 for change in recent_changes]

            # Calculate average gain and loss
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0

            # Calculate RSI
            if avg_loss == 0:
                return 100.0  # All gains

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            return rsi

        except Exception as e:
            logger.error(f"[RSI_MACD] Error calculating RSI: {e}")
            return 50.0

    def _calculate_macd(self, prices: list[float]) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            if len(prices) < self.macd_slow:
                return 0.0, 0.0, 0.0

            # Calculate EMAs
            ema_fast = self._calculate_ema(prices, self.macd_fast)
            ema_slow = self._calculate_ema(prices, self.macd_slow)

            # MACD line
            macd_line = ema_fast - ema_slow

            # Signal line (EMA of MACD line)
            # For simplicity, use a basic average
            signal_line = macd_line * 0.9  # Simplified signal line

            # Histogram
            histogram = macd_line - signal_line

            return macd_line, signal_line, histogram

        except Exception as e:
            logger.error(f"[RSI_MACD] Error calculating MACD: {e}")
            return 0.0, 0.0, 0.0

    def _calculate_ema(self, prices: list[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        try:
            if len(prices) < period:
                return sum(prices) / len(prices)  # Simple average

            recent_prices = prices[-period:]
            multiplier = 2 / (period + 1)

            # Start with simple average
            ema = sum(recent_prices[:period]) / period

            # Calculate EMA for remaining prices
            for price in recent_prices[period:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))

            return ema

        except Exception as e:
            logger.error(f"[RSI_MACD] Error calculating EMA: {e}")
            return prices[-1] if prices else 0.0

    def _update_price_history(self, symbol: str, price: float):
        """Update price history for symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []

        self.price_history[symbol].append(price)

        # Limit history size
        if len(self.price_history[symbol]) > self.max_history:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history:]

    def get_strategy_info(self) -> dict[str, Any]:
        """Get strategy information"""
        return {
            'name': 'RsiMacdStrategy',
            'version': '1.0.0',
            'type': 'technical_analysis',
            'timeframe': '1m',
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'macd_fast': self.macd_fast,
            'macd_slow': self.macd_slow,
            'macd_signal': self.macd_signal
        }
