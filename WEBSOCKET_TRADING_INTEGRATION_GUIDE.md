# WebSocket-Native Trading Engine Integration Guide

This guide explains how to integrate the WebSocket-native trading engine with your existing crypto trading bot for high-performance, low-latency order execution.

## Overview

The WebSocket-native trading engine eliminates REST API dependency for trading operations by using native WebSocket streams for:

- **Order Placement**: Real-time order submission via WebSocket
- **Execution Tracking**: Live order status and fill notifications
- **Order Management**: WebSocket-based cancellation and modification
- **Performance Optimization**: Reduced latency and improved throughput

## Quick Integration

### 1. Basic Integration (Minimal Changes)

Add WebSocket trading to your existing bot with minimal code changes:

```python
from src.integration.websocket_trading_integration import setup_websocket_trading

async def initialize_bot():
    # Your existing bot initialization
    bot = CryptoTradingBot()
    await bot.initialize()
    
    # Add WebSocket trading integration
    websocket_integration = await setup_websocket_trading(bot)
    
    if websocket_integration:
        print("✅ WebSocket trading enabled")
        # Your bot.trade_executor now uses WebSocket with REST fallback
    else:
        print("⚠️ Using REST-only trading")
    
    return bot
```

### 2. Advanced Integration (Custom Configuration)

For more control over WebSocket trading behavior:

```python
from src.integration.websocket_trading_integration import (
    setup_websocket_trading,
    create_websocket_trading_config
)

async def initialize_advanced_bot():
    bot = CryptoTradingBot()
    await bot.initialize()
    
    # Create custom WebSocket configuration
    ws_config = create_websocket_trading_config(
        enabled=True,
        prefer_websocket=True,
        max_concurrent_orders=10,
        order_timeout_seconds=60,
        auto_fallback_on_failure=True,
        performance_monitoring=True
    )
    
    # Set up with custom config
    websocket_integration = await setup_websocket_trading(bot, ws_config)
    
    return bot, websocket_integration
```

## Key Features

### 1. Seamless Fallback
The integration automatically falls back to REST API when WebSocket is unavailable:

```python
# Your existing trade execution code works unchanged
result = await bot.trade_executor.execute_trade({
    'symbol': 'SHIB/USDT',
    'side': 'buy',
    'amount': 5.0,
    'signal': {'strategy': 'micro_scalper', 'confidence': 85}
})
# Uses WebSocket if available, REST otherwise
```

### 2. Real-time Order Tracking
Monitor order execution in real-time:

```python
def setup_execution_monitoring(bot):
    if hasattr(bot, 'websocket_trading_engine'):
        bot.websocket_trading_engine.add_execution_callback(on_execution)

async def on_execution(execution_update):
    print(f"🎯 Execution: {execution_update.symbol} "
          f"{execution_update.side} {execution_update.amount} "
          f"@ ${execution_update.price}")
```

### 3. Direct WebSocket Operations
For advanced use cases, access the WebSocket engine directly:

```python
# Direct WebSocket order placement
engine = bot.websocket_trading_engine

# Market order
order = await engine.place_buy_order("SHIB/USDT", "100000")

# Limit order with IOC
order = await engine.place_sell_order(
    "SHIB/USDT", 
    "50000", 
    price="0.000025",
    order_type=OrderType.IOC
)

# Order management
await engine.cancel_order(order.id)
status = await engine.get_order_status(order.id)
```

## Integration Points

### 1. Enhanced Trade Executor Integration

The WebSocket engine integrates seamlessly with your existing `enhanced_trade_executor_with_assistants.py`:

```python
# Before integration
result = await enhanced_trade_executor.execute_trade(params)

# After integration (same code, enhanced performance)
result = await enhanced_trade_executor.execute_trade(params)
# Now uses WebSocket with automatic REST fallback
```

### 2. Balance Manager Integration

WebSocket executions automatically update your balance manager:

```python
# Balance updates happen automatically on WebSocket executions
# No code changes needed - existing balance logic works unchanged
balance = await bot.balance_manager.get_usdt_balance()
```

### 3. Strategy Manager Integration

Your existing strategy manager works without changes:

```python
# Strategies generate signals as usual
signal = await strategy_manager.generate_signal(symbol)

# Execution automatically uses WebSocket when available
result = await bot.execute_signal(signal)
```

## Performance Benefits

### Latency Improvement
- **WebSocket**: ~50-200ms order execution
- **REST API**: ~200-800ms order execution
- **Improvement**: Up to 75% faster execution

### Throughput Enhancement
- **Concurrent Orders**: Support for multiple simultaneous orders
- **Real-time Updates**: Instant execution notifications
- **Reduced API Calls**: Single connection for all order operations

### Example Performance Comparison

```python
async def compare_performance():
    # Force WebSocket execution
    await integration.force_websocket_preference(True)
    ws_start = time.time()
    ws_result = await bot.trade_executor.execute_trade(test_params)
    ws_time = (time.time() - ws_start) * 1000
    
    # Force REST execution
    await integration.force_websocket_preference(False)
    rest_start = time.time()
    rest_result = await bot.trade_executor.execute_trade(test_params)
    rest_time = (time.time() - rest_start) * 1000
    
    improvement = ((rest_time - ws_time) / rest_time) * 100
    print(f"WebSocket: {ws_time:.1f}ms, REST: {rest_time:.1f}ms, "
          f"Improvement: {improvement:.1f}%")
```

## Configuration Options

### WebSocketTradingConfig Parameters

```python
config = WebSocketTradingConfig(
    enabled=True,                    # Enable WebSocket trading
    prefer_websocket=True,           # Prefer WebSocket over REST
    max_concurrent_orders=10,        # Maximum simultaneous orders
    order_timeout_seconds=60,        # Order timeout duration
    auto_fallback_on_failure=True,   # Auto-fallback to REST on failures
    websocket_retry_attempts=3,      # Retry attempts for WebSocket init
    performance_monitoring=True      # Enable performance tracking
)
```

### Runtime Configuration

```python
# Change preferences at runtime
await integration.force_websocket_preference(False)  # Use REST
await integration.force_websocket_preference(True)   # Use WebSocket

# Retry WebSocket initialization
await integration.retry_websocket_initialization()

# Get detailed status
status = integration.get_status()
print(f"WebSocket Success Rate: {status['performance_metrics']['websocket_success_rate']:.2%}")
```

## Monitoring and Metrics

### Integration Status

```python
status = integration.get_status()

# Integration health
print(f"WebSocket Available: {status['integration_status']['websocket_available']}")
print(f"Integration Active: {status['integration_status']['integration_active']}")

# Performance metrics
metrics = status['performance_metrics']
print(f"WebSocket Trades: {metrics['websocket_trades']}")
print(f"REST Trades: {metrics['rest_trades']}")
print(f"Success Rate: {metrics['websocket_success_rate']:.2%}")
```

### Engine Metrics

```python
if bot.websocket_trading_engine:
    metrics = bot.websocket_trading_engine.get_metrics()
    print(f"Orders Placed: {metrics['orders_placed']}")
    print(f"Orders Filled: {metrics['orders_filled']}")
    print(f"Active Orders: {metrics['active_orders_count']}")
    print(f"Avg Latency: {metrics['websocket_latency_ms']:.1f}ms")
```

## Error Handling and Fallback

### Automatic Fallback Scenarios

The system automatically falls back to REST API when:

1. **WebSocket Connection Issues**: Connection lost or unhealthy
2. **Authentication Problems**: Token expired or invalid
3. **Order Execution Failures**: WebSocket order placement fails
4. **Performance Degradation**: High error rates or latency

### Manual Fallback Control

```python
# Force REST-only mode temporarily
await integration.force_websocket_preference(False)

# Re-enable WebSocket after issue resolution
await integration.force_websocket_preference(True)

# Check if fallback is active
status = integration.get_status()
fallback_events = status['performance_metrics']['fallback_events']
print(f"Fallback events: {fallback_events}")
```

## Best Practices

### 1. Initialization Order

```python
async def proper_initialization():
    # 1. Initialize bot core components
    bot = CryptoTradingBot()
    await bot.initialize()
    
    # 2. Ensure WebSocket connection is stable
    if bot.websocket_manager:
        await bot.websocket_manager.connect()
        await asyncio.sleep(2)  # Allow connection to stabilize
    
    # 3. Set up WebSocket trading integration
    integration = await setup_websocket_trading(bot)
    
    return bot, integration
```

### 2. Error Handling

```python
async def robust_trade_execution():
    try:
        result = await bot.trade_executor.execute_trade(params)
        
        if result.get('success'):
            execution_method = result.get('order', {}).get('execution_method', 'unknown')
            print(f"✅ Trade executed via {execution_method}")
        else:
            print(f"❌ Trade failed: {result.get('error')}")
            
    except Exception as e:
        print(f"🚨 Trade execution error: {e}")
        # Integration handles fallback automatically
```

### 3. Performance Monitoring

```python
async def monitor_performance():
    while True:
        await asyncio.sleep(60)  # Check every minute
        
        status = integration.get_status()
        success_rate = status['performance_metrics']['websocket_success_rate']
        
        if success_rate < 0.8:  # Below 80% success rate
            print("⚠️ WebSocket performance degraded, investigating...")
            # Integration will auto-fallback if configured
```

## Migration from REST-Only Trading

### Step 1: Test Integration
```python
# Add WebSocket integration alongside existing REST
websocket_integration = await setup_websocket_trading(bot)
# Existing functionality unchanged
```

### Step 2: Gradual Rollout
```python
# Start with WebSocket preference disabled
config = create_websocket_trading_config(prefer_websocket=False)
integration = await setup_websocket_trading(bot, config)

# Enable gradually
await integration.force_websocket_preference(True)
```

### Step 3: Monitor and Optimize
```python
# Track performance improvement
metrics = integration.get_status()['performance_metrics']
improvement = metrics['websocket_success_rate']
print(f"WebSocket success rate: {improvement:.2%}")
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check API key WebSocket permissions
   - Verify network connectivity
   - Ensure authentication token is valid

2. **Orders Not Executing via WebSocket**
   - Check order validation (size, price, symbol)
   - Verify account has sufficient balance
   - Check rate limits and API tier restrictions

3. **Performance Not Improved**
   - Verify WebSocket preference is enabled
   - Check if fallback to REST is occurring
   - Monitor network latency and stability

### Debug Mode

```python
# Enable detailed logging
import logging
logging.getLogger('websocket_trading').setLevel(logging.DEBUG)

# Check integration status
status = integration.get_status()
print(json.dumps(status, indent=2))

# Verify WebSocket engine availability
if bot.websocket_trading_engine:
    print("✅ WebSocket engine available")
    print(f"Order execution ready: {bot.websocket_trading_engine.order_execution_ready}")
else:
    print("❌ WebSocket engine not available")
```

## Example Complete Integration

See `examples/websocket_trading_example.py` for a complete working example showing:

- Bot initialization with WebSocket trading
- Order placement via WebSocket
- Performance comparison with REST
- Order management and lifecycle
- Real-time execution monitoring
- Integration status reporting

## Next Steps

1. **Test Integration**: Start with the basic integration in a test environment
2. **Monitor Performance**: Use the built-in metrics to track improvements
3. **Optimize Configuration**: Adjust settings based on your trading patterns
4. **Implement Monitoring**: Set up alerts for WebSocket health and performance
5. **Scale Usage**: Gradually increase WebSocket usage as confidence grows

The WebSocket-native trading engine provides significant performance improvements while maintaining full compatibility with your existing trading bot architecture. The seamless fallback ensures reliability, while the real-time capabilities enable more sophisticated trading strategies.