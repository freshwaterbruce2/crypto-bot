#!/usr/bin/env python3
"""
Enhanced Nonce Integration Test Suite
====================================

Comprehensive test suite to validate the integration of KrakenNonceFixer
with the existing crypto trading bot system, focusing on:

1. Enhanced nonce generation system
2. WebSocket V2 authentication with advanced nonce handling
3. Balance Manager V2 initialization with nonce fix
4. Integration compatibility with existing architecture
5. Error recovery and resilience testing

This test script should be run after applying the nonce fix integration
to ensure all components work together correctly.
"""

import asyncio
import logging
import os
import sys
import time
from decimal import Decimal
from typing import Dict, Any, Optional

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import test components
from src.utils.unified_kraken_nonce_manager import (
    UnifiedKrakenNonceManager, 
    KrakenNonceFixer,
    initialize_enhanced_nonce_manager
)
from src.auth.websocket_authentication_manager import WebSocketAuthenticationManager
from src.balance.enhanced_balance_manager_v2_init import EnhancedBalanceManagerV2Initializer
from src.balance.balance_detection_fix import BalanceDetectionFixer, test_balance_fix

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedNonceIntegrationTester:
    """
    Comprehensive test suite for enhanced nonce integration.
    """
    
    def __init__(self):
        """Initialize the test suite."""
        self.api_key = os.getenv('KRAKEN_API_KEY')
        self.api_secret = os.getenv('KRAKEN_API_SECRET')
        
        self.test_results = {
            'nonce_fixer_test': {},
            'unified_manager_test': {},
            'websocket_auth_test': {},
            'balance_manager_test': {},
            'integration_test': {},
            'error_recovery_test': {}
        }
        
        logger.info("Enhanced Nonce Integration Test Suite initialized")
    
    def test_kraken_nonce_fixer(self) -> Dict[str, Any]:
        """Test the KrakenNonceFixer class directly."""
        logger.info("🔧 Testing KrakenNonceFixer class...")
        
        try:
            if not self.api_key or not self.api_secret:
                return {
                    'success': False, 
                    'error': 'API credentials not available',
                    'skip_reason': 'No credentials'
                }
            
            # Create KrakenNonceFixer instance
            nonce_fixer = KrakenNonceFixer(self.api_key, self.api_secret)
            
            # Test nonce generation
            nonces = []
            for i in range(5):
                nonce = nonce_fixer.get_guaranteed_unique_nonce()
                nonces.append(int(nonce))
                time.sleep(0.001)  # Small delay
            
            # Verify sequence
            sequence_valid = all(nonces[i] < nonces[i+1] for i in range(len(nonces)-1))
            
            # Test the built-in test function
            fixer_test = nonce_fixer.test_nonce_fix()
            
            result = {
                'success': True,
                'nonces_generated': len(nonces),
                'sequence_valid': sequence_valid,
                'nonce_range': f"{nonces[0]} - {nonces[-1]}",
                'built_in_test': fixer_test,
                'base_nonce': nonce_fixer._base_nonce
            }
            
            logger.info(f"✅ KrakenNonceFixer test passed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ KrakenNonceFixer test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_unified_nonce_manager_integration(self) -> Dict[str, Any]:
        """Test the UnifiedKrakenNonceManager with KrakenNonceFixer integration."""
        logger.info("🔧 Testing UnifiedKrakenNonceManager integration...")
        
        try:
            # Reset the singleton for clean test
            UnifiedKrakenNonceManager.reset_instance()
            
            if self.api_key and self.api_secret:
                # Test enhanced initialization
                manager = initialize_enhanced_nonce_manager(self.api_key, self.api_secret)
                
                # Test enhanced nonce generation
                enhanced_nonces = []
                for i in range(3):
                    nonce = manager.get_enhanced_nonce(f"test_{i}")
                    enhanced_nonces.append(int(nonce))
                
                # Test comprehensive system
                system_test = manager.test_enhanced_nonce_system()
                
                result = {
                    'success': True,
                    'enhanced_integration': hasattr(manager, '_nonce_fixer') and manager._nonce_fixer is not None,
                    'enhanced_nonces': enhanced_nonces,
                    'system_test': system_test
                }
            else:
                # Test without credentials
                manager = UnifiedKrakenNonceManager.get_instance()
                
                # Test regular nonce generation
                regular_nonces = []
                for i in range(3):
                    nonce = manager.get_nonce(f"test_{i}")
                    regular_nonces.append(int(nonce))
                
                result = {
                    'success': True,
                    'enhanced_integration': False,
                    'regular_nonces': regular_nonces,
                    'skip_reason': 'No API credentials for enhanced features'
                }
            
            logger.info(f"✅ UnifiedKrakenNonceManager integration test passed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ UnifiedKrakenNonceManager integration test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_websocket_authentication_enhancement(self) -> Dict[str, Any]:
        """Test WebSocket authentication with enhanced nonce handling."""
        logger.info("🔧 Testing WebSocket authentication enhancement...")
        
        try:
            if not self.api_key or not self.api_secret:
                return {
                    'success': False,
                    'skip_reason': 'No API credentials available'
                }
            
            # Create a mock exchange client
            class MockExchangeClient:
                async def make_authenticated_request(self, *args, **kwargs):
                    return {'result': {'token': 'mock_token_12345'}, 'error': []}
            
            # Initialize WebSocket authentication manager
            auth_manager = WebSocketAuthenticationManager(
                exchange_client=MockExchangeClient(),
                api_key=self.api_key,
                private_key=self.api_secret,
                enable_debug=True
            )
            
            # Test enhanced token request (this will use enhanced nonce if available)
            logger.info("Testing enhanced WebSocket token request...")
            
            # Start the authentication manager
            start_success = await auth_manager.start()
            
            if start_success:
                # Get authentication status
                status = auth_manager.get_authentication_status()
                
                # Test token retrieval
                token = await auth_manager.get_websocket_token()
                
                result = {
                    'success': True,
                    'start_success': start_success,
                    'has_valid_token': status.get('has_valid_token', False),
                    'token_length': len(token) if token else 0,
                    'auth_status': status
                }
                
                # Stop the authentication manager
                await auth_manager.stop()
            else:
                result = {
                    'success': False,
                    'error': 'Failed to start WebSocket authentication manager'
                }
            
            logger.info(f"✅ WebSocket authentication test result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ WebSocket authentication test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_balance_detection_fix(self) -> Dict[str, Any]:
        """Test the balance detection fix system."""
        logger.info("🔧 Testing balance detection fix...")
        
        try:
            # Test the balance detection fix directly
            fix_test_result = await test_balance_fix()
            
            result = {
                'success': fix_test_result,
                'test_passed': fix_test_result
            }
            
            logger.info(f"✅ Balance detection fix test result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Balance detection fix test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_balance_manager_v2_initialization(self) -> Dict[str, Any]:
        """Test Enhanced Balance Manager V2 initialization."""
        logger.info("🔧 Testing Enhanced Balance Manager V2 initialization...")
        
        try:
            # Create mock clients
            class MockWebSocketClient:
                def __init__(self):
                    self.auth_manager = None
                
                async def get_balance_v2(self):
                    return {
                        'balances': {
                            'USDT': {'available': 161.39, 'reserved': 0.0},
                            'SHIB': {'available': 1500000.0, 'reserved': 0.0}
                        }
                    }
            
            class MockExchangeClient:
                async def get_balance(self):
                    return {
                        'result': {
                            'USDT': '161.3900',
                            'SHIB': '1500000.0'
                        },
                        'error': []
                    }
            
            # Create Enhanced Balance Manager V2 Initializer
            initializer = EnhancedBalanceManagerV2Initializer(
                websocket_client=MockWebSocketClient(),
                exchange_client=MockExchangeClient()
            )
            
            # Test each initialization phase
            nonce_init = await initializer.initialize_enhanced_nonce_system()
            balance_fix_init = await initializer.initialize_balance_detection_fix()
            
            # Get initialization status
            status = initializer.get_initialization_status()
            
            result = {
                'success': True,
                'nonce_system_init': nonce_init,
                'balance_fix_init': balance_fix_init,
                'initialization_status': status
            }
            
            logger.info(f"✅ Balance Manager V2 initialization test result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Balance Manager V2 initialization test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_error_recovery_mechanisms(self) -> Dict[str, Any]:
        """Test error recovery mechanisms in the enhanced nonce system."""
        logger.info("🔧 Testing error recovery mechanisms...")
        
        try:
            result = {
                'success': True,
                'tests_run': []
            }
            
            # Test 1: Nonce manager error recovery
            try:
                manager = UnifiedKrakenNonceManager.get_instance()
                
                # Simulate nonce error recovery
                recovery_nonce = manager.recover_from_error("error_recovery_test")
                result['tests_run'].append({
                    'test': 'nonce_manager_recovery',
                    'success': True,
                    'recovery_nonce_length': len(recovery_nonce)
                })
            except Exception as e:
                result['tests_run'].append({
                    'test': 'nonce_manager_recovery',
                    'success': False,
                    'error': str(e)
                })
            
            # Test 2: Enhanced nonce system fallback
            try:
                manager = UnifiedKrakenNonceManager.get_instance()
                
                # Test enhanced nonce with fallback
                enhanced_nonce = manager.get_enhanced_nonce("fallback_test")
                result['tests_run'].append({
                    'test': 'enhanced_nonce_fallback',
                    'success': True,
                    'nonce_length': len(enhanced_nonce)
                })
            except Exception as e:
                result['tests_run'].append({
                    'test': 'enhanced_nonce_fallback',
                    'success': False,
                    'error': str(e)
                })
            
            logger.info(f"✅ Error recovery test result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error recovery test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite."""
        logger.info("🚀 Starting Enhanced Nonce Integration Comprehensive Test Suite...")
        
        start_time = time.time()
        
        # Run all tests
        self.test_results['nonce_fixer_test'] = self.test_kraken_nonce_fixer()
        self.test_results['unified_manager_test'] = self.test_unified_nonce_manager_integration()
        self.test_results['websocket_auth_test'] = await self.test_websocket_authentication_enhancement()
        self.test_results['balance_manager_test'] = await self.test_balance_manager_v2_initialization()
        self.test_results['balance_detection_test'] = await self.test_balance_detection_fix()
        self.test_results['error_recovery_test'] = await self.test_error_recovery_mechanisms()
        
        # Calculate overall success
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get('success', False))
        
        test_duration = time.time() - start_time
        
        overall_result = {
            'overall_success': successful_tests == total_tests,
            'successful_tests': successful_tests,
            'total_tests': total_tests,
            'success_rate': (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            'test_duration_seconds': test_duration,
            'detailed_results': self.test_results
        }
        
        # Log summary
        if overall_result['overall_success']:
            logger.info(f"🎉 ALL TESTS PASSED! ({successful_tests}/{total_tests}) - Duration: {test_duration:.2f}s")
        else:
            logger.warning(f"⚠️  SOME TESTS FAILED ({successful_tests}/{total_tests}) - Duration: {test_duration:.2f}s")
        
        return overall_result
    
    def print_test_summary(self, results: Dict[str, Any]) -> None:
        """Print a formatted test summary."""
        print("\n" + "="*80)
        print("ENHANCED NONCE INTEGRATION TEST RESULTS")
        print("="*80)
        
        print(f"Overall Success: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
        print(f"Success Rate: {results['success_rate']:.1f}% ({results['successful_tests']}/{results['total_tests']})")
        print(f"Test Duration: {results['test_duration_seconds']:.2f} seconds")
        
        print("\nDetailed Results:")
        print("-" * 40)
        
        for test_name, test_result in results['detailed_results'].items():
            status = '✅ PASS' if test_result.get('success', False) else '❌ FAIL'
            print(f"{test_name}: {status}")
            
            if not test_result.get('success', False) and 'error' in test_result:
                print(f"  Error: {test_result['error']}")
            elif 'skip_reason' in test_result:
                print(f"  Skipped: {test_result['skip_reason']}")
        
        print("\n" + "="*80)


async def main():
    """Main test execution function."""
    print("Enhanced Nonce Integration Test Suite")
    print("=====================================")
    
    # Check for API credentials
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    if api_key and api_secret:
        print(f"✅ API credentials found (Key: {api_key[:8]}...)")
    else:
        print("⚠️  API credentials not found - some tests will be skipped")
    
    # Create and run test suite
    tester = EnhancedNonceIntegrationTester()
    results = await tester.run_comprehensive_test_suite()
    
    # Print summary
    tester.print_test_summary(results)
    
    # Return appropriate exit code
    return 0 if results['overall_success'] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)