# WebSocket V2 Installation Guide

## Prerequisites

- Python 3.8+ installed
- pip package manager
- Valid Kraken API credentials

## Installation Methods

### Option 1: Install Dependencies (Recommended)
```bash
# Install all requirements including WebSocket V2 SDK
pip install -r requirements.txt
```

### Option 2: Manual SDK Installation

#### Windows:
```powershell
# Use virtual environment (recommended)
python -m venv venv
venv\Scripts\activate
pip install python-kraken-sdk

# Or install globally
python -m pip install python-kraken-sdk

# If you get "externally-managed-environment" error
python -m pip install --user python-kraken-sdk
```

#### Linux/WSL:
```bash
# Use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install python-kraken-sdk

# Or install globally
pip3 install python-kraken-sdk
```

## What This Fixes

The bot now uses Kraken's official WebSocket V2 SDK for:
- Real-time ticker prices (NO CACHED DATA)
- Real-time balance updates via WebSocket
- Automatic reconnection handling
- Better performance and reliability

## Fallback Mode

If the SDK is not installed, the bot will:
1. Log a clear error message
2. Continue to run but without WebSocket V2 support
3. Not crash - just warn about missing functionality

## Verify Installation

After installing, verify the SDK is available:

```bash
# Test WebSocket V2 SDK import
python -c "from kraken.spot import SpotWSClient; print('✅ WebSocket V2 SDK installed successfully!')"

# Test basic bot imports
python -c "from src.bot import KrakenTradingBot; print('✅ Bot imports working!')"

# Run comprehensive test
python scripts/test_imports.py
```

## Configuration

Ensure your `config.json` has WebSocket V2 enabled:

```json
{
  "websocket": {
    "enabled": true,
    "version": "v2",
    "channels": ["ticker", "trade", "book"]
  },
  "exchange": {
    "name": "kraken",
    "api_tier": "pro"
  }
}
```

## Launch Options

### Development/Testing:
```bash
# Test WebSocket connection only
python websocket_v2_explorer.py

# Test full bot functionality
python scripts/test_websocket_v2.py
```

### Production:
```bash
# Start main trading bot
python scripts/live_launch.py

# Start with monitoring
python scripts/live_launch.py --monitor
```

## Troubleshooting

### Common Issues:

1. **Import Error**: `ModuleNotFoundError: No module named 'kraken'`
   - Solution: Install python-kraken-sdk as shown above

2. **WebSocket Connection Failed**
   - Check internet connection
   - Verify API credentials in `.env` file
   - Test with: `python scripts/test_kraken_connection.py`

3. **Permission Errors**
   - Use virtual environment or `--user` flag
   - On Linux: `sudo pip3 install python-kraken-sdk`

4. **Authentication Errors**
   - Verify API key permissions include WebSocket access
   - Check API key/secret format in configuration

The bot will automatically detect and use the WebSocket V2 implementation when available.