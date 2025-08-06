#!/usr/bin/env python3
"""
Run Balance Flow Test - Simple Launcher
=======================================

This script provides a simple way to test and fix the WebSocket V2 balance data flow.
It runs through the key validation steps and applies fixes as needed.

Usage:
    python run_balance_flow_test.py                    # Quick test
    python run_balance_flow_test.py --full-validation  # Comprehensive validation
    python run_balance_flow_test.py --apply-fix        # Apply integration fix
    python run_balance_flow_test.py --test-only        # Test flow only
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.custom_logging import configure_logging

logger = configure_logging()


async def run_quick_balance_test():
    """Run quick balance flow test"""
    logger.info("=" * 60)
    logger.info("QUICK WEBSOCKET V2 BALANCE FLOW TEST")
    logger.info("=" * 60)

    try:
        # Import and run the flow test
        from test_websocket_balance_flow import WebSocketBalanceFlowTest

        test = WebSocketBalanceFlowTest()
        success = await test.run_comprehensive_test()

        if success:
            logger.info("🎉 Quick balance flow test PASSED!")
            logger.info("   → WebSocket V2 is connected and authenticated")
            logger.info("   → Balance data is flowing to Balance Manager V2")
            logger.info("   → Real-time balance updates are working")
            return True
        else:
            logger.warning("⚠️ Quick balance flow test showed ISSUES")
            logger.warning("   → Some components may need attention")
            logger.warning("   → Try running with --apply-fix to resolve issues")
            return False

    except Exception as e:
        logger.error(f"❌ Quick balance flow test FAILED: {e}")
        logger.error("   → Check configuration and network connectivity")
        return False


async def apply_integration_fix():
    """Apply the WebSocket V2 balance integration fix"""
    logger.info("=" * 60)
    logger.info("APPLYING WEBSOCKET V2 BALANCE INTEGRATION FIX")
    logger.info("=" * 60)

    try:
        # Import and apply the integration fix
        from websocket_v2_balance_integration_fix import WebSocketV2BalanceIntegrationFix

        integration_fix = WebSocketV2BalanceIntegrationFix()
        success = await integration_fix.apply_fix()

        if success:
            logger.info("✅ Integration fix applied successfully!")

            # Test the fix
            logger.info("Testing the integration fix...")
            test_success = await integration_fix.test_integration(60)  # 1 minute test

            if test_success:
                logger.info("🎉 Integration fix WORKING correctly!")
                logger.info("   → WebSocket V2 balance data is now flowing to trading bot")
                logger.info("   → Balance Manager V2 is receiving real-time updates")
                logger.info("   → Trading logic can access balance data in real-time")
            else:
                logger.warning("⚠️ Integration fix applied but testing showed issues")
                logger.warning("   → Check WebSocket permissions and connectivity")

            await integration_fix.cleanup()
            return test_success
        else:
            logger.error("❌ Integration fix FAILED to apply")
            return False

    except Exception as e:
        logger.error(f"❌ Integration fix crashed: {e}")
        return False


async def run_full_validation():
    """Run comprehensive validation"""
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE WEBSOCKET V2 BALANCE PIPELINE VALIDATION")
    logger.info("=" * 60)

    try:
        # Import and run comprehensive validation
        from validate_websocket_balance_pipeline import WebSocketBalancePipelineValidator

        validator = WebSocketBalancePipelineValidator()
        report = await validator.run_comprehensive_validation()

        # Print the report
        validator.print_validation_report(report)

        # Determine result
        overall_score = report['validation_summary']['overall_score']

        if overall_score >= 0.8:
            logger.info("🎉 Comprehensive validation PASSED!")
            logger.info("   → All pipeline components are working correctly")
            logger.info("   → Balance data flow is healthy and performant")
            return True
        elif overall_score >= 0.5:
            logger.warning("⚠️ Comprehensive validation shows ISSUES!")
            logger.warning("   → Some components need attention")
            logger.warning("   → Consider applying integration fix")
            return False
        else:
            logger.error("❌ Comprehensive validation FAILED!")
            logger.error("   → Critical issues found in pipeline")
            logger.error("   → Apply integration fix and check configuration")
            return False

    except Exception as e:
        logger.error(f"❌ Comprehensive validation crashed: {e}")
        return False


async def main():
    """Main launcher function"""
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket V2 Balance Flow Test Launcher")
    parser.add_argument("--full-validation", action="store_true",
                       help="Run comprehensive validation")
    parser.add_argument("--apply-fix", action="store_true",
                       help="Apply integration fix")
    parser.add_argument("--test-only", action="store_true",
                       help="Run test only, no fixes")
    parser.add_argument("--config", default="config.json",
                       help="Configuration file path")

    args = parser.parse_args()

    start_time = time.time()

    try:
        if args.full_validation:
            # Run comprehensive validation
            success = await run_full_validation()
        elif args.apply_fix:
            # Apply integration fix
            success = await apply_integration_fix()
        elif args.test_only:
            # Run test only
            success = await run_quick_balance_test()
        else:
            # Default: Quick test, then fix if needed
            logger.info("Running quick test first...")
            success = await run_quick_balance_test()

            if not success:
                logger.info("\nQuick test found issues. Applying integration fix...")
                success = await apply_integration_fix()

        execution_time = time.time() - start_time

        print(f"\n{'=' * 60}")
        print("BALANCE FLOW TEST SUMMARY")
        print(f"{'=' * 60}")
        print(f"Execution time: {execution_time:.1f} seconds")

        if success:
            print("✅ SUCCESS: WebSocket V2 balance flow is working!")
            print("\nWhat this means:")
            print("  → Kraken WebSocket V2 is connected and authenticated")
            print("  → Real-time balance updates are flowing correctly")
            print("  → Balance Manager V2 is receiving and processing data")
            print("  → Trading bot can access up-to-date balance information")
            print("  → The balance pipeline is ready for live trading")

            print("\nNext steps:")
            print("  1. Your bot is ready to use real-time balance data")
            print("  2. Monitor the balance updates during trading")
            print("  3. Consider enabling WebSocket-first mode (95% WebSocket usage)")

            sys.exit(0)
        else:
            print("❌ ISSUES: WebSocket V2 balance flow needs attention!")
            print("\nPossible issues:")
            print("  → API key missing 'Access WebSockets API' permission")
            print("  → Network connectivity problems")
            print("  → Configuration errors")
            print("  → Component initialization failures")

            print("\nTroubleshooting steps:")
            print("  1. Check API key permissions in Kraken account")
            print("  2. Verify config.json has correct API credentials")
            print("  3. Test network connectivity to Kraken")
            print("  4. Run: python run_balance_flow_test.py --full-validation")
            print("  5. Check logs for specific error messages")

            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"\n💥 Test crashed with unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(3)


if __name__ == "__main__":
    # Set up event loop for Windows compatibility
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
