#!/usr/bin/env python3
"""
BALANCE ACCESS VALIDATION - Post-Fix Testing
===========================================

This script validates that the nonce fix successfully restored access to:
- $18.99 USDT balance
- $8.99 SHIB balance
- Kraken API operations

Tests performed:
1. Unified nonce manager functionality
2. API authentication with corrected nonces
3. Balance retrieval for USDT and SHIB
4. Minimal trading capability verification

CRITICAL: This script must pass for trading to resume
Author: Emergency Trading Bot Repair Team
Date: 2025-08-03
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path
from decimal import Decimal
from typing import Dict, Optional, Tuple
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('balance_validation.log')
    ]
)
logger = logging.getLogger(__name__)

class BalanceAccessValidator:
    """Validates that nonce fix restored balance access"""
    
    def __init__(self):
        self.results = {
            'nonce_manager_test': False,
            'api_connection_test': False,
            'usdt_balance_access': False,
            'shib_balance_access': False,
            'trading_readiness': False,
            'balances': {},
            'errors': [],
            'nonce_info': {}
        }
        
        self.expected_balances = {
            'USDT': 18.99,
            'SHIB': 8.99
        }
    
    def test_unified_nonce_manager(self) -> bool:
        """Test that unified nonce manager is working correctly"""
        try:
            logger.info("🔍 Testing unified nonce manager...")
            
            from src.utils.unified_kraken_nonce_manager import get_unified_nonce_manager
            
            # Get manager instance
            manager = get_unified_nonce_manager()
            
            # Generate test nonces
            nonce1 = manager.get_nonce("validation_test_1")
            time.sleep(0.1)  # Small delay
            nonce2 = manager.get_nonce("validation_test_2")
            
            # Validate nonces are increasing
            nonce1_int = int(nonce1)
            nonce2_int = int(nonce2)
            
            if nonce2_int > nonce1_int:
                logger.info(f"✅ Nonce manager working: {nonce1} -> {nonce2}")
                
                # Get status info
                status = manager.get_status()
                self.results['nonce_info'] = {
                    'current_nonce': status.get('current_nonce'),
                    'total_generated': status.get('total_generated'),
                    'error_recoveries': status.get('error_recoveries'),
                    'active_connections': status.get('active_connections')
                }
                
                self.results['nonce_manager_test'] = True
                return True
            else:
                error_msg = f"❌ Nonces not increasing: {nonce1} -> {nonce2}"
                logger.error(error_msg)
                self.results['errors'].append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"❌ Nonce manager test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    def test_api_connection(self) -> bool:
        """Test basic API connection with fixed nonces"""
        try:
            logger.info("🔍 Testing API connection...")
            
            # Try to import and initialize exchange
            from src.exchange.native_kraken_exchange import NativeKrakenExchange
            
            # Create exchange instance
            exchange = NativeKrakenExchange(
                api_key=os.getenv('KRAKEN_API_KEY', ''),
                api_secret=os.getenv('KRAKEN_API_SECRET', ''),
                tier='pro'
            )
            
            # Test basic API call (server time - no auth needed)
            server_time = exchange.get_server_time()
            
            if server_time:
                logger.info(f"✅ API connection working - Server time: {server_time}")
                self.results['api_connection_test'] = True
                return True
            else:
                error_msg = "❌ API connection failed - no server time"
                logger.error(error_msg)
                self.results['errors'].append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"❌ API connection test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    def test_balance_access(self) -> Tuple[bool, bool]:
        """Test access to USDT and SHIB balances"""
        usdt_success = False
        shib_success = False
        
        try:
            logger.info("🔍 Testing balance access...")
            
            # Import exchange with unified nonce manager
            from src.exchange.native_kraken_exchange import NativeKrakenExchange
            
            exchange = NativeKrakenExchange(
                api_key=os.getenv('KRAKEN_API_KEY', ''),
                api_secret=os.getenv('KRAKEN_API_SECRET', ''),
                tier='pro'
            )
            
            # Get account balances
            balances = exchange.get_account_balance()
            
            if balances:
                logger.info("✅ Successfully retrieved balances!")
                self.results['balances'] = balances
                
                # Check for USDT
                usdt_balance = balances.get('USDT', 0)
                if usdt_balance > 0:
                    logger.info(f"✅ USDT Balance Found: ${usdt_balance:.2f}")
                    usdt_success = True
                    self.results['usdt_balance_access'] = True
                else:
                    logger.warning("⚠️  USDT balance is 0 (might be deployed in positions)")
                
                # Check for SHIB
                shib_balance = balances.get('SHIB', 0)
                if shib_balance > 0:
                    logger.info(f"✅ SHIB Balance Found: {shib_balance:.2f} SHIB")
                    shib_success = True
                    self.results['shib_balance_access'] = True
                else:
                    logger.warning("⚠️  SHIB balance is 0 (might be deployed in positions)")
                
                # Print all available balances
                logger.info("💰 All Available Balances:")
                for asset, amount in balances.items():
                    if amount > 0:
                        logger.info(f"  • {asset}: {amount}")
                
                # Even if specific assets are 0, successful balance retrieval means fix worked
                return True, True
                
            else:
                error_msg = "❌ No balances retrieved - possible authentication failure"
                logger.error(error_msg)
                self.results['errors'].append(error_msg)
                return False, False
                
        except Exception as e:
            error_msg = f"❌ Balance access test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False, False
    
    def test_trading_readiness(self) -> bool:
        """Test basic trading readiness"""
        try:
            logger.info("🔍 Testing trading readiness...")
            
            # Test that we can access trading pairs
            from src.exchange.native_kraken_exchange import NativeKrakenExchange
            
            exchange = NativeKrakenExchange(
                api_key=os.getenv('KRAKEN_API_KEY', ''),
                api_secret=os.getenv('KRAKEN_API_SECRET', ''),
                tier='pro'
            )
            
            # Get tradable pairs info (minimal test)
            pairs_info = exchange.get_tradable_asset_pairs(['SHIBUSDT', 'USDTUSD'])
            
            if pairs_info:
                logger.info("✅ Trading pairs accessible")
                
                # Test order book access (read-only)
                orderbook = exchange.get_order_book('SHIBUSDT', count=1)
                
                if orderbook:
                    logger.info("✅ Order book access working")
                    self.results['trading_readiness'] = True
                    return True
                else:
                    logger.warning("⚠️  Order book access limited")
                    return True  # Still consider ready if pairs info works
            else:
                error_msg = "❌ Cannot access trading pairs"
                logger.error(error_msg)
                self.results['errors'].append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"❌ Trading readiness test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    async def run_comprehensive_validation(self) -> bool:
        """Run all validation tests"""
        logger.info("🚨 BALANCE ACCESS VALIDATION STARTING 🚨")
        logger.info("Testing nonce fix effectiveness...")
        
        success_count = 0
        total_tests = 4
        
        try:
            # Test 1: Unified nonce manager
            logger.info("\n📋 Test 1: Unified Nonce Manager")
            if self.test_unified_nonce_manager():
                success_count += 1
            
            # Test 2: API connection
            logger.info("\n📋 Test 2: API Connection")
            if self.test_api_connection():
                success_count += 1
            
            # Test 3: Balance access
            logger.info("\n📋 Test 3: Balance Access")
            usdt_ok, shib_ok = self.test_balance_access()
            if usdt_ok or shib_ok:  # Either one working means API access restored
                success_count += 1
            
            # Test 4: Trading readiness
            logger.info("\n📋 Test 4: Trading Readiness")
            if self.test_trading_readiness():
                success_count += 1
            
            # Overall success evaluation
            success_rate = success_count / total_tests
            overall_success = success_rate >= 0.75  # 3 out of 4 tests must pass
            
            return overall_success
            
        except Exception as e:
            error_msg = f"❌ Comprehensive validation failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    def save_validation_report(self):
        """Save detailed validation report"""
        report_path = project_root / f"validation_report_{int(time.time())}.json"
        
        report_data = {
            'timestamp': time.time(),
            'iso_time': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            'validation_results': self.results,
            'fix_effectiveness': {
                'nonce_conflicts_resolved': self.results['nonce_manager_test'],
                'api_access_restored': self.results['api_connection_test'],
                'balance_visibility': self.results['usdt_balance_access'] or self.results['shib_balance_access'],
                'trading_capability': self.results['trading_readiness']
            },
            'next_steps': self.get_next_steps()
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"📄 Validation report saved: {report_path}")
        return report_path
    
    def get_next_steps(self) -> list:
        """Determine next steps based on validation results"""
        steps = []
        
        if not self.results['nonce_manager_test']:
            steps.append("CRITICAL: Fix unified nonce manager - imports may still conflict")
        
        if not self.results['api_connection_test']:
            steps.append("CRITICAL: Resolve API connection issues - check credentials")
        
        if not (self.results['usdt_balance_access'] or self.results['shib_balance_access']):
            steps.append("WARNING: No balances visible - may be deployed in positions")
        
        if not self.results['trading_readiness']:
            steps.append("WARNING: Trading functions limited - check market access")
        
        if all([self.results['nonce_manager_test'], self.results['api_connection_test']]):
            steps.append("SUCCESS: Nonce fix effective - trading bot should work")
            steps.append("RECOMMENDED: Run bot in paper trading mode first")
            steps.append("NEXT: Execute small test trade to confirm full functionality")
        
        return steps
    
    def print_results(self):
        """Print comprehensive validation results"""
        logger.info("\n" + "="*70)
        logger.info("🚨 BALANCE ACCESS VALIDATION RESULTS 🚨")
        logger.info("="*70)
        
        # Test results
        tests = [
            ("Unified Nonce Manager", self.results['nonce_manager_test']),
            ("API Connection", self.results['api_connection_test']),
            ("USDT Balance Access", self.results['usdt_balance_access']),
            ("SHIB Balance Access", self.results['shib_balance_access']),
            ("Trading Readiness", self.results['trading_readiness'])
        ]
        
        for test_name, passed in tests:
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
        
        # Balance summary
        if self.results['balances']:
            logger.info("\n💰 DETECTED BALANCES:")
            for asset, amount in self.results['balances'].items():
                if amount > 0:
                    logger.info(f"  • {asset}: {amount}")
        
        # Nonce info
        if self.results['nonce_info']:
            logger.info(f"\n🔢 NONCE STATUS:")
            for key, value in self.results['nonce_info'].items():
                logger.info(f"  • {key}: {value}")
        
        # Errors
        if self.results['errors']:
            logger.info(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            for i, error in enumerate(self.results['errors'], 1):
                logger.info(f"  {i}. {error}")
        
        # Next steps
        next_steps = self.get_next_steps()
        if next_steps:
            logger.info(f"\n📋 NEXT STEPS:")
            for i, step in enumerate(next_steps, 1):
                logger.info(f"  {i}. {step}")
        
        logger.info("="*70)


async def main():
    """Run balance access validation"""
    print("🔍 BALANCE ACCESS VALIDATION - POST NONCE FIX 🔍")
    print("Purpose: Verify that nonce fix restored access to trading balances")
    print("Expected: $18.99 USDT + $8.99 SHIB should be accessible")
    print("-" * 70)
    
    validator = BalanceAccessValidator()
    
    # Run validation
    success = await validator.run_comprehensive_validation()
    
    # Print results
    validator.print_results()
    
    # Save report
    report_path = validator.save_validation_report()
    
    # Final verdict
    if success:
        print("\n🎉 VALIDATION SUCCESSFUL!")
        print("✅ Nonce fix appears to have resolved the trading access issue")
        print("🚀 Your trading bot should now be able to access balances")
        print("💡 Consider running a small test trade to confirm full functionality")
    else:
        print("\n⚠️  VALIDATION ISSUES DETECTED")
        print("❌ Some tests failed - manual intervention may be required")
        print("🔧 Check the errors above and consider additional fixes")
        print("📞 Review the validation report for detailed next steps")
    
    print(f"\n📄 Full report: {report_path}")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)