# Kraken WebSocket V2 Implementation

A comprehensive, high-performance WebSocket V2 client for Kraken exchange with authenticated balance streaming, real-time market data, and robust connection management.

## Features

### Core Capabilities
- **WebSocket V2 Protocol**: Full support for Kraken's latest WebSocket V2 API
- **Authenticated Balance Streaming**: Real-time balance updates via private channels
- **Real-time Market Data**: Ticker, orderbook, trades, and OHLC data streaming
- **Automatic Connection Management**: Auto-reconnection with exponential backoff
- **Message Queuing**: High-performance message processing with queuing
- **Event-driven Architecture**: Callback-based event handling
- **Thread-safe Operations**: Concurrent access with proper synchronization
- **Rate Limiting**: Built-in rate limiting and subscription management
- **Token Management**: Automatic authentication token refresh

### Advanced Features
- **Connection Healing**: Automatic detection and recovery from connection issues
- **Message Validation**: Type-safe message parsing and validation
- **Performance Monitoring**: Comprehensive statistics and performance metrics
- **Integration Ready**: Seamless integration with existing trading bot architecture
- **Error Recovery**: Robust error handling and recovery mechanisms
- **Visual Monitoring**: Optional visual display of connection and data status

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    KrakenWebSocketV2                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ ConnectionManager│  │  MessageHandler │  │   Data Models   │ │
│  │                 │  │                 │  │                 │ │
│  │ • Connection    │  │ • Message       │  │ • BalanceUpdate │ │
│  │   Lifecycle     │  │   Processing    │  │ • TickerUpdate  │ │
│  │ • Reconnection  │  │ • Validation    │  │ • OrderBook     │ │
│  │ • Health        │  │ • Routing       │  │ • TradeUpdate   │ │
│  │   Monitoring    │  │ • Callbacks     │  │ • OHLCUpdate    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
src/websocket/
├── __init__.py                 # Package initialization and exports
├── kraken_websocket_v2.py     # Main WebSocket V2 client
├── connection_manager.py      # Connection lifecycle management
├── message_handler.py         # Message processing and routing
├── data_models.py            # WebSocket message models
├── integration_example.py    # Integration example and usage guide
└── README.md                 # This documentation
```

## Quick Start

### Basic Usage

```python
from src.websocket import KrakenWebSocketV2

# Initialize WebSocket client
ws_client = KrakenWebSocketV2(
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# Set up callbacks
async def handle_balance_update(balance_updates):
    for balance in balance_updates:
        print(f"{balance.asset}: {balance.free_balance}")

async def handle_ticker_update(ticker_updates):
    for ticker in ticker_updates:
        print(f"{ticker.symbol}: ${ticker.last}")

# Register callbacks
ws_client.register_callback('balance', handle_balance_update)
ws_client.register_callback('ticker', handle_ticker_update)

# Connect and subscribe
await ws_client.connect()
await ws_client.subscribe_balance()
await ws_client.subscribe_ticker(['BTC/USDT', 'ETH/USDT'])
```

### Advanced Integration

```python
from src.websocket import KrakenWebSocketV2, KrakenWebSocketConfig

# Custom configuration
config = KrakenWebSocketConfig(
    ping_interval=20.0,
    heartbeat_timeout=60.0,
    message_queue_size=10000,
    subscription_rate_limit=5
)

# Initialize with custom config
ws_client = KrakenWebSocketV2(
    api_key=api_key,
    api_secret=api_secret,
    config=config
)

# Set exchange client reference for token refresh
ws_client.set_exchange_client(exchange_client)

# Connect with private channels
await ws_client.connect(private_channels=True)

# Multiple subscriptions
await ws_client.subscribe_balance()
await ws_client.subscribe_ticker(trading_pairs)
await ws_client.subscribe_orderbook(trading_pairs, depth=10)
await ws_client.subscribe_trades(trading_pairs)
await ws_client.subscribe_ohlc(trading_pairs, interval=1)
```

## API Reference

### KrakenWebSocketV2

#### Constructor
```python
KrakenWebSocketV2(api_key=None, api_secret=None, config=None)
```

#### Connection Methods
```python
await connect(private_channels=True) -> bool
await disconnect()
```

#### Subscription Methods
```python
await subscribe_balance() -> bool
await subscribe_ticker(symbols: List[str]) -> bool
await subscribe_orderbook(symbols: List[str], depth: int = 10) -> bool
await subscribe_trades(symbols: List[str]) -> bool
await subscribe_ohlc(symbols: List[str], interval: int = 1) -> bool
await unsubscribe(channel: str, symbols: List[str] = None) -> bool
```

#### Data Access Methods
```python
get_balance(asset: str) -> Optional[Dict[str, Any]]
get_all_balances() -> Dict[str, Dict[str, Any]]
get_ticker(symbol: str) -> Optional[Dict[str, Any]]
get_orderbook(symbol: str) -> Optional[Dict[str, Any]]
get_recent_trades(symbol: str, limit: int = 50) -> List[Dict[str, Any]]
get_ohlc_data(symbol: str, limit: int = 100) -> List[Dict[str, Any]]
```

#### Callback Management
```python
register_callback(event_type: str, callback: Callable)
unregister_callback(event_type: str, callback: Callable)
```

#### Status Methods
```python
is_connected() -> bool
is_authenticated() -> bool
get_connection_status() -> Dict[str, Any]
get_balance_streaming_status() -> Dict[str, Any]
```

### Data Models

#### BalanceUpdate
```python
@dataclass
class BalanceUpdate:
    asset: str
    balance: Decimal
    hold_trade: Decimal
    timestamp: float
    
    @property
    def free_balance(self) -> Decimal
    @property
    def total_balance(self) -> Decimal
```

#### TickerUpdate
```python
@dataclass
class TickerUpdate:
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: Decimal
    high: Decimal
    low: Decimal
    vwap: Decimal
    timestamp: float
    
    @property
    def spread(self) -> Decimal
    @property
    def spread_percentage(self) -> Decimal
    @property
    def mid_price(self) -> Decimal
```

#### OrderBookUpdate
```python
@dataclass
class OrderBookUpdate:
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: float
    
    @property
    def best_bid(self) -> Optional[OrderBookLevel]
    @property
    def best_ask(self) -> Optional[OrderBookLevel]
    @property
    def spread(self) -> Decimal
```

## Event Types

### Available Callbacks
- `'balance'`: Balance updates (List[BalanceUpdate])
- `'ticker'`: Ticker updates (List[TickerUpdate])
- `'orderbook'`: Orderbook updates (List[OrderBookUpdate])
- `'trade'`: Trade updates (List[TradeUpdate])
- `'ohlc'`: OHLC updates (List[OHLCUpdate])
- `'connected'`: Connection established (no arguments)
- `'disconnected'`: Connection lost (no arguments)
- `'authenticated'`: Authentication successful (no arguments)
- `'error'`: Error occurred (Exception)

### Callback Signature
```python
async def callback_function(data):
    # Handle the data
    pass

# Register callback
ws_client.register_callback('balance', callback_function)
```

## Integration with Existing Bot

### Balance Manager Integration

The WebSocket V2 system integrates seamlessly with the existing balance manager:

```python
# In your bot initialization
ws_client = KrakenWebSocketV2(api_key, api_secret)
ws_client.set_exchange_client(exchange_client)

async def integrate_balance_updates(balance_updates):
    for balance_update in balance_updates:
        asset = balance_update.asset
        balance_dict = balance_update.to_dict()
        
        # Direct integration with existing balance manager
        if balance_manager:
            balance_manager.balances[asset] = balance_dict
            
            # Reset circuit breaker on fresh data
            if balance_manager.circuit_breaker_active:
                balance_manager.circuit_breaker_active = False
                balance_manager.consecutive_failures = 0
            
            balance_manager.last_update = time.time()

ws_client.register_callback('balance', integrate_balance_updates)
```

### Trading Engine Integration

```python
async def integrate_ticker_updates(ticker_updates):
    for ticker_update in ticker_updates:
        symbol = ticker_update.symbol
        ticker_dict = ticker_update.to_dict()
        
        # Update trading engine with fresh market data
        if trading_engine:
            await trading_engine.update_market_data(symbol, 'ticker', ticker_dict)
            await trading_engine.check_trading_opportunity(symbol, ticker_dict)

ws_client.register_callback('ticker', integrate_ticker_updates)
```

## Configuration

### KrakenWebSocketConfig

```python
@dataclass
class KrakenWebSocketConfig:
    # WebSocket endpoints
    public_url: str = "wss://ws.kraken.com/v2"
    private_url: str = "wss://ws-auth.kraken.com/v2"
    
    # Connection settings
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    reconnect_delay: float = 1.0
    max_reconnect_attempts: int = 10
    
    # Message settings
    message_queue_size: int = 10000
    heartbeat_timeout: float = 60.0
    
    # Rate limiting
    subscription_rate_limit: int = 5
    
    # Authentication
    token_refresh_interval: float = 13 * 60  # 13 minutes
```

### Connection Configuration

```python
@dataclass
class ConnectionConfig:
    url: str
    auth_url: Optional[str] = None
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    close_timeout: float = 10.0
    max_reconnect_attempts: int = 10
    reconnect_delay: float = 1.0
    reconnect_backoff: float = 2.0
    max_reconnect_delay: float = 60.0
    message_queue_size: int = 1000
    heartbeat_timeout: float = 60.0
    connection_timeout: float = 30.0
```

## Performance Features

### Message Processing
- **High-throughput Queue**: Asynchronous message queue with configurable size
- **Batch Processing**: Efficient processing of multiple updates in batches
- **Memory Management**: Automatic cleanup of old data to prevent memory leaks
- **Rate Limiting**: Built-in rate limiting to prevent API abuse

### Connection Management
- **Health Monitoring**: Continuous monitoring of connection health
- **Automatic Reconnection**: Exponential backoff reconnection strategy
- **Token Refresh**: Proactive authentication token refresh
- **Error Recovery**: Comprehensive error handling and recovery

### Data Management
- **Type Safety**: Strong typing with dataclasses and validation
- **Precision Handling**: Decimal precision for financial calculations
- **Format Conversion**: Automatic conversion between WebSocket and internal formats
- **Cache Management**: Intelligent caching of recent data

## Error Handling

### Connection Errors
- Automatic reconnection with exponential backoff
- Connection state tracking and recovery
- Health monitoring and stale connection detection

### Authentication Errors
- Automatic token refresh before expiry
- Authentication failure handling and retry
- Permission error detection and reporting

### Message Errors
- Message validation and error reporting
- Invalid message handling and recovery
- Rate limiting detection and backoff

### Integration Errors
- Callback error isolation and logging
- Data conversion error handling
- Circuit breaker integration for reliability

## Monitoring and Debugging

### Status Information
```python
# Get connection status
status = ws_client.get_connection_status()
print(f"Connected: {status['is_running']}")
print(f"Uptime: {status['uptime']:.2f}s")
print(f"Message rate: {status['message_handler_stats']['overall_message_rate']:.2f}/s")

# Get balance streaming status
balance_status = ws_client.get_balance_streaming_status()
print(f"Balance streaming: {balance_status['streaming_healthy']}")
print(f"Auth token: {balance_status['auth_token_available']}")
```

### Performance Metrics
```python
# Get message handler statistics
stats = ws_client.message_handler.get_statistics()
print(f"Total messages: {stats['total_messages']}")
print(f"Error count: {stats['error_count']}")
print(f"Processing rates: {stats['processing_rates']}")
```

### Logging
The system uses comprehensive logging with different levels:
- `INFO`: Connection events, subscriptions, major state changes
- `DEBUG`: Message processing, data updates, detailed operations
- `WARNING`: Non-critical errors, fallback operations
- `ERROR`: Critical errors, connection failures, data corruption

## Best Practices

### Resource Management
```python
try:
    await ws_client.connect()
    # Use WebSocket client
finally:
    await ws_client.disconnect()  # Always disconnect
```

### Error Handling
```python
async def handle_error(error):
    logger.error(f"WebSocket error: {error}")
    # Implement recovery logic
    
ws_client.register_callback('error', handle_error)
```

### Rate Limiting
```python
# Limit subscription rate
config = KrakenWebSocketConfig(subscription_rate_limit=3)
ws_client = KrakenWebSocketV2(config=config)

# Batch subscriptions
symbols = ['BTC/USDT', 'ETH/USDT', 'SHIB/USDT']
await ws_client.subscribe_ticker(symbols)  # Single request
```

### Memory Management
```python
# The system automatically manages memory, but you can help:
# - Use appropriate queue sizes
# - Process messages promptly
# - Avoid storing large amounts of historical data
```

## Troubleshooting

### Common Issues

#### Authentication Failed
```
ERROR: Authentication failed: Invalid credentials
```
**Solution**: Check API key permissions, ensure "Access WebSockets API" is enabled

#### Connection Timeout
```
ERROR: Connection timeout after 30s
```
**Solution**: Check network connectivity, firewall settings, increase timeout

#### Rate Limit Exceeded
```
WARNING: Subscription rate limit exceeded
```
**Solution**: Reduce subscription rate, batch subscription requests

#### Message Queue Full
```
WARNING: Message queue full, dropping message
```
**Solution**: Increase queue size, process messages faster, optimize callbacks

### Debugging Steps

1. **Check Connection Status**
   ```python
   status = ws_client.get_connection_status()
   print(json.dumps(status, indent=2))
   ```

2. **Monitor Message Flow**
   ```python
   stats = ws_client.message_handler.get_statistics()
   print(f"Message rate: {stats['overall_message_rate']}")
   ```

3. **Verify Subscriptions**
   ```python
   status = ws_client.get_connection_status()
   print(f"Active subscriptions: {status['active_subscriptions']}")
   ```

4. **Check Authentication**
   ```python
   print(f"Authenticated: {ws_client.is_authenticated()}")
   balance_status = ws_client.get_balance_streaming_status()
   print(f"Token available: {balance_status['auth_token_available']}")
   ```

## Migration from Existing WebSocket

If migrating from the existing WebSocket implementation:

1. **Replace WebSocket Manager**
   ```python
   # Old
   from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager
   
   # New
   from src.websocket import KrakenWebSocketV2
   ```

2. **Update Callback Signatures**
   ```python
   # Old callback
   def handle_balance(balance_data):
       pass
   
   # New callback
   async def handle_balance(balance_updates: List[BalanceUpdate]):
       for balance in balance_updates:
           pass
   ```

3. **Update Data Access**
   ```python
   # Old
   balance = websocket_manager.get_balance('USDT')
   
   # New
   balance = ws_client.get_balance('USDT')
   ```

## Support and Contributing

For issues, questions, or contributions:

1. Check the integration example in `integration_example.py`
2. Review the existing bot integration patterns
3. Test with the provided example script
4. Check logs for detailed error information

## License

This WebSocket V2 implementation is part of the crypto trading bot project and follows the same licensing terms.