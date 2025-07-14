#!/usr/bin/env python3
"""
Emergency Portfolio Liquidation - Fresh Start
===========================================
Liquidates specific positions for fresh start with optimized pairs.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
load_dotenv()

async def liquidate_for_fresh_start():
    """Liquidate specific positions to enable fresh start"""
    
    print("="*60)
    print("EMERGENCY LIQUIDATION - FRESH START STRATEGY")
    print("="*60)
    
    # Import after path setup
    try:
        import ccxt.async_support as ccxt
    except ImportError:
        print("ERROR: ccxt not installed. Run: pip install ccxt")
        return
    
    # Get credentials
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    if not api_key or not api_secret:
        print("ERROR: Missing API credentials in .env file")
        return
    
    # Create exchange
    exchange = ccxt.kraken({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True
    })
    
    try:
        # Get current balance
        print("\n[1] Checking current balances...")
        balance = await exchange.fetch_balance()
        
        # Positions to liquidate (problematic high-minimum pairs)
        liquidation_targets = [
            "ALGO",  # ALGO/USDT - in avoid list  
            "ATOM",  # ATOM/USDT - in avoid list
            "AVAX"   # AVAX/USDT - in avoid list
        ]
        
        print("\n[2] Liquidating problematic positions...")
        liquidated_value = 0
        
        for asset in liquidation_targets:
            balance_amount = balance['total'].get(asset, 0)
            
            if balance_amount > 0.00001:  # Has meaningful balance
                try:
                    symbol = f"{asset}/USDT"
                    
                    # Get current price
                    ticker = await exchange.fetch_ticker(symbol)
                    price = ticker['last']
                    value = balance_amount * price
                    
                    print(f"\n  Selling {asset}:")
                    print(f"    Balance: {balance_amount:.8f}")
                    print(f"    Price: ${price:.4f}")
                    print(f"    Value: ${value:.2f}")
                    
                    if value >= 1.0:  # Only sell if worth $1+
                        # Execute market sell
                        order = await exchange.create_order(
                            symbol=symbol,
                            type='market',
                            side='sell', 
                            amount=balance_amount
                        )
                        
                        print(f"    ✅ SOLD - Order: {order.get('id', 'Unknown')}")
                        liquidated_value += value
                    else:
                        print(f"    ⏭️  SKIPPED - Value too small (${value:.2f})")
                        
                except Exception as e:
                    print(f"    ❌ FAILED to sell {asset}: {e}")
            else:
                print(f"\n  {asset}: No balance to sell")
        
        print(f"\n[3] Liquidation complete!")
        print(f"    Total liquidated value: ${liquidated_value:.2f}")
        
        # Check final USDT balance
        final_balance = await exchange.fetch_balance()
        usdt_balance = final_balance['total'].get('USDT', 0)
        print(f"    Final USDT balance: ${usdt_balance:.2f}")
        
        if usdt_balance >= 10:
            print("\n✅ SUCCESS: Sufficient USDT for optimized trading!")
            print("   Bot can now focus on TIER_1_PRIORITY_PAIRS:")
            print("   - SHIB/USDT, MATIC/USDT, AI16Z/USDT, BERA/USDT") 
            print("   - DOT/USDT, LINK/USDT, SOL/USDT, BTC/USDT")
        else:
            print("\n⚠️  Consider depositing additional USDT for optimal trading")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await exchange.close()

if __name__ == "__main__":
    print("This will liquidate ALGO, ATOM, and AVAX positions")
    print("These are in the avoid list due to high minimum requirements")
    print()
    
    response = input("Proceed with liquidation? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(liquidate_for_fresh_start())
    else:
        print("Liquidation cancelled")
