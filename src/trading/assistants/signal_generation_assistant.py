"""
Signal Generation Assistant - Trading signal generation helper
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List


class SignalType(Enum):
    """Types of trading signals"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class SignalGenerationAssistant:
    """Assistant for generating trading signals"""

    def __init__(self, manager_or_config):
        # Handle both manager object and config dict
        if hasattr(manager_or_config, 'config'):
            self.manager = manager_or_config
            self.config = manager_or_config.config
        else:
            self.manager = None
            self.config = manager_or_config
        self.logger = logging.getLogger(__name__)

    def generate_momentum_signal(self, price_data: List[float], volume_data: List[float] = None) -> Dict[str, Any]:
        """Generate momentum-based trading signal"""
        try:
            if len(price_data) < 3:
                return {
                    'signal': SignalType.HOLD,
                    'strength': 0.0,
                    'confidence': 0.0,
                    'reason': 'insufficient_data'
                }

            # Simple momentum calculation
            recent_prices = price_data[-3:]
            if recent_prices[-1] > recent_prices[-2] > recent_prices[-3]:
                signal = SignalType.BUY
                strength = min((recent_prices[-1] - recent_prices[-3]) / recent_prices[-3], 1.0)
                confidence = 0.7
                reason = 'upward_momentum'
            elif recent_prices[-1] < recent_prices[-2] < recent_prices[-3]:
                signal = SignalType.SELL
                strength = min((recent_prices[-3] - recent_prices[-1]) / recent_prices[-3], 1.0)
                confidence = 0.7
                reason = 'downward_momentum'
            else:
                signal = SignalType.HOLD
                strength = 0.0
                confidence = 0.5
                reason = 'sideways_movement'

            return {
                'signal': signal,
                'strength': float(strength),
                'confidence': float(confidence),
                'reason': reason
            }

        except Exception as e:
            self.logger.error(f"Momentum signal generation error: {e}")
            return {
                'signal': SignalType.HOLD,
                'strength': 0.0,
                'confidence': 0.0,
                'reason': 'error'
            }

    def generate_reversal_signal(self, price_data: List[float], rsi: float = 50.0) -> Dict[str, Any]:
        """Generate mean reversion signal"""
        try:
            if len(price_data) < 5:
                return {
                    'signal': SignalType.HOLD,
                    'strength': 0.0,
                    'confidence': 0.0,
                    'reason': 'insufficient_data'
                }

            # Check for oversold/overbought conditions
            if rsi < 30:
                signal = SignalType.BUY
                strength = (30 - rsi) / 30
                confidence = 0.6
                reason = 'oversold_rsi'
            elif rsi > 70:
                signal = SignalType.SELL
                strength = (rsi - 70) / 30
                confidence = 0.6
                reason = 'overbought_rsi'
            else:
                signal = SignalType.HOLD
                strength = 0.0
                confidence = 0.5
                reason = 'neutral_rsi'

            return {
                'signal': signal,
                'strength': float(strength),
                'confidence': float(confidence),
                'reason': reason
            }

        except Exception as e:
            self.logger.error(f"Reversal signal generation error: {e}")
            return {
                'signal': SignalType.HOLD,
                'strength': 0.0,
                'confidence': 0.0,
                'reason': 'error'
            }

    def combine_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple signals into a consensus signal"""
        try:
            if not signals:
                return {
                    'signal': SignalType.HOLD,
                    'strength': 0.0,
                    'confidence': 0.0,
                    'reason': 'no_signals'
                }

            # Simple voting mechanism
            signal_votes = {}
            total_strength = 0.0
            total_confidence = 0.0

            for signal_data in signals:
                signal = signal_data['signal']
                strength = signal_data['strength']
                confidence = signal_data['confidence']

                if signal not in signal_votes:
                    signal_votes[signal] = {'count': 0, 'total_strength': 0.0, 'total_confidence': 0.0}

                signal_votes[signal]['count'] += 1
                signal_votes[signal]['total_strength'] += strength
                signal_votes[signal]['total_confidence'] += confidence

                total_strength += strength
                total_confidence += confidence

            # Find consensus signal
            max_votes = max(signal_votes.values(), key=lambda x: x['count'])
            consensus_signal = next(k for k, v in signal_votes.items() if v == max_votes)

            avg_strength = total_strength / len(signals)
            avg_confidence = total_confidence / len(signals)

            return {
                'signal': consensus_signal,
                'strength': float(avg_strength),
                'confidence': float(avg_confidence),
                'reason': 'consensus_signal'
            }

        except Exception as e:
            self.logger.error(f"Signal combination error: {e}")
            return {
                'signal': SignalType.HOLD,
                'strength': 0.0,
                'confidence': 0.0,
                'reason': 'error'
            }

    def generate_buy_signals_sync(self, symbols: List[str] = None) -> List[Dict[str, Any]]:
        """Generate buy signals for given symbols (synchronous version)"""
        try:
            # Mock implementation for compatibility
            # In a real implementation, this would analyze market data for each symbol
            self.logger.debug(f"Generating buy signals for {len(symbols) if symbols else 0} symbols")

            signals = []
            if symbols:
                for symbol in symbols:
                    # Simple mock signal generation
                    signal = {
                        'symbol': symbol,
                        'signal': SignalType.HOLD,
                        'strength': 0.5,
                        'confidence': 0.6,
                        'reason': 'mock_signal',
                        'timestamp': None
                    }
                    signals.append(signal)

            return signals

        except Exception as e:
            self.logger.error(f"Error generating buy signals: {e}")
            return []

    # ASYNC METHODS REQUIRED BY INFINITY TRADING MANAGER

    async def initialize(self):
        """Initialize the signal generation assistant"""
        try:
            self.logger.info("[SIGNAL_ASSISTANT] Initializing...")

            # Initialize signal generation parameters
            self.confidence_threshold = 0.25  # Optimized setting from user requirements
            self.position_size_base = 4.2     # Optimized $4.2 position size from user requirements
            self.priority_symbols = ['SHIB/USDT', 'MATIC/USDT', 'AI16Z/USDT', 'BERA/USDT']  # Low-priced USDT pairs
            self.position_size_multiplier = 1.0
            self.profit_target_multiplier = 1.0

            # Connect to data sources
            if self.manager and hasattr(self.manager, 'bot'):
                if hasattr(self.manager.bot, 'websocket_manager'):
                    self.websocket_manager = self.manager.bot.websocket_manager
                    self.logger.info("[SIGNAL_ASSISTANT] Connected to WebSocket data source")

                if hasattr(self.manager.bot, 'exchange'):
                    self.exchange = self.manager.bot.exchange
                    self.logger.info("[SIGNAL_ASSISTANT] Connected to exchange")

            self.logger.info(f"[SIGNAL_ASSISTANT] Initialized with confidence threshold: {self.confidence_threshold}, position size: ${self.position_size_base}")

        except Exception as e:
            self.logger.error(f"[SIGNAL_ASSISTANT] Initialization error: {e}")

    async def stop(self):
        """Stop the signal generation assistant"""
        try:
            self.logger.info("[SIGNAL_ASSISTANT] Stopping...")

            # Clean up any resources
            self.logger.info("[SIGNAL_ASSISTANT] Stopped successfully")

        except Exception as e:
            self.logger.error(f"[SIGNAL_ASSISTANT] Stop error: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of the signal generation assistant"""
        try:
            # Check data connections
            has_websocket = hasattr(self, 'websocket_manager') and self.websocket_manager is not None
            has_exchange = hasattr(self, 'exchange') and self.exchange is not None

            healthy = has_websocket or has_exchange

            return {
                'healthy': healthy,
                'websocket_connected': has_websocket,
                'exchange_connected': has_exchange,
                'confidence_threshold': getattr(self, 'confidence_threshold', 0.25),
                'position_size_base': getattr(self, 'position_size_base', 4.2),
                'timestamp': time.time()
            }

        except Exception as e:
            self.logger.error(f"[SIGNAL_ASSISTANT] Health check error: {e}")
            return {'healthy': False, 'error': str(e)}

    async def generate_buy_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate buy signals based on market data (async version)"""
        try:
            self.logger.debug("[SIGNAL_ASSISTANT] Generating buy signals from market data")

            signals = []

            if not market_data or not market_data.get('symbols'):
                self.logger.debug("[SIGNAL_ASSISTANT] No market data or symbols available")
                return signals

            symbols = market_data.get('symbols', [])
            prices = market_data.get('prices', {})
            volumes = market_data.get('volumes', {})

            # Prioritize low-priced USDT pairs
            priority_symbols = [s for s in symbols if s in self.priority_symbols]
            other_symbols = [s for s in symbols if s not in self.priority_symbols]

            # Process priority symbols first
            for symbol in priority_symbols + other_symbols[:5]:  # Limit total symbols
                try:
                    current_price = prices.get(symbol, 0)
                    volume = volumes.get(symbol, 0)

                    if current_price <= 0:
                        continue

                    # Get additional data from WebSocket if available
                    ticker_data = None
                    if hasattr(self, 'websocket_manager') and self.websocket_manager:
                        ticker_data = self.websocket_manager.get_ticker(symbol)

                    # Generate signal based on available data
                    signal_data = await self._analyze_symbol_for_buy(symbol, current_price, volume, ticker_data)

                    if signal_data and signal_data.get('confidence', 0) >= self.confidence_threshold:
                        # Calculate position size
                        position_size = self.position_size_base * self.position_size_multiplier

                        # Create complete signal
                        complete_signal = {
                            'symbol': symbol,
                            'type': 'buy',
                            'price': current_price,
                            'amount': position_size / current_price,  # Calculate amount based on position size
                            'position_size_usd': position_size,
                            'confidence': signal_data['confidence'],
                            'strength': signal_data.get('strength', 0.5),
                            'reason': signal_data.get('reason', 'analysis'),
                            'timestamp': time.time(),
                            'priority': symbol in self.priority_symbols
                        }

                        signals.append(complete_signal)
                        self.logger.info(f"[SIGNAL_ASSISTANT] Generated buy signal for {symbol}: ${position_size:.2f} @ ${current_price:.8f}")

                except Exception as symbol_error:
                    self.logger.warning(f"[SIGNAL_ASSISTANT] Error analyzing {symbol}: {symbol_error}")
                    continue

            # Sort by priority and confidence
            signals.sort(key=lambda s: (s['priority'], s['confidence']), reverse=True)

            self.logger.info(f"[SIGNAL_ASSISTANT] Generated {len(signals)} buy signals")
            return signals[:5]  # Return top 5 signals

        except Exception as e:
            self.logger.error(f"[SIGNAL_ASSISTANT] Error generating buy signals: {e}")
            return []

    async def _analyze_symbol_for_buy(self, symbol: str, price: float, volume: float, ticker_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze a symbol for buy opportunity"""
        try:
            # Basic analysis
            confidence = 0.0
            strength = 0.0
            reasons = []

            # Price analysis (favor low-priced coins as per user requirements)
            if price < 1.0:  # Low-priced coins
                confidence += 0.15
                strength += 0.1
                reasons.append('low_price_advantage')

            # Volume analysis
            if volume > 100000:  # High volume
                confidence += 0.1
                strength += 0.1
                reasons.append('high_volume')

            # Technical analysis if ticker data available
            if ticker_data:
                bid = ticker_data.get('bid', 0)
                ask = ticker_data.get('ask', 0)
                last = ticker_data.get('last', 0)

                if bid > 0 and ask > 0 and last > 0:
                    # Spread analysis
                    spread = (ask - bid) / bid
                    if spread < 0.002:  # Tight spread
                        confidence += 0.1
                        strength += 0.1
                        reasons.append('tight_spread')

                    # Price position
                    mid_price = (bid + ask) / 2
                    if last <= mid_price:  # Price at or below mid
                        confidence += 0.05
                        strength += 0.05
                        reasons.append('favorable_price_position')

            # Priority symbol bonus
            if symbol in self.priority_symbols:
                confidence += 0.1
                strength += 0.1
                reasons.append('priority_symbol')

            # Ensure minimum confidence threshold
            if confidence < 0.25:
                return None

            return {
                'confidence': min(confidence, 1.0),
                'strength': min(strength, 1.0),
                'reason': ' + '.join(reasons) if reasons else 'basic_analysis'
            }

        except Exception as e:
            self.logger.error(f"[SIGNAL_ASSISTANT] Symbol analysis error for {symbol}: {e}")
            return None

    # OPTIONAL OPTIMIZATION METHODS

    async def adjust_confidence_threshold(self, multiplier: float):
        """Adjust confidence threshold by multiplier"""
        try:
            old_threshold = self.confidence_threshold
            self.confidence_threshold = max(0.1, min(1.0, self.confidence_threshold * multiplier))
            self.logger.info(f"[SIGNAL_ASSISTANT] Adjusted confidence threshold: {old_threshold:.3f} -> {self.confidence_threshold:.3f}")

        except Exception as e:
            self.logger.error(f"[SIGNAL_ASSISTANT] Error adjusting confidence threshold: {e}")

    async def adjust_position_sizing(self, multiplier: float):
        """Adjust position sizing by multiplier"""
        try:
            old_multiplier = self.position_size_multiplier
            self.position_size_multiplier = max(0.1, min(5.0, self.position_size_multiplier * multiplier))
            self.logger.info(f"[SIGNAL_ASSISTANT] Adjusted position size multiplier: {old_multiplier:.3f} -> {self.position_size_multiplier:.3f}")

        except Exception as e:
            self.logger.error(f"[SIGNAL_ASSISTANT] Error adjusting position sizing: {e}")

    async def adjust_profit_targets(self, multiplier: float):
        """Adjust profit targets by multiplier"""
        try:
            old_multiplier = self.profit_target_multiplier
            self.profit_target_multiplier = max(0.5, min(3.0, self.profit_target_multiplier * multiplier))
            self.logger.info(f"[SIGNAL_ASSISTANT] Adjusted profit target multiplier: {old_multiplier:.3f} -> {self.profit_target_multiplier:.3f}")

        except Exception as e:
            self.logger.error(f"[SIGNAL_ASSISTANT] Error adjusting profit targets: {e}")

    async def set_priority_symbols(self, symbols: List[str]):
        """Set priority symbols for signal generation"""
        try:
            self.priority_symbols = symbols[:10]  # Limit to 10 priority symbols
            self.logger.info(f"[SIGNAL_ASSISTANT] Updated priority symbols: {self.priority_symbols}")

        except Exception as e:
            self.logger.error(f"[SIGNAL_ASSISTANT] Error setting priority symbols: {e}")
