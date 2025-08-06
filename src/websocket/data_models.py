"""
WebSocket V2 Data Models
========================

Data models and validation for Kraken WebSocket V2 messages.
Provides type safety and structure for all WebSocket communications.
"""

import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Union

from ..utils.decimal_precision_fix import safe_decimal, safe_float


class MessageType(Enum):
    """WebSocket message types"""
    HEARTBEAT = "heartbeat"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    TICKER = "ticker"
    BALANCE = "balances"
    ORDERBOOK = "book"
    TRADE = "trade"
    OHLC = "ohlc"
    EXECUTIONS = "executions"
    ORDERS = "openOrders"
    STATUS = "status"
    ERROR = "error"


class ChannelType(Enum):
    """WebSocket channel types"""
    PUBLIC = "public"
    PRIVATE = "private"


@dataclass
class WebSocketMessage:
    """Base WebSocket message structure"""
    channel: str
    type: MessageType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    req_id: Optional[int] = None

    @classmethod
    def from_raw(cls, raw_data: dict[str, Any]) -> 'WebSocketMessage':
        """Create message from raw WebSocket data"""
        channel = raw_data.get('channel', 'unknown')
        message_type = raw_data.get('type', channel)

        # Map channel names to MessageType
        type_mapping = {
            'ticker': MessageType.TICKER,
            'balances': MessageType.BALANCE,
            'book': MessageType.ORDERBOOK,
            'trade': MessageType.TRADE,
            'ohlc': MessageType.OHLC,
            'executions': MessageType.EXECUTIONS,
            'openOrders': MessageType.ORDERS,
            'heartbeat': MessageType.HEARTBEAT,
            'status': MessageType.STATUS
        }

        msg_type = type_mapping.get(message_type, MessageType.STATUS)

        return cls(
            channel=channel,
            type=msg_type,
            data=raw_data.get('data', raw_data),
            timestamp=time.time(),
            req_id=raw_data.get('req_id')
        )


@dataclass
class SubscriptionRequest:
    """WebSocket subscription request"""
    method: str = "subscribe"
    params: dict[str, Any] = field(default_factory=dict)
    req_id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "method": self.method,
            "params": self.params
        }
        if self.req_id is not None:
            result["req_id"] = self.req_id
        return result


@dataclass
class SubscriptionResponse:
    """WebSocket subscription response"""
    method: str
    result: dict[str, Any]
    success: bool
    error: Optional[str] = None
    req_id: Optional[int] = None
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_raw(cls, raw_data: dict[str, Any]) -> 'SubscriptionResponse':
        """Create response from raw WebSocket data"""
        return cls(
            method=raw_data.get('method', 'unknown'),
            result=raw_data.get('result', {}),
            success=raw_data.get('success', False),
            error=raw_data.get('error'),
            req_id=raw_data.get('req_id'),
            timestamp=time.time()
        )


@dataclass
class BalanceUpdate:
    """Balance update message"""
    asset: str
    balance: Decimal
    hold_trade: Decimal = field(default_factory=lambda: Decimal('0'))
    timestamp: float = field(default_factory=time.time)

    @property
    def free_balance(self) -> Decimal:
        """Available balance for trading"""
        return self.balance - self.hold_trade

    @property
    def total_balance(self) -> Decimal:
        """Total balance including locked funds"""
        return self.balance

    @classmethod
    def from_raw(cls, raw_data: dict[str, Any]) -> 'BalanceUpdate':
        """Create balance update from raw data"""
        return cls(
            asset=raw_data.get('asset', ''),
            balance=safe_decimal(raw_data.get('balance', '0')),
            hold_trade=safe_decimal(raw_data.get('hold_trade', '0')),
            timestamp=time.time()
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format compatible with existing code"""
        return {
            'free': safe_float(self.free_balance),
            'used': safe_float(self.hold_trade),
            'total': safe_float(self.total_balance),
            'timestamp': self.timestamp
        }


@dataclass
class TickerUpdate:
    """Ticker update message"""
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: Decimal
    high: Decimal = field(default_factory=lambda: Decimal('0'))
    low: Decimal = field(default_factory=lambda: Decimal('0'))
    vwap: Decimal = field(default_factory=lambda: Decimal('0'))
    open_price: Decimal = field(default_factory=lambda: Decimal('0'))
    timestamp: float = field(default_factory=time.time)

    @property
    def spread(self) -> Decimal:
        """Bid-ask spread"""
        return self.ask - self.bid if self.ask > 0 and self.bid > 0 else Decimal('0')

    @property
    def spread_percentage(self) -> Decimal:
        """Bid-ask spread as percentage"""
        if self.bid > 0 and self.spread > 0:
            return (self.spread / self.bid) * Decimal('100')
        return Decimal('0')

    @property
    def mid_price(self) -> Decimal:
        """Mid price between bid and ask"""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / Decimal('2')
        return Decimal('0')

    @classmethod
    def from_raw(cls, symbol: str, raw_data: dict[str, Any]) -> 'TickerUpdate':
        """Create ticker update from raw data"""
        return cls(
            symbol=symbol,
            bid=safe_decimal(raw_data.get('bid', '0')),
            ask=safe_decimal(raw_data.get('ask', '0')),
            last=safe_decimal(raw_data.get('last', '0')),
            volume=safe_decimal(raw_data.get('volume', '0')),
            high=safe_decimal(raw_data.get('high', '0')),
            low=safe_decimal(raw_data.get('low', '0')),
            vwap=safe_decimal(raw_data.get('vwap', '0')),
            open_price=safe_decimal(raw_data.get('open', '0')),
            timestamp=time.time()
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format compatible with existing code"""
        return {
            'bid': safe_float(self.bid),
            'ask': safe_float(self.ask),
            'last': safe_float(self.last),
            'volume': safe_float(self.volume),
            'high': safe_float(self.high),
            'low': safe_float(self.low),
            'vwap': safe_float(self.vwap),
            'open': safe_float(self.open_price),
            'spread': safe_float(self.spread),
            'spread_pct': safe_float(self.spread_percentage),
            'mid_price': safe_float(self.mid_price),
            'timestamp': self.timestamp
        }


@dataclass
class OrderBookLevel:
    """Single orderbook level (price/volume pair)"""
    price: Decimal
    volume: Decimal
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_raw(cls, raw_data: Union[list, dict]) -> 'OrderBookLevel':
        """Create level from raw data (array or dict format)"""
        if isinstance(raw_data, list) and len(raw_data) >= 2:
            return cls(
                price=safe_decimal(raw_data[0]),
                volume=safe_decimal(raw_data[1]),
                timestamp=time.time()
            )
        elif isinstance(raw_data, dict):
            return cls(
                price=safe_decimal(raw_data.get('price', '0')),
                volume=safe_decimal(raw_data.get('qty', raw_data.get('volume', '0'))),
                timestamp=time.time()
            )
        else:
            return cls(price=Decimal('0'), volume=Decimal('0'))


@dataclass
class OrderBookUpdate:
    """Orderbook update message"""
    symbol: str
    bids: list[OrderBookLevel] = field(default_factory=list)
    asks: list[OrderBookLevel] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    checksum: Optional[str] = None

    @property
    def best_bid(self) -> Optional[OrderBookLevel]:
        """Best bid (highest price)"""
        if self.bids:
            return max(self.bids, key=lambda x: x.price)
        return None

    @property
    def best_ask(self) -> Optional[OrderBookLevel]:
        """Best ask (lowest price)"""
        if self.asks:
            return min(self.asks, key=lambda x: x.price)
        return None

    @property
    def spread(self) -> Decimal:
        """Bid-ask spread"""
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        return Decimal('0')

    @property
    def mid_price(self) -> Decimal:
        """Mid price between best bid and ask"""
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / Decimal('2')
        return Decimal('0')

    @classmethod
    def from_raw(cls, symbol: str, raw_data: dict[str, Any]) -> 'OrderBookUpdate':
        """Create orderbook update from raw data"""
        bids = []
        asks = []

        # Process bids
        raw_bids = raw_data.get('bids', [])
        for bid_data in raw_bids:
            level = OrderBookLevel.from_raw(bid_data)
            if level.price > 0 and level.volume > 0:
                bids.append(level)

        # Process asks
        raw_asks = raw_data.get('asks', [])
        for ask_data in raw_asks:
            level = OrderBookLevel.from_raw(ask_data)
            if level.price > 0 and level.volume > 0:
                asks.append(level)

        # Sort bids (highest first) and asks (lowest first)
        bids.sort(key=lambda x: x.price, reverse=True)
        asks.sort(key=lambda x: x.price)

        return cls(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=time.time(),
            checksum=raw_data.get('checksum')
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format compatible with existing code"""
        return {
            'bids': [{'price': safe_float(b.price), 'volume': safe_float(b.volume)} for b in self.bids],
            'asks': [{'price': safe_float(a.price), 'volume': safe_float(a.volume)} for a in self.asks],
            'spread': safe_float(self.spread),
            'mid_price': safe_float(self.mid_price),
            'timestamp': self.timestamp
        }


@dataclass
class TradeUpdate:
    """Trade update message"""
    symbol: str
    side: str  # 'buy' or 'sell'
    price: Decimal
    volume: Decimal
    timestamp: float = field(default_factory=time.time)
    trade_id: Optional[str] = None

    @classmethod
    def from_raw(cls, symbol: str, raw_data: dict[str, Any]) -> 'TradeUpdate':
        """Create trade update from raw data"""
        return cls(
            symbol=symbol,
            side=raw_data.get('side', 'unknown'),
            price=safe_decimal(raw_data.get('price', '0')),
            volume=safe_decimal(raw_data.get('qty', raw_data.get('volume', '0'))),
            timestamp=time.time(),
            trade_id=raw_data.get('trade_id')
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format compatible with existing code"""
        return {
            'side': self.side,
            'price': safe_float(self.price),
            'volume': safe_float(self.volume),
            'timestamp': self.timestamp,
            'trade_id': self.trade_id
        }


@dataclass
class OHLCUpdate:
    """OHLC (candlestick) update message"""
    symbol: str
    open_price: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    interval: int  # in minutes
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_raw(cls, symbol: str, raw_data: dict[str, Any]) -> 'OHLCUpdate':
        """Create OHLC update from raw data"""
        # Handle timestamp conversion
        timestamp_raw = raw_data.get('timestamp', time.time())
        if isinstance(timestamp_raw, str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp_raw.replace('Z', '+00:00'))
                timestamp = dt.timestamp()
            except:
                timestamp = time.time()
        else:
            timestamp = safe_float(timestamp_raw)

        return cls(
            symbol=symbol,
            open_price=safe_decimal(raw_data.get('open', '0')),
            high=safe_decimal(raw_data.get('high', '0')),
            low=safe_decimal(raw_data.get('low', '0')),
            close=safe_decimal(raw_data.get('close', '0')),
            volume=safe_decimal(raw_data.get('volume', '0')),
            interval=raw_data.get('interval', 1),
            timestamp=timestamp
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format compatible with existing code"""
        return {
            'open': safe_float(self.open_price),
            'high': safe_float(self.high),
            'low': safe_float(self.low),
            'close': safe_float(self.close),
            'volume': safe_float(self.volume),
            'interval': self.interval,
            'timestamp': self.timestamp
        }


@dataclass
class ConnectionStatus:
    """WebSocket connection status"""
    connected: bool = False
    authenticated: bool = False
    subscriptions: list[str] = field(default_factory=list)
    last_heartbeat: float = 0
    connection_time: float = 0
    reconnect_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None

    @property
    def uptime(self) -> float:
        """Connection uptime in seconds"""
        if self.connected and self.connection_time > 0:
            return time.time() - self.connection_time
        return 0

    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        if not self.connected:
            return False

        # Check if heartbeat is recent (within 60 seconds)
        if self.last_heartbeat > 0:
            heartbeat_age = time.time() - self.last_heartbeat
            return heartbeat_age < 60

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for status reporting"""
        return {
            'connected': self.connected,
            'authenticated': self.authenticated,
            'subscriptions': self.subscriptions.copy(),
            'last_heartbeat': self.last_heartbeat,
            'uptime': self.uptime,
            'reconnect_count': self.reconnect_count,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'is_healthy': self.is_healthy
        }
