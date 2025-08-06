"""
Trade Rules
Kraken-specific trading rules and validation
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class KrakenTradeRules:
    """Kraken trading rules and validation"""

    def __init__(self):
        """Initialize Kraken trade rules"""
        self.minimum_order_sizes = {
            "BTC/USDT": 0.0001,
            "ETH/USDT": 0.001,
            "ADA/USDT": 1.0,
            "ALGO/USDT": 1.0,
            "XRP/USDT": 1.0,
            "DOGE/USDT": 100.0,
            "AVAX/USDT": 0.1,
            "DOT/USDT": 0.1,
            "LINK/USDT": 0.1,
            "MATIC/USDT": 1.0,
            "AI16Z/USDT": 1.0,
            "ATOM/USDT": 0.1
        }

        self.minimum_order_value_usdt = 1.0  # Kraken actual minimum for low-priced pairs (CORRECTED)
        self.tier_1_limit = 1.0  # Low balance account minimum for micro-trading

    def get_minimum_order_size(self, symbol: str) -> float:
        """Get minimum order size for symbol"""
        return self.minimum_order_sizes.get(symbol, 1.0)

    def get_minimum_order_value(self) -> float:
        """Get minimum order value in USDT"""
        return self.minimum_order_value_usdt

    def validate_order_size(self, symbol: str, amount: float) -> bool:
        """Validate if order size meets minimum requirements"""
        min_size = self.get_minimum_order_size(symbol)
        return amount >= min_size

    def validate_order_value(self, value_usdt: float) -> bool:
        """Validate if order value meets minimum requirements"""
        return value_usdt >= self.minimum_order_value_usdt

    def check_tier_1_limit(self, value_usdt: float) -> bool:
        """Check if order is within tier 1 limits"""
        return value_usdt <= self.tier_1_limit


# Global instance
trade_rules = KrakenTradeRules()


def check_order(symbol: str, amount: float, price: float) -> Dict[str, Any]:
    """Check if order meets all requirements"""
    order_value = amount * price

    return {
        'valid': (
            trade_rules.validate_order_size(symbol, amount) and
            trade_rules.validate_order_value(order_value) and
            trade_rules.check_tier_1_limit(order_value)
        ),
        'min_size': trade_rules.get_minimum_order_size(symbol),
        'min_value': trade_rules.get_minimum_order_value(),
        'order_value': order_value,
        'within_tier_1': trade_rules.check_tier_1_limit(order_value)
    }


def can_sell(symbol: str, amount: float) -> bool:
    """Check if we can sell the given amount"""
    return trade_rules.validate_order_size(symbol, amount)


def get_minimum_buy(symbol: str, price: float) -> float:
    """Get minimum buy amount for symbol at given price"""
    min_size = trade_rules.get_minimum_order_size(symbol)
    min_value = trade_rules.get_minimum_order_value()

    # Ensure both size and value requirements are met
    min_amount_by_size = min_size
    min_amount_by_value = min_value / price

    return max(min_amount_by_size, min_amount_by_value)


def format_order_amount(amount: float, precision: int = 8) -> str:
    """Format order amount with proper precision"""
    return f"{amount:.{precision}f}".rstrip('0').rstrip('.')
