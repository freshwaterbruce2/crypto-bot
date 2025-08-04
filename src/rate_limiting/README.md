# Kraken 2025 Rate Limiting System

A comprehensive, production-ready rate limiting system designed specifically for Kraken's 2025 API specifications. This system provides advanced rate limiting capabilities with token bucket algorithms, sliding window tracking, penalty point management, and circuit breaker protection.

## 🎯 Key Features

### API Compliance
- **Private Endpoints**: 15 requests per minute compliance
- **Public Endpoints**: 20 requests per minute compliance  
- **Penalty Point System**: Tier-based limits with automatic decay
- **Age-based Penalties**: Smart penalty calculation for order modifications

### Advanced Algorithms
- **Token Bucket**: Precise burst handling with configurable refill rates
- **Sliding Window**: Accurate rate tracking over time periods
- **Priority Queue**: Request prioritization with multiple strategies
- **Circuit Breaker**: Automatic protection against cascade failures

### High-Performance Features
- **Async/Await Support**: Non-blocking operation for high-frequency trading
- **Per-API-Key Tracking**: Individual rate limit tracking
- **Automatic Recovery**: Self-healing with exponential backoff
- **Comprehensive Monitoring**: Detailed metrics and logging

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from src.rate_limiting import KrakenRateLimiter2025, RequestPriority
from src.rate_limiting.rate_limit_config import AccountTier

async def main():
    # Initialize rate limiter
    rate_limiter = KrakenRateLimiter2025(
        account_tier=AccountTier.PRO,
        api_key="your_api_key",
        enable_queue=True,
        enable_circuit_breaker=True
    )
    
    # Start the rate limiter
    await rate_limiter.start()
    
    try:
        # Check if request can proceed
        can_proceed, reason, wait_time = await rate_limiter.check_rate_limit("Balance")
        
        if can_proceed:
            # Make API call
            result = await your_api_call()
        else:
            print(f"Rate limited: {reason}, wait {wait_time}s")
        
        # Or use automatic waiting
        async def api_call():
            return await your_kraken_api.get_balance()
        
        result = await rate_limiter.execute_with_rate_limit(
            endpoint="Balance",
            func=api_call,
            priority=RequestPriority.NORMAL,
            timeout_seconds=30.0
        )
        
    finally:
        await rate_limiter.stop()

asyncio.run(main())
```

### Trading Integration Example

```python
class TradingBot:
    def __init__(self):
        self.rate_limiter = KrakenRateLimiter2025(
            account_tier=AccountTier.PRO,
            enable_queue=True,
            enable_circuit_breaker=True
        )
    
    async def place_order(self, symbol, side, amount, price):
        """Place order with automatic rate limiting."""
        
        async def create_order():
            return await self.exchange.create_order(symbol, side, amount, price)
        
        # Execute with high priority and automatic rate limiting
        order = await self.rate_limiter.execute_with_rate_limit(
            endpoint="AddOrder",
            func=create_order,
            priority=RequestPriority.HIGH,
            timeout_seconds=30.0
        )
        
        # Track order for age-based penalties
        self.rate_limiter.record_order_time(order['id'])
        
        return order
    
    async def cancel_order(self, order_id, symbol):
        """Cancel order with age-based penalty calculation."""
        
        # Get order age for penalty calculation
        order_age = self.rate_limiter.get_order_age(order_id)
        
        async def cancel_request():
            return await self.exchange.cancel_order(order_id, symbol)
        
        result = await self.rate_limiter.execute_with_rate_limit(
            endpoint="CancelOrder",
            func=cancel_request,
            order_age_seconds=order_age,
            priority=RequestPriority.HIGH
        )
        
        # Clean up tracking
        self.rate_limiter.remove_order_time(order_id)
        
        return result
```

## 📊 Account Tier Configuration

The system supports all Kraken account tiers with appropriate limits:

### Starter Tier
- **Private Limit**: 15 requests/minute
- **Public Limit**: 20 requests/minute
- **Max Penalty Points**: 60
- **Decay Rate**: 0.33 points/second

### Intermediate Tier
- **Private Limit**: 15 requests/minute
- **Public Limit**: 20 requests/minute
- **Max Penalty Points**: 125
- **Decay Rate**: 2.34 points/second

### Pro Tier
- **Private Limit**: 15 requests/minute
- **Public Limit**: 20 requests/minute
- **Max Penalty Points**: 180
- **Decay Rate**: 3.75 points/second

## ⚡ Penalty Point System

### Base Penalties
- **AddOrder**: 1 point
- **Balance**: 1 point
- **Ticker**: 0 points (public endpoint)
- **Heavy Endpoints** (Ledgers, TradesHistory): 2 points

### Age-based Penalties

#### Order Cancellation (CancelOrder)
- **< 5 seconds**: +8 points
- **< 10 seconds**: +6 points
- **< 15 seconds**: +5 points
- **< 45 seconds**: +4 points
- **< 90 seconds**: +2 points
- **< 300 seconds**: +1 point
- **> 300 seconds**: 0 points

#### Order Amendment (AmendOrder)
- **< 5 seconds**: +3 points
- **< 10 seconds**: +2 points
- **< 15 seconds**: +1 point
- **> 15 seconds**: 0 points

#### Order Editing (EditOrder)
- **< 5 seconds**: +6 points
- **< 10 seconds**: +5 points
- **< 15 seconds**: +4 points
- **< 45 seconds**: +2 points
- **< 90 seconds**: +1 point
- **> 90 seconds**: 0 points

## 🔧 Configuration Options

### Rate Limiter Configuration

```python
rate_limiter = KrakenRateLimiter2025(
    account_tier=AccountTier.PRO,           # Account tier
    api_key="your_api_key",                 # Optional API key for tracking
    enable_queue=True,                      # Enable request queuing
    enable_circuit_breaker=True,            # Enable circuit breaker
    persistence_path="rate_limiter.json"    # State persistence file
)
```

### Queue Configuration

```python
from src.rate_limiting import RequestQueue, RequestPriority, QueueStrategy

queue = RequestQueue(
    max_size=1000,                          # Maximum queue size
    strategy=QueueStrategy.PRIORITY_FIFO,   # Queue processing strategy
    cleanup_interval=30.0,                  # Cleanup interval in seconds
    max_age_seconds=300.0                   # Maximum request age
)
```

### Circuit Breaker Configuration

```python
circuit_breaker = CircuitBreaker(
    failure_threshold=5,        # Failures before opening
    recovery_timeout=30.0,      # Recovery timeout in seconds
    success_threshold=3         # Successes needed to close
)
```

## 📈 Monitoring and Metrics

### Get Status Information

```python
# Get comprehensive status
status = await rate_limiter.get_status()

print(f"Account Tier: {status['account_tier']}")
print(f"Penalty Points: {status['penalty_tracker']['current_points']}")
print(f"Token Buckets: {status['token_buckets']}")
print(f"Circuit Breaker: {status['circuit_breaker']['state']}")
```

### Statistics Tracking

```python
# Get endpoint-specific statistics
endpoint_stats = rate_limiter.get_endpoint_stats("AddOrder")
print(f"Requests: {endpoint_stats['requests']}")
print(f"Blocks: {endpoint_stats['blocks']}")
print(f"Average Time: {endpoint_stats['average_time']}")

# Get overall statistics
overall_stats = rate_limiter.get_endpoint_stats()
```

## 🛠️ Advanced Features

### Priority Queue Management

```python
from src.rate_limiting import RequestPriority

# Different priority levels
priorities = [
    RequestPriority.CRITICAL,    # Emergency orders, liquidations
    RequestPriority.HIGH,        # Trade execution, order management
    RequestPriority.NORMAL,      # Regular trading operations
    RequestPriority.LOW,         # Data fetching, analysis
    RequestPriority.BACKGROUND   # Cleanup, maintenance
]

# Execute with priority
await rate_limiter.execute_with_rate_limit(
    endpoint="AddOrder",
    func=trading_function,
    priority=RequestPriority.CRITICAL,
    timeout_seconds=10.0
)
```

### Custom Endpoint Configuration

```python
from src.rate_limiting.rate_limit_config import EndpointConfig, EndpointType

# Add custom endpoint
custom_endpoint = EndpointConfig(
    name="CustomEndpoint",
    endpoint_type=EndpointType.PRIVATE,
    weight=2,
    penalty_points=3,
    max_requests_per_minute=10,
    requires_auth=True
)
```

### State Persistence

```python
# Automatic state saving/loading
rate_limiter = KrakenRateLimiter2025(
    persistence_path="trading_data/rate_limiter_state.json"
)

# State includes:
# - Current penalty points
# - Order timestamps
# - Token bucket states
# - Statistics
```

## 🧪 Testing and Validation

### Run Test Suite

```bash
# Run comprehensive demo
python test_rate_limiting_system.py

# Run integration example
python integration_example.py
```

### Test Output Example

```
🚀 Kraken 2025 Rate Limiting System Demo
==================================================

🔧 Demo 1: Basic Functionality
------------------------------
✅ Initialized rate limiter for pro account
   Private limit: 15 RPM
   Public limit: 20 RPM
   Max penalty points: 180

🔍 Testing basic rate limit checks:
   Balance      ✅ ALLOWED    OK
   Ticker       ✅ ALLOWED    OK
   AddOrder     ✅ ALLOWED    OK
   CancelOrder  ✅ ALLOWED    OK
```

## 🔄 Integration with Existing Code

### Replace Existing Rate Limiting

```python
# Old approach
if not self.rate_limit_manager.can_proceed():
    await asyncio.sleep(self.backoff_time)

# New approach
await self.rate_limiter.execute_with_rate_limit(
    endpoint="Balance",
    func=api_call,
    priority=RequestPriority.NORMAL
)
```

### Migrate Order Tracking

```python
# Old approach
self.order_times[order_id] = time.time()

# New approach (automatic tracking)
order = await self.rate_limiter.execute_with_rate_limit(
    endpoint="AddOrder",
    func=create_order
)
self.rate_limiter.record_order_time(order['id'])
```

## 🚨 Error Handling

### Common Error Scenarios

```python
try:
    result = await rate_limiter.execute_with_rate_limit(
        endpoint="AddOrder",
        func=api_call,
        timeout_seconds=30.0
    )
except asyncio.TimeoutError:
    # Rate limit timeout exceeded
    logger.error("Rate limit timeout - request blocked too long")
    
except Exception as e:
    # API call failed
    logger.error(f"API call failed: {e}")
    # Circuit breaker automatically records failure
```

### Circuit Breaker Handling

```python
# Check circuit breaker state
if rate_limiter.circuit_breaker:
    state = rate_limiter.circuit_breaker.get_state()
    if state['state'] == 'OPEN':
        logger.warning("Circuit breaker is open - waiting for recovery")
        await asyncio.sleep(state['recovery_timeout'])
```

## 🔧 Performance Optimization

### High-Frequency Trading Tips

1. **Use Appropriate Priorities**: Reserve `CRITICAL` for emergency situations
2. **Batch Operations**: Group related requests when possible
3. **Monitor Penalty Points**: Keep utilization below 80%
4. **Use IOC Orders**: Zero penalty on failure for Kraken
5. **Enable Persistence**: Maintain state across restarts

### Memory Management

```python
# Automatic cleanup of old data
rate_limiter = KrakenRateLimiter2025(
    cleanup_interval=60.0  # Clean up every minute
)

# Manual cleanup if needed
rate_limiter.order_times.clear()  # Clear old order tracking
rate_limiter.reset_stats()        # Reset statistics
```

## 📚 API Reference

### KrakenRateLimiter2025

#### Methods

- `async start()`: Start the rate limiter
- `async stop()`: Stop and cleanup
- `async check_rate_limit(endpoint, weight=None, order_age_seconds=None, priority=NORMAL)`: Check if request can proceed
- `async wait_for_rate_limit(...)`: Wait until request can proceed
- `async execute_with_rate_limit(endpoint, func, ...)`: Execute function with automatic rate limiting
- `record_order_time(order_id, timestamp=None)`: Record order creation time
- `get_order_age(order_id)`: Get order age in seconds
- `remove_order_time(order_id)`: Remove order tracking
- `get_status()`: Get comprehensive status
- `get_endpoint_stats(endpoint=None)`: Get endpoint statistics
- `reset_stats()`: Reset all statistics

### RequestQueue

#### Methods

- `async start()`: Start queue management
- `async stop()`: Stop and cleanup
- `async enqueue(...)`: Add request to queue
- `async dequeue(timeout_seconds=None)`: Get next request
- `async complete_request(request_id, success=True)`: Mark request complete
- `async cancel_request(request_id, reason="Cancelled")`: Cancel request
- `get_stats()`: Get queue statistics
- `get_queue_size(priority=None)`: Get queue size
- `is_full()`: Check if queue is full
- `is_empty()`: Check if queue is empty

## 🤝 Contributing

### Development Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `python test_rate_limiting_system.py`
4. Check integration: `python integration_example.py`

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add comprehensive docstrings
- Include error handling
- Write unit tests

## 📄 License

This rate limiting system is part of the crypto trading bot project and follows the same license terms.

## 🆘 Support

For issues or questions:

1. Check the test scripts for examples
2. Review the integration guide
3. Examine the comprehensive logging output
4. Create an issue with detailed reproduction steps

---

**Built for high-frequency trading with Kraken's 2025 API specifications** 🚀