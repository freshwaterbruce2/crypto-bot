#!/usr/bin/env python3
"""
Simple Kraken Pro Client Test
============================

Basic test to verify the Kraken Pro client works with existing credentials.
This test focuses on REST API functionality first.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment for testing
os.environ['PYTHONPATH'] = str(Path(__file__).parent / "src")


async def test_basic_functionality():
    """Test basic functionality without WebSockets."""

    print("Testing Kraken Pro Client - Basic Functionality")
    print("=" * 50)

    try:
        # Import with better error handling
        try:
            from src.api.kraken_rest_client import KrakenRestClient
            from src.rate_limiting.kraken_rate_limiter import AccountTier
            print("✅ Successfully imported core components")
        except ImportError as e:
            print(f"❌ Import error: {e}")
            return False

        # Test 1: Basic REST client initialization
        print("\nTest 1: REST Client Initialization")
        try:
            client = KrakenRestClient(account_tier=AccountTier.PRO)
            await client.start()
            print("✅ REST client initialized successfully")
        except Exception as e:
            print(f"❌ REST client initialization failed: {e}")
            return False

        # Test 2: Basic API connectivity
        print("\nTest 2: API Connectivity")
        try:
            server_time = await client.get_server_time()
            if server_time.get('result'):
                print("✅ Server time retrieved successfully")
                print(f"   Server timestamp: {server_time['result'].get('unixtime')}")
            else:
                print(f"❌ Server time request failed: {server_time}")
                return False
        except Exception as e:
            print(f"❌ Server time request failed: {e}")
            return False

        # Test 3: Authentication test
        print("\nTest 3: API Authentication")
        try:
            balance = await client.get_account_balance()
            if balance.get('result'):
                print("✅ Authentication successful - balance retrieved")

                # Show non-zero balances
                result = balance['result']
                non_zero = {k: v for k, v in result.items() if float(v) > 0}
                if non_zero:
                    print("   Non-zero balances:")
                    for asset, amount in list(non_zero.items())[:5]:
                        print(f"     {asset}: {amount}")
                else:
                    print("   All balances are zero (normal for new accounts)")
            else:
                print(f"❌ Authentication failed: {balance}")
                return False
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
            return False

        # Test 4: WebSocket token test
        print("\nTest 4: WebSocket Token Availability")
        try:
            token_response = await client.get_websockets_token()
            if token_response.get('result') and token_response['result'].get('token'):
                print("✅ WebSocket token obtained successfully")
                print("   This indicates your API key has WebSocket permissions")
                token = token_response['result']['token']
                print(f"   Token length: {len(token)} characters")
            else:
                print("⚠️  WebSocket token not available")
                print("   This may indicate restricted API permissions")
                print(f"   Response: {token_response}")
        except Exception as e:
            print(f"⚠️  WebSocket token test failed: {e}")
            # Not a critical failure for basic functionality

        # Test 5: Market data access
        print("\nTest 5: Market Data Access")
        try:
            ticker_data = await client.get_ticker_information("XBTUSD")
            if ticker_data.get('result'):
                print("✅ Market data retrieved successfully")
                result = ticker_data['result']
                if 'XXBTZUSD' in result:
                    btc_data = result['XXBTZUSD']
                    last_price = btc_data.get('c', ['N/A'])[0]
                    print(f"   BTC/USD Last Price: ${last_price}")
            else:
                print(f"❌ Market data request failed: {ticker_data}")
                return False
        except Exception as e:
            print(f"❌ Market data test failed: {e}")
            return False

        # Test 6: Rate limiting status
        print("\nTest 6: Rate Limiting Status")
        try:
            if hasattr(client, 'rate_limiter') and client.rate_limiter:
                rl_status = client.rate_limiter.get_status()
                print("✅ Rate limiter active")
                print(f"   Account tier: {rl_status.get('account_tier', 'unknown')}")
                print(f"   Requests made: {rl_status.get('statistics', {}).get('requests_made', 0)}")
            else:
                print("⚠️  Rate limiter not active")
        except Exception as e:
            print(f"⚠️  Rate limiter status check failed: {e}")

        # Test 7: Clean shutdown
        print("\nTest 7: Clean Shutdown")
        try:
            await client.close()
            print("✅ Client closed successfully")
        except Exception as e:
            print(f"❌ Client shutdown failed: {e}")
            return False

        print("\n" + "=" * 50)
        print("🎉 ALL BASIC TESTS PASSED!")
        print("Your Kraken API credentials are working correctly.")
        print("✅ REST API connectivity: OK")
        print("✅ Authentication: OK")
        print("✅ Account access: OK")
        print("✅ Market data: OK")

        return True

    except Exception as e:
        print(f"\n❌ Test suite failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main function."""
    try:
        success = await test_basic_functionality()

        if success:
            print("\n🚀 Ready for Kraken Pro Client integration!")
            print("The enhanced client with WebSocket V2 support can now be tested.")
        else:
            print("\n⚠️  Basic functionality issues detected.")
            print("Please resolve these before testing WebSocket features.")

        return success

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
