# WebSocket V2 Implementation - Complete Guide

## Overview

This comprehensive WebSocket V2 implementation provides enterprise-grade real-time data streaming and order management for Kraken exchange. Built with advanced features including intelligent failover, proactive authentication, and seamless integration with existing trading infrastructure.

## 🚀 Key Features

### **Enhanced Connection Management**
- **Automatic Reconnection**: Exponential backoff with connection healing
- **Health Monitoring**: Real-time connection status and performance tracking
- **Circuit Breaker**: Protection against repeated authentication failures
- **Rate Limiting**: Built-in subscription rate limiting and throttling

### **Real-Time Data Processing**
- **Balance Streaming**: Live balance updates with integration to existing balance manager
- **Market Data**: Ticker, orderbook, trades, and OHLC data processing
- **Type Safety**: Strongly typed data models with validation
- **Performance Optimized**: High-throughput message processing with queuing

### **Order Management via WebSocket**
- **Real-Time Order Placement**: Direct order placement through WebSocket V2
- **Order Tracking**: Live order status updates and execution monitoring
- **Validation**: Comprehensive order parameter validation
- **Error Handling**: Robust error handling with timeout management

### **Unified Data Feed**
- **Primary WebSocket**: WebSocket V2 as primary data source
- **REST Fallback**: Automatic fallback to REST API for reliability
- **Intelligent Switching**: Data quality-based source selection
- **Caching**: Smart caching with freshness validation

### **Advanced Authentication**
- **Proactive Token Refresh**: Automatic token refresh before expiry
- **Session Management**: Persistent token storage and recovery
- **Error Recovery**: Comprehensive authentication error handling
- **Security**: Secure token handling and storage

## 📁 Architecture

```
src/websocket/
├── websocket_v2_manager.py      # Main WebSocket V2 connection manager
├── websocket_v2_channels.py     # Channel-specific data processors
├── websocket_v2_orders.py       # Order management via WebSocket
├── data_models.py               # Type-safe data models
├── integration_example_v2.py    # Comprehensive integration example
└── README_V2_IMPLEMENTATION.md  # This documentation

src/data/
└── unified_data_feed.py         # Unified data feed with fallback

src/auth/
└── websocket_authentication_manager.py  # Enhanced authentication
```

## 🛠 Components

### **1. WebSocketV2Manager**
Main connection manager with advanced features:

```python
from src.websocket import WebSocketV2Manager, WebSocketV2Config

# Configure WebSocket
config = WebSocketV2Config(
    ping_interval=20.0,
    heartbeat_timeout=60.0,
    message_queue_size=10000,
    subscription_rate_limit=5
)

# Initialize manager
ws_manager = WebSocketV2Manager(
    exchange_client=exchange_client,
    api_key=api_key,
    private_key=private_key,
    config=config,
    enable_debug=True
)

# Start connection
await ws_manager.start()

# Subscribe to channels
await ws_manager.subscribe_channel('ticker', {'symbol': ['BTC/USDT']})
await ws_manager.subscribe_channel('balances', private=True)
```

### **2. WebSocketV2ChannelProcessor**
Specialized processors for different channel types:

```python
# Get channel processor
processor = ws_manager.get_channel_processor()

# Access latest data
balance = processor.get_latest_balance('USDT')
ticker = processor.get_latest_ticker('BTC/USDT')
orderbook = processor.get_latest_orderbook('BTC/USDT')

# Get processing statistics
stats = processor.get_processing_stats()
print(f"Balance updates: {stats['balance_updates']}")
```

### **3. WebSocketV2OrderManager**
Order management via WebSocket V2:

```python
# Get order manager
order_manager = ws_manager.get_order_manager()

# Place buy order
response = await order_manager.place_order(
    symbol='BTC/USDT',
    side='buy',
    order_type='limit',
    volume='0.001',
    price='50000.00',
    order_flags=['fciq']  # Fee in quote currency
)

if response.error:
    print(f"Order failed: {response.error}")
else:
    print(f"Order placed: {response.order_id}")

# Cancel order
await order_manager.cancel_order(order_id=response.order_id)

# Get active orders
active_orders = order_manager.get_active_orders()
```

### **4. UnifiedDataFeed**
Intelligent data source management:

```python
from src.data import UnifiedDataFeed

# Initialize unified feed
data_feed = UnifiedDataFeed(
    exchange_client=exchange_client,
    symbols=['BTC/USDT', 'ETH/USDT'],
    api_key=api_key,
    private_key=private_key
)

await data_feed.start()

# Get data with automatic source selection
balance = await data_feed.get_balance('USDT')  # WebSocket primary, REST fallback
ticker = await data_feed.get_ticker('BTC/USDT')
orderbook = await data_feed.get_orderbook('BTC/USDT')

# Check data sources health
health = data_feed.get_data_sources_health()
```

## 📊 Real-Time Data Integration

### **Balance Updates**
Seamless integration with existing balance management:

```python
async def handle_balance_updates(balance_updates):
    for balance in balance_updates:
        asset = balance.asset
        free_balance = balance.free_balance
        
        print(f"{asset}: {free_balance} (free)")
        
        # Automatic integration with balance manager
        # The system automatically injects updates into existing balance manager
        # and resets circuit breakers on fresh data
```

### **Market Data Processing**
High-performance market data handling:

```python
async def handle_ticker_updates(ticker_updates):
    for ticker in ticker_updates:
        symbol = ticker.symbol
        price = ticker.last
        spread = ticker.spread_percentage
        
        print(f"{symbol}: ${price} (spread: {spread:.3f}%)")
        
        # Trigger trading logic
        await check_trading_opportunity(symbol, ticker)

async def handle_orderbook_updates(orderbook_updates):
    for orderbook in orderbook_updates:
        symbol = orderbook.symbol
        best_bid = orderbook.best_bid
        best_ask = orderbook.best_ask
        
        if best_bid and best_ask:
            mid_price = orderbook.mid_price
            print(f"{symbol} mid: ${mid_price}")
```

### **Order Status Tracking**
Real-time order execution monitoring:

```python
async def handle_order_updates(order_update):
    order_id = order_update.order_id
    status = order_update.status
    volume_exec = order_update.volume_exec
    
    if status == 'closed':
        print(f"Order {order_id} filled: {volume_exec}")
        await check_new_opportunities()
    elif status == 'partial':
        remaining = order_update.volume - volume_exec
        print(f"Order {order_id} partial fill: {remaining} remaining")
```

## 🔧 Configuration Options

### **WebSocket Configuration**
```python
config = WebSocketV2Config(
    # Connection settings
    public_url="wss://ws.kraken.com/v2",
    private_url="wss://ws-auth.kraken.com/v2",
    ping_interval=20.0,
    ping_timeout=10.0,
    connection_timeout=30.0,
    
    # Reconnection settings
    reconnect_delay=1.0,
    max_reconnect_attempts=10,
    reconnect_backoff=2.0,
    max_reconnect_delay=60.0,
    
    # Message processing
    message_queue_size=10000,
    heartbeat_timeout=60.0,
    
    # Rate limiting
    subscription_rate_limit=5,
    subscription_rate_window=60.0,
    
    # Authentication
    token_refresh_interval=13 * 60  # 13 minutes
)
```

### **Data Feed Configuration**
```python
data_feed = UnifiedDataFeed(
    exchange_client=exchange_client,
    symbols=trading_symbols,
    api_key=api_key,
    private_key=private_key,
    websocket_config=config,
    enable_debug=True
)

# Configure freshness thresholds
data_feed.freshness_thresholds = {
    DataType.BALANCE: 60.0,     # 1 minute
    DataType.TICKER: 10.0,      # 10 seconds
    DataType.ORDERBOOK: 5.0,    # 5 seconds
    DataType.TRADES: 30.0,      # 30 seconds
}

# Enable/disable features
data_feed.fallback_enabled = True
data_feed.auto_switch_enabled = True
```

## 🎯 Integration Patterns

### **Pattern 1: Enhanced Existing Bot**
Add WebSocket V2 to existing trading bot:

```python
class EnhancedTradingBot:
    def __init__(self):
        self.exchange_client = existing_exchange_client
        
        # Add WebSocket V2 manager
        self.websocket_manager = WebSocketV2Manager(
            exchange_client=self.exchange_client,
            api_key=self.api_key,
            private_key=self.private_key
        )
        
        # Register handlers
        self.websocket_manager.register_handler('balance', self.handle_balance_updates)
        self.websocket_manager.register_handler('ticker', self.handle_market_data)
    
    async def start(self):
        # Start existing components
        await self.existing_startup_sequence()
        
        # Start WebSocket V2
        await self.websocket_manager.start()
        
        # Subscribe to required channels
        await self.websocket_manager.subscribe_channel('balances', private=True)
        await self.websocket_manager.subscribe_channel('ticker', {'symbol': self.symbols})
```

### **Pattern 2: Unified Data Access**
Replace multiple data sources with unified feed:

```python
class UnifiedDataBot:
    def __init__(self):
        # Replace individual data managers with unified feed
        self.data_feed = UnifiedDataFeed(
            exchange_client=exchange_client,
            symbols=trading_symbols,
            api_key=api_key,
            private_key=private_key
        )
    
    async def get_account_data(self):
        # Single interface for all data
        balances = {}
        for asset in ['USDT', 'BTC', 'ETH']:
            balance = await self.data_feed.get_balance(asset)
            if balance:
                balances[asset] = balance
        return balances
    
    async def get_market_data(self, symbol):
        # Intelligent source selection
        ticker = await self.data_feed.get_ticker(symbol)
        orderbook = await self.data_feed.get_orderbook(symbol)
        
        return {
            'ticker': ticker,
            'orderbook': orderbook,
            'source': 'websocket' if self.data_feed.websocket_manager.is_connected else 'rest'
        }
```

### **Pattern 3: WebSocket-First Trading**
Build new trading logic around WebSocket V2:

```python
class WebSocketTrader:
    def __init__(self):
        self.ws_manager = WebSocketV2Manager(...)
        self.order_manager = None
        
    async def start_trading(self):
        await self.ws_manager.start()
        self.order_manager = self.ws_manager.get_order_manager()
        
        # Set up real-time event handling
        self.ws_manager.register_handler('ticker', self.on_price_update)
        self.ws_manager.register_handler('balance', self.on_balance_update)
        self.ws_manager.register_handler('order_update', self.on_order_update)
    
    async def on_price_update(self, ticker_updates):
        for ticker in ticker_updates:
            # Real-time trading decisions
            if self.should_buy(ticker):
                await self.place_buy_order(ticker.symbol, ticker.ask)
    
    async def place_buy_order(self, symbol, price):
        # Direct WebSocket order placement
        response = await self.order_manager.place_order(
            symbol=symbol,
            side='buy',
            order_type='limit',
            volume=self.calculate_position_size(price),
            price=price
        )
        
        if response.order_id:
            self.track_order(response.order_id)
```

## 🔍 Monitoring and Diagnostics

### **Connection Status**
```python
# Get comprehensive status
status = ws_manager.get_status()
print(f"Connected: {status['is_connected']}")
print(f"Authenticated: {status['is_authenticated']}")
print(f"Uptime: {status['uptime']:.2f}s")
print(f"Active subscriptions: {status['active_subscriptions']}")

# Message processing stats
stats = status['statistics']
print(f"Messages received: {stats['messages_received']}")
print(f"Messages processed: {stats['messages_processed']}")
print(f"Queue size: {status['message_queue_size']}")
```

### **Data Quality Monitoring**
```python
# Check data feed health
health = data_feed.get_data_sources_health()

websocket_health = health['websocket_v2']
print(f"WebSocket available: {websocket_health['available']}")
print(f"Quality score: {websocket_health['quality_score']:.2f}")

rest_health = health['rest_api']
print(f"REST quality score: {rest_health['quality_score']:.2f}")

# Performance metrics
performance = data_feed.get_status()['performance_stats']
print(f"Cache hit rate: {performance['cache_hits']/performance['cache_misses']*100:.1f}%")
print(f"Source switches: {performance['source_switches']}")
```

### **Order Management Stats**
```python
# Order statistics
order_stats = order_manager.get_order_stats()
print(f"Orders placed: {order_stats['orders_placed']}")
print(f"Orders filled: {order_stats['orders_filled']}")
print(f"Success rate: {order_stats['orders_filled']/order_stats['orders_placed']*100:.1f}%")
print(f"Avg execution time: {order_stats['avg_execution_time_ms']:.1f}ms")

# Active orders
active_orders = order_manager.get_active_orders()
print(f"Active orders: {len(active_orders)}")

for order_id, order in active_orders.items():
    print(f"  {order_id}: {order['symbol']} {order['side']} {order['volume']}")
```

## 🚨 Error Handling

### **Connection Errors**
```python
# Handle connection failures
async def on_connection_error():
    logger.warning("WebSocket connection lost")
    
    # Automatic reconnection is handled internally
    # Manual intervention only needed for persistent failures
    
    if ws_manager.status.reconnect_count > 5:
        logger.error("Multiple reconnection failures - check network/auth")
        await fallback_to_rest_only()

# Handle authentication errors
async def on_auth_error(error_message):
    logger.error(f"Authentication failed: {error_message}")
    
    # Token refresh is handled automatically
    # Manual token reset may be needed for persistent auth issues
    if "invalid credentials" in error_message.lower():
        await reset_authentication_credentials()
```

### **Data Quality Issues**
```python
# Monitor data freshness
async def check_data_quality():
    # Check if data is fresh
    if not processor.has_fresh_data('balance', max_age=120):
        logger.warning("Balance data is stale - using REST fallback")
        balance = await exchange_client.get_balance_rest()
    
    # Monitor error rates
    stats = processor.get_processing_stats()
    error_rate = stats['processing_errors'] / stats['balance_updates']
    
    if error_rate > 0.1:  # More than 10% error rate
        logger.warning(f"High processing error rate: {error_rate:.1%}")
        await restart_websocket_connection()
```

### **Order Failures**
```python
# Handle order placement failures
async def place_order_with_retry(symbol, side, volume, price):
    max_retries = 3
    
    for attempt in range(max_retries):
        response = await order_manager.place_order(
            symbol=symbol,
            side=side,
            order_type='limit',
            volume=volume,
            price=price
        )
        
        if not response.error:
            return response  # Success
        
        logger.warning(f"Order attempt {attempt + 1} failed: {response.error}")
        
        if "insufficient balance" in response.error.lower():
            # Don't retry insufficient balance errors
            break
        
        if attempt < max_retries - 1:
            await asyncio.sleep(1)  # Wait before retry
    
    # All retries failed - fall back to REST API
    logger.error(f"WebSocket order failed after {max_retries} attempts - using REST fallback")
    return await place_order_via_rest(symbol, side, volume, price)
```

## 📈 Performance Optimization

### **Message Processing**
- **Batch Processing**: Multiple updates processed together
- **Memory Management**: Automatic cleanup of old data
- **Queue Management**: Configurable queue sizes and processing rates
- **Parallel Processing**: Independent processing of different channel types

### **Connection Optimization**
- **Persistent Connections**: Long-lived connections with health monitoring
- **Smart Reconnection**: Exponential backoff with immediate retry for network issues
- **Subscription Management**: Efficient re-subscription after reconnection
- **Rate Limiting**: Built-in protection against API rate limits

### **Data Caching**
- **Smart Caching**: Intelligent caching based on data type and freshness
- **Cache Invalidation**: Automatic cleanup of stale data
- **Memory Efficiency**: Bounded cache sizes and LRU eviction
- **Performance Metrics**: Detailed cache hit/miss tracking

## 🔐 Security Features

### **Authentication Security**
- **Secure Token Storage**: Encrypted token persistence
- **Proactive Refresh**: Token refresh before expiry
- **Circuit Breaker**: Protection against authentication flooding
- **Error Handling**: Secure error responses without information leakage

### **Connection Security**
- **TLS/SSL**: Secure WebSocket connections
- **API Key Protection**: Secure credential handling
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Comprehensive parameter validation

## 🎯 Best Practices

### **Resource Management**
```python
# Always use context managers or explicit cleanup
try:
    await ws_manager.start()
    # Use WebSocket
finally:
    await ws_manager.stop()  # Always cleanup

# Or use context managers (if implemented)
async with WebSocketV2Manager(...) as ws_manager:
    # Use WebSocket - automatic cleanup
    pass
```

### **Error Handling**
```python
# Register error handlers
ws_manager.register_handler('error', handle_websocket_error)

async def handle_websocket_error(error):
    logger.error(f"WebSocket error: {error}")
    
    # Implement recovery logic
    if "authentication" in str(error).lower():
        await refresh_authentication()
    elif "connection" in str(error).lower():
        # Reconnection is automatic, but you can add custom logic
        await notify_admin_of_connection_issues()
```

### **Performance Monitoring**
```python
# Regular performance checks
async def monitor_performance():
    while running:
        status = ws_manager.get_status()
        
        # Check message processing rate
        stats = status['statistics']
        if stats['messages_received'] > 0:
            processing_rate = stats['messages_processed'] / stats['messages_received']
            if processing_rate < 0.95:
                logger.warning(f"Low processing rate: {processing_rate:.1%}")
        
        # Check queue size
        if status['message_queue_size'] > status['max_queue_size'] * 0.8:
            logger.warning("Message queue approaching capacity")
        
        await asyncio.sleep(60)  # Check every minute
```

## 🔄 Migration Guide

### **From Existing WebSocket Implementation**

1. **Update Imports**:
```python
# Old
from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager

# New
from src.websocket import WebSocketV2Manager, WebSocketV2Config
```

2. **Update Initialization**:
```python
# Old
ws_manager = KrakenProWebSocketManager(api_key, api_secret)

# New
config = WebSocketV2Config()
ws_manager = WebSocketV2Manager(exchange_client, api_key, private_key, config)
```

3. **Update Event Handling**:
```python
# Old
def handle_balance(balance_data):
    for asset, data in balance_data.items():
        process_balance(asset, data)

# New
async def handle_balance(balance_updates: List[BalanceUpdate]):
    for balance in balance_updates:
        process_balance(balance.asset, balance.to_dict())
```

4. **Update Data Access**:
```python
# Old
balance = ws_manager.get_balance('USDT')

# New
processor = ws_manager.get_channel_processor()
balance_update = processor.get_latest_balance('USDT')
balance = balance_update.to_dict() if balance_update else None
```

### **Integration with Existing Balance Manager**

The new WebSocket V2 system automatically integrates with existing balance managers:

```python
# No changes needed to existing balance manager code
# WebSocket V2 automatically injects balance updates into:
# - balance_manager.balances[asset] = balance_dict
# - Resets circuit breakers on fresh data
# - Updates last_update timestamps
# - Clears failure counters

# Your existing trading logic continues to work:
current_balance = balance_manager.get_balance('USDT')
if current_balance and current_balance['free'] > 10.0:
    # Execute trading logic
    pass
```

## 🧪 Testing

### **Unit Testing**
```python
import pytest
from src.websocket import WebSocketV2Manager

@pytest.mark.asyncio
async def test_websocket_connection():
    # Mock exchange client
    mock_client = MockExchangeClient()
    
    # Test connection
    ws_manager = WebSocketV2Manager(mock_client, "test_key", "test_secret")
    started = await ws_manager.start()
    
    assert started is True
    assert ws_manager.is_connected is True
    
    await ws_manager.stop()

@pytest.mark.asyncio
async def test_order_placement():
    # Test order placement
    order_manager = ws_manager.get_order_manager()
    
    response = await order_manager.place_order(
        symbol='BTC/USDT',
        side='buy',
        order_type='limit',
        volume='0.001',
        price='50000'
    )
    
    assert response.error is None
    assert response.order_id is not None
```

### **Integration Testing**
```python
@pytest.mark.asyncio
async def test_data_feed_integration():
    # Test unified data feed
    data_feed = UnifiedDataFeed(exchange_client, ['BTC/USDT'])
    await data_feed.start()
    
    # Test data retrieval
    ticker = await data_feed.get_ticker('BTC/USDT')
    assert ticker is not None
    assert 'last' in ticker
    
    await data_feed.stop()
```

## 📋 Troubleshooting

### **Common Issues**

**1. Authentication Failed**
```
ERROR: Authentication failed: Invalid credentials
```
- **Solution**: Check API key permissions, ensure "Access WebSockets API" is enabled
- **Debug**: Verify API key and private key format
- **Recovery**: Reset authentication credentials

**2. Connection Timeout**
```
ERROR: Connection timeout after 30s
```
- **Solution**: Check network connectivity, firewall settings
- **Debug**: Test with longer connection timeout
- **Recovery**: Enable debug logging to see detailed connection attempts

**3. Subscription Failures**
```
WARNING: Subscription rate limit exceeded
```
- **Solution**: Reduce subscription rate, batch subscription requests
- **Configuration**: Increase `subscription_rate_limit` in config
- **Recovery**: Implement subscription retry with backoff

**4. Data Processing Errors**
```
ERROR: Error processing message: KeyError
```
- **Solution**: Check Kraken API documentation for message format changes
- **Debug**: Enable debug logging to see raw messages
- **Recovery**: Update data model parsing logic

### **Debug Steps**

1. **Enable Debug Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

ws_manager = WebSocketV2Manager(..., enable_debug=True)
```

2. **Check Connection Status**:
```python
status = ws_manager.get_status()
print(json.dumps(status, indent=2, default=str))
```

3. **Monitor Message Flow**:
```python
stats = ws_manager.get_channel_processor().get_processing_stats()
print(f"Messages processed: {stats}")
```

4. **Verify Authentication**:
```python
auth_status = ws_manager._auth_manager.get_authentication_status()
print(f"Auth status: {auth_status}")
```

## 🤝 Contributing

### **Code Style**
- Follow PEP 8 guidelines
- Use type hints for all functions
- Add comprehensive docstrings
- Include error handling in all async functions

### **Testing Requirements**
- Add unit tests for new features
- Include integration tests for WebSocket functionality
- Test error conditions and edge cases
- Verify backward compatibility

### **Documentation**
- Update README for new features
- Add inline comments for complex logic
- Include usage examples
- Document configuration options

---

This WebSocket V2 implementation provides a robust, scalable foundation for real-time trading operations with Kraken exchange. The comprehensive feature set ensures reliability, performance, and ease of integration with existing trading infrastructure.