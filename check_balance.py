#!/usr/bin/env python3
"""
BALANCE CHECKER & RECOVERY
===========================
Find out where your money went
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

print("=" * 50)
print("ACCOUNT ANALYSIS")
print("=" * 50)

# Get all balances
balance = exchange.fetch_balance()

# Get prices
ticker_shib = exchange.fetch_ticker('SHIB/USDT')

# Calculate totals
usdt = balance['USDT']['total']
shib = balance['SHIB']['total']
shib_value = shib * ticker_shib['bid']
total_value = usdt + shib_value

print("\n💰 YOUR CURRENT BALANCES:")
print(f"   USDT: ${usdt:.2f}")
print(f"   SHIB: {shib:,.0f} (worth ${shib_value:.2f})")
print(f"   TOTAL VALUE: ${total_value:.2f}")

print("\n📊 SHIB PRICE:")
print(f"   Bid: ${ticker_shib['bid']:.8f}")
print(f"   Ask: ${ticker_shib['ask']:.8f}")
print(f"   Spread: {((ticker_shib['ask'] - ticker_shib['bid'])/ticker_shib['bid']*100):.3f}%")

# Check for open orders
print("\n🔍 Checking for locked funds...")
try:
    open_orders = exchange.fetch_open_orders()
    if open_orders:
        print(f"⚠️ Found {len(open_orders)} open orders!")
        for order in open_orders:
            print(f"   {order['symbol']}: {order['side']} {order['amount']} @ {order['price']}")
    else:
        print("   ✅ No open orders")
except:
    print("   Could not check orders")

# Analysis
print("\n📈 ANALYSIS:")

if total_value < 10:
    print(f"⚠️ Your total value is only ${total_value:.2f}")
    print("   You started with ~$27")
    print(f"   Loss: ${27 - total_value:.2f} (-{((27-total_value)/27*100):.1f}%)")
    print("\n   This happened because:")
    print("   1. SHIB spread is 0.08-0.16% per trade")
    print("   2. You made many quick trades")
    print("   3. Each trade lost money to spread")

    print("\n💡 RECOVERY OPTIONS:")

    if shib > 100000:
        shib_sell_value = shib * ticker_shib['bid']
        print("\n   Option 1: SELL YOUR SHIB")
        print(f"   - Sell {shib:,.0f} SHIB")
        print(f"   - Get ~${shib_sell_value:.2f} USDT")
        print(f"   - Total USDT: ${usdt + shib_sell_value:.2f}")
        print("   - Use smarter strategy")

        response = input("\n   Sell all SHIB now? (y/n): ")
        if response.lower() == 'y':
            try:
                amount = int(shib)
                print(f"   Selling {amount:,.0f} SHIB...")
                order = exchange.create_market_sell_order('SHIB/USDT', amount)
                print("   ✅ Sold! Check balance again.")
            except Exception as e:
                print(f"   ❌ Error: {e}")

    print("\n   Option 2: ADD MORE FUNDS")
    print("   - Add $20-50 to account")
    print("   - Use spread-aware strategy")
    print("   - Trade less frequently")
    print("   - Target 0.5-1% moves")

    print("\n   Option 3: SWITCH STRATEGY")
    print("   - Stop micro-scalping SHIB")
    print("   - Hold for larger moves (1-2%)")
    print("   - Or switch to lower spread pairs")

else:
    print(f"✅ Total value: ${total_value:.2f}")
    print("   You have enough to continue")
    print("   But use spread-aware strategy!")

print("\n" + "=" * 50)
print("RECOMMENDATIONS:")
print("=" * 50)
print("1. STOP micro-scalping SHIB (spread too high)")
print("2. Either hold for 1%+ moves or switch pairs")
print("3. BTC/USDT has 0.01% spread (10x better)")
print("4. Or add funds and trade more patiently")
print("=" * 50)
