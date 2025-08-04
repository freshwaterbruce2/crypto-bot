"""
Kraken Order Validator
Ensures all orders meet Kraken's precision and minimum requirements
"""

import logging
from typing import Dict, Any, Tuple, Optional
from decimal import Decimal, ROUND_DOWN
from ..config.kraken_precision_config import (
    get_precision_config, format_price, format_volume, validate_order_params
)

logger = logging.getLogger(__name__)

class KrakenOrderValidator:
    """Validates and formats orders according to Kraken requirements"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_and_format_order(
        self, 
        symbol: str, 
        side: str, 
        amount: float, 
        price: Optional[float] = None,
        order_type: str = 'market'
    ) -> Dict[str, Any]:
        """
        Validate and format order parameters for Kraken
        
        Args:
            symbol: Trading pair (e.g., 'SHIB/USDT')
            side: 'buy' or 'sell'
            amount: Order amount in base currency
            price: Order price (for limit orders)
            order_type: 'market' or 'limit'
            
        Returns:
            Dict with validation results and formatted parameters
        """
        try:
            self.logger.debug(f"[KRAKEN_VALIDATOR] Validating {side} order: {amount} {symbol}")
            
            # Get Kraken precision configuration
            config = get_precision_config(symbol)
            
            # Validate minimum volume
            if amount < config['min_volume']:
                return {
                    'valid': False,
                    'error': f"Amount {amount} below minimum {config['min_volume']} for {symbol}",
                    'min_required': config['min_volume'],
                    'provided': amount
                }
            
            # Format volume according to Kraken precision
            formatted_volume = format_volume(amount, symbol)
            
            # For market orders, price validation is optional
            formatted_price = None
            if price is not None:
                # Validate and format price
                valid, error = validate_order_params(symbol, price, amount)
                if not valid:
                    return {
                        'valid': False,
                        'error': error,
                        'symbol': symbol,
                        'price': price,
                        'amount': amount
                    }
                
                formatted_price = format_price(price, symbol)
            
            # Calculate order value for validation
            if price:
                order_value = amount * price
            else:
                # For market orders, we can't calculate exact value without current price
                order_value = None
            
            # Return formatted and validated order
            result = {
                'valid': True,
                'symbol': symbol,
                'side': side,
                'amount': formatted_volume,
                'amount_float': float(formatted_volume),
                'order_type': order_type,
                'precision_config': config,
                'kraken_compliant': True
            }
            
            if formatted_price:
                result['price'] = formatted_price
                result['price_float'] = float(formatted_price)
                result['order_value'] = order_value
            
            self.logger.info(f"[KRAKEN_VALIDATOR] ✅ Valid order: {formatted_volume} {symbol} @ {formatted_price or 'market'}")
            return result
            
        except Exception as e:
            self.logger.error(f"[KRAKEN_VALIDATOR] Validation error: {e}")
            return {
                'valid': False,
                'error': f"Validation failed: {str(e)}",
                'symbol': symbol,
                'side': side,
                'amount': amount
            }
    
    def get_minimum_order_info(self, symbol: str) -> Dict[str, Any]:
        """Get minimum order requirements for a symbol"""
        config = get_precision_config(symbol)
        
        return {
            'symbol': symbol,
            'min_volume': config['min_volume'],
            'price_decimals': config['price_decimals'],
            'base_precision': config['base_precision'],
            'quote_precision': config['quote_precision'],
            'example_min_order': f"{config['min_volume']} {symbol.split('/')[0]}"
        }
    
    def format_for_kraken_api(self, validated_order: Dict[str, Any]) -> Dict[str, Any]:
        """Convert validated order to Kraken API format"""
        if not validated_order.get('valid'):
            raise ValueError(f"Cannot format invalid order: {validated_order.get('error')}")
        
        api_params = {
            'pair': validated_order['symbol'].replace('/', ''),  # SHIBUSD format
            'type': validated_order['side'],
            'ordertype': validated_order['order_type'],
            'volume': validated_order['amount'],
        }
        
        if 'price' in validated_order:
            api_params['price'] = validated_order['price']
        
        return api_params

# Global validator instance
kraken_validator = KrakenOrderValidator()

def validate_kraken_order(symbol: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
    """Quick function to validate a Kraken order"""
    return kraken_validator.validate_and_format_order(symbol, side, amount, price)

def get_kraken_minimums(symbol: str) -> Dict[str, Any]:
    """Quick function to get minimum requirements"""
    return kraken_validator.get_minimum_order_info(symbol)

# Convenience functions for your main trading pairs
def validate_shib_order(side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
    """Validate SHIB/USDT order with proper 160,000 minimum"""
    return validate_kraken_order('SHIB/USDT', side, amount, price)

def validate_ai16z_order(side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
    """Validate AI16Z/USDT order with proper 5 minimum"""
    return validate_kraken_order('AI16Z/USDT', side, amount, price)

def validate_bera_order(side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
    """Validate BERA/USDT order with proper 0.5 minimum"""
    return validate_kraken_order('BERA/USDT', side, amount, price)

# Quick reference
VALIDATION_EXAMPLES = {
    'SHIB/USDT': {
        'min_order': '160000 SHIB',
        'price_example': '0.00001234',  # 8 decimals max
        'valid_order': "validate_shib_order('buy', 200000, 0.00001200)"
    },
    'AI16Z/USDT': {
        'min_order': '5 AI16Z',
        'price_example': '0.1861',  # 4 decimals max  
        'valid_order': "validate_ai16z_order('buy', 10, 0.1850)"
    },
    'BERA/USDT': {
        'min_order': '0.5 BERA',
        'price_example': '1.2345',  # 4 decimals max
        'valid_order': "validate_bera_order('buy', 1.0, 1.2300)"
    }
}