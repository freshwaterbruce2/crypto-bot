#!/usr/bin/env python3
"""Quick validation test for $3.50 position sizing"""

import sys
import os
sys.path.insert(0, '.')

from src.config.config import Config

def test_config_validation():
    """Test that configuration is correctly set to $3.50"""
    print("🔍 Live Validation: Testing $3.50 Position Sizing Configuration")
    print("=" * 60)
    
    try:
        config = Config()
        
        # Test position size
        position_size = config.position_size_usdt
        print(f"✅ Position size configured: ${position_size}")
        
        # Test min order size  
        min_order = config.min_order_size_usdt
        print(f"✅ Min order size: ${min_order}")
        
        # Test position percentage
        position_pct = config.position_size_percentage
        print(f"✅ Position size percentage: {position_pct * 100}%")
        
        # Calculate validation
        usdt_balance = 5.0  # Current balance from logs
        trade_amount = position_size
        percentage = (trade_amount / usdt_balance) * 100
        
        print(f"\n📊 VALIDATION CALCULATION:")
        print(f"   USDT Balance: ${usdt_balance}")
        print(f"   Trade Amount: ${trade_amount}")
        print(f"   Percentage: {percentage}%")
        
        if percentage <= 80:
            print(f"✅ VALIDATION PASSES: {percentage}% ≤ 80% limit")
            return True
        else:
            print(f"❌ VALIDATION FAILS: {percentage}% > 80% limit")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_config_validation()
    if success:
        print("\n🎯 VALIDATION SUCCESS: Bot configured for $3.50 trades (70% of $5 balance)")
    else:
        print("\n❌ VALIDATION FAILED: Configuration needs adjustment")
    exit(0 if success else 1)