#!/usr/bin/env python3
"""
Fallback Data Manager for Exchange Rate Limits
==============================================

Provides automatic fallback to alternative data sources when the primary
Kraken SDK hits rate limits. Ensures continuous data availability for trading.

Fallback Priority:
1. WebSocket V2 (Real-time, no rate limits)
2. Native REST API (Independent client)
3. CCXT Integration (Multi-exchange)
4. Cached/Historical Data (Emergency)
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class DataSource(Enum):
    """Available data sources"""
    KRAKEN_SDK = "kraken_sdk"
    WEBSOCKET_V2 = "websocket_v2"
    NATIVE_REST = "native_rest"
    CCXT = "ccxt"
    CACHED = "cached"

class FallbackDataManager:
    """Manages fallback data sources during rate limit periods"""

    def __init__(self):
        """Initialize fallback data manager"""
        self.current_source = DataSource.KRAKEN_SDK
        self.fallback_sources = [
            DataSource.WEBSOCKET_V2,
            DataSource.NATIVE_REST,
            DataSource.CCXT,
            DataSource.CACHED
        ]

        # Source availability status
        self.source_status = {
            DataSource.KRAKEN_SDK: True,
            DataSource.WEBSOCKET_V2: True,
            DataSource.NATIVE_REST: True,
            DataSource.CCXT: False,  # Will check on first use
            DataSource.CACHED: True
        }

        # Data caches
        self.data_cache = {
            'balance': {'data': None, 'timestamp': 0, 'ttl': 30},
            'ticker': {'data': {}, 'timestamp': 0, 'ttl': 10},
            'orders': {'data': [], 'timestamp': 0, 'ttl': 5}
        }

        # Initialize sources
        self._websocket_manager = None
        self._native_exchange = None
        self._ccxt_exchange = None

        logger.info("[FALLBACK] Fallback Data Manager initialized")

    async def initialize_sources(self):
        """Initialize all available fallback sources"""
        await self._init_websocket()
        await self._init_native_rest()
        await self._init_ccxt()

    async def _init_websocket(self):
        """Initialize WebSocket V2 manager"""
        try:
            # Skip WebSocket V2 in fallback manager - it's handled elsewhere
            # The proper WebSocket V2 manager is initialized in the main bot
            self.source_status[DataSource.WEBSOCKET_V2] = False
            logger.info("[FALLBACK] WebSocket V2 skipped - handled by main bot")

        except Exception as e:
            logger.error(f"[FALLBACK] WebSocket V2 initialization failed: {e}")
            self.source_status[DataSource.WEBSOCKET_V2] = False

    async def _init_native_rest(self):
        """Initialize native REST API client"""
        try:
            from ..auth.credential_manager import get_kraken_rest_credentials
            from .native_kraken_exchange import NativeKrakenExchange

            # Use unified credential manager that supports both unified and legacy formats
            api_key, api_secret = get_kraken_rest_credentials()

            if api_key and api_secret:
                self._native_exchange = NativeKrakenExchange(api_key, api_secret)
                self.source_status[DataSource.NATIVE_REST] = True
                logger.info("[FALLBACK] Native REST API fallback initialized with unified credentials")
            else:
                self.source_status[DataSource.NATIVE_REST] = False
                logger.warning("[FALLBACK] Native REST credentials missing - check KRAKEN_KEY/KRAKEN_SECRET in .env")

        except Exception as e:
            logger.error(f"[FALLBACK] Native REST initialization failed: {e}")
            self.source_status[DataSource.NATIVE_REST] = False

    async def _init_ccxt(self):
        """Initialize CCXT fallback (if available)"""
        try:
            import ccxt.async_support as ccxt

            from ..auth.credential_manager import get_kraken_rest_credentials

            # Use unified credential manager that supports both unified and legacy formats
            api_key, api_secret = get_kraken_rest_credentials()

            if api_key and api_secret:
                self._ccxt_exchange = ccxt.kraken({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'rateLimit': 1000  # More conservative rate limiting
                })
                self.source_status[DataSource.CCXT] = True
                logger.info("[FALLBACK] CCXT fallback initialized")
            else:
                self.source_status[DataSource.CCXT] = False

        except Exception as e:
            logger.error(f"[FALLBACK] CCXT initialization failed: {e}")
            self.source_status[DataSource.CCXT] = False

    def set_primary_source_status(self, source: DataSource, available: bool):
        """Update source availability status"""
        if source == DataSource.KRAKEN_SDK and not available:
            logger.warning("[FALLBACK] Primary SDK source unavailable, activating fallbacks")
            self._activate_fallback()

        self.source_status[source] = available

        if available and source == DataSource.KRAKEN_SDK and self.current_source != DataSource.KRAKEN_SDK:
            logger.info("[FALLBACK] Primary SDK source recovered, switching back")
            self.current_source = DataSource.KRAKEN_SDK

    def _activate_fallback(self):
        """Activate best available fallback source"""
        for source in self.fallback_sources:
            if self.source_status[source]:
                self.current_source = source
                logger.info(f"[FALLBACK] Switched to fallback source: {source.value}")
                return

        logger.critical("[FALLBACK] No fallback sources available!")
        self.current_source = DataSource.CACHED

    async def fetch_balance(self) -> Optional[Dict[str, Any]]:
        """Fetch balance using best available source"""
        if self.current_source == DataSource.WEBSOCKET_V2 and self._websocket_manager:
            return await self._fetch_balance_websocket()
        elif self.current_source == DataSource.NATIVE_REST and self._native_exchange:
            return await self._fetch_balance_native()
        elif self.current_source == DataSource.CCXT and self._ccxt_exchange:
            return await self._fetch_balance_ccxt()
        else:
            return self._fetch_balance_cached()

    async def _fetch_balance_websocket(self) -> Optional[Dict[str, Any]]:
        """Fetch balance via WebSocket"""
        try:
            # WebSocket balance is updated via callbacks, get latest
            balance = self._websocket_manager.get_cached_balance()
            if balance:
                self._update_cache('balance', balance)
                return balance
        except Exception as e:
            logger.error(f"[FALLBACK] WebSocket balance fetch failed: {e}")
            self._mark_source_failed(DataSource.WEBSOCKET_V2)
        return None

    async def _fetch_balance_native(self) -> Optional[Dict[str, Any]]:
        """Fetch balance via native REST API"""
        try:
            balance = await self._native_exchange.fetch_balance()
            if balance:
                self._update_cache('balance', balance)
                return balance
        except Exception as e:
            logger.error(f"[FALLBACK] Native REST balance fetch failed: {e}")
            self._mark_source_failed(DataSource.NATIVE_REST)
        return None

    async def _fetch_balance_ccxt(self) -> Optional[Dict[str, Any]]:
        """Fetch balance via CCXT"""
        try:
            balance = await self._ccxt_exchange.fetch_balance()
            if balance:
                # Convert CCXT format to our format
                formatted_balance = self._format_ccxt_balance(balance)
                self._update_cache('balance', formatted_balance)
                return formatted_balance
        except Exception as e:
            logger.error(f"[FALLBACK] CCXT balance fetch failed: {e}")
            self._mark_source_failed(DataSource.CCXT)
        return None

    def _fetch_balance_cached(self) -> Optional[Dict[str, Any]]:
        """Return cached balance data"""
        cache = self.data_cache['balance']
        if cache['data'] and (time.time() - cache['timestamp']) < cache['ttl']:
            logger.info("[FALLBACK] Using cached balance data")
            return cache['data']
        return None

    async def fetch_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch ticker using best available source"""
        if self.current_source == DataSource.WEBSOCKET_V2 and self._websocket_manager:
            return await self._fetch_ticker_websocket(symbol)
        elif self.current_source == DataSource.NATIVE_REST and self._native_exchange:
            return await self._fetch_ticker_native(symbol)
        elif self.current_source == DataSource.CCXT and self._ccxt_exchange:
            return await self._fetch_ticker_ccxt(symbol)
        else:
            return self._fetch_ticker_cached(symbol)

    async def _fetch_ticker_websocket(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch ticker via WebSocket"""
        try:
            ticker = self._websocket_manager.get_cached_ticker(symbol)
            if ticker:
                self._update_ticker_cache(symbol, ticker)
                return ticker
        except Exception as e:
            logger.error(f"[FALLBACK] WebSocket ticker fetch failed: {e}")
        return None

    async def _fetch_ticker_native(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch ticker via native REST API"""
        try:
            ticker = await self._native_exchange.fetch_ticker(symbol)
            if ticker:
                self._update_ticker_cache(symbol, ticker)
                return ticker
        except Exception as e:
            logger.error(f"[FALLBACK] Native REST ticker fetch failed: {e}")
        return None

    async def _fetch_ticker_ccxt(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch ticker via CCXT"""
        try:
            ticker = await self._ccxt_exchange.fetch_ticker(symbol)
            if ticker:
                self._update_ticker_cache(symbol, ticker)
                return ticker
        except Exception as e:
            logger.error(f"[FALLBACK] CCXT ticker fetch failed: {e}")
        return None

    def _fetch_ticker_cached(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return cached ticker data"""
        cache = self.data_cache['ticker']
        if symbol in cache['data']:
            ticker_cache = cache['data'][symbol]
            if (time.time() - ticker_cache['timestamp']) < cache['ttl']:
                logger.info(f"[FALLBACK] Using cached ticker for {symbol}")
                return ticker_cache['data']
        return None

    def _update_cache(self, data_type: str, data: Any):
        """Update data cache"""
        self.data_cache[data_type]['data'] = data
        self.data_cache[data_type]['timestamp'] = time.time()

    def _update_ticker_cache(self, symbol: str, ticker: Dict[str, Any]):
        """Update ticker cache"""
        if 'data' not in self.data_cache['ticker']:
            self.data_cache['ticker']['data'] = {}

        self.data_cache['ticker']['data'][symbol] = {
            'data': ticker,
            'timestamp': time.time()
        }

    def _mark_source_failed(self, source: DataSource):
        """Mark a source as temporarily failed and switch to next available"""
        self.source_status[source] = False
        if self.current_source == source:
            self._activate_fallback()

    def _format_ccxt_balance(self, ccxt_balance: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CCXT balance format to our internal format"""
        result = {}
        for currency, balance_info in ccxt_balance.items():
            if currency != 'info' and currency != 'free' and currency != 'used' and currency != 'total':
                result[currency] = {
                    'balance': str(balance_info.get('total', 0)),
                    'available': str(balance_info.get('free', 0))
                }
        return {'result': result}

    def get_current_source(self) -> DataSource:
        """Get currently active data source"""
        return self.current_source

    def get_source_status(self) -> Dict[str, bool]:
        """Get status of all data sources"""
        return {source.value: status for source, status in self.source_status.items()}

# Global instance
_fallback_manager = None

def get_fallback_manager() -> FallbackDataManager:
    """Get singleton fallback manager instance"""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = FallbackDataManager()
    return _fallback_manager

async def initialize_fallback_system():
    """Initialize the fallback system"""
    manager = get_fallback_manager()
    await manager.initialize_sources()
    return manager
