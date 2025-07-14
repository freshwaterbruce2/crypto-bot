# Trade Execution Flow - Autonomous Multi-Assistant System

<!-- CLAUDE-note-execution: Enhanced trade executor with 5 specialized assistants -->
<!-- CLAUDE-note-critical: All trades must pass rate limit and portfolio checks -->

## Execution Architecture

```python
class EnhancedTradeExecutorWithAssistants:
    def __init__(self):
        self.execution_assistant = ExecutionAssistantManager()
        self.buy_assistant = BuyLogicAssistant()
        self.sell_assistant = SellLogicAssistant()
        self.risk_assistant = RiskManagementAssistant()
        self.symbol_assistant = SymbolMappingAssistant()
        self.analytics_assistant = LoggingAnalyticsAssistant()
```

## Trade Flow Sequence

### 1. Signal Generation
```python
async def generate_trade_signal(self, symbol: str):
    # Multi-timeframe analysis
    signals = await self.analyze_timeframes(['1m', '5m', '15m'])
    
    # Assistant consensus
    buy_vote = await self.buy_assistant.evaluate_opportunity(signals)
    risk_check = await self.risk_assistant.validate_trade(symbol)
    
    if buy_vote.confidence > 0.75 and risk_check.approved:
        return TradeSignal(side='buy', confidence=buy_vote.confidence)
```

### 2. Pre-Execution Validation
```python
async def validate_trade_prerequisites(self, signal: TradeSignal):
    # Rate limit check (CRITICAL)
    rate_status = await self.rate_limiter.can_place_order(signal.symbol)
    if not rate_status.allowed:
        return await self.handle_rate_limit_exceeded(signal)
    
    # Portfolio intelligence check
    deployment = await self.balance_manager.get_deployment_status('USDT')
    if deployment == 'funds_deployed':
        return await self.evaluate_reallocation_opportunity(signal)
    
    # Minimum order validation
    min_order = await self.get_learned_minimum(signal.symbol)
    if signal.amount < min_order:
        signal.amount = min_order * 1.1  # 10% buffer
```
### 3. Order Execution
```python
async def execute_order_with_assistants(self, signal: TradeSignal):
    # Coordinate assistants
    coordination = await self.execution_assistant.coordinate_execution({
        'signal': signal,
        'buy_analysis': await self.buy_assistant.get_entry_parameters(),
        'risk_limits': await self.risk_assistant.get_position_limits(),
        'symbol_mapping': await self.symbol_assistant.map_to_kraken_pro(signal.symbol)
    })
    
    # Execute with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            order = await self.exchange.create_order(
                symbol=coordination.execution_symbol,
                type='limit',
                side=signal.side,
                amount=coordination.adjusted_amount,
                price=coordination.limit_price,
                params={'timeInForce': 'IOC'} if rate_status.counter > 70 else {}
            )
            
            # Record execution
            await self.analytics_assistant.record_trade_execution(order, coordination)
            return order
            
        except Exception as e:
            await self.handle_execution_error(e, attempt, signal)
```

### 4. Post-Execution Management
```python
async def manage_position_lifecycle(self, order: Order):
    # Start monitoring
    monitor_task = asyncio.create_task(
        self.monitor_position_for_exit(order)
    )
    
    # Update learning system
    await self.learning_manager.record_trade_entry(order)
    
    # Set exit parameters
    exit_params = await self.sell_assistant.calculate_exit_targets(order)
    await self.set_take_profit_orders(order, exit_params)
```
## Micro-Profit Exit Strategy
```python
async def monitor_position_for_exit(self, entry_order: Order):
    target_profit = 0.005  # 0.5%
    
    while True:
        current_price = await self.get_current_price(entry_order.symbol)
        profit_pct = (current_price - entry_order.price) / entry_order.price
        
        if profit_pct >= target_profit:
            # Market order for speed
            exit_order = await self.execute_market_exit(entry_order)
            await self.learning_manager.record_successful_exit(exit_order)
            break
            
        await asyncio.sleep(1)  # Check every second
```

## Error Handling
```python
async def handle_execution_error(self, error: Exception, attempt: int, signal: TradeSignal):
    error_pattern = self.error_resolver.match_pattern(str(error))
    
    if error_pattern:
        resolution = await self.error_resolver.apply_resolution(error_pattern, signal)
        if resolution.retry_allowed:
            await asyncio.sleep(resolution.wait_time)
            return
    
    # Log to learning system
    await self.learning_manager.record_execution_failure(error, signal)
```

## Performance Optimization
```python
async def optimize_execution_performance(self):
    # Analyze recent executions
    metrics = await self.analytics_assistant.get_execution_metrics()
    
    # Adjust parameters
    if metrics.avg_slippage > 0.001:  # 0.1%
        self.execution_params.use_ioc_orders = True
    
    if metrics.success_rate < 0.95:
        self.execution_params.add_buffer_to_minimums = True
```