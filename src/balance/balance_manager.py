"""
Unified Balance Manager System
=============================

Main balance management system that integrates WebSocket V2 streaming, REST API 
fallback, intelligent caching, validation, and history tracking. Provides a unified
interface for all balance operations in the crypto trading bot.

Features:
- Real-time balance streaming via WebSocket V2
- REST API fallback when WebSocket is unavailable
- Intelligent caching with TTL and LRU eviction
- Comprehensive balance validation
- Historical balance tracking and analysis
- Thread-safe operations for concurrent trading
- Circuit breaker integration for resilience
- Balance change notifications and callbacks
- Decimal precision for accurate financial calculations
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Any, Callable, Dict, List, Optional

from ..circuit_breaker.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ..utils.decimal_precision_fix import safe_decimal
from .balance_cache import BalanceCache
from .balance_history import BalanceHistory
from .balance_validator import BalanceValidationResult, BalanceValidator

logger = logging.getLogger(__name__)


class BalanceSource(Enum):
    """Balance data source types"""
    WEBSOCKET = "websocket"
    REST_API = "rest_api"
    CACHE = "cache"
    MANUAL = "manual"


@dataclass
class BalanceManagerConfig:
    """Configuration for balance manager"""
    # Cache settings
    cache_max_size: int = 1000
    cache_default_ttl: float = 300.0  # 5 minutes

    # History settings
    history_max_entries: int = 10000
    history_retention_hours: float = 24 * 7  # 1 week
    history_persistence_file: Optional[str] = None

    # Validation settings
    enable_validation: bool = True
    validation_on_cache: bool = True
    validation_on_update: bool = True

    # WebSocket settings
    websocket_timeout: float = 10.0
    websocket_retry_interval: float = 30.0

    # REST API fallback settings
    rest_api_timeout: float = 15.0
    rest_api_retry_attempts: int = 3

    # Circuit breaker settings
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 30.0

    # Update settings
    force_update_interval: float = 600.0  # 10 minutes
    balance_change_threshold: Decimal = safe_decimal("0.001")

    # Cleanup settings
    cleanup_interval: float = 300.0  # 5 minutes


class BalanceManager:
    """
    Unified balance management system
    """

    def __init__(self,
                 websocket_client=None,
                 rest_client=None,
                 config: Optional[BalanceManagerConfig] = None):
        """
        Initialize balance manager
        
        Args:
            websocket_client: WebSocket V2 client for real-time streaming
            rest_client: REST API client for fallback operations
            config: Balance manager configuration
        """
        self.config = config or BalanceManagerConfig()
        self.websocket_client = websocket_client
        self.rest_client = rest_client

        # Core components
        self.cache = BalanceCache(
            max_size=self.config.cache_max_size,
            default_ttl=self.config.cache_default_ttl
        )

        self.validator = BalanceValidator() if self.config.enable_validation else None

        self.history = BalanceHistory(
            max_entries_per_asset=self.config.history_max_entries,
            retention_hours=self.config.history_retention_hours,
            persistence_file=self.config.history_persistence_file
        )

        # Circuit breaker for REST API calls
        self.circuit_breaker = None
        if self.config.enable_circuit_breaker and rest_client:
            cb_config = CircuitBreakerConfig(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                recovery_timeout=self.config.circuit_breaker_recovery_timeout,
                timeout=self.config.rest_api_timeout
            )
            self.circuit_breaker = CircuitBreaker("balance_manager_rest", cb_config)

        # State management
        self._running = False
        self._initialized = False
        self._lock = RLock()
        self._async_lock = asyncio.Lock()

        # WebSocket state
        self._websocket_connected = False
        self._websocket_authenticated = False
        self._last_websocket_update = 0.0

        # Balance state
        self._last_full_refresh = 0.0
        self._balance_sources: Dict[str, BalanceSource] = {}

        # Background tasks
        self._websocket_monitor_task: Optional[asyncio.Task] = None
        self._force_update_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            'balance_update': [],
            'balance_change': [],
            'websocket_connected': [],
            'websocket_disconnected': [],
            'fallback_activated': [],
            'validation_failed': [],
            'error': []
        }

        # Statistics
        self._stats = {
            'websocket_updates': 0,
            'rest_api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_failures': 0,
            'fallback_activations': 0,
            'total_balance_requests': 0,
            'errors': 0
        }

        logger.info("[BALANCE_MANAGER] Initialized with WebSocket and REST API integration")

    async def initialize(self) -> bool:
        """
        Initialize the balance manager and all components
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            logger.warning("[BALANCE_MANAGER] Already initialized")
            return True

        try:
            async with self._async_lock:
                logger.info("[BALANCE_MANAGER] Starting initialization...")

                # Start core components
                await self.cache.start()
                await self.history.start()

                # Setup WebSocket integration if available
                if self.websocket_client:
                    await self._setup_websocket_integration()

                # Perform initial balance refresh
                initial_balances = await self._perform_initial_balance_refresh()

                # Start background tasks
                self._running = True
                await self._start_background_tasks()

                self._initialized = True

                logger.info(f"[BALANCE_MANAGER] Initialization complete. Loaded {len(initial_balances)} balances")
                return True

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Initialization failed: {e}")
            await self._cleanup_on_error()
            return False

    async def shutdown(self):
        """Shutdown the balance manager and cleanup resources"""
        if not self._running:
            return

        logger.info("[BALANCE_MANAGER] Shutting down...")

        self._running = False

        # Stop background tasks
        await self._stop_background_tasks()

        # Cleanup WebSocket integration
        if self.websocket_client:
            await self._cleanup_websocket_integration()

        # Stop core components
        await self.cache.stop()
        await self.history.stop()

        self._initialized = False

        logger.info("[BALANCE_MANAGER] Shutdown complete")

    async def get_balance(self, asset: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get balance for a specific asset
        
        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')
            force_refresh: Force refresh from API if True
            
        Returns:
            Balance dictionary or None if not found
        """
        if not self._initialized:
            raise RuntimeError("Balance manager not initialized")

        self._stats['total_balance_requests'] += 1

        try:
            # Try cache first unless force refresh requested
            if not force_refresh:
                cached_entry = await self.cache.get(asset)
                if cached_entry:
                    self._stats['cache_hits'] += 1
                    self._balance_sources[asset] = BalanceSource.CACHE

                    # Validate cached data if enabled
                    if self.config.validation_on_cache and self.validator:
                        validation = self.validator.validate_single_balance(
                            asset, cached_entry.balance, cached_entry.hold_trade,
                            cached_entry.source, cached_entry.timestamp
                        )
                        if not validation.is_valid:
                            logger.warning(f"[BALANCE_MANAGER] Cached balance validation failed for {asset}")
                            await self._call_callbacks('validation_failed', validation)

                    return cached_entry.to_dict()

            self._stats['cache_misses'] += 1

            # Try to get fresh balance from WebSocket first
            if self._websocket_connected and self._websocket_authenticated:
                websocket_balance = await self._get_balance_from_websocket(asset)
                if websocket_balance:
                    return websocket_balance

            # Fallback to REST API
            rest_balance = await self._get_balance_from_rest_api(asset)
            if rest_balance:
                return rest_balance

            logger.warning(f"[BALANCE_MANAGER] Could not retrieve balance for {asset}")
            return None

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error getting balance for {asset}: {e}")
            self._stats['errors'] += 1
            await self._call_callbacks('error', e)
            return None

    async def get_all_balances(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get all available balances
        
        Args:
            force_refresh: Force refresh from API if True
            
        Returns:
            Dictionary of all balances keyed by asset
        """
        if not self._initialized:
            raise RuntimeError("Balance manager not initialized")

        try:
            # Try cache first unless force refresh requested
            if not force_refresh:
                cached_balances = await self.cache.get_all()
                if cached_balances:
                    self._stats['cache_hits'] += len(cached_balances)
                    return {asset: entry.to_dict() for asset, entry in cached_balances.items()}

            # Try WebSocket data first
            if self._websocket_connected and self._websocket_authenticated:
                websocket_balances = await self._get_all_balances_from_websocket()
                if websocket_balances:
                    return websocket_balances

            # Fallback to REST API
            rest_balances = await self._get_all_balances_from_rest_api()
            return rest_balances or {}

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error getting all balances: {e}")
            self._stats['errors'] += 1
            await self._call_callbacks('error', e)
            return {}

    async def refresh_balance(self, asset: str) -> bool:
        """
        Force refresh balance for specific asset
        
        Args:
            asset: Asset symbol to refresh
            
        Returns:
            True if refresh successful
        """
        try:
            balance = await self.get_balance(asset, force_refresh=True)
            return balance is not None
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error refreshing balance for {asset}: {e}")
            return False

    async def refresh_all_balances(self) -> bool:
        """
        Force refresh all balances
        
        Returns:
            True if refresh successful
        """
        try:
            balances = await self.get_all_balances(force_refresh=True)
            return len(balances) > 0
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error refreshing all balances: {e}")
            return False

    def register_callback(self, event_type: str, callback: Callable):
        """
        Register callback for balance events
        
        Args:
            event_type: Type of event ('balance_update', 'balance_change', 'websocket_connected', etc.)
            callback: Async callback function
        """
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
            logger.debug(f"[BALANCE_MANAGER] Registered callback for {event_type}")
        else:
            logger.warning(f"[BALANCE_MANAGER] Unknown event type: {event_type}")

    def unregister_callback(self, event_type: str, callback: Callable):
        """Remove callback for event type"""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)
            logger.debug(f"[BALANCE_MANAGER] Unregistered callback for {event_type}")

    async def _setup_websocket_integration(self):
        """Setup WebSocket integration for real-time balance updates"""
        if not self.websocket_client:
            return

        try:
            # Register for balance updates
            self.websocket_client.register_callback('balance', self._handle_websocket_balance_update)
            self.websocket_client.register_callback('connected', self._handle_websocket_connected)
            self.websocket_client.register_callback('disconnected', self._handle_websocket_disconnected)
            self.websocket_client.register_callback('authenticated', self._handle_websocket_authenticated)

            # Check if already connected
            if hasattr(self.websocket_client, 'is_connected') and self.websocket_client.is_connected():
                self._websocket_connected = True

                # Check if authenticated
                if hasattr(self.websocket_client, 'is_authenticated') and self.websocket_client.is_authenticated():
                    self._websocket_authenticated = True
                    await self._subscribe_to_balance_updates()

            logger.info("[BALANCE_MANAGER] WebSocket integration setup complete")

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] WebSocket integration setup failed: {e}")

    async def _cleanup_websocket_integration(self):
        """Cleanup WebSocket integration"""
        if not self.websocket_client:
            return

        try:
            # Unregister callbacks
            self.websocket_client.unregister_callback('balance', self._handle_websocket_balance_update)
            self.websocket_client.unregister_callback('connected', self._handle_websocket_connected)
            self.websocket_client.unregister_callback('disconnected', self._handle_websocket_disconnected)
            self.websocket_client.unregister_callback('authenticated', self._handle_websocket_authenticated)

            logger.debug("[BALANCE_MANAGER] WebSocket integration cleanup complete")

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] WebSocket integration cleanup failed: {e}")

    async def _handle_websocket_balance_update(self, balance_updates: List[Any]):
        """Handle balance updates from WebSocket"""
        try:
            for balance_update in balance_updates:
                asset = balance_update.asset
                balance = balance_update.balance
                hold_trade = balance_update.hold_trade

                # Update cache
                await self.cache.put(
                    asset=asset,
                    balance=balance,
                    hold_trade=hold_trade,
                    source=BalanceSource.WEBSOCKET.value
                )

                # Add to history
                await self.history.add_balance_entry(
                    asset=asset,
                    balance=balance,
                    hold_trade=hold_trade,
                    source=BalanceSource.WEBSOCKET.value,
                    change_reason='websocket_update'
                )

                # Update statistics
                self._stats['websocket_updates'] += 1
                self._last_websocket_update = time.time()
                self._balance_sources[asset] = BalanceSource.WEBSOCKET

                # Validate if enabled
                if self.config.validation_on_update and self.validator:
                    validation = self.validator.validate_single_balance(
                        asset, balance, hold_trade, BalanceSource.WEBSOCKET.value
                    )
                    if not validation.is_valid:
                        logger.warning(f"[BALANCE_MANAGER] WebSocket balance validation failed for {asset}")
                        await self._call_callbacks('validation_failed', validation)

                # Call update callbacks
                balance_dict = {
                    'asset': asset,
                    'balance': float(balance),
                    'hold_trade': float(hold_trade),
                    'free': float(balance - hold_trade),
                    'source': BalanceSource.WEBSOCKET.value,
                    'timestamp': time.time()
                }

                await self._call_callbacks('balance_update', balance_dict)

                # Check for significant changes
                if balance_update.balance_change and abs(balance_update.balance_change) >= self.config.balance_change_threshold:
                    await self._call_callbacks('balance_change', balance_dict)

            logger.debug(f"[BALANCE_MANAGER] Processed {len(balance_updates)} WebSocket balance updates")

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error handling WebSocket balance update: {e}")
            self._stats['errors'] += 1

    async def _handle_websocket_connected(self):
        """Handle WebSocket connection established"""
        self._websocket_connected = True
        logger.info("[BALANCE_MANAGER] WebSocket connected")
        await self._call_callbacks('websocket_connected')

    async def _handle_websocket_disconnected(self):
        """Handle WebSocket connection lost"""
        self._websocket_connected = False
        self._websocket_authenticated = False
        logger.warning("[BALANCE_MANAGER] WebSocket disconnected")
        await self._call_callbacks('websocket_disconnected')

    async def _handle_websocket_authenticated(self):
        """Handle WebSocket authentication successful"""
        self._websocket_authenticated = True
        logger.info("[BALANCE_MANAGER] WebSocket authenticated")
        await self._subscribe_to_balance_updates()

    async def _subscribe_to_balance_updates(self):
        """Subscribe to balance updates via WebSocket"""
        try:
            if hasattr(self.websocket_client, 'subscribe_balance'):
                success = await self.websocket_client.subscribe_balance()
                if success:
                    logger.info("[BALANCE_MANAGER] Subscribed to WebSocket balance updates")
                else:
                    logger.error("[BALANCE_MANAGER] Failed to subscribe to WebSocket balance updates")
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error subscribing to balance updates: {e}")

    async def _get_balance_from_websocket(self, asset: str) -> Optional[Dict[str, Any]]:
        """Get balance from WebSocket client data"""
        try:
            if hasattr(self.websocket_client, 'get_balance'):
                balance_data = self.websocket_client.get_balance(asset)
                if balance_data:
                    # Update cache and history
                    await self._process_balance_data(asset, balance_data, BalanceSource.WEBSOCKET)
                    return balance_data
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error getting balance from WebSocket: {e}")

        return None

    async def _get_all_balances_from_websocket(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get all balances from WebSocket client data"""
        try:
            if hasattr(self.websocket_client, 'get_all_balances'):
                all_balances = self.websocket_client.get_all_balances()
                if all_balances:
                    # Process each balance
                    for asset, balance_data in all_balances.items():
                        await self._process_balance_data(asset, balance_data, BalanceSource.WEBSOCKET)

                    return all_balances
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error getting all balances from WebSocket: {e}")

        return None

    async def _get_balance_from_rest_api(self, asset: str) -> Optional[Dict[str, Any]]:
        """Get balance from REST API with circuit breaker protection"""
        if not self.rest_client:
            return None

        try:
            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                logger.warning("[BALANCE_MANAGER] Circuit breaker open, skipping REST API call")
                return None

            # Make REST API call
            self._stats['rest_api_calls'] += 1
            response = await self.rest_client.get_account_balance()

            if response and 'result' in response:
                balances = response['result']

                if asset in balances:
                    balance_value = safe_decimal(balances[asset])
                    balance_data = {
                        'asset': asset,
                        'balance': float(balance_value),
                        'hold_trade': 0.0,  # REST API doesn't provide hold info
                        'free': float(balance_value),
                        'source': BalanceSource.REST_API.value,
                        'timestamp': time.time()
                    }

                    # Process balance data
                    await self._process_balance_data(asset, balance_data, BalanceSource.REST_API)

                    # Record circuit breaker success
                    if self.circuit_breaker:
                        self.circuit_breaker._record_success(0)

                    return balance_data

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] REST API balance request failed: {e}")
            self._stats['errors'] += 1

            # Record circuit breaker failure
            if self.circuit_breaker:
                self.circuit_breaker._record_failure(e, 0)

        return None

    async def _get_all_balances_from_rest_api(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get all balances from REST API with circuit breaker protection"""
        if not self.rest_client:
            return None

        try:
            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                logger.warning("[BALANCE_MANAGER] Circuit breaker open, skipping REST API call")
                await self._call_callbacks('fallback_activated', 'circuit_breaker_open')
                return None

            # Make REST API call
            self._stats['rest_api_calls'] += 1
            response = await self.rest_client.get_account_balance()

            if response and 'result' in response:
                raw_balances = response['result']
                processed_balances = {}

                for asset, balance_value in raw_balances.items():
                    balance_decimal = safe_decimal(balance_value)

                    # Skip zero balances
                    if balance_decimal <= 0:
                        continue

                    balance_data = {
                        'asset': asset,
                        'balance': float(balance_decimal),
                        'hold_trade': 0.0,  # REST API doesn't provide hold info
                        'free': float(balance_decimal),
                        'source': BalanceSource.REST_API.value,
                        'timestamp': time.time()
                    }

                    processed_balances[asset] = balance_data

                    # Process balance data
                    await self._process_balance_data(asset, balance_data, BalanceSource.REST_API)

                # Record circuit breaker success
                if self.circuit_breaker:
                    self.circuit_breaker._record_success(0)

                self._last_full_refresh = time.time()
                await self._call_callbacks('fallback_activated', 'rest_api_success')

                return processed_balances

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] REST API all balances request failed: {e}")
            self._stats['errors'] += 1

            # Record circuit breaker failure
            if self.circuit_breaker:
                self.circuit_breaker._record_failure(e, 0)

        return None

    async def _process_balance_data(self, asset: str, balance_data: Dict[str, Any], source: BalanceSource):
        """Process and store balance data"""
        try:
            balance = safe_decimal(balance_data.get('balance', 0))
            hold_trade = safe_decimal(balance_data.get('hold_trade', 0))

            # Update cache
            await self.cache.put(
                asset=asset,
                balance=balance,
                hold_trade=hold_trade,
                source=source.value
            )

            # Add to history
            await self.history.add_balance_entry(
                asset=asset,
                balance=balance,
                hold_trade=hold_trade,
                source=source.value,
                change_reason=f'{source.value}_update'
            )

            # Update source tracking
            self._balance_sources[asset] = source

            # Validate if enabled
            if self.config.validation_on_update and self.validator:
                validation = self.validator.validate_single_balance(
                    asset, balance, hold_trade, source.value
                )
                if not validation.is_valid:
                    logger.warning(f"[BALANCE_MANAGER] Balance validation failed for {asset}")
                    self._stats['validation_failures'] += 1
                    await self._call_callbacks('validation_failed', validation)

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error processing balance data for {asset}: {e}")

    async def _perform_initial_balance_refresh(self) -> Dict[str, Dict[str, Any]]:
        """Perform initial balance refresh on startup"""
        logger.info("[BALANCE_MANAGER] Performing initial balance refresh...")

        try:
            # Try WebSocket first if available and connected
            if self._websocket_connected and self._websocket_authenticated:
                balances = await self._get_all_balances_from_websocket()
                if balances:
                    logger.info(f"[BALANCE_MANAGER] Initial refresh via WebSocket: {len(balances)} balances")
                    return balances

            # Fallback to REST API
            balances = await self._get_all_balances_from_rest_api()
            if balances:
                logger.info(f"[BALANCE_MANAGER] Initial refresh via REST API: {len(balances)} balances")
                return balances

            logger.warning("[BALANCE_MANAGER] Initial balance refresh failed")
            return {}

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Initial balance refresh error: {e}")
            return {}

    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        if self.websocket_client:
            self._websocket_monitor_task = asyncio.create_task(self._websocket_monitor_loop())

        self._force_update_task = asyncio.create_task(self._force_update_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("[BALANCE_MANAGER] Background tasks started")

    async def _stop_background_tasks(self):
        """Stop all background tasks"""
        tasks = [
            self._websocket_monitor_task,
            self._force_update_task,
            self._cleanup_task
        ]

        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("[BALANCE_MANAGER] Background tasks stopped")

    async def _websocket_monitor_loop(self):
        """Monitor WebSocket connection and handle reconnection"""
        while self._running:
            try:
                # Check WebSocket health
                if self.websocket_client and hasattr(self.websocket_client, 'is_connected'):
                    if not self.websocket_client.is_connected():
                        if self._websocket_connected:
                            logger.warning("[BALANCE_MANAGER] WebSocket connection lost")
                            await self._handle_websocket_disconnected()
                    else:
                        if not self._websocket_connected:
                            logger.info("[BALANCE_MANAGER] WebSocket reconnected")
                            await self._handle_websocket_connected()

                await asyncio.sleep(self.config.websocket_retry_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[BALANCE_MANAGER] WebSocket monitor error: {e}")
                await asyncio.sleep(10)

    async def _force_update_loop(self):
        """Periodically force balance updates"""
        while self._running:
            try:
                await asyncio.sleep(self.config.force_update_interval)

                if not self._running:
                    break

                # Force refresh if no WebSocket updates recently
                time_since_websocket = time.time() - self._last_websocket_update
                if time_since_websocket > self.config.force_update_interval:
                    logger.info("[BALANCE_MANAGER] Performing scheduled balance refresh")
                    await self.refresh_all_balances()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[BALANCE_MANAGER] Force update error: {e}")
                await asyncio.sleep(60)

    async def _cleanup_loop(self):
        """Periodic cleanup and maintenance"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)

                if not self._running:
                    break

                # Log statistics
                await self._log_periodic_statistics()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[BALANCE_MANAGER] Cleanup error: {e}")
                await asyncio.sleep(60)

    async def _log_periodic_statistics(self):
        """Log periodic statistics"""
        try:
            cache_stats = self.cache.get_statistics()
            history_stats = self.history.get_statistics()

            logger.info(f"[BALANCE_MANAGER] Stats - "
                       f"Cache: {cache_stats['cache_size']}/{cache_stats['max_size']} "
                       f"({cache_stats['hit_rate_percent']:.1f}% hit rate), "
                       f"History: {history_stats['total_entries']} entries, "
                       f"WebSocket: {'connected' if self._websocket_connected else 'disconnected'}, "
                       f"Sources: {len(self._balance_sources)} assets tracked")

        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error logging statistics: {e}")

    async def _cleanup_on_error(self):
        """Cleanup resources after initialization error"""
        try:
            if hasattr(self, 'cache') and self.cache:
                await self.cache.stop()
            if hasattr(self, 'history') and self.history:
                await self.history.stop()
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Error during cleanup: {e}")

    async def _call_callbacks(self, event_type: str, data: Any = None):
        """Call registered callbacks for event type"""
        callbacks = self._callbacks.get(event_type, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    if data is not None:
                        await callback(data)
                    else:
                        await callback()
                else:
                    if data is not None:
                        callback(data)
                    else:
                        callback()
            except Exception as e:
                logger.error(f"[BALANCE_MANAGER] Callback error for {event_type}: {e}")

    # Public status and monitoring methods

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive balance manager status"""
        cache_stats = self.cache.get_statistics()
        history_stats = self.history.get_statistics()

        return {
            'initialized': self._initialized,
            'running': self._running,
            'websocket': {
                'connected': self._websocket_connected,
                'authenticated': self._websocket_authenticated,
                'last_update': self._last_websocket_update,
                'time_since_update': time.time() - self._last_websocket_update if self._last_websocket_update > 0 else float('inf')
            },
            'rest_api': {
                'available': self.rest_client is not None,
                'circuit_breaker_open': self.circuit_breaker.get_status()['state'] == 'OPEN' if self.circuit_breaker else False,
                'last_full_refresh': self._last_full_refresh
            },
            'cache': cache_stats,
            'history': history_stats,
            'statistics': dict(self._stats),
            'tracked_assets': len(self._balance_sources),
            'balance_sources': {asset: source.value for asset, source in self._balance_sources.items()}
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics"""
        return dict(self._stats)

    async def validate_all_balances(self) -> BalanceValidationResult:
        """Validate all current balances"""
        if not self.validator:
            raise RuntimeError("Validation not enabled")

        try:
            balances = await self.get_all_balances()
            return self.validator.validate_multiple_balances(balances)
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER] Balance validation error: {e}")
            raise

    # Context manager support
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()
