# Kraken REST API Client

Comprehensive async REST API client for Kraken with full integration support. Includes authentication, rate limiting, circuit breaker protection, and comprehensive error handling.

## Features

- **Full Async Support**: Built with `aiohttp` for high-performance async operations
- **Session Management**: Connection pooling and session management for optimal performance
- **Authentication**: Automatic signature generation and nonce management
- **Rate Limiting**: Kraken 2025 compliant rate limiting with penalty point tracking
- **Circuit Breaker**: Protection against cascading failures with automatic recovery
- **Error Handling**: Comprehensive error mapping and retry logic
- **Response Validation**: Pydantic models for type-safe response parsing
- **Performance Monitoring**: Built-in metrics and performance tracking
- **Thread Safety**: Safe for concurrent use across multiple coroutines

## Quick Start

```python
import asyncio
from src.api import KrakenRestClient

async def main():
    async with KrakenRestClient(
        api_key="your_api_key",
        private_key="your_private_key"
    ) as client:
        # Get ticker information
        ticker = await client.get_ticker_information("XBTUSD")
        print(f"BTC price: {ticker}")
        
        # Get account balance
        balance = await client.get_account_balance()
        print(f"Balance: {balance}")
        
        # Place a limit order (validation mode)
        order = await client.add_order(
            pair="XBTUSD",
            type="buy",
            ordertype="limit",
            volume="0.001",
            price="50000.00",
            validate=True  # Validation only
        )
        print(f"Order validated: {order}")

asyncio.run(main())
```

## Installation

The API client is part of the crypto trading bot project. Ensure you have all dependencies installed:

```bash
pip install aiohttp pydantic
```

## Configuration

### Environment Variables

Set your Kraken API credentials as environment variables:

```bash
export KRAKEN_API_KEY="your_api_key"
export KRAKEN_PRIVATE_KEY="your_private_key"
```

### Client Configuration

```python
from src.api import KrakenRestClient
from src.rate_limiting.kraken_rate_limiter import AccountTier

client = KrakenRestClient(
    api_key="your_api_key",
    private_key="your_private_key",
    account_tier=AccountTier.INTERMEDIATE,  # or PRO, STARTER
    enable_rate_limiting=True,
    enable_circuit_breaker=True,
    timeout=30.0,
    max_retries=3
)
```

## API Methods

### Public Endpoints

- `get_server_time()` - Get server time
- `get_system_status()` - Get system status
- `get_asset_info(asset=None)` - Get asset information
- `get_asset_pairs(pair=None, info="info")` - Get tradable asset pairs
- `get_ticker_information(pair)` - Get ticker information
- `get_ohlc_data(pair, interval=1, since=None)` - Get OHLC data
- `get_order_book(pair, count=100)` - Get order book
- `get_recent_trades(pair, since=None)` - Get recent trades

### Private Endpoints

- `get_account_balance()` - Get account balance
- `get_trade_balance(asset="ZUSD")` - Get trade balance
- `get_open_orders(trades=False, userref=None)` - Get open orders
- `get_closed_orders(...)` - Get closed orders
- `query_orders_info(txid, trades=False, userref=None)` - Query orders info
- `get_trades_history(...)` - Get trades history

### Trading Endpoints

- `add_order(pair, type, ordertype, volume, ...)` - Add order
- `edit_order(txid, pair, ...)` - Edit order
- `cancel_order(txid)` - Cancel order
- `cancel_all_orders()` - Cancel all orders
- `cancel_all_orders_after(timeout)` - Cancel all orders after timeout

### Utility Methods

- `get_websockets_token()` - Get WebSocket authentication token
- `health_check()` - Perform health check
- `get_metrics()` - Get performance metrics
- `get_status()` - Get comprehensive status

## Error Handling

The client provides comprehensive error handling with specific exception types:

```python
from src.api.exceptions import (
    KrakenAPIError, AuthenticationError, RateLimitError,
    NetworkError, ValidationError, InsufficientFundsError, OrderError
)

try:
    balance = await client.get_account_balance()
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after} seconds")
except NetworkError as e:
    print(f"Network error: {e}")
except KrakenAPIError as e:
    print(f"API error: {e.error_code} - {e.message}")
```

## Response Models

Responses are automatically parsed using Pydantic models for type safety:

```python
from src.api.response_models import BalanceResponse, TickerResponse

# Get balance with type safety
balance_data = await client.get_account_balance()
balance = BalanceResponse(**balance_data)

if balance.is_success:
    btc_balance = balance.get_balance('XBT')
    print(f"BTC Balance: {btc_balance}")

# Get ticker with type safety
ticker_data = await client.get_ticker_information("XBTUSD")
ticker = TickerResponse(**ticker_data)

if ticker.is_success and ticker.result:
    for pair, info in ticker.result.items():
        print(f"{pair}: Last={info.last_price}, Bid={info.bid_price}")
```

## Rate Limiting

The client automatically handles Kraken's 2025 rate limiting specifications:

- **Private endpoints**: 15 requests per minute
- **Public endpoints**: 20 requests per minute
- **Penalty point system**: Automatic tracking and cooldown
- **Queue management**: Requests are queued when limits are approached

```python
# Rate limiting is automatic, but you can configure priority
from src.rate_limiting.kraken_rate_limiter import RequestPriority

config = RequestConfig(priority=RequestPriority.HIGH)
balance = await client.get_account_balance()
```

## Circuit Breaker

The circuit breaker protects against cascading failures:

- **Failure Threshold**: 5 failures before opening
- **Recovery Timeout**: 30 seconds before attempting recovery
- **Automatic Recovery**: Gradual recovery with success threshold

```python
# Check circuit breaker status
status = client.get_status()
cb_status = status.get('metrics', {}).get('circuit_breaker_status')
print(f"Circuit breaker state: {cb_status['state']}")
```

## Performance Monitoring

Built-in metrics track performance and reliability:

```python
# Get comprehensive metrics
metrics = client.get_metrics()
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Avg response time: {metrics['avg_response_time']:.3f}s")
print(f"Total requests: {metrics['total_requests']}")

# Endpoint-specific metrics
endpoint_stats = metrics['endpoint_stats']
for endpoint, stats in endpoint_stats.items():
    print(f"{endpoint}: {stats['successes']}/{stats['requests']} successful")
```

## Health Checks

Comprehensive health checking for monitoring:

```python
# Perform health check
health = await client.health_check()
print(f"Overall status: {health['overall_status']}")

for check_name, result in health['checks'].items():
    print(f"{check_name}: {result['status']}")
```

## Integration Examples

### With Trading Bot

```python
class TradingBot:
    def __init__(self):
        self.client = KrakenRestClient(
            api_key=os.getenv('KRAKEN_API_KEY'),
            private_key=os.getenv('KRAKEN_PRIVATE_KEY'),
            account_tier=AccountTier.PRO
        )
    
    async def start(self):
        await self.client.start()
        
        # Verify connectivity and authentication
        if not await self.client.test_connectivity():
            raise RuntimeError("API not reachable")
        
        if not await self.client.test_authentication():
            raise RuntimeError("Authentication failed")
    
    async def get_portfolio_balance(self):
        balance = await self.client.get_account_balance()
        return BalanceResponse(**balance)
    
    async def place_order(self, pair, side, volume, price=None):
        return await self.client.add_order(
            pair=pair,
            type=side,
            ordertype="limit" if price else "market",
            volume=str(volume),
            price=str(price) if price else None
        )
```

### With Monitoring

```python
import asyncio
from datetime import datetime

async def monitor_client_health(client):
    while True:
        try:
            health = await client.health_check()
            metrics = client.get_metrics()
            
            print(f"{datetime.now()}: Health={health['overall_status']}, "
                  f"Success Rate={metrics['success_rate']:.2%}")
            
            if health['overall_status'] != 'healthy':
                # Alert or take corrective action
                await handle_unhealthy_client(health)
            
        except Exception as e:
            print(f"Health check failed: {e}")
        
        await asyncio.sleep(60)  # Check every minute
```

## Best Practices

### 1. Always use context managers

```python
# Good
async with KrakenRestClient(...) as client:
    await client.get_account_balance()

# Bad - resource leaks
client = KrakenRestClient(...)
await client.get_account_balance()
# Missing cleanup
```

### 2. Handle specific exceptions

```python
# Good
try:
    await client.add_order(...)
except InsufficientFundsError:
    # Handle insufficient funds specifically
    pass
except OrderError as e:
    # Handle order-specific errors
    pass

# Bad - too broad
try:
    await client.add_order(...)
except Exception:
    # Loses important error context
    pass
```

### 3. Monitor performance

```python
# Regularly check metrics
metrics = client.get_metrics()
if metrics['success_rate'] < 0.95:  # Less than 95% success
    # Investigate or alert
    pass

if metrics['avg_response_time'] > 5.0:  # More than 5s average
    # Performance issue
    pass
```

### 4. Use appropriate account tiers

```python
# For high-frequency trading
client = KrakenRestClient(
    ...,
    account_tier=AccountTier.PRO  # Higher rate limits
)

# For occasional trading
client = KrakenRestClient(
    ...,
    account_tier=AccountTier.INTERMEDIATE  # Standard limits
)
```

## Testing

Run the integration example to test all functionality:

```bash
# Set credentials (optional for public endpoints)
export KRAKEN_API_KEY="your_key"
export KRAKEN_PRIVATE_KEY="your_private_key"

# Run comprehensive test
python -m src.api.integration_example
```

## Architecture

```
src/api/
├── __init__.py              # Package exports
├── kraken_rest_client.py    # Main client class
├── endpoints.py             # Endpoint definitions
├── exceptions.py            # Custom exceptions
├── response_models.py       # Pydantic response models
├── integration_example.py   # Usage examples
└── README.md               # This file

Dependencies:
├── src/auth/                # Authentication system
├── src/rate_limiting/       # Rate limiting system
└── src/circuit_breaker/     # Circuit breaker system
```

## Troubleshooting

### Common Issues

**Authentication Errors**
- Verify API key and private key are correct
- Check API key permissions (Query, Trade, etc.)
- Ensure nonce is increasing (handled automatically)

**Rate Limiting**
- Check your account tier settings
- Monitor request frequency
- Use appropriate request priorities

**Network Errors**
- Check internet connectivity
- Verify Kraken API is accessible
- Check firewall/proxy settings

**Circuit Breaker Open**
- Wait for automatic recovery (30 seconds)
- Check underlying network/API issues
- Use `health_check()` to monitor status

### Debug Logging

Enable debug logging for detailed information:

```python
import logging
logging.getLogger('src.api').setLevel(logging.DEBUG)
logging.getLogger('src.auth').setLevel(logging.DEBUG)
logging.getLogger('src.rate_limiting').setLevel(logging.DEBUG)
```

## Contributing

When contributing to the API client:

1. Ensure all new endpoints are added to `endpoints.py`
2. Create corresponding Pydantic models in `response_models.py`
3. Add proper error handling and exception mapping
4. Update integration examples and tests
5. Maintain backward compatibility

## License

This API client is part of the crypto trading bot project and follows the same license terms.