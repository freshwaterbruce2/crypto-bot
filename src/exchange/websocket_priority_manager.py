"""
WebSocket V2 Priority Manager - REST Fallback Optimization
===========================================================

Intelligently routes operations through WebSocket V2 when available,
falling back to REST only when necessary. Optimizes for speed and reliability.

Features:
- WebSocket V2 prioritization for real-time operations
- Automatic REST fallback for unsupported operations
- Connection health monitoring
- Performance-based routing decisions
- Operation-specific routing logic
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, Optional

from ..utils.kraken_rate_limit_pro import get_rate_limiter

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of trading operations"""
    # WebSocket V2 native operations
    BALANCE_CHECK = "balance"
    TICKER_SUBSCRIBE = "ticker"
    ORDER_PLACE = "order_place"
    ORDER_CANCEL = "order_cancel"
    ORDER_STATUS = "order_status"
    EXECUTION_STREAM = "executions"
    
    # REST-only operations
    HISTORICAL_DATA = "historical"
    ACCOUNT_INFO = "account"
    TRADING_FEES = "fees"
    DEPOSIT_WITHDRAW = "deposit_withdraw"
    
    # Hybrid operations (can use either)
    POSITION_CHECK = "positions"
    OPEN_ORDERS = "open_orders"


class WebSocketPriorityManager:
    """Manages operation routing between WebSocket V2 and REST API"""
    
    def __init__(self, websocket_manager=None, rest_client=None):
        """
        Initialize priority manager
        
        Args:
            websocket_manager: WebSocket V2 manager instance
            rest_client: REST API client instance
        """
        self.ws_manager = websocket_manager
        self.rest_client = rest_client
        self.rate_limiter = get_rate_limiter()
        
        # Performance metrics
        self.ws_latency_ms = 50  # Initial estimate
        self.rest_latency_ms = 200  # Initial estimate
        self.ws_success_rate = 1.0
        self.rest_success_rate = 1.0
        
        # Operation counts
        self.ws_operations = 0
        self.rest_operations = 0
        self.fallback_count = 0
        
        # WebSocket V2 native operations
        self.ws_native_operations = {
            OperationType.BALANCE_CHECK,
            OperationType.TICKER_SUBSCRIBE,
            OperationType.ORDER_PLACE,
            OperationType.ORDER_CANCEL,
            OperationType.ORDER_STATUS,
            OperationType.EXECUTION_STREAM,
        }
        
        # REST-only operations
        self.rest_only_operations = {
            OperationType.HISTORICAL_DATA,
            OperationType.ACCOUNT_INFO,
            OperationType.TRADING_FEES,
            OperationType.DEPOSIT_WITHDRAW,
        }
        
        logger.info("[WS_PRIORITY] Initialized WebSocket V2 priority manager")
    
    def should_use_websocket(self, operation: OperationType) -> bool:
        """
        Determine if WebSocket V2 should be used for an operation
        
        Args:
            operation: Type of operation to perform
            
        Returns:
            bool: True if WebSocket should be used
        """
        # REST-only operations
        if operation in self.rest_only_operations:
            return False
        
        # Check WebSocket availability
        if not self.ws_manager or not self.ws_manager.is_connected():
            logger.debug(f"[WS_PRIORITY] WebSocket not available for {operation.value}")
            return False
        
        # WebSocket native operations - always prefer WebSocket
        if operation in self.ws_native_operations:
            # Check connection health
            if self._is_websocket_healthy():
                return True
            else:
                logger.warning(f"[WS_PRIORITY] WebSocket unhealthy, falling back to REST for {operation.value}")
                return False
        
        # Hybrid operations - decide based on performance
        return self._decide_hybrid_routing(operation)
    
    def _is_websocket_healthy(self) -> bool:
        """Check if WebSocket connection is healthy"""
        if not self.ws_manager:
            return False
        
        try:
            status = self.ws_manager.get_connection_status()
            
            # Check connection
            if not status.get('is_running', False):
                return False
            
            # Check message recency (no messages for 60 seconds is unhealthy)
            last_message_time = status.get('last_message_time', 0)
            if time.time() - last_message_time > 60:
                logger.warning("[WS_PRIORITY] WebSocket stale (no messages for 60s)")
                return False
            
            # Check success rate
            if self.ws_success_rate < 0.8:
                logger.warning(f"[WS_PRIORITY] WebSocket success rate low: {self.ws_success_rate:.2%}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[WS_PRIORITY] Error checking WebSocket health: {e}")
            return False
    
    def _decide_hybrid_routing(self, operation: OperationType) -> bool:
        """Decide routing for hybrid operations based on performance"""
        # Check rate limits
        if self.rate_limiter.should_use_websocket():
            logger.info(f"[WS_PRIORITY] Using WebSocket for {operation.value} due to rate limits")
            return True
        
        # Compare latencies
        if self.ws_latency_ms < self.rest_latency_ms * 0.7:  # WebSocket 30% faster
            logger.debug(f"[WS_PRIORITY] Using WebSocket for {operation.value} (faster)")
            return True
        
        # Default to REST for hybrid operations
        return False
    
    async def execute_operation(
        self,
        operation: OperationType,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute an operation with automatic routing
        
        Args:
            operation: Type of operation
            **kwargs: Operation-specific parameters
            
        Returns:
            Operation result
        """
        start_time = time.time()
        use_websocket = self.should_use_websocket(operation)
        
        try:
            if use_websocket:
                result = await self._execute_via_websocket(operation, **kwargs)
                self.ws_operations += 1
                
                # Update metrics
                latency = (time.time() - start_time) * 1000
                self.ws_latency_ms = 0.9 * self.ws_latency_ms + 0.1 * latency
                
            else:
                result = await self._execute_via_rest(operation, **kwargs)
                self.rest_operations += 1
                
                # Update metrics
                latency = (time.time() - start_time) * 1000
                self.rest_latency_ms = 0.9 * self.rest_latency_ms + 0.1 * latency
            
            logger.debug(f"[WS_PRIORITY] {operation.value} completed via {'WebSocket' if use_websocket else 'REST'} in {latency:.1f}ms")
            return result
            
        except Exception as e:
            logger.error(f"[WS_PRIORITY] Operation {operation.value} failed: {e}")
            
            # Try fallback if WebSocket failed
            if use_websocket and operation not in self.ws_native_operations:
                logger.info(f"[WS_PRIORITY] Falling back to REST for {operation.value}")
                self.fallback_count += 1
                
                try:
                    result = await self._execute_via_rest(operation, **kwargs)
                    self.rest_operations += 1
                    return result
                except Exception as rest_error:
                    logger.error(f"[WS_PRIORITY] REST fallback also failed: {rest_error}")
                    raise
            
            raise
    
    async def _execute_via_websocket(
        self,
        operation: OperationType,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute operation via WebSocket V2"""
        if not self.ws_manager:
            raise ValueError("WebSocket manager not available")
        
        # Route to appropriate WebSocket method
        if operation == OperationType.BALANCE_CHECK:
            balances = self.ws_manager.get_all_balances()
            if not balances:
                # Subscribe and wait for update
                await self.ws_manager.subscribe_balance()
                await asyncio.sleep(1)  # Wait for initial update
                balances = self.ws_manager.get_all_balances()
            return {'balances': balances}
        
        elif operation == OperationType.TICKER_SUBSCRIBE:
            symbols = kwargs.get('symbols', [])
            success = await self.ws_manager.subscribe_ticker(symbols)
            return {'success': success}
        
        elif operation == OperationType.ORDER_PLACE:
            # This would integrate with WebSocket order execution
            return await self._place_order_websocket(**kwargs)
        
        elif operation == OperationType.ORDER_CANCEL:
            order_id = kwargs.get('order_id')
            return await self._cancel_order_websocket(order_id)
        
        elif operation == OperationType.POSITION_CHECK:
            # Get positions from balance data
            balances = self.ws_manager.get_all_balances()
            positions = {
                asset: balance 
                for asset, balance in balances.items()
                if float(balance.get('balance', 0)) > 0
            }
            return {'positions': positions}
        
        else:
            raise NotImplementedError(f"WebSocket operation {operation.value} not implemented")
    
    async def _execute_via_rest(
        self,
        operation: OperationType,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute operation via REST API"""
        if not self.rest_client:
            raise ValueError("REST client not available")
        
        # Apply rate limiting
        await self.rate_limiter.smart_acquire(operation.value)
        
        # Route to appropriate REST method
        if operation == OperationType.BALANCE_CHECK:
            return await self.rest_client.get_account_balance()
        
        elif operation == OperationType.HISTORICAL_DATA:
            return await self.rest_client.get_ohlc_data(**kwargs)
        
        elif operation == OperationType.ACCOUNT_INFO:
            return await self.rest_client.get_account_info()
        
        elif operation == OperationType.POSITION_CHECK:
            return await self.rest_client.get_open_positions()
        
        elif operation == OperationType.ORDER_PLACE:
            return await self.rest_client.place_order(**kwargs)
        
        elif operation == OperationType.ORDER_CANCEL:
            order_id = kwargs.get('order_id')
            return await self.rest_client.cancel_order(order_id)
        
        else:
            raise NotImplementedError(f"REST operation {operation.value} not implemented")
    
    async def _place_order_websocket(self, **kwargs) -> Dict:
        """Place order via WebSocket V2"""
        # This would integrate with the WebSocket order execution manager
        logger.info("[WS_PRIORITY] Placing order via WebSocket V2")
        
        # Mock implementation - replace with actual WebSocket order placement
        return {
            'success': True,
            'order_id': f"ws_order_{int(time.time())}",
            'method': 'websocket'
        }
    
    async def _cancel_order_websocket(self, order_id: str) -> Dict:
        """Cancel order via WebSocket V2"""
        logger.info(f"[WS_PRIORITY] Cancelling order {order_id} via WebSocket V2")
        
        # Mock implementation - replace with actual WebSocket order cancellation
        return {
            'success': True,
            'order_id': order_id,
            'method': 'websocket'
        }
    
    def get_statistics(self) -> Dict:
        """Get routing statistics"""
        total_ops = self.ws_operations + self.rest_operations
        
        return {
            'total_operations': total_ops,
            'websocket_operations': self.ws_operations,
            'rest_operations': self.rest_operations,
            'fallback_count': self.fallback_count,
            'ws_percentage': (self.ws_operations / total_ops * 100) if total_ops > 0 else 0,
            'ws_latency_ms': self.ws_latency_ms,
            'rest_latency_ms': self.rest_latency_ms,
            'ws_success_rate': self.ws_success_rate,
            'rest_success_rate': self.rest_success_rate,
            'ws_healthy': self._is_websocket_healthy()
        }
    
    async def optimize_for_speed(self):
        """Run optimization to determine fastest routes for each operation"""
        logger.info("[WS_PRIORITY] Running speed optimization tests...")
        
        test_operations = [
            OperationType.BALANCE_CHECK,
            OperationType.POSITION_CHECK,
        ]
        
        for operation in test_operations:
            # Test WebSocket
            if self.ws_manager and self.ws_manager.is_connected():
                ws_times = []
                for _ in range(3):
                    start = time.time()
                    try:
                        await self._execute_via_websocket(operation)
                        ws_times.append((time.time() - start) * 1000)
                    except:
                        pass
                    await asyncio.sleep(0.5)
                
                if ws_times:
                    avg_ws = sum(ws_times) / len(ws_times)
                    logger.info(f"[WS_PRIORITY] {operation.value} WebSocket avg: {avg_ws:.1f}ms")
            
            # Test REST
            if self.rest_client:
                rest_times = []
                for _ in range(3):
                    start = time.time()
                    try:
                        await self._execute_via_rest(operation)
                        rest_times.append((time.time() - start) * 1000)
                    except:
                        pass
                    await asyncio.sleep(1)  # Rate limit protection
                
                if rest_times:
                    avg_rest = sum(rest_times) / len(rest_times)
                    logger.info(f"[WS_PRIORITY] {operation.value} REST avg: {avg_rest:.1f}ms")
        
        logger.info("[WS_PRIORITY] Speed optimization complete")