# Unified Balance Manager System

A comprehensive balance management system for the crypto trading bot that provides real-time balance tracking, intelligent caching, validation, and historical analysis.

## Features

- **Real-time Balance Streaming**: WebSocket V2 integration for instant balance updates
- **REST API Fallback**: Automatic fallback to REST API when WebSocket is unavailable  
- **Intelligent Caching**: TTL-based caching with LRU eviction for optimal performance
- **Balance Validation**: Comprehensive validation rules for data integrity
- **Historical Tracking**: Complete balance history with trend analysis
- **Thread-Safe Operations**: Safe for concurrent access from multiple trading strategies
- **Circuit Breaker Integration**: Resilient operation with automatic failure recovery
- **Decimal Precision**: Accurate financial calculations using Python Decimal
- **Event-Driven Architecture**: Callbacks for balance updates and changes

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Balance Manager                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Cache     │  │ Validator   │  │  History    │         │
│  │             │  │             │  │             │         │
│  │ • TTL       │  │ • Rules     │  │ • Tracking  │         │
│  │ • LRU       │  │ • Cross-src │  │ • Trends    │         │
│  │ • Thread    │  │ • Decimal   │  │ • Persist   │         │
│  │   Safe      │  │   Checks    │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  WebSocket V2   │ │   REST API      │ │ Circuit Breaker │
│                 │ │                 │ │                 │
│ • Real-time     │ │ • Fallback      │ │ • Failure       │
│ • Streaming     │ │ • Full refresh  │ │   Detection     │
│ • Auth tokens   │ │ • Rate limits   │ │ • Auto recovery │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Components

### 1. BalanceManager
The main orchestrator that coordinates all balance operations.

**Key Features:**
- Unified interface for all balance operations
- Automatic source selection (WebSocket → REST API → Cache)
- Background monitoring and health checks
- Event-driven callbacks for balance changes

### 2. BalanceCache
Intelligent caching system with TTL and LRU eviction.

**Key Features:**
- Thread-safe operations with async locks
- Configurable TTL and cache size
- LRU eviction when cache is full
- Statistics and monitoring
- Event callbacks for cache operations

### 3. BalanceValidator
Comprehensive validation system for balance data integrity.

**Key Features:**
- Configurable validation rules
- Cross-source consistency checking  
- Decimal precision validation
- Threshold-based warnings
- Detailed validation reporting

### 4. BalanceHistory
Historical balance tracking and trend analysis.

**Key Features:**
- Complete balance change history
- Trend analysis with direction and strength
- Volatility calculations
- Persistent storage with automatic cleanup
- Change detection with configurable thresholds

## Usage

### Basic Usage

```python
from src.balance import BalanceManager, BalanceManagerConfig

# Create configuration
config = BalanceManagerConfig(
    cache_default_ttl=300.0,  # 5 minutes
    history_retention_hours=24 * 7,  # 1 week
    enable_validation=True
)

# Initialize balance manager
balance_manager = BalanceManager(
    websocket_client=websocket_client,
    rest_client=rest_client,
    config=config
)

# Initialize and start
await balance_manager.initialize()

# Get balance for specific asset
usdt_balance = await balance_manager.get_balance("USDT")
print(f"USDT Balance: {usdt_balance['free']}")

# Get all balances
all_balances = await balance_manager.get_all_balances()
for asset, data in all_balances.items():
    print(f"{asset}: {data['balance']} (free: {data['free']})")

# Force refresh from API
await balance_manager.refresh_all_balances()
```

### Event Callbacks

```python
async def on_balance_update(balance_data):
    asset = balance_data['asset']
    balance = balance_data['balance']
    print(f"Balance update: {asset} = {balance}")

async def on_balance_change(balance_data):
    asset = balance_data['asset']
    print(f"Significant change in {asset}")

# Register callbacks
balance_manager.register_callback('balance_update', on_balance_update)
balance_manager.register_callback('balance_change', on_balance_change)
```

### Advanced Usage

```python
# Get balance with validation
usdt_balance = await balance_manager.get_balance("USDT")
if balance_manager.validator:
    validation = balance_manager.validator.validate_single_balance(
        "USDT", usdt_balance['balance'], usdt_balance['hold_trade']
    )
    if not validation.is_valid:
        print("Balance validation failed!")

# Analyze balance trends
trend = await balance_manager.history.analyze_balance_trend("USDT", analysis_hours=24)
if trend:
    print(f"USDT trend: {trend.trend_direction} (strength: {trend.trend_strength})")

# Get balance history
history = balance_manager.history.get_asset_history("USDT", limit=10)
for entry in history:
    print(f"USDT: {entry.balance} at {entry.timestamp}")
```

## Configuration

### BalanceManagerConfig Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cache_max_size` | 1000 | Maximum cache entries |
| `cache_default_ttl` | 300.0 | Cache TTL in seconds |
| `history_max_entries` | 10000 | Max history per asset |
| `history_retention_hours` | 168 | History retention (1 week) |
| `enable_validation` | True | Enable balance validation |
| `websocket_timeout` | 10.0 | WebSocket operation timeout |
| `rest_api_timeout` | 15.0 | REST API timeout |
| `force_update_interval` | 600.0 | Periodic refresh interval |

### Validation Rules

The validator includes several built-in rules:

- **negative_balance**: Detects negative balance values
- **negative_free_balance**: Warns about negative free balance
- **hold_exceeds_balance**: Errors when hold > balance  
- **source_inconsistency**: Warns about source discrepancies
- **unrealistic_balance**: Flags unusually high balances
- **stale_data**: Warns about old data
- **precision_overflow**: Checks decimal precision

## Integration Examples

### With Trading Strategy

```python
class TradingStrategy:
    def __init__(self, balance_manager):
        self.balance_manager = balance_manager
        balance_manager.register_callback('balance_change', self.on_balance_change)
    
    async def on_balance_change(self, balance_data):
        if balance_data['asset'] == 'USDT' and balance_data['free'] < 10.0:
            await self.close_positions()  # Low balance protection
    
    async def can_open_position(self, required_usdt):
        usdt_balance = await self.balance_manager.get_balance('USDT')
        return usdt_balance and usdt_balance['free'] >= required_usdt
```

### With Risk Management

```python
class RiskManager:
    def __init__(self, balance_manager):
        self.balance_manager = balance_manager
    
    async def check_portfolio_risk(self):
        all_balances = await self.balance_manager.get_all_balances()
        
        # Calculate total value
        total_value = sum(data['balance'] for data in all_balances.values() 
                         if data['asset'] == 'USDT')
        
        # Check individual asset exposure
        for asset, data in all_balances.items():
            if asset != 'USDT' and data['balance'] > 0:
                exposure = data['balance'] / total_value if total_value > 0 else 0
                if exposure > 0.1:  # 10% max per asset
                    print(f"High exposure to {asset}: {exposure:.1%}")
```

## Monitoring and Debugging

### Status Monitoring

```python
# Get comprehensive status
status = balance_manager.get_status()
print(f"WebSocket connected: {status['websocket']['connected']}")
print(f"Cache hit rate: {status['cache']['hit_rate_percent']:.1f}%")
print(f"Tracked assets: {status['tracked_assets']}")

# Get detailed statistics
stats = balance_manager.get_statistics()
print(f"Total API calls: {stats['rest_api_calls']}")
print(f"Validation failures: {stats['validation_failures']}")
```

### Health Checks

```python
# Validate all balances
if balance_manager.validator:
    validation_result = await balance_manager.validate_all_balances()
    if not validation_result.is_valid:
        print(f"Found {len(validation_result.issues)} validation issues")
        for issue in validation_result.issues:
            print(f"- {issue.message}")

# Check cache health
cache_stats = balance_manager.cache.get_statistics()
if cache_stats['hit_rate_percent'] < 50:
    print("Warning: Low cache hit rate")
```

## Performance Considerations

### Memory Usage
- Cache: ~500 bytes per entry
- History: ~800 bytes per entry  
- Automatic cleanup based on TTL and retention policies

### Network Efficiency
- WebSocket streaming reduces API calls by 90%+
- Intelligent caching prevents redundant requests
- Circuit breaker prevents cascading failures

### Concurrency
- All operations are thread-safe
- Async locks prevent race conditions
- Background tasks handle maintenance

## Error Handling

The system provides comprehensive error handling:

1. **WebSocket Failures**: Automatic fallback to REST API
2. **REST API Failures**: Circuit breaker protection with exponential backoff
3. **Validation Failures**: Configurable severity levels with callbacks
4. **Cache Issues**: Automatic cleanup and recovery
5. **Network Issues**: Retry logic with intelligent delays

## File Structure

```
src/balance/
├── __init__.py                 # Package exports
├── balance_manager.py          # Main balance manager  
├── balance_cache.py           # Caching system
├── balance_validator.py       # Validation system
├── balance_history.py         # History tracking
├── integration_example.py     # Usage examples
└── README.md                  # This documentation
```

## Dependencies

- `asyncio`: Async/await support
- `decimal`: Precise financial calculations  
- `threading`: Thread-safe operations
- `dataclasses`: Data structure definitions
- `pathlib`: File system operations
- `json`: Serialization for persistence

## Testing

Run the integration example:

```bash
cd /mnt/c/dev/tools/crypto-trading-bot-2025
python -m src.balance.integration_example
```

This will demonstrate:
- WebSocket V2 integration
- REST API fallback
- Real-time balance updates
- Validation and history tracking
- Error handling and recovery

## Best Practices

1. **Always use the balance manager**: Don't access APIs directly
2. **Register for callbacks**: React to balance changes in real-time  
3. **Enable validation**: Catch data integrity issues early
4. **Monitor status**: Check WebSocket health and cache performance
5. **Use force_refresh sparingly**: Rely on real-time updates when possible
6. **Configure TTL appropriately**: Balance freshness vs. performance
7. **Handle validation failures**: Don't ignore data quality issues

## Future Enhancements

- Multi-exchange support
- Advanced trend analysis algorithms
- Machine learning for anomaly detection
- GraphQL API integration
- Real-time portfolio analytics
- Advanced alerting system