#!/usr/bin/env python3
"""
Fixed Trading Bot Launcher
==========================

Simple, reliable launcher for the crypto trading bot with comprehensive
error handling and diagnostics to identify and resolve initialization issues.
"""

import asyncio
import logging
import sys
import traceback
from pathlib import Path
import os
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import configuration and utilities
from src.utils.custom_logging import configure_logging
from src.config.config import Config

# Configure logging first
logger = configure_logging()

async def test_basic_imports():
    """Test if all basic imports work"""
    logger.info("Testing basic imports...")
    
    try:
        # Test core imports
        from src.auth.credential_manager import CredentialManager
        from src.auth.auth_service import AuthService
        logger.info("✓ Authentication modules imported successfully")
        
        # Test WebSocket imports
        from src.websocket.kraken_websocket_v2 import KrakenWebSocketV2
        from src.websocket.kraken_v2_message_handler import KrakenV2MessageHandler
        logger.info("✓ WebSocket V2 modules imported successfully")
        
        # Test API imports
        from src.api.kraken_rest_client import KrakenRestClient
        logger.info("✓ REST API modules imported successfully")
        
        # Test rate limiting
        from src.rate_limiting.kraken_rate_limiter import KrakenRateLimiter2025
        logger.info("✓ Rate limiting modules imported successfully")
        
        # Test balance management
        from src.balance.balance_manager import BalanceManager
        logger.info("✓ Balance management modules imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Import error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_credential_setup():
    """Test credential manager setup"""
    logger.info("Testing credential setup...")
    
    try:
        from src.auth.credential_manager import CredentialManager
        
        cred_manager = CredentialManager()
        api_key, private_key = cred_manager.get_kraken_credentials()
        
        if api_key and private_key:
            logger.info("✓ API credentials found and loaded")
            # Validate format without logging sensitive data
            if len(api_key) > 10 and len(private_key) > 10:
                logger.info("✓ Credentials appear to be valid format")
                return True
            else:
                logger.error("✗ Credentials appear to be invalid format")
                return False
        else:
            logger.error("✗ No API credentials found")
            logger.error("Please set KRAKEN_API_KEY and KRAKEN_PRIVATE_KEY environment variables")
            return False
            
    except Exception as e:
        logger.error(f"Credential setup error: {e}")
        return False

async def test_auth_service():
    """Test authentication service initialization"""
    logger.info("Testing authentication service...")
    
    try:
        from src.auth.auth_service import AuthService
        
        auth_service = AuthService()
        success = await auth_service.initialize()
        
        if success:
            logger.info("✓ Authentication service initialized successfully")
            
            # Test auth header generation
            test_success = await auth_service.test_authentication()
            if test_success:
                logger.info("✓ Authentication header generation test passed")
                return True
            else:
                logger.error("✗ Authentication header generation test failed")
                return False
        else:
            logger.error("✗ Authentication service initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"Authentication service error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_websocket_creation():
    """Test WebSocket V2 creation"""
    logger.info("Testing WebSocket V2 creation...")
    
    try:
        from src.websocket.kraken_websocket_v2 import KrakenWebSocketV2
        from src.auth.credential_manager import CredentialManager
        
        # Get credentials
        cred_manager = CredentialManager()
        api_key, private_key = cred_manager.get_kraken_credentials()
        
        # Create WebSocket client
        ws_client = KrakenWebSocketV2(api_key=api_key, api_secret=private_key)
        logger.info("✓ WebSocket V2 client created successfully")
        
        # Test configuration
        if ws_client.config and ws_client.message_handler:
            logger.info("✓ WebSocket V2 configuration and message handler ready")
            return True
        else:
            logger.error("✗ WebSocket V2 configuration or message handler missing")
            return False
            
    except Exception as e:
        logger.error(f"WebSocket creation error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_rest_api():
    """Test REST API client creation"""
    logger.info("Testing REST API client...")
    
    try:
        from src.api.kraken_rest_client import KrakenRestClient
        
        # Create REST client
        rest_client = KrakenRestClient()
        await rest_client.initialize()
        logger.info("✓ REST API client created and initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"REST API client error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_full_bot_creation():
    """Test creating the full orchestrated bot"""
    logger.info("Testing full bot creation...")
    
    try:
        from src.orchestrator.system_orchestrator import SystemOrchestrator
        from src.orchestrator.bot_integration import OrchestratedTradingBot
        
        # Create orchestrated bot
        bot = OrchestratedTradingBot("config.json")
        logger.info("✓ Orchestrated trading bot created")
        
        # Test initialization
        success = await bot.initialize()
        if success:
            logger.info("✓ Bot initialization successful!")
            
            # Get status
            status = bot.get_status()
            logger.info(f"Bot status: {status}")
            
            # Cleanup
            await bot.stop()
            logger.info("✓ Bot stopped cleanly")
            
            return True
        else:
            logger.error("✗ Bot initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"Full bot creation error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def run_comprehensive_diagnosis():
    """Run comprehensive diagnosis of the trading bot"""
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE TRADING BOT DIAGNOSIS")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().isoformat()}")
    
    results = {}
    
    # Test 1: Basic imports
    logger.info("\n" + "=" * 30)
    logger.info("TEST 1: Basic Imports")
    logger.info("=" * 30)
    results['imports'] = await test_basic_imports()
    
    if not results['imports']:
        logger.error("Basic imports failed - cannot continue")
        return False
    
    # Test 2: Credential setup
    logger.info("\n" + "=" * 30)
    logger.info("TEST 2: Credential Setup")
    logger.info("=" * 30)
    results['credentials'] = await test_credential_setup()
    
    if not results['credentials']:
        logger.error("Credential setup failed - cannot continue")
        return False
    
    # Test 3: Authentication service
    logger.info("\n" + "=" * 30)
    logger.info("TEST 3: Authentication Service")
    logger.info("=" * 30)
    results['auth_service'] = await test_auth_service()
    
    # Test 4: WebSocket creation
    logger.info("\n" + "=" * 30)
    logger.info("TEST 4: WebSocket V2 Creation")
    logger.info("=" * 30)
    results['websocket'] = await test_websocket_creation()
    
    # Test 5: REST API client
    logger.info("\n" + "=" * 30)
    logger.info("TEST 5: REST API Client")
    logger.info("=" * 30)
    results['rest_api'] = await test_rest_api()
    
    # Test 6: Full bot creation (if previous tests pass)
    logger.info("\n" + "=" * 30)
    logger.info("TEST 6: Full Bot Creation")
    logger.info("=" * 30)
    
    if all([results['imports'], results['credentials'], results['auth_service']]):
        results['full_bot'] = await test_full_bot_creation()
    else:
        logger.warning("Skipping full bot test due to previous failures")
        results['full_bot'] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("DIAGNOSIS SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name.upper():<20}: {status}")
    
    overall_success = all(results.values())
    
    if overall_success:
        logger.info("\n🎉 ALL TESTS PASSED - BOT IS READY TO LAUNCH!")
        logger.info("\nYou can now run the bot with:")
        logger.info("python main_orchestrated.py")
        logger.info("or")
        logger.info("python main_orchestrated.py --dashboard")
    else:
        logger.error("\n❌ SOME TESTS FAILED - PLEASE FIX ISSUES BEFORE LAUNCHING")
        
        # Provide specific guidance
        if not results['credentials']:
            logger.error("\n📋 TO FIX CREDENTIALS:")
            logger.error("Set environment variables:")
            logger.error("export KRAKEN_API_KEY='your_api_key'")
            logger.error("export KRAKEN_PRIVATE_KEY='your_private_key'")
            
        if not results['auth_service']:
            logger.error("\n📋 TO FIX AUTHENTICATION:")
            logger.error("Check API key permissions and format")
            
        if not results['full_bot']:
            logger.error("\n📋 TO FIX BOT INITIALIZATION:")
            logger.error("Check config.json file and all dependencies")
    
    return overall_success

async def main():
    """Main function"""
    try:
        success = await run_comprehensive_diagnosis()
        
        if success:
            logger.info("\n" + "=" * 60)
            logger.info("LAUNCHING TRADING BOT")
            logger.info("=" * 60)
            
            # Import and run the orchestrated bot
            from main_orchestrated import OrchestratedMain
            
            app = OrchestratedMain("config.json", enable_dashboard=False, websocket_first_mode=True)
            exit_code = await app.run()
            
            return exit_code
        else:
            logger.error("Bot diagnosis failed - cannot launch")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)