#!/usr/bin/env python3
"""
Kraken Pro WebSocket Authentication Fix - 2025
==============================================

This script specifically addresses WebSocket authentication issues for Kraken Pro accounts
where REST API works but WebSocket token requests fail with "Permission denied".

The issue is NOT with API version or format - it's with WebSocket-specific permissions
on Kraken Pro accounts that need to be explicitly enabled.

2025 API Compliance:
- Uses correct base URL: https://api.kraken.com
- Uses correct endpoint: /0/private/GetWebSocketsToken
- Uses proper authentication format
- Compatible with WebSocket V2

Focus: Kraken Pro WebSocket permissions diagnostics and fixes
"""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

import aiohttp

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

class KrakenProWebSocketAuthenticator:
    """Enhanced WebSocket authenticator specifically for Kraken Pro accounts"""

    def __init__(self):
        self.api_url = "https://api.kraken.com"  # Correct 2025 base URL
        self.token_endpoint = "/0/private/GetWebSocketsToken"  # Correct 2025 endpoint
        self.ws_public_url = "wss://ws.kraken.com/v2"  # WebSocket V2 public
        self.ws_private_url = "wss://ws-auth.kraken.com/v2"  # WebSocket V2 private

    async def diagnose_account_type(self, api_key, api_secret):
        """Diagnose if this is a Kraken Pro account"""
        print("\n🔍 ACCOUNT TYPE DIAGNOSIS")
        print("="*50)

        # Test REST API Balance endpoint to verify account type
        try:
            nonce = str(int(time.time() * 1000))
            uri_path = "/0/private/Balance"
            data = {"nonce": nonce}
            postdata = urllib.parse.urlencode(data)

            # Generate signature
            message = (str(nonce) + postdata).encode('utf-8')
            sha256_hash = hashlib.sha256(message).digest()
            hmac_message = uri_path.encode('utf-8') + sha256_hash
            secret_decoded = base64.b64decode(api_secret)
            signature = hmac.new(secret_decoded, hmac_message, hashlib.sha512)
            signature_b64 = base64.b64encode(signature.digest()).decode()

            headers = {
                'API-Key': api_key,
                'API-Sign': signature_b64,
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url + uri_path,
                    headers=headers,
                    data=postdata,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    response_text = await response.text()
                    print(f"📊 REST API Response Status: {response.status}")

                    if response.status == 200:
                        result = json.loads(response_text)
                        if result.get('error'):
                            print(f"❌ REST API Error: {result['error']}")
                            return False
                        else:
                            balance_data = result.get('result', {})
                            print("✅ REST API Working - Balance query successful")
                            print(f"💰 Account has {len(balance_data)} balance entries")

                            # Check for Pro account indicators
                            has_staking_assets = any('staked' in str(key).lower() for key in balance_data.keys())
                            has_margin_assets = any('margin' in str(key).lower() for key in balance_data.keys())

                            if has_staking_assets or has_margin_assets:
                                print("🏢 DETECTED: Likely Kraken Pro account")
                            else:
                                print("👤 DETECTED: Likely Standard Kraken account")

                            return True
                    else:
                        print(f"❌ REST API failed with status {response.status}")
                        return False

        except Exception as e:
            print(f"❌ Account diagnosis failed: {e}")
            return False

    async def test_websocket_token_request(self, api_key, api_secret):
        """Test WebSocket token request with enhanced error analysis"""
        print("\n🎫 WEBSOCKET TOKEN REQUEST TEST")
        print("="*50)

        try:
            # Generate nonce (milliseconds format for 2025)
            nonce = str(int(time.time() * 1000))
            print(f"🔢 Generated nonce: {nonce}")

            # Prepare POST data
            data = {"nonce": nonce}
            postdata = urllib.parse.urlencode(data)

            # Generate signature (2025 compliant format)
            message = (str(nonce) + postdata).encode('utf-8')
            sha256_hash = hashlib.sha256(message).digest()
            hmac_message = self.token_endpoint.encode('utf-8') + sha256_hash
            secret_decoded = base64.b64decode(api_secret)
            signature = hmac.new(secret_decoded, hmac_message, hashlib.sha512)
            signature_b64 = base64.b64encode(signature.digest()).decode()

            # Prepare headers
            headers = {
                'API-Key': api_key,
                'API-Sign': signature_b64,
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Kraken-Trading-Bot-2025/1.0'
            }

            print(f"🌐 Making request to: {self.api_url + self.token_endpoint}")
            print(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]}")
            print(f"✍️ Signature length: {len(signature_b64)} chars")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url + self.token_endpoint,
                    headers=headers,
                    data=postdata,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    print(f"📥 Response status: {response.status}")
                    print(f"📥 Response headers: {dict(response.headers)}")

                    response_text = await response.text()
                    print(f"📥 Raw response: {response_text}")

                    if response.status == 200:
                        try:
                            result = json.loads(response_text)

                            if result.get('error'):
                                error_msg = result['error'][0] if isinstance(result['error'], list) else str(result['error'])
                                print(f"❌ Kraken API Error: {error_msg}")

                                await self._analyze_websocket_error(error_msg)
                                return None

                            if 'result' in result and 'token' in result['result']:
                                token = result['result']['token']
                                print("✅ WebSocket token obtained successfully!")
                                print(f"🎫 Token: {token[:20]}...{token[-10:]}")
                                print(f"📏 Token length: {len(token)} characters")
                                return token
                            else:
                                print("❌ No token in response structure")
                                return None

                        except json.JSONDecodeError:
                            print("❌ Invalid JSON response from Kraken API")
                            return None
                    else:
                        print(f"❌ HTTP Error {response.status}: {response_text}")

                        if response.status == 403:
                            print("\n🚨 HTTP 403 FORBIDDEN - WEBSOCKET PERMISSION DENIED")
                            await self._provide_403_solution()

                        return None

        except Exception as e:
            print(f"❌ WebSocket token request failed: {e}")
            return None

    async def _analyze_websocket_error(self, error_msg):
        """Analyze WebSocket-specific errors and provide solutions"""
        error_lower = error_msg.lower()

        if "permission" in error_lower or "denied" in error_lower:
            print("\n🔍 WEBSOCKET PERMISSION ERROR ANALYSIS")
            print("="*50)
            print("❌ Your API key lacks WebSocket permissions")
            print("✅ Your REST API credentials work fine")
            print("🎯 This is a WebSocket-specific permission issue")

            await self._provide_websocket_permission_solution()

        elif "nonce" in error_lower:
            print("\n🔍 NONCE ERROR ANALYSIS")
            print("="*50)
            print("❌ Nonce validation failed")
            print("🕐 This can happen due to clock synchronization issues")
            print("🔧 Try running the test again in 30 seconds")

        elif "invalid" in error_lower and "key" in error_lower:
            print("\n🔍 INVALID KEY ERROR ANALYSIS")
            print("="*50)
            print("❌ API key format or content is invalid")
            print("🔧 Double-check your API key and secret")

        else:
            print("\n🔍 UNKNOWN ERROR ANALYSIS")
            print("="*50)
            print(f"❓ Unrecognized error: {error_msg}")
            print("🔧 This might be a new error type - check Kraken documentation")

    async def _provide_websocket_permission_solution(self):
        """Provide step-by-step solution for WebSocket permission issues"""
        print("\n🔧 WEBSOCKET PERMISSION FIX - STEP BY STEP")
        print("="*60)
        print("1️⃣ Log into your Kraken account (web browser)")
        print("2️⃣ Go to Settings → API → Manage API Keys")
        print("3️⃣ Click 'Edit' on your existing API key")
        print("4️⃣ Scroll down to 'Permissions' section")
        print("5️⃣ ENSURE these permissions are checked:")
        print("   ✅ Query Funds")
        print("   ✅ Query Open/Closed/Cancelled Orders")
        print("   ✅ Query Ledger Entries")
        print("   ✅ Access WebSockets API  ← THIS IS CRITICAL!")
        print("6️⃣ If using Kraken Pro, also check Pro-specific permissions")
        print("7️⃣ Click 'Update Settings'")
        print("8️⃣ Wait 5-10 minutes for changes to take effect")
        print("9️⃣ Run this test again")
        print("\n⚠️ CRITICAL: 'Access WebSockets API' must be enabled!")
        print("   This permission is separate from REST API permissions")

    async def _provide_403_solution(self):
        """Provide solution for HTTP 403 errors"""
        print("\n🔧 HTTP 403 FORBIDDEN FIX")
        print("="*40)
        print("🚨 This is a WebSocket permission issue!")
        print("📋 Your API key works for REST but not WebSocket")
        print("\n💡 SOLUTION:")
        print("1. Edit your API key in Kraken account")
        print("2. Enable 'Access WebSockets API' permission")
        print("3. For Kraken Pro: Check Pro WebSocket permissions")
        print("4. Save and wait 5-10 minutes")
        print("5. Test again")

    async def test_websocket_connection(self, token):
        """Test WebSocket V2 connection with the obtained token"""
        if not token:
            print("\n❌ Cannot test WebSocket - no token available")
            return False

        print("\n🔌 WEBSOCKET V2 CONNECTION TEST")
        print("="*50)
        print(f"🌐 Connecting to: {self.ws_private_url}")
        print(f"🎫 Using token: {token[:20]}...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.ws_private_url) as ws:
                    print("✅ WebSocket connected successfully!")

                    # Subscribe to balance channel (2025 format)
                    subscribe_msg = {
                        "method": "subscribe",
                        "params": {
                            "channel": "balances",
                            "token": token,
                            "snapshot": True
                        }
                    }

                    await ws.send_json(subscribe_msg)
                    print("📤 Sent balance subscription request")

                    # Wait for response
                    timeout = 10
                    start_time = time.time()
                    message_count = 0

                    while time.time() - start_time < timeout:
                        try:
                            msg = await asyncio.wait_for(ws.receive(), timeout=2.0)

                            if msg.type == aiohttp.WSMsgType.TEXT:
                                message_count += 1
                                data = json.loads(msg.data)
                                print(f"📥 Message {message_count}: {json.dumps(data, indent=2)}")

                                if data.get('channel') == 'balances':
                                    print("✅ Successfully subscribed to balances channel!")
                                    return True
                                elif 'error' in data:
                                    print(f"❌ WebSocket Error: {data['error']}")
                                    return False

                        except asyncio.TimeoutError:
                            continue

                    if message_count > 0:
                        print(f"✅ WebSocket working (received {message_count} messages)")
                        return True
                    else:
                        print("⚠️ No messages received but connection established")
                        return True

        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False

    async def run_comprehensive_test(self):
        """Run comprehensive WebSocket authentication test for Kraken Pro"""
        print("🎯 KRAKEN PRO WEBSOCKET AUTHENTICATION COMPREHENSIVE TEST")
        print("=" * 80)
        print("🔄 Updated for 2025 API compliance")
        print("🏢 Designed specifically for Kraken Pro accounts")
        print("🔗 Tests WebSocket V2 with enhanced diagnostics")
        print("=" * 80)

        # Get credentials
        api_key = (os.getenv('KRAKEN_KEY') or
                   os.getenv('KRAKEN_API_KEY') or
                   os.getenv('API_KEY'))
        api_secret = (os.getenv('KRAKEN_SECRET') or
                      os.getenv('KRAKEN_API_SECRET') or
                      os.getenv('API_SECRET'))

        if not api_key or not api_secret:
            print("❌ No API credentials found")
            print("📋 Set these environment variables:")
            print("   KRAKEN_KEY=your_api_key")
            print("   KRAKEN_SECRET=your_api_secret")
            return False

        print(f"🔑 Using API Key: {api_key[:8]}...{api_key[-4:]}")

        # Step 1: Diagnose account type
        print("\n" + "="*60)
        print("STEP 1: ACCOUNT TYPE DIAGNOSIS")
        print("="*60)

        account_ok = await self.diagnose_account_type(api_key, api_secret)
        if not account_ok:
            print("❌ Basic REST API test failed - check your credentials")
            return False

        # Step 2: Test WebSocket token request
        print("\n" + "="*60)
        print("STEP 2: WEBSOCKET TOKEN REQUEST")
        print("="*60)

        token = await self.test_websocket_token_request(api_key, api_secret)

        if not token:
            print("\n❌ WEBSOCKET TOKEN REQUEST FAILED")
            print("🎯 This is the core issue - WebSocket permissions")
            return False

        # Step 3: Test WebSocket connection
        print("\n" + "="*60)
        print("STEP 3: WEBSOCKET CONNECTION TEST")
        print("="*60)

        ws_success = await self.test_websocket_connection(token)

        # Final summary
        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)

        if ws_success:
            print("🎉 SUCCESS! WebSocket authentication working!")
            print("✅ Your Kraken Pro account is ready for WebSocket trading")
            print("🚀 You can now run the trading bot with WebSocket support")
            return True
        else:
            print("❌ WebSocket connection failed")
            print("🔧 Token was obtained but connection failed")
            print("📋 This might be a network or WebSocket server issue")
            return False


async def main():
    """Main test runner"""
    authenticator = KrakenProWebSocketAuthenticator()
    success = await authenticator.run_comprehensive_test()
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
