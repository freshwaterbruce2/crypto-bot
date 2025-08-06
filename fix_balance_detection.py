#!/usr/bin/env python3
"""
Fix Balance Detection for Kraken USDT
=====================================

This script checks what currency codes Kraken actually uses for USDT
and updates the balance manager to handle them correctly.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


async def check_kraken_currency_codes():
    """Check what currency codes Kraken uses for USDT and other assets"""
    logger.info("=" * 60)
    logger.info("CHECKING KRAKEN CURRENCY CODES")
    logger.info("=" * 60)

    try:
        # Import ccxt
        import ccxt.pro as ccxtpro

        # Get credentials
        api_key = os.getenv('KRAKEN_REST_API_KEY') or os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_REST_API_SECRET') or os.getenv('KRAKEN_API_SECRET', '')

        if not api_key or not api_secret:
            logger.warning("No API credentials found - using public API only")
            exchange = ccxtpro.kraken()
        else:
            logger.info("Using authenticated API")
            exchange = ccxtpro.kraken({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True
            })

        # Load markets to get currency mappings
        logger.info("\n1. Loading markets...")
        await exchange.load_markets()

        # Check currency codes
        logger.info("\n2. Currency codes in use:")
        if 'USDT' in exchange.currencies:
            logger.info(f"  USDT: {exchange.currencies['USDT']}")

        # Check all USDT-related codes
        usdt_codes = []
        for code in exchange.currencies:
            if 'USDT' in code.upper() or 'USD' in code.upper():
                usdt_codes.append(code)
                logger.info(f"  {code}: {exchange.currencies[code]}")

        # If we have credentials, try to fetch balance
        if api_key and api_secret:
            logger.info("\n3. Fetching actual balance...")
            try:
                balance = await exchange.fetch_balance()

                # Show raw balance info
                logger.info("\n4. Raw balance response keys:")
                if 'info' in balance:
                    for key in balance['info'].keys():
                        logger.info(f"  {key}")

                # Check for USDT in different forms
                logger.info("\n5. Looking for USDT in balance:")
                found_usdt = False

                for key in ['USDT', 'ZUSDT', 'USDT.S', 'XUSDT', 'USDT.M']:
                    if key in balance['total'] and balance['total'][key] > 0:
                        logger.info(f"  ✓ Found {key}: {balance['total'][key]}")
                        found_usdt = True
                    elif key in balance:
                        logger.info(f"  ✓ Found {key} in balance structure")
                        found_usdt = True

                if not found_usdt:
                    logger.info("  ✗ No USDT found - checking all non-zero balances:")
                    for asset, amount in balance['total'].items():
                        if amount > 0:
                            logger.info(f"    {asset}: {amount}")

                # Check the raw info for USDT variants
                if 'info' in balance and 'result' in balance['info']:
                    logger.info("\n6. Checking raw balance result:")
                    for key, value in balance['info']['result'].items():
                        if 'USD' in key.upper():
                            logger.info(f"  Raw key '{key}': {value}")

            except Exception as e:
                logger.error(f"Failed to fetch balance: {e}")

        # Close exchange
        await exchange.close()

        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)

        if usdt_codes:
            logger.info(f"Found {len(usdt_codes)} USD-related currency codes:")
            for code in usdt_codes:
                logger.info(f"  - {code}")
        else:
            logger.info("No USDT-related codes found in currencies")

        return usdt_codes

    except Exception as e:
        logger.error(f"Error checking currency codes: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


async def test_balance_manager():
    """Test the balance manager with correct currency codes"""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING BALANCE MANAGER")
    logger.info("=" * 60)

    try:
        from src.balance.balance_manager_v2 import BalanceManagerV2, BalanceManagerV2Config
        from src.exchange.exchange_singleton import get_exchange

        # Get exchange
        api_key = os.getenv('KRAKEN_REST_API_KEY') or os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_REST_API_SECRET') or os.getenv('KRAKEN_API_SECRET', '')

        if not api_key or not api_secret:
            logger.warning("No API credentials - skipping balance manager test")
            return

        exchange = await get_exchange(
            api_key=api_key,
            api_secret=api_secret,
            tier='pro'
        )

        # Create balance manager
        config = BalanceManagerV2Config(
            enable_balance_validation=True,
            websocket_primary_ratio=0.0,  # REST only for testing
            rest_fallback_ratio=1.0
        )

        balance_manager = BalanceManagerV2(
            websocket_client=None,
            exchange_client=exchange,
            config=config
        )

        await balance_manager.initialize()

        # Test USDT balance retrieval
        logger.info("\n1. Testing USDT balance retrieval...")
        usdt_balance = await balance_manager.get_balance('USDT')
        if usdt_balance:
            logger.info(f"  ✓ USDT balance: {usdt_balance}")
        else:
            logger.info("  ✗ Failed to get USDT balance")

        # Test all balances
        logger.info("\n2. Testing all balances...")
        all_balances = await balance_manager.get_all_balances()
        if all_balances:
            logger.info(f"  ✓ Found {len(all_balances)} assets")
            for asset, info in all_balances.items():
                if info.get('free', 0) > 0:
                    logger.info(f"    {asset}: {info.get('free', 0)}")
        else:
            logger.info("  ✗ Failed to get all balances")

        await balance_manager.shutdown()

    except Exception as e:
        logger.error(f"Balance manager test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # Run tests
    asyncio.run(check_kraken_currency_codes())
    asyncio.run(test_balance_manager())
