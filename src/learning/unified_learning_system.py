"""
Unified Learning System
=======================

Central coordination system for all learning components in the trading bot.
Implements cross-component learning, pattern sharing, and unified optimization.
"""

import asyncio
import logging
import json
import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class LearningMetrics:
    """Unified metrics for learning system performance"""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    profit_factor: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    learning_rate: float = 0.01
    adaptation_speed: float = 0.0
    pattern_recognition_score: float = 0.0
    memory_efficiency: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class LearningState:
    """Current state of the learning system"""
    active_patterns: List[str] = field(default_factory=list)
    recent_performance: deque = field(default_factory=lambda: deque(maxlen=100))
    adaptation_triggers: List[str] = field(default_factory=list)
    learning_phase: str = "exploration"  # exploration, exploitation, adaptation
    confidence_level: float = 0.5
    last_optimization: datetime = field(default_factory=datetime.now)
    

class CrossComponentPatternAnalyzer:
    """Analyzes patterns across all learning components"""
    
    def __init__(self):
        self.pattern_database = {}
        self.correlation_matrix = {}
        self.success_patterns = defaultdict(list)
        self.failure_patterns = defaultdict(list)
        
    async def analyze_cross_patterns(self, component_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns across multiple components"""
        try:
            patterns = {}
            
            # Extract patterns from each component
            for component, data in component_data.items():
                component_patterns = await self._extract_component_patterns(component, data)
                patterns[component] = component_patterns
            
            # Find correlations between components
            correlations = await self._find_correlations(patterns)
            
            # Identify successful pattern combinations
            successful_combinations = await self._identify_successful_combinations(patterns)
            
            return {
                'individual_patterns': patterns,
                'correlations': correlations,
                'successful_combinations': successful_combinations,
                'optimization_suggestions': await self._generate_optimization_suggestions(correlations)
            }
            
        except Exception as e:
            logger.error(f"[UNIFIED_LEARNING] Error analyzing cross patterns: {e}")
            return {}
    
    async def _extract_component_patterns(self, component: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract patterns from individual component data"""
        patterns = []
        
        if component == "memory_assistant":
            # Extract memory patterns
            for pattern_key, pattern_data in data.get('pattern_memory', {}).items():
                if pattern_data.get('frequency', 0) > 3:  # Significant patterns
                    patterns.append({
                        'type': 'memory_pattern',
                        'key': pattern_key,
                        'success_rate': pattern_data.get('success_rate', 0),
                        'frequency': pattern_data.get('frequency', 0),
                        'conditions': pattern_data.get('conditions', {})
                    })
        
        elif component == "buy_logic":
            # Extract buy decision patterns
            for rec in data.get('recommendations', []):
                if rec.get('confidence', 0) > 0.7:  # High confidence patterns
                    patterns.append({
                        'type': 'buy_pattern',
                        'confidence': rec.get('confidence', 0),
                        'market_conditions': rec.get('market_conditions', {}),
                        'analysis_factors': rec.get('analysis_factors', [])
                    })
        
        elif component == "sell_logic":
            # Extract sell decision patterns
            for decision in data.get('decisions', []):
                if decision.get('confidence', 0) > 0.7:  # High confidence patterns
                    patterns.append({
                        'type': 'sell_pattern',
                        'confidence': decision.get('confidence', 0),
                        'profit_pct': decision.get('profit_pct', 0),
                        'hold_time': decision.get('hold_time_hours', 0),
                        'exit_factors': decision.get('exit_factors', [])
                    })
        
        return patterns
    
    async def _find_correlations(self, patterns: Dict[str, List]) -> Dict[str, float]:
        """Find correlations between component patterns"""
        correlations = {}
        
        # Buy-Sell correlation
        buy_patterns = patterns.get('buy_logic', [])
        sell_patterns = patterns.get('sell_logic', [])
        
        if buy_patterns and sell_patterns:
            buy_confidence = np.mean([p.get('confidence', 0) for p in buy_patterns])
            sell_success = np.mean([1 if p.get('profit_pct', 0) > 0 else 0 for p in sell_patterns])
            correlations['buy_confidence_sell_success'] = buy_confidence * sell_success
        
        # Memory-Performance correlation
        memory_patterns = patterns.get('memory_assistant', [])
        if memory_patterns:
            memory_success = np.mean([p.get('success_rate', 0) for p in memory_patterns])
            correlations['memory_performance'] = memory_success
        
        return correlations
    
    async def _identify_successful_combinations(self, patterns: Dict[str, List]) -> List[Dict[str, Any]]:
        """Identify successful pattern combinations"""
        combinations = []
        
        # High buy confidence + profitable sell patterns
        buy_patterns = patterns.get('buy_logic', [])
        sell_patterns = patterns.get('sell_logic', [])
        
        for buy_pattern in buy_patterns:
            if buy_pattern.get('confidence', 0) > 0.8:
                for sell_pattern in sell_patterns:
                    if sell_pattern.get('profit_pct', 0) > 0.01:  # 1%+ profit
                        combinations.append({
                            'type': 'buy_sell_success',
                            'buy_confidence': buy_pattern.get('confidence', 0),
                            'sell_profit': sell_pattern.get('profit_pct', 0),
                            'hold_time': sell_pattern.get('hold_time', 0),
                            'success_score': buy_pattern.get('confidence', 0) * sell_pattern.get('profit_pct', 0)
                        })
        
        # Sort by success score
        combinations.sort(key=lambda x: x.get('success_score', 0), reverse=True)
        return combinations[:10]  # Top 10 combinations
    
    async def _generate_optimization_suggestions(self, correlations: Dict[str, float]) -> List[str]:
        """Generate optimization suggestions based on correlations"""
        suggestions = []
        
        buy_sell_correlation = correlations.get('buy_confidence_sell_success', 0)
        if buy_sell_correlation < 0.5:
            suggestions.append("Improve coordination between buy confidence and sell success rates")
        
        memory_performance = correlations.get('memory_performance', 0)
        if memory_performance < 0.6:
            suggestions.append("Enhance memory pattern learning to improve overall performance")
        
        if len(correlations) < 3:
            suggestions.append("Increase cross-component data collection for better correlation analysis")
        
        return suggestions


class PerformanceCoordinator:
    """Coordinates performance optimization across all components"""
    
    def __init__(self):
        self.performance_history = deque(maxlen=1000)
        self.optimization_targets = {}
        self.adaptation_strategies = {}
        
    async def coordinate_optimization(self, component_metrics: Dict[str, LearningMetrics]) -> Dict[str, Any]:
        """Coordinate optimization across all components"""
        try:
            # Calculate overall performance
            overall_performance = await self._calculate_overall_performance(component_metrics)
            
            # Identify underperforming components
            underperforming = await self._identify_underperforming_components(component_metrics)
            
            # Generate optimization strategy
            optimization_strategy = await self._generate_optimization_strategy(
                overall_performance, underperforming, component_metrics
            )
            
            # Update performance history
            self.performance_history.append({
                'timestamp': datetime.now(),
                'overall_performance': overall_performance,
                'component_metrics': {k: v.to_dict() for k, v in component_metrics.items()},
                'optimization_actions': optimization_strategy.get('actions', [])
            })
            
            return optimization_strategy
            
        except Exception as e:
            logger.error(f"[PERFORMANCE_COORDINATOR] Error coordinating optimization: {e}")
            return {}
    
    async def _calculate_overall_performance(self, component_metrics: Dict[str, LearningMetrics]) -> float:
        """Calculate overall system performance score"""
        if not component_metrics:
            return 0.0
        
        # Weighted performance calculation
        weights = {
            'accuracy': 0.3,
            'profit_factor': 0.25,
            'win_rate': 0.2,
            'sharpe_ratio': 0.15,
            'adaptation_speed': 0.1
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for component, metrics in component_metrics.items():
            component_score = 0.0
            component_weight = 0.0
            
            for metric, weight in weights.items():
                if hasattr(metrics, metric):
                    value = getattr(metrics, metric, 0.0)
                    component_score += value * weight
                    component_weight += weight
            
            if component_weight > 0:
                total_score += (component_score / component_weight) * component_weight
                total_weight += component_weight
        
        return total_score / max(total_weight, 1.0)
    
    async def _identify_underperforming_components(self, component_metrics: Dict[str, LearningMetrics]) -> List[str]:
        """Identify components that are underperforming"""
        underperforming = []
        
        # Performance thresholds
        thresholds = {
            'accuracy': 0.6,
            'win_rate': 0.5,
            'profit_factor': 1.2,
            'adaptation_speed': 0.3
        }
        
        for component, metrics in component_metrics.items():
            issues = []
            
            for metric, threshold in thresholds.items():
                if hasattr(metrics, metric):
                    value = getattr(metrics, metric, 0.0)
                    if value < threshold:
                        issues.append(metric)
            
            if len(issues) >= 2:  # Multiple issues indicate underperformance
                underperforming.append(component)
        
        return underperforming
    
    async def _generate_optimization_strategy(self, overall_performance: float, 
                                            underperforming: List[str], 
                                            component_metrics: Dict[str, LearningMetrics]) -> Dict[str, Any]:
        """Generate comprehensive optimization strategy"""
        strategy = {
            'overall_performance': overall_performance,
            'actions': [],
            'priorities': [],
            'expected_improvements': {}
        }
        
        # Global optimization actions
        if overall_performance < 0.6:
            strategy['actions'].append({
                'type': 'global_optimization',
                'action': 'increase_learning_rate',
                'target': 'all_components',
                'priority': 'high'
            })
        
        # Component-specific optimizations
        for component in underperforming:
            metrics = component_metrics.get(component, LearningMetrics())
            
            if metrics.accuracy < 0.6:
                strategy['actions'].append({
                    'type': 'accuracy_improvement',
                    'action': 'enhance_pattern_recognition',
                    'target': component,
                    'priority': 'high'
                })
            
            if metrics.adaptation_speed < 0.3:
                strategy['actions'].append({
                    'type': 'adaptation_enhancement',
                    'action': 'increase_adaptation_frequency',
                    'target': component,
                    'priority': 'medium'
                })
        
        # Memory optimization
        memory_metrics = component_metrics.get('memory_assistant', LearningMetrics())
        if memory_metrics.memory_efficiency < 0.7:
            strategy['actions'].append({
                'type': 'memory_optimization',
                'action': 'implement_memory_compression',
                'target': 'memory_assistant',
                'priority': 'medium'
            })
        
        # Sort actions by priority
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        strategy['actions'].sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)
        
        return strategy


class UnifiedLearningSystem:
    """Central coordination system for all learning components"""
    
    def __init__(self, bot_instance=None):
        """Initialize unified learning system"""
        self.bot = bot_instance
        self.logger = logger
        
        # Core components
        self.pattern_analyzer = CrossComponentPatternAnalyzer()
        self.performance_coordinator = PerformanceCoordinator()
        
        # Learning state
        self.state = LearningState()
        self.metrics = LearningMetrics()
        
        # Component interfaces
        self.components = {}
        self.component_metrics = {}
        
        # Learning configuration
        self.learning_config = {
            'adaptation_frequency': 300,  # 5 minutes
            'optimization_frequency': 3600,  # 1 hour
            'pattern_analysis_frequency': 900,  # 15 minutes
            'performance_evaluation_frequency': 1800,  # 30 minutes
        }
        
        # Neural coordination
        self.neural_model_id = None
        self.neural_patterns = {}
        
        self.logger.info("[UNIFIED_LEARNING] System initialized")
    
    async def initialize(self):
        """Initialize the unified learning system"""
        try:
            # Register components
            await self._discover_and_register_components()
            
            # Start learning loops
            asyncio.create_task(self._adaptation_loop())
            asyncio.create_task(self._optimization_loop())
            asyncio.create_task(self._pattern_analysis_loop())
            asyncio.create_task(self._performance_evaluation_loop())
            
            # Load any existing neural patterns
            await self._load_neural_patterns()
            
            self.logger.info("[UNIFIED_LEARNING] System started successfully")
            
        except Exception as e:
            self.logger.error(f"[UNIFIED_LEARNING] Error initializing system: {e}")
    
    async def _discover_and_register_components(self):
        """Discover and register all learning components"""
        if self.bot:
            # Register assistant manager components
            if hasattr(self.bot, 'assistant_manager'):
                assistant_manager = self.bot.assistant_manager
                
                # Register individual assistants
                component_names = [
                    'memory', 'analytics', 'buy_logic', 'sell_logic', 'adaptive_selling'
                ]
                
                for name in component_names:
                    assistant = getattr(assistant_manager, f'{name}_assistant', None)
                    if assistant:
                        self.components[name] = assistant
                        self.component_metrics[name] = LearningMetrics()
                        self.logger.info(f"[UNIFIED_LEARNING] Registered component: {name}")
    
    async def cross_component_learning(self):
        """Perform cross-component learning and optimization"""
        try:
            # Collect data from all components
            component_data = {}
            for name, component in self.components.items():
                data = await self._extract_component_data(name, component)
                component_data[name] = data
            
            # Analyze patterns across components
            pattern_analysis = await self.pattern_analyzer.analyze_cross_patterns(component_data)
            
            # Coordinate performance optimization
            optimization_strategy = await self.performance_coordinator.coordinate_optimization(
                self.component_metrics
            )
            
            # Apply optimizations
            await self._apply_optimizations(optimization_strategy)
            
            # Update learning state
            await self._update_learning_state(pattern_analysis, optimization_strategy)
            
            self.logger.info(f"[UNIFIED_LEARNING] Cross-component learning completed")
            
            return {
                'pattern_analysis': pattern_analysis,
                'optimization_strategy': optimization_strategy,
                'learning_state': self.state
            }
            
        except Exception as e:
            self.logger.error(f"[UNIFIED_LEARNING] Error in cross-component learning: {e}")
            return {}
    
    async def _extract_component_data(self, name: str, component: Any) -> Dict[str, Any]:
        """Extract learning data from individual component"""
        data = {}
        
        try:
            if name == 'memory' and hasattr(component, 'pattern_memory'):
                data['pattern_memory'] = component.pattern_memory
                data['performance_memory'] = component.performance_memory
                data['memory_stats'] = component.memory_stats
            
            elif name in ['buy_logic', 'sell_logic'] and hasattr(component, 'get_performance_summary'):
                data['performance_summary'] = await component.get_performance_summary()
                if hasattr(component, 'buy_recommendations'):
                    data['recommendations'] = component.buy_recommendations[-50:]  # Last 50
                elif hasattr(component, 'sell_decisions'):
                    data['decisions'] = component.sell_decisions[-50:]  # Last 50
            
            elif name == 'adaptive_selling' and hasattr(component, 'get_performance_summary'):
                data['performance_summary'] = await component.get_performance_summary()
                if hasattr(component, 'sell_decisions'):
                    data['decisions'] = component.sell_decisions[-50:]  # Last 50
            
            elif name == 'analytics' and hasattr(component, 'get_performance_report'):
                data['performance_report'] = await component.get_performance_report(hours=24)
                data['analytics_summary'] = component.get_analytics_summary()
            
        except Exception as e:
            self.logger.error(f"[UNIFIED_LEARNING] Error extracting data from {name}: {e}")
        
        return data
    
    async def _apply_optimizations(self, optimization_strategy: Dict[str, Any]):
        """Apply optimization strategy to components"""
        for action in optimization_strategy.get('actions', []):
            try:
                target = action.get('target')
                action_type = action.get('action')
                
                if target == 'all_components':
                    # Apply to all components
                    for name, component in self.components.items():
                        await self._apply_component_optimization(name, component, action)
                elif target in self.components:
                    # Apply to specific component
                    component = self.components[target]
                    await self._apply_component_optimization(target, component, action)
                    
            except Exception as e:
                self.logger.error(f"[UNIFIED_LEARNING] Error applying optimization: {e}")
    
    async def _apply_component_optimization(self, name: str, component: Any, action: Dict[str, Any]):
        """Apply specific optimization to a component"""
        action_type = action.get('action')
        
        if action_type == 'increase_learning_rate':
            # Increase component learning/adaptation rate
            if hasattr(component, 'learning_rate'):
                component.learning_rate = min(component.learning_rate * 1.2, 0.1)
            elif hasattr(component, 'adaptation_frequency'):
                component.adaptation_frequency = max(component.adaptation_frequency * 0.8, 60)
        
        elif action_type == 'enhance_pattern_recognition':
            # Enhance pattern recognition capabilities
            if name == 'memory' and hasattr(component, 'pattern_memory'):
                # Improve pattern memory retention
                for pattern_key, pattern_data in component.pattern_memory.items():
                    if pattern_data.get('success_rate', 0) > 0.7:
                        pattern_data['weight'] = pattern_data.get('weight', 1.0) * 1.1
        
        elif action_type == 'implement_memory_compression':
            # Implement memory compression for efficiency
            if name == 'memory' and hasattr(component, 'clear_old_memory'):
                await component.clear_old_memory(days=15)  # More aggressive cleanup
        
        self.logger.debug(f"[UNIFIED_LEARNING] Applied {action_type} to {name}")
    
    async def _update_learning_state(self, pattern_analysis: Dict[str, Any], 
                                   optimization_strategy: Dict[str, Any]):
        """Update learning state based on analysis results"""
        # Update learning phase
        overall_performance = optimization_strategy.get('overall_performance', 0.5)
        
        if overall_performance > 0.8:
            self.state.learning_phase = 'exploitation'
        elif overall_performance > 0.6:
            self.state.learning_phase = 'adaptation'
        else:
            self.state.learning_phase = 'exploration'
        
        # Update confidence level
        successful_patterns = len(pattern_analysis.get('successful_combinations', []))
        self.state.confidence_level = min(successful_patterns / 10.0, 1.0)
        
        # Update active patterns
        self.state.active_patterns = [
            combo.get('type', 'unknown') 
            for combo in pattern_analysis.get('successful_combinations', [])[:5]
        ]
        
        # Update adaptation triggers
        self.state.adaptation_triggers = [
            action.get('action', 'unknown')
            for action in optimization_strategy.get('actions', [])
            if action.get('priority') == 'high'
        ]
    
    async def _load_neural_patterns(self):
        """Load neural patterns from Claude Flow memory"""
        try:
            # This would integrate with the Claude Flow neural system
            # For now, we'll store basic pattern structure
            self.neural_patterns = {
                'coordination_patterns': {},
                'prediction_patterns': {},
                'optimization_patterns': {}
            }
            
        except Exception as e:
            self.logger.error(f"[UNIFIED_LEARNING] Error loading neural patterns: {e}")
    
    async def _adaptation_loop(self):
        """Main adaptation loop"""
        while True:
            try:
                await asyncio.sleep(self.learning_config['adaptation_frequency'])
                
                # Perform rapid adaptation based on recent performance
                await self._rapid_adaptation()
                
            except Exception as e:
                self.logger.error(f"[UNIFIED_LEARNING] Error in adaptation loop: {e}")
    
    async def _optimization_loop(self):
        """Main optimization loop"""
        while True:
            try:
                await asyncio.sleep(self.learning_config['optimization_frequency'])
                
                # Perform comprehensive optimization
                await self.cross_component_learning()
                
            except Exception as e:
                self.logger.error(f"[UNIFIED_LEARNING] Error in optimization loop: {e}")
    
    async def _pattern_analysis_loop(self):
        """Pattern analysis loop"""
        while True:
            try:
                await asyncio.sleep(self.learning_config['pattern_analysis_frequency'])
                
                # Analyze patterns for immediate insights
                await self._analyze_recent_patterns()
                
            except Exception as e:
                self.logger.error(f"[UNIFIED_LEARNING] Error in pattern analysis loop: {e}")
    
    async def _performance_evaluation_loop(self):
        """Performance evaluation loop"""
        while True:
            try:
                await asyncio.sleep(self.learning_config['performance_evaluation_frequency'])
                
                # Evaluate and update component performance metrics
                await self._evaluate_component_performance()
                
            except Exception as e:
                self.logger.error(f"[UNIFIED_LEARNING] Error in performance evaluation loop: {e}")
    
    async def _rapid_adaptation(self):
        """Perform rapid adaptation based on recent performance"""
        # Quick performance check and immediate adjustments
        recent_performance = self.state.recent_performance
        
        if len(recent_performance) >= 10:
            recent_avg = sum(recent_performance) / len(recent_performance)
            
            if recent_avg < 0.4:  # Poor recent performance
                # Increase exploration
                self.state.learning_phase = 'exploration'
                self.logger.info("[UNIFIED_LEARNING] Switching to exploration mode due to poor performance")
    
    async def _analyze_recent_patterns(self):
        """Analyze recent patterns for immediate insights"""
        # Quick pattern analysis for real-time adaptation
        pass
    
    async def _evaluate_component_performance(self):
        """Evaluate and update component performance metrics"""
        for name, component in self.components.items():
            try:
                # Extract performance data
                if hasattr(component, 'get_performance_summary'):
                    performance_data = await component.get_performance_summary()
                    
                    # Update metrics
                    metrics = self.component_metrics[name]
                    
                    if 'accuracy_rate' in performance_data:
                        metrics.accuracy = performance_data['accuracy_rate']
                    if 'success_rate' in performance_data:
                        metrics.win_rate = performance_data['success_rate']
                    
                    # Calculate adaptation speed based on recent changes
                    metrics.adaptation_speed = self._calculate_adaptation_speed(name)
                    
            except Exception as e:
                self.logger.error(f"[UNIFIED_LEARNING] Error evaluating {name} performance: {e}")
    
    def _calculate_adaptation_speed(self, component_name: str) -> float:
        """Calculate adaptation speed for a component based on its performance history"""
        try:
            # Get recent performance data for the component
            if component_name not in self.component_performance:
                return 0.5  # Default moderate adaptation speed
            
            performance_history = self.component_performance[component_name]
            
            if len(performance_history) < 2:
                return 0.5  # Need at least 2 data points
            
            # Calculate how quickly performance metrics change
            recent_scores = [entry['performance_score'] for entry in performance_history[-10:]]
            
            if len(recent_scores) < 2:
                return 0.5
            
            # Calculate variance in recent performance scores
            # Higher variance indicates faster adaptation (more dynamic behavior)
            import statistics
            variance = statistics.variance(recent_scores) if len(recent_scores) > 1 else 0
            
            # Calculate trend direction (improving vs declining)
            if len(recent_scores) >= 3:
                early_avg = sum(recent_scores[:len(recent_scores)//2]) / len(recent_scores[:len(recent_scores)//2])
                late_avg = sum(recent_scores[len(recent_scores)//2:]) / len(recent_scores[len(recent_scores)//2:])
                trend = abs(late_avg - early_avg)
            else:
                trend = abs(recent_scores[-1] - recent_scores[0])
            
            # Combine variance and trend to get adaptation speed
            # Higher values indicate faster adaptation
            adaptation_speed = min(1.0, (variance * 2) + (trend * 0.5))
            
            # Ensure reasonable bounds
            return max(0.1, min(0.9, adaptation_speed))
            
        except Exception as e:
            logger.warning(f"[LEARNING_SYSTEM] Error calculating adaptation speed for {component_name}: {e}")
            return 0.5  # Safe default
    
    def get_learning_status(self) -> Dict[str, Any]:
        """Get current learning system status"""
        return {
            'learning_phase': self.state.learning_phase,
            'confidence_level': self.state.confidence_level,
            'active_patterns': self.state.active_patterns,
            'adaptation_triggers': self.state.adaptation_triggers,
            'component_count': len(self.components),
            'overall_metrics': self.metrics.to_dict(),
            'component_metrics': {
                name: metrics.to_dict() 
                for name, metrics in self.component_metrics.items()
            }
        }