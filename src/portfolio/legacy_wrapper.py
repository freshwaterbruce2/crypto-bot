"""
Legacy Balance Manager Wrapper V2
=================================

Enhanced compatibility wrapper that provides legacy balance manager interface
while using the new Balance Manager V2 with WebSocket-primary architecture.

This maintains backward compatibility for existing code that expects
the old balance manager API while providing all functionality through
the modern WebSocket-first balance management system.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Union

from ..balance.balance_manager_v2 import BalanceManagerV2
from ..utils.decimal_precision_fix import safe_decimal

logger = logging.getLogger(__name__)


class LegacyBalanceManagerWrapper:
    """
    Enhanced wrapper that provides legacy balance manager interface using Balance Manager V2
    """

    def __init__(self, balance_manager_v2: BalanceManagerV2):
        """Initialize with Balance Manager V2 instance"""
        self.balance_manager_v2 = balance_manager_v2
        self.logger = logger
        self.logger.info("[LEGACY_WRAPPER_V2] Initialized with Balance Manager V2 backend")

    async def get_balance(self, symbol: str = 'USDT') -> Decimal:
        """Get balance for specific symbol"""
        try:
            balance_data = await self.balance_manager_v2.get_balance(symbol)
            if balance_data:
                return safe_decimal(balance_data.get('free', 0))
            return Decimal('0')
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error getting balance for {symbol}: {e}")
            return Decimal('0')

    async def get_balances(self) -> Dict[str, Decimal]:
        """Get all balances"""
        try:
            all_balances = await self.balance_manager_v2.get_all_balances()
            result = {}
            for symbol, balance_data in all_balances.items():
                if isinstance(balance_data, dict):
                    result[symbol] = safe_decimal(balance_data.get('free', 0))
                else:
                    result[symbol] = safe_decimal(balance_data)
            return result
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error getting balances: {e}")
            return {}

    async def get_total_balance_usdt(self) -> Decimal:
        """Get total portfolio value in USDT"""
        try:
            usdt_total = await self.balance_manager_v2.get_usdt_total()
            return safe_decimal(usdt_total)
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error getting total balance: {e}")
            return Decimal('0')

    async def refresh_balances(self) -> bool:
        """Refresh balance data"""
        try:
            # Balance Manager V2 automatically refreshes via WebSocket stream
            # Force a manual refresh by getting all balances
            await self.balance_manager_v2.get_all_balances(force_refresh=True)
            return True
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error refreshing balances: {e}")
            return False

    async def update_balance(self, symbol: str, amount: Union[Decimal, float], operation: str = 'set'):
        """Update balance for a symbol"""
        try:
            # Balance Manager V2 handles real-time updates automatically via WebSocket
            self.logger.debug(f"[LEGACY_WRAPPER_V2] Balance update: {symbol} {operation} {amount}")
            # Trigger a refresh to ensure data is current
            await self.balance_manager_v2.get_balance(symbol, force_refresh=True)
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error updating balance: {e}")

    def get_available_balance(self, symbol: str = 'USDT') -> Decimal:
        """Get available balance (synchronous version)"""
        try:
            # Use cached data from Balance Manager V2
            cached_balance = self.balance_manager_v2.get_balance_sync(symbol)
            if cached_balance:
                return safe_decimal(cached_balance.get('free', 0))
            return Decimal('0')
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error getting available balance: {e}")
            return Decimal('0')

    async def initialize(self):
        """Initialize the wrapper"""
        try:
            # Balance Manager V2 should already be initialized
            if not self.balance_manager_v2._initialized:
                await self.balance_manager_v2.initialize()
            self.logger.info("[LEGACY_WRAPPER_V2] Initialization complete")
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Initialization failed: {e}")
            raise

    async def close(self):
        """Close the wrapper"""
        try:
            await self.balance_manager_v2.shutdown()
            self.logger.info("[LEGACY_WRAPPER_V2] Closed successfully")
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error during close: {e}")

    # Additional compatibility methods
    @property
    def is_initialized(self) -> bool:
        """Check if wrapper is initialized"""
        return self.balance_manager_v2._initialized

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary for legacy compatibility"""
        try:
            all_balances = await self.balance_manager_v2.get_all_balances()
            total_usdt = await self.balance_manager_v2.get_usdt_total()

            summary = {
                'total_balance_usdt': total_usdt,
                'asset_count': len(all_balances),
                'balances': all_balances,
                'status': self.balance_manager_v2.get_status()
            }
            return summary
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error getting portfolio summary: {e}")
            return {}

    # Additional Balance Manager V2 compatibility methods
    async def get_balance_for_asset(self, asset: str) -> Decimal:
        """Get balance for asset (alternative method name)"""
        return await self.get_balance(asset)

    async def get_usdt_balance(self) -> Decimal:
        """Get USDT balance specifically"""
        return await self.get_balance('USDT')

    async def get_all_balances(self) -> Dict[str, Decimal]:
        """Alias for get_balances for compatibility"""
        return await self.get_balances()

    def get_deployment_status(self, asset: str = 'USDT') -> Dict[str, Any]:
        """Get deployment status for compatibility"""
        try:
            cached_balance = self.balance_manager_v2.get_balance_sync(asset)
            if cached_balance:
                free_balance = safe_decimal(cached_balance.get('free', 0))
                return {
                    'deployed_amount': Decimal('0'),  # This would need to be calculated from positions
                    'available_amount': free_balance,
                    'total_amount': free_balance,
                    'deployment_ratio': 0.0
                }
            return {'deployed_amount': Decimal('0'), 'available_amount': Decimal('0'), 'total_amount': Decimal('0'), 'deployment_ratio': 0.0}
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error getting deployment status: {e}")
            return {'deployed_amount': Decimal('0'), 'available_amount': Decimal('0'), 'total_amount': Decimal('0'), 'deployment_ratio': 0.0}

    async def analyze_portfolio_state(self, base_asset: str = 'USDT') -> Dict[str, Any]:
        """Analyze portfolio state for compatibility"""
        try:
            all_balances = await self.balance_manager_v2.get_all_balances()
            base_balance = await self.get_balance(base_asset)

            return {
                'base_asset': base_asset,
                'base_balance': base_balance,
                'total_assets': len(all_balances),
                'non_zero_balances': len([b for b in all_balances.values() if isinstance(b, dict) and b.get('free', 0) > 0]),
                'balances': all_balances
            }
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error analyzing portfolio state: {e}")
            return {}

    async def process_websocket_update(self, balance_updates: Dict[str, Dict[str, Any]]):
        """Process WebSocket updates for compatibility"""
        try:
            # Forward to Balance Manager V2
            await self.balance_manager_v2.process_websocket_update(balance_updates)
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error processing WebSocket update: {e}")

    async def force_refresh(self) -> bool:
        """Force refresh balances - compatibility method"""
        try:
            # Balance Manager V2 automatically refreshes via WebSocket stream
            # Force a manual refresh by getting all balances
            await self.balance_manager_v2.get_all_balances(force_refresh=True)
            self.logger.debug("[LEGACY_WRAPPER_V2] Force refresh completed")
            return True
        except Exception as e:
            self.logger.error(f"[LEGACY_WRAPPER_V2] Error during force refresh: {e}")
            return False

    async def stop(self):
        """Stop the wrapper (alias for close)"""
        await self.close()

    def __repr__(self):
        return f"LegacyBalanceManagerWrapper(balance_manager_v2={self.balance_manager_v2})"
