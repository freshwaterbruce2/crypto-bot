"""
Trade Cooldown Manager for Kraken Compliance
============================================

Implements same-side trade cooling periods to prevent market manipulation
and ensure compliance with Kraken's automated trading guidelines.
"""

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class TradeCooldownManager:
    """Manages trade cooldown periods for compliance"""
    
    def __init__(self, same_side_cooldown: int = 300):  # 5 minutes default
        self.same_side_cooldown = same_side_cooldown  # seconds
        self.last_trades: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.trade_counts: Dict[str, Dict[str, int]] = defaultdict(dict)
        
    def can_trade(self, symbol: str, side: str) -> tuple[bool, str]:
        """
        Check if trading is allowed for given symbol and side
        
        Args:
            symbol: Trading pair (e.g., 'SHIB/USDT')
            side: Trade side ('buy' or 'sell')
            
        Returns:
            Tuple of (allowed, reason)
        """
        current_time = time.time()
        
        # Check same-side cooldown
        if side in self.last_trades[symbol]:
            last_trade_time = self.last_trades[symbol][side]
            time_since_last = current_time - last_trade_time
            
            if time_since_last < self.same_side_cooldown:
                remaining = self.same_side_cooldown - time_since_last
                return False, f"Same-side cooldown: {remaining:.0f}s remaining for {side} {symbol}"
        
        return True, "Trade allowed"
    
    def record_trade(self, symbol: str, side: str, amount: float) -> None:
        """
        Record a completed trade
        
        Args:
            symbol: Trading pair
            side: Trade side
            amount: Trade amount in USD
        """
        current_time = time.time()
        
        # Record trade time
        self.last_trades[symbol][side] = current_time
        
        # Increment trade count
        if side not in self.trade_counts[symbol]:
            self.trade_counts[symbol][side] = 0
        self.trade_counts[symbol][side] += 1
        
        logger.info(f"[COOLDOWN] Recorded {side} trade for {symbol}: ${amount:.2f}")
    
    def get_cooldown_status(self, symbol: str) -> Dict[str, Any]:
        """Get cooldown status for a symbol"""
        current_time = time.time()
        status = {
            'symbol': symbol,
            'buy_cooldown': None,
            'sell_cooldown': None,
            'buy_count': self.trade_counts[symbol].get('buy', 0),
            'sell_count': self.trade_counts[symbol].get('sell', 0)
        }
        
        # Check buy cooldown
        if 'buy' in self.last_trades[symbol]:
            last_buy = self.last_trades[symbol]['buy']
            time_since = current_time - last_buy
            if time_since < self.same_side_cooldown:
                status['buy_cooldown'] = self.same_side_cooldown - time_since
        
        # Check sell cooldown
        if 'sell' in self.last_trades[symbol]:
            last_sell = self.last_trades[symbol]['sell']
            time_since = current_time - last_sell
            if time_since < self.same_side_cooldown:
                status['sell_cooldown'] = self.same_side_cooldown - time_since
        
        return status
    
    def cleanup_old_records(self, max_age: int = 3600) -> None:
        """Clean up old trade records (older than max_age seconds)"""
        current_time = time.time()
        
        for symbol in list(self.last_trades.keys()):
            for side in list(self.last_trades[symbol].keys()):
                if current_time - self.last_trades[symbol][side] > max_age:
                    del self.last_trades[symbol][side]
            
            # Clean up empty symbol entries
            if not self.last_trades[symbol]:
                del self.last_trades[symbol]
        
        logger.debug(f"[COOLDOWN] Cleaned up old trade records (max_age: {max_age}s)")


# Global cooldown manager instance
_cooldown_manager = None

def get_cooldown_manager() -> TradeCooldownManager:
    """Get or create the global cooldown manager"""
    global _cooldown_manager
    if _cooldown_manager is None:
        _cooldown_manager = TradeCooldownManager()
    return _cooldown_manager