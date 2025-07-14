#!/usr/bin/env python3
"""
Quick Kraken API test - Direct API call
"""

import os
import time
import hmac
import base64
import hashlib
import urllib.parse
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_kraken_api():
    """Direct API test without exchange wrapper"""
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('KRAKEN_SECRET_KEY')
    
    if not api_key or not api_secret:
        print("❌ API keys not found!")
        return
    
    print("🔍 Testing Kraken API directly...")
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    
    # Test 1: Public endpoint (no auth needed)
    print("\n1️⃣ Testing public endpoint (Ticker)...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.kraken.com/0/public/Ticker",
                params={"pair": "XBTUSD"}
            )
            if response.status_code == 200:
                print("✅ Public API working!")
            else:
                print(f"❌ Public API error: {response.status_code}")
        except Exception as e:
            print(f"❌ Connection error: {e}")
    
    # Test 2: Private endpoint (Balance)
    print("\n2️⃣ Testing private endpoint (Balance)...")
    
    # Prepare the request
    urlpath = '/0/private/Balance'
    nonce = str(int(time.time() * 1000))
    data = {
        'nonce': nonce
    }
    
    # Create signature
    postdata = urllib.parse.urlencode(data)
    encoded = (str(nonce) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(api_secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(signature.digest()).decode()
    
    headers = {
        'API-Key': api_key,
        'API-Sign': sigdigest,
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.kraken.com{urlpath}",
                data=postdata,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('error'):
                    print(f"❌ API Error: {result['error']}")
                else:
                    print("✅ Private API working!")
                    balances = result.get('result', {})
                    
                    # Look for USDT balance
                    usdt_keys = ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S']
                    for key in usdt_keys:
                        if key in balances:
                            balance = float(balances[key])
                            print(f"   {key} Balance: ${balance:.2f}")
                            break
                    else:
                        print("   No USDT balance found")
                        print(f"   Available assets: {list(balances.keys())[:5]}...")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Connection error: {e}")
    
    # Test 3: WebSocket token
    print("\n3️⃣ Testing WebSocket token endpoint...")
    urlpath = '/0/private/GetWebSocketsToken'
    nonce = str(int(time.time() * 1000))
    data = {'nonce': nonce}
    
    postdata = urllib.parse.urlencode(data)
    encoded = (str(nonce) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(api_secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(signature.digest()).decode()
    
    headers = {
        'API-Key': api_key,
        'API-Sign': sigdigest,
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.kraken.com{urlpath}",
                data=postdata,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('error'):
                    errors = result['error']
                    if 'EAPI:Feature disabled' in str(errors):
                        print("❌ WebSocket NOT enabled for this API key!")
                        print("   Please enable at: https://www.kraken.com/u/security/api")
                    else:
                        print(f"❌ API Error: {errors}")
                else:
                    print("✅ WebSocket token obtained!")
                    print("   WebSocket permissions are enabled")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Connection error: {e}")
    
    print("\n" + "="*50)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_kraken_api())