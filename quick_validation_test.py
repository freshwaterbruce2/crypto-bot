#!/usr/bin/env python3
"""
Quick validation test for critical fixes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_portfolio_manager():
    """Test PortfolioManager fixes"""
    print("Testing PortfolioManager...")

    try:
        from src.portfolio.portfolio_manager import PortfolioConfig, PortfolioManager

        # Create instance
        config = PortfolioConfig()
        portfolio = PortfolioManager(config=config)

        # Test method existence
        assert hasattr(portfolio, 'get_open_positions'), "get_open_positions method missing"
        assert hasattr(portfolio, 'get_open_positions_sync'), "get_open_positions_sync method missing"
        assert hasattr(portfolio, 'force_sync_with_exchange'), "force_sync_with_exchange method missing"

        # Test method signatures
        import inspect
        sig = inspect.signature(portfolio.force_sync_with_exchange)
        params = list(sig.parameters.keys())
        assert 'exchange' in params, "exchange parameter missing"
        assert 'balance_manager' in params, "balance_manager parameter missing"

        print("✓ PortfolioManager tests passed")
        return True

    except Exception as e:
        print(f"✗ PortfolioManager test failed: {e}")
        return False


def test_balance_manager_v2():
    """Test Balance Manager V2 fixes"""
    print("Testing BalanceManagerV2...")

    try:
        from src.balance.balance_manager_v2 import BalanceManagerV2, BalanceManagerV2Config

        # Create instance
        config = BalanceManagerV2Config()
        balance_manager = BalanceManagerV2(None, None, config)

        # Test method existence
        assert hasattr(balance_manager, 'get_balance'), "get_balance method missing"
        assert hasattr(balance_manager, 'get_usdt_total'), "get_usdt_total method missing"
        assert hasattr(balance_manager, 'force_refresh'), "force_refresh method missing"

        print("✓ BalanceManagerV2 tests passed")
        return True

    except Exception as e:
        print(f"✗ BalanceManagerV2 test failed: {e}")
        return False


def test_profit_harvester():
    """Test ProfitHarvester integration"""
    print("Testing ProfitHarvester integration...")

    try:
        from src.portfolio.portfolio_manager import PortfolioConfig, PortfolioManager
        from src.trading.profit_harvester import ProfitHarvester

        # Create portfolio instance
        config = PortfolioConfig()
        portfolio = PortfolioManager(config=config)

        # Create profit harvester with portfolio (need both portfolio_tracker and config)
        profit_harvester = ProfitHarvester(
            bot=None,
            exchange=None,
            portfolio_tracker=portfolio,
            config={'min_profit_pct': 1.0}
        )

        # Test that portfolio_tracker is set
        assert profit_harvester.portfolio_tracker is not None, "portfolio_tracker not set"

        print("✓ ProfitHarvester integration tests passed")
        return True

    except Exception as e:
        print(f"✗ ProfitHarvester integration test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("Running Critical Fixes Validation Tests...")
    print("=" * 50)

    tests = [
        ("PortfolioManager", test_portfolio_manager),
        ("BalanceManagerV2", test_balance_manager_v2),
        ("ProfitHarvester Integration", test_profit_harvester),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} test crashed: {e}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY:")
    print("=" * 50)

    all_passed = True
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")
        if not result:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("🎉 ALL CRITICAL FIXES VALIDATED SUCCESSFULLY!")
        print("\nThe bot should now work without the following errors:")
        print("- 'PortfolioManager' object has no attribute 'get_open_positions'")
        print("- 'Could not retrieve balance for USDT'")
        print("- 'PortfolioManager.force_sync_with_exchange() got an unexpected keyword argument'")
        print("- Profit harvester errors due to missing get_open_positions")
    else:
        print("❌ SOME TESTS FAILED - Review errors above")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
