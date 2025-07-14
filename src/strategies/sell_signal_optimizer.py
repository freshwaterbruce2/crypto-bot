"""
Sell Signal Optimizer
=====================

Advanced sell signal optimization for maximum profit capture and minimal slippage.
Provides real-time market condition analysis and execution timing optimization.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import statistics

logger = logging.getLogger(__name__)


@dataclass
class MarketCondition:
    """Current market condition analysis"""
    volatility: float
    spread_pct: float
    volume_ratio: float
    momentum: float
    liquidity_score: float
    execution_risk: str  # 'low', 'medium', 'high'
    optimal_order_type: str  # 'market', 'limit', 'aggressive_limit'


@dataclass
class OptimizedSellSignal:
    """Optimized sell signal with execution recommendations"""
    original_signal: Dict[str, Any]
    optimized_amount: float
    optimized_price: Optional[float]
    order_type: str
    urgency_level: int  # 1-10
    expected_slippage_pct: float
    confidence_boost: float
    execution_window_seconds: int
    market_conditions: MarketCondition
    optimization_reasons: List[str]


class SellSignalOptimizer:
    """
    Advanced sell signal optimization for micro-profit maximization.
    Analyzes market conditions and optimizes execution parameters.
    """
    
    def __init__(self, config: Dict[str, Any], exchange=None, websocket_manager=None):
        """Initialize sell signal optimizer"""
        self.config = config
        self.exchange = exchange
        self.websocket_manager = websocket_manager
        
        # Optimization parameters
        self.min_spread_for_limit = 0.0005  # 0.05% min spread for limit orders
        self.max_slippage_tolerance = 0.001  # 0.1% max acceptable slippage
        self.liquidity_threshold = 0.8  # Minimum liquidity score
        
        # Market condition thresholds
        self.volatility_thresholds = {
            'low': 0.01,    # 1%
            'medium': 0.03, # 3%
            'high': 0.05    # 5%
        }
        
        # Performance tracking
        self.optimization_history = []
        self.execution_results = []
        
        logger.info("[SELL_OPTIMIZER] Signal optimizer initialized")
    
    async def optimize_sell_signal(self, sell_signal: Dict[str, Any], 
                                 position_data: Dict[str, Any]) -> OptimizedSellSignal:
        """
        Optimize sell signal for maximum profit and minimal slippage.
        
        Args:
            sell_signal: Original sell signal from sell logic
            position_data: Current position and market data
            
        Returns:
            OptimizedSellSignal with execution recommendations
        """
        try:
            symbol = sell_signal.get('symbol', '')
            profit_pct = sell_signal.get('metadata', {}).get('profit_pct', 0)
            confidence = sell_signal.get('confidence', 0.5)
            urgency = sell_signal.get('urgency', 'medium')
            
            # Analyze current market conditions
            market_conditions = await self._analyze_market_conditions(symbol)
            
            # Optimize execution parameters
            optimized_amount = await self._optimize_sell_amount(
                sell_signal, position_data, market_conditions
            )
            
            optimized_price, order_type = await self._optimize_price_and_order_type(
                sell_signal, market_conditions, profit_pct
            )
            
            # Calculate urgency and execution window
            urgency_level, execution_window = self._calculate_execution_urgency(
                sell_signal, market_conditions, profit_pct
            )
            
            # Estimate execution quality
            expected_slippage = self._estimate_slippage(
                symbol, optimized_amount, order_type, market_conditions
            )
            
            # Calculate confidence adjustments
            confidence_boost = self._calculate_confidence_boost(
                market_conditions, profit_pct, expected_slippage
            )
            
            # Generate optimization reasons
            optimization_reasons = self._generate_optimization_reasons(
                sell_signal, market_conditions, order_type, confidence_boost
            )
            
            optimized_signal = OptimizedSellSignal(
                original_signal=sell_signal,
                optimized_amount=optimized_amount,
                optimized_price=optimized_price,
                order_type=order_type,
                urgency_level=urgency_level,
                expected_slippage_pct=expected_slippage,
                confidence_boost=confidence_boost,
                execution_window_seconds=execution_window,
                market_conditions=market_conditions,
                optimization_reasons=optimization_reasons
            )
            
            # Log optimization
            logger.info(f"[SELL_OPTIMIZER] Optimized {symbol}: "
                       f"{order_type} order, {optimized_amount:.8f} @ "
                       f"${optimized_price:.6f if optimized_price else 'market'}, "
                       f"confidence: {confidence:.2f} -> {confidence + confidence_boost:.2f}")
            
            return optimized_signal
            
        except Exception as e:
            logger.error(f"[SELL_OPTIMIZER] Error optimizing sell signal: {e}")
            # Return minimally optimized signal on error
            return OptimizedSellSignal(
                original_signal=sell_signal,
                optimized_amount=sell_signal.get('amount', 0),
                optimized_price=None,
                order_type='market',
                urgency_level=5,
                expected_slippage_pct=0.001,
                confidence_boost=0,
                execution_window_seconds=30,
                market_conditions=MarketCondition(0, 0, 0, 0, 0.5, 'medium', 'market'),
                optimization_reasons=['Optimization error - using safe defaults']
            )
    
    async def _analyze_market_conditions(self, symbol: str) -> MarketCondition:
        """Analyze current market conditions for the symbol"""
        try:
            # Get real-time market data
            if self.websocket_manager:
                ticker_data = await self.websocket_manager.get_ticker(symbol)
            elif self.exchange:
                ticker_data = await self.exchange.fetch_ticker(symbol)
            else:
                # Fallback to minimal market conditions
                return MarketCondition(
                    volatility=0.02,
                    spread_pct=0.001,
                    volume_ratio=1.0,
                    momentum=0.0,
                    liquidity_score=0.8,
                    execution_risk='medium',
                    optimal_order_type='market'
                )
            
            # Calculate market metrics
            last_price = ticker_data.get('last', 0)
            bid = ticker_data.get('bid', last_price * 0.999)
            ask = ticker_data.get('ask', last_price * 1.001)
            volume = ticker_data.get('baseVolume', 0)
            
            # Spread analysis
            spread_pct = (ask - bid) / last_price if last_price > 0 else 0.001
            
            # Volume analysis (simplified - would use historical data in real implementation)
            volume_ratio = min(volume / 1000000, 2.0) if volume > 0 else 1.0  # Normalized volume
            
            # Volatility estimation (simplified)
            volatility = spread_pct * 10  # Rough volatility estimate from spread
            
            # Momentum (would calculate from price changes)
            momentum = 0.0  # Placeholder
            
            # Liquidity score
            liquidity_score = min(1.0, volume_ratio * (1 - spread_pct * 100))
            
            # Execution risk assessment
            if spread_pct > 0.002 or volatility > 0.05:
                execution_risk = 'high'
                optimal_order_type = 'market'  # Use market orders in high-risk conditions
            elif spread_pct > 0.001 or volatility > 0.02:
                execution_risk = 'medium'
                optimal_order_type = 'aggressive_limit'
            else:
                execution_risk = 'low'
                optimal_order_type = 'limit'
            
            return MarketCondition(
                volatility=volatility,
                spread_pct=spread_pct,
                volume_ratio=volume_ratio,
                momentum=momentum,
                liquidity_score=liquidity_score,
                execution_risk=execution_risk,
                optimal_order_type=optimal_order_type
            )
            
        except Exception as e:
            logger.error(f"[SELL_OPTIMIZER] Error analyzing market conditions: {e}")
            # Return safe default conditions
            return MarketCondition(
                volatility=0.02,
                spread_pct=0.001,
                volume_ratio=1.0,
                momentum=0.0,
                liquidity_score=0.7,
                execution_risk='medium',
                optimal_order_type='market'
            )
    
    async def _optimize_sell_amount(self, sell_signal: Dict[str, Any], 
                                  position_data: Dict[str, Any], 
                                  market_conditions: MarketCondition) -> float:
        """Optimize the sell amount based on market conditions"""
        original_amount = sell_signal.get('amount', position_data.get('amount', 0))
        suggested_percentage = sell_signal.get('suggested_percentage', 1.0)
        
        # Start with suggested amount
        base_amount = original_amount * suggested_percentage
        
        # Adjust based on market conditions
        if market_conditions.execution_risk == 'high':
            # In high-risk conditions, prefer smaller orders for better execution
            if market_conditions.liquidity_score < 0.5:
                base_amount *= 0.7  # Reduce by 30%
        elif market_conditions.execution_risk == 'low' and market_conditions.liquidity_score > 0.9:
            # In excellent conditions, can sell full amount
            base_amount = original_amount
        
        # Ensure minimum viable amount
        min_viable_amount = self.config.get('min_order_size_usdt', 2.0) / position_data.get('current_price', 1)
        
        return max(base_amount, min_viable_amount)
    
    async def _optimize_price_and_order_type(self, sell_signal: Dict[str, Any], 
                                           market_conditions: MarketCondition, 
                                           profit_pct: float) -> Tuple[Optional[float], str]:
        """Optimize price and order type for execution"""
        symbol = sell_signal.get('symbol', '')
        urgency = sell_signal.get('urgency', 'medium')
        
        # For micro-profits, prioritize speed over price optimization
        if profit_pct <= 0.5:  # 0.5% or less
            return None, 'market'  # Market order for immediate execution
        
        # For emergency/critical sells, use market orders
        if urgency in ['critical', 'emergency']:
            return None, 'market'
        
        # Use market conditions to determine optimal approach
        if market_conditions.execution_risk == 'high':
            return None, 'market'
        
        # For good market conditions and larger profits, try to optimize price
        if market_conditions.spread_pct < self.min_spread_for_limit and profit_pct > 1.0:
            # Get current market price
            try:
                if self.websocket_manager:
                    ticker = await self.websocket_manager.get_ticker(symbol)
                elif self.exchange:
                    ticker = await self.exchange.fetch_ticker(symbol)
                else:
                    return None, 'market'
                
                current_price = ticker.get('last', 0)
                bid = ticker.get('bid', current_price * 0.999)
                
                # Place limit order slightly above current bid
                optimized_price = bid + (market_conditions.spread_pct * current_price * 0.3)
                
                return optimized_price, 'limit'
                
            except Exception as e:
                logger.error(f"[SELL_OPTIMIZER] Error optimizing price: {e}")
                return None, 'market'
        
        # Default to aggressive limit for medium conditions
        return None, market_conditions.optimal_order_type
    
    def _calculate_execution_urgency(self, sell_signal: Dict[str, Any], 
                                   market_conditions: MarketCondition, 
                                   profit_pct: float) -> Tuple[int, int]:
        """Calculate execution urgency level and time window"""
        base_urgency = {
            'low': 3,
            'medium': 5,
            'high': 7,
            'critical': 9
        }.get(sell_signal.get('urgency', 'medium'), 5)
        
        # Adjust urgency based on profit and market conditions
        urgency_adjustments = 0
        
        # Profit-based adjustments
        if profit_pct >= 2.0:  # 2%+ profit
            urgency_adjustments += 2  # Higher urgency for large profits
        elif profit_pct <= 0.2:  # 0.2% or less
            urgency_adjustments += 1  # Medium urgency for micro-profits
        
        # Market condition adjustments
        if market_conditions.execution_risk == 'high':
            urgency_adjustments += 2
        elif market_conditions.volatility > 0.05:  # High volatility
            urgency_adjustments += 1
        
        final_urgency = min(10, base_urgency + urgency_adjustments)
        
        # Calculate execution window
        execution_windows = {
            1: 300,  # 5 minutes
            2: 240,  # 4 minutes
            3: 180,  # 3 minutes
            4: 120,  # 2 minutes
            5: 90,   # 1.5 minutes
            6: 60,   # 1 minute
            7: 30,   # 30 seconds
            8: 15,   # 15 seconds
            9: 10,   # 10 seconds
            10: 5    # 5 seconds
        }
        
        execution_window = execution_windows.get(final_urgency, 60)
        
        return final_urgency, execution_window
    
    def _estimate_slippage(self, symbol: str, amount: float, order_type: str, 
                          market_conditions: MarketCondition) -> float:
        """Estimate expected slippage for the order"""
        base_slippage = market_conditions.spread_pct / 2  # Half spread as base
        
        # Order type adjustments
        if order_type == 'market':
            slippage_multiplier = 1.5  # Market orders have higher slippage
        elif order_type == 'aggressive_limit':
            slippage_multiplier = 0.8
        else:  # limit orders
            slippage_multiplier = 0.3
        
        # Liquidity adjustments
        liquidity_multiplier = 2.0 - market_conditions.liquidity_score
        
        # Volatility adjustments
        volatility_multiplier = 1.0 + market_conditions.volatility * 10
        
        estimated_slippage = base_slippage * slippage_multiplier * liquidity_multiplier * volatility_multiplier
        
        return min(estimated_slippage, self.max_slippage_tolerance * 2)  # Cap at 2x tolerance
    
    def _calculate_confidence_boost(self, market_conditions: MarketCondition, 
                                  profit_pct: float, expected_slippage: float) -> float:
        """Calculate confidence boost based on optimization"""
        boost = 0.0
        
        # Market condition boost
        if market_conditions.execution_risk == 'low':
            boost += 0.1
        elif market_conditions.liquidity_score > 0.9:
            boost += 0.05
        
        # Profit size boost
        if profit_pct >= 1.0:  # 1%+ profit
            boost += 0.1
        elif profit_pct >= 0.5:  # 0.5%+ profit
            boost += 0.05
        
        # Low slippage boost
        if expected_slippage < self.max_slippage_tolerance / 2:
            boost += 0.05
        
        return min(boost, 0.25)  # Cap boost at 0.25
    
    def _generate_optimization_reasons(self, sell_signal: Dict[str, Any], 
                                     market_conditions: MarketCondition, 
                                     order_type: str, confidence_boost: float) -> List[str]:
        """Generate human-readable optimization reasons"""
        reasons = []
        
        # Market condition reasons
        if market_conditions.execution_risk == 'low':
            reasons.append(f"Excellent market conditions (spread: {market_conditions.spread_pct:.3%})")
        elif market_conditions.execution_risk == 'high':
            reasons.append(f"High-risk market conditions - prioritizing execution speed")
        
        # Order type optimization
        if order_type == 'market':
            reasons.append("Market order selected for immediate execution")
        elif order_type == 'limit':
            reasons.append("Limit order optimized for better price")
        elif order_type == 'aggressive_limit':
            reasons.append("Aggressive limit order balancing price and speed")
        
        # Confidence improvements
        if confidence_boost > 0.1:
            reasons.append(f"High confidence boost (+{confidence_boost:.2f}) from optimization")
        elif confidence_boost > 0.05:
            reasons.append(f"Moderate confidence boost (+{confidence_boost:.2f})")
        
        # Liquidity assessment
        if market_conditions.liquidity_score > 0.9:
            reasons.append("Excellent liquidity conditions")
        elif market_conditions.liquidity_score < 0.5:
            reasons.append("Limited liquidity - using conservative approach")
        
        return reasons if reasons else ["Standard optimization applied"]
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization performance statistics"""
        if not self.optimization_history:
            return {'message': 'No optimization history available'}
        
        recent_optimizations = self.optimization_history[-100:]  # Last 100
        
        order_type_distribution = {}
        avg_confidence_boost = 0
        avg_slippage_estimate = 0
        
        for opt in recent_optimizations:
            order_type = opt.get('order_type', 'unknown')
            order_type_distribution[order_type] = order_type_distribution.get(order_type, 0) + 1
            avg_confidence_boost += opt.get('confidence_boost', 0)
            avg_slippage_estimate += opt.get('expected_slippage_pct', 0)
        
        count = len(recent_optimizations)
        avg_confidence_boost /= count
        avg_slippage_estimate /= count
        
        return {
            'total_optimizations': len(self.optimization_history),
            'recent_optimizations': count,
            'order_type_distribution': order_type_distribution,
            'avg_confidence_boost': avg_confidence_boost,
            'avg_slippage_estimate': avg_slippage_estimate,
            'optimization_success_indicators': {
                'low_slippage_rate': sum(1 for opt in recent_optimizations 
                                       if opt.get('expected_slippage_pct', 0) < 0.001) / count,
                'high_confidence_rate': sum(1 for opt in recent_optimizations 
                                          if opt.get('confidence_boost', 0) > 0.1) / count
            }
        }