# Risk Management Improvements

## Date: 2025-07-06

## Overview
Comprehensive risk management system upgrade to protect capital and optimize trading performance.

## New Components

### 1. Unified Risk Manager (`src/trading/unified_risk_manager.py`)
Central risk management system that coordinates all risk decisions:
- **Portfolio Risk Assessment**: Real-time monitoring of total exposure
- **Circuit Breaker**: Multi-level protection (Warning → Caution → Emergency)
- **Dynamic Position Sizing**: Adjusts based on volatility and performance
- **Drawdown Protection**: Tracks and limits maximum drawdown
- **Performance Metrics**: Win rate, profit factor, Sharpe ratio tracking

Key Features:
- Maximum portfolio risk: 50% (reduced from 60%)
- Circuit breaker at 3% drawdown (increased from 1%)
- Emergency shutdown at 10% loss (reduced from 15%)
- Position size reduction after consecutive losses
- Volatility-based position adjustments

### 2. Stop Loss Manager (`src/trading/stop_loss_manager.py`)
Manages actual stop loss orders on Kraken:
- **Places Stop Loss Orders**: Creates real orders on exchange
- **Trailing Stops**: Automatically adjusts stops for profitable positions
- **Order Tracking**: Monitors stop loss execution
- **Integration**: Works with risk manager for coordinated protection

Features:
- Default 2% stop loss
- Trailing activation at 0.5% profit
- Trails by 0.3% distance
- Automatic cancellation on position close

### 3. Volatility Calculator (`src/utils/volatility_calculator.py`)
Advanced volatility analysis for dynamic risk adjustment:
- **ATR Calculation**: Average True Range for volatility measurement
- **Historical Volatility**: Standard deviation of returns
- **Bollinger Width**: Alternative volatility measure
- **Regime Detection**: Low/Normal/High/Extreme volatility states

Position Size Multipliers:
- Low volatility: 1.2x
- Normal volatility: 1.0x
- High volatility: 0.7x
- Extreme volatility: 0.4x

## Configuration Updates

### Risk Parameters (config.json)
```json
"risk_management": {
  "enabled": true,
  "use_unified_risk_manager": true,
  "use_stop_loss_orders": true,
  "use_volatility_sizing": true,
  "max_daily_loss_pct": 5.0,
  "max_consecutive_losses": 3,
  "emergency_shutdown_loss_pct": 10.0,
  "circuit_breaker_cooldown_minutes": 30,
  "trailing_stop_activation_pct": 0.5,
  "trailing_stop_distance_pct": 0.3
}
```

### Adjusted Parameters
- `max_position_pct`: 0.7 (from 0.8)
- `circuit_breaker_drawdown`: 3.0 (from 1.0)
- `position_size_percentage`: 0.7 (from 0.95)
- `max_portfolio_risk`: 0.5 (from 0.6)
- `position_sizing_aggressive`: 0.7 (from 0.85)

## Integration Points

### Trade Executor
The `EnhancedTradeExecutor` now integrates with risk management:
1. Validates all trades through unified risk manager
2. Accepts position size adjustments from risk manager
3. Places stop loss orders automatically on buy trades
4. Updates risk manager on position changes
5. Feeds price data to volatility calculator

### Bot Initialization
Risk components are initialized before trade executor:
1. Create unified risk manager
2. Create stop loss manager
3. Pass both to trade executor
4. Initialize in startup sequence

## Risk Management Flow

1. **Pre-Trade Validation**
   - Check circuit breaker state
   - Validate daily loss limits
   - Calculate position risk
   - Apply volatility adjustments
   - Suggest position size changes

2. **Trade Execution**
   - Execute with adjusted parameters
   - Add position to risk tracking
   - Place stop loss order
   - Update volatility data

3. **Position Management**
   - Monitor unrealized P&L
   - Update trailing stops
   - Track time in position
   - Calculate risk scores

4. **Post-Trade**
   - Update performance metrics
   - Adjust circuit breaker state
   - Track consecutive wins/losses
   - Update equity curve

## Circuit Breaker States

### Normal (Green)
- All systems operational
- Full position sizing
- Normal risk parameters

### Warning (Yellow)
- Drawdown > 2% or 2+ consecutive losses
- Continue trading with caution
- Monitor closely

### Caution (Orange)
- Drawdown > 3%
- Reduce position size by 50%
- Require 3 winning trades to recover

### Emergency (Red)
- Drawdown > 10%
- Stop all trading
- 30-minute cooldown period
- Manual intervention recommended

## Benefits

1. **Capital Protection**
   - Actual stop losses on exchange
   - Multi-level circuit breakers
   - Daily loss limits

2. **Adaptive Sizing**
   - Volatility-based adjustments
   - Performance-based scaling
   - Market regime awareness

3. **Professional Risk Management**
   - Comprehensive metrics tracking
   - Real-time risk monitoring
   - Automated protective actions

## Testing Recommendations

1. Test circuit breaker triggers
2. Verify stop loss order placement
3. Monitor volatility calculations
4. Validate position size adjustments
5. Check risk metric accuracy

## Future Enhancements

1. Correlation risk between positions
2. Options-based hedging
3. Dynamic stop loss based on support/resistance
4. Machine learning for risk prediction
5. Portfolio optimization algorithms