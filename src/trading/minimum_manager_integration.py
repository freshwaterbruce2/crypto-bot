#!/usr/bin/env python3
"""
Integration layer for Smart Minimum Manager

This module provides integration points between the SmartMinimumManager and
the existing trading systems including trade executor, balance manager, and
opportunity scanner.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
import asyncio

from src.trading.smart_minimum_manager import (
    SmartMinimumManager, 
    get_smart_minimum_manager,
    TradingTier
)
from src.autonomous_minimum_learning import minimum_discovery_learning

logger = logging.getLogger(__name__)


class MinimumManagerIntegration:
    """
    Integration layer for minimum order management across the trading system.
    """
    
    def __init__(self, exchange=None, balance_manager=None):
        """
        Initialize the integration layer.
        
        Args:
            exchange: CCXT exchange instance
            balance_manager: Enhanced balance manager instance
        """
        self.exchange = exchange
        self.balance_manager = balance_manager
        self.smart_minimum_manager = get_smart_minimum_manager(exchange)
        self._initialized = False
        
        logger.info("[MINIMUM_INTEGRATION] Initialized integration layer")
    
    async def initialize(self):
        """Initialize the minimum management system."""
        if self._initialized:
            return
            
        logger.info("[MINIMUM_INTEGRATION] Starting initialization...")
        
        # Initialize smart minimum manager
        await self.smart_minimum_manager.initialize()
        
        # Check which portfolio pairs need learning
        portfolio_pairs = list(self.smart_minimum_manager.PORTFOLIO_PAIRS.keys())
        learned_status = minimum_discovery_learning.get_portfolio_pairs_status(portfolio_pairs)
        
        # Count unlearned pairs
        unlearned = [pair for pair, has_learned in learned_status.items() if not has_learned]
        
        if unlearned:
            logger.info(f"[MINIMUM_INTEGRATION] {len(unlearned)} portfolio pairs need minimum learning")
            # The system will learn these through actual trading attempts
        
        self._initialized = True
        logger.info("[MINIMUM_INTEGRATION] Initialization complete")
    
    async def calculate_trade_volume(self, symbol: str, available_balance: Optional[float] = None,
                                   current_price: Optional[float] = None) -> Tuple[float, str]:
        """
        Calculate optimal trade volume for a symbol.
        
        Args:
            symbol: Trading pair
            available_balance: Available USDT (fetches if not provided)
            current_price: Current price (fetches if not provided)
            
        Returns:
            Tuple of (volume, reason)
        """
        try:
            # Get balance if not provided
            if available_balance is None and self.balance_manager:
                balance_info = await self.balance_manager.get_balance_for_asset('USDT')
                available_balance = balance_info if isinstance(balance_info, (int, float)) else balance_info.get('free', 0)
            
            if available_balance is None:
                return 0.0, "Unable to determine available balance"
            
            # Get current price if not provided
            if current_price is None and self.exchange:
                ticker = await self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
            
            if current_price is None:
                return 0.0, "Unable to determine current price"
            
            # Use smart minimum manager for calculation
            volume, reason = await self.smart_minimum_manager.calculate_optimal_volume(
                symbol, available_balance, current_price
            )
            
            return volume, reason
            
        except Exception as e:
            logger.error(f"[MINIMUM_INTEGRATION] Error calculating volume for {symbol}: {e}")
            return 0.0, f"Error: {str(e)}"
    
    async def validate_order_size(self, symbol: str, volume: float, price: float) -> Tuple[bool, str]:
        """
        Validate if an order meets minimum requirements.
        
        Args:
            symbol: Trading pair
            volume: Proposed volume
            price: Order price
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            minimums = await self.smart_minimum_manager.get_minimum_for_pair(symbol)
            min_volume = minimums['volume']
            min_cost = minimums['cost']
            
            order_cost = volume * price
            
            # Check volume minimum
            if volume < min_volume:
                return False, f"Volume {volume} below minimum {min_volume}"
            
            # Check cost minimum
            if order_cost < min_cost:
                return False, f"Order cost ${order_cost:.2f} below minimum ${min_cost:.2f}"
            
            return True, "Order size valid"
            
        except Exception as e:
            logger.error(f"[MINIMUM_INTEGRATION] Error validating order for {symbol}: {e}")
            return False, f"Validation error: {str(e)}"
    
    async def handle_minimum_error(self, symbol: str, error_message: str,
                                 attempted_volume: float, attempted_price: float) -> bool:
        """
        Handle a minimum order error by learning from it.
        
        Args:
            symbol: Trading pair
            error_message: Error message from exchange
            attempted_volume: Volume that failed
            attempted_price: Price used
            
        Returns:
            bool: True if learning was successful
        """
        logger.info(f"[MINIMUM_INTEGRATION] Handling minimum error for {symbol}")
        
        # Use smart minimum manager's learning integration
        success = await self.smart_minimum_manager.update_from_trade_error(
            symbol, error_message, attempted_volume, attempted_price
        )
        
        if success:
            logger.info(f"[MINIMUM_INTEGRATION] Successfully learned from error for {symbol}")
        
        return success
    
    def get_tradeable_pairs(self, available_balance: float) -> List[Dict[str, Any]]:
        """
        Get list of tradeable pairs based on balance and minimums.
        
        Args:
            available_balance: Available USDT balance
            
        Returns:
            List of dicts with pair info
        """
        recommendations = self.smart_minimum_manager.get_recommended_pairs(available_balance)
        
        tradeable = []
        for symbol, reason in recommendations:
            tier = self.smart_minimum_manager.get_pair_tier(symbol)
            tradeable.append({
                "symbol": symbol,
                "tier": tier.value,
                "reason": reason,
                "min_cost": self.smart_minimum_manager.TIER_MIN_COSTS[tier]
            })
        
        return tradeable
    
    def filter_portfolio_pairs(self, all_pairs: List[str]) -> List[str]:
        """
        Filter a list of pairs to only include portfolio pairs.
        
        Args:
            all_pairs: List of all trading pairs
            
        Returns:
            List of pairs that are in our portfolio
        """
        return [p for p in all_pairs if self.smart_minimum_manager.is_portfolio_pair(p)]
    
    async def get_minimum_summary(self) -> Dict[str, Any]:
        """Get a summary of minimum requirements for all portfolio pairs."""
        summary = {
            "portfolio_pairs": {},
            "by_tier": {
                "tier_1": [],
                "meme": [],
                "mid_tier": []
            },
            "statistics": self.smart_minimum_manager.get_statistics()
        }
        
        # Get minimums for all portfolio pairs
        for symbol in self.smart_minimum_manager.PORTFOLIO_PAIRS:
            minimums = await self.smart_minimum_manager.get_minimum_for_pair(symbol)
            tier = self.smart_minimum_manager.get_pair_tier(symbol)
            
            pair_info = {
                "symbol": symbol,
                "tier": tier.value,
                "volume_min": minimums['volume'],
                "cost_min": minimums['cost']
            }
            
            summary["portfolio_pairs"][symbol] = pair_info
            summary["by_tier"][tier.value].append(symbol)
        
        return summary
    
    async def refresh_all_minimums(self) -> Dict[str, Dict[str, float]]:
        """Refresh minimums for all portfolio pairs."""
        logger.info("[MINIMUM_INTEGRATION] Refreshing all portfolio minimums...")
        return await self.smart_minimum_manager.bulk_update_minimums()


# Global instance
_integration = None


def get_minimum_integration(exchange=None, balance_manager=None) -> MinimumManagerIntegration:
    """Get or create the global integration instance."""
    global _integration
    if _integration is None:
        _integration = MinimumManagerIntegration(exchange, balance_manager)
    return _integration


# Convenience functions
async def validate_portfolio_order(symbol: str, volume: float, price: float) -> Tuple[bool, str]:
    """Validate if a portfolio order meets minimums."""
    integration = get_minimum_integration()
    return await integration.validate_order_size(symbol, volume, price)


async def get_portfolio_volume(symbol: str, balance: float = None, price: float = None) -> Tuple[float, str]:
    """Get optimal volume for a portfolio pair."""
    integration = get_minimum_integration()
    return await integration.calculate_trade_volume(symbol, balance, price)