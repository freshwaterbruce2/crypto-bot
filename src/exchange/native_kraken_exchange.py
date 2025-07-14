"""
Native Kraken Exchange Implementation
Direct API integration with full compliance
"""

import asyncio
from ..utils.base_exchange_connector import BaseExchangeConnector
from ..utils.unified_balance import get_balance_manager
import hashlib
import hmac
import time
import base64
import urllib.parse
import socket
import logging
import json
import os
from typing import Dict, Optional, Any, List
import aiohttp
from ..utils.network import ResilientRequest
from ..utils.kraken_rl import KrakenRateLimiter
from ..utils.rate_limit_handler import safe_exchange_call
from ..utils.decimal_precision_fix import safe_decimal, safe_float

logger = logging.getLogger(__name__)


class KrakenAPIError(Exception):
    """Custom exception for Kraken API errors"""
    pass


class NativeKrakenExchange:
    """Native Kraken exchange implementation with full compliance"""
    
    def __init__(self, api_key: str, api_secret: str, tier: str = "starter"):
        """Initialize native Kraken exchange"""
        self.api_key = api_key.strip() if api_key else ""
        self.api_secret = api_secret.strip() if api_secret else ""
        self.tier = tier
        
        # Kraken API endpoints
        self.base_url = "https://api.kraken.com"
        self.api_version = "0"
        
        # Session for HTTP requests with connection pooling
        self.session: Optional[aiohttp.ClientSession] = None
        self.connector: Optional[aiohttp.TCPConnector] = None
        
        # Thread-safe nonce generation
        self._nonce_lock = asyncio.Lock()
        self._last_nonce = 0
        
        # Resilient request handler - CRITICAL FIX: Use RequestConfig
        from ..utils.network import RequestConfig
        request_config = RequestConfig(
            max_retries=3,
            timeout=30.0,
            backoff_factor=2.0
        )
        self.resilient_request = ResilientRequest(request_config)
        
        # Health monitoring
        self.last_successful_request = time.time()
        self.consecutive_failures = 0
        self.is_healthy = True
        
        # Markets cache
        self.markets = {}
        self._markets_loaded = False
        
        # Use the sophisticated KrakenRateLimiter
        self.kraken_rate_limiter = KrakenRateLimiter(tier)
        
        # Rate limiting based on tier (keep for legacy compatibility)
        self.rate_limits = {
            'starter': {'counter': 60, 'decay': 1.0},
            'intermediate': {'counter': 125, 'decay': 2.34},
            'pro': {'counter': 180, 'decay': 3.75}
        }
        
        self.rate_counter = 0
        self.last_request_time = time.time()
        
        # DNS failure tracking
        self.dns_failures = 0
        self.dns_last_failure = 0
        self.dns_retry_delay = 30  # Start with 30 seconds
        
        logger.info(f"[KRAKEN] Initialized for {tier} tier")
    
    async def initialize(self) -> bool:
        """Initialize the exchange connection"""
        try:
            success = await self.connect()
            if success:
                # Load markets to ensure we have trading pairs
                await self.load_markets()
                logger.info("[KRAKEN] Exchange initialization complete")
                return True
            else:
                logger.error("[KRAKEN] Exchange initialization failed - connection failed")
                return False
        except Exception as e:
            logger.error(f"[KRAKEN] Exchange initialization error: {e}")
            return False
    
    async def connect(self) -> bool:
        """Establish connection to Kraken with enhanced error handling"""
        try:
            if not self.session:
                # Create connector with connection pooling and DNS cache
                self.connector = aiohttp.TCPConnector(
                    limit=100,  # Total connection pool size
                    limit_per_host=30,  # Per-host connection limit
                    ttl_dns_cache=300,  # DNS cache TTL in seconds
                    enable_cleanup_closed=True,
                    force_close=True,
                    family=socket.AF_INET  # Force IPv4 to avoid IPv6 issues
                )
                
                # Create session with timeout configuration
                timeout = aiohttp.ClientTimeout(
                    total=60,  # Total timeout for the whole operation
                    connect=10,  # Connection timeout
                    sock_connect=10,  # Socket connection timeout
                    sock_read=30  # Socket read timeout
                )
                
                self.session = aiohttp.ClientSession(
                    connector=self.connector,
                    timeout=timeout
                )
            
            # Test connection with resilient request
            result = await self.resilient_request.request(
                self._public_request_raw,
                'SystemStatus',
                {},
                retry_exceptions=(aiohttp.ClientError, asyncio.TimeoutError),
                context="Kraken connection test"
            )
            
            if result.get('status') == 'online':
                logger.info("[KRAKEN] Connected successfully")
                self.is_healthy = True
                self.last_successful_request = time.time()
                self.consecutive_failures = 0
                self.dns_failures = 0  # Reset DNS failures on success
                return True
            else:
                logger.warning(f"[KRAKEN] System status: {result.get('status')}")
                return False
                
        except socket.gaierror as dns_error:
            # Handle DNS resolution errors specifically
            self.dns_failures += 1
            self.dns_last_failure = time.time()
            
            # Exponential backoff for DNS issues
            retry_delay = min(
                self.dns_retry_delay * (2 ** (self.dns_failures - 1)), 300
            )
            
            logger.error(
                f"[KRAKEN] DNS resolution error: {dns_error}. "
                f"Retry in {retry_delay}s"
            )
            await asyncio.sleep(retry_delay)
            return False
        except Exception as e:
            logger.error(f"[KRAKEN] Connection failed: {e}")
            self.consecutive_failures += 1
            self._check_health()
            return False
    
    async def close(self) -> None:
        """Close exchange connection and cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
        
        if self.connector:
            await self.connector.close()
            self.connector = None
        
        logger.info("[KRAKEN] Connection closed and resources cleaned up")
    
    async def load_markets(self) -> Dict[str, Any]:
        """Load all trading pairs from Kraken"""
        if self._markets_loaded:
            return self.markets
        
        try:
            # Fetch asset pairs
            result = await self._public_request('AssetPairs')
            
            self.markets = {}
            
            for pair_name, pair_info in result.items():
                # Parse pair information
                if pair_info.get('status') != 'online':
                    continue
                
                base = pair_info.get('base', '')
                quote = pair_info.get('quote', '')
                
                # Convert Kraken's asset codes
                base = self._normalize_currency(base)
                quote = self._normalize_currency(quote)
                
                symbol = f"{base}/{quote}"
                
                self.markets[symbol] = {
                    'symbol': symbol,
                    'base': base,
                    'quote': quote,
                    'active': True,
                    'info': pair_info,
                    'kraken_name': pair_name,
                    'ordermin': float(pair_info.get('ordermin', 0)),
                    'costmin': float(pair_info.get('costmin', 0)),
                    'tick_size': float(pair_info.get('tick_size', 0)),
                    'lot_decimals': int(pair_info.get('lot_decimals', 8)),
                    'pair_decimals': int(pair_info.get('pair_decimals', 8))
                }
            
            # Create aliases for common symbols
            # This allows using ETH/USDT instead of XETH/USDT
            aliases_to_create = []
            for symbol, market in self.markets.items():
                if symbol.startswith('XETH/'):
                    # Create ETH alias
                    alias_symbol = symbol.replace('XETH/', 'ETH/')
                    aliases_to_create.append((alias_symbol, market))
                elif symbol.startswith('XXRP/'):
                    # Create XRP alias
                    alias_symbol = symbol.replace('XXRP/', 'XRP/')
                    aliases_to_create.append((alias_symbol, market))
                elif symbol.startswith('XBT/'):
                    # BTC alias already handled by _normalize_currency
                    pass
                elif symbol.startswith('XDG/'):
                    # DOGE alias already handled by _normalize_currency
                    pass
            
            # Add aliases
            for alias_symbol, market in aliases_to_create:
                if alias_symbol not in self.markets:
                    self.markets[alias_symbol] = market.copy()
                    self.markets[alias_symbol]['symbol'] = alias_symbol
                    self.markets[alias_symbol]['is_alias'] = True
                    logger.debug(f"[KRAKEN] Created alias: {alias_symbol} -> {market['symbol']}")
            
            self._markets_loaded = True
            logger.info(f"[KRAKEN] Loaded {len(self.markets)} markets (including aliases)")
            return self.markets
            
        except Exception as e:
            logger.error(f"[KRAKEN] Failed to load markets: {e}")
            return {}
    
    def _normalize_currency(self, currency: str) -> str:
        """Normalize Kraken currency codes"""
        mappings = {
            'XBT': 'BTC',
            'XDG': 'DOGE',
            'XXBT': 'BTC',
            'XXDG': 'DOGE',
            'XXRP': 'XRP',
            'ZEUR': 'EUR',
            'ZUSD': 'USD',
            'ZUSDT': 'USDT'
        }
        return mappings.get(currency, currency)
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch current ticker data"""
        try:
            # Ensure markets are loaded
            if not self._markets_loaded:
                logger.info(f"[KRAKEN] Markets not loaded, loading before fetching ticker for {symbol}")
                await self.load_markets()
            
            kraken_pair = self._get_kraken_pair(symbol)
            if not kraken_pair:
                raise KrakenAPIError(f"Unknown symbol: {symbol}")
            
            result = await self._public_request('Ticker', {'pair': kraken_pair})
            
            if kraken_pair in result:
                ticker_data = result[kraken_pair]
                return {
                    'symbol': symbol,
                    'bid': float(ticker_data['b'][0]),
                    'ask': float(ticker_data['a'][0]),
                    'last': float(ticker_data['c'][0]),
                    'volume': float(ticker_data['v'][1]),  # 24h volume
                    'high': float(ticker_data['h'][1]),    # 24h high
                    'low': float(ticker_data['l'][1]),     # 24h low
                    'vwap': float(ticker_data['p'][1]),    # 24h vwap
                    'timestamp': int(time.time() * 1000)
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"[KRAKEN] Error fetching ticker for {symbol}: {e}")
            return {}
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[List]:
        """Fetch OHLC data"""
        try:
            # Ensure markets are loaded
            if not self._markets_loaded:
                logger.info(f"[KRAKEN] Markets not loaded, loading before fetching OHLCV for {symbol}")
                await self.load_markets()
            
            kraken_pair = self._get_kraken_pair(symbol)
            if not kraken_pair:
                raise KrakenAPIError(f"Unknown symbol: {symbol}")
            
            # Convert timeframe to Kraken interval
            intervals = {
                '1m': 1,
                '5m': 5,
                '15m': 15,
                '30m': 30,
                '1h': 60,
                '4h': 240,
                '1d': 1440
            }
            
            interval = intervals.get(timeframe, 1)
            
            params = {
                'pair': kraken_pair,
                'interval': interval
            }
            
            result = await self._public_request('OHLC', params)
            
            if kraken_pair in result:
                ohlc_data = []
                for candle in result[kraken_pair]:
                    if len(candle) >= 6:
                        ohlc_data.append([
                            int(candle[0]) * 1000,  # timestamp (ms)
                            float(candle[1]),       # open
                            float(candle[2]),       # high
                            float(candle[3]),       # low
                            float(candle[4]),       # close
                            float(candle[6])        # volume
                        ])
                
                return ohlc_data[-limit:] if limit else ohlc_data
            
            return []
            
        except Exception as e:
            logger.error(f"[KRAKEN] Error fetching OHLC for {symbol}: {e}")
            return []
    
    async def fetch_balance_ex(self) -> Dict[str, Any]:
        """Fetch account balances using BalanceEx endpoint for accurate available balance"""
        try:
            logger.info("[KRAKEN_BALANCE] Fetching extended balance from Kraken BalanceEx API...")
            result = await self._private_request('BalanceEx')
            
            # Log raw response
            logger.info(f"[KRAKEN_BALANCE] Raw BalanceEx response keys: {list(result.keys())}")
            
            # Create balance structure
            balances = {
                'info': result,  # Keep raw response
                'free': {},
                'used': {},
                'total': {}
            }
            
            # Track USDT aggregation
            usdt_total = 0.0
            usdt_available = 0.0
            usdt_variants_found = []
            
            for asset, info in result.items():
                # BalanceEx returns: {balance, credit, credit_used, hold_trade}
                # Available = balance + credit - credit_used - hold_trade
                balance = float(info.get('balance', 0))
                credit = float(info.get('credit', 0))
                credit_used = float(info.get('credit_used', 0))
                hold_trade = float(info.get('hold_trade', 0))
                
                total = balance + credit
                available = total - credit_used - hold_trade
                used = credit_used + hold_trade
                
                # Store under raw asset name
                balances[asset] = {
                    'free': available,
                    'used': used,
                    'total': total
                }
                
                # Also store normalized version
                currency = self._normalize_currency(asset)
                balances[currency] = {
                    'free': available,
                    'used': used,
                    'total': total
                }
                
                balances['free'][currency] = available
                balances['used'][currency] = used
                balances['total'][currency] = total
                
                # Aggregate USDT variants
                if 'USDT' in asset or currency == 'USDT':
                    usdt_total += total
                    usdt_available += available
                    if available > 0:
                        usdt_variants_found.append(f"{asset}=${available:.2f}")
                    logger.info(f"[KRAKEN_BALANCE] {asset}: total=${total:.2f}, available=${available:.2f}, held=${used:.2f}")
            
            # Ensure USDT is properly aggregated
            if usdt_total > 0:
                balances['USDT'] = {
                    'free': usdt_available,
                    'used': usdt_total - usdt_available,
                    'total': usdt_total
                }
                balances['free']['USDT'] = usdt_available
                balances['used']['USDT'] = usdt_total - usdt_available
                balances['total']['USDT'] = usdt_total
                logger.info(f"[KRAKEN_BALANCE] *** USDT AGGREGATED from [{', '.join(usdt_variants_found)}]: Available=${usdt_available:.2f}, Total=${usdt_total:.2f} ***")
            
            return balances
            
        except Exception as e:
            logger.error(f"[KRAKEN_BALANCE] Error fetching BalanceEx: {e}", exc_info=True)
            # Fallback to standard balance endpoint
            logger.info("[KRAKEN_BALANCE] Falling back to standard Balance endpoint...")
            return await self.fetch_balance()
    
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balances with enhanced USDT detection"""
        try:
            # Try BalanceEx first for more accurate data
            return await self.fetch_balance_ex()
        except Exception as ex:
            # Fallback to standard implementation
            logger.info(f"[KRAKEN_BALANCE] BalanceEx failed ({ex}), using standard Balance endpoint...")
            result = await self._private_request('Balance')
            
            # Log raw response
            logger.info(f"[KRAKEN_BALANCE] Raw balance response keys: {list(result.keys())}")
            
            # Create both normalized and raw balances
            balances = {
                'info': result  # Keep raw response for debugging
            }
            
            # Track USDT specifically
            usdt_found = False
            usdt_amount = 0.0
            
            for asset, amount in result.items():
                amount_float = float(amount)
                
                # Keep raw asset code
                balances[asset] = amount_float
                
                # Also store normalized version
                currency = self._normalize_currency(asset)
                balances[currency] = amount_float
                
                # Log significant balances
                if amount_float > 0.01:
                    logger.info(f"[KRAKEN_BALANCE] {asset} ({currency}): {amount_float}")
                
                # Check for USDT in various forms
                if asset in ['USDT', 'ZUSDT', 'USDT.M', 'USDT.HOLD', 'USDT.S']:
                    usdt_found = True
                    usdt_amount = amount_float
                    logger.info(f"[KRAKEN_BALANCE] *** FOUND USDT as {asset}: ${amount_float:.2f} ***")
                elif currency == 'USDT':
                    usdt_found = True
                    usdt_amount = amount_float
                    logger.info(f"[KRAKEN_BALANCE] *** FOUND USDT via normalization from {asset}: ${amount_float:.2f} ***")
            
            # Add standardized entries for compatibility
            balances['free'] = {}
            balances['used'] = {}
            balances['total'] = {}
            
            for currency, amount in balances.items():
                if currency not in ['info', 'free', 'used', 'total'] and isinstance(amount, (int, float)):
                    balances['free'][currency] = amount
                    balances['used'][currency] = 0.0
                    balances['total'][currency] = amount
            
            if not usdt_found:
                logger.warning("[KRAKEN_BALANCE] *** NO USDT FOUND IN BALANCE! ***")
                logger.warning(f"[KRAKEN_BALANCE] Available assets: {[k for k, v in result.items() if float(v) > 0]}")
            else:
                logger.info(f"[KRAKEN_BALANCE] Total USDT balance: ${usdt_amount:.2f}")
            
            return balances
            
        except Exception as e:
            logger.error(f"[KRAKEN_BALANCE] Error fetching balance: {e}", exc_info=True)
            return {}
    
    async def create_order(self, symbol: str, side: str, amount: float, 
                          order_type: str = 'market', price: Optional[float] = None) -> Dict[str, Any]:
        """Create a new order with full Kraken compliance"""
        try:
            # Ensure markets are loaded
            if not self._markets_loaded:
                logger.info(f"[KRAKEN] Markets not loaded, loading before creating order for {symbol}")
                await self.load_markets()
            
            kraken_pair = self._get_kraken_pair(symbol)
            if not kraken_pair:
                raise KrakenAPIError(f"Unknown symbol: {symbol}")
            
            # Get market info for validation
            market = self.markets.get(symbol, {})
            
            # Validate minimum order value ($2 USDT for tier 1 pairs)
            if market.get('quote') == 'USDT':
                if order_type == 'limit' and price:
                    order_value = amount * price
                else:
                    # For market orders, estimate with current price
                    ticker = await self.fetch_ticker(symbol)
                    current_price = ticker.get('last', 0)
                    order_value = amount * current_price
                
                if order_value < 2.0:
                    raise KrakenAPIError(f"Order value ${order_value:.2f} below $2 minimum")
            
            # Prepare order parameters
            params = {
                'pair': kraken_pair,
                'type': side.lower(),
                'ordertype': order_type,
                'volume': str(amount)
            }
            
            if order_type == 'limit' and price:
                params['price'] = str(price)
            
            # Check rate limit
            if not self._check_rate_limit():
                raise KrakenAPIError("Rate limit exceeded")
            
            # Place order
            result = await self._private_request('AddOrder', params)
            
            if 'txid' in result:
                order_id = result['txid'][0] if result['txid'] else None
                return {
                    'id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'type': order_type,
                    'status': 'open',
                    'timestamp': int(time.time() * 1000)
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"[KRAKEN] Error creating order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            result = await self._private_request('CancelOrder', {'txid': order_id})
            return 'count' in result and result['count'] > 0
            
        except Exception as e:
            logger.error(f"[KRAKEN] Error canceling order {order_id}: {e}")
            return False
    
    async def fetch_order(self, order_id: str) -> Dict[str, Any]:
        """Fetch order details"""
        try:
            result = await self._private_request('QueryOrders', {'txid': order_id})
            
            if order_id in result:
                order_info = result[order_id]
                return {
                    'id': order_id,
                    'status': order_info.get('status'),
                    'symbol': self._parse_kraken_pair(order_info.get('descr', {}).get('pair', '')),
                    'side': order_info.get('descr', {}).get('type'),
                    'amount': float(order_info.get('vol', 0)),
                    'filled': float(order_info.get('vol_exec', 0)),
                    'remaining': safe_float(safe_decimal(order_info.get('vol', 0)) - safe_decimal(order_info.get('vol_exec', 0))),
                    'price': float(order_info.get('price', 0)),
                    'cost': float(order_info.get('cost', 0)),
                    'fee': float(order_info.get('fee', 0))
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"[KRAKEN] Error fetching order {order_id}: {e}")
            return {}
    
    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all open orders"""
        try:
            result = await self._private_request('OpenOrders')
            
            orders = []
            open_orders = result.get('open', {})
            
            for order_id, order_info in open_orders.items():
                parsed_order = {
                    'id': order_id,
                    'timestamp': int(order_info.get('opentm', 0) * 1000),
                    'status': 'open',
                    'symbol': self._parse_kraken_pair(order_info.get('descr', {}).get('pair', '')),
                    'side': order_info.get('descr', {}).get('type', 'buy'),
                    'amount': float(order_info.get('vol', 0)),
                    'filled': float(order_info.get('vol_exec', 0)),
                    'remaining': safe_float(safe_decimal(order_info.get('vol', 0)) - safe_decimal(order_info.get('vol_exec', 0))),
                    'price': float(order_info.get('descr', {}).get('price', 0)),
                    'cost': float(order_info.get('cost', 0)),
                    'fee': float(order_info.get('fee', 0))
                }
                
                # Filter by symbol if specified
                if symbol is None or parsed_order['symbol'] == symbol:
                    orders.append(parsed_order)
            
            return orders
            
        except Exception as e:
            logger.error(f"[KRAKEN] Error fetching open orders: {e}")
            return []
    
    async def get_websocket_token(self) -> str:
        """Get WebSocket authentication token (legacy method)"""
        try:
            result = await self._private_request('GetWebSocketsToken')
            return result.get('token', '')
        except Exception as e:
            logger.error(f"[KRAKEN] Error getting WebSocket token: {e}")
            return ''
    
    async def get_websockets_token(self) -> Dict[str, Any]:
        """
        Get WebSocket authentication token in the format expected by auth manager.
        
        Returns:
            Dict with 'result' containing 'token' or error information
        """
        try:
            response = await self._private_request('GetWebSocketsToken')
            if 'token' in response:
                return {
                    'result': {'token': response['token']},
                    'error': []
                }
            else:
                return {
                    'result': {},
                    'error': ['No token in response']
                }
        except Exception as e:
            logger.error(f"[KRAKEN] Error getting WebSocket token: {e}")
            return {
                'result': {},
                'error': [str(e)]
            }
    
    def _get_kraken_pair(self, symbol: str) -> Optional[str]:
        """Convert symbol to Kraken pair name"""
        if not self.markets:
            logger.warning(f"[KRAKEN] Markets not loaded yet when looking up {symbol}")
            return None
        
        market = self.markets.get(symbol)
        if market:
            return market.get('kraken_name')
        
        logger.warning(f"[KRAKEN] Symbol {symbol} not found in markets. Available: {list(self.markets.keys())[:10]}...")
        return None
    
    def _parse_kraken_pair(self, kraken_pair: str) -> str:
        """Convert Kraken pair to standard symbol"""
        for symbol, market in self.markets.items():
            if market.get('kraken_name') == kraken_pair:
                return symbol
        return kraken_pair
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = time.time()
        
        # Check if we're in rate limit recovery period
        if hasattr(self, '_rate_limit_recovery_time') and now < self._rate_limit_recovery_time:
            remaining = self._rate_limit_recovery_time - now
            logger.debug(f"[KRAKEN] Still in rate limit recovery, {remaining:.1f}s remaining")
            return False
        
        elapsed = now - self.last_request_time
        
        # Apply decay
        decay_rate = self.rate_limits[self.tier]['decay']
        self.rate_counter = max(0, self.rate_counter - (decay_rate * elapsed))
        
        # Check if under limit
        max_counter = self.rate_limits[self.tier]['counter']
        if self.rate_counter >= max_counter:
            return False
        
        # Increment counter
        self.rate_counter += 1
        self.last_request_time = now
        
        # Reset backoff time on successful check
        if hasattr(self, '_rate_limit_backoff_time'):
            self._rate_limit_backoff_time = 60.0  # Reset to initial backoff
        
        return True
    
    async def _public_request_raw(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Raw public API request without retry logic (for use with ResilientRequest)"""
        if not self.session:
            raise KrakenAPIError("Not connected")
        
        url = f"{self.base_url}/{self.api_version}/public/{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('error'):
                    error_msg = data['error'][0] if data['error'] else "Unknown error"
                    
                    # Check for rate limit error
                    if 'Rate limit exceeded' in error_msg:
                        logger.warning(
                            f"[KRAKEN] Public API rate limit exceeded: {error_msg}"
                        )
                        # Add small delay before raising to prevent immediate retry
                        await asyncio.sleep(0.1)
                        
                    raise KrakenAPIError(error_msg)
                
                # Update health metrics on success
                self.last_successful_request = time.time()
                self.consecutive_failures = 0
                self.is_healthy = True
                
                return data.get('result', {})
        except aiohttp.ClientConnectorError as conn_error:
            if "DNS lookup failed" in str(conn_error):
                self.dns_failures += 1
                logger.error(f"[KRAKEN] DNS lookup failed: {conn_error}")
                # Let the resilient request handle the retry
            raise
    
    async def _public_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make public API request with retry and error handling"""
        try:
            return await self.resilient_request.request(
                self._public_request_raw,
                endpoint,
                params or {},
                retry_exceptions=(aiohttp.ClientError, asyncio.TimeoutError, KrakenAPIError),
                context=f"Kraken public request: {endpoint}"
            )
        except Exception as e:
            self.consecutive_failures += 1
            self._check_health()
            logger.error(f"[KRAKEN] Public request error after retries: {e}")
            raise
    
    async def _private_request_raw(self, endpoint: str, params: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Raw private API request without retry logic (for use with ResilientRequest)"""
        if not self.session:
            raise KrakenAPIError("Not connected")
        
        url = f"{self.base_url}/{self.api_version}/private/{endpoint}"
        
        try:
            async with self.session.post(url, data=params, headers=headers) as response:
                result = await response.json()
                
                if result.get('error'):
                    error_msg = result['error'][0] if result['error'] else "Unknown error"
                    
                    # Check for nonce error
                    if 'EAPI:Invalid nonce' in error_msg:
                        logger.warning(f"[KRAKEN_AUTH] Invalid nonce error: {error_msg}")
                        # For nonce errors, we need to wait and let the caller regenerate a new nonce
                        await asyncio.sleep(0.1)  # Short delay to avoid rapid retries
                    
                    # Check for rate limit error
                    elif 'EAPI:Rate limit exceeded' in error_msg:
                        # Update both rate limiters
                        self.rate_counter = self.rate_limits[self.tier]['counter']  # Max out counter
                        self.kraken_rate_limiter.handle_kraken_error(error_msg, endpoint)
                        
                        logger.warning(f"[KRAKEN] Rate limit exceeded: {error_msg}")
                        # Implement exponential backoff for rate limit recovery
                        if not hasattr(self, '_rate_limit_backoff_time'):
                            self._rate_limit_backoff_time = 60.0  # Start with 60 seconds
                        else:
                            self._rate_limit_backoff_time = min(self._rate_limit_backoff_time * 1.5, 300.0)  # Max 5 minutes
                        
                        logger.warning(f"[KRAKEN] Entering rate limit backoff for {self._rate_limit_backoff_time:.1f} seconds")
                        self._rate_limit_recovery_time = time.time() + self._rate_limit_backoff_time
                        await asyncio.sleep(0.1)
                    
                    raise KrakenAPIError(error_msg)
                
                # Update health metrics on success
                self.last_successful_request = time.time()
                self.consecutive_failures = 0
                self.is_healthy = True
                
                return result.get('result', {})
        except aiohttp.ClientConnectorError as conn_error:
            if "DNS lookup failed" in str(conn_error):
                self.dns_failures += 1
                logger.error(f"[KRAKEN] DNS lookup failed: {conn_error}")
                # Let the resilient request handle the retry
            raise
    
    # Removed complex nonce persistence - using simple millisecond timestamps instead
    
    async def _private_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated private API request with retry and error handling"""
        if not self.api_key or not self.api_secret:
            raise KrakenAPIError("API credentials not set")
        
        # Use KrakenRateLimiter for sophisticated rate limiting
        operation = self._get_operation_type(endpoint)
        await self.kraken_rate_limiter.wait_if_needed(
            symbol='global',  # Use 'global' for non-pair-specific endpoints
            operation=operation,
            endpoint=endpoint
        )
        
        # Legacy rate limit check as backup
        if not self._check_rate_limit():
            # Instead of failing immediately, wait a bit and try again
            wait_time = 1.0
            logger.warning(
                f"[KRAKEN] Legacy rate limit would be exceeded, waiting {wait_time}s"
            )
            await asyncio.sleep(wait_time)
            
            # Check again after waiting
            if not self._check_rate_limit():
                raise KrakenAPIError("Rate limit would be exceeded")
        
        # Thread-safe nonce generation - Kraken best practice: milliseconds
        async with self._nonce_lock:
            # Ensure nonce always increases
            current_time_ms = int(time.time() * 1000)
            
            # If we're making requests too fast, increment from last nonce
            if current_time_ms <= self._last_nonce:
                self._last_nonce += 1
                nonce = str(self._last_nonce)
            else:
                self._last_nonce = current_time_ms
                nonce = str(current_time_ms)
            
            logger.debug(f"[KRAKEN_AUTH] Generated nonce: {nonce} for endpoint: {endpoint}")
            
            # Small delay to prevent rapid-fire requests
            await asyncio.sleep(0.05)  # 50ms minimum between requests
        
        if params is None:
            params = {}
        
        # CRITICAL: Nonce must be FIRST parameter for Kraken API
        ordered_params = {'nonce': nonce}
        ordered_params.update(params)
        
        # Create signature
        urlpath = f"/{self.api_version}/private/{endpoint}"
        data = urllib.parse.urlencode(ordered_params)
        
        # Create signature
        message = urlpath.encode() + hashlib.sha256((nonce + data).encode()).digest()
        signature = base64.b64encode(
            hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512).digest()
        ).decode()
        
        # Headers
        headers = {
            'API-Key': self.api_key,
            'API-Sign': signature
        }
        
        try:
            return await self.resilient_request.request(
                self._private_request_raw,
                endpoint,
                ordered_params,
                headers,
                retry_exceptions=(aiohttp.ClientError, asyncio.TimeoutError, KrakenAPIError),
                context=f"Kraken private request: {endpoint}"
            )
        except KrakenAPIError as e:
            # Handle specific Kraken errors with appropriate retry logic
            if 'Invalid nonce' in str(e):
                # Nonce errors can be retried with a delay
                logger.warning(f"[KRAKEN] Nonce error encountered, will be retried by resilient request: {e}")
                raise  # Let the resilient request handler retry
            elif 'Rate limit exceeded' in str(e):
                # Rate limit errors need longer delays
                await asyncio.sleep(1.0)
                raise  # Let the resilient request handler retry
            elif 'Insufficient funds' in str(e) or 'Order minimum not met' in str(e):
                # Don't retry these business logic errors
                raise
            else:
                # For other errors, let the resilient request handler decide
                raise
        except Exception as e:
            self.consecutive_failures += 1
            self._check_health()
            logger.error(f"[KRAKEN] Private request error after retries: {e}")
            raise
    
    def _check_health(self) -> None:
        """Check exchange health based on consecutive failures"""
        if self.consecutive_failures >= 5:
            self.is_healthy = False
            logger.error(f"[KRAKEN] Exchange unhealthy after {self.consecutive_failures} consecutive failures")
        elif self.consecutive_failures >= 3:
            logger.warning(f"[KRAKEN] Exchange degraded with {self.consecutive_failures} consecutive failures")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status of the exchange connection"""
        time_since_success = time.time() - self.last_successful_request
        
        return {
            "healthy": self.is_healthy,
            "consecutive_failures": self.consecutive_failures,
            "time_since_last_success": time_since_success,
            "rate_limit_usage": self.rate_counter / self.rate_limits[self.tier]['counter'],
            "connection_pool_stats": self.connector.stats if self.connector else None,
            "resilient_request_metrics": self.resilient_request.get_performance_metrics()
        }
    
    async def health_check(self) -> bool:
        """Perform active health check"""
        try:
            # Try a lightweight public request
            await self.fetch_ticker("BTC/USDT")
            return True
        except Exception as e:
            logger.error(f"[KRAKEN] Health check failed: {e}")
            return False
    
    def _get_operation_type(self, endpoint: str) -> str:
        """Map API endpoint to operation type for rate limiting"""
        endpoint_lower = endpoint.lower()
        if 'balance' in endpoint_lower:
            return 'balance'
        elif 'addorder' in endpoint_lower:
            return 'add_order'
        elif 'cancelorder' in endpoint_lower:
            return 'cancel_order'
        elif 'editorder' in endpoint_lower:
            return 'edit_order'
        elif 'ticker' in endpoint_lower:
            return 'ticker'
        elif 'position' in endpoint_lower:
            return 'positions'
        else:
            return 'system'
    
    async def create_market_sell_order(self, symbol: str, amount: float) -> Dict[str, Any]:
        """
        Create a market sell order for liquidating assets.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            amount: Amount to sell in base currency
            
        Returns:
            Order result dictionary
        """
        try:
            logger.info(f"[KRAKEN] Creating market sell order: {amount} {symbol}")
            
            # Use the existing create_order method with market type and sell side
            result = await self.create_order(
                symbol=symbol,
                side='sell',
                amount=amount,
                order_type='market'
            )
            
            logger.info(f"[KRAKEN] Market sell order created: {result.get('id', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"[KRAKEN] Failed to create market sell order for {symbol}: {e}")
            raise KrakenAPIError(f"Market sell order failed: {e}")