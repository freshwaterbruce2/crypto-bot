# Kraken WebSocket V2 Visual Mode

## Overview

Visual mode displays real-time data from Kraken WebSocket V2 in a colorful, auto-updating terminal display. It shows live market data, order book depth, trades, and your account activity in an easy-to-read format.

## Features

### 1. Real-Time Market Data
- **Live Price Updates**: Current bid/ask prices update as they change
- **24-Hour Statistics**: Volume, high/low, price changes
- **Order Book Visualization**: Top 10 bids and asks with depth bars
- **Recent Trades**: Last 20 trades with size and price
- **Your Orders & Trades**: Personal trading activity

### 2. Visual Components

```
┌─────────────────────────────────────────────────────────────┐
│                   KRAKEN WEBSOCKET V2 MONITOR                │
├─────────────────────────────────────────────────────────────┤
│ Status: Connected ● | Latency: 45ms | Uptime: 02:34:15      │
├─────────────────────────────────────────────────────────────┤
│                        MARKET DATA                           │
│ Symbol: BTC/USD                                              │
│ Price: $65,432.10 ▲ (+2.34%)                               │
│ 24h Volume: 1,234.56 BTC                                    │
│ 24h High/Low: $66,000.00 / $63,500.00                      │
├─────────────────────────────────────────────────────────────┤
│                      ORDER BOOK                              │
│        BIDS                          ASKS                    │
│ $65,432.00 ████████████   0.250 | 0.150  ██████ $65,433.00 │
│ $65,431.00 ██████████     0.200 | 0.300  ████████████      │
│ $65,430.00 ████████       0.175 | 0.225  █████████         │
└─────────────────────────────────────────────────────────────┘
```

### 3. Color Coding
- **Green**: Positive changes, buy orders, upticks
- **Red**: Negative changes, sell orders, downticks
- **Yellow**: Warnings, pending orders
- **Blue**: Informational data
- **White**: Neutral/static information
- **Cyan**: Your orders and trades

## Usage

### Starting Visual Mode

```bash
# Basic usage
python scripts/test_websocket_visual.py

# With specific trading pair
python scripts/test_websocket_visual.py --symbol ETH/USD

# With multiple pairs
python scripts/test_websocket_visual.py --symbols BTC/USD,ETH/USD,SOL/USD

# With authentication (for private data)
python scripts/test_websocket_visual.py --auth
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--symbol` | Single trading pair to monitor | BTC/USD |
| `--symbols` | Comma-separated list of pairs | None |
| `--auth` | Enable authenticated connection | False |
| `--depth` | Order book depth (10, 25, 100) | 10 |
| `--refresh` | Refresh rate in milliseconds | 100 |
| `--log-level` | Logging verbosity | INFO |

## Display Sections

### 1. Connection Status Bar
- **Status**: Connected (green) or Disconnected (red)
- **Latency**: Round-trip time to Kraken servers
- **Uptime**: How long the connection has been active
- **Messages/sec**: Current message throughput

### 2. Market Overview
- **Current Price**: Last traded price with direction indicator
- **24h Change**: Percentage and absolute change
- **Volume**: 24-hour trading volume
- **VWAP**: Volume-weighted average price
- **Spread**: Current bid-ask spread

### 3. Order Book
- **Depth Bars**: Visual representation of order sizes
- **Price Levels**: Top bids and asks
- **Total Volume**: Cumulative volume at each level
- **Your Orders**: Highlighted in cyan if present

### 4. Recent Trades
- **Time**: When the trade occurred
- **Price**: Execution price
- **Size**: Trade volume
- **Side**: Buy (green) or Sell (red)
- **Your Trades**: Highlighted with special marker

### 5. Account Activity (Authenticated Only)
- **Open Orders**: Your current limit orders
- **Recent Executions**: Your filled trades
- **Balance Changes**: Real-time balance updates

## Keyboard Controls

| Key | Action |
|-----|--------|
| `q` or `ESC` | Quit visual mode |
| `SPACE` | Pause/Resume updates |
| `↑`/`↓` | Scroll through trading pairs |
| `+`/`-` | Increase/Decrease order book depth |
| `r` | Force reconnect |
| `c` | Clear screen and redraw |
| `s` | Toggle statistics panel |
| `l` | Toggle log messages |
| `h` | Show help screen |

## Configuration

### Config File: `config/websocket_visual.json`

```json
{
  "display": {
    "refresh_rate_ms": 100,
    "order_book_depth": 10,
    "trade_history_size": 20,
    "decimal_places": {
      "BTC/USD": 2,
      "ETH/USD": 2,
      "default": 4
    }
  },
  "colors": {
    "price_up": "green",
    "price_down": "red",
    "neutral": "white",
    "warning": "yellow",
    "info": "blue",
    "user_data": "cyan"
  },
  "connection": {
    "heartbeat_interval": 30,
    "reconnect_delay": 5,
    "max_reconnect_attempts": 10
  },
  "alerts": {
    "price_change_threshold": 1.0,
    "volume_spike_multiplier": 2.0,
    "spread_warning_percent": 0.5
  }
}
```

## Advanced Features

### 1. Multi-Symbol Mode
Monitor multiple trading pairs simultaneously:
```bash
python scripts/test_websocket_visual.py --symbols BTC/USD,ETH/USD,SOL/USD --layout grid
```

### 2. Alert System
Configure price and volume alerts:
```python
# In config/websocket_visual.json
"alerts": {
  "price_alerts": {
    "BTC/USD": {"above": 70000, "below": 60000},
    "ETH/USD": {"above": 4000, "below": 3000}
  }
}
```

### 3. Data Recording
Record all WebSocket data for later analysis:
```bash
python scripts/test_websocket_visual.py --record --output data/ws_recording.json
```

### 4. Custom Indicators
Add technical indicators to the display:
```bash
python scripts/test_websocket_visual.py --indicators RSI,VWAP,EMA
```

## Troubleshooting

### Common Issues

1. **Connection Drops Frequently**
   - Check your internet connection stability
   - Increase `heartbeat_interval` in config
   - Enable auto-reconnect: `--auto-reconnect`

2. **Display Corrupted**
   - Terminal size too small (minimum 80x24)
   - Try different terminal emulator
   - Use `--simple-mode` for basic display

3. **No Data Showing**
   - Verify API credentials if using `--auth`
   - Check if symbol is valid (use REST API to verify)
   - Enable debug logging: `--log-level DEBUG`

4. **High CPU Usage**
   - Increase refresh rate: `--refresh 500`
   - Reduce order book depth: `--depth 10`
   - Disable animations: `--no-animations`

### Debug Mode

Enable detailed debugging:
```bash
python scripts/test_websocket_visual.py --debug --log-file debug.log
```

### Performance Optimization

For low-latency environments:
```bash
python scripts/test_websocket_visual.py --performance \
  --refresh 50 \
  --no-animations \
  --minimal-ui
```

## Integration with Trading Bot

Visual mode can run alongside your trading bot:

```python
# In your bot code
from src.websocket_visual import WebSocketVisualizer

# Initialize visualizer
visualizer = WebSocketVisualizer(
    symbols=['BTC/USD', 'ETH/USD'],
    authenticated=True
)

# Run in separate thread
visualizer.start_async()

# Your bot continues running
while trading:
    # Bot logic here
    pass
```

## Memory Server Integration

Visual mode automatically updates the memory server with:
- Connection status
- Latest market data
- Performance metrics
- Error counts

Access this data:
```python
memory_client.search_nodes("websocket_status")
memory_client.search_nodes("market_data_snapshot")
```

## Best Practices

1. **Start Simple**: Begin with one symbol and basic features
2. **Monitor Performance**: Watch CPU and memory usage
3. **Use Appropriate Refresh Rates**: 100-500ms for most cases
4. **Enable Logging**: Keep logs for debugging issues
5. **Test Reconnection**: Ensure graceful handling of disconnects

## Example Sessions

### Basic Monitoring
```bash
# Monitor BTC/USD with standard settings
python scripts/test_websocket_visual.py
```

### Advanced Trading Setup
```bash
# Multi-symbol with authentication and recording
python scripts/test_websocket_visual.py \
  --symbols BTC/USD,ETH/USD,SOL/USD,MATIC/USD \
  --auth \
  --record \
  --indicators RSI,MACD \
  --alerts config/price_alerts.json
```

### Debug Session
```bash
# Full debug mode with all features
python scripts/test_websocket_visual.py \
  --debug \
  --log-file websocket_debug.log \
  --symbols BTC/USD \
  --auth \
  --refresh 1000
```

## Updates and Maintenance

Visual mode is actively maintained. Check for updates:
```bash
python scripts/test_websocket_visual.py --version
```

Report issues or request features in the project repository.
