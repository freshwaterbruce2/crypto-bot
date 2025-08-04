# WebSocket V2 Pipeline Integration Guide

## Overview

The Unified WebSocket V2 Data Pipeline provides a high-performance, scalable routing system for all WebSocket streams in the crypto trading bot. It efficiently distributes real-time data to appropriate components with priority-based routing, message queuing, and comprehensive monitoring.

## Key Features

- **Priority-based message routing** with configurable queues
- **Real-time data transformation** and format conversion
- **Component coordination** with balance managers and trading engines
- **Memory-efficient processing** with configurable buffer limits
- **Comprehensive error handling** and circuit breaker integration
- **Performance monitoring** and metrics collection
- **Message deduplication** and validation
- **Async processing** with backpressure management

## Architecture

```
WebSocket V2 Manager
         ↓
Unified Data Pipeline
    ↓         ↓         ↓
Balance    Trading   Strategy
Manager    Engine    Manager
```

## Quick Start

### Basic Setup

```python
from src.exchange.websocket_pipeline_init import quick_setup_pipeline

# Initialize pipeline with existing components
success, initializer = await quick_setup_pipeline(websocket_manager, bot_instance)

if success:
    print("Pipeline initialized successfully!")
    # Pipeline is now routing all WebSocket data
else:
    print("Pipeline initialization failed")
```

### Advanced Setup

```python
from src.exchange.websocket_pipeline_init import WebSocketPipelineInitializer
from src.exchange.unified_websocket_data_pipeline import MessageQueueConfig, PerformanceConfig
from src.exchange.websocket_pipeline_monitor import AlertConfig

# Custom configurations
queue_config = MessageQueueConfig(
    max_size=2000,
    timeout_seconds=0.5,
    enable_deduplication=True
)

performance_config = PerformanceConfig(
    enable_metrics=True,
    max_processing_time_ms=10.0
)

alert_config = AlertConfig(
    max_latency_ms=50.0,
    max_error_rate_percent=5.0
)

# Initialize with custom settings
initializer = WebSocketPipelineInitializer(websocket_manager, bot_instance)
success = await initializer.initialize_complete_pipeline(
    queue_config=queue_config,
    performance_config=performance_config,
    alert_config=alert_config,
    enable_monitoring=True
)
```

## Component Integration

### Automatic Discovery

The pipeline automatically discovers and registers these components from your bot instance:

- **Balance Manager** (`bot.balance_manager`)
- **Balance Manager V2** (`bot.balance_manager_v2`)
- **Trade Executor** (`bot.trade_executor`)
- **Strategy Manager** (`bot.strategy_manager`)
- **Functional Strategy Manager** (`bot.functional_strategy_manager`)
- **Critical Error Guardian** (`bot.critical_error_guardian`)
- **Opportunity Scanner** (`bot.opportunity_scanner`)
- **HFT Signal Processor** (`bot.hft_signal_processor`)
- **Learning Manager** (`bot.learning_manager`)

### Manual Component Registration

```python
# Register custom component
initializer.integrator.register_additional_component(
    name="my_custom_analyzer",
    component=my_analyzer,
    channels=["ticker", "orderbook", "balances"]
)
```

### Component Interface Requirements

Components should implement these methods for automatic routing:

#### Balance Managers
```python
async def process_websocket_update(self, balance_data: Dict[str, Any])
async def _handle_balance_message(self, balance_array: List[Dict])
```

#### Trading Engines
```python
async def update_ticker(self, symbol: str, ticker_data: Dict[str, Any])
async def update_orderbook(self, symbol: str, orderbook_data: Dict[str, Any])
async def process_execution(self, execution_data: Dict[str, Any])
```

#### Strategy Managers
```python
async def on_ticker_update(self, symbol: str, ticker_data: Dict[str, Any])
async def on_ohlc_update(self, symbol: str, ohlc_data: Dict[str, Any])
```

#### Risk Managers
```python
async def process_market_data(self, channel: str, data: Dict[str, Any])
```

#### Custom Components
```python
async def on_{channel}_update(self, data: Dict[str, Any])
# or
async def process_websocket_data(self, channel: str, data: Dict[str, Any])
```

## Data Channels

The pipeline handles these WebSocket V2 channels:

| Channel | Priority | Description | Components |
|---------|----------|-------------|------------|
| `balances` | CRITICAL | Account balance updates | Balance Managers |
| `executions` | CRITICAL | Order execution updates | Balance Managers, Trading Engines |
| `ticker` | HIGH | Price ticker updates | Trading Engines, Strategy Managers |
| `book` | HIGH | Order book updates | Trading Engines, Strategy Managers |
| `ohlc` | MEDIUM | OHLC candle data | Strategy Managers |
| `trade` | MEDIUM | Individual trade data | Trading Engines |
| `heartbeat` | LOW | Connection heartbeats | System monitoring |

## Performance Monitoring

### Enable Monitoring

```python
# Monitoring is enabled by default in complete setup
await initializer.initialize_complete_pipeline(enable_monitoring=True)

# Get performance report
if initializer.monitor:
    report = initializer.monitor.get_performance_report()
    print(f"Throughput: {report['current_metrics']['throughput_msgs_per_sec']:.1f} msg/s")
    print(f"Latency: {report['current_metrics']['avg_latency_ms']:.2f}ms")
```

### Performance Metrics

The monitor tracks:
- **Throughput** (messages per second)
- **Latency** (processing time in milliseconds)
- **Memory usage** (RSS memory in MB)
- **Error rates** (percentage of failed messages)
- **Drop rates** (percentage of dropped messages)
- **Queue sizes** (current queue depths)
- **Component health** (component availability)

### Export Performance Data

```python
# Export to JSON file
initializer.monitor.export_performance_data('/path/to/performance_report.json')
```

## Configuration Options

### Message Queue Configuration

```python
MessageQueueConfig(
    max_size=1000,              # Maximum queue size
    timeout_seconds=1.0,        # Processing timeout
    priority_multiplier=2.0,    # Priority scaling factor
    enable_deduplication=True,  # Enable message deduplication
    dedup_window_seconds=0.1    # Deduplication time window
)
```

### Performance Configuration

```python
PerformanceConfig(
    enable_metrics=True,                # Enable performance tracking
    metrics_interval_seconds=30.0,     # Metrics collection interval
    max_processing_time_ms=5.0,        # Alert threshold for processing time
    enable_latency_tracking=True,      # Track processing latency
    memory_usage_threshold_mb=100.0    # Memory usage alert threshold
)
```

### Alert Configuration

```python
AlertConfig(
    max_latency_ms=50.0,               # Maximum acceptable latency
    max_memory_mb=500.0,               # Maximum acceptable memory usage
    max_error_rate_percent=5.0,        # Maximum acceptable error rate
    max_drop_rate_percent=2.0,         # Maximum acceptable drop rate
    min_throughput_msgs_per_sec=1.0,   # Minimum expected throughput
    queue_size_warning_threshold=1500, # Queue size warning level
    queue_size_critical_threshold=1800 # Queue size critical level
)
```

## Performance Modes

### Basic Mode
- Lightweight setup without monitoring
- Suitable for testing or resource-constrained environments

```python
await initializer.initialize_basic_pipeline()
```

### Balanced Mode (Default)
- Standard configuration with monitoring
- Good balance of performance and resource usage

```python
await initializer.initialize_complete_pipeline()
```

### High-Performance Mode
- Optimized for maximum throughput and low latency
- Uses more system resources

```python
await initializer.initialize_high_performance_pipeline()
```

## Error Handling

The pipeline provides comprehensive error handling:

- **Circuit breaker protection** prevents cascade failures
- **Automatic retry mechanisms** for transient failures
- **Dead letter queues** for failed messages
- **Graceful degradation** when components fail
- **Health monitoring** with automatic alerts

## Integration with Existing Code

### WebSocket Manager Integration

The pipeline integrates seamlessly with existing WebSocket managers:

```python
# The pipeline automatically overrides message handling
# No changes needed to existing WebSocket manager code

# Original callback system still works
websocket_manager.set_callback('ticker', my_ticker_callback)

# Pipeline processes messages first, then calls original callbacks
```

### Balance Manager Integration

```python
# Pipeline automatically injects balance updates
# Balance managers receive real-time updates via:
# - process_websocket_update()
# - _handle_balance_message()

# Existing REST fallback still works
balance = await balance_manager.get_balance('USDT')
```

### Trading Engine Integration

```python
# Pipeline routes market data to trading engines
# Engines receive updates via:
# - update_ticker()
# - update_orderbook()
# - process_execution()

# Existing order placement still works
await trading_engine.place_order(symbol, side, amount)
```

## Troubleshooting

### Common Issues

1. **High Latency**
   - Check queue sizes
   - Verify component processing times
   - Consider reducing buffer sizes

2. **Memory Usage**
   - Reduce queue max_size
   - Check for memory leaks in components
   - Enable garbage collection monitoring

3. **High Error Rates**
   - Check component health
   - Verify data format compatibility
   - Review error logs

4. **Message Drops**
   - Increase queue sizes
   - Add more processors
   - Check system resources

### Debug Information

```python
# Get system status
status = initializer.get_system_status()
print(f"Healthy: {initializer.is_healthy()}")

# Get pipeline statistics
stats = initializer.integrator.pipeline.get_pipeline_stats()
print(f"Messages processed: {stats['messages_processed']}")

# Get performance report
if initializer.monitor:
    report = initializer.monitor.get_performance_report()
    print(f"Current metrics: {report['current_metrics']}")
```

### Restart Pipeline

```python
# Restart pipeline if issues occur
success = await initializer.restart_pipeline()
```

## Best Practices

1. **Start with balanced mode** and adjust based on needs
2. **Monitor performance metrics** regularly
3. **Implement proper error handling** in components
4. **Use appropriate queue sizes** for your message volume
5. **Enable monitoring in production** for health tracking
6. **Test component integration** before deployment
7. **Keep component processing fast** to prevent bottlenecks
8. **Use async methods** in all component callbacks

## Example Implementation

See `examples/websocket_pipeline_example.py` for complete working examples of:
- Basic setup
- Advanced configuration
- Custom component integration
- Performance monitoring
- Stress testing

## Migration from Existing Systems

To migrate from existing WebSocket handling:

1. **Initialize the pipeline** with your existing components
2. **Test functionality** with existing callbacks
3. **Gradually remove old callback code** as pipeline takes over
4. **Enable monitoring** to verify performance
5. **Optimize configuration** based on your usage patterns

The pipeline is designed to work alongside existing code, providing a smooth migration path.