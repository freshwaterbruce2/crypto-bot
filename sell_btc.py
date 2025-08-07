#!/usr/bin/env python3
"""
SELL BTC POSITION
"""

import os

import ccxt
from dotenv import load_dotenv

load_dotenv()

exchange = ccxt.kraken({
    'apiKey': os.getenv('KRAKEN_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True
})

# Get balance
balance = exchange.fetch_balance()
btc = balance.get('BTC', {}).get('free', 0)

print(f"BTC Balance: {btc:.8f}")

if btc > 0:
    ticker = exchange.fetch_ticker('BTC/USDT')
    value = btc * ticker['bid']
    print(f"Value at bid: ${value:.2f}")
    print(f"Current bid: ${ticker['bid']:,.2f}")

    print("\nSelling BTC...")
    try:
        order = exchange.create_market_sell_order('BTC/USDT', btc)
        print(f"✅ SOLD {btc:.8f} BTC")
        print(f"Order ID: {order['id']}")

        # Check new balance
        balance = exchange.fetch_balance()
        usdt = balance.get('USDT', {}).get('free', 0)
        print(f"\nNew USDT balance: ${usdt:.2f}")

    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("No BTC to sell")
