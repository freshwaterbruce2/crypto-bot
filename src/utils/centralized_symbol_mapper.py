"""
Kraken Symbol Mapper Implementation
==================================

This module provides the centralized symbol mapping functionality
that's referenced throughout the codebase but was never implemented.

Based on Kraken API documentation:
- WebSocket v2: Uses standard format like "BTC/USD", "BTC/USDT"
- REST API: Uses various formats including "XBTUSD", "XBTUSDT", etc.
- CCXT: Handles some conversions but not all

The mapper ensures consistent symbol handling across all components.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class KrakenSymbolMapper:
    """
    Centralized symbol mapper for Kraken exchange.

    This class handles the conversion between different symbol formats:
    - WebSocket v2 format: "BTC/USD", "BTC/USDT" (with forward slash)
    - REST API format: "XBTUSD", "XBTUSDT" (no slash, uses XBT for BTC)
    - CCXT format: May vary depending on the market

    The mapper auto-learns from the exchange's market data.
    """

    def __init__(self):
        """Initialize the symbol mapper."""
        self.ws_to_rest: dict[str, str] = {}
        self.rest_to_ws: dict[str, str] = {}
        self.ccxt_to_ws: dict[str, str] = {}
        self.ws_to_ccxt: dict[str, str] = {}

        # Cache for discovered mappings
        self.cache_file = Path("D:/trading_data/symbol_mappings.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Load cached mappings
        self._load_cache()

        # Initialize with known mappings
        self._init_known_mappings()

        self.is_initialized = True
        logger.info("[SYMBOL_MAPPER] Initialized with cached and known mappings")

    def _init_known_mappings(self):
        """Initialize with known Kraken symbol mappings."""
        # Known WebSocket to REST mappings for common pairs
        known_mappings = {
            # USDT pairs (our focus)
            "BTC/USDT": ["XBTUSDT", "BTC/USDT", "BTCUSDT"],
            "ETH/USDT": ["ETHUSDT", "ETH/USDT"],
            "SOL/USDT": ["SOLUSDT", "SOL/USDT"],
            "ADA/USDT": ["ADAUSDT", "ADA/USDT"],
            "SHIB/USDT": ["SHIBUSDT", "SHIB/USDT"],
            "DOGE/USDT": ["DOGEUSDT", "DOGE/USDT", "XDGUSDT"],
            "AVAX/USDT": ["AVAXUSDT", "AVAX/USDT"],
            "DOT/USDT": ["DOTUSDT", "DOT/USDT"],
            "MATIC/USDT": ["MATICUSDT", "MATIC/USDT"],
            "XRP/USDT": ["XRPUSDT", "XRP/USDT"],
            "LTC/USDT": ["LTCUSDT", "LTC/USDT"],
            "BCH/USDT": ["BCHUSDT", "BCH/USDT"],

            # USD pairs commented out - USDT ONLY trading
            # "BTC/USD": ["XBTUSD", "XXBTZUSD"],  # NOT USED - USDT ONLY
            # "ETH/USD": ["ETHUSD", "XETHZUSD"],   # NOT USED - USDT ONLY
            # "SOL/USD": ["SOLUSD"],               # NOT USED - USDT ONLY
            # "ADA/USD": ["ADAUSD"],               # NOT USED - USDT ONLY
            # "DOGE/USD": ["DOGEUSD", "XDGUSD"],   # NOT USED - USDT ONLY
        }

        # Populate mappings
        for ws_symbol, rest_variants in known_mappings.items():
            # Use the first variant as primary
            if rest_variants:
                primary_rest = rest_variants[0]
                self.ws_to_rest[ws_symbol] = primary_rest
                self.rest_to_ws[primary_rest] = ws_symbol

                # Map all variants
                for variant in rest_variants:
                    self.rest_to_ws[variant] = ws_symbol

    def _load_cache(self):
        """Load cached symbol mappings from disk."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file) as f:
                    data = json.load(f)
                    self.ws_to_rest.update(data.get('ws_to_rest', {}))
                    self.rest_to_ws.update(data.get('rest_to_ws', {}))
                    self.ccxt_to_ws.update(data.get('ccxt_to_ws', {}))
                    self.ws_to_ccxt.update(data.get('ws_to_ccxt', {}))
                logger.info(f"[SYMBOL_MAPPER] Loaded {len(self.ws_to_rest)} mappings from cache")
        except Exception as e:
            logger.warning(f"[SYMBOL_MAPPER] Could not load cache: {e}")

    def _save_cache(self):
        """Save symbol mappings to disk."""
        try:
            data = {
                'ws_to_rest': self.ws_to_rest,
                'rest_to_ws': self.rest_to_ws,
                'ccxt_to_ws': self.ccxt_to_ws,
                'ws_to_ccxt': self.ws_to_ccxt
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"[SYMBOL_MAPPER] Could not save cache: {e}")

    async def learn_from_markets(self, markets: dict[str, dict]):
        """
        Learn symbol mappings from exchange market data.

        Args:
            markets: Market data from exchange.load_markets()
        """
        try:
            learned_count = 0

            for ccxt_symbol, market_info in markets.items():
                # Skip non-spot markets
                if market_info.get('type') != 'spot':
                    continue

                # Get WebSocket name if available
                ws_name = market_info.get('info', {}).get('wsname')
                if ws_name:
                    # Store CCXT to WebSocket mapping
                    self.ccxt_to_ws[ccxt_symbol] = ws_name
                    self.ws_to_ccxt[ws_name] = ccxt_symbol

                    # Also store as WebSocket to REST
                    rest_id = market_info.get('id', ccxt_symbol)
                    self.ws_to_rest[ws_name] = rest_id
                    self.rest_to_ws[rest_id] = ws_name

                    learned_count += 1

                # Also handle standard format
                if '/' in ccxt_symbol and ccxt_symbol.endswith('USDT'):
                    # For USDT pairs, ensure we have mappings
                    if ccxt_symbol not in self.ws_to_rest:
                        # Generate REST format (remove slash)
                        rest_format = ccxt_symbol.replace('/', '')

                        # Handle special cases
                        if ccxt_symbol.startswith('BTC/'):
                            rest_format = rest_format.replace('BTC', 'XBT')
                        elif ccxt_symbol.startswith('DOGE/'):
                            # Kraken might use XDG for DOGE
                            alt_format = rest_format.replace('DOGE', 'XDG')
                            self.rest_to_ws[alt_format] = ccxt_symbol

                        self.ws_to_rest[ccxt_symbol] = rest_format
                        self.rest_to_ws[rest_format] = ccxt_symbol
                        learned_count += 1

            if learned_count > 0:
                logger.info(f"[SYMBOL_MAPPER] Learned {learned_count} new mappings from markets")
                self._save_cache()

        except Exception as e:
            logger.error(f"[SYMBOL_MAPPER] Error learning from markets: {e}")

    def websocket_to_rest(self, ws_symbol: str) -> str:
        """
        Convert WebSocket v2 symbol to REST API format.

        Args:
            ws_symbol: Symbol in WebSocket format (e.g., 'BTC/USDT')

        Returns:
            REST API compatible symbol
        """
        # Check direct mapping
        if ws_symbol in self.ws_to_rest:
            return self.ws_to_rest[ws_symbol]

        # Handle USDT pairs
        if ws_symbol.endswith('/USDT'):
            base, quote = ws_symbol.split('/')

            # Apply Kraken-specific transformations
            if base == 'BTC':
                return f"XBT{quote}"
            elif base == 'DOGE':
                # Try both DOGE and XDG
                return f"DOGE{quote}"  # CCXT usually handles this
            else:
                return f"{base}{quote}"

        # Default: remove slash
        return ws_symbol.replace('/', '')

    def rest_to_websocket(self, rest_symbol: str) -> str:
        """
        Convert REST API symbol to WebSocket v2 format.

        Args:
            rest_symbol: Symbol in REST format (e.g., 'XBTUSDT')

        Returns:
            WebSocket v2 compatible symbol
        """
        # Check direct mapping
        if rest_symbol in self.rest_to_ws:
            return self.rest_to_ws[rest_symbol]

        # Apply transformations
        symbol = rest_symbol

        # Handle XBT -> BTC
        if symbol.startswith('XBT'):
            symbol = symbol.replace('XBT', 'BTC')

        # Handle XDG -> DOGE
        if symbol.startswith('XDG'):
            symbol = symbol.replace('XDG', 'DOGE')

        # Add slash before USDT
        if 'USDT' in symbol and '/' not in symbol:
            symbol = symbol.replace('USDT', '/USDT')

        # USD pairs are not supported - USDT ONLY
        elif 'USD' in symbol and '/' not in symbol and not symbol.endswith('USDT'):
            logger.warning(f"[SYMBOL_MAPPER] USD pair detected: {symbol} - Only USDT pairs are supported")
            return None  # Reject USD pairs

        return symbol

    def websocket_to_ccxt(self, ws_symbol: str) -> str:
        """
        Convert WebSocket symbol to CCXT format.

        Args:
            ws_symbol: Symbol in WebSocket format

        Returns:
            CCXT compatible symbol
        """
        # Check direct mapping
        if ws_symbol in self.ws_to_ccxt:
            return self.ws_to_ccxt[ws_symbol]

        # For most cases, WebSocket and CCXT use the same format
        return ws_symbol

    def ccxt_to_websocket(self, ccxt_symbol: str) -> str:
        """
        Convert CCXT symbol to WebSocket format.

        Args:
            ccxt_symbol: Symbol in CCXT format

        Returns:
            WebSocket compatible symbol
        """
        # Check direct mapping
        if ccxt_symbol in self.ccxt_to_ws:
            return self.ccxt_to_ws[ccxt_symbol]

        # For most cases, they use the same format
        return ccxt_symbol

    def map_websocket_v2_to_rest(self, ws_symbol: str) -> Optional[str]:
        """
        Convert WebSocket v2 symbol to REST API format.
        This is the MISSING METHOD that was causing errors.

        Args:
            ws_symbol: Symbol in WebSocket v2 format (e.g., 'BTC/USDT')

        Returns:
            REST API compatible symbol or None if not found
        """
        return self.websocket_to_rest(ws_symbol)

    def get_all_formats(self, symbol: str) -> dict[str, str]:
        """
        Get all known formats for a symbol.

        Args:
            symbol: Symbol in any format

        Returns:
            Dict with all known formats
        """
        # Normalize to WebSocket format first
        ws_symbol = None

        # Check if it's already a WebSocket symbol
        if '/' in symbol:
            ws_symbol = symbol
        # Check REST to WS mapping
        elif symbol in self.rest_to_ws:
            ws_symbol = self.rest_to_ws[symbol]
        # Check CCXT to WS mapping
        elif symbol in self.ccxt_to_ws:
            ws_symbol = self.ccxt_to_ws[symbol]
        # Try to convert
        else:
            ws_symbol = self.rest_to_websocket(symbol)

        return {
            'websocket': ws_symbol,
            'rest': self.websocket_to_rest(ws_symbol),
            'ccxt': self.websocket_to_ccxt(ws_symbol)
        }

    def is_usdt_pair(self, symbol: str) -> bool:
        """Check if a symbol is a USDT pair."""
        # Normalize to WebSocket format
        ws_symbol = self.rest_to_websocket(symbol) if '/' not in symbol else symbol

        # Handle None return from rest_to_websocket (rejected USD pairs)
        if not ws_symbol:
            return False

        return ws_symbol.endswith('/USDT')

    def filter_usdt_pairs(self, symbols: list[str]) -> list[str]:
        """Filter a list of symbols to only include USDT pairs."""
        usdt_pairs = []
        for symbol in symbols:
            if self.is_usdt_pair(symbol):
                # Normalize to WebSocket format
                ws_symbol = self.rest_to_websocket(symbol) if '/' not in symbol else symbol
                if ws_symbol:  # Check if conversion was successful
                    usdt_pairs.append(ws_symbol)
        return usdt_pairs

    def validate_usdt_only(self, symbol: str) -> bool:
        """
        Validate that a symbol is a USDT pair only.
        Rejects USD, EUR, and other non-USDT pairs.

        Args:
            symbol: Symbol in any format

        Returns:
            True if valid USDT pair, False otherwise
        """
        # Normalize to WebSocket format
        ws_symbol = self.rest_to_websocket(symbol) if '/' not in symbol else symbol

        if not ws_symbol:
            return False

        # Must end with /USDT
        if not ws_symbol.endswith('/USDT'):
            logger.warning(f"[SYMBOL_MAPPER] Non-USDT pair rejected: {symbol}")
            return False

        return True


# Global instance
symbol_mapper = KrakenSymbolMapper()

# For backward compatibility
centralized_mapper = symbol_mapper
