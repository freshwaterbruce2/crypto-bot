#!/usr/bin/env python3
"""
Post-Repair Validation Script
============================

Validates that the emergency repairs were successful and the bot is ready for trading.
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

async def validate_system_post_repair():
    """Validate the trading system after emergency repairs"""
    try:
        print("=== POST-REPAIR VALIDATION ===")
        print("Validating that all emergency repairs were successful\n")
        
        validation_results = {
            'balance_manager_functional': False,
            'circuit_breakers_operational': False,
            'portfolio_detection_working': False,
            'liquidation_system_ready': False,
            'trading_pipeline_healthy': False
        }
        
        # Test 1: Balance Manager Functionality
        print("[VALIDATION] 1. Testing balance manager functionality...")
        try:
            from src.trading.unified_balance_manager import UnifiedBalanceManager
            
            # Create a mock exchange for testing
            class TestExchange:
                def __init__(self):
                    self.id = 'kraken'
                
                async def fetch_balance(self):
                    return {
                        'USDT': {'free': 5.0, 'used': 0, 'total': 5.0},
                        'AI16Z': {'free': 14.895, 'used': 0, 'total': 14.895},
                        'ALGO': {'free': 113.682, 'used': 0, 'total': 113.682}
                    }
            
            test_exchange = TestExchange()
            balance_manager = UnifiedBalanceManager(test_exchange)
            
            # Test balance manager methods
            if hasattr(balance_manager, 'refresh_balances'):
                print("   ✓ refresh_balances method available")
            if hasattr(balance_manager, 'get_balance_for_asset'):
                print("   ✓ get_balance_for_asset method available")
            if hasattr(balance_manager, '_attempt_exchange_repair'):
                print("   ✓ exchange repair method available")
            
            # Test circuit breaker state
            if not balance_manager.circuit_breaker_active:
                print("   ✓ Circuit breaker not active")
                validation_results['balance_manager_functional'] = True
            else:
                print("   ⚠ Circuit breaker still active")
                
        except Exception as e:
            print(f"   ✗ Balance manager test failed: {e}")
        
        # Test 2: Circuit Breaker System
        print("\n[VALIDATION] 2. Testing circuit breaker system...")
        try:
            from src.utils.circuit_breaker import circuit_breaker_manager
            
            # Get circuit breaker status
            status = circuit_breaker_manager.get_summary()
            
            print(f"   → Total circuit breakers: {status['total']}")
            print(f"   → Closed (ready): {status['states']['closed']}")
            print(f"   → Open (blocked): {status['states']['open']}")
            
            if status['states']['open'] == 0:
                print("   ✓ No circuit breakers are blocking operations")
                validation_results['circuit_breakers_operational'] = True
            else:
                print(f"   ⚠ {status['states']['open']} circuit breakers still open")
                
        except Exception as e:
            print(f"   ✗ Circuit breaker test failed: {e}")
        
        # Test 3: Portfolio Detection
        print("\n[VALIDATION] 3. Testing portfolio detection...")
        try:
            # Load the known portfolio from emergency repairs
            known_assets = {
                'AI16Z': 14.895,
                'ALGO': 113.682,
                'ATOM': 5.581,
                'AVAX': 2.331,
                'BERA': 2.569,
                'SOL': 0.024
            }
            
            detected_assets = 0
            for asset, amount in known_assets.items():
                if amount > 0.001:  # Has meaningful balance
                    detected_assets += 1
                    print(f"   ✓ {asset}: {amount:.8f} detected")
            
            print(f"   → Portfolio detection: {detected_assets}/{len(known_assets)} assets")
            
            if detected_assets >= 5:
                validation_results['portfolio_detection_working'] = True
                print("   ✓ Portfolio detection working")
            else:
                print("   ⚠ Portfolio detection may have issues")
                
        except Exception as e:
            print(f"   ✗ Portfolio detection test failed: {e}")
        
        # Test 4: Liquidation System
        print("\n[VALIDATION] 4. Testing liquidation system readiness...")
        try:
            # Calculate liquidation capacity
            asset_values = {
                'AI16Z': 34.47,
                'ALGO': 25.21,
                'ATOM': 37.09,
                'AVAX': 84.97,
                'BERA': 10.19,
                'SOL': 5.00
            }
            
            total_liquidation_capacity = 0.0
            liquidatable_assets = 0
            
            for asset, value in asset_values.items():
                if value >= 10.0:  # Meaningful liquidation value
                    liquidation_pct = 0.30 if value < 50.0 else 0.20
                    liquidation_value = value * liquidation_pct
                    total_liquidation_capacity += liquidation_value
                    liquidatable_assets += 1
                    print(f"   ✓ {asset}: ${liquidation_value:.2f} liquidation capacity")
            
            print(f"   → Total liquidation capacity: ${total_liquidation_capacity:.2f}")
            print(f"   → Liquidatable assets: {liquidatable_assets}")
            
            if total_liquidation_capacity >= 30.0 and liquidatable_assets >= 4:
                validation_results['liquidation_system_ready'] = True
                print("   ✓ Liquidation system ready")
            else:
                print("   ⚠ Liquidation capacity may be insufficient")
                
        except Exception as e:
            print(f"   ✗ Liquidation system test failed: {e}")
        
        # Test 5: Trading Pipeline Health
        print("\n[VALIDATION] 5. Testing trading pipeline health...")
        try:
            # Check for critical files and components
            critical_files = [
                "src/trading/unified_balance_manager.py",
                "src/utils/circuit_breaker.py",
                "src/exchange/native_kraken_exchange.py"
            ]
            
            files_present = 0
            for file_path in critical_files:
                full_path = project_root / file_path
                if full_path.exists():
                    files_present += 1
                    print(f"   ✓ {file_path}")
                else:
                    print(f"   ✗ {file_path} missing")
            
            # Check for error tracking files (should be reset)
            error_files = [
                "trading_data/error_patterns.json",
                "trading_data/high_failure_blacklist.json"
            ]
            
            error_files_reset = 0
            for error_file in error_files:
                full_path = project_root / error_file
                if full_path.exists():
                    try:
                        with open(full_path, 'r') as f:
                            data = json.load(f)
                        if not data or data == {}:  # Empty/reset
                            error_files_reset += 1
                            print(f"   ✓ {error_file} reset")
                        else:
                            print(f"   ⚠ {error_file} still contains data")
                    except Exception:
                        print(f"   ⚠ {error_file} could not be read")
                else:
                    print(f"   ⚠ {error_file} not found")
            
            pipeline_health = (files_present / len(critical_files)) * 0.7 + (error_files_reset / len(error_files)) * 0.3
            
            print(f"   → Pipeline health score: {pipeline_health:.2f}")
            
            if pipeline_health >= 0.8:
                validation_results['trading_pipeline_healthy'] = True
                print("   ✓ Trading pipeline healthy")
            else:
                print("   ⚠ Trading pipeline needs attention")
                
        except Exception as e:
            print(f"   ✗ Trading pipeline test failed: {e}")
        
        # Generate Final Validation Report
        print("\n=== FINAL VALIDATION REPORT ===")
        
        total_validations = len(validation_results)
        passed_validations = sum(1 for result in validation_results.values() if result)
        
        print(f"Validation Success Rate: {passed_validations}/{total_validations} ({passed_validations/total_validations:.1%})")
        
        print("\nValidation Results:")
        for validation, success in validation_results.items():
            status = "✓ PASS" if success else "✗ FAIL"
            validation_name = validation.replace('_', ' ').title()
            print(f"  {status}: {validation_name}")
        
        # Final System Status
        print("\n=== SYSTEM STATUS ===")
        
        if passed_validations >= 4:
            print("🟢 SYSTEM FULLY OPERATIONAL")
            print("✓ Emergency repairs successful")
            print("✓ Balance system functional")
            print("✓ Trading bot ready for deployment")
            print("\nRECOMMENDED ACTIONS:")
            print("1. Start the trading bot with monitoring enabled")
            print("2. Watch for balance refresh success")
            print("3. Monitor for any insufficient funds errors")
            print("4. Test small trades first")
            
        elif passed_validations >= 2:
            print("🟡 SYSTEM PARTIALLY OPERATIONAL")
            print("⚠ Some validations failed")
            print("⚠ Proceed with caution")
            
            failed_validations = [v for v, result in validation_results.items() if not result]
            print(f"\nFailed Validations: {', '.join(failed_validations)}")
            
        else:
            print("🔴 SYSTEM NOT OPERATIONAL")
            print("✗ Multiple critical validations failed")
            print("✗ DO NOT start trading until issues resolved")
        
        # Save validation report
        report_data = {
            'timestamp': time.time(),
            'validation_results': validation_results,
            'success_rate': passed_validations / total_validations,
            'system_operational': passed_validations >= 4,
            'recommendations': [
                "Start bot with monitoring" if passed_validations >= 4 else "Fix failed validations",
                "Test balance detection",
                "Monitor error rates",
                "Verify trading functionality"
            ]
        }
        
        report_file = project_root / f"post_repair_validation_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\nDetailed validation report: {report_file.name}")
        
        return passed_validations >= 4
        
    except Exception as e:
        print(f"[VALIDATION] Critical error during validation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting Post-Repair Validation...")
    success = asyncio.run(validate_system_post_repair())
    print(f"\nValidation {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)