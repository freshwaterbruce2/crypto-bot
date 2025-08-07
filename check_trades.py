#!/usr/bin/env python3
"""
CHECK RECENT TRADES
===================
"""

import os
from datetime import datetime

import ccxt
from dotenv import load_dotenv

load_dotenv()

# Connect to Kraken
exchange = ccxt.kraken({
    'apiKey': os.getenv('KRAKEN_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True
})

print("=" * 60)
print("CHECKING YOUR SHIB/USDT TRADES")
print("=" * 60)

# Get balance
balance = exchange.fetch_balance()
usdt = balance.get('USDT', {}).get('total', 0)
shib = balance.get('SHIB', {}).get('total', 0)

print("\n💰 Current Balance:")
print(f"   USDT: ${usdt:.4f}")
print(f"   SHIB: {shib:,.0f}")

# Get current price
ticker = exchange.fetch_ticker('SHIB/USDT')
price = ticker['last']
total_value = usdt + (shib * price)

print(f"\n📊 Current SHIB Price: ${price:.8f}")
print(f"💎 Total Portfolio Value: ${total_value:.2f}")

# Get recent trades
print("\n📈 Recent Trades:")
print("-" * 60)

try:
    trades = exchange.fetch_my_trades('SHIB/USDT', limit=10)

    if trades:
        for trade in trades[-5:]:  # Show last 5 trades
            trade_time = datetime.fromisoformat(trade['datetime'].replace('Z', '+00:00'))
            side = "🟢 BUY " if trade['side'] == 'buy' else "🔴 SELL"

            print(f"{trade_time.strftime('%Y-%m-%d %H:%M:%S')} | {side} | "
                  f"{trade['amount']:,.0f} SHIB @ ${trade['price']:.8f} | "
                  f"Cost: ${trade['cost']:.2f}")

        # Calculate stats
        buy_trades = [t for t in trades if t['side'] == 'buy']
        sell_trades = [t for t in trades if t['side'] == 'sell']

        print("\n📊 Trade Statistics:")
        print(f"   Total Trades: {len(trades)}")
        print(f"   Buy Orders: {len(buy_trades)}")
        print(f"   Sell Orders: {len(sell_trades)}")

        if buy_trades:
            avg_buy = sum(t['price'] for t in buy_trades) / len(buy_trades)
            print(f"   Avg Buy Price: ${avg_buy:.8f}")

        if sell_trades:
            avg_sell = sum(t['price'] for t in sell_trades) / len(sell_trades)
            print(f"   Avg Sell Price: ${avg_sell:.8f}")

            if buy_trades:
                profit_pct = ((avg_sell / avg_buy) - 1) * 100
                print(f"   Avg Profit: {profit_pct:.2f}%")
    else:
        print("No trades found yet")

except Exception as e:
    print(f"Error fetching trades: {e}")

# Check open orders
print("\n⏳ Open Orders:")
print("-" * 60)

try:
    open_orders = exchange.fetch_open_orders('SHIB/USDT')

    if open_orders:
        for order in open_orders:
            order_type = "🟢 BUY " if order['side'] == 'buy' else "🔴 SELL"
            print(f"{order_type} | {order['amount']:,.0f} SHIB @ ${order['price']:.8f} | "
                  f"Status: {order['status']}")
    else:
        print("No open orders")

except Exception as e:
    print(f"Error fetching orders: {e}")

print("\n" + "=" * 60)
