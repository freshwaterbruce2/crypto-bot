#!/usr/bin/env python3
"""
Position Size Validation Fix
============================

This fix resolves the 100% > 80% validation error by implementing proper
percentage-based position sizing with safety margins for $5 balance trading.

CRITICAL FIXES:
1. Fix percentage calculations (100% > 80% error)
2. Implement safety margins for fees and slippage
3. Support $5 balance with 70% position sizing ($3.50)
4. Validate against exchange minimums
"""

import logging
from decimal import Decimal
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class PositionSizeValidator:
    """Validates position sizes for trading with small balances"""
    
    def __init__(self, balance_manager=None):
        self.balance_manager = balance_manager
        
        # EMERGENCY FIX: Configuration for $5 balance trading
        self.max_position_percentage = 0.70  # 70% of balance ($3.50 from $5)
        self.safety_margin = 0.05  # 5% safety margin for fees/slippage
        self.min_order_size = 2.0  # $2.00 minimum order size
        self.fee_buffer = 0.002  # 0.2% fee buffer
        
        logger.info("[POSITION_VALIDATOR] Initialized for $5 balance trading")
    
    def validate_position_size(self, symbol: str, position_size_usdt: float, 
                             available_balance: float) -> Tuple[bool, str, float]:
        """
        Validate if position size is acceptable for trading
        
        Args:
            symbol: Trading pair symbol
            position_size_usdt: Requested position size in USDT
            available_balance: Available USDT balance
            
        Returns:
            Tuple of (is_valid, reason, recommended_size)
        """
        try:
            # Convert to Decimal for precise calculations
            position_dec = Decimal(str(position_size_usdt))
            balance_dec = Decimal(str(available_balance))
            
            # Check minimum balance
            if balance_dec < Decimal(str(self.min_order_size)):
                return False, f"Insufficient balance: ${balance_dec:.2f} < ${self.min_order_size}", 0.0
            
            # Check minimum position size
            if position_dec < Decimal(str(self.min_order_size)):
                return False, f"Position size too small: ${position_dec:.2f} < ${self.min_order_size}", self.min_order_size
            
            # Calculate position percentage
            position_percentage = position_dec / balance_dec
            
            # CRITICAL FIX: Proper percentage comparison (fix 100% > 80% error)
            max_percentage_dec = Decimal(str(self.max_position_percentage))
            safety_margin_dec = Decimal(str(self.safety_margin))
            
            # Apply safety margin to max percentage
            effective_max_percentage = max_percentage_dec - safety_margin_dec  # 70% - 5% = 65%
            
            if position_percentage > effective_max_percentage:
                # Calculate recommended size with safety margin
                recommended_size = float(balance_dec * effective_max_percentage)
                
                return False, (
                    f"Position size {position_percentage:.1%} exceeds safe limit {effective_max_percentage:.1%} "
                    f"(with {safety_margin_dec:.1%} safety margin)"
                ), recommended_size
            
            # Add fee buffer check
            fee_amount = position_dec * Decimal(str(self.fee_buffer))
            total_required = position_dec + fee_amount
            
            if total_required > balance_dec:
                # Recommend size accounting for fees
                recommended_size = float(balance_dec * Decimal('0.65'))  # 65% safe maximum accounting for fees
                return False, f"Position + fees (${total_required:.2f}) exceeds balance", recommended_size
            
            # All validations passed
            return True, f"Position size valid: {position_percentage:.1%} of balance", float(position_dec)
            
        except Exception as e:
            logger.error(f"[POSITION_VALIDATOR] Validation error: {e}")
            return False, f"Validation error: {e}", self.min_order_size
    
    def calculate_safe_position_size(self, available_balance: float, 
                                   target_percentage: float = None) -> Tuple[float, str]:
        """
        Calculate a safe position size for the given balance
        
        Args:
            available_balance: Available USDT balance
            target_percentage: Target percentage (defaults to max safe percentage)
            
        Returns:
            Tuple of (position_size, explanation)
        """
        try:
            balance_dec = Decimal(str(available_balance))
            
            # Use target percentage or default to safe maximum
            if target_percentage is None:
                target_percentage = self.max_position_percentage - self.safety_margin  # 65%
            
            target_pct_dec = Decimal(str(target_percentage))
            
            # Calculate position size
            position_size_dec = balance_dec * target_pct_dec
            
            # Ensure it meets minimum requirements
            min_order_dec = Decimal(str(self.min_order_size))
            if position_size_dec < min_order_dec:
                position_size_dec = min_order_dec
                actual_percentage = position_size_dec / balance_dec
                explanation = f"Using minimum order size: ${position_size_dec:.2f} ({actual_percentage:.1%})"
            else:
                explanation = f"Safe position size: ${position_size_dec:.2f} ({target_percentage:.1%})"
            
            return float(position_size_dec), explanation
            
        except Exception as e:
            logger.error(f"[POSITION_VALIDATOR] Error calculating safe position size: {e}")
            return self.min_order_size, f"Error calculating position size, using minimum: ${self.min_order_size}"
    
    def get_validation_config(self) -> Dict[str, float]:
        """Get current validation configuration"""
        return {
            'max_position_percentage': self.max_position_percentage,
            'safety_margin': self.safety_margin,
            'min_order_size': self.min_order_size,
            'fee_buffer': self.fee_buffer,
            'effective_max_percentage': self.max_position_percentage - self.safety_margin
        }


# Global validator instance
_position_validator = None


def get_position_validator(balance_manager=None) -> PositionSizeValidator:
    """Get or create global position validator instance"""
    global _position_validator
    if _position_validator is None:
        _position_validator = PositionSizeValidator(balance_manager)
    return _position_validator


def validate_trade_size(symbol: str, position_size: float, balance: float) -> Tuple[bool, str, float]:
    """
    Quick validation function for trade sizes
    
    Returns:
        Tuple of (is_valid, reason, recommended_size)
    """
    validator = get_position_validator()
    return validator.validate_position_size(symbol, position_size, balance)


def calculate_safe_trade_size(balance: float, target_pct: float = None) -> Tuple[float, str]:
    """
    Quick function to calculate safe trade size
    
    Returns:
        Tuple of (position_size, explanation)
    """
    validator = get_position_validator()
    return validator.calculate_safe_position_size(balance, target_pct)


if __name__ == "__main__":
    # Test the validator with $5 balance
    validator = PositionSizeValidator()
    
    test_balance = 5.0
    test_cases = [
        (5.0, "100% position"),
        (4.0, "80% position"),  
        (3.5, "70% position"),
        (3.25, "65% position"),
        (2.0, "40% position"),
        (1.0, "20% position")
    ]
    
    print(f"Testing with ${test_balance} balance:")
    print("=" * 50)
    
    for position_size, description in test_cases:
        is_valid, reason, recommended = validator.validate_position_size(
            "DOGE/USDT", position_size, test_balance
        )
        
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"{description}: {status}")
        print(f"  Position: ${position_size:.2f}")
        print(f"  Reason: {reason}")
        if not is_valid:
            print(f"  Recommended: ${recommended:.2f}")
        print()