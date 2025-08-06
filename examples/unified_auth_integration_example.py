#!/usr/bin/env python3
"""
Unified Authentication Integration Example
==========================================

This example shows how to integrate the unified authentication wrapper
into trading bot components to ensure credentials work reliably.

Usage: python examples/unified_auth_integration_example.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TradingBotComponent:
    """Example trading bot component using unified authentication"""

    def __init__(self):
        self.exchange = None
        self.api_key = None
        self.private_key = None

    async def initialize(self):
        """Initialize the component with guaranteed working credentials"""
        print("🔄 Initializing trading bot component...")

        # Import unified auth
        from src.auth.unified_auth import get_credentials

        # Get credentials using unified auth
        self.api_key, self.private_key = get_credentials()

        if not self.api_key or not self.private_key:
            raise Exception("Failed to load API credentials - check unified auth setup")

        print(f"✅ Credentials loaded: {self.api_key[:8]}...")

        # Initialize exchange with guaranteed working credentials
        await self._initialize_exchange()

    async def _initialize_exchange(self):
        """Initialize Kraken exchange with unified auth credentials"""
        try:
            from src.exchange.native_kraken_exchange import NativeKrakenExchange

            self.exchange = NativeKrakenExchange(
                api_key=self.api_key,
                api_secret=self.private_key,
                tier='starter'  # or get from config
            )

            await self.exchange.connect()
            print("✅ Exchange connected successfully")

        except Exception as e:
            print(f"❌ Failed to initialize exchange: {e}")
            raise

    async def test_functionality(self):
        """Test basic exchange functionality"""
        if not self.exchange:
            raise Exception("Exchange not initialized")

        try:
            # Test balance access
            balances = await self.exchange.get_balance()
            print(f"✅ Balance access successful: {len(balances)} assets")

            # Test market data access
            ticker = await self.exchange.get_ticker('BTC/USD')
            if ticker:
                print(f"✅ Market data access successful: BTC/USD = ${ticker.get('last', 'N/A')}")

            return True

        except Exception as e:
            print(f"❌ Functionality test failed: {e}")
            return False

    async def cleanup(self):
        """Clean up resources"""
        if self.exchange:
            await self.exchange.disconnect()
            print("✅ Exchange disconnected")


class SimpleRestClient:
    """Example of a simple REST client using unified auth"""

    def __init__(self):
        self.auth = None

    async def initialize(self):
        """Initialize REST client with unified auth"""
        from src.auth.kraken_auth import KrakenAuth
        from src.auth.unified_auth import get_credentials

        api_key, private_key = get_credentials()

        if not api_key or not private_key:
            raise Exception("No credentials available")

        self.auth = KrakenAuth(api_key, private_key)
        print("✅ REST client initialized with unified auth")

    async def test_request(self):
        """Test a simple REST request"""
        try:
            # Test basic authentication with account balance
            test_results = self.auth.run_comprehensive_test()

            if test_results.get('overall_success'):
                print("✅ REST API test successful")
                return True
            else:
                print(f"❌ REST API test failed: {test_results}")
                return False

        except Exception as e:
            print(f"❌ REST request failed: {e}")
            return False


async def demonstrate_unified_auth_integration():
    """Demonstrate how to integrate unified auth into bot components"""
    print("🚀 UNIFIED AUTHENTICATION INTEGRATION DEMO")
    print("=" * 60)

    # Test 1: Full trading bot component
    print("\n📋 Test 1: Trading Bot Component Integration")
    print("-" * 40)

    try:
        bot_component = TradingBotComponent()
        await bot_component.initialize()

        success = await bot_component.test_functionality()
        await bot_component.cleanup()

        if success:
            print("✅ Trading bot component integration successful")
        else:
            print("⚠️ Trading bot component had functionality issues")

    except Exception as e:
        print(f"❌ Trading bot component integration failed: {e}")

    # Test 2: Simple REST client
    print("\n📋 Test 2: Simple REST Client Integration")
    print("-" * 40)

    try:
        rest_client = SimpleRestClient()
        await rest_client.initialize()

        success = await rest_client.test_request()

        if success:
            print("✅ REST client integration successful")
        else:
            print("⚠️ REST client had request issues")

    except Exception as e:
        print(f"❌ REST client integration failed: {e}")

    # Summary
    print("\n📊 INTEGRATION SUMMARY")
    print("-" * 30)
    print("✅ Unified auth can be easily integrated into any component")
    print("✅ Just call get_credentials() to get guaranteed working credentials")
    print("✅ No need to handle complex credential loading logic in each component")
    print("✅ Automatic fallback to Windows environment variables in WSL")


async def show_usage_patterns():
    """Show common usage patterns for unified auth"""
    print("\n💡 COMMON USAGE PATTERNS")
    print("=" * 40)

    print("\n1️⃣ SIMPLE CREDENTIAL LOADING:")
    print("```python")
    print("from src.auth.unified_auth import get_credentials")
    print("api_key, private_key = get_credentials()")
    print("```")

    print("\n2️⃣ CREDENTIAL STATUS CHECK:")
    print("```python")
    print("from src.auth.unified_auth import get_credential_status")
    print("status = get_credential_status()")
    print("if status['credentials_available']:")
    print("    # proceed with initialization")
    print("```")

    print("\n3️⃣ AUTHENTICATION TESTING:")
    print("```python")
    print("from src.auth.unified_auth import test_auth")
    print("if await test_auth():")
    print("    # authentication working")
    print("```")

    print("\n4️⃣ EXCHANGE INITIALIZATION:")
    print("```python")
    print("from src.auth.unified_auth import get_credentials")
    print("from src.exchange.native_kraken_exchange import NativeKrakenExchange")
    print("")
    print("api_key, private_key = get_credentials()")
    print("exchange = NativeKrakenExchange(")
    print("    api_key=api_key,")
    print("    api_secret=private_key")
    print(")")
    print("```")


async def main():
    """Main demonstration function"""
    await demonstrate_unified_auth_integration()
    await show_usage_patterns()

    print("\n🎉 UNIFIED AUTH INTEGRATION COMPLETE!")
    print("🚀 Use these patterns in your trading bot components")


if __name__ == "__main__":
    asyncio.run(main())
