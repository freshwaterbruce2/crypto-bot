#!/usr/bin/env python3
"""
TEST BUY SMALL BTC
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

# Check balance
balance = exchange.fetch_balance()
usdt = balance.get('USDT', {}).get('free', 0)
print(f"USDT Balance: ${usdt:.2f}")

# Get BTC price
ticker = exchange.fetch_ticker('BTC/USDT')
print(f"BTC Price: ${ticker['last']:,.2f}")

# Calculate tiny amount
btc_amount = 20 / ticker['last']  # $20 worth
btc_amount = round(btc_amount, 6)
print(f"Will buy: {btc_amount:.6f} BTC (~$20)")

if usdt >= 20:
    print("\nPlacing order...")
    try:
        order = exchange.create_market_buy_order('BTC/USDT', btc_amount)
        print(f"✅ SUCCESS! Order ID: {order['id']}")
        print(f"Bought {btc_amount:.6f} BTC")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ Not enough USDT")
