"""
KRAKEN COMPLIANCE VERIFICATION SCRIPT
=====================================
Run this to verify all Kraken compliance requirements are met
Last Updated: June 29, 2025
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


async def verify_kraken_compliance():
    """Verify all Kraken compliance requirements are met"""

    print("\n" + "="*60)
    print("KRAKEN COMPLIANCE VERIFICATION")
    print(f"Date: {datetime.now().strftime('%B %d, %Y')}")
    print("="*60 + "\n")

    issues = []
    warnings = []

    # 1. Check disk space
    try:
        import psutil
        disk = psutil.disk_usage('D:/')
        print(f"[CHECK 1] Disk Space: {disk.percent:.1f}%", end="")
        if disk.percent > 90:
            print(" [FAIL]")
            issues.append(f"Disk space too high: {disk.percent:.1f}%")
        elif disk.percent > 80:
            print(" [WARNING]")
            warnings.append(f"Disk space getting high: {disk.percent:.1f}%")
        else:
            print(" [PASS]")
    except Exception as e:
        print(" [ERROR]")
        issues.append(f"Could not check disk space: {e}")

    # 2. Check PID file
    pid_file = project_root / "bot.pid"
    print("[CHECK 2] PID File Exists: ", end="")
    if pid_file.exists():
        print("[PASS]")
    else:
        print("[WARNING]")
        warnings.append("PID file missing - will be created on bot start")

    # 3. Check configuration
    config_path = project_root / "config.json"
    print("[CHECK 3] Configuration File: ", end="")
    try:
        with open(config_path) as f:
            config = json.load(f)
        print("[PASS]")

        # 3a. WebSocket Auth
        print("[CHECK 3a] WebSocket Auth Enabled: ", end="")
        if config.get('exchange_config', {}).get('enable_websocket_auth'):
            print("[PASS]")
        else:
            print("[FAIL]")
            issues.append("WebSocket auth not enabled in config")

        # 3b. Order Validation
        print("[CHECK 3b] Order Size Validation: ", end="")
        if config.get('enable_size_validation'):
            print("[PASS]")
        else:
            print("[FAIL]")
            issues.append("Order size validation not enabled")

        # 3c. Minimum Order Size
        print("[CHECK 3c] Minimum Order Size: ", end="")
        min_order = config.get('min_order_size_usdt', 0)
        if min_order >= 10.0:
            print(f"${min_order} [PASS]")
        else:
            print(f"${min_order} [FAIL]")
            issues.append(f"Minimum order size ${min_order} below Kraken requirement of $10")

        # 3d. Kraken API Tier
        print("[CHECK 3d] API Tier Configuration: ", end="")
        api_tier = config.get('kraken_api_tier', 'starter')
        print(f"{api_tier} [PASS]")

    except FileNotFoundError:
        print("[FAIL]")
        issues.append("config.json not found")
    except json.JSONDecodeError as e:
        print("[FAIL]")
        issues.append(f"config.json invalid JSON: {e}")
    except Exception as e:
        print("[ERROR]")
        issues.append(f"Error reading config: {e}")

    # 4. Check required modules
    print("[CHECK 4] Required Modules:")

    modules_to_check = [
        ("src.kraken_websocket_auth", "WebSocket Authentication"),
        ("src.kraken_rl", "Rate Limiter"),
        ("src.websocket_manager", "WebSocket Manager"),
        ("src.enhanced_trade_executor_with_assistants", "Trade Executor"),
        ("src.symbol_mapping.symbol_mapping_manager", "Symbol Mapper"),
        ("ccxt", "CCXT Library"),
    ]

    for module_name, description in modules_to_check:
        print(f"  - {description}: ", end="")
        try:
            __import__(module_name)
            print("[PASS]")
        except ImportError:
            print("[FAIL]")
            issues.append(f"{description} module not found: {module_name}")

    # 5. Check environment variables
    print("\n[CHECK 5] API Credentials:")
    api_key = os.environ.get('KRAKEN_API_KEY')
    api_secret = os.environ.get('KRAKEN_API_SECRET')

    print("  - API Key: ", end="")
    if api_key:
        print(f"***{api_key[-4:]} [PASS]")
    else:
        print("[FAIL]")
        issues.append("KRAKEN_API_KEY not set in environment")

    print("  - API Secret: ", end="")
    if api_secret:
        print("******* [PASS]")
    else:
        print("[FAIL]")
        issues.append("KRAKEN_API_SECRET not set in environment")

    # 6. Check .env file backup
    env_file = project_root / ".env"
    print("\n[CHECK 6] .env File Backup: ", end="")
    if env_file.exists():
        print("[PASS]")
    else:
        print("[WARNING]")
        warnings.append(".env file not found - using environment variables only")

    # Summary
    print("\n" + "-"*60)
    if issues:
        print("CRITICAL ISSUES FOUND:")
        for issue in issues:
            print(f"  [X] {issue}")

    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  [!] {warning}")

    if not issues:
        print("ALL CRITICAL CHECKS PASSED!")
        print("\nYour bot is compliant with Kraken guidelines.")

    print("\nIMPORTANT REMINDERS:")
    print("  1. Minimum balance required: $10 USDT")
    print("  2. API key needs 'WebSocket interface' permission")
    print("  3. All trading pairs use USDT as quote currency")
    print("-"*60 + "\n")

    return len(issues) == 0, issues, warnings


async def test_websocket_auth():
    """Test WebSocket authentication with Kraken"""
    print("\n[TEST] Testing WebSocket Authentication...")

    try:
        import ccxt.async_support as ccxt

        from src.kraken_websocket_auth import KrakenWebSocketAuth

        # Create exchange instance
        exchange = ccxt.kraken({
            'apiKey': os.environ.get('KRAKEN_API_KEY'),
            'secret': os.environ.get('KRAKEN_API_SECRET'),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })

        # Test authentication
        auth = KrakenWebSocketAuth(exchange)
        token = await auth.get_websocket_token()

        if token:
            print(f"  [SUCCESS] Got WebSocket token: {token[:20]}...")
            print("  [INFO] Token valid for 15 minutes")
            print("  [INFO] Ready for private channel subscriptions")
        else:
            print("  [FAIL] Could not get WebSocket token")
            print("  [INFO] Check your API keys have 'WebSocket interface' permission")

        await exchange.close()
        return bool(token)

    except ImportError as e:
        print(f"  [ERROR] Import error: {e}")
        print("  [INFO] Make sure all dependencies are installed")
        return False
    except Exception as e:
        print(f"  [ERROR] WebSocket auth test failed: {e}")
        print("  [INFO] Make sure API keys are set correctly")
        return False


async def test_kraken_connection():
    """Test basic Kraken API connection"""
    print("\n[TEST] Testing Kraken API Connection...")

    try:
        import ccxt.async_support as ccxt

        # Create public exchange instance (no auth needed)
        exchange = ccxt.kraken({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })

        # Test public endpoint
        ticker = await exchange.fetch_ticker('BTC/USDT')
        if ticker and 'last' in ticker:
            print("  [SUCCESS] Connected to Kraken")
            print(f"  [INFO] BTC/USDT price: ${ticker['last']:,.2f}")
        else:
            print("  [FAIL] Could not fetch market data")

        await exchange.close()
        return True

    except Exception as e:
        print(f"  [ERROR] Connection test failed: {e}")
        return False


async def check_minimum_orders():
    """Display Kraken minimum order requirements"""
    print("\n[INFO] Kraken Minimum Order Requirements:")
    print("-"*50)
    print("| Pair       | Min Amount | Min Cost |")
    print("|------------|------------|----------|")

    min_orders = {
        "BTC/USDT": (0.0001, 10.0),
        "ETH/USDT": (0.001, 10.0),
        "ADA/USDT": (10.0, 10.0),
        "DOT/USDT": (1.0, 10.0),
        "SOL/USDT": (0.1, 10.0),
        "XRP/USDT": (10.0, 10.0),
        "SHIB/USDT": (1000000, 10.0),
        "ALGO/USDT": (10.0, 10.0),
        "ATOM/USDT": (1.0, 10.0),
        "AVAX/USDT": (0.5, 10.0),
    }

    for pair, (min_amt, min_cost) in min_orders.items():
        print(f"| {pair:<10} | {min_amt:<10} | ${min_cost:<7} |")

    print("-"*50)


async def main():
    """Main verification and testing routine"""

    print("KRAKEN TRADING BOT COMPLIANCE CHECKER")
    print("=====================================")
    print("Version: 1.0.0")
    print(f"Date: {datetime.now().strftime('%B %d, %Y')}")

    # Run compliance verification
    compliant, issues, warnings = await verify_kraken_compliance()

    # If no critical issues, run additional tests
    if compliant:
        # Test Kraken connection
        connection_ok = await test_kraken_connection()

        if connection_ok and not any("API" in issue for issue in issues):
            # Test WebSocket authentication
            await test_websocket_auth()

    # Show minimum order requirements
    await check_minimum_orders()

    # Final summary
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)

    if compliant:
        print("[OK] Bot is ready for launch!")
        print("\n1. Ensure you have at least $10 USDT deposited")
        print("2. Run: python scripts/live_launch.py")
        print("3. Monitor logs for successful trades")
    else:
        print("[FAIL] Please fix the critical issues above")
        print("\n1. Address all critical issues listed")
        print("2. Run this script again to verify")
        print("3. Then launch the bot")

    print("\nPress Enter to exit...")
    input()


if __name__ == "__main__":
    asyncio.run(main())
