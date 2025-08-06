#!/usr/bin/env python3
"""
Simple Bot Launcher - Fixed for August 2025
===========================================

Bypasses complex initialization and runs the trading bot directly.
"""

import asyncio
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run the bot in simple mode"""
    
    logger.info("Starting Simple Bot Launcher...")
    
    # Check credentials
    api_key = os.getenv('KRAKEN_KEY') or os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_SECRET') or os.getenv('KRAKEN_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("No API credentials found in environment")
        return
    
    logger.info("✅ Credentials loaded")
    
    # Import bot components
    try:
        from src.core.bot import KrakenTradingBot
        import json
        
        # Load configuration
        with open('config.json', 'r') as f:
            config = json.load(f)
        logger.info("✅ Configuration loaded")
        
        # Create bot instance
        bot = KrakenTradingBot(config=config)
        logger.info("✅ Bot instance created")
        
        # Initialize the bot
        logger.info("Initializing bot components...")
        await bot.initialize()
        logger.info("✅ Bot initialized successfully")
        
        # Run the bot
        logger.info("Starting trading loop...")
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())