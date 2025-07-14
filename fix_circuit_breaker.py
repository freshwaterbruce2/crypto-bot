#!/usr/bin/env python3
"""
Quick fix for circuit breaker issues
"""

import os
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

def reset_circuit_breaker():
    """Reset circuit breaker state"""
    print("🔧 Resetting circuit breaker...")
    
    try:
        from src.utils.circuit_breaker import CircuitBreaker
        
        # Reset the circuit breaker
        circuit_breaker = CircuitBreaker("kraken_sdk_pro", failure_threshold=10, recovery_timeout=60)
        circuit_breaker.reset()
        
        print("✅ Circuit breaker reset successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting circuit breaker: {e}")
        return False

def clean_cache_files():
    """Clean problematic cache files"""
    print("🧹 Cleaning cache files...")
    
    try:
        import shutil
        
        # Remove cache directories
        for cache_dir in project_root.rglob("__pycache__"):
            try:
                shutil.rmtree(cache_dir)
            except:
                pass
        
        # Remove .pyc files
        for pyc_file in project_root.rglob("*.pyc"):
            try:
                pyc_file.unlink()
            except:
                pass
        
        print("✅ Cache cleaned successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning cache: {e}")
        return False

def main():
    """Main entry point"""
    print("🚀 QUICK FIXES FOR BOT ISSUES")
    print("=" * 40)
    
    # Set environment to prevent cache issues
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    success = True
    
    # Clean cache
    if not clean_cache_files():
        success = False
    
    # Reset circuit breaker
    if not reset_circuit_breaker():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("✅ ALL FIXES APPLIED SUCCESSFULLY!")
        print("🚀 Bot should now run without issues")
        print("\nLaunch with: python3 scripts/live_launch.py")
    else:
        print("❌ Some fixes failed - check errors above")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())