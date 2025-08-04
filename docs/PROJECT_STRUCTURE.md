# Kraken Crypto Trading Bot 2025 - Complete Project Structure

## Overview
This document provides a comprehensive breakdown of the trading bot's architecture, file organization, and component relationships.

## Root Directory Structure

```
/mnt/c/dev/tools/crypto-trading-bot-2025/
├── main.py                    # Primary entry point
├── config.json               # Main configuration file
├── requirements.txt          # Python dependencies
├── .env                      # API credentials (not in git)
├── README.md                 # Project overview
├── CLAUDE.md                 # Development guidelines
│
├── src/                      # Core source code
├── scripts/                  # Utility and maintenance scripts
├── docs/                     # Documentation (this folder)
├── tests/                    # Test suites
├── dashboard/                # React-based monitoring dashboard
├── extensions/               # MCP extensions and integrations
├── mcp_server/               # Model Context Protocol server
└── trading_data/             # Local data storage
```

## Core Configuration Files

### Primary Configuration
- **`config.json`** - Main trading configuration
  - Trading pairs and strategies
  - Position sizing and risk parameters
  - Exchange settings and rate limits
  - Learning system configuration

- **`.env`** - Environment variables (secure)
  - `KRAKEN_API_KEY` - Trading API key
  - `KRAKEN_API_SECRET` - API secret
  - Optional environment overrides

- **`requirements.txt`** - Python dependencies
  - Kraken SDK 3.2.2
  - WebSocket libraries
  - ML/AI frameworks
  - Logging and monitoring tools

### Launch Scripts
- **`main.py`** - Primary entry point with full initialization
- **`START_BOT_OPTIMIZED.bat`** - Windows quick launch
- **`scripts/live_launch.py`** - Advanced launcher with monitoring
- **`scripts/paper_trading_launcher.py`** - Simulation mode launcher

## Source Code Architecture (`src/`)

### Core Components (`src/core/`)
```
src/core/
└── bot.py                   # Main bot orchestrator and control loop
```

### Exchange Integration (`src/exchange/`)
```
src/exchange/
├── kraken_sdk_exchange.py      # Primary Kraken SDK wrapper
├── native_kraken_exchange.py   # Legacy Kraken API integration
├── websocket_manager_v2.py     # WebSocket V2 implementation
├── websocket_auth_manager.py   # WebSocket authentication
├── balance_fix_wrapper.py      # Balance handling improvements
├── fallback_data_manager.py    # Multi-source data fallback
└── hft_websocket_optimizer.py  # High-frequency trading optimization
```

### Trading Engine (`src/trading/`)
```
src/trading/
├── enhanced_trade_executor_with_assistants.py  # AI-assisted execution
├── opportunity_scanner.py                      # Market opportunity detection
├── opportunity_execution_bridge.py             # Execution bridge
├── portfolio_tracker.py                       # Position tracking
├── profit_harvester.py                        # Automated profit-taking
├── unified_balance_manager.py                  # Balance management
├── smart_minimum_manager.py                    # Dynamic minimum handling
├── unified_risk_manager.py                     # Risk assessment
├── infinity_trading_manager.py                 # Continuous trading loop
└── assistants/                                 # AI trading assistants
    ├── balance_assistant.py
    ├── execution_assistant.py
    ├── risk_management_assistant.py
    └── signal_generation_assistant.py
```

### Trading Strategies (`src/strategies/`)
```
src/strategies/
├── base_strategy.py                  # Strategy interface
├── enhanced_portfolio_strategy.py    # Portfolio-aware strategy
├── fast_start_strategy.py            # Quick profit strategy
├── mean_reversion_strategy.py        # Mean reversion trading
├── micro_scalper_strategy.py         # Micro-scalping implementation
├── autonomous_sell_engine.py         # Automated selling logic
├── quantum_fluctuation_scalper.py    # Advanced scalping strategy
└── pro_fee_free_micro_scalper.py     # Fee-optimized strategy
```

### Learning Systems (`src/learning/`)
```
src/learning/
├── unified_learning_system.py        # Central learning coordinator
├── neural_pattern_engine.py          # Pattern recognition ML
├── advanced_memory_manager.py        # Persistent learning memory
├── learning_integration.py           # Integration with trading engine
└── universal_learning_manager.py     # Cross-strategy learning
```

### Utilities (`src/utils/`)
```
src/utils/
├── kraken_nonce_manager.py           # API nonce management
├── rate_limit_handler.py             # Rate limiting protection
├── decimal_precision_fix.py          # Financial precision handling
├── custom_logging.py                 # Enhanced logging system
├── performance_maximizer_2025.py     # Performance optimization
├── portfolio_intelligence.py         # Portfolio analysis
├── realtime_pnl_tracker.py           # Real-time P&L tracking
├── circuit_breaker.py                # Emergency stop mechanisms
└── self_repair.py                    # Self-healing functionality
```

### Configuration Management (`src/config/`)
```
src/config/
├── config.py                # Configuration loader
├── constants.py             # System constants
├── trading.py               # Trading-specific config
├── risk.py                  # Risk management config
├── learning.py              # Learning system config
└── validator.py             # Configuration validation
```

## Scripts Directory (`scripts/`)

### Launch Scripts
- **`live_launch.py`** - Production launch with full monitoring
- **`paper_trading_launcher.py`** - Simulation mode launcher
- **`dev_launch.py`** - Development mode launcher

### Diagnostic Scripts
- **`quick_check.py`** - System health check
- **`check_balance_simple.py`** - Balance verification
- **`test_kraken_connection.py`** - API connectivity test
- **`diagnose_signals.py`** - Signal generation diagnostics

### Maintenance Scripts
- **`emergency_cleanup.py`** - System cleanup and recovery
- **`migrate_data_to_d_drive.py`** - Data migration utility
- **`setup_enhanced_logging.py`** - Logging configuration
- **`rate_limit_recovery.py`** - Rate limit recovery

### Utility Scripts
- **`manual_sell_positions.py`** - Emergency position liquidation
- **`show_positions.py`** - Position overview
- **`check_portfolio_status.py`** - Portfolio status check
- **`force_refresh_balance.py`** - Balance refresh utility

## Data Storage Structure

### Local Data (`trading_data/`)
```
trading_data/
├── cache/                   # Temporary cache files
├── learning/                # ML model data and insights
├── logs/                    # Local log files
├── reports/                 # Performance reports
└── strategies/              # Strategy-specific data
```

### D: Drive Storage (`D:/trading_data/`)
```
D:/trading_data/
├── logs/                    # Primary log storage
├── historical/              # Historical market data
│   ├── daily/
│   ├── hourly/
│   └── ohlc/
├── learning/                # Learning system data
├── memory/                  # Persistent memory storage
└── guardian/                # Guardian system data
```

## Dashboard Interface (`dashboard/`)

### Frontend (`dashboard/frontend/`)
```
dashboard/frontend/
├── src/
│   ├── App.jsx              # Main dashboard application
│   ├── components/          # React components
│   └── hooks/               # Custom React hooks
├── package.json          # Node.js dependencies
└── vite.config.js        # Vite build configuration
```

### Backend (`dashboard/backend/`)
```
dashboard/backend/
└── main.py               # FastAPI backend server
```

## Extensions & Integrations (`extensions/`)

### MCP Extensions
```
extensions/
├── ccxt-mcp/             # CCXT trading library integration
├── mcp-trader/           # Advanced trading MCP server
├── financial-datasets-mcp/ # Financial data integration
└── sqlite-server/        # Database MCP server
```

## Test Suites (`tests/`)

### Test Organization
```
tests/
├── api/                  # API integration tests
├── core/                 # Core functionality tests
├── strategies/           # Strategy testing
├── integration/          # System integration tests
└── conftest.py           # Pytest configuration
```

## Key Technical Features

### Advanced Architecture
- **Async/Await Design**: Non-blocking concurrent operations
- **Multi-Source Data**: WebSocket + REST + fallback providers
- **Self-Healing System**: Automatic error recovery and optimization
- **Decimal Precision**: Financial-grade calculation accuracy
- **Memory Persistence**: State preservation across restarts

### Integration Capabilities
- **MCP Server**: Model Context Protocol for advanced diagnostics
- **WebSocket V2**: Real-time Kraken data streaming
- **React Dashboard**: Web-based monitoring and control
- **AI Assistants**: ML-driven trading decision support
- **Multi-Strategy**: Portfolio-aware strategy coordination

### Data Flow
```
Market Data (WebSocket V2) → Opportunity Scanner → Strategy Engine → 
AI Assistants → Risk Management → Trade Executor → Portfolio Tracker → 
Profit Harvester → Learning System → Performance Analytics
```

### Security & Compliance
- **API-Only Trading**: No withdrawal permissions required
- **Encrypted Storage**: Secure credential management
- **Audit Trail**: Complete transaction logging
- **Rate Limit Protection**: Multi-tier API protection
- **Emergency Controls**: Manual override capabilities

## Development Workflow

### Local Development
1. **Environment Setup**: Python 3.8+, pip, venv
2. **Dependency Installation**: `pip install -r requirements.txt`
3. **Configuration**: Create `.env` with API credentials
4. **Testing**: Run test suite with `python -m pytest`
5. **Launch**: Use `python main.py` for development mode

### Production Deployment
1. **System Requirements**: Windows/Linux with 4GB+ RAM
2. **Data Directory**: Ensure D: drive access for optimal performance
3. **API Configuration**: Kraken Pro account with trading permissions
4. **Monitoring**: Enable dashboard for real-time oversight
5. **Maintenance**: Regular log rotation and system health checks

---

**Last Updated**: July 30, 2025
**Architecture Version**: 2.1.0
**Component Status**: All systems operational
