# Kraken Trading Bot 2025 - Launch Guide

Comprehensive guide for launching and operating the advanced cryptocurrency trading bot with all 2025 enhancements.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Pre-Launch Checklist](#pre-launch-checklist)
3. [Launch Methods](#launch-methods)
4. [System Verification](#system-verification)
5. [Monitoring & Operations](#monitoring--operations)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Operations](#advanced-operations)

## Quick Start

### For Immediate Launch (Experienced Users)

**Windows:**
```batch
# Primary production launcher
START_BOT_OPTIMIZED.bat

# Alternative with enhanced monitoring
START_WITH_MONITORING.bat
```

**Linux/WSL:**
```bash
# Quick production launch
python main.py

# Advanced launch with full diagnostics
python scripts/live_launch.py

# Paper trading mode (safe testing)
python scripts/paper_trading_launcher.py
```

### For First-Time Users

1. **Complete system setup** (see Pre-Launch Checklist below)
2. **Test API connection**: `python scripts/test_kraken_connection.py`
3. **Run paper trading**: `python scripts/paper_trading_launcher.py`
4. **Launch production**: `python main.py`

## Pre-Launch Checklist

### System Requirements Verification

```bash
# Check Python version (3.8+ required)
python --version

# Verify pip and dependencies
pip --version
pip list | grep kraken

# Check disk space (10GB+ recommended on D: drive)
df -h /mnt/d  # Linux/WSL
dir D:\      # Windows

# Verify network connectivity
ping api.kraken.com
```

### API Configuration Setup

1. **Create Kraken API Key**:
   - Visit: https://www.kraken.com/u/security/api
   - Create new API key with **trading permissions only**
   - **DO NOT** enable withdrawal permissions
   - Copy API key and secret

2. **Configure Environment**:
   ```bash
   # Create .env file (if not exists)
   echo "KRAKEN_API_KEY=your_api_key_here" > .env
   echo "KRAKEN_API_SECRET=your_api_secret_here" >> .env
   
   # Verify configuration
   python scripts/test_kraken_connection.py
   ```

3. **Validate API Tier**:
   ```bash
   # Check your Kraken API tier limits
   python scripts/verify_kraken_compliance.py
   ```

### Balance and Trading Setup

1. **Minimum Balance Requirements**:
   - **Production**: $20+ USDT recommended
   - **Testing**: $5+ USDT minimum
   - **Paper Trading**: No real funds required

2. **Verify Account Balance**:
   ```bash
   # Check current USDT balance
   python scripts/check_balance_simple.py
   
   # Comprehensive balance check
   python scripts/comprehensive_balance_test.py
   ```

3. **Trading Pair Configuration**:
   ```bash
   # Verify available trading pairs
   python scripts/check_usdt_pairs.py
   
   # Test minimum order sizes
   python scripts/test_integration.py
   ```

## Launch Methods

### Method 1: Production Launch (Recommended)

**Primary Entry Point:**
```bash
# Full production launch with all features
python main.py
```

**Features Enabled:**
- Real-time WebSocket V2 data feeds
- AI-driven signal generation
- Automated profit harvesting
- Self-healing error recovery
- Comprehensive logging
- Performance optimization

**System Output:**
```
[INIT] Starting Kraken Trading Bot 2025...
[CONFIG] Loaded configuration: config.json
[EXCHANGE] Initializing Kraken SDK connection...
[WEBSOCKET] Starting WebSocket V2 feeds...
[LEARNING] Loading AI learning systems...
[TRADING] Initializing trading components...
[SYSTEM] Bot ready for autonomous operation
```

### Method 2: Advanced Launch with Monitoring

```bash
# Launch with enhanced monitoring and diagnostics
python scripts/live_launch.py
```

**Additional Features:**
- Real-time system diagnostics
- Performance monitoring dashboard
- Enhanced error reporting
- Automatic log rotation
- System health alerts

### Method 3: Paper Trading Mode

```bash
# Safe simulation mode (no real trading)
python scripts/paper_trading_launcher.py
```

**Benefits:**
- Test strategies without risk
- Validate system performance
- Debug configuration issues
- Training and evaluation

### Method 4: Development Mode

```bash
# Development launch with debugging
python scripts/dev_launch.py
```

**Features:**
- Enhanced debug logging
- Development-specific configurations
- Mock data generation
- Testing utilities

## System Verification

### Initial System Check

```bash
# Run comprehensive system diagnostics
python scripts/run_diagnostic_with_env.py

# Quick system health check
python scripts/quick_check.py

# Verify all components
python scripts/check_bot_ready.py
```

### Expected Startup Sequence

1. **Configuration Loading** (5-10 seconds)
   ```
   [CONFIG] Loading configuration from config.json
   [CONFIG] Validating trading pairs and parameters
   [CONFIG] Environment variables loaded successfully
   ```

2. **Exchange Connection** (10-15 seconds)
   ```
   [EXCHANGE] Connecting to Kraken API...
   [EXCHANGE] Authentication successful
   [EXCHANGE] Market data initialization complete
   [WEBSOCKET] WebSocket V2 connection established
   ```

3. **Component Initialization** (15-20 seconds)
   ```
   [BALANCE] Balance manager initialized
   [SCANNER] Opportunity scanner ready
   [EXECUTOR] Trade executor with AI assistants loaded
   [LEARNING] Neural pattern engine active
   ```

4. **Ready State** (20-30 seconds total)
   ```
   [SYSTEM] All systems operational
   [TRADING] Autonomous trading mode active
   [MONITOR] Performance monitoring enabled
   ```

### Verification Commands

```bash
# Check if bot is running correctly
python scripts/check_bot_status.py

# Verify trading functionality
python scripts/test_trading_functionality.py

# Monitor system performance
python scripts/monitor_bot.py
```

## Monitoring & Operations

### Real-Time Monitoring

**Dashboard Access:**
```bash
# Start web dashboard (if available)
cd dashboard/backend && python main.py
# Access: http://localhost:8000
```

**Log Monitoring:**
```bash
# Follow main bot logs
tail -f D:/trading_data/logs/bot_$(date +%Y%m%d).log

# Monitor critical events
grep -i "ERROR\|WARNING\|PROFIT" D:/trading_data/logs/*.log

# Real-time log viewer
python scripts/utilities/check_bot_status.py --follow
```

### Key Performance Indicators

**Trading Activity:**
- **Signal Generation**: 20-50 signals per hour
- **Trade Execution**: 5-15 trades per day
- **Success Rate**: 65-75% profitable trades
- **Average Profit**: 0.3-0.8% per successful trade

**System Health:**
- **API Response Time**: <500ms average
- **Memory Usage**: <400MB typical
- **CPU Usage**: <15% typical
- **Error Rate**: <1% of operations

**Financial Metrics:**
- **Capital Deployment**: 80-95% of available balance
- **Daily Return**: 0.5-2.0% typical range
- **Maximum Drawdown**: <5% with risk controls
- **Sharpe Ratio**: >1.5 target

### Success Indicators in Logs

```bash
# Successful signal generation
[SCANNER] Opportunity detected: SHIB/USDT +0.6% potential

# Successful trade execution
[EXECUTOR] Order filled: BUY 1000 SHIB/USDT @ 0.00001234

# Profit harvesting
[HARVESTER] Profit captured: +0.4% on ADA/USDT position

# Learning system updates
[LEARNING] Pattern learned: Morning breakout +0.7% avg

# System optimization
[OPTIMIZER] Rate limit efficiency: 94% API utilization
```

## Troubleshooting

### Common Issues and Solutions

#### 1. API Connection Problems

**Symptoms:**
```
[ERROR] Failed to connect to Kraken API
[ERROR] Authentication failed
```

**Solutions:**
```bash
# Test API credentials
python scripts/test_kraken_connection.py

# Verify API key permissions
python scripts/verify_api_security.py

# Reset API nonce
python scripts/reset_nonce.py
```

#### 2. Rate Limiting Issues

**Symptoms:**
```
[WARNING] Rate limit exceeded
[ERROR] API call frequency too high
```

**Solutions:**
```bash
# Check rate limit status
python scripts/rate_limit_recovery.py

# Optimize rate limit settings
python scripts/test_rate_limit_fixes.py

# Wait for reset (usually 1-3 hours)
```

#### 3. Balance Detection Problems

**Symptoms:**
```
[ERROR] Insufficient funds for trade
[WARNING] Balance mismatch detected
```

**Solutions:**
```bash
# Force balance refresh
python scripts/force_refresh_balance.py

# Fix balance detection
python scripts/fix_balance_detection.py

# Emergency balance sync
python scripts/emergency_balance_fix.py
```

#### 4. WebSocket Connection Issues

**Symptoms:**
```
[ERROR] WebSocket connection lost
[WARNING] Data feed interrupted
```

**Solutions:**
```bash
# Test WebSocket connection
python scripts/test_websocket_v2.py

# Fix authentication
python scripts/fix_websocket_auth.py

# Restart with fallback mode
python scripts/force_launch.py --no-websocket
```

### Emergency Procedures

#### Emergency Stop
```bash
# Immediate bot shutdown
python scripts/emergency_cleanup.py

# Kill all bot processes
scripts/KILL_ALL_BOTS.bat  # Windows
pkill -f "python.*main.py"  # Linux
```

#### Emergency Position Liquidation
```bash
# Sell all positions immediately
python scripts/emergency_sell.py

# Manual position liquidation
python scripts/manual_sell_positions.py

# Check liquidation status
python scripts/utilities/show_real_portfolio.py
```

#### System Recovery
```bash
# Full system cleanup and restart
python scripts/emergency_reset.py

# Repair corrupted data
python scripts/comprehensive_manual_cleanup.py

# Restart with clean state
python main.py --clean-start
```

## Advanced Operations

### Custom Configuration

**Create Custom Config:**
```bash
# Copy default configuration
cp config.json config_custom.json

# Edit configuration
nano config_custom.json

# Launch with custom config
python main.py --config config_custom.json
```

**Configuration Options:**
```json
{
  "trading_pairs": ["SHIB/USDT", "DOGE/USDT", "ADA/USDT"],
  "position_size_usdt": 10.0,
  "max_positions": 5,
  "profit_target": 0.005,
  "stop_loss": 0.008,
  "learning_enabled": true,
  "aggressive_mode": false
}
```

### Multi-Instance Deployment

```bash
# Launch multiple instances with different configs
python main.py --config config_shib.json --instance shib &
python main.py --config config_doge.json --instance doge &
python main.py --config config_ada.json --instance ada &

# Monitor all instances
python scripts/monitor_all_instances.py
```

### Performance Optimization

```bash
# Enable high-performance mode
python main.py --performance-mode

# Optimize for specific trading pairs
python scripts/optimize_for_pairs.py --pairs SHIB/USDT,DOGE/USDT

# Enable advanced learning
python main.py --enable-neural-optimization
```

### Backup and Recovery

```bash
# Create system backup
python scripts/create_backup.py

# Restore from backup
python scripts/restore_backup.py --backup-file backup_20250730.tar.gz

# Migrate data to new system
python scripts/migrate_data_to_d_drive.py
```

## Launch Checklist

### Pre-Launch (Every Time)
- [ ] Verify internet connection
- [ ] Check Kraken API status
- [ ] Confirm sufficient USDT balance
- [ ] Review current market conditions
- [ ] Check system resources (disk space, memory)

### Launch Execution
- [ ] Run system diagnostics
- [ ] Launch bot with appropriate method
- [ ] Verify successful initialization
- [ ] Monitor first few trades
- [ ] Confirm all systems operational

### Post-Launch Monitoring
- [ ] Monitor logs for errors
- [ ] Track trading performance
- [ ] Verify balance updates
- [ ] Check system health metrics
- [ ] Review AI learning progress

---

**Launch Status**: Production Ready
**Last Updated**: July 30, 2025
**Version**: 2.1.0
**Support**: Check troubleshooting_guide.md for additional help
