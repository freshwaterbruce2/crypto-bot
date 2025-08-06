"""
Sell Logic Assistant
Provides intelligent sell signal analysis and exit point optimization
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SellLogicAssistant:
    """
    Intelligent assistant for sell signal analysis and exit optimization
    Analyzes profit targets, risk management, and market conditions
    """

    def __init__(self, trade_executor=None):
        """Initialize sell logic assistant"""
        self.trade_executor = trade_executor
        self.logger = logger

        # Sell signal parameters
        self.min_profit_target = 0.005  # 0.5% minimum profit
        self.max_loss_threshold = -0.02  # -2% maximum loss
        self.trailing_stop_distance = 0.003  # 0.3% trailing stop

        # Time-based parameters
        self.max_hold_time = 3600  # 1 hour maximum hold
        self.profit_acceleration_time = 1800  # 30 minutes for profit acceleration

        # Technical exit parameters
        self.overbought_rsi = 75
        self.volume_spike_threshold = 2.0  # 200% volume increase
        self.resistance_proximity = 0.005  # 0.5% from resistance

        # Performance tracking
        self.sell_decisions = []
        self.exit_performance = {
            'total_exits': 0,
            'profitable_exits': 0,
            'avg_profit_pct': 0.0,
            'avg_hold_time': 0.0,
            'best_exit_timing': 0.0
        }

        self.logger.info("[SELL_LOGIC] Assistant initialized")

    async def analyze_exit_opportunity(self, position: dict[str, Any], market_data: dict[str, Any],
                                     portfolio_state: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze exit opportunity for a position

        Args:
            position: Position data with symbol, amount, entry_price, entry_time
            market_data: Current market data with price, volume, indicators
            portfolio_state: Current portfolio state and risk metrics

        Returns:
            Dict with recommendation, confidence, exit_price, exit_amount, reasoning
        """
        try:
            symbol = position.get('symbol', '')
            entry_price = Decimal(str(position.get('entry_price', 0)))
            entry_time = position.get('entry_time', datetime.now())
            position_size = Decimal(str(position.get('amount', 0)))

            current_price = Decimal(str(market_data.get('price', 0)))

            if current_price <= 0 or entry_price <= 0:
                return {
                    'recommendation': 'HOLD',
                    'confidence': 0.0,
                    'reason': 'Invalid price data',
                    'exit_price': 0,
                    'exit_amount': 0
                }

            # Calculate position metrics
            profit_pct = float((current_price - entry_price) / entry_price)
            hold_time_seconds = (datetime.now() - entry_time).total_seconds()
            hold_time_hours = hold_time_seconds / 3600

            # Analysis factors
            exit_factors = []
            confidence_score = 0.5  # Base confidence

            # 1. Profit Target Analysis
            profit_score = self._analyze_profit_targets(profit_pct, hold_time_hours)
            confidence_score += profit_score * 0.3
            if profit_score > 0.5:
                exit_factors.append(f"Profit target conditions met (profit: {profit_pct:.3f}%)")

            # 2. Risk Management Analysis
            risk_score = self._analyze_risk_factors(profit_pct, hold_time_seconds, portfolio_state)
            confidence_score += risk_score * 0.25
            if risk_score > 0.5:
                exit_factors.append(f"Risk management triggered (score: {risk_score:.2f})")

            # 3. Technical Exit Signals
            tech_score = await self._analyze_technical_exits(market_data, current_price)
            confidence_score += tech_score * 0.25
            if tech_score > 0.5:
                exit_factors.append(f"Technical exit signals (score: {tech_score:.2f})")

            # 4. Market Condition Analysis
            market_score = self._analyze_market_conditions(market_data, position)
            confidence_score += market_score * 0.2
            if market_score > 0.5:
                exit_factors.append(f"Market conditions favor exit (score: {market_score:.2f})")

            # Normalize confidence
            confidence_score = min(max(confidence_score, 0.0), 1.0)

            # Determine recommendation and exit strategy
            recommendation = 'HOLD'
            exit_price = float(current_price)
            exit_amount = 0

            if confidence_score >= 0.7:
                recommendation = 'SELL'
                exit_amount = await self._calculate_exit_amount(position_size, profit_pct,
                                                              confidence_score, hold_time_hours)
                exit_price = await self._optimize_exit_price(current_price, market_data)

            elif confidence_score >= 0.8 or profit_pct >= 0.02:  # Strong signal or 2%+ profit
                recommendation = 'SELL'
                exit_amount = float(position_size)  # Full exit

            elif profit_pct <= self.max_loss_threshold:  # Stop loss
                recommendation = 'SELL'
                exit_amount = float(position_size)  # Full exit at loss
                exit_factors.append(f"Stop loss triggered at {profit_pct:.3f}%")

            elif hold_time_seconds > self.max_hold_time:  # Time-based exit
                recommendation = 'SELL'
                exit_amount = float(position_size * Decimal('0.5'))  # Partial exit
                exit_factors.append(f"Maximum hold time exceeded ({hold_time_hours:.1f}h)")

            # Trailing stop check
            trailing_stop_price = await self._check_trailing_stop(position, current_price, market_data)
            if trailing_stop_price and current_price <= trailing_stop_price:
                recommendation = 'SELL'
                exit_amount = float(position_size)
                exit_factors.append(f"Trailing stop triggered at {trailing_stop_price}")

            # Record decision for learning
            decision_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'recommendation': recommendation,
                'confidence': confidence_score,
                'profit_pct': profit_pct,
                'hold_time_hours': hold_time_hours,
                'exit_amount': exit_amount,
                'market_conditions': {
                    'price': float(current_price),
                    'volume_ratio': market_data.get('volume_ratio', 1.0),
                    'rsi': market_data.get('rsi', 50)
                },
                'exit_factors': exit_factors
            }
            self.sell_decisions.append(decision_record)

            if recommendation == 'SELL':
                self.exit_performance['total_exits'] += 1
                if profit_pct > 0:
                    self.exit_performance['profitable_exits'] += 1

            reasoning = "; ".join(exit_factors) if exit_factors else "No strong exit signals detected"

            return {
                'recommendation': recommendation,
                'confidence': confidence_score,
                'reason': reasoning,
                'exit_price': exit_price,
                'exit_amount': exit_amount,
                'analysis': {
                    'profit_pct': profit_pct,
                    'hold_time_hours': hold_time_hours,
                    'profit_score': profit_score,
                    'risk_score': risk_score,
                    'technical_score': tech_score,
                    'market_score': market_score,
                    'trailing_stop_price': trailing_stop_price
                }
            }

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error analyzing exit opportunity: {e}")
            return {
                'recommendation': 'HOLD',
                'confidence': 0.0,
                'reason': f"Analysis error: {str(e)}",
                'exit_price': 0,
                'exit_amount': 0
            }

    def _analyze_profit_targets(self, profit_pct: float, hold_time_hours: float) -> float:
        """Analyze profit target achievement"""
        try:
            score = 0.0

            # Profit milestone analysis
            if profit_pct >= 0.02:  # 2%+ profit
                score += 0.8
            elif profit_pct >= 0.015:  # 1.5%+ profit
                score += 0.6
            elif profit_pct >= self.min_profit_target:  # Minimum target
                score += 0.4
            elif profit_pct > 0:  # Any profit
                score += 0.2

            # Time-adjusted profit expectations
            if hold_time_hours > 1:  # Held for over an hour
                if profit_pct >= 0.01:  # 1%+ after 1h is good
                    score += 0.3
                elif profit_pct >= 0.005:  # 0.5%+ after 1h is acceptable
                    score += 0.1
                else:  # Not meeting time-based expectations
                    score += 0.2  # Still consider exit

            # Profit acceleration analysis
            if hold_time_hours < 0.5 and profit_pct >= 0.01:  # Quick 1%+ profit
                score += 0.4

            return min(score, 1.0)

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error in profit analysis: {e}")
            return 0.0

    def _analyze_risk_factors(self, profit_pct: float, hold_time_seconds: float,
                             portfolio_state: dict[str, Any]) -> float:
        """Analyze risk factors requiring exit"""
        try:
            score = 0.0

            # Loss threshold analysis
            if profit_pct <= self.max_loss_threshold:
                score += 1.0  # Immediate exit required
            elif profit_pct <= -0.01:  # -1% loss
                score += 0.6
            elif profit_pct < 0:  # Any loss
                score += 0.3

            # Time risk analysis
            if hold_time_seconds > self.max_hold_time * 1.5:  # 1.5x max hold time
                score += 0.8
            elif hold_time_seconds > self.max_hold_time:  # Max hold time
                score += 0.5
            elif hold_time_seconds > self.max_hold_time * 0.8:  # 80% of max time
                score += 0.2

            # Portfolio risk analysis
            portfolio_risk = portfolio_state.get('total_risk_pct', 0)
            if portfolio_risk > 0.8:  # High portfolio risk
                score += 0.4
            elif portfolio_risk > 0.6:  # Moderate portfolio risk
                score += 0.2

            # Drawdown protection
            portfolio_drawdown = portfolio_state.get('drawdown_pct', 0)
            if portfolio_drawdown > 0.05:  # 5%+ drawdown
                score += 0.3

            return min(score, 1.0)

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error in risk analysis: {e}")
            return 0.0

    async def _analyze_technical_exits(self, market_data: dict[str, Any], current_price: Decimal) -> float:
        """Analyze technical indicators for exit signals"""
        try:
            score = 0.0

            # RSI overbought analysis
            rsi = market_data.get('rsi', 50)
            if rsi >= self.overbought_rsi:
                score += 0.7
            elif rsi >= 65:
                score += 0.4
            elif rsi >= 55:
                score += 0.1

            # MACD divergence
            macd = market_data.get('macd', 0)
            macd_signal = market_data.get('macd_signal', 0)
            if macd < macd_signal and macd > 0:  # Bearish divergence
                score += 0.6
            elif macd < macd_signal:  # Bearish momentum
                score += 0.3

            # Bollinger Bands analysis
            bb_upper = market_data.get('bb_upper', 0)
            if bb_upper > 0 and float(current_price) >= bb_upper * 0.99:  # Near upper band
                score += 0.5

            # Volume spike analysis
            volume_ratio = market_data.get('volume_ratio', 1.0)
            if volume_ratio >= self.volume_spike_threshold:
                score += 0.4  # High volume could indicate distribution

            # Resistance level analysis
            resistance_level = market_data.get('resistance_level', 0)
            if resistance_level > 0:
                distance_to_resistance = abs(float(current_price) - resistance_level) / resistance_level
                if distance_to_resistance <= self.resistance_proximity:
                    score += 0.5

            return min(score, 1.0)

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error in technical analysis: {e}")
            return 0.0

    def _analyze_market_conditions(self, market_data: dict[str, Any], position: dict[str, Any]) -> float:
        """Analyze overall market conditions for exit timing"""
        try:
            score = 0.0

            # Market trend analysis
            trend = market_data.get('trend', 'neutral')
            if trend == 'bearish':
                score += 0.4
            elif trend == 'neutral':
                score += 0.1

            # Volatility analysis
            volatility = market_data.get('volatility', 0.02)
            if volatility > 0.1:  # High volatility - consider exit
                score += 0.3
            elif volatility > 0.05:  # Moderate volatility
                score += 0.1

            # Market momentum
            market_momentum = market_data.get('market_momentum', 0)
            if market_momentum < -0.02:  # Negative momentum
                score += 0.3
            elif market_momentum < 0:  # Slight negative momentum
                score += 0.1

            # Time of day considerations (if available)
            current_hour = datetime.now().hour
            if 20 <= current_hour <= 23 or 0 <= current_hour <= 6:  # Lower liquidity hours
                score += 0.1

            return min(score, 1.0)

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error in market analysis: {e}")
            return 0.0

    async def _calculate_exit_amount(self, position_size: Decimal, profit_pct: float,
                                   confidence: float, hold_time_hours: float) -> float:
        """Calculate optimal exit amount based on conditions"""
        try:
            # Base exit percentage based on confidence
            if confidence >= 0.9:
                exit_pct = 1.0  # Full exit
            elif confidence >= 0.8:
                exit_pct = 0.8  # 80% exit
            elif confidence >= 0.7:
                exit_pct = 0.6  # 60% exit
            else:
                exit_pct = 0.3  # 30% exit

            # Adjust based on profit level
            if profit_pct >= 0.02:  # 2%+ profit - take more off
                exit_pct = min(exit_pct + 0.2, 1.0)
            elif profit_pct >= 0.01:  # 1%+ profit - take some off
                exit_pct = min(exit_pct + 0.1, 1.0)
            elif profit_pct <= 0:  # At loss - partial exit to preserve capital
                exit_pct = max(exit_pct - 0.2, 0.3)

            # Time-based adjustments
            if hold_time_hours > 2:  # Long hold - consider larger exit
                exit_pct = min(exit_pct + 0.1, 1.0)

            return float(position_size * Decimal(str(exit_pct)))

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error calculating exit amount: {e}")
            return float(position_size * Decimal('0.5'))  # Default 50% exit

    async def _optimize_exit_price(self, current_price: Decimal, market_data: dict[str, Any]) -> float:
        """Optimize exit price based on market microstructure"""
        try:
            optimized_price = float(current_price)

            # Bid-ask spread analysis
            bid = market_data.get('bid', optimized_price)
            ask = market_data.get('ask', optimized_price)
            spread = ask - bid if ask > bid else 0

            # For selling, target price closer to ask but realistic
            if spread > 0 and spread / optimized_price < 0.001:  # <0.1% spread
                optimized_price = ask - (spread * 0.3)

            # Resistance level consideration
            resistance_level = market_data.get('resistance_level', 0)
            if resistance_level > 0 and resistance_level > optimized_price:
                # If below resistance, might get better fill closer to resistance
                max_target = resistance_level * 0.999  # Slightly below resistance
                optimized_price = min(optimized_price * 1.002, max_target)

            return optimized_price

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error optimizing exit price: {e}")
            return float(current_price)

    async def _check_trailing_stop(self, position: dict[str, Any], current_price: Decimal,
                                 market_data: dict[str, Any]) -> Optional[float]:
        """Check if trailing stop should be triggered"""
        try:
            entry_price = Decimal(str(position.get('entry_price', 0)))
            highest_price = Decimal(str(position.get('highest_price', current_price)))

            # Update highest price if current is higher
            if current_price > highest_price:
                highest_price = current_price
                # Update position record (would need to persist this)

            # Calculate trailing stop price
            trailing_stop_price = highest_price * (Decimal('1') - Decimal(str(self.trailing_stop_distance)))

            # Only trigger if:
            # 1. We're in profit
            # 2. Current price hit the trailing stop
            if current_price > entry_price and current_price <= trailing_stop_price:
                return float(trailing_stop_price)

            return None

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error checking trailing stop: {e}")
            return None

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary of exit decisions"""
        if self.exit_performance['total_exits'] > 0:
            success_rate = self.exit_performance['profitable_exits'] / self.exit_performance['total_exits']
        else:
            success_rate = 0.0

        return {
            'total_exit_decisions': len(self.sell_decisions),
            'total_exits': self.exit_performance['total_exits'],
            'profitable_exits': self.exit_performance['profitable_exits'],
            'success_rate': success_rate,
            'recent_decisions': self.sell_decisions[-10:] if self.sell_decisions else []
        }

    async def update_exit_parameters(self, market_volatility: float, portfolio_performance: float):
        """Dynamically adjust exit parameters based on conditions"""
        try:
            # Adjust profit targets based on market volatility
            if market_volatility > 0.1:  # High volatility
                self.min_profit_target = 0.003  # Lower target, take profits quicker
                self.trailing_stop_distance = 0.005  # Wider trailing stop
            elif market_volatility < 0.02:  # Low volatility
                self.min_profit_target = 0.008  # Higher target, be more patient
                self.trailing_stop_distance = 0.002  # Tighter trailing stop

            # Adjust based on portfolio performance
            if portfolio_performance < -0.05:  # Portfolio down 5%+
                self.max_loss_threshold = -0.015  # Tighter stop loss
                self.max_hold_time = 2700  # Shorter hold time (45 min)
            elif portfolio_performance > 0.1:  # Portfolio up 10%+
                self.min_profit_target = 0.008  # Higher profit targets
                self.max_hold_time = 5400  # Longer hold time (1.5h)

            self.logger.info(f"[SELL_LOGIC] Parameters adjusted - profit target: {self.min_profit_target:.3f}, stop loss: {self.max_loss_threshold:.3f}")

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error updating parameters: {e}")

    async def analyze_sell_opportunity(self, symbol: str, position: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze sell opportunity for a position (simplified interface)
        Called by AssistantManager - provides compatibility with existing code
        """
        try:
            # Get market data if we have access to trade executor
            market_data = {}
            if self.trade_executor and hasattr(self.trade_executor, 'exchange'):
                try:
                    ticker = await self.trade_executor.exchange.fetch_ticker(symbol)
                    market_data = {
                        'price': ticker.get('last', 0),
                        'volume': ticker.get('baseVolume', 0),
                        'volume_ratio': ticker.get('percentage', 0) / 100 + 1,  # Convert % to ratio
                        'volatility': 0.02,  # Default volatility
                        'rsi': 50,  # Default RSI
                        'trend': 'neutral'  # Default trend
                    }
                except Exception as e:
                    self.logger.warning(f"[SELL_LOGIC] Could not fetch market data for {symbol}: {e}")
                    market_data = {'price': 0}

            # Create basic portfolio state
            portfolio_state = {
                'total_value': 1000,  # Default portfolio value
                'risk_level': 'medium',
                'unrealized_pnl_pct': 0
            }

            # Call the main exit analysis
            result = await self.analyze_exit_opportunity(position, market_data, portfolio_state)

            # Convert to expected format for assistant manager
            return {
                'recommend': result.get('recommendation') == 'SELL',
                'reason': result.get('reason', 'No sell conditions met'),
                'confidence': result.get('confidence', 0.0),
                'suggested_amount': result.get('exit_amount', 0),
                'exit_analysis': {
                    'profit_pct': result.get('profit_pct', 0),
                    'exit_price': result.get('exit_price', 0),
                    'hold_time_hours': result.get('hold_time_hours', 0)
                }
            }

        except Exception as e:
            self.logger.error(f"[SELL_LOGIC] Error analyzing sell opportunity for {symbol}: {e}")
            return {
                'recommend': False,
                'reason': f"Analysis error: {str(e)}",
                'confidence': 0.0,
                'suggested_amount': 0
            }
