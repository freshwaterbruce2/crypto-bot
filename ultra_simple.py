#!/usr/bin/env python3
"""
ULTRA SIMPLE BTC BOT
Buy, wait for $1 profit, sell. Repeat.
"""

import json
import os
import time

import ccxt
from dotenv import load_dotenv

load_dotenv()

exchange = ccxt.kraken({
    'apiKey': os.getenv('KRAKEN_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True
})

# Load saved position if exists
try:
    with open('ultra_position.json') as f:
        data = json.load(f)
        buy_price = data['price']
        print(f"Loaded position: Buy price ${buy_price:,.0f}")
except Exception:
    buy_price = 117400  # Estimate based on recent price

print("ULTRA SIMPLE BOT - Buy BTC, sell for $1 profit")
print("=" * 50)

while True:
    try:
        # Get current price and balance
        ticker = exchange.fetch_ticker('BTC/USDT')
        balance = exchange.fetch_balance()
        usdt = balance.get('USDT', {}).get('free', 0)
        btc = balance.get('BTC', {}).get('free', 0)

        price = ticker['last']

        # Status
        print(f"\n${price:,.0f} | USDT: ${usdt:.2f} | BTC: {btc:.6f}", end="")

        # Buy if we have USDT
        if usdt > 20 and btc < 0.0001:
            amount = 0.00017  # ~$20 worth
            exchange.create_market_buy_order('BTC/USDT', amount)
            buy_price = price
            print(f"\n✅ BOUGHT at ${buy_price:,.0f}")
            # Save position
            with open('ultra_position.json', 'w') as f:
                json.dump({'price': buy_price}, f)

        # Sell if we have BTC and made profit
        elif btc > 0.0001 and buy_price > 0:
            profit_per_btc = ticker['bid'] - buy_price
            total_profit = profit_per_btc * btc

            print(f" | P&L: ${total_profit:.2f}", end="")

            if total_profit > 0.10:  # $0.10 profit target
                exchange.create_market_sell_order('BTC/USDT', btc)
                print(f"\n✅ SOLD at ${ticker['bid']:,.0f} | Profit: ${total_profit:.2f}")
                buy_price = 0

        time.sleep(5)

    except KeyboardInterrupt:
        print("\nStopped")
        break
    except Exception as e:
        print(f"\nError: {e}")
        time.sleep(10)
