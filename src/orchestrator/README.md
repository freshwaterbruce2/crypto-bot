# System Orchestrator

The System Orchestrator provides centralized coordination, configuration, monitoring, and lifecycle management for all trading bot components.

## Overview

The orchestrator brings together all rebuilt systems:
- Authentication & Credentials
- Rate Limiting
- Circuit Breaker
- REST API Client
- WebSocket V2 Client
- Balance Manager
- Portfolio System
- Data Storage

## Core Components

### 1. System Orchestrator (`system_orchestrator.py`)
Main coordinator that manages all system components with unified initialization and monitoring.

**Features:**
- Coordinated initialization with dependency resolution
- Component lifecycle management
- System-wide diagnostics
- Integration with existing bot architecture

**Usage:**
```python
orchestrator = SystemOrchestrator('config.json')
await orchestrator.initialize()

# Get components
balance_manager = await orchestrator.get_component(UnifiedBalanceManager)
```

### 2. Configuration Manager (`config_manager.py`)
Centralized configuration with validation, environment support, and hot reloading.

**Features:**
- Hierarchical configuration sections
- Environment variable overrides
- Hot configuration reloading
- Configuration validation
- Change notifications

**Usage:**
```python
# Get configuration values
profit_target = orchestrator.config.get('trading.profit_target')

# Update configuration
await orchestrator.update_config('trading.profit_target', 0.007)

# Subscribe to changes
orchestrator.config.subscribe(on_config_change)
```

### 3. Dependency Injector (`dependency_injector.py`)
Manages component dependencies and lifecycle with IoC container.

**Features:**
- Service registration with lifetimes (Singleton, Transient, Scoped)
- Automatic dependency resolution
- Initialization/disposal lifecycle
- Circular dependency detection

**Usage:**
```python
# Register services
injector.register_singleton(BalanceManager, init_method='initialize')
injector.register_transient(TradeExecutor)

# Resolve dependencies
balance_manager = await injector.resolve(BalanceManager)
```

### 4. Health Monitor (`health_monitor.py`)
Monitors all components for health, performance, and automatic recovery.

**Features:**
- Component health tracking
- Automatic recovery procedures
- Alert management
- Performance metrics
- Cascading health checks

**Usage:**
```python
# Register component
orchestrator.health.register_component('websocket')

# Update health status
await orchestrator.health.update_component_status(
    'websocket',
    HealthStatus.HEALTHY,
    {'connected': True, 'latency': 45}
)

# Register recovery handler
orchestrator.health.register_recovery_handler('websocket', recover_websocket)
```

### 5. Startup Sequence (`startup_sequence.py`)
Manages ordered initialization and graceful shutdown.

**Features:**
- Phased startup (Core → Infrastructure → Auth → Network → Services)
- Dependency-ordered initialization
- Retry mechanisms
- Rollback on failure
- Graceful shutdown

**Usage:**
```python
# Register startup steps
startup.register_step(
    name='balance_manager_init',
    phase=StartupPhase.SERVICES,
    handler=initialize_balance_manager,
    dependencies=['rest_api_init'],
    critical=True
)

# Execute startup
success = await startup.startup()
```

## Integration Examples

### 1. Basic Integration
```python
# In main.py
from src.orchestrator import SystemOrchestrator

orchestrator = SystemOrchestrator('config.json')
await orchestrator.initialize()

# System is ready to use
status = orchestrator.get_status()
```

### 2. Trading Bot Integration
```python
from src.orchestrator.bot_integration import OrchestratedTradingBot

bot = OrchestratedTradingBot('config.json')
await bot.run()  # Runs with full orchestration
```

### 3. Running with Dashboard
```python
python main_orchestrated.py --dashboard
```

### 4. Health Check Only
```python
python main_orchestrated.py --health-check
```

### 5. Export Diagnostics
```python
python main_orchestrated.py --diagnostics
```

## Configuration

The orchestrator uses a hierarchical configuration structure:

```json
{
  "system": {
    "debug": false,
    "log_level": "INFO",
    "health_check_interval": 60
  },
  "exchange": {
    "name": "kraken",
    "api_version": "v2"
  },
  "rate_limiting": {
    "tier": "pro",
    "adaptive_mode": true
  },
  "circuit_breaker": {
    "failure_threshold": 5,
    "recovery_timeout": 60
  },
  "trading": {
    "profit_target": 0.005,
    "max_position_size": 100.0
  }
}
```

Environment variables override config values:
```bash
export TRADINGBOT_TRADING_PROFIT_TARGET=0.007
export TRADINGBOT_SYSTEM_DEBUG=true
```

## Monitoring & Diagnostics

### Dashboard View
The interactive dashboard shows:
- System status and health
- Component states
- Performance metrics
- Recent alerts
- Real-time updates

### Simple Diagnostics
```python
from src.orchestrator.diagnostics_dashboard import SimpleDiagnostics

diag = SimpleDiagnostics(orchestrator)
diag.print_status()
await diag.export_report()
```

### Health Monitoring
- Automatic health checks every 60 seconds
- Component-specific health metrics
- Automatic recovery attempts
- Alert notifications

## Benefits

1. **Centralized Management**: All components managed from one place
2. **Dependency Resolution**: Automatic handling of component dependencies
3. **Configuration Management**: Hot-reloadable configuration with validation
4. **Health Monitoring**: Proactive monitoring with automatic recovery
5. **Graceful Lifecycle**: Ordered startup and clean shutdown
6. **Diagnostics**: Comprehensive system diagnostics and reporting
7. **Error Recovery**: Automatic recovery procedures for failures
8. **Performance Tracking**: Real-time performance metrics

## Migration Guide

To migrate existing code to use the orchestrator:

1. Replace direct component initialization with orchestrator
2. Register components with dependency injector
3. Add health checks for critical components
4. Configure startup sequence steps
5. Use configuration manager for all settings

Example migration:
```python
# Old way
exchange = KrakenExchange()
balance_manager = BalanceManager(exchange)
await balance_manager.initialize()

# New way
orchestrator = SystemOrchestrator()
await orchestrator.initialize()
balance_manager = await orchestrator.get_component(BalanceManager)
```

## Troubleshooting

### System Won't Start
- Check logs for initialization errors
- Run diagnostics: `python main_orchestrated.py --diagnostics`
- Verify configuration file exists and is valid

### Component Unhealthy
- Check health monitor alerts
- Review component-specific logs
- Verify dependencies are healthy
- Check recovery handler output

### Configuration Issues
- Verify JSON syntax in config files
- Check environment variable format
- Review configuration validation errors
- Enable debug mode for detailed logs