# Production Deployment Guide

## Quick Start

### 1. Launch Bot with Monitoring
```bash
# Terminal 1: Start the bot
python scripts/live_launch.py

# Terminal 2: Start the monitoring dashboard
python monitor_live_trading.py
```

### 2. Verify Systems are Working
The monitoring dashboard will show:
- **Balance Tracking**: Real-time USDT balance updates
- **Trading Activity**: Live signal generation and trade execution
- **Profit Accumulation**: Snowball effect tracker showing compound growth
- **Precision Monitoring**: Verification that all calculations use Decimal

### 3. Initial Monitoring Checklist
- [ ] Balance shows correct amount (not $1.97)
- [ ] WebSocket ticker data flowing (updates every second)
- [ ] Signals being evaluated (check signal count)
- [ ] Decimal precision active (no float warnings)

## Deployment Phases

### Phase 1: Initial Test (First Hour)
- Start with minimum position size ($1.00)
- Monitor first 10-20 trades
- Verify profit accumulation working
- Check no float precision errors

### Phase 2: Scale Up (After 10 Successful Trades)
- Increase position size to $5.00
- Monitor win rate and profitability
- Ensure balance tracking remains accurate

### Phase 3: Full Production (After 100 Trades)
- Scale to target position size
- Enable all trading pairs
- Monitor performance metrics

## Key Monitoring Points

### Balance Accuracy
```
Expected: $161.39 (or your actual balance)
If showing: $1.97 -> Balance cache issue (should be fixed)
```

### Profit Tracking
```
Target: 0.1-0.3% per trade
Compound Effect: Small profits should accumulate
```

### Error Monitoring
Watch for:
- Rate limit warnings (bot should handle automatically)
- WebSocket disconnections (auto-reconnect enabled)
- Order failures (logged with reasons)

## Troubleshooting

### Bot Not Finding Trades
1. Check WebSocket data is flowing
2. Lower momentum threshold in config.json (currently 0.001)
3. Verify trading pairs have sufficient volume

### Balance Not Updating
1. Check WebSocket balance updates in monitor
2. Force balance refresh: Bot automatically does this before trades
3. Verify API permissions include balance reading

### Profits Not Accumulating
1. Check decimal precision is active (no float warnings)
2. Verify trades are executing (check order confirmations)
3. Monitor spread to ensure profitable entry/exit

## Emergency Controls

### Stop Trading
```bash
# Graceful shutdown
Ctrl+C in bot terminal

# Force stop
pkill -f "python.*live_launch"
```

### Reset State
```bash
# Clear logs and start fresh
rm kraken_bot.log
rm -rf logs/
python scripts/live_launch.py
```

## Performance Optimization

### After 24 Hours
- Review win/loss ratio
- Adjust momentum threshold if needed
- Fine-tune position sizing
- Analyze most profitable pairs

### After 1 Week
- Review accumulated profits
- Optimize trading pair selection
- Adjust risk parameters if needed
- Scale position sizes based on results