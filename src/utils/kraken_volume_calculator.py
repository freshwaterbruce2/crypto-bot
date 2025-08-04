"""
Kraken volume calculator with correct minimums
Ensures all orders meet exchange requirements
"""

from decimal import Decimal, ROUND_UP
from typing import Dict, Tuple, Optional

# Kraken minimum order sizes by base currency
KRAKEN_MINIMUMS = {
    "ADA": 10.0,
    "ALGO": 4.0,
    "APE": 4.0,
    "ATOM": 1.0,
    "AVAX": 0.2,
    "BCH": 0.01,
    "BNB": 0.02,
    "BTC": 0.0001,
    "CRO": 20.0,
    "DOGE": 100.0,
    "DOT": 0.5,
    "ETH": 0.005,
    "LINK": 0.5,
    "MANA": 5.0,
    "MATIC": 5.0,
    "SHIB": 100000.0,
    "SOL": 0.05,
    "AI16Z": 1.0,
    "BERA": 1.0
}

def calculate_order_volume(symbol: str, usdt_amount: float, price: float) -> Tuple[float, float]:
    """
    Calculate order volume that meets Kraken minimums
    
    Args:
        symbol: Trading pair (e.g., 'ADA/USDT')
        usdt_amount: Desired order size in USDT
        price: Current price of the asset
        
    Returns:
        Tuple of (volume, actual_usdt_cost)
    """
    # Extract base currency
    base_currency = symbol.split('/')[0]
    
    # Get minimum volume for this currency
    min_volume = KRAKEN_MINIMUMS.get(base_currency, 1.0)
    
    # Calculate desired volume
    desired_volume = Decimal(str(usdt_amount)) / Decimal(str(price))
    
    # Ensure we meet minimum
    if desired_volume < Decimal(str(min_volume)):
        volume = min_volume
        actual_cost = float(Decimal(str(min_volume)) * Decimal(str(price)))
    else:
        volume = float(desired_volume)
        actual_cost = usdt_amount
    
    return volume, actual_cost

def get_minimum_order_cost(symbol: str, price: float) -> float:
    """Get minimum order cost in USDT for a symbol"""
    base_currency = symbol.split('/')[0]
    min_volume = KRAKEN_MINIMUMS.get(base_currency, 1.0)
    return float(Decimal(str(min_volume)) * Decimal(str(price)))

def meets_minimum_requirements(symbol: str, volume: float) -> bool:
    """Check if volume meets Kraken minimum requirements"""
    base_currency = symbol.split('/')[0]
    min_volume = KRAKEN_MINIMUMS.get(base_currency, 1.0)
    return volume >= min_volume

# Export minimums for other modules
__all__ = ['KRAKEN_MINIMUMS', 'calculate_order_volume', 'get_minimum_order_cost', 'meets_minimum_requirements']
