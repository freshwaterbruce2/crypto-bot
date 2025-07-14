#!/usr/bin/env python3
"""
Quick sell script to liquidate positions with proper nonce handling
"""
import asyncio
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from src.exchange.native_kraken_exchange import NativeKrakenExchange

async def main():
    """Quick sell positions"""
    try:
        # Get API credentials from environment
        api_key = os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_API_SECRET', '')
        
        if not api_key or not api_secret:
            print("Missing API credentials in environment")
            return
        
        print(f"Using API key: {api_key[:8]}...")
        
        # Initialize exchange with fresh nonce
        exchange = NativeKrakenExchange(api_key, api_secret, 'pro')
        
        # Add delay to ensure different nonce
        time.sleep(2)
        
        if not await exchange.connect():
            print("Failed to connect to exchange")
            return
        
        # Load markets
        await exchange.load_markets()
        
        # Get balance with retry
        max_retries = 3
        balance = None
        
        for attempt in range(max_retries):
            try:
                print(f"\nAttempt {attempt + 1} to fetch balance...")
                balance = await exchange.fetch_balance()
                if balance:
                    break
            except Exception as e:
                print(f"Balance fetch error: {e}")
                if "nonce" in str(e).lower():
                    print("Nonce error - waiting 10 seconds...")
                    await asyncio.sleep(10)
                else:
                    raise
        
        if not balance:
            print("Failed to fetch balance after retries")
            return
            
        print("\nCurrent Holdings:")
        positions = []
        
        # Find all non-USDT holdings
        for asset, amount in balance.get('total', {}).items():
            if amount > 0 and asset not in ['USDT', 'USD', 'EUR', 'info', 'free', 'used', 'total']:
                # Normalize asset
                normalized = exchange._normalize_currency(asset)
                
                # Skip if too small
                if amount < 0.0001:
                    continue
                
                # Try to get value
                try:
                    symbol = f"{normalized}/USDT"
                    ticker = await exchange.fetch_ticker(symbol)
                    price = ticker.get('last', 0)
                    value = amount * price
                    
                    print(f"  - {normalized}: {amount:.8f} @ ${price:.6f} = ${value:.2f}")
                    
                    if value >= 1.0:  # Only sell if worth $1+
                        positions.append({
                            'asset': asset,
                            'normalized': normalized,
                            'symbol': symbol,
                            'amount': amount,
                            'price': price,
                            'value': value
                        })
                except Exception as e:
                    print(f"  - {normalized}: {amount:.8f} (price error: {e})")
        
        if not positions:
            print("\n[OK] No positions to sell")
            return
        
        print(f"\n[SELL] Found {len(positions)} positions to liquidate")
        
        # Sell each position
        for pos in positions:
            print(f"\n[SELLING] {pos['normalized']} - ${pos['value']:.2f}")
            print(f"   Symbol: {pos['symbol']}")
            print(f"   Amount: {pos['amount']:.8f}")
            
            try:
                # Add delay between orders
                await asyncio.sleep(2)
                
                order = await exchange.create_order(
                    symbol=pos['symbol'],
                    side='sell',
                    amount=pos['amount'],
                    order_type='market'
                )
                
                if order and order.get('id'):
                    print(f"   [OK] Sell order created! Order ID: {order['id']}")
                else:
                    print(f"   [ERROR] Failed to create sell order")
                    
            except Exception as e:
                print(f"   [ERROR] Error creating order: {e}")
        
        await exchange.close()
        print("\n[DONE] Sell script completed")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())