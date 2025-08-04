"""
Vectorized Mathematical Operations for High-Performance Trading
==============================================================

NumPy-based vectorized calculations for portfolio analysis, risk assessment,
and bulk trading operations. Provides significant performance improvements
for operations on multiple assets or historical data.
"""

import logging
from typing import Dict, List, Tuple, Optional, Union, Any
import time
from functools import wraps

logger = logging.getLogger(__name__)

# Optional NumPy import with fallback
try:
    import numpy as np
    HAS_NUMPY = True
    logger.info("[VECTORIZED] NumPy available for high-performance calculations")
except ImportError:
    logger.warning("[VECTORIZED] NumPy not available, falling back to Python native operations")
    HAS_NUMPY = False
    # Create minimal numpy-like interface for fallback
    class MockNumPy:
        @staticmethod
        def array(data):
            return data
        
        @staticmethod
        def mean(data):
            return sum(data) / len(data) if data else 0
        
        @staticmethod
        def std(data):
            if not data:
                return 0
            mean_val = sum(data) / len(data)
            variance = sum((x - mean_val) ** 2 for x in data) / len(data)
            return variance ** 0.5
        
        @staticmethod
        def sum(data):
            return sum(data) if data else 0
        
        @staticmethod
        def max(data):
            return max(data) if data else 0
        
        @staticmethod
        def min(data):
            return min(data) if data else 0
    
    np = MockNumPy()


def require_numpy(func):
    """Decorator to check NumPy availability"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not HAS_NUMPY:
            logger.warning(f"[VECTORIZED] {func.__name__} requires NumPy, using fallback")
            # Try to find fallback function
            fallback_name = f"{func.__name__}_fallback"
            if hasattr(func.__self__ if hasattr(func, '__self__') else func.__module__, fallback_name):
                fallback_func = getattr(func.__self__ if hasattr(func, '__self__') else func.__module__, fallback_name)
                return fallback_func(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper


class VectorizedPortfolioAnalyzer:
    """High-performance portfolio analysis using vectorized operations"""
    
    def __init__(self):
        self.calculation_cache = {}
        self.performance_stats = {
            'operations': 0,
            'total_time': 0.0,
            'cache_hits': 0
        }
    
    @require_numpy
    def analyze_portfolio_performance(self, 
                                    positions: List[Dict[str, Any]],
                                    price_history: Dict[str, List[float]]) -> Dict[str, Any]:
        """Vectorized portfolio performance analysis"""
        start_time = time.time()
        
        if not positions:
            return self._empty_portfolio_result()
        
        try:
            # Extract position data
            symbols = [pos['symbol'] for pos in positions]
            quantities = np.array([pos.get('quantity', 0) for pos in positions])
            entry_prices = np.array([pos.get('entry_price', 0) for pos in positions])
            current_prices = np.array([pos.get('current_price', 0) for pos in positions])
            
            # Calculate position values
            position_values = quantities * current_prices
            entry_values = quantities * entry_prices
            
            # Calculate P&L
            unrealized_pnl = position_values - entry_values
            total_unrealized_pnl = np.sum(unrealized_pnl)
            
            # Calculate portfolio metrics
            total_value = np.sum(position_values)
            total_invested = np.sum(entry_values)
            
            # Risk metrics
            position_weights = position_values / total_value if total_value > 0 else np.zeros_like(position_values)
            max_position_weight = np.max(position_weights) if len(position_weights) > 0 else 0
            
            # Volatility analysis (if price history available)
            portfolio_volatility = 0.0
            sharpe_ratio = 0.0
            
            if price_history and len(price_history) > 0:
                portfolio_volatility, sharpe_ratio = self._calculate_portfolio_risk_metrics(
                    symbols, quantities, price_history, position_weights
                )
            
            # Performance tracking
            self.performance_stats['operations'] += 1
            self.performance_stats['total_time'] += time.time() - start_time
            
            return {
                'total_value': float(total_value),
                'total_invested': float(total_invested),
                'unrealized_pnl': float(total_unrealized_pnl),
                'unrealized_pnl_pct': float((total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0),
                'position_count': len(positions),
                'max_position_weight': float(max_position_weight),
                'portfolio_volatility': float(portfolio_volatility),
                'sharpe_ratio': float(sharpe_ratio),
                'position_breakdown': [
                    {
                        'symbol': symbol,
                        'value': float(value),
                        'pnl': float(pnl),
                        'weight': float(weight)
                    }
                    for symbol, value, pnl, weight in zip(symbols, position_values, unrealized_pnl, position_weights)
                ],
                'calculation_time': time.time() - start_time,
                'used_numpy': HAS_NUMPY
            }
            
        except Exception as e:
            logger.error(f"[VECTORIZED] Portfolio analysis error: {e}")
            return self._empty_portfolio_result()
    
    def _calculate_portfolio_risk_metrics(self, 
                                        symbols: List[str], 
                                        quantities: np.ndarray,
                                        price_history: Dict[str, List[float]],
                                        weights: np.ndarray) -> Tuple[float, float]:
        """Calculate portfolio volatility and Sharpe ratio"""
        try:
            # Calculate returns for each asset
            returns_matrix = []
            
            for symbol in symbols:
                if symbol in price_history and len(price_history[symbol]) > 1:
                    prices = np.array(price_history[symbol])
                    returns = np.diff(prices) / prices[:-1]
                    returns_matrix.append(returns)
                else:
                    # If no history, assume zero returns
                    returns_matrix.append(np.zeros(30))  # Default 30 periods
            
            if not returns_matrix:
                return 0.0, 0.0
            
            # Ensure all return series have the same length
            min_length = min(len(returns) for returns in returns_matrix)
            returns_matrix = [returns[:min_length] for returns in returns_matrix]
            
            # Convert to numpy array
            returns_array = np.array(returns_matrix)
            
            # Calculate portfolio returns
            portfolio_returns = np.dot(weights[:len(returns_matrix)], returns_array)
            
            # Calculate volatility (annualized)
            volatility = np.std(portfolio_returns) * np.sqrt(252)  # 252 trading days
            
            # Calculate Sharpe ratio (assuming 0% risk-free rate)
            mean_return = np.mean(portfolio_returns) * 252  # Annualized
            sharpe_ratio = mean_return / volatility if volatility > 0 else 0.0
            
            return float(volatility), float(sharpe_ratio)
            
        except Exception as e:
            logger.error(f"[VECTORIZED] Risk metrics calculation error: {e}")
            return 0.0, 0.0
    
    def _empty_portfolio_result(self) -> Dict[str, Any]:
        """Return empty portfolio analysis result"""
        return {
            'total_value': 0.0,
            'total_invested': 0.0,
            'unrealized_pnl': 0.0,
            'unrealized_pnl_pct': 0.0,
            'position_count': 0,
            'max_position_weight': 0.0,
            'portfolio_volatility': 0.0,
            'sharpe_ratio': 0.0,
            'position_breakdown': [],
            'calculation_time': 0.0,
            'used_numpy': HAS_NUMPY
        }


class VectorizedTechnicalIndicators:
    """High-performance technical indicators using vectorized operations"""
    
    @staticmethod
    @require_numpy
    def calculate_moving_averages(prices: List[float], 
                                windows: List[int]) -> Dict[int, float]:
        """Calculate multiple moving averages efficiently"""
        if not prices or not windows:
            return {}
        
        prices_array = np.array(prices)
        results = {}
        
        for window in windows:
            if len(prices) >= window:
                ma = np.mean(prices_array[-window:])
                results[window] = float(ma)
            else:
                results[window] = float(prices_array[-1]) if len(prices_array) > 0 else 0.0
        
        return results
    
    @staticmethod
    @require_numpy
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate RSI using vectorized operations"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        prices_array = np.array(prices)
        deltas = np.diff(prices_array)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    @staticmethod
    @require_numpy
    def calculate_bollinger_bands(prices: List[float], 
                                period: int = 20, 
                                std_dev: float = 2.0) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            last_price = prices[-1] if prices else 0.0
            return {
                'upper': last_price,
                'middle': last_price,
                'lower': last_price
            }
        
        prices_array = np.array(prices)
        recent_prices = prices_array[-period:]
        
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return {
            'upper': float(upper),
            'middle': float(middle),
            'lower': float(lower)
        }


class VectorizedRiskCalculator:
    """High-performance risk calculations for position sizing and portfolio management"""
    
    @staticmethod
    @require_numpy
    def calculate_position_sizes_batch(balances: List[float],
                                     risk_percentages: List[float],
                                     prices: List[float]) -> List[float]:
        """Calculate position sizes for multiple assets simultaneously"""
        if not balances or not risk_percentages or not prices:
            return []
        
        # Ensure all arrays have the same length
        min_length = min(len(balances), len(risk_percentages), len(prices))
        
        balance_array = np.array(balances[:min_length])
        risk_array = np.array(risk_percentages[:min_length]) / 100.0
        price_array = np.array(prices[:min_length])
        
        # Vectorized calculation
        position_values = balance_array * risk_array
        position_sizes = np.where(price_array > 0, position_values / price_array, 0)
        
        return position_sizes.tolist()
    
    @staticmethod
    @require_numpy
    def calculate_portfolio_var(positions: List[Dict[str, Any]], 
                              price_volatilities: Dict[str, float],
                              confidence_level: float = 0.95,
                              time_horizon: int = 1) -> float:
        """Calculate Portfolio Value at Risk (VaR)"""
        if not positions or not price_volatilities:
            return 0.0
        
        try:
            # Extract position data
            values = []
            volatilities = []
            
            for pos in positions:
                symbol = pos.get('symbol', '')
                value = pos.get('value', 0)
                vol = price_volatilities.get(symbol, 0.0)
                
                values.append(value)
                volatilities.append(vol)
            
            if not values:
                return 0.0
            
            values_array = np.array(values)
            vol_array = np.array(volatilities)
            
            # Calculate portfolio volatility (simplified - assumes no correlation)
            portfolio_value = np.sum(values_array)
            weights = values_array / portfolio_value if portfolio_value > 0 else np.zeros_like(values_array)
            
            # Portfolio variance (assuming zero correlation between assets)
            portfolio_variance = np.sum((weights * vol_array) ** 2)
            portfolio_volatility = np.sqrt(portfolio_variance)
            
            # Scale for time horizon
            portfolio_volatility_scaled = portfolio_volatility * np.sqrt(time_horizon)
            
            # Calculate VaR using normal distribution approximation
            from scipy.stats import norm
            z_score = norm.ppf(confidence_level)
            var = portfolio_value * portfolio_volatility_scaled * z_score
            
            return float(var)
            
        except ImportError:
            # Fallback without scipy
            # Use rule of thumb: 2.33 for 99%, 1.96 for 95%, 1.65 for 90%
            z_scores = {0.99: 2.33, 0.95: 1.96, 0.90: 1.65}
            z_score = z_scores.get(confidence_level, 1.96)
            
            values_array = np.array([pos.get('value', 0) for pos in positions])
            vol_array = np.array([price_volatilities.get(pos.get('symbol', ''), 0.0) for pos in positions])
            
            portfolio_value = np.sum(values_array)
            weights = values_array / portfolio_value if portfolio_value > 0 else np.zeros_like(values_array)
            
            portfolio_variance = np.sum((weights * vol_array) ** 2)
            portfolio_volatility = np.sqrt(portfolio_variance) * np.sqrt(time_horizon)
            
            var = portfolio_value * portfolio_volatility * z_score
            return float(var)
        
        except Exception as e:
            logger.error(f"[VECTORIZED] VaR calculation error: {e}")
            return 0.0


class PerformanceOptimizer:
    """Monitor and optimize vectorized calculation performance"""
    
    def __init__(self):
        self.benchmarks = {}
        self.numpy_available = HAS_NUMPY
    
    def benchmark_operation(self, operation_name: str, 
                          vectorized_func: callable,
                          fallback_func: callable,
                          test_data: Any,
                          iterations: int = 100) -> Dict[str, Any]:
        """Benchmark vectorized vs fallback operations"""
        
        # Benchmark vectorized version
        start_time = time.time()
        for _ in range(iterations):
            vectorized_result = vectorized_func(test_data)
        vectorized_time = time.time() - start_time
        
        # Benchmark fallback version
        start_time = time.time() 
        for _ in range(iterations):
            fallback_result = fallback_func(test_data)
        fallback_time = time.time() - start_time
        
        speedup = fallback_time / vectorized_time if vectorized_time > 0 else 1.0
        
        benchmark_result = {
            'operation': operation_name,
            'vectorized_time': vectorized_time,
            'fallback_time': fallback_time,
            'speedup': speedup,
            'numpy_available': HAS_NUMPY,
            'iterations': iterations
        }
        
        self.benchmarks[operation_name] = benchmark_result
        
        logger.info(f"[VECTORIZED] {operation_name} benchmark: "
                   f"{speedup:.2f}x speedup with vectorization")
        
        return benchmark_result
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            'numpy_available': HAS_NUMPY,
            'total_benchmarks': len(self.benchmarks),
            'benchmarks': self.benchmarks,
            'avg_speedup': np.mean([b['speedup'] for b in self.benchmarks.values()]) if self.benchmarks else 1.0
        }


# Global instances
portfolio_analyzer = VectorizedPortfolioAnalyzer()
technical_indicators = VectorizedTechnicalIndicators()
risk_calculator = VectorizedRiskCalculator()
performance_optimizer = PerformanceOptimizer()

# Export main functions
__all__ = [
    'VectorizedPortfolioAnalyzer',
    'VectorizedTechnicalIndicators', 
    'VectorizedRiskCalculator',
    'PerformanceOptimizer',
    'portfolio_analyzer',
    'technical_indicators',
    'risk_calculator',
    'performance_optimizer',
    'HAS_NUMPY'
]