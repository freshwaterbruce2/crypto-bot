"""
Unified Data Coordinator
========================

Coordinates data flow between WebSocket V2 and REST API to optimize performance
and minimize nonce conflicts while ensuring data consistency and availability.

Features:
- Smart routing between WebSocket and REST
- Automatic fallback management
- Nonce conflict minimization
- Intelligent caching and batching
- Real-time performance monitoring
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Data source types"""
    WEBSOCKET = "websocket"
    REST = "rest"
    CACHE = "cache"


@dataclass
class DataRoutingConfig:
    """Configuration for data routing decisions"""
    websocket_primary_ratio: float = 0.95
    rest_fallback_ratio: float = 0.05
    enable_smart_routing: bool = True
    max_websocket_failures: int = 3
    fallback_timeout: float = 30.0
    cache_ttl: float = 5.0


@dataclass
class RestOptimizationConfig:
    """Configuration for REST API optimization"""
    minimize_nonce_conflicts: bool = True
    batch_requests: bool = True
    intelligent_caching: bool = True
    max_batch_size: int = 10
    batch_timeout: float = 0.5
    nonce_spacing_ms: int = 100


class UnifiedDataCoordinator:
    """
    Coordinates data flow between WebSocket V2 and REST API
    Optimizes for performance while minimizing API conflicts
    """

    def __init__(self, exchange_client, config: dict[str, Any]):
        """Initialize the unified data coordinator"""
        self.exchange = exchange_client
        self.config = config

        # Routing configuration
        self.routing_config = DataRoutingConfig()
        self.rest_config = RestOptimizationConfig()

        # Component references
        self.websocket_manager = None

        # State tracking
        self.websocket_failures = 0
        self.last_websocket_failure = None
        self.in_fallback_mode = False

        # Performance tracking
        self.request_stats = defaultdict(int)
        self.response_times = defaultdict(deque)
        self.error_counts = defaultdict(int)

        # Data caching
        self.cache = {}
        self.cache_timestamps = {}

        # Request batching and nonce optimization
        self.pending_requests = []
        self.batch_timer = None
        self.last_rest_call = 0
        self.nonce_spacing_lock = asyncio.Lock()

        # API call routing optimization
        self.api_call_queue = asyncio.Queue()
        self.api_worker_task = None

        # Callbacks
        self.data_callbacks = {
            'ticker': [],
            'balance': [],
            'ohlc': [],
            'order': []
        }

        logger.info("[DATA_COORDINATOR] Unified data coordinator initialized")

    def set_websocket_manager(self, websocket_manager):
        """Set the WebSocket manager reference"""
        self.websocket_manager = websocket_manager
        logger.info("[DATA_COORDINATOR] WebSocket manager reference set")

    def configure_data_routing(self,
                             websocket_primary_ratio: float = 0.95,
                             rest_fallback_ratio: float = 0.05,
                             enable_smart_routing: bool = True):
        """Configure data routing preferences"""
        self.routing_config.websocket_primary_ratio = websocket_primary_ratio
        self.routing_config.rest_fallback_ratio = rest_fallback_ratio
        self.routing_config.enable_smart_routing = enable_smart_routing

        logger.info(f"[DATA_COORDINATOR] Data routing configured: "
                   f"WS:{websocket_primary_ratio:.1%} REST:{rest_fallback_ratio:.1%}")

    def configure_rest_optimization(self,
                                  minimize_nonce_conflicts: bool = True,
                                  batch_requests: bool = True,
                                  intelligent_caching: bool = True):
        """Configure REST API optimization strategies"""
        self.rest_config.minimize_nonce_conflicts = minimize_nonce_conflicts
        self.rest_config.batch_requests = batch_requests
        self.rest_config.intelligent_caching = intelligent_caching

        logger.info(f"[DATA_COORDINATOR] REST optimization configured: "
                   f"nonce_minimize={minimize_nonce_conflicts}, "
                   f"batching={batch_requests}, caching={intelligent_caching}")

    async def get_ticker_data(self, symbol: str, force_source: Optional[DataSource] = None) -> dict[str, Any]:
        """
        Get ticker data with intelligent source routing

        Args:
            symbol: Trading pair symbol
            force_source: Force specific data source (optional)

        Returns:
            Ticker data dictionary
        """
        source = force_source or self._determine_data_source('ticker')

        try:
            if source == DataSource.WEBSOCKET and self.websocket_manager:
                # Try WebSocket first
                data = await self._get_websocket_ticker(symbol)
                if data:
                    self._record_success('ticker', DataSource.WEBSOCKET)
                    return data
                else:
                    # Fallback to REST
                    return await self._get_rest_ticker(symbol)

            elif source == DataSource.CACHE:
                # Check cache first
                cached_data = self._get_cached_data('ticker', symbol)
                if cached_data:
                    self._record_success('ticker', DataSource.CACHE)
                    return cached_data
                # Cache miss - fallback to primary source
                return await self.get_ticker_data(symbol, DataSource.WEBSOCKET)

            else:
                # Use REST
                return await self._get_rest_ticker(symbol)

        except Exception as e:
            logger.error(f"[DATA_COORDINATOR] Error getting ticker for {symbol}: {e}")
            self._record_error('ticker', source)
            # Try fallback source
            if source != DataSource.REST:
                return await self._get_rest_ticker(symbol)
            raise

    async def get_balance_data(self, force_refresh: bool = False) -> dict[str, Any]:
        """
        Get balance data with intelligent source routing

        Args:
            force_refresh: Force refresh from primary source

        Returns:
            Balance data dictionary
        """
        if not force_refresh:
            # Check cache first
            cached_data = self._get_cached_data('balance', 'all')
            if cached_data:
                self._record_success('balance', DataSource.CACHE)
                return cached_data

        source = self._determine_data_source('balance')

        try:
            if source == DataSource.WEBSOCKET and self.websocket_manager:
                # WebSocket balance updates are pushed, not pulled
                # Use REST for balance queries
                return await self._get_rest_balance()
            else:
                return await self._get_rest_balance()

        except Exception as e:
            logger.error(f"[DATA_COORDINATOR] Error getting balance data: {e}")
            self._record_error('balance', source)
            raise

    async def get_ohlc_data(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> list[dict[str, Any]]:
        """
        Get OHLC data with intelligent source routing

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe (1m, 5m, 1h, etc.)
            limit: Number of candles to retrieve

        Returns:
            List of OHLC data
        """
        source = self._determine_data_source('ohlc')

        try:
            if source == DataSource.WEBSOCKET and self.websocket_manager:
                # WebSocket provides real-time OHLC updates
                # For historical data, always use REST
                return await self._get_rest_ohlc(symbol, timeframe, limit)
            else:
                return await self._get_rest_ohlc(symbol, timeframe, limit)

        except Exception as e:
            logger.error(f"[DATA_COORDINATOR] Error getting OHLC for {symbol}: {e}")
            self._record_error('ohlc', source)
            raise

    def _determine_data_source(self, data_type: str) -> DataSource:
        """Determine the best data source for a request"""

        # Check if we're in fallback mode
        if self.in_fallback_mode:
            return DataSource.REST

        # Check WebSocket health
        if self.websocket_failures >= self.routing_config.max_websocket_failures:
            self._enter_fallback_mode()
            return DataSource.REST

        # Smart routing based on data type and configuration
        if self.routing_config.enable_smart_routing:
            # Real-time data prefers WebSocket
            if data_type in ['ticker', 'ohlc'] and self.websocket_manager:
                if self.websocket_manager.is_connected:
                    return DataSource.WEBSOCKET

            # Balance data can use cache if recent
            if data_type == 'balance':
                cached_data = self._get_cached_data('balance', 'all')
                if cached_data:
                    return DataSource.CACHE

        # Default routing based on ratios
        import random
        if random.random() < self.routing_config.websocket_primary_ratio:
            if self.websocket_manager and self.websocket_manager.is_connected:
                return DataSource.WEBSOCKET

        return DataSource.REST

    async def _get_websocket_ticker(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get ticker data from WebSocket"""
        if not self.websocket_manager or not self.websocket_manager.is_connected:
            return None

        # WebSocket data is pushed via callbacks
        # Return cached WebSocket data if available
        return self._get_cached_data('ws_ticker', symbol)

    async def _get_rest_ticker(self, symbol: str) -> dict[str, Any]:
        """Get ticker data from REST API"""
        start_time = time.time()

        try:
            # Use exchange client to get ticker
            ticker_data = await self.exchange.fetch_ticker(symbol)

            # Cache the result
            self._cache_data('ticker', symbol, ticker_data)

            # Record success
            response_time = time.time() - start_time
            self._record_success('ticker', DataSource.REST, response_time)

            return ticker_data

        except Exception:
            self._record_error('ticker', DataSource.REST)
            raise

    async def _get_rest_balance(self) -> dict[str, Any]:
        """Get balance data from REST API with optimization"""
        start_time = time.time()

        try:
            # Check if we should batch this request
            if self.rest_config.batch_requests:
                return await self._add_to_batch('balance', {})

            # Direct REST call
            balance_data = await self.exchange.fetch_balance()

            # Cache the result
            self._cache_data('balance', 'all', balance_data)

            # Record success
            response_time = time.time() - start_time
            self._record_success('balance', DataSource.REST, response_time)

            return balance_data

        except Exception:
            self._record_error('balance', DataSource.REST)
            raise

    async def _get_rest_ohlc(self, symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
        """Get OHLC data from REST API"""
        start_time = time.time()

        try:
            # Use exchange client to get OHLC
            ohlc_data = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            # Cache the result
            cache_key = f"{symbol}_{timeframe}_{limit}"
            self._cache_data('ohlc', cache_key, ohlc_data)

            # Record success
            response_time = time.time() - start_time
            self._record_success('ohlc', DataSource.REST, response_time)

            return ohlc_data

        except Exception:
            self._record_error('ohlc', DataSource.REST)
            raise

    def _cache_data(self, data_type: str, key: str, data: Any):
        """Cache data with TTL"""
        if not self.rest_config.intelligent_caching:
            return

        cache_key = f"{data_type}_{key}"
        self.cache[cache_key] = data
        self.cache_timestamps[cache_key] = time.time()

        # Clean old cache entries
        self._clean_cache()

    def _get_cached_data(self, data_type: str, key: str) -> Optional[Any]:
        """Get cached data if still valid"""
        if not self.rest_config.intelligent_caching:
            return None

        cache_key = f"{data_type}_{key}"

        if cache_key not in self.cache:
            return None

        # Check TTL
        if time.time() - self.cache_timestamps[cache_key] > self.routing_config.cache_ttl:
            del self.cache[cache_key]
            del self.cache_timestamps[cache_key]
            return None

        return self.cache[cache_key]

    def _clean_cache(self):
        """Clean expired cache entries"""
        current_time = time.time()
        expired_keys = []

        for key, timestamp in self.cache_timestamps.items():
            if current_time - timestamp > self.routing_config.cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            if key in self.cache:
                del self.cache[key]
            if key in self.cache_timestamps:
                del self.cache_timestamps[key]

    async def _add_to_batch(self, request_type: str, params: dict[str, Any]) -> Any:
        """Add request to batch for processing with nonce optimization"""
        if self.rest_config.minimize_nonce_conflicts:
            return await self._execute_with_nonce_spacing(request_type, params)
        else:
            # Direct execution without spacing
            return await getattr(self.exchange, f'fetch_{request_type}')(**params)

    async def _execute_with_nonce_spacing(self, request_type: str, params: dict[str, Any]) -> Any:
        """Execute REST call with proper nonce spacing to prevent conflicts"""
        async with self.nonce_spacing_lock:
            # Calculate required delay
            current_time = time.time() * 1000  # Convert to milliseconds
            time_since_last_call = current_time - self.last_rest_call

            if time_since_last_call < self.rest_config.nonce_spacing_ms:
                delay = (self.rest_config.nonce_spacing_ms - time_since_last_call) / 1000
                await asyncio.sleep(delay)

            # Execute the request
            try:
                result = await getattr(self.exchange, f'fetch_{request_type}')(**params)
                self.last_rest_call = time.time() * 1000
                return result
            except Exception as e:
                logger.error(f"[DATA_COORDINATOR] Nonce-spaced API call failed: {e}")
                raise

    async def start_api_worker(self):
        """Start the API call worker for optimal routing"""
        if self.api_worker_task:
            return

        self.api_worker_task = asyncio.create_task(self._api_worker_loop())
        logger.info("[DATA_COORDINATOR] API worker started for optimal call routing")

    async def stop_api_worker(self):
        """Stop the API call worker"""
        if self.api_worker_task:
            self.api_worker_task.cancel()
            try:
                await self.api_worker_task
            except asyncio.CancelledError:
                pass
            self.api_worker_task = None
            logger.info("[DATA_COORDINATOR] API worker stopped")

    async def _api_worker_loop(self):
        """Worker loop for processing API calls with optimal timing"""
        while True:
            try:
                # Get next API call from queue
                call_info = await self.api_call_queue.get()

                if call_info is None:  # Shutdown signal
                    break

                method, args, kwargs, future = call_info

                try:
                    # Execute with nonce spacing if required
                    if self.rest_config.minimize_nonce_conflicts:
                        result = await self._execute_with_nonce_spacing(method, kwargs)
                    else:
                        result = await getattr(self.exchange, method)(*args, **kwargs)

                    if not future.cancelled():
                        future.set_result(result)

                except Exception as e:
                    if not future.cancelled():
                        future.set_exception(e)

                # Mark task as done
                self.api_call_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[DATA_COORDINATOR] API worker error: {e}")
                await asyncio.sleep(1)

    async def queue_api_call(self, method: str, *args, **kwargs) -> Any:
        """Queue an API call for optimal execution timing"""
        if not self.api_worker_task:
            # Start worker if not running
            await self.start_api_worker()

        # Create future for result
        future = asyncio.Future()

        # Queue the call
        await self.api_call_queue.put((method, args, kwargs, future))

        # Wait for result
        return await future

    def _record_success(self, data_type: str, source: DataSource, response_time: float = 0):
        """Record successful request"""
        self.request_stats[f"{data_type}_{source.value}_success"] += 1

        if response_time > 0:
            self.response_times[f"{data_type}_{source.value}"].append(response_time)
            # Keep only recent response times
            if len(self.response_times[f"{data_type}_{source.value}"]) > 100:
                self.response_times[f"{data_type}_{source.value}"].popleft()

        # Reset WebSocket failure count on success
        if source == DataSource.WEBSOCKET:
            self.websocket_failures = 0
            self._exit_fallback_mode()

    def _record_error(self, data_type: str, source: DataSource):
        """Record failed request"""
        self.error_counts[f"{data_type}_{source.value}"] += 1

        # Track WebSocket failures
        if source == DataSource.WEBSOCKET:
            self.websocket_failures += 1
            self.last_websocket_failure = time.time()

            if self.websocket_failures >= self.routing_config.max_websocket_failures:
                self._enter_fallback_mode()

    def _enter_fallback_mode(self):
        """Enter REST fallback mode with enhanced coordination"""
        if not self.in_fallback_mode:
            self.in_fallback_mode = True
            logger.warning(f"[DATA_COORDINATOR] Entering REST fallback mode due to "
                          f"{self.websocket_failures} WebSocket failures")

            # Notify components about fallback mode
            if hasattr(self, 'fallback_callbacks'):
                for callback in self.fallback_callbacks:
                    try:
                        asyncio.create_task(callback('entered'))
                    except Exception as e:
                        logger.error(f"[DATA_COORDINATOR] Fallback callback error: {e}")

            # Adjust REST optimization for increased load
            self.rest_config.batch_requests = True
            self.rest_config.intelligent_caching = True

            # Start fallback monitoring
            asyncio.create_task(self._monitor_fallback_recovery())

    def _exit_fallback_mode(self):
        """Exit REST fallback mode with enhanced coordination"""
        if self.in_fallback_mode:
            # Check if enough time has passed since last failure
            if (self.last_websocket_failure and
                time.time() - self.last_websocket_failure > self.routing_config.fallback_timeout):
                self.in_fallback_mode = False
                logger.info("[DATA_COORDINATOR] Exiting REST fallback mode - WebSocket recovered")

                # Notify components about recovery
                if hasattr(self, 'fallback_callbacks'):
                    for callback in self.fallback_callbacks:
                        try:
                            asyncio.create_task(callback('exited'))
                        except Exception as e:
                            logger.error(f"[DATA_COORDINATOR] Recovery callback error: {e}")

    async def _monitor_fallback_recovery(self):
        """Monitor WebSocket recovery during fallback mode"""
        while self.in_fallback_mode:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds

                # Test WebSocket connectivity
                if self.websocket_manager and hasattr(self.websocket_manager, 'is_connected'):
                    if self.websocket_manager.is_connected:
                        # WebSocket is back - reset failure count
                        self.websocket_failures = 0
                        self._exit_fallback_mode()
                        break

            except Exception as e:
                logger.error(f"[DATA_COORDINATOR] Fallback monitoring error: {e}")
                await asyncio.sleep(10)  # Wait longer on error

    def register_fallback_callback(self, callback: Callable):
        """Register callback for fallback mode changes"""
        if not hasattr(self, 'fallback_callbacks'):
            self.fallback_callbacks = []
        self.fallback_callbacks.append(callback)
        logger.debug("[DATA_COORDINATOR] Registered fallback callback")

    async def force_rest_fallback(self, duration: float = 60.0):
        """Force REST fallback mode for a specific duration"""
        logger.info(f"[DATA_COORDINATOR] Forcing REST fallback for {duration} seconds")
        self._enter_fallback_mode()

        # Set a timer to exit fallback mode
        async def exit_timer():
            await asyncio.sleep(duration)
            self.in_fallback_mode = False
            self.websocket_failures = 0
            logger.info("[DATA_COORDINATOR] Forced REST fallback period ended")

        asyncio.create_task(exit_timer())

    async def test_websocket_connectivity(self) -> bool:
        """Test WebSocket connectivity and adjust routing"""
        try:
            if not self.websocket_manager:
                return False

            # Check connection status
            if hasattr(self.websocket_manager, 'is_connected'):
                is_connected = self.websocket_manager.is_connected

                if not is_connected:
                    self._record_error('connectivity', DataSource.WEBSOCKET)
                    return False
                else:
                    self._record_success('connectivity', DataSource.WEBSOCKET)
                    return True

            return False

        except Exception as e:
            logger.error(f"[DATA_COORDINATOR] WebSocket connectivity test failed: {e}")
            self._record_error('connectivity', DataSource.WEBSOCKET)
            return False

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics"""
        stats = {
            'request_counts': dict(self.request_stats),
            'error_counts': dict(self.error_counts),
            'websocket_failures': self.websocket_failures,
            'in_fallback_mode': self.in_fallback_mode,
            'cache_size': len(self.cache),
            'average_response_times': {}
        }

        # Calculate average response times
        for key, times in self.response_times.items():
            if times:
                stats['average_response_times'][key] = sum(times) / len(times)

        return stats

    # WebSocket callback methods for unified data handling
    async def handle_websocket_ticker(self, symbol: str, ticker_data: dict[str, Any]):
        """Handle WebSocket ticker updates"""
        # Cache WebSocket data
        self._cache_data('ws_ticker', symbol, ticker_data)

        # Notify registered callbacks
        for callback in self.data_callbacks['ticker']:
            try:
                await callback(symbol, ticker_data, DataSource.WEBSOCKET)
            except Exception as e:
                logger.error(f"[DATA_COORDINATOR] Ticker callback error: {e}")

    async def handle_websocket_balance(self, balance_data: dict[str, Any]):
        """Handle WebSocket balance updates"""
        # Cache WebSocket balance data
        self._cache_data('ws_balance', 'all', balance_data)

        # Notify registered callbacks
        for callback in self.data_callbacks['balance']:
            try:
                await callback(balance_data, DataSource.WEBSOCKET)
            except Exception as e:
                logger.error(f"[DATA_COORDINATOR] Balance callback error: {e}")

    async def handle_websocket_ohlc(self, symbol: str, ohlc_data: dict[str, Any]):
        """Handle WebSocket OHLC updates"""
        # Cache WebSocket OHLC data
        self._cache_data('ws_ohlc', symbol, ohlc_data)

        # Notify registered callbacks
        for callback in self.data_callbacks['ohlc']:
            try:
                await callback(symbol, ohlc_data, DataSource.WEBSOCKET)
            except Exception as e:
                logger.error(f"[DATA_COORDINATOR] OHLC callback error: {e}")

    async def handle_websocket_order(self, order_data: dict[str, Any]):
        """Handle WebSocket order updates"""
        # Notify registered callbacks
        for callback in self.data_callbacks['order']:
            try:
                await callback(order_data, DataSource.WEBSOCKET)
            except Exception as e:
                logger.error(f"[DATA_COORDINATOR] Order callback error: {e}")

    def register_callback(self, data_type: str, callback: Callable):
        """Register callback for data updates"""
        if data_type in self.data_callbacks:
            self.data_callbacks[data_type].append(callback)
            logger.debug(f"[DATA_COORDINATOR] Registered {data_type} callback")
        else:
            logger.warning(f"[DATA_COORDINATOR] Unknown data type: {data_type}")
