"""
Advanced Portfolio Rebalancing Engine
Intelligent rebalancing with multiple triggers and optimization algorithms
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class RebalanceTrigger(Enum):
    """Rebalancing trigger types"""
    TIME_BASED = "time_based"
    DEVIATION_BASED = "deviation_based"
    VOLATILITY_BASED = "volatility_based"
    CORRELATION_BASED = "correlation_based"
    MOMENTUM_BASED = "momentum_based"
    DRAWDOWN_BASED = "drawdown_based"
    EMERGENCY = "emergency"


class RebalanceStrategy(Enum):
    """Rebalancing strategy types"""
    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP_WEIGHT = "market_cap_weight"
    RISK_PARITY = "risk_parity"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_DIVERSIFICATION = "maximum_diversification"
    MOMENTUM_TILT = "momentum_tilt"
    MEAN_REVERSION = "mean_reversion"
    KELLY_OPTIMAL = "kelly_optimal"


@dataclass
class RebalanceAction:
    """Individual rebalancing action"""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    current_weight: float
    target_weight: float
    weight_deviation: float
    amount_usd: float
    priority: int
    reason: str
    urgency: str  # 'low', 'medium', 'high', 'critical'


@dataclass
class RebalanceProposal:
    """Complete rebalancing proposal"""
    trigger: RebalanceTrigger
    strategy: RebalanceStrategy
    actions: List[RebalanceAction]
    total_turnover: float
    estimated_cost: float
    expected_benefit: float
    confidence: float
    execution_order: List[str]
    created_at: datetime


class PortfolioRebalancer:
    """
    Advanced portfolio rebalancing engine with multiple strategies and triggers
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize portfolio rebalancer"""
        self.config = config
        
        # Rebalancing triggers configuration
        self.time_trigger_hours = config.get('time_trigger_hours', 24)  # Daily rebalancing
        self.deviation_threshold = config.get('deviation_threshold', 0.05)  # 5% deviation
        self.volatility_threshold = config.get('volatility_threshold', 0.08)  # 8% daily vol
        self.correlation_threshold = config.get('correlation_threshold', 0.85)  # 85% correlation
        self.drawdown_threshold = config.get('drawdown_threshold', 0.10)  # 10% drawdown
        
        # Transaction cost parameters
        self.transaction_cost_bps = config.get('transaction_cost_bps', 10)  # 10 basis points
        self.minimum_trade_size = config.get('minimum_trade_size', 5.0)  # $5 minimum
        self.slippage_bps = config.get('slippage_bps', 5)  # 5 basis points slippage
        
        # Risk parameters
        self.max_position_size = config.get('max_position_size', 0.25)  # 25% max per asset
        self.min_position_size = config.get('min_position_size', 0.01)  # 1% minimum
        self.cash_buffer = config.get('cash_buffer', 0.05)  # 5% cash buffer
        
        # Optimization parameters
        self.lookback_periods = config.get('lookback_periods', 30)  # 30 periods for analysis
        self.confidence_threshold = config.get('confidence_threshold', 0.6)  # 60% minimum confidence
        self.max_turnover = config.get('max_turnover', 0.3)  # 30% max turnover per rebalance
        
        # State tracking
        self.last_rebalance = {}  # Per trigger type
        self.rebalance_history = []
        self.performance_metrics = {}
        
        # Asset universe and constraints
        self.asset_universe = set()
        self.asset_constraints = {}
        
        logger.info("[PORTFOLIO_REBALANCER] Advanced portfolio rebalancer initialized")
    
    async def evaluate_rebalancing_need(self, portfolio: Dict[str, Any], 
                                      market_data: Dict[str, Any],
                                      correlation_matrix: Dict[str, Dict[str, float]]) -> List[RebalanceProposal]:
        """Evaluate if portfolio needs rebalancing and generate proposals"""
        try:
            proposals = []
            
            # Check each trigger type
            triggers_to_check = [
                RebalanceTrigger.TIME_BASED,
                RebalanceTrigger.DEVIATION_BASED,
                RebalanceTrigger.VOLATILITY_BASED,
                RebalanceTrigger.CORRELATION_BASED,
                RebalanceTrigger.MOMENTUM_BASED,
                RebalanceTrigger.DRAWDOWN_BASED
            ]
            
            for trigger in triggers_to_check:
                should_trigger, urgency = await self._check_trigger(
                    trigger, portfolio, market_data, correlation_matrix
                )
                
                if should_trigger:
                    # Generate rebalancing proposal for this trigger
                    proposal = await self._generate_rebalance_proposal(
                        trigger, portfolio, market_data, correlation_matrix, urgency
                    )
                    
                    if proposal and proposal.confidence >= self.confidence_threshold:
                        proposals.append(proposal)
                        logger.info(f"[PORTFOLIO_REBALANCER] Generated {trigger.value} proposal "
                                  f"with {len(proposal.actions)} actions")
            
            # Sort proposals by urgency and expected benefit
            proposals.sort(key=lambda p: (
                ['low', 'medium', 'high', 'critical'].index(
                    max([a.urgency for a in p.actions], default='low')
                ),
                -p.expected_benefit
            ), reverse=True)
            
            return proposals
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error evaluating rebalancing need: {e}")
            return []
    
    async def _check_trigger(self, trigger: RebalanceTrigger, portfolio: Dict[str, Any],
                           market_data: Dict[str, Any], 
                           correlation_matrix: Dict[str, Dict[str, float]]) -> Tuple[bool, str]:
        """Check if specific trigger condition is met"""
        try:
            now = datetime.now()
            last_trigger = self.last_rebalance.get(trigger, datetime.min)
            
            if trigger == RebalanceTrigger.TIME_BASED:
                # Time-based trigger
                hours_since_last = (now - last_trigger).total_seconds() / 3600
                should_trigger = hours_since_last >= self.time_trigger_hours
                urgency = 'low' if should_trigger else 'none'
                
            elif trigger == RebalanceTrigger.DEVIATION_BASED:
                # Weight deviation trigger
                max_deviation = await self._calculate_max_weight_deviation(portfolio)
                should_trigger = max_deviation > self.deviation_threshold
                if max_deviation > self.deviation_threshold * 2:
                    urgency = 'high'
                elif max_deviation > self.deviation_threshold * 1.5:
                    urgency = 'medium'
                else:
                    urgency = 'low' if should_trigger else 'none'
                    
            elif trigger == RebalanceTrigger.VOLATILITY_BASED:
                # Volatility spike trigger
                portfolio_vol = await self._calculate_portfolio_volatility(portfolio, market_data)
                should_trigger = portfolio_vol > self.volatility_threshold
                if portfolio_vol > self.volatility_threshold * 2:
                    urgency = 'critical'
                elif portfolio_vol > self.volatility_threshold * 1.5:
                    urgency = 'high'
                else:
                    urgency = 'medium' if should_trigger else 'none'
                    
            elif trigger == RebalanceTrigger.CORRELATION_BASED:
                # High correlation trigger
                avg_correlation = await self._calculate_average_correlation(correlation_matrix)
                should_trigger = avg_correlation > self.correlation_threshold
                urgency = 'high' if avg_correlation > 0.9 else 'medium' if should_trigger else 'none'
                
            elif trigger == RebalanceTrigger.MOMENTUM_BASED:
                # Momentum shift trigger
                momentum_signal = await self._detect_momentum_shift(portfolio, market_data)
                should_trigger = abs(momentum_signal) > 0.7
                urgency = 'medium' if should_trigger else 'none'
                
            elif trigger == RebalanceTrigger.DRAWDOWN_BASED:
                # Drawdown trigger
                current_drawdown = await self._calculate_portfolio_drawdown(portfolio)
                should_trigger = current_drawdown > self.drawdown_threshold
                if current_drawdown > self.drawdown_threshold * 2:
                    urgency = 'critical'
                elif current_drawdown > self.drawdown_threshold * 1.5:
                    urgency = 'high'
                else:
                    urgency = 'medium' if should_trigger else 'none'
                    
            else:
                should_trigger = False
                urgency = 'none'
            
            return should_trigger, urgency
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error checking trigger {trigger}: {e}")
            return False, 'none'
    
    async def _generate_rebalance_proposal(self, trigger: RebalanceTrigger, 
                                         portfolio: Dict[str, Any],
                                         market_data: Dict[str, Any],
                                         correlation_matrix: Dict[str, Dict[str, float]],
                                         urgency: str) -> Optional[RebalanceProposal]:
        """Generate rebalancing proposal for specific trigger"""
        try:
            # Determine optimal rebalancing strategy for this trigger
            if trigger == RebalanceTrigger.VOLATILITY_BASED:
                strategy = RebalanceStrategy.MINIMUM_VARIANCE
            elif trigger == RebalanceTrigger.CORRELATION_BASED:
                strategy = RebalanceStrategy.MAXIMUM_DIVERSIFICATION
            elif trigger == RebalanceTrigger.MOMENTUM_BASED:
                strategy = RebalanceStrategy.MOMENTUM_TILT
            elif trigger == RebalanceTrigger.DRAWDOWN_BASED:
                strategy = RebalanceStrategy.RISK_PARITY
            else:
                strategy = RebalanceStrategy.RISK_PARITY  # Default
            
            # Calculate target weights
            target_weights = await self._calculate_target_weights(
                strategy, portfolio, market_data, correlation_matrix
            )
            
            if not target_weights:
                return None
            
            # Generate rebalancing actions
            actions = await self._generate_rebalance_actions(
                portfolio, target_weights, urgency
            )
            
            if not actions:
                return None
            
            # Calculate proposal metrics
            total_turnover = sum(abs(action.weight_deviation) for action in actions)
            estimated_cost = await self._estimate_transaction_costs(actions)
            expected_benefit = await self._estimate_rebalance_benefit(
                actions, strategy, correlation_matrix
            )
            
            # Calculate confidence based on multiple factors
            confidence = await self._calculate_proposal_confidence(
                trigger, strategy, actions, total_turnover, expected_benefit
            )
            
            # Determine execution order
            execution_order = await self._optimize_execution_order(actions)
            
            proposal = RebalanceProposal(
                trigger=trigger,
                strategy=strategy,
                actions=actions,
                total_turnover=total_turnover,
                estimated_cost=estimated_cost,
                expected_benefit=expected_benefit,
                confidence=confidence,
                execution_order=execution_order,
                created_at=datetime.now()
            )
            
            return proposal
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error generating proposal: {e}")
            return None
    
    async def _calculate_target_weights(self, strategy: RebalanceStrategy,
                                      portfolio: Dict[str, Any],
                                      market_data: Dict[str, Any],
                                      correlation_matrix: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate target weights based on strategy"""
        try:
            positions = portfolio.get('positions', {})
            active_assets = [asset for asset, pos in positions.items() 
                           if pos.get('value_usd', 0) > 0 and asset not in ['USDT', 'USDC', 'USD']]
            
            if not active_assets:
                return {}
            
            if strategy == RebalanceStrategy.EQUAL_WEIGHT:
                # Equal weight allocation
                weight_per_asset = (1.0 - self.cash_buffer) / len(active_assets)
                return {asset: weight_per_asset for asset in active_assets}
                
            elif strategy == RebalanceStrategy.MARKET_CAP_WEIGHT:
                # Market cap weighted (simplified)
                return await self._calculate_market_cap_weights(active_assets, market_data)
                
            elif strategy == RebalanceStrategy.RISK_PARITY:
                # Risk parity allocation
                return await self._calculate_risk_parity_weights(active_assets, market_data)
                
            elif strategy == RebalanceStrategy.MINIMUM_VARIANCE:
                # Minimum variance optimization
                return await self._calculate_minimum_variance_weights(
                    active_assets, correlation_matrix, market_data
                )
                
            elif strategy == RebalanceStrategy.MAXIMUM_DIVERSIFICATION:
                # Maximum diversification
                return await self._calculate_max_diversification_weights(
                    active_assets, correlation_matrix, market_data
                )
                
            elif strategy == RebalanceStrategy.MOMENTUM_TILT:
                # Momentum-tilted allocation
                return await self._calculate_momentum_weights(active_assets, market_data)
                
            elif strategy == RebalanceStrategy.MEAN_REVERSION:
                # Mean reversion allocation
                return await self._calculate_mean_reversion_weights(active_assets, market_data)
                
            elif strategy == RebalanceStrategy.KELLY_OPTIMAL:
                # Kelly criterion optimization
                return await self._calculate_kelly_weights(active_assets, market_data)
                
            else:
                # Default to equal weight
                weight_per_asset = (1.0 - self.cash_buffer) / len(active_assets)
                return {asset: weight_per_asset for asset in active_assets}
                
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error calculating target weights: {e}")
            return {}
    
    async def _calculate_risk_parity_weights(self, assets: List[str], 
                                           market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate risk parity weights (inverse volatility weighting)"""
        try:
            volatilities = {}
            
            for asset in assets:
                asset_data = market_data.get(asset, {})
                price_history = asset_data.get('price_history', [])
                
                if len(price_history) >= 10:
                    returns = np.diff(price_history) / price_history[:-1]
                    vol = np.std(returns)
                else:
                    vol = 0.05  # Default 5% volatility
                    
                volatilities[asset] = max(0.001, vol)  # Minimum volatility
            
            # Inverse volatility weights
            inv_vol_weights = {asset: 1.0 / vol for asset, vol in volatilities.items()}
            
            # Normalize to sum to (1 - cash_buffer)
            total_weight = sum(inv_vol_weights.values())
            target_total = 1.0 - self.cash_buffer
            
            weights = {
                asset: (weight / total_weight) * target_total
                for asset, weight in inv_vol_weights.items()
            }
            
            # Apply position size constraints
            for asset in weights:
                weights[asset] = max(self.min_position_size, 
                                   min(self.max_position_size, weights[asset]))
            
            return weights
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error calculating risk parity weights: {e}")
            return {}
    
    async def _calculate_minimum_variance_weights(self, assets: List[str],
                                                correlation_matrix: Dict[str, Dict[str, float]],
                                                market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate minimum variance portfolio weights"""
        try:
            n = len(assets)
            if n < 2:
                return {assets[0]: 1.0 - self.cash_buffer} if assets else {}
            
            # Build covariance matrix
            cov_matrix = np.zeros((n, n))
            volatilities = []
            
            for i, asset in enumerate(assets):
                asset_data = market_data.get(asset, {})
                price_history = asset_data.get('price_history', [])
                
                if len(price_history) >= 10:
                    returns = np.diff(price_history) / price_history[:-1]
                    vol = np.std(returns)
                else:
                    vol = 0.05  # Default volatility
                    
                volatilities.append(vol)
            
            # Fill covariance matrix
            for i, asset1 in enumerate(assets):
                for j, asset2 in enumerate(assets):
                    if i == j:
                        cov_matrix[i, j] = volatilities[i] ** 2
                    else:
                        correlation = correlation_matrix.get(asset1, {}).get(asset2, 0.5)
                        cov_matrix[i, j] = correlation * volatilities[i] * volatilities[j]
            
            # Optimization: minimize w^T * Σ * w subject to constraints
            def objective(weights):
                return np.dot(weights, np.dot(cov_matrix, weights))
            
            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - (1.0 - self.cash_buffer)}
            ]
            
            # Bounds
            bounds = [(self.min_position_size, self.max_position_size) for _ in assets]
            
            # Initial guess (equal weights)
            x0 = np.array([(1.0 - self.cash_buffer) / n] * n)
            
            # Optimize
            result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
            
            if result.success:
                weights = {asset: weight for asset, weight in zip(assets, result.x)}
                return weights
            else:
                # Fallback to equal weights
                equal_weight = (1.0 - self.cash_buffer) / n
                return {asset: equal_weight for asset in assets}
                
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error calculating minimum variance weights: {e}")
            return {}
    
    async def _calculate_max_diversification_weights(self, assets: List[str],
                                                   correlation_matrix: Dict[str, Dict[str, float]],
                                                   market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate maximum diversification portfolio weights"""
        try:
            n = len(assets)
            if n < 2:
                return {assets[0]: 1.0 - self.cash_buffer} if assets else {}
            
            # Get volatilities
            volatilities = []
            for asset in assets:
                asset_data = market_data.get(asset, {})
                price_history = asset_data.get('price_history', [])
                
                if len(price_history) >= 10:
                    returns = np.diff(price_history) / price_history[:-1]
                    vol = np.std(returns)
                else:
                    vol = 0.05
                    
                volatilities.append(vol)
            
            vol_array = np.array(volatilities)
            
            # Build correlation matrix
            corr_matrix = np.zeros((n, n))
            for i, asset1 in enumerate(assets):
                for j, asset2 in enumerate(assets):
                    if i == j:
                        corr_matrix[i, j] = 1.0
                    else:
                        corr_matrix[i, j] = correlation_matrix.get(asset1, {}).get(asset2, 0.5)
            
            # Diversification ratio = (w^T * σ) / sqrt(w^T * Σ * w)
            # Maximize this by minimizing its inverse
            def objective(weights):
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(
                    corr_matrix * np.outer(vol_array, vol_array), weights
                )))
                weighted_avg_vol = np.dot(weights, vol_array)
                
                if portfolio_vol > 0:
                    return portfolio_vol / weighted_avg_vol  # Minimize inverse of diversification ratio
                else:
                    return 1.0
            
            # Constraints and bounds
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - (1.0 - self.cash_buffer)}
            ]
            bounds = [(self.min_position_size, self.max_position_size) for _ in assets]
            x0 = np.array([(1.0 - self.cash_buffer) / n] * n)
            
            result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
            
            if result.success:
                weights = {asset: weight for asset, weight in zip(assets, result.x)}
                return weights
            else:
                # Fallback to inverse correlation weighting
                return await self._calculate_inverse_correlation_weights(assets, correlation_matrix)
                
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error calculating max diversification weights: {e}")
            return {}
    
    async def _calculate_momentum_weights(self, assets: List[str], 
                                        market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate momentum-tilted weights"""
        try:
            momentum_scores = {}
            
            for asset in assets:
                asset_data = market_data.get(asset, {})
                price_history = asset_data.get('price_history', [])
                
                if len(price_history) >= 20:
                    # Multiple timeframe momentum
                    short_momentum = (price_history[-1] - price_history[-5]) / price_history[-5]
                    medium_momentum = (price_history[-1] - price_history[-10]) / price_history[-10]
                    long_momentum = (price_history[-1] - price_history[-20]) / price_history[-20]
                    
                    # Weighted momentum score
                    momentum_score = 0.5 * short_momentum + 0.3 * medium_momentum + 0.2 * long_momentum
                else:
                    momentum_score = 0.0
                    
                momentum_scores[asset] = momentum_score
            
            # Convert to positive weights
            min_momentum = min(momentum_scores.values())
            adjusted_scores = {
                asset: score - min_momentum + 0.1  # Add small base to avoid zero weights
                for asset, score in momentum_scores.items()
            }
            
            # Normalize weights
            total_score = sum(adjusted_scores.values())
            target_total = 1.0 - self.cash_buffer
            
            weights = {
                asset: (score / total_score) * target_total
                for asset, score in adjusted_scores.items()
            }
            
            # Apply constraints
            for asset in weights:
                weights[asset] = max(self.min_position_size, 
                                   min(self.max_position_size, weights[asset]))
            
            return weights
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error calculating momentum weights: {e}")
            return {}
    
    async def _generate_rebalance_actions(self, portfolio: Dict[str, Any],
                                        target_weights: Dict[str, float],
                                        urgency: str) -> List[RebalanceAction]:
        """Generate specific rebalancing actions"""
        try:
            actions = []
            positions = portfolio.get('positions', {})
            total_value = portfolio.get('total_value_usd', 0)
            
            if total_value <= 0:
                return actions
            
            # Calculate current weights
            current_weights = {}
            for asset, position in positions.items():
                if asset not in ['USDT', 'USDC', 'USD']:
                    current_weight = position.get('value_usd', 0) / total_value
                    current_weights[asset] = current_weight
            
            # Generate actions for each asset
            priority = 1
            for asset, target_weight in target_weights.items():
                current_weight = current_weights.get(asset, 0)
                weight_deviation = target_weight - current_weight
                
                # Skip small deviations unless urgent
                if abs(weight_deviation) < 0.01 and urgency not in ['high', 'critical']:
                    continue
                
                # Calculate trade amount
                amount_usd = abs(weight_deviation) * total_value
                
                if amount_usd < self.minimum_trade_size:
                    continue
                
                # Determine action
                if weight_deviation > 0.01:
                    action = 'buy'
                elif weight_deviation < -0.01:
                    action = 'sell'
                else:
                    action = 'hold'
                
                if action != 'hold':
                    rebalance_action = RebalanceAction(
                        symbol=asset,
                        action=action,
                        current_weight=current_weight,
                        target_weight=target_weight,
                        weight_deviation=weight_deviation,
                        amount_usd=amount_usd,
                        priority=priority,
                        reason=f"Rebalance to target allocation",
                        urgency=urgency
                    )
                    
                    actions.append(rebalance_action)
                    priority += 1
            
            # Sort by priority (largest deviations first)
            actions.sort(key=lambda a: abs(a.weight_deviation), reverse=True)
            
            # Update priorities
            for i, action in enumerate(actions):
                action.priority = i + 1
            
            return actions
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error generating rebalance actions: {e}")
            return []
    
    async def _estimate_transaction_costs(self, actions: List[RebalanceAction]) -> float:
        """Estimate total transaction costs for rebalancing"""
        try:
            total_cost = 0.0
            
            for action in actions:
                # Transaction cost = amount * (spread + commission + slippage)
                trade_value = action.amount_usd
                
                # Commission cost
                commission = trade_value * (self.transaction_cost_bps / 10000)
                
                # Slippage cost (simplified)
                slippage = trade_value * (self.slippage_bps / 10000)
                
                # Spread cost (estimate 0.1% for crypto)
                spread = trade_value * 0.001
                
                action_cost = commission + slippage + spread
                total_cost += action_cost
            
            return total_cost
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error estimating transaction costs: {e}")
            return 0.0
    
    async def _estimate_rebalance_benefit(self, actions: List[RebalanceAction],
                                        strategy: RebalanceStrategy,
                                        correlation_matrix: Dict[str, Dict[str, float]]) -> float:
        """Estimate expected benefit from rebalancing"""
        try:
            # Benefit estimation based on strategy type
            if strategy in [RebalanceStrategy.MINIMUM_VARIANCE, RebalanceStrategy.RISK_PARITY]:
                # Risk reduction benefit
                risk_reduction = sum(abs(action.weight_deviation) for action in actions) * 0.1
                return risk_reduction
                
            elif strategy == RebalanceStrategy.MAXIMUM_DIVERSIFICATION:
                # Diversification benefit
                diversification_improvement = len(actions) * 0.05
                return diversification_improvement
                
            elif strategy == RebalanceStrategy.MOMENTUM_TILT:
                # Momentum capture benefit
                momentum_benefit = sum(
                    abs(action.weight_deviation) for action in actions 
                    if action.action == 'buy'
                ) * 0.02
                return momentum_benefit
                
            else:
                # Generic rebalancing benefit
                return sum(abs(action.weight_deviation) for action in actions) * 0.01
                
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error estimating rebalance benefit: {e}")
            return 0.0
    
    async def _calculate_proposal_confidence(self, trigger: RebalanceTrigger,
                                           strategy: RebalanceStrategy,
                                           actions: List[RebalanceAction],
                                           total_turnover: float,
                                           expected_benefit: float) -> float:
        """Calculate confidence score for rebalancing proposal"""
        try:
            confidence_factors = []
            
            # Trigger confidence
            if trigger in [RebalanceTrigger.EMERGENCY, RebalanceTrigger.DRAWDOWN_BASED]:
                confidence_factors.append(0.9)  # High confidence for emergency situations
            elif trigger in [RebalanceTrigger.VOLATILITY_BASED, RebalanceTrigger.CORRELATION_BASED]:
                confidence_factors.append(0.8)  # High confidence for risk-based triggers
            else:
                confidence_factors.append(0.6)  # Moderate confidence for other triggers
            
            # Strategy confidence
            if strategy in [RebalanceStrategy.RISK_PARITY, RebalanceStrategy.MINIMUM_VARIANCE]:
                confidence_factors.append(0.8)  # High confidence in risk-based strategies
            else:
                confidence_factors.append(0.6)  # Moderate confidence in other strategies
            
            # Action quality confidence
            if len(actions) > 0:
                avg_deviation = np.mean([abs(a.weight_deviation) for a in actions])
                if avg_deviation > 0.1:  # Large deviations
                    confidence_factors.append(0.9)
                elif avg_deviation > 0.05:  # Medium deviations
                    confidence_factors.append(0.7)
                else:  # Small deviations
                    confidence_factors.append(0.5)
            else:
                confidence_factors.append(0.0)
            
            # Benefit vs cost confidence
            if expected_benefit > 0.01:  # Meaningful expected benefit
                confidence_factors.append(0.8)
            elif expected_benefit > 0.005:  # Small expected benefit
                confidence_factors.append(0.6)
            else:
                confidence_factors.append(0.3)
            
            # Turnover confidence (prefer lower turnover)
            if total_turnover < 0.1:  # Low turnover
                confidence_factors.append(0.8)
            elif total_turnover < 0.2:  # Medium turnover
                confidence_factors.append(0.6)
            else:  # High turnover
                confidence_factors.append(0.4)
            
            # Calculate weighted average confidence
            confidence = np.mean(confidence_factors)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error calculating proposal confidence: {e}")
            return 0.0
    
    async def _optimize_execution_order(self, actions: List[RebalanceAction]) -> List[str]:
        """Optimize the execution order of rebalancing actions"""
        try:
            # Sort by priority and urgency
            sell_actions = [a for a in actions if a.action == 'sell']
            buy_actions = [a for a in actions if a.action == 'buy']
            
            # Execute sells first to free up capital
            sell_actions.sort(key=lambda a: (
                ['low', 'medium', 'high', 'critical'].index(a.urgency),
                -abs(a.weight_deviation)
            ), reverse=True)
            
            # Then execute buys
            buy_actions.sort(key=lambda a: (
                ['low', 'medium', 'high', 'critical'].index(a.urgency),
                -abs(a.weight_deviation)
            ), reverse=True)
            
            # Combine in optimal order
            execution_order = [a.symbol for a in sell_actions] + [a.symbol for a in buy_actions]
            
            return execution_order
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error optimizing execution order: {e}")
            return [a.symbol for a in actions]
    
    async def execute_rebalance_proposal(self, proposal: RebalanceProposal,
                                       exchange_client: Any) -> Dict[str, Any]:
        """Execute approved rebalancing proposal"""
        try:
            execution_results = {
                'proposal_id': f"{proposal.trigger.value}_{proposal.created_at.timestamp()}",
                'strategy': proposal.strategy.value,
                'executed_actions': [],
                'failed_actions': [],
                'total_cost': 0.0,
                'execution_time': datetime.now(),
                'success_rate': 0.0
            }
            
            logger.info(f"[PORTFOLIO_REBALANCER] Executing {proposal.strategy.value} rebalancing "
                       f"with {len(proposal.actions)} actions")
            
            # Execute actions in optimized order
            for symbol in proposal.execution_order:
                # Find corresponding action
                action = next((a for a in proposal.actions if a.symbol == symbol), None)
                if not action:
                    continue
                
                try:
                    # Execute the trade
                    result = await self._execute_rebalance_trade(action, exchange_client)
                    
                    if result['success']:
                        execution_results['executed_actions'].append({
                            'symbol': symbol,
                            'action': action.action,
                            'amount': result['amount'],
                            'price': result['price'],
                            'cost': result['cost']
                        })
                        execution_results['total_cost'] += result['cost']
                    else:
                        execution_results['failed_actions'].append({
                            'symbol': symbol,
                            'action': action.action,
                            'error': result['error']
                        })
                    
                    # Small delay between trades
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"[PORTFOLIO_REBALANCER] Error executing trade for {symbol}: {e}")
                    execution_results['failed_actions'].append({
                        'symbol': symbol,
                        'action': action.action,
                        'error': str(e)
                    })
            
            # Calculate success rate
            total_actions = len(execution_results['executed_actions']) + len(execution_results['failed_actions'])
            if total_actions > 0:
                execution_results['success_rate'] = len(execution_results['executed_actions']) / total_actions
            
            # Update rebalance history
            self.rebalance_history.append({
                'timestamp': datetime.now(),
                'trigger': proposal.trigger.value,
                'strategy': proposal.strategy.value,
                'actions_count': len(proposal.actions),
                'success_rate': execution_results['success_rate'],
                'total_cost': execution_results['total_cost']
            })
            
            # Update last rebalance timestamp
            self.last_rebalance[proposal.trigger] = datetime.now()
            
            logger.info(f"[PORTFOLIO_REBALANCER] Rebalancing completed. "
                       f"Success rate: {execution_results['success_rate']:.1%}, "
                       f"Total cost: ${execution_results['total_cost']:.2f}")
            
            return execution_results
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error executing rebalance proposal: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_rebalance_trade(self, action: RebalanceAction, 
                                     exchange_client: Any) -> Dict[str, Any]:
        """Execute individual rebalancing trade"""
        try:
            symbol = action.symbol
            
            if action.action == 'buy':
                # Execute buy order
                result = await exchange_client.create_market_buy_order(
                    symbol + '/USDT',
                    None,  # Amount will be calculated from USD value
                    None,
                    None,
                    {'quoteOrderQty': action.amount_usd}
                )
            elif action.action == 'sell':
                # Get current position size
                balance = await exchange_client.fetch_balance()
                available = balance.get(symbol, {}).get('free', 0)
                
                if available > 0:
                    # Calculate amount to sell based on weight deviation
                    sell_amount = available * abs(action.weight_deviation) / action.current_weight
                    
                    result = await exchange_client.create_market_sell_order(
                        symbol + '/USDT',
                        sell_amount
                    )
                else:
                    return {'success': False, 'error': 'Insufficient balance to sell'}
            else:
                return {'success': False, 'error': 'Invalid action'}
            
            if result and result.get('id'):
                return {
                    'success': True,
                    'order_id': result['id'],
                    'amount': result.get('amount', 0),
                    'price': result.get('price', 0),
                    'cost': result.get('cost', 0)
                }
            else:
                return {'success': False, 'error': 'Order execution failed'}
                
        except Exception as e:
            logger.error(f"[PORTFOLIO_REBALANCER] Error executing trade: {e}")
            return {'success': False, 'error': str(e)}
    
    # Utility methods for calculations
    async def _calculate_max_weight_deviation(self, portfolio: Dict[str, Any]) -> float:
        """Calculate maximum weight deviation from target"""
        # Simplified implementation - would need target weights
        return 0.05  # Placeholder
    
    async def _calculate_portfolio_volatility(self, portfolio: Dict[str, Any],
                                            market_data: Dict[str, Any]) -> float:
        """Calculate portfolio volatility"""
        # Simplified implementation
        return 0.06  # Placeholder
    
    async def _calculate_average_correlation(self, correlation_matrix: Dict[str, Dict[str, float]]) -> float:
        """Calculate average correlation in portfolio"""
        if not correlation_matrix:
            return 0.5
            
        correlations = []
        for asset1, corr_dict in correlation_matrix.items():
            for asset2, corr in corr_dict.items():
                if asset1 != asset2:
                    correlations.append(abs(corr))
        
        return np.mean(correlations) if correlations else 0.5
    
    async def _detect_momentum_shift(self, portfolio: Dict[str, Any],
                                   market_data: Dict[str, Any]) -> float:
        """Detect momentum shift in portfolio"""
        # Simplified implementation
        return 0.3  # Placeholder
    
    async def _calculate_portfolio_drawdown(self, portfolio: Dict[str, Any]) -> float:
        """Calculate current portfolio drawdown"""
        # Simplified implementation
        return 0.05  # Placeholder
    
    def get_rebalancer_stats(self) -> Dict[str, Any]:
        """Get rebalancing statistics"""
        return {
            'total_rebalances': len(self.rebalance_history),
            'last_rebalance_times': {
                trigger.value: timestamp.isoformat() if timestamp != datetime.min else None
                for trigger, timestamp in self.last_rebalance.items()
            },
            'average_success_rate': np.mean([r['success_rate'] for r in self.rebalance_history]) if self.rebalance_history else 0,
            'total_rebalance_cost': sum([r['total_cost'] for r in self.rebalance_history]),
            'rebalance_frequency': {
                trigger.value: len([r for r in self.rebalance_history if r['trigger'] == trigger.value])
                for trigger in RebalanceTrigger
            }
        }