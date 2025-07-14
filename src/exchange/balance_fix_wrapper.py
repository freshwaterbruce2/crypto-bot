"""
Balance Fix Wrapper
Ensures balance is always available even when WebSocket fails
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BalanceFixWrapper:
    """Wrapper that ensures balance is always available"""
    
    def __init__(self, exchange):
        self.exchange = exchange
        self._last_known_balance = {}
        
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch balance with fallback to last known values"""
        try:
            balance = await self.exchange.fetch_balance()
            
            # Store last known values for USDT
            for key in ['USDT', 'ZUSDT']:
                if key in balance and float(balance.get(key, 0)) > 0:
                    self._last_known_balance['USDT'] = float(balance[key])
                    break
            
            # Log what we found
            logger.info(f"[BALANCE_FIX] Original balance keys: {list(balance.keys())}")
            
            # Ensure USDT is accessible
            if 'USDT' not in balance and 'ZUSDT' in balance:
                balance['USDT'] = balance['ZUSDT']
            
            # Log USDT balance
            for key in ['USDT', 'ZUSDT']:
                if key in balance:
                    value = balance[key]
                    if isinstance(value, dict):
                        value = value.get('free', 0)
                    if float(value) > 0:
                        logger.info(f"[BALANCE_FIX] Found USDT: ${float(value):.2f} in {key}")
                        break
            
            return balance
            
        except Exception as e:
            logger.error(f"[BALANCE_FIX] Error fetching balance: {e}")
            
            # Return last known balance if available
            if self._last_known_balance:
                logger.warning("[BALANCE_FIX] Using last known balance")
                return {
                    'USDT': self._last_known_balance.get('USDT', 0),
                    'free': {'USDT': self._last_known_balance.get('USDT', 0)},
                    'used': {'USDT': 0},
                    'total': {'USDT': self._last_known_balance.get('USDT', 0)},
                    'info': {}
                }
            
            raise
    
    def __getattr__(self, name):
        """Proxy all other attributes to the exchange"""
        return getattr(self.exchange, name)


def apply_balance_fix(exchange):
    """Apply the balance fix wrapper to an exchange"""
    logger.info("[BALANCE_FIX] Applied balance detection wrapper")
    return BalanceFixWrapper(exchange)
