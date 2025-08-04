#!/bin/bash
# Migrate Windows Trading Bot to WSL
# This script helps adapt your Windows bot for WSL

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Windows to WSL Bot Migration ===${NC}"

# Source and destination
WINDOWS_SRC="/mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025"
WSL_DEST="$HOME/projects/kraken-trading-bot-wsl"

# Check if source exists
if [ ! -d "$WINDOWS_SRC" ]; then
    echo -e "${RED}Error: Windows source not found at $WINDOWS_SRC${NC}"
    exit 1
fi

# Check if destination exists
if [ ! -d "$WSL_DEST" ]; then
    echo -e "${RED}Error: WSL project not found. Run quick_setup.sh first!${NC}"
    exit 1
fi

cd "$WSL_DEST"

echo -e "${YELLOW}Copying Python source files...${NC}"

# Copy core modules
for module in core exchange trading utils; do
    if [ -d "$WINDOWS_SRC/src/$module" ]; then
        echo "Copying $module..."
        cp -r "$WINDOWS_SRC/src/$module"/* "src/$module/" 2>/dev/null || true
    fi
done

# Copy specific files
for file in config.py __init__.py; do
    if [ -f "$WINDOWS_SRC/src/$file" ]; then
        cp "$WINDOWS_SRC/src/$file" "src/"
    fi
done

echo -e "${YELLOW}Adapting files for WSL...${NC}"

# Fix common Windows-specific issues
find src -name "*.py" -type f -exec sed -i \
    -e 's/C:\\projects050625/\/home\/$USER\/projects/g' \
    -e 's/D:\\trading_data/~\/projects\/kraken-trading-bot-wsl\/data/g' \
    -e 's/D:\\trading_bot_data/~\/projects\/kraken-trading-bot-wsl\/data/g' \
    -e 's/\\/\//g' \
    -e 's/Path(r"/Path("/g' \
    -e 's/colorama/# colorama not needed in Linux/g' \
    {} \;

# Create WSL-specific config overrides
cat > src/wsl_config_override.py << 'EOF'
"""WSL-specific configuration overrides"""
import os
from pathlib import Path

def apply_wsl_overrides(config):
    """Apply WSL-specific configuration overrides"""
    
    # Update paths for WSL
    home = Path.home()
    project_root = home / "projects" / "kraken-trading-bot-wsl"
    
    config['paths'] = {
        'data_dir': str(project_root / "data"),
        'log_dir': str(project_root / "logs"),
        'cache_dir': str(project_root / "data" / "cache"),
    }
    
    # WSL-optimized settings
    config['performance'] = {
        'use_uvloop': True,  # Faster event loop for Linux
        'multi_threading': True,
        'worker_threads': os.cpu_count() or 4,
    }
    
    # Ensure WebSocket v2 and amend support
    if 'exchange' not in config:
        config['exchange'] = {}
    config['exchange']['websocket'] = {
        'use_v2': True,
        'heartbeat_interval': 30,
        'reconnect_attempts': 5,
    }
    
    # Enable amend orders
    if 'trading' not in config:
        config['trading'] = {}
    config['trading']['use_amend_orders'] = True
    
    return config
EOF

# Update main config.py to use overrides
if [ -f "src/config.py" ]; then
    echo -e "\n# WSL overrides\ntry:\n    from .wsl_config_override import apply_wsl_overrides\n    config = apply_wsl_overrides(config)\nexcept ImportError:\n    pass" >> src/config.py
fi

# Create a compatibility layer for Windows-specific modules
cat > src/utils/wsl_compat.py << 'EOF'
"""WSL compatibility layer"""
import sys
import os

# Disable Windows-specific modules
sys.modules['colorama'] = None
sys.modules['win32api'] = None
sys.modules['win32con'] = None

# Path compatibility
def fix_path(path):
    """Convert Windows paths to WSL paths"""
    if isinstance(path, str):
        # Convert Windows paths
        if path.startswith('C:\\'):
            path = path.replace('C:\\', '/mnt/c/')
        elif path.startswith('D:\\'):
            path = path.replace('D:\\', '/mnt/d/')
        
        # Convert backslashes
        path = path.replace('\\', '/')
        
        # Expand user paths
        if path.startswith('~'):
            path = os.path.expanduser(path)
    
    return path

# Override built-in open to handle path conversion
_original_open = open
def open(file, *args, **kwargs):
    return _original_open(fix_path(file), *args, **kwargs)

# Make it available globally
__builtins__['open'] = open
EOF

# Check for missing dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"

# Activate virtual environment
source venv/bin/activate

# Install any missing dependencies
MISSING_DEPS=""
for dep in ccxt websockets pandas numpy; do
    if ! python -c "import $dep" 2>/dev/null; then
        MISSING_DEPS="$MISSING_DEPS $dep"
    fi
done

if [ -n "$MISSING_DEPS" ]; then
    echo -e "${YELLOW}Installing missing dependencies:$MISSING_DEPS${NC}"
    pip install $MISSING_DEPS
fi

# Create test script
cat > test_migration.py << 'EOF'
#!/usr/bin/env python3
"""Test migrated bot setup"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("Testing migrated bot...")

# Test imports
try:
    from src.config import load_config
    print("✓ Config module loaded")
    
    config = load_config()
    print(f"✓ Configuration loaded: {config.get('trading', {}).get('strategy', 'unknown')}")
    
    # Check paths
    data_dir = config.get('paths', {}).get('data_dir', '')
    if '/home/' in data_dir or '~' in data_dir:
        print("✓ Paths adapted for WSL")
    else:
        print("⚠ Paths may need adjustment")
        
except Exception as e:
    print(f"✗ Error loading config: {e}")

# Test exchange modules
try:
    from src.exchange import *
    print("✓ Exchange modules available")
except Exception as e:
    print(f"⚠ Exchange modules issue: {e}")

# Test trading modules  
try:
    from src.trading import *
    print("✓ Trading modules available")
except Exception as e:
    print(f"⚠ Trading modules issue: {e}")

print("\nMigration test complete!")
print("Run './launch_bot.sh' to start the bot")
EOF

chmod +x test_migration.py

# Summary
echo -e "\n${GREEN}=== Migration Complete ===${NC}"
echo -e "${GREEN}Files copied and adapted for WSL${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Test migration: ${GREEN}python test_migration.py${NC}"
echo "2. Review and fix any remaining Windows-specific code"
echo "3. Update your .env file with API credentials"
echo "4. Launch bot: ${GREEN}./launch_bot.sh${NC}"
echo -e "\n${YELLOW}Common fixes needed:${NC}"
echo "- File paths (C:\\ → /home/\$USER/)"
echo "- Remove colorama (not needed in Linux)"
echo "- Update any hardcoded Windows paths"
echo "- Check file permissions (chmod +x for scripts)"
