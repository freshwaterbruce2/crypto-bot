# Real-Time Balance Management System

## Overview
The Kraken Trading Bot now uses a real-time balance management system powered by WebSocket v2, completely eliminating the 5-minute cache that was causing trading failures.

## Key Changes

### 1. New Real-Time Balance Manager
- **File**: `src/trading/real_time_balance_manager.py`
- Subscribes to Kraken's authenticated `balances` WebSocket channel
- Receives instant balance updates after any trade, deposit, or withdrawal
- Zero caching - always returns current balance state
- Thread-safe with async locks

### 2. Enhanced Balance Manager Updates
- **File**: `src/trading/enhanced_balance_manager.py`
- Integrated with RealTimeBalanceManager when WebSocket is available
- Automatic fallback to REST API if WebSocket connection fails
- Removed all balance caching logic for real-time mode
- Maintains backward compatibility for systems without WebSocket

### 3. WebSocket Manager Enhancements
- **File**: `src/exchange/websocket_manager.py`
- Added support for authenticated private channels
- New methods: `register_private_callback()`, `connect_private_channels()`
- Handles balance update messages from Kraken v2 WebSocket
- Automatic reconnection for private channels

### 4. Bot Initialization Updates
- **File**: `src/core/bot.py`
- WebSocket manager is now passed to balance manager during initialization
- Private channels connect automatically on startup
- Graceful fallback if authentication fails

### 5. Trade Executor Optimization
- **File**: `src/trading/enhanced_trade_executor_with_assistants.py`
- Removed all force_refresh parameters
- Balance checks now use real-time data
- No more stale balance errors

## Configuration

Add to `config.json`:
```json
{
  "balance_management": {
    "use_realtime_websocket": true,
    "cache_duration_seconds": 0,
    "min_tradeable_balance": 2.50,
    "balance_check_before_trade": true,
    "websocket_channels": {
      "balances": {
        "enabled": true,
        "snapshot": true
      },
      "executions": {
        "enabled": true,
        "snap_orders": true,
        "snap_trades": false
      }
    }
  }
}
```

## How It Works

1. **Startup**: Bot connects to Kraken WebSocket v2
2. **Authentication**: Uses WebSocketAuthManager to get valid tokens
3. **Private Channel**: Connects to authenticated endpoint at `wss://ws-auth.kraken.com/v2`
4. **Balance Subscription**: Subscribes to `balances` channel with snapshot
5. **Real-Time Updates**: Receives balance changes instantly via WebSocket
6. **Trade Execution**: Balance checks always return current values

## Benefits

- **Instant Updates**: Balance updates in milliseconds, not minutes
- **No Cache Issues**: Eliminates "insufficient funds" errors from stale data
- **Accurate Trading**: Always knows exact available balance
- **Better Capital Management**: Real-time awareness of deployed capital
- **Improved Reliability**: Proper handling of all balance state changes

## Fallback Mechanism

If WebSocket fails:
1. System automatically falls back to REST API
2. Cache duration remains at 0 (always fetch fresh)
3. Rate limiting prevents excessive API calls
4. Bot continues operating with slightly higher latency

## Testing

Run the test suite:
```bash
pytest tests/test_real_time_balance_manager.py
```

## Monitoring

Check real-time balance status:
```python
# In bot console or logs
balance_info = balance_manager.get_cache_info()
print(balance_info['real_time_mode'])  # True if using WebSocket
print(balance_info['real_time_balance'])  # Connection status
```

## Troubleshooting

### WebSocket Not Connecting
- Check API credentials have WebSocket permissions
- Verify network allows WebSocket connections
- Check logs for authentication errors

### Falling Back to REST
- Normal if WebSocket temporarily unavailable
- Bot will continue working with REST API
- Monitor logs for reconnection attempts

### Balance Not Updating
- Check WebSocket connection status
- Verify private channels are connected
- Look for balance update messages in logs

## Future Enhancements

- Add order book depth via WebSocket
- Implement execution tracking via WebSocket
- Add WebSocket-based position monitoring
- Expand to other real-time data feeds