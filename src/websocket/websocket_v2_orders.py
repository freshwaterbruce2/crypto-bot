"""
WebSocket V2 Order Management
===========================

Advanced order management via WebSocket V2 including:
- Order placement through WebSocket
- Order modification and cancellation
- Real-time order status tracking
- Order execution monitoring
- Error handling and validation

Features:
- Type-safe order operations
- Real-time order status updates
- Integration with existing order validation
- Comprehensive error handling
- Performance optimized execution
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.decimal_precision_fix import safe_decimal, safe_float
from ..utils.kraken_order_validator import validate_order_params

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types supported by Kraken WebSocket V2"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop-loss"
    TAKE_PROFIT = "take-profit"
    STOP_LOSS_LIMIT = "stop-loss-limit"
    TAKE_PROFIT_LIMIT = "take-profit-limit"


class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status types"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PARTIAL = "partial"


@dataclass
class OrderRequest:
    """Order request data structure"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    volume: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "GTC"  # Good Till Canceled
    order_flags: List[str] = None
    user_ref: Optional[str] = None
    
    def __post_init__(self):
        if self.order_flags is None:
            self.order_flags = []


@dataclass
class OrderResponse:
    """Order response data structure"""
    order_id: Optional[str] = None
    user_ref: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class OrderUpdate:
    """Order status update data structure"""
    order_id: str
    symbol: str
    side: str
    order_type: str
    status: str
    volume: Decimal
    volume_exec: Decimal
    cost: Decimal
    fee: Decimal
    avg_price: Decimal
    stop_price: Optional[Decimal] = None
    limit_price: Optional[Decimal] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class WebSocketV2OrderManager:
    """
    Order management via WebSocket V2.
    
    Provides comprehensive order management including placement,
    modification, cancellation, and real-time status tracking.
    """
    
    def __init__(self, websocket_manager):
        """
        Initialize order manager.
        
        Args:
            websocket_manager: WebSocket V2 manager instance
        """
        self.websocket_manager = websocket_manager
        
        # Order tracking
        self._active_orders: Dict[str, OrderUpdate] = {}
        self._pending_orders: Dict[str, OrderRequest] = {}
        self._order_history: List[OrderUpdate] = []
        self._order_lock = asyncio.Lock()
        
        # Performance tracking
        self._order_stats = {
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_failed': 0,
            'total_volume_traded': Decimal('0'),
            'total_fees_paid': Decimal('0'),
            'avg_execution_time_ms': 0.0,
            'last_order_time': 0.0
        }
        
        # Request tracking for response correlation
        self._pending_requests: Dict[str, Dict[str, Any]] = {}
        self._request_counter = 0
        
        logger.info("[WS_V2_ORDERS] Order manager initialized")
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        volume: Union[str, float, Decimal],
        price: Optional[Union[str, float, Decimal]] = None,
        stop_price: Optional[Union[str, float, Decimal]] = None,
        time_in_force: str = "GTC",
        order_flags: Optional[List[str]] = None,
        user_ref: Optional[str] = None,
        validate: bool = True
    ) -> OrderResponse:
        """
        Place order via WebSocket V2.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: 'buy' or 'sell'
            order_type: Order type ('market', 'limit', etc.)
            volume: Order volume
            price: Limit price (required for limit orders)
            stop_price: Stop price (for stop orders)
            time_in_force: Time in force ('GTC', 'IOC', 'FOK')
            order_flags: Order flags (e.g., ['fciq'] for fee-in-quote)
            user_ref: User reference ID
            validate: Whether to validate order parameters
            
        Returns:
            OrderResponse with order ID or error information
        """
        try:
            start_time = time.time()
            
            # Convert inputs to proper types
            volume_decimal = safe_decimal(volume)
            price_decimal = safe_decimal(price) if price is not None else None
            stop_price_decimal = safe_decimal(stop_price) if stop_price is not None else None
            
            # Create order request
            order_request = OrderRequest(
                symbol=symbol,
                side=OrderSide(side.lower()),
                order_type=OrderType(order_type.lower()),
                volume=volume_decimal,
                price=price_decimal,
                stop_price=stop_price_decimal,
                time_in_force=time_in_force,
                order_flags=order_flags or [],
                user_ref=user_ref
            )
            
            # Validate order if requested
            if validate:
                validation_result = await self._validate_order(order_request)
                if not validation_result['valid']:
                    return OrderResponse(
                        error=f"Order validation failed: {validation_result['error']}",
                        timestamp=time.time()
                    )
            
            # Check WebSocket availability
            if not self.websocket_manager.has_private_access:
                return OrderResponse(
                    error="Private WebSocket access not available",
                    timestamp=time.time()
                )
            
            # Generate request ID
            request_id = self._generate_request_id()
            
            # Build WebSocket message
            order_message = {
                "method": "add_order",
                "params": {
                    "order_type": order_request.order_type.value,
                    "side": order_request.side.value,
                    "symbol": order_request.symbol,
                    "volume": str(order_request.volume),
                    "time_in_force": order_request.time_in_force
                },
                "req_id": request_id
            }
            
            # Add optional parameters
            if order_request.price is not None:
                order_message["params"]["limit_price"] = str(order_request.price)
            
            if order_request.stop_price is not None:
                order_message["params"]["trigger_price"] = str(order_request.stop_price)
            
            if order_request.order_flags:
                order_message["params"]["order_flags"] = order_request.order_flags
            
            if order_request.user_ref:
                order_message["params"]["user_ref"] = order_request.user_ref
            
            # Store pending request
            async with self._order_lock:
                self._pending_requests[request_id] = {
                    'order_request': order_request,
                    'timestamp': start_time,
                    'response_future': asyncio.Future()
                }
                
                self._pending_orders[request_id] = order_request
            
            # Send order via private WebSocket
            await self._send_private_message(order_message)
            
            # Wait for response
            try:
                response = await asyncio.wait_for(
                    self._pending_requests[request_id]['response_future'],
                    timeout=30.0  # 30 second timeout
                )
                
                # Update statistics
                execution_time = (time.time() - start_time) * 1000
                self._update_execution_stats(execution_time, response.error is None)
                
                return response
                
            except asyncio.TimeoutError:
                # Clean up pending request
                async with self._order_lock:
                    self._pending_requests.pop(request_id, None)
                    self._pending_orders.pop(request_id, None)
                
                return OrderResponse(
                    error="Order request timeout",
                    timestamp=time.time()
                )
            
        except Exception as e:
            logger.error(f"[WS_V2_ORDERS] Error placing order: {e}")
            return OrderResponse(
                error=f"Order placement failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def cancel_order(
        self,
        order_id: Optional[str] = None,
        user_ref: Optional[str] = None
    ) -> OrderResponse:
        """
        Cancel order via WebSocket V2.
        
        Args:
            order_id: Order ID to cancel
            user_ref: User reference ID to cancel
            
        Returns:
            OrderResponse with cancellation status
        """
        try:
            if not order_id and not user_ref:
                return OrderResponse(
                    error="Either order_id or user_ref must be provided",
                    timestamp=time.time()
                )
            
            # Check WebSocket availability
            if not self.websocket_manager.has_private_access:
                return OrderResponse(
                    error="Private WebSocket access not available",
                    timestamp=time.time()
                )
            
            # Generate request ID
            request_id = self._generate_request_id()
            
            # Build cancellation message
            cancel_message = {
                "method": "cancel_order",
                "params": {},
                "req_id": request_id
            }
            
            if order_id:
                cancel_message["params"]["order_id"] = order_id
            
            if user_ref:
                cancel_message["params"]["user_ref"] = user_ref
            
            # Store pending request
            async with self._order_lock:
                self._pending_requests[request_id] = {
                    'cancel_request': {'order_id': order_id, 'user_ref': user_ref},
                    'timestamp': time.time(),
                    'response_future': asyncio.Future()
                }
            
            # Send cancellation via private WebSocket
            await self._send_private_message(cancel_message)
            
            # Wait for response
            try:
                response = await asyncio.wait_for(
                    self._pending_requests[request_id]['response_future'],
                    timeout=15.0  # 15 second timeout
                )
                
                return response
                
            except asyncio.TimeoutError:
                # Clean up pending request
                async with self._order_lock:
                    self._pending_requests.pop(request_id, None)
                
                return OrderResponse(
                    error="Cancel request timeout",
                    timestamp=time.time()
                )
            
        except Exception as e:
            logger.error(f"[WS_V2_ORDERS] Error canceling order: {e}")
            return OrderResponse(
                error=f"Order cancellation failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> OrderResponse:
        """
        Cancel all orders via WebSocket V2.
        
        Args:
            symbol: Optional symbol to limit cancellation to
            
        Returns:
            OrderResponse with cancellation status
        """
        try:
            # Check WebSocket availability
            if not self.websocket_manager.has_private_access:
                return OrderResponse(
                    error="Private WebSocket access not available",
                    timestamp=time.time()
                )
            
            # Generate request ID
            request_id = self._generate_request_id()
            
            # Build cancel all message
            cancel_all_message = {
                "method": "cancel_all_orders",
                "params": {},
                "req_id": request_id
            }
            
            if symbol:
                cancel_all_message["params"]["symbol"] = symbol
            
            # Store pending request
            async with self._order_lock:
                self._pending_requests[request_id] = {
                    'cancel_all_request': {'symbol': symbol},
                    'timestamp': time.time(),
                    'response_future': asyncio.Future()
                }
            
            # Send cancel all via private WebSocket
            await self._send_private_message(cancel_all_message)
            
            # Wait for response
            try:
                response = await asyncio.wait_for(
                    self._pending_requests[request_id]['response_future'],
                    timeout=30.0  # 30 second timeout
                )
                
                return response
                
            except asyncio.TimeoutError:
                # Clean up pending request
                async with self._order_lock:
                    self._pending_requests.pop(request_id, None)
                
                return OrderResponse(
                    error="Cancel all request timeout",
                    timestamp=time.time()
                )
            
        except Exception as e:
            logger.error(f"[WS_V2_ORDERS] Error canceling all orders: {e}")
            return OrderResponse(
                error=f"Cancel all orders failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _send_private_message(self, message: Dict[str, Any]) -> None:
        """Send message via private WebSocket"""
        websocket = self.websocket_manager._websocket_private
        
        if not websocket or websocket.closed:
            raise RuntimeError("Private WebSocket not available")
        
        await websocket.send(json.dumps(message))
        logger.debug(f"[WS_V2_ORDERS] Sent message: {message.get('method', 'unknown')}")
    
    async def _validate_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """
        Validate order parameters.
        
        Args:
            order_request: Order request to validate
            
        Returns:
            Validation result with 'valid' boolean and optional 'error'
        """
        try:
            # Basic validation
            if order_request.volume <= 0:
                return {'valid': False, 'error': 'Volume must be positive'}
            
            if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LOSS_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
                if order_request.price is None or order_request.price <= 0:
                    return {'valid': False, 'error': 'Price required for limit orders'}
            
            if order_request.order_type in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT, 
                                          OrderType.STOP_LOSS_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
                if order_request.stop_price is None or order_request.stop_price <= 0:
                    return {'valid': False, 'error': 'Stop price required for stop orders'}
            
            # Use existing order validator if available
            if validate_order_params:
                validation_params = {
                    'symbol': order_request.symbol,
                    'side': order_request.side.value,
                    'type': order_request.order_type.value,
                    'volume': str(order_request.volume)
                }
                
                if order_request.price:
                    validation_params['price'] = str(order_request.price)
                
                is_valid = validate_order_params(validation_params)
                if not is_valid:
                    return {'valid': False, 'error': 'Order parameters validation failed'}
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"[WS_V2_ORDERS] Order validation error: {e}")
            return {'valid': False, 'error': f'Validation error: {str(e)}'}
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        self._request_counter += 1
        return f"req_{int(time.time())}_{self._request_counter}"
    
    def _update_execution_stats(self, execution_time_ms: float, success: bool) -> None:
        """Update execution statistics"""
        if success:
            self._order_stats['orders_placed'] += 1
        else:
            self._order_stats['orders_failed'] += 1
        
        # Update average execution time
        current_avg = self._order_stats['avg_execution_time_ms']
        total_orders = self._order_stats['orders_placed'] + self._order_stats['orders_failed']
        
        if total_orders > 0:
            self._order_stats['avg_execution_time_ms'] = (
                (current_avg * (total_orders - 1) + execution_time_ms) / total_orders
            )
        
        self._order_stats['last_order_time'] = time.time()
    
    async def process_order_response(self, message: Dict[str, Any]) -> None:
        """
        Process order response from WebSocket.
        
        Args:
            message: WebSocket message containing order response
        """
        try:
            req_id = message.get('req_id')
            method = message.get('method')
            success = message.get('success', False)
            result = message.get('result', {})
            error = message.get('error')
            
            if not req_id:
                logger.warning(f"[WS_V2_ORDERS] Order response missing req_id: {message}")
                return
            
            # Find pending request
            async with self._order_lock:
                pending_request = self._pending_requests.get(req_id)
                
                if not pending_request:
                    logger.warning(f"[WS_V2_ORDERS] No pending request for {req_id}")
                    return
                
                # Create response
                if success:
                    response = OrderResponse(
                        order_id=result.get('order_id'),
                        user_ref=result.get('user_ref'),
                        status='submitted',
                        description=result.get('description'),
                        timestamp=time.time()
                    )
                    
                    # Handle successful order placement
                    if method == 'add_order' and 'order_request' in pending_request:
                        order_request = pending_request['order_request']
                        logger.info(f"[WS_V2_ORDERS] Order placed successfully: "
                                   f"{order_request.symbol} {order_request.side.value} "
                                   f"{order_request.volume} @ {order_request.price}")
                        
                        # Track order
                        if response.order_id:
                            self._active_orders[response.order_id] = OrderUpdate(
                                order_id=response.order_id,
                                symbol=order_request.symbol,
                                side=order_request.side.value,
                                order_type=order_request.order_type.value,
                                status='open',
                                volume=order_request.volume,
                                volume_exec=Decimal('0'),
                                cost=Decimal('0'),
                                fee=Decimal('0'),
                                avg_price=Decimal('0'),
                                limit_price=order_request.price,
                                stop_price=order_request.stop_price,
                                timestamp=time.time()
                            )
                    
                    elif method == 'cancel_order':
                        logger.info(f"[WS_V2_ORDERS] Order canceled successfully: {result}")
                        self._order_stats['orders_canceled'] += 1
                    
                    elif method == 'cancel_all_orders':
                        canceled_count = result.get('count', 0)
                        logger.info(f"[WS_V2_ORDERS] {canceled_count} orders canceled")
                        self._order_stats['orders_canceled'] += canceled_count
                        
                        # Clear active orders if all were canceled
                        if not result.get('symbol'):  # All orders canceled
                            self._active_orders.clear()
                
                else:
                    response = OrderResponse(
                        error=error or "Order operation failed",
                        timestamp=time.time()
                    )
                    
                    logger.error(f"[WS_V2_ORDERS] Order operation failed: {error}")
                
                # Complete the future
                if not pending_request['response_future'].done():
                    pending_request['response_future'].set_result(response)
                
                # Clean up
                self._pending_requests.pop(req_id, None)
                if method == 'add_order':
                    self._pending_orders.pop(req_id, None)
            
        except Exception as e:
            logger.error(f"[WS_V2_ORDERS] Error processing order response: {e}")
            logger.debug(f"[WS_V2_ORDERS] Failed message: {message}")
    
    async def process_order_update(self, message: Dict[str, Any]) -> None:
        """
        Process order status update from WebSocket.
        
        Args:
            message: WebSocket message containing order update
        """
        try:
            data_array = message.get('data', [])
            if not data_array:
                return
            
            for order_data in data_array:
                try:
                    order_id = order_data.get('order_id')
                    if not order_id:
                        continue
                    
                    # Create order update
                    order_update = OrderUpdate(
                        order_id=order_id,
                        symbol=order_data.get('symbol', ''),
                        side=order_data.get('side', ''),
                        order_type=order_data.get('order_type', ''),
                        status=order_data.get('status', ''),
                        volume=safe_decimal(order_data.get('volume', 0)),
                        volume_exec=safe_decimal(order_data.get('volume_exec', 0)),
                        cost=safe_decimal(order_data.get('cost', 0)),
                        fee=safe_decimal(order_data.get('fee', 0)),
                        avg_price=safe_decimal(order_data.get('avg_price', 0)),
                        limit_price=safe_decimal(order_data.get('limit_price')) if order_data.get('limit_price') else None,
                        stop_price=safe_decimal(order_data.get('stop_price')) if order_data.get('stop_price') else None,
                        timestamp=time.time()
                    )
                    
                    # Update order tracking
                    async with self._order_lock:
                        # Update active orders
                        if order_update.status in ['open', 'partial']:
                            self._active_orders[order_id] = order_update
                        elif order_update.status in ['closed', 'canceled', 'expired']:
                            # Move to history
                            if order_id in self._active_orders:
                                self._active_orders.pop(order_id)
                            
                            self._order_history.append(order_update)
                            
                            # Keep only last 1000 history entries
                            if len(self._order_history) > 1000:
                                self._order_history = self._order_history[-1000:]
                            
                            # Update statistics
                            if order_update.status == 'closed':
                                self._order_stats['orders_filled'] += 1
                                self._order_stats['total_volume_traded'] += order_update.volume_exec
                                self._order_stats['total_fees_paid'] += order_update.fee
                            
                            elif order_update.status == 'canceled':
                                self._order_stats['orders_canceled'] += 1
                    
                    # Log significant updates
                    if order_update.status in ['closed', 'canceled']:
                        logger.info(f"[WS_V2_ORDERS] Order {order_update.status}: "
                                   f"{order_update.symbol} {order_update.side} "
                                   f"Volume: {order_update.volume_exec}/{order_update.volume}")
                    
                    # Notify handlers
                    await self.websocket_manager._notify_handlers('order_update', order_update)
                    
                except Exception as e:
                    logger.warning(f"[WS_V2_ORDERS] Error processing order update {order_data}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"[WS_V2_ORDERS] Error processing order updates: {e}")
    
    # Data access methods
    def get_active_orders(self) -> Dict[str, OrderUpdate]:
        """Get all active orders"""
        return dict(self._active_orders)
    
    def get_order_by_id(self, order_id: str) -> Optional[OrderUpdate]:
        """Get order by ID"""
        return self._active_orders.get(order_id)
    
    def get_orders_by_symbol(self, symbol: str) -> List[OrderUpdate]:
        """Get all orders for symbol"""
        return [order for order in self._active_orders.values() 
                if order.symbol == symbol]
    
    def get_order_history(self, limit: int = 100) -> List[OrderUpdate]:
        """Get recent order history"""
        return self._order_history[-limit:] if limit > 0 else self._order_history
    
    def get_order_stats(self) -> Dict[str, Any]:
        """Get order statistics"""
        stats = dict(self._order_stats)
        
        # Convert Decimal to float for JSON serialization
        stats['total_volume_traded'] = float(stats['total_volume_traded'])
        stats['total_fees_paid'] = float(stats['total_fees_paid'])
        
        # Add current counts
        stats['active_order_count'] = len(self._active_orders)
        stats['pending_request_count'] = len(self._pending_requests)
        stats['history_count'] = len(self._order_history)
        
        return stats
    
    def has_active_orders(self, symbol: Optional[str] = None) -> bool:
        """Check if there are active orders"""
        if symbol:
            return any(order.symbol == symbol for order in self._active_orders.values())
        else:
            return len(self._active_orders) > 0
    
    def get_open_order_volume(self, symbol: str, side: str) -> Decimal:
        """Get total open order volume for symbol and side"""
        total_volume = Decimal('0')
        
        for order in self._active_orders.values():
            if order.symbol == symbol and order.side == side and order.status == 'open':
                remaining_volume = order.volume - order.volume_exec
                total_volume += remaining_volume
        
        return total_volume