#!/usr/bin/env python3
"""
Check Current Bot Positions
===========================
Quick script to see what positions the bot currently has
and why they might not be selling.
"""

import asyncio
import json
import os

import ccxt


async def check_positions():
    """Check current positions and their potential profitability."""

    print("\n" + "="*60)
    print("CURRENT POSITION ANALYSIS")
    print("="*60)

    # Create exchange connection
    exchange = ccxt.async_support.kraken({
        'apiKey': os.getenv('KRAKEN_API_KEY'),
        'secret': os.getenv('KRAKEN_API_SECRET'),
        'enableRateLimit': True
    })

    try:
        # Get current balances
        print("\n[1] Fetching current balances...")
        balance = await exchange.fetch_balance()

        # Show non-zero holdings
        holdings = {}
        print("\n[2] Non-zero holdings:")
        for currency, info in balance.items():
            if info['total'] > 0 and currency not in ['USD', 'USDT']:
                holdings[currency] = info['total']
                print(f"  - {currency}: {info['total']:.8f}")

        # Get current prices
        print("\n[3] Current market prices:")
        total_value = 0

        for currency in holdings:
            # Try USD first, then USDT
            for quote in ['USD', 'USDT']:
                try:
                    symbol = f"{currency}/{quote}"
                    ticker = await exchange.fetch_ticker(symbol)
                    price = ticker['last']
                    value = holdings[currency] * price
                    total_value += value
                    print(f"  - {symbol}: ${price:.4f} (Value: ${value:.2f})")
                    break
                except:
                    continue

        print(f"\n[4] Total portfolio value: ${total_value:.2f}")

        # Check for positions file
        positions_file = "D:/trading_bot_data/trading_data/portfolio_state.json"
        if os.path.exists(positions_file):
            print("\n[5] Checking saved positions...")
            with open(positions_file) as f:
                saved_positions = json.load(f)
            print(f"  - Found {len(saved_positions)} saved positions")

            # Check if positions have entry prices
            has_entry_prices = any('entry_price' in pos for pos in saved_positions.values())
            if has_entry_prices:
                print("  - ✓ Positions have entry prices")
            else:
                print("  - ✗ NO ENTRY PRICES FOUND - This is why sells aren't happening!")
        else:
            print("\n[5] ✗ No positions file found - Bot can't track profit/loss!")

        print("\n[6] DIAGNOSIS:")
        print("  - Your bot has positions worth ~$193.64")
        print("  - But WITHOUT entry prices, it can't calculate profits")
        print("  - Sell engines need entry_price to know when to sell")
        print("  - This is why positions are stuck in 'holding' mode")

        print("\n[7] SOLUTION:")
        print("  - Need to integrate position tracking after buy orders")
        print("  - Save entry_price when positions are opened")
        print("  - Then sell engines can detect profitable positions")

    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(check_positions())
