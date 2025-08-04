"""
Balance Manager V2 - Unified WebSocket-Primary Interface
=======================================================

Next-generation balance manager that provides a unified interface for the crypto trading bot
with WebSocket V2 as the primary data source and REST API fallback. Designed to eliminate
nonce issues while providing robust, real-time balance access.

Features:
- WebSocket V2 primary with REST fallback
- Seamless integration with existing bot architecture  
- Real-time balance streaming with 90% WebSocket usage
- Intelligent source selection and failover
- Circuit breaker protection and error recovery
- Thread-safe operations for concurrent trading
- Balance validation and consistency checks
- Performance monitoring and statistics
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union, Callable
from decimal import Decimal
from threading import RLock
from dataclasses import dataclass

from .websocket_balance_stream import WebSocketBalanceStream, BalanceUpdate
from .hybrid_portfolio_manager import HybridPortfolioManager, HybridPortfolioConfig, DataSource
from ..utils.decimal_precision_fix import safe_decimal, safe_float, is_zero

logger = logging.getLogger(__name__)


@dataclass
class BalanceManagerV2Config:
    """Configuration for Balance Manager V2"""
    # WebSocket streaming settings
    websocket_token_refresh_interval: float = 720.0  # 12 minutes
    websocket_connection_timeout: float = 10.0
    
    # Hybrid portfolio settings
    websocket_primary_ratio: float = 0.9  # 90% WebSocket usage
    rest_fallback_ratio: float = 0.1      # 10% REST usage
    
    # Data freshness and validation
    balance_max_age: float = 60.0         # Max age for balance data
    enable_balance_validation: bool = True
    enable_balance_aggregation: bool = True
    
    # Circuit breaker settings
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 60.0
    
    # Performance monitoring
    enable_performance_monitoring: bool = True
    performance_log_interval: float = 300.0  # 5 minutes
    
    # Compatibility settings
    maintain_legacy_interface: bool = True
    enable_balance_callbacks: bool = True


class BalanceManagerV2:
    """
    Unified balance manager with WebSocket V2 primary and REST fallback
    
    Provides a simple, unified interface for balance operations while using
    WebSocket streaming as the primary source and REST API as fallback only.
    """
    
    def __init__(self,
                 websocket_client,
                 exchange_client,
                 config: Optional[BalanceManagerV2Config] = None):
        """
        Initialize Balance Manager V2
        
        Args:
            websocket_client: WebSocket V2 client for streaming
            exchange_client: Exchange client for REST fallback and token management
            config: Configuration object
        """
        self.config = config or BalanceManagerV2Config()
        self.websocket_client = websocket_client
        self.exchange_client = exchange_client
        
        # Core components
        self.websocket_stream: Optional[WebSocketBalanceStream] = None
        self.hybrid_manager: Optional[HybridPortfolioManager] = None
        
        # State management
        self._lock = RLock()
        self._async_lock = asyncio.Lock()
        self._initialized = False
        self._running = False
        
        # Legacy compatibility attributes
        self.balances: Dict[str, Dict[str, Any]] = {}
        self.websocket_balances: Dict[str, Dict[str, Any]] = {}
        self.last_update = 0.0
        self.circuit_breaker_active = False
        self.consecutive_failures = 0
        self.backoff_multiplier = 1.0
        self.circuit_breaker_reset_time = 0
        self._api_call_counter = 0
        
        # Callback management for legacy compatibility
        self._balance_callbacks: List[Callable] = []
        self._update_callbacks: List[Callable] = []
        
        # Background tasks
        self._sync_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'total_balance_requests': 0,
            'websocket_requests': 0,
            'rest_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'last_request_time': 0.0,
            'uptime_start': 0.0,
            'balance_updates_processed': 0
        }
        
        logger.info("[BALANCE_MANAGER_V2] Initialized with WebSocket-primary architecture")
    
    async def initialize(self) -> bool:
        """
        Initialize the balance manager and all components with enhanced error handling
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            logger.warning("[BALANCE_MANAGER_V2] Already initialized")
            return True
        
        try:
            async with self._async_lock:
                logger.info("[BALANCE_MANAGER_V2] Starting initialization...")
                
                self.stats['uptime_start'] = time.time()
                
                # Phase 1: Initialize WebSocket balance stream with validation
                logger.info("[BALANCE_MANAGER_V2] Phase 1: Initializing WebSocket balance stream...")
                
                if not self.websocket_client:
                    logger.error("[BALANCE_MANAGER_V2] No WebSocket client provided - cannot initialize WebSocket streaming")
                    return await self._initialize_rest_only_mode()
                
                self.websocket_stream = WebSocketBalanceStream(
                    websocket_client=self.websocket_client,
                    exchange_client=self.exchange_client,
                    token_refresh_interval=self.config.websocket_token_refresh_interval,
                    connection_timeout=self.config.websocket_connection_timeout
                )
                
                # Start WebSocket stream with timeout
                logger.info("[BALANCE_MANAGER_V2] Starting WebSocket balance stream...")
                try:
                    start_task = asyncio.create_task(self.websocket_stream.start())
                    websocket_started = await asyncio.wait_for(start_task, timeout=30.0)
                    
                    if not websocket_started:
                        logger.error("[BALANCE_MANAGER_V2] WebSocket balance stream failed to start")
                        return await self._initialize_rest_fallback_mode()
                    
                    logger.info("[BALANCE_MANAGER_V2] WebSocket balance stream started successfully")
                    
                except asyncio.TimeoutError:
                    logger.error("[BALANCE_MANAGER_V2] WebSocket balance stream startup timed out after 30s")
                    return await self._initialize_rest_fallback_mode()
                except Exception as ws_error:
                    logger.error(f"[BALANCE_MANAGER_V2] WebSocket balance stream startup failed: {ws_error}")
                    return await self._initialize_rest_fallback_mode()
                
                # Phase 2: Initialize hybrid portfolio manager
                logger.info("[BALANCE_MANAGER_V2] Phase 2: Initializing hybrid portfolio manager...")
                
                hybrid_config = HybridPortfolioConfig(
                    websocket_primary_ratio=self.config.websocket_primary_ratio,
                    rest_fallback_ratio=self.config.rest_fallback_ratio,
                    enable_balance_validation=self.config.enable_balance_validation,
                    enable_balance_aggregation=self.config.enable_balance_aggregation,
                    enable_circuit_breaker=self.config.enable_circuit_breaker,
                    circuit_breaker_failure_threshold=self.config.circuit_breaker_failure_threshold,
                    circuit_breaker_recovery_timeout=self.config.circuit_breaker_recovery_timeout
                )
                
                self.hybrid_manager = HybridPortfolioManager(
                    websocket_stream=self.websocket_stream,
                    rest_client=self.exchange_client,
                    config=hybrid_config
                )
                
                # Start hybrid manager with timeout
                try:
                    hybrid_start_task = asyncio.create_task(self.hybrid_manager.start())
                    hybrid_started = await asyncio.wait_for(hybrid_start_task, timeout=15.0)
                    
                    if not hybrid_started:
                        logger.error("[BALANCE_MANAGER_V2] Hybrid portfolio manager failed to start")
                        return await self._initialize_rest_fallback_mode()
                    
                    logger.info("[BALANCE_MANAGER_V2] Hybrid portfolio manager started successfully")
                    
                except asyncio.TimeoutError:
                    logger.error("[BALANCE_MANAGER_V2] Hybrid portfolio manager startup timed out after 15s")
                    return await self._initialize_rest_fallback_mode()
                except Exception as hybrid_error:
                    logger.error(f"[BALANCE_MANAGER_V2] Hybrid portfolio manager startup failed: {hybrid_error}")
                    return await self._initialize_rest_fallback_mode()
                
                # Phase 3: Setup callbacks and background tasks
                logger.info("[BALANCE_MANAGER_V2] Phase 3: Setting up callbacks and background tasks...")
                
                # Register callbacks for real-time updates
                if self.config.enable_balance_callbacks:
                    self.websocket_stream.register_balance_callback(self._handle_balance_update)
                    logger.info("[BALANCE_MANAGER_V2] Balance update callbacks registered")
                
                # Start background tasks
                self._running = True
                await self._start_background_tasks()
                
                # Phase 4: Perform initial balance sync with validation
                logger.info("[BALANCE_MANAGER_V2] Phase 4: Performing initial balance sync...")
                try:
                    await asyncio.wait_for(self._sync_balance_data(), timeout=10.0)
                    logger.info(f"[BALANCE_MANAGER_V2] Initial balance sync complete - {len(self.balances)} balances loaded")
                except asyncio.TimeoutError:
                    logger.warning("[BALANCE_MANAGER_V2] Initial balance sync timed out - will sync in background")
                except Exception as sync_error:
                    logger.warning(f"[BALANCE_MANAGER_V2] Initial balance sync failed: {sync_error} - will retry in background")
                
                self._initialized = True
                
                logger.info(f"[BALANCE_MANAGER_V2] Initialization complete - "
                           f"WebSocket-primary mode active with {len(self.balances)} balances")
                return True
                
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] Initialization failed: {e}")
            await self._cleanup_on_error()
            return False
    
    async def _initialize_rest_only_mode(self) -> bool:
        """Initialize in REST-only mode as fallback"""
        try:
            logger.warning("[BALANCE_MANAGER_V2] Initializing in REST-only fallback mode...")
            
            # Create REST-only hybrid configuration
            rest_only_config = HybridPortfolioConfig(
                websocket_primary_ratio=0.0,  # No WebSocket usage
                rest_fallback_ratio=1.0,      # 100% REST usage
                enable_balance_validation=True,
                enable_balance_aggregation=False,  # Disable aggregation for REST-only
                enable_circuit_breaker=self.config.enable_circuit_breaker,
                circuit_breaker_failure_threshold=self.config.circuit_breaker_failure_threshold,
                circuit_breaker_recovery_timeout=self.config.circuit_breaker_recovery_timeout
            )
            
            # Create REST-only hybrid manager
            self.hybrid_manager = HybridPortfolioManager(
                websocket_stream=None,  # No WebSocket stream
                rest_client=self.exchange_client,
                config=rest_only_config
            )
            
            # Start hybrid manager
            if not await self.hybrid_manager.start():
                logger.error("[BALANCE_MANAGER_V2] REST-only hybrid manager failed to start")
                return False
            
            # Start background tasks
            self._running = True
            await self._start_background_tasks()
            
            # Perform initial balance sync
            await self._sync_balance_data()
            
            self._initialized = True
            
            logger.info(f"[BALANCE_MANAGER_V2] REST-only mode initialized successfully - "
                       f"{len(self.balances)} balances loaded")
            return True
            
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] REST-only mode initialization failed: {e}")
            return False
    
    async def _initialize_rest_fallback_mode(self) -> bool:
        """Initialize with REST fallback after WebSocket failure"""
        try:
            logger.warning("[BALANCE_MANAGER_V2] WebSocket failed - switching to REST fallback mode...")
            
            # Clean up failed WebSocket components
            if self.websocket_stream:
                try:
                    await self.websocket_stream.stop()
                except:
                    pass
                self.websocket_stream = None
            
            # Initialize REST-only mode
            return await self._initialize_rest_only_mode()
            
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] REST fallback initialization failed: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the balance manager and cleanup resources"""
        if not self._running:
            return
        
        logger.info("[BALANCE_MANAGER_V2] Shutting down...")
        
        self._running = False
        
        # Stop background tasks
        await self._stop_background_tasks()
        
        # Stop components
        if self.hybrid_manager:
            await self.hybrid_manager.stop()
        
        if self.websocket_stream:
            await self.websocket_stream.stop()
        
        self._initialized = False
        
        logger.info("[BALANCE_MANAGER_V2] Shutdown complete")
    
    # Primary balance access methods
    
    async def get_balance(self, asset: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get balance for specific asset
        
        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')
            force_refresh: Force refresh (will use WebSocket stream data)
            
        Returns:
            Balance dictionary or None if not found
        """
        if not self._initialized:
            raise RuntimeError("Balance manager not initialized")
        
        self.stats['total_balance_requests'] += 1
        self.stats['last_request_time'] = time.time()
        
        try:
            # Use hybrid manager for intelligent source selection
            balance_data = await self.hybrid_manager.get_balance(asset)
            
            if balance_data:
                self.stats['successful_requests'] += 1
                
                # Update legacy compatibility attributes
                with self._lock:
                    self.balances[asset] = balance_data
                    self.websocket_balances[asset] = balance_data
                    self.last_update = time.time()
                    self.circuit_breaker_active = False
                    self.consecutive_failures = 0
                
                # Enhanced logging for key assets
                if asset in ['USDT', 'SHIB', 'MANA'] or balance_data.get('free', 0) > 1.0:
                    logger.info(f"[BALANCE_MANAGER_V2] {asset} balance: {balance_data.get('free', 0):.8f}")
                
                return balance_data
            else:
                self.stats['failed_requests'] += 1
                logger.warning(f"[BALANCE_MANAGER_V2] Could not retrieve balance for {asset}")
                return None
                
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] Error getting balance for {asset}: {e}")
            self.stats['failed_requests'] += 1
            return None
    
    async def get_all_balances(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get all available balances
        
        Args:
            force_refresh: Force refresh (will use WebSocket stream data)
            
        Returns:
            Dictionary of all balances keyed by asset
        """
        if not self._initialized:
            raise RuntimeError("Balance manager not initialized")
        
        self.stats['total_balance_requests'] += 1
        self.stats['last_request_time'] = time.time()
        
        try:
            # Use hybrid manager for intelligent source selection
            all_balances = await self.hybrid_manager.get_all_balances()
            
            if all_balances:
                self.stats['successful_requests'] += 1
                
                # Update legacy compatibility attributes
                with self._lock:
                    self.balances.clear()
                    self.websocket_balances.clear()
                    
                    for asset, balance_data in all_balances.items():
                        self.balances[asset] = balance_data
                        self.websocket_balances[asset] = balance_data
                    
                    self.last_update = time.time()
                    self.circuit_breaker_active = False
                    self.consecutive_failures = 0
                
                logger.info(f"[BALANCE_MANAGER_V2] Retrieved {len(all_balances)} balances successfully")
                return all_balances
            else:
                self.stats['failed_requests'] += 1
                logger.warning("[BALANCE_MANAGER_V2] Could not retrieve any balances")
                return {}
                
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] Error getting all balances: {e}")
            self.stats['failed_requests'] += 1
            return {}
    
    async def get_usdt_total(self) -> float:
        """
        Get total USDT across all USDT variants
        
        Returns:
            Total USDT amount
        """
        if not self._initialized:
            return 0.0
        
        try:
            if self.hybrid_manager:
                return await self.hybrid_manager.get_usdt_total()
            else:
                # Fallback to manual calculation
                total = 0.0
                usdt_variants = ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S', 'USDT.F', 'USDT.B']
                
                for variant in usdt_variants:
                    balance_data = await self.get_balance(variant)
                    if balance_data:
                        total += balance_data.get('free', 0)
                
                return total
                
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] Error getting USDT total: {e}")
            return 0.0
    
    # Legacy compatibility methods
    
    def get_balance_sync(self, asset: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous balance access for legacy compatibility
        
        Args:
            asset: Asset symbol
            
        Returns:
            Balance dictionary or None
        """
        with self._lock:
            return self.balances.get(asset)
    
    def get_all_balances_sync(self) -> Dict[str, Dict[str, Any]]:
        """
        Synchronous all balances access for legacy compatibility
        
        Returns:
            Dictionary of all cached balances
        """
        with self._lock:
            return self.balances.copy()
    
    async def process_websocket_update(self, balance_updates: Dict[str, Dict[str, Any]]):
        """Legacy method for WebSocket update processing"""
        try:
            with self._lock:
                for asset, balance_data in balance_updates.items():
                    self.balances[asset] = balance_data
                    self.websocket_balances[asset] = balance_data
                
                self.last_update = time.time()
                self.circuit_breaker_active = False
                self.consecutive_failures = 0
            
            self.stats['balance_updates_processed'] += len(balance_updates)
            
            logger.debug(f"[BALANCE_MANAGER_V2] Processed {len(balance_updates)} legacy WebSocket updates")
            
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] Error processing WebSocket update: {e}")
    
    def register_callback(self, callback: Callable):
        """Register callback for balance updates (legacy compatibility)"""
        self._balance_callbacks.append(callback)
        logger.debug("[BALANCE_MANAGER_V2] Registered legacy balance callback")
    
    def register_update_callback(self, callback: Callable):
        """Register callback for balance updates (legacy compatibility)"""
        self._update_callbacks.append(callback)
        logger.debug("[BALANCE_MANAGER_V2] Registered legacy update callback")
    
    # Internal methods
    
    async def _handle_balance_update(self, balance_update: BalanceUpdate):
        """Handle balance updates from WebSocket stream"""
        try:
            balance_data = balance_update.to_dict()
            asset = balance_update.asset
            
            # Update legacy compatibility attributes
            with self._lock:
                self.balances[asset] = balance_data
                self.websocket_balances[asset] = balance_data
                self.last_update = time.time()
                self.circuit_breaker_active = False
                self.consecutive_failures = 0
            
            self.stats['balance_updates_processed'] += 1
            
            # Call legacy callbacks
            if self.config.enable_balance_callbacks:
                await self._call_balance_callbacks(asset, balance_data)
            
            # Enhanced logging for key assets
            if asset in ['USDT', 'SHIB', 'MANA'] or balance_update.free_balance > 1.0:
                logger.info(f"[BALANCE_MANAGER_V2] {asset} updated via WebSocket: "
                           f"{float(balance_update.free_balance):.8f}")
            
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] Error handling balance update: {e}")
    
    async def _call_balance_callbacks(self, asset: str, balance_data: Dict[str, Any]):
        """Call registered balance callbacks"""
        for callback in self._balance_callbacks + self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(asset, balance_data)
                else:
                    callback(asset, balance_data)
            except Exception as e:
                logger.error(f"[BALANCE_MANAGER_V2] Balance callback error: {e}")
    
    async def _sync_balance_data(self):
        """Sync balance data from hybrid manager to legacy attributes"""
        try:
            all_balances = await self.hybrid_manager.get_all_balances()
            
            with self._lock:
                self.balances.clear()
                self.websocket_balances.clear()
                
                for asset, balance_data in all_balances.items():
                    self.balances[asset] = balance_data
                    self.websocket_balances[asset] = balance_data
                
                self.last_update = time.time()
            
            logger.info(f"[BALANCE_MANAGER_V2] Synced {len(all_balances)} balances to legacy attributes")
            
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] Error syncing balance data: {e}")
    
    async def _start_background_tasks(self):
        """Start background monitoring tasks"""
        self._sync_task = asyncio.create_task(self._sync_loop())
        
        if self.config.enable_performance_monitoring:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("[BALANCE_MANAGER_V2] Background tasks started")
    
    async def _stop_background_tasks(self):
        """Stop background tasks"""
        tasks = [self._sync_task, self._monitor_task]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("[BALANCE_MANAGER_V2] Background tasks stopped")
    
    async def _sync_loop(self):
        """Background sync loop for legacy compatibility"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Sync every 30 seconds
                
                if not self._running:
                    break
                
                await self._sync_balance_data()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[BALANCE_MANAGER_V2] Sync loop error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                await asyncio.sleep(self.config.performance_log_interval)
                
                if not self._running:
                    break
                
                await self._log_performance_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[BALANCE_MANAGER_V2] Monitor loop error: {e}")
                await asyncio.sleep(60)
    
    async def _log_performance_metrics(self):
        """Log performance metrics"""
        try:
            uptime = time.time() - self.stats['uptime_start']
            success_rate = (self.stats['successful_requests'] / 
                           max(self.stats['total_balance_requests'], 1) * 100)
            
            # Get component statuses
            ws_status = self.websocket_stream.get_status() if self.websocket_stream else {}
            hybrid_status = self.hybrid_manager.get_status() if self.hybrid_manager else {}
            
            logger.info(f"[BALANCE_MANAGER_V2] Performance Summary - "
                       f"Uptime: {uptime:.1f}s, "
                       f"Requests: {self.stats['total_balance_requests']}, "
                       f"Success Rate: {success_rate:.1f}%, "
                       f"WebSocket: {ws_status.get('state', 'unknown')}, "
                       f"Balances Cached: {len(self.balances)}")
            
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] Error logging performance metrics: {e}")
    
    async def _cleanup_on_error(self):
        """Cleanup resources after initialization error"""
        try:
            if self.hybrid_manager:
                await self.hybrid_manager.stop()
            if self.websocket_stream:
                await self.websocket_stream.stop()
        except Exception as e:
            logger.error(f"[BALANCE_MANAGER_V2] Error during cleanup: {e}")
    
    # Public status and monitoring methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information"""
        uptime = time.time() - self.stats['uptime_start'] if self.stats['uptime_start'] > 0 else 0
        success_rate = (self.stats['successful_requests'] / 
                       max(self.stats['total_balance_requests'], 1) * 100)
        
        status = {
            'initialized': self._initialized,
            'running': self._running,
            'uptime_seconds': uptime,
            'balance_count': len(self.balances),
            'websocket_balance_count': len(self.websocket_balances),
            'last_update': self.last_update,
            'time_since_update': time.time() - self.last_update if self.last_update > 0 else float('inf'),
            'circuit_breaker_active': self.circuit_breaker_active,
            'consecutive_failures': self.consecutive_failures,
            'success_rate_percent': success_rate,
            'statistics': dict(self.stats)
        }
        
        # Add component statuses
        if self.websocket_stream:
            status['websocket_stream'] = self.websocket_stream.get_status()
        
        if self.hybrid_manager:
            status['hybrid_manager'] = self.hybrid_manager.get_status()
        
        return status
    
    def get_balance_streaming_status(self) -> Dict[str, Any]:
        """Get balance streaming status for compatibility"""
        return self.get_status()
    
    # Context manager support
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()


# Factory function for easy integration
async def create_balance_manager_v2(websocket_client, 
                                   exchange_client,
                                   config: Optional[BalanceManagerV2Config] = None) -> BalanceManagerV2:
    """
    Factory function to create and initialize Balance Manager V2
    
    Args:
        websocket_client: WebSocket V2 client
        exchange_client: Exchange client for REST fallback
        config: Configuration object
        
    Returns:
        Initialized BalanceManagerV2 instance
    """
    manager = BalanceManagerV2(websocket_client, exchange_client, config)
    
    if not await manager.initialize():
        raise RuntimeError("Failed to initialize Balance Manager V2")
    
    return manager