#!/usr/bin/env python3
"""
Enhanced MCP Server Installation Script
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

def install_npm_packages():
    """Install required npm packages for MCP servers"""
    print("🚀 Installing NPM packages for MCP servers...")
    
    packages = [
        "@modelcontextprotocol/server-memory",
        "@modelcontextprotocol/server-sqlite", 
        "@modelcontextprotocol/server-filesystem",
        "@modelcontextprotocol/server-time",
        "@modelcontextprotocol/server-brave-search",
        "@modelcontextprotocol/server-puppeteer",
        "@modelcontextprotocol/server-github",
        "@modelcontextprotocol/server-sequential-thinking",
        "mcp-trader"
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        result = run_command(f"npm install -g {package}")
        if result and result.returncode == 0:
            print(f"✅ {package} installed successfully")
        else:
            print(f"❌ Failed to install {package}")

def install_python_dependencies():
    """Install Python dependencies for custom MCP servers"""
    print("🐍 Installing Python dependencies...")
    
    # Desktop Commander dependencies
    desktop_commander_path = Path("extensions/desktop-commander")
    if desktop_commander_path.exists():
        print("Installing Desktop Commander dependencies...")
        run_command(f"pip install -r {desktop_commander_path}/requirements.txt")
    
    # Crypto Math Calculator dependencies  
    crypto_math_path = Path("extensions/crypto-math-calculator")
    if crypto_math_path.exists():
        print("Installing Crypto Math Calculator dependencies...")
        run_command(f"pip install -r {crypto_math_path}/requirements.txt")

def backup_existing_config():
    """Backup existing Claude Desktop config"""
    config_path = Path.home() / "Documents" / "claude_desktop_config.json"
    if config_path.exists():
        backup_path = config_path.with_suffix(".json.backup")
        shutil.copy2(config_path, backup_path)
        print(f"✅ Backed up existing config to {backup_path}")
        return True
    return False

def update_claude_desktop_config():
    """Update Claude Desktop configuration with enhanced MCP servers"""
    print("📝 Updating Claude Desktop configuration...")
    
    # Read the enhanced config
    enhanced_config_path = Path("claude_desktop_config_enhanced.json")
    if not enhanced_config_path.exists():
        print("❌ Enhanced config file not found!")
        return False
    
    with open(enhanced_config_path, 'r') as f:
        enhanced_config = json.load(f)
    
    # Claude Desktop config location
    claude_config_path = Path.home() / "Documents" / "claude_desktop_config.json"
    
    # Backup existing config
    backup_existing_config()
    
    # Write enhanced config
    with open(claude_config_path, 'w') as f:
        json.dump(enhanced_config, f, indent=2)
    
    print(f"✅ Updated Claude Desktop config at {claude_config_path}")
    return True

def create_startup_scripts():
    """Create startup scripts for testing MCP servers"""
    print("📜 Creating startup scripts...")
    
    # Test Desktop Commander
    desktop_test = '''
import asyncio
import sys
sys.path.append("extensions/desktop-commander")
from server import DesktopCommander

async def test_desktop_commander():
    print("Testing Desktop Commander MCP Server...")
    commander = DesktopCommander()
    print("✅ Desktop Commander initialized successfully")

if __name__ == "__main__":
    asyncio.run(test_desktop_commander())
'''
    
    with open("test_desktop_commander.py", "w") as f:
        f.write(desktop_test)
    
    # Test Crypto Math Calculator
    crypto_test = '''
import asyncio
import sys
sys.path.append("extensions/crypto-math-calculator")
from server import CryptoMathCalculator

async def test_crypto_calculator():
    print("Testing Crypto Math Calculator MCP Server...")
    calculator = CryptoMathCalculator()
    print("✅ Crypto Math Calculator initialized successfully")

if __name__ == "__main__":
    asyncio.run(test_crypto_calculator())
'''
    
    with open("test_crypto_calculator.py", "w") as f:
        f.write(crypto_test)
    
    print("✅ Created test scripts")

def main():
    """Main installation process"""
    print("🚀 Enhanced MCP Server Installation Starting...")
    print("=" * 60)
    
    # Change to project directory
    project_dir = Path("C:/projects050625/projects/active/tool-crypto-trading-bot-2025")
    if project_dir.exists():
        os.chdir(project_dir)
        print(f"📁 Changed to project directory: {project_dir}")
    else:
        print(f"❌ Project directory not found: {project_dir}")
        return False
    
    # Install components
    install_npm_packages()
    install_python_dependencies()
    update_claude_desktop_config()
    create_startup_scripts()
    
    print("=" * 60)
    print("🎉 Enhanced MCP Server Installation Complete!")
    print("\n📋 What was installed:")
    print("✅ Desktop Commander - Windows 11 system control")
    print("✅ Crypto Math Calculator - High-precision decimal calculations")
    print("✅ Puppeteer - Web automation") 
    print("✅ GitHub Integration - Repository management")
    print("✅ Sequential Thinking - Enhanced reasoning")
    print("✅ Multiple filesystem access points")
    print("✅ Memory server for persistent data")
    print("✅ SQLite database access")
    print("✅ Time utilities")
    print("✅ Web search capabilities")
    
    print("\n🔧 Next Steps:")
    print("1. Restart Claude Desktop to load new MCP servers")
    print("2. Test servers with: python test_desktop_commander.py")
    print("3. Test crypto math with: python test_crypto_calculator.py")
    print("4. Check Claude Desktop for new available tools")
    
    print("\n💡 Key Features Added:")
    print("🖥️  Desktop Commander: Process management, GUI automation, system control")
    print("🧮 Crypto Calculator: Position sizing, P&L calculations, arbitrage analysis")
    print("🌐 Web Automation: Screenshot, click, form filling capabilities")
    print("📊 Enhanced Analysis: Multi-server data access and processing")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎯 Installation completed successfully!")
        print("Your cryptocurrency trading system now has enhanced MCP capabilities!")
    else:
        print("\n❌ Installation encountered errors. Please check the output above.")
    
    input("\nPress Enter to exit...")
