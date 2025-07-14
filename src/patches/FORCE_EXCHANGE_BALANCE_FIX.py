#!/usr/bin/env python3
"""
FORCE EXCHANGE BALANCE FIX
===========================

This script patches the bot to use actual exchange balances instead of cached position data.
Fixes the "tracked position amount: 0" vs actual balance mismatch.

Run this to force real balance usage for immediate sell signal execution.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_balance_override_patch():
    """Apply patch to force exchange balance usage"""
    
    # Patch the unified balance manager to always use fresh exchange data
    balance_manager_file = project_root / 'src' / 'trading' / 'unified_balance_manager.py'
    
    try:
        with open(balance_manager_file, 'r') as f:
            content = f.read()
        
        # Add emergency override at the top of get_balance_for_asset method
        old_method_start = "    async def get_balance_for_asset(self, asset: str) -> float:"
        new_method_start = """    async def get_balance_for_asset(self, asset: str) -> float:
        # EMERGENCY OVERRIDE: Force fresh exchange balance lookup
        if hasattr(self, '_emergency_mode_enabled'):
            try:
                if self.exchange:
                    fresh_balance = await self.exchange.fetch_balance()
                    if fresh_balance and asset in fresh_balance:
                        balance_data = fresh_balance[asset]
                        if isinstance(balance_data, dict):
                            amount = float(balance_data.get('total', 0))
                        else:
                            amount = float(balance_data)
                        if amount > 0.0001:
                            logger.info(f"[UBM] EMERGENCY: Found {asset} balance via direct exchange: {amount:.8f}")
                            return amount
            except Exception as e:
                logger.warning(f"[UBM] EMERGENCY: Direct exchange lookup failed for {asset}: {e}")"""
        
        if old_method_start in content:
            content = content.replace(old_method_start, new_method_start)
            
            with open(balance_manager_file, 'w') as f:
                f.write(content)
            
            logger.info("✅ Applied emergency balance override patch")
            return True
        else:
            logger.warning("❌ Could not find method to patch")
            return False
            
    except Exception as e:
        logger.error(f"❌ Patch application failed: {e}")
        return False

def create_emergency_balance_enabler():
    """Create script to enable emergency mode"""
    
    enabler_code = '''#!/usr/bin/env python3
"""Emergency Balance Mode Enabler"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

try:
    from src.trading.unified_balance_manager import UnifiedBalanceManager
    
    # Enable emergency mode globally for all instances
    UnifiedBalanceManager._emergency_mode_enabled = True
    
    # Monkey patch the __init__ method to set emergency mode
    original_init = UnifiedBalanceManager.__init__
    
    def emergency_init(self, *args, **kwargs):
        result = original_init(self, *args, **kwargs)
        self._emergency_mode_enabled = True
        self.cache_duration = 30  # 30 second cache for better efficiency
        self.min_refresh_interval = 15  # 15 second refresh for balanced performance
        return result
    
    UnifiedBalanceManager.__init__ = emergency_init
    
    print("[EMERGENCY] Balance manager patched for direct exchange access")
    
except Exception as e:
    print(f"[EMERGENCY] Error applying patch: {e}")
'''
    
    try:
        enabler_file = project_root / 'src' / 'patches' / '_enable_emergency_balance.py'
        with open(enabler_file, 'w') as f:
            f.write(enabler_code)
        
        logger.info("✅ Created emergency balance enabler")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create enabler: {e}")
        return False

def main():
    """Main execution"""
    print("🔧 FORCE EXCHANGE BALANCE FIX")
    print("=" * 40)
    print("This patches the bot to use direct exchange balances")
    print("instead of cached position data.")
    print("=" * 40)
    
    response = input("Apply balance override patch? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Patch cancelled.")
        return False
    
    success = True
    
    # Apply the main patch
    success &= apply_balance_override_patch()
    
    # Create the enabler
    success &= create_emergency_balance_enabler()
    
    if success:
        print("\n✅ EMERGENCY BALANCE PATCH APPLIED!")
        print("   Bot will now use direct exchange balance lookups")
        print("   This should resolve 'tracked position amount: 0' issues")
        print("   Restart the bot or wait for automatic reload")
    else:
        print("\n❌ Patch application failed")
        print("   Check the logs for details")
    
    return success

if __name__ == "__main__":
    main()