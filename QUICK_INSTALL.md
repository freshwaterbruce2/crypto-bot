# Crypto Trading Bot 2025 - Quick Installation Guide

## Prerequisites
- Windows 10/11 with WSL2 support
- Python 3.9+ installed
- Git (optional but recommended)

## Installation Steps

### Option 1: WSL2 Installation (Recommended)

1. **Enable WSL2** (Run as Administrator in PowerShell):
   ```powershell
   # Enable WSL features
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   
   # Restart your computer (required)
   # After restart, install Ubuntu
   wsl --install -d Ubuntu
   ```

2. **Set up the trading bot in WSL2**:
   ```bash
   # Clone or navigate to project
   cd /mnt/c/dev/tools/crypto-trading-bot-2025/
   
   # Install Python dependencies
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   
   # Configure API keys (edit with your credentials)
   cp config.json.example config.json
   # Edit config.json with your Kraken API credentials
   ```

3. **Launch the bot**:
   ```bash
   # Test installation
   python scripts/test_kraken_connection.py
   
   # Start trading
   python main.py
   ```

### Option 2: Windows Native Installation

1. **Install dependencies**:
   ```cmd
   cd C:\dev\tools\crypto-trading-bot-2025
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Configure and launch**:
   ```cmd
   # Copy example config
   copy config.json.example config.json
   # Edit config.json with your API credentials
   
   # Test connection
   python scripts\test_kraken_connection.py
   
   # Launch using batch file
   START_TRADING_BOT.bat
   ```

## Quick Commands

### Essential Commands:
```bash
# Test API connection
python scripts/test_kraken_connection.py

# Check account balance
python scripts/check_balance_simple.py

# Start paper trading (safe testing)
python start_paper_trading.py

# Start live trading
python main.py
```

### Troubleshooting:
```bash
# Check bot status
python scripts/check_bot_status.py

# Clean cache and restart
python scripts/emergency_cleanup.py

# Force refresh balance
python scripts/force_refresh_balance.py
```

## Next Steps

1. Configure your Kraken API credentials in `config.json`
2. Test with paper trading first: `python start_paper_trading.py`
3. Once confident, start live trading: `python main.py`
4. Monitor logs in the `logs/` directory

For detailed setup instructions, see `INSTALLATION_CHECKLIST.md`
