#!/usr/bin/env python3
"""
Simple Kraken API test using requests
"""

import os
import time
import hmac
import base64
import hashlib
import urllib.parse
import requests
from dotenv import load_dotenv

load_dotenv()

def test_kraken_api():
    """Direct API test"""
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('KRAKEN_SECRET_KEY')
    
    print("🔍 Kraken API Verification")
    print("="*50)
    
    if not api_key or not api_secret:
        print("❌ API keys not found!")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Test 1: Public endpoint
    print("\n1️⃣ Testing public API...")
    try:
        response = requests.get(
            "https://api.kraken.com/0/public/SystemStatus"
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('error') == []:
                status = data.get('result', {}).get('status', 'unknown')
                print(f"✅ Kraken system status: {status}")
            else:
                print(f"❌ API error: {data.get('error')}")
        else:
            print(f"❌ HTTP error: {response.status_code}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    # Test 2: Private endpoint (Balance)
    print("\n2️⃣ Testing private API (Balance)...")
    urlpath = '/0/private/Balance'
    nonce = str(int(time.time() * 1000))
    data = {'nonce': nonce}
    
    postdata = urllib.parse.urlencode(data)
    encoded = (str(nonce) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(api_secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(signature.digest()).decode()
    
    headers = {
        'API-Key': api_key,
        'API-Sign': sigdigest
    }
    
    try:
        response = requests.post(
            f"https://api.kraken.com{urlpath}",
            data=data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('error'):
                print(f"❌ API Error: {result['error']}")
                return False
            else:
                print("✅ Balance API working!")
                balances = result.get('result', {})
                
                # Look for USDT
                found_usdt = False
                for key, value in balances.items():
                    if 'USDT' in key or key in ['ZUSDT', 'USDT.M']:
                        balance = float(value)
                        print(f"   {key}: ${balance:.2f}")
                        found_usdt = True
                
                if not found_usdt:
                    print("   No USDT balance found")
                    if balances:
                        print(f"   Other assets: {list(balances.keys())[:3]}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 3: WebSocket token
    print("\n3️⃣ Testing WebSocket permissions...")
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
        'API-Sign': sigdigest
    }
    
    try:
        response = requests.post(
            f"https://api.kraken.com{urlpath}",
            data=data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('error'):
                errors = result['error']
                if any('Feature disabled' in str(e) for e in errors):
                    print("❌ WebSocket NOT enabled!")
                    print("   Enable at: https://www.kraken.com/u/security/api")
                    print("   Settings → API → Edit → WebSocket → Enable")
                    return False
                else:
                    print(f"❌ Error: {errors}")
                    return False
            else:
                print("✅ WebSocket permissions enabled!")
                token = result.get('result', {}).get('token', '')
                if token:
                    print(f"   Token obtained: {token[:20]}...")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("\n🚀 Kraken Trading Bot - API Verification\n")
    
    if test_kraken_api():
        print("\n✅ ALL TESTS PASSED!")
        print("\n📋 Next steps:")
        print("1. Review position sizing in config.json (currently 0.7)")
        print("2. Ensure you have at least $10-20 USDT")
        print("3. Run: python scripts/live_launch.py")
    else:
        print("\n❌ Fix the issues above before launching")