"""
Unified sell coordinator for managing all sell operations in the trading bot.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SellReason(Enum):
    """Reasons for selling positions."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    RISK_MANAGEMENT = "risk_management"
    PORTFOLIO_REBALANCE = "portfolio_rebalance"
    MARKET_CONDITION = "market_condition"
    MANUAL = "manual"
    EMERGENCY = "emergency"


class SellPriority(Enum):
    """Priority levels for sell orders."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


@dataclass
class SellOrder:
    """Sell order information."""
    id: str
    symbol: str
    quantity: float
    price: Optional[float] = None
    order_type: str = "market"  # market, limit, stop, stop_limit
    reason: SellReason = SellReason.MANUAL
    priority: SellPriority = SellPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    status: str = "pending"  # pending, executing, completed, failed, cancelled
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SellResult:
    """Result of a sell operation."""
    success: bool
    order_id: str
    executed_quantity: float
    executed_price: float
    fees: float
    total_proceeds: float
    execution_time: datetime
    error_message: Optional[str] = None


class UnifiedSellCoordinator:
    """
    Unified sell coordinator that manages all sell operations across the trading bot.
    Handles prioritization, execution, and coordination of sell orders.
    """

    def __init__(self,
                 max_concurrent_sells: int = 5,
                 order_timeout: int = 300,
                 retry_attempts: int = 3,
                 retry_delay: int = 5):
        """
        Initialize the unified sell coordinator.
        
        Args:
            max_concurrent_sells: Maximum number of concurrent sell operations
            order_timeout: Timeout for sell orders in seconds
            retry_attempts: Number of retry attempts for failed orders
            retry_delay: Delay between retry attempts in seconds
        """
        self.max_concurrent_sells = max_concurrent_sells
        self.order_timeout = order_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # Order management
        self.pending_orders: Dict[str, SellOrder] = {}
        self.executing_orders: Dict[str, SellOrder] = {}
        self.completed_orders: Dict[str, SellOrder] = {}
        self.failed_orders: Dict[str, SellOrder] = {}

        # Priority queues
        self.priority_queue: List[SellOrder] = []
        self.emergency_queue: List[SellOrder] = []

        # Execution state
        self.active_sells = 0
        self.is_running = False
        self.coordinator_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Exchange interface (would be injected in real implementation)
        self.exchange = None

        # Statistics
        self.total_sells = 0
        self.successful_sells = 0
        self.failed_sells = 0
        self.total_proceeds = 0.0
        self.total_fees = 0.0

        # Callbacks
        self.on_sell_complete = None
        self.on_sell_failed = None
        self.on_emergency_sell = None

        logger.info("UnifiedSellCoordinator initialized")

    def start(self) -> None:
        """Start the sell coordinator."""
        if self.is_running:
            logger.warning("Sell coordinator already running")
            return

        self.is_running = True
        self.coordinator_thread = threading.Thread(target=self._coordination_loop, daemon=True)
        self.coordinator_thread.start()

        logger.info("Sell coordinator started")

    def stop(self) -> None:
        """Stop the sell coordinator."""
        if not self.is_running:
            return

        self.is_running = False

        if self.coordinator_thread and self.coordinator_thread.is_alive():
            self.coordinator_thread.join(timeout=10)

        logger.info("Sell coordinator stopped")

    def _coordination_loop(self) -> None:
        """Main coordination loop."""
        while self.is_running:
            try:
                # Process emergency sells first
                self._process_emergency_sells()

                # Process regular sells
                self._process_regular_sells()

                # Check for timed out orders
                self._check_order_timeouts()

                # Clean up completed orders
                self._cleanup_old_orders()

                # Sleep before next iteration
                threading.Event().wait(1)

            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                threading.Event().wait(5)

    def _process_emergency_sells(self) -> None:
        """Process emergency sell orders."""
        with self.lock:
            while self.emergency_queue and self.active_sells < self.max_concurrent_sells:
                order = self.emergency_queue.pop(0)
                self._execute_sell_order(order)

    def _process_regular_sells(self) -> None:
        """Process regular sell orders."""
        with self.lock:
            # Sort priority queue by priority and creation time
            self.priority_queue.sort(key=lambda x: (x.priority.value, x.created_at), reverse=True)

            while self.priority_queue and self.active_sells < self.max_concurrent_sells:
                order = self.priority_queue.pop(0)
                self._execute_sell_order(order)

    def _execute_sell_order(self, order: SellOrder) -> None:
        """Execute a sell order."""
        try:
            # Move order to executing state
            self.executing_orders[order.id] = order
            self.pending_orders.pop(order.id, None)

            order.status = "executing"
            self.active_sells += 1

            # Execute order in a separate thread
            execution_thread = threading.Thread(
                target=self._execute_order_async,
                args=(order,),
                daemon=True
            )
            execution_thread.start()

        except Exception as e:
            logger.error(f"Error executing sell order {order.id}: {e}")
            self._handle_order_failure(order, str(e))

    def _execute_order_async(self, order: SellOrder) -> None:
        """Execute order asynchronously."""
        try:
            # Simulate order execution (in real implementation, this would call the exchange)
            result = self._simulate_order_execution(order)

            if result.success:
                self._handle_order_success(order, result)
            else:
                self._handle_order_failure(order, result.error_message)

        except Exception as e:
            logger.error(f"Error in async order execution: {e}")
            self._handle_order_failure(order, str(e))
        finally:
            with self.lock:
                self.active_sells -= 1

    def _simulate_order_execution(self, order: SellOrder) -> SellResult:
        """Simulate order execution (placeholder for real exchange integration)."""
        import random
        import time

        # Simulate execution time
        time.sleep(random.uniform(0.5, 2.0))

        # Simulate success/failure
        if random.random() > 0.1:  # 90% success rate
            # Use a more realistic price simulation based on symbol
            executed_price = order.price or self._get_realistic_market_price(order.symbol)
            executed_quantity = order.quantity
            fees = executed_quantity * executed_price * 0.0026  # Taker fee
            total_proceeds = (executed_quantity * executed_price) - fees

            return SellResult(
                success=True,
                order_id=order.id,
                executed_quantity=executed_quantity,
                executed_price=executed_price,
                fees=fees,
                total_proceeds=total_proceeds,
                execution_time=datetime.now()
            )
        else:
            return SellResult(
                success=False,
                order_id=order.id,
                executed_quantity=0.0,
                executed_price=0.0,
                fees=0.0,
                total_proceeds=0.0,
                execution_time=datetime.now(),
                error_message="Simulated execution failure"
            )

    def _handle_order_success(self, order: SellOrder, result: SellResult) -> None:
        """Handle successful order execution."""
        with self.lock:
            order.status = "completed"
            order.executed_at = result.execution_time

            # Move to completed orders
            self.completed_orders[order.id] = order
            self.executing_orders.pop(order.id, None)

            # Update statistics
            self.total_sells += 1
            self.successful_sells += 1
            self.total_proceeds += result.total_proceeds
            self.total_fees += result.fees

            logger.info(f"Sell order {order.id} completed successfully: {result.executed_quantity} {order.symbol} @ {result.executed_price}")

        # Call completion callback
        if self.on_sell_complete:
            try:
                self.on_sell_complete(order, result)
            except Exception as e:
                logger.error(f"Error in sell completion callback: {e}")

    def _handle_order_failure(self, order: SellOrder, error_message: str) -> None:
        """Handle failed order execution."""
        with self.lock:
            order.status = "failed"
            order.error_message = error_message

            # Check if we should retry
            retry_count = order.metadata.get('retry_count', 0)
            if retry_count < self.retry_attempts:
                # Retry the order
                order.metadata['retry_count'] = retry_count + 1
                order.status = "pending"

                # Add back to appropriate queue
                if order.priority == SellPriority.EMERGENCY:
                    self.emergency_queue.append(order)
                else:
                    self.priority_queue.append(order)

                logger.warning(f"Retrying sell order {order.id} (attempt {retry_count + 1})")
            else:
                # Move to failed orders
                self.failed_orders[order.id] = order
                self.executing_orders.pop(order.id, None)

                # Update statistics
                self.total_sells += 1
                self.failed_sells += 1

                logger.error(f"Sell order {order.id} failed after {retry_count + 1} attempts: {error_message}")

        # Call failure callback
        if self.on_sell_failed:
            try:
                self.on_sell_failed(order, error_message)
            except Exception as e:
                logger.error(f"Error in sell failure callback: {e}")

    def _check_order_timeouts(self) -> None:
        """Check for timed out orders."""
        current_time = datetime.now()
        timeout_threshold = timedelta(seconds=self.order_timeout)

        with self.lock:
            timed_out_orders = []

            for order_id, order in self.executing_orders.items():
                if current_time - order.created_at > timeout_threshold:
                    timed_out_orders.append(order)

            for order in timed_out_orders:
                self._handle_order_failure(order, "Order execution timeout")

    def _cleanup_old_orders(self) -> None:
        """Clean up old completed and failed orders."""
        current_time = datetime.now()
        cleanup_threshold = timedelta(hours=24)

        with self.lock:
            # Clean up completed orders
            completed_to_remove = [
                order_id for order_id, order in self.completed_orders.items()
                if current_time - order.created_at > cleanup_threshold
            ]

            for order_id in completed_to_remove:
                del self.completed_orders[order_id]

            # Clean up failed orders
            failed_to_remove = [
                order_id for order_id, order in self.failed_orders.items()
                if current_time - order.created_at > cleanup_threshold
            ]

            for order_id in failed_to_remove:
                del self.failed_orders[order_id]

    def submit_sell_order(self,
                         symbol: str,
                         quantity: float,
                         price: Optional[float] = None,
                         order_type: str = "market",
                         reason: SellReason = SellReason.MANUAL,
                         priority: SellPriority = SellPriority.MEDIUM,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Submit a sell order for execution.
        
        Args:
            symbol: Trading pair symbol
            quantity: Quantity to sell
            price: Price for limit orders
            order_type: Type of order (market, limit, stop, etc.)
            reason: Reason for the sell
            priority: Priority level
            metadata: Additional metadata
            
        Returns:
            Order ID
        """
        import uuid

        order_id = str(uuid.uuid4())

        order = SellOrder(
            id=order_id,
            symbol=symbol,
            quantity=quantity,
            price=price,
            order_type=order_type,
            reason=reason,
            priority=priority,
            metadata=metadata or {}
        )

        with self.lock:
            self.pending_orders[order_id] = order

            # Add to appropriate queue
            if priority == SellPriority.EMERGENCY:
                self.emergency_queue.append(order)

                # Call emergency callback
                if self.on_emergency_sell:
                    try:
                        self.on_emergency_sell(order)
                    except Exception as e:
                        logger.error(f"Error in emergency sell callback: {e}")
            else:
                self.priority_queue.append(order)

        logger.info(f"Submitted sell order {order_id}: {quantity} {symbol} ({reason.value}, {priority.value})")

        return order_id

    def cancel_sell_order(self, order_id: str) -> bool:
        """
        Cancel a pending sell order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if order was cancelled
        """
        with self.lock:
            # Check if order is pending
            if order_id in self.pending_orders:
                order = self.pending_orders.pop(order_id)
                order.status = "cancelled"

                # Remove from queues
                self.priority_queue = [o for o in self.priority_queue if o.id != order_id]
                self.emergency_queue = [o for o in self.emergency_queue if o.id != order_id]

                logger.info(f"Cancelled sell order {order_id}")
                return True
            else:
                logger.warning(f"Cannot cancel order {order_id} - not in pending state")
                return False

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a sell order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order status dictionary or None if not found
        """
        # Check all order dictionaries
        for order_dict in [self.pending_orders, self.executing_orders,
                          self.completed_orders, self.failed_orders]:
            if order_id in order_dict:
                order = order_dict[order_id]
                return {
                    'id': order.id,
                    'symbol': order.symbol,
                    'quantity': order.quantity,
                    'price': order.price,
                    'order_type': order.order_type,
                    'reason': order.reason.value,
                    'priority': order.priority.value,
                    'status': order.status,
                    'created_at': order.created_at.isoformat(),
                    'executed_at': order.executed_at.isoformat() if order.executed_at else None,
                    'error_message': order.error_message,
                    'metadata': order.metadata
                }

        return None

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get all pending sell orders."""
        with self.lock:
            return [self.get_order_status(order_id) for order_id in self.pending_orders.keys()]

    def get_executing_orders(self) -> List[Dict[str, Any]]:
        """Get all executing sell orders."""
        with self.lock:
            return [self.get_order_status(order_id) for order_id in self.executing_orders.keys()]

    def emergency_sell_all(self, reason: str = "Emergency liquidation") -> List[str]:
        """
        Emergency sell all positions.
        
        Args:
            reason: Reason for emergency sell
            
        Returns:
            List of order IDs
        """
        # This would typically get all open positions from the portfolio
        # For now, we'll just log the emergency action

        logger.critical(f"EMERGENCY SELL ALL triggered: {reason}")

        # In a real implementation, this would:
        # 1. Get all open positions
        # 2. Submit emergency sell orders for each position
        # 3. Return the order IDs

        return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get sell coordinator statistics."""
        with self.lock:
            return {
                'total_sells': self.total_sells,
                'successful_sells': self.successful_sells,
                'failed_sells': self.failed_sells,
                'success_rate': self.successful_sells / max(self.total_sells, 1),
                'total_proceeds': self.total_proceeds,
                'total_fees': self.total_fees,
                'net_proceeds': self.total_proceeds - self.total_fees,
                'active_sells': self.active_sells,
                'pending_orders': len(self.pending_orders),
                'executing_orders': len(self.executing_orders),
                'completed_orders': len(self.completed_orders),
                'failed_orders': len(self.failed_orders),
                'emergency_queue_size': len(self.emergency_queue),
                'priority_queue_size': len(self.priority_queue),
                'is_running': self.is_running
            }

    def set_callbacks(self,
                     on_sell_complete: Optional[Callable] = None,
                     on_sell_failed: Optional[Callable] = None,
                     on_emergency_sell: Optional[Callable] = None) -> None:
        """
        Set callback functions for sell events.
        
        Args:
            on_sell_complete: Called when a sell order completes
            on_sell_failed: Called when a sell order fails
            on_emergency_sell: Called when an emergency sell is triggered
        """
        self.on_sell_complete = on_sell_complete
        self.on_sell_failed = on_sell_failed
        self.on_emergency_sell = on_emergency_sell

        logger.info("Sell coordinator callbacks set")

    def get_orders_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get all orders for a specific symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            List of order status dictionaries
        """
        orders = []

        for order_dict in [self.pending_orders, self.executing_orders,
                          self.completed_orders, self.failed_orders]:
            for order in order_dict.values():
                if order.symbol == symbol:
                    orders.append(self.get_order_status(order.id))

        return orders

    def get_orders_by_reason(self, reason: SellReason) -> List[Dict[str, Any]]:
        """
        Get all orders for a specific reason.
        
        Args:
            reason: Sell reason
            
        Returns:
            List of order status dictionaries
        """
        orders = []

        for order_dict in [self.pending_orders, self.executing_orders,
                          self.completed_orders, self.failed_orders]:
            for order in order_dict.values():
                if order.reason == reason:
                    orders.append(self.get_order_status(order.id))

        return orders

    def _get_realistic_market_price(self, symbol: str) -> float:
        """Get a realistic market price for simulation purposes"""
        # Simplified price mapping for common trading pairs
        price_ranges = {
            'BTC/USDT': (30000, 70000),
            'ETH/USDT': (1500, 4000),
            'SHIB/USDT': (0.000006, 0.00003),
            'DOGE/USDT': (0.05, 0.30),
            'ADA/USDT': (0.25, 1.20),
            'DOT/USDT': (4.0, 12.0),
            'LINK/USDT': (5.0, 25.0),
            'UNI/USDT': (3.0, 15.0),
            'SOL/USDT': (15.0, 200.0),
            'MATIC/USDT': (0.40, 2.50)
        }

        # Get price range for symbol or use default
        min_price, max_price = price_ranges.get(symbol, (0.01, 100.0))

        # Return random price within realistic range
        return random.uniform(min_price, max_price)

    def __del__(self):
        """Cleanup when object is destroyed."""
        if self.is_running:
            self.stop()
