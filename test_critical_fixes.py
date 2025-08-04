#!/usr/bin/env python3
"""
Critical Fixes Validation Script
===============================

Quick validation script to test the emergency fixes applied to the trading bot:
1. Nonce system reset verification
2. PortfolioManager missing method fix
3. WebSocket message handler improvements
4. Balance manager REST fallback capability

This script runs basic tests without starting the full bot to verify fixes work.
"""

import asyncio
import json
import time
import sys
import os
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.portfolio.portfolio_manager import PortfolioManager
from src.websocket.kraken_v2_message_handler import KrakenV2MessageHandler
from src.balance.balance_manager_v2 import BalanceManagerV2


async def test_nonce_system():
    """Test if nonce system was properly reset"""
    print("=" * 60)
    print("Testing Nonce System Reset...")
    print("=" * 60)
    
    try:
        # Check if nonce file was updated
        nonce_file = "nonce_state_rYOFiSAo.json"
        if not os.path.exists(nonce_file):
            print("❌ FAIL: Nonce state file not found")
            return False
        
        with open(nonce_file, 'r') as f:
            nonce_data = json.load(f)
        
        current_time = int(time.time() * 1000000)
        last_nonce = nonce_data.get('last_nonce', 0)
        reset_reason = nonce_data.get('reset_reason', '')
        
        print(f"Current time (μs): {current_time}")
        print(f"Last nonce (μs):   {last_nonce}")
        print(f"Reset reason:      {reset_reason}")
        
        # Check if nonce was recently reset
        time_diff = current_time - last_nonce
        if time_diff < 120000000:  # Less than 2 minutes old
            print(f"✅ PASS: Nonce was recently reset ({time_diff/1000000:.1f}s ago)")
            return True
        else:
            print(f"⚠️  WARNING: Nonce is old ({time_diff/1000000:.1f}s ago)")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error testing nonce system: {e}")
        return False


def test_portfolio_manager_method():
    """Test if PortfolioManager has the missing method"""
    print("\n" + "=" * 60)
    print("Testing PortfolioManager Missing Method Fix...")
    print("=" * 60)
    
    try:
        # Check if the method exists
        if hasattr(PortfolioManager, 'force_sync_with_exchange'):
            print("✅ PASS: force_sync_with_exchange method exists")
            
            # Check if it's callable
            portfolio = PortfolioManager()
            if callable(getattr(portfolio, 'force_sync_with_exchange')):
                print("✅ PASS: force_sync_with_exchange method is callable")
                return True
            else:
                print("❌ FAIL: force_sync_with_exchange is not callable")
                return False
        else:
            print("❌ FAIL: force_sync_with_exchange method does not exist")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error testing PortfolioManager: {e}")
        return False


async def test_websocket_message_handler():
    """Test WebSocket message handler improvements"""
    print("\n" + "=" * 60)
    print("Testing WebSocket Message Handler Fixes...")
    print("=" * 60)
    
    try:
        handler = KrakenV2MessageHandler()
        
        # Test 1: Pong message handling
        pong_message = {
            "channel": "pong",
            "type": "pong",
            "method": "pong"
        }
        
        # This should not raise an exception
        await handler.process_message(pong_message)
        print("✅ PASS: Pong message processed without error")
        
        # Test 2: Status message with list data
        status_message = {
            "channel": "status",
            "type": "update",
            "data": [{"connection": {"status": "online"}}]  # List format
        }
        
        # This should not raise an exception
        await handler.process_message(status_message)
        print("✅ PASS: Status message with list data processed without error")
        
        # Test 3: Check if handler has pong handler method
        if hasattr(handler, '_handle_pong_message'):
            print("✅ PASS: _handle_pong_message method exists")
        else:
            print("❌ FAIL: _handle_pong_message method missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Error testing WebSocket handler: {e}")
        return False


def test_balance_manager_force_refresh():
    """Test if Balance Manager V2 has force_refresh method"""
    print("\n" + "=" * 60)
    print("Testing Balance Manager V2 Force Refresh...")
    print("=" * 60)
    
    try:
        # Check if the method exists
        if hasattr(BalanceManagerV2, 'force_refresh'):
            print("✅ PASS: force_refresh method exists in BalanceManagerV2")
            
            # Create instance without initialization to test method signature
            manager = BalanceManagerV2(None, None)
            if callable(getattr(manager, 'force_refresh')):
                print("✅ PASS: force_refresh method is callable")
                return True
            else:
                print("❌ FAIL: force_refresh is not callable")
                return False
        else:
            print("❌ FAIL: force_refresh method does not exist")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error testing BalanceManagerV2: {e}")
        return False


async def run_all_tests():
    """Run all critical fix tests"""
    print("CRYPTO TRADING BOT - CRITICAL FIXES VALIDATION")
    print("=" * 60)
    print("Testing emergency fixes applied to resolve bot startup issues...")
    print()
    
    test_results = []
    
    # Test 1: Nonce System Reset
    test_results.append(await test_nonce_system())
    
    # Test 2: Portfolio Manager Method Fix
    test_results.append(test_portfolio_manager_method())
    
    # Test 3: WebSocket Message Handler Fix
    test_results.append(await test_websocket_message_handler())
    
    # Test 4: Balance Manager Force Refresh
    test_results.append(test_balance_manager_force_refresh())
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL CRITICAL FIXES VALIDATED SUCCESSFULLY!")
        print("✅ The trading bot should now be able to start without the previous errors.")
        print("\nNext steps:")
        print("1. Run the bot with: python main.py")
        print("2. Monitor for any remaining issues")
        print("3. Check balance detection and trading functionality")
    else:
        print("⚠️  SOME FIXES NEED ATTENTION")
        print("❌ Bot may still have startup issues")
        print("\nRecommended actions:")
        print("1. Review failed tests above")
        print("2. Apply additional fixes as needed")
        print("3. Re-run this validation script")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during validation: {e}")
        sys.exit(1)