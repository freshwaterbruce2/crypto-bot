# REST API Strategic Implementation

This module provides a comprehensive REST API implementation designed to work strategically with WebSocket V2 to minimize nonce issues while ensuring reliable data access and emergency fallback capabilities.

## 🎯 Design Philosophy

### Strategic REST Usage
- **WebSocket V2 First**: REST is secondary to WebSocket for real-time data
- **Minimal API Calls**: Aggressive reduction of REST requests to preserve nonce integrity
- **Smart Batching**: Intelligent request batching to minimize API overhead
- **Emergency Fallback**: Critical operations when WebSocket fails
- **Validation Only**: Cross-validation of WebSocket data integrity

### Nonce Issue Mitigation
- **Circuit Breaker Protection**: Prevents cascade failures from nonce conflicts
- **Exponential Backoff**: Smart retry logic with increasing delays
- **Request Prioritization**: Critical operations get priority during conflicts
- **Load Balancing**: Intelligent distribution between WebSocket and REST
- **Conflict Detection**: Automatic detection and recovery from nonce issues

## 📁 Module Structure

```
src/rest/
├── __init__.py                 # Module exports
├── strategic_rest_client.py    # Core strategic REST client
├── rest_data_validator.py      # Cross-validation system
├── rest_fallback_manager.py    # Emergency fallback management
├── integration_example.py      # Comprehensive usage example
└── README.md                  # This file
```

## 🔧 Components Overview

### 1. Strategic REST Client (`strategic_rest_client.py`)

The core REST client designed for minimal, strategic API usage.

**Key Features:**
- **Minimal API Usage**: Only when WebSocket is insufficient
- **Smart Request Batching**: Groups multiple requests to reduce nonce usage
- **Circuit Breaker Protection**: Prevents cascade failures
- **Emergency Operations**: Critical account safety functions
- **Nonce Management Integration**: Works with unified nonce manager

**Usage:**
```python
from src.rest import StrategicRestClient

client = StrategicRestClient(api_key, private_key)
await client.initialize()

# Emergency operations
balance = await client.emergency_balance_check()
orders = await client.emergency_open_orders()

# Batch operations for efficiency
await client.add_to_batch('Ticker', {'pair': 'SHIBUSDT'})
await client.add_to_batch('OHLC', {'pair': 'ADAUSDT', 'interval': 5})

# Historical data queries
historical = await client.batch_historical_query(
    pairs=['SHIBUSDT', 'ADAUSDT'],
    timeframe=5,
    max_age_hours=24
)
```

### 2. REST Data Validator (`rest_data_validator.py`)

Cross-validation system ensuring data integrity between WebSocket and REST sources.

**Key Features:**
- **Cross-Source Validation**: Compare REST vs WebSocket data
- **Discrepancy Detection**: Identify and report data inconsistencies  
- **Automated Scheduling**: Periodic validation with smart intervals
- **Confidence Scoring**: Quality metrics for validation results
- **Pattern Recognition**: Detect recurring validation issues

**Usage:**
```python
from src.rest import RestDataValidator

validator = RestDataValidator(strategic_client, websocket_manager)
await validator.initialize()

# Start continuous validation
await validator.start_continuous_validation()

# Validate specific data
balance_result = await validator.validate_balance_data()
price_result = await validator.validate_price_data('SHIBUSDT')

# Add critical pairs for monitoring
validator.add_critical_pair('SHIBUSDT')
validator.add_critical_pair('ADAUSDT')

# Get validation statistics
stats = validator.get_validation_stats()
```

### 3. REST Fallback Manager (`rest_fallback_manager.py`)

Emergency fallback system for WebSocket failures and service degradation management.

**Key Features:**
- **Service Level Management**: Automatic degradation and recovery
- **Emergency Operations**: Critical functions during outages
- **Recovery Coordination**: Automatic failover and failback
- **Operation Queuing**: Priority-based operation management
- **Health Monitoring**: Continuous service health assessment

**Usage:**
```python
from src.rest import RestFallbackManager, ServiceLevel

fallback_manager = RestFallbackManager(strategic_client, websocket_manager)
await fallback_manager.initialize()

# Handle WebSocket failure
await fallback_manager.handle_websocket_failure("Connection lost")

# Emergency operations
balance = await fallback_manager.emergency_get_balance()
result = await fallback_manager.emergency_cancel_order(txid)

# Queue operations with priority
await fallback_manager.queue_operation(
    'Balance',
    priority=OperationPriority.HIGH
)

# Monitor service status
status = fallback_manager.get_service_status()
```

## 🚀 Integration with Data Source Coordinator

The REST module integrates with the Data Source Coordinator for intelligent data routing:

```python
from src.data import DataSourceCoordinator
from src.rest import StrategicRestClient, RestFallbackManager

# Initialize components
rest_client = StrategicRestClient(api_key, private_key)
fallback_manager = RestFallbackManager(rest_client, websocket_manager)

# Create coordinator for intelligent source selection
coordinator = DataSourceCoordinator(
    websocket_manager=websocket_manager,
    strategic_rest_client=rest_client,
    fallback_manager=fallback_manager
)

await coordinator.initialize()

# Automatic source selection based on performance and availability
balance = await coordinator.get_balance()  # Auto-selects best source
ticker = await coordinator.get_ticker_data('SHIBUSDT')

# Force specific source when needed
rest_balance = await coordinator.get_balance(source=DataSource.REST)
ws_ticker = await coordinator.get_ticker_data('SHIBUSDT', source=DataSource.WEBSOCKET)
```

## 📊 Performance Monitoring

All components provide comprehensive performance monitoring:

### Strategic Client Metrics
```python
stats = strategic_client.get_strategic_stats()
print(f"Total requests: {stats['stats']['total_requests']}")
print(f"Batched requests: {stats['stats']['batched_requests']}")
print(f"Emergency requests: {stats['stats']['emergency_requests']}")
print(f"Nonce conflicts: {stats['stats']['nonce_conflicts']}")
```

### Validation Statistics
```python
validation_stats = validator.get_validation_stats()
stats = validation_stats['stats']
print(f"Success rate: {stats['successful_validations']}/{stats['total_validations']}")
print(f"Average confidence: {stats['average_confidence']:.3f}")
```

### Fallback Metrics
```python
fallback_stats = fallback_manager.get_fallback_stats()
print(f"Recovery success rate: {fallback_stats['recovery_success_rate']:.1%}")
print(f"Emergency operations: {fallback_stats['emergency_operations']}")
```

## 🔄 Service Level Management

The system automatically manages service degradation levels:

### Service Levels
- **FULL_SERVICE**: Both WebSocket and REST working optimally
- **DEGRADED_SERVICE**: One source has issues, using fallback
- **EMERGENCY_ONLY**: Only critical operations allowed
- **SERVICE_OUTAGE**: Both sources failed

### Automatic Transitions
```python
# Service level callbacks
def on_service_change(old_level, new_level):
    if new_level == ServiceLevel.SERVICE_OUTAGE:
        logger.critical("CRITICAL: All data sources failed!")
    elif new_level == ServiceLevel.EMERGENCY_ONLY:
        logger.warning("Emergency mode: Limited operations")

fallback_manager.add_service_level_callback(on_service_change)
```

## ⚡ Emergency Operations

Critical operations available during service degradation:

### Account Safety
```python
# Emergency balance check
balance = await strategic_client.emergency_balance_check()

# Emergency order management
orders = await strategic_client.emergency_open_orders()
cancel_result = await strategic_client.emergency_cancel_order(txid)
cancel_all = await fallback_manager.emergency_cancel_all_orders()
```

### System Status
```python
# Emergency system status
status = await strategic_client.emergency_system_status()
system_health = status['result']['status']
```

## 🛡️ Circuit Breaker Protection

Built-in circuit breaker prevents cascade failures:

```python
# Circuit breaker status
cb_status = strategic_client.circuit_breaker.get_status()
print(f"State: {cb_status['state']}")
print(f"Can execute: {cb_status['can_execute']}")
print(f"Failure count: {cb_status['failure_count']}")

# Manual circuit breaker control
strategic_client.circuit_breaker.force_open()  # Emergency stop
strategic_client.circuit_breaker.force_closed()  # Force enable
```

## 📈 Optimization Recommendations

The system provides automatic optimization recommendations:

```python
from src.data import DataSourceCoordinator

coordinator = DataSourceCoordinator(...)
recommendations = coordinator.get_optimization_recommendations()

for recommendation in recommendations:
    print(f"💡 {recommendation}")
```

Example recommendations:
- "Low cache hit rate (25%). Consider increasing cache TTL from 5s"
- "WebSocket reliability low (75%). Consider investigating connection stability"
- "High REST usage (80%). Consider improving WebSocket reliability"

## 🔧 Configuration Options

### Strategic REST Client
```python
client = StrategicRestClient(
    api_key=api_key,
    private_key=private_key,
    max_batch_size=5,           # Maximum requests per batch
    batch_timeout=2.0,          # Batch processing timeout
    emergency_only=False        # Restrict to emergency operations only
)
```

### Data Validator
```python
validator = RestDataValidator(
    strategic_client=client,
    websocket_manager=ws_manager,
    validation_interval=60.0,    # Seconds between validations
    tolerance_threshold=0.001,   # Numerical comparison tolerance
    max_validation_age=300.0     # Maximum age of validation data
)
```

### Fallback Manager
```python
fallback_manager = RestFallbackManager(
    strategic_client=client,
    websocket_manager=ws_manager,
    health_check_interval=30.0,  # Health check frequency
    recovery_timeout=300.0,      # Maximum recovery time
    max_recovery_attempts=5      # Maximum recovery attempts
)
```

## 🏃‍♂️ Quick Start Example

```python
import asyncio
from src.rest import StrategicRestClient, RestDataValidator, RestFallbackManager
from src.data import DataSourceCoordinator

async def quick_start():
    # Initialize REST client
    client = StrategicRestClient(api_key, private_key)
    await client.initialize()
    
    # Initialize validator and fallback manager
    validator = RestDataValidator(client, websocket_manager)
    fallback_manager = RestFallbackManager(client, websocket_manager)
    
    await validator.initialize()
    await fallback_manager.initialize()
    
    # Start continuous validation
    await validator.start_continuous_validation()
    
    # Create data coordinator for intelligent routing
    coordinator = DataSourceCoordinator(
        websocket_manager=websocket_manager,
        strategic_rest_client=client,
        fallback_manager=fallback_manager
    )
    await coordinator.initialize()
    
    # Get data with automatic source selection
    balance = await coordinator.get_balance()
    ticker = await coordinator.get_ticker_data('SHIBUSDT')
    
    print(f"Balance: {len(balance.get('result', {}))} assets")
    print(f"SHIB ticker retrieved successfully")
    
    # Cleanup
    await validator.stop_continuous_validation()
    await fallback_manager.shutdown()
    await client.shutdown()

# Run the example
asyncio.run(quick_start())
```

## 🧪 Testing and Validation

Run the comprehensive integration example:

```bash
# Set environment variables
export KRAKEN_API_KEY="your_api_key"
export KRAKEN_PRIVATE_KEY="your_private_key"

# Run the integration example
python -m src.rest.integration_example
```

The example demonstrates:
- ✅ Component initialization and coordination
- ✅ Automatic data source selection
- ✅ Performance comparison between sources
- ✅ Real-time data validation
- ✅ Fallback scenario handling
- ✅ Batch operation efficiency
- ✅ Emergency operation capabilities
- ✅ Performance monitoring and optimization

## ⚠️ Important Notes

### Nonce Management
- **Always use unified nonce manager**: Prevents conflicts with WebSocket
- **Respect rate limits**: Circuit breaker protects against overuse
- **Emergency mode**: Automatically enabled during WebSocket failures
- **Batch operations**: Preferred method for multiple requests

### Security Considerations
- **API key protection**: Same security as main trading system
- **Request validation**: All parameters validated before execution
- **Error handling**: Comprehensive error handling prevents information leakage
- **Audit logging**: All operations logged for security audit

### Performance Guidelines
- **WebSocket First**: Always prefer WebSocket for real-time data
- **REST for Historical**: Use REST for historical data and validation
- **Cache Effectively**: 3-5 second cache TTL optimal for most data
- **Monitor Performance**: Regular health checks and optimization

This REST implementation provides a robust, strategic approach to API usage that complements the WebSocket V2 system while ensuring reliable data access and emergency fallback capabilities.