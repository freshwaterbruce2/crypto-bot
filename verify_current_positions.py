#!/usr/bin/env python3
"""
Verify Current Positions - Quick Balance Check
===========================================
Uses ccxt to quickly check current balances and positions.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

async def verify_positions():
    """Check current positions to verify liquidation analysis"""
    
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
        print("Make sure .env file exists with KRAKEN_API_KEY and KRAKEN_API_SECRET")
        return
    
    print("="*60)
    print("CURRENT POSITION VERIFICATION")
    print("="*60)
    
    # Create exchange
    exchange = ccxt.kraken({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True
    })
    
    try:
        # Get current balance
        print("\n[1] Fetching current balances...")
        balance = await exchange.fetch_balance()
        
        print("\n[2] Current Holdings:")
        print("-" * 50)
        
        total_usd_value = 0
        positions = []
        
        # Process all assets with balance
        for asset, amount in balance['total'].items():
            if amount > 0.00001:  # Has meaningful balance
                
                if asset in ['USDT', 'USD', 'ZUSD']:
                    # USD/USDT variants
                    usd_value = amount
                    print(f"  💰 {asset:8s}: {amount:12.2f} (${usd_value:.2f})")
                else:
                    # Try to get USD value for crypto assets
                    try:
                        symbol = f"{asset}/USDT"
                        ticker = await exchange.fetch_ticker(symbol)
                        price = ticker['last']
                        usd_value = amount * price
                        
                        # Determine status based on our analysis
                        if asset in ['ALGO', 'ATOM', 'AVAX']:
                            status = "🔴 LIQUIDATE"
                        elif asset in ['AI16Z', 'BERA', 'SOL']:
                            status = "🟢 KEEP"
                        else:
                            status = "🟡 REVIEW"
                        
                        print(f"  {status} {asset:8s}: {amount:12.6f} @ ${price:8.4f} = ${usd_value:8.2f}")
                        
                        positions.append({
                            'asset': asset,
                            'amount': amount,
                            'price': price,
                            'value': usd_value,
                            'status': status
                        })
                        
                    except Exception as e:
                        print(f"  ❓ {asset:8s}: {amount:12.6f} (price unavailable)")
                
                total_usd_value += usd_value if 'usd_value' in locals() else 0
        
        print("-" * 50)
        print(f"Total Portfolio Value: ${total_usd_value:.2f}")
        
        # Calculate liquidation potential
        liquidation_value = sum(p['value'] for p in positions if '🔴 LIQUIDATE' in p['status'])
        keep_value = sum(p['value'] for p in positions if '🟢 KEEP' in p['status'])
        
        usdt_available = balance['free'].get('USDT', 0)
        
        print(f"\n[3] Liquidation Analysis:")
        print(f"  Current USDT available: ${usdt_available:.2f}")
        print(f"  Positions to liquidate: ${liquidation_value:.2f}")
        print(f"  Positions to keep: ${keep_value:.2f}")
        print(f"  Expected USDT after liquidation: ${usdt_available + liquidation_value:.2f}")
        
        print(f"\n[4] Liquidation Targets:")
        for pos in positions:
            if '🔴 LIQUIDATE' in pos['status']:
                print(f"  - SELL {pos['asset']}: {pos['amount']:.6f} tokens → ${pos['value']:.2f}")
        
        print(f"\n[5] Positions to Keep:")
        for pos in positions:
            if '🟢 KEEP' in pos['status']:
                print(f"  - HOLD {pos['asset']}: {pos['amount']:.6f} tokens → ${pos['value']:.2f}")
        
        # Trading recommendation
        if usdt_available < 2.0:
            print(f"\n⚠️  TRADING BLOCKED: Only ${usdt_available:.2f} USDT available (need $2.00 minimum)")
            if liquidation_value > 0:
                print(f"✅ SOLUTION: Liquidate positions to free ${liquidation_value:.2f} USDT")
        else:
            print(f"\n✅ TRADING READY: ${usdt_available:.2f} USDT available")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(verify_positions())