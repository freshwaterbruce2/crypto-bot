#!/usr/bin/env python3
"""Debug balance detection issue"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

async def debug_balances():
    """Debug balance detection"""
    from src.core.bot import KrakenTradingBot
    from src.config import load_config
    
    print("Loading config...")
    config = load_config()
    
    print("Creating bot instance...")
    bot = KrakenTradingBot(config)
    await bot.initialize()
    
    print("Getting exchange...")
    exchange = bot.exchange
    
    print("Fetching balance...")
    balance = await exchange.fetch_balance()
    
    print("\n=== BALANCE STRUCTURE ===")
    print(f"Balance keys: {list(balance.keys())}")
    
    print("\n=== ASSETS WITH BALANCES ===")
    for key, value in balance.items():
        if key not in ['info', 'free', 'used', 'total', 'timestamp']:
            if isinstance(value, (int, float)) and value > 0:
                print(f"{key}: {value}")
    
    print("\n=== CHECKING SPECIFIC ASSETS ===")
    assets_to_check = ['ALGO', 'ATOM', 'AVAX', 'AI16Z', 'BERA', 'SOL']
    for asset in assets_to_check:
        if asset in balance:
            print(f"{asset}: {balance[asset]}")
        else:
            print(f"{asset}: NOT FOUND in balance dict")
    
    print("\n=== CHECKING FREE/TOTAL STRUCTURE ===")
    if 'free' in balance and isinstance(balance['free'], dict):
        print("Free balances:")
        for asset, amount in balance['free'].items():
            if amount > 0:
                print(f"  {asset}: {amount}")
    
    if 'total' in balance and isinstance(balance['total'], dict):
        print("\nTotal balances:")
        for asset, amount in balance['total'].items():
            if amount > 0:
                print(f"  {asset}: {amount}")

if __name__ == "__main__":
    asyncio.run(debug_balances())