#!/usr/bin/env python3
"""
TEST KRAKEN PRO 2025 API FORMATS
=================================
"""

import os

import ccxt
from dotenv import load_dotenv

load_dotenv()

exchange = ccxt.kraken({
    'apiKey': os.getenv('KRAKEN_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True,
    'sandbox': False,  # Production
    'options': {
        'adjustForTimeDifference': True,
        'recvWindow': 10000
    }
})

print("=" * 70)
print("KRAKEN PRO 2025 API COMPATIBILITY TEST")
print("=" * 70)

# Test 1: Check API version and capabilities
print("\n1. EXCHANGE INFO:")
print(f"   Exchange ID: {exchange.id}")
print(f"   Version: {exchange.version}")
print(f"   Has USDT: {'USDT' in exchange.currencies}")
print(f"   Pro Account: {exchange.pro if hasattr(exchange, 'pro') else 'Standard'}")

# Test 2: Market data for BTC/USDT
print("\n2. BTC/USDT MARKET:")
try:
    exchange.load_markets()
    market = exchange.market('BTC/USDT')
    print(f"   Symbol: {market['symbol']}")
    print(f"   Base: {market['base']}")
    print(f"   Quote: {market['quote']}")
    print(f"   Active: {market['active']}")
    print(f"   Min Amount: {market['limits']['amount']['min']}")
    print(f"   Min Cost: {market['limits']['cost']['min']}")
    print(f"   Precision Amount: {market['precision']['amount']}")
    print(f"   Precision Price: {market['precision']['price']}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Current ticker
print("\n3. CURRENT TICKER:")
try:
    ticker = exchange.fetch_ticker('BTC/USDT')
    print(f"   Last: ${ticker['last']:,.2f}")
    print(f"   Bid: ${ticker['bid']:,.2f}")
    print(f"   Ask: ${ticker['ask']:,.2f}")
    print(f"   Spread: {((ticker['ask'] - ticker['bid']) / ticker['bid'] * 100):.4f}%")
    print(f"   Volume: {ticker['baseVolume']:,.2f} BTC")
    print(f"   Quote Volume: ${ticker['quoteVolume']:,.0f}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Account balance (USDT focus)
print("\n4. ACCOUNT BALANCE:")
try:
    balance = exchange.fetch_balance()

    # Check different USDT formats Kraken might use
    usdt_variants = ['USDT', 'ZUSDT', 'USD', 'ZUSD']
    for variant in usdt_variants:
        if variant in balance and balance[variant]['total'] > 0:
            print(f"   {variant}: ${balance[variant]['total']:.2f}")
            print(f"   {variant} Free: ${balance[variant]['free']:.2f}")
            print(f"   {variant} Used: ${balance[variant]['used']:.2f}")

    # Check BTC
    btc_variants = ['BTC', 'XBT', 'XXBT']
    for variant in btc_variants:
        if variant in balance and balance[variant]['total'] > 0:
            print(f"   {variant}: {balance[variant]['total']:.6f}")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Order book
print("\n5. ORDER BOOK:")
try:
    orderbook = exchange.fetch_order_book('BTC/USDT', limit=5)
    print(f"   Best Bid: ${orderbook['bids'][0][0]:,.2f} (Size: {orderbook['bids'][0][1]:.6f})")
    print(f"   Best Ask: ${orderbook['asks'][0][0]:,.2f} (Size: {orderbook['asks'][0][1]:.6f})")
    print(f"   Depth: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 6: Check trading fees
print("\n6. TRADING FEES:")
try:
    fees = exchange.fetch_trading_fees()
    if 'BTC/USDT' in fees:
        btc_fees = fees['BTC/USDT']
        print(f"   Maker Fee: {btc_fees['maker'] * 100:.2f}%")
        print(f"   Taker Fee: {btc_fees['taker'] * 100:.2f}%")
    else:
        print(f"   General Maker: {fees['maker'] * 100:.2f}%")
        print(f"   General Taker: {fees['taker'] * 100:.2f}%")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 7: Recent trades
print("\n7. RECENT TRADES:")
try:
    trades = exchange.fetch_trades('BTC/USDT', limit=3)
    for trade in trades:
        print(f"   {trade['datetime'][:19]} | ${trade['price']:,.2f} | {trade['amount']:.6f} BTC")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 8: Test small order validation (DON'T PLACE)
print("\n8. ORDER VALIDATION:")
try:
    ticker = exchange.fetch_ticker('BTC/USDT')
    test_amount = 0.0001  # Minimum
    test_price = ticker['bid']
    test_cost = test_amount * test_price

    print(f"   Test Order: {test_amount} BTC @ ${test_price:,.2f}")
    print(f"   Cost: ${test_cost:.2f}")

    # Check if this would be valid
    market = exchange.market('BTC/USDT')
    min_amount = market['limits']['amount']['min']
    min_cost = market['limits']['cost']['min']

    if test_amount >= min_amount:
        print(f"   ✅ Amount OK (min: {min_amount})")
    else:
        print(f"   ❌ Amount too small (min: {min_amount})")

    if test_cost >= min_cost:
        print(f"   ✅ Cost OK (min: ${min_cost})")
    else:
        print(f"   ❌ Cost too small (min: ${min_cost})")

except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("API TEST COMPLETE")
print("=" * 70)
