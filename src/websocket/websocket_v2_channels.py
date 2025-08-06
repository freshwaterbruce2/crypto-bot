"""
WebSocket V2 Channel Processors
=============================

Specialized processors for different WebSocket V2 channels including:
- Balance updates (real-time account balance streaming)
- Market data (ticker, orderbook, trades, OHLC)
- Order execution notifications
- Account status updates

Features:
- Real-time data parsing and validation
- Type-safe data models
- Integration with existing balance management
- Performance optimized processing
- Comprehensive error handling
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.decimal_precision_fix import safe_decimal, safe_float
from .data_models import (
    BalanceUpdate,
    OHLCUpdate,
    OrderBookLevel,
    OrderBookUpdate,
    TickerUpdate,
    TradeUpdate,
)

logger = logging.getLogger(__name__)


class WebSocketV2ChannelProcessor:
    """
    Channel processor for WebSocket V2 messages.
    
    Handles parsing and processing of different channel types with
    intelligent routing and data validation.
    """

    def __init__(self, manager):
        """
        Initialize channel processor.
        
        Args:
            manager: WebSocket V2 manager instance
        """
        self.manager = manager

        # Channel handlers mapping
        self._channel_handlers = {
            'balances': self._process_balance_channel,
            'ticker': self._process_ticker_channel,
            'book': self._process_orderbook_channel,
            'trade': self._process_trade_channel,
            'ohlc': self._process_ohlc_channel,
            'executions': self._process_execution_channel,
            'status': self._process_status_channel
        }

        # Data storage for latest values
        self._latest_balances: Dict[str, BalanceUpdate] = {}
        self._latest_tickers: Dict[str, TickerUpdate] = {}
        self._latest_orderbooks: Dict[str, OrderBookUpdate] = {}
        self._recent_trades: Dict[str, List[TradeUpdate]] = {}
        self._recent_ohlc: Dict[str, List[OHLCUpdate]] = {}

        # Performance tracking
        self._processing_stats = {
            'balance_updates': 0,
            'ticker_updates': 0,
            'orderbook_updates': 0,
            'trade_updates': 0,
            'ohlc_updates': 0,
            'execution_updates': 0,
            'processing_errors': 0,
            'last_balance_update': 0.0,
            'last_market_update': 0.0
        }

        logger.info("[WS_V2_CHANNELS] Channel processor initialized")

    async def process_message(self, message: Dict[str, Any]) -> None:
        """
        Process incoming WebSocket V2 message.
        
        Args:
            message: Raw WebSocket message
        """
        try:
            channel = message.get('channel')
            if not channel:
                logger.warning(f"[WS_V2_CHANNELS] Message missing channel: {message}")
                return

            # Get handler for channel
            handler = self._channel_handlers.get(channel)
            if not handler:
                logger.debug(f"[WS_V2_CHANNELS] No handler for channel: {channel}")
                return

            # Process message with appropriate handler
            await handler(message)

        except Exception as e:
            logger.error(f"[WS_V2_CHANNELS] Error processing message: {e}")
            logger.debug(f"[WS_V2_CHANNELS] Failed message: {message}")
            self._processing_stats['processing_errors'] += 1

    async def _process_balance_channel(self, message: Dict[str, Any]) -> None:
        """
        Process balance channel updates.
        
        Handles real-time balance updates from Kraken WebSocket V2.
        Format: {"channel": "balances", "data": [{"asset": "BTC", "balance": "1.0", "hold_trade": "0.0"}]}
        """
        try:
            data_array = message.get('data', [])
            if not data_array:
                logger.debug("[WS_V2_CHANNELS] Empty balance update received")
                return

            balance_updates = []
            total_assets = 0
            significant_updates = 0

            for balance_item in data_array:
                try:
                    # Parse balance data
                    asset = balance_item.get('asset')
                    balance_str = balance_item.get('balance', '0')
                    hold_trade_str = balance_item.get('hold_trade', '0')

                    if not asset:
                        continue

                    # Convert to Decimal for precision
                    balance_decimal = safe_decimal(balance_str)
                    hold_trade_decimal = safe_decimal(hold_trade_str)

                    # Create balance update object
                    balance_update = BalanceUpdate(
                        asset=asset,
                        balance=balance_decimal,
                        hold_trade=hold_trade_decimal,
                        timestamp=time.time()
                    )

                    # Store latest balance
                    self._latest_balances[asset] = balance_update
                    balance_updates.append(balance_update)
                    total_assets += 1

                    # Track significant updates (free balance > threshold)
                    if balance_update.free_balance > safe_decimal('0.0001'):
                        significant_updates += 1

                        # Log important assets
                        if asset in ['USDT', 'BTC', 'ETH', 'MANA', 'SHIB']:
                            logger.info(f"[WS_V2_CHANNELS] {asset} balance: {balance_update.free_balance}")

                except Exception as e:
                    logger.warning(f"[WS_V2_CHANNELS] Error parsing balance item {balance_item}: {e}")
                    continue

            # Update statistics
            self._processing_stats['balance_updates'] += 1
            self._processing_stats['last_balance_update'] = time.time()

            logger.info(f"[WS_V2_CHANNELS] Processed {total_assets} balance updates "
                       f"({significant_updates} significant)")

            # Integrate with existing balance manager
            await self._integrate_balance_updates(balance_updates)

            # Notify handlers
            await self.manager._notify_handlers('balance', balance_updates)

        except Exception as e:
            logger.error(f"[WS_V2_CHANNELS] Error processing balance channel: {e}")
            self._processing_stats['processing_errors'] += 1

    async def _integrate_balance_updates(self, balance_updates: List[BalanceUpdate]) -> None:
        """
        Integrate balance updates with existing balance management system.
        
        Args:
            balance_updates: List of balance updates to integrate
        """
        try:
            # Get manager reference for balance integration
            manager_ref = None

            # Try multiple methods to get balance manager reference
            if hasattr(self.manager, 'exchange_client'):
                exchange_client = self.manager.exchange_client

                if hasattr(exchange_client, 'bot_instance'):
                    manager_ref = exchange_client.bot_instance
                elif hasattr(exchange_client, 'balance_manager'):
                    manager_ref = exchange_client

            if not manager_ref:
                logger.debug("[WS_V2_CHANNELS] No balance manager reference found")
                return

            balance_manager = None
            if hasattr(manager_ref, 'balance_manager'):
                balance_manager = manager_ref.balance_manager
            elif hasattr(manager_ref, 'balances'):
                balance_manager = manager_ref

            if not balance_manager:
                logger.debug("[WS_V2_CHANNELS] Balance manager not accessible")
                return

            # Inject balance updates
            injected_count = 0
            for balance_update in balance_updates:
                if balance_update.total_balance > safe_decimal('0'):
                    # Convert to format expected by balance manager
                    balance_dict = {
                        'free': safe_float(balance_update.free_balance),
                        'used': safe_float(balance_update.hold_trade),
                        'total': safe_float(balance_update.total_balance),
                        'timestamp': balance_update.timestamp
                    }

                    # Direct injection to balance manager
                    if hasattr(balance_manager, 'balances'):
                        balance_manager.balances[balance_update.asset] = balance_dict
                        injected_count += 1

                    # Also update WebSocket cache if available
                    if hasattr(balance_manager, 'websocket_balances'):
                        balance_manager.websocket_balances[balance_update.asset] = balance_dict

            # Reset circuit breaker if balance manager has one
            if (hasattr(balance_manager, 'circuit_breaker_active') and
                balance_manager.circuit_breaker_active and injected_count > 0):

                logger.info("[WS_V2_CHANNELS] Fresh balance data received - resetting circuit breaker")
                balance_manager.circuit_breaker_active = False
                balance_manager.consecutive_failures = 0
                if hasattr(balance_manager, 'backoff_multiplier'):
                    balance_manager.backoff_multiplier = 1.0

            # Update last update timestamp
            if hasattr(balance_manager, 'last_update'):
                balance_manager.last_update = time.time()

            if injected_count > 0:
                logger.info(f"[WS_V2_CHANNELS] Injected {injected_count} balance updates to balance manager")

        except Exception as e:
            logger.error(f"[WS_V2_CHANNELS] Error integrating balance updates: {e}")

    async def _process_ticker_channel(self, message: Dict[str, Any]) -> None:
        """
        Process ticker channel updates.
        
        Handles real-time ticker data from WebSocket V2.
        """
        try:
            data_array = message.get('data', [])
            if not data_array:
                return

            ticker_updates = []

            for ticker_data in data_array:
                try:
                    symbol = ticker_data.get('symbol')
                    if not symbol:
                        continue

                    # Create ticker update object
                    ticker_update = TickerUpdate(
                        symbol=symbol,
                        bid=safe_decimal(ticker_data.get('bid', 0)),
                        ask=safe_decimal(ticker_data.get('ask', 0)),
                        last=safe_decimal(ticker_data.get('last', 0)),
                        volume=safe_decimal(ticker_data.get('volume', 0)),
                        high=safe_decimal(ticker_data.get('high', 0)),
                        low=safe_decimal(ticker_data.get('low', 0)),
                        vwap=safe_decimal(ticker_data.get('vwap', 0)),
                        timestamp=time.time()
                    )

                    # Store latest ticker
                    self._latest_tickers[symbol] = ticker_update
                    ticker_updates.append(ticker_update)

                except Exception as e:
                    logger.warning(f"[WS_V2_CHANNELS] Error parsing ticker data {ticker_data}: {e}")
                    continue

            # Update statistics
            self._processing_stats['ticker_updates'] += len(ticker_updates)
            self._processing_stats['last_market_update'] = time.time()

            if ticker_updates:
                logger.debug(f"[WS_V2_CHANNELS] Processed {len(ticker_updates)} ticker updates")

                # Notify handlers
                await self.manager._notify_handlers('ticker', ticker_updates)

        except Exception as e:
            logger.error(f"[WS_V2_CHANNELS] Error processing ticker channel: {e}")
            self._processing_stats['processing_errors'] += 1

    async def _process_orderbook_channel(self, message: Dict[str, Any]) -> None:
        """
        Process orderbook channel updates.
        
        Handles real-time orderbook data from WebSocket V2.
        """
        try:
            data_array = message.get('data', [])
            if not data_array:
                return

            orderbook_updates = []

            for orderbook_data in data_array:
                try:
                    symbol = orderbook_data.get('symbol')
                    if not symbol:
                        continue

                    # Parse bids and asks
                    bids = []
                    asks = []

                    # Process bids
                    for bid_data in orderbook_data.get('bids', []):
                        if isinstance(bid_data, dict):
                            price = safe_decimal(bid_data.get('price', 0))
                            qty = safe_decimal(bid_data.get('qty', 0))
                        elif isinstance(bid_data, list) and len(bid_data) >= 2:
                            price = safe_decimal(bid_data[0])
                            qty = safe_decimal(bid_data[1])
                        else:
                            continue

                        if price > 0 and qty > 0:
                            bids.append(OrderBookLevel(price=price, qty=qty))

                    # Process asks
                    for ask_data in orderbook_data.get('asks', []):
                        if isinstance(ask_data, dict):
                            price = safe_decimal(ask_data.get('price', 0))
                            qty = safe_decimal(ask_data.get('qty', 0))
                        elif isinstance(ask_data, list) and len(ask_data) >= 2:
                            price = safe_decimal(ask_data[0])
                            qty = safe_decimal(ask_data[1])
                        else:
                            continue

                        if price > 0 and qty > 0:
                            asks.append(OrderBookLevel(price=price, qty=qty))

                    # Sort orderbook levels
                    bids.sort(key=lambda x: x.price, reverse=True)  # Highest bid first
                    asks.sort(key=lambda x: x.price)  # Lowest ask first

                    # Create orderbook update
                    orderbook_update = OrderBookUpdate(
                        symbol=symbol,
                        bids=bids,
                        asks=asks,
                        timestamp=time.time()
                    )

                    # Store latest orderbook
                    self._latest_orderbooks[symbol] = orderbook_update
                    orderbook_updates.append(orderbook_update)

                except Exception as e:
                    logger.warning(f"[WS_V2_CHANNELS] Error parsing orderbook data {orderbook_data}: {e}")
                    continue

            # Update statistics
            self._processing_stats['orderbook_updates'] += len(orderbook_updates)
            self._processing_stats['last_market_update'] = time.time()

            if orderbook_updates:
                logger.debug(f"[WS_V2_CHANNELS] Processed {len(orderbook_updates)} orderbook updates")

                # Notify handlers
                await self.manager._notify_handlers('orderbook', orderbook_updates)

        except Exception as e:
            logger.error(f"[WS_V2_CHANNELS] Error processing orderbook channel: {e}")
            self._processing_stats['processing_errors'] += 1

    async def _process_trade_channel(self, message: Dict[str, Any]) -> None:
        """
        Process trade channel updates.
        
        Handles real-time trade data from WebSocket V2.
        """
        try:
            data_array = message.get('data', [])
            if not data_array:
                return

            trade_updates = []

            for trade_data in data_array:
                try:
                    symbol = trade_data.get('symbol')
                    if not symbol:
                        continue

                    # Create trade update
                    trade_update = TradeUpdate(
                        symbol=symbol,
                        price=safe_decimal(trade_data.get('price', 0)),
                        qty=safe_decimal(trade_data.get('qty', 0)),
                        side=trade_data.get('side', 'unknown'),
                        trade_id=trade_data.get('trade_id'),
                        timestamp=time.time()
                    )

                    # Store recent trades (keep last 100)
                    if symbol not in self._recent_trades:
                        self._recent_trades[symbol] = []

                    self._recent_trades[symbol].append(trade_update)
                    if len(self._recent_trades[symbol]) > 100:
                        self._recent_trades[symbol].pop(0)

                    trade_updates.append(trade_update)

                except Exception as e:
                    logger.warning(f"[WS_V2_CHANNELS] Error parsing trade data {trade_data}: {e}")
                    continue

            # Update statistics
            self._processing_stats['trade_updates'] += len(trade_updates)
            self._processing_stats['last_market_update'] = time.time()

            if trade_updates:
                logger.debug(f"[WS_V2_CHANNELS] Processed {len(trade_updates)} trade updates")

                # Notify handlers
                await self.manager._notify_handlers('trade', trade_updates)

        except Exception as e:
            logger.error(f"[WS_V2_CHANNELS] Error processing trade channel: {e}")
            self._processing_stats['processing_errors'] += 1

    async def _process_ohlc_channel(self, message: Dict[str, Any]) -> None:
        """
        Process OHLC channel updates.
        
        Handles real-time OHLC (candlestick) data from WebSocket V2.
        """
        try:
            data_array = message.get('data', [])
            if not data_array:
                return

            ohlc_updates = []

            for ohlc_data in data_array:
                try:
                    symbol = ohlc_data.get('symbol')
                    if not symbol:
                        continue

                    # Parse timestamp
                    timestamp_str = ohlc_data.get('timestamp', '')
                    if timestamp_str and isinstance(timestamp_str, str):
                        try:
                            # Convert ISO timestamp to Unix timestamp
                            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            timestamp = dt.timestamp()
                        except:
                            timestamp = time.time()
                    else:
                        timestamp = safe_float(safe_decimal(ohlc_data.get('timestamp', time.time())))

                    # Create OHLC update
                    ohlc_update = OHLCUpdate(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=safe_decimal(ohlc_data.get('open', 0)),
                        high=safe_decimal(ohlc_data.get('high', 0)),
                        low=safe_decimal(ohlc_data.get('low', 0)),
                        close=safe_decimal(ohlc_data.get('close', 0)),
                        volume=safe_decimal(ohlc_data.get('volume', 0)),
                        interval=ohlc_data.get('interval', 1)
                    )

                    # Store recent OHLC data (keep last 100 candles)
                    if symbol not in self._recent_ohlc:
                        self._recent_ohlc[symbol] = []

                    self._recent_ohlc[symbol].append(ohlc_update)
                    if len(self._recent_ohlc[symbol]) > 100:
                        self._recent_ohlc[symbol].pop(0)

                    ohlc_updates.append(ohlc_update)

                except Exception as e:
                    logger.warning(f"[WS_V2_CHANNELS] Error parsing OHLC data {ohlc_data}: {e}")
                    continue

            # Update statistics
            self._processing_stats['ohlc_updates'] += len(ohlc_updates)
            self._processing_stats['last_market_update'] = time.time()

            if ohlc_updates:
                logger.debug(f"[WS_V2_CHANNELS] Processed {len(ohlc_updates)} OHLC updates")

                # Notify handlers
                await self.manager._notify_handlers('ohlc', ohlc_updates)

        except Exception as e:
            logger.error(f"[WS_V2_CHANNELS] Error processing OHLC channel: {e}")
            self._processing_stats['processing_errors'] += 1

    async def _process_execution_channel(self, message: Dict[str, Any]) -> None:
        """
        Process execution channel updates.
        
        Handles real-time order execution notifications from WebSocket V2.
        """
        try:
            data_array = message.get('data', [])
            if not data_array:
                return

            execution_updates = []

            for execution_data in data_array:
                try:
                    # Extract execution information
                    execution_info = {
                        'order_id': execution_data.get('order_id'),
                        'trade_id': execution_data.get('trade_id'),
                        'symbol': execution_data.get('symbol'),
                        'side': execution_data.get('side'),
                        'order_type': execution_data.get('order_type'),
                        'limit_price': safe_decimal(execution_data.get('limit_price', 0)),
                        'exec_type': execution_data.get('exec_type'),
                        'cost': safe_decimal(execution_data.get('cost', 0)),
                        'fee': safe_decimal(execution_data.get('fee', 0)),
                        'margin': execution_data.get('margin', False),
                        'timestamp': time.time()
                    }

                    execution_updates.append(execution_info)

                    # Log important executions
                    if execution_info.get('exec_type') in ['trade', 'partial']:
                        symbol = execution_info.get('symbol', 'UNKNOWN')
                        cost = execution_info.get('cost', 0)
                        logger.info(f"[WS_V2_CHANNELS] Order execution: {symbol} cost=${cost}")

                except Exception as e:
                    logger.warning(f"[WS_V2_CHANNELS] Error parsing execution data {execution_data}: {e}")
                    continue

            # Update statistics
            self._processing_stats['execution_updates'] += len(execution_updates)

            if execution_updates:
                logger.info(f"[WS_V2_CHANNELS] Processed {len(execution_updates)} execution updates")

                # Notify handlers
                await self.manager._notify_handlers('execution', execution_updates)

        except Exception as e:
            logger.error(f"[WS_V2_CHANNELS] Error processing execution channel: {e}")
            self._processing_stats['processing_errors'] += 1

    async def _process_status_channel(self, message: Dict[str, Any]) -> None:
        """
        Process status channel updates.
        
        Handles connection status and authentication confirmations.
        """
        try:
            # Extract status information
            status = message.get('status', 'unknown')
            data = message.get('data', {})

            logger.info(f"[WS_V2_CHANNELS] Status update: {status}")

            # Handle authentication status
            if status == 'online' and data.get('api_key'):
                logger.info("[WS_V2_CHANNELS] Authentication confirmed")

            # Notify handlers
            await self.manager._notify_handlers('status', {
                'status': status,
                'data': data,
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"[WS_V2_CHANNELS] Error processing status channel: {e}")
            self._processing_stats['processing_errors'] += 1

    # Data access methods
    def get_latest_balance(self, asset: str) -> Optional[BalanceUpdate]:
        """Get latest balance for asset"""
        return self._latest_balances.get(asset)

    def get_all_balances(self) -> Dict[str, BalanceUpdate]:
        """Get all latest balances"""
        return dict(self._latest_balances)

    def get_latest_ticker(self, symbol: str) -> Optional[TickerUpdate]:
        """Get latest ticker for symbol"""
        return self._latest_tickers.get(symbol)

    def get_all_tickers(self) -> Dict[str, TickerUpdate]:
        """Get all latest tickers"""
        return dict(self._latest_tickers)

    def get_latest_orderbook(self, symbol: str) -> Optional[OrderBookUpdate]:
        """Get latest orderbook for symbol"""
        return self._latest_orderbooks.get(symbol)

    def get_recent_trades(self, symbol: str, limit: int = 50) -> List[TradeUpdate]:
        """Get recent trades for symbol"""
        trades = self._recent_trades.get(symbol, [])
        return trades[-limit:] if limit > 0 else trades

    def get_recent_ohlc(self, symbol: str, limit: int = 100) -> List[OHLCUpdate]:
        """Get recent OHLC data for symbol"""
        ohlc_data = self._recent_ohlc.get(symbol, [])
        return ohlc_data[-limit:] if limit > 0 else ohlc_data

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get channel processing statistics"""
        return dict(self._processing_stats)

    def reset_stats(self) -> None:
        """Reset processing statistics"""
        for key in self._processing_stats:
            if isinstance(self._processing_stats[key], (int, float)):
                self._processing_stats[key] = 0

    def has_fresh_data(self, data_type: str, max_age: float = 30.0) -> bool:
        """
        Check if we have fresh data of specified type.
        
        Args:
            data_type: Type of data ('balance', 'ticker', 'orderbook', etc.)
            max_age: Maximum age in seconds
            
        Returns:
            True if fresh data is available
        """
        current_time = time.time()

        if data_type == 'balance':
            last_update = self._processing_stats.get('last_balance_update', 0)
        elif data_type in ['ticker', 'orderbook', 'trade', 'ohlc']:
            last_update = self._processing_stats.get('last_market_update', 0)
        else:
            return False

        return (current_time - last_update) <= max_age
