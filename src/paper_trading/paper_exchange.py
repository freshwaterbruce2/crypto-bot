"""
Paper Exchange
Simple simulated exchange for paper trading
"""

import asyncio
import random
from typing import Any, Dict, Optional


class PaperExchange:
    """Simulated exchange for paper trading"""

    def __init__(self):
        # Simulated market prices
        self.prices = {
            'BTC/USDT': 45000.0,
            'ETH/USDT': 3000.0,
            'SOL/USDT': 160.0,
            'AVAX/USDT': 21.0,
            'ALGO/USDT': 0.25,
            'ATOM/USDT': 4.65,
            'AI16Z/USDT': 0.186,
            'BERA/USDT': 2.0
        }

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get simulated ticker data"""
        base_price = self.prices.get(symbol, 100.0)

        # Add random price movement (±1%)
        variation = random.uniform(-0.01, 0.01)
        current_price = base_price * (1 + variation)

        return {
            'symbol': symbol,
            'last': current_price,
            'bid': current_price * 0.999,
            'ask': current_price * 1.001,
            'volume': random.uniform(1000, 10000)
        }

    async def place_order(self, symbol: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """Simulate order placement"""
        # Simulate network delay
        await asyncio.sleep(random.uniform(0.1, 0.3))

        # Simulate occasional failures
        if random.random() < 0.02:  # 2% failure rate
            return {
                'success': False,
                'error': 'Simulated network timeout'
            }

        order_id = f'paper_{int(asyncio.get_event_loop().time() * 1000)}'

        return {
            'success': True,
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price or (await self.get_ticker(symbol))['last'],
            'status': 'filled'
        }
