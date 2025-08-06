"""
Native Kraken Exchange Implementation
Direct API integration with full compliance
"""

import asyncio
import base64
import hashlib
import hmac
import logging
import socket
import time
import urllib.parse
from typing import Any, Optional

import aiohttp

from ..utils.consolidated_nonce_manager import ConsolidatedNonceManager
from ..utils.decimal_precision_fix import safe_decimal, safe_float
from ..utils.kraken_rl import KrakenRateLimiter
from ..utils.network import ResilientRequest

# from ..utils.comprehensive_api_protection import get_comprehensive_protection  # Module missing

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

        # Thread-safe nonce generation with persistence
        self._nonce_lock = asyncio.Lock()
        # Use consolidated nonce manager (singleton)
        self.nonce_manager = ConsolidatedNonceManager.get_instance()
        logger.info(f"[KRAKEN] Initialized with unified nonce manager: {self.nonce_manager.__class__.__name__}")

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

        # Add max_api_counter for compatibility
        self.max_api_counter = 20 if tier == "pro" else 15

        # Markets cache
        self.markets = {}
        self._markets_loaded = False

        # CRITICAL FIX 2025: Enhanced rate limiting based on latest Kraken specs
        self.kraken_rate_limiter = KrakenRateLimiter(tier)

        # ENHANCED 2025: Comprehensive API protection system
        # self.comprehensive_protection = get_comprehensive_protection(api_key, api_secret, tier)  # Module missing
        self.comprehensive_protection = self._create_simple_protection()  # Simple fallback

        # 2025 Kraken API Rate Limits by Tier:
        # Starter: Max Counter 15, Decay -0.33/sec
        # Intermediate: Max Counter 20, Decay -0.5/sec
        # Pro: Max Counter 20, Decay -1/sec
        tier_configs = {
            'starter': {'max_counter': 15, 'decay_rate': 0.33},
            'intermediate': {'max_counter': 20, 'decay_rate': 0.5},
            'pro': {'max_counter': 20, 'decay_rate': 1.0}
        }

        self.rate_config = tier_configs.get(tier.lower(), tier_configs['starter'])
        self.api_counter = 0
        self.last_counter_update = time.time()

        # Minimum delay between API calls (enhanced for 2025)
        self.min_api_delay = 0.1  # 100ms minimum
        self.last_api_call_time = 0

        logger.info(f"[KRAKEN_2025] Rate limiting configured for {tier} tier: max_counter={self.rate_config['max_counter']}, decay={self.rate_config['decay_rate']}/sec")

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

    async def load_markets(self) -> dict[str, Any]:
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

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
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

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> list[list]:
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

    async def fetch_balance_ex(self) -> dict[str, Any]:
        """Fetch account balances using BalanceEx endpoint for accurate available balance"""
        try:
            logger.info("[KRAKEN_BALANCE] Fetching extended balance from Kraken BalanceEx API...")

            # Use comprehensive protection for balance calls
            success, result, error = await self.comprehensive_protection.safe_api_call(
                'BalanceEx', self._private_request, 'BalanceEx'
            )

            if not success:
                logger.error(f"[KRAKEN_BALANCE] BalanceEx call failed: {error}")

                # Check if this is a circuit breaker error and handle appropriately
                if await self._handle_circuit_breaker_error(error, 'BalanceEx'):
                    # Circuit breaker detected and handled, try fallback
                    logger.warning("[KRAKEN_BALANCE] Circuit breaker detected, falling back to standard Balance endpoint")
                    return await self.fetch_balance()

                raise KrakenAPIError(f"BalanceEx failed: {error}")

            if not result:
                logger.warning("[KRAKEN_BALANCE] BalanceEx returned empty result")
                return await self.fetch_balance()  # Fallback to standard balance

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

    async def fetch_balance(self) -> dict[str, Any]:
        """Fetch account balances with enhanced USDT detection"""
        try:
            # Try BalanceEx first for more accurate data
            return await self.fetch_balance_ex()
        except Exception as ex:
            # Fallback to standard implementation
            logger.info(f"[KRAKEN_BALANCE] BalanceEx failed ({ex}), using standard Balance endpoint...")

            # Use comprehensive protection for fallback balance call
            success, result, error = await self.comprehensive_protection.safe_api_call(
                'Balance', self._private_request, 'Balance'
            )

            if not success:
                logger.error(f"[KRAKEN_BALANCE] Balance call failed: {error}")

                # Check if this is a circuit breaker error for fallback too
                if await self._handle_circuit_breaker_error(error, 'Balance'):
                    logger.warning("[KRAKEN_BALANCE] Circuit breaker detected on fallback Balance endpoint")
                    # Return empty balance structure rather than failing completely
                    return {'info': {}, 'free': {}, 'used': {}, 'total': {}}

                return {}

            if not result:
                logger.warning("[KRAKEN_BALANCE] Balance returned empty result")
                return {}

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
                          order_type: str = 'market', price: Optional[float] = None) -> dict[str, Any]:
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

            # Use comprehensive protection for order creation
            success, result, error = await self.comprehensive_protection.safe_api_call(
                'AddOrder', self._private_request, 'AddOrder', params
            )

            if not success:
                # Handle circuit breaker errors gracefully for order creation
                if await self._handle_circuit_breaker_error(error, 'AddOrder'):
                    logger.warning(f"[KRAKEN_ORDER] Circuit breaker detected for {symbol} order - retrying after wait")
                    # Retry once after circuit breaker wait
                    success, result, error = await self.comprehensive_protection.safe_api_call(
                        'AddOrder', self._private_request, 'AddOrder', params
                    )
                    if not success:
                        raise KrakenAPIError(f"Order creation failed after circuit breaker wait: {error}")
                else:
                    raise KrakenAPIError(f"Order creation failed: {error}")

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
            # Use comprehensive protection for order cancellation
            success, result, error = await self.comprehensive_protection.safe_api_call(
                'CancelOrder', self._private_request, 'CancelOrder', {'txid': order_id}
            )

            if not success:
                # Handle circuit breaker errors for cancellation
                if await self._handle_circuit_breaker_error(error, 'CancelOrder'):
                    logger.warning(f"[KRAKEN_CANCEL] Circuit breaker detected for order {order_id} - retrying after wait")
                    # Retry once after circuit breaker wait
                    success, result, error = await self.comprehensive_protection.safe_api_call(
                        'CancelOrder', self._private_request, 'CancelOrder', {'txid': order_id}
                    )
                    if not success:
                        logger.error(f"[KRAKEN_CANCEL] Cancel failed after circuit breaker wait: {error}")
                        return False
                else:
                    logger.error(f"[KRAKEN_CANCEL] Cancel failed: {error}")
                    return False

            return 'count' in result and result['count'] > 0

        except Exception as e:
            logger.error(f"[KRAKEN] Error canceling order {order_id}: {e}")
            return False

    async def fetch_order(self, order_id: str) -> dict[str, Any]:
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

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> list[dict[str, Any]]:
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
            logger.info("[KRAKEN] Requesting WebSocket token (legacy method)...")
            result = await self._private_request('GetWebSocketsToken')
            token = result.get('token', '')

            if token:
                token_preview = token[:20] + '...' if len(token) > 20 else token
                logger.info(f"[KRAKEN] ✅ WebSocket token obtained: {token_preview}")
            else:
                logger.warning("[KRAKEN] ⚠️ No token returned from GetWebSocketsToken")

            return token
        except KrakenAPIError as e:
            error_msg = str(e)
            if 'EGeneral:Permission denied' in error_msg:
                logger.error("[KRAKEN] 🔑 WebSocket token access denied - check API permissions")
            logger.error(f"[KRAKEN] Error getting WebSocket token: {error_msg}")
            return ''
        except Exception as e:
            logger.error(f"[KRAKEN] Error getting WebSocket token: {e}")
            return ''

    async def get_websockets_token(self) -> dict[str, Any]:
        """
        Get WebSocket authentication token in the format expected by auth manager.
        Enhanced with better error handling for permission issues.

        Returns:
            Dict with 'result' containing 'token' or error information
        """
        try:
            logger.info("[KRAKEN_WS_TOKEN] Requesting WebSocket authentication token...")
            response = await self._private_request('GetWebSocketsToken')

            if 'token' in response:
                token_preview = response['token'][:20] + '...' if len(response['token']) > 20 else response['token']
                logger.info(f"[KRAKEN_WS_TOKEN] ✅ Token obtained successfully: {token_preview}")
                return {
                    'result': {'token': response['token']},
                    'error': []
                }
            else:
                logger.warning(f"[KRAKEN_WS_TOKEN] ⚠️ No token in response: {response}")
                return {
                    'result': {},
                    'error': ['No token in response']
                }
        except KrakenAPIError as e:
            error_msg = str(e)
            logger.error(f"[KRAKEN_WS_TOKEN] ❌ Kraken API error: {error_msg}")

            # Enhanced error handling for permission issues
            if 'EGeneral:Permission denied' in error_msg:
                logger.error("[KRAKEN_WS_TOKEN] 🔑 PERMISSION DENIED - WebSocket token access not allowed")
                logger.error("[KRAKEN_WS_TOKEN] 📝 Required Kraken API permissions:")
                logger.error("[KRAKEN_WS_TOKEN]    ✅ Query Funds (REQUIRED)")
                logger.error("[KRAKEN_WS_TOKEN]    ✅ WebSocket Feeds (REQUIRED if available)")
                logger.error("[KRAKEN_WS_TOKEN]    ✅ Query Private Data (RECOMMENDED)")
                logger.error("[KRAKEN_WS_TOKEN] 🔧 Fix: Login to Kraken → Settings → API → Edit Key → Enable permissions")
            elif 'EAPI:Invalid nonce' in error_msg:
                logger.error("[KRAKEN_WS_TOKEN] 🔢 Nonce error - this will be retried automatically")
            elif 'Rate limit' in error_msg:
                logger.error("[KRAKEN_WS_TOKEN] 🚦 Rate limit reached - will retry after delay")

            return {
                'result': {},
                'error': [error_msg]
            }
        except Exception as e:
            logger.error(f"[KRAKEN_WS_TOKEN] ❌ Unexpected error getting WebSocket token: {e}")
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

    async def _ensure_minimum_delay(self) -> None:
        """CRITICAL FIX 2025: Enhanced API delay with counter-based rate limiting"""
        now = time.time()

        # Update counter based on decay rate
        time_elapsed = now - self.last_counter_update
        if time_elapsed > 0:
            # Decay counter based on tier specifications
            decay_amount = time_elapsed * self.rate_config['decay_rate']
            self.api_counter = max(0, self.api_counter - decay_amount)
            self.last_counter_update = now

        # Check if we're approaching rate limit
        max_counter = self.rate_config['max_counter']
        if self.api_counter >= (max_counter * 0.8):  # 80% threshold
            # Calculate required wait time
            excess = self.api_counter - (max_counter * 0.7)  # Target 70%
            wait_time = excess / self.rate_config['decay_rate']
            wait_time = min(wait_time, 5.0)  # Cap at 5 seconds

            logger.warning(f"[KRAKEN_2025] Rate limit protection: counter={self.api_counter:.1f}/{max_counter}, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)

            # Update counter after wait
            self.api_counter = max(0, self.api_counter - (wait_time * self.rate_config['decay_rate']))
            self.last_counter_update = time.time()

        # Ensure minimum delay between calls
        time_since_last_call = now - self.last_api_call_time
        if time_since_last_call < self.min_api_delay:
            delay_needed = self.min_api_delay - time_since_last_call
            await asyncio.sleep(delay_needed)

        # Increment counter for this call (Balance calls = +1, Ledger calls = +2)
        self.api_counter += 1
        self.last_api_call_time = time.time()

    async def _public_request_raw(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
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

    async def _public_request(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
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

    async def _private_request_raw(self, endpoint: str, params: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
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

                    # Check for rate limit errors
                    elif 'EAPI:Rate limit exceeded' in error_msg or 'EGeneral:Temporary lockout' in error_msg:
                        # CRITICAL FIX 2025: Enhanced rate limit error handling
                        error_type = "rate_limit" if "Rate limit" in error_msg else "temporary_lockout"

                        # Update internal counter to reflect we hit the limit
                        self.api_counter = self.rate_config['max_counter']

                        # Update rate limiter and open circuit breaker
                        self.kraken_rate_limiter.handle_kraken_error(error_msg, endpoint)
                        self.kraken_rate_limiter.open_circuit_breaker()

                        logger.warning(f"[KRAKEN_2025] {error_type.title()} detected: {error_msg}")

                        # Enhanced exponential backoff based on error type
                        if not hasattr(self, '_rate_limit_backoff_attempt'):
                            self._rate_limit_backoff_attempt = 0

                        self._rate_limit_backoff_attempt += 1

                        if error_type == "temporary_lockout":
                            # CRITICAL FIX 2025: Temporary lockout requires EXACTLY 15 minutes wait per Kraken docs
                            lockout_wait_minutes = 15.0
                            backoff_time = lockout_wait_minutes * 60.0  # Convert to seconds

                            # For temporary lockout, use fixed 15-minute wait, not exponential backoff
                            logger.error(f"[KRAKEN_2025] TEMPORARY LOCKOUT: Waiting exactly {lockout_wait_minutes} minutes as required by Kraken API")
                            logger.error(f"[KRAKEN_2025] This is attempt {self._rate_limit_backoff_attempt} - lockout time is fixed at 15 minutes")
                        else:
                            # Regular rate limit uses exponential backoff with Pro tier optimization
                            base_wait = 2.0 if self.tier == "pro" else 4.0
                            backoff_time = min(base_wait ** (self._rate_limit_backoff_attempt - 1), 32.0)

                        logger.warning(f"[KRAKEN_2025] Backoff attempt {self._rate_limit_backoff_attempt}: waiting {backoff_time}s")
                        await asyncio.sleep(backoff_time)

                        # Reset counter after successful wait
                        self.api_counter = 0
                        self.last_counter_update = time.time()

                    raise KrakenAPIError(error_msg)

                # Update health metrics on success
                self.last_successful_request = time.time()
                self.consecutive_failures = 0
                self.is_healthy = True

                # Reset exponential backoff on successful request
                if hasattr(self, '_rate_limit_backoff_attempt'):
                    self._rate_limit_backoff_attempt = 0

                # Update rate limit counter decay
                self.last_counter_update = time.time()

                return result.get('result', {})
        except aiohttp.ClientConnectorError as conn_error:
            if "DNS lookup failed" in str(conn_error):
                self.dns_failures += 1
                logger.error(f"[KRAKEN] DNS lookup failed: {conn_error}")
                # Let the resilient request handle the retry
            raise

    # Removed complex nonce persistence - using simple millisecond timestamps instead

    async def _private_request(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Make authenticated private API request with retry and error handling"""
        if not self.api_key or not self.api_secret:
            raise KrakenAPIError("API credentials not set")

        # Ensure minimum delay between API calls (100ms minimum)
        await self._ensure_minimum_delay()

        # Use ONLY KrakenRateLimiter for sophisticated rate limiting
        operation = self._get_operation_type(endpoint)
        await self.kraken_rate_limiter.wait_if_needed(
            symbol='global',  # Use 'global' for non-pair-specific endpoints
            operation=operation,
            endpoint=endpoint
        )

        # Check circuit breaker before proceeding
        if not self.kraken_rate_limiter.check_circuit_breaker():
            raise KrakenAPIError("Circuit breaker is open - preventing cascade failures")

        # Use unified nonce manager with async support
        nonce = await self.nonce_manager.get_nonce_async("native_kraken_rest")
        logger.debug(f"[KRAKEN_AUTH] Generated nonce: {nonce} for endpoint: {endpoint}")

        # Small delay to prevent rapid-fire requests
        await asyncio.sleep(0.05)  # 50ms between requests

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

    def get_health_status(self) -> dict[str, Any]:
        """Get detailed health status of the exchange connection"""
        time_since_success = time.time() - self.last_successful_request

        return {
            "healthy": self.is_healthy,
            "consecutive_failures": self.consecutive_failures,
            "time_since_last_success": time_since_success,
            "rate_limiter_status": self.kraken_rate_limiter.get_status(),
            "circuit_breaker_open": self.kraken_rate_limiter.circuit_breaker_open,
            "connection_pool_stats": self.connector.stats if self.connector else None,
            "resilient_request_metrics": self.resilient_request.get_performance_metrics(),
            "min_api_delay": self.min_api_delay,
            "last_api_call_time": self.last_api_call_time,
            "comprehensive_protection": self.comprehensive_protection.get_health_status()
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

    async def _handle_circuit_breaker_error(self, error_message: str, endpoint: str) -> bool:
        """
        Handle circuit breaker errors by parsing wait time and managing delays

        Args:
            error_message: Error message from API call
            endpoint: The endpoint that failed

        Returns:
            bool: True if circuit breaker error was handled, False otherwise
        """
        import asyncio
        import re

        # Check if this is a circuit breaker error
        if "Circuit breaker open" not in error_message:
            return False

        # Parse the remaining time from the error message
        # Format: "Circuit breaker open, 294s remaining"
        time_match = re.search(r'(\d+)s remaining', error_message)
        if not time_match:
            logger.warning(f"[CIRCUIT_BREAKER] Could not parse wait time from: {error_message}")
            return False

        wait_seconds = int(time_match.group(1))
        logger.warning(f"[CIRCUIT_BREAKER] {endpoint} blocked - circuit breaker open for {wait_seconds}s")

        # If wait time is reasonable (under 10 minutes), handle it gracefully
        if wait_seconds <= 600:  # 10 minutes max
            logger.info(f"[CIRCUIT_BREAKER] Gracefully handling circuit breaker - will wait {wait_seconds}s")

            # Log every 30 seconds during wait
            elapsed = 0
            while elapsed < wait_seconds:
                sleep_time = min(30, wait_seconds - elapsed)
                await asyncio.sleep(sleep_time)
                elapsed += sleep_time

                if elapsed < wait_seconds:
                    remaining = wait_seconds - elapsed
                    logger.info(f"[CIRCUIT_BREAKER] Still waiting for circuit breaker reset - {remaining}s remaining")

            logger.info("[CIRCUIT_BREAKER] Circuit breaker wait complete - resuming API calls")
            return True
        else:
            logger.error(f"[CIRCUIT_BREAKER] Wait time too long ({wait_seconds}s) - will not wait")
            return False

    def _create_simple_protection(self):
        """Create a simple protection wrapper for API calls"""
        class SimpleProtection:
            async def safe_api_call(self, endpoint, method, *args, **kwargs):
                """Simple wrapper that just calls the method directly"""
                try:
                    result = await method(*args, **kwargs)
                    return True, result, None
                except Exception as e:
                    return False, None, str(e)

            def get_health_status(self):
                """Simple health status"""
                return {"status": "active", "type": "simple_fallback"}

        return SimpleProtection()

    async def create_market_sell_order(self, symbol: str, amount: float) -> dict[str, Any]:
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

    async def get_account_balance(self) -> dict[str, Any]:
        """
        Get account balance for compatibility with hybrid portfolio manager.
        This wraps the fetch_balance method to provide the expected interface.

        Returns:
            Dict with 'result' containing balance data
        """
        try:
            logger.debug("[KRAKEN] Getting account balance via fetch_balance...")
            balance_data = await self.fetch_balance()

            # Return in the format expected by the hybrid portfolio manager
            if balance_data and balance_data.get('info'):
                return {
                    'result': balance_data['info'],  # Raw Kraken balance data
                    'error': []
                }
            else:
                logger.warning("[KRAKEN] No balance data returned")
                return {
                    'result': {},
                    'error': ['No balance data available']
                }

        except Exception as e:
            logger.error(f"[KRAKEN] Error getting account balance: {e}")
            return {
                'result': {},
                'error': [str(e)]
            }
