# Crypto Trading Bot 2025 - Installation Checklist

## Pre-Installation Requirements
- [ ] Windows 10/11 (version 2004 or higher)
- [ ] Python 3.9+ installed and in PATH
- [ ] Administrator access for WSL setup
- [ ] Kraken account with API access enabled

## Installation Progress Checklist

### Phase 1: System Setup
- [ ] WSL2 features enabled (requires admin privileges)
- [ ] Computer restarted after WSL feature enablement
- [ ] Ubuntu installed via `wsl --install -d Ubuntu`
- [ ] Ubuntu initial setup completed (username/password created)

### Phase 2: Project Setup
- [ ] Project directory accessible at `/mnt/c/dev/tools/crypto-trading-bot-2025/`
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Virtual environment created (optional but recommended)
- [ ] Configuration file prepared (`config.json`)

### Phase 3: API Configuration
- [ ] Kraken API key obtained from account settings
- [ ] API secret safely stored
- [ ] API permissions verified (trading enabled)
- [ ] Configuration file updated with credentials

### Phase 4: Verification Tests
- [ ] API connection test passed (`python scripts/test_kraken_connection.py`)
- [ ] Balance check working (`python scripts/check_balance_simple.py`)
- [ ] Bot status check passed (`python scripts/check_bot_status.py`)
- [ ] Paper trading mode tested (`python start_paper_trading.py`)

## Installation Commands Reference

### WSL2 Setup (Run as Administrator)
```powershell
# Enable WSL features
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Restart computer, then install Ubuntu
wsl --install -d Ubuntu
```

### Python Environment Setup
```bash
# In WSL Ubuntu terminal
cd /mnt/c/dev/tools/crypto-trading-bot-2025/

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Optional: Create virtual environment
python -m venv venv
source venv/bin/activate
```

### Configuration Setup
```bash
# Backup and configure
cp config.json config.json.backup
# Edit config.json with your API credentials using nano or vim
nano config.json
```

### Verification Commands
```bash
# Test API connection
python scripts/test_kraken_connection.py

# Check system status
python scripts/check_bot_status.py

# Test paper trading
python start_paper_trading.py

# Start live trading (after successful tests)
python main.py
```

## Common Issues and Solutions

### WSL Installation Issues
- **Error**: "WSL not found" → Run enable WSL commands as Administrator
- **Error**: "Ubuntu installation failed" → Check Windows version compatibility
- **Fix**: Use `wsl --install -d Ubuntu --no-launch` if GUI fails

### Python Dependencies Issues
- **Error**: "pip not found" → Install Python via Microsoft Store or python.org
- **Error**: "Permission denied" → Use `--user` flag: `pip install --user -r requirements.txt`
- **Error**: "Package conflicts" → Create virtual environment first

### API Configuration Issues
- **Error**: "Invalid API key" → Verify key copied correctly without spaces
- **Error**: "Permission denied" → Enable trading permissions in Kraken account
- **Error**: "Nonce error" → Delete any existing nonce files: `rm kraken_nonce.json`

## Files Created During Installation
- `config.json` - Main configuration with API credentials
- `logs/` - Directory for bot operation logs
- `trading_data/` - Directory for trading history and analysis
- `paper_trading_data/` - Directory for paper trading records

## Post-Installation Next Steps
1. Run paper trading mode first to test strategies safely
2. Monitor logs for any issues or warnings
3. Start with small trade amounts for live trading
4. Set up monitoring and alerts as needed

## Security Checklist
- [ ] API keys stored securely (not in git repository)
- [ ] File permissions set correctly (`chmod 600 config.json`)
- [ ] Backup of configuration created
- [ ] Test environment separated from production
