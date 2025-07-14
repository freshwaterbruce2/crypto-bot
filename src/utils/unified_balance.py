"""
Unified Balance Management Interface
Consolidates all balance-related operations
"""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BalanceProvider(ABC):
    """Abstract base class for balance providers"""
    
    @abstractmethod
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch current balance from exchange"""
        pass
    
    @abstractmethod
    async def get_balance(self, asset: str = 'USDT') -> float:
        """Get balance for specific asset"""
        pass
    
    @abstractmethod
    async def refresh_balance(self) -> bool:
        """Refresh balance cache"""
        pass


class UnifiedBalanceManager(BalanceProvider):
    """Unified balance manager that consolidates all balance operations"""
    
    def __init__(self, exchange_client):
        self.exchange_client = exchange_client
        self.balance_cache = {}
        self.last_refresh = 0
        self.cache_timeout = 30  # seconds
    
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch balance using the primary exchange client"""
        try:
            # Use the exchange client's fetch_balance method
            if hasattr(self.exchange_client, 'fetch_balance'):
                return await self.exchange_client.fetch_balance()
            else:
                logger.error("Exchange client doesn't have fetch_balance method")
                return {}
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {}
    
    async def get_balance(self, asset: str = 'USDT') -> float:
        """Get balance for specific asset"""
        try:
            balance_data = await self.fetch_balance()
            return balance_data.get(asset, {}).get('free', 0.0)
        except Exception as e:
            logger.error(f"Error getting {asset} balance: {e}")
            return 0.0
    
    async def refresh_balance(self) -> bool:
        """Refresh balance cache"""
        try:
            self.balance_cache = await self.fetch_balance()
            self.last_refresh = time.time()
            return True
        except Exception as e:
            logger.error(f"Error refreshing balance: {e}")
            return False


# Global instance
_balance_manager = None


def get_balance_manager(exchange_client=None):
    """Get or create unified balance manager"""
    global _balance_manager
    
    if _balance_manager is None and exchange_client:
        _balance_manager = UnifiedBalanceManager(exchange_client)
    
    return _balance_manager
