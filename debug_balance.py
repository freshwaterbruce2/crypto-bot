#!/usr/bin/env python3
"""Debug balance loading issue"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

async def test_balance():
    """Test balance loading directly"""
    from src.exchange.native_kraken_exchange import NativeKrakenExchange
    from src.trading.unified_balance_manager import UnifiedBalanceManager
    
    # Create exchange
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    exchange = NativeKrakenExchange(api_key, api_secret)
    await exchange.connect()  # Connect first!
    
    # Create balance manager
    balance_mgr = UnifiedBalanceManager(exchange, None)
    await balance_mgr.initialize()
    
    # Get USDT balance
    usdt_balance = await balance_mgr.get_balance('USDT')
    print(f"USDT Balance: ${usdt_balance:.2f}")
    
    # Get all balances
    all_balances = await balance_mgr.get_all_balances()
    print(f"\nAll non-zero balances:")
    for asset, balance in all_balances.items():
        print(f"  {asset}: {balance}")
    
    # Check raw balance data
    raw_balance = await exchange.fetch_balance()
    print(f"\nRaw balance keys: {list(raw_balance.keys())}")
    
    # Check for USDT variants
    for key in raw_balance:
        if 'USDT' in str(key).upper() or 'USD' in str(key).upper():
            print(f"  Found {key}: {raw_balance[key]}")

if __name__ == "__main__":
    asyncio.run(test_balance())