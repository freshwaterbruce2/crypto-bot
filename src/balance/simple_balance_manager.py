"""
Emergency Simple Balance Manager
==============================

Ultra-lightweight balance manager for immediate trading access.
Direct REST API calls without WebSocket complexity.
Emergency bypass for critical trading operations.
"""

import asyncio
import logging
import time
import os
from typing import Dict, Optional, Any
from decimal import Decimal
from ..utils.decimal_precision_fix import safe_decimal, safe_float

logger = logging.getLogger(__name__)


class SimpleBalanceManager:
    """Emergency simple balance access for immediate trading"""
    
    def __init__(self, exchange):
        """
        Initialize simple balance manager
        
        Args:
            exchange: Exchange client (NativeKrakenExchange or similar)
        """
        self.exchange = exchange
        self._cache = {}
        self._cache_timeout = 30  # 30 seconds cache
        self._last_update = 0
        
        logger.info("[SIMPLE_BALANCE] Emergency balance manager initialized")
    
    async def get_balance(self, asset: str = 'USDT') -> float:
        """
        Get balance for specific asset with basic caching
        
        Args:
            asset: Asset symbol (default: USDT)
            
        Returns:
            float: Balance amount, 0 if not found or error
        """
        try:
            # Check cache first
            now = time.time()
            if (now - self._last_update) < self._cache_timeout and asset in self._cache:
                logger.debug(f"[SIMPLE_BALANCE] Using cached {asset} balance: {self._cache[asset]}")
                return self._cache[asset]
            
            # Fetch fresh data
            logger.debug(f"[SIMPLE_BALANCE] Fetching fresh {asset} balance...")
            balance_data = await self.exchange.get_account_balance()
            
            if balance_data and 'result' in balance_data:
                balances = balance_data['result']
                balance = safe_float(balances.get(asset, 0))
                
                # Update cache
                self._cache[asset] = balance
                self._last_update = now
                
                logger.info(f"[SIMPLE_BALANCE] {asset} balance: {balance}")
                return balance
            else:
                logger.warning(f"[SIMPLE_BALANCE] No balance data received for {asset}")
                return 0.0
                
        except Exception as e:
            logger.error(f"[SIMPLE_BALANCE] Failed to get {asset} balance: {e}")
            return 0.0
    
    async def get_total_balance(self) -> Dict[str, float]:
        """
        Get all balances with simple REST API call
        
        Returns:
            Dict[str, float]: All asset balances
        """
        try:
            logger.debug("[SIMPLE_BALANCE] Fetching all balances...")
            balance_data = await self.exchange.get_account_balance()
            
            if balance_data and 'result' in balance_data:
                raw_balances = balance_data['result']
                processed_balances = {}
                
                for asset, amount in raw_balances.items():
                    balance = safe_float(amount)
                    if balance > 0:  # Only include non-zero balances
                        processed_balances[asset] = balance
                
                # Update cache
                now = time.time()
                self._cache.update(processed_balances)
                self._last_update = now
                
                logger.info(f"[SIMPLE_BALANCE] Retrieved {len(processed_balances)} non-zero balances")
                return processed_balances
            else:
                logger.warning("[SIMPLE_BALANCE] No balance data received")
                return {}
                
        except Exception as e:
            logger.error(f"[SIMPLE_BALANCE] Failed to get total balance: {e}")
            return {}
    
    async def get_usdt_balance(self) -> float:
        """Get USDT balance specifically (most commonly needed)"""
        return await self.get_balance('USDT')
    
    async def get_available_balance(self, asset: str) -> float:
        """
        Get available balance for trading (same as get_balance for simple manager)
        
        Args:
            asset: Asset symbol
            
        Returns:
            float: Available balance for trading
        """
        return await self.get_balance(asset)
    
    async def refresh_balances(self) -> bool:
        """
        Force refresh all balances (clear cache)
        
        Returns:
            bool: True if refresh successful
        """
        try:
            logger.info("[SIMPLE_BALANCE] Force refreshing balances...")
            self._cache.clear()
            self._last_update = 0
            
            # Fetch fresh data
            balances = await self.get_total_balance()
            success = len(balances) > 0
            
            if success:
                logger.info("[SIMPLE_BALANCE] Balance refresh successful")
            else:
                logger.warning("[SIMPLE_BALANCE] Balance refresh returned no data")
                
            return success
            
        except Exception as e:
            logger.error(f"[SIMPLE_BALANCE] Balance refresh failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get simple status information
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            'type': 'SimpleBalanceManager',
            'cache_age': time.time() - self._last_update,
            'cached_assets': list(self._cache.keys()),
            'cache_timeout': self._cache_timeout,
            'last_update': self._last_update,
            'exchange_connected': self.exchange is not None
        }
    
    async def start(self) -> bool:
        """
        Start the balance manager (no-op for simple manager)
        
        Returns:
            bool: Always True for simple manager
        """
        logger.info("[SIMPLE_BALANCE] Simple balance manager started (no background tasks)")
        return True
    
    async def stop(self):
        """Stop the balance manager (no-op for simple manager)"""
        logger.info("[SIMPLE_BALANCE] Simple balance manager stopped")
        self._cache.clear()


# Quick factory function for emergency use
async def create_emergency_balance_manager(exchange) -> SimpleBalanceManager:
    """
    Create and start emergency balance manager
    
    Args:
        exchange: Exchange client
        
    Returns:
        SimpleBalanceManager: Ready-to-use balance manager
    """
    manager = SimpleBalanceManager(exchange)
    await manager.start()
    
    logger.info("[SIMPLE_BALANCE] Emergency balance manager created and ready")
    return manager