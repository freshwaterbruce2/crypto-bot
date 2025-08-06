"""
Order Execution Assistant - Order placement and management helper
"""

import asyncio
import logging
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List


class OrderType(Enum):
    """Types of orders"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    PARTIAL = "partial"
    FAILED = "failed"


class OrderExecutionAssistant:
    """Assistant for order execution operations"""

    def __init__(self, manager_or_config):
        # Handle both manager object and config dict
        if hasattr(manager_or_config, 'config'):
            self.manager = manager_or_config
            self.config = manager_or_config.config
        else:
            self.manager = None
            self.config = manager_or_config
        self.logger = logging.getLogger(__name__)

    def prepare_market_order(self, symbol: str, side: str, amount: Decimal) -> Dict[str, Any]:
        """Prepare market order parameters"""
        try:
            order_params = {
                'symbol': symbol,
                'side': side.lower(),
                'type': OrderType.MARKET.value,
                'amount': str(amount),
                'timestamp': None  # Will be set by exchange
            }

            self.logger.info(f"Prepared market order: {side} {amount} {symbol}")
            return order_params

        except Exception as e:
            self.logger.error(f"Market order preparation error: {e}")
            return {}

    def prepare_limit_order(self, symbol: str, side: str, amount: Decimal, price: Decimal) -> Dict[str, Any]:
        """Prepare limit order parameters"""
        try:
            order_params = {
                'symbol': symbol,
                'side': side.lower(),
                'type': OrderType.LIMIT.value,
                'amount': str(amount),
                'price': str(price),
                'timestamp': None
            }

            self.logger.info(f"Prepared limit order: {side} {amount} {symbol} @ {price}")
            return order_params

        except Exception as e:
            self.logger.error(f"Limit order preparation error: {e}")
            return {}

    def validate_order_parameters(self, order_params: Dict[str, Any]) -> bool:
        """Validate order parameters before execution"""
        try:
            required_fields = ['symbol', 'side', 'type', 'amount']

            # Check required fields
            for field in required_fields:
                if field not in order_params:
                    self.logger.error(f"Missing required field: {field}")
                    return False

            # Validate amount
            try:
                amount = Decimal(order_params['amount'])
                if amount <= 0:
                    self.logger.error("Order amount must be positive")
                    return False
            except:
                self.logger.error("Invalid amount format")
                return False

            # Validate side
            if order_params['side'] not in ['buy', 'sell']:
                self.logger.error("Invalid order side")
                return False

            # Validate price for limit orders
            if order_params['type'] == OrderType.LIMIT.value:
                if 'price' not in order_params:
                    self.logger.error("Limit order missing price")
                    return False
                try:
                    price = Decimal(order_params['price'])
                    if price <= 0:
                        self.logger.error("Order price must be positive")
                        return False
                except:
                    self.logger.error("Invalid price format")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Order validation error: {e}")
            return False

    def calculate_order_cost(self, side: str, amount: Decimal, price: Decimal) -> Decimal:
        """Calculate estimated order cost"""
        try:
            if side.lower() == 'buy':
                cost = amount * price
            else:  # sell
                cost = amount  # For sell orders, cost is the amount being sold

            return cost

        except Exception as e:
            self.logger.error(f"Order cost calculation error: {e}")
            return Decimal('0')

    def estimate_fees(self, order_cost: Decimal, fee_rate: float = 0.0026) -> Decimal:
        """Estimate trading fees"""
        try:
            fee = order_cost * Decimal(str(fee_rate))
            return fee

        except Exception as e:
            self.logger.error(f"Fee estimation error: {e}")
            return Decimal('0')

    def check_order_status(self, order_id: str) -> Dict[str, Any]:
        """Check order status (mock implementation)"""
        try:
            # Mock implementation - in real version would query exchange
            return {
                'order_id': order_id,
                'status': OrderStatus.PENDING.value,
                'filled_amount': '0',
                'remaining_amount': '0',
                'average_price': '0'
            }

        except Exception as e:
            self.logger.error(f"Order status check error: {e}")
            return {}

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions (synchronous version for compatibility)"""
        try:
            # Mock implementation for compatibility
            # In a real implementation, this would fetch from the exchange
            self.logger.debug("Fetching open positions (mock implementation)")
            return []

        except Exception as e:
            self.logger.error(f"Error getting open positions: {e}")
            return []

    # ASYNC METHODS REQUIRED BY INFINITY TRADING MANAGER

    async def initialize(self):
        """Initialize the execution assistant"""
        try:
            self.logger.info("[EXECUTION_ASSISTANT] Initializing...")
            # Connect to exchange if manager has one
            if self.manager and hasattr(self.manager, 'bot') and hasattr(self.manager.bot, 'exchange'):
                self.exchange = self.manager.bot.exchange
                self.logger.info("[EXECUTION_ASSISTANT] Connected to exchange")
            else:
                self.logger.warning("[EXECUTION_ASSISTANT] No exchange connection available")

            self.logger.info("[EXECUTION_ASSISTANT] Initialization complete")

        except Exception as e:
            self.logger.error(f"[EXECUTION_ASSISTANT] Initialization error: {e}")

    async def stop(self):
        """Stop the execution assistant"""
        try:
            self.logger.info("[EXECUTION_ASSISTANT] Stopping...")
            # Cleanup any resources
            self.logger.info("[EXECUTION_ASSISTANT] Stopped successfully")

        except Exception as e:
            self.logger.error(f"[EXECUTION_ASSISTANT] Stop error: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of the execution assistant"""
        try:
            # Check if we have exchange connection
            has_exchange = (
                hasattr(self, 'exchange') and self.exchange is not None or
                (self.manager and hasattr(self.manager, 'bot') and
                 hasattr(self.manager.bot, 'exchange') and self.manager.bot.exchange is not None)
            )

            return {
                'healthy': has_exchange,
                'exchange_connected': has_exchange,
                'timestamp': asyncio.get_event_loop().time()
            }

        except Exception as e:
            self.logger.error(f"[EXECUTION_ASSISTANT] Health check error: {e}")
            return {'healthy': False, 'error': str(e)}

    async def execute_buy(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a buy order based on signal"""
        try:
            self.logger.info(f"[EXECUTION_ASSISTANT] Executing buy signal for {signal.get('symbol', 'unknown')}")

            # Extract signal parameters
            symbol = signal.get('symbol')
            amount = signal.get('amount', 0)
            price = signal.get('price')
            order_type = signal.get('type', 'market')

            if not symbol or not amount:
                return {
                    'success': False,
                    'error': 'Invalid signal: missing symbol or amount',
                    'signal': signal
                }

            # Get exchange reference
            exchange = getattr(self, 'exchange', None)
            if not exchange and self.manager and hasattr(self.manager, 'bot'):
                exchange = getattr(self.manager.bot, 'exchange', None)

            if not exchange:
                self.logger.error("[EXECUTION_ASSISTANT] No exchange available for order execution")
                return {
                    'success': False,
                    'error': 'No exchange connection available',
                    'signal': signal
                }

            # Prepare order parameters
            if order_type.lower() == 'limit' and price:
                order_params = self.prepare_limit_order(symbol, 'buy', Decimal(str(amount)), Decimal(str(price)))
            else:
                order_params = self.prepare_market_order(symbol, 'buy', Decimal(str(amount)))

            # Validate order
            if not self.validate_order_parameters(order_params):
                return {
                    'success': False,
                    'error': 'Order validation failed',
                    'signal': signal
                }

            # Execute order through exchange
            try:
                # Check if exchange has async create_order method
                if hasattr(exchange, 'create_order'):
                    if asyncio.iscoroutinefunction(exchange.create_order):
                        order_result = await exchange.create_order(
                            symbol=order_params['symbol'],
                            type=order_params['type'],
                            side=order_params['side'],
                            amount=float(order_params['amount']),
                            price=float(order_params.get('price', 0)) if order_params.get('price') else None
                        )
                    else:
                        order_result = exchange.create_order(
                            symbol=order_params['symbol'],
                            type=order_params['type'],
                            side=order_params['side'],
                            amount=float(order_params['amount']),
                            price=float(order_params.get('price', 0)) if order_params.get('price') else None
                        )

                    self.logger.info(f"[EXECUTION_ASSISTANT] Buy order executed: {order_result.get('id', 'unknown_id')}")

                    return {
                        'success': True,
                        'order_id': order_result.get('id'),
                        'order_result': order_result,
                        'signal': signal
                    }

                else:
                    self.logger.error("[EXECUTION_ASSISTANT] Exchange doesn't support create_order method")
                    return {
                        'success': False,
                        'error': 'Exchange method not available',
                        'signal': signal
                    }

            except Exception as order_error:
                self.logger.error(f"[EXECUTION_ASSISTANT] Order execution failed: {order_error}")
                return {
                    'success': False,
                    'error': f'Order execution failed: {str(order_error)}',
                    'signal': signal
                }

        except Exception as e:
            self.logger.error(f"[EXECUTION_ASSISTANT] Execute buy error: {e}")
            return {
                'success': False,
                'error': f'Execute buy error: {str(e)}',
                'signal': signal
            }

    async def execute_sell(self, position: Dict[str, Any], sell_decision: Any) -> Dict[str, Any]:
        """Execute a sell order for a position"""
        try:
            symbol = position.get('symbol')
            amount = position.get('amount', 0)

            self.logger.info(f"[EXECUTION_ASSISTANT] Executing sell for {symbol}, amount: {amount}")

            if not symbol or not amount:
                return {
                    'success': False,
                    'error': 'Invalid position: missing symbol or amount',
                    'position': position
                }

            # Get exchange reference
            exchange = getattr(self, 'exchange', None)
            if not exchange and self.manager and hasattr(self.manager, 'bot'):
                exchange = getattr(self.manager.bot, 'exchange', None)

            if not exchange:
                self.logger.error("[EXECUTION_ASSISTANT] No exchange available for sell execution")
                return {
                    'success': False,
                    'error': 'No exchange connection available',
                    'position': position
                }

            # Determine sell price and type
            sell_price = None
            order_type = 'market'

            if hasattr(sell_decision, 'price') and sell_decision.price:
                sell_price = sell_decision.price
                order_type = 'limit'
            elif hasattr(sell_decision, 'order_type'):
                order_type = sell_decision.order_type

            # Prepare sell order
            if order_type == 'limit' and sell_price:
                order_params = self.prepare_limit_order(symbol, 'sell', Decimal(str(amount)), Decimal(str(sell_price)))
            else:
                order_params = self.prepare_market_order(symbol, 'sell', Decimal(str(amount)))

            # Validate order
            if not self.validate_order_parameters(order_params):
                return {
                    'success': False,
                    'error': 'Sell order validation failed',
                    'position': position
                }

            # Execute sell order
            try:
                if hasattr(exchange, 'create_order'):
                    if asyncio.iscoroutinefunction(exchange.create_order):
                        order_result = await exchange.create_order(
                            symbol=order_params['symbol'],
                            type=order_params['type'],
                            side=order_params['side'],
                            amount=float(order_params['amount']),
                            price=float(order_params.get('price', 0)) if order_params.get('price') else None
                        )
                    else:
                        order_result = exchange.create_order(
                            symbol=order_params['symbol'],
                            type=order_params['type'],
                            side=order_params['side'],
                            amount=float(order_params['amount']),
                            price=float(order_params.get('price', 0)) if order_params.get('price') else None
                        )

                    # Calculate proceeds and profit
                    proceeds = float(order_params['amount']) * float(order_params.get('price', 0)) if order_params.get('price') else 0
                    entry_price = position.get('entry_price', 0)
                    profit = proceeds - (float(order_params['amount']) * entry_price) if entry_price else 0

                    self.logger.info(f"[EXECUTION_ASSISTANT] Sell order executed: {order_result.get('id', 'unknown_id')}, profit: ${profit:.2f}")

                    return {
                        'success': True,
                        'order_id': order_result.get('id'),
                        'order_result': order_result,
                        'position': position,
                        'side': 'sell',
                        'proceeds': proceeds,
                        'profit': profit,
                        'symbol': symbol
                    }

                else:
                    return {
                        'success': False,
                        'error': 'Exchange create_order method not available',
                        'position': position
                    }

            except Exception as order_error:
                self.logger.error(f"[EXECUTION_ASSISTANT] Sell order execution failed: {order_error}")
                return {
                    'success': False,
                    'error': f'Sell order failed: {str(order_error)}',
                    'position': position
                }

        except Exception as e:
            self.logger.error(f"[EXECUTION_ASSISTANT] Execute sell error: {e}")
            return {
                'success': False,
                'error': f'Execute sell error: {str(e)}',
                'position': position
            }
