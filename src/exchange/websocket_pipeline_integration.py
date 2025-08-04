"""
WebSocket Pipeline Integration
============================

Integration layer that connects the unified WebSocket V2 data pipeline
with the existing bot architecture. Provides seamless integration with
balance managers, trading engines, and strategy components.

Features:
- Automatic component discovery and registration
- Backward compatibility with existing callback systems
- Performance monitoring and health checks
- Circuit breaker coordination
- Error recovery and fallback mechanisms
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
import weakref

from .unified_websocket_data_pipeline import (
    UnifiedWebSocketDataPipeline, 
    MessageQueueConfig, 
    PerformanceConfig,
    DataChannel
)

logger = logging.getLogger(__name__)


class WebSocketPipelineIntegrator:
    """
    Integration layer for the unified WebSocket data pipeline
    
    Handles automatic component discovery, registration, and coordination
    with the existing bot architecture.
    """
    
    def __init__(self, websocket_manager, bot_instance=None):
        """
        Initialize the pipeline integrator
        
        Args:
            websocket_manager: WebSocket V2 manager instance
            bot_instance: Main bot instance for component discovery
        """
        self.websocket_manager = websocket_manager
        self.bot_instance = bot_instance
        
        # Create pipeline with optimized configuration
        queue_config = MessageQueueConfig(
            max_size=2000,  # Large buffer for high-frequency data
            timeout_seconds=0.5,  # Fast processing
            priority_multiplier=1.5,  # Reasonable priority scaling
            enable_deduplication=True,
            dedup_window_seconds=0.05  # Very short dedup window
        )
        
        performance_config = PerformanceConfig(
            enable_metrics=True,
            metrics_interval_seconds=60.0,  # Stats every minute
            max_processing_time_ms=10.0,  # Alert on 10ms+ processing
            enable_latency_tracking=True,
            memory_usage_threshold_mb=200.0
        )
        
        self.pipeline = UnifiedWebSocketDataPipeline(
            websocket_manager=websocket_manager,
            queue_config=queue_config,
            performance_config=performance_config
        )
        
        # Integration state
        self._integrated = False
        self._discovered_components = {}
        self._health_check_task = None
        
        logger.info("[INTEGRATION] WebSocket pipeline integrator initialized")
    
    async def integrate_with_bot(self, bot_instance=None) -> bool:
        """
        Integrate pipeline with bot components
        
        Args:
            bot_instance: Bot instance to discover components from
            
        Returns:
            True if integration successful
        """
        try:
            if bot_instance:
                self.bot_instance = bot_instance
            
            if not self.bot_instance:
                logger.warning("[INTEGRATION] No bot instance provided for component discovery")
                return False
            
            logger.info("[INTEGRATION] Starting bot integration...")
            
            # Discover and register components
            await self._discover_and_register_components()
            
            # Setup WebSocket manager integration
            await self._setup_websocket_integration()
            
            # Start the pipeline
            await self.pipeline.start()
            
            # Start health monitoring
            self._health_check_task = asyncio.create_task(self._health_monitor())
            
            self._integrated = True
            logger.info("[INTEGRATION] Bot integration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"[INTEGRATION] Failed to integrate with bot: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the pipeline integration"""
        logger.info("[INTEGRATION] Shutting down pipeline integration...")
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.pipeline:
            await self.pipeline.stop()
        
        self._integrated = False
        logger.info("[INTEGRATION] Pipeline integration shutdown complete")
    
    async def _discover_and_register_components(self):
        """Discover and register bot components with the pipeline"""
        try:
            components_registered = 0
            
            # Register balance manager
            if hasattr(self.bot_instance, 'balance_manager'):
                balance_manager = self.bot_instance.balance_manager
                self.pipeline.register_balance_manager(balance_manager, "primary")
                self._discovered_components['balance_manager'] = weakref.ref(balance_manager)
                components_registered += 1
                logger.info("[INTEGRATION] Registered primary balance manager")
            
            # Register additional balance managers
            if hasattr(self.bot_instance, 'balance_manager_v2'):
                balance_manager_v2 = self.bot_instance.balance_manager_v2
                self.pipeline.register_balance_manager(balance_manager_v2, "v2")
                self._discovered_components['balance_manager_v2'] = weakref.ref(balance_manager_v2)
                components_registered += 1
                logger.info("[INTEGRATION] Registered V2 balance manager")
            
            # Register trading engine/executor
            if hasattr(self.bot_instance, 'trade_executor'):
                trade_executor = self.bot_instance.trade_executor
                self.pipeline.register_trading_engine(trade_executor, "primary")
                self._discovered_components['trade_executor'] = weakref.ref(trade_executor)
                components_registered += 1
                logger.info("[INTEGRATION] Registered trade executor")
            
            # Register strategy manager
            if hasattr(self.bot_instance, 'strategy_manager'):
                strategy_manager = self.bot_instance.strategy_manager
                self.pipeline.register_strategy_manager(strategy_manager, "primary")
                self._discovered_components['strategy_manager'] = weakref.ref(strategy_manager)
                components_registered += 1
                logger.info("[INTEGRATION] Registered strategy manager")
            
            # Register functional strategy manager
            if hasattr(self.bot_instance, 'functional_strategy_manager'):
                functional_manager = self.bot_instance.functional_strategy_manager
                self.pipeline.register_strategy_manager(functional_manager, "functional")
                self._discovered_components['functional_strategy_manager'] = weakref.ref(functional_manager)
                components_registered += 1
                logger.info("[INTEGRATION] Registered functional strategy manager")
            
            # Register risk manager/guardian
            if hasattr(self.bot_instance, 'critical_error_guardian'):
                guardian = self.bot_instance.critical_error_guardian
                self.pipeline.register_risk_manager(guardian, "guardian")
                self._discovered_components['critical_error_guardian'] = weakref.ref(guardian)
                components_registered += 1
                logger.info("[INTEGRATION] Registered critical error guardian")
            
            # Register opportunity scanner
            if hasattr(self.bot_instance, 'opportunity_scanner'):
                scanner = self.bot_instance.opportunity_scanner
                self.pipeline.register_custom_component(
                    "opportunity_scanner", 
                    scanner, 
                    [DataChannel.TICKER, DataChannel.ORDERBOOK]
                )
                self._discovered_components['opportunity_scanner'] = weakref.ref(scanner)
                components_registered += 1
                logger.info("[INTEGRATION] Registered opportunity scanner")
            
            # Register HFT signal processor
            if hasattr(self.bot_instance, 'hft_signal_processor'):
                hft_processor = self.bot_instance.hft_signal_processor
                self.pipeline.register_custom_component(
                    "hft_signal_processor",
                    hft_processor,
                    [DataChannel.TICKER, DataChannel.ORDERBOOK, DataChannel.TRADES]
                )
                self._discovered_components['hft_signal_processor'] = weakref.ref(hft_processor)
                components_registered += 1
                logger.info("[INTEGRATION] Registered HFT signal processor")
            
            # Register learning manager
            if hasattr(self.bot_instance, 'learning_manager'):
                learning_manager = self.bot_instance.learning_manager
                self.pipeline.register_custom_component(
                    "learning_manager",
                    learning_manager,
                    [DataChannel.TICKER, DataChannel.EXECUTION, DataChannel.TRADES]
                )
                self._discovered_components['learning_manager'] = weakref.ref(learning_manager)
                components_registered += 1
                logger.info("[INTEGRATION] Registered learning manager")
            
            logger.info(f"[INTEGRATION] Discovered and registered {components_registered} components")
            
        except Exception as e:
            logger.error(f"[INTEGRATION] Error discovering components: {e}")
    
    async def _setup_websocket_integration(self):
        """Setup integration with WebSocket manager"""
        try:
            # Set the manager reference in WebSocket manager for balance updates
            if hasattr(self.websocket_manager, 'set_manager'):
                self.websocket_manager.set_manager(self.bot_instance)
                logger.info("[INTEGRATION] Set bot manager reference in WebSocket manager")
            
            # Override WebSocket manager's message handling to use pipeline
            if hasattr(self.websocket_manager, 'bot'):
                original_on_message = self.websocket_manager.bot.on_message
                
                async def enhanced_on_message(message):
                    """Enhanced message handler that uses pipeline"""
                    try:
                        # Process through pipeline first
                        await self.pipeline.process_raw_message(message)
                        
                        # Also call original handler for backward compatibility
                        if original_on_message:
                            await original_on_message(message)
                    
                    except Exception as e:
                        logger.error(f"[INTEGRATION] Error in enhanced message handler: {e}")
                        # Fallback to original handler
                        if original_on_message:
                            try:
                                await original_on_message(message)
                            except Exception as fallback_error:
                                logger.error(f"[INTEGRATION] Fallback handler also failed: {fallback_error}")
                
                # Replace the message handler
                self.websocket_manager.bot.on_message = enhanced_on_message
                logger.info("[INTEGRATION] Enhanced WebSocket message handling with pipeline")
            
        except Exception as e:
            logger.error(f"[INTEGRATION] Error setting up WebSocket integration: {e}")
    
    async def _health_monitor(self):
        """Monitor pipeline and component health"""
        while self._integrated:
            try:
                await asyncio.sleep(30.0)  # Check every 30 seconds
                
                # Check pipeline health
                stats = self.pipeline.get_pipeline_stats()
                
                # Log health summary
                total_processed = sum(stats.get('messages_processed', {}).values())
                total_dropped = sum(stats.get('messages_dropped', {}).values())
                total_errors = sum(stats.get('errors', {}).values())
                
                if total_processed > 0:
                    drop_rate = total_dropped / total_processed * 100
                    error_rate = total_errors / total_processed * 100
                    
                    if drop_rate > 5.0:  # Alert if >5% drop rate
                        logger.warning(f"[INTEGRATION] High message drop rate: {drop_rate:.2f}%")
                    
                    if error_rate > 1.0:  # Alert if >1% error rate
                        logger.warning(f"[INTEGRATION] High error rate: {error_rate:.2f}%")
                    
                    logger.debug(
                        f"[INTEGRATION] Health: {total_processed} processed, "
                        f"{drop_rate:.2f}% dropped, {error_rate:.2f}% errors"
                    )
                
                # Check component health
                dead_components = []
                for name, ref in self._discovered_components.items():
                    if ref() is None:
                        dead_components.append(name)
                
                if dead_components:
                    logger.warning(f"[INTEGRATION] Dead component references: {dead_components}")
                
                # Check queue health
                queue_sizes = stats.get('queue_sizes', {})
                for priority, size in queue_sizes.items():
                    if size > 1500:  # Alert if queue getting full
                        logger.warning(f"[INTEGRATION] High queue size for {priority}: {size}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[INTEGRATION] Error in health monitor: {e}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration status and health information"""
        status = {
            'integrated': self._integrated,
            'components_discovered': len(self._discovered_components),
            'pipeline_running': self.pipeline._running if self.pipeline else False,
            'websocket_connected': getattr(self.websocket_manager, 'is_connected', False),
            'health_monitoring': self._health_check_task is not None and not self._health_check_task.done()
        }
        
        # Add component status
        status['components'] = {}
        for name, ref in self._discovered_components.items():
            component = ref()
            status['components'][name] = {
                'alive': component is not None,
                'type': type(component).__name__ if component else 'None'
            }
        
        # Add pipeline stats if available
        if self.pipeline:
            status['pipeline_stats'] = self.pipeline.get_pipeline_stats()
        
        return status
    
    async def manual_route_balance_update(self, balance_data: Dict[str, Any]) -> bool:
        """Manually route balance update through pipeline"""
        if not self._integrated:
            logger.warning("[INTEGRATION] Not integrated, cannot route balance update")
            return False
        
        return await self.pipeline.route_balance_update(balance_data)
    
    async def manual_route_ticker_update(self, symbol: str, ticker_data: Dict[str, Any]) -> bool:
        """Manually route ticker update through pipeline"""
        if not self._integrated:
            logger.warning("[INTEGRATION] Not integrated, cannot route ticker update")
            return False
        
        ticker_data['symbol'] = symbol
        return await self.pipeline.route_ticker_update(ticker_data)
    
    async def manual_route_execution_update(self, execution_data: Dict[str, Any]) -> bool:
        """Manually route execution update through pipeline"""
        if not self._integrated:
            logger.warning("[INTEGRATION] Not integrated, cannot route execution update")
            return False
        
        return await self.pipeline.route_execution_update(execution_data)
    
    def register_additional_component(self, name: str, component: Any, channels: List[str]):
        """Register additional component with the pipeline"""
        if not self._integrated:
            logger.warning("[INTEGRATION] Not integrated, cannot register component")
            return False
        
        try:
            # Convert string channels to DataChannel enums
            data_channels = []
            for channel_str in channels:
                if hasattr(DataChannel, channel_str.upper()):
                    data_channels.append(getattr(DataChannel, channel_str.upper()))
                else:
                    # Try to find by value
                    for dc in DataChannel:
                        if dc.value == channel_str.lower():
                            data_channels.append(dc)
                            break
            
            if data_channels:
                self.pipeline.register_custom_component(name, component, data_channels)
                self._discovered_components[name] = weakref.ref(component)
                logger.info(f"[INTEGRATION] Registered additional component: {name}")
                return True
            else:
                logger.error(f"[INTEGRATION] No valid channels found for {name}: {channels}")
                return False
        
        except Exception as e:
            logger.error(f"[INTEGRATION] Error registering component {name}: {e}")
            return False


# Convenience function for easy integration
async def setup_websocket_pipeline(websocket_manager, bot_instance) -> Optional[WebSocketPipelineIntegrator]:
    """
    Convenience function to setup WebSocket pipeline integration
    
    Args:
        websocket_manager: WebSocket V2 manager
        bot_instance: Main bot instance
        
    Returns:
        WebSocketPipelineIntegrator instance if successful, None otherwise
    """
    try:
        logger.info("[INTEGRATION] Setting up WebSocket pipeline integration...")
        
        integrator = WebSocketPipelineIntegrator(websocket_manager, bot_instance)
        success = await integrator.integrate_with_bot()
        
        if success:
            logger.info("[INTEGRATION] WebSocket pipeline integration setup complete")
            return integrator
        else:
            logger.error("[INTEGRATION] Failed to setup WebSocket pipeline integration")
            return None
    
    except Exception as e:
        logger.error(f"[INTEGRATION] Error setting up WebSocket pipeline: {e}")
        return None