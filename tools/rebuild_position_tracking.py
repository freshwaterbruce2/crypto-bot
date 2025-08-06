#!/usr/bin/env python3
"""
Rebuild Position Tracking with Entry Prices
===========================================

This tool rebuilds position tracking by:
1. Scanning recent trade history for buy orders
2. Matching them with current holdings
3. Storing entry prices for profit calculation
4. Enabling sell engines to detect profitable positions

This solves the issue where $193.64 is deployed but positions
are stuck in "holding" mode because entry prices are missing.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ccxt

from src.config import load_config


async def get_recent_trades(exchange, hours=24) -> List[Dict[str, Any]]:
    """Fetch recent trades from exchange."""
    print(f"\n[SCAN] Fetching trades from last {hours} hours...")

    try:
        # Calculate time range
        since = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

        # Fetch all trades
        all_trades = []
        for symbol in ['BTC/USD', 'BTC/USDT', 'ETH/USD', 'ETH/USDT',
                      'ADA/USD', 'ADA/USDT', 'SOL/USD', 'SOL/USDT',
                      'DOGE/USD', 'DOGE/USDT', 'SHIB/USD', 'SHIB/USDT']:
            try:
                trades = await exchange.fetch_my_trades(symbol, since=since, limit=100)
                all_trades.extend(trades)
                print(f"  - {symbol}: Found {len(trades)} trades")
            except Exception as e:
                print(f"  - {symbol}: Error fetching trades: {e}")

        return all_trades
    except Exception as e:
        print(f"[ERROR] Failed to fetch trades: {e}")
        return []


async def get_current_balances(exchange) -> Dict[str, float]:
    """Get current non-zero balances."""
    print("\n[SCAN] Fetching current balances...")

    try:
        balance = await exchange.fetch_balance()

        # Filter for non-zero balances
        holdings = {}
        for currency, amount in balance['total'].items():
            if amount > 0 and currency not in ['USD', 'USDT']:
                holdings[currency] = amount
                print(f"  - {currency}: {amount:.8f}")

        return holdings
    except Exception as e:
        print(f"[ERROR] Failed to fetch balances: {e}")
        return {}


async def match_trades_to_holdings(trades: List[Dict], holdings: Dict[str, float]) -> Dict[str, Dict]:
    """Match buy trades to current holdings to determine entry prices."""
    print("\n[MATCH] Analyzing trades to determine entry prices...")

    positions = {}

    # Group trades by base currency
    trades_by_currency = {}
    for trade in trades:
        if trade['side'] == 'buy':
            base = trade['symbol'].split('/')[0]
            if base not in trades_by_currency:
                trades_by_currency[base] = []
            trades_by_currency[base].append(trade)

    # For each holding, find matching buy trades
    for currency, amount in holdings.items():
        if currency in trades_by_currency:
            currency_trades = sorted(trades_by_currency[currency],
                                   key=lambda x: x['timestamp'],
                                   reverse=True)

            # Calculate weighted average entry price
            total_amount = 0
            total_cost = 0

            for trade in currency_trades:
                if total_amount < amount:
                    trade_amount = min(trade['amount'], amount - total_amount)
                    total_amount += trade_amount
                    total_cost += trade_amount * trade['price']

                    # Check if we've matched enough
                    if total_amount >= amount * 0.95:  # 95% match is good enough
                        break

            if total_amount > 0:
                avg_price = total_cost / total_amount
                positions[currency] = {
                    'amount': amount,
                    'entry_price': avg_price,
                    'current_value': None,  # Will be updated with current price
                    'matched_amount': total_amount,
                    'match_percentage': (total_amount / amount) * 100
                }
                print(f"  - {currency}: Entry price ${avg_price:.4f} "
                      f"(matched {total_amount:.8f}/{amount:.8f} = "
                      f"{positions[currency]['match_percentage']:.1f}%)")

    return positions


async def rebuild_position_tracking():
    """Main function to rebuild position tracking."""
    print("=" * 60)
    print("POSITION TRACKING REBUILDER")
    print("=" * 60)

    # Load config and create exchange
    config = load_config()
    exchange = ccxt.kraken({
        'apiKey': os.getenv('KRAKEN_API_KEY'),
        'secret': os.getenv('KRAKEN_API_SECRET'),
        'enableRateLimit': True
    })

    # Make it async
    exchange = ccxt.async_support.kraken({
        'apiKey': os.getenv('KRAKEN_API_KEY'),
        'secret': os.getenv('KRAKEN_API_SECRET'),
        'enableRateLimit': True
    })

    try:
        # 1. Get recent trades
        trades = await get_recent_trades(exchange, hours=48)  # Look back 48 hours
        print(f"\n[TOTAL] Found {len(trades)} total trades")

        # 2. Get current balances
        holdings = await get_current_balances(exchange)
        print(f"\n[TOTAL] Found {len(holdings)} non-zero holdings")

        # 3. Match trades to holdings
        positions = await match_trades_to_holdings(trades, holdings)
        print(f"\n[TOTAL] Matched {len(positions)} positions with entry prices")

        # 4. Get current prices
        print("\n[PRICE] Fetching current prices...")
        for currency, position in positions.items():
            try:
                # Try different pair combinations
                for quote in ['USD', 'USDT']:
                    symbol = f"{currency}/{quote}"
                    try:
                        ticker = await exchange.fetch_ticker(symbol)
                        current_price = ticker['last']
                        position['current_price'] = current_price
                        position['current_value'] = position['amount'] * current_price
                        position['profit_loss'] = (current_price - position['entry_price']) * position['amount']
                        position['profit_percentage'] = ((current_price - position['entry_price']) / position['entry_price']) * 100
                        print(f"  - {symbol}: ${current_price:.4f} "
                              f"(P/L: ${position['profit_loss']:.2f} = "
                              f"{position['profit_percentage']:.2f}%)")
                        break
                    except:
                        continue
            except Exception as e:
                print(f"  - {currency}: Error fetching price: {e}")

        # 5. Save to portfolio state file
        portfolio_file = Path("D:/trading_bot_data/trading_data/portfolio_state.json")
        portfolio_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert positions to portfolio format
        portfolio_data = {}
        for currency, position in positions.items():
            if 'current_price' in position:
                # Try to find the best trading pair
                for quote in ['USD', 'USDT']:
                    symbol = f"{currency}/{quote}"
                    portfolio_data[symbol] = {
                        'amount': position['amount'],
                        'price': position['entry_price'],  # Entry price
                        'value': position['current_value'],
                        'current_price': position['current_price'],
                        'entry_price': position['entry_price'],
                        'profit_loss': position['profit_loss'],
                        'profit_percentage': position['profit_percentage'],
                        'last_updated': datetime.now().isoformat()
                    }

        # Save portfolio state
        with open(portfolio_file, 'w') as f:
            json.dump(portfolio_data, f, indent=2)
        print(f"\n[SAVE] Portfolio state saved to {portfolio_file}")

        # 6. Summary
        print("\n" + "=" * 60)
        print("POSITION TRACKING REBUILT SUCCESSFULLY")
        print("=" * 60)
        print(f"\nTotal Positions: {len(portfolio_data)}")

        total_value = sum(p.get('current_value', 0) for p in positions.values())
        total_pl = sum(p.get('profit_loss', 0) for p in positions.values())

        print(f"Total Value: ${total_value:.2f}")
        print(f"Total P/L: ${total_pl:.2f}")

        if len(positions) > 0:
            print("\nPositions Ready for Profit Taking:")
            for currency, position in positions.items():
                if position.get('profit_percentage', 0) > 0.01:  # Any profit
                    print(f"  - {currency}: {position['profit_percentage']:.2f}% profit "
                          f"(${position.get('profit_loss', 0):.2f})")

    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(rebuild_position_tracking())
