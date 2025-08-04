#!/usr/bin/env python3
"""
Kraken Account Status and API Key Verification Check
"""

import asyncio
import os
import time
import hashlib
import hmac
import base64
import urllib.parse
import sys
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

# Load .env
load_dotenv()

async def check_account_status():
    """Check account status and API key functionality"""
    print("🔍 KRAKEN ACCOUNT & API KEY STATUS CHECK")
    print("=" * 60)
    
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ API credentials not found")
        return False
    
    print(f"✓ API Key: [SECURE - {len(api_key)} chars]")
    print(f"✅ Key Length: {len(api_key)} chars")
    print(f"✅ Secret Length: {len(api_secret)} chars")
    
    def create_signature(api_secret, urlpath, nonce, data):
        """Create Kraken API signature"""
        message = urlpath.encode() + hashlib.sha256((nonce + data).encode()).digest()
        signature = base64.b64encode(
            hmac.new(base64.b64decode(api_secret), message, hashlib.sha512).digest()
        ).decode()
        return signature
    
    # Test 1: Check server time first
    print(f"\n📊 TEST 1: SERVER TIME SYNC")
    print("-" * 30)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.kraken.com/0/public/Time") as response:
                result = await response.json()
                if 'result' in result:
                    server_time = result['result']['unixtime']
                    local_time = int(time.time())
                    time_diff = abs(server_time - local_time)
                    
                    print(f"✅ Server time: {server_time} ({time.ctime(server_time)})")
                    print(f"✅ Local time:  {local_time} ({time.ctime(local_time)})")
                    print(f"✅ Time diff:   {time_diff} seconds")
                    
                    if time_diff > 30:
                        print(f"⚠️  WARNING: Time difference > 30 seconds!")
                    else:
                        print(f"✅ Time synchronization OK")
                else:
                    print(f"❌ Failed to get server time")
    except Exception as e:
        print(f"❌ Server time check failed: {e}")
    
    # Test 2: Try different nonce strategies
    print(f"\n🔄 TEST 2: NONCE STRATEGY TESTING")
    print("-" * 30)
    
    nonce_strategies = [
        ("Current Timestamp (ms)", lambda: str(int(time.time() * 1000))),
        ("Large Timestamp (us)", lambda: str(int(time.time() * 1000000))),
        ("Future Timestamp (+5min)", lambda: str(int((time.time() + 300) * 1000))),
        ("Simple Counter", lambda: str(int(time.time() * 1000) + 999999)),
    ]
    
    for strategy_name, nonce_func in nonce_strategies:
        print(f"\n  Testing: {strategy_name}")
        
        nonce = nonce_func()
        endpoint = "Balance"
        urlpath = f"/0/private/{endpoint}"
        params = {'nonce': nonce}
        data = urllib.parse.urlencode(params)
        
        signature = create_signature(api_secret, urlpath, nonce, data)
        
        headers = {
            'API-Key': api_key,
            'API-Sign': signature,
            'User-Agent': 'KrakenAccountCheck/1.0'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"https://api.kraken.com{urlpath}", 
                                      data=params, headers=headers) as response:
                    result = await response.json()
                    
                    print(f"    Nonce: {nonce}")
                    print(f"    Status: {response.status}")
                    
                    if result.get('error'):
                        error_msg = result['error'][0] if result['error'] else "Unknown"
                        print(f"    ❌ Error: {error_msg}")
                        
                        if 'Invalid nonce' in error_msg:
                            print(f"    🔍 Nonce issue detected")
                        elif 'Invalid key' in error_msg:
                            print(f"    🔍 API key issue detected")
                        elif 'Permission denied' in error_msg:
                            print(f"    🔍 Permission issue detected")
                        elif 'Invalid signature' in error_msg:
                            print(f"    🔍 Signature issue detected")
                        else:
                            print(f"    🔍 Other error type")
                    else:
                        print(f"    ✅ SUCCESS!")
                        balance_data = result.get('result', {})
                        print(f"    📊 Balance keys: {len(balance_data)}")
                        return True
                        
        except Exception as e:
            print(f"    ❌ Request failed: {e}")
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Test 3: Check account info endpoint
    print(f"\n👤 TEST 3: ACCOUNT INFO CHECK")
    print("-" * 30)
    
    try:
        nonce = str(int(time.time() * 1000000))  # Use microseconds
        endpoint = "TradeBalance"
        urlpath = f"/0/private/{endpoint}"
        params = {'nonce': nonce}
        data = urllib.parse.urlencode(params)
        
        signature = create_signature(api_secret, urlpath, nonce, data)
        
        headers = {
            'API-Key': api_key,
            'API-Sign': signature,
            'User-Agent': 'KrakenAccountCheck/1.0'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"https://api.kraken.com{urlpath}", 
                                  data=params, headers=headers) as response:
                result = await response.json()
                
                if result.get('error'):
                    error_msg = result['error'][0] if result['error'] else "Unknown"
                    print(f"❌ TradeBalance failed: {error_msg}")
                else:
                    print(f"✅ TradeBalance succeeded!")
                    trade_balance = result.get('result', {})
                    if 'eb' in trade_balance:
                        print(f"💰 Equivalent balance: ${float(trade_balance['eb']):.2f}")
                    return True
                    
    except Exception as e:
        print(f"❌ Account info check failed: {e}")
    
    # Summary
    print(f"\n📋 DIAGNOSIS SUMMARY")
    print("=" * 60)
    print(f"❌ All API calls failed with nonce errors")
    print(f"")
    print(f"🔍 POSSIBLE CAUSES:")
    print(f"   1. API key needs activation time (try again in 15-30 minutes)")
    print(f"   2. Account has API restrictions enabled")
    print(f"   3. IP address is not whitelisted (if IP restrictions enabled)")
    print(f"   4. API key permissions insufficient despite settings")
    print(f"   5. Account verification level insufficient for API access")
    print(f"")
    print(f"💡 RECOMMENDED ACTIONS:")
    print(f"   1. Wait 30 minutes and try again (new keys need time)")
    print(f"   2. Check account verification status in Kraken Pro")
    print(f"   3. Verify no IP restrictions are enabled")
    print(f"   4. Contact Kraken support if issue persists")
    print(f"   5. Try creating API key from different browser/session")
    
    return False

async def main():
    """Main function"""
    try:
        success = await check_account_status()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)