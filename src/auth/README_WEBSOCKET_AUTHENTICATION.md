# Enhanced WebSocket Authentication Manager

## Overview

The Enhanced WebSocket Authentication Manager is a comprehensive solution for Kraken WebSocket V2 authentication that solves critical issues preventing reliable trading bot operation:

- **"EAPI:Invalid nonce" errors** that cause connection failures
- **Token expiry handling** with proactive refresh (13-minute intervals)
- **Circuit breaker protection** against authentication failures
- **Exponential backoff** for failed requests
- **Thread-safe token lifecycle management**
- **Automatic error recovery** with fallback mechanisms

## Key Features

### 🔧 Proactive Token Management
- Generates WebSocket tokens via REST API `/private/GetWebSocketsToken`
- Refreshes tokens every 13 minutes (before 15-minute expiry)
- Handles token expiry gracefully with automatic refresh
- Stores token state persistently across restarts

### 🛡️ Authentication Flow
- Initial token generation and validation
- WebSocket connection authentication with retry logic
- Private channel subscription with authenticated tokens
- Token refresh without connection interruption

### 🔄 Error Recovery
- Handles "EAPI:Invalid nonce" errors automatically
- Implements exponential backoff for failed requests
- Provides graceful fallback when token generation fails
- Circuit breaker integration for authentication failures

### 🚀 Integration Features
- Works seamlessly with existing REST API authentication
- Coordinates with websocket_manager_v2.py
- Thread-safe token management with async/await patterns
- Comprehensive monitoring and status reporting

## Installation & Setup

### 1. Import the Authentication Manager

```python
from src.auth.websocket_authentication_manager import (
    WebSocketAuthenticationManager,
    WebSocketAuthenticationError,
    websocket_auth_context
)
```

### 2. Initialize with WebSocket Manager

```python
from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager

# Create WebSocket manager
websocket_manager = KrakenProWebSocketManager(
    exchange_client=your_exchange_client,
    symbols=['SHIB/USDT', 'MATIC/USDT', 'AI16Z/USDT'],
    visual_mode=True
)

# Initialize enhanced authentication
auth_success = await websocket_manager.initialize_authentication(
    api_key="your_kraken_api_key",
    private_key="your_kraken_private_key"
)

if auth_success:
    # Connect with enhanced authentication
    await websocket_manager.connect()
```

### 3. Direct Usage (Advanced)

```python
# Create authentication manager directly
auth_manager = WebSocketAuthenticationManager(
    exchange_client=exchange_client,
    api_key="your_api_key",
    private_key="your_private_key",
    enable_debug=True
)

# Start authentication manager
await auth_manager.start()

# Get WebSocket token
token = await auth_manager.get_websocket_token()

# Use token for WebSocket connection
# ...

# Stop when done
await auth_manager.stop()
```

## Usage Examples

### Basic Integration

```python
import asyncio
from src.auth.websocket_authentication_manager import WebSocketAuthenticationManager
from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager

async def setup_enhanced_websocket():
    # Initialize WebSocket manager
    ws_manager = KrakenProWebSocketManager(
        exchange_client=exchange,
        symbols=['SHIB/USDT', 'MATIC/USDT'],
        visual_mode=True
    )
    
    # Initialize enhanced authentication
    success = await ws_manager.initialize_authentication(
        api_key="your_api_key",
        private_key="your_private_key"
    )
    
    if success:
        # Connect WebSocket with enhanced auth
        await ws_manager.connect()
        
        # Monitor authentication status
        auth_status = ws_manager.get_authentication_status()
        print(f"Auth Status: {auth_status}")
        
        return ws_manager
    else:
        raise Exception("Failed to initialize enhanced authentication")

# Run setup
ws_manager = await setup_enhanced_websocket()
```

### Context Manager Usage

```python
from src.auth.websocket_authentication_manager import websocket_auth_context

async def use_context_manager():
    async with websocket_auth_context(
        exchange_client=exchange,
        api_key="your_api_key",
        private_key="your_private_key",
        enable_debug=True
    ) as auth_manager:
        
        # Get token
        token = await auth_manager.get_websocket_token()
        
        # Use token for WebSocket operations
        # Authentication manager automatically cleaned up on exit
```

### Error Handling

```python
from src.auth.websocket_authentication_manager import (
    WebSocketAuthenticationError,
    TokenExpiredError,
    NonceValidationError,
    CircuitBreakerOpenError
)

try:
    token = await auth_manager.get_websocket_token()
except TokenExpiredError:
    # Handle token expiry
    token = await auth_manager.handle_token_expiry()
except NonceValidationError:
    # Handle nonce errors
    token = await auth_manager.handle_authentication_error("EAPI:Invalid nonce")
except CircuitBreakerOpenError:
    # Circuit breaker is open, wait before retry
    await asyncio.sleep(60)
    auth_manager.reset_circuit_breaker()
except WebSocketAuthenticationError as e:
    # Handle other authentication errors
    print(f"Authentication error: {e}")
```

## Authentication Status Monitoring

### Get Comprehensive Status

```python
# Get detailed authentication status
status = websocket_manager.get_authentication_status()

print(f"Enhanced Auth Available: {status['enhanced_auth_manager_available']}")
print(f"Token Valid: {status['enhanced_authentication']['has_valid_token']}")
print(f"Circuit Breaker Open: {status['enhanced_authentication']['circuit_breaker_open']}")
print(f"Successful Auths: {status['enhanced_authentication']['statistics']['successful_auths']}")
print(f"Auth Failures: {status['enhanced_authentication']['statistics']['auth_failures']}")

# Get token information (without exposing sensitive data)
token_info = status.get('enhanced_token_info', {})
print(f"Token Expires In: {token_info.get('expires_in_seconds', 0)} seconds")
print(f"Token Age: {token_info.get('age_seconds', 0)} seconds")
print(f"Needs Refresh: {token_info.get('needs_refresh', True)}")
```

### Monitor Balance Streaming

```python
# Get balance streaming status including authentication
balance_status = websocket_manager.get_balance_streaming_status()

print(f"WebSocket Connected: {balance_status['websocket_connected']}")
print(f"WebSocket Healthy: {balance_status['websocket_healthy']}")
print(f"Enhanced Auth Available: {balance_status['enhanced_auth_available']}")
print(f"Balance Data Count: {balance_status['balance_data_count']}")
print(f"USDT Total: ${balance_status['usdt_total_all_variants']:.2f}")
```

## Configuration Options

### Authentication Manager Settings

```python
auth_manager = WebSocketAuthenticationManager(
    exchange_client=exchange,
    api_key="your_api_key",
    private_key="your_private_key",
    storage_dir="/path/to/token/storage",  # Optional: custom storage directory
    enable_debug=True  # Enable detailed logging
)

# Customize timeouts and intervals
auth_manager.token_lifetime_seconds = 15 * 60  # 15 minutes (Kraken default)
auth_manager.refresh_interval_seconds = 13 * 60  # 13 minutes (2 min buffer)
auth_manager.max_retry_attempts = 3
auth_manager.base_retry_delay = 1.0
auth_manager.max_retry_delay = 30.0

# Customize circuit breaker
auth_manager.circuit_breaker_threshold = 5  # failures before tripping
auth_manager.circuit_breaker_timeout = 300  # 5 minutes timeout
```

## Troubleshooting

### Common Issues

1. **"EAPI:Invalid nonce" Errors**
   ```python
   # The enhanced auth manager handles this automatically
   # But you can also handle manually:
   recovery_token = await auth_manager.handle_authentication_error("EAPI:Invalid nonce")
   ```

2. **Token Expiry Issues**
   ```python
   # Tokens are refreshed automatically every 13 minutes
   # Force refresh if needed:
   success = await auth_manager.force_token_refresh()
   ```

3. **Circuit Breaker Tripped**
   ```python
   # Check circuit breaker status
   status = auth_manager.get_authentication_status()
   if status['circuit_breaker_open']:
       # Wait for timeout or manually reset
       auth_manager.reset_circuit_breaker()
   ```

4. **Connection Failures**
   ```python
   # Check comprehensive status
   auth_status = websocket_manager.get_authentication_status()
   balance_status = websocket_manager.get_balance_streaming_status()
   
   # Look for specific issues in the status data
   ```

### Debug Logging

Enable debug logging to see detailed authentication flow:

```python
import logging

# Enable debug logging
logging.getLogger('src.auth.websocket_authentication_manager').setLevel(logging.DEBUG)
logging.getLogger('src.exchange.websocket_manager_v2').setLevel(logging.DEBUG)

# Or enable during initialization
auth_manager = WebSocketAuthenticationManager(
    # ... other params ...
    enable_debug=True
)
```

### Status Check Script

```python
async def check_auth_health():
    """Check authentication system health"""
    if not websocket_manager:
        return "WebSocket manager not initialized"
    
    auth_status = websocket_manager.get_authentication_status()
    
    issues = []
    
    if not auth_status.get('enhanced_auth_manager_available'):
        issues.append("Enhanced authentication not available")
    
    if auth_status.get('enhanced_authentication', {}).get('circuit_breaker_open'):
        issues.append("Circuit breaker is open")
    
    if not auth_status.get('enhanced_authentication', {}).get('has_valid_token'):
        issues.append("No valid authentication token")
    
    token_info = auth_status.get('enhanced_token_info', {})
    if token_info.get('expires_in_seconds', 0) < 120:
        issues.append("Token expires soon (< 2 minutes)")
    
    if issues:
        return f"Issues found: {', '.join(issues)}"
    else:
        return "Authentication system healthy"

# Run health check
health_status = await check_auth_health()
print(f"Health Status: {health_status}")
```

## Integration with Existing Code

The enhanced authentication manager is designed to integrate seamlessly with existing code:

### 1. Minimal Changes Required

```python
# Before (legacy approach)
websocket_manager = KrakenProWebSocketManager(exchange, symbols)
await websocket_manager.connect()

# After (enhanced authentication)
websocket_manager = KrakenProWebSocketManager(exchange, symbols)
await websocket_manager.initialize_authentication(api_key, private_key)
await websocket_manager.connect()
```

### 2. Backward Compatibility

The system maintains backward compatibility with existing authentication methods while providing enhanced capabilities when available.

### 3. Gradual Migration

You can gradually migrate to enhanced authentication:
- Initialize enhanced auth where possible
- Fall back to legacy methods when needed
- Monitor authentication status to verify improvements

## Security Considerations

1. **Token Storage**: Tokens are stored securely with proper file permissions
2. **No Token Logging**: Sensitive token data is never logged in full
3. **Secure Cleanup**: Tokens are properly cleaned up on shutdown
4. **Rate Limiting**: Built-in rate limiting prevents API abuse
5. **Circuit Breaker**: Protects against authentication storms

## Performance Impact

The enhanced authentication manager is designed for minimal performance impact:

- **Lazy Loading**: Authentication only initializes when needed
- **Efficient Caching**: Tokens are cached and reused appropriately
- **Background Refresh**: Token refresh happens in background
- **Minimal Overhead**: ~1-2ms additional latency per authenticated request

## Support

For issues or questions about the enhanced authentication system:

1. Check the debug logs for detailed error information
2. Use the status monitoring methods to diagnose issues
3. Refer to the integration example for proper usage patterns
4. Consider the troubleshooting section for common problems

The enhanced authentication manager provides a robust, production-ready solution for WebSocket authentication that will significantly improve the reliability of your trading bot's connection to Kraken's WebSocket V2 API.