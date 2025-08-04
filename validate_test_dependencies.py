#!/usr/bin/env python3
"""
Balance Manager Test Dependencies Validator
==========================================

Quick check to ensure all required modules and dependencies
are available before running the main test.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / "src"))

def validate_imports():
    """Validate all required imports are available"""
    missing_modules = []
    
    try:
        # Core Python modules
        import asyncio
        import json
        import logging
        import os
        import time
        print("✓ Core Python modules available")
    except ImportError as e:
        missing_modules.append(f"Core Python module: {e}")
    
    try:
        # Exchange components
        from src.exchange.exchange_singleton import get_exchange
        print("✓ Exchange singleton import successful")
    except ImportError as e:
        missing_modules.append(f"Exchange singleton: {e}")
    
    try:
        # Balance Manager V2
        from src.balance.balance_manager_v2 import BalanceManagerV2, BalanceManagerV2Config
        print("✓ Balance Manager V2 import successful")
    except ImportError as e:
        missing_modules.append(f"Balance Manager V2: {e}")
    
    try:
        # WebSocket client
        from src.websocket.kraken_websocket_v2 import KrakenWebSocketV2
        print("✓ WebSocket V2 client import successful")
    except ImportError as e:
        missing_modules.append(f"WebSocket V2 client: {e}")
    
    try:
        # Configuration
        from src.config.core import load_config
        print("✓ Configuration loader import successful")
    except ImportError as e:
        missing_modules.append(f"Configuration loader: {e}")
    
    try:
        # Credentials
        from src.utils.secure_credentials import SecureCredentials
        print("✓ Secure credentials import successful")
    except ImportError as e:
        missing_modules.append(f"Secure credentials: {e}")
    
    return missing_modules

def check_config_files():
    """Check if required configuration files exist"""
    missing_files = []
    
    config_file = Path(__file__).parent / "config.json"
    if not config_file.exists():
        missing_files.append("config.json")
    else:
        print("✓ config.json found")
    
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("⚠ .env file not found (may be optional)")
    else:
        print("✓ .env file found")
    
    return missing_files

def main():
    """Main validation"""
    print("Balance Manager Test Dependencies Validation")
    print("=" * 50)
    
    # Check imports
    print("\nChecking Python imports...")
    missing_modules = validate_imports()
    
    if missing_modules:
        print("\n✗ MISSING MODULES:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\nPlease install missing dependencies before running the test.")
        return 1
    
    # Check config files
    print("\nChecking configuration files...")
    missing_files = check_config_files()
    
    if missing_files:
        print("\n⚠ MISSING CONFIG FILES:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nSome configuration files are missing but test may still work.")
    
    print("\n✓ Dependency validation completed successfully")
    print("You can now run the Balance Manager V2 fixes test.")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except ImportError as e:
        print(f"\n✗ CRITICAL IMPORT ERROR: {e}")
        print("Cannot proceed with validation - check your Python environment.")
        sys.exit(2)
    except Exception as e:
        print(f"\n✗ VALIDATION ERROR: {e}")
        sys.exit(3)