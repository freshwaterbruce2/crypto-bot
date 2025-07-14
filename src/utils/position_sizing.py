"""
Unified Position Sizing Utility
Centralized position sizing logic to eliminate duplication across strategies
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from ..config.constants import MINIMUM_ORDER_SIZE_TIER1

logger = logging.getLogger(__name__)


class PositionSizeCalculator:
    """Unified position sizing calculator for all trading strategies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_size = config.get('position_size_usdt', MINIMUM_ORDER_SIZE_TIER1)
        self.min_size = config.get('min_order_size_usdt', 1.0)
        self.max_size = config.get('max_order_size_usdt', 100.0)
        self.tier_1_limit = config.get('tier_1_trade_limit', 5.0)
        self.api_tier = config.get('kraken_api_tier', 'starter')
        
    def calculate_position_size(self, symbol: str, analysis: Dict[str, Any], 
                              balance: Optional[float] = None) -> float:
        """
        Calculate position size based on confidence and risk parameters
        
        Args:
            symbol: Trading pair symbol
            analysis: Analysis data containing confidence score
            balance: Available balance (optional)
            
        Returns:
            float: Calculated position size in USDT
        """
        try:
            confidence = analysis.get('confidence', 0)
            volatility = analysis.get('volatility', 0.02)
            
            # Base size calculation
            base_size = self.base_size
            
            # Confidence-based scaling (0.5x to 1.5x multiplier)
            confidence_multiplier = 0.5 + (confidence * 1.0)
            
            # Volatility adjustment (reduce size for high volatility)
            volatility_adjustment = max(0.5, 1.0 - (volatility * 10))
            
            # Calculate preliminary size
            calculated_size = base_size * confidence_multiplier * volatility_adjustment
            
            # Apply tier-1 limits for starter accounts
            if self.api_tier == 'starter':
                calculated_size = min(calculated_size, self.tier_1_limit)
            
            # Apply min/max constraints
            calculated_size = max(self.min_size, min(calculated_size, self.max_size))
            
            # Balance-based adjustment if balance is provided
            if balance is not None:
                max_position_pct = self.config.get('max_position_pct', 0.8)
                max_allowed = balance * max_position_pct
                calculated_size = min(calculated_size, max_allowed)
            
            # Round to 2 decimal places
            final_size = round(calculated_size, 2)
            
            logger.debug(f"[POSITION_SIZE] {symbol}: confidence={confidence:.3f}, "
                        f"volatility={volatility:.3f}, size=${final_size:.2f}")
            
            return final_size
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return self.base_size
    
    def calculate_dynamic_size(self, symbol: str, analysis: Dict[str, Any], 
                             portfolio_state: Dict[str, Any]) -> float:
        """
        Calculate dynamic position size based on portfolio state
        
        Args:
            symbol: Trading pair symbol
            analysis: Analysis data
            portfolio_state: Current portfolio state
            
        Returns:
            float: Dynamic position size in USDT
        """
        try:
            # Get base calculation
            base_size = self.calculate_position_size(symbol, analysis)
            
            # Portfolio-based adjustments
            liquid_balance = portfolio_state.get('liquid_balance', 0)
            total_portfolio = portfolio_state.get('total_value', liquid_balance)
            deployment_ratio = portfolio_state.get('deployment_ratio', 0)
            
            # Reduce size if portfolio is heavily deployed
            if deployment_ratio > 0.8:
                deployment_penalty = 0.5
            elif deployment_ratio > 0.6:
                deployment_penalty = 0.75
            else:
                deployment_penalty = 1.0
            
            # Apply portfolio-based scaling
            dynamic_size = base_size * deployment_penalty
            
            # Ensure we don't exceed available balance
            if liquid_balance > 0:
                dynamic_size = min(dynamic_size, liquid_balance * 0.8)
            
            return max(self.min_size, round(dynamic_size, 2))
            
        except Exception as e:
            logger.error(f"Error calculating dynamic position size for {symbol}: {e}")
            return self.calculate_position_size(symbol, analysis)
    
    def validate_position_size(self, size: float, symbol: str, 
                             available_balance: float) -> Dict[str, Any]:
        """
        Validate and adjust position size if needed
        
        Args:
            size: Requested position size
            symbol: Trading pair symbol
            available_balance: Available balance
            
        Returns:
            Dict containing validation result and adjusted size
        """
        try:
            # Check minimum size
            if size < self.min_size:
                return {
                    'valid': False,
                    'adjusted_size': self.min_size,
                    'reason': f'Below minimum size ${self.min_size}',
                    'auto_adjust': size >= self.min_size * 0.8
                }
            
            # Check maximum size
            if size > self.max_size:
                return {
                    'valid': False,
                    'adjusted_size': self.max_size,
                    'reason': f'Above maximum size ${self.max_size}',
                    'auto_adjust': True
                }
            
            # Check tier-1 limits
            if self.api_tier == 'starter' and size > self.tier_1_limit:
                return {
                    'valid': False,
                    'adjusted_size': self.tier_1_limit,
                    'reason': f'Exceeds tier-1 limit ${self.tier_1_limit}',
                    'auto_adjust': True
                }
            
            # Check balance availability
            max_position_pct = self.config.get('max_position_pct', 0.8)
            max_allowed = available_balance * max_position_pct
            
            if size > max_allowed:
                return {
                    'valid': False,
                    'adjusted_size': max_allowed,
                    'reason': f'Exceeds {max_position_pct:.1%} of available balance',
                    'auto_adjust': max_allowed >= self.min_size
                }
            
            # All checks passed
            return {
                'valid': True,
                'adjusted_size': size,
                'reason': 'Position size valid',
                'auto_adjust': False
            }
            
        except Exception as e:
            logger.error(f"Error validating position size for {symbol}: {e}")
            return {
                'valid': False,
                'adjusted_size': self.base_size,
                'reason': f'Validation error: {str(e)}',
                'auto_adjust': False
            }


# Global instance for easy access
_position_calculator = None


def get_position_calculator(config: Dict[str, Any] = None) -> PositionSizeCalculator:
    """Get or create position size calculator instance"""
    global _position_calculator
    
    if _position_calculator is None or config is not None:
        _position_calculator = PositionSizeCalculator(config or {})
    
    return _position_calculator


def calculate_position_size(symbol: str, analysis: Dict[str, Any], 
                          config: Dict[str, Any] = None, 
                          balance: Optional[float] = None) -> float:
    """
    Convenience function for position size calculation
    
    Args:
        symbol: Trading pair symbol
        analysis: Analysis data containing confidence score
        config: Configuration dictionary (optional)
        balance: Available balance (optional)
        
    Returns:
        float: Calculated position size in USDT
    """
    calculator = get_position_calculator(config)
    return calculator.calculate_position_size(symbol, analysis, balance)


def validate_position_size(size: float, symbol: str, available_balance: float,
                         config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function for position size validation
    
    Args:
        size: Requested position size
        symbol: Trading pair symbol
        available_balance: Available balance
        config: Configuration dictionary (optional)
        
    Returns:
        Dict containing validation result
    """
    calculator = get_position_calculator(config)
    return calculator.validate_position_size(size, symbol, available_balance)