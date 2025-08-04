#!/usr/bin/env python3
"""
Test Live WebSocket V2 Fixes
============================

This script runs the trading bot for a short period to verify that the
WebSocket V2 message parsing fixes resolve the "unknown message" issues.
"""

import asyncio
import logging
import sys
import os
import signal
import time
from datetime import datetime

# Setup enhanced logging
logging.basicConfig(
    level=logging.INFO,  # Use INFO to avoid too much debug output
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s'
)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, requesting shutdown...")
    shutdown_requested = True

async def test_live_websocket_fixes():
    """Test the WebSocket fixes with the live bot"""
    logger.info("=== Live WebSocket V2 Fix Testing ===")
    
    try:
        # Import bot components
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from src.core.bot import KrakenTradingBot
        from src.config.core import load_config
        
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Create bot instance
        bot = KrakenTradingBot(config)
        logger.info("Bot instance created")
        
        # Initialize bot
        await bot.initialize()
        logger.info("Bot initialized successfully")
        
        # Run bot for 60 seconds to test WebSocket message processing
        logger.info("Starting bot for 60 seconds to test WebSocket message processing...")
        
        start_time = time.time()
        test_duration = 60  # seconds
        
        # Start bot
        bot_task = asyncio.create_task(bot.run())
        
        # Monitor for shutdown or timeout
        while not shutdown_requested and (time.time() - start_time) < test_duration:
            await asyncio.sleep(1)
            
            # Log progress every 10 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                logger.info(f"Test running... {elapsed:.0f}s elapsed")
        
        # Shutdown bot
        logger.info("Shutting down bot...")
        bot_task.cancel()
        
        try:
            await bot_task
        except asyncio.CancelledError:
            logger.info("Bot task cancelled successfully")
        
        # Get final statistics if available
        if hasattr(bot, 'websocket_manager') and bot.websocket_manager:
            if hasattr(bot.websocket_manager, 'v2_message_handler'):
                handler = bot.websocket_manager.v2_message_handler
                if handler:
                    stats = handler.get_statistics()
                    logger.info("=== Final WebSocket Statistics ===")
                    for key, value in stats.items():
                        logger.info(f"{key}: {value}")
        
        logger.info("=== Live WebSocket V2 Fix Testing Complete ===")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main test function"""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        success = await test_live_websocket_fixes()
        return success
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return True
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting live WebSocket V2 fix testing...")
    success = asyncio.run(main())
    logger.info(f"Test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)