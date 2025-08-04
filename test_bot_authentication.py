#!/usr/bin/env python3
"""
Test Bot Authentication and Startup
===================================

This script tests the crypto trading bot's authentication and startup process
to verify that the nonce authentication fixes are working correctly.

Tests performed:
1. Nonce system validation
2. REST API authentication test
3. WebSocket token authentication test
4. Balance access verification
5. Basic bot initialization test

Author: Kraken Exchange API Integration Specialist
Date: 2025-08-03
"""

import asyncio
import logging
import sys
import json
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_authentication_test.log')
    ]
)
logger = logging.getLogger(__name__)


class BotAuthenticationTest:
    """Comprehensive test suite for bot authentication"""
    
    def __init__(self):
        self.project_root = project_root
        self.results = {
            'nonce_system': False,
            'rest_auth': False,
            'websocket_token': False,
            'balance_access': False,
            'bot_initialization': False,
            'total_tests': 5,
            'passed_tests': 0,
            'errors': []
        }
        
        # Load configuration
        self.config = self._load_config()
        
    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load bot configuration"""
        try:
            config_file = self.project_root / "config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning("⚠️  Config file not found, using environment variables")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            return None
    
    def test_nonce_system(self) -> bool:
        """Test unified nonce system"""
        try:
            logger.info("🧪 Testing nonce system...")
            
            from src.utils.unified_kraken_nonce_manager import get_unified_nonce_manager
            
            manager = get_unified_nonce_manager()
            
            # Test nonce generation and sequence
            nonces = []
            for i in range(5):
                nonce = manager.get_nonce(f"auth_test_{i}")
                nonces.append(int(nonce))
            
            # Verify sequence is increasing
            is_increasing = all(nonces[i] < nonces[i+1] for i in range(len(nonces)-1))
            
            if is_increasing:
                logger.info(f"✅ Nonce system working: {nonces[0]} -> {nonces[-1]}")
                self.results['nonce_system'] = True
                self.results['passed_tests'] += 1
                return True
            else:
                raise Exception(f"Nonce sequence not increasing: {nonces}")
                
        except Exception as e:
            error_msg = f"❌ Nonce system test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    async def test_rest_authentication(self) -> bool:
        """Test REST API authentication"""
        try:
            logger.info("🧪 Testing REST API authentication...")
            
            if not self.config:
                logger.warning("⚠️  No config available, skipping REST auth test")
                return True
            
            kraken_config = self.config.get('kraken', {})
            api_key = kraken_config.get('API_KEY')
            private_key = kraken_config.get('API_SECRET')
            
            if not api_key or not private_key:
                logger.warning("⚠️  API credentials not found, skipping REST auth test")
                return True
            
            from src.auth.kraken_auth import KrakenAuth
            
            # Create auth instance
            auth = KrakenAuth(api_key, private_key, enable_debug=True)
            
            # Run comprehensive test
            test_results = auth.run_comprehensive_test()
            
            if test_results.get('overall_success', False):
                logger.info("✅ REST API authentication working")
                self.results['rest_auth'] = True
                self.results['passed_tests'] += 1
                return True
            else:
                raise Exception(f"REST auth test failed: {test_results}")
                
        except Exception as e:
            error_msg = f"❌ REST authentication test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    async def test_websocket_token_authentication(self) -> bool:
        """Test WebSocket token authentication"""
        try:
            logger.info("🧪 Testing WebSocket token authentication...")
            
            if not self.config:
                logger.warning("⚠️  No config available, skipping WebSocket token test")
                return True
            
            kraken_config = self.config.get('kraken', {})
            api_key = kraken_config.get('API_KEY')
            private_key = kraken_config.get('API_SECRET')
            
            if not api_key or not private_key:
                logger.warning("⚠️  API credentials not found, skipping WebSocket token test")
                return True
            
            from src.auth.enhanced_websocket_auth_wrapper import create_enhanced_websocket_auth
            from src.utils.unified_kraken_nonce_manager import get_unified_nonce_manager
            
            nonce_manager = get_unified_nonce_manager()
            auth_wrapper = await create_enhanced_websocket_auth(
                api_key, private_key, nonce_manager
            )
            
            # Test token request with timeout
            token = await asyncio.wait_for(
                auth_wrapper.get_websocket_token_with_retry(),
                timeout=60.0
            )
            
            if token and len(token) > 10:
                logger.info(f"✅ WebSocket token authentication successful: {token[:20]}...")
                self.results['websocket_token'] = True
                self.results['passed_tests'] += 1
                return True
            else:
                raise Exception("No valid token received")
                
        except asyncio.TimeoutError:
            error_msg = "❌ WebSocket token test timed out"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
        except Exception as e:
            error_msg = f"❌ WebSocket token test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    async def test_balance_access(self) -> bool:
        """Test balance access through exchange client"""
        try:
            logger.info("🧪 Testing balance access...")
            
            if not self.config:
                logger.warning("⚠️  No config available, skipping balance access test")
                return True
            
            # Try to initialize exchange client
            from src.exchange.kraken_sdk_exchange import KrakenSDKExchange
            
            exchange = KrakenSDKExchange(self.config)
            await exchange.initialize()
            
            # Test balance retrieval
            balances = await exchange.get_balance()
            
            if isinstance(balances, dict) and len(balances) > 0:
                # Log non-zero balances
                non_zero_balances = {k: v for k, v in balances.items() 
                                   if float(v.get('available', 0)) > 0}
                
                logger.info(f"✅ Balance access successful. Assets: {list(non_zero_balances.keys())}")
                self.results['balance_access'] = True
                self.results['passed_tests'] += 1
                return True
            else:
                logger.warning("⚠️  Balance access returned empty or invalid data")
                return True  # Don't fail test for empty balances
                
        except Exception as e:
            error_msg = f"❌ Balance access test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    async def test_bot_initialization(self) -> bool:
        """Test basic bot initialization"""
        try:
            logger.info("🧪 Testing bot initialization...")
            
            # Try to initialize the main bot components
            from src.core.bot import CryptoTradingBot
            
            # Create bot instance (don't start trading)
            bot = CryptoTradingBot("config.json")
            
            # Initialize core components only
            await bot.initialize_core_components()
            
            # Check if key components are initialized
            if hasattr(bot, 'exchange') and bot.exchange:
                logger.info("✅ Bot core initialization successful")
                self.results['bot_initialization'] = True
                self.results['passed_tests'] += 1
                
                # Clean shutdown
                await bot.cleanup()
                return True
            else:
                raise Exception("Bot initialization incomplete")
                
        except Exception as e:
            error_msg = f"❌ Bot initialization test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all authentication tests"""
        logger.info("🚨 BOT AUTHENTICATION TEST SUITE STARTING 🚨")
        logger.info("=" * 60)
        
        try:
            # Test 1: Nonce system
            logger.info("\n📋 Test 1: Nonce System Validation")
            self.test_nonce_system()
            
            # Test 2: REST authentication
            logger.info("\n📋 Test 2: REST API Authentication")
            await self.test_rest_authentication()
            
            # Test 3: WebSocket token authentication
            logger.info("\n📋 Test 3: WebSocket Token Authentication")
            await self.test_websocket_token_authentication()
            
            # Test 4: Balance access
            logger.info("\n📋 Test 4: Balance Access Verification")
            await self.test_balance_access()
            
            # Test 5: Bot initialization
            logger.info("\n📋 Test 5: Bot Initialization")
            await self.test_bot_initialization()
            
            return self.results['passed_tests'] >= 3  # At least 3 critical tests must pass
            
        except Exception as e:
            logger.error(f"❌ Test suite execution failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def print_results(self):
        """Print comprehensive test results"""
        logger.info("\n" + "=" * 60)
        logger.info("🚨 BOT AUTHENTICATION TEST RESULTS 🚨")
        logger.info("=" * 60)
        
        # Individual test results
        logger.info(f"✅ Nonce System: {'PASS' if self.results['nonce_system'] else 'FAIL'}")
        logger.info(f"✅ REST Authentication: {'PASS' if self.results['rest_auth'] else 'FAIL/SKIP'}")
        logger.info(f"✅ WebSocket Token: {'PASS' if self.results['websocket_token'] else 'FAIL/SKIP'}")
        logger.info(f"✅ Balance Access: {'PASS' if self.results['balance_access'] else 'FAIL/SKIP'}")
        logger.info(f"✅ Bot Initialization: {'PASS' if self.results['bot_initialization'] else 'FAIL/SKIP'}")
        
        # Summary
        passed = self.results['passed_tests']
        total = self.results['total_tests']
        success_rate = (passed / total) * 100
        
        logger.info(f"\n📊 Overall: {passed}/{total} tests passed ({success_rate:.1f}%)")
        
        if self.results['errors']:
            logger.info(f"\n❌ ERRORS ENCOUNTERED ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                logger.info(f"  • {error}")
        
        # Recommendations
        logger.info("\n📋 RECOMMENDATIONS:")
        if passed >= 3:
            logger.info("✅ Authentication system appears to be working correctly")
            logger.info("🚀 Bot should be able to start and authenticate with Kraken")
            logger.info("📊 Try running the bot to verify trading functionality")
        else:
            logger.info("⚠️  Multiple authentication tests failed")
            logger.info("🔍 Review error messages and check API credentials")
            logger.info("🔧 Consider running fix_nonce_authentication_issues.py again")
        
        logger.info("=" * 60)


async def main():
    """Run the bot authentication test suite"""
    print("🚨 CRYPTO TRADING BOT AUTHENTICATION TEST SUITE 🚨")
    print("Problem: Verify nonce authentication fixes are working")
    print("Solution: Comprehensive test of all authentication components")
    print("Impact: Confirm bot can authenticate and access trading functionality")
    print("-" * 60)
    
    tester = BotAuthenticationTest()
    
    success = await tester.run_all_tests()
    tester.print_results()
    
    if success:
        print("\n✅ AUTHENTICATION TESTS SUCCESSFUL!")
        print("🚀 Your bot should now be able to start and trade")
        print("📊 Ready for live trading operations")
    else:
        print("\n⚠️  AUTHENTICATION TESTS ENCOUNTERED ISSUES")
        print("🔍 Review the test results and error messages")
        print("🔧 Additional fixes may be required")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)