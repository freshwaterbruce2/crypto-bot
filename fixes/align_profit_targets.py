#!/usr/bin/env python3
"""
Align Profit Targets Fix
========================

This script aligns the profit targets between strategies and the autonomous sell engine
to ensure consistent micro-scalping behavior.

Target: 0.2% profit for ultra-fast turnover with fee-free advantage
"""

import json
import os
from pathlib import Path

def fix_profit_targets():
    """Align all profit targets to 0.2% for consistent micro-scalping."""
    
    print("[TARGET] Aligning Profit Targets for Maximum Turnover")
    print("=" * 60)
    
    # Fix 1: Update config.json
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update main profit targets
        config['take_profit_pct'] = 0.2  # Was 0.5
        config['profit_accumulation_target'] = 0.2  # Was 0.35
        
        # Update mean reversion config
        if 'mean_reversion_config' in config:
            config['mean_reversion_config']['take_profit_pct'] = 0.002  # 0.2%
        
        # Quantum strategy already at 0.5%, but let's make it 0.2% for consistency
        if 'quantum_strategy_config' in config:
            config['quantum_strategy_config']['profit_target_pct'] = 0.2
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("[OK] Updated config.json profit targets to 0.2%")
    
    # Fix 2: Update AutonomousSellEngine default
    sell_engine_path = Path(__file__).parent.parent / "src/strategies/autonomous_sell_engine.py"
    if sell_engine_path.exists():
        with open(sell_engine_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the default take_profit_pct in SellEngineConfig
        content = content.replace(
            "take_profit_pct: float = 0.5",
            "take_profit_pct: float = 0.2"
        )
        
        with open(sell_engine_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("[OK] Updated AutonomousSellEngine default to 0.2%")
    
    print("\n[COMPLETE] Profit Target Alignment Complete!")
    print("All components now use 0.2% profit targets for:")
    print("- [OK] Ultra-fast position turnover")
    print("- [OK] Maximum trades per day")
    print("- [OK] Compound profit accumulation")
    print("- [OK] Fee-free trading advantage")
    print("\n[READY] Ready for rapid micro-scalping!")

if __name__ == "__main__":
    fix_profit_targets()
