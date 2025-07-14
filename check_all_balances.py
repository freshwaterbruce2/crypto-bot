#!/usr/bin/env python3
"""Check all balances including Kraken-specific names"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def check_all_balances():
    from src.exchange.native_kraken_exchange import NativeKrakenExchange
    
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    exchange = NativeKrakenExchange(api_key, api_secret)
    await exchange.connect()
    
    print("=== Checking ALL Kraken Balances ===\n")
    
    try:
        # Get raw balance data
        balance_data = await exchange.fetch_balance()
        
        if not balance_data:
            print("No balance data returned")
        else:
            print(f"Found {len(balance_data)} assets in account:\n")
            
            # Group by type
            usd_variants = []
            crypto_assets = []
            
            for asset, amount in sorted(balance_data.items()):
                amount_float = float(amount)
                
                # Show ALL assets, even zero balance
                if 'USD' in asset.upper():
                    usd_variants.append((asset, amount_float))
                else:
                    crypto_assets.append((asset, amount_float))
                
                # Show non-zero with emphasis
                if amount_float > 0:
                    print(f"⭐ {asset}: {amount_float}")
            
            # Show USD variants
            print("\nUSD variants found:")
            for asset, amount in usd_variants:
                print(f"  {asset}: {amount}")
            
            # Show crypto with balance
            print("\nCrypto assets with balance:")
            has_crypto = False
            for asset, amount in crypto_assets:
                if amount > 0:
                    print(f"  {asset}: {amount}")
                    has_crypto = True
            
            if not has_crypto:
                print("  No crypto balances found")
            
            # Check specific expected assets
            print("\nChecking expected assets:")
            expected = ['ALGO', 'ATOM', 'AVAX', 'AI16Z', 'BERA', 'ADA', 'USDT', 'ZUSD', 'ZUSDT', 'USD']
            for asset in expected:
                if asset in balance_data:
                    amount = float(balance_data[asset])
                    if amount > 0:
                        print(f"  ✓ {asset}: {amount}")
                    else:
                        print(f"  - {asset}: 0")
                        
    except Exception as e:
        print(f"Error: {e}")
    
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(check_all_balances())