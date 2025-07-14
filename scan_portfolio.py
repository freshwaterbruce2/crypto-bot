#!/usr/bin/env python3
"""
Direct Portfolio Scanner - Find and analyze deployed capital
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fix the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from src.exchange.native_kraken_exchange import NativeKrakenExchange as KrakenExchange
    from src.config import load_config
except ImportError:
    # Try alternative import
    sys.path.insert(0, os.path.join(current_dir, 'src'))
    from exchange.native_kraken_exchange import NativeKrakenExchange as KrakenExchange
    from config import load_config

from datetime import datetime

async def scan_portfolio():
    """Scan portfolio and identify reallocation opportunities"""
    
    print("=" * 80)
    print(f"PORTFOLIO SCANNER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Load config and create client
        print("\n[INIT] Loading configuration...")
        config = load_config()
        
        print("[INIT] Creating Kraken client...")
        api_key = os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_SECRET_KEY', '')
        client = KrakenExchange(api_key, api_secret)
        
        # Connect to exchange
        connected = await client.connect()
        if not connected:
            print("[ERROR] Failed to connect to Kraken")
            return
        
        # Get all balances
        print("\n[SCAN] Fetching account balances...")
        balance_data = await client.fetch_balance()
        balances = balance_data.get('free', {})
        
        # Process holdings
        holdings = []
        total_value = 0.0
        
        print("\n[HOLDINGS] Found balances:")
        for asset, balance in balances.items():
            if float(balance) > 0.0001:
                print(f"  - {asset}: {balance}")
                
                # Get USD value
                usd_value = 0.0
                price = 0.0
                
                # Try to get price
                if asset == 'USDT':
                    usd_value = float(balance)
                    price = 1.0
                else:
                    # Try USDT pair
                    try:
                        ticker = await client.fetch_ticker(f"{asset}/USDT")
                        if ticker and 'last' in ticker:
                            price = ticker['last']
                            usd_value = float(balance) * price
                    except:
                        # Try USD pair
                        try:
                            ticker = await client.fetch_ticker(f"{asset}/USD")
                            if ticker and 'last' in ticker:
                                price = ticker['last']
                                usd_value = float(balance) * price
                        except:
                            pass
                
                holdings.append({
                    'asset': asset,
                    'balance': float(balance),
                    'price': price,
                    'value': usd_value
                })
                
                if usd_value > 0:
                    total_value += usd_value
        
        # Display results
        print(f"\n[SUMMARY] Total Portfolio Value: ${total_value:.2f}")
        print("\n[DETAILED HOLDINGS]")
        
        # Sort by value
        holdings.sort(key=lambda x: x['value'], reverse=True)
        
        for h in holdings:
            if h['value'] > 0:
                print(f"{h['asset']:10s} | Balance: {h['balance']:12.6f} | Price: ${h['price']:10.4f} | Value: ${h['value']:10.2f}")
        
        # Identify reallocation candidates
        print("\n[REALLOCATION ANALYSIS]")
        print("Assets that could be sold for USDT to enable trading:")
        
        realloc_candidates = []
        for h in holdings:
            if h['asset'] != 'USDT' and h['value'] > 5:  # Worth more than $5
                realloc_candidates.append(h)
                print(f"  - Sell {h['asset']}: Would provide ${h['value']:.2f} USDT")
        
        if not realloc_candidates and total_value < 10:
            print("\n[WARNING] No significant holdings found. You may need to deposit funds.")
        elif total_value > 0:
            print(f"\n[RECOMMENDATION] You have ${total_value:.2f} deployed that could be reallocated.")
            
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(scan_portfolio())
