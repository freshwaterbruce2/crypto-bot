"""
Kraken Order Validator

Validates orders against Kraken minimum requirements based on official documentation.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class KrakenOrderValidator:
    """
    Validates orders against Kraken minimum requirements.

    Based on Kraken documentation:
    - Order minimum requirements (ordermin)
    - Cost minimum requirements (costmin)
    - Tick size validation
    """

    def __init__(self):
        # Default Kraken minimums for USDT pairs (primary focus)
        self.pair_minimums = {
            # USDT pairs (our focus)
            "BTC/USDT": {"ordermin": 0.0001, "costmin": 1.0, "tick_size": 0.01},
            "ETH/USDT": {"ordermin": 0.001, "costmin": 1.0, "tick_size": 0.01},
            "ADA/USDT": {"ordermin": 1.0, "costmin": 1.0, "tick_size": 0.0001},
            "SOL/USDT": {"ordermin": 0.01, "costmin": 1.0, "tick_size": 0.001},
            "SHIB/USDT": {"ordermin": 1000.0, "costmin": 1.0, "tick_size": 0.000001},
            "DOGE/USDT": {"ordermin": 1.0, "costmin": 1.0, "tick_size": 0.00001},
            "AVAX/USDT": {"ordermin": 0.01, "costmin": 1.0, "tick_size": 0.001},
            "DOT/USDT": {"ordermin": 0.1, "costmin": 1.0, "tick_size": 0.0001},
            "LINK/USDT": {"ordermin": 0.1, "costmin": 1.0, "tick_size": 0.0001},
            "ATOM/USDT": {"ordermin": 0.1, "costmin": 1.0, "tick_size": 0.0001},
            # Legacy USD pairs for reference
            "BTC/USD": {"ordermin": 0.0001, "costmin": 1.0, "tick_size": 0.1},
            "ETH/USD": {"ordermin": 0.001, "costmin": 1.0, "tick_size": 0.01},
        }
        logger.info("[ORDER_VALIDATOR] Initialized with Kraken minimum requirements")

    def validate_order(self, symbol: str, quantity: float, price: float) -> dict[str, Any]:
        """Validate order against Kraken requirements."""
        try:
            # Get pair minimums
            minimums = self.pair_minimums.get(symbol, {
                "ordermin": 0.0001,
                "costmin": 1.0,
                "tick_size": 0.0001
            })

            cost = quantity * price
            errors = []

            # Check order minimum
            if quantity < minimums["ordermin"]:
                errors.append(f"Order quantity {quantity} below minimum {minimums['ordermin']}")

            # Check cost minimum
            if cost < minimums["costmin"]:
                errors.append(f"Order cost ${cost:.2f} below minimum ${minimums['costmin']}")

            # Check tick size
            if price % minimums["tick_size"] != 0:
                errors.append(f"Price {price} not multiple of tick size {minimums['tick_size']}")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "quantity": quantity,
                "price": price,
                "cost": cost,
                "minimums": minimums
            }

        except Exception as e:
            logger.error(f"[ORDER_VALIDATOR] Error validating order: {e}")
            return {"valid": False, "errors": [str(e)]}
