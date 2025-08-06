"""
Neural Pattern Engine
=====================

Advanced pattern recognition engine using neural networks for trading optimization.
Implements deep learning for market pattern recognition and strategy optimization.
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PatternFeatures:
    """Features extracted from trading patterns"""
    technical_indicators: Dict[str, float]
    market_conditions: Dict[str, Any]
    volume_profile: Dict[str, float]
    price_action: Dict[str, float]
    time_features: Dict[str, float]
    sentiment_indicators: Dict[str, float]

    def to_vector(self) -> np.ndarray:
        """Convert features to numerical vector for ML processing"""
        vector = []

        # Technical indicators
        tech_values = list(self.technical_indicators.values())
        vector.extend(tech_values)

        # Market conditions (encoded)
        trend = self.market_conditions.get('trend', 'neutral')
        trend_encoding = {'bullish': 1, 'neutral': 0, 'bearish': -1}.get(trend, 0)
        vector.append(trend_encoding)

        volatility = self.market_conditions.get('volatility', 0.02)
        vector.append(volatility)

        # Volume profile
        volume_values = list(self.volume_profile.values())
        vector.extend(volume_values)

        # Price action
        price_values = list(self.price_action.values())
        vector.extend(price_values)

        # Time features
        time_values = list(self.time_features.values())
        vector.extend(time_values)

        # Sentiment indicators
        sentiment_values = list(self.sentiment_indicators.values())
        vector.extend(sentiment_values)

        return np.array(vector, dtype=np.float32)


class SimpleNeuralNetwork:
    """Simplified neural network for pattern recognition"""

    def __init__(self, input_size: int, hidden_sizes: List[int], output_size: int):
        """Initialize neural network with specified architecture"""
        self.input_size = input_size
        self.hidden_sizes = hidden_sizes
        self.output_size = output_size

        # Initialize weights and biases
        self.weights = []
        self.biases = []

        # Input to first hidden layer
        prev_size = input_size
        for hidden_size in hidden_sizes:
            # Xavier initialization
            w = np.random.randn(prev_size, hidden_size) * np.sqrt(2.0 / prev_size)
            b = np.zeros((1, hidden_size))

            self.weights.append(w)
            self.biases.append(b)
            prev_size = hidden_size

        # Last hidden to output
        w = np.random.randn(prev_size, output_size) * np.sqrt(2.0 / prev_size)
        b = np.zeros((1, output_size))

        self.weights.append(w)
        self.biases.append(b)

        self.learning_rate = 0.001
        self.training_history = []

    def relu(self, x: np.ndarray) -> np.ndarray:
        """ReLU activation function"""
        return np.maximum(0, x)

    def relu_derivative(self, x: np.ndarray) -> np.ndarray:
        """ReLU derivative"""
        return (x > 0).astype(float)

    def sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Sigmoid activation function"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, List[np.ndarray]]:
        """Forward pass through the network"""
        activations = [x]

        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            z = np.dot(activations[-1], w) + b

            if i < len(self.weights) - 1:  # Hidden layers
                a = self.relu(z)
            else:  # Output layer
                a = self.sigmoid(z)

            activations.append(a)

        return activations[-1], activations

    def backward(self, x: np.ndarray, y: np.ndarray, activations: List[np.ndarray]) -> float:
        """Backward pass and weight updates"""
        m = x.shape[0]

        # Calculate loss
        predictions = activations[-1]
        loss = -np.mean(y * np.log(predictions + 1e-8) + (1 - y) * np.log(1 - predictions + 1e-8))

        # Backward pass
        deltas = [predictions - y]

        for i in range(len(self.weights) - 1, -1, -1):
            if i > 0:
                delta = np.dot(deltas[0], self.weights[i].T) * self.relu_derivative(activations[i])
                deltas.insert(0, delta)

        # Update weights and biases
        for i in range(len(self.weights)):
            dw = np.dot(activations[i].T, deltas[i]) / m
            db = np.mean(deltas[i], axis=0, keepdims=True)

            self.weights[i] -= self.learning_rate * dw
            self.biases[i] -= self.learning_rate * db

        return loss

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100) -> List[float]:
        """Train the neural network"""
        losses = []

        for epoch in range(epochs):
            predictions, activations = self.forward(X)
            loss = self.backward(X, y, activations)
            losses.append(loss)

            if epoch % 10 == 0:
                logger.debug(f"[NEURAL_ENGINE] Epoch {epoch}, Loss: {loss:.4f}")

        self.training_history.extend(losses)
        return losses

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Make predictions"""
        predictions, _ = self.forward(x)
        return predictions


class PatternRecognitionEngine:
    """Advanced pattern recognition using neural networks"""

    def __init__(self):
        """Initialize pattern recognition engine"""
        self.networks = {}
        self.pattern_database = defaultdict(list)
        self.feature_extractors = {}
        self.training_data = defaultdict(list)

        # Pattern types
        self.pattern_types = [
            'entry_patterns',
            'exit_patterns',
            'market_regime_patterns',
            'risk_patterns',
            'optimization_patterns'
        ]

        # Initialize neural networks for each pattern type
        for pattern_type in self.pattern_types:
            self.networks[pattern_type] = SimpleNeuralNetwork(
                input_size=20,  # Will adjust based on actual features
                hidden_sizes=[64, 32, 16],
                output_size=1
            )

        logger.info("[NEURAL_ENGINE] Pattern recognition engine initialized")

    async def extract_features(self, market_data: Dict[str, Any],
                             trading_context: Dict[str, Any]) -> PatternFeatures:
        """Extract comprehensive features from market data"""
        try:
            # Technical indicators
            technical_indicators = {
                'rsi': market_data.get('rsi', 50.0),
                'macd': market_data.get('macd', 0.0),
                'macd_signal': market_data.get('macd_signal', 0.0),
                'bb_upper': market_data.get('bb_upper', 0.0),
                'bb_lower': market_data.get('bb_lower', 0.0),
                'ma_20': market_data.get('ma_20', 0.0),
                'ma_50': market_data.get('ma_50', 0.0)
            }

            # Market conditions
            market_conditions = {
                'trend': market_data.get('trend', 'neutral'),
                'volatility': market_data.get('volatility', 0.02),
                'volume_ratio': market_data.get('volume_ratio', 1.0),
                'market_phase': trading_context.get('market_phase', 'normal')
            }

            # Volume profile
            volume_profile = {
                'current_volume': market_data.get('volume', 0.0),
                'avg_volume': market_data.get('avg_volume', 0.0),
                'volume_momentum': market_data.get('volume_momentum', 0.0)
            }

            # Price action
            price = market_data.get('price', 0.0)
            price_action = {
                'price_change_1h': market_data.get('price_change_1h', 0.0),
                'price_change_24h': market_data.get('price_change_24h', 0.0),
                'price_momentum': market_data.get('price_momentum', 0.0),
                'support_distance': self._calculate_support_distance(price, market_data),
                'resistance_distance': self._calculate_resistance_distance(price, market_data)
            }

            # Time features
            now = datetime.now()
            time_features = {
                'hour_of_day': now.hour / 24.0,
                'day_of_week': now.weekday() / 7.0,
                'time_since_market_open': self._time_since_market_open() / 24.0
            }

            # Sentiment indicators (placeholder for now)
            sentiment_indicators = {
                'market_sentiment': 0.5,  # Neutral
                'fear_greed_index': 0.5,  # Neutral
                'social_sentiment': 0.5   # Neutral
            }

            return PatternFeatures(
                technical_indicators=technical_indicators,
                market_conditions=market_conditions,
                volume_profile=volume_profile,
                price_action=price_action,
                time_features=time_features,
                sentiment_indicators=sentiment_indicators
            )

        except Exception as e:
            logger.error(f"[NEURAL_ENGINE] Error extracting features: {e}")
            return PatternFeatures({}, {}, {}, {}, {}, {})

    def _calculate_support_distance(self, price: float, market_data: Dict[str, Any]) -> float:
        """Calculate distance to support level"""
        support_level = market_data.get('support_level', price * 0.98)
        if support_level > 0:
            return (price - support_level) / support_level
        return 0.0

    def _calculate_resistance_distance(self, price: float, market_data: Dict[str, Any]) -> float:
        """Calculate distance to resistance level"""
        resistance_level = market_data.get('resistance_level', price * 1.02)
        if resistance_level > 0:
            return (resistance_level - price) / resistance_level
        return 0.0

    def _time_since_market_open(self) -> float:
        """Calculate hours since market open (placeholder)"""
        # For crypto, markets are always open, so this could be time since UTC midnight
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return (now - midnight).total_seconds() / 3600.0

    async def recognize_entry_pattern(self, features: PatternFeatures,
                                    historical_outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Recognize entry patterns using neural network"""
        try:
            pattern_type = 'entry_patterns'
            network = self.networks[pattern_type]

            # Prepare input
            feature_vector = features.to_vector()

            # Ensure correct input size
            if len(feature_vector) != network.input_size:
                # Resize network if needed
                network = SimpleNeuralNetwork(
                    input_size=len(feature_vector),
                    hidden_sizes=[64, 32, 16],
                    output_size=1
                )
                self.networks[pattern_type] = network

            # Make prediction
            input_data = feature_vector.reshape(1, -1)
            prediction = network.predict(input_data)[0, 0]

            # Interpret prediction
            confidence = float(prediction)
            recommendation = 'BUY' if confidence > 0.6 else 'HOLD'

            # Add pattern analysis
            pattern_analysis = await self._analyze_pattern_components(features, pattern_type)

            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'pattern_type': 'entry_pattern',
                'neural_score': prediction,
                'pattern_analysis': pattern_analysis,
                'feature_importance': await self._calculate_feature_importance(features, network)
            }

        except Exception as e:
            logger.error(f"[NEURAL_ENGINE] Error recognizing entry pattern: {e}")
            return {
                'recommendation': 'HOLD',
                'confidence': 0.5,
                'pattern_type': 'entry_pattern',
                'error': str(e)
            }

    async def recognize_exit_pattern(self, features: PatternFeatures,
                                   position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Recognize exit patterns using neural network"""
        try:
            pattern_type = 'exit_patterns'
            network = self.networks[pattern_type]

            # Enhance features with position data
            enhanced_features = await self._enhance_features_with_position(features, position_data)
            feature_vector = enhanced_features.to_vector()

            # Ensure correct input size
            if len(feature_vector) != network.input_size:
                network = SimpleNeuralNetwork(
                    input_size=len(feature_vector),
                    hidden_sizes=[64, 32, 16],
                    output_size=1
                )
                self.networks[pattern_type] = network

            # Make prediction
            input_data = feature_vector.reshape(1, -1)
            prediction = network.predict(input_data)[0, 0]

            # Interpret prediction
            confidence = float(prediction)
            recommendation = 'SELL' if confidence > 0.7 else 'HOLD'

            # Calculate exit amount based on confidence and position
            exit_amount = await self._calculate_neural_exit_amount(
                confidence, position_data, enhanced_features
            )

            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'exit_amount': exit_amount,
                'pattern_type': 'exit_pattern',
                'neural_score': prediction,
                'reasoning': await self._generate_exit_reasoning(enhanced_features, confidence)
            }

        except Exception as e:
            logger.error(f"[NEURAL_ENGINE] Error recognizing exit pattern: {e}")
            return {
                'recommendation': 'HOLD',
                'confidence': 0.5,
                'exit_amount': 0,
                'error': str(e)
            }

    async def detect_market_regime(self, features: PatternFeatures,
                                 historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect current market regime using neural patterns"""
        try:
            pattern_type = 'market_regime_patterns'
            network = self.networks[pattern_type]

            # Prepare regime detection features
            regime_features = await self._prepare_regime_features(features, historical_data)
            feature_vector = regime_features.to_vector()

            # Ensure correct input size
            if len(feature_vector) != network.input_size:
                network = SimpleNeuralNetwork(
                    input_size=len(feature_vector),
                    hidden_sizes=[32, 16],
                    output_size=3  # bullish, neutral, bearish
                )
                self.networks[pattern_type] = network

            # Make prediction
            input_data = feature_vector.reshape(1, -1)
            predictions = network.predict(input_data)[0]

            # Interpret regime
            regime_names = ['bearish', 'neutral', 'bullish']
            regime_index = np.argmax(predictions)
            regime = regime_names[regime_index]
            confidence = float(predictions[regime_index])

            return {
                'regime': regime,
                'confidence': confidence,
                'regime_probabilities': {
                    'bearish': float(predictions[0]),
                    'neutral': float(predictions[1]),
                    'bullish': float(predictions[2])
                },
                'regime_strength': await self._calculate_regime_strength(regime_features),
                'transition_probability': await self._calculate_transition_probability(historical_data)
            }

        except Exception as e:
            logger.error(f"[NEURAL_ENGINE] Error detecting market regime: {e}")
            return {
                'regime': 'neutral',
                'confidence': 0.5,
                'error': str(e)
            }

    async def train_on_outcomes(self, pattern_type: str, features_list: List[PatternFeatures],
                              outcomes: List[float]) -> Dict[str, Any]:
        """Train neural network on historical outcomes"""
        try:
            if pattern_type not in self.networks:
                logger.error(f"[NEURAL_ENGINE] Unknown pattern type: {pattern_type}")
                return {'success': False, 'error': 'Unknown pattern type'}

            network = self.networks[pattern_type]

            # Prepare training data
            X = np.array([features.to_vector() for features in features_list])
            y = np.array(outcomes).reshape(-1, 1)

            # Normalize outcomes to [0, 1]
            y_normalized = (y - np.min(y)) / (np.max(y) - np.min(y) + 1e-8)

            # Ensure network input size matches
            if X.shape[1] != network.input_size:
                network = SimpleNeuralNetwork(
                    input_size=X.shape[1],
                    hidden_sizes=[64, 32, 16],
                    output_size=1
                )
                self.networks[pattern_type] = network

            # Train network
            losses = network.train(X, y_normalized, epochs=50)

            training_result = {
                'success': True,
                'pattern_type': pattern_type,
                'training_samples': len(features_list),
                'final_loss': losses[-1] if losses else 0.0,
                'improvement': (losses[0] - losses[-1]) / losses[0] if len(losses) > 1 else 0.0
            }

            logger.info(f"[NEURAL_ENGINE] Trained {pattern_type} network on {len(features_list)} samples")
            return training_result

        except Exception as e:
            logger.error(f"[NEURAL_ENGINE] Error training on outcomes: {e}")
            return {'success': False, 'error': str(e)}

    async def _enhance_features_with_position(self, features: PatternFeatures,
                                            position_data: Dict[str, Any]) -> PatternFeatures:
        """Enhance features with position-specific data"""
        # Add position-specific features
        enhanced_features = PatternFeatures(
            technical_indicators=features.technical_indicators.copy(),
            market_conditions=features.market_conditions.copy(),
            volume_profile=features.volume_profile.copy(),
            price_action=features.price_action.copy(),
            time_features=features.time_features.copy(),
            sentiment_indicators=features.sentiment_indicators.copy()
        )

        # Add position features
        entry_price = position_data.get('entry_price', 0)
        current_price = features.price_action.get('price', 0)

        if entry_price > 0 and current_price > 0:
            profit_pct = (current_price - entry_price) / entry_price
            enhanced_features.price_action['profit_pct'] = profit_pct
            enhanced_features.price_action['hold_time'] = position_data.get('hold_time', 0)

        return enhanced_features

    async def _calculate_neural_exit_amount(self, confidence: float,
                                          position_data: Dict[str, Any],
                                          features: PatternFeatures) -> float:
        """Calculate exit amount using neural network insights"""
        position_size = position_data.get('amount', 0)
        profit_pct = features.price_action.get('profit_pct', 0)

        # Base exit percentage on confidence
        if confidence > 0.9:
            exit_pct = 1.0  # Full exit
        elif confidence > 0.8:
            exit_pct = 0.8  # 80% exit
        elif confidence > 0.7:
            exit_pct = 0.6  # 60% exit
        else:
            exit_pct = 0.3  # 30% exit

        # Adjust based on profit
        if profit_pct > 0.02:  # 2%+ profit
            exit_pct = min(exit_pct + 0.2, 1.0)
        elif profit_pct < -0.01:  # 1%+ loss
            exit_pct = min(exit_pct + 0.3, 1.0)

        return position_size * exit_pct

    async def _analyze_pattern_components(self, features: PatternFeatures,
                                        pattern_type: str) -> Dict[str, Any]:
        """Analyze individual pattern components"""
        analysis = {}

        # Technical analysis
        rsi = features.technical_indicators.get('rsi', 50)
        if rsi < 30:
            analysis['technical'] = 'oversold_signal'
        elif rsi > 70:
            analysis['technical'] = 'overbought_signal'
        else:
            analysis['technical'] = 'neutral'

        # Volume analysis
        volume_ratio = features.volume_profile.get('volume_momentum', 1.0)
        if volume_ratio > 1.5:
            analysis['volume'] = 'high_volume'
        elif volume_ratio < 0.8:
            analysis['volume'] = 'low_volume'
        else:
            analysis['volume'] = 'normal_volume'

        # Trend analysis
        trend = features.market_conditions.get('trend', 'neutral')
        analysis['trend'] = trend

        return analysis

    async def _prepare_regime_features(self, features: PatternFeatures,
                                     historical_data: List[Dict[str, Any]]) -> PatternFeatures:
        """Prepare features specifically for regime detection"""
        # Add historical context features
        regime_features = PatternFeatures(
            technical_indicators=features.technical_indicators.copy(),
            market_conditions=features.market_conditions.copy(),
            volume_profile=features.volume_profile.copy(),
            price_action=features.price_action.copy(),
            time_features=features.time_features.copy(),
            sentiment_indicators=features.sentiment_indicators.copy()
        )

        # Add regime-specific features from historical data
        if historical_data:
            # Calculate trend persistence
            recent_trends = [d.get('trend', 'neutral') for d in historical_data[-10:]]
            trend_persistence = len([t for t in recent_trends if t == features.market_conditions.get('trend')]) / len(recent_trends)
            regime_features.market_conditions['trend_persistence'] = trend_persistence

            # Calculate volatility trend
            recent_volatilities = [d.get('volatility', 0.02) for d in historical_data[-5:]]
            if recent_volatilities:
                volatility_trend = (recent_volatilities[-1] - recent_volatilities[0]) / (recent_volatilities[0] + 1e-8)
                regime_features.market_conditions['volatility_trend'] = volatility_trend

        return regime_features

    async def _calculate_feature_importance(self, features: PatternFeatures,
                                          network: SimpleNeuralNetwork) -> Dict[str, float]:
        """Calculate feature importance using simple sensitivity analysis"""
        importance = {}

        try:
            base_vector = features.to_vector()
            base_prediction = network.predict(base_vector.reshape(1, -1))[0, 0]

            # Calculate sensitivity for each feature
            for i in range(len(base_vector)):
                # Perturb feature slightly
                perturbed_vector = base_vector.copy()
                perturbed_vector[i] += 0.1 * abs(perturbed_vector[i]) + 0.01

                # Get new prediction
                perturbed_prediction = network.predict(perturbed_vector.reshape(1, -1))[0, 0]

                # Calculate sensitivity
                sensitivity = abs(perturbed_prediction - base_prediction)
                importance[f'feature_{i}'] = float(sensitivity)

        except Exception as e:
            logger.error(f"[NEURAL_ENGINE] Error calculating feature importance: {e}")

        return importance

    async def _generate_exit_reasoning(self, features: PatternFeatures, confidence: float) -> str:
        """Generate human-readable reasoning for exit decisions"""
        reasons = []

        if confidence > 0.8:
            reasons.append("Strong neural pattern signal")

        profit_pct = features.price_action.get('profit_pct', 0)
        if profit_pct > 0.02:
            reasons.append(f"Significant profit achieved ({profit_pct:.2%})")
        elif profit_pct < -0.01:
            reasons.append(f"Loss threshold approached ({profit_pct:.2%})")

        rsi = features.technical_indicators.get('rsi', 50)
        if rsi > 75:
            reasons.append("Overbought conditions detected")
        elif rsi < 25:
            reasons.append("Oversold conditions detected")

        if not reasons:
            reasons.append("Neural pattern analysis suggests exit")

        return "; ".join(reasons)

    async def _calculate_regime_strength(self, features: PatternFeatures) -> float:
        """Calculate strength of current market regime"""
        # Simple regime strength calculation
        volatility = features.market_conditions.get('volatility', 0.02)
        volume_momentum = features.volume_profile.get('volume_momentum', 1.0)
        trend_persistence = features.market_conditions.get('trend_persistence', 0.5)

        # Higher volatility and volume with trend persistence indicates strong regime
        strength = (volatility * 10 + volume_momentum + trend_persistence) / 3
        return min(strength, 1.0)

    async def _calculate_transition_probability(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate probability of regime transition"""
        if len(historical_data) < 10:
            return 0.3  # Default moderate probability

        # Count regime changes in recent history
        regimes = [d.get('regime', 'neutral') for d in historical_data[-10:]]
        transitions = sum(1 for i in range(1, len(regimes)) if regimes[i] != regimes[i-1])

        transition_rate = transitions / (len(regimes) - 1)
        return min(transition_rate, 1.0)

    def save_networks(self, filepath: str):
        """Save trained neural networks"""
        try:
            network_data = {}
            for pattern_type, network in self.networks.items():
                network_data[pattern_type] = {
                    'weights': [w.tolist() for w in network.weights],
                    'biases': [b.tolist() for b in network.biases],
                    'input_size': network.input_size,
                    'hidden_sizes': network.hidden_sizes,
                    'output_size': network.output_size,
                    'training_history': network.training_history
                }

            with open(filepath, 'w') as f:
                json.dump(network_data, f, indent=2)

            logger.info(f"[NEURAL_ENGINE] Networks saved to {filepath}")

        except Exception as e:
            logger.error(f"[NEURAL_ENGINE] Error saving networks: {e}")

    def load_networks(self, filepath: str):
        """Load trained neural networks"""
        try:
            with open(filepath) as f:
                network_data = json.load(f)

            for pattern_type, data in network_data.items():
                # Recreate network
                network = SimpleNeuralNetwork(
                    input_size=data['input_size'],
                    hidden_sizes=data['hidden_sizes'],
                    output_size=data['output_size']
                )

                # Load weights and biases
                network.weights = [np.array(w) for w in data['weights']]
                network.biases = [np.array(b) for b in data['biases']]
                network.training_history = data.get('training_history', [])

                self.networks[pattern_type] = network

            logger.info(f"[NEURAL_ENGINE] Networks loaded from {filepath}")

        except Exception as e:
            logger.error(f"[NEURAL_ENGINE] Error loading networks: {e}")

    def get_network_status(self) -> Dict[str, Any]:
        """Get status of all neural networks"""
        status = {}

        for pattern_type, network in self.networks.items():
            status[pattern_type] = {
                'input_size': network.input_size,
                'hidden_sizes': network.hidden_sizes,
                'output_size': network.output_size,
                'training_samples': len(network.training_history),
                'last_loss': network.training_history[-1] if network.training_history else 'not_trained'
            }

        return status
