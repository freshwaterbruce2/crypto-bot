"""
Strategic REST Client for Crypto Trading Bot
==========================================

Minimalist REST API client designed to work strategically with WebSocket V2
to minimize nonce issues while providing essential fallback functionality.

Key Principles:
- REST is secondary to WebSocket V2
- Minimal API calls to preserve nonce integrity
- Smart request batching and circuit breaker protection
- Strategic usage patterns to reduce conflicts

Usage:
    client = StrategicRestClient(api_key, private_key)
    await client.initialize()
    
    # Emergency balance check
    balance = await client.emergency_balance_check()
    
    # Historical data fetch (batch)
    historical = await client.batch_historical_query(pairs, timeframe)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..api.exceptions import NetworkError
from ..api.kraken_rest_client import KrakenRestClient, RequestConfig
from ..circuit_breaker.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ..utils.consolidated_nonce_manager import get_nonce_manager

logger = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    """Represents a batched API request."""
    endpoint: str
    params: Dict[str, Any]
    priority: int = 1  # Higher = more important
    timestamp: float = field(default_factory=time.time)
    callback: Optional[callable] = None


@dataclass
class StrategicUsageStats:
    """Track strategic REST usage patterns."""
    total_requests: int = 0
    batched_requests: int = 0
    emergency_requests: int = 0
    historical_requests: int = 0
    validation_requests: int = 0
    nonce_conflicts: int = 0
    websocket_fallbacks: int = 0

    def log_summary(self):
        """Log usage summary."""
        logger.info(
            f"[STRATEGIC_REST] Usage Summary: "
            f"total={self.total_requests}, batched={self.batched_requests}, "
            f"emergency={self.emergency_requests}, nonce_conflicts={self.nonce_conflicts}"
        )


class StrategicRestClient:
    """
    Strategic REST client that minimizes API usage while providing essential fallback.
    
    Design Philosophy:
    1. WebSocket V2 is primary data source
    2. REST is for emergency/validation/historical only
    3. Batch requests to minimize nonce usage
    4. Circuit breaker prevents cascade failures
    5. Strategic timing to avoid WebSocket conflicts
    """

    def __init__(
        self,
        api_key: str,
        private_key: str,
        base_url: str = "https://api.kraken.com",
        max_batch_size: int = 5,
        batch_timeout: float = 2.0,
        emergency_only: bool = False
    ):
        """
        Initialize strategic REST client.
        
        Args:
            api_key: Kraken API key
            private_key: Kraken private key
            base_url: Kraken API base URL
            max_batch_size: Maximum requests per batch
            batch_timeout: Maximum time to wait for batch completion
            emergency_only: If True, only allow emergency operations
        """
        self.api_key = api_key
        self.private_key = private_key
        self.base_url = base_url
        self.max_batch_size = max_batch_size
        self.batch_timeout = batch_timeout
        self.emergency_only = emergency_only

        # Core REST client (will be initialized later)
        self._rest_client: Optional[KrakenRestClient] = None

        # Nonce coordination
        self.nonce_manager = get_nonce_manager()
        self._nonce_prefix = "strategic_rest"

        # Request batching
        self._pending_requests: List[BatchRequest] = []
        self._batch_lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None

        # Circuit breaker for REST protection
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,  # Fail fast
            recovery_timeout=60.0,  # Longer recovery
            success_threshold=2,
            max_recovery_attempts=3
        )
        self.circuit_breaker = CircuitBreaker(
            name="strategic_rest_client",
            config=cb_config
        )

        # Usage tracking
        self.stats = StrategicUsageStats()

        # Emergency endpoints (always allowed)
        self._emergency_endpoints = {
            'Balance',
            'TradeBalance',
            'OpenOrders',
            'SystemStatus',
            'CancelOrder',
            'CancelAllOrders'
        }

        # Historical endpoints (batch friendly)
        self._historical_endpoints = {
            'OHLC',
            'RecentTrades',
            'Ticker',
            'OrderBook',
            'AssetPairs',
            'AssetInfo'
        }

        # State
        self._initialized = False
        self._last_request_time = 0.0
        self._minimum_interval = 1.0  # Minimum seconds between requests

        logger.info(
            f"[STRATEGIC_REST] Initialized: emergency_only={emergency_only}, "
            f"max_batch_size={max_batch_size}"
        )

    async def initialize(self) -> None:
        """Initialize the strategic REST client."""
        if self._initialized:
            return

        # Create underlying REST client with conservative settings
        self._rest_client = KrakenRestClient(
            api_key=self.api_key,
            private_key=self.private_key,
            base_url=self.base_url,
            timeout=30.0,
            max_retries=2,  # Conservative retries
            enable_rate_limiting=True,
            enable_circuit_breaker=False  # We have our own
        )

        await self._rest_client.start()

        # Start batch processing task
        self._batch_task = asyncio.create_task(self._batch_processor())

        self._initialized = True
        logger.info("[STRATEGIC_REST] Client initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown the strategic REST client."""
        if not self._initialized:
            return

        # Cancel batch processor
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

        # Process any remaining requests
        await self._process_pending_batch()

        # Close REST client
        if self._rest_client:
            await self._rest_client.close()

        self._initialized = False
        self.stats.log_summary()
        logger.info("[STRATEGIC_REST] Client shutdown complete")

    async def _ensure_minimum_interval(self) -> None:
        """Ensure minimum interval between requests."""
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self._minimum_interval:
            wait_time = self._minimum_interval - elapsed
            logger.debug(f"[STRATEGIC_REST] Waiting {wait_time:.2f}s for minimum interval")
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()

    async def _execute_strategic_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Execute a strategic REST request with full protection.
        
        Args:
            endpoint: API endpoint name
            params: Request parameters
            priority: Request priority (emergency, normal, batch)
            
        Returns:
            API response data
        """
        if not self._initialized:
            await self.initialize()

        # Check if request is allowed
        if self.emergency_only and endpoint not in self._emergency_endpoints:
            raise ValueError(f"Emergency-only mode: {endpoint} not allowed")

        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            self.stats.nonce_conflicts += 1
            raise NetworkError(
                "Strategic REST circuit breaker is open",
                retry_after=60.0,
                endpoint=endpoint
            )

        # Ensure minimum interval
        await self._ensure_minimum_interval()

        # Track request
        self.stats.total_requests += 1
        if priority == "emergency":
            self.stats.emergency_requests += 1

        start_time = time.time()

        try:
            # Configure request for strategic usage
            config = RequestConfig(
                timeout=15.0 if priority == "emergency" else 30.0,
                max_retries=1 if priority == "batch" else 2,
                priority=priority,
                validate_response=True
            )

            # Execute through circuit breaker
            response = await self.circuit_breaker.execute(
                self._rest_client._make_request,
                endpoint,
                params,
                config
            )

            # Record success
            response_time = time.time() - start_time
            logger.debug(
                f"[STRATEGIC_REST] Success: {endpoint} in {response_time:.2f}s"
            )

            return response

        except Exception as e:
            response_time = time.time() - start_time

            # Check for nonce conflicts
            if "nonce" in str(e).lower() or "invalid nonce" in str(e).lower():
                self.stats.nonce_conflicts += 1
                logger.warning(
                    f"[STRATEGIC_REST] Nonce conflict detected: {endpoint} - {e}"
                )

            logger.error(
                f"[STRATEGIC_REST] Failed: {endpoint} in {response_time:.2f}s - {e}"
            )
            raise

    # ====== EMERGENCY OPERATIONS ======

    async def emergency_balance_check(self) -> Dict[str, Any]:
        """
        Emergency balance check when WebSocket fails.
        
        Returns:
            Account balance data
        """
        logger.warning("[STRATEGIC_REST] Emergency balance check initiated")
        return await self._execute_strategic_request(
            'Balance',
            priority="emergency"
        )

    async def emergency_open_orders(self) -> Dict[str, Any]:
        """
        Emergency check of open orders.
        
        Returns:
            Open orders data
        """
        logger.warning("[STRATEGIC_REST] Emergency open orders check")
        return await self._execute_strategic_request(
            'OpenOrders',
            priority="emergency"
        )

    async def emergency_cancel_order(self, txid: str) -> Dict[str, Any]:
        """
        Emergency order cancellation.
        
        Args:
            txid: Transaction ID to cancel
            
        Returns:
            Cancellation response
        """
        logger.warning(f"[STRATEGIC_REST] Emergency cancel order: {txid}")
        return await self._execute_strategic_request(
            'CancelOrder',
            {'txid': txid},
            priority="emergency"
        )

    async def emergency_system_status(self) -> Dict[str, Any]:
        """
        Emergency system status check.
        
        Returns:
            System status data
        """
        return await self._execute_strategic_request(
            'SystemStatus',
            priority="emergency"
        )

    # ====== BATCH OPERATIONS ======

    async def add_to_batch(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        priority: int = 1,
        callback: Optional[callable] = None
    ) -> None:
        """
        Add request to batch queue.
        
        Args:
            endpoint: API endpoint name
            params: Request parameters
            priority: Request priority (higher = more important)
            callback: Optional callback for result
        """
        if endpoint not in self._historical_endpoints:
            logger.warning(
                f"[STRATEGIC_REST] Endpoint {endpoint} not recommended for batching"
            )

        async with self._batch_lock:
            request = BatchRequest(
                endpoint=endpoint,
                params=params or {},
                priority=priority,
                callback=callback
            )
            self._pending_requests.append(request)

            logger.debug(f"[STRATEGIC_REST] Added to batch: {endpoint}")

    async def _batch_processor(self) -> None:
        """Background task to process batched requests."""
        while True:
            try:
                # Wait for batch timeout or max size
                await asyncio.sleep(self.batch_timeout)

                async with self._batch_lock:
                    if self._pending_requests:
                        await self._process_pending_batch()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[STRATEGIC_REST] Batch processor error: {e}")
                await asyncio.sleep(1.0)

    async def _process_pending_batch(self) -> None:
        """Process all pending batch requests."""
        if not self._pending_requests:
            return

        # Sort by priority (highest first)
        self._pending_requests.sort(key=lambda r: r.priority, reverse=True)

        # Process in batches
        while self._pending_requests:
            batch = self._pending_requests[:self.max_batch_size]
            self._pending_requests = self._pending_requests[self.max_batch_size:]

            await self._execute_batch(batch)

            # Small delay between batches
            if self._pending_requests:
                await asyncio.sleep(0.5)

    async def _execute_batch(self, batch: List[BatchRequest]) -> None:
        """Execute a batch of requests."""
        if not batch:
            return

        logger.info(f"[STRATEGIC_REST] Processing batch of {len(batch)} requests")
        self.stats.batched_requests += len(batch)

        # Execute requests with minimal delay
        results = []
        for request in batch:
            try:
                result = await self._execute_strategic_request(
                    request.endpoint,
                    request.params,
                    priority="batch"
                )
                results.append((request, result, None))

                # Call callback if provided
                if request.callback:
                    try:
                        await request.callback(result)
                    except Exception as e:
                        logger.error(f"[STRATEGIC_REST] Callback error: {e}")

                # Small delay between batch requests
                await asyncio.sleep(0.1)

            except Exception as e:
                results.append((request, None, e))
                logger.error(f"[STRATEGIC_REST] Batch request failed: {request.endpoint} - {e}")

        logger.info(f"[STRATEGIC_REST] Batch complete: {len(results)} processed")

    # ====== HISTORICAL DATA OPERATIONS ======

    async def batch_historical_query(
        self,
        pairs: List[str],
        timeframe: int = 1,
        max_age_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Batch query for historical OHLC data.
        
        Args:
            pairs: List of trading pairs
            timeframe: Timeframe in minutes
            max_age_hours: Maximum age of data to fetch
            
        Returns:
            Combined historical data
        """
        since_timestamp = int((datetime.now() - timedelta(hours=max_age_hours)).timestamp())

        results = {}

        # Add all pairs to batch
        for pair in pairs:
            await self.add_to_batch(
                'OHLC',
                {
                    'pair': pair,
                    'interval': timeframe,
                    'since': since_timestamp
                },
                priority=2
            )

        # Process batch immediately
        async with self._batch_lock:
            await self._process_pending_batch()

        self.stats.historical_requests += len(pairs)
        logger.info(f"[STRATEGIC_REST] Historical data queued for {len(pairs)} pairs")

        return results

    async def get_ticker_snapshot(self, pairs: List[str]) -> Dict[str, Any]:
        """
        Get ticker snapshots for multiple pairs.
        
        Args:
            pairs: List of trading pairs
            
        Returns:
            Ticker data for all pairs
        """
        # Batch all ticker requests
        for pair in pairs:
            await self.add_to_batch(
                'Ticker',
                {'pair': pair},
                priority=3
            )

        # Process immediately
        async with self._batch_lock:
            await self._process_pending_batch()

        logger.info(f"[STRATEGIC_REST] Ticker snapshots queued for {len(pairs)} pairs")
        return {}

    # ====== VALIDATION OPERATIONS ======

    async def validate_order_book(self, pair: str, count: int = 10) -> Dict[str, Any]:
        """
        Validate order book data against WebSocket.
        
        Args:
            pair: Trading pair
            count: Number of levels to fetch
            
        Returns:
            Order book data
        """
        self.stats.validation_requests += 1
        return await self._execute_strategic_request(
            'OrderBook',
            {'pair': pair, 'count': count},
            priority="normal"
        )

    async def validate_balance_snapshot(self) -> Dict[str, Any]:
        """
        Validate balance against WebSocket data.
        
        Returns:
            Balance validation data
        """
        self.stats.validation_requests += 1
        return await self._execute_strategic_request(
            'Balance',
            priority="normal"
        )

    # ====== STATUS AND MONITORING ======

    def get_strategic_stats(self) -> Dict[str, Any]:
        """Get strategic REST usage statistics."""
        return {
            'initialized': self._initialized,
            'emergency_only': self.emergency_only,
            'circuit_breaker_status': self.circuit_breaker.get_status(),
            'pending_batch_size': len(self._pending_requests),
            'stats': {
                'total_requests': self.stats.total_requests,
                'batched_requests': self.stats.batched_requests,
                'emergency_requests': self.stats.emergency_requests,
                'historical_requests': self.stats.historical_requests,
                'validation_requests': self.stats.validation_requests,
                'nonce_conflicts': self.stats.nonce_conflicts,
                'websocket_fallbacks': self.stats.websocket_fallbacks
            },
            'last_request_time': self._last_request_time,
            'minimum_interval': self._minimum_interval
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform strategic REST health check.
        
        Returns:
            Health status
        """
        health = {
            'timestamp': time.time(),
            'status': 'healthy',
            'checks': {}
        }

        # Check circuit breaker
        cb_status = self.circuit_breaker.get_status()
        health['checks']['circuit_breaker'] = {
            'status': 'healthy' if cb_status['can_execute'] else 'degraded',
            'state': cb_status['state']
        }

        # Check underlying client
        if self._rest_client:
            try:
                client_health = await self._rest_client.health_check()
                health['checks']['underlying_client'] = client_health
            except Exception as e:
                health['checks']['underlying_client'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health['status'] = 'degraded'

        # Check batch processing
        health['checks']['batch_processor'] = {
            'status': 'healthy' if self._batch_task and not self._batch_task.done() else 'degraded',
            'pending_requests': len(self._pending_requests)
        }

        return health

    def set_emergency_mode(self, enabled: bool) -> None:
        """
        Enable or disable emergency-only mode.
        
        Args:
            enabled: True to enable emergency-only mode
        """
        self.emergency_only = enabled
        logger.info(f"[STRATEGIC_REST] Emergency-only mode: {enabled}")

    def set_minimum_interval(self, interval: float) -> None:
        """
        Set minimum interval between requests.
        
        Args:
            interval: Minimum seconds between requests
        """
        self._minimum_interval = max(0.1, interval)
        logger.info(f"[STRATEGIC_REST] Minimum interval set to {self._minimum_interval}s")


# ====== INTEGRATION HELPERS ======

class RestWebSocketCoordinator:
    """Coordinates between REST and WebSocket to minimize conflicts."""

    def __init__(self, strategic_client: StrategicRestClient):
        """
        Initialize coordinator.
        
        Args:
            strategic_client: Strategic REST client instance
        """
        self.strategic_client = strategic_client
        self._websocket_active = True
        self._last_websocket_data = time.time()

    def websocket_status_update(self, active: bool) -> None:
        """
        Update WebSocket status.
        
        Args:
            active: True if WebSocket is active and receiving data
        """
        self._websocket_active = active
        if active:
            self._last_websocket_data = time.time()
            # Disable emergency mode when WebSocket is healthy
            self.strategic_client.set_emergency_mode(False)
        else:
            # Enable emergency mode when WebSocket fails
            self.strategic_client.set_emergency_mode(True)
            logger.warning("[REST_WS_COORDINATOR] WebSocket inactive, enabling emergency mode")

    def should_use_rest_fallback(self, data_age_seconds: float = 10.0) -> bool:
        """
        Determine if REST fallback should be used.
        
        Args:
            data_age_seconds: Maximum age of WebSocket data before fallback
            
        Returns:
            True if REST fallback should be used
        """
        if not self._websocket_active:
            return True

        data_age = time.time() - self._last_websocket_data
        return data_age > data_age_seconds
