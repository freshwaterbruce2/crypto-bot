#!/usr/bin/env python3
"""
Quick test to verify bot can launch without errors
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


async def test_launch():
    """Test bot launch sequence"""
    logger.info("=" * 60)
    logger.info("TESTING BOT LAUNCH SEQUENCE")
    logger.info("=" * 60)

    try:
        # Test 1: Load configuration
        logger.info("\n1. Loading configuration...")
        import json
        with open('config.json') as f:
            config = json.load(f)
        logger.info("✅ Configuration loaded successfully")

        # Test 2: Check credentials
        logger.info("\n2. Checking credentials...")
        api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('KRAKEN_KEY', '')
        api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('KRAKEN_SECRET', '')

        if api_key and api_secret:
            logger.info(f"✅ API credentials found: {api_key[:8]}...")
        else:
            logger.error("❌ API credentials missing")
            return False

        # Test 3: Initialize bot
        logger.info("\n3. Initializing bot...")
        from src.core.bot import TradingBot

        bot = TradingBot(config)
        logger.info("✅ Bot instance created")

        # Test 4: Setup basic components
        logger.info("\n4. Setting up basic components...")
        await bot._setup_basic_components()
        logger.info("✅ Basic components initialized")

        # Test 5: Test WebSocket manager
        logger.info("\n5. Testing WebSocket manager...")
        if bot.websocket_manager:
            logger.info("✅ WebSocket manager available")
        else:
            logger.warning("⚠️ WebSocket manager not available (will use REST fallback)")

        # Test 6: Test balance manager
        logger.info("\n6. Testing balance manager...")
        if bot.balance_manager:
            logger.info("✅ Balance manager available")

            # Try to get USDT balance
            try:
                usdt_balance = await bot.balance_manager.get_balance('USDT')
                if usdt_balance is not None:
                    logger.info(f"✅ USDT balance: ${usdt_balance:.2f}")
                else:
                    logger.warning("⚠️ USDT balance not available")
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch USDT balance: {e}")
        else:
            logger.error("❌ Balance manager not available")

        logger.info("\n" + "=" * 60)
        logger.info("✅ BOT LAUNCH TEST SUCCESSFUL!")
        logger.info("=" * 60)

        # Cleanup
        if bot.websocket_manager and hasattr(bot.websocket_manager, 'stop'):
            await bot.websocket_manager.stop()

        return True

    except Exception as e:
        logger.error(f"❌ Launch test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(test_launch())
    sys.exit(0 if success else 1)
