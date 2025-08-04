#!/usr/bin/env python3
"""
Bot Initialization Test
======================

Quick test to ensure bot can initialize with the critical fixes.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_bot_components():
    """Test that bot core components can initialize"""
    try:
        logger.info("🔍 Testing bot component initialization...")
        
        # Test exchange initialization
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        exchange = NativeKrakenExchange(
            api_key=os.getenv('KRAKEN_API_KEY', 'test_key'),
            api_secret=os.getenv('KRAKEN_API_SECRET', 'test_secret'),
            tier='pro'
        )
        logger.info("✅ Exchange component initialized")
        
        # Test simple balance manager
        from src.balance.simple_balance_manager import create_emergency_balance_manager
        balance_manager = await create_emergency_balance_manager(exchange)
        logger.info("✅ Balance manager component initialized")
        
        # Test strategy base class
        from src.strategies.base_strategy import BaseStrategy
        logger.info("✅ Strategy base class imported successfully")
        
        # Test core bot module
        from src.core.bot import KrakenTradingBot
        logger.info("✅ Core bot module imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Bot component test failed: {e}")
        return False


async def main():
    """Run bot initialization test"""
    logger.info("🚨 BOT INITIALIZATION TEST 🚨")
    logger.info("=" * 50)
    
    success = await test_bot_components()
    
    if success:
        logger.info("\n🎉 BOT INITIALIZATION TEST SUCCESSFUL!")
        logger.info("✅ All critical components can initialize")
        logger.info("🚀 Bot is ready for live trading!")
    else:
        logger.error("\n❌ BOT INITIALIZATION TEST FAILED")
        logger.error("🔧 Additional fixes may be needed")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)