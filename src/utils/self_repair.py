"""
Self-Repair System

This module provides autonomous self-repair capabilities for the trading bot.
It can diagnose issues, apply fixes, and recover from errors without human intervention.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import traceback
import os
import json
import inspect
import ast

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """SECURITY FIX: Exception for security-related repair validation errors"""
    pass


class RepairAction:
    """Represents a repair action that can be taken."""
    
    def __init__(
        self,
        name: str,
        description: str,
        check_func: Callable,
        repair_func: Callable,
        severity: str = "medium"
    ):
        self.name = name
        self.description = description
        self.check_func = check_func
        self.repair_func = repair_func
        self.severity = severity
        self.last_executed = None
        self.execution_count = 0
        

class SelfRepairSystem:
    """
    Autonomous self-repair system for the trading bot.
    Diagnoses and fixes common issues without human intervention.
    """
    
    def __init__(self, bot_instance: Any = None):
        """Initialize the self-repair system."""
        self.bot = bot_instance
        self.repair_actions: Dict[str, RepairAction] = {}
        self.repair_history = []
        self.diagnostic_results = {}
        self.max_repair_attempts = 3
        self.repair_cooldown_seconds = 300
        
        # Register default repair actions
        self._register_default_repairs()
        
    def _register_default_repairs(self) -> None:
        """Register default repair actions."""
        # Connection repairs
        self.register_repair(
            RepairAction(
                name="websocket_reconnect",
                description="Reconnect WebSocket if disconnected",
                check_func=self._check_websocket_connection,
                repair_func=self._repair_websocket_connection,
                severity="high"
            )
        )
        
        # Memory cleanup
        self.register_repair(
            RepairAction(
                name="memory_cleanup",
                description="Clean up excessive memory usage",
                check_func=self._check_memory_usage,
                repair_func=self._repair_memory_usage,
                severity="medium"
            )
        )
        
        # Data integrity
        self.register_repair(
            RepairAction(
                name="data_integrity",
                description="Verify and fix data integrity issues",
                check_func=self._check_data_integrity,
                repair_func=self._repair_data_integrity,
                severity="high"
            )
        )
        
        # Rate limit handling
        self.register_repair(
            RepairAction(
                name="rate_limit_recovery",
                description="Handle rate limit errors",
                check_func=self._check_rate_limits,
                repair_func=self._repair_rate_limits,
                severity="medium"
            )
        )
        
    def register_repair(self, repair_action: RepairAction) -> None:
        """Register a repair action."""
        self.repair_actions[repair_action.name] = repair_action
        logger.info(f"[SELF_REPAIR] Registered repair: {repair_action.name}")
        
    async def diagnose_and_repair(self) -> Dict[str, Any]:
        """
        Run diagnostics and apply repairs as needed.
        
        Returns:
            Dict with repair results
        """
        logger.info("[SELF_REPAIR] Starting diagnostic cycle")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'issues_found': [],
            'repairs_attempted': [],
            'repairs_successful': [],
            'repairs_failed': [],
            'repaired': True
        }
        
        try:
            # Run all diagnostic checks
            for name, repair_action in self.repair_actions.items():
                try:
                    # Check if repair is needed
                    needs_repair = await self._safe_check(repair_action)
                    
                    if needs_repair:
                        results['issues_found'].append(name)
                        
                        # Check cooldown
                        if self._can_execute_repair(repair_action):
                            logger.warning(f"[SELF_REPAIR] Issue detected: {name}")
                            
                            # Attempt repair
                            results['repairs_attempted'].append(name)
                            repair_success = await self._safe_repair(repair_action)
                            
                            if repair_success:
                                results['repairs_successful'].append(name)
                                repair_action.last_executed = time.time()
                                repair_action.execution_count += 1
                                
                                self._record_repair(name, True, "Repair successful")
                            else:
                                results['repairs_failed'].append(name)
                                results['repaired'] = False
                                
                                self._record_repair(name, False, "Repair failed")
                        else:
                            logger.info(
                                f"[SELF_REPAIR] Skipping {name} - cooldown active"
                            )
                            
                except Exception as e:
                    logger.error(f"[SELF_REPAIR] Error checking {name}: {e}")
                    results['repairs_failed'].append(name)
                    results['repaired'] = False
                    
        except Exception as e:
            logger.error(f"[SELF_REPAIR] Diagnostic cycle error: {e}")
            results['repaired'] = False
            results['error'] = str(e)
            
        return results
        
    async def _safe_check(self, repair_action: RepairAction) -> bool:
        """Safely execute a check function."""
        try:
            if asyncio.iscoroutinefunction(repair_action.check_func):
                return await repair_action.check_func()
            else:
                return repair_action.check_func()
        except Exception as e:
            logger.error(f"[SELF_REPAIR] Check error for {repair_action.name}: {e}")
            return False
            
    async def _safe_repair(self, repair_action: RepairAction) -> bool:
        """Safely execute a repair function with security validation."""
        try:
            # SECURITY FIX: Validate repair function before execution
            if not self._validate_repair_function(repair_action.repair_func):
                logger.error(f"[SELF_REPAIR] Security validation failed for {repair_action.name}")
                return False
            
            if asyncio.iscoroutinefunction(repair_action.repair_func):
                return await repair_action.repair_func()
            else:
                return repair_action.repair_func()
        except Exception as e:
            logger.error(f"[SELF_REPAIR] Repair error for {repair_action.name}: {e}")
            return False
            
    def _can_execute_repair(self, repair_action: RepairAction) -> bool:
        """Check if repair can be executed (cooldown check)."""
        if repair_action.last_executed is None:
            return True
            
        time_since_last = time.time() - repair_action.last_executed
        return time_since_last >= self.repair_cooldown_seconds
        
    def _record_repair(self, action_name: str, success: bool, details: str) -> None:
        """Record repair attempt in history."""
        self.repair_history.append({
            'timestamp': datetime.now().isoformat(),
            'action': action_name,
            'success': success,
            'details': details
        })
        
        # Keep only last 100 entries
        if len(self.repair_history) > 100:
            self.repair_history = self.repair_history[-100:]
            
    # Default check and repair functions
    
    async def _check_websocket_connection(self) -> bool:
        """Check if WebSocket connection needs repair."""
        if not self.bot:
            return False
            
        ws_manager = getattr(self.bot, 'websocket_manager', None)
        if not ws_manager:
            return False
            
        # Check if connected
        is_connected = getattr(ws_manager, 'connected', False)
        return not is_connected
        
    async def _repair_websocket_connection(self) -> bool:
        """Repair WebSocket connection."""
        try:
            if not self.bot:
                return False
                
            ws_manager = getattr(self.bot, 'websocket_manager', None)
            if not ws_manager:
                return False
                
            logger.info("[SELF_REPAIR] Reconnecting WebSocket...")
            
            # Attempt reconnection
            if hasattr(ws_manager, 'reconnect'):
                await ws_manager.reconnect()
                return True
            elif hasattr(ws_manager, 'connect'):
                await ws_manager.connect()
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"[SELF_REPAIR] WebSocket repair failed: {e}")
            return False
            
    def _check_memory_usage(self) -> bool:
        """Check if memory usage is excessive."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Consider >500MB excessive for a trading bot
            return memory_mb > 500
        except:
            return False
            
    def _repair_memory_usage(self) -> bool:
        """Clean up memory usage."""
        try:
            import gc
            
            # Force garbage collection
            gc.collect()
            
            # Clear caches if bot has them
            if self.bot:
                # Clear any caches
                for attr_name in dir(self.bot):
                    if 'cache' in attr_name.lower():
                        attr = getattr(self.bot, attr_name)
                        if hasattr(attr, 'clear'):
                            attr.clear()
                            
            logger.info("[SELF_REPAIR] Memory cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"[SELF_REPAIR] Memory cleanup failed: {e}")
            return False
            
    async def _check_data_integrity(self) -> bool:
        """Check data integrity."""
        # This would check for corrupted data, NaN values, etc.
        # For now, return False (no issues)
        return False
        
    async def _repair_data_integrity(self) -> bool:
        """Repair data integrity issues."""
        # This would fix data issues
        # For now, return True (success)
        return True
        
    def _check_rate_limits(self) -> bool:
        """Check if rate limited."""
        if not self.bot:
            return False
            
        # Check if bot has rate limit flag
        is_rate_limited = getattr(self.bot, 'rate_limited', False)
        return is_rate_limited
        
    async def _repair_rate_limits(self) -> bool:
        """Handle rate limit recovery."""
        try:
            if not self.bot:
                return False
                
            logger.info("[SELF_REPAIR] Handling rate limit - waiting...")
            
            # Wait for rate limit to clear
            await asyncio.sleep(60)  # Wait 1 minute
            
            # Reset rate limit flag if exists
            if hasattr(self.bot, 'rate_limited'):
                self.bot.rate_limited = False
                
            return True
            
        except Exception as e:
            logger.error(f"[SELF_REPAIR] Rate limit repair failed: {e}")
            return False
            
    def get_repair_history(self) -> List[Dict]:
        """Get repair history."""
        return self.repair_history
        
    def _validate_repair_function(self, repair_func: Callable) -> bool:
        """SECURITY FIX: Validate repair function for security."""
        try:
            # Check if function is defined in this module or trusted modules
            func_module = getattr(repair_func, '__module__', '')
            trusted_modules = [
                __name__,  # This module
                'src.utils.self_repair',
                'builtins',
                'asyncio',
                'gc',
                'psutil'
            ]
            
            if not any(func_module.startswith(mod) or func_module == mod for mod in trusted_modules):
                logger.warning(f"[SELF_REPAIR] Untrusted module for repair function: {func_module}")
                return False
            
            # Check if function has dangerous operations
            if hasattr(repair_func, '__code__'):
                # Get function source if possible
                try:
                    source = inspect.getsource(repair_func)
                    # Parse AST to check for dangerous operations
                    tree = ast.parse(source)
                    
                    # Check for dangerous function calls
                    dangerous_calls = ['eval', 'exec', 'compile', '__import__', 'open']
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name) and node.func.id in dangerous_calls:
                                logger.warning(f"[SELF_REPAIR] Dangerous function call detected: {node.func.id}")
                                return False
                except (OSError, TypeError):
                    # Can't get source, but that's okay for built-in functions
                    pass
            
            return True
        except Exception as e:
            logger.error(f"[SELF_REPAIR] Error validating repair function: {e}")
            return False
    
    def get_repair_stats(self) -> Dict[str, Any]:
        """Get repair statistics."""
        total_repairs = len(self.repair_history)
        successful_repairs = sum(1 for r in self.repair_history if r['success'])
        
        return {
            'total_repairs': total_repairs,
            'successful_repairs': successful_repairs,
            'failed_repairs': total_repairs - successful_repairs,
            'success_rate': (successful_repairs / total_repairs * 100) if total_repairs > 0 else 0,
            'repair_actions_registered': len(self.repair_actions)
        }
