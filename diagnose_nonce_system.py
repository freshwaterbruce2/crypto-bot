#!/usr/bin/env python3
"""
Nonce Diagnostic and Monitoring Script
=====================================

This script provides ongoing monitoring and diagnostics for nonce management
to prevent future "EAPI:Invalid nonce" errors.
"""

import sys
import time
import json
import asyncio
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.unified_kraken_nonce_manager import get_unified_nonce_manager


def run_nonce_diagnostics():
    """Run comprehensive nonce diagnostics"""
    print("🔍 NONCE DIAGNOSTIC REPORT")
    print("=" * 50)
    
    try:
        manager = get_unified_nonce_manager()
        status = manager.get_status()
        
        print(f"Current Nonce: {status['current_nonce']}")
        print(f"Total Generated: {status['total_generated']}")
        print(f"Error Recoveries: {status['error_recoveries']}")
        print(f"Active Connections: {status['active_connections']}")
        print(f"Time Until Current: {status['time_until_current']:.2f}s")
        print(f"State File: {status['state_file']}")
        
        # Test nonce sequence
        print("\n🧪 Testing Nonce Sequence:")
        nonces = []
        for i in range(5):
            nonce = manager.get_nonce(f"diagnostic_test_{i}")
            nonces.append(int(nonce))
            print(f"  Nonce {i+1}: {nonce}")
            time.sleep(0.01)
        
        # Verify sequence
        is_increasing = all(nonces[i] < nonces[i+1] for i in range(len(nonces)-1))
        print(f"  Sequence Valid: {'✅ YES' if is_increasing else '❌ NO'}")
        
        print("\n✅ Diagnostic completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        return False


if __name__ == "__main__":
    success = run_nonce_diagnostics()
    sys.exit(0 if success else 1)
