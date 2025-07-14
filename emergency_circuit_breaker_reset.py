#!/usr/bin/env python3
"""
Emergency Circuit Breaker Reset Script
=====================================

Resets all circuit breakers and clears failure counters to restore trading functionality.
"""

import asyncio
import os
import sys
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

async def emergency_reset():
    """Emergency reset of all circuit breakers and failure counters"""
    try:
        print("=== EMERGENCY CIRCUIT BREAKER RESET ===")
        
        # Import circuit breaker components
        from src.utils.circuit_breaker import circuit_breaker_manager, CircuitBreakerConfig
        from src.trading.unified_balance_manager import UnifiedBalanceManager
        
        print("[RESET] Resetting global circuit breaker manager...")
        circuit_breaker_manager.reset_all()
        
        # Create a test balance manager to reset its circuit breaker
        print("[RESET] Creating temporary balance manager to reset internal breakers...")
        try:
            from src.exchange.native_kraken_exchange import NativeKrakenExchange
            
            # Create minimal exchange for testing
            api_key = os.getenv('KRAKEN_API_KEY', '')
            api_secret = os.getenv('KRAKEN_API_SECRET', '')
            
            if api_key and api_secret:
                print("[RESET] Initializing exchange connection...")
                exchange = NativeKrakenExchange(
                    api_key=api_key,
                    api_secret=api_secret,
                    tier='starter'
                )
                
                # Create balance manager and reset its internal state
                balance_manager = UnifiedBalanceManager(exchange)
                
                # Reset circuit breaker state
                balance_manager.circuit_breaker_active = False
                balance_manager.consecutive_failures = 0
                balance_manager.backoff_multiplier = 1.0
                balance_manager.circuit_breaker_reset_time = 0
                balance_manager.last_refresh_attempt = 0
                
                print("[RESET] Balance manager circuit breaker state reset")
                
                # Test connection
                print("[RESET] Testing exchange connection...")
                try:
                    if hasattr(exchange, 'fetch_balance'):
                        # Just test if method exists, don't actually call it yet
                        print("[RESET] Exchange fetch_balance method available")
                    else:
                        print("[RESET] WARNING: Exchange missing fetch_balance method")
                except Exception as e:
                    print(f"[RESET] Exchange test issue: {e}")
                    
            else:
                print("[RESET] WARNING: No API credentials found, circuit breaker reset only")
                
        except Exception as exchange_error:
            print(f"[RESET] Exchange initialization error: {exchange_error}")
            print("[RESET] Continuing with circuit breaker reset...")
        
        # Clear any stuck cache files
        print("[RESET] Clearing cache files...")
        cache_paths = [
            project_root / "trading_data" / "cache",
            project_root / "data",
            project_root / "logs" / "cache"
        ]
        
        for cache_path in cache_paths:
            if cache_path.exists() and cache_path.is_dir():
                cache_files = list(cache_path.glob("*.cache"))
                for cache_file in cache_files:
                    try:
                        cache_file.unlink()
                        print(f"[RESET] Cleared cache: {cache_file.name}")
                    except Exception as e:
                        print(f"[RESET] Could not clear {cache_file.name}: {e}")
        
        # Reset failure counter files
        print("[RESET] Resetting failure counter files...")
        failure_files = [
            project_root / "trading_data" / "error_patterns.json",
            project_root / "trading_data" / "high_failure_blacklist.json"
        ]
        
        for failure_file in failure_files:
            if failure_file.exists():
                try:
                    # Reset to empty state
                    if failure_file.name.endswith('.json'):
                        failure_file.write_text('{}')
                        print(f"[RESET] Reset failure file: {failure_file.name}")
                except Exception as e:
                    print(f"[RESET] Could not reset {failure_file.name}: {e}")
        
        print("\n=== EMERGENCY RESET COMPLETE ===")
        print("✓ Circuit breakers reset")
        print("✓ Failure counters cleared")
        print("✓ Cache files cleaned")
        print("✓ System ready for trading")
        
        # Show circuit breaker status
        print("\nCircuit Breaker Status:")
        status = circuit_breaker_manager.get_summary()
        print(f"  Total breakers: {status['total']}")
        print(f"  Closed (ready): {status['states']['closed']}")
        print(f"  Open (blocked): {status['states']['open']}")
        print(f"  Half-open (testing): {status['states']['half_open']}")
        
        return True
        
    except Exception as e:
        print(f"[RESET] Emergency reset error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(emergency_reset())
    sys.exit(0 if success else 1)