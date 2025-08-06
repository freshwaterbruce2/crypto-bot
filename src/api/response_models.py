"""
Kraken API Response Models
==========================

Pydantic models for validating and parsing Kraken API responses.
Provides type safety, automatic validation, and easy data access.

Features:
- Complete type definitions for all Kraken API responses
- Automatic JSON parsing and validation
- Custom validators for Kraken-specific data formats
- Error handling and data transformation
- Support for nested objects and collections

Usage:
    from src.api.response_models import BalanceResponse, OrderResponse
    
    # Parse balance response
    balance_data = await client.get_account_balance()
    balance = BalanceResponse(**balance_data)
    
    # Access typed data
    btc_balance = balance.result.get('XBT', '0')
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    EXPIRED = "expired"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop-loss"
    TAKE_PROFIT = "take-profit"
    STOP_LOSS_LIMIT = "stop-loss-limit"
    TAKE_PROFIT_LIMIT = "take-profit-limit"
    SETTLE_POSITION = "settle-position"


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class SystemStatus(str, Enum):
    """System status enumeration."""
    ONLINE = "online"
    MAINTENANCE = "maintenance"
    CANCEL_ONLY = "cancel_only"
    POST_ONLY = "post_only"


class KrakenResponse(BaseModel):
    """
    Base Kraken API response model.
    
    All Kraken responses follow this structure with error and result fields.
    """
    error: List[str] = Field(default_factory=list, description="List of error messages")
    result: Optional[Dict[str, Any]] = Field(None, description="Response result data")

    @validator('error', pre=True)
    def validate_error(cls, v):
        """Ensure error is always a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    @property
    def has_errors(self) -> bool:
        """Check if response has errors."""
        return len(self.error) > 0

    @property
    def is_success(self) -> bool:
        """Check if response is successful."""
        return not self.has_errors

    def get_error_string(self) -> str:
        """Get concatenated error string."""
        return "; ".join(self.error) if self.error else ""


class ServerTimeResponse(KrakenResponse):
    """Server time response model."""
    result: Optional[Dict[str, Union[int, str]]] = None

    @property
    def unixtime(self) -> Optional[int]:
        """Get Unix timestamp."""
        return self.result.get('unixtime') if self.result else None

    @property
    def rfc1123(self) -> Optional[str]:
        """Get RFC1123 formatted time."""
        return self.result.get('rfc1123') if self.result else None


class SystemStatusResponse(KrakenResponse):
    """System status response model."""
    result: Optional[Dict[str, Union[str, int]]] = None

    @property
    def status(self) -> Optional[str]:
        """Get system status."""
        return self.result.get('status') if self.result else None

    @property
    def timestamp(self) -> Optional[str]:
        """Get status timestamp."""
        return self.result.get('timestamp') if self.result else None


class AssetInfo(BaseModel):
    """Asset information model."""
    aclass: Optional[str] = Field(None, description="Asset class")
    altname: Optional[str] = Field(None, description="Alternative name")
    decimals: Optional[int] = Field(None, description="Scaling decimal places for record keeping")
    display_decimals: Optional[int] = Field(None, description="Scaling decimal places for output display")


class AssetInfoResponse(KrakenResponse):
    """Asset info response model."""
    result: Optional[Dict[str, AssetInfo]] = None

    @validator('result', pre=True)
    def parse_assets(cls, v):
        """Parse asset info objects."""
        if not v:
            return v

        parsed = {}
        for asset_name, asset_data in v.items():
            if isinstance(asset_data, dict):
                parsed[asset_name] = AssetInfo(**asset_data)
            else:
                parsed[asset_name] = asset_data
        return parsed


class AssetPairInfo(BaseModel):
    """Asset pair information model."""
    altname: Optional[str] = Field(None, description="Alternative pair name")
    wsname: Optional[str] = Field(None, description="WebSocket pair name")
    aclass_base: Optional[str] = Field(None, description="Asset class of base component")
    base: Optional[str] = Field(None, description="Asset ID of base component")
    aclass_quote: Optional[str] = Field(None, description="Asset class of quote component")
    quote: Optional[str] = Field(None, description="Asset ID of quote component")
    lot: Optional[str] = Field(None, description="Volume lot size")
    pair_decimals: Optional[int] = Field(None, description="Scaling decimal places for pair")
    lot_decimals: Optional[int] = Field(None, description="Scaling decimal places for volume")
    lot_multiplier: Optional[int] = Field(None, description="Amount to multiply lot volume by to get currency volume")
    leverage_buy: Optional[List[int]] = Field(None, description="Array of leverage amounts available when buying")
    leverage_sell: Optional[List[int]] = Field(None, description="Array of leverage amounts available when selling")
    fees: Optional[List[List[Union[int, float]]]] = Field(None, description="Fee schedule array")
    fees_maker: Optional[List[List[Union[int, float]]]] = Field(None, description="Maker fee schedule array")
    fee_volume_currency: Optional[str] = Field(None, description="Volume discount currency")
    margin_call: Optional[int] = Field(None, description="Margin call level")
    margin_stop: Optional[int] = Field(None, description="Stop-out/liquidation margin level")
    ordermin: Optional[str] = Field(None, description="Minimum order volume for pair")


class AssetPairResponse(KrakenResponse):
    """Asset pairs response model."""
    result: Optional[Dict[str, AssetPairInfo]] = None

    @validator('result', pre=True)
    def parse_pairs(cls, v):
        """Parse asset pair info objects."""
        if not v:
            return v

        parsed = {}
        for pair_name, pair_data in v.items():
            if isinstance(pair_data, dict):
                parsed[pair_name] = AssetPairInfo(**pair_data)
            else:
                parsed[pair_name] = pair_data
        return parsed


class TickerInfo(BaseModel):
    """Ticker information model."""
    a: Optional[List[str]] = Field(None, description="Ask array (price, whole lot volume, lot volume)")
    b: Optional[List[str]] = Field(None, description="Bid array (price, whole lot volume, lot volume)")
    c: Optional[List[str]] = Field(None, description="Last trade closed array (price, lot volume)")
    v: Optional[List[str]] = Field(None, description="Volume array (today, last 24 hours)")
    p: Optional[List[str]] = Field(None, description="Volume weighted average price array (today, last 24 hours)")
    t: Optional[List[int]] = Field(None, description="Number of trades array (today, last 24 hours)")
    l: Optional[List[str]] = Field(None, description="Low array (today, last 24 hours)")
    h: Optional[List[str]] = Field(None, description="High array (today, last 24 hours)")
    o: Optional[str] = Field(None, description="Today's opening price")

    @property
    def ask_price(self) -> Optional[str]:
        """Get current ask price."""
        return self.a[0] if self.a and len(self.a) > 0 else None

    @property
    def bid_price(self) -> Optional[str]:
        """Get current bid price."""
        return self.b[0] if self.b and len(self.b) > 0 else None

    @property
    def last_price(self) -> Optional[str]:
        """Get last trade price."""
        return self.c[0] if self.c and len(self.c) > 0 else None

    @property
    def volume_24h(self) -> Optional[str]:
        """Get 24h volume."""
        return self.v[1] if self.v and len(self.v) > 1 else None

    @property
    def vwap_24h(self) -> Optional[str]:
        """Get 24h volume weighted average price."""
        return self.p[1] if self.p and len(self.p) > 1 else None


class TickerResponse(KrakenResponse):
    """Ticker response model."""
    result: Optional[Dict[str, TickerInfo]] = None

    @validator('result', pre=True)
    def parse_tickers(cls, v):
        """Parse ticker info objects."""
        if not v:
            return v

        parsed = {}
        for pair_name, ticker_data in v.items():
            if isinstance(ticker_data, dict):
                parsed[pair_name] = TickerInfo(**ticker_data)
            else:
                parsed[pair_name] = ticker_data
        return parsed


class OHLCData(BaseModel):
    """OHLC data model."""
    time: int = Field(description="Begin time of interval, in seconds since epoch")
    open: str = Field(description="Open price of interval")
    high: str = Field(description="High price of interval")
    low: str = Field(description="Low price of interval")
    close: str = Field(description="Close price of interval")
    vwap: str = Field(description="Volume weighted average price of interval")
    volume: str = Field(description="Volume of interval")
    count: int = Field(description="Number of trades in interval")


class OHLCResponse(KrakenResponse):
    """OHLC response model."""
    result: Optional[Dict[str, Union[List[List], int]]] = None

    def get_ohlc_data(self, pair: str) -> List[OHLCData]:
        """
        Get parsed OHLC data for a specific pair.
        
        Args:
            pair: Asset pair name
            
        Returns:
            List of OHLC data objects
        """
        if not self.result or pair not in self.result:
            return []

        raw_data = self.result[pair]
        if not isinstance(raw_data, list):
            return []

        ohlc_list = []
        for candle in raw_data:
            if len(candle) >= 8:
                ohlc_list.append(OHLCData(
                    time=int(candle[0]),
                    open=str(candle[1]),
                    high=str(candle[2]),
                    low=str(candle[3]),
                    close=str(candle[4]),
                    vwap=str(candle[5]),
                    volume=str(candle[6]),
                    count=int(candle[7])
                ))

        return ohlc_list


class OrderBookEntry(BaseModel):
    """Order book entry model."""
    price: str = Field(description="Price level")
    volume: str = Field(description="Volume at price level")
    timestamp: int = Field(description="Timestamp, seconds since epoch")


class OrderBookData(BaseModel):
    """Order book data model."""
    asks: List[OrderBookEntry] = Field(default_factory=list, description="Ask side of book")
    bids: List[OrderBookEntry] = Field(default_factory=list, description="Bid side of book")


class OrderBookResponse(KrakenResponse):
    """Order book response model."""
    result: Optional[Dict[str, Dict[str, List[List]]]] = None

    def get_order_book(self, pair: str) -> Optional[OrderBookData]:
        """
        Get parsed order book data for a specific pair.
        
        Args:
            pair: Asset pair name
            
        Returns:
            OrderBookData object or None
        """
        if not self.result or pair not in self.result:
            return None

        book_data = self.result[pair]

        asks = []
        for ask in book_data.get('asks', []):
            if len(ask) >= 3:
                asks.append(OrderBookEntry(
                    price=str(ask[0]),
                    volume=str(ask[1]),
                    timestamp=int(ask[2])
                ))

        bids = []
        for bid in book_data.get('bids', []):
            if len(bid) >= 3:
                bids.append(OrderBookEntry(
                    price=str(bid[0]),
                    volume=str(bid[1]),
                    timestamp=int(bid[2])
                ))

        return OrderBookData(asks=asks, bids=bids)


class TradeInfo(BaseModel):
    """Trade information model."""
    price: str = Field(description="Price")
    volume: str = Field(description="Volume")
    time: float = Field(description="Time, seconds since epoch")
    side: str = Field(description="Triggering order side (buy/sell)")
    ordertype: str = Field(description="Triggering order type")
    misc: str = Field(description="Miscellaneous")


class RecentTradesResponse(KrakenResponse):
    """Recent trades response model."""
    result: Optional[Dict[str, Union[List[List], str]]] = None

    def get_trades(self, pair: str) -> List[TradeInfo]:
        """
        Get parsed trade data for a specific pair.
        
        Args:
            pair: Asset pair name
            
        Returns:
            List of TradeInfo objects
        """
        if not self.result or pair not in self.result:
            return []

        raw_trades = self.result[pair]
        if not isinstance(raw_trades, list):
            return []

        trades = []
        for trade in raw_trades:
            if len(trade) >= 6:
                trades.append(TradeInfo(
                    price=str(trade[0]),
                    volume=str(trade[1]),
                    time=float(trade[2]),
                    side=str(trade[3]),
                    ordertype=str(trade[4]),
                    misc=str(trade[5])
                ))

        return trades


class BalanceResponse(KrakenResponse):
    """Account balance response model."""
    result: Optional[Dict[str, str]] = None

    def get_balance(self, asset: str) -> str:
        """
        Get balance for specific asset.
        
        Args:
            asset: Asset name
            
        Returns:
            Balance as string, '0' if not found
        """
        if not self.result:
            return '0'
        return self.result.get(asset, '0')

    def get_total_balance_usd(self, ticker_data: Optional[Dict[str, TickerInfo]] = None) -> str:
        """
        Calculate total balance in USD equivalent.
        
        Args:
            ticker_data: Ticker data for price conversion
            
        Returns:
            Total balance in USD as string
        """
        if not self.result or not ticker_data:
            return '0'

        total_usd = Decimal('0')

        for asset, balance in self.result.items():
            if asset in ['ZUSD', 'USD']:
                total_usd += Decimal(balance)
            elif ticker_data:
                # Try to find USD pair for this asset
                usd_pair = f"{asset}USD"
                if usd_pair in ticker_data:
                    ticker = ticker_data[usd_pair]
                    if ticker.last_price:
                        asset_price = Decimal(ticker.last_price)
                        asset_balance = Decimal(balance)
                        total_usd += asset_balance * asset_price

        return str(total_usd)


class TradeBalanceInfo(BaseModel):
    """Trade balance information model."""
    eb: Optional[str] = Field(None, description="Equivalent balance (combined balance of all currencies)")
    tb: Optional[str] = Field(None, description="Trade balance (combined balance of all equity currencies)")
    m: Optional[str] = Field(None, description="Margin amount of open positions")
    n: Optional[str] = Field(None, description="Unrealized net profit/loss of open positions")
    c: Optional[str] = Field(None, description="Cost basis of open positions")
    v: Optional[str] = Field(None, description="Current floating valuation of open positions")
    e: Optional[str] = Field(None, description="Equity = trade balance + unrealized net profit/loss")
    mf: Optional[str] = Field(None, description="Free margin = equity - initial margin (maximum margin available to open new positions)")
    ml: Optional[str] = Field(None, description="Margin level = (equity / initial margin) * 100")


class TradeBalanceResponse(KrakenResponse):
    """Trade balance response model."""
    result: Optional[TradeBalanceInfo] = None

    @validator('result', pre=True)
    def parse_trade_balance(cls, v):
        """Parse trade balance info."""
        if isinstance(v, dict):
            return TradeBalanceInfo(**v)
        return v


class OrderInfo(BaseModel):
    """Order information model."""
    refid: Optional[str] = Field(None, description="Referral order transaction ID that created the order")
    userref: Optional[int] = Field(None, description="User reference ID")
    status: Optional[OrderStatus] = Field(None, description="Order status")
    opentm: Optional[float] = Field(None, description="Unix timestamp of when order was placed")
    starttm: Optional[float] = Field(None, description="Unix timestamp of order start time (if set)")
    expiretm: Optional[float] = Field(None, description="Unix timestamp of order end time (if set)")
    descr: Optional[Dict[str, str]] = Field(None, description="Order description info")
    vol: Optional[str] = Field(None, description="Volume of order (base currency unless viqc set in oflags)")
    vol_exec: Optional[str] = Field(None, description="Volume executed (base currency unless viqc set in oflags)")
    cost: Optional[str] = Field(None, description="Total cost (quote currency unless unless viqc set in oflags)")
    fee: Optional[str] = Field(None, description="Total fee (quote currency)")
    price: Optional[str] = Field(None, description="Average price (quote currency unless viqc set in oflags)")
    stopprice: Optional[str] = Field(None, description="Stop price (quote currency, for trailing stops)")
    limitprice: Optional[str] = Field(None, description="Triggered limit price (quote currency, when limit based order type triggered)")
    misc: Optional[str] = Field(None, description="Miscellaneous")
    oflags: Optional[str] = Field(None, description="Comma delimited list of order flags")
    trades: Optional[List[str]] = Field(None, description="Array of trade IDs related to order (if trades info requested and data available)")

    @property
    def order_type(self) -> Optional[str]:
        """Get order type from description."""
        return self.descr.get('ordertype') if self.descr else None

    @property
    def order_side(self) -> Optional[str]:
        """Get order side from description."""
        return self.descr.get('type') if self.descr else None

    @property
    def pair(self) -> Optional[str]:
        """Get trading pair from description."""
        return self.descr.get('pair') if self.descr else None


class OpenOrdersResponse(KrakenResponse):
    """Open orders response model."""
    result: Optional[Dict[str, Union[Dict[str, OrderInfo], int]]] = None

    @validator('result', pre=True)
    def parse_orders(cls, v):
        """Parse order info objects."""
        if not v or 'open' not in v:
            return v

        open_orders = v['open']
        parsed_orders = {}

        for order_id, order_data in open_orders.items():
            if isinstance(order_data, dict):
                parsed_orders[order_id] = OrderInfo(**order_data)
            else:
                parsed_orders[order_id] = order_data

        v['open'] = parsed_orders
        return v

    def get_open_orders(self) -> Dict[str, OrderInfo]:
        """Get dictionary of open orders."""
        if not self.result or 'open' not in self.result:
            return {}
        return self.result['open']


class ClosedOrdersResponse(KrakenResponse):
    """Closed orders response model."""
    result: Optional[Dict[str, Union[Dict[str, OrderInfo], int]]] = None

    @validator('result', pre=True)
    def parse_orders(cls, v):
        """Parse order info objects."""
        if not v or 'closed' not in v:
            return v

        closed_orders = v['closed']
        parsed_orders = {}

        for order_id, order_data in closed_orders.items():
            if isinstance(order_data, dict):
                parsed_orders[order_id] = OrderInfo(**order_data)
            else:
                parsed_orders[order_id] = order_data

        v['closed'] = parsed_orders
        return v

    def get_closed_orders(self) -> Dict[str, OrderInfo]:
        """Get dictionary of closed orders."""
        if not self.result or 'closed' not in self.result:
            return {}
        return self.result['closed']


class QueryOrdersResponse(KrakenResponse):
    """Query orders response model."""
    result: Optional[Dict[str, OrderInfo]] = None

    @validator('result', pre=True)
    def parse_orders(cls, v):
        """Parse order info objects."""
        if not v:
            return v

        parsed_orders = {}
        for order_id, order_data in v.items():
            if isinstance(order_data, dict):
                parsed_orders[order_id] = OrderInfo(**order_data)
            else:
                parsed_orders[order_id] = order_data

        return parsed_orders


class TradeInfo(BaseModel):
    """Trade information model."""
    ordertxid: Optional[str] = Field(None, description="Order responsible for execution of trade")
    postxid: Optional[str] = Field(None, description="Position trade ID")
    pair: Optional[str] = Field(None, description="Asset pair")
    time: Optional[float] = Field(None, description="Unix timestamp of trade")
    type: Optional[str] = Field(None, description="Type of order (buy/sell)")
    ordertype: Optional[str] = Field(None, description="Order type")
    price: Optional[str] = Field(None, description="Average price order was executed at (quote currency)")
    cost: Optional[str] = Field(None, description="Total cost of order (quote currency)")
    fee: Optional[str] = Field(None, description="Total fee (quote currency)")
    vol: Optional[str] = Field(None, description="Volume (base currency)")
    margin: Optional[str] = Field(None, description="Initial margin (quote currency)")
    misc: Optional[str] = Field(None, description="Miscellaneous")


class TradeHistoryResponse(KrakenResponse):
    """Trade history response model."""
    result: Optional[Dict[str, Union[Dict[str, TradeInfo], int]]] = None

    @validator('result', pre=True)
    def parse_trades(cls, v):
        """Parse trade info objects."""
        if not v or 'trades' not in v:
            return v

        trades = v['trades']
        parsed_trades = {}

        for trade_id, trade_data in trades.items():
            if isinstance(trade_data, dict):
                parsed_trades[trade_id] = TradeInfo(**trade_data)
            else:
                parsed_trades[trade_id] = trade_data

        v['trades'] = parsed_trades
        return v

    def get_trades(self) -> Dict[str, TradeInfo]:
        """Get dictionary of trades."""
        if not self.result or 'trades' not in self.result:
            return {}
        return self.result['trades']


class AddOrderResult(BaseModel):
    """Add order result model."""
    descr: Optional[Dict[str, str]] = Field(None, description="Order description info")
    txid: Optional[List[str]] = Field(None, description="Array of transaction IDs for order")


class OrderResponse(KrakenResponse):
    """Order response model (for AddOrder, EditOrder, etc.)."""
    result: Optional[AddOrderResult] = None

    @validator('result', pre=True)
    def parse_order_result(cls, v):
        """Parse order result."""
        if isinstance(v, dict):
            return AddOrderResult(**v)
        return v

    @property
    def transaction_ids(self) -> List[str]:
        """Get transaction IDs."""
        if self.result and self.result.txid:
            return self.result.txid
        return []

    @property
    def primary_txid(self) -> Optional[str]:
        """Get primary transaction ID."""
        txids = self.transaction_ids
        return txids[0] if txids else None


class CancelOrderResult(BaseModel):
    """Cancel order result model."""
    count: Optional[int] = Field(None, description="Number of orders canceled")
    pending: Optional[bool] = Field(None, description="If set, order(s) is/are pending cancellation")


class CancelOrderResponse(KrakenResponse):
    """Cancel order response model."""
    result: Optional[CancelOrderResult] = None

    @validator('result', pre=True)
    def parse_cancel_result(cls, v):
        """Parse cancel order result."""
        if isinstance(v, dict):
            return CancelOrderResult(**v)
        return v


class WebSocketTokenResult(BaseModel):
    """WebSocket token result model."""
    token: Optional[str] = Field(None, description="WebSocket authentication token")
    expires: Optional[int] = Field(None, description="Token expiration time (Unix timestamp)")


class WebSocketTokenResponse(KrakenResponse):
    """WebSocket token response model."""
    result: Optional[WebSocketTokenResult] = None

    @validator('result', pre=True)
    def parse_token_result(cls, v):
        """Parse WebSocket token result."""
        if isinstance(v, dict):
            return WebSocketTokenResult(**v)
        return v

    @property
    def token(self) -> Optional[str]:
        """Get WebSocket token."""
        return self.result.token if self.result else None

    @property
    def expires(self) -> Optional[int]:
        """Get token expiration timestamp."""
        return self.result.expires if self.result else None


# Helper function to parse any Kraken response
def parse_kraken_response(
    response_data: Dict[str, Any],
    response_class: Optional[type] = None
) -> KrakenResponse:
    """
    Parse Kraken API response into appropriate model.
    
    Args:
        response_data: Raw response data from Kraken API
        response_class: Specific response class to use (optional)
        
    Returns:
        Parsed response object
    """
    try:
        if response_class:
            return response_class(**response_data)
        else:
            return KrakenResponse(**response_data)
    except Exception as e:
        logger.error(f"Failed to parse Kraken response: {e}")
        # Return base response with error
        return KrakenResponse(
            error=[f"Response parsing error: {str(e)}"],
            result=response_data.get('result')
        )


# Response type mapping for automatic parsing
RESPONSE_TYPE_MAPPING = {
    'ServerTime': ServerTimeResponse,
    'SystemStatus': SystemStatusResponse,
    'AssetInfo': AssetInfoResponse,
    'AssetPairs': AssetPairResponse,
    'Ticker': TickerResponse,
    'OHLC': OHLCResponse,
    'OrderBook': OrderBookResponse,
    'RecentTrades': RecentTradesResponse,
    'Balance': BalanceResponse,
    'TradeBalance': TradeBalanceResponse,
    'OpenOrders': OpenOrdersResponse,
    'ClosedOrders': ClosedOrdersResponse,
    'QueryOrders': QueryOrdersResponse,
    'TradesHistory': TradeHistoryResponse,
    'AddOrder': OrderResponse,
    'EditOrder': OrderResponse,
    'CancelOrder': CancelOrderResponse,
    'CancelAllOrders': CancelOrderResponse,
    'GetWebSocketsToken': WebSocketTokenResponse,
}


def get_response_model(endpoint_name: str) -> type:
    """
    Get appropriate response model for endpoint.
    
    Args:
        endpoint_name: Name of the API endpoint
        
    Returns:
        Response model class
    """
    return RESPONSE_TYPE_MAPPING.get(endpoint_name, KrakenResponse)
