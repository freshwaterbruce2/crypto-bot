# Kraken Crypto Trading Bot

**PRODUCTION READY 2025** - An advanced cryptocurrency trading bot optimized for Kraken exchange using fee-free micro-scalping strategies with comprehensive error handling and decimal precision.

## 🎯 Current Strategy: Low-Priced Pair Focus

**DESIGNED FOR BALANCE BUILDING** - The bot prioritizes low-priced altcoins to maximize position sizes with limited capital:

### Priority Pairs (Under $2):
- SHIB/USDT, DOGE/USDT, ADA/USDT, ALGO/USDT, MATIC/USDT, XRP/USDT
- **Avoids expensive pairs** during balance building phase (BTC/ETH skipped)

### Key Features:
- **Decimal Precision Trading**: All calculations use Decimal type for accuracy
- **Enhanced Error Handling**: Fixed format string, nonce, and type comparison errors
- **WebSocket v2 + REST Hybrid**: Multi-source price feeds with automatic failover
- **Smart Position Sizing**: $5-10 trades optimized for small account growth
- **Pro Account Optimized**: Leverages Kraken Pro benefits and fee-free trading

## 🛠️ 2025 Technical Improvements

### Fixed Issues:
- ✅ **Format String Errors**: Added `_ensure_float()` helper for safe formatting
- ✅ **Invalid Nonce Errors**: Proper nonce management with `nonce_manager`
- ✅ **Type Comparison Errors**: Safe decimal handling with `safe_decimal()`
- ✅ **WebSocket Connection**: Hybrid mode with REST API fallback
- ✅ **Balance Type Issues**: Consistent float/decimal handling throughout

### Architecture:
- **Kraken SDK 3.2.2**: Official SDK implementation for 2025
- **Multi-source Data**: WebSocket v2 + CoinGecko + REST API fallback
- **Memory Persistence**: Configuration and learning persist across sessions

## 📋 Prerequisites

- Python 3.8+ with Decimal precision support
- Kraken Pro account with API credentials (NO withdrawal permissions)
- WSL/Ubuntu environment recommended
- Starting balance: $20+ USDT (optimized for small account growth)

## 🛠️ Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/crypto-trading-bot-2025.git
cd crypto-trading-bot-2025
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Create environment file**:
```bash
cp .env.example .env
```

4. **Configure your Kraken API credentials**:

   **CRITICAL**: Your API key must have specific permissions enabled. See complete setup guide:
   📖 **[KRAKEN_API_PERMISSIONS_GUIDE.md](KRAKEN_API_PERMISSIONS_GUIDE.md)**

   **Required Permissions Checklist**:
   - ✅ Query Funds
   - ✅ Access Websockets connection
   - ✅ Create & Modify Orders  
   - ✅ Query Open Orders & Trades
   - ✅ Cancel/Close Orders
   - ❌ Withdraw Funds (NOT recommended)

   **Update your `.env` file**:
   ```bash
   KRAKEN_API_KEY=your_api_key_here
   KRAKEN_API_SECRET=your_api_secret_here
   ```

   **Test your API setup**:
   ```bash
   # Windows
   DIAGNOSE_API.bat
   
   # Linux/WSL
   python diagnose_api_key.py
   ```

## ⚙️ Configuration

The bot is configured through `config.json`. Key settings include:

```json
{
  "exchange": "kraken",
  "position_size_usdt": 0.5,
  "max_order_size_usdt": 1.0, 
  "trade_pairs": [
    "SHIB/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "XRP/USDT",
    "TRX/USDT"
  ],
  "exchange_config": {
    "rate_limit": 180,
    "validate_minimums": true
  },
  "live_trading": true
}
```

## 🚦 Running the Bot

### Production Mode
```bash
# Linux/WSL
python scripts/live_launch.py

# Or use main entry point
python main.py
```

### Windows (Batch Files)
```batch
# Main trading bot
START_BOT_OPTIMIZED.bat

# SHIB-focused trading
START_SHIB_BOT_V2.bat

# Test API connection
TEST_API.bat
```

### Manual Sell Script (Emergency Capital Release)
```bash
python3 scripts/manual_sell_positions.py
```

## 📊 Architecture Overview

```
├── src/
│   ├── core/
│   │   └── bot.py                    # Main bot orchestrator
│   ├── exchange/
│   │   ├── native_kraken_exchange.py # Kraken API wrapper
│   │   └── websocket_manager.py      # WebSocket data streaming
│   ├── trading/
│   │   ├── enhanced_balance_manager.py        # Balance & portfolio management
│   │   ├── enhanced_trade_executor_with_assistants.py  # AI-assisted execution
│   │   ├── portfolio_tracker.py               # Position tracking & persistence
│   │   ├── profit_harvester.py                # Automated profit-taking
│   │   └── opportunity_scanner.py             # Market opportunity detection
│   ├── strategies/
│   │   └── Various trading strategies
│   ├── learning/
│   │   └── ML components for adaptation
│   └── utils/
│       ├── rate_limit_handler.py      # Rate limit management
│       └── kraken_rl.py               # Advanced Kraken rate limiter
```

## 🔄 Trading Flow

1. **Initialization**
   - Connect to Kraken API
   - Load markets and validate trading pairs
   - Initialize portfolio from current holdings
   - Start WebSocket connections

2. **Signal Generation**
   - Opportunity scanner identifies trading opportunities
   - Multiple strategies analyze market conditions
   - Signals are validated and queued

3. **Execution**
   - Trade executor validates orders against:
     - Minimum order size ($5)
     - Available balance
     - Rate limits
     - Risk parameters
   - Orders are placed via Kraken API

4. **Position Management**
   - Portfolio tracker records entry prices
   - Profit harvester monitors positions
   - Automatic selling at profit targets
   - Emergency rebalancing for stale positions

5. **Capital Recycling**
   - Profits are immediately available for new trades
   - Continuous compounding effect

## 🛡️ Safety Features

- **Rate Limit Protection**: Three-layer system prevents API bans
- **Position Size Limits**: Maximum 80% of balance per trade
- **Stop Loss Protection**: 0.8% stop loss on all positions
- **Balance Verification**: Continuous balance checking
- **Emergency Rebalancing**: Automatic position cleanup

## 📈 Production Monitoring System

**NEW: Comprehensive Real-time Monitoring** with web dashboard and health checks:

### Quick Start with Monitoring
```bash
# Launch bot with production monitoring
python launch_with_monitoring.py

# Or use Windows batch file
START_WITH_MONITORING.bat
```

### Dashboard Features
- **Real-time Web Dashboard**: http://localhost:8000
- **Live Health Checks**: Every 5 minutes automated monitoring
- **Performance Metrics**: Trading success rates, P&L tracking, resource usage
- **Alert System**: Configurable thresholds with notifications
- **Emergency Controls**: Manual emergency stop functionality
- **Mobile Responsive**: Access from any device

### Monitored Metrics
- **Trading Performance**: trades_executed, success_rate, total_pnl, daily_pnl
- **System Health**: nonce_failures, websocket_reconnects, api_errors
- **Resource Usage**: memory_usage_mb, log_file_size_mb, cpu_usage
- **Component Health**: balance_manager_health, websocket_status
- **Performance Timings**: trade_execution_time, balance_check_time

### Alert Thresholds
- Memory usage > 500MB
- API error rate > 0.1%
- Trading success rate < 85%
- Daily P&L loss > $50
- WebSocket reconnects > 5/hour

### Configuration Options
```bash
# Production monitoring (aggressive thresholds)
python launch_with_monitoring.py --config production

# Development monitoring (relaxed thresholds)
python launch_with_monitoring.py --config development

# Custom dashboard port
python launch_with_monitoring.py --dashboard-port 8001
```

See [Monitoring Documentation](src/monitoring/README.md) for complete details.

## 🚨 Emergency Controls

### Automated Emergency Shutdown
The monitoring system automatically triggers emergency shutdown on:
- Memory usage > 1000MB
- API error rate > 1%
- Daily losses > $100
- Critical system failures

### Manual Emergency Stop
- **Dashboard**: Red emergency stop button
- **API**: POST to `/api/control/emergency-stop`
- **Keyboard**: Ctrl+C for graceful shutdown

### Emergency Actions
1. Halt all trading loops
2. Cancel all open orders
3. Optionally liquidate positions
4. Set emergency mode flag

## 🔧 Troubleshooting

### Rate Limit Issues
- The bot implements exponential backoff
- Wait 3-5 hours if severely rate limited
- Check `kraken_api_tier` in config

### Insufficient Funds Errors
- Ensure minimum $5 USDT available
- Check for capital deployed in positions
- Use emergency sell script if needed

### Position Tracking Issues
- Portfolio state saved in `trading_data/portfolio_state.json`
- Delete file to reset position tracking
- Bot will reinitialize from current holdings

## 📝 Logging

Logs are stored in multiple locations:
- Console output: Real-time execution info
- `kraken_infinity_bot.log`: Detailed debug logs
- `bot_output.log`: Launch script output
- `D:/trading_data/logs/`: Historical logs (Windows)

## 🚨 Important Notes

1. **API Tier Limits**:
   - Starter: 60 rate limit points
   - Intermediate: 125 points
   - Pro: 180 points

2. **Minimum Order Requirements**:
   - All orders must be at least $5 USDT
   - Bot automatically enforces this limit

3. **USDT Only**:
   - Bot trades only USDT pairs
   - Ensure USDT balance for trading

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License.

## ⚠️ Disclaimer

Cryptocurrency trading involves substantial risk. This bot is provided as-is without any guarantees. Always test with small amounts first and never invest more than you can afford to lose.

## 📞 Support

For issues and questions:
- Check CLAUDE.md for development guidelines
- Review logs for error messages
- Ensure rate limits aren't exceeded
- Verify API credentials are correct

---

**Remember**: The key to success is the "snowball effect" - many small profits compounding over time!