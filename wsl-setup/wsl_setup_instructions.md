# WSL Trading Bot Setup Guide

## Prerequisites

### 1. Install WSL (if not already installed)
Open PowerShell as Administrator and run:
```powershell
wsl --install
# This installs Ubuntu by default
```

### 2. Access WSL
```bash
# From Windows Terminal or PowerShell:
wsl

# Or directly open Ubuntu from Start Menu
```

## Project Setup in WSL

### 1. Create Project Directory Structure
```bash
# Navigate to home directory
cd ~

# Create projects folder
mkdir -p ~/projects/kraken-trading-bot-wsl
cd ~/projects/kraken-trading-bot-wsl

# Create project structure
mkdir -p {src/{core,exchange,trading,utils,analysis,learning},config,logs,data,scripts,tests}
```

### 2. Install Python 3.11 (Recommended for stability)
```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Install pip for Python 3.11
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
```

### 3. Create Virtual Environment
```bash
# Create venv with Python 3.11
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip wheel setuptools
```

### 4. Set Up Git Repository
```bash
# Initialize git
git init

# Configure git (replace with your info)
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Trading Bot Specific
.env
config/credentials.json
logs/
data/
*.log
kraken_nonce.json
bot.lock
*.pid

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db
EOF
```

### 5. Create Environment File
```bash
# Create .env file for credentials
cat > .env << 'EOF'
# Kraken API Credentials
KRAKEN_API_KEY="your_api_key_here"
KRAKEN_API_SECRET="your_api_secret_here"

# Bot Configuration
BOT_ENV="development"
LOG_LEVEL="INFO"
USE_WEBSOCKET_V2=true
USE_AMEND_ORDERS=true

# Paths (WSL specific)
DATA_DIR="/home/$USER/projects/kraken-trading-bot-wsl/data"
LOG_DIR="/home/$USER/projects/kraken-trading-bot-wsl/logs"
EOF

# Set proper permissions
chmod 600 .env
```

### 6. Install Dependencies
```bash
# Create requirements.txt
cat > requirements.txt << 'EOF'
# Core dependencies
ccxt==4.4.50
websocket-client==1.8.0
websockets==13.1
python-dotenv==1.0.1
aiofiles==24.1.0
aiohttp==3.11.11

# Kraken specific
krakenex==2.2.2

# Data handling
pandas==2.2.3
numpy==2.0.2
scipy==1.14.1

# Technical analysis
ta==0.11.0
pandas-ta==0.3.14b0

# Logging and monitoring
colorlog==6.9.0
python-json-logger==3.2.1

# Utils
pyyaml==6.0.2
click==8.1.8
pytz==2024.2
dateparser==1.2.0

# Development
pytest==8.3.4
pytest-asyncio==0.25.0
pytest-cov==6.0.0
black==24.10.0
flake8==7.1.1
mypy==1.14.0

# Performance
cython==3.0.11
numba==0.61.0
EOF

# Install all dependencies
pip install -r requirements.txt
```

### 7. Create Project Configuration
```bash
# Create config file
cat > config/config.yaml << 'EOF'
# Kraken Trading Bot Configuration - WSL Optimized

exchange:
  name: "kraken"
  test_mode: false
  rate_limit:
    requests_per_minute: 30
    order_rate_limit: 15
  websocket:
    use_v2: true
    heartbeat_interval: 30
    reconnect_attempts: 5
    reconnect_delay: 5

trading:
  # Fee-free micro-scalping strategy
  strategy: "micro_scalper"
  pairs:
    - "BTC/USDT"
    - "ETH/USDT"
    - "XRP/USDT"
    - "ADA/USDT"
    - "SOL/USDT"
    - "DOGE/USDT"
    - "DOT/USDT"
    - "MATIC/USDT"
    - "SHIB/USDT"
    - "AVAX/USDT"
    - "LINK/USDT"
    - "UNI/USDT"
  
  position_sizing:
    min_position_value: 10.0
    max_position_value: 100.0
    max_positions: 5
    risk_per_trade: 0.01  # 1% risk
  
  micro_scalping:
    profit_target_pct: 0.5  # 0.5% target
    stop_loss_pct: 0.8     # 0.8% stop
    use_trailing_stop: true
    trailing_stop_pct: 0.3
    max_holding_time: 3600  # 1 hour max
    use_amend_orders: true  # WSL optimized
    min_volume_24h: 10000   # $10k minimum volume

risk_management:
  max_daily_loss_pct: 5.0
  max_drawdown_pct: 10.0
  circuit_breaker:
    consecutive_losses: 5
    cooldown_minutes: 30

paths:
  data_dir: "~/projects/kraken-trading-bot-wsl/data"
  log_dir: "~/projects/kraken-trading-bot-wsl/logs"
  cache_dir: "~/projects/kraken-trading-bot-wsl/data/cache"

logging:
  level: "INFO"
  format: "json"
  rotation:
    max_bytes: 10485760  # 10MB
    backup_count: 5
  
performance:
  use_cython: true
  cache_enabled: true
  multi_threading: true
  worker_threads: 4
EOF
```

### 8. Copy Core Bot Files
```bash
# This script will help you copy essential files from Windows to WSL
cat > scripts/copy_from_windows.sh << 'EOF'
#!/bin/bash
# Copy essential bot files from Windows project to WSL

WINDOWS_PROJECT="/mnt/c/dev/tools/crypto-trading-bot-2025"
WSL_PROJECT="$HOME/projects/kraken-trading-bot-wsl"

# Check if Windows project exists
if [ ! -d "$WINDOWS_PROJECT" ]; then
    echo "Error: Windows project not found at $WINDOWS_PROJECT"
    exit 1
fi

echo "Copying core bot files from Windows to WSL..."

# Copy Python source files (excluding Windows-specific)
cp -r "$WINDOWS_PROJECT/src/core" "$WSL_PROJECT/src/" 2>/dev/null || echo "Core files not found"
cp -r "$WINDOWS_PROJECT/src/exchange" "$WSL_PROJECT/src/" 2>/dev/null || echo "Exchange files not found"
cp -r "$WINDOWS_PROJECT/src/trading" "$WSL_PROJECT/src/" 2>/dev/null || echo "Trading files not found"
cp -r "$WINDOWS_PROJECT/src/utils" "$WSL_PROJECT/src/" 2>/dev/null || echo "Utils files not found"

# Copy specific useful files
cp "$WINDOWS_PROJECT/src/config.py" "$WSL_PROJECT/src/" 2>/dev/null || echo "Config.py not found"

echo "Files copied. You may need to modify paths and Windows-specific code."
echo "Remember to update all file paths to use Unix-style paths!"
EOF

chmod +x scripts/copy_from_windows.sh
```

### 9. Create WSL-Optimized Launch Script
```bash
cat > scripts/launch_bot.sh << 'EOF'
#!/bin/bash
# WSL-Optimized Trading Bot Launcher

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}Kraken Trading Bot - WSL Edition${NC}"
echo -e "${CYAN}=====================================${NC}"

# Check virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Check environment variables
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)

# Check API credentials
if [ -z "$KRAKEN_API_KEY" ] || [ -z "$KRAKEN_API_SECRET" ]; then
    echo -e "${RED}Error: API credentials not set in .env!${NC}"
    exit 1
fi

# Create necessary directories
mkdir -p "$PROJECT_ROOT/logs" "$PROJECT_ROOT/data/cache"

# Kill any existing bot processes
echo -e "${YELLOW}Checking for existing bot processes...${NC}"
pkill -f "python.*bot.py" 2>/dev/null || true

# Check system resources
echo -e "${YELLOW}System Status:${NC}"
echo "CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "Disk: $(df -h $HOME | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')"

# Launch the bot
echo -e "${GREEN}Starting Trading Bot...${NC}"
cd "$PROJECT_ROOT"

# Use exec to replace shell with Python process
exec python -u src/main.py

EOF

chmod +x scripts/launch_bot.sh
```

### 10. Create Main Entry Point
```bash
cat > src/main.py << 'EOF'
#!/usr/bin/env python3
"""
Kraken Trading Bot - WSL Optimized Entry Point
"""

import asyncio
import sys
import os
import signal
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.bot import KrakenTradingBot
from src.config import load_config
from src.utils.logging_setup import setup_logging

# Global shutdown flag
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    shutdown_requested = True
    print("\n[SIGNAL] Shutdown requested...")

async def main():
    """Main bot execution"""
    global shutdown_requested
    
    # Setup logging
    logger = setup_logging()
    logger.info("="*50)
    logger.info("Kraken Trading Bot - WSL Edition Starting")
    logger.info("="*50)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = None
    try:
        # Load configuration
        config = load_config()
        logger.info(f"Configuration loaded: {config.get('trading', {}).get('strategy', 'unknown')}")
        
        # Create and start bot
        bot = KrakenTradingBot(config)
        logger.info("Bot initialized successfully")
        
        # Run bot
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        if bot:
            logger.info("Shutting down bot...")
            await bot.stop()
        logger.info("Bot stopped cleanly")

if __name__ == "__main__":
    asyncio.run(main())
EOF
```

## Quick Start Commands

Once you're in WSL, run these commands to set up your project:

```bash
# Use existing project directly
cd /mnt/c/dev/tools/crypto-trading-bot-2025/

# Install dependencies in WSL
python -m pip install --upgrade pip
pip install -r requirements.txt

# Launch the bot
python main.py
```

## WSL-Specific Optimizations

1. **File System Performance**: Uses native Linux file system (not /mnt/c)
2. **Process Management**: Native Linux signals and process handling
3. **Dependencies**: No Windows-specific packages
4. **Paths**: Unix-style paths throughout
5. **Performance**: Can use Linux-specific optimizations

## Next Steps

1. Open WSL (Ubuntu)
2. Navigate to the project: `cd /mnt/c/dev/tools/crypto-trading-bot-2025/`
3. Install dependencies: `pip install -r requirements.txt`
4. Configure your API credentials in `config.json`
5. Launch the bot: `python main.py`
