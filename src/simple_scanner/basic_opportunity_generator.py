"""
Basic Opportunity Generator - Creates simple buy low, sell high opportunities
Integrates with learning system and portfolio intelligence for self-optimization
"""

import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional


class BasicOpportunityGenerator:
    """
    Generate basic trading opportunities based on simple price movements
    Self-learning and self-optimizing through integration with bot systems
    """

    def __init__(self, logger, bot_reference=None):
        self.logger = logger
        self.bot = bot_reference

        # Dynamic configuration that can be optimized by learning system
        self.config = {
            'cooldown_period': 30,  # Seconds between opportunities per symbol
            'price_history_size': 50,  # More history for better analysis
            'min_price_deviation': 0.005,  # 0.5% minimum deviation
            'confidence_base': 0.7,  # Base confidence level
            'volume_weight': 0.2,  # Weight for volume in confidence calculation
            'momentum_weight': 0.3,  # Weight for momentum in confidence calculation
            'max_opportunities_per_scan': 5  # Limit opportunities to prevent overtrading
        }

        # Use deque for efficient price history management
        self.price_history = {}
        self.volume_history = {}
        self.last_opportunities = {}
        self.opportunity_performance = {}  # Track performance for learning

        # Integration points
        self.learning_manager = None
        self.portfolio_intelligence = None
        self.performance_tracker = None

        # Performance metrics
        self.metrics = {
            'opportunities_generated': 0,
            'opportunities_executed': 0,
            'successful_opportunities': 0,
            'total_profit': 0.0,
            'last_optimization': time.time()
        }

        self._initialize_integrations()

    def _initialize_integrations(self):
        """Initialize connections to bot systems for self-learning"""
        try:
            if self.bot:
                if hasattr(self.bot, 'learning_manager'):
                    self.learning_manager = self.bot.learning_manager
                    self.logger.info("[SCANNER] Connected to learning manager")

                if hasattr(self.bot, 'portfolio_intelligence'):
                    self.portfolio_intelligence = self.bot.portfolio_intelligence
                    self.logger.info("[SCANNER] Connected to portfolio intelligence")

                if hasattr(self.bot, 'performance_tracker'):
                    self.performance_tracker = self.bot.performance_tracker
                    self.logger.info("[SCANNER] Connected to performance tracker")

        except Exception as e:
            self.logger.warning(f"[SCANNER] Failed to initialize integrations: {e}")

    def update_price_data(self, symbol: str, price: float, volume: float = 0) -> None:
        """Update price and volume history for a symbol"""
        try:
            # Initialize history if needed
            if symbol not in self.price_history:
                self.price_history[symbol] = deque(maxlen=self.config['price_history_size'])
                self.volume_history[symbol] = deque(maxlen=self.config['price_history_size'])

            # Add new data point
            self.price_history[symbol].append({
                'price': price,
                'timestamp': time.time()
            })

            if volume > 0:
                self.volume_history[symbol].append({
                    'volume': volume,
                    'timestamp': time.time()
                })

        except Exception as e:
            self.logger.error(f"[SCANNER] Error updating price data for {symbol}: {e}")

    def generate_opportunities(self, real_time_data: Dict[str, List[Dict]],
                             portfolio_state: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Generate trading opportunities with self-learning optimization
        
        Args:
            real_time_data: Current market data by symbol
            portfolio_state: Current portfolio positions (for sell opportunities)
            
        Returns:
            List of opportunity dictionaries
        """
        opportunities = []
        current_time = time.time()

        # Self-optimize if needed
        if current_time - self.metrics['last_optimization'] > 300:  # Every 5 minutes
            self._self_optimize()

        try:
            # Process each symbol
            for symbol, candles in real_time_data.items():
                if not self._validate_data(candles):
                    continue

                # Check cooldown
                if not self._check_cooldown(symbol, current_time):
                    continue

                # Extract market data
                market_data = self._extract_market_data(candles)
                if not market_data:
                    continue

                # Generate buy opportunities (buy low)
                buy_opportunity = self._evaluate_buy_opportunity(symbol, market_data)
                if buy_opportunity:
                    opportunities.append(buy_opportunity)
                    self.last_opportunities[symbol] = current_time
                    self.metrics['opportunities_generated'] += 1

                # Generate sell opportunities (sell high) - only if we have positions
                if portfolio_state and symbol in portfolio_state:
                    sell_opportunity = self._evaluate_sell_opportunity(
                        symbol, market_data, portfolio_state[symbol]
                    )
                    if sell_opportunity:
                        opportunities.append(sell_opportunity)
                        self.metrics['opportunities_generated'] += 1

                # Break if we have enough opportunities
                if len(opportunities) >= self.config['max_opportunities_per_scan']:
                    break

        except Exception as e:
            self.logger.error(f"[SCANNER] Error generating opportunities: {e}")

        # Record opportunities for learning
        if self.learning_manager and opportunities:
            self._record_opportunities(opportunities)

        # Sort by confidence and return best opportunities
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        return opportunities[:self.config['max_opportunities_per_scan']]

    def _validate_data(self, candles: List[Dict]) -> bool:
        """Validate we have enough data to analyze"""
        if not candles or len(candles) < 5:
            return False

        # Check for valid price data
        for candle in candles[-5:]:
            if not candle.get('close') or candle['close'] <= 0:
                return False

        return True

    def _check_cooldown(self, symbol: str, current_time: float) -> bool:
        """Check if symbol is in cooldown period"""
        if symbol in self.last_opportunities:
            time_since_last = current_time - self.last_opportunities[symbol]
            if time_since_last < self.config['cooldown_period']:
                return False
        return True

    def _extract_market_data(self, candles: List[Dict]) -> Optional[Dict]:
        """Extract and calculate market data from candles"""
        try:
            # Get recent prices and volumes
            recent_candles = candles[-20:] if len(candles) >= 20 else candles
            prices = [c['close'] for c in recent_candles]
            volumes = [c.get('volume', 0) for c in recent_candles]

            # Calculate metrics
            current_price = prices[-1]
            avg_price_short = sum(prices[-5:]) / 5
            avg_price_long = sum(prices) / len(prices)

            # Price momentum
            if len(prices) >= 10:
                momentum = (prices[-1] - prices[-10]) / prices[-10]
            else:
                momentum = 0

            # Volume analysis
            avg_volume = sum(volumes) / len(volumes) if volumes else 0
            volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1

            # Volatility (simple)
            price_changes = [abs(prices[i] - prices[i-1]) / prices[i-1]
                           for i in range(1, len(prices))]
            volatility = sum(price_changes) / len(price_changes) if price_changes else 0

            return {
                'current_price': current_price,
                'avg_price_short': avg_price_short,
                'avg_price_long': avg_price_long,
                'momentum': momentum,
                'volume_ratio': volume_ratio,
                'volatility': volatility,
                'price_position': (current_price - avg_price_long) / avg_price_long
            }

        except Exception as e:
            self.logger.error(f"[SCANNER] Error extracting market data: {e}")
            return None

    def _evaluate_buy_opportunity(self, symbol: str, market_data: Dict) -> Optional[Dict]:
        """
        Evaluate if current conditions present a buy opportunity
        Buy low logic with self-learning confidence adjustment
        """
        try:
            current_price = market_data['current_price']
            avg_price = market_data['avg_price_short']
            price_position = market_data['price_position']

            # Check if price is below average (buy low)
            price_deviation = (avg_price - current_price) / avg_price
            if price_deviation < self.config['min_price_deviation']:
                return None

            # Calculate dynamic confidence based on multiple factors
            confidence = self._calculate_confidence(market_data, 'buy')

            # Check minimum confidence threshold
            if confidence < 0.6:
                return None

            # Estimate profit potential
            potential_profit_pct = min(price_deviation * 100, 1.0)  # Cap at 1%

            # Create opportunity
            opportunity = {
                'symbol': symbol,
                'type': 'mean_reversion',
                'side': 'buy',
                'price': current_price,
                'confidence': confidence,
                'potential_profit_pct': potential_profit_pct,
                'reason': f'Price ${current_price:.4f} is {price_deviation*100:.2f}% below avg',
                'market_conditions': {
                    'momentum': market_data['momentum'],
                    'volume_ratio': market_data['volume_ratio'],
                    'volatility': market_data['volatility']
                },
                'timestamp': datetime.now().isoformat()
            }

            self.logger.info(f"[SCANNER] Buy opportunity: {symbol} at ${current_price:.4f} "
                           f"(confidence: {confidence:.2f})")

            return opportunity

        except Exception as e:
            self.logger.error(f"[SCANNER] Error evaluating buy opportunity: {e}")
            return None

    def _evaluate_sell_opportunity(self, symbol: str, market_data: Dict,
                                 position: Dict) -> Optional[Dict]:
        """
        Evaluate if we should sell an existing position (sell high)
        Only generate sell signals for positions we actually hold
        """
        try:
            current_price = market_data['current_price']
            position_price = position.get('avg_price', 0)
            position_size = position.get('size', 0)

            if position_price <= 0 or position_size <= 0:
                return None

            # Calculate profit percentage
            profit_pct = ((current_price - position_price) / position_price) * 100

            # Check if we've reached minimum profit target (0.5%)
            if profit_pct < 0.5:
                return None

            # Calculate confidence for selling
            confidence = self._calculate_confidence(market_data, 'sell', profit_pct)

            # Higher confidence threshold for selling profitable positions
            if confidence < 0.65:
                return None

            # Create sell opportunity
            opportunity = {
                'symbol': symbol,
                'type': 'take_profit',
                'side': 'sell',
                'price': current_price,
                'confidence': confidence,
                'potential_profit_pct': profit_pct,
                'reason': f'Position up {profit_pct:.2f}% from ${position_price:.4f}',
                'position_info': {
                    'size': position_size,
                    'entry_price': position_price,
                    'current_profit': profit_pct
                },
                'market_conditions': {
                    'momentum': market_data['momentum'],
                    'volume_ratio': market_data['volume_ratio'],
                    'volatility': market_data['volatility']
                },
                'timestamp': datetime.now().isoformat()
            }

            self.logger.info(f"[SCANNER] Sell opportunity: {symbol} at ${current_price:.4f} "
                           f"(profit: {profit_pct:.2f}%, confidence: {confidence:.2f})")

            return opportunity

        except Exception as e:
            self.logger.error(f"[SCANNER] Error evaluating sell opportunity: {e}")
            return None

    def _calculate_confidence(self, market_data: Dict, side: str,
                            profit_pct: float = 0) -> float:
        """
        Calculate dynamic confidence score based on market conditions
        Self-learning through performance tracking
        """
        try:
            base_confidence = self.config['confidence_base']

            # Adjust for momentum
            momentum = market_data['momentum']
            if side == 'buy' and momentum < 0:  # Negative momentum for buy
                base_confidence += self.config['momentum_weight'] * 0.1
            elif side == 'sell' and momentum > 0:  # Positive momentum for sell
                base_confidence += self.config['momentum_weight'] * 0.1

            # Adjust for volume
            volume_ratio = market_data['volume_ratio']
            if volume_ratio > 1.2:  # Higher than average volume
                base_confidence += self.config['volume_weight'] * 0.1

            # Adjust for volatility
            volatility = market_data['volatility']
            if volatility < 0.01:  # Low volatility
                base_confidence += 0.05
            elif volatility > 0.03:  # High volatility
                base_confidence -= 0.1

            # For sells, boost confidence if profit is good
            if side == 'sell' and profit_pct > 0.7:
                base_confidence += min(profit_pct * 0.1, 0.2)

            # Apply learning adjustments if available
            if self.learning_manager:
                learning_adjustment = self._get_learning_adjustment(market_data, side)
                base_confidence *= learning_adjustment

            # Ensure confidence is within bounds
            return max(0.5, min(0.95, base_confidence))

        except Exception as e:
            self.logger.error(f"[SCANNER] Error calculating confidence: {e}")
            return self.config['confidence_base']

    def _get_learning_adjustment(self, market_data: Dict, side: str) -> float:
        """Get confidence adjustment from learning system"""
        try:
            if not self.learning_manager:
                return 1.0

            # Create pattern key for learning lookup
            pattern_key = f"{side}_momentum_{market_data['momentum']:.2f}_vol_{market_data['volume_ratio']:.1f}"

            # Get historical performance for similar patterns
            if hasattr(self.learning_manager, 'get_pattern_performance'):
                performance = self.learning_manager.get_pattern_performance(pattern_key)
                if performance and performance.get('success_rate', 0) > 0:
                    # Adjust confidence based on historical success
                    return 0.8 + (performance['success_rate'] * 0.4)

            return 1.0

        except Exception as e:
            self.logger.debug(f"[SCANNER] Learning adjustment error: {e}")
            return 1.0

    def _record_opportunities(self, opportunities: List[Dict]):
        """Record opportunities for learning system"""
        try:
            if not self.learning_manager:
                return

            for opp in opportunities:
                self.learning_manager.record_event(
                    event_type='opportunity_generated',
                    data={
                        'symbol': opp['symbol'],
                        'side': opp['side'],
                        'confidence': opp['confidence'],
                        'market_conditions': opp.get('market_conditions', {}),
                        'timestamp': opp['timestamp']
                    }
                )

        except Exception as e:
            self.logger.debug(f"[SCANNER] Error recording opportunities: {e}")

    def _self_optimize(self):
        """
        Self-optimize parameters based on performance
        Part of the self-learning, self-optimizing infinity loop
        """
        try:
            self.logger.info("[SCANNER] Running self-optimization cycle")

            # Get performance data
            if self.performance_tracker:
                performance = self.performance_tracker.get_strategy_performance('opportunity_scanner')
                if performance:
                    success_rate = performance.get('success_rate', 0.5)

                    # Adjust parameters based on performance
                    if success_rate < 0.4:
                        # Poor performance - be more conservative
                        self.config['min_price_deviation'] *= 1.1
                        self.config['confidence_base'] *= 0.95
                        self.logger.info("[SCANNER] Adjusted parameters for more conservative scanning")

                    elif success_rate > 0.6:
                        # Good performance - can be slightly more aggressive
                        self.config['min_price_deviation'] *= 0.95
                        self.config['confidence_base'] *= 1.02
                        self.logger.info("[SCANNER] Adjusted parameters for more aggressive scanning")

            # Update optimization timestamp
            self.metrics['last_optimization'] = time.time()

            # Save optimization results
            if self.learning_manager:
                self.learning_manager.save_optimization_results(
                    'opportunity_scanner',
                    self.config,
                    self.metrics
                )

        except Exception as e:
            self.logger.error(f"[SCANNER] Self-optimization error: {e}")

    def update_opportunity_result(self, opportunity_id: str, result: Dict):
        """
        Update the result of an opportunity for learning
        Called by the trading system after execution
        """
        try:
            if opportunity_id in self.opportunity_performance:
                self.opportunity_performance[opportunity_id].update(result)

                # Update metrics
                if result.get('executed'):
                    self.metrics['opportunities_executed'] += 1
                    if result.get('profitable'):
                        self.metrics['successful_opportunities'] += 1
                        self.metrics['total_profit'] += result.get('profit', 0)

                # Trigger learning update
                if self.learning_manager:
                    self.learning_manager.update_pattern_performance(
                        opportunity_id,
                        self.opportunity_performance[opportunity_id]
                    )

        except Exception as e:
            self.logger.error(f"[SCANNER] Error updating opportunity result: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring"""
        try:
            success_rate = (self.metrics['successful_opportunities'] /
                          self.metrics['opportunities_executed']) if self.metrics['opportunities_executed'] > 0 else 0

            return {
                'opportunities_generated': self.metrics['opportunities_generated'],
                'opportunities_executed': self.metrics['opportunities_executed'],
                'success_rate': success_rate,
                'total_profit': self.metrics['total_profit'],
                'avg_profit_per_opportunity': (self.metrics['total_profit'] /
                                              self.metrics['successful_opportunities'])
                                              if self.metrics['successful_opportunities'] > 0 else 0,
                'last_optimization': datetime.fromtimestamp(self.metrics['last_optimization']).isoformat(),
                'current_config': self.config
            }

        except Exception as e:
            self.logger.error(f"[SCANNER] Error getting performance summary: {e}")
            return {}
