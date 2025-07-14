#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from trading.portfolio_tracker import PortfolioTracker
from exchange.exchange_singleton import get_exchange_singleton
import asyncio

async def force_balance_sync():
    print("Forcing portfolio sync with exchange...")
    
    exchange = get_exchange_singleton()
    if not await exchange.connect():
        print("Failed to connect to exchange")
        return
    
    tracker = PortfolioTracker(exchange)
    await tracker.initialize()
    
    # Force sync
    result = await tracker.force_sync_with_exchange()
    
    print(f"\nSync complete!")
    print(f"Positions synced: {result['positions_synced']}")
    print(f"Positions added: {result['positions_added']}")
    print(f"Positions updated: {result['positions_updated']}")
    print(f"Positions removed: {result['positions_removed']}")
    
    # Show current positions
    positions = tracker.get_all_positions()
    total_value = 0
    print("\nCurrent positions:")
    for symbol, pos in positions.items():
        value = pos['amount'] * pos.get('current_price', 0)
        total_value += value
        print(f"  {symbol}: {pos['amount']:.4f} @ ${pos.get('current_price', 0):.2f} = ${value:.2f}")
    
    print(f"\nTotal portfolio value: ${total_value:.2f}")

if __name__ == "__main__":
    asyncio.run(force_balance_sync())
