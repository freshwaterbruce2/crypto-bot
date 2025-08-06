"""
Trade Assistant - Core trading operations helper
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional


class TradeAssistant:
    """Assistant for trade-related operations"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def validate_trade_parameters(self, symbol: str, side: str, amount: Decimal, price: Optional[Decimal] = None) -> bool:
        """Validate trade parameters"""
        try:
            # Basic validation
            if not symbol or not side or amount <= 0:
                return False

            # Check minimum order size
            if amount < Decimal('0.0001'):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Trade validation error: {e}")
            return False

    def calculate_position_size(self, symbol: str, balance: Decimal, risk_percentage: float = 0.1) -> Decimal:
        """Calculate appropriate position size"""
        try:
            # Simple position sizing based on risk percentage
            position_size = balance * Decimal(str(risk_percentage))
            return max(position_size, Decimal('0.0001'))

        except Exception as e:
            self.logger.error(f"Position size calculation error: {e}")
            return Decimal('0.0001')
