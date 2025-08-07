#!/usr/bin/env python3
"""
Monitor BTC Adaptive Scalper
"""

import json
import os
from datetime import datetime

import ccxt
from dotenv import load_dotenv

load_dotenv()

# Check position file
position_file = 'btc_adaptive_position.json'
if os.path.exists(position_file):
    with open(position_file) as f:
        position = json.load(f)
    print("📂 ACTIVE POSITION:")
    print(f"   Amount: {position['amount']:.6f} BTC")
    print(f"   Entry: ${position['price']:,.2f}")
    print(f"   Time: {datetime.fromtimestamp(position['time']).strftime('%H:%M:%S')}")
else:
    print("📂 No active position")

# Check market
exchange = ccxt.kraken({
    'apiKey': os.getenv('KRAKEN_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True
})

# Get ticker
ticker = exchange.fetch_ticker('BTC/USDT')
price = ticker['last']
bid = ticker['bid']
ask = ticker['ask']
high = ticker['high']
low = ticker['low']
spread = (ask - bid) / bid

# Get balance
balance = exchange.fetch_balance()
usdt = balance.get('USDT', {}).get('free', 0)
btc = balance.get('BTC', {}).get('free', 0)

# Calculate range position
if high > low:
    range_pos = (price - low) / (high - low)
else:
    range_pos = 0.5

print("\n📊 MARKET STATUS:")
print(f"   BTC: ${price:,.2f}")
print(f"   Range Position: {range_pos:.1%}")
print(f"   Spread: {spread:.4%}")

print("\n💰 BALANCE:")
print(f"   USDT: ${usdt:.2f}")
print(f"   BTC: {btc:.6f}")
print(f"   Total: ${usdt + btc * price:.2f}")

# Check if position exists and calculate P&L
if os.path.exists(position_file):
    with open(position_file) as f:
        position = json.load(f)
    profit = (bid - position['price']) / position['price']
    hold_time = (datetime.now().timestamp() - position['time']) / 60
    print("\n📈 POSITION P&L:")
    print(f"   Profit: {profit:.4%}")
    print(f"   Hold Time: {hold_time:.1f} minutes")
    print(f"   If sold at bid: ${position['amount'] * bid:.2f}")
