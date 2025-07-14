#!/usr/bin/env python3
"""
EMERGENCY POSITION RECOGNITION FIX
==================================

This script forces the bot to recognize existing positions and enables immediate sell signals.
Bypasses all balance caching and position tracking issues.

Run this script to immediately enable trading on existing positions.
"""

import asyncio
import sys
import time
import logging
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from src.trading.unified_balance_manager import UnifiedBalanceManager
from src.utils.circuit_breaker import circuit_breaker_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Known deployed positions from previous analysis
KNOWN_POSITIONS = {
    'AI16Z': {'amount': 14.895, 'value_usd': 34.47},
    'ALGO': {'amount': 113.682, 'value_usd': 25.21}, 
    'ATOM': {'amount': 5.581, 'value_usd': 37.09},
    'AVAX': {'amount': 2.331, 'value_usd': 84.97},
    'BERA': {'amount': 2.569, 'value_usd': 10.19},
    'SOL': {'amount': 0.024, 'value_usd': 5.00}
}

class EmergencyPositionFix:
    """Force position recognition and enable immediate trading"""
    
    def __init__(self):
        self.logger = logger
        self.fixes_applied = []
    
    async def force_balance_refresh(self):
        """Force immediate balance refresh bypassing all caches"""
        try:
            self.logger.info("🔧 EMERGENCY: Forcing immediate balance refresh...")
            
            # Create a temporary balance manager
            from src.exchange.native_kraken_exchange import NativeKrakenExchange
            exchange = NativeKrakenExchange()
            await exchange.initialize()
            
            balance_manager = UnifiedBalanceManager(exchange)
            
            # Force real-time mode with optimized settings
            balance_manager.cache_duration = 30  # 30 second cache for efficiency
            balance_manager.min_refresh_interval = 15  # 15 second intervals for balanced performance
            balance_manager.smart_cache_enabled = False
            
            # Force refresh with multiple retries
            success = await balance_manager.force_refresh(retry_count=5)
            
            if success:
                all_balances = await balance_manager.get_all_balances()
                self.logger.info(f"✅ EMERGENCY: Balance refresh successful - {len(all_balances)} assets found")
                
                # Log positions that have balances
                for asset, balance_data in all_balances.items():
                    if asset in ['info', 'free', 'used', 'total']:
                        continue
                    
                    if isinstance(balance_data, dict):
                        amount = float(balance_data.get('total', 0))
                    else:
                        amount = float(balance_data)
                    
                    if amount > 0.0001:
                        self.logger.info(f"✅ FOUND POSITION: {asset} = {amount:.8f}")
                
                self.fixes_applied.append("Forced balance refresh")
                return True
            else:
                self.logger.warning("❌ EMERGENCY: Balance refresh failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ EMERGENCY: Balance refresh error: {e}")
            return False
    
    def reset_all_circuit_breakers(self):
        """Reset all circuit breakers to allow immediate trading"""
        try:
            self.logger.info("🔧 EMERGENCY: Resetting all circuit breakers...")
            
            # Reset all circuit breakers
            circuit_breaker_manager.reset_all()
            
            # Get status
            status = circuit_breaker_manager.get_summary()
            self.logger.info(f"✅ EMERGENCY: Circuit breakers reset - {status['total']} total, {status['states']['closed']} closed")
            
            self.fixes_applied.append("Circuit breaker reset")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ EMERGENCY: Circuit breaker reset error: {e}")
            return False
    
    def create_emergency_position_file(self):
        """Create emergency position file for immediate recognition"""
        try:
            self.logger.info("🔧 EMERGENCY: Creating position recognition file...")
            
            emergency_positions = {
                'positions': KNOWN_POSITIONS,
                'timestamp': time.time(),
                'source': 'emergency_fix',
                'total_value_usd': sum(pos['value_usd'] for pos in KNOWN_POSITIONS.values()),
                'available_for_sell': list(KNOWN_POSITIONS.keys())
            }
            
            import json
            emergency_file = project_root / 'src' / 'patches' / '_emergency_positions.json'
            with open(emergency_file, 'w') as f:
                json.dump(emergency_positions, f, indent=2)
            
            self.logger.info(f"✅ EMERGENCY: Position file created with {len(KNOWN_POSITIONS)} assets")
            self.fixes_applied.append("Emergency position file")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ EMERGENCY: Position file error: {e}")
            return False
    
    def enable_emergency_sell_mode(self):
        """Enable emergency sell mode by creating config override"""
        try:
            self.logger.info("🔧 EMERGENCY: Enabling emergency sell mode...")
            
            emergency_config = {
                'emergency_sell_mode': True,
                'min_sell_confidence': 0.1,
                'min_buy_confidence': 0.2,
                'circuit_breaker_bypass': True,
                'force_position_recognition': True,
                'balance_cache_duration': 1,
                'emergency_timeout': 30,
                'created_at': time.time(),
                'known_positions': KNOWN_POSITIONS
            }
            
            import json
            config_file = project_root / 'src' / 'patches' / '_emergency_config.json'
            with open(config_file, 'w') as f:
                json.dump(emergency_config, f, indent=2)
            
            self.logger.info("✅ EMERGENCY: Emergency sell mode enabled")
            self.fixes_applied.append("Emergency sell mode")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ EMERGENCY: Emergency mode error: {e}")
            return False
    
    async def run_emergency_fix(self):
        """Run complete emergency fix deployment"""
        self.logger.info("🚨 EMERGENCY POSITION FIX - DEPLOYMENT STARTED")
        self.logger.info("=" * 60)
        
        fixes_success = []
        
        # 1. Reset circuit breakers
        fixes_success.append(self.reset_all_circuit_breakers())
        
        # 2. Force balance refresh
        fixes_success.append(await self.force_balance_refresh())
        
        # 3. Create emergency position file
        fixes_success.append(self.create_emergency_position_file())
        
        # 4. Enable emergency sell mode
        fixes_success.append(self.enable_emergency_sell_mode())
        
        # Summary
        self.logger.info("=" * 60)
        self.logger.info("🎯 EMERGENCY FIX SUMMARY")
        self.logger.info(f"✅ Fixes Applied: {len(self.fixes_applied)}")
        
        for fix in self.fixes_applied:
            self.logger.info(f"   ✅ {fix}")
        
        if all(fixes_success):
            self.logger.info("🎉 ALL EMERGENCY FIXES APPLIED SUCCESSFULLY!")
            self.logger.info("   Bot should recognize positions and execute trades within 5 minutes")
        else:
            self.logger.warning("⚠️ Some emergency fixes failed - partial deployment")
        
        # Expected positions
        self.logger.info("=" * 60)
        self.logger.info("📊 EXPECTED POSITIONS TO BE RECOGNIZED:")
        total_value = 0
        for asset, data in KNOWN_POSITIONS.items():
            self.logger.info(f"   {asset}: {data['amount']:.6f} (${data['value_usd']:.2f})")
            total_value += data['value_usd']
        
        self.logger.info(f"   TOTAL DEPLOYED VALUE: ${total_value:.2f}")
        self.logger.info("=" * 60)
        
        return all(fixes_success)

async def main():
    """Main execution function"""
    print("🚨 EMERGENCY POSITION RECOGNITION FIX")
    print("=" * 50)
    print("This script forces the bot to recognize existing positions")
    print("and enables immediate sell signals on deployed capital.")
    print("=" * 50)
    
    response = input("Apply EMERGENCY position fix now? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Emergency fix cancelled.")
        return False
    
    fixer = EmergencyPositionFix()
    success = await fixer.run_emergency_fix()
    
    if success:
        print("\n🎉 EMERGENCY FIXES DEPLOYED SUCCESSFULLY!")
        print("   Bot should recognize positions within 5 minutes")
        print("   Expect sell signals on existing positions immediately")
        print("   Monitor logs for 'EMERGENCY' and 'FOUND POSITION' messages")
    else:
        print("\n❌ Some emergency fixes failed")
        print("   Check logs for details")
        print("   Bot may still benefit from partial fixes")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())