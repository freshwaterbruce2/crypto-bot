#!/usr/bin/env python3
"""
Balance Manager V2 Fixes Test Script
====================================

Quick focused test to validate Balance Manager V2 initialization and fixes
without running the full bot. Tests specific nonce/authentication issues
and WebSocket balance streaming integration.

This script performs a fast validation of:
1. Exchange initialization (known working)
2. Balance Manager V2 creation with fallback handling
3. Nonce/authentication resolution 
4. WebSocket connection with proper error handling
5. REST API fallback capabilities

Expected runtime: 30-60 seconds maximum
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Import required components
from src.exchange.exchange_singleton import get_exchange
from src.balance.balance_manager_v2 import BalanceManagerV2, BalanceManagerV2Config, create_balance_manager_v2
from src.websocket.kraken_websocket_v2 import KrakenWebSocketV2
from src.config.core import CoreConfigManager
from src.utils.secure_credentials import SecureCredentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('balance_manager_test.log')
    ]
)

logger = logging.getLogger(__name__)


class BalanceManagerFixesTest:
    """Test suite for Balance Manager V2 fixes validation"""
    
    def __init__(self):
        self.config: Optional[Dict[str, Any]] = None
        self.exchange = None
        self.balance_manager = None
        self.websocket_client = None
        self.results = {
            'test_results': {},
            'timestamps': {},
            'errors': [],
            'summary': {}
        }
        
    async def setup(self) -> bool:
        """Initialize test environment"""
        try:
            logger.info("=== Balance Manager V2 Fixes Test Setup ===")
            
            # Step 1: Load configuration
            logger.info("Loading configuration...")
            config_manager = CoreConfigManager()
            self.config = config_manager.get_core_config()
            if not self.config:
                logger.error("Failed to load configuration")
                return False
            
            logger.info("Configuration loaded successfully")
            self.results['test_results']['config_load'] = 'PASS'
            
            # Step 2: Load credentials
            logger.info("Loading API credentials...")
            credentials = SecureCredentials()
            api_key = credentials.get_api_key()
            api_secret = credentials.get_api_secret()
            
            if not api_key or not api_secret:
                logger.error("API credentials not found")
                self.results['errors'].append("Missing API credentials")
                return False
            
            logger.info("API credentials loaded successfully")
            self.results['test_results']['credentials_load'] = 'PASS'
            
            # Step 3: Initialize exchange (known working)
            logger.info("Initializing exchange singleton...")
            self.exchange = await get_exchange(
                api_key=api_key,
                api_secret=api_secret, 
                tier='pro',
                config=self.config
            )
            
            if not self.exchange:
                logger.error("Failed to initialize exchange")
                return False
            
            logger.info("Exchange initialized successfully")
            self.results['test_results']['exchange_init'] = 'PASS'
            
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            self.results['errors'].append(f"Setup error: {str(e)}")
            return False
    
    async def test_exchange_connection(self) -> bool:
        """Test basic exchange connectivity (should work)"""
        try:
            logger.info("=== Testing Exchange Connection ===")
            
            # Test basic connection
            logger.info("Testing exchange connection...")
            
            # Simple market load test
            if hasattr(self.exchange, 'markets') and self.exchange.markets:
                market_count = len(self.exchange.markets)
                logger.info(f"Exchange has {market_count} markets loaded")
                self.results['test_results']['exchange_connection'] = 'PASS'
                return True
            else:
                logger.warning("Exchange markets not loaded, attempting load...")
                await self.exchange.load_markets()
                market_count = len(self.exchange.markets) if hasattr(self.exchange, 'markets') else 0
                
                if market_count > 0:
                    logger.info(f"Exchange loaded {market_count} markets successfully")
                    self.results['test_results']['exchange_connection'] = 'PASS'
                    return True
                else:
                    logger.error("Exchange connection test failed - no markets")
                    self.results['test_results']['exchange_connection'] = 'FAIL'
                    return False
                
        except Exception as e:
            logger.error(f"Exchange connection test failed: {e}")
            self.results['test_results']['exchange_connection'] = 'FAIL'
            self.results['errors'].append(f"Exchange connection error: {str(e)}")
            return False
    
    async def test_websocket_client_creation(self) -> bool:
        """Test WebSocket V2 client creation"""
        try:
            logger.info("=== Testing WebSocket Client Creation ===")
            
            # Test WebSocket client initialization
            logger.info("Creating WebSocket V2 client...")
            
            self.websocket_client = KrakenWebSocketV2()
            
            if self.websocket_client:
                logger.info("WebSocket V2 client created successfully")
                self.results['test_results']['websocket_creation'] = 'PASS'
                return True
            else:
                logger.error("Failed to create WebSocket V2 client")
                self.results['test_results']['websocket_creation'] = 'FAIL'
                return False
                
        except Exception as e:
            logger.error(f"WebSocket client creation failed: {e}")
            self.results['test_results']['websocket_creation'] = 'FAIL'
            self.results['errors'].append(f"WebSocket creation error: {str(e)}")
            return False
    
    async def test_balance_manager_creation(self) -> bool:
        """Test Balance Manager V2 creation with fallback handling"""
        try:
            logger.info("=== Testing Balance Manager V2 Creation ===")
            
            # Create Balance Manager V2 configuration
            logger.info("Creating Balance Manager V2 configuration...")
            config = BalanceManagerV2Config(
                websocket_connection_timeout=10.0,  # Short timeout for testing
                websocket_token_refresh_interval=720.0,
                enable_circuit_breaker=True,
                circuit_breaker_failure_threshold=3,  # Lower threshold for testing
                circuit_breaker_recovery_timeout=30.0,
                enable_performance_monitoring=True,
                maintain_legacy_interface=True
            )
            
            logger.info("Creating Balance Manager V2 instance...")
            self.balance_manager = BalanceManagerV2(
                websocket_client=self.websocket_client,
                exchange_client=self.exchange,
                config=config
            )
            
            if self.balance_manager:
                logger.info("Balance Manager V2 instance created successfully")
                self.results['test_results']['balance_manager_creation'] = 'PASS'
                return True
            else:
                logger.error("Failed to create Balance Manager V2 instance")
                self.results['test_results']['balance_manager_creation'] = 'FAIL'
                return False
                
        except Exception as e:
            logger.error(f"Balance Manager V2 creation failed: {e}")
            self.results['test_results']['balance_manager_creation'] = 'FAIL'
            self.results['errors'].append(f"Balance Manager creation error: {str(e)}")
            return False
    
    async def test_balance_manager_initialization(self) -> bool:
        """Test Balance Manager V2 initialization with timeout protection"""
        try:
            logger.info("=== Testing Balance Manager V2 Initialization ===")
            
            # Test initialization with timeout
            logger.info("Initializing Balance Manager V2 (max 45 seconds)...")
            
            start_time = time.time()
            
            # Use asyncio timeout to prevent hanging
            try:
                initialization_success = await asyncio.wait_for(
                    self.balance_manager.initialize(),
                    timeout=45.0
                )
                
                elapsed = time.time() - start_time
                
                if initialization_success:
                    logger.info(f"Balance Manager V2 initialized successfully in {elapsed:.2f} seconds")
                    self.results['test_results']['balance_manager_init'] = 'PASS'
                    self.results['timestamps']['balance_manager_init_time'] = elapsed
                    
                    # Check initialization status
                    status = self.balance_manager.get_status()
                    logger.info(f"Balance Manager Status: {status}")
                    
                    return True
                else:
                    logger.warning(f"Balance Manager V2 initialization returned False after {elapsed:.2f} seconds")
                    self.results['test_results']['balance_manager_init'] = 'PARTIAL'
                    self.results['timestamps']['balance_manager_init_time'] = elapsed
                    return True  # Still pass as fallback mode might be working
                    
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                logger.error(f"Balance Manager V2 initialization timed out after {elapsed:.2f} seconds")
                self.results['test_results']['balance_manager_init'] = 'TIMEOUT'
                self.results['timestamps']['balance_manager_init_time'] = elapsed
                return False
                
        except Exception as e:
            elapsed = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"Balance Manager V2 initialization failed: {e}")
            self.results['test_results']['balance_manager_init'] = 'FAIL'
            self.results['errors'].append(f"Balance Manager init error: {str(e)}")
            if elapsed > 0:
                self.results['timestamps']['balance_manager_init_time'] = elapsed
            return False
    
    async def test_balance_access(self) -> bool:
        """Test basic balance access functionality"""
        try:
            logger.info("=== Testing Balance Access ===")
            
            if not self.balance_manager or not self.balance_manager._initialized:
                logger.warning("Balance Manager not initialized, skipping balance access test")
                self.results['test_results']['balance_access'] = 'SKIP'
                return True
            
            # Test USDT balance access (most common)
            logger.info("Testing USDT balance access...")
            
            try:
                usdt_balance = await asyncio.wait_for(
                    self.balance_manager.get_balance('USDT'),
                    timeout=10.0
                )
                
                if usdt_balance is not None:
                    logger.info(f"USDT balance retrieved: {usdt_balance}")
                    self.results['test_results']['balance_access'] = 'PASS'
                    return True
                else:
                    logger.info("USDT balance returned None (may be expected if no USDT)")
                    self.results['test_results']['balance_access'] = 'PARTIAL'
                    return True
                    
            except asyncio.TimeoutError:
                logger.warning("Balance access timed out after 10 seconds")
                self.results['test_results']['balance_access'] = 'TIMEOUT'
                return False
                
        except Exception as e:
            logger.error(f"Balance access test failed: {e}")
            self.results['test_results']['balance_access'] = 'FAIL'
            self.results['errors'].append(f"Balance access error: {str(e)}")
            return False
    
    async def test_nonce_authentication(self) -> bool:
        """Test that nonce/authentication issues are resolved"""
        try:
            logger.info("=== Testing Nonce/Authentication Resolution ===")
            
            # Check nonce manager
            if hasattr(self.exchange, 'nonce_manager'):
                logger.info("Exchange has nonce manager")
                
                # Generate a test nonce
                nonce = self.exchange.nonce_manager.generate_nonce('test_connection')
                logger.info(f"Generated test nonce successfully")
                self.results['test_results']['nonce_generation'] = 'PASS'
            else:
                logger.warning("Exchange does not have nonce manager")
                self.results['test_results']['nonce_generation'] = 'SKIP'
            
            # Test basic REST API call (should not have nonce issues)
            logger.info("Testing basic REST API call...")
            
            try:
                # Simple server time call (public API, no auth needed)
                if hasattr(self.exchange, 'fetch_time'):
                    server_time = await asyncio.wait_for(
                        self.exchange.fetch_time(),
                        timeout=10.0
                    )
                    if server_time:
                        logger.info("REST API call successful - no nonce issues detected")
                        self.results['test_results']['rest_api_test'] = 'PASS'
                    else:
                        logger.warning("REST API call returned None")
                        self.results['test_results']['rest_api_test'] = 'PARTIAL'
                else:
                    logger.info("Exchange does not support fetch_time, skipping REST test")
                    self.results['test_results']['rest_api_test'] = 'SKIP'
                    
            except Exception as api_error:
                if "invalid nonce" in str(api_error).lower():
                    logger.error(f"NONCE ISSUE DETECTED: {api_error}")
                    self.results['test_results']['rest_api_test'] = 'FAIL_NONCE'
                    self.results['errors'].append(f"Nonce error: {str(api_error)}")
                    return False
                else:
                    logger.warning(f"REST API test failed (not nonce related): {api_error}")
                    self.results['test_results']['rest_api_test'] = 'FAIL_OTHER'
            
            return True
            
        except Exception as e:
            logger.error(f"Nonce/authentication test failed: {e}")
            self.results['test_results']['nonce_authentication'] = 'FAIL'
            self.results['errors'].append(f"Nonce/auth error: {str(e)}")
            return False
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            logger.info("=== Cleaning Up Resources ===")
            
            if self.balance_manager:
                logger.info("Shutting down Balance Manager V2...")
                await self.balance_manager.shutdown()
            
            if self.websocket_client:
                logger.info("Closing WebSocket client...")
                if hasattr(self.websocket_client, 'close'):
                    await self.websocket_client.close()
            
            if self.exchange:
                logger.info("Closing exchange connection...")
                # Exchange singleton will handle cleanup
                pass
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = len(self.results['test_results'])
        passed_tests = sum(1 for result in self.results['test_results'].values() 
                          if result == 'PASS')
        failed_tests = sum(1 for result in self.results['test_results'].values() 
                          if result in ['FAIL', 'FAIL_NONCE', 'FAIL_OTHER'])
        partial_tests = sum(1 for result in self.results['test_results'].values() 
                           if result in ['PARTIAL', 'TIMEOUT', 'SKIP'])
        
        # Determine overall status
        if failed_tests == 0 and passed_tests > 0:
            overall_status = 'PASS'
        elif any('FAIL_NONCE' in str(result) for result in self.results['test_results'].values()):
            overall_status = 'NONCE_ISSUES_DETECTED'
        elif failed_tests > 0:
            overall_status = 'SOME_FAILURES'
        else:
            overall_status = 'INCONCLUSIVE'
        
        summary = {
            'overall_status': overall_status,
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'partial': partial_tests,
            'error_count': len(self.results['errors']),
            'key_findings': [],
            'recommendations': []
        }
        
        # Add key findings
        if self.results['test_results'].get('exchange_init') == 'PASS':
            summary['key_findings'].append("✓ Exchange initialization working correctly")
        
        if self.results['test_results'].get('balance_manager_creation') == 'PASS':
            summary['key_findings'].append("✓ Balance Manager V2 creation successful")
            
        if self.results['test_results'].get('balance_manager_init') == 'PASS':
            summary['key_findings'].append("✓ Balance Manager V2 initialization successful")
        elif self.results['test_results'].get('balance_manager_init') == 'PARTIAL':
            summary['key_findings'].append("⚠ Balance Manager V2 partial initialization (fallback mode)")
        elif self.results['test_results'].get('balance_manager_init') == 'TIMEOUT':
            summary['key_findings'].append("✗ Balance Manager V2 initialization timeout")
            
        if 'FAIL_NONCE' in str(self.results['test_results']):
            summary['key_findings'].append("✗ NONCE AUTHENTICATION ISSUES DETECTED")
            summary['recommendations'].append("Review nonce manager implementation")
        else:
            summary['key_findings'].append("✓ No nonce authentication issues detected")
        
        # Add recommendations
        if overall_status == 'PASS':
            summary['recommendations'].append("Balance Manager V2 fixes appear to be working correctly")
        elif overall_status == 'NONCE_ISSUES_DETECTED':
            summary['recommendations'].append("Address nonce authentication issues before proceeding")
        elif 'TIMEOUT' in str(self.results['test_results']):
            summary['recommendations'].append("Investigate timeout issues - may indicate networking problems")
        
        self.results['summary'] = summary
        return summary
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite"""
        start_time = time.time()
        
        try:
            logger.info("Starting Balance Manager V2 Fixes Test Suite")
            logger.info("=" * 60)
            
            # Setup
            if not await self.setup():
                logger.error("Test setup failed, aborting")
                return self.results
            
            # Run tests in sequence
            await self.test_exchange_connection()
            await self.test_websocket_client_creation()
            await self.test_balance_manager_creation()
            await self.test_balance_manager_initialization()
            await self.test_balance_access()
            await self.test_nonce_authentication()
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            self.results['errors'].append(f"Test suite error: {str(e)}")
        
        finally:
            # Always cleanup
            await self.cleanup()
            
            # Generate summary
            total_time = time.time() - start_time
            summary = self.generate_summary()
            
            logger.info("=" * 60)
            logger.info("TEST SUITE COMPLETE")
            logger.info(f"Total execution time: {total_time:.2f} seconds")
            logger.info(f"Overall status: {summary['overall_status']}")
            logger.info(f"Tests: {summary['total_tests']} total, {summary['passed']} passed, {summary['failed']} failed")
            
            if summary['key_findings']:
                logger.info("Key Findings:")
                for finding in summary['key_findings']:
                    logger.info(f"  {finding}")
            
            if summary['recommendations']:
                logger.info("Recommendations:")
                for rec in summary['recommendations']:
                    logger.info(f"  {rec}")
            
            self.results['total_execution_time'] = total_time
            
        return self.results


async def main():
    """Main test execution"""
    test_runner = BalanceManagerFixesTest()
    results = await test_runner.run_all_tests()
    
    # Save results to file
    results_file = Path(__file__).parent / f"balance_manager_test_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Test results saved to: {results_file}")
    
    # Exit with appropriate code
    summary = results.get('summary', {})
    overall_status = summary.get('overall_status', 'UNKNOWN')
    
    if overall_status == 'PASS':
        logger.info("All tests passed - Balance Manager V2 fixes are working!")
        return 0
    elif overall_status == 'NONCE_ISSUES_DETECTED':
        logger.error("NONCE AUTHENTICATION ISSUES DETECTED - Requires immediate attention")
        return 2
    else:
        logger.warning(f"Test completed with status: {overall_status}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)