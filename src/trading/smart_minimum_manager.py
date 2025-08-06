#!/usr/bin/env python3
"""
Smart Minimum Order Management System

Optimized for the 12 specific USDT pairs in our portfolio:
ADA, AI16Z, ALGO, ATOM, AVAX, BERA, DOT, FARTCOIN, LINK, MANA, MATIC, SHIB, SOL, DOGE

This system provides intelligent minimum order handling with tier-based classification,
dynamic updates, and integration with our existing learning systems.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Tuple

try:
    import ccxt
except ImportError:
    ccxt = None

from src.autonomous_minimum_learning.minimum_discovery_learning import minimum_discovery_learning
from src.utils.minimum_provider import get_dynamic_minimums

logger = logging.getLogger(__name__)


class TradingTier(Enum):
    """Trading tier classification for pairs."""
    TIER_1 = "tier_1"  # High liquidity, stable pairs: SOL, ADA, AVAX, DOT, LINK, ATOM, ALGO, MATIC
    MEME = "meme"      # Meme coins: SHIB, DOGE, FARTCOIN, BERA, AI16Z
    MID_TIER = "mid_tier"  # MANA and similar


class SmartMinimumManager:
    """
    Smart minimum order management focused on portfolio pairs.
    
    Features:
    - Tier-based classification for optimization
    - Dynamic minimum updates from multiple sources
    - Integration with existing learning systems
    - Smart position sizing based on tier and balance
    """

    # Portfolio pairs configuration
    PORTFOLIO_PAIRS = {
        "ADA/USDT": TradingTier.TIER_1,
        "AI16Z/USDT": TradingTier.MEME,
        "ALGO/USDT": TradingTier.TIER_1,
        "ATOM/USDT": TradingTier.TIER_1,
        "AVAX/USDT": TradingTier.TIER_1,
        "BERA/USDT": TradingTier.MEME,
        "DOT/USDT": TradingTier.TIER_1,
        "FARTCOIN/USDT": TradingTier.MEME,
        "LINK/USDT": TradingTier.TIER_1,
        "MANA/USDT": TradingTier.MID_TIER,
        "MATIC/USDT": TradingTier.TIER_1,
        "SHIB/USDT": TradingTier.MEME,
        "SOL/USDT": TradingTier.TIER_1,
        "DOGE/USDT": TradingTier.MEME
    }

    # Tier-based minimum cost preferences - EMERGENCY FIX: Adjusted for $5 balance trading
    TIER_MIN_COSTS = {
        TradingTier.TIER_1: 2.0,    # $2.0 minimum for stable pairs (70% of $5 balance fix)
        TradingTier.MEME: 2.0,      # $2.0 minimum for meme coins (same as tier 1)
        TradingTier.MID_TIER: 2.0   # $2.0 for mid-tier pairs (consistent minimums)
    }

    # Tier-based position sizing - EMERGENCY FIX: Optimized for $5 balance with 70% position size
    TIER_POSITION_SIZES = {
        TradingTier.TIER_1: 0.70,   # 70% for stable pairs ($3.50 from $5 balance)
        TradingTier.MEME: 0.70,     # 70% for meme coins (same as tier 1 for consistency)
        TradingTier.MID_TIER: 0.70  # 70% for mid-tier (maintain consistency)
    }

    def __init__(self, exchange = None):
        """
        Initialize the smart minimum manager.
        
        Args:
            exchange: CCXT exchange instance for live data
        """
        self.exchange = exchange
        self._minimum_cache = {}
        self._cache_timestamps = {}
        self._cache_duration = 300  # 5 minutes
        self._initialization_complete = False

        # Statistics tracking
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "dynamic_updates": 0,
            "learning_applied": 0
        }

        logger.info(f"[SMART_MINIMUM] Initialized with {len(self.PORTFOLIO_PAIRS)} portfolio pairs")

    async def initialize(self):
        """Initialize by fetching minimums for all portfolio pairs."""
        if self._initialization_complete:
            return

        logger.info("[SMART_MINIMUM] Initializing minimums for portfolio pairs...")

        # Bulk fetch minimums for all pairs
        tasks = []
        for pair in self.PORTFOLIO_PAIRS:
            tasks.append(self._fetch_and_cache_minimum(pair))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"[SMART_MINIMUM] Initialized {successful}/{len(self.PORTFOLIO_PAIRS)} pairs")

        self._initialization_complete = True

    async def _fetch_and_cache_minimum(self, symbol: str) -> Tuple[float, float]:
        """Fetch and cache minimum for a symbol."""
        try:
            # First try our existing minimum provider
            vol_min, cost_min = get_dynamic_minimums(symbol)

            # If we have an exchange, try to get live data
            if self.exchange and hasattr(self.exchange, 'load_markets'):
                try:
                    if not self.exchange.markets:
                        await self.exchange.load_markets()

                    market = self.exchange.market(symbol)
                    if market:
                        # Extract minimums from market info
                        limits = market.get('limits', {})
                        amount_limits = limits.get('amount', {})
                        cost_limits = limits.get('cost', {})

                        if amount_limits.get('min'):
                            vol_min = float(amount_limits['min'])
                        if cost_limits.get('min'):
                            cost_min = float(cost_limits['min'])

                        self.stats["dynamic_updates"] += 1
                        logger.debug(f"[SMART_MINIMUM] Live data for {symbol}: vol={vol_min}, cost={cost_min}")
                except Exception as e:
                    logger.debug(f"[SMART_MINIMUM] Could not fetch live data for {symbol}: {e}")

            # Cache the results
            self._minimum_cache[symbol] = {"volume": vol_min, "cost": cost_min}
            self._cache_timestamps[symbol] = time.time()

            return vol_min, cost_min

        except Exception as e:
            logger.error(f"[SMART_MINIMUM] Error fetching minimum for {symbol}: {e}")
            # Return safe defaults
            tier = self.PORTFOLIO_PAIRS.get(symbol, TradingTier.MID_TIER)
            return 0.001, self.TIER_MIN_COSTS[tier]

    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached minimum is still valid."""
        if symbol not in self._cache_timestamps:
            return False
        return (time.time() - self._cache_timestamps[symbol]) < self._cache_duration

    async def get_minimum_for_pair(self, symbol: str) -> Dict[str, float]:
        """
        Get minimum requirements for a trading pair.
        
        Returns:
            Dict with 'volume' and 'cost' minimums
        """
        # Check cache first
        if self._is_cache_valid(symbol):
            self.stats["cache_hits"] += 1
            return self._minimum_cache[symbol].copy()

        self.stats["cache_misses"] += 1

        # Fetch fresh data
        vol_min, cost_min = await self._fetch_and_cache_minimum(symbol)

        # Apply tier-based minimum cost if needed
        if symbol in self.PORTFOLIO_PAIRS:
            tier = self.PORTFOLIO_PAIRS[symbol]
            tier_min_cost = self.TIER_MIN_COSTS[tier]
            if cost_min < tier_min_cost:
                logger.debug(f"[SMART_MINIMUM] Applying tier minimum ${tier_min_cost} for {symbol}")
                cost_min = tier_min_cost

        return {"volume": vol_min, "cost": cost_min}

    async def calculate_optimal_volume(self, symbol: str, available_balance: float,
                                     current_price: float) -> Tuple[float, str]:
        """
        Calculate optimal trading volume based on tier, balance, and minimums.
        
        Args:
            symbol: Trading pair
            available_balance: Available USDT balance
            current_price: Current price of the asset
            
        Returns:
            Tuple of (volume, reason)
        """
        # Get minimums
        minimums = await self.get_minimum_for_pair(symbol)
        min_volume = minimums["volume"]
        min_cost = minimums["cost"]

        # Get tier for position sizing
        tier = self.PORTFOLIO_PAIRS.get(symbol, TradingTier.MID_TIER)
        position_size_pct = self.TIER_POSITION_SIZES[tier]

        # Calculate position size based on tier
        tier_based_cost = available_balance * position_size_pct
        tier_based_volume = tier_based_cost / current_price

        # Calculate minimum required volume
        min_volume_from_cost = min_cost / current_price
        required_volume = max(min_volume, min_volume_from_cost)

        # Choose the larger of tier-based or minimum required
        if tier_based_volume >= required_volume:
            return tier_based_volume, f"{tier.value} position size: {position_size_pct*100}% of balance"
        else:
            # Use minimum + small buffer
            buffered_volume = required_volume * 1.05
            return buffered_volume, f"Minimum requirement: ${min_cost:.2f} + 5% buffer"

    def get_pair_tier(self, symbol: str) -> TradingTier:
        """Get the trading tier for a pair."""
        return self.PORTFOLIO_PAIRS.get(symbol, TradingTier.MID_TIER)

    def is_portfolio_pair(self, symbol: str) -> bool:
        """Check if a pair is in our portfolio."""
        return symbol in self.PORTFOLIO_PAIRS

    def get_portfolio_pairs_by_tier(self, tier: TradingTier) -> List[str]:
        """Get all pairs of a specific tier."""
        return [pair for pair, pair_tier in self.PORTFOLIO_PAIRS.items() if pair_tier == tier]

    async def update_from_trade_error(self, symbol: str, error_message: str,
                                    attempted_volume: float, attempted_price: float) -> bool:
        """
        Update minimums based on trade error (integration with learning system).
        
        Args:
            symbol: Trading pair
            error_message: Error message from exchange
            attempted_volume: Volume that was attempted
            attempted_price: Price used in attempt
            
        Returns:
            bool: True if learning was successful
        """
        # Use existing learning system
        success = minimum_discovery_learning.learn_from_error(
            error_message, symbol, attempted_volume, attempted_price
        )

        if success:
            # Clear cache to force refresh
            if symbol in self._cache_timestamps:
                del self._cache_timestamps[symbol]
            self.stats["learning_applied"] += 1
            logger.info(f"[SMART_MINIMUM] Updated {symbol} minimums from trade error")

        return success

    def get_statistics(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "cached_pairs": len(self._minimum_cache),
            "portfolio_pairs": len(self.PORTFOLIO_PAIRS),
            "tier_distribution": {
                tier.value: len(self.get_portfolio_pairs_by_tier(tier))
                for tier in TradingTier
            }
        }

    async def bulk_update_minimums(self) -> Dict[str, Dict[str, float]]:
        """
        Bulk update minimums for all portfolio pairs.
        
        Returns:
            Dict mapping symbols to their minimums
        """
        logger.info("[SMART_MINIMUM] Starting bulk minimum update...")

        tasks = []
        for symbol in self.PORTFOLIO_PAIRS:
            # Force cache invalidation
            if symbol in self._cache_timestamps:
                del self._cache_timestamps[symbol]
            tasks.append(self.get_minimum_for_pair(symbol))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        updated = {}
        for symbol, result in zip(self.PORTFOLIO_PAIRS, results):
            if not isinstance(result, Exception):
                updated[symbol] = result
            else:
                logger.error(f"[SMART_MINIMUM] Failed to update {symbol}: {result}")

        logger.info(f"[SMART_MINIMUM] Updated {len(updated)}/{len(self.PORTFOLIO_PAIRS)} pairs")
        return updated

    def get_recommended_pairs(self, available_balance: float) -> List[Tuple[str, str]]:
        """
        Get recommended pairs to trade based on balance and tier.
        
        Args:
            available_balance: Available USDT balance
            
        Returns:
            List of (symbol, reason) tuples
        """
        recommendations = []

        # Check each tier
        for tier in [TradingTier.TIER_1, TradingTier.MID_TIER, TradingTier.MEME]:
            tier_pairs = self.get_portfolio_pairs_by_tier(tier)
            min_required = self.TIER_MIN_COSTS[tier]

            if available_balance >= min_required * 1.1:  # 10% buffer
                for pair in tier_pairs:
                    reason = f"{tier.value}: min ${min_required:.2f}"
                    recommendations.append((pair, reason))

        return recommendations


# Convenience functions for easy integration
_smart_minimum_manager = None


def get_smart_minimum_manager(exchange = None) -> SmartMinimumManager:
    """Get or create the global smart minimum manager instance."""
    global _smart_minimum_manager
    if _smart_minimum_manager is None:
        _smart_minimum_manager = SmartMinimumManager(exchange)
    return _smart_minimum_manager


async def get_portfolio_minimum(symbol: str) -> Dict[str, float]:
    """Get minimum requirements for a portfolio pair."""
    manager = get_smart_minimum_manager()
    return await manager.get_minimum_for_pair(symbol)


async def calculate_portfolio_volume(symbol: str, balance: float, price: float) -> Tuple[float, str]:
    """Calculate optimal volume for a portfolio pair."""
    manager = get_smart_minimum_manager()
    return await manager.calculate_optimal_volume(symbol, balance, price)
