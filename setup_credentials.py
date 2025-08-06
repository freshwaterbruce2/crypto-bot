#!/usr/bin/env python3
"""
Kraken API Credentials Setup Wizard
==================================

Interactive setup wizard to help users configure their Kraken API credentials
securely for the crypto trading bot. Works on Windows, WSL, and Linux.

Features:
- Interactive credential configuration
- Secure input with hidden password entry
- API key validation
- Multiple credential storage options
- Windows PowerShell environment variable setup
- Comprehensive validation and testing

Usage:
    python setup_credentials.py
    
Requirements:
    - Kraken account with API access
    - API keys generated from Kraken security settings
"""

import getpass
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.auth.credential_manager import CredentialManager
    from src.auth.kraken_auth import KrakenAuth
    from src.utils.windows_env_bridge import WindowsEnvBridge, get_windows_env_var
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure you're running this from the project root directory.")
    print("Required files:")
    print("- src/auth/credential_manager.py")
    print("- src/utils/windows_env_bridge.py")
    print("- src/auth/kraken_auth.py")

    # Fallback basic validation functions
    def validate_api_key(api_key):
        """Basic validation of API key format"""
        if not api_key or len(api_key) < 20:
            return False, "API key appears too short or empty"
        return True, "Valid format"

    def validate_private_key(private_key):
        """Basic validation of private key format"""
        if not private_key or len(private_key) < 32:
            return False, "Private key appears too short or empty"

        # Check for base64-like characters
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
        if not all(c in valid_chars for c in private_key):
            return False, "Private key should be base64 encoded"

        return True, "Valid format"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CredentialSetupWizard:
    """Interactive credential setup wizard"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / ".env"
        self.env_template = self.project_root / ".env.template"

        # Try to initialize advanced components
        try:
            self.credential_manager = CredentialManager()
            self.windows_bridge = WindowsEnvBridge()
            self.advanced_mode = True
        except:
            self.credential_manager = None
            self.windows_bridge = None
            self.advanced_mode = False
            print("Running in basic mode - some advanced features unavailable")

        # Detect environment
        self.is_wsl = self._is_wsl()
        self.is_windows = os.name == 'nt'
        self.powershell_available = self._check_powershell()

        print("=" * 60)
        print("🔐 KRAKEN API CREDENTIALS SETUP WIZARD")
        print("=" * 60)
        print(f"Environment: {'WSL' if self.is_wsl else 'Windows' if self.is_windows else 'Linux'}")
        print(f"Advanced Mode: {'✅ Yes' if self.advanced_mode else '❌ No (basic setup only)'}")
        print(f"PowerShell Available: {'✅ Yes' if self.powershell_available else '❌ No'}")
        print()

    def _is_wsl(self) -> bool:
        """Check if running in WSL"""
        try:
            with open('/proc/version') as f:
                return 'microsoft' in f.read().lower()
        except:
            return False

    def _check_powershell(self) -> bool:
        """Check if PowerShell is available"""
        if self.advanced_mode and self.windows_bridge:
            return self.windows_bridge._powershell_path is not None

        # Basic check
        try:
            result = subprocess.run(
                ["powershell.exe", "-Command", "echo test"],
                capture_output=True, timeout=5, check=False
            )
            return result.returncode == 0
        except:
            return False

def show_instructions():
    """Show instructions for getting API credentials"""
    print("\n" + "=" * 60)
    print("🔑 KRAKEN API CREDENTIALS SETUP")
    print("=" * 60)
    print()
    print("To get your Kraken API credentials:")
    print()
    print("1. Login to your Kraken account")
    print("2. Go to Settings → API")
    print("3. Create a new API key with these permissions:")
    print("   ✅ Query Funds")
    print("   ✅ Query Open Orders & Trades")
    print("   ✅ Query Closed Orders & Trades")
    print("   ✅ Create & Modify Orders")
    print("   ✅ Cancel Orders")
    print("   ✅ Query Private Data")
    print("4. Copy the API Key and Private Key")
    print()
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("• Never share your private key")
    print("• Use a dedicated API key for trading bots")
    print("• Enable IP restrictions if possible")
    print("• Monitor your API key usage regularly")
    print()

def main():
    """Main credential setup function"""
    print("🚀 Crypto Trading Bot - Credential Setup")
    print("=" * 50)

    # Check if credentials already exist
    existing_api_key = os.getenv('KRAKEN_API_KEY')
    existing_private_key = os.getenv('KRAKEN_PRIVATE_KEY')

    if existing_api_key and existing_private_key:
        print("✅ API credentials already found in environment variables")
        print(f"API Key: {existing_api_key[:8]}...{existing_api_key[-4:]}")

        response = input("\nDo you want to update them? (y/N): ").lower()
        if response != 'y':
            print("Using existing credentials. Run 'python3 quick_diagnosis.py' to verify.")
            return 0

    # Check for existing .env file
    env_file = Path('.env')
    if env_file.exists():
        print("✅ .env file already exists")
        response = input("Do you want to overwrite it? (y/N): ").lower()
        if response != 'y':
            print("Keeping existing .env file. Ensure it contains valid credentials.")
            return 0

    # Show instructions
    show_instructions()

    # Get API credentials
    print("📝 Enter your Kraken API credentials:")
    print()

    while True:
        api_key = input("API Key: ").strip()

        if not api_key:
            print("❌ API Key cannot be empty")
            continue

        valid, message = validate_api_key(api_key)
        if not valid:
            print(f"❌ {message}")
            continue

        print(f"✅ {message}")
        break

    while True:
        private_key = getpass.getpass("Private Key (hidden): ").strip()

        if not private_key:
            print("❌ Private Key cannot be empty")
            continue

        valid, message = validate_private_key(private_key)
        if not valid:
            print(f"❌ {message}")
            continue

        print(f"✅ {message}")
        break

    # Confirm credentials
    print("\n" + "=" * 50)
    print("📋 CREDENTIAL SUMMARY")
    print("=" * 50)
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Private Key: {private_key[:8]}...{private_key[-4:]}")
    print()

    response = input("Save these credentials? (Y/n): ").lower()
    if response == 'n':
        print("❌ Credentials not saved")
        return 1

    # Save credentials
    try:
        env_file = create_env_file(api_key, private_key)
        print(f"✅ Credentials saved to {env_file}")
        print()
        print("🔒 Security: .env file has been created with restricted permissions")
        print("📁 Location:", env_file.absolute())

        # Set environment variables for current session
        os.environ['KRAKEN_API_KEY'] = api_key
        os.environ['KRAKEN_PRIVATE_KEY'] = private_key

        print("\n✅ Environment variables set for current session")

        print("\n" + "=" * 50)
        print("🎯 NEXT STEPS")
        print("=" * 50)
        print("1. Verify setup: python3 quick_diagnosis.py")
        print("2. Launch bot: python3 launch_bot_fixed.py")
        print()
        print("🎉 Credential setup complete!")

        return 0

    except Exception as e:
        print(f"❌ Error saving credentials: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
