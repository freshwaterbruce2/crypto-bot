"""
Hybrid Portfolio Manager
========================

Intelligent portfolio management system that uses WebSocket as the primary source (90% usage)
with REST API fallback (10% usage - only for recovery). Provides seamless balance access
while avoiding nonce issues and ensuring high availability.

Features:
- WebSocket-primary architecture (90% usage rate)
- REST API fallback only when WebSocket fails (10% usage)
- Intelligent source selection based on data freshness
- Circuit breaker protection for REST API
- Automatic failover and recovery
- Balance aggregation across multiple sources
- Real-time balance validation and consistency checks
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union, Tuple
from decimal import Decimal
from threading import RLock
from enum import Enum
import statistics

from .websocket_balance_stream import WebSocketBalanceStream, BalanceUpdate
from ..utils.decimal_precision_fix import safe_decimal, safe_float, is_zero
from ..circuit_breaker.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Data source types for balance information"""
    WEBSOCKET_PRIMARY = "websocket_primary"
    REST_FALLBACK = "rest_fallback"
    CACHE = "cache"
    HYBRID = "hybrid"


class SourceHealth(Enum):
    """Health status of data sources"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class SourceMetrics:
    """Metrics for tracking data source performance"""
    requests_total: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    avg_response_time: float = 0.0
    last_success_time: float = 0.0
    last_failure_time: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    health_status: SourceHealth = SourceHealth.HEALTHY
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.requests_total == 0:
            return 100.0
        return (self.requests_successful / self.requests_total) * 100.0
    
    @property
    def is_healthy(self) -> bool:
        """Check if source is healthy"""
        return self.health_status in [SourceHealth.HEALTHY, SourceHealth.RECOVERING]


@dataclass
class HybridPortfolioConfig:
    """Configuration for hybrid portfolio manager"""
    # Source preferences
    websocket_primary_ratio: float = 0.9  # 90% WebSocket usage
    rest_fallback_ratio: float = 0.1      # 10% REST fallback
    
    # Health monitoring
    health_check_interval: float = 30.0   # Health check every 30 seconds
    source_timeout: float = 5.0           # Source timeout in seconds
    max_consecutive_failures: int = 3     # Max failures before marking unhealthy
    recovery_threshold: int = 2           # Successful requests to mark as recovering
    
    # Data freshness
    websocket_max_age: float = 60.0       # Max age for WebSocket data (seconds)
    rest_max_age: float = 300.0           # Max age for REST data (seconds)
    cache_max_age: float = 30.0           # Max age for cached data (seconds)
    
    # Circuit breaker for REST API
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 60.0
    
    # Balance validation
    enable_balance_validation: bool = True
    balance_consistency_threshold: float = 0.001  # 0.1% threshold for balance consistency
    
    # Aggregation settings
    enable_balance_aggregation: bool = True
    usdt_variants: List[str] = None
    
    def __post_init__(self):
        if self.usdt_variants is None:
            self.usdt_variants = ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S', 'USDT.F', 'USDT.B']


class HybridPortfolioManager:
    """
    Hybrid portfolio management system with intelligent source selection
    """
    
    def __init__(self,
                 websocket_stream: WebSocketBalanceStream,
                 rest_client,
                 config: Optional[HybridPortfolioConfig] = None):
        """
        Initialize hybrid portfolio manager
        
        Args:
            websocket_stream: WebSocket balance streaming component
            rest_client: REST API client for fallback
            config: Configuration object
        """
        self.config = config or HybridPortfolioConfig()
        self.websocket_stream = websocket_stream
        self.rest_client = rest_client
        
        # Source metrics tracking
        self.source_metrics = {
            DataSource.WEBSOCKET_PRIMARY: SourceMetrics(),
            DataSource.REST_FALLBACK: SourceMetrics()
        }
        
        # Circuit breaker for REST API
        self.circuit_breaker = None
        if self.config.enable_circuit_breaker and rest_client:
            cb_config = CircuitBreakerConfig(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                recovery_timeout=self.config.circuit_breaker_recovery_timeout,
                timeout=self.config.source_timeout
            )
            self.circuit_breaker = CircuitBreaker("hybrid_portfolio_rest", cb_config)
        
        # State management
        self._lock = RLock()
        self._async_lock = asyncio.Lock()
        self._running = False
        
        # Cache for balance data
        self._balance_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # Background tasks
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._metrics_update_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'websocket_requests': 0,
            'rest_requests': 0,
            'cache_hits': 0,
            'fallback_activations': 0,
            'source_switches': 0,
            'validation_failures': 0,
            'aggregated_usdt_queries': 0,
            'last_request_time': 0.0,
            'uptime_start': 0.0
        }
        
        logger.info("[HYBRID_PORTFOLIO] Initialized with {:.0%} WebSocket / {:.0%} REST split".format(
            self.config.websocket_primary_ratio, self.config.rest_fallback_ratio))
    
    async def start(self) -> bool:
        """Start the hybrid portfolio manager"""
        if self._running:
            logger.warning("[HYBRID_PORTFOLIO] Already running")
            return True
        
        try:
            async with self._async_lock:
                logger.info("[HYBRID_PORTFOLIO] Starting hybrid portfolio manager...")
                
                self._running = True
                self.stats['uptime_start'] = time.time()
                
                # Ensure WebSocket stream is started
                if self.websocket_stream and (not hasattr(self.websocket_stream, '_running') or not self.websocket_stream._running):
                    logger.info("[HYBRID_PORTFOLIO] Starting WebSocket balance stream...")
                    if not await self.websocket_stream.start():
                        logger.error("[HYBRID_PORTFOLIO] Failed to start WebSocket stream")
                        return False
                
                # Register callbacks with WebSocket stream
                if self.websocket_stream:
                    self.websocket_stream.register_balance_callback(self._handle_websocket_balance_update)
                    self.websocket_stream.register_state_callback(self._handle_websocket_state_change)
                    self.websocket_stream.register_error_callback(self._handle_websocket_error)
                
                # Start background tasks
                await self._start_background_tasks()
                
                # Perform initial health check
                await self._update_source_health()
                
                logger.info("[HYBRID_PORTFOLIO] Started successfully - intelligent balance access active")
                return True
                
        except Exception as e:
            logger.error(f"[HYBRID_PORTFOLIO] Start failed: {e}")
            self._running = False
            return False
    
    async def stop(self):
        """Stop the hybrid portfolio manager"""
        if not self._running:
            return
        
        logger.info("[HYBRID_PORTFOLIO] Stopping hybrid portfolio manager...")
        
        self._running = False
        
        # Stop background tasks
        await self._stop_background_tasks()
        
        # Stop WebSocket stream if managed by us
        if self.websocket_stream and hasattr(self.websocket_stream, '_running') and self.websocket_stream._running:
            await self.websocket_stream.stop()
        
        logger.info("[HYBRID_PORTFOLIO] Stopped")
    
    async def get_balance(self, asset: str, force_source: Optional[DataSource] = None) -> Optional[Dict[str, Any]]:
        """
        Get balance for specific asset using intelligent source selection
        
        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')
            force_source: Force specific source (optional)
            
        Returns:
            Balance dictionary or None if not found
        """
        start_time = time.time()
        self.stats['total_requests'] += 1
        self.stats['last_request_time'] = start_time
        
        try:
            # Determine optimal data source
            selected_source = force_source or await self._select_optimal_source(asset)
            
            balance_data = None
            
            # Try primary source first
            if selected_source == DataSource.WEBSOCKET_PRIMARY:
                balance_data = await self._get_balance_from_websocket(asset, start_time)
                
                # Fallback to REST if WebSocket fails
                if balance_data is None and self._should_fallback_to_rest():
                    logger.debug(f"[HYBRID_PORTFOLIO] WebSocket failed for {asset}, falling back to REST")
                    balance_data = await self._get_balance_from_rest(asset, start_time)
                    if balance_data:
                        self.stats['fallback_activations'] += 1
            
            elif selected_source == DataSource.REST_FALLBACK:
                balance_data = await self._get_balance_from_rest(asset, start_time)
                
                # Try WebSocket as secondary if REST fails
                if balance_data is None:
                    logger.debug(f"[HYBRID_PORTFOLIO] REST failed for {asset}, trying WebSocket")
                    balance_data = await self._get_balance_from_websocket(asset, start_time)
            
            # Try cache as last resort
            if balance_data is None:
                balance_data = self._get_balance_from_cache(asset)
                if balance_data:
                    self.stats['cache_hits'] += 1
            
            # Validate balance data if enabled
            if balance_data and self.config.enable_balance_validation:
                if not self._validate_balance_data(asset, balance_data):
                    logger.warning(f"[HYBRID_PORTFOLIO] Balance validation failed for {asset}")
                    self.stats['validation_failures'] += 1
            
            # Update cache
            if balance_data:
                self._update_balance_cache(asset, balance_data)
            
            return balance_data
            
        except Exception as e:
            logger.error(f"[HYBRID_PORTFOLIO] Error getting balance for {asset}: {e}")
            return None
    
    async def get_all_balances(self, force_source: Optional[DataSource] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get all balances using intelligent source selection
        
        Args:
            force_source: Force specific source (optional)
            
        Returns:
            Dictionary of all balances keyed by asset
        """
        start_time = time.time()
        self.stats['total_requests'] += 1
        self.stats['last_request_time'] = start_time
        
        try:
            # Determine optimal data source
            selected_source = force_source or await self._select_optimal_source()
            
            all_balances = {}
            
            # Try primary source first
            if selected_source == DataSource.WEBSOCKET_PRIMARY:
                all_balances = await self._get_all_balances_from_websocket(start_time)
                
                # Fallback to REST if WebSocket fails
                if not all_balances and self._should_fallback_to_rest():
                    logger.info("[HYBRID_PORTFOLIO] WebSocket failed for all balances, falling back to REST")
                    all_balances = await self._get_all_balances_from_rest(start_time)
                    if all_balances:
                        self.stats['fallback_activations'] += 1
            
            elif selected_source == DataSource.REST_FALLBACK:
                all_balances = await self._get_all_balances_from_rest(start_time)
                
                # Try WebSocket as secondary if REST fails
                if not all_balances:
                    logger.info("[HYBRID_PORTFOLIO] REST failed for all balances, trying WebSocket")
                    all_balances = await self._get_all_balances_from_websocket(start_time)
            
            # Merge with cache data if needed
            if all_balances:
                all_balances = self._merge_with_cache(all_balances)
            else:
                # Use cache as last resort
                all_balances = self._get_all_balances_from_cache()
                if all_balances:
                    self.stats['cache_hits'] += len(all_balances)
            
            # Update cache
            for asset, balance_data in all_balances.items():
                self._update_balance_cache(asset, balance_data)
            
            return all_balances
            
        except Exception as e:
            logger.error(f"[HYBRID_PORTFOLIO] Error getting all balances: {e}")
            return {}
    
    async def get_usdt_total(self) -> float:
        """
        Get total USDT across all USDT variants with intelligent aggregation
        
        Returns:
            Total USDT amount
        """
        self.stats['aggregated_usdt_queries'] += 1
        
        try:
            # Try WebSocket first for real-time data
            websocket_total = self.websocket_stream.get_usdt_total() if self.websocket_stream else 0
            if websocket_total > 0:
                logger.debug(f"[HYBRID_PORTFOLIO] USDT total from WebSocket: ${websocket_total:.2f}")
                return websocket_total
            
            # Fallback to getting individual balances
            total_usdt = Decimal('0')
            usdt_sources = []
            
            for variant in self.config.usdt_variants:
                balance_data = await self.get_balance(variant)
                if balance_data and balance_data.get('free', 0) > 0:
                    amount = safe_decimal(balance_data['free'])
                    total_usdt += amount
                    usdt_sources.append(f"{variant}=${float(amount):.2f}")
            
            if usdt_sources:
                logger.info(f"[HYBRID_PORTFOLIO] USDT total aggregated: ${float(total_usdt):.2f} "
                           f"from [{', '.join(usdt_sources)}]")
            
            return float(total_usdt)
            
        except Exception as e:
            logger.error(f"[HYBRID_PORTFOLIO] Error getting USDT total: {e}")
            return 0.0
    
    async def _select_optimal_source(self, asset: Optional[str] = None) -> DataSource:
        """
        Select optimal data source based on health, preferences, and data freshness
        
        Args:
            asset: Specific asset to check (optional)
            
        Returns:
            Optimal data source
        """
        websocket_metrics = self.source_metrics[DataSource.WEBSOCKET_PRIMARY]
        rest_metrics = self.source_metrics[DataSource.REST_FALLBACK]
        
        # Check WebSocket health and data freshness
        websocket_healthy = websocket_metrics.is_healthy
        websocket_fresh = True
        
        if asset:
            # Check specific asset data freshness
            ws_balance = self.websocket_stream.get_balance(asset) if self.websocket_stream else None
            if ws_balance:
                age = time.time() - ws_balance.get('timestamp', 0)
                websocket_fresh = age <= self.config.websocket_max_age
        
        # Check REST API health (considering circuit breaker)
        rest_healthy = rest_metrics.is_healthy
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            rest_healthy = False
        
        # Decision logic based on health and preferences
        if websocket_healthy and websocket_fresh:
            # WebSocket is healthy and fresh - use it according to configured ratio
            if self._should_use_websocket():
                return DataSource.WEBSOCKET_PRIMARY
            elif rest_healthy:
                return DataSource.REST_FALLBACK
            else:
                return DataSource.WEBSOCKET_PRIMARY  # Fallback to WebSocket if REST unhealthy
        
        elif rest_healthy:
            # WebSocket unhealthy but REST healthy - use REST
            return DataSource.REST_FALLBACK
        
        else:
            # Both sources have issues - prefer WebSocket as it's more reliable
            return DataSource.WEBSOCKET_PRIMARY
    
    def _should_use_websocket(self) -> bool:
        """Determine if WebSocket should be used based on configured ratio"""
        import random
        return random.random() < self.config.websocket_primary_ratio
    
    def _should_fallback_to_rest(self) -> bool:
        """Check if fallback to REST is appropriate"""
        rest_metrics = self.source_metrics[DataSource.REST_FALLBACK]
        
        # Don't fallback if REST is unhealthy
        if not rest_metrics.is_healthy:
            return False
        
        # Don't fallback if circuit breaker is open
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            return False
        
        return True
    
    async def _get_balance_from_websocket(self, asset: str, start_time: float) -> Optional[Dict[str, Any]]:
        """Get balance from WebSocket stream"""
        try:
            balance_data = self.websocket_stream.get_balance(asset) if self.websocket_stream else None
            
            if balance_data:
                self._record_source_success(DataSource.WEBSOCKET_PRIMARY, start_time)
                self.stats['websocket_requests'] += 1
                return balance_data
            else:
                self._record_source_failure(DataSource.WEBSOCKET_PRIMARY, start_time, "no_data")
                return None
                
        except Exception as e:
            self._record_source_failure(DataSource.WEBSOCKET_PRIMARY, start_time, str(e))
            logger.debug(f"[HYBRID_PORTFOLIO] WebSocket balance request failed: {e}")
            return None
    
    async def _get_all_balances_from_websocket(self, start_time: float) -> Dict[str, Dict[str, Any]]:
        """Get all balances from WebSocket stream"""
        try:
            all_balances = self.websocket_stream.get_all_balances() if self.websocket_stream else {}
            
            if all_balances:
                self._record_source_success(DataSource.WEBSOCKET_PRIMARY, start_time)
                self.stats['websocket_requests'] += 1
                return all_balances
            else:
                self._record_source_failure(DataSource.WEBSOCKET_PRIMARY, start_time, "no_data")
                return {}
                
        except Exception as e:
            self._record_source_failure(DataSource.WEBSOCKET_PRIMARY, start_time, str(e))
            logger.debug(f"[HYBRID_PORTFOLIO] WebSocket all balances request failed: {e}")
            return {}
    
    async def _get_balance_from_rest(self, asset: str, start_time: float) -> Optional[Dict[str, Any]]:
        """Get balance from REST API with circuit breaker protection"""
        try:
            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                logger.debug("[HYBRID_PORTFOLIO] Circuit breaker open, skipping REST request")
                return None
            
            # Make REST API call
            response = await asyncio.wait_for(
                self.rest_client.get_account_balance(),
                timeout=self.config.source_timeout
            )
            
            if response and 'result' in response:
                balances = response['result']
                
                if asset in balances:
                    balance_value = safe_decimal(balances[asset])
                    balance_data = {
                        'asset': asset,
                        'balance': float(balance_value),
                        'hold_trade': 0.0,  # REST doesn't provide hold info
                        'free': float(balance_value),
                        'total': float(balance_value),
                        'source': 'rest_api',
                        'timestamp': time.time()
                    }
                    
                    self._record_source_success(DataSource.REST_FALLBACK, start_time)
                    self.stats['rest_requests'] += 1
                    
                    # Record circuit breaker success
                    if self.circuit_breaker:
                        self.circuit_breaker._record_success(time.time() - start_time)
                    
                    return balance_data
            
            self._record_source_failure(DataSource.REST_FALLBACK, start_time, "asset_not_found")
            return None
            
        except asyncio.TimeoutError:
            error_msg = "timeout"
            self._record_source_failure(DataSource.REST_FALLBACK, start_time, error_msg)
            if self.circuit_breaker:
                self.circuit_breaker._record_failure(Exception(error_msg), time.time() - start_time)
            return None
            
        except Exception as e:
            self._record_source_failure(DataSource.REST_FALLBACK, start_time, str(e))
            if self.circuit_breaker:
                self.circuit_breaker._record_failure(e, time.time() - start_time)
            logger.debug(f"[HYBRID_PORTFOLIO] REST balance request failed: {e}")
            return None
    
    async def _get_all_balances_from_rest(self, start_time: float) -> Dict[str, Dict[str, Any]]:
        """Get all balances from REST API with circuit breaker protection"""
        try:
            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                logger.debug("[HYBRID_PORTFOLIO] Circuit breaker open, skipping REST request")
                return {}
            
            # Make REST API call
            response = await asyncio.wait_for(
                self.rest_client.get_account_balance(),
                timeout=self.config.source_timeout
            )
            
            if response and 'result' in response:
                raw_balances = response['result']
                processed_balances = {}
                
                for asset, balance_value in raw_balances.items():
                    balance_decimal = safe_decimal(balance_value)
                    
                    # Skip zero balances
                    if balance_decimal <= 0:
                        continue
                    
                    processed_balances[asset] = {
                        'asset': asset,
                        'balance': float(balance_decimal),
                        'hold_trade': 0.0,  # REST doesn't provide hold info
                        'free': float(balance_decimal),
                        'total': float(balance_decimal),
                        'source': 'rest_api',
                        'timestamp': time.time()
                    }
                
                self._record_source_success(DataSource.REST_FALLBACK, start_time)
                self.stats['rest_requests'] += 1
                
                # Record circuit breaker success
                if self.circuit_breaker:
                    self.circuit_breaker._record_success(time.time() - start_time)
                
                return processed_balances
            
            self._record_source_failure(DataSource.REST_FALLBACK, start_time, "no_result")
            return {}
            
        except asyncio.TimeoutError:
            error_msg = "timeout"
            self._record_source_failure(DataSource.REST_FALLBACK, start_time, error_msg)
            if self.circuit_breaker:
                self.circuit_breaker._record_failure(Exception(error_msg), time.time() - start_time)
            return {}
            
        except Exception as e:
            self._record_source_failure(DataSource.REST_FALLBACK, start_time, str(e))
            if self.circuit_breaker:
                self.circuit_breaker._record_failure(e, time.time() - start_time)
            logger.debug(f"[HYBRID_PORTFOLIO] REST all balances request failed: {e}")
            return {}
    
    def _get_balance_from_cache(self, asset: str) -> Optional[Dict[str, Any]]:
        """Get balance from cache if fresh enough"""
        with self._lock:
            if asset in self._balance_cache:
                cache_time = self._cache_timestamps.get(asset, 0)
                age = time.time() - cache_time
                
                if age <= self.config.cache_max_age:
                    cache_data = self._balance_cache[asset].copy()
                    cache_data['source'] = 'cache'
                    cache_data['cache_age'] = age
                    return cache_data
        
        return None
    
    def _get_all_balances_from_cache(self) -> Dict[str, Dict[str, Any]]:
        """Get all balances from cache if fresh enough"""
        cached_balances = {}
        current_time = time.time()
        
        with self._lock:
            for asset, balance_data in self._balance_cache.items():
                cache_time = self._cache_timestamps.get(asset, 0)
                age = current_time - cache_time
                
                if age <= self.config.cache_max_age:
                    cache_data = balance_data.copy()
                    cache_data['source'] = 'cache'
                    cache_data['cache_age'] = age
                    cached_balances[asset] = cache_data
        
        return cached_balances
    
    def _update_balance_cache(self, asset: str, balance_data: Dict[str, Any]):
        """Update balance cache"""
        with self._lock:
            self._balance_cache[asset] = balance_data.copy()
            self._cache_timestamps[asset] = time.time()
    
    def _merge_with_cache(self, fresh_balances: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Merge fresh balances with cache data for complete picture"""
        if not self.config.enable_balance_aggregation:
            return fresh_balances
        
        merged_balances = fresh_balances.copy()
        cached_balances = self._get_all_balances_from_cache()
        
        # Add cached balances for assets not in fresh data
        for asset, cached_data in cached_balances.items():
            if asset not in merged_balances:
                merged_balances[asset] = cached_data
        
        return merged_balances
    
    def _validate_balance_data(self, asset: str, balance_data: Dict[str, Any]) -> bool:
        """Validate balance data for consistency"""
        try:
            # Basic structure validation
            required_fields = ['asset', 'balance', 'free', 'timestamp']
            for field in required_fields:
                if field not in balance_data:
                    return False
            
            # Value validation
            balance = safe_decimal(balance_data.get('balance', 0))
            free = safe_decimal(balance_data.get('free', 0))
            hold_trade = safe_decimal(balance_data.get('hold_trade', 0))
            
            # Basic consistency checks
            if balance < 0 or free < 0 or hold_trade < 0:
                return False
            
            if abs(float(balance - (free + hold_trade))) > self.config.balance_consistency_threshold:
                return False
            
            # Timestamp validation
            timestamp = balance_data.get('timestamp', 0)
            age = time.time() - timestamp
            if age < 0 or age > 3600:  # Future timestamp or older than 1 hour
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"[HYBRID_PORTFOLIO] Balance validation error for {asset}: {e}")
            return False
    
    def _record_source_success(self, source: DataSource, start_time: float):
        """Record successful request for source metrics"""
        response_time = time.time() - start_time
        metrics = self.source_metrics[source]
        
        metrics.requests_total += 1
        metrics.requests_successful += 1
        metrics.last_success_time = time.time()
        metrics.consecutive_successes += 1
        metrics.consecutive_failures = 0
        
        # Update average response time
        if metrics.avg_response_time == 0:
            metrics.avg_response_time = response_time
        else:
            metrics.avg_response_time = (metrics.avg_response_time + response_time) / 2
        
        # Update health status
        if metrics.consecutive_successes >= self.config.recovery_threshold:
            if metrics.health_status == SourceHealth.FAILED:
                metrics.health_status = SourceHealth.RECOVERING
            elif metrics.health_status == SourceHealth.RECOVERING:
                metrics.health_status = SourceHealth.HEALTHY
    
    def _record_source_failure(self, source: DataSource, start_time: float, error: str):
        """Record failed request for source metrics"""
        metrics = self.source_metrics[source]
        
        metrics.requests_total += 1
        metrics.requests_failed += 1
        metrics.last_failure_time = time.time()
        metrics.consecutive_failures += 1
        metrics.consecutive_successes = 0
        
        # Update health status
        if metrics.consecutive_failures >= self.config.max_consecutive_failures:
            metrics.health_status = SourceHealth.FAILED
        elif metrics.consecutive_failures > 1:
            metrics.health_status = SourceHealth.DEGRADED
    
    async def _start_background_tasks(self):
        """Start background monitoring tasks"""
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        self._metrics_update_task = asyncio.create_task(self._metrics_update_loop())
        
        logger.info("[HYBRID_PORTFOLIO] Background tasks started")
    
    async def _stop_background_tasks(self):
        """Stop background tasks"""
        tasks = [self._health_monitor_task, self._metrics_update_task]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("[HYBRID_PORTFOLIO] Background tasks stopped")
    
    async def _health_monitor_loop(self):
        """Monitor source health"""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if not self._running:
                    break
                
                await self._update_source_health()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HYBRID_PORTFOLIO] Health monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _metrics_update_loop(self):
        """Update performance metrics"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                if not self._running:
                    break
                
                await self._log_performance_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HYBRID_PORTFOLIO] Metrics update error: {e}")
                await asyncio.sleep(60)
    
    async def _update_source_health(self):
        """Update health status of all sources"""
        try:
            # Check WebSocket stream health
            ws_status = self.websocket_stream.get_status() if self.websocket_stream else {'healthy': False}
            ws_metrics = self.source_metrics[DataSource.WEBSOCKET_PRIMARY]
            
            if ws_status['running'] and ws_status['subscribed']:
                if ws_status['last_websocket_message'] < 120:  # Less than 2 minutes
                    ws_metrics.health_status = SourceHealth.HEALTHY
                else:
                    ws_metrics.health_status = SourceHealth.DEGRADED
            else:
                ws_metrics.health_status = SourceHealth.FAILED
            
            # REST API health is updated through request metrics
            
            logger.debug("[HYBRID_PORTFOLIO] Source health updated - "
                        f"WebSocket: {ws_metrics.health_status.value}, "
                        f"REST: {self.source_metrics[DataSource.REST_FALLBACK].health_status.value}")
            
        except Exception as e:
            logger.error(f"[HYBRID_PORTFOLIO] Error updating source health: {e}")
    
    async def _log_performance_metrics(self):
        """Log performance metrics"""
        try:
            ws_metrics = self.source_metrics[DataSource.WEBSOCKET_PRIMARY]
            rest_metrics = self.source_metrics[DataSource.REST_FALLBACK]
            
            logger.info(f"[HYBRID_PORTFOLIO] Performance - "
                       f"Total requests: {self.stats['total_requests']}, "
                       f"WebSocket: {ws_metrics.success_rate:.1f}% ({ws_metrics.health_status.value}), "
                       f"REST: {rest_metrics.success_rate:.1f}% ({rest_metrics.health_status.value}), "
                       f"Fallback activations: {self.stats['fallback_activations']}")
            
        except Exception as e:
            logger.error(f"[HYBRID_PORTFOLIO] Error logging metrics: {e}")
    
    # WebSocket stream event handlers
    
    async def _handle_websocket_balance_update(self, balance_update: BalanceUpdate):
        """Handle balance updates from WebSocket stream"""
        # Update cache with fresh data
        balance_data = balance_update.to_dict()
        self._update_balance_cache(balance_update.asset, balance_data)
    
    async def _handle_websocket_state_change(self, new_state):
        """Handle WebSocket state changes"""
        logger.debug(f"[HYBRID_PORTFOLIO] WebSocket state changed to: {new_state.value}")
        
        # Update source health based on state
        ws_metrics = self.source_metrics[DataSource.WEBSOCKET_PRIMARY]
        
        if new_state.value in ['subscribed', 'authenticated']:
            ws_metrics.health_status = SourceHealth.HEALTHY
        elif new_state.value in ['connected', 'connecting']:
            ws_metrics.health_status = SourceHealth.RECOVERING
        else:
            ws_metrics.health_status = SourceHealth.FAILED
    
    async def _handle_websocket_error(self, error: Exception):
        """Handle WebSocket errors"""
        logger.warning(f"[HYBRID_PORTFOLIO] WebSocket error: {error}")
        self.source_metrics[DataSource.WEBSOCKET_PRIMARY].health_status = SourceHealth.FAILED
    
    # Public status and monitoring methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information"""
        ws_metrics = self.source_metrics[DataSource.WEBSOCKET_PRIMARY]
        rest_metrics = self.source_metrics[DataSource.REST_FALLBACK]
        
        uptime = time.time() - self.stats['uptime_start'] if self.stats['uptime_start'] > 0 else 0
        
        return {
            'running': self._running,
            'uptime_seconds': uptime,
            'websocket_stream': self.websocket_stream.get_status() if self.websocket_stream else {'status': 'not_available'},
            'source_metrics': {
                'websocket': {
                    'health': ws_metrics.health_status.value,
                    'success_rate': ws_metrics.success_rate,
                    'avg_response_time': ws_metrics.avg_response_time,
                    'consecutive_failures': ws_metrics.consecutive_failures,
                    'last_success': ws_metrics.last_success_time
                },
                'rest': {
                    'health': rest_metrics.health_status.value,
                    'success_rate': rest_metrics.success_rate,
                    'avg_response_time': rest_metrics.avg_response_time,
                    'consecutive_failures': rest_metrics.consecutive_failures,
                    'last_success': rest_metrics.last_success_time,
                    'circuit_breaker_open': (self.circuit_breaker.get_status()['state'] == 'OPEN' 
                                            if self.circuit_breaker else False)
                }
            },
            'cache': {
                'entries': len(self._balance_cache),
                'hit_rate': self.stats['cache_hits'] / max(self.stats['total_requests'], 1) * 100
            },
            'statistics': dict(self.stats),
            'configuration': {
                'websocket_ratio': self.config.websocket_primary_ratio,
                'rest_ratio': self.config.rest_fallback_ratio,
                'balance_validation_enabled': self.config.enable_balance_validation,
                'circuit_breaker_enabled': self.config.enable_circuit_breaker
            }
        }
    
    # Context manager support
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()