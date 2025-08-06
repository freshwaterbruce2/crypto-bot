"""
Kraken WebSocket V2 Order Execution Manager
===========================================

Comprehensive WebSocket-based order execution system for high-frequency trading.
Provides real-time order management through Kraken's WebSocket V2 API with:

- Native WebSocket order placement (add_order)
- Real-time order status tracking (executions channel)
- Order modification and cancellation
- Batch operations for efficiency
- Circuit breaker integration
- Authentication management with auto-refresh
- Fallback to REST API when needed

Key Features:
✅ WebSocket-native order execution
✅ Real-time execution tracking
✅ Order lifecycle management
✅ Rate limiting and queue management
✅ Error handling and recovery
✅ Authentication token management
✅ Circuit breaker integration
✅ Comprehensive logging and monitoring
"""

import asyncio
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

try:
    from ..guardian.critical_error_guardian import CriticalErrorGuardian, CriticalityLevel
    from ..utils.decimal_precision_fix import is_zero, safe_decimal, safe_float
    from ..utils.kraken_rl import KrakenRateLimiter
except ImportError:
    # Fallback for testing
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.guardian.critical_error_guardian import CriticalErrorGuardian, CriticalityLevel
    from src.utils.decimal_precision_fix import safe_float
    from src.utils.kraken_rl import KrakenRateLimiter

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"        # Order submitted but not confirmed
    OPEN = "open"             # Order confirmed and active
    PARTIAL = "partial"       # Partially filled
    FILLED = "filled"         # Completely filled
    CANCELLED = "cancelled"   # Order cancelled
    REJECTED = "rejected"     # Order rejected by exchange
    EXPIRED = "expired"       # Order expired
    UNKNOWN = "unknown"       # Status unknown


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop-loss"
    TAKE_PROFIT = "take-profit"
    STOP_LOSS_LIMIT = "stop-loss-limit"
    TAKE_PROFIT_LIMIT = "take-profit-limit"


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderRequest:
    """Order request structure"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: str  # Use string for precision
    price: Optional[str] = None  # Limit price for limit orders
    stop_price: Optional[str] = None  # Stop price for stop orders
    time_in_force: str = "GTC"  # GTC, IOC, FOK
    post_only: bool = False  # Post-only flag
    reduce_only: bool = False  # Reduce-only flag
    client_order_id: Optional[str] = None  # Custom order ID

    def __post_init__(self):
        if not self.client_order_id:
            self.client_order_id = f"ws_order_{uuid.uuid4().hex[:8]}"


@dataclass
class OrderExecution:
    """Order execution details"""
    order_id: str
    client_order_id: Optional[str]
    symbol: str
    side: str
    order_type: str
    exec_type: str  # trade, canceled, expired, etc.
    order_status: OrderStatus
    filled_quantity: str
    remaining_quantity: str
    avg_price: str
    fee: str = "0"
    timestamp: float = field(default_factory=time.time)
    execution_id: Optional[str] = None

    @classmethod
    def from_kraken_execution(cls, raw_data: dict[str, Any]) -> 'OrderExecution':
        """Create OrderExecution from Kraken execution message"""
        return cls(
            order_id=raw_data.get('order_id', ''),
            client_order_id=raw_data.get('cl_ord_id'),
            symbol=raw_data.get('symbol', ''),
            side=raw_data.get('side', ''),
            order_type=raw_data.get('ord_type', ''),
            exec_type=raw_data.get('exec_type', ''),
            order_status=OrderStatus(raw_data.get('order_status', 'unknown')),
            filled_quantity=str(raw_data.get('cum_qty', '0')),
            remaining_quantity=str(raw_data.get('leaves_qty', '0')),
            avg_price=str(raw_data.get('avg_px', '0')),
            fee=str(raw_data.get('fee', '0')),
            timestamp=time.time(),
            execution_id=raw_data.get('exec_id')
        )


@dataclass
class OrderState:
    """Complete order state tracking"""
    request: OrderRequest
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: str = "0"
    remaining_quantity: str = "0"
    avg_price: str = "0"
    total_fees: str = "0"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    executions: list[OrderExecution] = field(default_factory=list)
    error_message: Optional[str] = None
    retry_count: int = 0

    @property
    def is_final_state(self) -> bool:
        """Check if order is in a final state"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED,
                               OrderStatus.REJECTED, OrderStatus.EXPIRED]

    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage"""
        try:
            if self.request.quantity == "0":
                return 0.0
            filled = safe_float(self.filled_quantity)
            total = safe_float(self.request.quantity)
            return (filled / total) * 100 if total > 0 else 0.0
        except:
            return 0.0


class WebSocketOrderExecutionManager:
    """
    Comprehensive WebSocket V2 order execution manager

    Manages order lifecycle through WebSocket connections:
    1. Order placement via WebSocket add_order method
    2. Real-time execution tracking via executions channel
    3. Order modifications and cancellations
    4. Batch operations for efficiency
    5. Fallback to REST API when needed
    """

    def __init__(self, exchange_client, websocket_manager=None,
                 guardian: Optional[CriticalErrorGuardian] = None,
                 rate_limiter: Optional[KrakenRateLimiter] = None):
        """
        Initialize WebSocket order execution manager

        Args:
            exchange_client: Exchange client for REST API fallback
            websocket_manager: WebSocket V2 manager for real-time data
            guardian: Critical error guardian for safety
            rate_limiter: Rate limiter for API calls
        """
        self.exchange = exchange_client
        self.websocket_manager = websocket_manager
        self.guardian = guardian
        self.rate_limiter = rate_limiter or KrakenRateLimiter(max_calls_per_second=10)

        # Order tracking
        self.active_orders: dict[str, OrderState] = {}  # client_order_id -> OrderState
        self.order_id_mapping: dict[str, str] = {}  # order_id -> client_order_id
        self.execution_history: deque = deque(maxlen=1000)  # Recent executions

        # WebSocket connection state
        self.websocket_connected = False
        self.websocket_authenticated = False
        self.auth_token: Optional[str] = None
        self.token_created_time: float = 0
        self.token_refresh_interval = 13 * 60  # 13 minutes

        # Execution callbacks
        self.execution_callbacks: list[Callable] = []
        self.order_status_callbacks: list[Callable] = []

        # Circuit breaker state
        self.circuit_breaker_active = False
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.circuit_breaker_timeout = 60  # seconds
        self.last_failure_time = 0

        # Message queue for WebSocket orders
        self.order_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.processing_orders = False

        # Statistics
        self.stats = {
            'orders_submitted': 0,
            'orders_filled': 0,
            'orders_cancelled': 0,
            'orders_rejected': 0,
            'websocket_orders': 0,
            'rest_fallback_orders': 0,
            'execution_messages_processed': 0,
            'average_execution_time': 0.0
        }

        logger.info("[WS_ORDER_EXEC] WebSocket Order Execution Manager initialized")

    async def initialize(self) -> bool:
        """
        Initialize the order execution manager

        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("[WS_ORDER_EXEC] Initializing WebSocket order execution...")

            # Set up WebSocket manager if available
            if self.websocket_manager:
                # Register for execution updates
                self.websocket_manager.register_callback('executions', self._handle_execution_update)
                logger.info("[WS_ORDER_EXEC] Registered for execution updates")

                # Check WebSocket connection status
                self.websocket_connected = self.websocket_manager.is_connected()
                self.websocket_authenticated = self.websocket_manager.is_authenticated()

                if self.websocket_authenticated:
                    logger.info("[WS_ORDER_EXEC] WebSocket authenticated - order execution via WebSocket enabled")
                else:
                    logger.warning("[WS_ORDER_EXEC] WebSocket not authenticated - using REST API fallback")

            # Start order processing queue
            asyncio.create_task(self._process_order_queue())
            self.processing_orders = True

            # Start token refresh task if needed
            if self.websocket_authenticated:
                asyncio.create_task(self._token_refresh_loop())

            # Start cleanup task
            asyncio.create_task(self._cleanup_completed_orders())

            logger.info("[WS_ORDER_EXEC] Order execution manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] Initialization error: {e}")
            if self.guardian:
                await self.guardian.handle_critical_error("websocket_order_execution", e, CriticalityLevel.HIGH)
            return False

    async def add_order(self, order_request: OrderRequest) -> Optional[str]:
        """
        Place a new order via WebSocket or REST fallback

        Args:
            order_request: Order details

        Returns:
            str: Client order ID if successful, None otherwise
        """
        try:
            # Check circuit breaker
            if self.circuit_breaker_active:
                if time.time() - self.last_failure_time < self.circuit_breaker_timeout:
                    logger.warning("[WS_ORDER_EXEC] Circuit breaker active - order rejected")
                    return None
                else:
                    logger.info("[WS_ORDER_EXEC] Circuit breaker timeout expired - resetting")
                    self.circuit_breaker_active = False
                    self.consecutive_failures = 0

            # Create order state
            order_state = OrderState(request=order_request)
            self.active_orders[order_request.client_order_id] = order_state

            # Try WebSocket first if available and authenticated
            if self.websocket_authenticated and self.websocket_connected:
                success = await self._submit_websocket_order(order_request)
                if success:
                    self.stats['websocket_orders'] += 1
                    self.stats['orders_submitted'] += 1
                    logger.info(f"[WS_ORDER_EXEC] Order submitted via WebSocket: {order_request.client_order_id}")
                    return order_request.client_order_id
                else:
                    logger.warning("[WS_ORDER_EXEC] WebSocket order submission failed, falling back to REST")

            # Fallback to REST API
            success = await self._submit_rest_order(order_request)
            if success:
                self.stats['rest_fallback_orders'] += 1
                self.stats['orders_submitted'] += 1
                logger.info(f"[WS_ORDER_EXEC] Order submitted via REST: {order_request.client_order_id}")
                return order_request.client_order_id
            else:
                # Remove failed order from tracking
                self.active_orders.pop(order_request.client_order_id, None)
                logger.error(f"[WS_ORDER_EXEC] Order submission failed: {order_request.client_order_id}")
                await self._handle_order_failure(order_request, "Order submission failed")
                return None

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] Error placing order: {e}")
            if self.guardian:
                await self.guardian.handle_critical_error("order_placement", e, CriticalityLevel.HIGH)
            await self._handle_order_failure(order_request, str(e))
            return None

    async def _submit_websocket_order(self, order_request: OrderRequest) -> bool:
        """Submit order via WebSocket add_order method"""
        try:
            # Rate limiting check
            if not await self.rate_limiter.acquire():
                logger.warning("[WS_ORDER_EXEC] Rate limit exceeded for WebSocket order")
                return False

            # Build Kraken WebSocket V2 order message
            order_params = {
                "order_type": order_request.order_type.value,
                "side": order_request.side.value,
                "symbol": order_request.symbol,
                "order_qty": order_request.quantity,
                "time_in_force": order_request.time_in_force
            }

            # Add price for limit orders
            if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LOSS_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
                if order_request.price:
                    order_params["limit_price"] = order_request.price
                else:
                    logger.error("[WS_ORDER_EXEC] Limit order requires price")
                    return False

            # Add stop price for stop orders
            if order_request.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LOSS_LIMIT,
                                           OrderType.TAKE_PROFIT, OrderType.TAKE_PROFIT_LIMIT]:
                if order_request.stop_price:
                    order_params["stop_price"] = order_request.stop_price
                else:
                    logger.error("[WS_ORDER_EXEC] Stop order requires stop price")
                    return False

            # Add optional parameters
            if order_request.post_only:
                order_params["post_only"] = True

            if order_request.reduce_only:
                order_params["reduce_only"] = True

            if order_request.client_order_id:
                order_params["cl_ord_id"] = order_request.client_order_id

            # Create WebSocket message
            ws_message = {
                "method": "add_order",
                "params": order_params,
                "req_id": int(time.time() * 1000)  # Unique request ID
            }

            # Send via WebSocket manager
            if self.websocket_manager and hasattr(self.websocket_manager, 'send_private_message'):
                success = await self.websocket_manager.send_private_message(ws_message)
                if success:
                    logger.info(f"[WS_ORDER_EXEC] WebSocket order message sent: {order_request.symbol} {order_request.side.value} {order_request.quantity}")
                    return True
                else:
                    logger.error("[WS_ORDER_EXEC] Failed to send WebSocket order message")
                    return False
            else:
                logger.error("[WS_ORDER_EXEC] WebSocket manager not available for private messages")
                return False

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] WebSocket order submission error: {e}")
            return False

    async def _submit_rest_order(self, order_request: OrderRequest) -> bool:
        """Submit order via REST API fallback"""
        try:
            # Convert to exchange-specific format
            order_params = {
                'ordertype': order_request.order_type.value,
                'type': order_request.side.value,
                'pair': order_request.symbol,
                'volume': order_request.quantity,
                'timeinforce': order_request.time_in_force
            }

            # Add price for limit orders
            if order_request.price and order_request.order_type != OrderType.MARKET:
                order_params['price'] = order_request.price

            # Add stop price for stop orders
            if order_request.stop_price:
                order_params['price2'] = order_request.stop_price

            # Add optional flags
            oflags = []
            if order_request.post_only:
                oflags.append('post')
            if order_request.reduce_only:
                oflags.append('reduce')

            if oflags:
                order_params['oflags'] = ','.join(oflags)

            # Add client order ID if supported
            if order_request.client_order_id and hasattr(self.exchange, 'supports_client_order_id'):
                order_params['userref'] = order_request.client_order_id

            # Submit order via exchange
            if hasattr(self.exchange, 'create_order'):
                result = await self.exchange.create_order(**order_params)
            elif hasattr(self.exchange, 'add_order'):
                result = await self.exchange.add_order(**order_params)
            else:
                logger.error("[WS_ORDER_EXEC] Exchange doesn't support order creation")
                return False

            # Process result
            if result and 'txid' in result:
                order_id = result['txid'][0] if isinstance(result['txid'], list) else result['txid']

                # Update order state with exchange order ID
                if order_request.client_order_id in self.active_orders:
                    self.active_orders[order_request.client_order_id].order_id = order_id
                    self.active_orders[order_request.client_order_id].status = OrderStatus.OPEN
                    self.order_id_mapping[order_id] = order_request.client_order_id

                logger.info(f"[WS_ORDER_EXEC] REST order successful: {order_id}")
                return True
            else:
                logger.error(f"[WS_ORDER_EXEC] REST order failed: {result}")
                return False

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] REST order submission error: {e}")
            return False

    async def cancel_order(self, client_order_id: str) -> bool:
        """
        Cancel an order via WebSocket or REST fallback

        Args:
            client_order_id: Client order ID to cancel

        Returns:
            bool: True if cancellation successful
        """
        try:
            order_state = self.active_orders.get(client_order_id)
            if not order_state:
                logger.warning(f"[WS_ORDER_EXEC] Order not found for cancellation: {client_order_id}")
                return False

            if order_state.is_final_state:
                logger.info(f"[WS_ORDER_EXEC] Order already in final state: {client_order_id}")
                return True

            # Try WebSocket cancellation first
            if self.websocket_authenticated and self.websocket_connected:
                success = await self._cancel_websocket_order(order_state)
                if success:
                    logger.info(f"[WS_ORDER_EXEC] Order cancelled via WebSocket: {client_order_id}")
                    return True
                else:
                    logger.warning("[WS_ORDER_EXEC] WebSocket cancellation failed, falling back to REST")

            # Fallback to REST API cancellation
            success = await self._cancel_rest_order(order_state)
            if success:
                logger.info(f"[WS_ORDER_EXEC] Order cancelled via REST: {client_order_id}")
                return True
            else:
                logger.error(f"[WS_ORDER_EXEC] Order cancellation failed: {client_order_id}")
                return False

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] Error cancelling order {client_order_id}: {e}")
            if self.guardian:
                await self.guardian.handle_critical_error("order_cancellation", e, CriticalityLevel.MEDIUM)
            return False

    async def _cancel_websocket_order(self, order_state: OrderState) -> bool:
        """Cancel order via WebSocket cancel_order method"""
        try:
            if not order_state.order_id:
                logger.error("[WS_ORDER_EXEC] Cannot cancel order without exchange order ID")
                return False

            # Build cancel message
            cancel_params = {
                "order_id": [order_state.order_id]  # Kraken expects array
            }

            ws_message = {
                "method": "cancel_order",
                "params": cancel_params,
                "req_id": int(time.time() * 1000)
            }

            # Send via WebSocket
            if self.websocket_manager and hasattr(self.websocket_manager, 'send_private_message'):
                success = await self.websocket_manager.send_private_message(ws_message)
                if success:
                    logger.info(f"[WS_ORDER_EXEC] WebSocket cancel message sent: {order_state.order_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] WebSocket cancellation error: {e}")
            return False

    async def _cancel_rest_order(self, order_state: OrderState) -> bool:
        """Cancel order via REST API fallback"""
        try:
            if not order_state.order_id:
                logger.error("[WS_ORDER_EXEC] Cannot cancel order without exchange order ID")
                return False

            # Cancel via exchange REST API
            if hasattr(self.exchange, 'cancel_order'):
                result = await self.exchange.cancel_order(order_state.order_id)
                if result and 'count' in result and result['count'] > 0:
                    # Update order state
                    order_state.status = OrderStatus.CANCELLED
                    order_state.updated_at = time.time()
                    self.stats['orders_cancelled'] += 1
                    return True

            return False

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] REST cancellation error: {e}")
            return False

    async def amend_order(self, client_order_id: str, new_quantity: Optional[str] = None,
                         new_price: Optional[str] = None) -> bool:
        """
        Modify an existing order via WebSocket amend_order method

        Args:
            client_order_id: Client order ID to modify
            new_quantity: New order quantity
            new_price: New order price

        Returns:
            bool: True if amendment successful
        """
        try:
            order_state = self.active_orders.get(client_order_id)
            if not order_state:
                logger.warning(f"[WS_ORDER_EXEC] Order not found for amendment: {client_order_id}")
                return False

            if not order_state.order_id:
                logger.error("[WS_ORDER_EXEC] Cannot amend order without exchange order ID")
                return False

            if order_state.is_final_state:
                logger.info(f"[WS_ORDER_EXEC] Cannot amend order in final state: {client_order_id}")
                return False

            # Build amend parameters
            amend_params = {
                "order_id": order_state.order_id
            }

            if new_quantity:
                amend_params["order_qty"] = new_quantity

            if new_price:
                amend_params["limit_price"] = new_price

            # Send amend message via WebSocket
            if self.websocket_authenticated and self.websocket_connected:
                ws_message = {
                    "method": "amend_order",
                    "params": amend_params,
                    "req_id": int(time.time() * 1000)
                }

                if self.websocket_manager and hasattr(self.websocket_manager, 'send_private_message'):
                    success = await self.websocket_manager.send_private_message(ws_message)
                    if success:
                        logger.info(f"[WS_ORDER_EXEC] Order amendment sent: {client_order_id}")
                        return True

            logger.warning("[WS_ORDER_EXEC] WebSocket not available for order amendment")
            return False

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] Error amending order {client_order_id}: {e}")
            if self.guardian:
                await self.guardian.handle_critical_error("order_amendment", e, CriticalityLevel.MEDIUM)
            return False

    async def batch_cancel(self, client_order_ids: list[str]) -> dict[str, bool]:
        """
        Cancel multiple orders efficiently

        Args:
            client_order_ids: List of client order IDs to cancel

        Returns:
            Dict[str, bool]: Results for each order ID
        """
        try:
            results = {}

            # Collect valid order IDs
            order_ids_to_cancel = []
            client_id_mapping = {}

            for client_order_id in client_order_ids:
                order_state = self.active_orders.get(client_order_id)
                if order_state and order_state.order_id and not order_state.is_final_state:
                    order_ids_to_cancel.append(order_state.order_id)
                    client_id_mapping[order_state.order_id] = client_order_id
                else:
                    results[client_order_id] = False

            if not order_ids_to_cancel:
                logger.warning("[WS_ORDER_EXEC] No valid orders to cancel in batch")
                return results

            # Try batch cancellation via WebSocket
            if self.websocket_authenticated and self.websocket_connected:
                success = await self._batch_cancel_websocket(order_ids_to_cancel)
                if success:
                    # Mark all as successfully cancelled
                    for order_id in order_ids_to_cancel:
                        client_id = client_id_mapping[order_id]
                        results[client_id] = True
                        if client_id in self.active_orders:
                            self.active_orders[client_id].status = OrderStatus.CANCELLED
                            self.active_orders[client_id].updated_at = time.time()

                    self.stats['orders_cancelled'] += len(order_ids_to_cancel)
                    logger.info(f"[WS_ORDER_EXEC] Batch cancelled {len(order_ids_to_cancel)} orders via WebSocket")
                    return results

            # Fallback to individual REST cancellations
            logger.info("[WS_ORDER_EXEC] Falling back to individual REST cancellations")
            for client_order_id in client_order_ids:
                if client_order_id not in results:
                    results[client_order_id] = await self.cancel_order(client_order_id)

            return results

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] Batch cancel error: {e}")
            if self.guardian:
                await self.guardian.handle_critical_error("batch_cancel", e, CriticalityLevel.MEDIUM)
            return dict.fromkeys(client_order_ids, False)

    async def _batch_cancel_websocket(self, order_ids: list[str]) -> bool:
        """Cancel multiple orders via WebSocket batch operation"""
        try:
            cancel_params = {
                "order_id": order_ids  # Kraken accepts array for batch cancel
            }

            ws_message = {
                "method": "cancel_order",
                "params": cancel_params,
                "req_id": int(time.time() * 1000)
            }

            if self.websocket_manager and hasattr(self.websocket_manager, 'send_private_message'):
                success = await self.websocket_manager.send_private_message(ws_message)
                if success:
                    logger.info(f"[WS_ORDER_EXEC] Batch cancel message sent for {len(order_ids)} orders")
                    return True

            return False

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] Batch cancel WebSocket error: {e}")
            return False

    async def _handle_execution_update(self, execution_data: list[dict[str, Any]]):
        """
        Handle execution updates from WebSocket executions channel

        Args:
            execution_data: List of execution messages from Kraken
        """
        try:
            logger.info(f"[WS_ORDER_EXEC] Processing {len(execution_data)} execution updates")

            for exec_msg in execution_data:
                try:
                    # Parse execution message
                    execution = OrderExecution.from_kraken_execution(exec_msg)

                    # Find corresponding order
                    client_order_id = None
                    if execution.client_order_id:
                        client_order_id = execution.client_order_id
                    elif execution.order_id in self.order_id_mapping:
                        client_order_id = self.order_id_mapping[execution.order_id]

                    if not client_order_id:
                        logger.warning(f"[WS_ORDER_EXEC] Execution for unknown order: {execution.order_id}")
                        continue

                    # Update order state
                    if client_order_id in self.active_orders:
                        await self._update_order_state(client_order_id, execution)
                    else:
                        logger.warning(f"[WS_ORDER_EXEC] Execution for untracked order: {client_order_id}")

                    # Store execution in history
                    self.execution_history.append(execution)
                    self.stats['execution_messages_processed'] += 1

                    # Call execution callbacks
                    await self._call_execution_callbacks(execution)

                except Exception as e:
                    logger.error(f"[WS_ORDER_EXEC] Error processing individual execution: {e}")
                    continue

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] Error handling execution updates: {e}")
            if self.guardian:
                await self.guardian.handle_critical_error("execution_update", e, CriticalityLevel.MEDIUM)

    async def _update_order_state(self, client_order_id: str, execution: OrderExecution):
        """Update order state based on execution"""
        try:
            order_state = self.active_orders[client_order_id]

            # Update order ID if not set
            if not order_state.order_id and execution.order_id:
                order_state.order_id = execution.order_id
                self.order_id_mapping[execution.order_id] = client_order_id

            # Update execution details
            order_state.status = execution.order_status
            order_state.filled_quantity = execution.filled_quantity
            order_state.remaining_quantity = execution.remaining_quantity
            order_state.avg_price = execution.avg_price
            order_state.updated_at = time.time()

            # Add execution to history
            order_state.executions.append(execution)

            # Update fees
            if execution.fee and execution.fee != "0":
                current_fees = safe_float(order_state.total_fees)
                new_fee = safe_float(execution.fee)
                order_state.total_fees = str(current_fees + new_fee)

            # Update statistics based on status
            if execution.order_status == OrderStatus.FILLED:
                self.stats['orders_filled'] += 1
                logger.info(f"[WS_ORDER_EXEC] Order filled: {client_order_id} - {execution.filled_quantity} @ {execution.avg_price}")
            elif execution.order_status == OrderStatus.CANCELLED:
                self.stats['orders_cancelled'] += 1
                logger.info(f"[WS_ORDER_EXEC] Order cancelled: {client_order_id}")
            elif execution.order_status == OrderStatus.REJECTED:
                self.stats['orders_rejected'] += 1
                logger.warning(f"[WS_ORDER_EXEC] Order rejected: {client_order_id}")

            # Call status callbacks
            await self._call_status_callbacks(client_order_id, order_state)

        except Exception as e:
            logger.error(f"[WS_ORDER_EXEC] Error updating order state for {client_order_id}: {e}")

    async def _call_execution_callbacks(self, execution: OrderExecution):
        """Call registered execution callbacks"""
        for callback in self.execution_callbacks:
            try:
                await callback(execution)
            except Exception as e:
                logger.error(f"[WS_ORDER_EXEC] Execution callback error: {e}")

    async def _call_status_callbacks(self, client_order_id: str, order_state: OrderState):
        """Call registered order status callbacks"""
        for callback in self.order_status_callbacks:
            try:
                await callback(client_order_id, order_state)
            except Exception as e:
                logger.error(f"[WS_ORDER_EXEC] Status callback error: {e}")

    async def _handle_order_failure(self, order_request: OrderRequest, error_message: str):
        """Handle order submission failure"""
        self.consecutive_failures += 1
        self.last_failure_time = time.time()

        # Update order state with error
        if order_request.client_order_id in self.active_orders:
            order_state = self.active_orders[order_request.client_order_id]
            order_state.status = OrderStatus.REJECTED
            order_state.error_message = error_message
            order_state.updated_at = time.time()

        # Activate circuit breaker if too many failures
        if self.consecutive_failures >= self.max_consecutive_failures:
            self.circuit_breaker_active = True
            logger.error(f"[WS_ORDER_EXEC] Circuit breaker activated after {self.consecutive_failures} failures")

            if self.guardian:
                await self.guardian.handle_critical_error(
                    "order_execution_circuit_breaker",
                    Exception(f"Order execution circuit breaker activated: {error_message}"),
                    CriticalityLevel.HIGH
                )

    async def _process_order_queue(self):
        """Background task to process queued orders"""
        while self.processing_orders:
            try:
                # This can be extended for order queueing if needed
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"[WS_ORDER_EXEC] Order queue processing error: {e}")
                await asyncio.sleep(1)

    async def _token_refresh_loop(self):
        """Background task to refresh authentication token"""
        while self.websocket_authenticated and self.processing_orders:
            try:
                await asyncio.sleep(self.token_refresh_interval)

                if self.websocket_manager and hasattr(self.websocket_manager, '_refresh_auth_token'):
                    success = await self.websocket_manager._refresh_auth_token()
                    if success:
                        logger.info("[WS_ORDER_EXEC] Authentication token refreshed")
                    else:
                        logger.warning("[WS_ORDER_EXEC] Token refresh failed")

            except Exception as e:
                logger.error(f"[WS_ORDER_EXEC] Token refresh error: {e}")
                await asyncio.sleep(60)

    async def _cleanup_completed_orders(self):
        """Background task to cleanup completed orders"""
        while self.processing_orders:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes

                current_time = time.time()
                cleanup_age = 3600  # 1 hour

                orders_to_remove = []
                for client_order_id, order_state in list(self.active_orders.items()):
                    if (order_state.is_final_state and
                        current_time - order_state.updated_at > cleanup_age):
                        orders_to_remove.append(client_order_id)

                for client_order_id in orders_to_remove:
                    order_state = self.active_orders.pop(client_order_id, None)
                    if order_state and order_state.order_id:
                        self.order_id_mapping.pop(order_state.order_id, None)

                if orders_to_remove:
                    logger.info(f"[WS_ORDER_EXEC] Cleaned up {len(orders_to_remove)} completed orders")

            except Exception as e:
                logger.error(f"[WS_ORDER_EXEC] Cleanup error: {e}")
                await asyncio.sleep(300)

    # Public API Methods

    def register_execution_callback(self, callback: Callable):
        """Register callback for order executions"""
        self.execution_callbacks.append(callback)
        logger.info("[WS_ORDER_EXEC] Execution callback registered")

    def register_status_callback(self, callback: Callable):
        """Register callback for order status changes"""
        self.order_status_callbacks.append(callback)
        logger.info("[WS_ORDER_EXEC] Status callback registered")

    def get_order_status(self, client_order_id: str) -> Optional[OrderState]:
        """Get current order status"""
        return self.active_orders.get(client_order_id)

    def get_active_orders(self) -> dict[str, OrderState]:
        """Get all active orders"""
        return {k: v for k, v in self.active_orders.items() if not v.is_final_state}

    def get_order_history(self, limit: int = 100) -> list[OrderExecution]:
        """Get recent execution history"""
        return list(self.execution_history)[-limit:]

    def get_statistics(self) -> dict[str, Any]:
        """Get execution manager statistics"""
        stats = self.stats.copy()
        stats.update({
            'active_orders_count': len([o for o in self.active_orders.values() if not o.is_final_state]),
            'total_orders_tracked': len(self.active_orders),
            'websocket_connected': self.websocket_connected,
            'websocket_authenticated': self.websocket_authenticated,
            'circuit_breaker_active': self.circuit_breaker_active,
            'consecutive_failures': self.consecutive_failures,
            'execution_history_count': len(self.execution_history)
        })
        return stats

    async def shutdown(self):
        """Shutdown the order execution manager"""
        logger.info("[WS_ORDER_EXEC] Shutting down order execution manager")

        self.processing_orders = False

        # Cancel any pending orders if needed
        active_orders = self.get_active_orders()
        if active_orders:
            logger.info(f"[WS_ORDER_EXEC] Cancelling {len(active_orders)} active orders on shutdown")
            await self.batch_cancel(list(active_orders.keys()))

        logger.info("[WS_ORDER_EXEC] Order execution manager shutdown complete")


# Integration helper for existing bot code
class OrderExecutionIntegration:
    """Helper class to integrate WebSocket order execution with existing bot"""

    def __init__(self, bot, websocket_manager):
        self.bot = bot
        self.execution_manager = WebSocketOrderExecutionManager(
            exchange_client=bot.exchange,
            websocket_manager=websocket_manager,
            guardian=getattr(bot, 'guardian', None),
            rate_limiter=getattr(bot, 'rate_limiter', None)
        )

    async def initialize(self):
        """Initialize the integration"""
        success = await self.execution_manager.initialize()
        if success:
            # Register callbacks for bot integration
            self.execution_manager.register_execution_callback(self._handle_execution)
            self.execution_manager.register_status_callback(self._handle_status_change)
            logger.info("[WS_ORDER_INTEGRATION] Order execution integration initialized")
        return success

    async def _handle_execution(self, execution: OrderExecution):
        """Handle order execution for bot integration"""
        try:
            # Update bot's order tracking if it exists
            if hasattr(self.bot, 'order_tracker'):
                await self.bot.order_tracker.update_from_execution(execution)

            # Update profit tracking if it exists
            if hasattr(self.bot, 'profit_tracker') and execution.order_status == OrderStatus.FILLED:
                await self.bot.profit_tracker.record_trade(
                    symbol=execution.symbol,
                    side=execution.side,
                    quantity=execution.filled_quantity,
                    price=execution.avg_price,
                    fee=execution.fee
                )

        except Exception as e:
            logger.error(f"[WS_ORDER_INTEGRATION] Execution handling error: {e}")

    async def _handle_status_change(self, client_order_id: str, order_state: OrderState):
        """Handle order status changes for bot integration"""
        try:
            # Notify bot of order status changes if it has handlers
            if hasattr(self.bot, 'on_order_status_change'):
                await self.bot.on_order_status_change(client_order_id, order_state)

        except Exception as e:
            logger.error(f"[WS_ORDER_INTEGRATION] Status change handling error: {e}")

    async def place_order(self, symbol: str, side: str, quantity: str,
                         order_type: str = "limit", price: str = None, **kwargs) -> Optional[str]:
        """
        Convenient order placement method for existing bot code

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            quantity: Order quantity
            order_type: Order type ('market', 'limit', etc.)
            price: Order price for limit orders
            **kwargs: Additional order parameters

        Returns:
            str: Client order ID if successful
        """
        try:
            order_request = OrderRequest(
                symbol=symbol,
                side=OrderSide(side.lower()),
                order_type=OrderType(order_type.lower()),
                quantity=quantity,
                price=price,
                **kwargs
            )

            return await self.execution_manager.add_order(order_request)

        except Exception as e:
            logger.error(f"[WS_ORDER_INTEGRATION] Order placement error: {e}")
            return None
