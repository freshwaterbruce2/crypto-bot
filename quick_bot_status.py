#!/usr/bin/env python3
"""
Quick Bot Status Check
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent / 'src'))

async def check_bot_status():
    """Check what's working in the bot"""

    print("="*50)
    print("QUICK BOT STATUS CHECK")
    print("="*50)

    # Check credentials
    api_key = os.getenv('KRAKEN_KEY') or os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_SECRET') or os.getenv('KRAKEN_API_SECRET')

    print(f"✅ Credentials found: {bool(api_key and api_secret)}")

    # Test REST client
    try:
        from src.api.simple_kraken_rest import SimpleKrakenREST

        async with SimpleKrakenREST() as client:
            print("✅ REST client created")

            balance = await client.get_account_balance()
            print(f"✅ Balance query successful: {len(balance)} assets")

            # Show some balances
            for asset, amount in list(balance.items())[:3]:
                if float(amount) > 0:
                    print(f"   {asset}: {amount}")

    except Exception as e:
        print(f"❌ REST client error: {e}")

    # Test WebSocket token
    try:
        from src.exchange.websocket_manager_v2 import WebSocketManagerV2

        ws_manager = WebSocketManagerV2()
        token = await ws_manager.get_websocket_token()

        if token:
            print(f"✅ WebSocket token obtained: {len(token)} chars")
        else:
            print("❌ WebSocket token failed")

    except Exception as e:
        print(f"❌ WebSocket test error: {e}")

    print("\n" + "="*50)
    print("BOT STATUS SUMMARY")
    print("="*50)
    print("The bot should now be working! Try:")
    print("1. python main.py → option 2")
    print("2. Let it initialize completely")
    print("3. Check for live trading activity")

if __name__ == "__main__":
    asyncio.run(check_bot_status())
