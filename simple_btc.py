#!/usr/bin/env python3
"""
SIMPLEST BTC BOT
"""

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

position = None

while True:
    try:
        # Get data
        ticker = exchange.fetch_ticker('BTC/USDT')
        balance = exchange.fetch_balance()
        usdt = balance.get('USDT', {}).get('free', 0)
        btc = balance.get('BTC', {}).get('free', 0)

        print(f"BTC: ${ticker['last']:,.0f} | USDT: ${usdt:.2f} | BTC: {btc:.6f}")

        # Buy if we have USDT
        if not position and usdt > 20:
            amount = 0.0002  # ~$23 worth
            order = exchange.create_market_buy_order('BTC/USDT', amount)
            position = ticker['last']
            print(f"BOUGHT at ${position:,.0f}")

        # Sell if we made $0.10
        elif position and btc > 0:
            profit = ticker['bid'] - position
            if profit > 10:  # $10 profit
                order = exchange.create_market_sell_order('BTC/USDT', btc)
                print(f"SOLD at ${ticker['bid']:,.0f} | Profit: ${profit:.0f}")
                position = None

        time.sleep(5)

    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
