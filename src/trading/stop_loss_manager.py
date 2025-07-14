"""
Stop Loss Manager - Kraken Order Management
==========================================

Manages stop loss orders on Kraken exchange:
- Places stop-loss orders
- Tracks active stop losses
- Updates trailing stops
- Handles stop loss execution
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class StopLossType(Enum):
    """Types of stop loss orders"""
    FIXED = "fixed"
    TRAILING = "trailing"
    TRAILING_PERCENT = "trailing_percent"


@dataclass
class StopLossOrder:
    """Stop loss order tracking"""
    order_id: str
    symbol: str
    position_size: float
    stop_price: float
    stop_type: StopLossType
    trailing_distance: Optional[float] = None
    placed_at: float = 0.0
    last_update: float = 0.0
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    is_active: bool = True


class StopLossManager:
    """
    Manages stop loss orders on Kraken
    """
    
    def __init__(self, exchange, risk_manager=None):
        """Initialize stop loss manager"""
        self.exchange = exchange
        self.risk_manager = risk_manager
        
        # Active stop loss orders
        self.active_stops: Dict[str, StopLossOrder] = {}
        
        # Kraken order tracking
        self.kraken_orders: Dict[str, str] = {}  # symbol -> kraken_order_id
        
        # Configuration
        self.config = {
            'use_stop_loss_orders': True,
            'default_stop_pct': 0.02,  # 2% default
            'trailing_activation_pct': 0.005,  # Activate trailing at 0.5% profit
            'trailing_distance_pct': 0.003,  # Trail by 0.3%
            'update_frequency': 30,  # Check every 30 seconds
            'min_stop_distance': 0.001,  # Minimum 0.1% from current price
        }
        
        # Performance metrics
        self.metrics = {
            'stops_placed': 0,
            'stops_triggered': 0,
            'stops_updated': 0,
            'stops_cancelled': 0,
            'errors': 0
        }
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Start monitoring task
        self._monitoring_task = None
        
        logger.info("[STOP_LOSS] Stop loss manager initialized")
    
    async def initialize(self):
        """Initialize stop loss manager"""
        try:
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitor_stop_losses())
            logger.info("[STOP_LOSS] Monitoring task started")
            
        except Exception as e:
            logger.error(f"[STOP_LOSS] Initialization error: {e}")
    
    async def place_stop_loss(self, symbol: str, position_size: float, entry_price: float, 
                            stop_price: Optional[float] = None, stop_type: StopLossType = StopLossType.FIXED) -> Optional[str]:
        """
        Place a stop loss order on Kraken
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            position_size: Size of position to protect
            entry_price: Entry price of position
            stop_price: Stop trigger price (calculated if not provided)
            stop_type: Type of stop loss
            
        Returns:
            Order ID if successful, None otherwise
        """
        async with self._lock:
            try:
                # Calculate stop price if not provided
                if not stop_price:
                    if self.risk_manager:
                        stop_price = await self.risk_manager.get_stop_loss_price(symbol, entry_price, 'buy')
                    else:
                        stop_price = entry_price * (1 - self.config['default_stop_pct'])
                
                # Validate stop price
                if stop_price >= entry_price * (1 - self.config['min_stop_distance']):
                    logger.warning(f"[STOP_LOSS] Stop price too close to entry price for {symbol}")
                    return None
                
                # Format order for Kraken
                order_params = self._format_kraken_stop_order(
                    symbol=symbol,
                    amount=position_size,
                    stop_price=stop_price,
                    stop_type=stop_type
                )
                
                # Place order on Kraken
                logger.info(f"[STOP_LOSS] Placing stop loss for {symbol} at ${stop_price:.4f}")
                
                order_result = await self._place_kraken_order(order_params)
                
                if order_result and 'id' in order_result:
                    order_id = order_result['id']
                    
                    # Track stop loss
                    stop_order = StopLossOrder(
                        order_id=order_id,
                        symbol=symbol,
                        position_size=position_size,
                        stop_price=stop_price,
                        stop_type=stop_type,
                        placed_at=time.time(),
                        last_update=time.time(),
                        entry_price=entry_price,
                        current_price=entry_price,
                        is_active=True
                    )
                    
                    self.active_stops[symbol] = stop_order
                    self.kraken_orders[symbol] = order_id
                    self.metrics['stops_placed'] += 1
                    
                    logger.info(f"[STOP_LOSS] Stop loss placed for {symbol}: {order_id}")
                    return order_id
                else:
                    logger.error(f"[STOP_LOSS] Failed to place stop loss for {symbol}")
                    self.metrics['errors'] += 1
                    return None
                    
            except Exception as e:
                logger.error(f"[STOP_LOSS] Error placing stop loss for {symbol}: {e}")
                self.metrics['errors'] += 1
                return None
    
    async def update_stop_loss(self, symbol: str, new_stop_price: float) -> bool:
        """Update existing stop loss order"""
        async with self._lock:
            try:
                if symbol not in self.active_stops:
                    logger.warning(f"[STOP_LOSS] No active stop loss for {symbol}")
                    return False
                
                stop_order = self.active_stops[symbol]
                
                # Only update if new stop is higher (for long positions)
                if new_stop_price <= stop_order.stop_price:
                    return False
                
                # Cancel existing order
                if await self._cancel_kraken_order(stop_order.order_id):
                    # Place new order
                    new_order_params = self._format_kraken_stop_order(
                        symbol=symbol,
                        amount=stop_order.position_size,
                        stop_price=new_stop_price,
                        stop_type=stop_order.stop_type
                    )
                    
                    order_result = await self._place_kraken_order(new_order_params)
                    
                    if order_result and 'id' in order_result:
                        # Update tracking
                        stop_order.order_id = order_result['id']
                        stop_order.stop_price = new_stop_price
                        stop_order.last_update = time.time()
                        self.kraken_orders[symbol] = order_result['id']
                        self.metrics['stops_updated'] += 1
                        
                        logger.info(f"[STOP_LOSS] Updated stop loss for {symbol} to ${new_stop_price:.4f}")
                        return True
                
                return False
                
            except Exception as e:
                logger.error(f"[STOP_LOSS] Error updating stop loss for {symbol}: {e}")
                return False
    
    async def cancel_stop_loss(self, symbol: str) -> bool:
        """Cancel stop loss order"""
        async with self._lock:
            try:
                if symbol not in self.active_stops:
                    return True
                
                stop_order = self.active_stops[symbol]
                
                if await self._cancel_kraken_order(stop_order.order_id):
                    del self.active_stops[symbol]
                    del self.kraken_orders[symbol]
                    self.metrics['stops_cancelled'] += 1
                    
                    logger.info(f"[STOP_LOSS] Cancelled stop loss for {symbol}")
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"[STOP_LOSS] Error cancelling stop loss for {symbol}: {e}")
                return False
    
    async def check_trailing_stops(self):
        """Update trailing stops based on current prices"""
        async with self._lock:
            for symbol, stop_order in list(self.active_stops.items()):
                if stop_order.stop_type != StopLossType.TRAILING:
                    continue
                
                try:
                    # Get current price
                    current_price = await self._get_current_price(symbol)
                    if not current_price:
                        continue
                    
                    stop_order.current_price = current_price
                    
                    # Check if we should trail the stop
                    if stop_order.entry_price:
                        profit_pct = (current_price - stop_order.entry_price) / stop_order.entry_price
                        
                        # Only trail if profit exceeds activation threshold
                        if profit_pct >= self.config['trailing_activation_pct']:
                            # Calculate new stop price
                            trailing_distance = current_price * self.config['trailing_distance_pct']
                            new_stop_price = current_price - trailing_distance
                            
                            # Ensure stop only moves up
                            if new_stop_price > stop_order.stop_price:
                                await self.update_stop_loss(symbol, new_stop_price)
                    
                except Exception as e:
                    logger.error(f"[STOP_LOSS] Error checking trailing stop for {symbol}: {e}")
    
    async def get_active_stops(self) -> Dict[str, Dict[str, Any]]:
        """Get all active stop loss orders"""
        async with self._lock:
            return {
                symbol: {
                    'order_id': stop.order_id,
                    'stop_price': stop.stop_price,
                    'position_size': stop.position_size,
                    'stop_type': stop.stop_type.value,
                    'entry_price': stop.entry_price,
                    'current_price': stop.current_price,
                    'placed_at': stop.placed_at,
                    'last_update': stop.last_update
                }
                for symbol, stop in self.active_stops.items()
                if stop.is_active
            }
    
    # Private helper methods
    
    async def _monitor_stop_losses(self):
        """Background task to monitor stop losses"""
        while True:
            try:
                # Check for triggered stops
                await self._check_triggered_stops()
                
                # Update trailing stops
                await self.check_trailing_stops()
                
                await asyncio.sleep(self.config['update_frequency'])
                
            except Exception as e:
                logger.error(f"[STOP_LOSS] Monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _check_triggered_stops(self):
        """Check if any stops have been triggered"""
        for symbol, stop_order in list(self.active_stops.items()):
            try:
                # Check order status on Kraken
                order_status = await self._get_kraken_order_status(stop_order.order_id)
                
                if order_status and order_status.get('status') == 'closed':
                    # Stop was triggered
                    logger.info(f"[STOP_LOSS] Stop loss triggered for {symbol}")
                    
                    self.metrics['stops_triggered'] += 1
                    stop_order.is_active = False
                    
                    # Notify risk manager if available
                    if self.risk_manager:
                        exit_price = float(order_status.get('price', stop_order.stop_price))
                        await self.risk_manager.close_position(symbol, exit_price, "stop_loss")
                    
                    # Remove from active stops
                    del self.active_stops[symbol]
                    del self.kraken_orders[symbol]
                    
            except Exception as e:
                logger.error(f"[STOP_LOSS] Error checking stop status for {symbol}: {e}")
    
    def _format_kraken_stop_order(self, symbol: str, amount: float, stop_price: float, 
                                 stop_type: StopLossType) -> Dict[str, Any]:
        """Format stop loss order for Kraken API"""
        order_params = {
            'pair': symbol.replace('/', ''),  # Kraken format: BTCUSDT
            'type': 'sell',
            'ordertype': 'stop-loss',
            'price': stop_price,
            'volume': amount,
            'stopprice': stop_price,
            'validate': False  # Actually place the order
        }
        
        # Add trailing stop parameters if needed
        if stop_type == StopLossType.TRAILING_PERCENT:
            order_params['ordertype'] = 'trailing-stop'
            order_params['trailingpercent'] = self.config['trailing_distance_pct'] * 100
        
        return order_params
    
    async def _place_kraken_order(self, order_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Place order on Kraken"""
        try:
            if hasattr(self.exchange, 'create_order'):
                # Using ccxt-style interface
                result = await self.exchange.create_order(
                    symbol=order_params['pair'],
                    type=order_params['ordertype'],
                    side=order_params['type'],
                    amount=order_params['volume'],
                    price=order_params['price'],
                    params={'stopPrice': order_params['stopprice']}
                )
                return result
            else:
                # Direct Kraken API
                result = await self.exchange._private_request('AddOrder', order_params)
                if result and 'result' in result:
                    return {'id': result['result']['txid'][0]}
            
            return None
            
        except Exception as e:
            logger.error(f"[STOP_LOSS] Kraken order error: {e}")
            return None
    
    async def _cancel_kraken_order(self, order_id: str) -> bool:
        """Cancel order on Kraken"""
        try:
            if hasattr(self.exchange, 'cancel_order'):
                await self.exchange.cancel_order(order_id)
                return True
            else:
                result = await self.exchange._private_request('CancelOrder', {'txid': order_id})
                return result and 'error' not in result
                
        except Exception as e:
            logger.error(f"[STOP_LOSS] Error cancelling order {order_id}: {e}")
            return False
    
    async def _get_kraken_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status from Kraken"""
        try:
            if hasattr(self.exchange, 'fetch_order'):
                return await self.exchange.fetch_order(order_id)
            else:
                result = await self.exchange._private_request('QueryOrders', {'txid': order_id})
                if result and 'result' in result and order_id in result['result']:
                    return result['result'][order_id]
            
            return None
            
        except Exception as e:
            logger.error(f"[STOP_LOSS] Error getting order status {order_id}: {e}")
            return None
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            if hasattr(self.exchange, 'fetch_ticker'):
                ticker = await self.exchange.fetch_ticker(symbol)
                return ticker.get('last')
            else:
                # Use WebSocket or other price source
                return None
                
        except Exception as e:
            logger.error(f"[STOP_LOSS] Error getting price for {symbol}: {e}")
            return None