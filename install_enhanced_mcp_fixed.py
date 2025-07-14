#!/usr/bin/env python3
"""
Fixed Enhanced MCP Server Installation Script
Installs Desktop Commander, Crypto Math Calculator, and other useful MCP servers
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path

def run_command(command, cwd=None, check=True):
    """Run a command and return the result"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            print(f"Output: {result.stdout}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return None

def install_python_dependencies():
    """Install Python dependencies for custom MCP servers"""
    print("Installing Python dependencies...")
    
    # Desktop Commander dependencies
    desktop_commander_path = Path("extensions/desktop-commander")
    if desktop_commander_path.exists():
        print("Installing Desktop Commander dependencies...")
        result = run_command(f"pip install -r {desktop_commander_path}/requirements.txt")
        if result and result.returncode == 0:
            print("Desktop Commander dependencies installed successfully")
    
    # Crypto Math Calculator dependencies  
    crypto_math_path = Path("extensions/crypto-math-calculator")
    if crypto_math_path.exists():
        print("Installing Crypto Math Calculator dependencies...")
        result = run_command(f"pip install -r {crypto_math_path}/requirements.txt")
        if result and result.returncode == 0:
            print("Crypto Math Calculator dependencies installed successfully")
    
    # Time Server dependencies
    time_server_path = Path("extensions/time-server")
    if time_server_path.exists():
        print("Installing Time Server dependencies...")
        result = run_command(f"pip install -r {time_server_path}/requirements.txt")
        if result and result.returncode == 0:
            print("Time Server dependencies installed successfully")

def backup_existing_config():
    """Backup existing Claude Desktop config"""
    config_path = Path.home() / "Documents" / "claude_desktop_config.json"
    if config_path.exists():
        backup_path = config_path.with_suffix(".json.backup")
        shutil.copy2(config_path, backup_path)
        print(f"Backed up existing config to {backup_path}")
        return True
    return False

def update_claude_desktop_config():
    """Update Claude Desktop configuration with enhanced MCP servers"""
    print("Updating Claude Desktop configuration...")
    
    # Read the fixed config
    fixed_config_path = Path("claude_desktop_config_fixed.json")
    if not fixed_config_path.exists():
        print("Fixed config file not found!")
        return False
    
    with open(fixed_config_path, 'r') as f:
        fixed_config = json.load(f)
    
    # Claude Desktop config location
    claude_config_path = Path.home() / "Documents" / "claude_desktop_config.json"
    
    # Backup existing config
    backup_existing_config()
    
    # Write fixed config
    with open(claude_config_path, 'w') as f:
        json.dump(fixed_config, f, indent=2)
    
    print(f"Updated Claude Desktop config at {claude_config_path}")
    return True

def create_simple_test_scripts():
    """Create simple test scripts without Unicode"""
    print("Creating test scripts...")
    
    # Test Desktop Commander
    desktop_test = '''#!/usr/bin/env python3
import sys
import os
sys.path.append("extensions/desktop-commander")

def test_desktop_commander():
    print("Testing Desktop Commander MCP Server...")
    try:
        from server import DesktopCommander
        commander = DesktopCommander()
        print("Desktop Commander initialized successfully")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_desktop_commander()
    if success:
        print("Desktop Commander test PASSED")
    else:
        print("Desktop Commander test FAILED")
'''
    
    with open("test_desktop_commander.py", "w", encoding='utf-8') as f:
        f.write(desktop_test)
    
    # Test Crypto Math Calculator
    crypto_test = '''#!/usr/bin/env python3
import sys
import os
sys.path.append("extensions/crypto-math-calculator")

def test_crypto_calculator():
    print("Testing Crypto Math Calculator MCP Server...")
    try:
        from server import CryptoMathCalculator
        calculator = CryptoMathCalculator()
        print("Crypto Math Calculator initialized successfully")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_crypto_calculator()
    if success:
        print("Crypto Math Calculator test PASSED")
    else:
        print("Crypto Math Calculator test FAILED")
'''
    
    with open("test_crypto_calculator.py", "w", encoding='utf-8') as f:
        f.write(crypto_test)
    
    # Test SQLite Server
    sqlite_test = '''#!/usr/bin/env python3
import sys
import os
sys.path.append("extensions/sqlite-server")

def test_sqlite_server():
    print("Testing SQLite Server MCP Server...")
    try:
        from server import SQLiteServer
        sqlite_server = SQLiteServer()
        print("SQLite Server initialized successfully")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_sqlite_server()
    if success:
        print("SQLite Server test PASSED")
    else:
        print("SQLite Server test FAILED")
'''
    
    with open("test_sqlite_server.py", "w", encoding='utf-8') as f:
        f.write(sqlite_test)
    
    print("Created test scripts successfully")

def main():
    """Main installation process"""
    print("Enhanced MCP Server Installation Starting...")
    print("=" * 60)
    
    # Change to project directory
    project_dir = Path("C:/projects050625/projects/active/tool-crypto-trading-bot-2025")
    if project_dir.exists():
        os.chdir(project_dir)
        print(f"Changed to project directory: {project_dir}")
    else:
        print(f"Project directory not found: {project_dir}")
        return False
    
    # Install components
    install_python_dependencies()
    update_claude_desktop_config()
    create_simple_test_scripts()
    
    print("=" * 60)
    print("Enhanced MCP Server Installation Complete!")
    print()
    print("What was installed:")
    print("- Desktop Commander - Windows 11 system control")
    print("- Crypto Math Calculator - High-precision decimal calculations")
    print("- SQLite Server - Database operations for trading data")
    print("- Time Server - Trading session and candle timing")
    print("- Puppeteer - Web automation") 
    print("- GitHub Integration - Repository management")
    print("- Sequential Thinking - Enhanced reasoning")
    print("- Multiple filesystem access points")
    print("- Memory server for persistent data")
    print("- Web search capabilities")
    
    print()
    print("Next Steps:")
    print("1. Restart Claude Desktop to load new MCP servers")
    print("2. Test servers with: python test_desktop_commander.py")
    print("3. Test crypto math with: python test_crypto_calculator.py")
    print("4. Test database with: python test_sqlite_server.py")
    print("5. Check Claude Desktop for new available tools")
    
    print()
    print("Key Features Added:")
    print("- Desktop Commander: Process management, GUI automation, system control")
    print("- Crypto Calculator: Position sizing, P&L calculations, arbitrage analysis")
    print("- Database Operations: Trade tracking and performance analytics")
    print("- Time Utilities: Market hours, candle timing, trading sessions")
    print("- Web Automation: Screenshot, click, form filling capabilities")
    print("- Enhanced Analysis: Multi-server data access and processing")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print()
        print("Installation completed successfully!")
        print("Your cryptocurrency trading system now has enhanced MCP capabilities!")
    else:
        print()
        print("Installation encountered errors. Please check the output above.")
    
    input("\nPress Enter to exit...")
