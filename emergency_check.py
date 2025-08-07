#!/usr/bin/env python3
"""
EMERGENCY POSITION CHECK
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
print("EMERGENCY POSITION ANALYSIS")
print("=" * 70)

# Get ticker
ticker = exchange.fetch_ticker('SHIB/USDT')
price = ticker['last']
high = ticker['high']
low = ticker['low']
bid = ticker['bid']
ask = ticker['ask']
spread = (ask - bid) / bid * 100

# Get balance
balance = exchange.fetch_balance()
usdt = balance.get('USDT', {}).get('free', 0)
shib = balance.get('SHIB', {}).get('free', 0)

print("\n📊 MARKET DATA:")
print(f"   Current: ${price:.8f}")
print(f"   24h High: ${high:.8f}")
print(f"   24h Low: ${low:.8f}")
print(f"   Bid: ${bid:.8f}")
print(f"   Ask: ${ask:.8f}")
print(f"   Spread: {spread:.3f}%")

# Calculate position
if high > low:
    range_position = (price - low) / (high - low) * 100
else:
    range_position = 50

print("\n📍 PRICE POSITION:")
print(f"   Position in range: {range_position:.1f}%")
if range_position > 90:
    print("   ⚠️ DANGER: Price at DAILY HIGH!")
elif range_position < 10:
    print("   ✅ GOOD: Price at daily low")
else:
    print("   Price is in middle of range")

print("\n💰 YOUR POSITION:")
print(f"   SHIB: {shib:,.0f}")
print(f"   USDT: ${usdt:.2f}")
print(f"   Value at bid: ${shib * bid:.2f}")
print(f"   Value at ask: ${shib * ask:.2f}")

# Estimate entry price (working backwards)
if shib > 0:
    # You have 2,008,828 SHIB
    estimated_entry = price  # Current price as baseline
    profit_at_bid = 0

    print("\n📈 IF YOU SELL NOW:")
    print(f"   You'll get bid price: ${bid:.8f}")
    print(f"   Total: ${shib * bid:.2f}")
    print(f"   Spread loss: ${shib * (ask-bid):.2f}")

print("\n⚠️ RECOMMENDATIONS:")
if range_position > 80:
    print("   1. DO NOT BUY - Price at daily HIGH!")
    print("   2. Consider selling if you have any profit")
    print("   3. Wait for price to drop to 50% or below")
elif range_position < 30:
    print("   1. Good buying opportunity")
    print("   2. Hold existing positions")
else:
    print("   1. Neutral zone - be patient")
    print("   2. Wait for better entry/exit")

# Check if high/low are realistic
price_range = (high - low) / low * 100
print(f"\n📊 DAILY RANGE: {price_range:.2f}%")
if price_range < 0.1:
    print("   ⚠️ VERY TIGHT RANGE - Data might be stale")
    print("   High and low are almost identical!")

print("=" * 70)
