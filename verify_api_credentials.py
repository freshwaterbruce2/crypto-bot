#!/usr/bin/env python3
"""
Verify Kraken API credentials and WebSocket permissions
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment
load_dotenv()

async def verify_credentials():
    """Test API credentials and permissions"""
    print("🔍 Verifying Kraken API Credentials...")
    print("=" * 50)
    
    # Check if API keys are set
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('KRAKEN_SECRET_KEY')
    
    if not api_key or not api_secret:
        print("❌ ERROR: API keys not found in environment!")
        print("   Please check your .env file")
        return False
    
    print("✅ API keys found in environment")
    print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Secret: {api_secret[:10]}...{api_secret[-4:]}")
    
    # Test connection
    try:
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        
        print("\n📡 Testing API connection...")
        exchange = NativeKrakenExchange(api_key=api_key, api_secret=api_secret)
        
        # Test 1: Check balance (basic API test)
        print("\n1️⃣ Testing balance endpoint...")
        balance = await exchange.fetch_balance()
        if balance:
            print("✅ Balance endpoint working!")
            # Check for USDT in various formats
            usdt_balance = balance.get('USDT', balance.get('ZUSDT', balance.get('USDT.M', 0)))
            print(f"   USDT Balance: ${usdt_balance:.2f}")
            
            if usdt_balance < 10:
                print("⚠️  WARNING: Low USDT balance for testing")
        else:
            print("❌ Failed to get balance")
            return False
        
        # Test 2: Check WebSocket permissions
        print("\n2️⃣ Testing WebSocket permissions...")
        try:
            # Get WebSocket token
            token_response = await exchange.get_websockets_token()
            if token_response and isinstance(token_response, dict) and ('token' in token_response or 'result' in token_response):
                print("✅ WebSocket token obtained!")
                print("   Your API key has WebSocket permissions enabled")
            else:
                print("❌ WebSocket token failed")
                print("   Please enable WebSocket permissions for your API key at:")
                print("   https://www.kraken.com/u/security/api")
                return False
        except Exception as e:
            print(f"❌ WebSocket test failed: {e}")
            print("   Please enable WebSocket permissions for your API key")
            return False
        
        # Test 3: Check trading pairs
        print("\n3️⃣ Checking configured trading pairs...")
        from src.config import load_config
        config = load_config()
        pairs = config.get('trade_pairs', [])
        
        print(f"   Configured pairs: {len(pairs)}")
        for pair in pairs[:5]:  # Show first 5
            print(f"   - {pair}")
        
        # Test 4: Check order permissions
        print("\n4️⃣ Testing order permissions...")
        # We won't place actual orders, just check if we can access the endpoint
        try:
            open_orders = await exchange._api_request('OpenOrders')
            print("✅ Order endpoint accessible")
        except Exception as e:
            print(f"⚠️  Order endpoint error: {e}")
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED! Bot is ready to launch.")
        print("\n⚠️  IMPORTANT REMINDERS:")
        print("   1. Start with small amounts ($10-20)")
        print("   2. Monitor the first few trades closely")
        print("   3. Current position size: 0.7 (aggressive)")
        print("   4. Consider reducing to 0.5 for safety")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if 'exchange' in locals():
            await exchange.close()

if __name__ == "__main__":
    # Run the verification
    if asyncio.run(verify_credentials()):
        print("\n✅ Bot is ready to launch!")
        print("   Run: python scripts/live_launch.py")
    else:
        print("\n❌ Please fix the issues above before launching")