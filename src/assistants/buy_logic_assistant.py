"""
Buy Logic Assistant
Provides intelligent buy signal analysis and entry point optimization
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BuyLogicAssistant:
    """
    Intelligent assistant for buy signal analysis and entry optimization
    Analyzes market conditions, technical indicators, and risk factors
    """

    def __init__(self, trade_executor=None):
        """Initialize buy logic assistant"""
        self.trade_executor = trade_executor
        self.logger = logger

        # Enhanced buy signal parameters
        self.base_confidence_threshold = 0.6  # Base confidence threshold
        self.min_confidence_threshold = self.base_confidence_threshold  # Adaptive threshold
        self.max_position_size_pct = 0.08  # 8% max per position (more conservative)
        self.min_volume_increase = 1.3  # 30% volume increase required (higher bar)

        # Market condition awareness
        self.market_regime_weights = {
            'bullish': 1.2,   # Boost confidence in bull markets
            'bearish': 0.6,   # Reduce confidence in bear markets
            'neutral': 1.0    # No adjustment
        }

        # Enhanced technical analysis thresholds
        self.rsi_extreme_oversold = 25  # Extreme oversold for strong signals
        self.rsi_oversold = 35  # Regular oversold threshold
        self.rsi_neutral_low = 45  # Approaching oversold
        self.rsi_overbought = 65  # RSI overbought threshold
        self.ma_alignment_threshold = 0.015  # 1.5% MA alignment (tighter)
        self.momentum_threshold = 0.008  # 0.8% minimum momentum

        # Enhanced market condition factors
        self.volatility_preference = 0.025  # 2.5% preferred volatility (lower)
        self.volatility_penalty_threshold = 0.06  # Penalize above 6% volatility
        self.support_resistance_margin = 0.008  # 0.8% margin (wider for accuracy)
        self.trend_confirmation_periods = [5, 10, 20]  # Multi-timeframe confirmation

        # Enhanced performance tracking
        self.buy_recommendations = []
        self.success_metrics = {
            'total_recommendations': 0,
            'successful_entries': 0,
            'avg_entry_accuracy': 0.0,
            'best_confidence_threshold': 0.6,
            'market_regime_performance': {},
            'volatility_performance': {},
            'pattern_success_rates': {}
        }

        # Adaptive learning components
        self.performance_buffer = []  # Rolling performance window
        self.threshold_optimization_enabled = True
        self.market_regime_detector = None  # Will be initialized if needed

        self.logger.info("[BUY_LOGIC] Assistant initialized")

    async def analyze_buy_opportunity(self, symbol: str, market_data: Dict[str, Any],
                                    portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced analysis with market regime awareness and adaptive thresholds
        
        Args:
            symbol: Trading symbol
            market_data: Current market data with price, volume, indicators
            portfolio_state: Current portfolio allocation and risk
            
        Returns:
            Dict with recommendation, confidence, entry_price, position_size, reasoning
        """
        try:
            current_price = Decimal(str(market_data.get('price', 0)))
            volume = market_data.get('volume', 0)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            volatility = market_data.get('volatility', 0.02)

            if current_price <= 0:
                return {
                    'recommendation': 'SKIP',
                    'confidence': 0.0,
                    'reason': 'Invalid price data',
                    'entry_price': 0,
                    'position_size': 0
                }

            # Detect market regime
            market_regime = await self._detect_market_regime(market_data)

            # Adaptive threshold adjustment
            adaptive_threshold = await self._calculate_adaptive_threshold(market_regime, volatility)

            # Enhanced analysis with market context
            analysis_factors = []
            confidence_score = 0.4  # Lower base confidence for higher quality

            # 1. Enhanced Technical Analysis (35% weight)
            tech_analysis = await self._analyze_technical_indicators_enhanced(market_data)
            tech_score = tech_analysis['score']
            confidence_score += tech_score * 0.35
            if tech_score > 0.6:
                analysis_factors.extend(tech_analysis['factors'])

            # 2. Enhanced Volume Flow Analysis (25% weight)
            volume_analysis = await self._analyze_volume_flow_enhanced(market_data)
            volume_score = volume_analysis['score']
            confidence_score += volume_score * 0.25
            if volume_score > 0.5:
                analysis_factors.extend(volume_analysis['factors'])

            # 3. Market Structure & Regime Analysis (20% weight)
            structure_analysis = await self._analyze_market_structure_enhanced(symbol, current_price, market_data, market_regime)
            structure_score = structure_analysis['score']
            confidence_score += structure_score * 0.20
            if structure_score > 0.5:
                analysis_factors.extend(structure_analysis['factors'])

            # 4. Enhanced Risk Assessment (10% weight)
            risk_analysis = await self._assess_entry_risk_enhanced(portfolio_state, symbol, current_price, market_regime)
            risk_score = risk_analysis['score']
            confidence_score += risk_score * 0.10
            if risk_score > 0.5:
                analysis_factors.extend(risk_analysis['factors'])

            # 5. Multi-timeframe Momentum Analysis (10% weight)
            momentum_analysis = await self._analyze_momentum_confluence(market_data)
            momentum_score = momentum_analysis['score']
            confidence_score += momentum_score * 0.10
            if momentum_score > 0.5:
                analysis_factors.extend(momentum_analysis['factors'])

            # Apply market regime weighting
            regime_weight = self.market_regime_weights.get(market_regime['trend'], 1.0)
            confidence_score *= regime_weight

            # Volatility penalty for extreme conditions
            if volatility > self.volatility_penalty_threshold:
                volatility_penalty = min(0.3, (volatility - self.volatility_penalty_threshold) * 5)
                confidence_score *= (1 - volatility_penalty)
                analysis_factors.append(f"Volatility penalty applied: {volatility_penalty:.1%}")

            # Normalize confidence score
            confidence_score = min(max(confidence_score, 0.0), 1.0)

            # Enhanced decision logic
            recommendation = 'SKIP'
            entry_price = float(current_price)
            position_size = 0

            if confidence_score >= adaptive_threshold:
                recommendation = 'BUY'

                # Enhanced position sizing with market regime consideration
                position_analysis = await self._calculate_optimal_position_size(
                    confidence_score, market_regime, volatility, portfolio_state
                )
                position_size = position_analysis['size']

                # Validate minimum position requirements
                min_order_size = 2.0
                if position_size < min_order_size:
                    available_capital = portfolio_state.get('available_usdt', 0)
                    if available_capital >= min_order_size:
                        position_size = min_order_size
                    else:
                        recommendation = 'SKIP'
                        analysis_factors.append("Insufficient capital for minimum order")

            # Enhanced entry price optimization
            if recommendation == 'BUY':
                entry_optimization = await self._optimize_entry_price_enhanced(current_price, market_data, market_regime)
                entry_price = entry_optimization['price']
                if entry_optimization.get('adjustment_reason'):
                    analysis_factors.append(entry_optimization['adjustment_reason'])

            # Record for adaptive learning
            recommendation_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'recommendation': recommendation,
                'confidence': confidence_score,
                'adaptive_threshold': adaptive_threshold,
                'entry_price': entry_price,
                'position_size': position_size,
                'market_regime': market_regime,
                'market_conditions': {
                    'price': float(current_price),
                    'volume_ratio': volume_ratio,
                    'volatility': volatility
                },
                'analysis_factors': analysis_factors,
                'component_scores': {
                    'technical': tech_score,
                    'volume': volume_score,
                    'structure': structure_score,
                    'risk': risk_score,
                    'momentum': momentum_score
                }
            }
            await self._record_recommendation(recommendation_record)

            reasoning = "; ".join(analysis_factors[:5]) if analysis_factors else "No strong buy signals detected"

            return {
                'recommendation': recommendation,
                'confidence': confidence_score,
                'reason': reasoning,
                'entry_price': entry_price,
                'position_size': position_size,
                'market_regime': market_regime,
                'adaptive_threshold': adaptive_threshold,
                'analysis': {
                    'technical_score': tech_score,
                    'volume_score': volume_score,
                    'structure_score': structure_score,
                    'risk_score': risk_score,
                    'momentum_score': momentum_score,
                    'regime_weight': regime_weight,
                    'detailed_factors': analysis_factors
                }
            }

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Enhanced analysis error for {symbol}: {e}")
            return {
                'recommendation': 'SKIP',
                'confidence': 0.0,
                'reason': f"Enhanced analysis error: {str(e)}",
                'entry_price': 0,
                'position_size': 0
            }

    async def _analyze_technical_indicators(self, market_data: Dict[str, Any]) -> float:
        """Analyze technical indicators for buy signals"""
        try:
            score = 0.0
            factors = 0

            # RSI Analysis
            rsi = market_data.get('rsi', 50)
            if rsi < self.rsi_oversold:
                score += 0.8  # Strong oversold signal
                factors += 1
            elif rsi < 45:
                score += 0.4  # Mild oversold
                factors += 1
            elif rsi > self.rsi_overbought:
                score -= 0.3  # Overbought penalty
                factors += 1

            # Moving Average Analysis
            price = market_data.get('price', 0)
            ma_20 = market_data.get('ma_20', price)
            ma_50 = market_data.get('ma_50', price)

            if price > ma_20 > ma_50:  # Bullish alignment
                score += 0.6
                factors += 1
            elif price > ma_20:  # Above short-term MA
                score += 0.3
                factors += 1

            # MACD Analysis
            macd = market_data.get('macd', 0)
            macd_signal = market_data.get('macd_signal', 0)
            if macd > macd_signal and macd < 0:  # Bullish divergence
                score += 0.7
                factors += 1
            elif macd > macd_signal:  # Bullish momentum
                score += 0.4
                factors += 1

            # Bollinger Bands
            bb_lower = market_data.get('bb_lower', 0)
            bb_upper = market_data.get('bb_upper', 0)
            if bb_lower > 0 and price <= bb_lower * 1.01:  # Near lower band
                score += 0.5
                factors += 1

            return score / max(factors, 1)

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Error in technical analysis: {e}")
            return 0.0

    def _analyze_volume_patterns(self, volume_ratio: float, current_volume: float) -> float:
        """Analyze volume patterns for buy signals"""
        try:
            score = 0.0

            # Volume increase analysis
            if volume_ratio >= 2.0:  # 100%+ increase
                score += 0.8
            elif volume_ratio >= self.min_volume_increase:  # 20%+ increase
                score += 0.5
            elif volume_ratio >= 1.0:  # Maintained volume
                score += 0.2
            else:  # Decreasing volume
                score -= 0.2

            # Absolute volume check
            if current_volume > 1000000:  # High absolute volume
                score += 0.2
            elif current_volume > 100000:  # Moderate volume
                score += 0.1

            return min(max(score, 0.0), 1.0)

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Error in volume analysis: {e}")
            return 0.0

    async def _analyze_market_structure(self, symbol: str, current_price: Decimal,
                                      market_data: Dict[str, Any]) -> float:
        """Analyze market structure for optimal entry"""
        try:
            score = 0.5  # Neutral starting point

            # Support/Resistance Analysis
            support_level = market_data.get('support_level', 0)
            resistance_level = market_data.get('resistance_level', 0)

            if support_level > 0:
                distance_from_support = abs(float(current_price) - support_level) / support_level
                if distance_from_support <= self.support_resistance_margin:
                    score += 0.4  # Near support
                elif distance_from_support <= 0.02:  # Within 2%
                    score += 0.2

            # Trend Analysis
            trend_direction = market_data.get('trend', 'neutral')
            if trend_direction == 'bullish':
                score += 0.3
            elif trend_direction == 'bearish':
                score -= 0.2

            # Market volatility preference
            volatility = market_data.get('volatility', 0.02)
            if 0.01 <= volatility <= 0.05:  # Optimal volatility range
                score += 0.2
            elif volatility > 0.1:  # Too volatile
                score -= 0.3

            return min(max(score, 0.0), 1.0)

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Error in market structure analysis: {e}")
            return 0.5

    def _assess_entry_risk(self, portfolio_state: Dict[str, Any], symbol: str,
                          current_price: Decimal) -> float:
        """Assess risk factors for entry"""
        try:
            score = 0.5  # Neutral risk

            # Portfolio diversification
            current_positions = portfolio_state.get('positions', {})
            if symbol not in current_positions:
                score += 0.3  # New position adds diversification

            # Available capital ratio
            available_ratio = portfolio_state.get('available_ratio', 0.5)
            if available_ratio > 0.8:  # High available capital
                score += 0.3
            elif available_ratio > 0.5:  # Moderate capital
                score += 0.1
            elif available_ratio < 0.2:  # Low capital
                score -= 0.3

            # Current portfolio performance
            portfolio_pnl = portfolio_state.get('unrealized_pnl_pct', 0)
            if portfolio_pnl > 0.05:  # Portfolio up 5%+
                score += 0.2
            elif portfolio_pnl < -0.1:  # Portfolio down 10%+
                score -= 0.2

            return min(max(score, 0.0), 1.0)

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Error in risk assessment: {e}")
            return 0.5

    def _analyze_price_momentum(self, market_data: Dict[str, Any]) -> float:
        """Analyze price momentum indicators"""
        try:
            score = 0.0

            # Price change analysis
            price_change_1h = market_data.get('price_change_1h', 0)
            price_change_24h = market_data.get('price_change_24h', 0)

            # Short-term momentum
            if 0 < price_change_1h <= 0.02:  # 0-2% positive
                score += 0.4
            elif price_change_1h > 0.02:  # >2% might be overextended
                score += 0.2
            elif price_change_1h < -0.03:  # Oversold
                score += 0.3

            # Medium-term momentum
            if 0 < price_change_24h <= 0.05:  # 0-5% positive
                score += 0.3
            elif price_change_24h < -0.05:  # Potential reversal
                score += 0.2

            # Momentum acceleration
            momentum_acceleration = market_data.get('momentum_acceleration', 0)
            if momentum_acceleration > 0:
                score += 0.3

            return min(score, 1.0)

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Error in momentum analysis: {e}")
            return 0.0

    async def _optimize_entry_price(self, current_price: Decimal, market_data: Dict[str, Any]) -> float:
        """Optimize entry price based on market microstructure"""
        try:
            # Start with current price
            optimized_price = float(current_price)

            # Bid-ask spread analysis
            bid = market_data.get('bid', optimized_price)
            ask = market_data.get('ask', optimized_price)
            spread = ask - bid if ask > bid else 0

            # If spread is reasonable, try to get better entry
            if spread > 0 and spread / optimized_price < 0.001:  # <0.1% spread
                # Target price slightly above bid
                optimized_price = bid + (spread * 0.3)

            # Support level adjustment
            support_level = market_data.get('support_level', 0)
            if support_level > 0 and abs(optimized_price - support_level) / support_level < 0.005:
                # If near support, target slightly above it
                optimized_price = support_level * 1.001

            return optimized_price

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Error optimizing entry price: {e}")
            return float(current_price)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of buy recommendations"""
        if self.success_metrics['total_recommendations'] > 0:
            accuracy = self.success_metrics['successful_entries'] / self.success_metrics['total_recommendations']
        else:
            accuracy = 0.0

        return {
            'total_recommendations': self.success_metrics['total_recommendations'],
            'successful_entries': self.success_metrics['successful_entries'],
            'accuracy_rate': accuracy,
            'recent_recommendations': self.buy_recommendations[-10:] if self.buy_recommendations else [],
            'optimal_confidence_threshold': self.success_metrics['best_confidence_threshold']
        }

    async def update_success_metrics(self, symbol: str, entry_price: float, success: bool):
        """Update success metrics based on trade outcome"""
        try:
            if success:
                self.success_metrics['successful_entries'] += 1

            # Adjust confidence threshold based on results
            if self.success_metrics['total_recommendations'] > 10:
                accuracy = self.success_metrics['successful_entries'] / self.success_metrics['total_recommendations']
                if accuracy > 0.7 and self.min_confidence_threshold > 0.5:
                    self.min_confidence_threshold -= 0.05  # Lower threshold for more trades
                elif accuracy < 0.4 and self.min_confidence_threshold < 0.8:
                    self.min_confidence_threshold += 0.05  # Raise threshold for quality

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Error updating success metrics: {e}")

    async def _detect_market_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect current market regime (bullish, bearish, neutral)"""
        try:
            # Simple regime detection based on multiple factors
            price_data = market_data.get('price_history', [])
            if len(price_data) < 20:
                return {'trend': 'neutral', 'strength': 0.5, 'confidence': 0.3}

            # Trend analysis over multiple timeframes
            short_trend = (price_data[-1] - price_data[-5]) / price_data[-5] if len(price_data) >= 5 else 0
            medium_trend = (price_data[-1] - price_data[-10]) / price_data[-10] if len(price_data) >= 10 else 0
            long_trend = (price_data[-1] - price_data[-20]) / price_data[-20] if len(price_data) >= 20 else 0

            # Moving average positioning
            ma_short = market_data.get('ma_5', price_data[-1])
            ma_medium = market_data.get('ma_20', price_data[-1])
            ma_long = market_data.get('ma_50', price_data[-1])

            current_price = price_data[-1]
            ma_alignment_score = 0

            if current_price > ma_short > ma_medium > ma_long:
                ma_alignment_score = 1.0  # Perfect bullish alignment
            elif current_price > ma_short > ma_medium:
                ma_alignment_score = 0.7  # Good bullish alignment
            elif current_price < ma_short < ma_medium < ma_long:
                ma_alignment_score = -1.0  # Perfect bearish alignment
            elif current_price < ma_short < ma_medium:
                ma_alignment_score = -0.7  # Good bearish alignment

            # Combine signals
            trend_score = (short_trend * 0.5 + medium_trend * 0.3 + long_trend * 0.2)
            total_score = (trend_score * 0.7 + ma_alignment_score * 0.3)

            # Determine regime
            if total_score > 0.02:  # 2% threshold
                trend = 'bullish'
                strength = min(total_score * 10, 1.0)
            elif total_score < -0.02:
                trend = 'bearish'
                strength = min(abs(total_score) * 10, 1.0)
            else:
                trend = 'neutral'
                strength = 0.5

            return {
                'trend': trend,
                'strength': strength,
                'confidence': min(len(price_data) / 50, 1.0),  # Higher confidence with more data
                'trend_score': trend_score,
                'ma_alignment': ma_alignment_score
            }

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Market regime detection error: {e}")
            return {'trend': 'neutral', 'strength': 0.5, 'confidence': 0.1}

    async def _calculate_adaptive_threshold(self, market_regime: Dict[str, Any], volatility: float) -> float:
        """Calculate adaptive confidence threshold based on market conditions"""
        try:
            base_threshold = self.base_confidence_threshold

            # Adjust for market regime
            if market_regime['trend'] == 'bullish' and market_regime['strength'] > 0.7:
                regime_adjustment = -0.1  # Lower threshold in strong bull market
            elif market_regime['trend'] == 'bearish':
                regime_adjustment = 0.15  # Higher threshold in bear market
            else:
                regime_adjustment = 0.05  # Slightly higher for neutral markets

            # Adjust for volatility
            if volatility > 0.06:  # High volatility
                volatility_adjustment = 0.1
            elif volatility < 0.02:  # Low volatility
                volatility_adjustment = -0.05
            else:
                volatility_adjustment = 0

            # Adjust based on recent performance
            if len(self.performance_buffer) > 10:
                recent_success = sum(self.performance_buffer[-10:]) / 10
                if recent_success < 0.4:  # Poor recent performance
                    performance_adjustment = 0.1
                elif recent_success > 0.7:  # Good recent performance
                    performance_adjustment = -0.05
                else:
                    performance_adjustment = 0
            else:
                performance_adjustment = 0

            adaptive_threshold = base_threshold + regime_adjustment + volatility_adjustment + performance_adjustment

            # Keep within reasonable bounds
            adaptive_threshold = max(0.4, min(0.85, adaptive_threshold))

            return adaptive_threshold

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Adaptive threshold calculation error: {e}")
            return self.base_confidence_threshold

    async def _analyze_technical_indicators_enhanced(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced technical analysis with multiple confirmations"""
        try:
            score = 0.0
            factors = []
            signal_count = 0

            # Enhanced RSI Analysis
            rsi = market_data.get('rsi', 50)
            if rsi <= self.rsi_extreme_oversold:
                score += 0.9
                factors.append(f'RSI extreme oversold: {rsi:.1f}')
                signal_count += 1
            elif rsi <= self.rsi_oversold:
                score += 0.7
                factors.append(f'RSI oversold: {rsi:.1f}')
                signal_count += 1
            elif rsi <= self.rsi_neutral_low:
                score += 0.4
                factors.append(f'RSI approaching oversold: {rsi:.1f}')
                signal_count += 1

            # Enhanced Moving Average Analysis
            price = market_data.get('price', 0)
            ma_5 = market_data.get('ma_5', price)
            ma_10 = market_data.get('ma_10', price)
            ma_20 = market_data.get('ma_20', price)
            ma_50 = market_data.get('ma_50', price)

            # MA alignment and momentum
            if ma_5 > ma_10 > ma_20 and price > ma_5:
                score += 0.8
                factors.append('Strong bullish MA alignment')
                signal_count += 1
            elif price > ma_10 > ma_20:
                score += 0.5
                factors.append('Moderate bullish MA trend')
                signal_count += 1

            # MACD Enhanced Analysis
            macd = market_data.get('macd', 0)
            macd_signal = market_data.get('macd_signal', 0)
            macd_histogram = market_data.get('macd_histogram', 0)

            if macd > macd_signal and macd < 0:  # Bullish crossover below zero
                score += 0.8
                factors.append('MACD bullish crossover below zero')
                signal_count += 1
            elif macd > macd_signal and macd_histogram > 0:
                score += 0.6
                factors.append('MACD bullish momentum')
                signal_count += 1

            # Bollinger Bands Analysis
            bb_lower = market_data.get('bb_lower', 0)
            bb_upper = market_data.get('bb_upper', 0)
            bb_middle = market_data.get('bb_middle', price)

            if bb_lower > 0 and price <= bb_lower * 1.005:  # Near lower band
                score += 0.7
                factors.append('Price near Bollinger lower band')
                signal_count += 1
            elif bb_middle > 0 and abs(price - bb_middle) / bb_middle < 0.01:  # Near middle
                score += 0.3
                factors.append('Price testing Bollinger middle band')
                signal_count += 1

            # Momentum confirmation
            price_history = market_data.get('price_history', [])
            if len(price_history) >= 5:
                short_momentum = (price_history[-1] - price_history[-3]) / price_history[-3]
                if short_momentum > self.momentum_threshold:
                    score += 0.5
                    factors.append(f'Positive short-term momentum: {short_momentum:.2%}')
                    signal_count += 1

            # Normalize score based on signal count
            if signal_count > 0:
                final_score = min(score / signal_count, 1.0)
            else:
                final_score = 0.0

            return {
                'score': final_score,
                'factors': factors,
                'signal_count': signal_count
            }

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Enhanced technical analysis error: {e}")
            return {'score': 0.0, 'factors': [], 'signal_count': 0}

    async def _analyze_volume_flow_enhanced(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced volume flow analysis with institutional detection"""
        try:
            score = 0.0
            factors = []

            volume = market_data.get('volume', 0)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            volume_history = market_data.get('volume_history', [])

            # Volume spike analysis
            if volume_ratio >= 2.5:  # Strong volume spike
                score += 0.8
                factors.append(f'Strong volume spike: {volume_ratio:.1f}x average')
            elif volume_ratio >= self.min_volume_increase:
                score += 0.5
                factors.append(f'Volume increase: {volume_ratio:.1f}x average')

            # Volume trend analysis
            if len(volume_history) >= 5:
                recent_avg = sum(volume_history[-3:]) / 3
                older_avg = sum(volume_history[-6:-3]) / 3

                if recent_avg > older_avg * 1.3:  # Increasing volume trend
                    score += 0.4
                    factors.append('Increasing volume trend')

            # Price-volume relationship
            price_change = market_data.get('price_change_24h', 0)
            if volume_ratio > 1.5 and price_change > 0.01:  # Volume with price increase
                score += 0.6
                factors.append('Volume supporting price increase')
            elif volume_ratio > 2.0 and price_change < -0.01:  # High volume on decline (potential reversal)
                score += 0.7
                factors.append('High volume on decline (potential reversal)')

            # Institutional flow detection (simplified)
            if volume > 1000000 and volume_ratio > 1.8:  # Large absolute volume with spike
                score += 0.3
                factors.append('Potential institutional activity')

            final_score = min(score, 1.0)

            return {
                'score': final_score,
                'factors': factors
            }

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Enhanced volume analysis error: {e}")
            return {'score': 0.0, 'factors': []}

    async def _analyze_market_structure_enhanced(self, symbol: str, current_price: Decimal,
                                               market_data: Dict[str, Any], market_regime: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced market structure analysis with regime awareness"""
        try:
            score = 0.5  # Neutral starting point
            factors = []

            # Market regime contribution
            if market_regime['trend'] == 'bullish' and market_regime['strength'] > 0.6:
                score += 0.4
                factors.append(f"Strong bullish regime (strength: {market_regime['strength']:.2f})")
            elif market_regime['trend'] == 'neutral':
                score += 0.1
                factors.append('Neutral market regime')

            # Support/Resistance Analysis
            support_level = market_data.get('support_level', 0)
            resistance_level = market_data.get('resistance_level', 0)

            if support_level > 0:
                distance_from_support = abs(float(current_price) - support_level) / support_level
                if distance_from_support <= self.support_resistance_margin:
                    score += 0.6
                    factors.append(f'Price at strong support: {support_level:.6f}')
                elif distance_from_support <= 0.02:  # Within 2%
                    score += 0.3
                    factors.append(f'Price near support: {support_level:.6f}')

            # Trend quality assessment
            volatility = market_data.get('volatility', 0.02)
            if volatility <= self.volatility_preference:
                score += 0.3
                factors.append(f'Optimal volatility: {volatility:.2%}')
            elif volatility > self.volatility_penalty_threshold:
                score -= 0.2
                factors.append(f'High volatility penalty: {volatility:.2%}')

            # Multi-timeframe confirmation
            confirmation_count = 0
            for period in self.trend_confirmation_periods:
                price_history = market_data.get('price_history', [])
                if len(price_history) >= period:
                    period_change = (price_history[-1] - price_history[-period]) / price_history[-period]
                    if period_change > 0.005:  # Positive over this timeframe
                        confirmation_count += 1

            if confirmation_count >= 2:  # At least 2 timeframes bullish
                score += 0.2
                factors.append(f'Multi-timeframe bullish confirmation ({confirmation_count}/3)')

            final_score = min(max(score, 0.0), 1.0)

            return {
                'score': final_score,
                'factors': factors
            }

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Enhanced market structure analysis error: {e}")
            return {'score': 0.5, 'factors': []}

    async def _assess_entry_risk_enhanced(self, portfolio_state: Dict[str, Any], symbol: str,
                                        current_price: Decimal, market_regime: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced risk assessment with regime awareness"""
        try:
            score = 0.5  # Neutral risk
            factors = []

            # Portfolio diversification
            current_positions = portfolio_state.get('positions', {})
            if symbol not in current_positions:
                score += 0.3
                factors.append('New position adds diversification')

            # Available capital assessment
            available_ratio = portfolio_state.get('available_ratio', 0.5)
            if available_ratio > 0.8:
                score += 0.3
                factors.append(f'High available capital: {available_ratio:.1%}')
            elif available_ratio > 0.5:
                score += 0.1
                factors.append(f'Adequate available capital: {available_ratio:.1%}')
            elif available_ratio < 0.2:
                score -= 0.3
                factors.append(f'Low available capital: {available_ratio:.1%}')

            # Market regime risk adjustment
            if market_regime['trend'] == 'bearish':
                score -= 0.2
                factors.append('Increased risk in bearish regime')
            elif market_regime['trend'] == 'bullish' and market_regime['strength'] > 0.7:
                score += 0.2
                factors.append('Reduced risk in strong bullish regime')

            # Portfolio performance consideration
            portfolio_pnl = portfolio_state.get('unrealized_pnl_pct', 0)
            if portfolio_pnl > 0.1:  # Portfolio up 10%+
                score += 0.2
                factors.append(f'Strong portfolio performance: {portfolio_pnl:.1%}')
            elif portfolio_pnl < -0.05:  # Portfolio down 5%+
                score -= 0.1
                factors.append(f'Portfolio drawdown concern: {portfolio_pnl:.1%}')

            # Correlation risk (simplified)
            position_count = len(current_positions)
            if position_count > 8:  # Too many positions
                score -= 0.2
                factors.append(f'High position count risk: {position_count}')
            elif position_count < 3:  # Good diversification opportunity
                score += 0.1
                factors.append(f'Good diversification opportunity: {position_count} positions')

            final_score = min(max(score, 0.0), 1.0)

            return {
                'score': final_score,
                'factors': factors
            }

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Enhanced risk assessment error: {e}")
            return {'score': 0.5, 'factors': []}

    async def _analyze_momentum_confluence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze momentum confluence across multiple timeframes"""
        try:
            score = 0.0
            factors = []
            momentum_count = 0

            price_history = market_data.get('price_history', [])

            if len(price_history) < 10:
                return {'score': 0.0, 'factors': ['Insufficient price history']}

            # Multiple timeframe momentum analysis
            timeframes = [3, 5, 7, 10]
            positive_momentum_count = 0

            for tf in timeframes:
                if len(price_history) >= tf:
                    momentum = (price_history[-1] - price_history[-tf]) / price_history[-tf]
                    if momentum > 0.003:  # 0.3% threshold
                        positive_momentum_count += 1
                        momentum_count += 1

                        if momentum > 0.02:  # Strong momentum (2%+)
                            score += 0.8
                            factors.append(f'Strong {tf}-period momentum: {momentum:.2%}')
                        elif momentum > 0.01:  # Moderate momentum (1%+)
                            score += 0.5
                            factors.append(f'Moderate {tf}-period momentum: {momentum:.2%}')
                        else:  # Weak positive momentum
                            score += 0.3
                            factors.append(f'Weak {tf}-period momentum: {momentum:.2%}')

            # Momentum acceleration
            if len(price_history) >= 7:
                short_momentum = (price_history[-1] - price_history[-3]) / price_history[-3]
                medium_momentum = (price_history[-3] - price_history[-7]) / price_history[-7]

                if short_momentum > medium_momentum and short_momentum > 0.005:
                    score += 0.4
                    factors.append('Momentum acceleration detected')
                    momentum_count += 1

            # Volume-price momentum relationship
            volume_ratio = market_data.get('volume_ratio', 1.0)
            price_change = market_data.get('price_change_1h', 0)

            if volume_ratio > 1.5 and price_change > 0.01:
                score += 0.3
                factors.append('Volume supporting price momentum')
                momentum_count += 1

            # Confluence bonus
            if positive_momentum_count >= 3:  # Most timeframes showing momentum
                score += 0.2
                factors.append(f'Multi-timeframe confluence: {positive_momentum_count}/4 bullish')

            # Normalize score
            if momentum_count > 0:
                final_score = min(score / max(momentum_count, 1), 1.0)
            else:
                final_score = 0.0

            return {
                'score': final_score,
                'factors': factors
            }

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Momentum confluence analysis error: {e}")
            return {'score': 0.0, 'factors': []}

    async def _calculate_optimal_position_size(self, confidence: float, market_regime: Dict[str, Any],
                                             volatility: float, portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimal position size based on multiple factors"""
        try:
            available_capital = portfolio_state.get('available_usdt', 0)

            if available_capital <= 0:
                return {'size': 0, 'reason': 'No available capital'}

            # Base position size from confidence
            base_size_pct = self.max_position_size_pct * confidence

            # Market regime adjustment
            if market_regime['trend'] == 'bullish' and market_regime['strength'] > 0.7:
                regime_multiplier = 1.3  # Larger positions in strong bull markets
            elif market_regime['trend'] == 'bearish':
                regime_multiplier = 0.6  # Smaller positions in bear markets
            else:
                regime_multiplier = 1.0

            # Volatility adjustment
            if volatility > 0.06:  # High volatility
                volatility_multiplier = 0.5
            elif volatility < 0.02:  # Low volatility
                volatility_multiplier = 1.2
            else:
                volatility_multiplier = max(0.8, self.volatility_preference / volatility)

            # Portfolio heat adjustment
            portfolio_utilization = 1 - portfolio_state.get('available_ratio', 0.5)
            if portfolio_utilization > 0.8:  # Portfolio heavily utilized
                heat_multiplier = 0.7
            elif portfolio_utilization < 0.3:  # Portfolio lightly utilized
                heat_multiplier = 1.2
            else:
                heat_multiplier = 1.0

            # Calculate final position size
            final_size_pct = base_size_pct * regime_multiplier * volatility_multiplier * heat_multiplier
            final_size_pct = min(final_size_pct, self.max_position_size_pct)

            position_size = available_capital * final_size_pct

            return {
                'size': position_size,
                'size_pct': final_size_pct,
                'base_size_pct': base_size_pct,
                'regime_multiplier': regime_multiplier,
                'volatility_multiplier': volatility_multiplier,
                'heat_multiplier': heat_multiplier
            }

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Position size calculation error: {e}")
            return {'size': 0, 'reason': f'Calculation error: {str(e)}'}

    async def _optimize_entry_price_enhanced(self, current_price: Decimal, market_data: Dict[str, Any],
                                           market_regime: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced entry price optimization with market microstructure analysis"""
        try:
            optimized_price = float(current_price)
            adjustment_reason = None

            # Bid-ask spread analysis
            bid = market_data.get('bid', optimized_price)
            ask = market_data.get('ask', optimized_price)
            spread = ask - bid if ask > bid else 0

            # Support level adjustment
            support_level = market_data.get('support_level', 0)
            if support_level > 0:
                distance_to_support = abs(optimized_price - support_level) / support_level
                if distance_to_support < 0.01:  # Very close to support
                    # Target slightly above support for better fill probability
                    optimized_price = support_level * 1.002
                    adjustment_reason = f'Adjusted to support level: {support_level:.6f}'

            # Market regime consideration
            if market_regime['trend'] == 'bullish' and market_regime['strength'] > 0.8:
                # In strong bull market, pay up slightly for better fill
                if spread > 0 and spread / optimized_price < 0.002:  # <0.2% spread
                    optimized_price = bid + (spread * 0.6)  # Closer to ask
                    adjustment_reason = 'Bull market adjustment for better fill'
            elif market_regime['trend'] == 'bearish':
                # In bear market, try for better entry
                if spread > 0 and spread / optimized_price < 0.001:
                    optimized_price = bid + (spread * 0.2)  # Closer to bid
                    adjustment_reason = 'Bear market adjustment for better entry'

            # Volatility-based adjustment
            volatility = market_data.get('volatility', 0.02)
            if volatility > 0.05:  # High volatility - use market order mentality
                if not adjustment_reason:
                    adjustment_reason = 'High volatility - market price recommended'

            return {
                'price': optimized_price,
                'adjustment_reason': adjustment_reason,
                'original_price': float(current_price),
                'spread': spread
            }

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Entry price optimization error: {e}")
            return {
                'price': float(current_price),
                'adjustment_reason': f'Optimization error: {str(e)}',
                'original_price': float(current_price)
            }

    async def _record_recommendation(self, record: Dict[str, Any]) -> None:
        """Record recommendation for performance tracking and learning"""
        try:
            self.buy_recommendations.append(record)
            self.success_metrics['total_recommendations'] += 1

            # Update regime-specific tracking
            regime = record['market_regime']['trend']
            if regime not in self.success_metrics['market_regime_performance']:
                self.success_metrics['market_regime_performance'][regime] = {
                    'count': 0, 'avg_confidence': 0.0
                }

            regime_perf = self.success_metrics['market_regime_performance'][regime]
            regime_perf['count'] += 1
            regime_perf['avg_confidence'] = (
                (regime_perf['avg_confidence'] * (regime_perf['count'] - 1) + record['confidence']) /
                regime_perf['count']
            )

            # Limit memory usage
            if len(self.buy_recommendations) > 1000:
                self.buy_recommendations = self.buy_recommendations[-1000:]

        except Exception as e:
            self.logger.error(f"[BUY_LOGIC] Error recording recommendation: {e}")
