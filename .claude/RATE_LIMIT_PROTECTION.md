# Rate Limit Protection System

<!-- CLAUDE-note-critical: Rate limit violations cause immediate 10-minute bans -->
<!-- CLAUDE-note-tier: Intermediate tier: 125 max counter, -2.34/sec decay -->

## Rate Limit Configuration

```python
RATE_LIMITS = {
    'intermediate': {
        'max_counter': 125,
        'decay_rate': 2.34,  # per second
        'operations': {
            'add_order': 1,
            'cancel_5s': 8,      # NEVER DO THIS
            'cancel_10s': 6,     # AVOID
            'cancel_15s': 5,     # AVOID
            'cancel_45s': 4,     # USE SPARINGLY
            'cancel_90s': 2,     # ACCEPTABLE
            'cancel_300s': 1,    # PREFERRED
            'amend_order': 1,
            'amend_5s': 3,
            'amend_10s': 2,
            'amend_15s': 1
        }
    }
}
```

## Protection Implementation

### Pre-Operation Validation
```python
async def validate_rate_limit(self, symbol: str, operation: str) -> RateLimitStatus:
    """Check if operation is safe to perform"""
    
    current_counter = self.counters.get(symbol, 0)
    operation_cost = self.get_operation_cost(operation)
    
    # Calculate if operation would exceed limit
    if current_counter + operation_cost > self.max_counter:
        return RateLimitStatus(
            allowed=False,
            current_counter=current_counter,
            operation_cost=operation_cost,
            reason='Would exceed rate limit',
            recovery_time=self.calculate_recovery_time(current_counter)
        )
    
    # Check percentage for warnings
    percentage = (current_counter / self.max_counter) * 100
```    
    return RateLimitStatus(
        allowed=True,
        current_counter=current_counter,
        operation_cost=operation_cost,
        percentage=percentage,
        warning=percentage > 70
    )
```

### Smart Order Cancellation
```python
async def safe_cancel_order(self, order_id: str, symbol: str) -> bool:
    """Cancel order with rate limit protection"""
    
    # Get order age
    order_age = time.time() - self.order_timestamps.get(order_id, 0)
    
    # Determine cancel cost
    if order_age < 5:
        # FORBIDDEN - would cost 8 points
        logger.error(f"FORBIDDEN: Order {order_id} is only {order_age:.1f}s old")
        return False
    
    cancel_cost = self.get_cancel_cost_by_age(order_age)
    
    # Check if we can afford it
    status = await self.validate_rate_limit(symbol, f'cancel_{int(order_age)}s')
    
    if not status.allowed:
        # Try to find alternative
        if order_age < 300:  # If young order
            logger.warning(f"Deferring cancel of {order_id} to reduce rate limit impact")
            await self.schedule_deferred_cancel(order_id, symbol, 300 - order_age)
            return False
    
    # Proceed with cancel
    try:
        await self.exchange.cancel_order(order_id, symbol)
        self.record_operation(symbol, cancel_cost)
        return True
    except Exception as e:
        logger.error(f"Cancel failed: {e}")
        return False
```

### IOC Order Strategy
```python
async def determine_order_type(self, symbol: str) -> Dict[str, Any]:
    """Determine optimal order type based on rate limit status"""
    
    status = await self.get_rate_limit_status(symbol)
    
    params = {}
```    
    if status.percentage > 70:
        # Use IOC orders to avoid cancellation needs
        params['timeInForce'] = 'IOC'
        logger.info(f"Using IOC order due to high rate limit: {status.percentage:.1f}%")
    
    elif status.percentage > 50:
        # Use shorter time windows
        params['timeInForce'] = 'GTT'
        params['expireTime'] = int(time.time() + 300)  # 5 minutes
    
    return params
```

## Recovery Strategies

### Automatic Recovery Management
```python
async def manage_rate_limit_recovery(self):
    """Monitor and manage rate limit recovery"""
    
    while True:
        for symbol in self.trading_pairs:
            status = await self.get_rate_limit_status(symbol)
            
            if status.percentage > 90:
                # Critical - pause trading
                await self.pause_symbol_trading(symbol)
                
                # Cancel old orders only
                await self.cancel_orders_older_than(symbol, 600)  # 10+ minutes
                
            elif status.percentage > 70:
                # Warning - switch to conservative mode
                self.set_conservative_mode(symbol)
                
            elif status.percentage < 30 and self.is_paused(symbol):
                # Safe to resume
                await self.resume_symbol_trading(symbol)
        
        await asyncio.sleep(10)  # Check every 10 seconds
```

### Multi-Symbol Load Balancing
```python
async def balance_rate_limit_load(self):
    """Balance operations across symbols to prevent limits"""
    
    # Get status for all symbols
    symbol_status = {}
    for symbol in self.trading_pairs:
        symbol_status[symbol] = await self.get_rate_limit_status(symbol)
```    
    # Sort by available capacity
    sorted_symbols = sorted(
        symbol_status.items(),
        key=lambda x: x[1].percentage
    )
    
    # Prefer symbols with more capacity
    self.preferred_symbols = [s[0] for s in sorted_symbols[:5]]
    
    logger.info(f"Rate limit load balancing - preferred: {self.preferred_symbols}")
```

## Emergency Procedures

### Rate Limit Exceeded Handler
```python
async def handle_rate_limit_exceeded(self, symbol: str, error: Exception):
    """Emergency handler for rate limit errors"""
    
    logger.critical(f"RATE LIMIT EXCEEDED on {symbol}: {error}")
    
    # 1. Immediate trading halt
    await self.emergency_halt_symbol(symbol)
    
    # 2. Cancel all pending operations
    self.cancel_pending_operations(symbol)
    
    # 3. Calculate recovery time
    recovery_seconds = self.calculate_full_recovery_time(symbol)
    
    # 4. Set recovery timer
    self.set_symbol_recovery_timer(symbol, recovery_seconds)
    
    # 5. Notify monitoring system
    await self.notify_rate_limit_violation(symbol, recovery_seconds)
    
    # 6. Log for learning system
    await self.learning_manager.record_rate_limit_violation(symbol)
```

### Gradual Resume Strategy
```python
async def gradual_resume_after_limit(self, symbol: str):
    """Gradually resume trading after rate limit recovery"""
    
    # Phase 1: Monitor only (5 minutes)
    await self.set_monitor_only_mode(symbol)
    await asyncio.sleep(300)
    
    # Phase 2: IOC orders only (10 minutes)
    await self.set_ioc_only_mode(symbol)
    await asyncio.sleep(600)
```    
    # Phase 3: Conservative trading (30 minutes)
    await self.set_conservative_mode(symbol)
    await asyncio.sleep(1800)
    
    # Phase 4: Normal operations
    await self.resume_normal_trading(symbol)
    
    logger.info(f"Successfully resumed normal trading on {symbol}")
```

## Monitoring Dashboard
```python
async def get_rate_limit_dashboard(self) -> Dict[str, Any]:
    """Real-time rate limit status for all symbols"""
    
    dashboard = {
        'timestamp': time.time(),
        'symbols': {}
    }
    
    for symbol in self.trading_pairs:
        status = await self.get_rate_limit_status(symbol)
        
        dashboard['symbols'][symbol] = {
            'counter': status.current_counter,
            'max': status.max_counter,
            'percentage': status.percentage,
            'status': self.get_status_level(status.percentage),
            'recovery_time': status.recovery_time if status.percentage > 70 else 0,
            'operations_available': self.calculate_available_operations(status)
        }
    
    dashboard['summary'] = {
        'healthy_symbols': sum(1 for s in dashboard['symbols'].values() if s['percentage'] < 50),
        'warning_symbols': sum(1 for s in dashboard['symbols'].values() if 50 <= s['percentage'] < 85),
        'critical_symbols': sum(1 for s in dashboard['symbols'].values() if s['percentage'] >= 85)
    }
    
    return dashboard
```