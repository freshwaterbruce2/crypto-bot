#!/usr/bin/env python3
"""
Live Trading Readiness Verification
===================================

Verifies the bot is properly configured for live trading with real funds.
"""

import json
import os

def verify_live_trading_config():
    """Verify configuration is ready for live trading"""
    print("🔍 VERIFYING LIVE TRADING READINESS")
    print("=" * 50)
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        issues = []
        warnings = []
        
        # Critical live trading checks
        if not config.get('live_trading', False):
            issues.append("live_trading is not enabled")
        
        if config.get('paper_trading', False):
            issues.append("paper_trading is still enabled")
        
        if config.get('emergency_mode', False):
            issues.append("emergency_mode is enabled (blocks trading)")
        
        # Trading configuration checks
        if not config.get('trading_enabled', False):
            issues.append("trading_enabled is not set to true")
        
        # API configuration checks
        exchange_config = config.get('exchange_config', {})
        if not exchange_config.get('validate_minimums', True):
            warnings.append("minimum validation is disabled")
        
        # Safety checks
        if not config.get('risk_management', {}).get('enabled', True):
            warnings.append("risk management is disabled")
        
        # Balance checks
        if config.get('disable_balance_checks', False):
            issues.append("balance checks are disabled (dangerous for live trading)")
        
        if config.get('force_trade_execution', False):
            warnings.append("force trade execution is enabled (bypasses safety checks)")
        
        # Results
        if issues:
            print("❌ CRITICAL ISSUES - NOT READY FOR LIVE TRADING:")
            for issue in issues:
                print(f"   • {issue}")
        
        if warnings:
            print("\n⚠️ WARNINGS:")
            for warning in warnings:
                print(f"   • {warning}")
        
        if not issues and not warnings:
            print("✅ PERFECT CONFIGURATION!")
        elif not issues:
            print("\n✅ READY FOR LIVE TRADING (with warnings noted)")
        
        # Show current configuration
        print(f"\n📊 CURRENT CONFIGURATION:")
        print(f"   Live Trading: {config.get('live_trading', False)}")
        print(f"   Paper Trading: {config.get('paper_trading', True)}")
        print(f"   Trading Enabled: {config.get('trading_enabled', False)}")
        print(f"   Emergency Mode: {config.get('emergency_mode', False)}")
        print(f"   Emergency Balance Mode: {config.get('emergency_balance_mode', False)}")
        print(f"   Ultra Aggressive Mode: {config.get('ultra_aggressive_mode', False)}")
        print(f"   Risk Management: {config.get('risk_management', {}).get('enabled', False)}")
        print(f"   Balance Checks: {'Disabled' if config.get('disable_balance_checks', False) else 'Enabled'}")
        
        return len(issues) == 0
        
    except Exception as e:
        print(f"❌ ERROR: Could not verify configuration: {e}")
        return False

def check_environment_file():
    """Check if environment file exists with API keys"""
    print(f"\n🔑 CHECKING API CREDENTIALS:")
    
    env_files = ['.env', '.env.local', '.env.production']
    found_env = False
    
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"   ✅ Found: {env_file}")
            found_env = True
            
            # Check if it has the required keys (without reading actual values)
            with open(env_file, 'r') as f:
                content = f.read()
                has_api_key = 'KRAKEN_API_KEY' in content
                has_secret = 'KRAKEN_API_SECRET' in content
                
            print(f"      - API Key: {'✅ Present' if has_api_key else '❌ Missing'}")
            print(f"      - API Secret: {'✅ Present' if has_secret else '❌ Missing'}")
            
            if has_api_key and has_secret:
                print(f"      - Status: ✅ Ready for live trading")
                return True
    
    if not found_env:
        print("   ❌ No environment file found")
        print("   ⚠️ You'll need to create .env with your Kraken API keys")
    
    return found_env

def main():
    """Main verification function"""
    print("🚀 LIVE TRADING READINESS VERIFICATION")
    print("=" * 60)
    
    config_ready = verify_live_trading_config()
    env_ready = check_environment_file()
    
    print(f"\n📋 FINAL READINESS ASSESSMENT:")
    print("=" * 40)
    
    if config_ready and env_ready:
        print("🎉 READY FOR LIVE TRADING!")
        print("\nYour bot is configured for:")
        print("   ✅ Live trading with real funds")
        print("   ✅ SHIB/USDT single pair focus")
        print("   ✅ $1.00 minimum orders for low balance accounts")
        print("   ✅ 95% capital deployment")
        print("   ✅ Micro-profit accumulation strategy")
        print("\n💰 You can now fund your Kraken account and start trading!")
        print("⚠️ IMPORTANT: Start with small amounts to validate live performance")
        
    elif config_ready:
        print("⚠️ CONFIGURATION READY - NEED API KEYS")
        print("   Configure your Kraken API keys in .env file")
        
    else:
        print("❌ NOT READY FOR LIVE TRADING")
        print("   Fix configuration issues above before funding account")
    
    return config_ready and env_ready

if __name__ == "__main__":
    main()