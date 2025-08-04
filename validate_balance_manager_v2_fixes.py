#!/usr/bin/env python3
"""
Balance Manager V2 WebSocket Connectivity Validation Script
==========================================================

This script validates that the Balance Manager V2 WebSocket connectivity fixes
are working properly and can successfully initialize and stream balance data.

Features:
- WebSocket connection validation  
- Authentication token validation
- Balance subscription testing
- Fallback mechanism validation
- Comprehensive error reporting
"""

import asyncio
import logging
import os
import sys
import time 
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / 'balance_manager_v2_validation.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_websocket_readiness():
    """Test WebSocket manager readiness for Balance Manager V2"""
    try:
        logger.info("=" * 60)
        logger.info("TESTING WEBSOCKET READINESS FOR BALANCE MANAGER V2")
        logger.info("=" * 60)
        
        # Import WebSocket manager
        from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        from src.config import load_config
        
        # Load configuration
        config = load_config()
        
        # Get API credentials from environment
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
        api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
        tier = os.getenv('KRAKEN_TIER', 'starter')
        
        if not api_key or not api_secret:
            logger.error("Missing Kraken API credentials. Please set KRAKEN_API_KEY and KRAKEN_API_SECRET in .env file")
            return False
        
        # Create exchange instance
        logger.info("Creating exchange instance...")
        exchange = NativeKrakenExchange(
            api_key=api_key,
            api_secret=api_secret,
            tier=tier
        )
        await exchange.initialize()
        
        # Create WebSocket manager
        logger.info("Creating WebSocket manager...")
        symbols = ['SHIB/USDT', 'MANA/USDT', 'MATIC/USDT']
        ws_manager = KrakenProWebSocketManager(
            exchange_client=exchange,
            symbols=symbols
        )
        
        # Test connection
        logger.info("Testing WebSocket connection...")
        connected = await ws_manager.connect()
        if not connected:
            logger.error("WebSocket connection failed")
            return False
        
        logger.info("WebSocket connected successfully")
        
        # Test readiness validation
        logger.info("Validating WebSocket readiness...")
        readiness = ws_manager.validate_connection_readiness()
        
        logger.info(f"Connection healthy: {readiness['connection_healthy']}")
        logger.info(f"Authentication ready: {readiness['authentication_ready']}")  
        logger.info(f"Bot available: {readiness['bot_available']}")
        logger.info(f"Ready for Balance Manager: {readiness['ready_for_balance_manager']}")
        
        if readiness['issues']:
            logger.warning(f"Issues found: {readiness['issues']}")
            logger.info(f"Recommendations: {readiness['recommendations']}")
        
        # Test ensuring readiness
        logger.info("Ensuring WebSocket readiness...")
        ensured_ready = await ws_manager.ensure_ready_for_balance_manager()
        logger.info(f"WebSocket ensured ready: {ensured_ready}")
        
        # Final readiness check
        final_readiness = ws_manager.validate_connection_readiness()
        logger.info(f"Final readiness status: {final_readiness['ready_for_balance_manager']}")
        
        # Get authentication status
        auth_status = ws_manager.get_authentication_status()
        logger.info("Authentication Status:")
        logger.info(f"  Token available: {auth_status['legacy_auth_token_available']}")
        logger.info(f"  Enhanced auth available: {auth_status['enhanced_auth_manager_available']}")
        
        # Cleanup
        await ws_manager.disconnect()
        logger.info("WebSocket disconnected")
        
        return final_readiness['ready_for_balance_manager']
        
    except Exception as e:
        logger.error(f"WebSocket readiness test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_balance_manager_v2_initialization():
    """Test Balance Manager V2 initialization with WebSocket integration"""
    try:
        logger.info("=" * 60)
        logger.info("TESTING BALANCE MANAGER V2 INITIALIZATION")
        logger.info("=" * 60)
        
        # Import required components
        from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        from src.balance.balance_manager_v2 import create_balance_manager_v2, BalanceManagerV2Config
        from src.config import load_config
        
        # Load configuration
        config = load_config()
        
        # Get API credentials from environment
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
        api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
        tier = os.getenv('KRAKEN_TIER', 'starter')
        
        if not api_key or not api_secret:
            logger.error("Missing Kraken API credentials. Please set KRAKEN_API_KEY and KRAKEN_API_SECRET in .env file")
            return False
        
        # Create exchange instance
        logger.info("Creating exchange instance...")
        exchange = NativeKrakenExchange(
            api_key=api_key,
            api_secret=api_secret,
            tier=tier
        )
        await exchange.initialize()
        
        # Create WebSocket manager  
        logger.info("Creating WebSocket manager...")
        symbols = ['SHIB/USDT', 'MANA/USDT', 'MATIC/USDT']
        ws_manager = KrakenProWebSocketManager(
            exchange_client=exchange,
            symbols=symbols
        )
        
        # Connect WebSocket
        logger.info("Connecting WebSocket...")
        connected = await ws_manager.connect()
        if not connected:
            logger.error("WebSocket connection failed - testing fallback mode")
            ws_manager = None  # Test with None to trigger fallback
        else:
            logger.info("WebSocket connected successfully")
            
            # Ensure readiness
            await ws_manager.ensure_ready_for_balance_manager()
        
        # Configure Balance Manager V2
        logger.info("Configuring Balance Manager V2...")
        balance_config = BalanceManagerV2Config(
            websocket_primary_ratio=0.9 if ws_manager else 0.0,
            rest_fallback_ratio=0.1 if ws_manager else 1.0,
            enable_balance_validation=True,
            enable_balance_aggregation=True,
            enable_circuit_breaker=True,
            websocket_token_refresh_interval=720.0,
            websocket_connection_timeout=10.0
        )
        
        # Create Balance Manager V2
        logger.info("Creating Balance Manager V2...")
        start_time = time.time()
        
        balance_manager = await create_balance_manager_v2(
            websocket_client=ws_manager,
            exchange_client=exchange,
            config=balance_config
        )
        
        init_time = time.time() - start_time
        logger.info(f"Balance Manager V2 created successfully in {init_time:.2f}s")
        
        # Test balance retrieval
        logger.info("Testing balance retrieval...")
        
        # Test USDT balance
        usdt_balance = await balance_manager.get_balance('USDT')
        if usdt_balance:
            logger.info(f"USDT balance retrieved: {usdt_balance.get('free', 0):.8f}")
        else:
            logger.warning("USDT balance not found")
        
        # Test all balances
        all_balances = await balance_manager.get_all_balances()
        logger.info(f"Retrieved {len(all_balances)} total balances")
        
        # Test USDT aggregation
        usdt_total = await balance_manager.get_usdt_total()
        logger.info(f"Total USDT across variants: {usdt_total:.8f}")
        
        # Get status
        status = balance_manager.get_status()
        logger.info("Balance Manager V2 Status:")
        logger.info(f"  Initialized: {status['initialized']}")
        logger.info(f"  Running: {status['running']}")
        logger.info(f"  Balance count: {status['balance_count']}")
        logger.info(f"  Success rate: {status['success_rate_percent']:.1f}%")
        logger.info(f"  WebSocket stream available: {'websocket_stream' in status}")
        
        if 'websocket_stream' in status:
            ws_status = status['websocket_stream']
            logger.info(f"  WebSocket state: {ws_status.get('state', 'unknown')}")
            logger.info(f"  WebSocket authenticated: {ws_status.get('authenticated', False)}")
            logger.info(f"  WebSocket subscribed: {ws_status.get('subscribed', False)}")
        
        # Test streaming capabilities (if available)
        if ws_manager and hasattr(balance_manager, 'websocket_stream'):
            logger.info("Testing WebSocket balance streaming...")
            stream_status = balance_manager.websocket_stream.get_status()
            logger.info(f"Stream state: {stream_status['state']}")
            logger.info(f"Balance updates received: {stream_status['statistics']['balance_updates_received']}")
        
        # Cleanup
        logger.info("Shutting down Balance Manager V2...")
        await balance_manager.shutdown()
        
        if ws_manager:
            await ws_manager.disconnect()
        
        logger.info("Balance Manager V2 test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Balance Manager V2 initialization test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_websocket_balance_stream_directly():
    """Test WebSocket Balance Stream component directly"""
    try:
        logger.info("=" * 60)
        logger.info("TESTING WEBSOCKET BALANCE STREAM DIRECTLY")
        logger.info("=" * 60)
        
        # Import required components
        from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        from src.balance.websocket_balance_stream import WebSocketBalanceStream
        from src.config import load_config
        
        # Load configuration
        config = load_config()
        
        # Get API credentials from environment
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
        api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
        tier = os.getenv('KRAKEN_TIER', 'starter')
        
        if not api_key or not api_secret:
            logger.error("Missing Kraken API credentials. Please set KRAKEN_API_KEY and KRAKEN_API_SECRET in .env file")
            return False
        
        # Create exchange instance
        logger.info("Creating exchange instance...")
        exchange = NativeKrakenExchange(
            api_key=api_key,
            api_secret=api_secret,
            tier=tier
        )
        await exchange.initialize()
        
        # Create WebSocket manager
        logger.info("Creating WebSocket manager...")
        symbols = ['SHIB/USDT', 'MANA/USDT']
        ws_manager = KrakenProWebSocketManager(
            exchange_client=exchange,
            symbols=symbols
        )
        
        # Connect WebSocket
        logger.info("Connecting WebSocket...")
        connected = await ws_manager.connect()
        if not connected:
            logger.error("WebSocket connection failed")
            return False
        
        # Create WebSocket balance stream
        logger.info("Creating WebSocket balance stream...")
        balance_stream = WebSocketBalanceStream(
            websocket_client=ws_manager,
            exchange_client=exchange,
            token_refresh_interval=720.0,
            connection_timeout=10.0
        )
        
        # Test stream startup
        logger.info("Starting balance stream...")
        started = await balance_stream.start()
        
        if started:
            logger.info("Balance stream started successfully")
            
            # Get status
            stream_status = balance_stream.get_status()
            logger.info("Balance Stream Status:")
            logger.info(f"  State: {stream_status['state']}")
            logger.info(f"  Running: {stream_status['running']}")
            logger.info(f"  Authenticated: {stream_status['authenticated']}")
            logger.info(f"  Subscribed: {stream_status['subscribed']}")
            logger.info(f"  Balances count: {stream_status['balances_count']}")
            logger.info(f"  WebSocket connected: {stream_status['websocket_connected']}")
            
            # Wait for some data
            logger.info("Waiting for balance data...")
            await asyncio.sleep(5.0)
            
            # Check for balance data
            all_balances = balance_stream.get_all_balances()
            logger.info(f"Received {len(all_balances)} balance entries")
            
            if all_balances:
                for asset, balance in list(all_balances.items())[:5]:  # Show first 5
                    logger.info(f"  {asset}: {balance.get('free', 0):.8f}")
            
            # Test USDT aggregation
            usdt_total = balance_stream.get_usdt_total()
            logger.info(f"Total USDT: {usdt_total:.8f}")
            
            # Stop stream
            logger.info("Stopping balance stream...")
            await balance_stream.stop()
            
        else:
            logger.error("Balance stream failed to start")
            return False
        
        # Cleanup
        await ws_manager.disconnect()
        
        logger.info("WebSocket balance stream test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"WebSocket balance stream test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def run_comprehensive_validation():
    """Run comprehensive validation of all Balance Manager V2 fixes"""
    logger.info("🚀 STARTING COMPREHENSIVE BALANCE MANAGER V2 VALIDATION")
    logger.info("=" * 80)
    
    results = {
        'websocket_readiness': False,
        'balance_manager_initialization': False,
        'websocket_balance_stream': False,
        'overall_success': False
    }
    
    try:
        # Test 1: WebSocket Readiness
        logger.info("\n🔧 TEST 1: WebSocket Readiness")
        results['websocket_readiness'] = await test_websocket_readiness()
        
        # Test 2: Balance Manager V2 Initialization  
        logger.info("\n🔧 TEST 2: Balance Manager V2 Initialization")
        results['balance_manager_initialization'] = await test_balance_manager_v2_initialization()
        
        # Test 3: WebSocket Balance Stream Direct Test
        logger.info("\n🔧 TEST 3: WebSocket Balance Stream Direct")
        results['websocket_balance_stream'] = await test_websocket_balance_stream_directly()
        
        # Overall assessment
        results['overall_success'] = all([
            results['websocket_readiness'],
            results['balance_manager_initialization'],
            results['websocket_balance_stream']
        ])
        
    except Exception as e:
        logger.error(f"Validation suite error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Print results
    logger.info("\n" + "=" * 80)
    logger.info("🏁 VALIDATION RESULTS SUMMARY")
    logger.info("=" * 80)
    
    for test_name, success in results.items():
        status_icon = "✅" if success else "❌"
        logger.info(f"{status_icon} {test_name.replace('_', ' ').title()}: {'PASS' if success else 'FAIL'}")
    
    if results['overall_success']:
        logger.info("\n🎉 ALL TESTS PASSED - Balance Manager V2 fixes are working correctly!")
        logger.info("The WebSocket connectivity issues have been resolved.")
    else:
        logger.error("\n❌ SOME TESTS FAILED - Balance Manager V2 needs additional fixes")
        logger.error("Check the logs above for specific issues and recommendations.")
    
    return results

if __name__ == "__main__":
    # Set up event loop for Windows compatibility
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run validation
    try:
        results = asyncio.run(run_comprehensive_validation())
        exit_code = 0 if results['overall_success'] else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        sys.exit(1)