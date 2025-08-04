#!/usr/bin/env python3
"""
Credential Setup Script
======================

Interactive script to help users set up their Kraken API credentials safely.
"""

import os
import getpass
from pathlib import Path

def validate_api_key(api_key):
    """Basic validation of API key format"""
    if not api_key:
        return False, "API key is empty"
    
    if len(api_key) < 20:
        return False, "API key appears too short"
    
    if not api_key.isalnum():
        return False, "API key should contain only alphanumeric characters"
    
    return True, "Valid format"

def validate_private_key(private_key):
    """Basic validation of private key format"""
    if not private_key:
        return False, "Private key is empty"
    
    if len(private_key) < 50:
        return False, "Private key appears too short"
    
    # Check for base64-like characters
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
    if not all(c in valid_chars for c in private_key):
        return False, "Private key should be base64 encoded"
    
    return True, "Valid format"

def create_env_file(api_key, private_key):
    """Create .env file with credentials"""
    env_content = f"""# Kraken API Credentials for Trading Bot
# Generated on {os.path.basename(__file__)}

KRAKEN_API_KEY={api_key}
KRAKEN_PRIVATE_KEY={private_key}

# Optional: Set to true for paper trading mode
# PAPER_TRADING=false

# Optional: Set log level
# LOG_LEVEL=INFO
"""
    
    env_file = Path('.env')
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    # Set restrictive permissions (Linux/Mac)
    try:
        os.chmod(env_file, 0o600)
    except:
        pass  # Windows doesn't support chmod
    
    return env_file

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