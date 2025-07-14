#!/usr/bin/env python3
"""
Force refresh balance cache
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

async def force_refresh():
    """Force refresh the balance cache"""
    try:
        from src.exchange.native_kraken_exchange import NativeKrakenExchange
        from src.trading.unified_balance_manager import UnifiedBalanceManager
        
        # Get credentials
        api_key = os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_API_SECRET', '')
        
        if not api_key or not api_secret:
            print("ERROR: Missing API credentials!")
            return
        
        # Create exchange
        print("Creating exchange...")
        exchange = NativeKrakenExchange(
            api_key=api_key,
            api_secret=api_secret,
            tier='starter'
        )
        
        if not await exchange.connect():
            print("Failed to connect to exchange!")
            return
        
        # Create balance manager
        print("Creating balance manager...")
        balance_manager = UnifiedBalanceManager(exchange)
        
        # Clear any bad cache
        print("Clearing balance cache...")
        balance_manager.clear_balance_cache()
        
        # Force fetch balance
        print("Fetching fresh balance...")
        balance = await balance_manager.get_balance(force_refresh=True)
        
        print(f"\nBalance fetched successfully!")
        print(f"USDT balance: ${await balance_manager.get_balance_for_asset('USDT'):.2f}")
        
        # Show all non-zero balances
        print("\nAll balances:")
        for currency, amount in balance.items():
            if currency in ['info', 'free', 'used', 'total']:
                continue
            if isinstance(amount, (int, float)) and amount > 0:
                print(f"  {currency}: {amount}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== Force Balance Refresh Tool ===")
    asyncio.run(force_refresh())