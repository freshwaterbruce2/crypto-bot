#!/usr/bin/env python3
"""Quick test to verify bot can launch without errors."""

import asyncio
import logging
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


async def test_bot_launch():
    """Test if the bot can launch successfully."""
    logger.info("=" * 60)
    logger.info("TESTING BOT LAUNCH")
    logger.info("=" * 60)

    try:
        # Import the bot
        from src.core.bot import KrakenTradingBot

        logger.info("✓ Bot module imported successfully")

        # Initialize the bot
        bot = KrakenTradingBot()
        logger.info("✓ Bot initialized successfully")

        # Check critical components
        if bot.exchange:
            logger.info("✓ Exchange initialized")
        else:
            logger.warning("✗ Exchange not initialized")

        if bot.balance_manager:
            logger.info("✓ Balance manager initialized")
        else:
            logger.warning("✗ Balance manager not initialized")

        if bot.strategy_manager:
            logger.info("✓ Strategy manager initialized")
        else:
            logger.warning("✗ Strategy manager not initialized")

        # Try to start the bot (but stop immediately)
        logger.info("\nAttempting to start bot components...")

        # Just initialize, don't run the full loop
        await bot.initialize()
        logger.info("✓ Bot initialization completed")

        # Cleanup
        if hasattr(bot, 'cleanup'):
            await bot.cleanup()

        logger.info("\n" + "=" * 60)
        logger.info("✓ BOT LAUNCH TEST SUCCESSFUL")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"\n✗ BOT LAUNCH FAILED: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(test_bot_launch())
    sys.exit(0 if success else 1)
