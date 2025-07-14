"""
Portfolio intelligence module for advanced portfolio analysis and optimization.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class PortfolioSignal(Enum):
    """Portfolio-level signals."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"
    REBALANCE = "rebalance"


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""
    total_value: float
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    var_95: float  # Value at Risk 95%
    beta: float
    alpha: float
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AssetAllocation:
    """Asset allocation information."""
    symbol: str
    current_weight: float
    target_weight: float
    current_value: float
    target_value: float
    rebalance_amount: float
    rebalance_direction: str  # 'buy', 'sell', 'hold'


@dataclass
class RiskMetrics:
    """Portfolio risk metrics."""
    portfolio_volatility: float
    concentration_risk: float
    correlation_risk: float
    liquidity_risk: float
    market_risk: float
    overall_risk_score: float
    risk_level: str  # 'low', 'medium', 'high', 'very_high'


class PortfolioIntelligence:
    """
    Advanced portfolio intelligence system for analysis, optimization, and risk management.
    """
    
    def __init__(self, 
                 benchmark_symbol: str = "BTC/USD",
                 risk_free_rate: float = 0.02,
                 rebalance_threshold: float = 0.05,
                 max_position_weight: float = 0.3):
        """
        Initialize portfolio intelligence system.
        
        Args:
            benchmark_symbol: Benchmark for performance comparison
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
            rebalance_threshold: Threshold for triggering rebalancing
            max_position_weight: Maximum weight for any single position
        """
        self.benchmark_symbol = benchmark_symbol
        self.risk_free_rate = risk_free_rate
        self.rebalance_threshold = rebalance_threshold
        self.max_position_weight = max_position_weight
        
        # Portfolio data
        self.positions: Dict[str, Dict[str, float]] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.portfolio_history: List[Dict[str, Any]] = []
        self.benchmark_history: List[float] = []
        
        # Analysis results
        self.current_metrics: Optional[PortfolioMetrics] = None
        self.risk_metrics: Optional[RiskMetrics] = None
        self.allocation_targets: Dict[str, float] = {}
        self.rebalance_signals: List[AssetAllocation] = []
        
        # Performance tracking
        self.daily_returns: List[float] = []
        self.cumulative_returns: List[float] = []
        self.drawdown_history: List[float] = []
        
        logger.info("PortfolioIntelligence initialized")
    
    def update_position(self, symbol: str, quantity: float, price: float, 
                       cost_basis: float = None) -> None:
        """
        Update position information.
        
        Args:
            symbol: Trading pair symbol
            quantity: Position quantity
            price: Current price
            cost_basis: Cost basis for the position
        """
        if cost_basis is None:
            cost_basis = price
        
        self.positions[symbol] = {
            'quantity': quantity,
            'price': price,
            'cost_basis': cost_basis,
            'market_value': quantity * price,
            'unrealized_pnl': (price - cost_basis) * quantity,
            'weight': 0.0,  # Will be calculated in analyze_portfolio
            'last_updated': datetime.now()
        }
        
        # Update price history
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(price)
        
        # Keep reasonable history size
        if len(self.price_history[symbol]) > 1000:
            self.price_history[symbol] = self.price_history[symbol][-1000:]
        
        logger.debug(f"Updated position: {symbol} @ {price}")
    
    def remove_position(self, symbol: str) -> None:
        """Remove a position from the portfolio."""
        if symbol in self.positions:
            del self.positions[symbol]
            logger.debug(f"Removed position: {symbol}")
    
    def analyze_portfolio(self) -> PortfolioMetrics:
        """
        Perform comprehensive portfolio analysis.
        
        Returns:
            PortfolioMetrics object with analysis results
        """
        try:
            if not self.positions:
                return PortfolioMetrics(
                    total_value=0.0,
                    total_pnl=0.0,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    total_return=0.0,
                    annualized_return=0.0,
                    volatility=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    var_95=0.0,
                    beta=0.0,
                    alpha=0.0
                )
            
            # Calculate basic metrics
            total_value = sum(pos['market_value'] for pos in self.positions.values())
            total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in self.positions.values())
            
            # Update position weights
            for symbol, position in self.positions.items():
                position['weight'] = position['market_value'] / total_value if total_value > 0 else 0.0
            
            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns()
            
            # Calculate performance metrics
            total_return = portfolio_returns[-1] if portfolio_returns else 0.0
            annualized_return = self._calculate_annualized_return(portfolio_returns)
            volatility = np.std(portfolio_returns) * np.sqrt(252) if len(portfolio_returns) > 1 else 0.0
            sharpe_ratio = (annualized_return - self.risk_free_rate) / volatility if volatility > 0 else 0.0
            
            # Calculate drawdown
            cumulative_returns = np.cumprod(1 + np.array(portfolio_returns))
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0
            
            # Calculate win rate and profit factor
            win_rate, profit_factor = self._calculate_win_metrics(portfolio_returns)
            
            # Calculate VaR
            var_95 = np.percentile(portfolio_returns, 5) if len(portfolio_returns) > 0 else 0.0
            
            # Calculate beta and alpha
            beta, alpha = self._calculate_beta_alpha(portfolio_returns)
            
            # Calculate correlation matrix
            correlation_matrix = self._calculate_correlation_matrix()
            
            # Create metrics object
            metrics = PortfolioMetrics(
                total_value=total_value,
                total_pnl=total_unrealized_pnl,
                unrealized_pnl=total_unrealized_pnl,
                realized_pnl=0.0,  # Would need trade history
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                var_95=var_95,
                beta=beta,
                alpha=alpha,
                correlation_matrix=correlation_matrix
            )
            
            self.current_metrics = metrics
            
            # Store in history
            self.portfolio_history.append({
                'timestamp': datetime.now(),
                'total_value': total_value,
                'total_pnl': total_unrealized_pnl,
                'positions': dict(self.positions)
            })
            
            # Keep history manageable
            if len(self.portfolio_history) > 1000:
                self.portfolio_history = self.portfolio_history[-1000:]
            
            logger.info(f"Portfolio analyzed: Value={total_value:.2f}, Return={total_return:.2%}, Sharpe={sharpe_ratio:.2f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {e}")
            return PortfolioMetrics(
                total_value=0.0, total_pnl=0.0, unrealized_pnl=0.0, realized_pnl=0.0,
                total_return=0.0, annualized_return=0.0, volatility=0.0, sharpe_ratio=0.0,
                max_drawdown=0.0, win_rate=0.0, profit_factor=0.0, var_95=0.0, beta=0.0, alpha=0.0
            )
    
    def assess_risk(self) -> RiskMetrics:
        """
        Assess portfolio risk across multiple dimensions.
        
        Returns:
            RiskMetrics object with risk assessment
        """
        try:
            if not self.positions:
                return RiskMetrics(
                    portfolio_volatility=0.0,
                    concentration_risk=0.0,
                    correlation_risk=0.0,
                    liquidity_risk=0.0,
                    market_risk=0.0,
                    overall_risk_score=0.0,
                    risk_level="low"
                )
            
            # Calculate portfolio volatility
            portfolio_returns = self._calculate_portfolio_returns()
            portfolio_volatility = np.std(portfolio_returns) * np.sqrt(252) if len(portfolio_returns) > 1 else 0.0
            
            # Calculate concentration risk (Herfindahl-Hirschman Index)
            weights = [pos['weight'] for pos in self.positions.values()]
            concentration_risk = sum(w**2 for w in weights) if weights else 0.0
            
            # Calculate correlation risk
            correlation_matrix = self._calculate_correlation_matrix()
            correlation_risk = self._calculate_correlation_risk(correlation_matrix)
            
            # Calculate liquidity risk (simplified)
            liquidity_risk = self._calculate_liquidity_risk()
            
            # Calculate market risk (beta-based)
            portfolio_returns = self._calculate_portfolio_returns()
            beta, _ = self._calculate_beta_alpha(portfolio_returns)
            market_risk = abs(beta) if beta != 0 else 0.0
            
            # Calculate overall risk score
            risk_components = [
                portfolio_volatility * 0.3,
                concentration_risk * 0.25,
                correlation_risk * 0.2,
                liquidity_risk * 0.15,
                market_risk * 0.1
            ]
            overall_risk_score = sum(risk_components)
            
            # Determine risk level
            if overall_risk_score < 0.2:
                risk_level = "low"
            elif overall_risk_score < 0.4:
                risk_level = "medium"
            elif overall_risk_score < 0.6:
                risk_level = "high"
            else:
                risk_level = "very_high"
            
            risk_metrics = RiskMetrics(
                portfolio_volatility=portfolio_volatility,
                concentration_risk=concentration_risk,
                correlation_risk=correlation_risk,
                liquidity_risk=liquidity_risk,
                market_risk=market_risk,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level
            )
            
            self.risk_metrics = risk_metrics
            
            logger.info(f"Risk assessed: Overall={overall_risk_score:.2f}, Level={risk_level}")
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Error assessing risk: {e}")
            return RiskMetrics(
                portfolio_volatility=0.0,
                concentration_risk=0.0,
                correlation_risk=0.0,
                liquidity_risk=0.0,
                market_risk=0.0,
                overall_risk_score=0.0,
                risk_level="low"
            )
    
    def generate_rebalance_signals(self, target_allocation: Dict[str, float]) -> List[AssetAllocation]:
        """
        Generate rebalancing signals based on target allocation.
        
        Args:
            target_allocation: Dictionary mapping symbols to target weights
            
        Returns:
            List of AssetAllocation objects with rebalancing recommendations
        """
        try:
            if not self.positions:
                return []
            
            total_value = sum(pos['market_value'] for pos in self.positions.values())
            signals = []
            
            # Store target allocation
            self.allocation_targets = target_allocation
            
            # Check each position
            for symbol, position in self.positions.items():
                current_weight = position['weight']
                target_weight = target_allocation.get(symbol, 0.0)
                
                current_value = position['market_value']
                target_value = total_value * target_weight
                
                rebalance_amount = target_value - current_value
                weight_diff = abs(current_weight - target_weight)
                
                # Determine rebalance direction
                if weight_diff > self.rebalance_threshold:
                    if rebalance_amount > 0:
                        direction = "buy"
                    elif rebalance_amount < 0:
                        direction = "sell"
                    else:
                        direction = "hold"
                    
                    allocation = AssetAllocation(
                        symbol=symbol,
                        current_weight=current_weight,
                        target_weight=target_weight,
                        current_value=current_value,
                        target_value=target_value,
                        rebalance_amount=rebalance_amount,
                        rebalance_direction=direction
                    )
                    
                    signals.append(allocation)
            
            # Check for new positions in target allocation
            for symbol, target_weight in target_allocation.items():
                if symbol not in self.positions and target_weight > 0:
                    target_value = total_value * target_weight
                    
                    allocation = AssetAllocation(
                        symbol=symbol,
                        current_weight=0.0,
                        target_weight=target_weight,
                        current_value=0.0,
                        target_value=target_value,
                        rebalance_amount=target_value,
                        rebalance_direction="buy"
                    )
                    
                    signals.append(allocation)
            
            self.rebalance_signals = signals
            
            logger.info(f"Generated {len(signals)} rebalance signals")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating rebalance signals: {e}")
            return []
    
    def _calculate_portfolio_returns(self) -> List[float]:
        """Calculate daily portfolio returns."""
        if not self.portfolio_history or len(self.portfolio_history) < 2:
            return []
        
        returns = []
        for i in range(1, len(self.portfolio_history)):
            prev_value = self.portfolio_history[i-1]['total_value']
            curr_value = self.portfolio_history[i]['total_value']
            
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
        
        return returns
    
    def _calculate_annualized_return(self, returns: List[float]) -> float:
        """Calculate annualized return from daily returns."""
        if not returns:
            return 0.0
        
        cumulative_return = np.prod(1 + np.array(returns))
        days = len(returns)
        
        if days == 0:
            return 0.0
        
        annualized_return = (cumulative_return ** (252 / days)) - 1
        return annualized_return
    
    def _calculate_win_metrics(self, returns: List[float]) -> Tuple[float, float]:
        """Calculate win rate and profit factor."""
        if not returns:
            return 0.0, 0.0
        
        winning_trades = [r for r in returns if r > 0]
        losing_trades = [r for r in returns if r < 0]
        
        win_rate = len(winning_trades) / len(returns) if returns else 0.0
        
        gross_profit = sum(winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0.0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return win_rate, profit_factor
    
    def _calculate_beta_alpha(self, returns: List[float]) -> Tuple[float, float]:
        """Calculate portfolio beta and alpha against benchmark."""
        if not returns or not self.benchmark_history:
            return 0.0, 0.0
        
        # Align returns with benchmark
        min_length = min(len(returns), len(self.benchmark_history))
        if min_length < 2:
            return 0.0, 0.0
        
        portfolio_returns = np.array(returns[-min_length:])
        benchmark_returns = np.array(self.benchmark_history[-min_length:])
        
        # Calculate beta
        covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 0.0
        
        # Calculate alpha
        portfolio_mean = np.mean(portfolio_returns)
        benchmark_mean = np.mean(benchmark_returns)
        
        alpha = portfolio_mean - (beta * benchmark_mean)
        
        return beta, alpha
    
    def _calculate_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between positions."""
        if len(self.positions) < 2:
            return {}
        
        symbols = list(self.positions.keys())
        correlation_matrix = {}
        
        for symbol1 in symbols:
            correlation_matrix[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    correlation_matrix[symbol1][symbol2] = 1.0
                elif symbol1 in self.price_history and symbol2 in self.price_history:
                    # Calculate correlation between price histories
                    prices1 = self.price_history[symbol1]
                    prices2 = self.price_history[symbol2]
                    
                    min_length = min(len(prices1), len(prices2))
                    if min_length > 10:
                        returns1 = np.diff(prices1[-min_length:]) / np.array(prices1[-min_length:-1])
                        returns2 = np.diff(prices2[-min_length:]) / np.array(prices2[-min_length:-1])
                        
                        correlation = np.corrcoef(returns1, returns2)[0, 1]
                        correlation_matrix[symbol1][symbol2] = correlation if not np.isnan(correlation) else 0.0
                    else:
                        correlation_matrix[symbol1][symbol2] = 0.0
                else:
                    correlation_matrix[symbol1][symbol2] = 0.0
        
        return correlation_matrix
    
    def _calculate_correlation_risk(self, correlation_matrix: Dict[str, Dict[str, float]]) -> float:
        """Calculate correlation risk from correlation matrix."""
        if not correlation_matrix:
            return 0.0
        
        # Calculate average correlation (excluding self-correlation)
        correlations = []
        for symbol1 in correlation_matrix:
            for symbol2 in correlation_matrix[symbol1]:
                if symbol1 != symbol2:
                    correlations.append(abs(correlation_matrix[symbol1][symbol2]))
        
        if not correlations:
            return 0.0
        
        # High correlation means high risk
        avg_correlation = np.mean(correlations)
        return avg_correlation
    
    def _calculate_liquidity_risk(self) -> float:
        """Calculate liquidity risk (simplified)."""
        # This is a simplified implementation
        # In practice, this would consider trading volumes, bid-ask spreads, etc.
        
        # For now, assume smaller positions have higher liquidity risk
        total_value = sum(pos['market_value'] for pos in self.positions.values())
        if total_value == 0:
            return 0.0
        
        # Calculate weighted average of position sizes
        position_sizes = [pos['market_value'] / total_value for pos in self.positions.values()]
        
        # Smaller positions indicate higher liquidity risk
        avg_position_size = np.mean(position_sizes)
        liquidity_risk = 1.0 - avg_position_size  # Inverse relationship
        
        return max(0.0, min(1.0, liquidity_risk))
    
    def get_portfolio_signal(self) -> PortfolioSignal:
        """
        Generate overall portfolio signal based on analysis.
        
        Returns:
            PortfolioSignal enum value
        """
        try:
            if not self.current_metrics or not self.risk_metrics:
                return PortfolioSignal.HOLD
            
            # Decision logic based on metrics
            sharpe_ratio = self.current_metrics.sharpe_ratio
            total_return = self.current_metrics.total_return
            risk_level = self.risk_metrics.risk_level
            
            # Strong buy conditions
            if sharpe_ratio > 2.0 and total_return > 0.1 and risk_level in ["low", "medium"]:
                return PortfolioSignal.STRONG_BUY
            
            # Buy conditions
            elif sharpe_ratio > 1.0 and total_return > 0.05 and risk_level in ["low", "medium"]:
                return PortfolioSignal.BUY
            
            # Sell conditions
            elif sharpe_ratio < -1.0 or total_return < -0.1 or risk_level == "very_high":
                return PortfolioSignal.STRONG_SELL
            
            elif sharpe_ratio < -0.5 or total_return < -0.05 or risk_level == "high":
                return PortfolioSignal.SELL
            
            # Rebalance conditions
            elif self.rebalance_signals:
                return PortfolioSignal.REBALANCE
            
            # Default to hold
            else:
                return PortfolioSignal.HOLD
                
        except Exception as e:
            logger.error(f"Error generating portfolio signal: {e}")
            return PortfolioSignal.HOLD
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        try:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'positions': {
                    symbol: {
                        'quantity': pos['quantity'],
                        'price': pos['price'],
                        'market_value': pos['market_value'],
                        'weight': pos['weight'],
                        'unrealized_pnl': pos['unrealized_pnl']
                    }
                    for symbol, pos in self.positions.items()
                },
                'metrics': {
                    'total_value': self.current_metrics.total_value if self.current_metrics else 0.0,
                    'total_return': self.current_metrics.total_return if self.current_metrics else 0.0,
                    'sharpe_ratio': self.current_metrics.sharpe_ratio if self.current_metrics else 0.0,
                    'max_drawdown': self.current_metrics.max_drawdown if self.current_metrics else 0.0,
                    'volatility': self.current_metrics.volatility if self.current_metrics else 0.0
                },
                'risk': {
                    'overall_risk_score': self.risk_metrics.overall_risk_score if self.risk_metrics else 0.0,
                    'risk_level': self.risk_metrics.risk_level if self.risk_metrics else "unknown",
                    'concentration_risk': self.risk_metrics.concentration_risk if self.risk_metrics else 0.0
                },
                'signals': {
                    'portfolio_signal': self.get_portfolio_signal().value,
                    'rebalance_needed': len(self.rebalance_signals) > 0,
                    'rebalance_signals': len(self.rebalance_signals)
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating portfolio summary: {e}")
            return {}
    
    def reset(self) -> None:
        """Reset portfolio intelligence state."""
        self.positions.clear()
        self.price_history.clear()
        self.portfolio_history.clear()
        self.benchmark_history.clear()
        self.current_metrics = None
        self.risk_metrics = None
        self.allocation_targets.clear()
        self.rebalance_signals.clear()
        self.daily_returns.clear()
        self.cumulative_returns.clear()
        self.drawdown_history.clear()
        
        logger.info("PortfolioIntelligence reset")