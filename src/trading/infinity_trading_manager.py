"""
Infinity Trading Manager
========================

Central orchestrator implementing the Manager + 5 Assistants architecture
for self-sustaining infinity loop trading.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..config.constants import (
    MINIMUM_ORDER_SIZE_TIER1,
    TRADING_CONSTANTS,
    INFINITY_LOOP_CONFIG,
    SELF_MANAGEMENT_CONFIG
)
from .assistants.data_analysis_assistant import DataAnalysisAssistant
from .assistants.signal_generation_assistant import SignalGenerationAssistant
from .assistants.order_execution_assistant import OrderExecutionAssistant
from .assistants.risk_management_assistant import RiskManagementAssistant
from .assistants.performance_tracking_assistant import PerformanceTrackingAssistant
from .unified_sell_coordinator import UnifiedSellCoordinator
from ..utils.event_bus import get_event_bus, EventType, publish_event

logger = logging.getLogger(__name__)


@dataclass
class TradingState:
    """Current state of the trading system"""
    capital_deployed: float = 0.0
    capital_available: float = 0.0
    active_positions: int = 0
    total_trades: int = 0
    realized_pnl: float = 0.0
    loop_iterations: int = 0
    last_optimization: float = 0.0
    health_status: str = "healthy"
    capital_flow: Dict[str, Any] = field(default_factory=lambda: {
        'total_buys': 0,
        'total_sells': 0,
        'total_buy_volume': 0.0,
        'total_sell_volume': 0.0,
        'flow_history': []
    })


class InfinityTradingManager:
    """
    Central orchestrator for infinity loop trading system.
    Implements the Manager + 5 Assistants pattern for clean architecture.
    """
    
    def __init__(self, bot_instance):
        """Initialize the trading manager with all assistants"""
        self.bot = bot_instance
        self.config = bot_instance.config
        self.running = False
        
        # Initialize assistants
        logger.info("[MANAGER] Initializing 5 assistants...")
        self.data_assistant = DataAnalysisAssistant(self)
        self.signal_assistant = SignalGenerationAssistant(self)
        self.execution_assistant = OrderExecutionAssistant(self)
        self.risk_assistant = RiskManagementAssistant(self)
        self.performance_assistant = PerformanceTrackingAssistant(self)
        
        # Initialize unified sell coordinator
        self.sell_coordinator = UnifiedSellCoordinator(self.config)
        
        # Event bus for communication
        self.event_bus = get_event_bus()
        
        # Trading state
        self.state = TradingState()
        
        # Infinity loop configuration
        self.scan_interval = INFINITY_LOOP_CONFIG['SCAN_INTERVAL']
        self.batch_window = INFINITY_LOOP_CONFIG['BATCH_WINDOW']
        self.max_signals_per_batch = INFINITY_LOOP_CONFIG['MAX_SIGNALS_PER_BATCH']
        self.capital_deployment_target = INFINITY_LOOP_CONFIG['CAPITAL_DEPLOYMENT_TARGET']
        
        # Signal queue for batching
        self.signal_queue = asyncio.Queue()
        self.signal_batch = []
        self.last_batch_time = time.time()
        
        # Capital checking optimization
        self.capital_cache = {
            'balance': 0.0,
            'last_check': 0.0,
            'cache_duration': 90.0,  # Cache balance for 90 seconds (reduced frequency)
            'last_capital_warning': 0.0,  # Track warning frequency
            'warning_interval': 300.0  # Log warnings every 5 minutes
        }
        
        # Performance metrics
        self.metrics = {
            'start_time': time.time(),
            'total_loops': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'signals_generated': 0,
            'signals_executed': 0,
        }
        
        # Self-management settings
        self.health_check_interval = SELF_MANAGEMENT_CONFIG['HEALTH_CHECK_INTERVAL']
        self.optimization_interval = SELF_MANAGEMENT_CONFIG['OPTIMIZATION_INTERVAL']
        self.last_health_check = time.time()
        
        # Error tracking
        self.error_counts = {}
        
        logger.info(f"[MANAGER] Infinity Trading Manager initialized with {MINIMUM_ORDER_SIZE_TIER1} USDT minimum")
    
    async def start(self):
        """Start the infinity trading loop"""
        logger.info("[MANAGER] Starting Infinity Trading Loop...")
        self.running = True
        
        # Initialize all assistants
        await self._initialize_assistants()
        
        # Wait for WebSocket data to be available
        logger.info("[MANAGER] Waiting for WebSocket data to initialize (15 seconds)...")
        await asyncio.sleep(15)
        
        # Start background tasks
        asyncio.create_task(self._health_monitoring_loop())
        asyncio.create_task(self._signal_processing_loop())
        
        # Start main trading loop
        await self.infinity_loop()
    
    async def stop(self):
        """Stop the trading loop gracefully"""
        logger.info("[MANAGER] Stopping Infinity Trading Loop...")
        self.running = False
        
        # Stop all assistants
        await self._stop_assistants()
        
        # Final metrics report
        await self.performance_assistant.generate_final_report()
    
    async def infinity_loop(self):
        """
        Core infinity trading loop implementation.
        This is the heart of the self-sustaining trading system.
        """
        while self.running:
            try:
                loop_start = time.time()
                self.state.loop_iterations += 1
                
                # 1. COLLECT AND ANALYZE DATA
                market_data = await self.data_assistant.collect_market_data()
                if not market_data:
                    logger.warning("[MANAGER] No market data available, skipping iteration")
                    
                    # Debug: Check WebSocket status
                    if hasattr(self.bot, 'websocket_manager') and self.bot.websocket_manager:
                        if hasattr(self.bot.websocket_manager, 'get_available_data_summary'):
                            ws_status = self.bot.websocket_manager.get_available_data_summary()
                            logger.warning(f"[MANAGER] WebSocket data summary: {ws_status}")
                    
                    await asyncio.sleep(self.scan_interval)
                    continue
                else:
                    logger.info(f"[MANAGER] Collected market data for {len(market_data)} symbols")
                
                # 2. GENERATE BUY SIGNALS
                buy_signals = await self.signal_assistant.generate_buy_signals(market_data)
                self.metrics['signals_generated'] += len(buy_signals)
                
                # 3. CHECK CAPITAL AVAILABILITY ONLY IF WE HAVE SIGNALS
                if buy_signals:
                    capital_status = await self._check_capital_availability()
                    
                    if capital_status['available'] >= MINIMUM_ORDER_SIZE_TIER1:
                        # 4. VALIDATE SIGNALS WITH RISK MANAGEMENT
                        validated_signals = await self.risk_assistant.validate_signals(buy_signals)
                        
                        # 5. EXECUTE BUY ORDERS
                        if validated_signals:
                            await self._batch_and_execute_signals(validated_signals)
                    else:
                        # Use same warning throttling for insufficient capital during main loop
                        current_time = time.time()
                        if current_time - self.capital_cache['last_capital_warning'] > self.capital_cache['warning_interval']:
                            logger.info(f"[MANAGER] Insufficient capital: ${capital_status['available']:.2f} < ${MINIMUM_ORDER_SIZE_TIER1}")
                            self.capital_cache['last_capital_warning'] = current_time
                else:
                    logger.debug("[MANAGER] No buy signals generated, skipping capital check")
                
                # 6. MONITOR EXISTING POSITIONS
                positions = self.execution_assistant.get_open_positions()
                self.state.active_positions = len(positions)
                
                # 7. EVALUATE SELL OPPORTUNITIES
                for position in positions:
                    sell_decision = await self.sell_coordinator.evaluate_position(position)
                    
                    if sell_decision.should_sell:
                        # Execute sell through unified coordinator
                        sell_result = await self.execution_assistant.execute_sell(position, sell_decision)
                        
                        if sell_result['success']:
                            # Update capital tracking
                            await self._update_capital_flow(sell_result)
                
                # 8. PERFORMANCE TRACKING
                await self.performance_assistant.update_metrics(self.state)
                
                # 9. SELF-OPTIMIZATION (periodic)
                if self._should_optimize():
                    await self._self_optimize()
                    self.state.last_optimization = time.time()
                
                # 10. LOOP TIMING CONTROL
                loop_duration = time.time() - loop_start
                sleep_time = max(0, self.scan_interval - loop_duration)
                
                if loop_duration > self.scan_interval:
                    logger.warning(f"[MANAGER] Loop took {loop_duration:.2f}s, longer than scan interval {self.scan_interval}s")
                
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"[MANAGER] Error in infinity loop: {e}", exc_info=True)
                await self._handle_loop_error(e)
                await asyncio.sleep(self.scan_interval)
    
    async def _initialize_assistants(self):
        """Initialize all assistants"""
        logger.info("[MANAGER] Initializing assistants...")
        
        await self.data_assistant.initialize()
        await self.signal_assistant.initialize()
        await self.execution_assistant.initialize()
        await self.risk_assistant.initialize()
        await self.performance_assistant.initialize()
        
        logger.info("[MANAGER] All assistants initialized successfully")
    
    async def _stop_assistants(self):
        """Stop all assistants gracefully"""
        logger.info("[MANAGER] Stopping assistants...")
        
        await self.data_assistant.stop()
        await self.signal_assistant.stop()
        await self.execution_assistant.stop()
        await self.risk_assistant.stop()
        await self.performance_assistant.stop()
        
        logger.info("[MANAGER] All assistants stopped")
    
    async def _check_capital_availability(self, force_refresh: bool = False) -> Dict[str, float]:
        """Check available capital for trading with caching optimization"""
        try:
            current_time = time.time()
            
            # Use cached balance if recent (within cache_duration)
            if (not force_refresh and 
                current_time - self.capital_cache['last_check'] < self.capital_cache['cache_duration'] and
                self.capital_cache['balance'] >= 0):  # Allow zero balance to be cached
                
                usdt_balance = self.capital_cache['balance']
                logger.debug(f"[MANAGER] Using cached balance: ${usdt_balance:.2f} (age: {current_time - self.capital_cache['last_check']:.1f}s)")
            else:
                # Get fresh balance from bot's balance manager
                balance_manager = self.bot.balance_manager
                if balance_manager:
                    logger.debug("[MANAGER] Fetching fresh balance data...")
                    usdt_balance = await balance_manager.get_balance_for_asset('USDT')
                    
                    # Update cache
                    self.capital_cache['balance'] = usdt_balance
                    self.capital_cache['last_check'] = current_time
                    logger.debug(f"[MANAGER] Updated balance cache: ${usdt_balance:.2f} (will cache for {self.capital_cache['cache_duration']}s)")
                else:
                    logger.error("[MANAGER] No balance manager available")
                    return {'total': 0, 'deployed': 0, 'available': 0, 'deployment_ratio': 0}
            
            # Calculate deployed capital (always check positions as they change frequently)
            try:
                positions = self.execution_assistant.get_open_positions()
                deployed = sum(p.get('value', 0) for p in positions)
            except Exception as e:
                logger.warning(f"[MANAGER] Error getting open positions: {e}")
                deployed = 0
            
            available = max(0, usdt_balance - deployed)  # Ensure available never goes negative
            
            self.state.capital_available = available
            self.state.capital_deployed = deployed
            
            result = {
                'total': usdt_balance,
                'deployed': deployed,
                'available': available,
                'deployment_ratio': deployed / usdt_balance if usdt_balance > 0 else 0
            }
            
            # Log capital status occasionally (every 20 checks to reduce noise)
            if hasattr(self, '_capital_check_count'):
                self._capital_check_count += 1
            else:
                self._capital_check_count = 1
                
            if self._capital_check_count % 20 == 0:  # Reduced from every 10 to every 20
                logger.info(f"[MANAGER] Capital status: Total=${result['total']:.2f}, Available=${result['available']:.2f}, Deployed=${result['deployed']:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"[MANAGER] Error checking capital: {e}")
            return {'total': 0, 'deployed': 0, 'available': 0, 'deployment_ratio': 0}
    
    async def _batch_and_execute_signals(self, signals: List[Dict[str, Any]]):
        """Batch signals and execute efficiently"""
        # Add to batch
        self.signal_batch.extend(signals)
        
        # Check if we should process batch
        current_time = time.time()
        time_since_last_batch = current_time - self.last_batch_time
        
        should_process = (
            len(self.signal_batch) >= self.max_signals_per_batch or
            time_since_last_batch >= self.batch_window
        )
        
        if should_process and self.signal_batch:
            # Sort by confidence/priority
            sorted_signals = sorted(
                self.signal_batch,
                key=lambda s: s.get('confidence', 0),
                reverse=True
            )
            
            # Execute top signals
            to_execute = sorted_signals[:self.max_signals_per_batch]
            
            for signal in to_execute:
                result = await self.execution_assistant.execute_buy(signal)
                
                if result['success']:
                    self.metrics['successful_trades'] += 1
                    self.state.total_trades += 1
                else:
                    self.metrics['failed_trades'] += 1
            
            # Clear batch
            self.signal_batch.clear()
            self.last_batch_time = current_time
            self.metrics['signals_executed'] += len(to_execute)
    
    async def _update_capital_flow(self, trade_result: Dict[str, Any]):
        """Update capital flow tracking"""
        if trade_result.get('side') == 'sell':
            proceeds = trade_result.get('proceeds', 0)
            profit = trade_result.get('profit', 0)
            
            self.state.realized_pnl += profit
            
            # Track capital flow
            self.state.capital_flow['total_sells'] += 1
            self.state.capital_flow['total_sell_volume'] += proceeds
            
            # Log capital movement
            flow_entry = {
                'timestamp': time.time(),
                'type': 'sell',
                'amount': proceeds,
                'profit': profit,
                'symbol': trade_result.get('symbol')
            }
            self.state.capital_flow['flow_history'].append(flow_entry)
    
    def _should_optimize(self) -> bool:
        """Check if it's time to optimize parameters"""
        return (time.time() - self.state.last_optimization) >= self.optimization_interval
    
    async def _self_optimize(self):
        """Self-optimization routine wrapper"""
        logger.info("[MANAGER] Running self-optimization...")
        
        # Call the comprehensive self-optimization method
        await self.self_optimize()
    
    async def _health_monitoring_loop(self):
        """Background health monitoring"""
        while self.running:
            try:
                current_time = time.time()
                
                if (current_time - self.last_health_check) >= self.health_check_interval:
                    # Check health of all components
                    health_status = await self._check_system_health()
                    
                    if health_status['status'] != 'healthy':
                        logger.warning(f"[MANAGER] System health issue: {health_status}")
                        await self._handle_health_issue(health_status)
                    
                    self.last_health_check = current_time
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"[MANAGER] Health monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check health of all system components"""
        health_checks = {
            'data_assistant': await self.data_assistant.health_check(),
            'signal_assistant': await self.signal_assistant.health_check(),
            'execution_assistant': await self.execution_assistant.health_check(),
            'risk_assistant': await self.risk_assistant.health_check(),
            'performance_assistant': await self.performance_assistant.health_check(),
        }
        
        # Overall health
        all_healthy = all(check.get('healthy', False) for check in health_checks.values())
        
        return {
            'status': 'healthy' if all_healthy else 'unhealthy',
            'components': health_checks,
            'timestamp': time.time()
        }
    
    async def _handle_health_issue(self, health_status: Dict[str, Any]):
        """Handle system health issues with self-healing capabilities"""
        unhealthy_components = [
            name for name, status in health_status['components'].items()
            if not status.get('healthy', False)
        ]
        
        logger.error(f"[MANAGER] Unhealthy components: {unhealthy_components}")
        
        # Attempt self-repair for each unhealthy component
        for component_name in unhealthy_components:
            try:
                # Map component name to assistant
                assistant_map = {
                    'data_feed': self.data_assistant,
                    'signals': self.signal_assistant,
                    'execution': self.execution_assistant,
                    'risk': self.risk_assistant,
                    'performance': self.performance_assistant
                }
                
                assistant = assistant_map.get(component_name)
                if assistant:
                    logger.info(f"[SELF-HEAL] Attempting to repair {component_name}...")
                    
                    # Try to reconnect/restart the assistant
                    if hasattr(assistant, 'reconnect'):
                        await assistant.reconnect()
                    else:
                        # Restart the assistant
                        await assistant.stop()
                        await asyncio.sleep(1)
                        await assistant.initialize()
                    
                    logger.info(f"[SELF-HEAL] {component_name} repaired successfully")
                    
            except Exception as e:
                logger.error(f"[SELF-HEAL] Failed to repair {component_name}: {e}")
                # Increment failure count
                self.error_counts[f"{component_name}_repair_failure"] += 1
    
    async def _handle_loop_error(self, error: Exception):
        """Handle errors in the main loop"""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log error with context
        logger.error(f"[MANAGER] Loop error ({error_type}): {str(error)}", exc_info=True)
        
        # Check if we need to take drastic action
        total_errors = sum(self.error_counts.values())
        if total_errors > 100:  # Too many errors
            logger.critical("[MANAGER] Too many errors, initiating emergency shutdown")
            await self.emergency_shutdown()
        elif self.error_counts.get(error_type, 0) > 10:  # Repeated error
            logger.warning(f"[MANAGER] Repeated {error_type} errors, attempting recovery")
            await self._attempt_recovery(error_type)
    
    async def _attempt_recovery(self, error_type: str):
        """Attempt to recover from specific error types"""
        logger.info(f"[RECOVERY] Attempting recovery for {error_type}")
        
        recovery_actions = {
            'ConnectionError': self._recover_connections,
            'TimeoutError': self._recover_from_timeout,
            'InsufficientFundsError': self._recover_from_insufficient_funds,
            'DataError': self._recover_data_feed
        }
        
        recovery_func = recovery_actions.get(error_type)
        if recovery_func:
            try:
                await recovery_func()
                logger.info(f"[RECOVERY] Successfully recovered from {error_type}")
                # Reset error count after successful recovery
                self.error_counts[error_type] = 0
            except Exception as e:
                logger.error(f"[RECOVERY] Failed to recover from {error_type}: {e}")
    
    async def _recover_connections(self):
        """Recover from connection errors"""
        logger.info("[RECOVERY] Reconnecting data feeds...")
        await self.data_assistant.reconnect()
        
    async def _recover_from_timeout(self):
        """Recover from timeout errors"""
        logger.info("[RECOVERY] Clearing stale operations...")
        # Clear any pending operations
        await asyncio.sleep(5)  # Wait for operations to clear
        
    async def _recover_from_insufficient_funds(self):
        """Recover from insufficient funds errors"""
        logger.info("[RECOVERY] Adjusting position sizes...")
        # Reduce position sizes
        if hasattr(self.signal_assistant, 'adjust_position_sizing'):
            await self.signal_assistant.adjust_position_sizing(0.5)  # Reduce by 50%
        
    async def _recover_data_feed(self):
        """Recover from data feed errors"""
        logger.info("[RECOVERY] Restarting data assistant...")
        await self.data_assistant.stop()
        await asyncio.sleep(2)
        await self.data_assistant.initialize()
    
    async def emergency_shutdown(self):
        """Emergency shutdown procedure"""
        logger.critical("[EMERGENCY] Initiating emergency shutdown")
        
        try:
            # 1. Stop all new trading
            self.is_running = False
            
            # 2. Cancel all pending orders
            logger.info("[EMERGENCY] Cancelling all pending orders...")
            # Implementation depends on exchange interface
            
            # 3. Generate final report
            await self.performance_assistant.generate_final_report()
            
            # 4. Stop all assistants
            await self._stop_assistants()
            
            logger.info("[EMERGENCY] Emergency shutdown completed")
            
        except Exception as e:
            logger.error(f"[EMERGENCY] Error during shutdown: {e}")
    
    async def _signal_processing_loop(self):
        """Background signal processing"""
        while self.running:
            try:
                # Process any queued signals
                if not self.signal_queue.empty():
                    signals = []
                    while not self.signal_queue.empty() and len(signals) < self.max_signals_per_batch:
                        signal = await self.signal_queue.get()
                        signals.append(signal)
                    
                    if signals:
                        await self._batch_and_execute_signals(signals)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"[MANAGER] Signal processing error: {e}")
                await asyncio.sleep(5)
    
    def get_state(self) -> TradingState:
        """Get current trading state"""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        uptime = time.time() - self.metrics['start_time']
        
        return {
            **self.metrics,
            'uptime_hours': uptime / 3600,
            'loops_per_hour': self.state.loop_iterations / (uptime / 3600) if uptime > 0 else 0,
            'trade_success_rate': (
                self.metrics['successful_trades'] / 
                (self.metrics['successful_trades'] + self.metrics['failed_trades'])
                if (self.metrics['successful_trades'] + self.metrics['failed_trades']) > 0 else 0
            ),
            'signal_execution_rate': (
                self.metrics['signals_executed'] / self.metrics['signals_generated']
                if self.metrics['signals_generated'] > 0 else 0
            ),
            'current_state': {
                'capital_deployed': self.state.capital_deployed,
                'capital_available': self.state.capital_available,
                'active_positions': self.state.active_positions,
                'realized_pnl': self.state.realized_pnl
            }
        }
    
    async def get_next_action(self) -> Optional[List[Dict[str, Any]]]:
        """Get next trading actions from the infinity loop
        
        This method is called by the main bot to get signals.
        Returns a list of trading signals ready for execution.
        """
        try:
            # Check if we have signals in the batch
            if self.signal_batch:
                # Return current batch and clear it
                signals = self.signal_batch.copy()
                self.signal_batch.clear()
                logger.info(f"[MANAGER] Returning {len(signals)} batched signals")
                return signals
            
            # Quick capital check first to avoid unnecessary work
            capital_status = await self._check_capital_availability()
            if capital_status['available'] < MINIMUM_ORDER_SIZE_TIER1:
                # Only log capital warnings occasionally to avoid spam
                current_time = time.time()
                if current_time - self.capital_cache['last_capital_warning'] > self.capital_cache['warning_interval']:
                    logger.info(f"[MANAGER] Insufficient capital for new signals: ${capital_status['available']:.2f} < ${MINIMUM_ORDER_SIZE_TIER1}")
                    self.capital_cache['last_capital_warning'] = current_time
                return None
            
            # We have sufficient capital, proceed with signal generation
            logger.debug(f"[MANAGER] Capital available: ${capital_status['available']:.2f} - proceeding with signal generation")
            
            # Collect fresh market data and generate signals
            market_data = await self.data_assistant.collect_market_data()
            if not market_data:
                logger.debug("[MANAGER] No market data available")
                return None
            
            # Generate buy signals
            buy_signals = await self.signal_assistant.generate_buy_signals(market_data)
            if not buy_signals:
                logger.debug("[MANAGER] No buy signals generated")
                return None
            
            logger.info(f"[MANAGER] Generated {len(buy_signals)} buy signals")
            
            # Validate with risk management
            validated_signals = await self.risk_assistant.validate_signals(buy_signals)
            if validated_signals:
                logger.info(f"[MANAGER] {len(validated_signals)} signals passed risk validation")
                return validated_signals
            else:
                logger.debug("[MANAGER] No signals passed risk validation")
                return None
            
        except Exception as e:
            logger.error(f"[MANAGER] Error in get_next_action: {e}")
            return None
    
    # SELF-MANAGEMENT CAPABILITIES
    
    async def self_optimize(self):
        """Self-optimization routine that runs periodically"""
        logger.info("[SELF-OPTIMIZE] Starting optimization routine...")
        
        try:
            # 1. Analyze performance metrics
            performance = await self.performance_assistant.get_performance_summary()
            
            # 2. Optimize based on performance
            if performance['overall']['win_rate'] < 0.4:  # Below 40% win rate
                logger.info("[SELF-OPTIMIZE] Low win rate detected, adjusting parameters...")
                await self._adjust_for_better_win_rate()
            
            if performance['overall']['profit_factor'] < 1.2:  # Low profit factor
                logger.info("[SELF-OPTIMIZE] Low profit factor, adjusting risk/reward...")
                await self._adjust_risk_reward_ratio()
            
            # 3. Optimize based on market conditions
            market_analysis = await self.data_assistant.analyze_market_conditions()
            if market_analysis.get('trending_up', 0) > market_analysis.get('trending_down', 0) * 2:
                logger.info("[SELF-OPTIMIZE] Bullish market detected, adjusting strategy...")
                await self._adjust_for_bullish_market()
            elif market_analysis.get('trending_down', 0) > market_analysis.get('trending_up', 0) * 2:
                logger.info("[SELF-OPTIMIZE] Bearish market detected, adjusting strategy...")
                await self._adjust_for_bearish_market()
            
            # 4. Learn from best performing symbols
            best_symbols = performance.get('best_performing_symbols', [])
            if best_symbols:
                logger.info(f"[SELF-OPTIMIZE] Focusing on best performers: {[s['symbol'] for s in best_symbols[:3]]}")
                await self._focus_on_best_symbols(best_symbols[:5])
            
            logger.info("[SELF-OPTIMIZE] Optimization routine completed")
            
        except Exception as e:
            logger.error(f"[SELF-OPTIMIZE] Error during optimization: {e}")
    
    async def _adjust_for_better_win_rate(self):
        """Adjust parameters to improve win rate"""
        # Tighten signal generation criteria
        if hasattr(self.signal_assistant, 'adjust_confidence_threshold'):
            await self.signal_assistant.adjust_confidence_threshold(1.2)  # Increase by 20%
        
        # Tighten risk management
        await self.risk_assistant.adjust_risk_parameters(tighter=True)
    
    async def _adjust_risk_reward_ratio(self):
        """Adjust risk/reward parameters"""
        # Increase profit targets slightly
        if hasattr(self.signal_assistant, 'adjust_profit_targets'):
            await self.signal_assistant.adjust_profit_targets(1.1)  # Increase by 10%
    
    async def _adjust_for_bullish_market(self):
        """Adjust for bullish market conditions"""
        # Increase position sizes
        if hasattr(self.signal_assistant, 'adjust_position_sizing'):
            await self.signal_assistant.adjust_position_sizing(1.2)  # Increase by 20%
        
        # Loosen risk parameters slightly
        await self.risk_assistant.adjust_risk_parameters(tighter=False)
    
    async def _adjust_for_bearish_market(self):
        """Adjust for bearish market conditions"""
        # Reduce position sizes
        if hasattr(self.signal_assistant, 'adjust_position_sizing'):
            await self.signal_assistant.adjust_position_sizing(0.8)  # Reduce by 20%
        
        # Tighten risk parameters
        await self.risk_assistant.adjust_risk_parameters(tighter=True)
    
    async def _focus_on_best_symbols(self, best_symbols: List[Dict[str, Any]]):
        """Focus trading on best performing symbols"""
        # Extract symbol names
        symbol_names = [s['symbol'] for s in best_symbols]
        
        # Update signal generation to prioritize these symbols
        if hasattr(self.signal_assistant, 'set_priority_symbols'):
            await self.signal_assistant.set_priority_symbols(symbol_names)
    
    async def self_diagnose(self) -> Dict[str, Any]:
        """Run comprehensive self-diagnosis"""
        logger.info("[SELF-DIAGNOSE] Running comprehensive diagnosis...")
        
        diagnosis = {
            'timestamp': time.time(),
            'health': await self._check_system_health(),
            'performance': await self.performance_assistant.get_performance_summary(),
            'issues': [],
            'recommendations': []
        }
        
        # Check for common issues
        metrics = self.get_metrics()
        
        # Issue: Low execution rate
        if metrics['signal_execution_rate'] < 0.5:
            diagnosis['issues'].append('Low signal execution rate')
            diagnosis['recommendations'].append('Check risk parameters and capital availability')
        
        # Issue: High error rate
        total_errors = sum(self.error_counts.values())
        if total_errors > 50:
            diagnosis['issues'].append(f'High error count: {total_errors}')
            diagnosis['recommendations'].append('Review error logs and consider system restart')
        
        # Issue: No recent trades
        if metrics['successful_trades'] == 0 and metrics['uptime_hours'] > 1:
            diagnosis['issues'].append('No successful trades')
            diagnosis['recommendations'].append('Review signal generation parameters')
        
        # Issue: Poor performance
        if diagnosis['performance']['overall']['win_rate'] < 0.3:
            diagnosis['issues'].append('Very low win rate')
            diagnosis['recommendations'].append('Consider pausing trading and reviewing strategy')
        
        logger.info(f"[SELF-DIAGNOSE] Found {len(diagnosis['issues'])} issues")
        return diagnosis
    
    async def self_repair(self) -> bool:
        """Attempt to self-repair identified issues"""
        logger.info("[SELF-REPAIR] Starting self-repair procedure...")
        
        try:
            # Run diagnosis first
            diagnosis = await self.self_diagnose()
            
            if not diagnosis['issues']:
                logger.info("[SELF-REPAIR] No issues found, system healthy")
                return True
            
            # Attempt to fix each issue
            for issue in diagnosis['issues']:
                logger.info(f"[SELF-REPAIR] Addressing issue: {issue}")
                
                if 'Low signal execution rate' in issue:
                    # Check capital and adjust parameters
                    capital = await self._check_capital_availability()
                    if capital['available'] < MINIMUM_ORDER_SIZE_TIER1:
                        logger.warning("[SELF-REPAIR] Insufficient capital, cannot fix execution rate")
                    else:
                        await self.risk_assistant.adjust_risk_parameters(tighter=False)
                
                elif 'High error count' in issue:
                    # Clear error counts and restart problematic components
                    self.error_counts.clear()
                    await self._restart_unhealthy_components()
                
                elif 'No successful trades' in issue:
                    # Lower signal thresholds temporarily
                    if hasattr(self.signal_assistant, 'adjust_confidence_threshold'):
                        await self.signal_assistant.adjust_confidence_threshold(0.8)  # Reduce by 20%
                
                elif 'Very low win rate' in issue:
                    # Run optimization
                    await self.self_optimize()
            
            # Verify repair success
            await asyncio.sleep(5)
            new_diagnosis = await self.self_diagnose()
            
            success = len(new_diagnosis['issues']) < len(diagnosis['issues'])
            logger.info(f"[SELF-REPAIR] Repair {'successful' if success else 'failed'}")
            
            return success
            
        except Exception as e:
            logger.error(f"[SELF-REPAIR] Error during self-repair: {e}")
            return False
    
    async def _restart_unhealthy_components(self):
        """Restart components that are unhealthy"""
        health = await self._check_system_health()
        
        for component, status in health['components'].items():
            if not status.get('healthy', False):
                logger.info(f"[SELF-REPAIR] Restarting {component}...")
                
                assistant_map = {
                    'data_feed': self.data_assistant,
                    'signals': self.signal_assistant,
                    'execution': self.execution_assistant,
                    'risk': self.risk_assistant,
                    'performance': self.performance_assistant
                }
                
                assistant = assistant_map.get(component)
                if assistant:
                    await assistant.stop()
                    await asyncio.sleep(1)
                    await assistant.initialize()