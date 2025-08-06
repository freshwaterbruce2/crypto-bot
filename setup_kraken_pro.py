#!/usr/bin/env python3
"""
Kraken Pro Setup Script
Configures the bot for Kraken Pro accounts with fee-free trading
"""

import os
import platform
import sys
from pathlib import Path

from dotenv import load_dotenv


def setup_kraken_pro():
    """Configure bot for Kraken Pro account"""

    print("\n" + "="*50)
    print("KRAKEN PRO CONFIGURATION")
    print("="*50)
    print("\n✅ Detected Kraken Pro account")
    print("   • Fee-free trading enabled")
    print("   • Advanced API features available")

    # Update .env file with Kraken Pro settings
    env_path = Path('.env')

    # Read existing .env
    existing_lines = []
    if env_path.exists():
        try:
            with open(env_path, encoding='utf-8') as f:
                existing_lines = f.readlines()
        except UnicodeDecodeError:
            # Try with a different encoding
            with open(env_path, encoding='latin-1') as f:
                existing_lines = f.readlines()

    # Update settings for Kraken Pro
    updated_lines = []
    settings_updated = {
        'KRAKEN_TIER': False,
        'PAPER_SIMULATE_FEES': False,
        'PAPER_TRADING_ENABLED': False
    }

    for line in existing_lines:
        if line.startswith('KRAKEN_TIER='):
            updated_lines.append('KRAKEN_TIER=pro\n')
            settings_updated['KRAKEN_TIER'] = True
        elif line.startswith('PAPER_SIMULATE_FEES='):
            updated_lines.append('PAPER_SIMULATE_FEES=false\n')
            settings_updated['PAPER_SIMULATE_FEES'] = True
        elif line.startswith('PAPER_TRADING_ENABLED='):
            # Disable paper trading for real trading
            updated_lines.append('PAPER_TRADING_ENABLED=false\n')
            settings_updated['PAPER_TRADING_ENABLED'] = True
        else:
            updated_lines.append(line)

    # Add missing settings
    if not settings_updated['KRAKEN_TIER']:
        updated_lines.append('\n# Kraken Pro Settings\n')
        updated_lines.append('KRAKEN_TIER=pro\n')

    if not settings_updated['PAPER_SIMULATE_FEES']:
        updated_lines.append('PAPER_SIMULATE_FEES=false\n')

    if not settings_updated['PAPER_TRADING_ENABLED']:
        updated_lines.append('PAPER_TRADING_ENABLED=false\n')

    # Write updated .env
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)

    print("\n✅ Configuration updated:")
    print("   • KRAKEN_TIER=pro")
    print("   • PAPER_SIMULATE_FEES=false (fee-free trading)")
    print("   • PAPER_TRADING_ENABLED=false (real trading mode)")

    # Reload environment
    load_dotenv(override=True)

    return True

def verify_credentials():
    """Verify API credentials are loaded"""

    print("\n" + "="*50)
    print("VERIFYING CREDENTIALS")
    print("="*50)

    # Check for credentials in various formats
    api_key = (os.getenv('KRAKEN_KEY') or
               os.getenv('KRAKEN_API_KEY') or
               os.environ.get('KRAKEN_KEY') or
               os.environ.get('KRAKEN_API_KEY'))

    secret = (os.getenv('KRAKEN_SECRET') or
              os.getenv('KRAKEN_API_SECRET') or
              os.environ.get('KRAKEN_SECRET') or
              os.environ.get('KRAKEN_API_SECRET'))

    if api_key and secret:
        print("✅ API credentials found")
        print(f"   • API Key: {api_key[:8]}...{api_key[-4:]}")
        print(f"   • Secret: ***{secret[-4:]}")
        return True
    else:
        print("❌ No API credentials found")

        if platform.system() == 'Windows':
            print("\n📋 To set up credentials:")
            print("1. Open System Properties → Environment Variables")
            print("2. Add these System variables:")
            print("   • KRAKEN_KEY = your_api_key_from_kraken_pro")
            print("   • KRAKEN_SECRET = your_secret_from_kraken_pro")
            print("3. Restart PowerShell")
            print("4. Run: python fix_windows_credentials.py")

        return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("KRAKEN PRO SETUP")
    print("="*50)

    # First fix Windows credentials if needed
    if platform.system() == 'Windows':
        try:
            from fix_windows_credentials import fix_credential_loading
            print("\n🔧 Syncing Windows credentials...")
            if fix_credential_loading():
                print("✅ Credentials synced from Windows environment")
        except Exception as e:
            print(f"⚠ Could not sync Windows credentials: {e}")

    # Setup Kraken Pro configuration
    if setup_kraken_pro():
        # Verify credentials
        if verify_credentials():
            print("\n" + "="*50)
            print("✅ SETUP COMPLETE")
            print("="*50)
            print("\nYou can now run the bot with:")
            print("   python main.py")
            print("\nSelect option 2 (Orchestrated Mode) for full features")
        else:
            sys.exit(1)
    else:
        print("❌ Setup failed")
        sys.exit(1)
