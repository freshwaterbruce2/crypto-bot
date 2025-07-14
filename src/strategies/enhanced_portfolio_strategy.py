"""
Enhanced Portfolio-Aware Trading Strategy
Advanced multi-asset coordination with correlation analysis and dynamic optimization
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
from scipy.optimize import minimize
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class EnhancedPortfolioMetrics:
    """Enhanced portfolio-wide metrics for advanced decision making"""
    total_value_usd: float
    asset_count: int
    concentration_ratio: float
    correlation_matrix: Dict[str, Dict[str, float]]
    risk_score: float
    cash_percentage: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    beta_to_market: float
    diversification_ratio: float
    market_regime: str  # bull, bear, sideways
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional Value at Risk 95%


@dataclass
class MarketRegime:
    """Market regime detection and characteristics"""
    regime_type: str  # bull, bear, sideways, high_volatility
    confidence: float
    duration_days: int
    volatility_percentile: float
    trend_strength: float
    correlation_regime: str  # low, medium, high


class EnhancedPortfolioStrategy(BaseStrategy):
    """
    Advanced portfolio-aware trading strategy with:
    - Real-time correlation analysis
    - Dynamic portfolio optimization
    - Market regime detection
    - Intelligent capital allocation
    - Risk parity considerations
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize enhanced portfolio strategy"""
        super().__init__(config)
        
        # Enhanced portfolio constraints
        self.max_position_size = config.get('max_position_size', 0.15)
        self.min_position_size = config.get('min_position_size', 0.02)
        self.max_asset_count = config.get('max_asset_count', 20)
        self.min_cash_reserve = config.get('min_cash_reserve', 0.10)
        self.max_correlation = config.get('max_correlation', 0.7)
        
        # Advanced risk parameters
        self.max_portfolio_var = config.get('max_portfolio_var', 0.05)  # 5% daily VaR
        self.target_sharpe_ratio = config.get('target_sharpe_ratio', 1.5)
        self.max_sector_concentration = config.get('max_sector_concentration', 0.3)
        
        # Correlation analysis parameters
        self.correlation_window = config.get('correlation_window', 30)  # 30-period rolling
        self.correlation_decay = config.get('correlation_decay', 0.94)  # EWMA decay
        self.regime_lookback = config.get('regime_lookback', 90)  # 90 periods for regime
        
        # Optimization parameters
        self.rebalance_frequency = config.get('rebalance_frequency', 'daily')
        self.transaction_cost_bps = config.get('transaction_cost_bps', 10)  # 10 bps
        self.minimum_trade_size = config.get('minimum_trade_size', 0.01)  # 1% minimum trade
        
        # Risk parity parameters
        self.use_risk_parity = config.get('use_risk_parity', True)
        self.risk_target = config.get('risk_target', 0.15)  # 15% annual volatility target
        
        # Dynamic allocation weights
        self.momentum_weight = config.get('momentum_weight', 0.3)
        self.mean_reversion_weight = config.get('mean_reversion_weight', 0.3)
        self.quality_weight = config.get('quality_weight', 0.2)
        self.diversification_weight = config.get('diversification_weight', 0.2)
        
        # Data storage for analysis
        self.price_history = defaultdict(list)  # Price history per asset
        self.return_history = defaultdict(list)  # Return history per asset
        self.correlation_cache = {}
        self.portfolio_cache = {
            'metrics': None,
            'timestamp': None,
            'cache_duration': 30  # Cache for 30 seconds
        }
        
        # Market regime tracking
        self.current_regime = None
        self.regime_history = []
        
        # Asset classification
        self.asset_tiers = self._initialize_asset_tiers()
        self.sector_mapping = self._initialize_sector_mapping()
        
        logger.info(f"[ENHANCED_PORTFOLIO] Initialized with advanced portfolio optimization")
    
    def _initialize_asset_tiers(self) -> Dict[str, str]:
        """Initialize asset tier classification for risk management"""
        return {
            # Tier 1: Large cap, established
            'BTC': 'tier1', 'ETH': 'tier1',
            
            # Tier 2: Mid cap, established
            'SOL': 'tier2', 'ADA': 'tier2', 'DOT': 'tier2', 'AVAX': 'tier2',
            'LINK': 'tier2', 'MATIC': 'tier2', 'ALGO': 'tier2', 'ATOM': 'tier2',
            
            # Tier 3: Small cap, higher risk
            'MANA': 'tier3', 'SHIB': 'tier3', 'DOGE': 'tier3', 'APE': 'tier3',
            'AI16Z': 'tier3', 'BERA': 'tier3'
        }
    
    def _initialize_sector_mapping(self) -> Dict[str, str]:
        """Initialize sector classification for diversification"""
        return {
            'BTC': 'store_of_value',
            'ETH': 'smart_contracts',
            'SOL': 'smart_contracts',
            'ADA': 'smart_contracts',
            'DOT': 'interoperability',
            'AVAX': 'smart_contracts',
            'LINK': 'oracle',
            'MATIC': 'scaling',
            'ALGO': 'smart_contracts',
            'ATOM': 'interoperability',
            'MANA': 'metaverse',
            'SHIB': 'meme',
            'DOGE': 'meme',
            'APE': 'metaverse',
            'AI16Z': 'ai',
            'BERA': 'defi'
        }
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced analysis with correlation, regime detection, and optimization
        """
        try:
            symbol = data.get('symbol', 'UNKNOWN')
            price_data = data.get('price_data', [])
            portfolio = data.get('portfolio', {})
            market_data = data.get('market_data', {})
            
            if not price_data or len(price_data) < self.correlation_window:
                return self._create_signal('hold', 0, 0, "Insufficient price data for correlation analysis")
            
            # Update price and return history
            await self._update_market_data(symbol, price_data, market_data)
            
            # Calculate enhanced portfolio metrics
            portfolio_metrics = await self._calculate_enhanced_portfolio_metrics(portfolio)
            
            # Detect market regime
            current_regime = await self._detect_market_regime(portfolio_metrics)
            
            # Check portfolio constraints with regime awareness
            constraint_check = self._check_enhanced_portfolio_constraints(
                symbol, portfolio_metrics, current_regime
            )
            if not constraint_check['allowed']:
                return self._create_signal('hold', 0, 0, constraint_check['reason'])
            
            # Calculate multi-factor signal
            multi_factor_signal = await self._calculate_multi_factor_signal(
                symbol, price_data, portfolio_metrics, current_regime
            )
            
            # Apply portfolio optimization
            optimized_signal = await self._apply_portfolio_optimization(
                multi_factor_signal, symbol, portfolio, portfolio_metrics, current_regime
            )
            
            # Check for systematic rebalancing
            rebalance_signal = await self._check_systematic_rebalancing(
                symbol, portfolio, portfolio_metrics, current_regime
            )
            
            if rebalance_signal['action'] != 'hold':
                logger.info(f"[ENHANCED_PORTFOLIO] Systematic rebalancing for {symbol}: {rebalance_signal}")
                return rebalance_signal
            
            return optimized_signal
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Analysis error for {symbol}: {e}")
            return self._create_signal('hold', 0, 0, f"Analysis error: {str(e)}")
    
    async def _update_market_data(self, symbol: str, price_data: List[float], 
                                 market_data: Dict[str, Any]) -> None:
        """Update price and return history for correlation analysis"""
        try:
            current_price = price_data[-1]
            self.price_history[symbol].append(current_price)
            
            # Calculate returns
            if len(self.price_history[symbol]) > 1:
                previous_price = self.price_history[symbol][-2]
                return_pct = (current_price - previous_price) / previous_price
                self.return_history[symbol].append(return_pct)
            
            # Keep only recent history for memory efficiency
            max_history = max(self.correlation_window * 3, 200)
            if len(self.price_history[symbol]) > max_history:
                self.price_history[symbol] = self.price_history[symbol][-max_history:]
                self.return_history[symbol] = self.return_history[symbol][-max_history:]
                
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error updating market data for {symbol}: {e}")
    
    async def _calculate_correlation_matrix(self, active_assets: List[str]) -> Dict[str, Dict[str, float]]:
        """Calculate real-time correlation matrix using EWMA"""
        try:
            correlation_matrix = {}
            
            for asset1 in active_assets:
                correlation_matrix[asset1] = {}
                for asset2 in active_assets:
                    if asset1 == asset2:
                        correlation_matrix[asset1][asset2] = 1.0
                    elif asset2 in correlation_matrix and asset1 in correlation_matrix[asset2]:
                        # Use already calculated correlation (symmetric)
                        correlation_matrix[asset1][asset2] = correlation_matrix[asset2][asset1]
                    else:
                        # Calculate new correlation
                        corr = await self._calculate_ewma_correlation(asset1, asset2)
                        correlation_matrix[asset1][asset2] = corr
            
            return correlation_matrix
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating correlation matrix: {e}")
            return {}
    
    async def _calculate_ewma_correlation(self, asset1: str, asset2: str) -> float:
        """Calculate exponentially weighted moving average correlation"""
        try:
            returns1 = self.return_history.get(asset1, [])
            returns2 = self.return_history.get(asset2, [])
            
            if len(returns1) < 10 or len(returns2) < 10:
                return 0.0  # Default correlation for insufficient data
            
            # Align the arrays
            min_length = min(len(returns1), len(returns2))
            if min_length < 10:
                return 0.0
                
            returns1 = np.array(returns1[-min_length:])
            returns2 = np.array(returns2[-min_length:])
            
            # Calculate EWMA correlation
            weights = np.array([self.correlation_decay ** i for i in range(min_length-1, -1, -1)])
            weights = weights / weights.sum()
            
            # Weighted means
            mean1 = np.average(returns1, weights=weights)
            mean2 = np.average(returns2, weights=weights)
            
            # Weighted covariance and variances
            cov = np.average((returns1 - mean1) * (returns2 - mean2), weights=weights)
            var1 = np.average((returns1 - mean1) ** 2, weights=weights)
            var2 = np.average((returns2 - mean2) ** 2, weights=weights)
            
            # Correlation coefficient
            if var1 > 0 and var2 > 0:
                correlation = cov / (np.sqrt(var1) * np.sqrt(var2))
                return max(-1.0, min(1.0, correlation))  # Bound between -1 and 1
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating EWMA correlation: {e}")
            return 0.0
    
    async def _detect_market_regime(self, portfolio_metrics: EnhancedPortfolioMetrics) -> MarketRegime:
        """Detect current market regime using multiple indicators"""
        try:
            # Get market data for regime detection
            if len(self.regime_history) >= self.regime_lookback:
                recent_returns = []
                recent_volatilities = []
                
                # Collect data from major assets
                for asset in ['BTC', 'ETH', 'SOL']:
                    if asset in self.return_history and len(self.return_history[asset]) >= 20:
                        returns = self.return_history[asset][-20:]
                        recent_returns.extend(returns)
                        recent_volatilities.append(np.std(returns))
                
                if recent_returns:
                    # Market trend analysis
                    avg_return = np.mean(recent_returns)
                    volatility = np.std(recent_returns)
                    
                    # Volatility percentile (simplified)
                    vol_percentile = min(100, max(0, (volatility / 0.05) * 100))  # Normalize to 5% daily vol
                    
                    # Determine regime
                    if avg_return > 0.01 and volatility < 0.03:  # Strong positive returns, low vol
                        regime_type = "bull"
                        confidence = 0.8
                    elif avg_return < -0.01 and volatility > 0.04:  # Negative returns, high vol
                        regime_type = "bear"
                        confidence = 0.8
                    elif volatility > 0.06:  # Very high volatility
                        regime_type = "high_volatility"
                        confidence = 0.9
                    else:
                        regime_type = "sideways"
                        confidence = 0.6
                    
                    # Correlation regime
                    avg_correlation = portfolio_metrics.diversification_ratio
                    if avg_correlation > 0.8:
                        correlation_regime = "high"
                    elif avg_correlation > 0.5:
                        correlation_regime = "medium"
                    else:
                        correlation_regime = "low"
                    
                    regime = MarketRegime(
                        regime_type=regime_type,
                        confidence=confidence,
                        duration_days=1,  # Simplified
                        volatility_percentile=vol_percentile,
                        trend_strength=abs(avg_return),
                        correlation_regime=correlation_regime
                    )
                    
                    self.current_regime = regime
                    return regime
            
            # Default regime if insufficient data
            return MarketRegime(
                regime_type="sideways",
                confidence=0.5,
                duration_days=0,
                volatility_percentile=50.0,
                trend_strength=0.0,
                correlation_regime="medium"
            )
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error detecting market regime: {e}")
            return MarketRegime("sideways", 0.5, 0, 50.0, 0.0, "medium")
    
    async def _calculate_enhanced_portfolio_metrics(self, portfolio: Dict[str, Any]) -> EnhancedPortfolioMetrics:
        """Calculate comprehensive portfolio metrics with advanced analysis"""
        try:
            # Check cache first
            now = datetime.now()
            if self.portfolio_cache['metrics'] and self.portfolio_cache['timestamp']:
                age = (now - self.portfolio_cache['timestamp']).total_seconds()
                if age < self.portfolio_cache['cache_duration']:
                    return self.portfolio_cache['metrics']
            
            positions = portfolio.get('positions', {})
            total_value = portfolio.get('total_value_usd', 0)
            
            if not positions or total_value <= 0:
                # Return minimal metrics for empty portfolio
                metrics = EnhancedPortfolioMetrics(
                    total_value_usd=total_value,
                    asset_count=0,
                    concentration_ratio=0,
                    correlation_matrix={},
                    risk_score=0,
                    cash_percentage=1.0,
                    sharpe_ratio=0,
                    max_drawdown=0,
                    volatility=0,
                    beta_to_market=1.0,
                    diversification_ratio=1.0,
                    market_regime="sideways",
                    var_95=0,
                    cvar_95=0
                )
                self.portfolio_cache['metrics'] = metrics
                self.portfolio_cache['timestamp'] = now
                return metrics
            
            # Get active assets
            active_assets = [asset for asset, pos in positions.items() 
                           if pos.get('value_usd', 0) > 0 and asset not in ['USDT', 'USDC', 'USD']]
            
            # Calculate correlation matrix
            correlation_matrix = await self._calculate_correlation_matrix(active_assets)
            
            # Portfolio concentration
            position_values = [pos.get('value_usd', 0) for pos in positions.values()]
            max_position = max(position_values) if position_values else 0
            concentration = max_position / total_value if total_value > 0 else 0
            
            # Cash percentage
            cash_value = sum(
                pos.get('value_usd', 0) for asset, pos in positions.items()
                if asset in ['USDT', 'USDC', 'USD', 'EUR']
            )
            cash_percentage = cash_value / total_value if total_value > 0 else 0
            
            # Portfolio volatility and risk metrics
            portfolio_returns = self._calculate_portfolio_returns(positions, active_assets)
            volatility = np.std(portfolio_returns) if len(portfolio_returns) > 5 else 0.1
            
            # Sharpe ratio (simplified, assuming risk-free rate = 0)
            avg_return = np.mean(portfolio_returns) if len(portfolio_returns) > 0 else 0
            sharpe_ratio = avg_return / volatility if volatility > 0 else 0
            
            # Max drawdown calculation
            max_drawdown = self._calculate_max_drawdown(portfolio_returns)
            
            # VaR and CVaR calculations
            var_95, cvar_95 = self._calculate_var_cvar(portfolio_returns)
            
            # Diversification ratio
            diversification_ratio = self._calculate_diversification_ratio(
                correlation_matrix, positions, active_assets
            )
            
            # Market beta (simplified using BTC as market proxy)
            beta_to_market = self._calculate_portfolio_beta(positions, active_assets)
            
            # Risk score combining multiple factors
            risk_score = min(1.0, (
                volatility * 0.4 +
                concentration * 0.3 +
                (1.0 - diversification_ratio) * 0.3
            ))
            
            metrics = EnhancedPortfolioMetrics(
                total_value_usd=total_value,
                asset_count=len(active_assets),
                concentration_ratio=concentration,
                correlation_matrix=correlation_matrix,
                risk_score=risk_score,
                cash_percentage=cash_percentage,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                volatility=volatility,
                beta_to_market=beta_to_market,
                diversification_ratio=diversification_ratio,
                market_regime=self.current_regime.regime_type if self.current_regime else "sideways",
                var_95=var_95,
                cvar_95=cvar_95
            )
            
            # Update cache
            self.portfolio_cache['metrics'] = metrics
            self.portfolio_cache['timestamp'] = now
            
            return metrics
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating enhanced portfolio metrics: {e}")
            # Return safe default metrics
            return EnhancedPortfolioMetrics(0, 0, 0, {}, 0, 1.0, 0, 0, 0, 1.0, 1.0, "sideways", 0, 0)
    
    def _calculate_portfolio_returns(self, positions: Dict[str, Any], 
                                   active_assets: List[str]) -> List[float]:
        """Calculate portfolio returns based on position weights"""
        try:
            portfolio_returns = []
            total_value = sum(pos.get('value_usd', 0) for pos in positions.values())
            
            if total_value <= 0:
                return []
            
            # Calculate weights
            weights = {}
            for asset in active_assets:
                if asset in positions:
                    weight = positions[asset].get('value_usd', 0) / total_value
                    weights[asset] = weight
            
            # Calculate portfolio returns for available periods
            min_periods = min([len(self.return_history.get(asset, [])) for asset in active_assets] or [0])
            
            for i in range(min(min_periods, 100)):  # Last 100 periods max
                portfolio_return = 0
                for asset in active_assets:
                    if asset in weights and asset in self.return_history:
                        if i < len(self.return_history[asset]):
                            asset_return = self.return_history[asset][-(i+1)]
                            portfolio_return += weights[asset] * asset_return
                
                portfolio_returns.append(portfolio_return)
            
            return portfolio_returns[::-1]  # Reverse to get chronological order
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating portfolio returns: {e}")
            return []
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from return series"""
        try:
            if len(returns) < 2:
                return 0.0
                
            cumulative = np.cumprod(1 + np.array(returns))
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            return abs(np.min(drawdown))
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating max drawdown: {e}")
            return 0.0
    
    def _calculate_var_cvar(self, returns: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate Value at Risk and Conditional Value at Risk"""
        try:
            if len(returns) < 10:
                return 0.0, 0.0
                
            returns_array = np.array(returns)
            var_95 = np.percentile(returns_array, (1 - confidence) * 100)
            
            # CVaR is the expected return of the worst (1-confidence)% of cases
            worst_cases = returns_array[returns_array <= var_95]
            cvar_95 = np.mean(worst_cases) if len(worst_cases) > 0 else var_95
            
            return abs(var_95), abs(cvar_95)
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating VaR/CVaR: {e}")
            return 0.0, 0.0
    
    def _calculate_diversification_ratio(self, correlation_matrix: Dict[str, Dict[str, float]],
                                       positions: Dict[str, Any], 
                                       active_assets: List[str]) -> float:
        """Calculate portfolio diversification ratio"""
        try:
            if len(active_assets) <= 1:
                return 1.0
                
            total_value = sum(pos.get('value_usd', 0) for pos in positions.values())
            if total_value <= 0:
                return 1.0
            
            # Calculate weighted average correlation
            total_correlation = 0.0
            weight_sum = 0.0
            
            for asset1 in active_assets:
                for asset2 in active_assets:
                    if asset1 != asset2 and asset1 in correlation_matrix and asset2 in correlation_matrix[asset1]:
                        weight1 = positions.get(asset1, {}).get('value_usd', 0) / total_value
                        weight2 = positions.get(asset2, {}).get('value_usd', 0) / total_value
                        corr = correlation_matrix[asset1][asset2]
                        
                        total_correlation += weight1 * weight2 * corr
                        weight_sum += weight1 * weight2
            
            avg_correlation = total_correlation / weight_sum if weight_sum > 0 else 0.0
            
            # Diversification ratio: 1 means perfect diversification, 0 means perfect correlation
            return max(0.0, 1.0 - avg_correlation)
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating diversification ratio: {e}")
            return 0.5  # Default moderate diversification
    
    def _calculate_portfolio_beta(self, positions: Dict[str, Any], 
                                active_assets: List[str]) -> float:
        """Calculate portfolio beta relative to BTC (market proxy)"""
        try:
            if 'BTC' not in self.return_history or len(self.return_history['BTC']) < 20:
                return 1.0  # Default beta
                
            btc_returns = np.array(self.return_history['BTC'][-20:])
            portfolio_returns = np.array(self._calculate_portfolio_returns(positions, active_assets)[-20:])
            
            if len(portfolio_returns) < 20:
                return 1.0
                
            # Calculate beta using simple linear regression
            btc_var = np.var(btc_returns)
            if btc_var > 0:
                covariance = np.cov(portfolio_returns, btc_returns)[0][1]
                beta = covariance / btc_var
                return max(0.0, min(3.0, beta))  # Bound between 0 and 3
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating portfolio beta: {e}")
            return 1.0
    
    async def _calculate_multi_factor_signal(self, symbol: str, price_data: List[float],
                                           portfolio_metrics: EnhancedPortfolioMetrics,
                                           current_regime: MarketRegime) -> Dict[str, Any]:
        """Calculate multi-factor signal incorporating momentum, mean reversion, quality, and diversification"""
        try:
            if len(price_data) < 20:
                return self._create_signal('hold', 0, 0, "Insufficient data for multi-factor analysis")
            
            base_asset = symbol.split('/')[0]
            
            # Momentum factor
            momentum_signal = self._calculate_momentum_factor(price_data, current_regime)
            
            # Mean reversion factor
            mean_reversion_signal = self._calculate_mean_reversion_factor(price_data, current_regime)
            
            # Quality factor (based on Sharpe ratio, volatility)
            quality_signal = self._calculate_quality_factor(base_asset, current_regime)
            
            # Diversification factor
            diversification_signal = self._calculate_diversification_factor(
                base_asset, portfolio_metrics, current_regime
            )
            
            # Combine factors with regime-adjusted weights
            regime_weights = self._get_regime_adjusted_weights(current_regime)
            
            combined_strength = (
                momentum_signal['strength'] * regime_weights['momentum'] +
                mean_reversion_signal['strength'] * regime_weights['mean_reversion'] +
                quality_signal['strength'] * regime_weights['quality'] +
                diversification_signal['strength'] * regime_weights['diversification']
            )
            
            # Determine action based on combined signal
            if combined_strength > 0.6:
                action = 'buy'
                confidence = min(0.95, combined_strength)
            elif combined_strength < -0.6:
                action = 'sell'
                confidence = min(0.95, abs(combined_strength))
            else:
                action = 'hold'
                confidence = 0.0
            
            reason = (
                f"Multi-factor: momentum={momentum_signal['strength']:.2f}, "
                f"mean_rev={mean_reversion_signal['strength']:.2f}, "
                f"quality={quality_signal['strength']:.2f}, "
                f"diversification={diversification_signal['strength']:.2f}, "
                f"regime={current_regime.regime_type}"
            )
            
            return self._create_signal(action, confidence, combined_strength, reason)
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating multi-factor signal: {e}")
            return self._create_signal('hold', 0, 0, f"Multi-factor analysis error: {str(e)}")
    
    def _calculate_momentum_factor(self, price_data: List[float], 
                                 regime: MarketRegime) -> Dict[str, float]:
        """Calculate momentum factor signal"""
        try:
            # Multiple timeframe momentum
            short_momentum = (price_data[-1] - price_data[-5]) / price_data[-5] if len(price_data) >= 5 else 0
            medium_momentum = (price_data[-1] - price_data[-10]) / price_data[-10] if len(price_data) >= 10 else 0
            long_momentum = (price_data[-1] - price_data[-20]) / price_data[-20] if len(price_data) >= 20 else 0
            
            # Weight by timeframe and regime
            if regime.regime_type == "bull":
                # In bull markets, favor longer-term momentum
                momentum_strength = 0.2 * short_momentum + 0.3 * medium_momentum + 0.5 * long_momentum
            elif regime.regime_type == "bear":
                # In bear markets, favor shorter-term momentum for quick exits
                momentum_strength = 0.6 * short_momentum + 0.3 * medium_momentum + 0.1 * long_momentum
            else:
                # Balanced approach for sideways markets
                momentum_strength = 0.33 * short_momentum + 0.33 * medium_momentum + 0.34 * long_momentum
            
            # Normalize to [-1, 1] range
            momentum_strength = max(-1, min(1, momentum_strength * 10))  # Scale by 10 for sensitivity
            
            return {'strength': momentum_strength, 'components': {
                'short': short_momentum, 'medium': medium_momentum, 'long': long_momentum
            }}
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating momentum factor: {e}")
            return {'strength': 0.0, 'components': {}}
    
    def _calculate_mean_reversion_factor(self, price_data: List[float], 
                                       regime: MarketRegime) -> Dict[str, float]:
        """Calculate mean reversion factor signal"""
        try:
            if len(price_data) < 20:
                return {'strength': 0.0, 'components': {}}
                
            current_price = price_data[-1]
            
            # Multiple timeframe means
            sma_5 = np.mean(price_data[-5:])
            sma_10 = np.mean(price_data[-10:])
            sma_20 = np.mean(price_data[-20:])
            
            # Deviations from means
            dev_5 = (current_price - sma_5) / sma_5
            dev_10 = (current_price - sma_10) / sma_10
            dev_20 = (current_price - sma_20) / sma_20
            
            # Mean reversion strength (negative when price is above mean)
            if regime.regime_type == "sideways":
                # Strong mean reversion in sideways markets
                mean_rev_strength = -(0.4 * dev_5 + 0.3 * dev_10 + 0.3 * dev_20)
            elif regime.regime_type == "high_volatility":
                # Moderate mean reversion in volatile markets
                mean_rev_strength = -(0.5 * dev_5 + 0.3 * dev_10 + 0.2 * dev_20)
            else:
                # Weak mean reversion in trending markets
                mean_rev_strength = -(0.3 * dev_5 + 0.3 * dev_10 + 0.4 * dev_20)
            
            # Normalize to [-1, 1] range
            mean_rev_strength = max(-1, min(1, mean_rev_strength * 5))  # Scale by 5 for sensitivity
            
            return {'strength': mean_rev_strength, 'components': {
                'dev_5': dev_5, 'dev_10': dev_10, 'dev_20': dev_20
            }}
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating mean reversion factor: {e}")
            return {'strength': 0.0, 'components': {}}
    
    def _calculate_quality_factor(self, asset: str, regime: MarketRegime) -> Dict[str, float]:
        """Calculate quality factor based on asset characteristics"""
        try:
            # Asset tier quality score
            tier = self.asset_tiers.get(asset, 'tier3')
            tier_scores = {'tier1': 0.8, 'tier2': 0.5, 'tier3': 0.2}
            tier_quality = tier_scores.get(tier, 0.2)
            
            # Volatility quality (lower volatility = higher quality in uncertain times)
            if asset in self.return_history and len(self.return_history[asset]) >= 10:
                asset_volatility = np.std(self.return_history[asset][-10:])
                vol_quality = max(0, 1 - (asset_volatility / 0.1))  # Normalize by 10% daily vol
            else:
                vol_quality = 0.5  # Default
            
            # Regime-adjusted quality preferences
            if regime.regime_type == "bear" or regime.regime_type == "high_volatility":
                # Prefer high-quality assets in difficult markets
                quality_strength = 0.7 * tier_quality + 0.3 * vol_quality
            else:
                # Balanced approach in normal markets
                quality_strength = 0.5 * tier_quality + 0.5 * vol_quality
            
            # Convert to signal strength (-1 to 1, where 1 favors high quality)
            quality_signal = 2 * quality_strength - 1  # Convert [0,1] to [-1,1]
            
            return {'strength': quality_signal, 'components': {
                'tier_quality': tier_quality, 'vol_quality': vol_quality
            }}
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating quality factor: {e}")
            return {'strength': 0.0, 'components': {}}
    
    def _calculate_diversification_factor(self, asset: str, 
                                        portfolio_metrics: EnhancedPortfolioMetrics,
                                        regime: MarketRegime) -> Dict[str, float]:
        """Calculate diversification benefit of adding/increasing position in asset"""
        try:
            # Current portfolio concentration in this asset
            current_weight = 0.0
            if portfolio_metrics.total_value_usd > 0:
                # Simplified: assume we can get current weight somehow
                current_weight = min(0.3, portfolio_metrics.concentration_ratio)  # Cap at 30%
            
            # Sector diversification
            asset_sector = self.sector_mapping.get(asset, 'other')
            sector_concentration = 0.2  # Simplified: assume moderate sector concentration
            
            # Correlation with existing holdings
            avg_correlation = 0.5  # Default moderate correlation
            if asset in portfolio_metrics.correlation_matrix:
                correlations = [corr for corr in portfolio_metrics.correlation_matrix[asset].values() 
                               if isinstance(corr, (int, float))]
                if correlations:
                    avg_correlation = np.mean([abs(c) for c in correlations])
            
            # Diversification benefit calculation
            position_diversity = max(0, 1 - (current_weight / self.max_position_size))
            sector_diversity = max(0, 1 - (sector_concentration / self.max_sector_concentration))
            correlation_diversity = max(0, 1 - avg_correlation)
            
            # Overall diversification signal
            diversification_strength = (
                0.4 * position_diversity +
                0.3 * sector_diversity +
                0.3 * correlation_diversity
            )
            
            # Regime adjustment
            if regime.correlation_regime == "high":
                # When correlations are high, diversification is more important
                diversification_strength *= 1.5
            elif regime.correlation_regime == "low":
                # When correlations are low, diversification is less critical
                diversification_strength *= 0.8
            
            # Convert to signal strength (-1 to 1)
            diversification_signal = 2 * diversification_strength - 1
            
            return {'strength': min(1, max(-1, diversification_signal)), 'components': {
                'position_diversity': position_diversity,
                'sector_diversity': sector_diversity,
                'correlation_diversity': correlation_diversity
            }}
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating diversification factor: {e}")
            return {'strength': 0.0, 'components': {}}
    
    def _get_regime_adjusted_weights(self, regime: MarketRegime) -> Dict[str, float]:
        """Get factor weights adjusted for current market regime"""
        base_weights = {
            'momentum': self.momentum_weight,
            'mean_reversion': self.mean_reversion_weight,
            'quality': self.quality_weight,
            'diversification': self.diversification_weight
        }
        
        if regime.regime_type == "bull":
            # In bull markets, emphasize momentum and diversification
            return {
                'momentum': 0.4,
                'mean_reversion': 0.1,
                'quality': 0.2,
                'diversification': 0.3
            }
        elif regime.regime_type == "bear":
            # In bear markets, emphasize quality and mean reversion
            return {
                'momentum': 0.1,
                'mean_reversion': 0.3,
                'quality': 0.4,
                'diversification': 0.2
            }
        elif regime.regime_type == "high_volatility":
            # In volatile markets, emphasize quality and diversification
            return {
                'momentum': 0.2,
                'mean_reversion': 0.2,
                'quality': 0.3,
                'diversification': 0.3
            }
        else:  # sideways
            # In sideways markets, balanced approach with slight mean reversion bias
            return {
                'momentum': 0.2,
                'mean_reversion': 0.4,
                'quality': 0.2,
                'diversification': 0.2
            }
    
    def _check_enhanced_portfolio_constraints(self, symbol: str, 
                                            metrics: EnhancedPortfolioMetrics,
                                            regime: MarketRegime) -> Dict[str, Any]:
        """Enhanced portfolio constraint checking with regime awareness"""
        # Basic constraints
        basic_check = super()._check_portfolio_constraints(symbol, metrics)
        if not basic_check['allowed']:
            return basic_check
        
        # Enhanced constraints
        
        # VaR constraint
        if metrics.var_95 > self.max_portfolio_var:
            return {'allowed': False, 'reason': f'Portfolio VaR ({metrics.var_95:.2%}) exceeds limit'}
        
        # Regime-specific constraints
        if regime.regime_type == "high_volatility":
            # Stricter constraints during high volatility
            if metrics.concentration_ratio > self.max_position_size * 0.8:
                return {'allowed': False, 'reason': 'High volatility: concentration too high'}
        
        # Correlation constraint
        if regime.correlation_regime == "high" and metrics.diversification_ratio < 0.3:
            return {'allowed': False, 'reason': 'High correlation regime: insufficient diversification'}
        
        return {'allowed': True, 'reason': 'All enhanced constraints satisfied'}
    
    async def _apply_portfolio_optimization(self, signal: Dict[str, Any], symbol: str,
                                          portfolio: Dict[str, Any], 
                                          metrics: EnhancedPortfolioMetrics,
                                          regime: MarketRegime) -> Dict[str, Any]:
        """Apply portfolio optimization to adjust signal strength and size"""
        try:
            if signal['action'] == 'hold':
                return signal
                
            base_asset = symbol.split('/')[0]
            
            # Calculate optimal position size using Kelly Criterion (simplified)
            optimal_size = await self._calculate_optimal_position_size(
                signal, base_asset, metrics, regime
            )
            
            # Apply transaction cost adjustment
            signal = self._adjust_for_transaction_costs(signal, optimal_size, metrics)
            
            # Apply risk parity adjustment if enabled
            if self.use_risk_parity:
                signal = self._apply_risk_parity_adjustment(signal, base_asset, metrics)
            
            # Final portfolio-level validation
            signal = await self._validate_portfolio_impact(signal, symbol, metrics, regime)
            
            return signal
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error applying portfolio optimization: {e}")
            return signal
    
    async def _calculate_optimal_position_size(self, signal: Dict[str, Any], asset: str,
                                             metrics: EnhancedPortfolioMetrics,
                                             regime: MarketRegime) -> float:
        """Calculate optimal position size using Kelly Criterion and risk constraints"""
        try:
            # Simplified Kelly Criterion
            # Kelly = (bp - q) / b, where b = odds, p = win probability, q = loss probability
            
            win_probability = max(0.51, signal['confidence'])  # Minimum 51% for positive expectancy
            loss_probability = 1 - win_probability
            
            # Estimate average win/loss ratio from historical data
            if asset in self.return_history and len(self.return_history[asset]) >= 20:
                returns = np.array(self.return_history[asset][-20:])
                positive_returns = returns[returns > 0]
                negative_returns = returns[returns < 0]
                
                avg_win = np.mean(positive_returns) if len(positive_returns) > 0 else 0.02
                avg_loss = abs(np.mean(negative_returns)) if len(negative_returns) > 0 else 0.02
                
                win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0
            else:
                win_loss_ratio = 1.0  # Conservative default
            
            # Kelly fraction
            kelly_fraction = (win_probability * win_loss_ratio - loss_probability) / win_loss_ratio
            kelly_fraction = max(0, min(0.25, kelly_fraction))  # Cap at 25% of portfolio
            
            # Adjust for regime
            if regime.regime_type == "bear" or regime.regime_type == "high_volatility":
                kelly_fraction *= 0.5  # More conservative in difficult markets
            elif regime.regime_type == "bull":
                kelly_fraction *= 1.2  # Slightly more aggressive in bull markets
            
            # Convert to position size
            target_position_value = kelly_fraction * metrics.total_value_usd
            
            # Apply portfolio constraints
            max_position_value = self.max_position_size * metrics.total_value_usd
            min_position_value = self.min_position_size * metrics.total_value_usd
            
            optimal_size = max(min_position_value, min(max_position_value, target_position_value))
            
            return optimal_size
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating optimal position size: {e}")
            return self.order_size_usdt  # Fallback to default
    
    def _adjust_for_transaction_costs(self, signal: Dict[str, Any], position_size: float,
                                    metrics: EnhancedPortfolioMetrics) -> Dict[str, Any]:
        """Adjust signal for transaction costs"""
        try:
            # Calculate transaction cost in basis points
            transaction_cost = position_size * (self.transaction_cost_bps / 10000)
            
            # Minimum profit required to overcome transaction costs
            min_profit_needed = transaction_cost * 2  # 2x to account for round trip
            expected_profit = position_size * signal.get('strength', 0) * 0.02  # Assume 2% move
            
            if expected_profit < min_profit_needed:
                # Reduce signal strength if expected profit doesn't justify costs
                signal['confidence'] *= 0.7
                signal['reason'] += " (reduced: transaction cost concern)"
            
            return signal
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error adjusting for transaction costs: {e}")
            return signal
    
    def _apply_risk_parity_adjustment(self, signal: Dict[str, Any], asset: str,
                                    metrics: EnhancedPortfolioMetrics) -> Dict[str, Any]:
        """Apply risk parity principles to position sizing"""
        try:
            # Calculate asset volatility
            if asset in self.return_history and len(self.return_history[asset]) >= 10:
                asset_volatility = np.std(self.return_history[asset][-10:])
            else:
                asset_volatility = 0.05  # Default 5% daily volatility
            
            # Risk parity adjustment: inverse volatility weighting
            if asset_volatility > 0:
                vol_adjustment = self.risk_target / asset_volatility
                vol_adjustment = max(0.5, min(2.0, vol_adjustment))  # Bound between 0.5x and 2x
                
                signal['confidence'] *= vol_adjustment
                signal['reason'] += f" (risk parity adj: {vol_adjustment:.2f})"
            
            return signal
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error applying risk parity adjustment: {e}")
            return signal
    
    async def _validate_portfolio_impact(self, signal: Dict[str, Any], symbol: str,
                                       metrics: EnhancedPortfolioMetrics,
                                       regime: MarketRegime) -> Dict[str, Any]:
        """Validate the impact of the signal on overall portfolio"""
        try:
            if signal['action'] == 'hold':
                return signal
                
            base_asset = symbol.split('/')[0]
            
            # Simulate portfolio impact
            simulated_metrics = await self._simulate_portfolio_impact(signal, base_asset, metrics)
            
            # Check if the trade improves portfolio metrics
            improvement_score = self._calculate_portfolio_improvement(metrics, simulated_metrics)
            
            if improvement_score < 0:
                # Trade would worsen portfolio - reduce confidence
                signal['confidence'] *= max(0.3, 1 + improvement_score)
                signal['reason'] += f" (portfolio impact: {improvement_score:.2f})"
            elif improvement_score > 0.1:
                # Trade significantly improves portfolio - boost confidence
                signal['confidence'] = min(0.95, signal['confidence'] * 1.2)
                signal['reason'] += f" (portfolio boost: {improvement_score:.2f})"
            
            return signal
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error validating portfolio impact: {e}")
            return signal
    
    async def _simulate_portfolio_impact(self, signal: Dict[str, Any], asset: str,
                                       current_metrics: EnhancedPortfolioMetrics) -> EnhancedPortfolioMetrics:
        """Simulate the impact of a trade on portfolio metrics"""
        try:
            # Simplified simulation - in practice, this would be more complex
            new_metrics = current_metrics
            
            if signal['action'] == 'buy':
                # Simulate adding position
                new_concentration = min(0.25, current_metrics.concentration_ratio + 0.05)
                new_asset_count = current_metrics.asset_count + (1 if asset not in current_metrics.correlation_matrix else 0)
            else:  # sell
                # Simulate reducing position
                new_concentration = max(0, current_metrics.concentration_ratio - 0.05)
                new_asset_count = max(1, current_metrics.asset_count - 1)
            
            # Create simulated metrics (simplified)
            new_metrics = EnhancedPortfolioMetrics(
                total_value_usd=current_metrics.total_value_usd,
                asset_count=new_asset_count,
                concentration_ratio=new_concentration,
                correlation_matrix=current_metrics.correlation_matrix,
                risk_score=current_metrics.risk_score,
                cash_percentage=current_metrics.cash_percentage,
                sharpe_ratio=current_metrics.sharpe_ratio,
                max_drawdown=current_metrics.max_drawdown,
                volatility=current_metrics.volatility,
                beta_to_market=current_metrics.beta_to_market,
                diversification_ratio=current_metrics.diversification_ratio,
                market_regime=current_metrics.market_regime,
                var_95=current_metrics.var_95,
                cvar_95=current_metrics.cvar_95
            )
            
            return new_metrics
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error simulating portfolio impact: {e}")
            return current_metrics
    
    def _calculate_portfolio_improvement(self, current: EnhancedPortfolioMetrics,
                                       simulated: EnhancedPortfolioMetrics) -> float:
        """Calculate portfolio improvement score"""
        try:
            # Portfolio improvement factors
            concentration_improvement = (current.concentration_ratio - simulated.concentration_ratio) * 2
            diversification_improvement = (simulated.diversification_ratio - current.diversification_ratio) * 1
            risk_improvement = (current.risk_score - simulated.risk_score) * 1.5
            
            total_improvement = concentration_improvement + diversification_improvement + risk_improvement
            
            return max(-1, min(1, total_improvement))  # Bound between -1 and 1
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error calculating portfolio improvement: {e}")
            return 0.0
    
    async def _check_systematic_rebalancing(self, symbol: str, portfolio: Dict[str, Any],
                                          metrics: EnhancedPortfolioMetrics,
                                          regime: MarketRegime) -> Dict[str, Any]:
        """Check for systematic rebalancing opportunities"""
        try:
            # Time-based rebalancing
            if self.rebalance_frequency == 'daily':
                # Check if we should rebalance today (simplified)
                should_rebalance = True  # Placeholder
            else:
                should_rebalance = False
            
            if not should_rebalance:
                return self._create_signal('hold', 0, 0, "No rebalancing needed")
            
            # Volatility-based rebalancing
            if metrics.volatility > 0.06:  # High volatility threshold
                # Rebalance towards less volatile assets
                base_asset = symbol.split('/')[0]
                asset_tier = self.asset_tiers.get(base_asset, 'tier3')
                
                if asset_tier == 'tier1':  # High quality asset
                    return self._create_signal(
                        'buy', 0.6, 0.05,
                        "Volatility rebalancing: towards quality assets"
                    )
            
            # Correlation-based rebalancing
            if metrics.diversification_ratio < 0.3:  # Low diversification
                # Look for diversifying assets
                base_asset = symbol.split('/')[0]
                if base_asset in metrics.correlation_matrix:
                    avg_correlation = np.mean([
                        abs(corr) for corr in metrics.correlation_matrix[base_asset].values()
                        if isinstance(corr, (int, float))
                    ])
                    
                    if avg_correlation < 0.4:  # Low correlation with existing holdings
                        return self._create_signal(
                            'buy', 0.5, 0.03,
                            "Correlation rebalancing: improving diversification"
                        )
            
            return self._create_signal('hold', 0, 0, "No systematic rebalancing needed")
            
        except Exception as e:
            logger.error(f"[ENHANCED_PORTFOLIO] Error checking systematic rebalancing: {e}")
            return self._create_signal('hold', 0, 0, "Rebalancing check error")
    
    def get_description(self) -> str:
        """Get enhanced strategy description"""
        return (
            f"Enhanced Portfolio Strategy: max_pos={self.max_position_size:.0%}, "
            f"max_assets={self.max_asset_count}, VaR_limit={self.max_portfolio_var:.1%}, "
            f"regime_aware=True, risk_parity={self.use_risk_parity}"
        )