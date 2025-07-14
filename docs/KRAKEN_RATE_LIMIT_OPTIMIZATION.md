# Kraken Rate Limit Optimization Guide

## Overview

This guide documents the advanced rate limiting optimizations implemented for Kraken exchange integration, focusing on micro-profit trading strategies.

## Key Enhancements

### 1. IOC Order Optimization (0 Penalty on Failure!)

**Critical Advantage**: Failed IOC (Immediate-or-Cancel) orders incur **0 penalty points** on Kraken, making them ideal for high-frequency micro-profit strategies.

```python
# Regular order cancellation: 8 penalty points!
# Failed IOC order: 0 penalty points!
```

**Implementation**:
- MicroScalperStrategy now prefers IOC orders
- Trade executor handles IOC orders with special logic
- Rate limiter tracks IOC success/failure rates

### 2. WebSocket Rate Counter Monitoring

Real-time monitoring of rate limit usage through WebSocket subscription:

```python
# Subscribe with rate counter enabled
ticker_sub = {
    "method": "subscribe",
    "params": {
        "channel": "ticker",
        "symbol": symbols,
        "ratecounter": True  # Enable monitoring
    }
}
```

### 3. Circuit Breaker Pattern

Automatic protection when approaching rate limits:
- Opens at 90% utilization
- 60-second cooldown period
- Prevents cascade failures

### 4. Hierarchical Rate Limiting

Separate tracking for:
- REST API limits (15-20 counter based on tier)
- Trading engine limits (60-180 counter based on tier)
- Per-pair rate counters

## Tier-Specific Configurations

### Starter Tier
- **REST API**: 15 max counter, 0.33/s decay
- **Trading**: 60 max counter, 1.0/s decay
- **Max Orders**: 60

### Intermediate Tier
- **REST API**: 20 max counter, 0.5/s decay
- **Trading**: 125 max counter, 2.34/s decay
- **Max Orders**: 80

### Pro Tier
- **REST API**: 20 max counter, 1.0/s decay
- **Trading**: 180 max counter, 3.75/s decay
- **Max Orders**: 225

## Best Practices for Micro-Profits

1. **Always Use IOC for Scalping**
   - 0 penalty on failure vs 8 points for cancellation
   - Allows more aggressive trading

2. **Monitor WebSocket Counter**
   - Real-time rate limit awareness
   - Adjust strategy before hitting limits

3. **Leverage Circuit Breaker**
   - Automatic protection
   - Graceful degradation

4. **Optimize for Your Tier**
   - Pro tier: 3.75 points/second recovery
   - Can execute ~225 events/minute theoretical max

## Example: Micro-Scalping Optimization

```python
# Signal with IOC preference
signal = {
    'symbol': 'BTC/USDT',
    'side': 'buy',
    'order_type': 'ioc',  # 0 penalty on failure!
    'take_profit_pct': 0.004,  # 0.4% micro-profit
    'strategy': 'micro_scalper'
}

# Rate limiter tracks outcomes
if order_filled:
    rate_limiter.track_ioc_order(success=True)
else:
    rate_limiter.track_ioc_order(success=False)
    # Saved 1 point vs regular order!
```

## Monitoring and Analytics

The system provides real-time statistics:

```python
stats = rate_limiter.get_ioc_optimization_stats()
# {
#     'ioc_orders_total': 100,
#     'ioc_success_rate': 35.0,
#     'points_saved_by_ioc': 65,
#     'cancellation_penalty_points': 80,
#     'recommendation': 'Continue using IOC orders'
# }
```

## Key Takeaways

1. **IOC orders are FREE** when they fail (0 penalty)
2. **Cancellations are EXPENSIVE** (8 penalty points)
3. **Monitor rate counters** via WebSocket
4. **Circuit breaker** prevents limit breaches
5. **Upgrade to Pro tier** for 3.75x faster recovery

## Testing

Run the test suite to verify optimizations:

```bash
python3 tests/test_kraken_rate_limiter_enhancements.py
```

This will test:
- IOC order tracking
- WebSocket monitoring
- Circuit breaker functionality
- REST API limits
- Real-world scenarios