"""
Symbol Format Converter - Kraken 2025 Compliance
=================================================

Handles conversion between REST and WebSocket symbol formats.
Critical for proper API communication across different endpoints.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SymbolConverter:
    """Converts between Kraken REST and WebSocket symbol formats"""
    
    # Known conversions
    CONVERSIONS = {
        'XBT': 'BTC',
        'XDG': 'DOGE',
    }
    
    # Reverse conversions
    REVERSE_CONVERSIONS = {v: k for k, v in CONVERSIONS.items()}
    
    @classmethod
    def to_websocket(cls, symbol: str) -> str:
        """
        Convert REST format to WebSocket format
        
        Examples:
            XBTUSD -> BTC/USD
            SHIBUSDT -> SHIB/USDT
            XXBTZUSD -> BTC/USD
        """
        # Remove leading X or Z for legacy pairs
        if symbol.startswith('X') and len(symbol) > 6:
            symbol = symbol[1:]
        if symbol.startswith('Z') and 'USD' in symbol:
            symbol = symbol[1:]
        
        # Apply known conversions
        for old, new in cls.CONVERSIONS.items():
            symbol = symbol.replace(old, new)
        
        # Add slash for pairs
        if 'USD' in symbol:
            if 'USDT' in symbol:
                symbol = symbol.replace('USDT', '/USDT')
            elif 'USDC' in symbol:
                symbol = symbol.replace('USDC', '/USDC')
            else:
                symbol = symbol.replace('USD', '/USD')
        elif 'EUR' in symbol:
            symbol = symbol.replace('EUR', '/EUR')
        elif 'GBP' in symbol:
            symbol = symbol.replace('GBP', '/GBP')
        elif 'BTC' in symbol and '/' not in symbol:
            # Handle BTC pairs
            symbol = symbol.replace('BTC', '/BTC')
        elif 'ETH' in symbol and '/' not in symbol:
            # Handle ETH pairs
            symbol = symbol.replace('ETH', '/ETH')
        
        return symbol
    
    @classmethod
    def to_rest(cls, symbol: str) -> str:
        """
        Convert WebSocket format to REST format
        
        Examples:
            BTC/USD -> XBTUSD
            SHIB/USDT -> SHIBUSDT
            BTC/EUR -> XBTEUR
        """
        # Remove slash
        symbol = symbol.replace('/', '')
        
        # Apply reverse conversions
        for new, old in cls.REVERSE_CONVERSIONS.items():
            if symbol.startswith(new):
                symbol = symbol.replace(new, old, 1)
        
        # Add X prefix for certain base currencies in legacy format
        if symbol.startswith('BTC') or symbol.startswith('XBT'):
            if 'USD' in symbol and not symbol.startswith('X'):
                symbol = 'X' + symbol
        
        return symbol
    
    @classmethod
    def convert_symbol_format(cls, symbol: str, to_ws: bool = True) -> str:
        """
        Main conversion method
        
        Args:
            symbol: Symbol to convert
            to_ws: True to convert to WebSocket format, False for REST format
            
        Returns:
            Converted symbol
        """
        try:
            if to_ws:
                converted = cls.to_websocket(symbol)
                logger.debug(f"[SYMBOL_CONVERTER] REST->WS: {symbol} -> {converted}")
            else:
                converted = cls.to_rest(symbol)
                logger.debug(f"[SYMBOL_CONVERTER] WS->REST: {symbol} -> {converted}")
            
            return converted
            
        except Exception as e:
            logger.error(f"[SYMBOL_CONVERTER] Error converting {symbol}: {e}")
            return symbol
    
    @classmethod
    def batch_convert(cls, symbols: List[str], to_ws: bool = True) -> List[str]:
        """Convert multiple symbols at once"""
        return [cls.convert_symbol_format(s, to_ws) for s in symbols]
    
    @classmethod
    def get_all_formats(cls, symbol: str) -> Dict[str, str]:
        """Get all possible formats for a symbol"""
        ws_format = cls.to_websocket(symbol)
        rest_format = cls.to_rest(ws_format)
        
        return {
            'websocket': ws_format,
            'rest': rest_format,
            'original': symbol
        }


# Convenience function
def convert_symbol_format(symbol: str, to_ws: bool = True) -> str:
    """Quick conversion function"""
    return SymbolConverter.convert_symbol_format(symbol, to_ws)