#!/usr/bin/env python3
"""Debug exchange connection and nonce issues"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

async def test_connection():
    """Test exchange connection with proper error handling"""
    from src.exchange.native_kraken_exchange import NativeKrakenExchange
    
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    print(f"API Key present: {bool(api_key)}")
    print(f"API Secret present: {bool(api_secret)}")
    
    exchange = NativeKrakenExchange(api_key, api_secret)
    
    # Test 1: Check connection status
    print("\n1. Testing connection...")
    try:
        await exchange.connect()
        print("✓ Connected successfully")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # Test 2: Test API authentication with server time
    print("\n2. Testing API authentication...")
    try:
        # Get server time first (public endpoint)
        server_time = await exchange.fetch_server_time()
        print(f"✓ Server time: {server_time}")
        
        # Test private endpoint with proper nonce
        balance = await exchange.fetch_balance()
        print("✓ API authentication successful")
        
        # Show balance info
        if balance:
            print("\nRaw balance info:")
            for asset, amount in balance.items():
                if float(amount) > 0:
                    print(f"  {asset}: {amount}")
    except Exception as e:
        print(f"✗ API authentication failed: {e}")
        
        # Check for nonce error
        if 'nonce' in str(e).lower():
            print("\nNonce error detected. This usually means:")
            print("1. System time is out of sync")
            print("2. API key was used elsewhere with higher nonce")
            print("3. Multiple instances using same API key")
            
            # Try with manual nonce management
            print("\nAttempting with manual nonce...")
            try:
                # Force a new nonce by waiting
                await asyncio.sleep(2)
                balance = await exchange.fetch_balance()
                print("✓ Manual nonce retry successful")
                if balance:
                    for asset, amount in balance.items():
                        if float(amount) > 0:
                            print(f"  {asset}: {amount}")
            except Exception as e2:
                print(f"✗ Manual nonce retry failed: {e2}")
    
    # Test 3: Check exchange status
    print("\n3. Checking exchange status...")
    try:
        print(f"Exchange healthy: {exchange.is_healthy}")
        print(f"Session active: {exchange.session is not None}")
        print(f"Last successful request: {time.time() - exchange.last_successful_request:.1f}s ago")
    except Exception as e:
        print(f"Error checking status: {e}")
    
    # Test 4: Test balance manager integration
    print("\n4. Testing balance manager...")
    try:
        from src.trading.unified_balance_manager import UnifiedBalanceManager
        
        balance_mgr = UnifiedBalanceManager(exchange, None)
        await balance_mgr.initialize()
        
        usdt_balance = await balance_mgr.get_balance('USDT')
        print(f"✓ USDT Balance: ${usdt_balance:.2f}")
        
        all_balances = await balance_mgr.get_all_balances()
        print(f"✓ Found {len(all_balances)} non-zero balances")
        
    except Exception as e:
        print(f"✗ Balance manager test failed: {e}")
    
    # Close connection
    try:
        await exchange.close()
    except:
        pass

if __name__ == "__main__":
    asyncio.run(test_connection())