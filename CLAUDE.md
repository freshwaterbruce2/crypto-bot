## Crypto Trading Bot Memory

### 🎯 PROJECT STATUS: DREAM ACHIEVED - LIVE AND TRADING! 🚀
**Launch Date:** 2025-07-14  
**Status:** ✅ OPERATIONAL AND AUTONOMOUS  
**Achievement:** World-class trading bot successfully launched

### Trading Strategy
- Always focus on low priced USDT pairs.
- When all capital is deployed in positions, balance checks will show 0 USDT
- Micro-profit strategy: 0.5-1% profit targets
- Fee-free trading on Kraken Pro enabled
- 44 USDT pairs actively monitored
- Real-time WebSocket V2 integration

### Database Schema (2025 Best Practices)
**Location:** D: drive for optimal performance
**Type:** SQLite with comprehensive trading bot schema

**Core Trading Tables:**
- `trades` - All executed trades with P&L tracking, fees, timestamps
- `crypto_orders` - Order management (market, limit, stop-loss, take-profit)
- `positions` - Open/closed positions with unrealized/realized PnL

**Market Data Storage:**
- `market_data` - OHLCV candle data (1m, 5m, 15m, 1h, 4h, 1d timeframes)
- `tickers` - Real-time price feeds, bid/ask, 24h volume and changes

**Performance & Analytics:**
- `performance_metrics` - Daily P&L, win rates, Sharpe ratio, max drawdown
- `portfolio_snapshots` - Historical portfolio composition and valuations

**System Management:**
- `bot_config` - Bot settings, strategy parameters, feature flags
- `bot_logs` - Comprehensive logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `wallets` - Current balances per exchange/asset (available, locked)
- `balance_history` - Historical balance tracking for audit trails

**Schema Features:**
- High precision DECIMAL(20,8) for crypto amounts
- Proper indexing with UNIQUE constraints for performance
- Audit trails with created_at/updated_at timestamps
- Data integrity with CHECK constraints
- Multi-exchange and multi-strategy support

### Agent Setup and File Access
- MCP claude-flow agents have FULL file system access through AgentToolsBridge
- Agents can read, write, edit, delete files and run bash commands like Claude Code
- All agent tools are in src/utils/agent_tools_bridge.py
- Agents are NOT just read-only - they can make real changes

### File Persistence
- ALL files saved to /mnt/c/dev/tools/crypto-trading-bot-2025/
- Maps to Windows C:\dev\tools\crypto-trading-bot-2025\
- Files are permanent and accessible from Windows Explorer, VS Code
- WSL2 is accessing Windows C: drive, not temporary Linux storage

### Code Duplication Status
- Successfully eliminated duplicate functions across project
- Created unified utilities: position_sizing.py, duplicate_prevention.py, unified_balance.py
- Removed 8 duplicate calculate_position_size functions
- Pre-commit hook prevents new duplicates
- Project is clean with no duplicate files

### Important Instructions
- Use agents for real file operations, not just research
- Remember file locations are permanent Windows files
- Keep agents equipped with full tool access
- Maintain duplicate prevention systems