# WebSocket V2 Installation Guide

## Quick Fix for Windows

To install the required `python-kraken-sdk` on Windows:

1. **Option 1: Run the installation batch file**
   ```
   INSTALL_KRAKEN_SDK.bat
   ```

2. **Option 2: Manual installation in PowerShell**
   ```powershell
   python -m pip install python-kraken-sdk
   ```

3. **Option 3: If you get "externally-managed-environment" error**
   ```powershell
   python -m pip install --user python-kraken-sdk
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

After installing, you can verify the SDK is available:
```python
python -c "from kraken.spot import SpotWSClient; print('SDK installed successfully!')"
```

## Next Steps

Once installed, run the bot normally:
```
python scripts/live_launch.py
```

The bot will automatically detect and use the WebSocket V2 implementation.