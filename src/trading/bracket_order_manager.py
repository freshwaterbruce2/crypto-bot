"""
Bracket Order Manager for Micro-Scalping
=========================================

Implements bracket orders (TP/SL) for SHIB micro-scalping strategy.
Designed for Kraken Pro fee-free trading with 0.8-4% profit targets.

Features:
- Simultaneous TP/SL order placement
- AmendOrder support for queue priority preservation
- Dynamic profit target adjustment
- Risk management with tight stop losses
- WebSocket V2 native execution
"""

import asyncio
import logging
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


class BracketOrderManager:
    """Manages bracket orders for micro-scalping strategy"""

    def __init__(self, exchange_client, config: dict = None):
        """
        Initialize bracket order manager

        Args:
            exchange_client: Exchange client for order execution
            config: Configuration parameters
        """
        self.exchange = exchange_client
        self.config = config or self._get_default_config()

        # Track active bracket orders
        self.active_brackets: dict[str, dict] = {}

        # Performance metrics
        self.total_brackets = 0
        self.successful_brackets = 0
        self.stopped_out = 0

        logger.info("[BRACKET_ORDERS] Initialized with profit target: {}%".format(
            self.config['default_profit_target'] * 100
        ))

    def _get_default_config(self) -> dict:
        """Get default configuration for SHIB micro-scalping"""
        return {
            'default_profit_target': 0.008,  # 0.8% profit target
            'default_stop_loss': 0.004,      # 0.4% stop loss
            'use_amend_order': True,          # Use AmendOrder for queue priority
            'enable_trailing': False,         # Disable trailing for micro-scalping
            'max_profit_target': 0.04,        # 4% max profit
            'min_profit_target': 0.005,       # 0.5% min profit
            'position_size_usdt': 10.0,       # $10 position size
        }

    async def place_bracket_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        entry_price: Optional[str] = None,
        profit_target: Optional[float] = None,
        stop_loss: Optional[float] = None
    ) -> dict:
        """
        Place a bracket order (entry + TP + SL)

        Args:
            symbol: Trading pair (e.g., 'SHIB/USDT')
            side: 'buy' or 'sell'
            quantity: Order quantity
            entry_price: Entry price (None for market order)
            profit_target: Profit target percentage (default from config)
            stop_loss: Stop loss percentage (default from config)

        Returns:
            Dict with order IDs and status
        """
        try:
            profit_target = profit_target or self.config['default_profit_target']
            stop_loss = stop_loss or self.config['default_stop_loss']

            # Place entry order
            if entry_price:
                # Limit order
                entry_order = await self._place_limit_order(
                    symbol, side, quantity, entry_price
                )
            else:
                # Market order
                entry_order = await self._place_market_order(
                    symbol, side, quantity
                )

            if not entry_order or 'error' in entry_order:
                logger.error(f"[BRACKET_ORDERS] Failed to place entry order: {entry_order}")
                return {'error': 'Failed to place entry order'}

            # Get actual entry price
            actual_entry_price = Decimal(entry_order.get('price', entry_price or '0'))

            if actual_entry_price == 0:
                logger.error("[BRACKET_ORDERS] Invalid entry price")
                return {'error': 'Invalid entry price'}

            # Calculate TP and SL prices
            if side == 'buy':
                tp_price = actual_entry_price * Decimal(1 + profit_target)
                sl_price = actual_entry_price * Decimal(1 - stop_loss)
            else:  # sell
                tp_price = actual_entry_price * Decimal(1 - profit_target)
                sl_price = actual_entry_price * Decimal(1 + stop_loss)

            # Place TP and SL orders simultaneously
            tp_task = asyncio.create_task(
                self._place_take_profit_order(
                    symbol,
                    'sell' if side == 'buy' else 'buy',
                    quantity,
                    str(tp_price)
                )
            )

            sl_task = asyncio.create_task(
                self._place_stop_loss_order(
                    symbol,
                    'sell' if side == 'buy' else 'buy',
                    quantity,
                    str(sl_price)
                )
            )

            # Wait for both orders
            tp_order, sl_order = await asyncio.gather(tp_task, sl_task)

            # Create bracket record
            bracket_id = f"bracket_{symbol}_{entry_order.get('txid', 'unknown')}"

            self.active_brackets[bracket_id] = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'entry_order_id': entry_order.get('txid'),
                'entry_price': str(actual_entry_price),
                'tp_order_id': tp_order.get('txid') if tp_order and 'txid' in tp_order else None,
                'tp_price': str(tp_price),
                'sl_order_id': sl_order.get('txid') if sl_order and 'txid' in sl_order else None,
                'sl_price': str(sl_price),
                'profit_target': profit_target,
                'stop_loss': stop_loss,
                'created_at': asyncio.get_event_loop().time(),
                'status': 'active'
            }

            self.total_brackets += 1

            logger.info(f"[BRACKET_ORDERS] Placed bracket order {bracket_id}")
            logger.info(f"  Entry: {actual_entry_price}, TP: {tp_price:.8f}, SL: {sl_price:.8f}")

            return {
                'success': True,
                'bracket_id': bracket_id,
                'entry_order': entry_order,
                'tp_order': tp_order,
                'sl_order': sl_order,
                'bracket_details': self.active_brackets[bracket_id]
            }

        except Exception as e:
            logger.error(f"[BRACKET_ORDERS] Error placing bracket order: {e}")
            return {'error': str(e)}

    async def amend_bracket_order(
        self,
        bracket_id: str,
        new_profit_target: Optional[float] = None,
        new_stop_loss: Optional[float] = None
    ) -> dict:
        """
        Amend an existing bracket order using AmendOrder (preserves queue priority)

        Args:
            bracket_id: Bracket order ID
            new_profit_target: New profit target percentage
            new_stop_loss: New stop loss percentage

        Returns:
            Dict with amendment status
        """
        if bracket_id not in self.active_brackets:
            return {'error': 'Bracket order not found'}

        bracket = self.active_brackets[bracket_id]

        if bracket['status'] != 'active':
            return {'error': 'Bracket order not active'}

        try:
            entry_price = Decimal(bracket['entry_price'])
            side = bracket['side']

            tasks = []

            # Amend TP order if new target provided
            if new_profit_target and bracket['tp_order_id']:
                if side == 'buy':
                    new_tp_price = entry_price * Decimal(1 + new_profit_target)
                else:
                    new_tp_price = entry_price * Decimal(1 - new_profit_target)

                tasks.append(
                    self._amend_order(
                        bracket['tp_order_id'],
                        price=str(new_tp_price)
                    )
                )
                bracket['tp_price'] = str(new_tp_price)
                bracket['profit_target'] = new_profit_target

            # Amend SL order if new stop loss provided
            if new_stop_loss and bracket['sl_order_id']:
                if side == 'buy':
                    new_sl_price = entry_price * Decimal(1 - new_stop_loss)
                else:
                    new_sl_price = entry_price * Decimal(1 + new_stop_loss)

                tasks.append(
                    self._amend_order(
                        bracket['sl_order_id'],
                        price=str(new_sl_price)
                    )
                )
                bracket['sl_price'] = str(new_sl_price)
                bracket['stop_loss'] = new_stop_loss

            if tasks:
                results = await asyncio.gather(*tasks)

                logger.info(f"[BRACKET_ORDERS] Amended bracket {bracket_id}")
                return {
                    'success': True,
                    'bracket_id': bracket_id,
                    'amendments': results
                }

            return {'success': True, 'message': 'No amendments needed'}

        except Exception as e:
            logger.error(f"[BRACKET_ORDERS] Error amending bracket order: {e}")
            return {'error': str(e)}

    async def _place_market_order(self, symbol: str, side: str, quantity: str) -> dict:
        """Place market order through exchange"""
        try:
            if hasattr(self.exchange, 'create_market_order'):
                return await self.exchange.create_market_order(symbol, side, quantity)
            else:
                # Fallback to REST API
                return await self.exchange.place_order({
                    'pair': symbol.replace('/', ''),
                    'type': side,
                    'ordertype': 'market',
                    'volume': quantity
                })
        except Exception as e:
            logger.error(f"[BRACKET_ORDERS] Market order error: {e}")
            return {'error': str(e)}

    async def _place_limit_order(self, symbol: str, side: str, quantity: str, price: str) -> dict:
        """Place limit order through exchange"""
        try:
            if hasattr(self.exchange, 'create_limit_order'):
                return await self.exchange.create_limit_order(symbol, side, quantity, price)
            else:
                # Fallback to REST API
                return await self.exchange.place_order({
                    'pair': symbol.replace('/', ''),
                    'type': side,
                    'ordertype': 'limit',
                    'price': price,
                    'volume': quantity
                })
        except Exception as e:
            logger.error(f"[BRACKET_ORDERS] Limit order error: {e}")
            return {'error': str(e)}

    async def _place_take_profit_order(self, symbol: str, side: str, quantity: str, price: str) -> dict:
        """Place take profit order"""
        try:
            if hasattr(self.exchange, 'create_take_profit_order'):
                return await self.exchange.create_take_profit_order(symbol, side, quantity, price)
            else:
                # Use limit order as TP
                return await self._place_limit_order(symbol, side, quantity, price)
        except Exception as e:
            logger.error(f"[BRACKET_ORDERS] TP order error: {e}")
            return {'error': str(e)}

    async def _place_stop_loss_order(self, symbol: str, side: str, quantity: str, price: str) -> dict:
        """Place stop loss order"""
        try:
            if hasattr(self.exchange, 'create_stop_loss_order'):
                return await self.exchange.create_stop_loss_order(symbol, side, quantity, price)
            else:
                # Fallback to stop-loss order through REST
                return await self.exchange.place_order({
                    'pair': symbol.replace('/', ''),
                    'type': side,
                    'ordertype': 'stop-loss',
                    'price': price,
                    'volume': quantity
                })
        except Exception as e:
            logger.error(f"[BRACKET_ORDERS] SL order error: {e}")
            return {'error': str(e)}

    async def _amend_order(self, order_id: str, **kwargs) -> dict:
        """Amend an existing order using AmendOrder API"""
        try:
            if hasattr(self.exchange, 'amend_order'):
                # Use native AmendOrder method
                return await self.exchange.amend_order(order_id, **kwargs)
            elif hasattr(self.exchange, 'edit_order'):
                # Fallback to EditOrder (loses queue priority)
                logger.warning("[BRACKET_ORDERS] Using EditOrder instead of AmendOrder")
                return await self.exchange.edit_order(order_id, **kwargs)
            else:
                # No amendment support
                return {'error': 'Order amendment not supported'}
        except Exception as e:
            logger.error(f"[BRACKET_ORDERS] Amend order error: {e}")
            return {'error': str(e)}

    def get_active_brackets(self) -> dict:
        """Get all active bracket orders"""
        return {
            bid: bracket
            for bid, bracket in self.active_brackets.items()
            if bracket['status'] == 'active'
        }

    def get_statistics(self) -> dict:
        """Get bracket order statistics"""
        active_count = sum(1 for b in self.active_brackets.values() if b['status'] == 'active')

        return {
            'total_brackets': self.total_brackets,
            'active_brackets': active_count,
            'successful_brackets': self.successful_brackets,
            'stopped_out': self.stopped_out,
            'success_rate': (self.successful_brackets / self.total_brackets * 100) if self.total_brackets > 0 else 0,
            'active_details': self.get_active_brackets()
        }
