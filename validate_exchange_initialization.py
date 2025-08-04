#!/usr/bin/env python3
"""
Quick validation script to test NativeKrakenExchange initialization fix
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_exchange_initialization():
    """Test that NativeKrakenExchange can be initialized with correct parameters"""
    try:
        logger.info("🔧 TESTING NATIVE KRAKEN EXCHANGE INITIALIZATION")
        logger.info("=" * 60)
        
        # Import the exchange
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        from src.config import load_config
        
        # Load configuration
        config = load_config()
        logger.info("✅ Configuration loaded successfully")
        
        # Get API credentials from environment
        load_dotenv()
        
        api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
        api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
        tier = os.getenv('KRAKEN_TIER', 'starter')
        
        if not api_key or not api_secret:
            logger.error("❌ Missing Kraken API credentials. Please set KRAKEN_API_KEY and KRAKEN_API_SECRET in .env file")
            return False
        
        logger.info("✅ API credentials found")
        logger.info(f"   API Key length: {len(api_key)} chars")
        logger.info(f"   API Secret length: {len(api_secret)} chars") 
        logger.info(f"   Tier: {tier}")
        
        # Test exchange creation (this was failing before the fix)
        logger.info("Creating NativeKrakenExchange instance...")
        exchange = NativeKrakenExchange(
            api_key=api_key,
            api_secret=api_secret,
            tier=tier
        )
        logger.info("✅ NativeKrakenExchange instance created successfully")
        
        # Test initialization
        logger.info("Initializing exchange connection...")
        initialized = await exchange.initialize()
        
        if initialized:
            logger.info("✅ Exchange initialized successfully")
            
            # Test basic health check
            health = exchange.get_health_status()
            logger.info(f"   Healthy: {health['healthy']}")
            logger.info(f"   Consecutive failures: {health['consecutive_failures']}")
            logger.info(f"   Rate limiter status: {health['rate_limiter_status'].get('tier', 'unknown')}")
            
            # Test basic market data (non-authenticated)
            logger.info("Testing market data access...")
            try:
                ticker = await exchange.fetch_ticker('BTC/USDT')
                if ticker:
                    logger.info(f"✅ BTC/USDT ticker: ${ticker.get('last', 'N/A')}")
                else:
                    logger.warning("⚠️  Ticker data empty")
            except Exception as ticker_error:
                logger.warning(f"⚠️  Ticker test failed: {ticker_error}")
            
        else:
            logger.error("❌ Exchange initialization failed")
            return False
        
        # Cleanup
        await exchange.close()
        logger.info("✅ Exchange connection closed")
        
        logger.info("\n🎉 ALL TESTS PASSED - NativeKrakenExchange initialization fix is working!")
        return True
        
    except TypeError as e:
        if "unexpected keyword argument 'config'" in str(e):
            logger.error("❌ CRITICAL: The old config parameter bug is still present!")
            logger.error(f"   Error: {e}")
            return False
        else:
            logger.error(f"❌ TypeError: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    # Set up event loop for Windows compatibility
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run validation
    try:
        success = asyncio.run(test_exchange_initialization())
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        sys.exit(1)