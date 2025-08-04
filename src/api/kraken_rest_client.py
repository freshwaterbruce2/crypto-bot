"""
Kraken Async REST API Client
============================

Comprehensive async REST API client for Kraken with full integration support.
Provides production-ready client with connection pooling, authentication,
rate limiting, circuit breaker protection, and comprehensive error handling.

Features:
- Full async/await support with aiohttp
- Session management with connection pooling
- Automatic authentication with signature generation
- Rate limiting with penalty point tracking
- Circuit breaker protection against failures
- Comprehensive error handling and retry logic
- Request/response validation with Pydantic
- Performance monitoring and metrics
- Thread-safe operations for concurrent use

Usage:
    async with KrakenRestClient(api_key, private_key) as client:
        balance = await client.get_account_balance()
        order = await client.add_order('XBTUSD', 'buy', 'market', volume='0.001')

Integration:
- Authentication: src/auth/kraken_auth.py
- Rate Limiting: src/rate_limiting/kraken_rate_limiter.py
- Circuit Breaker: src/circuit_breaker/circuit_breaker.py
"""

import asyncio
import json
import logging
import time
import urllib.parse
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from collections import deque, defaultdict
import threading

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector, ClientError

# Import our components
from ..auth.kraken_auth import KrakenAuth
from ..rate_limiting.kraken_rate_limiter import KrakenRateLimiter2025, AccountTier, RequestPriority
from ..circuit_breaker.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState

# Import API components
from .endpoints import (
    get_endpoint_definition, KRAKEN_ENDPOINTS, EndpointDefinition,
    EndpointType, HttpMethod, validate_endpoint_parameters
)
from .exceptions import (
    KrakenAPIError, AuthenticationError, RateLimitError, NetworkError,
    ValidationError, raise_for_kraken_errors, create_exception_from_error
)
from .response_models import (
    KrakenResponse, parse_kraken_response, get_response_model,
    BalanceResponse, OrderResponse, TickerResponse, OrderBookResponse,
    TradeHistoryResponse, CancelOrderResponse, WebSocketTokenResponse
)

logger = logging.getLogger(__name__)


@dataclass
class RequestConfig:
    """Configuration for individual requests."""
    timeout: Optional[float] = None
    max_retries: Optional[int] = None
    retry_delay: Optional[float] = None
    priority: RequestPriority = RequestPriority.NORMAL
    validate_response: bool = True
    raise_for_errors: bool = True


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_status_codes: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    retryable_exceptions: List[type] = field(default_factory=lambda: [
        NetworkError, RateLimitError, aiohttp.ClientError
    ])


@dataclass
class ClientMetrics:
    """Client performance metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retried_requests: int = 0
    rate_limited_requests: int = 0
    circuit_breaker_blocks: int = 0
    authentication_errors: int = 0
    network_errors: int = 0
    avg_response_time: float = 0.0
    total_response_time: float = 0.0
    endpoint_stats: Dict[str, Dict[str, Any]] = field(default_factory=lambda: defaultdict(dict))
    
    def update_request_stats(self, endpoint: str, success: bool, response_time: float, error_type: Optional[str] = None):
        """Update request statistics."""
        self.total_requests += 1
        self.total_response_time += response_time
        self.avg_response_time = self.total_response_time / self.total_requests
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type == 'rate_limit':
                self.rate_limited_requests += 1
            elif error_type == 'auth':
                self.authentication_errors += 1
            elif error_type == 'network':
                self.network_errors += 1
        
        # Update endpoint-specific stats
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                'requests': 0,
                'successes': 0,
                'failures': 0,
                'avg_response_time': 0.0,
                'total_response_time': 0.0
            }
        
        stats = self.endpoint_stats[endpoint]
        stats['requests'] += 1
        stats['total_response_time'] += response_time
        stats['avg_response_time'] = stats['total_response_time'] / stats['requests']
        
        if success:
            stats['successes'] += 1
        else:
            stats['failures'] += 1
    
    def get_success_rate(self) -> float:
        """Get overall success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def get_endpoint_success_rate(self, endpoint: str) -> float:
        """Get success rate for specific endpoint."""
        if endpoint not in self.endpoint_stats:
            return 0.0
        
        stats = self.endpoint_stats[endpoint]
        if stats['requests'] == 0:
            return 0.0
        
        return stats['successes'] / stats['requests']


class KrakenRestClient:
    """
    Production-ready async REST API client for Kraken.
    
    Provides comprehensive API access with authentication, rate limiting,
    circuit breaker protection, retry logic, and performance monitoring.
    """
    
    def __init__(
        self,
        api_key: str,
        private_key: str,
        base_url: str = "https://api.kraken.com",
        api_version: str = "0",
        timeout: float = 30.0,
        max_retries: int = 3,
        account_tier: Union[AccountTier, str] = AccountTier.INTERMEDIATE,
        enable_rate_limiting: bool = True,
        enable_circuit_breaker: bool = True,
        session: Optional[ClientSession] = None,
        user_agent: str = "KrakenRestClient/1.0.0"
    ):
        """
        Initialize Kraken REST client.
        
        Args:
            api_key: Kraken API key
            private_key: Kraken private key (base64 encoded)
            base_url: Base URL for Kraken API
            api_version: API version
            timeout: Default request timeout
            max_retries: Maximum retry attempts
            account_tier: Kraken account tier for rate limiting
            enable_rate_limiting: Enable rate limiting protection
            enable_circuit_breaker: Enable circuit breaker protection
            session: Optional aiohttp session (will create if None)
            user_agent: User agent string
        """
        self.api_key = api_key
        self.private_key = private_key
        self.base_url = base_url.rstrip('/')
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        
        # Convert account tier if string
        if isinstance(account_tier, str):
            account_tier = AccountTier(account_tier.lower())
        self.account_tier = account_tier
        
        # Session management
        self._session = session
        self._session_owned = session is None
        self._session_lock = asyncio.Lock()
        
        # Authentication
        self.auth = KrakenAuth(
            api_key=api_key,
            private_key=private_key,
            enable_debug=False
        )
        
        # Rate limiting
        self.rate_limiter = None
        if enable_rate_limiting:
            self.rate_limiter = KrakenRateLimiter2025(
                account_tier=account_tier,
                api_key=api_key,
                enable_queue=True,
                enable_circuit_breaker=False  # We have our own circuit breaker
            )
        
        # Circuit breaker
        self.circuit_breaker = None
        if enable_circuit_breaker:
            cb_config = CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=30.0,
                success_threshold=3,
                max_recovery_attempts=5,
                timeout=timeout
            )
            self.circuit_breaker = CircuitBreaker(
                name=f"kraken_api_{api_key[:8]}",
                config=cb_config
            )
        
        # Configuration
        self.retry_config = RetryConfig(
            max_attempts=max_retries,
            base_delay=1.0,
            max_delay=60.0
        )
        
        # Metrics and monitoring
        self.metrics = ClientMetrics()
        self._request_history = deque(maxlen=1000)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # State
        self._closed = False
        self._start_time = time.time()
        
        logger.info(
            f"Kraken REST client initialized: "
            f"api_key={api_key[:8]}..., tier={account_tier.value}, "
            f"rate_limiting={enable_rate_limiting}, circuit_breaker={enable_circuit_breaker}"
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self):
        """Start the client and initialize components."""
        async with self._session_lock:
            if self._session is None:
                # Create session with connection pooling
                connector = TCPConnector(
                    limit=100,  # Total connection pool size
                    limit_per_host=20,  # Max connections per host
                    ttl_dns_cache=300,  # DNS cache TTL
                    use_dns_cache=True,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )
                
                timeout_config = ClientTimeout(
                    total=self.timeout,
                    connect=10.0,
                    sock_read=self.timeout
                )
                
                headers = {
                    'User-Agent': self.user_agent,
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                self._session = ClientSession(
                    connector=connector,
                    timeout=timeout_config,
                    headers=headers,
                    raise_for_status=False  # We handle status codes manually
                )
        
        # Start rate limiter
        if self.rate_limiter:
            await self.rate_limiter.start()
        
        logger.info("Kraken REST client started")
    
    async def close(self):
        """Close the client and cleanup resources."""
        if self._closed:
            return
        
        self._closed = True
        
        # Close session if we own it
        if self._session_owned and self._session:
            await self._session.close()
        
        # Stop rate limiter
        if self.rate_limiter:
            await self.rate_limiter.stop()
        
        # Cleanup auth
        self.auth.cleanup()
        
        # Log final metrics
        success_rate = self.metrics.get_success_rate() * 100
        uptime = time.time() - self._start_time
        
        logger.info(
            f"Kraken REST client closed: "
            f"requests={self.metrics.total_requests}, "
            f"success_rate={success_rate:.1f}%, "
            f"avg_response_time={self.metrics.avg_response_time:.2f}s, "
            f"uptime={uptime:.1f}s"
        )
    
    async def _get_session(self) -> ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            await self.start()
        return self._session
    
    async def _make_request(
        self,
        endpoint_name: str,
        params: Optional[Dict[str, Any]] = None,
        config: Optional[RequestConfig] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request with full protection.
        
        Args:
            endpoint_name: Name of the API endpoint
            params: Request parameters
            config: Request configuration
            
        Returns:
            Response data dictionary
            
        Raises:
            KrakenAPIError: For API-specific errors
            NetworkError: For network/connectivity issues
            ValidationError: For parameter validation errors
        """
        if self._closed:
            raise RuntimeError("Client is closed")
        
        # Get endpoint definition
        endpoint = get_endpoint_definition(endpoint_name)
        if not endpoint:
            raise ValidationError(f"Unknown endpoint: {endpoint_name}")
        
        # Set default config
        if config is None:
            config = RequestConfig()
        
        # Validate parameters
        if params:
            validation_errors = endpoint.validate_parameters(params)
            if validation_errors:
                raise ValidationError(
                    f"Parameter validation failed: {'; '.join(validation_errors)}",
                    endpoint=endpoint_name,
                    request_data=params
                )
        
        start_time = time.time()
        last_exception = None
        
        for attempt in range(config.max_retries or self.retry_config.max_attempts):
            try:
                # Check circuit breaker
                if self.circuit_breaker and not self.circuit_breaker.can_execute():
                    self.metrics.circuit_breaker_blocks += 1
                    raise NetworkError(
                        "Circuit breaker is open",
                        retry_after=30.0,
                        endpoint=endpoint_name
                    )
                
                # Check rate limiting
                if self.rate_limiter:
                    can_proceed = await self.rate_limiter.wait_for_rate_limit(
                        endpoint_name,
                        priority=config.priority,
                        timeout_seconds=config.timeout or self.timeout
                    )
                    
                    if not can_proceed:
                        raise RateLimitError(
                            "Rate limit timeout",
                            retry_after=60.0,
                            endpoint=endpoint_name
                        )
                
                # Make the actual HTTP request
                response_data = await self._execute_http_request(endpoint, params, config)
                
                # Record success
                response_time = time.time() - start_time
                self.metrics.update_request_stats(endpoint_name, True, response_time)
                
                if self.circuit_breaker:
                    self.circuit_breaker._record_success(response_time * 1000)
                
                # Record request in history
                self._request_history.append({
                    'endpoint': endpoint_name,
                    'timestamp': time.time(),
                    'success': True,
                    'response_time': response_time,
                    'attempt': attempt + 1
                })
                
                return response_data
            
            except Exception as e:
                last_exception = e
                response_time = time.time() - start_time
                
                # Determine error type for metrics
                error_type = 'unknown'
                if isinstance(e, AuthenticationError):
                    error_type = 'auth'
                elif isinstance(e, RateLimitError):
                    error_type = 'rate_limit'
                elif isinstance(e, NetworkError):
                    error_type = 'network'
                
                self.metrics.update_request_stats(endpoint_name, False, response_time, error_type)
                
                if self.circuit_breaker:
                    self.circuit_breaker._record_failure(e, response_time * 1000)
                
                # Record failed request in history
                self._request_history.append({
                    'endpoint': endpoint_name,
                    'timestamp': time.time(),
                    'success': False,
                    'response_time': response_time,
                    'attempt': attempt + 1,
                    'error': str(e)
                })
                
                # Check if we should retry
                should_retry = self._should_retry_request(e, attempt, config)
                
                if not should_retry or attempt >= (config.max_retries or self.retry_config.max_attempts) - 1:
                    logger.error(
                        f"Request failed after {attempt + 1} attempts: "
                        f"endpoint={endpoint_name}, error={e}"
                    )
                    raise e
                
                # Calculate retry delay
                retry_delay = self._calculate_retry_delay(e, attempt)
                
                logger.warning(
                    f"Request failed, retrying in {retry_delay:.1f}s: "
                    f"endpoint={endpoint_name}, attempt={attempt + 1}, error={e}"
                )
                
                self.metrics.retried_requests += 1
                await asyncio.sleep(retry_delay)
        
        # Should never reach here due to the loop logic, but just in case
        raise last_exception or NetworkError("Request failed after all retries")
    
    async def _execute_http_request(
        self,
        endpoint: EndpointDefinition,
        params: Optional[Dict[str, Any]] = None,
        config: Optional[RequestConfig] = None
    ) -> Dict[str, Any]:
        """
        Execute the actual HTTP request.
        
        Args:
            endpoint: Endpoint definition
            params: Request parameters
            config: Request configuration
            
        Returns:
            Response data dictionary
        """
        if config is None:
            config = RequestConfig()
            
        session = await self._get_session()
        
        # Build URL
        url = f"{self.base_url}/{self.api_version}/{endpoint.path.lstrip('/')}"
        
        # Prepare request data
        request_data = params.copy() if params else {}
        
        # Add nonce for private endpoints
        if endpoint.endpoint_type == EndpointType.PRIVATE:
            nonce = self.auth.nonce_manager.get_nonce("kraken_rest_api")
            request_data['nonce'] = nonce
        
        # Get authentication headers
        headers = {}
        if endpoint.endpoint_type == EndpointType.PRIVATE:
            auth_headers = await self.auth.get_auth_headers_async(
                f"/{self.api_version}/{endpoint.path.lstrip('/')}",
                request_data
            )
            headers.update(auth_headers)
        
        # Prepare request body
        if endpoint.method == HttpMethod.GET:
            # GET requests use query parameters
            query_params = urllib.parse.urlencode(request_data) if request_data else ""
            full_url = f"{url}?{query_params}" if query_params else url
            request_body = None
        else:
            # POST requests use form data
            full_url = url
            request_body = urllib.parse.urlencode(request_data).encode('utf-8') if request_data else None
        
        # Set timeout
        timeout = ClientTimeout(total=config.timeout or self.timeout)
        
        # Make HTTP request
        try:
            async with session.request(
                method=endpoint.method.value,
                url=full_url,
                data=request_body,
                headers=headers,
                timeout=timeout
            ) as response:
                
                # Check for HTTP errors
                if response.status >= 400:
                    error_text = await response.text()
                    
                    if response.status == 401:
                        raise AuthenticationError(
                            f"Authentication failed: {error_text}",
                            endpoint=endpoint.name
                        )
                    elif response.status == 429:
                        # Extract retry-after header if present
                        retry_after = response.headers.get('Retry-After', '60')
                        try:
                            retry_after_seconds = float(retry_after)
                        except ValueError:
                            retry_after_seconds = 60.0
                        
                        raise RateLimitError(
                            f"Rate limit exceeded: {error_text}",
                            retry_after=retry_after_seconds,
                            endpoint=endpoint.name
                        )
                    elif response.status >= 500:
                        raise NetworkError(
                            f"Server error ({response.status}): {error_text}",
                            retry_after=30.0,
                            endpoint=endpoint.name
                        )
                    else:
                        raise NetworkError(
                            f"HTTP error ({response.status}): {error_text}",
                            endpoint=endpoint.name
                        )
                
                # Parse JSON response
                try:
                    response_data = await response.json()
                except json.JSONDecodeError as e:
                    response_text = await response.text()
                    raise NetworkError(
                        f"Invalid JSON response: {e}",
                        endpoint=endpoint.name,
                        response_data={'raw_response': response_text}
                    )
                
                # Check for Kraken API errors
                if config.raise_for_errors:
                    raise_for_kraken_errors(response_data, endpoint.name, request_data)
                
                return response_data
        
        except asyncio.TimeoutError:
            raise NetworkError(
                f"Request timeout after {config.timeout or self.timeout}s",
                retry_after=5.0,
                endpoint=endpoint.name
            )
        except ClientError as e:
            raise NetworkError(
                f"Network error: {e}",
                retry_after=5.0,
                endpoint=endpoint.name,
                original_exception=e
            )
    
    def _should_retry_request(
        self,
        error: Exception,
        attempt: int,
        config: RequestConfig
    ) -> bool:
        """
        Determine if request should be retried.
        
        Args:
            error: Exception that occurred
            attempt: Current attempt number (0-based)
            config: Request configuration
            
        Returns:
            True if request should be retried
        """
        max_attempts = config.max_retries or self.retry_config.max_attempts
        
        if attempt >= max_attempts - 1:
            return False
        
        # Check if error type is retryable
        for retryable_type in self.retry_config.retryable_exceptions:
            if isinstance(error, retryable_type):
                return True
        
        # Check if it's a retryable Kraken API error
        if isinstance(error, KrakenAPIError) and error.is_retryable():
            return True
        
        return False
    
    def _calculate_retry_delay(self, error: Exception, attempt: int) -> float:
        """
        Calculate delay before retry attempt.
        
        Args:
            error: Exception that occurred
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Use error-specific retry delay if available
        if isinstance(error, KrakenAPIError) and error.retry_after:
            return error.retry_after
        
        # Calculate exponential backoff
        delay = self.retry_config.base_delay * (
            self.retry_config.backoff_multiplier ** attempt
        )
        
        # Apply jitter if enabled
        if self.retry_config.jitter:
            import random
            jitter = delay * 0.1 * (random.random() - 0.5)
            delay += jitter
        
        # Cap at maximum delay
        return min(delay, self.retry_config.max_delay)
    
    # ====== PUBLIC API METHODS ======
    
    async def get_server_time(self) -> Dict[str, Any]:
        """Get server time."""
        return await self._make_request('ServerTime')
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status."""
        return await self._make_request('SystemStatus')
    
    async def get_asset_info(self, asset: Optional[str] = None) -> Dict[str, Any]:
        """
        Get asset information.
        
        Args:
            asset: Comma delimited list of assets to get info on
        """
        params = {}
        if asset:
            params['asset'] = asset
        
        return await self._make_request('AssetInfo', params)
    
    async def get_asset_pairs(self, pair: Optional[str] = None, info: str = "info") -> Dict[str, Any]:
        """
        Get tradable asset pairs.
        
        Args:
            pair: Comma delimited list of asset pairs
            info: Info to retrieve (info, leverage, fees, margin)
        """
        params = {'info': info}
        if pair:
            params['pair'] = pair
        
        return await self._make_request('AssetPairs', params)
    
    async def get_ticker_information(self, pair: str) -> Dict[str, Any]:
        """
        Get ticker information.
        
        Args:
            pair: Comma delimited list of asset pairs
        """
        return await self._make_request('Ticker', {'pair': pair})
    
    async def get_ohlc_data(
        self,
        pair: str,
        interval: int = 1,
        since: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get OHLC data.
        
        Args:
            pair: Asset pair
            interval: Time frame interval in minutes
            since: Return committed OHLC data since given ID
        """
        params = {'pair': pair, 'interval': interval}
        if since:
            params['since'] = since
        
        return await self._make_request('OHLC', params)
    
    async def get_order_book(self, pair: str, count: int = 100) -> Dict[str, Any]:
        """
        Get order book.
        
        Args:
            pair: Asset pair
            count: Maximum number of asks/bids
        """
        return await self._make_request('OrderBook', {'pair': pair, 'count': count})
    
    async def get_recent_trades(self, pair: str, since: Optional[str] = None) -> Dict[str, Any]:
        """
        Get recent trades.
        
        Args:
            pair: Asset pair
            since: Return trade data since given ID
        """
        params = {'pair': pair}
        if since:
            params['since'] = since
        
        return await self._make_request('RecentTrades', params)
    
    # ====== PRIVATE API METHODS ======
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance."""
        return await self._make_request('Balance')
    
    async def get_trade_balance(self, asset: str = "ZUSD") -> Dict[str, Any]:
        """
        Get trade balance.
        
        Args:
            asset: Base asset used to determine balance
        """
        return await self._make_request('TradeBalance', {'asset': asset})
    
    async def get_open_orders(
        self,
        trades: bool = False,
        userref: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get open orders.
        
        Args:
            trades: Whether to include trades related to position in output
            userref: Restrict results to given user reference id
        """
        params = {'trades': trades}
        if userref:
            params['userref'] = userref
        
        return await self._make_request('OpenOrders', params)
    
    async def get_closed_orders(
        self,
        trades: bool = False,
        userref: Optional[int] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        ofs: Optional[int] = None,
        closetime: str = "both"
    ) -> Dict[str, Any]:
        """
        Get closed orders.
        
        Args:
            trades: Whether to include trades related to position in output
            userref: Restrict results to given user reference id
            start: Starting unix timestamp or order tx ID of results
            end: Ending unix timestamp or order tx ID of results
            ofs: Result offset for pagination
            closetime: Which time to use to search (open, close, both)
        """
        params = {'trades': trades, 'closetime': closetime}
        if userref:
            params['userref'] = userref
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        if ofs:
            params['ofs'] = ofs
        
        return await self._make_request('ClosedOrders', params)
    
    async def query_orders_info(
        self,
        txid: str,
        trades: bool = False,
        userref: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Query orders info.
        
        Args:
            txid: Comma delimited list of transaction IDs to query info about
            trades: Whether to include trades related to position in output
            userref: Restrict results to given user reference id
        """
        params = {'txid': txid, 'trades': trades}
        if userref:
            params['userref'] = userref
        
        return await self._make_request('QueryOrders', params)
    
    async def get_trades_history(
        self,
        type: str = "all",
        trades: bool = False,
        start: Optional[int] = None,
        end: Optional[int] = None,
        ofs: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get trades history.
        
        Args:
            type: Type of trade
            trades: Whether to include trades related to position in output
            start: Starting unix timestamp or trade tx ID of results
            end: Ending unix timestamp or trade tx ID of results
            ofs: Result offset for pagination
        """
        params = {'type': type, 'trades': trades}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        if ofs:
            params['ofs'] = ofs
        
        return await self._make_request('TradesHistory', params)
    
    # ====== TRADING METHODS ======
    
    async def add_order(
        self,
        pair: str,
        type: str,  # buy/sell
        ordertype: str,
        volume: str,
        price: Optional[str] = None,
        price2: Optional[str] = None,
        leverage: Optional[str] = None,
        oflags: Optional[str] = None,
        starttm: Optional[str] = None,
        expiretm: Optional[str] = None,
        userref: Optional[int] = None,
        validate: bool = False,
        close: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add standard order.
        
        Args:
            pair: Asset pair
            type: Order direction (buy/sell)
            ordertype: Order type (market, limit, etc.)
            volume: Order quantity in terms of the base asset
            price: Price (dependent on ordertype)
            price2: Secondary price (dependent on ordertype)
            leverage: Amount of leverage desired
            oflags: Comma delimited list of order flags
            starttm: Scheduled start time
            expiretm: Expiration time
            userref: User reference id
            validate: Validate inputs only, do not submit order
            close: Closing order to add to system when order gets filled
        """
        params = {
            'pair': pair,
            'type': type,
            'ordertype': ordertype,
            'volume': volume
        }
        
        if price:
            params['price'] = price
        if price2:
            params['price2'] = price2
        if leverage:
            params['leverage'] = leverage
        if oflags:
            params['oflags'] = oflags
        if starttm:
            params['starttm'] = starttm
        if expiretm:
            params['expiretm'] = expiretm
        if userref:
            params['userref'] = userref
        if validate:
            params['validate'] = validate
        if close:
            params['close'] = close
        
        return await self._make_request('AddOrder', params)
    
    async def edit_order(
        self,
        txid: str,
        pair: str,
        volume: Optional[str] = None,
        price: Optional[str] = None,
        price2: Optional[str] = None,
        oflags: Optional[str] = None,
        newuserref: Optional[int] = None,
        validate: bool = False
    ) -> Dict[str, Any]:
        """
        Edit an order.
        
        Args:
            txid: Transaction ID of order to edit
            pair: Asset pair
            volume: Order quantity in terms of the base asset
            price: Price
            price2: Secondary price
            oflags: Comma delimited list of order flags
            newuserref: New user reference id
            validate: Validate inputs only, do not submit order
        """
        params = {'txid': txid, 'pair': pair}
        
        if volume:
            params['volume'] = volume
        if price:
            params['price'] = price
        if price2:
            params['price2'] = price2
        if oflags:
            params['oflags'] = oflags
        if newuserref:
            params['newuserref'] = newuserref
        if validate:
            params['validate'] = validate
        
        return await self._make_request('EditOrder', params)
    
    async def cancel_order(self, txid: str) -> Dict[str, Any]:
        """
        Cancel open order.
        
        Args:
            txid: Transaction ID of order to cancel
        """
        return await self._make_request('CancelOrder', {'txid': txid})
    
    async def cancel_all_orders(self) -> Dict[str, Any]:
        """Cancel all open orders."""
        return await self._make_request('CancelAllOrders')
    
    async def cancel_all_orders_after(self, timeout: int) -> Dict[str, Any]:
        """
        Cancel all orders after X seconds.
        
        Args:
            timeout: Duration (in seconds) to set/extend the timer by
        """
        return await self._make_request('CancelAllOrdersAfter', {'timeout': timeout})
    
    # ====== WEBSOCKET TOKEN METHOD ======
    
    async def get_websockets_token(self) -> Dict[str, Any]:
        """Get WebSocket authentication token."""
        return await self._make_request('GetWebSocketsToken')
    
    # ====== UTILITY METHODS ======
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics."""
        uptime = time.time() - self._start_time
        
        return {
            'uptime_seconds': uptime,
            'success_rate': self.metrics.get_success_rate(),
            'total_requests': self.metrics.total_requests,
            'successful_requests': self.metrics.successful_requests,
            'failed_requests': self.metrics.failed_requests,
            'retried_requests': self.metrics.retried_requests,
            'rate_limited_requests': self.metrics.rate_limited_requests,
            'circuit_breaker_blocks': self.metrics.circuit_breaker_blocks,
            'authentication_errors': self.metrics.authentication_errors,
            'network_errors': self.metrics.network_errors,
            'avg_response_time': self.metrics.avg_response_time,
            'requests_per_second': self.metrics.total_requests / uptime if uptime > 0 else 0.0,
            'endpoint_stats': dict(self.metrics.endpoint_stats),
            'rate_limiter_status': self.rate_limiter.get_status() if self.rate_limiter else None,
            'circuit_breaker_status': self.circuit_breaker.get_status() if self.circuit_breaker else None
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive client status."""
        return {
            'client_info': {
                'api_key': self.api_key[:8] + '...',
                'account_tier': self.account_tier.value,
                'base_url': self.base_url,
                'api_version': self.api_version,
                'closed': self._closed
            },
            'configuration': {
                'timeout': self.timeout,
                'max_retries': self.max_retries,
                'rate_limiting_enabled': self.rate_limiter is not None,
                'circuit_breaker_enabled': self.circuit_breaker is not None
            },
            'metrics': self.get_metrics(),
            'recent_requests': list(self._request_history)[-10:]  # Last 10 requests
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health check results
        """
        health = {
            'timestamp': time.time(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        # Check API connectivity
        try:
            server_time = await self.get_server_time()
            health['checks']['api_connectivity'] = {
                'status': 'healthy',
                'response_time': time.time() - health['timestamp'],
                'server_time': server_time.get('result', {}).get('unixtime')
            }
        except Exception as e:
            health['checks']['api_connectivity'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['overall_status'] = 'unhealthy'
        
        # Check authentication
        if health['overall_status'] == 'healthy':
            try:
                balance = await self.get_account_balance()
                health['checks']['authentication'] = {
                    'status': 'healthy',
                    'has_balance_data': bool(balance.get('result'))
                }
            except AuthenticationError as e:
                health['checks']['authentication'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health['overall_status'] = 'unhealthy'
            except Exception as e:
                health['checks']['authentication'] = {
                    'status': 'degraded',
                    'error': str(e)
                }
                if health['overall_status'] == 'healthy':
                    health['overall_status'] = 'degraded'
        
        # Check rate limiter
        if self.rate_limiter:
            rl_status = self.rate_limiter.get_status()
            health['checks']['rate_limiter'] = {
                'status': 'healthy',
                'requests_made': rl_status['statistics']['requests_made'],
                'requests_blocked': rl_status['statistics']['requests_blocked']
            }
        
        # Check circuit breaker
        if self.circuit_breaker:
            cb_status = self.circuit_breaker.get_status()
            health['checks']['circuit_breaker'] = {
                'status': 'healthy' if cb_status['can_execute'] else 'degraded',
                'state': cb_status['state'],
                'failure_count': cb_status['failure_count']
            }
            
            if not cb_status['can_execute'] and health['overall_status'] == 'healthy':
                health['overall_status'] = 'degraded'
        
        return health
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        with self._lock:
            self.metrics = ClientMetrics()
            self._request_history.clear()
            self._start_time = time.time()
        
        logger.info("Client metrics reset")
    
    async def test_connectivity(self) -> bool:
        """
        Test basic API connectivity.
        
        Returns:
            True if API is reachable
        """
        try:
            await self.get_server_time()
            return True
        except Exception as e:
            logger.error(f"Connectivity test failed: {e}")
            return False
    
    async def test_authentication(self) -> bool:
        """
        Test API authentication.
        
        Returns:
            True if authentication is working
        """
        try:
            await self.get_account_balance()
            return True
        except AuthenticationError:
            return False
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            return False