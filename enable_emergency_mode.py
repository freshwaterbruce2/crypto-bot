#!/usr/bin/env python3
"""
Enable Emergency Mode for Ultra-Low Confidence Trading

This script enables emergency mode which lowers confidence thresholds to 0.1
to allow more signals through when the bot is being too conservative.
"""

import json
import sys
from pathlib import Path

def enable_emergency_mode():
    """Enable emergency mode in config.json"""
    config_path = Path("config.json")
    
    if not config_path.exists():
        print("❌ config.json not found!")
        return False
    
    try:
        # Read config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Enable emergency mode
        config['emergency_mode'] = True
        
        # Ensure confidence thresholds are set correctly
        if 'confidence_thresholds' not in config.get('advanced_strategy_params', {}):
            if 'advanced_strategy_params' not in config:
                config['advanced_strategy_params'] = {}
            config['advanced_strategy_params']['confidence_thresholds'] = {}
        
        thresholds = config['advanced_strategy_params']['confidence_thresholds']
        thresholds['emergency'] = 0.1
        thresholds['buy'] = 0.3
        thresholds['sell'] = 0.2
        
        # Write back
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✅ Emergency mode ENABLED!")
        print("   - Emergency threshold: 0.1 (10%)")
        print("   - Buy threshold: 0.3 (30%)")
        print("   - Sell threshold: 0.2 (20%)")
        print("\n⚠️  WARNING: This will allow many more signals through!")
        print("   Monitor closely and disable if too many false signals occur.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error enabling emergency mode: {e}")
        return False

def disable_emergency_mode():
    """Disable emergency mode in config.json"""
    config_path = Path("config.json")
    
    if not config_path.exists():
        print("❌ config.json not found!")
        return False
    
    try:
        # Read config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Disable emergency mode
        config['emergency_mode'] = False
        
        # Write back
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✅ Emergency mode DISABLED!")
        print("   Returned to normal confidence thresholds.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error disabling emergency mode: {e}")
        return False

def check_status():
    """Check current emergency mode status"""
    config_path = Path("config.json")
    
    if not config_path.exists():
        print("❌ config.json not found!")
        return
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        emergency_mode = config.get('emergency_mode', False)
        thresholds = config.get('advanced_strategy_params', {}).get('confidence_thresholds', {})
        
        print(f"\n📊 Current Status:")
        print(f"   Emergency Mode: {'ENABLED' if emergency_mode else 'DISABLED'}")
        print(f"   Min Confidence: {config.get('min_confidence_threshold', 'Not set')}")
        print(f"\n   Thresholds:")
        print(f"   - Emergency: {thresholds.get('emergency', 'Not set')}")
        print(f"   - Buy: {thresholds.get('buy', 'Not set')}")
        print(f"   - Sell: {thresholds.get('sell', 'Not set')}")
        print(f"   - Minimum: {thresholds.get('minimum', 'Not set')}")
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "enable":
            enable_emergency_mode()
        elif command == "disable":
            disable_emergency_mode()
        elif command == "status":
            check_status()
        else:
            print("Usage: python enable_emergency_mode.py [enable|disable|status]")
    else:
        # Default to enable
        print("🚨 ENABLING EMERGENCY MODE...")
        enable_emergency_mode()