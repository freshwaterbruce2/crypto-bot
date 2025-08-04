"""
WebSocket Trading Engine Integration
===================================

Integration module to seamlessly integrate WebSocket-native trading engine
with the existing crypto trading bot architecture.

Features:
- Automatic detection and initialization of WebSocket trading capabilities
- Seamless fallback between WebSocket and REST execution
- Integration with existing balance manager and strategy systems
- Performance monitoring and metrics collection
- Configuration management for WebSocket trading preferences
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..trading.websocket_native_trading_engine import (
    WebSocketNativeTradingEngine, 
    WebSocketTradeExecutorAdapter,
    create_websocket_trading_engine
)
from ..trading.enhanced_trade_executor_with_assistants import EnhancedTradeExecutor

logger = logging.getLogger(__name__)


@dataclass
class WebSocketTradingConfig:
    """Configuration for WebSocket trading integration"""
    enabled: bool = True
    prefer_websocket: bool = True
    max_concurrent_orders: int = 10
    order_timeout_seconds: int = 60
    auto_fallback_on_failure: bool = True
    websocket_retry_attempts: int = 3
    performance_monitoring: bool = True


class WebSocketTradingIntegration:
    """
    Integration manager for WebSocket trading capabilities.
    
    Handles:
    - WebSocket trading engine initialization
    - Integration with existing trade execution pipeline
    - Performance monitoring and optimization
    - Automatic fallback management
    """
    
    def __init__(self, bot_instance, config: WebSocketTradingConfig = None):
        """
        Initialize WebSocket trading integration.
        
        Args:
            bot_instance: Main bot instance
            config: WebSocket trading configuration
        """
        self.bot = bot_instance
        self.config = config or WebSocketTradingConfig()
        
        # Core components
        self.websocket_engine: Optional[WebSocketNativeTradingEngine] = None
        self.trade_executor_adapter: Optional[WebSocketTradeExecutorAdapter] = None
        self.original_executor: Optional[EnhancedTradeExecutor] = None
        
        # Status tracking
        self.integration_status = {
            'websocket_available': False,
            'websocket_initialized': False,
            'adapter_created': False,
            'integration_active': False,
            'last_initialization_attempt': None,
            'initialization_attempts': 0
        }
        
        # Performance metrics
        self.performance_metrics = {
            'websocket_trades': 0,
            'rest_trades': 0,
            'websocket_latency_ms': [],
            'rest_latency_ms': [],
            'fallback_events': 0,
            'websocket_success_rate': 0.0,
            'integration_start_time': time.time()
        }
        
        logger.info("[WEBSOCKET_INTEGRATION] WebSocket trading integration initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize WebSocket trading integration.
        
        Returns:
            True if integration successful
        """
        try:
            logger.info("[WEBSOCKET_INTEGRATION] Starting WebSocket trading integration...")
            
            self.integration_status['last_initialization_attempt'] = time.time()
            self.integration_status['initialization_attempts'] += 1
            
            # Check prerequisites
            if not await self._check_prerequisites():
                logger.error("[WEBSOCKET_INTEGRATION] Prerequisites not met")
                return False
            
            # Create WebSocket trading engine
            if not await self._create_websocket_engine():
                logger.error("[WEBSOCKET_INTEGRATION] Failed to create WebSocket engine")
                return False
            
            # Create trade executor adapter
            if not await self._create_trade_executor_adapter():
                logger.error("[WEBSOCKET_INTEGRATION] Failed to create trade executor adapter")
                return False
            
            # Integrate with bot's trading pipeline
            if not await self._integrate_with_bot():
                logger.error("[WEBSOCKET_INTEGRATION] Failed to integrate with bot")
                return False
            
            # Start performance monitoring
            if self.config.performance_monitoring:
                await self._start_performance_monitoring()
            
            self.integration_status['integration_active'] = True
            logger.info("[WEBSOCKET_INTEGRATION] ✅ WebSocket trading integration complete")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Integration failed: {e}")
            await self._cleanup_failed_integration()
            return False
    
    async def _check_prerequisites(self) -> bool:
        """Check if all prerequisites for WebSocket trading are met"""
        try:
            # Check if WebSocket trading is enabled
            if not self.config.enabled:
                logger.info("[WEBSOCKET_INTEGRATION] WebSocket trading disabled in config")
                return False
            
            # Check if bot has WebSocket manager
            if not hasattr(self.bot, 'websocket_manager') or not self.bot.websocket_manager:
                logger.error("[WEBSOCKET_INTEGRATION] Bot missing WebSocket manager")
                return False
            
            # Check if WebSocket manager is connected and healthy
            if not self.bot.websocket_manager.is_connected or not self.bot.websocket_manager.is_healthy:
                logger.warning("[WEBSOCKET_INTEGRATION] WebSocket manager not connected/healthy")
                # Try to reconnect
                if hasattr(self.bot.websocket_manager, 'connect'):
                    await self.bot.websocket_manager.connect()
                    await asyncio.sleep(2)  # Wait for connection
                    
                    if not self.bot.websocket_manager.is_connected:
                        logger.error("[WEBSOCKET_INTEGRATION] Failed to establish WebSocket connection")
                        return False
            
            # Check if bot has balance manager
            if not hasattr(self.bot, 'balance_manager') or not self.bot.balance_manager:
                logger.error("[WEBSOCKET_INTEGRATION] Bot missing balance manager")
                return False
            
            # Check for authentication capabilities
            if not hasattr(self.bot.websocket_manager, '_auth_token') or not self.bot.websocket_manager._auth_token:
                logger.warning("[WEBSOCKET_INTEGRATION] WebSocket authentication not available")
                # This may limit order execution capabilities but shouldn't prevent integration
            
            logger.info("[WEBSOCKET_INTEGRATION] ✅ Prerequisites check passed")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Prerequisites check failed: {e}")
            return False
    
    async def _create_websocket_engine(self) -> bool:
        """Create and initialize WebSocket trading engine"""
        try:
            logger.info("[WEBSOCKET_INTEGRATION] Creating WebSocket trading engine...")
            
            # Create the engine
            self.websocket_engine = await create_websocket_trading_engine(self.bot)
            
            if not self.websocket_engine:
                logger.error("[WEBSOCKET_INTEGRATION] Failed to create WebSocket trading engine")
                return False
            
            # Apply configuration settings
            self.websocket_engine.max_concurrent_orders = self.config.max_concurrent_orders
            self.websocket_engine.order_timeout_seconds = self.config.order_timeout_seconds
            
            self.integration_status['websocket_available'] = True
            self.integration_status['websocket_initialized'] = True
            
            logger.info("[WEBSOCKET_INTEGRATION] ✅ WebSocket trading engine created")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error creating WebSocket engine: {e}")
            return False
    
    async def _create_trade_executor_adapter(self) -> bool:
        """Create trade executor adapter for seamless integration"""
        try:
            logger.info("[WEBSOCKET_INTEGRATION] Creating trade executor adapter...")
            
            # Get existing trade executor
            original_executor = None
            if hasattr(self.bot, 'trade_executor'):
                original_executor = self.bot.trade_executor
            elif hasattr(self.bot, 'enhanced_trade_executor'):
                original_executor = self.bot.enhanced_trade_executor
            
            if not original_executor:
                logger.error("[WEBSOCKET_INTEGRATION] No existing trade executor found in bot")
                return False
            
            self.original_executor = original_executor
            
            # Create adapter
            self.trade_executor_adapter = WebSocketTradeExecutorAdapter(
                websocket_engine=self.websocket_engine,
                rest_executor=original_executor
            )
            
            # Configure adapter preferences
            self.trade_executor_adapter.prefer_websocket = self.config.prefer_websocket
            
            self.integration_status['adapter_created'] = True
            
            logger.info("[WEBSOCKET_INTEGRATION] ✅ Trade executor adapter created")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error creating adapter: {e}")
            return False
    
    async def _integrate_with_bot(self) -> bool:
        """Integrate WebSocket trading with bot's trading pipeline"""
        try:
            logger.info("[WEBSOCKET_INTEGRATION] Integrating with bot's trading pipeline...")
            
            # Replace bot's trade executor with our adapter
            if hasattr(self.bot, 'trade_executor'):
                self.bot.trade_executor = self.trade_executor_adapter
                logger.info("[WEBSOCKET_INTEGRATION] Replaced bot.trade_executor with WebSocket adapter")
            
            if hasattr(self.bot, 'enhanced_trade_executor'):
                self.bot.enhanced_trade_executor = self.trade_executor_adapter
                logger.info("[WEBSOCKET_INTEGRATION] Replaced bot.enhanced_trade_executor with WebSocket adapter")
            
            # Add WebSocket engine reference to bot for direct access
            self.bot.websocket_trading_engine = self.websocket_engine
            
            # Set up execution callbacks for performance monitoring
            if self.config.performance_monitoring:
                self.websocket_engine.add_execution_callback(self._track_execution_performance)
            
            logger.info("[WEBSOCKET_INTEGRATION] ✅ Bot integration complete")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error integrating with bot: {e}")
            return False
    
    async def _start_performance_monitoring(self) -> None:
        """Start performance monitoring task"""
        try:
            logger.info("[WEBSOCKET_INTEGRATION] Starting performance monitoring...")
            
            # Create monitoring task
            self.monitoring_task = asyncio.create_task(self._performance_monitoring_loop())
            
            logger.info("[WEBSOCKET_INTEGRATION] ✅ Performance monitoring started")
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error starting performance monitoring: {e}")
    
    async def _performance_monitoring_loop(self) -> None:
        """Performance monitoring loop"""
        try:
            while self.integration_status['integration_active']:
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
                # Collect metrics
                await self._collect_performance_metrics()
                
                # Log performance summary
                self._log_performance_summary()
                
                # Check for optimization opportunities
                await self._check_optimization_opportunities()
                
        except asyncio.CancelledError:
            logger.info("[WEBSOCKET_INTEGRATION] Performance monitoring stopped")
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Performance monitoring error: {e}")
    
    async def _collect_performance_metrics(self) -> None:
        """Collect current performance metrics"""
        try:
            if self.websocket_engine:
                ws_metrics = self.websocket_engine.get_metrics()
                
                # Update performance metrics
                self.performance_metrics['websocket_trades'] = ws_metrics.get('orders_filled', 0)
                
                # Calculate success rate
                orders_placed = ws_metrics.get('orders_placed', 0)
                orders_filled = ws_metrics.get('orders_filled', 0)
                
                if orders_placed > 0:
                    self.performance_metrics['websocket_success_rate'] = orders_filled / orders_placed
                
                # Track latency
                latency = ws_metrics.get('websocket_latency_ms', 0)
                if latency > 0:
                    self.performance_metrics['websocket_latency_ms'].append(latency)
                    # Keep only last 100 measurements
                    if len(self.performance_metrics['websocket_latency_ms']) > 100:
                        self.performance_metrics['websocket_latency_ms'].pop(0)
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error collecting metrics: {e}")
    
    def _log_performance_summary(self) -> None:
        """Log performance summary"""
        try:
            ws_trades = self.performance_metrics['websocket_trades']
            rest_trades = self.performance_metrics['rest_trades']
            success_rate = self.performance_metrics['websocket_success_rate']
            fallback_events = self.performance_metrics['fallback_events']
            
            # Calculate average latency
            ws_latencies = self.performance_metrics['websocket_latency_ms']
            avg_ws_latency = sum(ws_latencies) / len(ws_latencies) if ws_latencies else 0
            
            uptime = time.time() - self.performance_metrics['integration_start_time']
            
            logger.info(
                f"[WEBSOCKET_INTEGRATION] Performance Summary: "
                f"WS trades: {ws_trades}, REST trades: {rest_trades}, "
                f"Success rate: {success_rate:.2%}, Fallback events: {fallback_events}, "
                f"Avg WS latency: {avg_ws_latency:.1f}ms, Uptime: {uptime/3600:.1f}h"
            )
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error logging performance summary: {e}")
    
    async def _check_optimization_opportunities(self) -> None:
        """Check for optimization opportunities"""
        try:
            # Check if WebSocket success rate is too low
            success_rate = self.performance_metrics['websocket_success_rate']
            if success_rate < 0.8 and self.config.auto_fallback_on_failure:
                logger.warning(f"[WEBSOCKET_INTEGRATION] Low WebSocket success rate ({success_rate:.2%}), considering REST preference")
                
                # Temporarily prefer REST
                if self.trade_executor_adapter:
                    self.trade_executor_adapter.prefer_websocket = False
                    
                    # Re-enable WebSocket after some time
                    asyncio.create_task(self._re_enable_websocket_after_delay(300))  # 5 minutes
            
            # Check for high latency
            ws_latencies = self.performance_metrics['websocket_latency_ms']
            if ws_latencies:
                avg_latency = sum(ws_latencies) / len(ws_latencies)
                if avg_latency > 1000:  # 1 second
                    logger.warning(f"[WEBSOCKET_INTEGRATION] High WebSocket latency ({avg_latency:.1f}ms)")
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error checking optimization opportunities: {e}")
    
    async def _re_enable_websocket_after_delay(self, delay_seconds: int) -> None:
        """Re-enable WebSocket preference after delay"""
        try:
            await asyncio.sleep(delay_seconds)
            
            if self.trade_executor_adapter:
                self.trade_executor_adapter.prefer_websocket = True
                logger.info("[WEBSOCKET_INTEGRATION] WebSocket preference re-enabled")
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error re-enabling WebSocket: {e}")
    
    async def _track_execution_performance(self, execution_update) -> None:
        """Track execution performance metrics"""
        try:
            # Update execution counters
            self.performance_metrics['websocket_trades'] += 1
            
            # Track timing if available
            if hasattr(execution_update, 'timestamp'):
                # Calculate latency (simplified)
                current_time = time.time()
                latency_ms = (current_time - execution_update.timestamp) * 1000
                self.performance_metrics['websocket_latency_ms'].append(latency_ms)
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error tracking execution performance: {e}")
    
    async def _cleanup_failed_integration(self) -> None:
        """Clean up after failed integration"""
        try:
            logger.info("[WEBSOCKET_INTEGRATION] Cleaning up after failed integration...")
            
            # Reset bot's trade executor to original if we changed it
            if self.original_executor:
                if hasattr(self.bot, 'trade_executor'):
                    self.bot.trade_executor = self.original_executor
                if hasattr(self.bot, 'enhanced_trade_executor'):
                    self.bot.enhanced_trade_executor = self.original_executor
            
            # Clean up WebSocket engine
            if self.websocket_engine:
                await self.websocket_engine.shutdown()
            
            # Reset status
            self.integration_status['integration_active'] = False
            
            logger.info("[WEBSOCKET_INTEGRATION] ✅ Cleanup complete")
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error during cleanup: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown WebSocket trading integration"""
        try:
            logger.info("[WEBSOCKET_INTEGRATION] Shutting down...")
            
            # Stop performance monitoring
            if hasattr(self, 'monitoring_task') and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Restore original trade executor
            if self.original_executor:
                if hasattr(self.bot, 'trade_executor'):
                    self.bot.trade_executor = self.original_executor
                if hasattr(self.bot, 'enhanced_trade_executor'):
                    self.bot.enhanced_trade_executor = self.original_executor
            
            # Shutdown WebSocket engine
            if self.websocket_engine:
                await self.websocket_engine.shutdown()
            
            # Update status
            self.integration_status['integration_active'] = False
            
            logger.info("[WEBSOCKET_INTEGRATION] ✅ Shutdown complete")
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error during shutdown: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get integration status"""
        return {
            'integration_status': self.integration_status.copy(),
            'performance_metrics': self.performance_metrics.copy(),
            'config': {
                'enabled': self.config.enabled,
                'prefer_websocket': self.config.prefer_websocket,
                'max_concurrent_orders': self.config.max_concurrent_orders,
                'order_timeout_seconds': self.config.order_timeout_seconds,
                'auto_fallback_on_failure': self.config.auto_fallback_on_failure
            },
            'websocket_engine_metrics': self.websocket_engine.get_metrics() if self.websocket_engine else {}
        }
    
    async def force_websocket_preference(self, prefer_websocket: bool) -> None:
        """Force WebSocket preference setting"""
        try:
            self.config.prefer_websocket = prefer_websocket
            
            if self.trade_executor_adapter:
                self.trade_executor_adapter.prefer_websocket = prefer_websocket
                
            logger.info(f"[WEBSOCKET_INTEGRATION] WebSocket preference set to: {prefer_websocket}")
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error setting WebSocket preference: {e}")
    
    async def retry_websocket_initialization(self) -> bool:
        """Retry WebSocket initialization"""
        try:
            if self.integration_status['initialization_attempts'] >= self.config.websocket_retry_attempts:
                logger.warning("[WEBSOCKET_INTEGRATION] Maximum retry attempts reached")
                return False
            
            logger.info("[WEBSOCKET_INTEGRATION] Retrying WebSocket initialization...")
            return await self.initialize()
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_INTEGRATION] Error during retry: {e}")
            return False


# Utility functions for easy integration
async def setup_websocket_trading(bot_instance, config: WebSocketTradingConfig = None) -> Optional[WebSocketTradingIntegration]:
    """
    Set up WebSocket trading integration for a bot instance.
    
    Args:
        bot_instance: Main bot instance
        config: WebSocket trading configuration
        
    Returns:
        WebSocketTradingIntegration instance if successful, None otherwise
    """
    try:
        logger.info("[WEBSOCKET_INTEGRATION] Setting up WebSocket trading integration...")
        
        # Create integration instance
        integration = WebSocketTradingIntegration(bot_instance, config)
        
        # Initialize integration
        if await integration.initialize():
            logger.info("[WEBSOCKET_INTEGRATION] ✅ WebSocket trading setup complete")
            return integration
        else:
            logger.error("[WEBSOCKET_INTEGRATION] WebSocket trading setup failed")
            return None
            
    except Exception as e:
        logger.error(f"[WEBSOCKET_INTEGRATION] Error setting up WebSocket trading: {e}")
        return None


def create_websocket_trading_config(
    enabled: bool = True,
    prefer_websocket: bool = True,
    max_concurrent_orders: int = 10,
    order_timeout_seconds: int = 60,
    auto_fallback_on_failure: bool = True,
    performance_monitoring: bool = True
) -> WebSocketTradingConfig:
    """
    Create WebSocket trading configuration.
    
    Args:
        enabled: Enable WebSocket trading
        prefer_websocket: Prefer WebSocket over REST
        max_concurrent_orders: Maximum concurrent orders
        order_timeout_seconds: Order timeout in seconds
        auto_fallback_on_failure: Auto fallback to REST on failures
        performance_monitoring: Enable performance monitoring
        
    Returns:
        WebSocketTradingConfig instance
    """
    return WebSocketTradingConfig(
        enabled=enabled,
        prefer_websocket=prefer_websocket,
        max_concurrent_orders=max_concurrent_orders,
        order_timeout_seconds=order_timeout_seconds,
        auto_fallback_on_failure=auto_fallback_on_failure,
        performance_monitoring=performance_monitoring
    )