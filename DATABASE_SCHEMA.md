# Crypto Trading Bot Database Schema

## Overview
Comprehensive SQLite database schema designed for high-performance crypto trading bot operations, following 2025 best practices for trading data management.

**Storage Location:** D: drive (as per project requirements)  
**Database Type:** SQLite with optimizations for trading workloads  
**Precision:** DECIMAL(20,8) for all crypto amounts  

## Core Trading Tables

### `trades`
Records all executed trades with complete transaction details.

```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,                    -- Trading pair (e.g., BTC/USDT)
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    amount DECIMAL(20,8) NOT NULL,           -- Quantity traded
    price DECIMAL(20,8) NOT NULL,            -- Execution price
    total_value DECIMAL(20,8) NOT NULL,      -- Total transaction value
    fee DECIMAL(20,8) DEFAULT 0,             -- Trading fee
    fee_currency TEXT,                       -- Fee currency
    timestamp INTEGER NOT NULL,              -- Trade execution time
    exchange TEXT NOT NULL,                  -- Exchange name
    order_id TEXT,                          -- Exchange order reference
    strategy TEXT,                          -- Trading strategy used
    status TEXT DEFAULT 'filled' CHECK (status IN ('filled', 'partial', 'canceled')),
    profit_loss DECIMAL(20,8),              -- P&L calculation
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
)
```

### `crypto_orders`
Order management with support for multiple order types.

```sql
CREATE TABLE crypto_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,           -- Exchange order ID
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type TEXT NOT NULL CHECK (order_type IN ('market', 'limit', 'stop_loss', 'take_profit')),
    amount DECIMAL(20,8) NOT NULL,           -- Order quantity
    price DECIMAL(20,8),                     -- Order price (null for market orders)
    filled_amount DECIMAL(20,8) DEFAULT 0,   -- Amount filled
    remaining_amount DECIMAL(20,8),          -- Remaining to fill
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'open', 'filled', 'canceled', 'expired')),
    exchange TEXT NOT NULL,
    strategy TEXT,                          -- Associated strategy
    timestamp INTEGER NOT NULL,              -- Order creation time
    filled_at INTEGER,                      -- Fill completion time
    canceled_at INTEGER,                    -- Cancellation time
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
)
```

### `positions`
Open and closed position tracking with P&L monitoring.

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('long', 'short')),
    amount DECIMAL(20,8) NOT NULL,           -- Position size
    entry_price DECIMAL(20,8) NOT NULL,      -- Average entry price
    current_price DECIMAL(20,8),             -- Current market price
    unrealized_pnl DECIMAL(20,8) DEFAULT 0, -- Unrealized P&L
    realized_pnl DECIMAL(20,8) DEFAULT 0,    -- Realized P&L
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    exchange TEXT NOT NULL,
    strategy TEXT,
    opened_at INTEGER NOT NULL,              -- Position open time
    closed_at INTEGER,                       -- Position close time
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
)
```

## Market Data Storage

### `market_data`
OHLCV candlestick data for technical analysis.

```sql
CREATE TABLE market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,              -- Candle timestamp
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    timeframe TEXT NOT NULL CHECK (timeframe IN ('1m', '5m', '15m', '1h', '4h', '1d')),
    exchange TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(symbol, timestamp, timeframe, exchange)
)
```

### `tickers`
Real-time price and volume data.

```sql
CREATE TABLE tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    bid_price DECIMAL(20,8),                 -- Best bid price
    ask_price DECIMAL(20,8),                 -- Best ask price
    last_price DECIMAL(20,8) NOT NULL,       -- Last trade price
    volume_24h DECIMAL(20,8),                -- 24h volume
    price_change_24h DECIMAL(20,8),          -- 24h price change
    price_change_percent_24h DECIMAL(10,4),  -- 24h percentage change
    timestamp INTEGER NOT NULL,              -- Ticker timestamp
    exchange TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(symbol, exchange, timestamp)
)
```

## Performance & Analytics

### `performance_metrics`
Daily performance tracking and strategy analysis.

```sql
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                      -- Trading date
    total_portfolio_value DECIMAL(20,8) NOT NULL,
    daily_pnl DECIMAL(20,8) DEFAULT 0,       -- Daily P&L
    daily_pnl_percent DECIMAL(10,4) DEFAULT 0, -- Daily P&L percentage
    total_trades INTEGER DEFAULT 0,          -- Number of trades
    winning_trades INTEGER DEFAULT 0,        -- Profitable trades
    losing_trades INTEGER DEFAULT 0,         -- Loss-making trades
    win_rate DECIMAL(10,4) DEFAULT 0,        -- Win rate percentage
    sharpe_ratio DECIMAL(10,4),              -- Risk-adjusted returns
    max_drawdown DECIMAL(10,4),              -- Maximum drawdown
    strategy TEXT,                          -- Strategy identifier
    exchange TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(date, strategy, exchange)
)
```

### `portfolio_snapshots`
Historical portfolio composition for analysis.

```sql
CREATE TABLE portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,              -- Snapshot time
    asset TEXT NOT NULL,                     -- Asset symbol
    amount DECIMAL(20,8) NOT NULL,           -- Asset quantity
    usd_value DECIMAL(20,8) NOT NULL,        -- USD valuation
    price_per_unit DECIMAL(20,8) NOT NULL,   -- Asset price
    exchange TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
)
```

## System Management

### `bot_config`
Configuration management for bot settings and strategies.

```sql
CREATE TABLE bot_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT UNIQUE NOT NULL,         -- Configuration key
    config_value TEXT NOT NULL,              -- Configuration value
    config_type TEXT DEFAULT 'string' CHECK (config_type IN ('string', 'number', 'boolean', 'json')),
    description TEXT,                        -- Config description
    strategy TEXT,                          -- Associated strategy
    is_active BOOLEAN DEFAULT true,          -- Configuration status
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
)
```

### `bot_logs`
Comprehensive logging system for debugging and audit trails.

```sql
CREATE TABLE bot_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,              -- Log timestamp
    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    message TEXT NOT NULL,                   -- Log message
    module TEXT,                            -- Source module
    strategy TEXT,                          -- Associated strategy
    exchange TEXT,                          -- Associated exchange
    symbol TEXT,                            -- Associated symbol
    metadata TEXT,                          -- Additional JSON metadata
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
)
```

## Wallet Management

### `wallets`
Current balance tracking per exchange and asset.

```sql
CREATE TABLE wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    asset TEXT NOT NULL,
    available_balance DECIMAL(20,8) NOT NULL DEFAULT 0, -- Available for trading
    locked_balance DECIMAL(20,8) NOT NULL DEFAULT 0,    -- Locked in orders
    total_balance DECIMAL(20,8) GENERATED ALWAYS AS (available_balance + locked_balance) STORED,
    usd_value DECIMAL(20,8),                -- USD equivalent
    last_updated INTEGER NOT NULL,           -- Last balance update
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(exchange, asset)
)
```

### `balance_history`
Historical balance tracking for audit and analysis.

```sql
CREATE TABLE balance_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    asset TEXT NOT NULL,
    balance DECIMAL(20,8) NOT NULL,          -- Balance amount
    usd_value DECIMAL(20,8),                -- USD valuation
    timestamp INTEGER NOT NULL,              -- Balance timestamp
    balance_type TEXT DEFAULT 'total' CHECK (balance_type IN ('available', 'locked', 'total')),
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
)
```

## Indexing Strategy

### Performance Indexes
```sql
-- Trading performance indexes
CREATE INDEX idx_trades_symbol_timestamp ON trades(symbol, timestamp);
CREATE INDEX idx_trades_strategy_timestamp ON trades(strategy, timestamp);
CREATE INDEX idx_orders_status ON crypto_orders(status);
CREATE INDEX idx_positions_status ON positions(status);

-- Market data indexes
CREATE INDEX idx_market_data_symbol_timeframe ON market_data(symbol, timeframe, timestamp);
CREATE INDEX idx_tickers_symbol_exchange ON tickers(symbol, exchange, timestamp);

-- Analytics indexes
CREATE INDEX idx_performance_date ON performance_metrics(date);
CREATE INDEX idx_logs_timestamp_level ON bot_logs(timestamp, level);
CREATE INDEX idx_balance_history_timestamp ON balance_history(timestamp);
```

## Data Retention Policies

### Automated Cleanup (Recommended)
- **Raw Market Data:** Retain 1 year, compress older data
- **Trade Records:** Permanent retention for tax/audit purposes
- **Debug Logs:** 30 days retention
- **Performance Metrics:** Permanent retention
- **Balance History:** 2 years retention

## Integration Notes

### MCP Integration
The schema is designed to work seamlessly with the existing MCP trader models in `extensions/mcp-trader/src/mcp_trader/models.py`. The database structure complements the Pydantic models for:
- Market data validation
- Technical analysis results
- Risk calculations
- Pattern detection

### Multi-Exchange Support
All tables include `exchange` fields to support:
- Kraken (primary)
- Binance (secondary)
- Future exchange integrations

### Strategy Flexibility
Strategy fields throughout the schema support:
- Multiple concurrent strategies
- Strategy performance comparison
- A/B testing of trading algorithms
- Risk-adjusted strategy allocation

## Backup and Recovery

### Recommended Backup Strategy
1. **Real-time replication** to D:\backups\crypto-bot\
2. **Daily snapshots** with compression
3. **Weekly cloud backup** of critical data
4. **Monthly full system backup**

This schema provides a robust foundation for professional crypto trading operations with enterprise-grade data management capabilities.