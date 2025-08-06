"""
Critical Error Guardian System - Zero Human Intervention Safety Net
==================================================================

This Guardian System monitors the entire trading bot for critical errors and
provides a kill switch mechanism for extreme situations. It works alongside
the self-learning error resolver to ensure the bot can handle ANY error,
including those it has never encountered before.

Key Features:
1. Critical error detection and classification
2. Kill switch for emergency shutdown
3. Automatic recovery attempts before shutdown
4. Learning from critical events
5. System health monitoring
6. Kraken-specific error handling
"""

import asyncio
import gc
import json
import logging
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CriticalityLevel(Enum):
    """Levels of error criticality"""
    LOW = "low"  # Normal operational errors
    MEDIUM = "medium"  # Errors affecting performance
    HIGH = "high"  # Errors that could cause losses
    CRITICAL = "critical"  # Errors requiring immediate shutdown
    CATASTROPHIC = "catastrophic"  # Kill switch trigger

@dataclass
class CriticalEvent:
    """Record of a critical event"""
    timestamp: float
    level: CriticalityLevel
    component: str
    error_type: str
    error_message: str
    stack_trace: str
    system_state: Dict[str, Any]
    recovery_attempted: bool = False
    recovery_successful: bool = False
    kill_switch_triggered: bool = False


class CriticalErrorGuardian:
    """
    The Guardian System that ensures the bot never operates in an unsafe state.
    It monitors all components for critical errors and can trigger an emergency
    shutdown if necessary.
    """

    def __init__(self, bot, data_dir: str = "D:/trading_bot_data/guardian"):
        self.bot = bot
        self.logger = bot.logger if hasattr(bot, 'logger') else logger
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Guardian state
        self.active = True
        self.monitoring_interval = 5  # seconds
        self.kill_switch_engaged = False

        # Critical event tracking
        self.critical_events: List[CriticalEvent] = []
        self.max_events_history = 100  # Reduced for memory efficiency
        # Error thresholds for automatic actions
        self.thresholds = {
            CriticalityLevel.LOW: float('inf'),  # No limit on low errors
            CriticalityLevel.MEDIUM: 50,  # Max 50 medium errors per hour
            CriticalityLevel.HIGH: 10,  # Max 10 high errors per hour
            CriticalityLevel.CRITICAL: 3,  # Max 3 critical errors per hour
            CriticalityLevel.CATASTROPHIC: 1  # Immediate kill switch
        }

        # Error counters (reset hourly)
        self.error_counts = dict.fromkeys(CriticalityLevel, 0)
        self.last_reset = time.time()

        # Component health tracking
        self.component_health = {
            'exchange_api': True,
            'websocket': True,
            'balance_manager': True,
            'trade_executor': True,
            'strategy_manager': True,
            'profit_tracker': True,
            'error_resolver': True
        }

        # Recovery strategies
        self.recovery_strategies = {
            'exchange_api': self._recover_exchange_api,
            'websocket': self._recover_websocket,
            'balance_manager': self._recover_balance_manager,
            'trade_executor': self._recover_trade_executor,
            'strategy_manager': self._recover_strategy_manager,
            'profit_tracker': self._recover_profit_tracker,
            'error_resolver': self._recover_error_resolver
        }

        # Kill switch conditions
        self.kill_switch_conditions = [
            self._check_catastrophic_loss,
            self._check_api_compromise,
            self._check_infinite_loop,
            self._check_memory_explosion,
            self._check_critical_component_failure
        ]
        # Kraken-specific error patterns
        self.kraken_error_patterns = {
            'rate_limit': ['EOrder:Rate limit exceeded', 'EAPI:Rate limit exceeded', 'EAuth:Rate limit exceeded'],
            'auth_failure': ['EAPI:Invalid key', 'EAPI:Invalid signature', 'EAPI:Invalid nonce'],
            'insufficient_funds': ['EOrder:Insufficient funds', 'EOrder:Insufficient margin'],
            'order_limit': ['EOrder:Orders limit exceeded', 'EOrder:Positions limit exceeded'],
            'invalid_request': ['EGeneral:Invalid arguments', 'EOrder:Invalid price'],
            'service_unavailable': ['EService:Unavailable', 'EService:Market in cancel_only mode'],
            'lockout': ['EGeneral:Temporary lockout', 'EAuth:Account temporary disabled']
        }

        self.logger.info("[GUARDIAN] Critical Error Guardian System initialized")

    async def start_monitoring(self):
        """Start the guardian monitoring loop"""
        self.logger.info("[GUARDIAN] Starting critical error monitoring...")

        while self.active and not self.kill_switch_engaged:
            try:
                # Reset hourly counters
                if time.time() - self.last_reset > 3600:
                    self.error_counts = dict.fromkeys(CriticalityLevel, 0)
                    self.last_reset = time.time()
                    # Cleanup old events
                    await self._cleanup_old_events()

                # Check system health
                await self._monitor_system_health()

                # Check for kill switch conditions
                await self._check_kill_switch_conditions()

                # Process any pending critical events
                await self._process_critical_events()

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"[GUARDIAN] Monitoring error: {e}")
                # Guardian must never fail completely
                await asyncio.sleep(self.monitoring_interval)
    async def handle_error(self, component: str, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Handle an error and determine if it's critical.
        Returns True if the bot should continue, False if it should stop.
        """
        try:
            # Classify error criticality
            criticality = self._classify_error(component, error, context)

            # Create critical event record
            event = CriticalEvent(
                timestamp=time.time(),
                level=criticality,
                component=component,
                error_type=type(error).__name__,
                error_message=str(error),
                stack_trace=traceback.format_exc(),
                system_state=await self._capture_system_state()
            )

            # Record event
            self.critical_events.append(event)
            self.error_counts[criticality] += 1

            # Trim history
            if len(self.critical_events) > self.max_events_history:
                self.critical_events = self.critical_events[-self.max_events_history:]

            # Check thresholds
            if self.error_counts[criticality] >= self.thresholds[criticality]:
                self.logger.warning(
                    f"[GUARDIAN] {criticality.value} error threshold exceeded: "
                    f"{self.error_counts[criticality]}/{self.thresholds[criticality]}"
                )

                if criticality == CriticalityLevel.CATASTROPHIC:
                    await self.engage_kill_switch("Catastrophic error threshold exceeded")
                    return False
                elif criticality == CriticalityLevel.CRITICAL:
                    # Attempt recovery before considering kill switch
                    recovery_success = await self._attempt_recovery(component, event)
                    if not recovery_success:
                        await self.engage_kill_switch(f"Failed to recover from critical error in {component}")
                        return False
            # For non-catastrophic errors, attempt recovery
            if criticality in [CriticalityLevel.HIGH, CriticalityLevel.CRITICAL]:
                await self._attempt_recovery(component, event)

            # Save event data
            await self._save_critical_event(event)

            return not self.kill_switch_engaged

        except Exception as e:
            self.logger.error(f"[GUARDIAN] Error in error handler (meta-error): {e}")
            # If the guardian itself fails, engage kill switch
            await self.engage_kill_switch("Guardian system failure")
            return False

    def _classify_error(self, component: str, error: Exception, context: Dict[str, Any]) -> CriticalityLevel:
        """Classify the criticality level of an error with Kraken-specific handling"""
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Check for Kraken-specific errors first
        error_msg = str(error)

        # CATASTROPHIC - Immediate kill switch
        if any(err in error_msg for err in self.kraken_error_patterns['lockout']):
            return CriticalityLevel.CATASTROPHIC

        if any(err in error_msg for err in self.kraken_error_patterns['auth_failure']):
            # Multiple auth failures can indicate compromised API keys
            return CriticalityLevel.CRITICAL

        # CRITICAL - Could cause significant losses
        if any(err in error_msg for err in self.kraken_error_patterns['insufficient_funds']):
            return CriticalityLevel.CRITICAL

        if any(phrase in error_str for phrase in [
            'negative balance', 'order failed', 'position mismatch',
            'strategy failure', 'data corruption', 'infinite loop'
        ]):
            return CriticalityLevel.CRITICAL
        # HIGH - Affects trading performance
        if any(err in error_msg for err in self.kraken_error_patterns['rate_limit']):
            return CriticalityLevel.HIGH

        if any(err in error_msg for err in self.kraken_error_patterns['order_limit']):
            return CriticalityLevel.HIGH

        if any(phrase in error_str for phrase in [
            'connection lost', 'timeout', 'websocket disconnect'
        ]):
            return CriticalityLevel.HIGH

        # MEDIUM - Normal operational issues
        if any(err in error_msg for err in self.kraken_error_patterns['invalid_request']):
            return CriticalityLevel.MEDIUM

        if any(err in error_msg for err in self.kraken_error_patterns['service_unavailable']):
            return CriticalityLevel.MEDIUM

        if any(phrase in error_str for phrase in [
            'parsing error', 'validation failed', 'cache miss',
            'temporary failure', 'retry needed'
        ]):
            return CriticalityLevel.MEDIUM

        # LOW - Minor issues
        return CriticalityLevel.LOW

    async def _monitor_system_health(self):
        """Monitor the health of all critical components"""
        try:
            # Check exchange API (using Kraken pairs)
            if hasattr(self.bot, 'exchange'):
                try:
                    # Use a Kraken-specific pair
                    await self.bot.exchange.fetch_ticker('BTC/USD')
                    self.component_health['exchange_api'] = True
                except Exception as e:
                    self.component_health['exchange_api'] = False
                    self.logger.warning(f"[GUARDIAN] Exchange API unhealthy: {e}")
            # Check WebSocket
            if hasattr(self.bot, 'websocket_manager'):
                self.component_health['websocket'] = getattr(
                    self.bot.websocket_manager, 'is_connected', False
                )

            # Check balance manager
            if hasattr(self.bot, 'enhanced_balance_manager'):
                try:
                    await self.bot.enhanced_balance_manager.get_balance('USD')
                    self.component_health['balance_manager'] = True
                except Exception as e:
                    self.component_health['balance_manager'] = False
                    self.logger.warning(f"[GUARDIAN] Balance manager unhealthy: {e}")

            # Check error resolver
            if hasattr(self.bot, 'error_resolver'):
                self.component_health['error_resolver'] = self.bot.error_resolver is not None

            # Log health status
            healthy_components = sum(1 for healthy in self.component_health.values() if healthy)
            total_components = len(self.component_health)

            if healthy_components < total_components:
                self.logger.warning(
                    f"[GUARDIAN] System health: {healthy_components}/{total_components} components healthy"
                )
                unhealthy = [k for k, v in self.component_health.items() if not v]
                self.logger.warning(f"[GUARDIAN] Unhealthy components: {unhealthy}")

        except Exception as e:
            self.logger.error(f"[GUARDIAN] Health monitoring error: {e}")

    async def _check_kill_switch_conditions(self):
        """Check all kill switch conditions"""
        for condition_check in self.kill_switch_conditions:
            try:
                should_trigger, reason = await condition_check()
                if should_trigger:
                    await self.engage_kill_switch(reason)
                    break
            except Exception as e:
                self.logger.error(f"[GUARDIAN] Kill switch check error: {e}")
    async def _check_catastrophic_loss(self) -> tuple[bool, str]:
        """Check for catastrophic trading losses"""
        try:
            if hasattr(self.bot, 'metrics'):
                total_profit = self.bot.metrics.get('total_profit', 0)

                # Check for significant loss (more than 5% of starting balance)
                if hasattr(self.bot, 'starting_balance'):
                    loss_threshold = self.bot.starting_balance * 0.05
                    if total_profit < -loss_threshold:
                        return True, f"Catastrophic loss detected: ${abs(total_profit):.2f}"

            return False, ""

        except Exception as e:
            self.logger.error(f"[GUARDIAN] Loss check error: {e}")
            return False, ""

    async def _check_api_compromise(self) -> tuple[bool, str]:
        """Check for signs of API key compromise"""
        try:
            # Check for unusual activity patterns
            recent_errors = [e for e in self.critical_events
                           if time.time() - e.timestamp < 300]  # Last 5 minutes

            # Count Kraken auth errors
            auth_errors = [e for e in recent_errors
                         if any(pattern in e.error_message
                               for pattern in self.kraken_error_patterns['auth_failure'])]

            if len(auth_errors) > 3:
                return True, "Multiple authentication errors - possible API compromise"

            # Check for lockout
            lockout_errors = [e for e in recent_errors
                            if any(pattern in e.error_message
                                  for pattern in self.kraken_error_patterns['lockout'])]

            if lockout_errors:
                return True, "Account lockout detected - immediate shutdown required"

            return False, ""

        except Exception as e:
            self.logger.error(f"[GUARDIAN] API compromise check error: {e}")
            return False, ""
    async def _check_infinite_loop(self) -> tuple[bool, str]:
        """Check for infinite loop conditions"""
        try:
            # Check if the same error is repeating rapidly
            if len(self.critical_events) < 10:
                return False, ""

            recent_errors = self.critical_events[-10:]

            # Check if all recent errors are identical
            first_error = recent_errors[0].error_message
            if all(e.error_message == first_error for e in recent_errors):
                time_span = recent_errors[-1].timestamp - recent_errors[0].timestamp
                if time_span < 60:  # 10 identical errors in 60 seconds
                    return True, f"Infinite loop detected: {first_error[:50]}..."

            return False, ""

        except Exception as e:
            self.logger.error(f"[GUARDIAN] Infinite loop check error: {e}")
            return False, ""

    async def _check_memory_explosion(self) -> tuple[bool, str]:
        """Check for memory usage explosion"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            # If using more than 1GB, something is wrong
            if memory_mb > 1024:
                return True, f"Memory explosion detected: {memory_mb:.0f}MB used"

            return False, ""

        except Exception:
            # If we can't check memory, don't trigger kill switch
            return False, ""

    async def _check_critical_component_failure(self) -> tuple[bool, str]:
        """Check for critical component failures"""
        try:
            # Count unhealthy components
            unhealthy = [k for k, v in self.component_health.items() if not v]
            # If more than half of components are unhealthy
            if len(unhealthy) > len(self.component_health) / 2:
                return True, f"Multiple component failures: {', '.join(unhealthy)}"

            # If specific critical components fail together
            if not self.component_health['exchange_api'] and not self.component_health['websocket']:
                return True, "Both exchange API and WebSocket failed"

            return False, ""

        except Exception as e:
            self.logger.error(f"[GUARDIAN] Component failure check error: {e}")
            return False, ""

    async def _attempt_recovery(self, component: str, event: CriticalEvent) -> bool:
        """Attempt to recover from a critical error"""
        self.logger.info(f"[GUARDIAN] Attempting recovery for {component}...")

        event.recovery_attempted = True

        try:
            # Use component-specific recovery strategy
            if component in self.recovery_strategies:
                recovery_func = self.recovery_strategies[component]
                success = await recovery_func(event)
                event.recovery_successful = success

                if success:
                    self.logger.info(f"[GUARDIAN] Recovery successful for {component}")
                    self.component_health[component] = True
                else:
                    self.logger.warning(f"[GUARDIAN] Recovery failed for {component}")

                return success
            else:
                # Try generic recovery through error resolver
                if hasattr(self.bot, 'error_resolver'):
                    error = Exception(event.error_message)
                    success, _ = await self.bot.error_resolver.resolve_error(
                        component, error, {'critical_event': event}
                    )
                    event.recovery_successful = success
                    return success

            return False
        except Exception as e:
            self.logger.error(f"[GUARDIAN] Recovery attempt failed: {e}")
            return False

    # Component-specific recovery methods

    async def _recover_exchange_api(self, event: CriticalEvent) -> bool:
        """Recover exchange API connection"""
        try:
            if hasattr(self.bot, 'exchange'):
                # For Kraken-specific errors, wait before reconnecting
                if any(err in event.error_message for err in self.kraken_error_patterns['rate_limit']):
                    await asyncio.sleep(10)  # Wait for rate limit to clear

                # Reconnect
                await self.bot.exchange.close()
                await asyncio.sleep(2)
                return await self.bot.initialize_exchange()
            return False
        except:
            return False

    async def _recover_websocket(self, event: CriticalEvent) -> bool:
        """Recover WebSocket connection"""
        try:
            if hasattr(self.bot, 'websocket_manager'):
                await self.bot.websocket_manager.disconnect()
                await asyncio.sleep(3)
                success = await self.bot.websocket_manager.connect()
                if success:
                    # Re-subscribe to channels
                    await self.bot.websocket_manager.subscribe_to_ticker(self.bot.trade_pairs)
                    await self.bot.websocket_manager.subscribe_to_ohlc(self.bot.trade_pairs)
                return success
            return False
        except:
            return False

    async def _recover_balance_manager(self, event: CriticalEvent) -> bool:
        """Recover balance manager"""
        try:
            # Fix: Add proper null checking for enhanced_balance_manager
            if (hasattr(self.bot, 'enhanced_balance_manager') and
                self.bot.enhanced_balance_manager is not None):
                # Clear cache and force refresh
                self.bot.enhanced_balance_manager._cache.clear()
                await self.bot.enhanced_balance_manager.refresh_all_balances()
                return True

            # Also check for regular balance_manager
            elif (hasattr(self.bot, 'balance_manager') and
                  self.bot.balance_manager is not None):
                await self.bot.balance_manager.refresh_all_balances()
                return True

            return False
        except Exception as e:
            logger.warning(f"[RECOVERY] Balance manager recovery failed: {e}")
            return False
    async def _recover_trade_executor(self, event: CriticalEvent) -> bool:
        """Recover trade executor"""
        try:
            if hasattr(self.bot, 'trade_executor'):
                # Reset any locks or pending operations
                if hasattr(self.bot.trade_executor, 'reset'):
                    await self.bot.trade_executor.reset()
                return True
            return False
        except:
            return False

    async def _recover_strategy_manager(self, event: CriticalEvent) -> bool:
        """Recover strategy manager"""
        try:
            if hasattr(self.bot, 'strategy_manager'):
                # Reinitialize strategies
                await self.bot.strategy_manager.stop_all_strategies()
                await self.bot.strategy_manager.initialize_strategies()
                return True
            return False
        except:
            return False

    async def _recover_profit_tracker(self, event: CriticalEvent) -> bool:
        """Recover profit tracker"""
        try:
            if hasattr(self.bot, 'profit_harvester'):
                # Reset tracking state
                if hasattr(self.bot.profit_harvester, 'reset_tracking'):
                    await self.bot.profit_harvester.reset_tracking()
                return True
            return False
        except:
            return False

    async def _recover_error_resolver(self, event: CriticalEvent) -> bool:
        """Recover error resolver"""
        try:
            # Error resolver should be self-healing
            # Just verify it exists
            return hasattr(self.bot, 'error_resolver') and self.bot.error_resolver is not None
        except:
            return False
    async def engage_kill_switch(self, reason: str):
        """
        Engage the kill switch - emergency shutdown of the bot.
        This is the last resort when the bot cannot operate safely.
        """
        self.kill_switch_engaged = True

        self.logger.critical(f"[GUARDIAN] KILL SWITCH ENGAGED: {reason}")

        # Create kill switch event
        event = CriticalEvent(
            timestamp=time.time(),
            level=CriticalityLevel.CATASTROPHIC,
            component="guardian",
            error_type="KillSwitch",
            error_message=reason,
            stack_trace="",
            system_state=await self._capture_system_state(),
            kill_switch_triggered=True
        )

        self.critical_events.append(event)

        # Save final state
        await self._save_kill_switch_report(event)

        # Attempt graceful shutdown
        try:
            self.logger.info("[GUARDIAN] Attempting graceful shutdown...")

            # Stop all trading immediately
            if hasattr(self.bot, 'trade_executor'):
                self.bot.trade_executor.trading_enabled = False

            # Cancel all open orders
            if hasattr(self.bot, 'exchange'):
                try:
                    await self.bot.exchange.cancel_all_orders()
                except:
                    pass
            # Stop all strategies
            if hasattr(self.bot, 'strategy_manager'):
                await self.bot.strategy_manager.stop_all_strategies()

            # Disconnect WebSocket
            if hasattr(self.bot, 'websocket_manager'):
                await self.bot.websocket_manager.disconnect()

            # Stop infinity loop
            if hasattr(self.bot, 'unified_infinity_system'):
                self.bot.unified_infinity_system.running = False

            # Signal bot to stop
            self.bot.running = False
            if hasattr(self.bot, 'shutdown_event'):
                self.bot.shutdown_event.set()

            self.logger.info("[GUARDIAN] Graceful shutdown completed")

        except Exception as e:
            self.logger.error(f"[GUARDIAN] Error during shutdown: {e}")

        # Final message
        self.logger.critical(
            "[GUARDIAN] Bot has been stopped for safety. "
            "Review the kill switch report before restarting."
        )

    async def _process_critical_events(self):
        """Process and learn from critical events"""
        # This would integrate with the learning system
        # to prevent future occurrences
        pass

    async def _capture_system_state(self) -> Dict[str, Any]:
        """Capture current system state"""
        state = {
            'timestamp': time.time(),
            'kill_switch_engaged': self.kill_switch_engaged,
            'component_health': self.component_health.copy(),
            'error_counts': self.error_counts.copy(),
            'recent_errors': len([e for e in self.critical_events if time.time() - e.timestamp < 300])
        }
        try:
            # Add bot metrics if available
            if hasattr(self.bot, 'metrics'):
                state['bot_metrics'] = self.bot.metrics.copy()
        except:
            pass

        return state

    async def _save_critical_event(self, event: CriticalEvent):
        """Save critical event to disk"""
        try:
            event_file = self.data_dir / f"critical_events_{datetime.now().strftime('%Y%m%d')}.jsonl"

            event_data = {
                'timestamp': event.timestamp,
                'level': event.level.value,
                'component': event.component,
                'error_type': event.error_type,
                'error_message': event.error_message,
                'recovery_attempted': event.recovery_attempted,
                'recovery_successful': event.recovery_successful,
                'system_state': event.system_state
            }

            with open(event_file, 'a') as f:
                f.write(json.dumps(event_data) + '\n')

        except Exception as e:
            self.logger.error(f"[GUARDIAN] Failed to save critical event: {e}")

    async def _save_kill_switch_report(self, event: CriticalEvent):
        """Save detailed kill switch report"""
        try:
            report_file = self.data_dir / f"kill_switch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            report = {
                'timestamp': datetime.now().isoformat(),
                'reason': event.error_message,
                'system_state': event.system_state,
                'recent_critical_events': [
                    {
                        'timestamp': e.timestamp,
                        'level': e.level.value,
                        'component': e.component,
                        'error': e.error_message
                    }
                    for e in self.critical_events[-20:]  # Last 20 events
                ],
                'component_health': self.component_health,
                'error_counts': self.error_counts,
                'bot_metrics': getattr(self.bot, 'metrics', {})
            }
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            self.logger.info(f"[GUARDIAN] Kill switch report saved to {report_file}")

        except Exception as e:
            self.logger.error(f"[GUARDIAN] Failed to save kill switch report: {e}")

    async def _cleanup_old_events(self):
        """Clean up old events to prevent memory growth"""
        try:
            # Keep only recent events in memory
            cutoff_time = time.time() - 3600  # 1 hour
            self.critical_events = [e for e in self.critical_events
                                  if e.timestamp > cutoff_time]

            # Force garbage collection
            gc.collect()

        except Exception as e:
            self.logger.error(f"[GUARDIAN] Cleanup error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current guardian status"""
        return {
            'active': self.active,
            'kill_switch_engaged': self.kill_switch_engaged,
            'component_health': self.component_health,
            'error_counts': self.error_counts,
            'recent_critical_events': len([e for e in self.critical_events
                                         if e.level in [CriticalityLevel.CRITICAL,
                                                       CriticalityLevel.CATASTROPHIC]]),
            'total_events': len(self.critical_events),
            'memory_usage_mb': self._get_memory_usage()
        }

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
