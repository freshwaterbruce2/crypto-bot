#!/usr/bin/env python3
import os

import ccxt
from dotenv import load_dotenv

load_dotenv()

exchange = ccxt.kraken({
    'apiKey': os.getenv('KRAKEN_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True
})

balance = exchange.fetch_balance()
usdt = balance.get('USDT', {}).get('free', 0)
btc = balance.get('BTC', {}).get('free', 0)

ticker = exchange.fetch_ticker('BTC/USDT')
total = usdt + (btc * ticker['last'])

print(f"USDT: ${usdt:.2f}")
print(f"BTC: {btc:.6f} (${btc * ticker['last']:.2f})")
print(f"Total: ${total:.2f}")
print(f"BTC Price: ${ticker['last']:,.0f}")
