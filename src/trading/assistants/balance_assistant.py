"""
Balance Assistant - Balance management helper
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional


class BalanceAssistant:
    """Assistant for balance-related operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def validate_balance_for_trade(self, symbol: str, side: str, amount: Decimal, balance: Decimal) -> bool:
        """Validate if balance is sufficient for trade"""
        try:
            # For buy orders, check quote balance
            if side.lower() == 'buy':
                # Rough estimate - in real implementation would use current price
                estimated_cost = amount * Decimal('50000')  # Placeholder price
                return balance >= estimated_cost
            
            # For sell orders, check base balance
            elif side.lower() == 'sell':
                return balance >= amount
                
            return False
            
        except Exception as e:
            self.logger.error(f"Balance validation error: {e}")
            return False
            
    def calculate_available_balance(self, total_balance: Decimal, reserved_balance: Decimal = Decimal('0')) -> Decimal:
        """Calculate available balance for trading"""
        try:
            available = total_balance - reserved_balance
            return max(available, Decimal('0'))
            
        except Exception as e:
            self.logger.error(f"Available balance calculation error: {e}")
            return Decimal('0')