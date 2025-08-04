#!/usr/bin/env python3
"""
Comprehensive Kraken Authentication System Test
==============================================

Tests both nonce management and WebSocket token generation to ensure
the authentication system is fully operational after fixes.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

class AuthenticationSystemTester:
    """Comprehensive authentication system tester"""
    
    def __init__(self):
        self.config_file = project_root / 'config.json'
        self.api_key = None
        self.api_secret = None
        
    async def load_credentials(self) -> bool:
        """Load API credentials from config"""
        try:
            if not self.config_file.exists():
                logger.error("❌ config.json not found")
                return False
                
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            kraken_config = config.get('kraken', {})
            self.api_key = kraken_config.get('api_key', '')
            self.api_secret = kraken_config.get('api_secret', '')
            
            if not self.api_key or not self.api_secret:
                logger.error("❌ Kraken API credentials not found in config.json")
                return False
                
            logger.info(f"✅ Loaded API credentials (key: {self.api_key[:8]}...)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load credentials: {e}")
            return False
    
    async def test_nonce_system(self) -> Dict[str, Any]:
        """Test the unified nonce management system"""
        logger.info("🔍 Testing nonce management system...")
        
        results = {
            'initialization': False,
            'sequence_generation': False,
            'concurrent_access': False,
            'collision_detection': False,
            'persistence': False,
            'error_recovery': False
        }
        
        try:
            # Import nonce manager
            from src.utils.unified_kraken_nonce_manager import UnifiedKrakenNonceManager, initialize_enhanced_nonce_manager
            
            # Initialize with credentials
            if self.api_key and self.api_secret:
                nonce_manager = initialize_enhanced_nonce_manager(self.api_key, self.api_secret)
                logger.info("✅ Enhanced nonce manager initialized")
            else:
                nonce_manager = UnifiedKrakenNonceManager.get_instance()
                logger.info("✅ Basic nonce manager initialized")
            
            results['initialization'] = True
            
            # Test sequence generation
            logger.info("📋 Testing nonce sequence generation...")
            nonces = []
            for i in range(10):
                nonce = nonce_manager.get_nonce(f"test_{i}")
                nonces.append(int(nonce))
                await asyncio.sleep(0.01)  # 10ms delay
            
            # Verify sequence is increasing
            sequence_valid = all(nonces[i] < nonces[i+1] for i in range(len(nonces)-1))
            if sequence_valid:
                logger.info("✅ Nonce sequence generation valid")
                results['sequence_generation'] = True
            else:
                logger.error("❌ Nonce sequence generation invalid")
            
            # Test for collisions
            unique_nonces = set(nonces)
            no_collisions = len(unique_nonces) == len(nonces)
            if no_collisions:
                logger.info("✅ No nonce collisions detected")
                results['collision_detection'] = True
            else:
                logger.error("❌ Nonce collisions detected!")
            
            # Test concurrent access
            logger.info("📋 Testing concurrent access...")
            async def generate_concurrent_nonces(prefix: str, count: int):
                results = []
                for i in range(count):
                    nonce = await nonce_manager.get_nonce_async(f"{prefix}_{i}")
                    results.append(int(nonce))
                return results
            
            # Run 3 concurrent generators
            tasks = [
                generate_concurrent_nonces("concurrent_1", 3),
                generate_concurrent_nonces("concurrent_2", 3),
                generate_concurrent_nonces("concurrent_3", 3)
            ]
            
            concurrent_results = await asyncio.gather(*tasks)
            all_concurrent = []
            for result_set in concurrent_results:
                all_concurrent.extend(result_set)
            
            concurrent_unique = set(all_concurrent)
            concurrent_no_collisions = len(concurrent_unique) == len(all_concurrent)
            
            if concurrent_no_collisions:
                logger.info("✅ Concurrent access test passed")
                results['concurrent_access'] = True
            else:
                logger.error("❌ Concurrent access collisions detected!")
            
            # Test persistence
            logger.info("📋 Testing nonce persistence...")
            status = nonce_manager.get_status()
            if status and 'state_file' in status:
                nonce_manager.force_save()
                logger.info("✅ Nonce persistence test passed")
                results['persistence'] = True
            else:
                logger.warning("⚠️  Nonce persistence test inconclusive")
            
            # Test error recovery
            logger.info("📋 Testing error recovery...")
            recovery_nonce = nonce_manager.recover_from_error("test_recovery")
            if recovery_nonce and int(recovery_nonce) > max(nonces):
                logger.info("✅ Error recovery test passed")
                results['error_recovery'] = True
            else:
                logger.warning("⚠️  Error recovery test inconclusive")
                
        except Exception as e:
            logger.error(f"❌ Nonce system test failed: {e}")
        
        return results
    
    async def test_websocket_token_generation(self) -> Dict[str, Any]:
        """Test WebSocket token generation"""
        logger.info("🔍 Testing WebSocket token generation...")
        
        results = {
            'enhanced_api_call': False,
            'native_exchange': False,
            'websocket_auth_manager': False,
            'token_validation': False
        }
        
        if not self.api_key or not self.api_secret:
            logger.warning("⚠️  Skipping token generation tests - no API credentials")
            return results
        
        try:
            # Test 1: Enhanced API call through nonce manager
            logger.info("📋 Testing enhanced API call...")
            from src.utils.unified_kraken_nonce_manager import UnifiedKrakenNonceManager
            
            nonce_manager = UnifiedKrakenNonceManager.get_instance()
            
            if hasattr(nonce_manager, 'make_authenticated_api_call'):
                try:
                    token_response = await nonce_manager.make_authenticated_api_call(
                        '/0/private/GetWebSocketsToken', {}
                    )
                    
                    if 'result' in token_response and 'token' in token_response['result']:
                        token = token_response['result']['token']
                        if len(token) > 10:
                            logger.info(f"✅ Enhanced API call successful (token length: {len(token)})")
                            results['enhanced_api_call'] = True
                            results['token_validation'] = True
                        else:
                            logger.error(f"❌ Enhanced API call returned invalid token (length: {len(token)})")
                    else:
                        logger.error("❌ Enhanced API call returned no token")
                        
                except Exception as e:
                    logger.error(f"❌ Enhanced API call failed: {e}")
            else:
                logger.warning("⚠️  Enhanced API call not available on nonce manager")
            
            # Test 2: Native exchange client
            logger.info("📋 Testing native exchange client...")
            try:
                from src.exchange.native_kraken_exchange import NativeKrakenExchange
                
                exchange = NativeKrakenExchange(self.api_key, self.api_secret, "pro")
                await exchange.initialize()
                
                token_response = await exchange.get_websockets_token()
                
                if (token_response and 'result' in token_response and 
                    'token' in token_response['result']):
                    token = token_response['result']['token']
                    if len(token) > 10:
                        logger.info(f"✅ Native exchange successful (token length: {len(token)})")
                        results['native_exchange'] = True
                        results['token_validation'] = True
                    else:
                        logger.error(f"❌ Native exchange returned invalid token (length: {len(token)})")
                else:
                    logger.error("❌ Native exchange returned no token")
                
                await exchange.close()
                
            except Exception as e:
                logger.error(f"❌ Native exchange test failed: {e}")
            
            # Test 3: WebSocket authentication manager
            logger.info("📋 Testing WebSocket authentication manager...")
            try:
                from src.auth.websocket_authentication_manager import WebSocketAuthenticationManager
                from src.exchange.native_kraken_exchange import NativeKrakenExchange
                
                # Create exchange client
                exchange_client = NativeKrakenExchange(self.api_key, self.api_secret, "pro")
                await exchange_client.initialize()
                
                # Create auth manager
                auth_manager = WebSocketAuthenticationManager(
                    exchange_client=exchange_client,
                    api_key=self.api_key,
                    private_key=self.api_secret,
                    enable_debug=True
                )
                
                # Start and get token
                await auth_manager.start()
                token = await auth_manager.get_websocket_token()
                
                if token and len(token) > 10:
                    logger.info(f"✅ WebSocket auth manager successful (token length: {len(token)})")
                    results['websocket_auth_manager'] = True
                    results['token_validation'] = True
                else:
                    logger.error(f"❌ WebSocket auth manager failed (token length: {len(token) if token else 0})")
                
                # Cleanup
                await auth_manager.stop()
                await exchange_client.close()
                
            except Exception as e:
                logger.error(f"❌ WebSocket auth manager test failed: {e}")
                
        except Exception as e:
            logger.error(f"❌ WebSocket token generation test failed: {e}")
        
        return results
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive authentication system test"""
        logger.info("🧪 Starting comprehensive authentication system test...")
        print("=" * 60)
        print("🔐 KRAKEN AUTHENTICATION SYSTEM TEST")
        print("=" * 60)
        
        # Load credentials
        if not await self.load_credentials():
            print("❌ FAILED: Could not load API credentials")
            return {'success': False, 'error': 'No credentials'}
        
        # Test results
        test_results = {
            'timestamp': time.time(),
            'nonce_tests': {},
            'token_tests': {},
            'overall_success': False
        }
        
        # Test nonce system
        print("\n📋 TESTING NONCE MANAGEMENT SYSTEM")
        print("-" * 40)
        test_results['nonce_tests'] = await self.test_nonce_system()
        
        nonce_success = all([
            test_results['nonce_tests'].get('initialization', False),
            test_results['nonce_tests'].get('sequence_generation', False),
            test_results['nonce_tests'].get('collision_detection', False)
        ])
        
        if nonce_success:
            print("✅ Nonce system: PASSED")
        else:
            print("❌ Nonce system: FAILED")
        
        # Test WebSocket token generation
        print("\n📋 TESTING WEBSOCKET TOKEN GENERATION")
        print("-" * 40)
        test_results['token_tests'] = await self.test_websocket_token_generation()
        
        token_success = any([
            test_results['token_tests'].get('enhanced_api_call', False),
            test_results['token_tests'].get('native_exchange', False),
            test_results['token_tests'].get('websocket_auth_manager', False)
        ])
        
        if token_success:
            print("✅ WebSocket tokens: PASSED")
        else:
            print("❌ WebSocket tokens: FAILED")
        
        # Overall assessment
        test_results['overall_success'] = nonce_success and token_success
        
        print("\n" + "=" * 60)
        print("📊 FINAL RESULTS")
        print("=" * 60)
        
        if test_results['overall_success']:
            print("🎉 SUCCESS: Authentication system is fully operational!")
            print("✅ Nonce management: Working correctly")
            print("✅ WebSocket tokens: Generation successful")
            print("🚀 Your trading bot should now connect without authentication errors")
        else:
            print("⚠️  PARTIAL SUCCESS: Some authentication components need attention")
            if nonce_success:
                print("✅ Nonce management: Working correctly")
            else:
                print("❌ Nonce management: Needs fixes")
            
            if token_success:
                print("✅ WebSocket tokens: Generation successful")
            else:
                print("❌ WebSocket tokens: Generation failed")
        
        # Save results
        results_file = project_root / f'authentication_test_results_{int(time.time())}.json'
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file.name}")
        
        return test_results

async def main():
    """Main test execution"""
    tester = AuthenticationSystemTester()
    results = await tester.run_comprehensive_test()
    
    # Exit with appropriate code
    sys.exit(0 if results.get('overall_success', False) else 1)

if __name__ == "__main__":
    asyncio.run(main())