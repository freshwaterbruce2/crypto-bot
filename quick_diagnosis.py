#!/usr/bin/env python3
"""
Quick Diagnosis Script
=====================

Fast diagnosis of trading bot readiness without full initialization.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_environment():
    """Check basic environment setup"""
    print("🔍 Checking Environment...")
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Python 3.8+ required")
        return False
    else:
        print("✅ Python version OK")
    
    # Check project structure
    required_dirs = ['src', 'src/auth', 'src/websocket', 'src/api', 'src/orchestrator']
    for directory in required_dirs:
        if not Path(directory).exists():
            print(f"❌ Missing directory: {directory}")
            return False
    print("✅ Project structure OK")
    
    # Check config file
    if not Path('config.json').exists():
        print("❌ Missing config.json file")
        return False
    else:
        print("✅ Config file exists")
    
    return True

def check_credentials():
    """Check API credentials"""
    print("\n🔑 Checking Credentials...")
    
    api_key = os.getenv('KRAKEN_API_KEY')
    private_key = os.getenv('KRAKEN_PRIVATE_KEY')
    
    if not api_key:
        print("❌ KRAKEN_API_KEY environment variable not set")
        return False
    
    if not private_key:
        print("❌ KRAKEN_PRIVATE_KEY environment variable not set")
        return False
    
    if len(api_key) < 20 or len(private_key) < 50:
        print("❌ API credentials appear too short (invalid format)")
        return False
    
    print("✅ API credentials found and appear valid")
    return True

def check_dependencies():
    """Check critical dependencies"""
    print("\n📦 Checking Dependencies...")
    
    critical_modules = [
        'asyncio',
        'logging',
        'json',
        'decimal',
        'websockets',
        'aiohttp'
    ]
    
    missing_modules = []
    
    for module in critical_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - MISSING")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n❌ Missing modules: {', '.join(missing_modules)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def check_imports():
    """Check project imports"""
    print("\n🔌 Checking Project Imports...")
    
    try:
        from src.auth.credential_manager import CredentialManager
        print("✅ CredentialManager")
    except Exception as e:
        print(f"❌ CredentialManager: {e}")
        return False
    
    try:
        from src.auth.auth_service import AuthService
        print("✅ AuthService")
    except Exception as e:
        print(f"❌ AuthService: {e}")
        return False
    
    try:
        from src.websocket.kraken_websocket_v2 import KrakenWebSocketV2
        print("✅ KrakenWebSocketV2")
    except Exception as e:
        print(f"❌ KrakenWebSocketV2: {e}")
        return False
    
    try:
        from src.websocket.kraken_v2_message_handler import KrakenV2MessageHandler
        print("✅ KrakenV2MessageHandler")
    except Exception as e:
        print(f"❌ KrakenV2MessageHandler: {e}")
        return False
    
    try:
        from src.orchestrator.system_orchestrator import SystemOrchestrator
        print("✅ SystemOrchestrator")
    except Exception as e:
        print(f"❌ SystemOrchestrator: {e}")
        return False
    
    return True

def main():
    """Run quick diagnosis"""
    print("🚀 Quick Trading Bot Diagnosis")
    print("=" * 50)
    
    results = []
    
    # Check environment
    results.append(check_environment())
    
    # Check credentials
    results.append(check_credentials())
    
    # Check dependencies
    results.append(check_dependencies())
    
    # Check imports
    results.append(check_imports())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DIAGNOSIS SUMMARY")
    print("=" * 50)
    
    if all(results):
        print("✅ ALL CHECKS PASSED!")
        print("\n🎯 Ready to launch bot with:")
        print("   python launch_bot_fixed.py")
        print("   python main_orchestrated.py")
        return 0
    else:
        print("❌ SOME CHECKS FAILED!")
        print("\n🔧 Fix the issues above before launching the bot")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)