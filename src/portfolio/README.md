# Portfolio Management System

A comprehensive portfolio management system for the crypto trading bot that provides real-time position tracking, P&L calculation, risk management, portfolio rebalancing, and performance analytics.

## Features

### 🎯 Core Capabilities
- **Real-time Position Tracking**: Track all positions with entry/exit prices and P&L
- **Risk Management**: Comprehensive risk assessment with automated limits
- **Portfolio Rebalancing**: Multiple rebalancing strategies (DCA, GRID, momentum, etc.)
- **Performance Analytics**: Advanced metrics and reporting
- **Thread-safe Operations**: Concurrent trading support
- **Data Persistence**: All data stored on D: drive for performance

### 📊 Position Tracking
- Real-time P&L calculation (realized and unrealized)
- Position lifecycle management (OPEN, PARTIAL, CLOSED)
- Entry/exit price tracking with cost basis calculation
- Strategy and tag-based position categorization
- Historical position data with performance analysis

### 🛡️ Risk Management
- Real-time risk metric calculation (VaR, Sharpe ratio, drawdown)
- Position size limits and exposure controls
- Volatility-based position sizing
- Drawdown protection and circuit breakers
- Automated risk limit enforcement
- Risk budgeting and allocation

### ⚖️ Portfolio Rebalancing
- **DCA (Dollar Cost Averaging)**: Gradual accumulation strategy
- **GRID Trading**: Systematic buy/sell at predetermined levels
- **Momentum**: Increase allocation to winning positions
- **Mean Reversion**: Reduce allocation to overperforming positions
- **Risk Parity**: Allocate based on inverse volatility
- **Threshold**: Standard drift-based rebalancing

### 📈 Performance Analytics
- Comprehensive performance metrics (returns, volatility, ratios)
- Risk analytics (VaR, drawdowns, correlation analysis)
- Benchmarking against market indices
- Attribution analysis (performance breakdown by asset/strategy)
- Real-time analytics dashboard data
- Export capabilities for reporting

## Quick Start

### Basic Usage

```python
import asyncio
from src.portfolio import PortfolioManager, PortfolioConfig, PositionType

async def basic_example():
    # Configure portfolio
    config = PortfolioConfig(
        target_allocations={
            "BTC/USDT": 0.6,
            "SHIB/USDT": 0.4
        },
        max_single_position_pct=25.0,
        rebalance_enabled=True
    )
    
    # Create portfolio manager
    async with PortfolioManager(config=config) as portfolio:
        # Create position
        position = await portfolio.create_position(
            symbol="SHIB/USDT",
            position_type=PositionType.LONG,
            size=1000000,  # 1M SHIB
            entry_price=0.00001
        )
        
        # Update price
        await portfolio.update_position_price("SHIB/USDT", 0.000012)
        
        # Get summary
        summary = await portfolio.get_portfolio_summary()
        print(f"Portfolio Value: ${summary['total_value']:.2f}")
        print(f"P&L: ${summary['positions']['total_unrealized_pnl']:.2f}")

asyncio.run(basic_example())
```

### Integration with Balance Manager

```python
from src.balance.balance_manager import BalanceManager
from src.portfolio import PortfolioManager

async def integrated_example():
    # Initialize balance manager
    balance_manager = BalanceManager()
    await balance_manager.initialize()
    
    # Create portfolio with balance integration
    portfolio = PortfolioManager(balance_manager=balance_manager)
    await portfolio.initialize()
    
    # Portfolio will automatically sync with balance manager
    summary = await portfolio.get_portfolio_summary()
    print(f"Real Portfolio Value: ${summary['total_value']:.2f}")
```

## Architecture

### Component Overview

```
PortfolioManager (Main Interface)
├── PositionTracker (Position & P&L tracking)
├── RiskManager (Risk assessment & limits)
├── Rebalancer (Portfolio rebalancing strategies)
└── Analytics (Performance metrics & reporting)
```

### Data Flow

1. **Position Creation**: Risk check → Create position → Track P&L
2. **Price Updates**: Update positions → Recalculate P&L → Analytics
3. **Risk Monitoring**: Continuous risk assessment → Limit enforcement
4. **Rebalancing**: Drift detection → Strategy selection → Execution
5. **Analytics**: Performance calculation → Reporting → Export

## Configuration

### Portfolio Strategies

```python
from src.portfolio import PortfolioStrategy, PortfolioConfig

# Conservative strategy
config = PortfolioConfig(
    strategy=PortfolioStrategy.CONSERVATIVE,
    max_single_position_pct=10.0,
    max_drawdown_pct=5.0,
    rebalance_threshold_pct=5.0
)

# Aggressive strategy
config = PortfolioConfig(
    strategy=PortfolioStrategy.AGGRESSIVE,
    max_single_position_pct=50.0,
    max_drawdown_pct=25.0,
    rebalance_threshold_pct=20.0
)
```

### Risk Limits

```python
from src.portfolio.risk_manager import RiskLimits

risk_limits = RiskLimits(
    max_portfolio_risk_pct=2.0,      # Max 2% portfolio risk
    max_single_position_pct=20.0,    # Max 20% single position
    max_drawdown_pct=15.0,           # Max 15% drawdown
    max_positions=10,                # Max 10 concurrent positions
    max_leverage=1.0                 # No leverage
)
```

### Rebalancing Configuration

```python
from src.portfolio.rebalancer import RebalanceConfig, RebalanceStrategy

rebalance_config = RebalanceConfig(
    max_drift_pct=10.0,              # Rebalance when drift > 10%
    rebalance_interval_hours=24.0,   # Daily rebalancing
    max_rebalance_cost_pct=0.5,     # Max 0.5% cost
    dry_run=False                    # Execute trades
)

# Set target allocations
target_allocations = {
    "BTC/USDT": 0.4,    # 40%
    "ETH/USDT": 0.3,    # 30%
    "SHIB/USDT": 0.2,   # 20%
    "ADA/USDT": 0.1     # 10%
}
```

## API Reference

### PortfolioManager

#### Core Methods

```python
# Initialization
await portfolio.initialize()
await portfolio.shutdown()

# Position management
position = await portfolio.create_position(symbol, type, size, price)
success = await portfolio.close_position(position_id, price)
updated = await portfolio.update_position_price(symbol, price)

# Portfolio operations
summary = await portfolio.get_portfolio_summary()
report = await portfolio.get_performance_report()
risk_report = await portfolio.get_risk_report()

# Rebalancing
result = await portfolio.rebalance_portfolio(strategy)
success = await portfolio.set_target_allocations(targets)

# Status management
await portfolio.pause_portfolio()
await portfolio.resume_portfolio()
liquidation = await portfolio.liquidate_portfolio()
```

#### Event Callbacks

```python
# Register event handlers
portfolio.register_callback('position_opened', on_position_opened)
portfolio.register_callback('position_closed', on_position_closed)
portfolio.register_callback('risk_limit_exceeded', on_risk_exceeded)
portfolio.register_callback('rebalance_completed', on_rebalance)
portfolio.register_callback('performance_update', on_performance)
```

### Position Tracking

```python
from src.portfolio.position_tracker import PositionTracker, PositionType

# Create position
position = await tracker.create_position("SHIB/USDT", PositionType.LONG, 1000000, 0.00001)

# Update price
updated = await tracker.update_position_price("SHIB/USDT", 0.000012)

# Close position
realized_pnl = await tracker.close_position_partial(position_id, size, price)

# Get positions
positions = tracker.get_all_open_positions()
closed = tracker.get_closed_positions(symbol="SHIB/USDT", limit=10)
summary = tracker.get_portfolio_summary()
```

### Risk Management

```python
from src.portfolio.risk_manager import RiskManager, RiskAction

# Check position risk
action, reason = await risk_manager.check_position_risk(symbol, size, price)

# Calculate optimal size
sizing = await risk_manager.calculate_optimal_position_size(symbol, price)

# Get risk metrics
metrics = await risk_manager.calculate_risk_metrics()
report = await risk_manager.get_risk_report()
```

### Rebalancing

```python
from src.portfolio.rebalancer import Rebalancer, RebalanceStrategy

# Create rebalance plan
plan = await rebalancer.create_rebalance_plan(RebalanceStrategy.DCA)

# Execute plan
result = await rebalancer.execute_rebalance_plan(plan)

# Auto rebalance
result = await rebalancer.auto_rebalance()

# DCA specific
result = await rebalancer.dca_rebalance("SHIB/USDT", 100.0)
```

### Analytics

```python
from src.portfolio.analytics import PortfolioAnalytics, MetricPeriod

# Performance metrics
metrics = await analytics.calculate_performance_metrics(MetricPeriod.DAILY)
attribution = await analytics.calculate_attribution_analysis(MetricPeriod.MONTHLY)

# Reports
report = await analytics.generate_performance_report()
dashboard = await analytics.get_dashboard_data()

# Export
filepath = await analytics.export_analytics("json")
```

## Data Storage

All data is stored on the D: drive for optimal performance:

```
D:/trading_data/
├── positions.json              # Open positions
├── closed_positions.json       # Closed positions history
├── risk_metrics.json          # Risk metrics
├── risk_violations.json       # Risk violations log
├── rebalance_history.json     # Rebalancing history
├── performance_metrics.json   # Performance data
├── portfolio_config.json      # Configuration
└── analytics/                 # Analytics exports
    ├── portfolio_analytics_20250102_120000.json
    └── ...
```

## Performance Considerations

### Optimizations
- **Thread-safe operations** for concurrent access
- **Intelligent caching** with TTL for expensive calculations
- **Batch updates** for price changes across multiple positions
- **Background processing** for analytics and monitoring
- **Efficient data structures** (deques, dictionaries) for fast access

### Memory Management
- **Limited history** kept in memory (configurable limits)
- **Periodic cleanup** of old data
- **File-based persistence** for long-term storage
- **Lazy loading** of historical data when needed

## Integration Points

### Balance Manager Integration
```python
# Portfolio manager automatically integrates with balance manager
portfolio = PortfolioManager(balance_manager=your_balance_manager)

# Real-time balance synchronization
# Automatic portfolio value calculation
# Cash balance tracking
```

### Trading System Integration
```python
# Integrate with trade executor
portfolio = PortfolioManager(trade_executor=your_trade_executor)

# Automatic position creation from trades
# Risk checking before trade execution
# Rebalancing trade execution
```

### Strategy Integration
```python
# Strategy can use portfolio for position management
class MyStrategy:
    def __init__(self, portfolio_manager):
        self.portfolio = portfolio_manager
    
    async def execute_signal(self, symbol, signal):
        # Check if position creation is allowed
        action, reason = await self.portfolio.risk_manager.check_position_risk(
            symbol, size, price
        )
        
        if action == RiskAction.ALLOW:
            position = await self.portfolio.create_position(
                symbol, PositionType.LONG, size, price, strategy="my_strategy"
            )
```

## Monitoring and Alerts

### Real-time Monitoring
- Portfolio value tracking
- P&L monitoring
- Risk limit monitoring
- Position status updates
- Performance metric updates

### Event System
```python
async def risk_alert_handler(risk_metrics):
    if risk_metrics.overall_risk_level.value == 'critical':
        # Send alert, pause trading, etc.
        await portfolio.pause_portfolio()
        send_emergency_alert(f"Critical risk level: {risk_metrics.risk_score}")

portfolio.register_callback('risk_limit_exceeded', risk_alert_handler)
```

## Testing

Run the integration example:

```bash
cd /mnt/c/dev/tools/crypto-trading-bot-2025
python -m src.portfolio.example_integration
```

This will demonstrate:
- Portfolio initialization
- Position creation and management
- Risk checking and limits
- Rebalancing operations
- Performance analytics
- Event handling
- Data export

## Error Handling

The system includes comprehensive error handling:

- **Graceful degradation** when components fail
- **Automatic retry** for transient failures
- **Circuit breakers** for persistent failures
- **Error callbacks** for custom handling
- **Detailed logging** for debugging

## Future Enhancements

Potential areas for expansion:

1. **Advanced Analytics**
   - Machine learning performance prediction
   - Factor analysis and attribution
   - Custom benchmark integration

2. **Risk Management**
   - Options-based hedging strategies
   - Dynamic correlation analysis
   - Stress testing and scenario analysis

3. **Rebalancing**
   - Black-Litterman optimization
   - Transaction cost analysis
   - Tax-loss harvesting

4. **Integration**
   - Multiple exchange support
   - External data feed integration
   - API for third-party access

## Support

For questions or issues with the portfolio management system:

1. Check the example integration file
2. Review the API documentation above
3. Examine the test files and logs
4. Consult individual component README files