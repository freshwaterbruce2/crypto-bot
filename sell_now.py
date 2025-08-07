#!/usr/bin/env python3
"""
SELL SHIB POSITION
==================
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
print("SELLING SHIB POSITION")
print("=" * 70)

# Get balance
balance = exchange.fetch_balance()
shib = balance.get('SHIB', {}).get('free', 0)

print(f"SHIB Balance: {shib:,.0f}")

if shib < 160000:
    print("❌ Not enough SHIB to sell (minimum 160,000)")
    exit()

# Get current price
ticker = exchange.fetch_ticker('SHIB/USDT')
bid = ticker['bid']
print(f"Current Bid: ${bid:.8f}")
print(f"Expected: ${shib * bid:.2f}")

# Sell all SHIB
try:
    print(f"\n🔄 Selling {shib:,.0f} SHIB...")
    order = exchange.create_market_sell_order('SHIB/USDT', shib)

    print("✅ SOLD SUCCESSFULLY!")
    print(f"Order ID: {order['id']}")

    # Check new balance
    balance = exchange.fetch_balance()
    usdt = balance.get('USDT', {}).get('free', 0)
    shib_remaining = balance.get('SHIB', {}).get('free', 0)

    print("\n💰 NEW BALANCE:")
    print(f"   USDT: ${usdt:.2f}")
    print(f"   SHIB: {shib_remaining:,.0f}")

    # Clean up position files
    import os
    for file in ['patient_position.json', 'aggressive_position.json', 'position.json']:
        if os.path.exists(file):
            os.remove(file)
            print(f"   Cleaned: {file}")

    print("\n✅ Ready to trade a better pair!")
    print("   Suggested: BTC/USDT (0.01% spread)")
    print("   Or: ETH/USDT (0.02% spread)")

except Exception as e:
    print(f"❌ Error: {e}")
