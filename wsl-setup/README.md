# WSL Trading Bot - Quick Start Guide

## Why WSL?

Running your trading bot in WSL (Windows Subsystem for Linux) provides:
- ✅ Better Python compatibility (no readline errors!)
- ✅ Native Linux performance
- ✅ Easier dependency management
- ✅ Better process control
- ✅ Isolated from Windows environment

## Quick Start (5 minutes)

### Step 1: Install WSL (if not installed)
Open PowerShell as Administrator:
```powershell
wsl --install
```
Restart your computer after installation.

### Step 2: Launch WSL Setup
Double-click: `launch_wsl_setup.bat`

Or manually:
1. Open Ubuntu/WSL terminal
2. Copy setup files:
```bash
cp -r /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025/wsl-setup ~/
cd ~/wsl-setup
bash quick_setup.sh
```

### Step 3: Configure API Keys
```bash
cd ~/projects/kraken-trading-bot-wsl
cp .env.template .env
nano .env  # Add your Kraken API credentials
```

### Step 4: Launch Bot
```bash
./launch_bot.sh
```

## Project Structure

```
~/projects/kraken-trading-bot-wsl/
├── src/               # Bot source code
│   ├── core/         # Core bot logic
│   ├── exchange/     # Exchange interfaces
│   ├── trading/      # Trading strategies
│   └── utils/        # Utilities
├── config/           # Configuration files
├── data/            # Data storage
├── logs/            # Log files
├── scripts/         # Utility scripts
├── venv/            # Python virtual environment
├── .env             # API credentials (create from template)
└── launch_bot.sh    # Main launch script
```

## Key Differences from Windows

1. **Paths**: Use Unix-style paths (`~/projects/` not `C:\projects\`)
2. **Python**: Uses Python 3.11 (stable for trading)
3. **Process Management**: Native Linux signals
4. **Performance**: Runs on WSL2's optimized Linux kernel

## Copying Your Existing Bot

To copy your Windows bot code to WSL:
```bash
# From WSL terminal
cd ~/projects/kraken-trading-bot-wsl
cp -r /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025/src/* src/

# Fix Windows-specific paths
find src -name "*.py" -exec sed -i 's/C:\\\/home\/$USER\//g' {} \;
find src -name "*.py" -exec sed -i 's/\\/\//g' {} \;
```

## Troubleshooting

### WSL Not Found
- Install from Microsoft Store: "Ubuntu 22.04 LTS"
- Or run: `wsl --install` in admin PowerShell

### Permission Denied
```bash
chmod +x launch_bot.sh
chmod +x scripts/*.sh
```

### Can't Find Project
Your project is at: `~/projects/kraken-trading-bot-wsl`
```bash
cd ~/projects/kraken-trading-bot-wsl
pwd  # Shows current directory
```

### Python Issues
```bash
# Verify Python 3.11
python3.11 --version

# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## Monitoring Your Bot

### View Logs
```bash
# Real-time logs
tail -f logs/bot_*.log

# Today's logs
less logs/bot_$(date +%Y%m%d).log
```

### Check Process
```bash
# Is bot running?
ps aux | grep python

# System resources
htop  # Install with: sudo apt install htop
```

## Advantages for Your Strategy

Your micro-scalping strategy benefits from WSL:
1. **Faster Execution**: Native Linux networking
2. **Better Stability**: No Windows interruptions
3. **Lower Latency**: Direct system calls
4. **Efficient Resources**: Less overhead than Windows

## Next Steps

1. ✅ Complete setup with `quick_setup.sh`
2. ✅ Add API credentials to `.env`
3. ✅ Test with `python test_setup.py`
4. ✅ Launch with `./launch_bot.sh`
5. 🚀 Watch profits accumulate!

## Support

- WSL Issues: https://docs.microsoft.com/en-us/windows/wsl/
- Ubuntu Help: https://ubuntu.com/tutorials/
- Trading Bot: Check logs in `~/projects/kraken-trading-bot-wsl/logs/`
