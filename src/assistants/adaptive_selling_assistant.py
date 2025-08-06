"""
Adaptive Selling Assistant
Provides intelligent selling decisions based on market conditions and profit targets
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AdaptiveSellingAssistant:
    """
    Intelligent assistant for adaptive selling decisions
    Analyzes market conditions, profit targets, and risk factors
    """

    def __init__(self, bot=None):
        """Initialize adaptive selling assistant"""
        self.bot = bot
        self.logger = logger

        # Selling parameters
        self.min_profit_pct = 0.005  # 0.5% minimum profit
        self.max_hold_time = 3600  # 1 hour max hold time
        self.trailing_stop_pct = 0.002  # 0.2% trailing stop

        # Market condition thresholds
        self.volatility_threshold = 0.05  # 5% volatility threshold
        self.volume_increase_threshold = 1.5  # 50% volume increase

        # Performance tracking
        self.sell_decisions = []
        self.performance_metrics = {
            'total_sells': 0,
            'profitable_sells': 0,
            'avg_profit_pct': 0.0,
            'avg_hold_time': 0.0
        }

        self.logger.info("[ADAPTIVE_SELLING] Assistant initialized")

    async def initialize(self):
        """Initialize the assistant"""
        self.logger.info("[ADAPTIVE_SELLING] Assistant ready for adaptive selling decisions")

    async def should_sell_position(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze if a position should be sold
        
        Args:
            position: Position data with symbol, amount, entry_price, entry_time
            market_data: Current market conditions
            
        Returns:
            Dict with sell_decision, reason, confidence, suggested_amount
        """
        try:
            symbol = position.get('symbol')
            entry_price = Decimal(str(position.get('entry_price', 0)))
            entry_time = position.get('entry_time', datetime.now())
            amount = Decimal(str(position.get('amount', 0)))

            current_price = Decimal(str(market_data.get('price', 0)))

            if current_price <= 0 or entry_price <= 0:
                return {
                    'sell_decision': False,
                    'reason': 'Invalid price data',
                    'confidence': 0.0,
                    'suggested_amount': 0
                }

            # Calculate current profit
            profit_pct = float((current_price - entry_price) / entry_price)
            hold_time = (datetime.now() - entry_time).total_seconds()

            # Decision factors
            factors = []
            confidence = 0.5

            # 1. Profit target analysis
            if profit_pct >= self.min_profit_pct:
                factors.append(f"Profit target reached: {profit_pct:.3f}%")
                confidence += 0.3

                # Higher confidence for higher profits
                if profit_pct >= 0.01:  # 1% profit
                    confidence += 0.2
                if profit_pct >= 0.02:  # 2% profit
                    confidence += 0.3

            # 2. Time-based selling
            if hold_time > self.max_hold_time:
                factors.append(f"Max hold time exceeded: {hold_time/3600:.1f}h")
                confidence += 0.2

            # 3. Market condition analysis
            volatility = market_data.get('volatility', 0)
            if volatility > self.volatility_threshold:
                factors.append(f"High volatility detected: {volatility:.3f}")
                confidence += 0.1

            # 4. Volume analysis
            volume_ratio = market_data.get('volume_ratio', 1.0)
            if volume_ratio > self.volume_increase_threshold:
                factors.append(f"Volume spike: {volume_ratio:.1f}x")
                confidence += 0.1

            # 5. Technical indicators
            rsi = market_data.get('rsi', 50)
            if rsi > 70:  # Overbought
                factors.append(f"Overbought condition: RSI {rsi:.1f}")
                confidence += 0.15

            # Decision logic
            should_sell = False
            suggested_amount = 0

            if confidence >= 0.7 and (profit_pct >= self.min_profit_pct or hold_time > self.max_hold_time):
                should_sell = True

                # Determine sell amount based on conditions
                if profit_pct >= 0.02:  # 2%+ profit - sell all
                    suggested_amount = float(amount)
                elif profit_pct >= 0.01:  # 1%+ profit - sell 80%
                    suggested_amount = float(amount * Decimal('0.8'))
                elif profit_pct >= self.min_profit_pct:  # Min profit - sell 60%
                    suggested_amount = float(amount * Decimal('0.6'))
                else:  # Time-based or risk-based - sell 50%
                    suggested_amount = float(amount * Decimal('0.5'))

            # Record decision for learning
            decision_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'profit_pct': profit_pct,
                'hold_time': hold_time,
                'decision': should_sell,
                'confidence': confidence,
                'factors': factors
            }
            self.sell_decisions.append(decision_record)

            # Update performance metrics
            if should_sell:
                self.performance_metrics['total_sells'] += 1
                if profit_pct > 0:
                    self.performance_metrics['profitable_sells'] += 1

            reason = "; ".join(factors) if factors else "No sell conditions met"

            return {
                'sell_decision': should_sell,
                'reason': reason,
                'confidence': min(confidence, 1.0),
                'suggested_amount': suggested_amount,
                'profit_pct': profit_pct,
                'analysis': {
                    'hold_time_hours': hold_time / 3600,
                    'profit_target_met': profit_pct >= self.min_profit_pct,
                    'market_conditions': {
                        'volatility': volatility,
                        'volume_ratio': volume_ratio,
                        'rsi': rsi
                    }
                }
            }

        except Exception as e:
            self.logger.error(f"[ADAPTIVE_SELLING] Error analyzing sell decision: {e}")
            return {
                'sell_decision': False,
                'reason': f"Analysis error: {str(e)}",
                'confidence': 0.0,
                'suggested_amount': 0
            }

    async def get_trailing_stop_price(self, position: Dict[str, Any], current_price: float) -> Optional[float]:
        """Calculate trailing stop price for a position"""
        try:
            entry_price = float(position.get('entry_price', 0))
            highest_price = float(position.get('highest_price', current_price))

            # Update highest price if current is higher
            if current_price > highest_price:
                highest_price = current_price

            # Calculate trailing stop
            trailing_stop = highest_price * (1 - self.trailing_stop_pct)

            # Only trigger if we're in profit and price has dropped
            if current_price <= trailing_stop and current_price > entry_price:
                return trailing_stop

            return None

        except Exception as e:
            self.logger.error(f"[ADAPTIVE_SELLING] Error calculating trailing stop: {e}")
            return None

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of selling decisions"""
        if self.performance_metrics['total_sells'] > 0:
            success_rate = self.performance_metrics['profitable_sells'] / self.performance_metrics['total_sells']
        else:
            success_rate = 0.0

        return {
            'total_decisions': len(self.sell_decisions),
            'total_sells': self.performance_metrics['total_sells'],
            'success_rate': success_rate,
            'recent_decisions': self.sell_decisions[-10:] if self.sell_decisions else []
        }

    async def evaluate_position(self, symbol: str, position: Dict[str, Any], market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Evaluate position for selling (alias for should_sell_position)
        Called by AssistantManager - provides compatibility with existing code
        """
        try:
            # If market_data not provided, try to get it from bot
            if market_data is None and self.bot and hasattr(self.bot, 'exchange'):
                try:
                    ticker = await self.bot.exchange.fetch_ticker(symbol)
                    market_data = {
                        'price': ticker.get('last', 0),
                        'volume': ticker.get('baseVolume', 0),
                        'volume_ratio': ticker.get('percentage', 0) / 100 + 1,  # Convert % to ratio
                        'volatility': 0.02,  # Default volatility
                        'rsi': 50  # Default RSI
                    }
                except Exception as e:
                    self.logger.warning(f"[ADAPTIVE_SELLING] Could not fetch market data for {symbol}: {e}")
                    market_data = {'price': 0}

            if market_data is None:
                market_data = {'price': 0}

            # Call the main selling logic
            return await self.should_sell_position(position, market_data)

        except Exception as e:
            self.logger.error(f"[ADAPTIVE_SELLING] Error evaluating position for {symbol}: {e}")
            return {
                'sell_decision': False,
                'reason': f"Evaluation error: {str(e)}",
                'confidence': 0.0,
                'suggested_amount': 0
            }

    async def adjust_selling_parameters(self, market_conditions: str):
        """Adjust selling parameters based on market conditions"""
        try:
            if market_conditions == 'bullish':
                # In bull market, be more patient
                self.min_profit_pct = 0.008  # 0.8%
                self.max_hold_time = 5400  # 1.5 hours
                self.logger.info("[ADAPTIVE_SELLING] Adjusted for bullish conditions")

            elif market_conditions == 'bearish':
                # In bear market, take profits quickly
                self.min_profit_pct = 0.003  # 0.3%
                self.max_hold_time = 1800  # 30 minutes
                self.logger.info("[ADAPTIVE_SELLING] Adjusted for bearish conditions")

            elif market_conditions == 'volatile':
                # In volatile market, use tighter stops
                self.trailing_stop_pct = 0.003  # 0.3%
                self.min_profit_pct = 0.004  # 0.4%
                self.logger.info("[ADAPTIVE_SELLING] Adjusted for volatile conditions")

        except Exception as e:
            self.logger.error(f"[ADAPTIVE_SELLING] Error adjusting parameters: {e}")
