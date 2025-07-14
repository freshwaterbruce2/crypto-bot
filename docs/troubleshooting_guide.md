# Troubleshooting Guide - Kraken Trading Bot

## Common Issues and Solutions

### 1. Circuit Breaker Triggered (Emergency Shutdown)

**Symptoms:**
- `EMERGENCY SHUTDOWN - Drawdown: XX.X%`
- All trades rejected with "Circuit breaker is closed"

**Causes:**
- Portfolio drawdown exceeded emergency threshold (default: 50%)
- Multiple consecutive losses
- Large single loss

**Solutions:**
1. Run the reset script:
   ```bash
   python scripts/reset_circuit_breaker.py
   ```

2. Review what caused the drawdown:
   ```bash
   # Check recent trades
   tail -n 1000 kraken_bot.log | grep -E "(EXECUTE|Trade|Loss)"
   ```

3. Before restarting:
   - Verify account balance on Kraken
   - Check all positions are closed
   - Consider reducing risk parameters

### 2. Balance Refresh Failed

**Symptoms:**
- `[UBM] Balance refresh failed on attempt X`
- Balance showing as $0.00 or stale

**Causes:**
- API rate limit reached
- Network connectivity issues
- Invalid API credentials
- WebSocket permissions not enabled

**Solutions:**
1. Check API credentials:
   ```python
   # Verify in config.json
   {
     "kraken_api_key": "your_key",
     "kraken_api_secret": "your_secret"
   }
   ```

2. Verify API permissions on Kraken:
   - Query Funds
   - Query Open Orders & Trades
   - Query Closed Orders & Trades
   - Create & Modify Orders
   - WebSocket - Display Balances (if using WebSocket)

3. Test connection:
   ```bash
   python scripts/test_rate_limit_fixes.py
   ```

### 3. WebSocket Data Stale

**Symptoms:**
- `[WEBSOCKET_V2] Stale data for symbols: [...]`
- Ticker prices not updating

**Causes:**
- WebSocket connection dropped
- Network interruption
- WebSocket permissions not enabled

**Solutions:**
1. Restart the bot to reconnect WebSocket
2. Check WebSocket permissions on Kraken API key
3. Use fallback mode if WebSocket unavailable

### 4. Missing Method Error

**Symptoms:**
- `AttributeError: 'UnifiedBalanceManager' object has no attribute 'analyze_portfolio_state'`

**Cause:**
- Code version mismatch
- Incomplete update

**Solution:**
- Update has been applied - restart the bot

### 5. API Rate Limit Exceeded

**Symptoms:**
- `API rate limit exceeded`
- Trades failing during execution

**Solutions:**
1. Wait 15 minutes for rate limit reset
2. Ensure balance caching is working:
   - Cache duration: 10 seconds
   - Min refresh interval: 5 seconds
3. Reduce trading frequency

## Monitoring Commands

### Check Bot Status
```bash
# Recent errors
tail -n 100 kraken_bot.log | grep ERROR

# Circuit breaker status
grep "Circuit breaker" kraken_bot.log | tail -n 10

# Balance updates
grep "Balance" kraken_bot.log | tail -n 20

# API rate limit warnings
grep "rate limit" kraken_bot.log | tail -n 20
```

### Performance Metrics
```bash
# Win/loss ratio
grep "Trade result" kraken_bot.log | grep -c "profit"
grep "Trade result" kraken_bot.log | grep -c "loss"

# Recent trades
grep "EXECUTE" kraken_bot.log | tail -n 50
```

## Prevention Tips

1. **Risk Management**
   - Start with minimum position sizes ($2)
   - Set conservative drawdown limits
   - Use tier-appropriate trade sizes

2. **Monitoring**
   - Watch for rate limit warnings
   - Monitor balance updates
   - Check WebSocket connectivity

3. **Configuration**
   - Verify API credentials regularly
   - Keep risk parameters conservative
   - Use appropriate tier settings

## Emergency Contacts

- Kraken Support: https://support.kraken.com
- API Status: https://status.kraken.com
- Bot Issues: Check GitHub repository

## Recovery Checklist

When recovering from circuit breaker:

- [ ] Check Kraken account balance
- [ ] Verify all positions closed
- [ ] Review trade logs for cause
- [ ] Backup current state
- [ ] Reset circuit breaker
- [ ] Start with reduced risk
- [ ] Monitor closely for 1 hour