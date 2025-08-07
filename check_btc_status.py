#!/usr/bin/env python3
"""
CHECK BTC TRADING STATUS
========================
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
print("BTC/USDT TRADING STATUS")
print("=" * 70)

# Get balance
balance = exchange.fetch_balance()
usdt = balance.get('USDT', {}).get('free', 0)
btc = balance.get('BTC', {}).get('free', 0)

# Get BTC price
ticker = exchange.fetch_ticker('BTC/USDT')
btc_price = ticker['last']
total_value = usdt + (btc * btc_price)

print("💰 CURRENT BALANCE:")
print(f"   USDT: ${usdt:.2f}")
print(f"   BTC: {btc:.6f} BTC")
print(f"   BTC Value: ${btc * btc_price:.2f}")
print(f"   TOTAL: ${total_value:.2f}")

# Market data
bid = ticker['bid']
ask = ticker['ask']
spread = (ask - bid) / bid * 100

print("\n📊 BTC MARKET:")
print(f"   Price: ${btc_price:,.2f}")
print(f"   Bid: ${bid:,.2f}")
print(f"   Ask: ${ask:,.2f}")
print(f"   Spread: {spread:.4f}% (ultra-tight!)")

# Check for recent BTC trades
print("\n📈 RECENT BTC TRADES:")
try:
    trades = exchange.fetch_my_trades('BTC/USDT', limit=5)
    if trades:
        for trade in trades:
            side = "🟢 BUY " if trade['side'] == 'buy' else "🔴 SELL"
            print(f"   {trade['datetime'][:19]} | {side} | "
                  f"{trade['amount']:.6f} BTC @ ${trade['price']:,.2f}")
    else:
        print("   No BTC trades yet")
except:
    print("   Error fetching trades")

# Check open orders
print("\n⏳ OPEN ORDERS:")
try:
    orders = exchange.fetch_open_orders('BTC/USDT')
    if orders:
        for order in orders:
            side = "🟢 BUY " if order['side'] == 'buy' else "🔴 SELL"
            print(f"   {side} | {order['amount']:.6f} BTC @ ${order['price']:,.2f}")
    else:
        print("   No open orders")
except:
    print("   Error fetching orders")

print("=" * 70)
