#!/usr/bin/env python3
"""Setup .env file for Kraken trading bot."""
import os
from pathlib import Path

def setup_env():
    """Setup .env file with proper structure."""
    env_path = Path(".env")
    template_path = Path(".env.template")
    
    if not env_path.exists():
        print("❌ No .env file found!")
        if template_path.exists():
            print("   Creating .env from template...")
            env_path.write_text(template_path.read_text())
            print("✅ .env file created from template")
        else:
            print("   Creating new .env file...")
            env_content = """# KRAKEN API CREDENTIALS
KRAKEN_API_KEY=your_kraken_api_key_here
KRAKEN_SECRET=your_kraken_secret_key_here

# TRADING CONFIGURATION
DEFAULT_EXCHANGE=kraken
DEFAULT_MARKET_TYPE=spot
LOG_LEVEL=INFO
"""
            env_path.write_text(env_content)
            print("✅ .env file created")
    
    # Check if credentials are configured
    env_content = env_path.read_text()
    if "your_kraken_api_key_here" in env_content:
        print("\n⚠️  IMPORTANT: You need to add your Kraken API credentials!")
        print("   1. Go to https://www.kraken.com/u/security/api")
        print("   2. Create a new API key with these permissions:")
        print("      - Query Funds")
        print("      - Query Open Orders & Trades")
        print("      - Query Closed Orders & Trades")
        print("      - Create & Modify Orders")
        print("      - Cancel/Close Orders")
        print("      - Access WebSockets API")
        print("   3. Edit .env file and replace:")
        print("      - your_kraken_api_key_here → Your actual API key")
        print("      - your_kraken_secret_key_here → Your actual API secret")
    else:
        print("\n✅ API credentials appear to be configured")
        print("   Run the bot to test the connection")

if __name__ == "__main__":
    setup_env()