"""
Micro Scalper Strategy
Ultra-fast micro-profit scalping strategy for small, frequent gains
"""

import logging
import time
from typing import Any, Dict, List

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class MicroScalperStrategy(BaseStrategy):
    """Micro scalping strategy for small, frequent profits"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize micro scalper strategy"""
        super().__init__("micro_scalper", config)

        # Micro scalping parameters
        self.micro_profit_target = 0.001  # 0.1% target
        self.micro_stop_loss = 0.0005     # 0.05% stop loss
        self.max_hold_time = 300          # 5 minutes max
        self.min_spread = 0.0001          # 0.01% minimum spread

        # Execution tracking
        self.entry_times = {}
        self.entry_prices = {}
        self.tick_history = {}
        self.max_ticks = 20

        # Performance optimization
        self.rapid_fire_mode = config.get('rapid_fire_mode', {}).get('enabled', False)
        self.consecutive_wins = 0
        self.win_streak_boost = 1.0

        logger.info("[MICRO_SCALP] Ultra-fast micro scalping strategy initialized")

    async def analyze(self, symbol: str, timeframe: str = '1m') -> Dict[str, Any]:
        """Ultra-fast micro scalping analysis"""
        start_time = time.time()

        try:
            # Get current ticker with minimal delay
            ticker = await self.exchange.fetch_ticker(symbol) if self.exchange else {}

            if not ticker:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'No ticker data'}

            current_price = ticker.get('last', 0)
            bid = ticker.get('bid', current_price)
            ask = ticker.get('ask', current_price)

            if current_price <= 0:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'Invalid price'}

            # Update tick history
            self._update_tick_history(symbol, current_price)

            # Calculate spread
            spread = (ask - bid) / current_price if ask > bid else 0

            # Get tick data
            ticks = self.tick_history.get(symbol, [])
            if len(ticks) < 3:
                return {'action': 'HOLD', 'confidence': 0.4, 'reason': 'Insufficient tick data'}

            # Micro momentum analysis
            recent_ticks = ticks[-3:]
            tick_change = (recent_ticks[-1] - recent_ticks[0]) / recent_ticks[0]

            # Quick volatility check
            tick_volatility = self._calculate_tick_volatility(recent_ticks)

            # Generate micro signals
            confidence = 0.5
            action = 'HOLD'
            reason = 'Neutral micro movement'

            # Ultra-small movement detection
            if tick_change > 0.0005:  # 0.05% upward micro movement
                action = 'BUY'
                confidence = 0.6 + min(tick_change * 200, 0.3)  # Scale confidence
                reason = f'Micro uptrend: {tick_change:.6f}'
            elif tick_change < -0.0005:  # 0.05% downward micro movement
                action = 'SELL'
                confidence = 0.6 + min(abs(tick_change) * 200, 0.3)
                reason = f'Micro downtrend: {tick_change:.6f}'

            # Spread check
            if spread > self.min_spread:
                confidence += 0.1
            else:
                confidence *= 0.8  # Reduce confidence for tight spreads

            # Rapid fire mode boost
            if self.rapid_fire_mode and self.consecutive_wins >= 3:
                confidence *= self.win_streak_boost
                reason += ' (rapid fire boost)'

            # Volume micro-confirmation
            volume = ticker.get('quoteVolume', 0)
            if volume > 100000:  # Minimum volume for micro scalping
                confidence += 0.05

            # Check hold time for existing positions
            if symbol in self.entry_times:
                hold_time = time.time() - self.entry_times[symbol]
                if hold_time > self.max_hold_time:
                    action = 'SELL'
                    confidence = 0.9
                    reason = 'Max hold time exceeded'

            return {
                'action': action,
                'confidence': min(confidence, 1.0),
                'reason': reason,
                'price': current_price,
                'execution_time': time.time() - start_time,
                'metadata': {
                    'tick_change': tick_change,
                    'tick_volatility': tick_volatility,
                    'spread': spread,
                    'bid': bid,
                    'ask': ask,
                    'consecutive_wins': self.consecutive_wins,
                    'rapid_fire_active': self.rapid_fire_mode and self.consecutive_wins >= 3
                }
            }

        except Exception as e:
            logger.error(f"[MICRO_SCALP] Error analyzing {symbol}: {e}")
            return {'action': 'HOLD', 'confidence': 0, 'reason': f'Analysis error: {e}'}

    async def should_buy(self, symbol: str, analysis: Dict[str, Any]) -> bool:
        """Ultra-fast buy decision for micro scalping"""
        try:
            if analysis.get('action') != 'BUY':
                return False

            confidence = analysis.get('confidence', 0)
            if confidence < 0.55:  # Lower threshold for micro scalping
                return False

            # Don't buy if we already have a position
            if symbol in self.entry_times:
                return False

            # Check micro spread requirement
            metadata = analysis.get('metadata', {})
            spread = metadata.get('spread', 0)
            if spread < self.min_spread:
                return False

            # Check available balance
            if self.balance_manager:
                usdt_balance = await self.balance_manager.get_balance_for_asset('USDT')
                if usdt_balance < 2.0:
                    return False

            # Record entry
            self.entry_times[symbol] = time.time()
            self.entry_prices[symbol] = analysis.get('price', 0)

            logger.info(f"[MICRO_SCALP] Micro buy signal for {symbol} (confidence: {confidence:.3f})")
            return True

        except Exception as e:
            logger.error(f"[MICRO_SCALP] Error in buy decision for {symbol}: {e}")
            return False

    async def should_sell(self, symbol: str, analysis: Dict[str, Any]) -> bool:
        """Ultra-fast sell decision for micro scalping"""
        try:
            # Check if we have a position
            if symbol not in self.entry_times:
                return False

            current_price = analysis.get('price', 0)
            entry_price = self.entry_prices.get(symbol, 0)

            if entry_price <= 0:
                return False

            # Calculate micro profit
            profit_pct = (current_price - entry_price) / entry_price

            # Micro profit target reached
            if profit_pct >= self.micro_profit_target:
                self._record_win(symbol)
                return True

            # Micro stop loss triggered
            if profit_pct <= -self.micro_stop_loss:
                self._record_loss(symbol)
                return True

            # Time-based exit
            hold_time = time.time() - self.entry_times[symbol]
            if hold_time > self.max_hold_time:
                self._record_exit(symbol, 'time_based')
                return True

            # Sell signal from analysis
            if analysis.get('action') == 'SELL' and analysis.get('confidence', 0) > 0.7:
                self._record_exit(symbol, 'signal_based')
                return True

            return False

        except Exception as e:
            logger.error(f"[MICRO_SCALP] Error in sell decision for {symbol}: {e}")
            return False

    def _update_tick_history(self, symbol: str, price: float):
        """Update tick price history"""
        if symbol not in self.tick_history:
            self.tick_history[symbol] = []

        self.tick_history[symbol].append(price)

        # Limit tick history
        if len(self.tick_history[symbol]) > self.max_ticks:
            self.tick_history[symbol] = self.tick_history[symbol][-self.max_ticks:]

    def _calculate_tick_volatility(self, ticks: List[float]) -> float:
        """Calculate micro tick volatility"""
        try:
            if len(ticks) < 2:
                return 0.0

            changes = []
            for i in range(1, len(ticks)):
                change = abs(ticks[i] - ticks[i-1]) / ticks[i-1]
                changes.append(change)

            return sum(changes) / len(changes) if changes else 0.0

        except Exception:
            return 0.0

    def _record_win(self, symbol: str):
        """Record successful micro trade"""
        self.consecutive_wins += 1
        self.win_streak_boost = min(1.5, 1.0 + (self.consecutive_wins * 0.1))
        self._cleanup_position(symbol)
        logger.info(f"[MICRO_SCALP] Win recorded for {symbol} (streak: {self.consecutive_wins})")

    def _record_loss(self, symbol: str):
        """Record losing micro trade"""
        self.consecutive_wins = 0
        self.win_streak_boost = 1.0
        self._cleanup_position(symbol)
        logger.info(f"[MICRO_SCALP] Loss recorded for {symbol} (streak reset)")

    def _record_exit(self, symbol: str, reason: str):
        """Record trade exit"""
        self._cleanup_position(symbol)
        logger.info(f"[MICRO_SCALP] Exit recorded for {symbol}: {reason}")

    def _cleanup_position(self, symbol: str):
        """Clean up position tracking"""
        if symbol in self.entry_times:
            del self.entry_times[symbol]
        if symbol in self.entry_prices:
            del self.entry_prices[symbol]

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        return {
            'name': 'MicroScalperStrategy',
            'version': '1.0.0',
            'type': 'micro_scalping',
            'timeframe': 'tick',
            'micro_profit_target': self.micro_profit_target,
            'micro_stop_loss': self.micro_stop_loss,
            'max_hold_time': self.max_hold_time,
            'min_spread': self.min_spread,
            'rapid_fire_mode': self.rapid_fire_mode,
            'consecutive_wins': self.consecutive_wins,
            'win_streak_boost': self.win_streak_boost
        }
