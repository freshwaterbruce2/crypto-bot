"""
Portfolio-Aware Trading Strategy

This strategy makes trading decisions based on the overall portfolio composition,
ensuring proper diversification and risk management across all holdings.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class PortfolioMetrics:
    """Portfolio-wide metrics for decision making"""
    total_value_usd: float
    asset_count: int
    concentration_ratio: float  # Highest position as % of portfolio
    correlation_score: float    # Average correlation between holdings
    risk_score: float          # Overall portfolio risk
    cash_percentage: float     # % of portfolio in stablecoins/cash


class PortfolioAwareStrategy(BaseStrategy):
    """
    Trading strategy that considers overall portfolio composition
    before making individual trading decisions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize portfolio-aware strategy"""
        super().__init__(config)
        
        # Portfolio constraints
        self.max_position_size = config.get('max_position_size', 0.15)  # 15% max per position
        self.min_position_size = config.get('min_position_size', 0.02)  # 2% min per position
        self.max_asset_count = config.get('max_asset_count', 20)       # Max 20 different assets
        self.min_cash_reserve = config.get('min_cash_reserve', 0.10)   # Keep 10% in cash
        self.max_correlation = config.get('max_correlation', 0.7)      # Max correlation threshold
        
        # Rebalancing parameters
        self.rebalance_threshold = config.get('rebalance_threshold', 0.05)  # 5% deviation triggers rebalance
        self.target_weights = config.get('target_weights', {})  # Target portfolio weights
        
        # Risk parameters
        self.max_portfolio_risk = config.get('max_portfolio_risk', 0.25)  # 25% max portfolio risk
        self.diversification_bonus = config.get('diversification_bonus', 1.2)  # 20% signal boost for diversification
        
        # Cache for portfolio metrics
        self._portfolio_cache = {
            'metrics': None,
            'timestamp': None,
            'cache_duration': 60  # Cache for 60 seconds
        }
        
        logger.info(f"[PORTFOLIO_AWARE] Initialized with max_position_size={self.max_position_size}, "
                   f"max_assets={self.max_asset_count}, min_cash={self.min_cash_reserve}")
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze trading opportunity considering portfolio context
        
        Args:
            data: Market data and current portfolio state
            
        Returns:
            Trading signal with portfolio-aware adjustments
        """
        try:
            symbol = data.get('symbol', 'UNKNOWN')
            price_data = data.get('price_data', [])
            portfolio = data.get('portfolio', {})
            
            if not price_data or len(price_data) < 10:
                return self._create_signal('hold', 0, 0, "Insufficient price data")
            
            # Get portfolio metrics
            portfolio_metrics = await self._calculate_portfolio_metrics(portfolio)
            
            # Check portfolio constraints first
            constraint_check = self._check_portfolio_constraints(symbol, portfolio_metrics)
            if not constraint_check['allowed']:
                return self._create_signal('hold', 0, 0, constraint_check['reason'])
            
            # Calculate base signal (technical analysis)
            base_signal = self._calculate_base_signal(price_data)
            
            # Adjust signal based on portfolio context
            adjusted_signal = self._adjust_for_portfolio(
                base_signal, symbol, portfolio, portfolio_metrics
            )
            
            # Check if rebalancing is needed
            rebalance_signal = self._check_rebalancing_need(symbol, portfolio, portfolio_metrics)
            if rebalance_signal['action'] != 'hold':
                logger.info(f"[PORTFOLIO_AWARE] Rebalancing signal for {symbol}: {rebalance_signal}")
                return rebalance_signal
            
            return adjusted_signal
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_AWARE] Analysis error for {symbol}: {e}")
            return self._create_signal('hold', 0, 0, f"Analysis error: {str(e)}")
    
    async def _calculate_portfolio_metrics(self, portfolio: Dict[str, Any]) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics"""
        try:
            # Check cache first
            now = datetime.now()
            if self._portfolio_cache['metrics'] and self._portfolio_cache['timestamp']:
                age = (now - self._portfolio_cache['timestamp']).total_seconds()
                if age < self._portfolio_cache['cache_duration']:
                    return self._portfolio_cache['metrics']
            
            # Calculate fresh metrics
            positions = portfolio.get('positions', {})
            total_value = portfolio.get('total_value_usd', 0)
            
            if not positions or total_value <= 0:
                metrics = PortfolioMetrics(
                    total_value_usd=total_value,
                    asset_count=0,
                    concentration_ratio=0,
                    correlation_score=0,
                    risk_score=0,
                    cash_percentage=1.0
                )
            else:
                # Calculate concentration (largest position as % of portfolio)
                position_values = [pos.get('value_usd', 0) for pos in positions.values()]
                max_position = max(position_values) if position_values else 0
                concentration = max_position / total_value if total_value > 0 else 0
                
                # Calculate cash percentage
                cash_value = sum(
                    pos.get('value_usd', 0) for asset, pos in positions.items()
                    if asset in ['USDT', 'USDC', 'USD', 'EUR']
                )
                cash_percentage = cash_value / total_value if total_value > 0 else 0
                
                # Simple risk score based on volatility and concentration
                avg_volatility = sum(
                    pos.get('volatility', 0.1) * pos.get('value_usd', 0)
                    for pos in positions.values()
                ) / total_value if total_value > 0 else 0.1
                
                risk_score = avg_volatility * (1 + concentration)
                
                metrics = PortfolioMetrics(
                    total_value_usd=total_value,
                    asset_count=len(positions),
                    concentration_ratio=concentration,
                    correlation_score=0.5,  # Placeholder - would calculate actual correlations
                    risk_score=min(risk_score, 1.0),
                    cash_percentage=cash_percentage
                )
            
            # Update cache
            self._portfolio_cache['metrics'] = metrics
            self._portfolio_cache['timestamp'] = now
            
            return metrics
            
        except Exception as e:
            logger.error(f"[PORTFOLIO_AWARE] Error calculating portfolio metrics: {e}")
            return PortfolioMetrics(0, 0, 0, 0, 0, 1.0)
    
    def _check_portfolio_constraints(self, symbol: str, metrics: PortfolioMetrics) -> Dict[str, Any]:
        """Check if trading is allowed based on portfolio constraints"""
        # Check max asset count
        if metrics.asset_count >= self.max_asset_count:
            return {'allowed': False, 'reason': f'Max asset count ({self.max_asset_count}) reached'}
        
        # Check minimum cash reserve
        if metrics.cash_percentage < self.min_cash_reserve:
            return {'allowed': False, 'reason': f'Below minimum cash reserve ({self.min_cash_reserve:.1%})'}
        
        # Check portfolio risk
        if metrics.risk_score > self.max_portfolio_risk:
            return {'allowed': False, 'reason': f'Portfolio risk too high ({metrics.risk_score:.2f})'}
        
        return {'allowed': True, 'reason': 'All constraints satisfied'}
    
    def _calculate_base_signal(self, price_data: List[float]) -> Dict[str, Any]:
        """Calculate base trading signal from price data"""
        if len(price_data) < 20:
            return self._create_signal('hold', 0, 0, "Insufficient data for analysis")
        
        # Simple momentum + mean reversion hybrid
        recent_prices = price_data[-20:]
        current_price = recent_prices[-1]
        
        # Short-term momentum (5 periods)
        short_momentum = (current_price - recent_prices[-5]) / recent_prices[-5]
        
        # Medium-term mean reversion (20 periods)
        mean_20 = sum(recent_prices) / len(recent_prices)
        deviation = (current_price - mean_20) / mean_20
        
        # Combine signals
        if short_momentum > 0.02 and deviation < -0.03:  # Momentum up, price below mean
            return self._create_signal('buy', 0.7, abs(short_momentum), "Momentum reversal from oversold")
        elif short_momentum < -0.02 and deviation > 0.03:  # Momentum down, price above mean
            return self._create_signal('sell', 0.7, abs(short_momentum), "Overbought reversal")
        elif abs(short_momentum) > 0.05:  # Strong momentum
            action = 'buy' if short_momentum > 0 else 'sell'
            return self._create_signal(action, 0.6, abs(short_momentum), "Strong momentum")
        else:
            return self._create_signal('hold', 0, 0, "No clear signal")
    
    def _adjust_for_portfolio(self, base_signal: Dict[str, Any], symbol: str, 
                            portfolio: Dict[str, Any], metrics: PortfolioMetrics) -> Dict[str, Any]:
        """Adjust trading signal based on portfolio context"""
        signal = base_signal.copy()
        
        # Get current position info
        positions = portfolio.get('positions', {})
        base_asset = symbol.split('/')[0]
        current_position = positions.get(base_asset, {})
        position_value = current_position.get('value_usd', 0)
        position_weight = position_value / metrics.total_value_usd if metrics.total_value_usd > 0 else 0
        
        # Adjust for position size
        if signal['action'] == 'buy':
            # Reduce signal if position is already large
            if position_weight > self.max_position_size * 0.8:
                signal['confidence'] *= 0.5
                signal['reason'] += f" (reduced: position at {position_weight:.1%} of portfolio)"
            # Boost signal for diversification
            elif metrics.asset_count < 10 and position_weight == 0:
                signal['confidence'] *= self.diversification_bonus
                signal['reason'] += " (boosted: improves diversification)"
        
        elif signal['action'] == 'sell':
            # Boost sell signal if position is too large
            if position_weight > self.max_position_size:
                signal['confidence'] *= 1.5
                signal['reason'] += f" (boosted: position oversized at {position_weight:.1%})"
            # Reduce sell signal if it would hurt diversification
            elif metrics.asset_count <= 5 and position_weight > 0:
                signal['confidence'] *= 0.7
                signal['reason'] += " (reduced: would reduce diversification)"
        
        # Risk adjustment
        if metrics.risk_score > 0.2:  # High portfolio risk
            if signal['action'] == 'buy':
                signal['confidence'] *= 0.8
                signal['reason'] += " (reduced: high portfolio risk)"
            elif signal['action'] == 'sell':
                signal['confidence'] *= 1.2
                signal['reason'] += " (boosted: risk reduction needed)"
        
        return signal
    
    def _check_rebalancing_need(self, symbol: str, portfolio: Dict[str, Any], 
                               metrics: PortfolioMetrics) -> Dict[str, Any]:
        """Check if portfolio rebalancing is needed"""
        if not self.target_weights:
            return self._create_signal('hold', 0, 0, "No target weights configured")
        
        positions = portfolio.get('positions', {})
        base_asset = symbol.split('/')[0]
        
        # Check if this asset has a target weight
        if base_asset not in self.target_weights:
            return self._create_signal('hold', 0, 0, "Asset not in target portfolio")
        
        # Calculate current weight
        current_position = positions.get(base_asset, {})
        current_value = current_position.get('value_usd', 0)
        current_weight = current_value / metrics.total_value_usd if metrics.total_value_usd > 0 else 0
        
        # Compare to target weight
        target_weight = self.target_weights[base_asset]
        deviation = abs(current_weight - target_weight)
        
        if deviation > self.rebalance_threshold:
            if current_weight < target_weight:
                # Need to buy more
                confidence = min(deviation / self.rebalance_threshold, 1.0) * 0.8
                return self._create_signal(
                    'buy', confidence, deviation,
                    f"Rebalancing: {current_weight:.1%} -> {target_weight:.1%}"
                )
            else:
                # Need to sell some
                confidence = min(deviation / self.rebalance_threshold, 1.0) * 0.8
                return self._create_signal(
                    'sell', confidence, deviation,
                    f"Rebalancing: {current_weight:.1%} -> {target_weight:.1%}"
                )
        
        return self._create_signal('hold', 0, 0, "Within rebalancing threshold")
    
    def get_description(self) -> str:
        """Get strategy description"""
        return (
            f"Portfolio-Aware Strategy: max_position={self.max_position_size:.0%}, "
            f"max_assets={self.max_asset_count}, min_cash={self.min_cash_reserve:.0%}"
        )