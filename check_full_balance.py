#!/usr/bin/env python3
"""
CHECK FULL BALANCE
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

print("=" * 70)
print("FULL BALANCE CHECK")
print("=" * 70)

balance = exchange.fetch_balance()

# Check all possible USDT/USD variants
for key in ['USDT', 'ZUSDT', 'USD', 'ZUSD', 'USDC']:
    if key in balance:
        total = balance[key].get('total', 0)
        free = balance[key].get('free', 0)
        used = balance[key].get('used', 0)
        if total > 0:
            print(f"\n{key}:")
            print(f"  Total: ${total:.2f}")
            print(f"  Free: ${free:.2f}")
            print(f"  Used: ${used:.2f}")

# Check BTC
for key in ['BTC', 'XBT', 'XXBT']:
    if key in balance:
        total = balance[key].get('total', 0)
        if total > 0:
            print(f"\n{key}: {total:.8f}")

# Check for any other crypto
print("\nOther Assets:")
for currency, data in balance.items():
    if currency not in ['USDT', 'ZUSDT', 'USD', 'ZUSD', 'USDC', 'BTC', 'XBT', 'XXBT', 'info', 'free', 'used', 'total']:
        if data.get('total', 0) > 0:
            print(f"  {currency}: {data['total']}")

# Get open orders
print("\nChecking open orders...")
try:
    orders = exchange.fetch_open_orders()
    if orders:
        print(f"Found {len(orders)} open orders:")
        for order in orders:
            print(f"  {order['symbol']}: {order['side']} {order['amount']} @ ${order['price']}")
    else:
        print("No open orders")
except Exception as e:
    print(f"Error checking orders: {e}")
