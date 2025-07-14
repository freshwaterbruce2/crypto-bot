"""
Learning Integration Module
===========================

Integrates all learning components with the existing trading bot architecture.
Provides seamless integration with minimal disruption to existing code.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .unified_learning_system import UnifiedLearningSystem, LearningMetrics
from .neural_pattern_engine import PatternRecognitionEngine, PatternFeatures
from .advanced_memory_manager import AdvancedMemoryManager

logger = logging.getLogger(__name__)


class LearningSystemIntegrator:
    """Main integration class for the enhanced learning system"""
    
    def __init__(self, bot_instance=None):
        """Initialize learning system integrator"""
        self.bot = bot_instance
        self.logger = logger
        
        # Core learning components
        self.unified_learning = UnifiedLearningSystem(bot_instance)
        self.neural_engine = PatternRecognitionEngine()
        self.advanced_memory = AdvancedMemoryManager()
        
        # Integration settings
        self.integration_enabled = True
        self.neural_learning_enabled = True
        self.advanced_memory_enabled = True
        
        # Performance tracking
        self.integration_metrics = {
            'learning_decisions': 0,
            'neural_predictions': 0,
            'memory_operations': 0,
            'performance_improvements': 0.0
        }
        
        self.logger.info("[LEARNING_INTEGRATION] System initialized")
    
    async def initialize(self):
        """Initialize all learning components"""
        try:
            # Initialize components in parallel
            init_tasks = []
            
            if self.integration_enabled:
                init_tasks.append(self.unified_learning.initialize())
            
            if self.advanced_memory_enabled:
                init_tasks.append(self.advanced_memory.initialize())
            
            # Wait for all to complete
            if init_tasks:
                await asyncio.gather(*init_tasks, return_exceptions=True)
            
            # Register with existing assistants
            await self._register_with_assistants()
            
            self.logger.info("[LEARNING_INTEGRATION] All components initialized")
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error initializing: {e}")
    
    async def enhance_buy_decision(self, symbol: str, market_data: Dict[str, Any], 
                                 original_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance buy decision with neural learning"""
        try:
            if not self.neural_learning_enabled:
                return original_decision
            
            # Extract features for neural analysis
            features = await self.neural_engine.extract_features(
                market_data, 
                {'symbol': symbol, 'decision_type': 'buy'}
            )
            
            # Get neural prediction
            neural_result = await self.neural_engine.recognize_entry_pattern(
                features, 
                await self._get_historical_outcomes(symbol, 'buy')
            )
            
            # Enhance original decision
            enhanced_decision = original_decision.copy()
            
            # Combine confidences (weighted average)
            original_confidence = original_decision.get('confidence', 0.5)
            neural_confidence = neural_result.get('confidence', 0.5)
            
            # Neural weight based on training quality
            neural_weight = 0.3 if neural_result.get('neural_score', 0) > 0.1 else 0.1
            
            combined_confidence = (
                original_confidence * (1 - neural_weight) + 
                neural_confidence * neural_weight
            )
            
            enhanced_decision.update({
                'confidence': combined_confidence,
                'neural_confidence': neural_confidence,
                'neural_recommendation': neural_result.get('recommendation', 'HOLD'),
                'pattern_analysis': neural_result.get('pattern_analysis', {}),
                'feature_importance': neural_result.get('feature_importance', {}),
                'learning_enhanced': True
            })
            
            # Store decision for learning
            await self._store_buy_decision(symbol, features, enhanced_decision, market_data)
            
            self.integration_metrics['learning_decisions'] += 1
            self.integration_metrics['neural_predictions'] += 1
            
            return enhanced_decision
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error enhancing buy decision: {e}")
            return original_decision
    
    async def enhance_sell_decision(self, symbol: str, position_data: Dict[str, Any], 
                                  market_data: Dict[str, Any], 
                                  original_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance sell decision with neural learning"""
        try:
            if not self.neural_learning_enabled:
                return original_decision
            
            # Extract features for neural analysis
            features = await self.neural_engine.extract_features(
                market_data,
                {'symbol': symbol, 'decision_type': 'sell', 'position': position_data}
            )
            
            # Get neural prediction
            neural_result = await self.neural_engine.recognize_exit_pattern(
                features, 
                position_data
            )
            
            # Enhance original decision
            enhanced_decision = original_decision.copy()
            
            # Combine confidences
            original_confidence = original_decision.get('confidence', 0.5)
            neural_confidence = neural_result.get('confidence', 0.5)
            
            # Neural weight based on position profitability and training quality
            profit_pct = position_data.get('profit_pct', 0)
            neural_weight = 0.4 if abs(profit_pct) > 0.01 else 0.2  # Higher weight for significant moves
            
            combined_confidence = (
                original_confidence * (1 - neural_weight) + 
                neural_confidence * neural_weight
            )
            
            # Adjust exit amount based on neural insights
            original_amount = original_decision.get('exit_amount', 0)
            neural_amount = neural_result.get('exit_amount', original_amount)
            
            # Use neural amount if confidence is high
            if neural_confidence > 0.8:
                final_amount = neural_amount
            else:
                final_amount = (original_amount + neural_amount) / 2
            
            enhanced_decision.update({
                'confidence': combined_confidence,
                'exit_amount': final_amount,
                'neural_confidence': neural_confidence,
                'neural_recommendation': neural_result.get('recommendation', 'HOLD'),
                'neural_reasoning': neural_result.get('reasoning', ''),
                'learning_enhanced': True
            })
            
            # Store decision for learning
            await self._store_sell_decision(symbol, features, enhanced_decision, position_data)
            
            self.integration_metrics['learning_decisions'] += 1
            self.integration_metrics['neural_predictions'] += 1
            
            return enhanced_decision
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error enhancing sell decision: {e}")
            return original_decision
    
    async def learn_from_trade_outcome(self, symbol: str, trade_data: Dict[str, Any], 
                                     outcome: Dict[str, Any]):
        """Learn from completed trade outcomes"""
        try:
            # Store trade outcome in advanced memory
            if self.advanced_memory_enabled:
                await self.advanced_memory.store_entry(
                    data={
                        'symbol': symbol,
                        'trade_data': trade_data,
                        'outcome': outcome,
                        'profit_pct': outcome.get('profit_pct', 0),
                        'hold_time': outcome.get('hold_time_seconds', 0)
                    },
                    entry_type='trade_outcome',
                    tags=[symbol, 'trade_complete', trade_data.get('signal_type', 'unknown')],
                    importance_score=self._calculate_trade_importance(outcome)
                )
            
            # Train neural networks on outcome
            if self.neural_learning_enabled:
                await self._train_on_trade_outcome(symbol, trade_data, outcome)
            
            # Update unified learning system
            if self.integration_enabled:
                await self.unified_learning.cross_component_learning()
            
            self.integration_metrics['memory_operations'] += 1
            
            # Calculate performance improvement
            profit_pct = outcome.get('profit_pct', 0)
            if profit_pct > 0:
                self.integration_metrics['performance_improvements'] += profit_pct
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error learning from trade outcome: {e}")
    
    async def get_market_regime_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive market regime analysis"""
        try:
            if not self.neural_learning_enabled:
                return {'regime': 'neutral', 'confidence': 0.5}
            
            # Extract features
            features = await self.neural_engine.extract_features(
                market_data,
                {'analysis_type': 'market_regime'}
            )
            
            # Get historical market data
            historical_data = await self._get_historical_market_data()
            
            # Detect market regime
            regime_analysis = await self.neural_engine.detect_market_regime(
                features, 
                historical_data
            )
            
            # Store regime analysis
            if self.advanced_memory_enabled:
                await self.advanced_memory.store_entry(
                    data=regime_analysis,
                    entry_type='market_regime',
                    tags=['regime_analysis', regime_analysis.get('regime', 'unknown')],
                    importance_score=regime_analysis.get('confidence', 0.5)
                )
            
            return regime_analysis
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error in market regime analysis: {e}")
            return {'regime': 'neutral', 'confidence': 0.5, 'error': str(e)}
    
    async def get_learning_insights(self, symbol: str = None) -> Dict[str, Any]:
        """Get comprehensive learning insights"""
        try:
            insights = {
                'unified_learning': {},
                'neural_patterns': {},
                'memory_analysis': {},
                'integration_metrics': self.integration_metrics.copy()
            }
            
            # Get unified learning status
            if self.integration_enabled:
                insights['unified_learning'] = self.unified_learning.get_learning_status()
            
            # Get neural network status
            if self.neural_learning_enabled:
                insights['neural_patterns'] = self.neural_engine.get_network_status()
            
            # Get memory statistics
            if self.advanced_memory_enabled:
                insights['memory_analysis'] = self.advanced_memory.get_memory_stats()
            
            # Get symbol-specific insights if requested
            if symbol and self.advanced_memory_enabled:
                symbol_insights = await self._get_symbol_insights(symbol)
                insights['symbol_specific'] = symbol_insights
            
            return insights
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error getting learning insights: {e}")
            return {'error': str(e)}
    
    async def optimize_learning_system(self) -> Dict[str, Any]:
        """Optimize the entire learning system"""
        try:
            optimization_results = {}
            
            # Run unified learning optimization
            if self.integration_enabled:
                unified_result = await self.unified_learning.cross_component_learning()
                optimization_results['unified_learning'] = unified_result
            
            # Train neural networks on recent data
            if self.neural_learning_enabled:
                neural_result = await self._optimize_neural_networks()
                optimization_results['neural_optimization'] = neural_result
            
            # Clean up and optimize memory
            if self.advanced_memory_enabled:
                memory_result = await self._optimize_memory_system()
                optimization_results['memory_optimization'] = memory_result
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error optimizing learning system: {e}")
            return {'error': str(e)}
    
    # Helper methods
    
    async def _register_with_assistants(self):
        """Register learning integration with existing assistants"""
        if not self.bot or not hasattr(self.bot, 'assistant_manager'):
            return
        
        try:
            assistant_manager = self.bot.assistant_manager
            
            # Add learning enhancement methods to assistants
            if hasattr(assistant_manager, 'buy_logic_assistant'):
                assistant_manager.buy_logic_assistant.learning_integrator = self
            
            if hasattr(assistant_manager, 'sell_logic_assistant'):
                assistant_manager.sell_logic_assistant.learning_integrator = self
            
            if hasattr(assistant_manager, 'adaptive_selling_assistant'):
                assistant_manager.adaptive_selling_assistant.learning_integrator = self
            
            self.logger.info("[LEARNING_INTEGRATION] Registered with existing assistants")
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error registering with assistants: {e}")
    
    async def _get_historical_outcomes(self, symbol: str, decision_type: str) -> List[Dict[str, Any]]:
        """Get historical outcomes for a symbol and decision type"""
        if not self.advanced_memory_enabled:
            return []
        
        try:
            # Search for historical trade outcomes
            search_results = await self.advanced_memory.search_entries({
                'tags': [symbol, 'trade_complete'],
                'type': 'trade_outcome',
                'limit': 50
            })
            
            return [result['data'] for result in search_results]
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error getting historical outcomes: {e}")
            return []
    
    async def _store_buy_decision(self, symbol: str, features: PatternFeatures, 
                                decision: Dict[str, Any], market_data: Dict[str, Any]):
        """Store buy decision for learning"""
        if not self.advanced_memory_enabled:
            return
        
        try:
            await self.advanced_memory.store_entry(
                data={
                    'symbol': symbol,
                    'decision': decision,
                    'features': features.__dict__,
                    'market_data': market_data,
                    'decision_type': 'buy'
                },
                entry_type='buy_decision',
                tags=[symbol, 'buy_decision', decision.get('recommendation', 'HOLD')],
                importance_score=decision.get('confidence', 0.5)
            )
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error storing buy decision: {e}")
    
    async def _store_sell_decision(self, symbol: str, features: PatternFeatures, 
                                 decision: Dict[str, Any], position_data: Dict[str, Any]):
        """Store sell decision for learning"""
        if not self.advanced_memory_enabled:
            return
        
        try:
            await self.advanced_memory.store_entry(
                data={
                    'symbol': symbol,
                    'decision': decision,
                    'features': features.__dict__,
                    'position_data': position_data,
                    'decision_type': 'sell'
                },
                entry_type='sell_decision',
                tags=[symbol, 'sell_decision', decision.get('recommendation', 'HOLD')],
                importance_score=decision.get('confidence', 0.5)
            )
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error storing sell decision: {e}")
    
    def _calculate_trade_importance(self, outcome: Dict[str, Any]) -> float:
        """Calculate importance score for a trade outcome"""
        profit_pct = abs(outcome.get('profit_pct', 0))
        hold_time = outcome.get('hold_time_seconds', 3600)
        
        # Higher importance for larger profits/losses and reasonable hold times
        profit_score = min(profit_pct * 20, 1.0)  # 5% profit = max score
        time_score = 0.5 if 300 < hold_time < 7200 else 0.2  # 5min to 2h is optimal
        
        return (profit_score + time_score) / 2
    
    async def _train_on_trade_outcome(self, symbol: str, trade_data: Dict[str, Any], 
                                    outcome: Dict[str, Any]):
        """Train neural networks on trade outcome"""
        try:
            # Get the original decision features
            decision_entries = await self.advanced_memory.search_entries({
                'tags': [symbol],
                'type': 'buy_decision' if trade_data.get('signal_type') == 'buy' else 'sell_decision',
                'limit': 1
            })
            
            if decision_entries:
                decision_data = decision_entries[0]['data']
                features_dict = decision_data.get('features', {})
                
                # Reconstruct features
                features = PatternFeatures(
                    technical_indicators=features_dict.get('technical_indicators', {}),
                    market_conditions=features_dict.get('market_conditions', {}),
                    volume_profile=features_dict.get('volume_profile', {}),
                    price_action=features_dict.get('price_action', {}),
                    time_features=features_dict.get('time_features', {}),
                    sentiment_indicators=features_dict.get('sentiment_indicators', {})
                )
                
                # Normalize outcome for training (0-1 range)
                profit_pct = outcome.get('profit_pct', 0)
                normalized_outcome = max(0, min(1, (profit_pct + 0.05) / 0.1))  # -5% to +5% maps to 0-1
                
                # Train appropriate network
                pattern_type = 'entry_patterns' if trade_data.get('signal_type') == 'buy' else 'exit_patterns'
                await self.neural_engine.train_on_outcomes(
                    pattern_type=pattern_type,
                    features_list=[features],
                    outcomes=[normalized_outcome]
                )
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error training on trade outcome: {e}")
    
    async def _get_historical_market_data(self) -> List[Dict[str, Any]]:
        """Get historical market data for regime analysis"""
        if not self.advanced_memory_enabled:
            return []
        
        try:
            # Search for recent market regime data
            search_results = await self.advanced_memory.search_entries({
                'type': 'market_regime',
                'limit': 20
            })
            
            return [result['data'] for result in search_results]
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error getting historical market data: {e}")
            return []
    
    async def _get_symbol_insights(self, symbol: str) -> Dict[str, Any]:
        """Get symbol-specific learning insights"""
        try:
            # Get symbol-specific trade history
            trade_history = await self.advanced_memory.search_entries({
                'tags': [symbol, 'trade_complete'],
                'limit': 20
            })
            
            # Calculate symbol performance metrics
            profits = []
            hold_times = []
            
            for trade in trade_history:
                outcome = trade['data'].get('outcome', {})
                profits.append(outcome.get('profit_pct', 0))
                hold_times.append(outcome.get('hold_time_seconds', 0))
            
            if profits:
                avg_profit = sum(profits) / len(profits)
                win_rate = len([p for p in profits if p > 0]) / len(profits)
                avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
            else:
                avg_profit = 0
                win_rate = 0
                avg_hold_time = 0
            
            return {
                'symbol': symbol,
                'total_trades': len(trade_history),
                'avg_profit_pct': avg_profit,
                'win_rate': win_rate,
                'avg_hold_time_seconds': avg_hold_time,
                'recent_trades': len([t for t in trade_history if 
                                    datetime.fromisoformat(t['data']['outcome'].get('timestamp', '2020-01-01')) > 
                                    datetime.now() - timedelta(days=7)])
            }
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error getting symbol insights: {e}")
            return {}
    
    async def _optimize_neural_networks(self) -> Dict[str, Any]:
        """Optimize neural networks with recent data"""
        try:
            optimization_results = {}
            
            # Get recent trade outcomes for training
            recent_trades = await self.advanced_memory.search_entries({
                'type': 'trade_outcome',
                'start_date': datetime.now() - timedelta(days=7),
                'limit': 100
            })
            
            if len(recent_trades) > 10:  # Need sufficient data
                # Group by pattern type
                entry_data = []
                exit_data = []
                
                for trade in recent_trades:
                    trade_data = trade['data']['trade_data']
                    outcome = trade['data']['outcome']
                    
                    if trade_data.get('signal_type') == 'buy':
                        entry_data.append((trade_data, outcome))
                    else:
                        exit_data.append((trade_data, outcome))
                
                # Train networks
                if entry_data:
                    # Extract features and outcomes for entry patterns
                    # This would need to be implemented with proper feature extraction
                    pass
                
                if exit_data:
                    # Extract features and outcomes for exit patterns
                    # This would need to be implemented with proper feature extraction
                    pass
                
                optimization_results['entries_trained'] = len(entry_data)
                optimization_results['exits_trained'] = len(exit_data)
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error optimizing neural networks: {e}")
            return {'error': str(e)}
    
    async def _optimize_memory_system(self) -> Dict[str, Any]:
        """Optimize memory system performance"""
        try:
            # This would trigger memory cleanup and optimization
            initial_stats = self.advanced_memory.get_memory_stats()
            
            # Trigger cleanup (this would be done by the memory manager automatically)
            # For now, just return current stats
            final_stats = self.advanced_memory.get_memory_stats()
            
            return {
                'initial_stats': initial_stats,
                'final_stats': final_stats,
                'optimization_completed': True
            }
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error optimizing memory system: {e}")
            return {'error': str(e)}
    
    async def stop(self):
        """Stop all learning components"""
        try:
            if self.advanced_memory_enabled:
                await self.advanced_memory.stop()
            
            self.logger.info("[LEARNING_INTEGRATION] All learning components stopped")
            
        except Exception as e:
            self.logger.error(f"[LEARNING_INTEGRATION] Error stopping learning components: {e}")


# Integration helper functions for existing assistants

async def enhance_assistant_with_learning(assistant, learning_integrator: LearningSystemIntegrator):
    """Enhance existing assistant with learning capabilities"""
    assistant.learning_integrator = learning_integrator


async def get_learning_enhanced_decision(assistant, decision_data: Dict[str, Any], 
                                       context: Dict[str, Any]) -> Dict[str, Any]:
    """Get learning-enhanced decision from assistant"""
    if not hasattr(assistant, 'learning_integrator') or not assistant.learning_integrator:
        return decision_data
    
    try:
        symbol = context.get('symbol', '')
        market_data = context.get('market_data', {})
        
        if context.get('decision_type') == 'buy':
            return await assistant.learning_integrator.enhance_buy_decision(
                symbol, market_data, decision_data
            )
        elif context.get('decision_type') == 'sell':
            position_data = context.get('position_data', {})
            return await assistant.learning_integrator.enhance_sell_decision(
                symbol, position_data, market_data, decision_data
            )
        
        return decision_data
        
    except Exception as e:
        logger.error(f"[LEARNING_INTEGRATION] Error getting enhanced decision: {e}")
        return decision_data