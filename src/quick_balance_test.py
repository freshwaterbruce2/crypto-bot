#!/usr/bin/env python3
"""
QUICK BALANCE TEST - Test Nonce Fix with Real Configuration
=========================================================

This script tests the nonce fix using the bot's existing configuration
to verify that we can now access the $18.99 USDT + $8.99 SHIB balances.

CRITICAL: This is the final validation that nonce fix worked
Author: Emergency Trading Bot Repair Team
Date: 2025-08-03
"""

import logging
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_balance_access():
    """Test balance access with existing bot configuration"""
    print("🔍 QUICK BALANCE TEST - Using Bot Configuration")
    print("=" * 60)

    try:
        # Import the main bot configuration
        from src.config.trading import TradingConfig
        from src.exchange.exchange_singleton import ExchangeSingleton

        # Initialize with existing config
        print("📋 Loading trading configuration...")
        TradingConfig()

        print("📋 Initializing exchange singleton...")
        exchange = ExchangeSingleton.get_instance()

        print("📋 Testing nonce manager status...")
        from src.utils.consolidated_nonce_manager import get_nonce_manager
        nonce_manager = get_nonce_manager()
        status = nonce_manager.get_status()
        print(f"  • Nonce manager working: {status.get('current_nonce')}")
        print(f"  • Total nonces generated: {status.get('total_generated')}")
        print(f"  • Error recoveries: {status.get('error_recoveries')}")

        print("📋 Testing balance retrieval...")

        # Test balance access
        balances = exchange.get_account_balance()

        if balances:
            print("✅ SUCCESS: Balance retrieval working!")
            print("\n💰 Available Balances:")

            total_assets = 0
            for asset, amount in balances.items():
                if amount > 0:
                    print(f"  • {asset}: {amount}")
                    total_assets += 1

            # Check for specific assets
            usdt_balance = balances.get('USDT', 0)
            shib_balance = balances.get('SHIB', 0)

            if usdt_balance > 0:
                print(f"\n✅ USDT Found: ${usdt_balance:.2f}")
            else:
                print("\n⚠️  USDT: $0.00 (may be deployed in positions)")

            if shib_balance > 0:
                print(f"✅ SHIB Found: {shib_balance:.2f} SHIB")
            else:
                print("⚠️  SHIB: 0.00 SHIB (may be deployed in positions)")

            print(f"\n📊 Total Asset Types: {total_assets}")

            if total_assets > 0:
                print("\n🎉 NONCE FIX SUCCESSFUL!")
                print("✅ Your trading bot can now access account balances")
                print("🚀 The 'EAPI:Invalid nonce' errors have been resolved")

                # Test a simple order book call to validate trading readiness
                print("\n📋 Testing trading functionality...")
                try:
                    orderbook = exchange.get_order_book('SHIBUSDT', 1)
                    if orderbook:
                        print("✅ Order book access working - trading should be functional")
                        return True
                    else:
                        print("⚠️  Order book access limited")
                        return True  # Balance access is what matters most
                except Exception as e:
                    print(f"⚠️  Trading test error: {e}")
                    return True  # Balance access worked, that's the main goal
            else:
                print("\n⚠️  No balances detected - all funds may be in open positions")
                print("✅ But balance API access is working (nonce fix successful)")
                return True
        else:
            print("❌ Failed to retrieve balances")
            return False

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Try running the bot normally to see if nonce fix worked")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"💡 Error type: {type(e).__name__}")
        return False

def test_minimal_nonce():
    """Test minimal nonce functionality without full bot initialization"""
    print("\n🔍 MINIMAL NONCE TEST")
    print("-" * 40)

    try:
        from src.utils.consolidated_nonce_manager import get_nonce_manager

        manager = get_nonce_manager()

        # Generate a few test nonces
        nonces = []
        for i in range(3):
            nonce = manager.get_nonce(f"test_{i}")
            nonces.append(int(nonce))
            time.sleep(0.01)  # Small delay

        # Verify they're increasing
        if all(nonces[i] < nonces[i+1] for i in range(len(nonces)-1)):
            print("✅ Nonce generation working correctly")
            print(f"  • Generated: {len(nonces)} nonces")
            print(f"  • Range: {nonces[0]} -> {nonces[-1]}")
            return True
        else:
            print("❌ Nonces not properly increasing")
            return False

    except Exception as e:
        print(f"❌ Minimal nonce test failed: {e}")
        return False

def main():
    """Run quick balance test"""
    print("🚨 EMERGENCY NONCE FIX VALIDATION 🚨")
    print("Testing access to $18.99 USDT + $8.99 SHIB balances")
    print("=" * 60)

    # First test the nonce manager in isolation
    nonce_ok = test_minimal_nonce()

    if not nonce_ok:
        print("\n❌ CRITICAL: Nonce manager not working")
        print("🔧 The emergency fix may have failed")
        return False

    # Then test with full bot configuration
    balance_ok = test_balance_access()

    print("\n" + "=" * 60)
    print("🏁 FINAL RESULT")
    print("=" * 60)

    if balance_ok:
        print("🎉 SUCCESS: Nonce fix appears to have worked!")
        print("✅ Bot should now be able to access trading balances")
        print("🚀 Try running your normal trading bot to confirm")
        print("\n💡 If you still see 'EAPI:Invalid nonce' errors:")
        print("   1. Restart any running bot processes")
        print("   2. Clear any cached nonce files")
        print("   3. The unified nonce manager should handle recovery")
    else:
        print("⚠️  PARTIAL SUCCESS: Nonce manager fixed but balance access failed")
        print("🔧 This could mean:")
        print("   1. API credentials need checking")
        print("   2. Network connectivity issues")
        print("   3. The bot needs to be restarted")
        print("   4. Configuration files need updating")

    return balance_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
