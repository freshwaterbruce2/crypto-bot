#!/usr/bin/env python3
"""
Check Kraken API Key Permissions
Diagnoses what permissions your API key has
"""

import asyncio
import base64
import hashlib
import hmac
import os
import time
import urllib.parse
from datetime import datetime

import aiohttp


async def test_api_endpoint(api_key, api_secret, endpoint, description):
    """Test a specific API endpoint to check permissions"""

    api_url = "https://api.kraken.com"

    # Generate nonce (milliseconds)
    nonce = str(int(time.time() * 1000))

    # Prepare POST data
    data = {"nonce": nonce}
    postdata = urllib.parse.urlencode(data)

    # Generate signature
    message = (str(nonce) + postdata).encode('utf-8')
    sha256_hash = hashlib.sha256(message).digest()
    hmac_message = endpoint.encode('utf-8') + sha256_hash
    secret_decoded = base64.b64decode(api_secret)
    signature = hmac.new(secret_decoded, hmac_message, hashlib.sha512)
    signature_b64 = base64.b64encode(signature.digest()).decode()

    # Prepare headers
    headers = {
        'API-Key': api_key,
        'API-Sign': signature_b64,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url + endpoint,
                headers=headers,
                data=postdata,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:

                result = await response.json()

                if result.get('error') and len(result['error']) > 0:
                    error_msg = result['error'][0] if isinstance(result['error'], list) else str(result['error'])
                    return False, error_msg

                return True, "Success"

    except Exception as e:
        return False, str(e)

async def main():
    """Main diagnostic function"""

    print("="*60)
    print("KRAKEN API KEY PERMISSIONS CHECK")
    print("="*60)
    print(f"Time: {datetime.now()}")

    # Get credentials
    api_key = os.getenv('KRAKEN_KEY') or os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_SECRET') or os.getenv('KRAKEN_API_SECRET')

    if not api_key or not api_secret:
        print("\n❌ No API credentials found in environment variables")
        print("\nPlease set:")
        print("  KRAKEN_KEY=your_api_key")
        print("  KRAKEN_SECRET=your_api_secret")
        return

    print(f"\n🔑 Testing API Key: {api_key[:8]}...{api_key[-4:]}")
    print("\n" + "="*60)
    print("TESTING API PERMISSIONS")
    print("="*60)

    # Test different endpoints to determine permissions
    endpoints_to_test = [
        ("/0/private/Balance", "Query Funds (View Balances)"),
        ("/0/private/TradeBalance", "Query Trade Balance"),
        ("/0/private/OpenOrders", "Query Open Orders"),
        ("/0/private/ClosedOrders", "Query Closed Orders"),
        ("/0/private/QueryOrders", "Query Order Details"),
        ("/0/private/TradesHistory", "Query Trade History"),
        ("/0/private/OpenPositions", "Query Open Positions"),
        ("/0/private/Ledgers", "Query Ledger Entries"),
        ("/0/private/QueryLedgers", "Query Specific Ledgers"),
        ("/0/private/GetWebSocketsToken", "Access WebSockets API"),
    ]

    results = []
    permissions_found = []
    permissions_missing = []

    for endpoint, description in endpoints_to_test:
        print(f"\n📋 Testing: {description}")
        print(f"   Endpoint: {endpoint}")

        success, message = await test_api_endpoint(api_key, api_secret, endpoint, description)

        if success:
            print(f"   ✅ GRANTED - {description}")
            permissions_found.append(description)
        else:
            if "Permission denied" in message:
                print(f"   ❌ DENIED - {description}")
                permissions_missing.append(description)
            elif "Invalid key" in message:
                print("   ❌ INVALID KEY - API key not recognized")
                break
            else:
                print(f"   ⚠️  ERROR - {message}")

        results.append((description, success, message))

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

    # Summary
    print("\n" + "="*60)
    print("PERMISSIONS SUMMARY")
    print("="*60)

    if permissions_found:
        print("\n✅ GRANTED PERMISSIONS:")
        for perm in permissions_found:
            print(f"   • {perm}")

    if permissions_missing:
        print("\n❌ MISSING PERMISSIONS:")
        for perm in permissions_missing:
            print(f"   • {perm}")

    # Recommendations for trading bot
    print("\n" + "="*60)
    print("RECOMMENDATIONS FOR TRADING BOT")
    print("="*60)

    required_permissions = [
        "Query Funds (View Balances)",
        "Query Open Orders",
        "Query Closed Orders",
        "Access WebSockets API"
    ]

    trading_permissions = [
        "Create & Modify Orders",
        "Cancel/Close Orders"
    ]

    missing_required = [p for p in required_permissions if p in permissions_missing]

    if "Access WebSockets API" in permissions_missing:
        print("\n⚠️  CRITICAL: Missing 'Access WebSockets API' permission!")
        print("\n📋 TO FIX THIS:")
        print("1. Log into https://www.kraken.com/u/security/api")
        print("2. Find your API key or create a new one")
        print("3. Click 'Edit' on your API key")
        print("4. Enable these permissions:")
        print("   ✓ Query Funds")
        print("   ✓ Query Open Orders & Trades")
        print("   ✓ Query Closed Orders & Trades")
        print("   ✓ Create & Modify Orders")
        print("   ✓ Cancel/Close Orders")
        print("   ✓ Access WebSockets API  ← REQUIRED FOR BOT!")
        print("5. Save the changes")
        print("6. Run this script again to verify")
    elif missing_required:
        print(f"\n⚠️  Missing required permissions: {', '.join(missing_required)}")
        print("\nPlease update your API key permissions on Kraken")
    else:
        print("\n✅ Your API key has the minimum required permissions!")

        # Check for trading permissions
        print("\n📋 For live trading, you also need:")
        print("   • Create & Modify Orders")
        print("   • Cancel/Close Orders")
        print("\nNote: These weren't tested but are required for placing trades")

    print("\n" + "="*60)
    print("For Kraken Pro (fee-free) accounts, ensure KRAKEN_TIER=pro in .env")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
