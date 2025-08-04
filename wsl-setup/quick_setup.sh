#!/bin/bash
# Quick WSL Trading Bot Setup Script
# Run this after copying to WSL

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}Kraken Trading Bot WSL Setup${NC}"
echo -e "${CYAN}=====================================${NC}"

# Check if running in WSL
if ! grep -q Microsoft /proc/version; then
    echo -e "${YELLOW}Warning: This doesn't appear to be WSL${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set project directory
PROJECT_DIR="$HOME/projects/kraken-trading-bot-wsl"

echo -e "${GREEN}Creating project directory: $PROJECT_DIR${NC}"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create directory structure
echo -e "${GREEN}Creating project structure...${NC}"
mkdir -p {src/{core,exchange,trading,utils,analysis,learning},config,logs,data/{cache,backups},scripts,tests,docs}

# Install system dependencies
echo -e "${GREEN}Installing system dependencies...${NC}"
sudo apt update
sudo apt install -y software-properties-common curl git build-essential

# Install Python 3.11
echo -e "${GREEN}Installing Python 3.11...${NC}"
if ! command -v python3.11 &> /dev/null; then
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3.11-dev
else
    echo -e "${YELLOW}Python 3.11 already installed${NC}"
fi

# Create virtual environment
echo -e "${GREEN}Creating virtual environment...${NC}"
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip wheel setuptools

# Create essential files
echo -e "${GREEN}Creating configuration files...${NC}"

# Create .env template
cat > .env.template << 'EOF'
# Kraken API Credentials
KRAKEN_API_KEY="your_api_key_here"
KRAKEN_API_SECRET="your_api_secret_here"

# Bot Configuration
BOT_ENV="development"
LOG_LEVEL="INFO"
USE_WEBSOCKET_V2=true
USE_AMEND_ORDERS=true

# WSL Paths
DATA_DIR="$HOME/projects/kraken-trading-bot-wsl/data"
LOG_DIR="$HOME/projects/kraken-trading-bot-wsl/logs"
EOF

# Create requirements.txt
cat > requirements.txt << 'EOF'
# Core dependencies
ccxt==4.4.50
websocket-client==1.8.0
websockets==13.1
python-dotenv==1.0.1
aiofiles==24.1.0
aiohttp==3.11.11

# Data handling
pandas==2.2.3
numpy==2.0.2
scipy==1.14.1

# Technical analysis
ta==0.11.0
pandas-ta==0.3.14b0

# Logging
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
black==24.10.0
flake8==7.1.1
EOF

# Install dependencies
echo -e "${GREEN}Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Create basic bot structure
echo -e "${GREEN}Creating basic bot structure...${NC}"

# Create __init__.py files
touch src/__init__.py
touch src/core/__init__.py
touch src/exchange/__init__.py
touch src/trading/__init__.py
touch src/utils/__init__.py

# Create config.py
cat > src/config.py << 'EOF'
"""Configuration loader for WSL environment"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def load_config():
    """Load configuration from YAML and environment"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    
    # Default configuration
    config = {
        "exchange": {
            "name": "kraken",
            "test_mode": False,
            "websocket": {
                "use_v2": True,
                "heartbeat_interval": 30
            }
        },
        "trading": {
            "strategy": "micro_scalper",
            "pairs": ["BTC/USDT", "ETH/USDT", "DOGE/USDT"],
            "position_sizing": {
                "min_position_value": 10.0,
                "max_position_value": 100.0
            }
        },
        "paths": {
            "data_dir": os.environ.get("DATA_DIR", "~/projects/kraken-trading-bot-wsl/data"),
            "log_dir": os.environ.get("LOG_DIR", "~/projects/kraken-trading-bot-wsl/logs")
        }
    }
    
    # Load from YAML if exists
    if config_path.exists():
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                config.update(yaml_config)
    
    # Expand paths
    for key in ['data_dir', 'log_dir']:
        if key in config['paths']:
            config['paths'][key] = os.path.expanduser(config['paths'][key])
    
    return config
EOF

# Create a simple test script
cat > test_setup.py << 'EOF'
#!/usr/bin/env python3
"""Test WSL bot setup"""
import sys
import os
from pathlib import Path

print("Testing WSL Trading Bot Setup...")

# Test Python version
print(f"Python version: {sys.version}")

# Test imports
try:
    import ccxt
    print("✓ ccxt imported successfully")
except ImportError:
    print("✗ ccxt import failed")

try:
    import pandas
    print("✓ pandas imported successfully")
except ImportError:
    print("✗ pandas import failed")

try:
    from dotenv import load_dotenv
    print("✓ python-dotenv imported successfully")
except ImportError:
    print("✗ python-dotenv import failed")

# Test paths
project_root = Path(__file__).parent
print(f"\nProject root: {project_root}")
print(f"Data directory exists: {(project_root / 'data').exists()}")
print(f"Logs directory exists: {(project_root / 'logs').exists()}")

# Test environment
load_dotenv()
api_key = os.environ.get('KRAKEN_API_KEY', '')
print(f"\nAPI Key configured: {'Yes' if api_key else 'No'}")

print("\nSetup test complete!")
EOF

chmod +x test_setup.py

# Create launch script
cat > launch_bot.sh << 'EOF'
#!/bin/bash
# Launch the trading bot

# Activate virtual environment
source venv/bin/activate

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Copy .env.template to .env and add your API credentials"
    exit 1
fi

# Run the bot
echo "Starting Kraken Trading Bot (WSL Edition)..."
python src/main.py
EOF

chmod +x launch_bot.sh

# Final instructions
echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}=====================================${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Copy .env.template to .env and add your Kraken API credentials:"
echo "   cp .env.template .env"
echo "   nano .env"
echo ""
echo "2. Copy your bot source files from Windows (optional):"
echo "   cp -r /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025/src/* src/"
echo ""
echo "3. Test the setup:"
echo "   source venv/bin/activate"
echo "   python test_setup.py"
echo ""
echo "4. Launch the bot:"
echo "   ./launch_bot.sh"
echo ""
echo -e "${CYAN}Project location: $PROJECT_DIR${NC}"
echo -e "${CYAN}Virtual environment: $PROJECT_DIR/venv${NC}"
