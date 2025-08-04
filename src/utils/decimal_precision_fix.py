"""
Decimal precision fix for micro-profit trading
Replaces all float operations with high-precision Decimal
"""

from decimal import Decimal, ROUND_DOWN, ROUND_UP, getcontext
from typing import Union, Optional, Any, Dict

# Set precision to 18 decimal places for micro-profits
getcontext().prec = 18

class MoneyDecimal:
    """High-precision decimal wrapper for financial calculations"""
    
    def __init__(self, value: Union[str, float, Decimal, int], currency: str = "USDT"):
        """Initialize with string to avoid float precision loss"""
        if isinstance(value, float):
            # Convert float to string with high precision
            self.value = Decimal(str(value))
        elif isinstance(value, (str, int)):
            self.value = Decimal(value)
        elif isinstance(value, Decimal):
            self.value = value
        else:
            self.value = Decimal("0")
        
        self.currency = currency
    
    def __str__(self):
        """String representation with 8 decimal places"""
        return f"{self.value:.8f} {self.currency}"
    
    def __repr__(self):
        return f"MoneyDecimal('{self.value}', '{self.currency}')"
    
    def __add__(self, other):
        if isinstance(other, MoneyDecimal):
            return MoneyDecimal(self.value + other.value, self.currency)
        return MoneyDecimal(self.value + Decimal(str(other)), self.currency)
    
    def __sub__(self, other):
        if isinstance(other, MoneyDecimal):
            return MoneyDecimal(self.value - other.value, self.currency)
        return MoneyDecimal(self.value - Decimal(str(other)), self.currency)
    
    def __mul__(self, other):
        if isinstance(other, MoneyDecimal):
            return MoneyDecimal(self.value * other.value, self.currency)
        return MoneyDecimal(self.value * Decimal(str(other)), self.currency)
    
    def __truediv__(self, other):
        if isinstance(other, MoneyDecimal):
            return MoneyDecimal(self.value / other.value, self.currency)
        return MoneyDecimal(self.value / Decimal(str(other)), self.currency)
    
    def __lt__(self, other):
        if isinstance(other, MoneyDecimal):
            return self.value < other.value
        return self.value < Decimal(str(other))
    
    def __le__(self, other):
        if isinstance(other, MoneyDecimal):
            return self.value <= other.value
        return self.value <= Decimal(str(other))
    
    def __gt__(self, other):
        if isinstance(other, MoneyDecimal):
            return self.value > other.value
        return self.value > Decimal(str(other))
    
    def __ge__(self, other):
        if isinstance(other, MoneyDecimal):
            return self.value >= other.value
        return self.value >= Decimal(str(other))
    
    def __eq__(self, other):
        if isinstance(other, MoneyDecimal):
            return self.value == other.value
        return self.value == Decimal(str(other))
    
    def round_down(self, decimal_places: int = 8):
        """Round down to specified decimal places"""
        multiplier = Decimal(10) ** decimal_places
        return MoneyDecimal(
            (self.value * multiplier).to_integral_value(ROUND_DOWN) / multiplier,
            self.currency
        )
    
    def round_up(self, decimal_places: int = 8):
        """Round up to specified decimal places"""
        multiplier = Decimal(10) ** decimal_places
        return MoneyDecimal(
            (self.value * multiplier).to_integral_value(ROUND_UP) / multiplier,
            self.currency
        )
    
    def to_float(self) -> float:
        """Convert to float (use sparingly, only for display)"""
        return float(self.value)
    
    @classmethod
    def from_api_response(cls, value: Any, currency: str = "USDT"):
        """Create from API response, handling various formats"""
        if value is None:
            return cls("0", currency)
        return cls(str(value), currency)


class PrecisionTradingCalculator:
    """Calculator for precise micro-profit calculations"""
    
    @staticmethod
    def calculate_profit(buy_price: Union[str, float], sell_price: Union[str, float], 
                        quantity: Union[str, float], fee_rate: Union[str, float] = "0") -> Dict[str, Any]:
        """Calculate profit with full precision"""
        buy = MoneyDecimal(buy_price)
        sell = MoneyDecimal(sell_price)
        qty = MoneyDecimal(quantity)
        fee = MoneyDecimal(fee_rate)
        
        # Calculate gross profit
        gross_profit = (sell - buy) * qty
        
        # Calculate fees (if any)
        buy_fee = buy * qty * fee
        sell_fee = sell * qty * fee
        total_fees = buy_fee + sell_fee
        
        # Net profit
        net_profit = gross_profit - total_fees
        
        # Profit percentage
        profit_pct = (net_profit.value / (buy.value * qty.value)) * Decimal("100")
        
        return {
            "gross_profit": gross_profit,
            "total_fees": total_fees,
            "net_profit": net_profit,
            "profit_percentage": MoneyDecimal(profit_pct, "%"),
            "buy_cost": buy * qty,
            "sell_revenue": sell * qty
        }
    
    @staticmethod
    def calculate_position_size(balance: Union[str, float], risk_pct: Union[str, float] = "2",
                               price: Union[str, float] = "1") -> MoneyDecimal:
        """Calculate position size based on balance and risk"""
        bal = MoneyDecimal(balance)
        risk = MoneyDecimal(risk_pct)
        px = MoneyDecimal(price)
        
        # Calculate position value (risk % of balance)
        position_value = bal * (risk / MoneyDecimal("100"))
        
        # Calculate quantity
        quantity = position_value / px
        
        return quantity.round_down(8)  # Round down to 8 decimals for safety


# Helper functions for compatibility
def safe_decimal(value: Any, default: Union[str, float] = "0") -> Decimal:
    """Safely convert any value to Decimal"""
    try:
        if value is None:
            return Decimal(str(default))
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except:
        return Decimal(str(default))

def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert any value to float (use sparingly)"""
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        return float(str(value))
    except:
        return default

def is_zero(value: Any, tolerance: float = 1e-10) -> bool:
    """Check if a value is effectively zero"""
    try:
        if value is None:
            return True
        if isinstance(value, Decimal):
            return abs(value) < Decimal(str(tolerance))
        return abs(float(value)) < tolerance
    except:
        return True

class DecimalHandler:
    """Decimal handler for validation and testing systems"""
    
    @staticmethod
    def normalize_decimal(value: Any) -> Decimal:
        """Normalize any value to a Decimal"""
        return safe_decimal(value)
    
    @staticmethod
    def format_currency(value: Any, currency: str = "USDT") -> str:
        """Format value as currency string"""
        decimal_val = safe_decimal(value)
        return f"{decimal_val:.8f} {currency}"
    
    @staticmethod
    def validate_precision(value: Any, max_precision: int = 8) -> bool:
        """Validate that a value doesn't exceed maximum precision"""
        try:
            decimal_val = safe_decimal(value)
            # Check number of decimal places
            sign, digits, exponent = decimal_val.as_tuple()
            if exponent >= 0:
                return True  # No decimal places
            return abs(exponent) <= max_precision
        except:
            return False
    
    @staticmethod
    def calculate_percentage_change(old_value: Any, new_value: Any) -> Decimal:
        """Calculate percentage change between two values"""
        old_val = safe_decimal(old_value)
        new_val = safe_decimal(new_value)
        
        if old_val == 0:
            return Decimal("0")
        
        change = new_val - old_val
        percentage = (change / old_val) * Decimal("100")
        return percentage


# Export classes and functions
__all__ = ['MoneyDecimal', 'PrecisionTradingCalculator', 'DecimalHandler', 'safe_decimal', 'safe_float', 'is_zero']
