# Kraken Trading Bot 2025 - Comprehensive Troubleshooting Guide

This guide provides systematic solutions for all common issues encountered with the advanced trading bot, including diagnostic procedures, recovery methods, and preventive measures.

## Table of Contents
1. [Emergency Procedures](#emergency-procedures)
2. [API and Connection Issues](#api-and-connection-issues)
3. [Trading and Execution Problems](#trading-and-execution-problems)
4. [Balance and Portfolio Issues](#balance-and-portfolio-issues)
5. [WebSocket and Data Issues](#websocket-and-data-issues)
6. [Performance and Resource Problems](#performance-and-resource-problems)
7. [Learning System Issues](#learning-system-issues)
8. [Diagnostic Tools](#diagnostic-tools)
9. [Prevention and Best Practices](#prevention-and-best-practices)

## Emergency Procedures

### Immediate Bot Shutdown

**When to Use:**
- Unexpected losses exceeding 5%
- System behaving erratically
- API credentials compromised
- Market emergency conditions

**Emergency Stop Commands:**
```bash
# Immediate shutdown (preferred)
python scripts/emergency_cleanup.py

# Force kill all processes (if unresponsive)
scripts/KILL_ALL_BOTS.bat  # Windows
pkill -f "python.*main.py"  # Linux

# Emergency position liquidation
python scripts/emergency_sell.py
```

### Circuit Breaker Recovery

**Symptoms:**
```
[EMERGENCY] Circuit breaker triggered - Drawdown: 8.5%
[SAFETY] All trading suspended
[CIRCUIT] Emergency shutdown initiated
```

**Recovery Steps:**
```bash
# 1. Check current status
python scripts/check_portfolio_status.py

# 2. Review what caused the trigger
grep -i "circuit\|emergency\|drawdown" D:/trading_data/logs/*.log | tail -20

# 3. Verify all positions
python scripts/utilities/show_real_portfolio.py

# 4. Reset circuit breaker (only after review)
python scripts/reset_circuit_breaker.py

# 5. Restart with reduced risk
python main.py --conservative-mode
```

### Portfolio Emergency Liquidation

```bash
# Sell all positions immediately
python scripts/emergency_liquidation.py

# Manual position-by-position liquidation
python scripts/manual_sell_positions.py

# Check liquidation progress
python scripts/utilities/verify_live_trading.py
```

## API and Connection Issues

### Issue 1: API Authentication Failures

**Symptoms:**
```
[ERROR] Authentication failed: Invalid API credentials
[ERROR] API signature verification failed
[KRAKEN] 401 Unauthorized response
```

**Diagnostic Steps:**
```bash
# Test API credentials
python scripts/test_kraken_connection.py

# Verify API key format
python scripts/verify_api_security.py

# Check API permissions
python scripts/check_credentials.py
```

**Solutions:**
1. **Verify API Key Setup:**
   ```bash
   # Check .env file
   cat .env
   
   # Expected format:
   KRAKEN_API_KEY=your_64_character_key
   KRAKEN_API_SECRET=your_88_character_secret
   ```

2. **Recreate API Key:**
   - Visit https://www.kraken.com/u/security/api
   - Delete old API key
   - Create new key with permissions:
     - Query Funds ✓
     - Query Open Orders & Trades ✓
     - Query Closed Orders & Trades ✓
     - Create & Modify Orders ✓
     - WebSocket - Display Balances ✓
   - Update .env file

3. **Test New Credentials:**
   ```bash
   python scripts/setup_new_keys.py
   python scripts/test_new_api_keys.py
   ```

### Issue 2: Rate Limiting

**Symptoms:**
```
[WARNING] Rate limit exceeded: 180/180 points used
[ERROR] API call rejected: Rate limit
[LIMITER] Backing off for 300 seconds
```

**Immediate Solutions:**
```bash
# Check current rate limit status
python scripts/rate_limit_recovery.py

# Wait for automatic recovery (recommended)
# Rate limits reset every 3 hours

# Force restart with conservative settings
python main.py --low-frequency-mode
```

**Long-term Solutions:**
1. **Upgrade Kraken Account Tier:**
   - Starter: 60 calls/hour
   - Intermediate: 125 calls/hour
   - Pro: 180 calls/hour

2. **Optimize API Usage:**
   ```bash
   # Enable advanced rate limiting
   python scripts/test_rate_limit_fixes.py
   
   # Check API efficiency
   python scripts/check_api_usage.py
   ```

### Issue 3: Network Connectivity

**Symptoms:**
```
[ERROR] Connection timeout to api.kraken.com
[ERROR] Network unreachable
[WEBSOCKET] Connection lost, attempting reconnect
```

**Diagnostic Commands:**
```bash
# Test network connectivity
ping api.kraken.com
ping ws.kraken.com

# Test DNS resolution
nslookup api.kraken.com

# Check firewall/proxy settings
curl -I https://api.kraken.com/0/public/Time
```

**Solutions:**
```bash
# Test with fallback endpoints
python scripts/test_kraken_connection.py --fallback

# Use proxy if needed
python main.py --proxy http://your-proxy:port

# Enable offline mode for diagnostics
python scripts/validation_test_no_api.py
```

## Trading and Execution Problems

### Issue 4: Orders Failing to Execute

**Symptoms:**
```
[ERROR] Order rejected: Insufficient funds
[ERROR] Order rejected: Minimum order size not met
[EXECUTOR] Failed to place order for SHIB/USDT
```

**Diagnostic Steps:**
```bash
# Check account balance
python scripts/check_balance_simple.py

# Verify minimum order sizes
python scripts/check_trading_minimums.py

# Test order placement
python scripts/test_trading_functionality.py
```

**Solutions:**
1. **Insufficient Funds:**
   ```bash
   # Check available balance
   python scripts/comprehensive_balance_test.py
   
   # Liquidate stuck positions
   python scripts/manual_sell_positions.py
   
   # Refresh balance cache
   python scripts/force_refresh_balance.py
   ```

2. **Minimum Order Size Issues:**
   ```bash
   # Update minimum configurations
   python scripts/apply_low_minimum_config.py
   
   # Test with current minimums
   python scripts/test_integration.py
   ```

3. **Symbol/Pair Issues:**
   ```bash
   # Fix symbol mapping
   python scripts/fix_symbol_issues.py
   
   # Check available pairs
   python scripts/check_usdt_pairs.py
   ```

### Issue 5: Strategy Performance Problems

**Symptoms:**
```
[WARNING] Strategy win rate below 60%
[PERFORMANCE] Consecutive losses: 5
[STRATEGY] Low signal confidence detected
```

**Analysis Tools:**
```bash
# Performance analysis
python scripts/status_report.py

# Strategy health check
python scripts/test_autonomous_sell_engine.py

# Learning system status
python scripts/test_learning_system.py
```

**Solutions:**
```bash
# Reset learning system
python scripts/test_dynamic_learning.py --reset

# Switch to conservative strategy
python main.py --strategy conservative

# Enable paper trading for testing
python scripts/paper_trading_launcher.py
```

## Balance and Portfolio Issues

### Issue 6: Balance Synchronization Problems

**Symptoms:**
```
[ERROR] Balance mismatch: Expected 25.5 USDT, Got 23.1 USDT
[WARNING] Portfolio state inconsistent
[BALANCE] Cache refresh failed on attempt 3
```

**Diagnostic Steps:**
```bash
# Check balance synchronization
python scripts/trace_balance_flow.py

# Compare with Kraken directly
python scripts/check_balance_simple.py --compare-kraken

# Test balance detection fixes
python scripts/test_balance_and_volume_fixes.py
```

**Solutions:**
```bash
# Emergency balance sync
python scripts/emergency_balance_fix.py

# Clear balance cache
python scripts/clear_portfolio_cache.py

# Fix balance detection system
python scripts/fix_balance_detection.py

# Restart with clean state
python main.py --reset-portfolio
```

### Issue 7: Position Tracking Errors

**Symptoms:**
```
[ERROR] Position not found in tracker
[WARNING] Entry price missing for SHIB/USDT
[PORTFOLIO] State file corrupted
```

**Recovery Steps:**
```bash
# Rebuild position tracking
python tools/rebuild_position_tracking.py

# Fix entry prices
python tools/add_entry_prices.py

# Verify position accuracy
python tools/check_positions.py
```

## WebSocket and Data Issues

### Issue 8: WebSocket Connection Problems

**Symptoms:**
```
[WEBSOCKET] Authentication failed
[WEBSOCKET_V2] Connection timeout
[DATA] Stale price data detected
```

**Diagnostic Commands:**
```bash
# Test WebSocket connection
python scripts/test_websocket_v2.py

# Check authentication
python scripts/test_websocket_auth.py

# Visual WebSocket demo
python scripts/visual_websocket_demo.py
```

**Solutions:**
```bash
# Fix WebSocket authentication
python scripts/fix_websocket_auth.py

# Enable fallback data sources
python main.py --no-websocket

# Test WebSocket integration
python scripts/test_websocket_integration.py
```

### Issue 9: Data Feed Interruptions

**Symptoms:**
```
[DATA] No price updates for 30 seconds
[FEED] Fallback to REST API activated
[MARKET] Data staleness detected
```

**Solutions:**
```bash
# Check data source health
python scripts/check_websocket.py

# Test multi-source data
python scripts/test_integration.py --data-sources

# Enable visual monitoring
python scripts/websocket_v2_explorer.py
```

## Performance and Resource Problems

### Issue 10: High Memory Usage

**Symptoms:**
```
[SYSTEM] Memory usage: 1.2GB (Warning threshold: 800MB)
[PERFORMANCE] Garbage collection frequency high
```

**Solutions:**
```bash
# Check memory usage
python scripts/monitor_bot.py --memory

# Clean up memory leaks
python scripts/cleanup_duplicates.py

# Restart with memory optimization
python main.py --memory-optimized
```

### Issue 11: CPU Performance Issues

**Symptoms:**
```
[PERFORMANCE] CPU usage: 85% (sustained)
[SYSTEM] Response time degraded
```

**Solutions:**
```bash
# Performance profiling
python scripts/stress_test.py

# Optimize performance
python scripts/test_rate_limit_fixes.py --optimize

# Enable performance mode
python main.py --performance-mode
```

## Learning System Issues

### Issue 12: AI Learning System Errors

**Symptoms:**
```
[LEARNING] Pattern recognition failed
[AI] Neural engine unresponsive
[MEMORY] Learning data corrupted
```

**Solutions:**
```bash
# Test learning system
python scripts/test_learning_system.py

# Reset AI components
python scripts/test_dynamic_learning.py --reset-ai

# Rebuild learning data
python scripts/sync_agent_state.py
```

## Diagnostic Tools

### Comprehensive System Diagnostics

```bash
# Full system health check
python scripts/run_diagnostic_with_env.py

# Quick status check
python scripts/quick_check.py

# Component-specific diagnostics
python scripts/diagnose_signals.py
python scripts/test_bot_startup.py
python scripts/verify_ready.py
```

### Log Analysis Tools

```bash
# Real-time log monitoring
tail -f D:/trading_data/logs/bot_$(date +%Y%m%d).log

# Error analysis
grep -i "error" D:/trading_data/logs/*.log | tail -50

# Performance metrics
grep -i "profit\|loss\|trade" D:/trading_data/logs/*.log | tail -100

# System warnings
grep -i "warning\|circuit\|rate limit" D:/trading_data/logs/*.log | tail -30
```

### Performance Monitoring

```bash
# Trading performance
python scripts/checks/check_positions_and_profits.py
python scripts/checks/check_snowball_profits.py

# System performance
python scripts/monitor_bot.py --performance
python scripts/utilities/check_bot_status.py
```

## Prevention and Best Practices

### Daily Maintenance Checklist

- [ ] **System Health Check**
  ```bash
  python scripts/quick_check.py
  ```

- [ ] **Balance Verification**
  ```bash
  python scripts/check_balance_simple.py
  ```

- [ ] **Performance Review**
  ```bash
  python scripts/status_report.py
  ```

- [ ] **Log Analysis**
  ```bash
  grep -i "error\|warning" D:/trading_data/logs/*.log | tail -20
  ```

- [ ] **API Rate Limit Check**
  ```bash
  python scripts/rate_limit_recovery.py --status
  ```

### Risk Management Best Practices

1. **Position Sizing**
   - Start with $5-10 per trade
   - Never exceed 20% of balance per position
   - Use dynamic position sizing based on volatility

2. **Stop Loss Management**
   - Always set stop losses (recommended: 0.8%)
   - Use trailing stops for profitable positions
   - Monitor drawdown carefully

3. **API Management**
   - Monitor rate limit usage
   - Use appropriate account tier
   - Keep backup API keys ready

### Configuration Optimization

```json
{
  "risk_management": {
    "max_position_size_percent": 15,
    "stop_loss_percent": 0.8,
    "max_daily_drawdown": 5.0,
    "circuit_breaker_threshold": 8.0
  },
  "performance": {
    "balance_cache_duration": 10,
    "api_call_interval": 2,
    "websocket_timeout": 30,
    "memory_cleanup_interval": 300
  }
}
```

### Monitoring and Alerting

```bash
# Set up automated monitoring
python scripts/setup_enhanced_logging.py

# Enable performance alerts
python scripts/monitor_bot.py --alerts

# Create monitoring dashboard
cd dashboard && python backend/main.py
```

## Recovery Procedures

### Complete System Recovery

```bash
# 1. Emergency shutdown
python scripts/emergency_cleanup.py

# 2. Backup current state
python scripts/create_backup.py

# 3. Clean system state
python scripts/comprehensive_manual_cleanup.py

# 4. Verify system integrity
python scripts/run_diagnostic_with_env.py

# 5. Restart with clean configuration
python main.py --clean-start

# 6. Monitor for stability
python scripts/monitor_bot.py --duration 3600
```

### Data Recovery

```bash
# Recover trading data
python scripts/migrate_data_to_d_drive.py --recover

# Rebuild corrupted files
python scripts/cleanup_duplicates.py --rebuild

# Restore from backup
python scripts/restore_backup.py --latest
```

## Support and Resources

### Internal Resources
- **Documentation**: `/docs/` folder
- **Scripts**: `/scripts/` folder
- **Logs**: `D:/trading_data/logs/`
- **Configuration**: `config.json`, `.env`

### External Resources
- **Kraken API Documentation**: https://docs.kraken.com/rest/
- **Kraken Support**: https://support.kraken.com
- **API Status Page**: https://status.kraken.com
- **WebSocket Documentation**: https://docs.kraken.com/websockets/

### Emergency Contacts
- **System Issues**: Check GitHub repository
- **API Issues**: Kraken support team
- **Account Issues**: Kraken customer service

---

**Troubleshooting Guide Version**: 2.1.0
**Last Updated**: July 30, 2025
**Status**: Comprehensive coverage of all known issues