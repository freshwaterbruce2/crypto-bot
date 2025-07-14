# Kraken WebSocket v2 Implementation Guide

## Overview

This document describes the updated Kraken WebSocket v2 implementation with automatic token management, proper error handling, and order placement capabilities.

## Key Components

### 1. WebSocket Authentication Manager (`websocket_auth_manager.py`)

The authentication manager handles all token-related operations:

- **Automatic Token Refresh**: Refreshes tokens every 10 minutes (configurable)
- **Token Validation**: Checks token age and validity before use
- **Thread-Safe Operations**: Uses async locks to prevent race conditions
- **Error Recovery**: Implements exponential backoff for failed refreshes
- **Statistics Tracking**: Monitors refresh count and failures

#### Usage Example:
```python
# Initialize auth manager
auth_manager = WebSocketAuthManager(rest_client, refresh_interval=600)
await auth_manager.initialize()

# Get valid token (auto-refreshes if needed)
token = await auth_manager.get_valid_token()

# Check token info
info = auth_manager.get_token_info()
print(f"Token age: {info['age_seconds']}s")
```

### 2. WebSocket Manager Updates

The WebSocket manager now includes:

- **Dual Connection Architecture**: Separate connections for public and private channels
- **Integrated Auth Manager**: Automatic token management for authenticated operations
- **Order Placement via WebSocket**: New `add_order()` method for v2 API
- **Improved Error Handling**: Exponential backoff and circuit breaker patterns

#### Connection URLs:
- Public: `wss://ws.kraken.com/v2`
- Private: `wss://ws-auth.kraken.com/v2`

### 3. Order Placement

Place orders directly via WebSocket for lower latency:

```python
# Place a limit order
result = await ws_manager.add_order({
    "order_type": "limit",
    "side": "buy",
    "order_qty": 1.25,
    "symbol": "BTC/USD",
    "limit_price": 37500,
    "time_in_force": "gtc",
    "post_only": True
})

if result['success']:
    print(f"Order placed: {result['result']}")
else:
    print(f"Order failed: {result['error']}")
```

## Configuration

Update your `config.json`:

```json
{
  "kraken": {
    "websocket_settings": {
      "public_url": "wss://ws.kraken.com/v2",
      "private_url": "wss://ws-auth.kraken.com/v2",
      "token_refresh_interval": 600,
      "ping_interval": 20,
      "ping_timeout": 10,
      "reconnect_interval": 5,
      "max_reconnect_attempts": 10,
      "enable_auth_manager": true
    }
  }
}
```

## Error Handling

### Rate Limit Errors
- Implements exponential backoff
- Respects Kraken's 5-second minimum reconnection interval
- Tracks rate limit usage via ratecounter subscription

### Connection Failures
- Automatic reconnection with backoff
- DNS pre-resolution for stability
- Circuit breaker after repeated failures

### Token Expiry
- Proactive refresh before 15-minute expiry
- Maintains token validity with active subscriptions
- Fallback to REST API for new tokens

## Testing

Run the test suite:

```bash
# Run all WebSocket tests
pytest tests/test_websocket_v2.py -v

# Run specific test
pytest tests/test_websocket_v2.py::TestWebSocketManager::test_add_order_success -v

# Run with coverage
pytest tests/test_websocket_v2.py --cov=src.exchange --cov-report=html
```

## Migration Notes

### From v1 to v2

1. **Token Management**: No longer need manual token refresh
2. **Order Format**: Use v2 JSON schema (see examples)
3. **Connection URLs**: Update to v2 endpoints
4. **Error Responses**: Different error format in v2

### Breaking Changes

- `auth_token` parameter deprecated - use `rest_client` instead
- Order placement format changed
- Error responses have different structure

## Troubleshooting

### Common Issues

1. **"Authentication manager not initialized"**
   - Ensure REST client is passed to WebSocket manager
   - Check that `enable_auth_manager` is true in config

2. **"Token expired" errors**
   - Verify REST API credentials are valid
   - Check network connectivity to Kraken API
   - Ensure system time is synchronized

3. **Order placement timeouts**
   - Check private WebSocket connection status
   - Verify token is valid
   - Ensure order parameters match Kraken requirements

### Debug Logging

Enable debug logging for detailed diagnostics:

```python
import logging
logging.getLogger('src.exchange.websocket_manager').setLevel(logging.DEBUG)
logging.getLogger('src.exchange.websocket_auth_manager').setLevel(logging.DEBUG)
```

## Best Practices

1. **Always Initialize Auth Manager**: Call `await ws_manager.connect()` before operations
2. **Handle Connection Loss**: Implement reconnection logic in your application
3. **Monitor Token Age**: Use `auth_manager.get_token_info()` for monitoring
4. **Graceful Shutdown**: Always call `await ws_manager.disconnect()` on exit
5. **Error Recovery**: Implement retry logic for transient failures

## API Reference

### WebSocketAuthManager

- `initialize()` - Initialize and get first token
- `get_valid_token()` - Get current token or refresh if needed
- `refresh_token()` - Force token refresh
- `get_token_info()` - Get token statistics
- `shutdown()` - Clean shutdown

### WebSocketManager

- `connect()` - Connect to public WebSocket
- `connect_private_channels()` - Connect to private WebSocket
- `add_order(params)` - Place order via WebSocket
- `disconnect()` - Disconnect all connections
- `ensure_valid_token()` - Get valid token (internal)

## Performance Considerations

- Token refresh adds ~100-500ms latency (once per 10 minutes)
- WebSocket orders are 50-200ms faster than REST
- Maintain persistent connections for best performance
- Use connection pooling for multiple strategies

## Security Notes

- Tokens are never logged or persisted
- All token operations use secure memory practices
- Network traffic uses TLS 1.2+
- Implements rate limiting to prevent abuse