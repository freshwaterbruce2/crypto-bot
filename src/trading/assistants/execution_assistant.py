"""
Execution Assistant - Trade execution helper
"""

import logging
from decimal import Decimal
from typing import Any, Optional


class ExecutionAssistant:
    """Assistant for trade execution operations"""

    def __init__(self, config: dict[str, Any], bot_reference: Any = None):
        self.config = config
        self.bot = bot_reference  # CLAUDE FLOW FIX: Add bot reference for compatibility
        self.bot_reference = bot_reference  # Primary reference
        self.logger = logging.getLogger(__name__)

    def prepare_order_parameters(self, symbol: str, side: str, amount: Decimal,
                               order_type: str = 'market', price: Optional[Decimal] = None) -> dict[str, Any]:
        """Prepare order parameters for execution"""
        try:
            params = {
                'symbol': symbol,
                'side': side,
                'amount': str(amount),
                'type': order_type
            }

            if price is not None and order_type == 'limit':
                params['price'] = str(price)

            return params

        except Exception as e:
            self.logger.error(f"Order parameter preparation error: {e}")
            return {}

    def validate_execution_conditions(self, symbol: str, market_conditions: dict[str, Any]) -> bool:
        """Validate if conditions are suitable for execution"""
        try:
            # Basic validation - in real implementation would check volatility, liquidity, etc.
            if not market_conditions:
                return False

            # Check if symbol is active
            if 'status' in market_conditions and market_conditions['status'] != 'active':
                return False

            return True

        except Exception as e:
            self.logger.error(f"Execution condition validation error: {e}")
            return False
