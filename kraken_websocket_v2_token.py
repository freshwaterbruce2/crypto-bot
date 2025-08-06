#!/usr/bin/env python3
"""
Kraken WebSocket V2 Token Retrieval
Correct implementation for getting WebSocket token from REST API
Based on official Kraken documentation
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
from typing import Optional

import requests


def get_kraken_signature(urlpath: str, data: dict, secret: str) -> str:
    """
    Generate Kraken API signature

    Args:
        urlpath: API endpoint path (e.g., '/0/private/GetWebSocketsToken')
        data: POST data including nonce
        secret: Base64 encoded API secret

    Returns:
        Base64 encoded signature
    """
    # Encode POST data
    postdata = urllib.parse.urlencode(data)

    # Create the message: nonce + postdata
    encoded = (str(data['nonce']) + postdata).encode()

    # Hash the message
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    # Create signature
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())

    return sigdigest.decode()

def get_websocket_token() -> Optional[str]:
    """
    Get WebSocket authentication token from Kraken REST API

    Returns:
        WebSocket token string or None if failed
    """

    # Get credentials from environment
    api_key = os.getenv('KRAKEN_KEY') or os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_SECRET') or os.getenv('KRAKEN_API_SECRET')

    if not api_key or not api_secret:
        print("❌ No API credentials found in environment variables")
        return None

    print(f"🔑 Using API Key: {api_key[:8]}...{api_key[-4:]}")

    # Kraken REST API configuration
    api_url = "https://api.kraken.com"
    api_path = "/0/private/GetWebSocketsToken"

    # Generate nonce (milliseconds as per Kraken requirement)
    nonce = str(int(time.time() * 1000))

    # Prepare POST data (only nonce required for GetWebSocketsToken)
    data = {
        "nonce": nonce
    }

    # Generate API signature
    try:
        signature = get_kraken_signature(api_path, data, api_secret)
    except Exception as e:
        print(f"❌ Failed to generate signature: {e}")
        print("   Check if your API secret is valid base64")
        return None

    # Prepare headers
    headers = {
        'API-Key': api_key,
        'API-Sign': signature,
        'User-Agent': 'Kraken-WebSocket-V2-Client/1.0'
    }

    # Make the request
    print(f"📡 Requesting WebSocket token from: {api_url}{api_path}")

    try:
        response = requests.post(
            api_url + api_path,
            headers=headers,
            data=data,
            timeout=10
        )

        # Parse response
        result = response.json()

        # Check for errors
        if 'error' in result and result['error']:
            error_msg = result['error'][0] if isinstance(result['error'], list) else str(result['error'])
            print(f"❌ Kraken API Error: {error_msg}")

            # Provide specific guidance
            if 'Invalid key' in error_msg:
                print("\n📋 Fix: Your API key is not recognized by Kraken")
                print("   • Verify the key is copied correctly")
                print("   • Check if the key hasn't been deleted")
            elif 'Permission denied' in error_msg or 'EGeneral:Permission denied' in error_msg:
                print("\n📋 Fix: Your API key lacks WebSocket permission")
                print("   1. Go to: https://www.kraken.com/u/security/api")
                print("   2. Edit your API key")
                print("   3. Enable: 'WebSocket interface - On' or 'Access WebSockets API'")
                print("   4. Save and wait 5 minutes")
            elif 'Invalid nonce' in error_msg:
                print("\n📋 Fix: Nonce issue - try again")

            return None

        # Extract token from successful response
        if 'result' in result and 'token' in result['result']:
            token = result['result']['token']
            print("✅ WebSocket token obtained successfully!")
            print(f"   Token: {token[:20]}...{token[-10:]}")
            print("   Valid for: 15 minutes (for initial connection)")
            return token
        else:
            print(f"❌ Unexpected response format: {result}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        print("   • Check your internet connection")
        print("   • Verify api.kraken.com is accessible")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def connect_websocket_v2(token: str) -> bool:
    """
    Test WebSocket V2 connection with the token

    Args:
        token: WebSocket authentication token from REST API

    Returns:
        True if connection successful
    """
    import asyncio

    import websockets

    async def test_connection():
        # WebSocket V2 authenticated endpoint
        ws_url = "wss://ws-auth.kraken.com/v2"

        print("\n🔌 Connecting to WebSocket V2...")
        print(f"   URL: {ws_url}")

        try:
            async with websockets.connect(ws_url) as ws:
                print("✅ WebSocket V2 connected!")

                # Subscribe to private channel with token
                subscribe_msg = {
                    "method": "subscribe",
                    "params": {
                        "channel": "balances",
                        "token": token,
                        "snapshot": True
                    }
                }

                await ws.send(json.dumps(subscribe_msg))
                print("📤 Sent balance subscription with token")

                # Wait for response
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)

                if data.get('method') == 'subscribe':
                    if data.get('success'):
                        print("✅ Successfully subscribed to private channel!")
                        print("🎉 WebSocket V2 authentication complete!")
                        return True
                    else:
                        error = data.get('error', 'Unknown error')
                        print(f"❌ Subscription failed: {error}")
                        return False

                # Check for balance data
                if data.get('channel') == 'balances':
                    print("✅ Receiving balance data!")
                    print(f"   Data: {json.dumps(data.get('data', {}), indent=2)[:200]}...")
                    return True

                print(f"📥 Received: {data}")
                return True

        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False

    # Run async function
    return asyncio.run(test_connection())

def main():
    """Main function to test complete flow"""

    print("="*60)
    print("KRAKEN WEBSOCKET V2 TOKEN AUTHENTICATION")
    print("="*60)
    print("Following official Kraken API documentation")
    print("Endpoint: /0/private/GetWebSocketsToken")
    print("="*60)

    # Step 1: Get token from REST API
    print("\n📋 Step 1: Get WebSocket Token from REST API")
    print("-"*40)

    token = get_websocket_token()

    if not token:
        print("\n❌ Failed to obtain WebSocket token")
        print("\n💡 Common Solutions:")
        print("1. Enable 'WebSocket interface' permission on your API key")
        print("2. For Kraken Pro: Create API key on main Kraken site (not Pro)")
        print("3. Wait 5-10 minutes after enabling permissions")
        return False

    # Step 2: Connect to WebSocket V2 with token
    print("\n📋 Step 2: Connect to WebSocket V2 with Token")
    print("-"*40)

    success = connect_websocket_v2(token)

    if success:
        print("\n✅ SUCCESS: WebSocket V2 Authentication Working!")
        print("🚀 Your bot can now use private WebSocket feeds")
        return True
    else:
        print("\n❌ WebSocket V2 connection failed")
        print("Token was valid but connection failed")
        return False

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)
