#!/usr/bin/env python3
"""
High Failure Pair Filter
========================

Automatically filters out trading pairs that have high failure rates
due to volume minimum issues, preventing repeated failed attempts.
"""

import json
import logging
from pathlib import Path
from typing import List, Set

logger = logging.getLogger(__name__)

class HighFailureFilter:
    """Filters trading pairs with high failure rates"""

    def __init__(self):
        """Initialize the high failure filter"""
        self.project_root = Path(__file__).parent.parent.parent
        self.minimums_file = self.project_root / "trading_data" / "minimum_learning" / "kraken_learned_minimums.json"
        self.blacklist_file = self.project_root / "trading_data" / "high_failure_blacklist.json"

        # Thresholds for filtering
        self.min_learn_count_threshold = 10  # Pairs with 10+ failures
        self.min_volume_threshold = 3.0      # Pairs requiring 3.0+ volume (problematic for $2 trades)

    def get_problematic_pairs(self) -> Set[str]:
        """Get list of pairs that should be avoided due to high failure rates"""
        problematic = set()

        try:
            if not self.minimums_file.exists():
                logger.warning("[FILTER] No learned minimums file found")
                return problematic

            with open(self.minimums_file) as f:
                minimums = json.load(f)

            for pair, data in minimums.items():
                learn_count = data.get('learn_count', 0)
                volume_min = data.get('volume', 0)

                # Filter pairs with high failure rates AND high minimums
                if learn_count >= self.min_learn_count_threshold and volume_min >= self.min_volume_threshold:
                    problematic.add(pair)
                    logger.info(f"[FILTER] Blacklisting {pair}: {learn_count} failures, {volume_min} min volume")

            # Save blacklist
            self._save_blacklist(list(problematic))

        except Exception as e:
            logger.error(f"[FILTER] Error analyzing problematic pairs: {e}")

        return problematic

    def should_trade_pair(self, pair: str) -> bool:
        """Check if a pair should be traded based on failure history"""
        try:
            if not self.minimums_file.exists():
                return True  # No data, allow trading

            with open(self.minimums_file) as f:
                minimums = json.load(f)

            if pair not in minimums:
                return True  # No failure history, allow trading

            data = minimums[pair]
            learn_count = data.get('learn_count', 0)
            volume_min = data.get('volume', 0)

            # Block if high failures AND high minimum
            if learn_count >= self.min_learn_count_threshold and volume_min >= self.min_volume_threshold:
                logger.warning(f"[FILTER] Blocking {pair}: {learn_count} failures, {volume_min} min volume")
                return False

            return True

        except Exception as e:
            logger.error(f"[FILTER] Error checking pair {pair}: {e}")
            return True  # On error, allow trading

    def _save_blacklist(self, blacklisted_pairs: List[str]):
        """Save blacklisted pairs to file"""
        try:
            blacklist_data = {
                "blacklisted_pairs": blacklisted_pairs,
                "updated": str(Path(__file__).stat().st_mtime),
                "criteria": {
                    "min_learn_count": self.min_learn_count_threshold,
                    "min_volume": self.min_volume_threshold
                },
                "reason": "High failure rate with volume minimum errors"
            }

            self.blacklist_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.blacklist_file, 'w') as f:
                json.dump(blacklist_data, f, indent=2)

            logger.info(f"[FILTER] Saved {len(blacklisted_pairs)} blacklisted pairs")

        except Exception as e:
            logger.error(f"[FILTER] Error saving blacklist: {e}")

# Global filter instance
_filter_instance = None

def get_failure_filter() -> HighFailureFilter:
    """Get singleton filter instance"""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = HighFailureFilter()
    return _filter_instance

def should_trade_pair(pair: str) -> bool:
    """Quick check if pair should be traded"""
    return get_failure_filter().should_trade_pair(pair)

def get_problematic_pairs() -> Set[str]:
    """Get set of problematic pairs to avoid"""
    return get_failure_filter().get_problematic_pairs()
