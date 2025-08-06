"""Minimum Provider
Centralized access to Kraken minimum order requirements.

Resolves minimum volume (ordermin) and minimum cost (costmin) for a symbol.
Workflow:
1. AutonomousMinimumLearning cache (learned from past errors)
2. AssetPairStore (live data fetched from Kraken / cached)
3. Static Kraken fallback table (single source of truth)
4. Ultimate absolute fallback (ultra-micro)

Usage:
    from utils.minimum_provider import get_dynamic_minimums
    vol_min, cost_min = get_dynamic_minimums("BTC/USDT")

This single module eliminates scattered hard-coded minimums across the codebase.
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple

# Lazy imports to avoid circular dependencies
try:
    from autonomous_minimum_learning import minimum_discovery_learning  # type: ignore
except Exception:  # pragma: no cover
    minimum_discovery_learning = None  # Fallback if module not present

try:
    from utils.asset_pair_store import AssetPairStore

    # Global store instance (uses underlying async fetch cache internally)
    _asset_pair_store = AssetPairStore()
except Exception:  # pragma: no cover
    _asset_pair_store = None

logger = logging.getLogger(__name__)

# Static Kraken fallback table (USDT pairs only per project requirements)
# Updated to include all 12 portfolio pairs
_STATIC_KRAKEN_MINIMUMS: Dict[str, Dict[str, float]] = {
    # Core portfolio pairs with known minimums
    "BTC/USDT": {"volume": 0.00001, "cost": 1.0},
    "ETH/USDT": {"volume": 0.0001, "cost": 1.0},
    "SOL/USDT": {"volume": 0.01, "cost": 1.0},
    "ADA/USDT": {"volume": 1.0, "cost": 1.0},
    "SHIB/USDT": {"volume": 50000.0, "cost": 1.0},
    "DOGE/USDT": {"volume": 10.0, "cost": 1.0},
    "AVAX/USDT": {"volume": 0.1, "cost": 1.0},
    "DOT/USDT": {"volume": 0.1, "cost": 1.0},
    "MATIC/USDT": {"volume": 1.0, "cost": 1.0},
    "XRP/USDT": {"volume": 1.0, "cost": 1.0},

    # Additional portfolio pairs
    "ALGO/USDT": {"volume": 1.0, "cost": 1.0},
    "ATOM/USDT": {"volume": 0.1, "cost": 1.0},
    "LINK/USDT": {"volume": 0.1, "cost": 1.0},
    "MANA/USDT": {"volume": 1.0, "cost": 1.0},

    # Meme coins (conservative estimates)
    "AI16Z/USDT": {"volume": 1.0, "cost": 5.0},
    "BERA/USDT": {"volume": 1.0, "cost": 5.0},
    "FARTCOIN/USDT": {"volume": 100.0, "cost": 5.0},
}

_ABSOLUTE_MIN_VOLUME = 0.000001
_ABSOLUTE_MIN_COST = 0.01


def _from_autonomous_learning(symbol: str) -> Tuple[float | None, float | None]:
    if minimum_discovery_learning is None:
        return None, None
    try:
        learned = minimum_discovery_learning.get_learned_minimum(symbol)
        if learned:
            return float(learned.get("ordermin", 0)), float(learned.get("costmin", 0))
    except Exception as e:  # pragma: no cover
        logger.debug(f"MinimumProvider: error reading autonomous cache for {symbol}: {e}")
    return None, None


def _from_asset_pair_store(symbol: str) -> Tuple[float | None, float | None]:
    if _asset_pair_store is None:
        return None, None
    try:
        pair_info = _asset_pair_store.get_pair_info(symbol)
        if pair_info and hasattr(pair_info, "ordermin") and hasattr(pair_info, "costmin"):
            return float(pair_info.ordermin), float(pair_info.costmin)
    except Exception as e:  # pragma: no cover
        logger.debug(f"MinimumProvider: asset pair store failure for {symbol}: {e}")
    return None, None


def _from_static_table(symbol: str) -> Tuple[float | None, float | None]:
    data = _STATIC_KRAKEN_MINIMUMS.get(symbol)
    if data:
        return data["volume"], data["cost"]
    return None, None


def get_dynamic_minimums(symbol: str) -> Tuple[float, float]:
    """Return (min_volume, min_cost) for symbol.

    Order of precedence:
    1. Autonomous learning cache (freshly learned real values)
    2. Live AssetPairStore data
    3. Static Kraken fallback table (maintained centrally)
    4. Absolute ultra-micro fallback
    """

    # 1. Learned values
    vol, cost = _from_autonomous_learning(symbol)
    if vol and cost:
        logger.debug(f"MinimumProvider: using learned minimums for {symbol} -> {vol}, {cost}")
        return vol, cost

    # 2. AssetPairStore values
    vol, cost = _from_asset_pair_store(symbol)
    if vol and cost:
        logger.debug(f"MinimumProvider: using AssetPairStore minimums for {symbol} -> {vol}, {cost}")
        return vol, cost

    # 3. Static table
    vol, cost = _from_static_table(symbol)
    if vol and cost:
        logger.debug(f"MinimumProvider: using static fallback minimums for {symbol} -> {vol}, {cost}")
        return vol, cost

    # 4. Absolute fallback
    logger.warning(
        f"MinimumProvider: No minimums found for {symbol}. Using absolute fallback {_ABSOLUTE_MIN_VOLUME}, {_ABSOLUTE_MIN_COST}"
    )
    return _ABSOLUTE_MIN_VOLUME, _ABSOLUTE_MIN_COST
