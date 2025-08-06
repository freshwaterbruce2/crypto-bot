#!/usr/bin/env python3
"""
MINIMUM DISCOVERY LEARNING SYSTEM - Dollar Cost Averaging Strategy

This system implements the "try to trade, if it fails learn the minimum, try again" philosophy
for your DCA strategy. Instead of hardcoded minimums, the bot learns optimal amounts through experience.

Philosophy:
- Make trading attempts with available balance
- Learn from "volume minimum not met" errors
- Store learned minimums permanently
- Apply knowledge to future trades
- Continuously improve through experience

DCA Integration:
- Uses available balance efficiently
- Learns optimal position sizes naturally
- Enables progressive position building
- Maximizes opportunities within learned constraints
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MinimumDiscoveryLearning:
    """
    Autonomous minimum discovery learning system for DCA strategy.

    This system learns Kraken trading minimums through experience rather than
    hardcoded values, enabling true DCA with optimal position sizing.
    """

    def __init__(self):
        """Initialize the minimum discovery learning system."""
        # Use centralized path configuration

        # Get project root and construct path relative to it
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # Navigate up from src/autonomous_minimum_learning to project root
        self.storage_dir = project_root / "trading_data" / "minimum_learning"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.learned_minimums_file = self.storage_dir / "kraken_learned_minimums.json"
        self.learning_events_file = self.storage_dir / "learning_events.json"

        # Load existing learned minimums
        self.learned_minimums = self._load_learned_minimums()

        # Learning statistics
        self.learning_stats = {
            "total_attempts": 0,
            "successful_learns": 0,
            "failed_learns": 0,
            "last_update": None
        }

        logger.info(f"[MINIMUM_LEARNING] Initialized with {len(self.learned_minimums)} learned pairs")

    def _load_learned_minimums(self) -> dict[str, dict[str, float]]:
        """Load previously learned minimums from persistent storage."""
        if self.learned_minimums_file.exists():
            try:
                with open(self.learned_minimums_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[MINIMUM_LEARNING] Error loading learned minimums: {e}")
        return {}

    def _save_learned_minimums(self):
        """Save learned minimums to persistent storage."""
        try:
            with open(self.learned_minimums_file, 'w') as f:
                json.dump(self.learned_minimums, f, indent=2)
            logger.info(f"[MINIMUM_LEARNING] Saved {len(self.learned_minimums)} learned minimums")

            # Auto-filter high failure pairs
            self._analyze_and_warn_problematic_pairs()
        except Exception as e:
            logger.error(f"[MINIMUM_LEARNING] Error saving learned minimums: {e}")

    def _log_learning_event(self, event: dict[str, Any]):
        """Log a learning event for analysis."""
        try:
            events = []
            if self.learning_events_file.exists():
                with open(self.learning_events_file) as f:
                    events = json.load(f)

            event['timestamp'] = time.time()
            events.append(event)

            # Keep only last 1000 events
            if len(events) > 1000:
                events = events[-1000:]

            with open(self.learning_events_file, 'w') as f:
                json.dump(events, f, indent=2)
        except Exception as e:
            logger.error(f"[MINIMUM_LEARNING] Error logging learning event: {e}")

    def extract_minimum_from_error(self, error_message: str, pair: str) -> Optional[dict[str, float]]:
        """
        Extract minimum requirements from Kraken error messages.

        Common Kraken error patterns:
        - "EOrder:Order minimum not met (volume too low)"
        - "EOrder:Order minimum not met:BTC/USDT:volume:0.0001"
        - "EOrder:Order minimum cost not met"
        """
        try:
            # Pattern 1: Explicit minimum in error message
            pattern1 = r"minimum.*?(\d+\.?\d*)"
            match1 = re.search(pattern1, error_message, re.IGNORECASE)

            # Pattern 2: Volume specification
            pattern2 = r"volume[:\s]+(\d+\.?\d*)"
            match2 = re.search(pattern2, error_message, re.IGNORECASE)

            # Pattern 3: Cost specification
            pattern3 = r"cost[:\s]+(\d+\.?\d*)"
            match3 = re.search(pattern3, error_message, re.IGNORECASE)

            minimums = {}

            if "volume" in error_message.lower() and (match1 or match2):
                volume = float(match1.group(1) if match1 else match2.group(1))
                minimums['volume'] = volume * 1.1  # Add 10% buffer
                logger.info(f"[MINIMUM_LEARNING] Extracted volume minimum: {minimums['volume']} for {pair}")

            if "cost" in error_message.lower() and (match1 or match3):
                cost = float(match1.group(1) if match1 else match3.group(1))
                minimums['cost'] = cost * 1.1  # Add 10% buffer
                logger.info(f"[MINIMUM_LEARNING] Extracted cost minimum: {minimums['cost']} for {pair}")

            return minimums if minimums else None

        except Exception as e:
            logger.error(f"[MINIMUM_LEARNING] Error extracting minimum from '{error_message}': {e}")
            return None

    def learn_from_error(self, error_message: str, pair: str, attempted_volume: float,
                        attempted_price: float) -> bool:
        """
        Learn minimum requirements from a trading error.

        Args:
            error_message: The error message from Kraken
            pair: Trading pair (e.g., "BTC/USDT")
            attempted_volume: The volume that was attempted
            attempted_price: The price used in the attempt

        Returns:
            bool: True if learning was successful
        """
        self.learning_stats['total_attempts'] += 1

        try:
            # First try to extract explicit minimums from error
            extracted = self.extract_minimum_from_error(error_message, pair)

            if not extracted:
                # Fallback: Infer from attempted values
                if "volume" in error_message.lower():
                    # Volume was too low, estimate minimum
                    estimated_min = attempted_volume * 2  # Conservative estimate
                    extracted = {'volume': estimated_min}
                    logger.info(f"[MINIMUM_LEARNING] Estimated volume minimum: {estimated_min} for {pair}")

                elif "cost" in error_message.lower():
                    # Cost was too low, estimate minimum
                    attempted_cost = attempted_volume * attempted_price
                    estimated_min = max(attempted_cost * 2, 2.0)  # At least $2 for tier 1
                    extracted = {'cost': estimated_min}
                    logger.info(f"[MINIMUM_LEARNING] Estimated cost minimum: {estimated_min} for {pair}")

            if extracted:
                # Update learned minimums
                if pair not in self.learned_minimums:
                    self.learned_minimums[pair] = {}

                self.learned_minimums[pair].update(extracted)
                self.learned_minimums[pair]['last_updated'] = time.time()
                self.learned_minimums[pair]['learn_count'] = self.learned_minimums[pair].get('learn_count', 0) + 1

                # Save to persistent storage
                self._save_learned_minimums()

                # Log the learning event
                self._log_learning_event({
                    'type': 'minimum_learned',
                    'pair': pair,
                    'minimums': extracted,
                    'error_message': error_message,
                    'attempted_volume': attempted_volume,
                    'attempted_price': attempted_price
                })

                self.learning_stats['successful_learns'] += 1
                self.learning_stats['last_update'] = time.time()

                return True

        except Exception as e:
            logger.error(f"[MINIMUM_LEARNING] Error learning from error: {e}")
            self.learning_stats['failed_learns'] += 1

        return False

    def get_learned_minimums(self, pair: str) -> Optional[dict[str, float]]:
        """
        Get learned minimums for a trading pair.

        Returns:
            Dict with 'volume' and/or 'cost' minimums, or None if not learned yet
        """
        if pair in self.learned_minimums:
            minimums = self.learned_minimums[pair].copy()
            # Remove metadata fields
            minimums.pop('last_updated', None)
            minimums.pop('learn_count', None)
            return minimums
        return None

    def suggest_trade_volume(self, pair: str, available_balance: float,
                           current_price: float) -> tuple[float, str]:
        """
        Suggest optimal trade volume based on learned minimums and available balance.

        This is the heart of the DCA strategy - finding the sweet spot between
        minimum requirements and available capital.

        Args:
            pair: Trading pair
            available_balance: Available USDT balance
            current_price: Current price of the asset

        Returns:
            Tuple of (suggested_volume, reason)
        """
        learned = self.get_learned_minimums(pair)

        if not learned:
            # No learned minimums yet - start with conservative estimate
            # This will trigger learning if it fails
            suggested_volume = available_balance / current_price * 0.9  # Use 90% of available
            return suggested_volume, "No learned minimums - attempting with available balance"

        # Calculate volumes based on different constraints
        candidates = []

        # Volume-based minimum
        if 'volume' in learned:
            min_volume = learned['volume']
            candidates.append((min_volume, f"Learned volume minimum: {min_volume}"))

        # Cost-based minimum
        if 'cost' in learned:
            min_cost = learned['cost']
            min_volume_from_cost = min_cost / current_price
            candidates.append((min_volume_from_cost, f"Learned cost minimum: ${min_cost}"))

        # Available balance constraint
        max_volume_from_balance = available_balance / current_price * 0.95  # Keep 5% buffer

        # Choose the maximum of all minimums (most conservative)
        if candidates:
            suggested_volume, reason = max(candidates, key=lambda x: x[0])

            # But don't exceed available balance
            if suggested_volume > max_volume_from_balance:
                return max_volume_from_balance, f"Limited by balance: ${available_balance:.2f}"

            return suggested_volume * 1.05, reason + " (with 5% buffer)"

        # Fallback
        return max_volume_from_balance, "Using available balance"

    def get_learning_stats(self) -> dict[str, Any]:
        """Get learning statistics for monitoring."""
        return {
            **self.learning_stats,
            'pairs_learned': len(self.learned_minimums),
            'total_minimums': sum(len(m) - 2 for m in self.learned_minimums.values())  # Exclude metadata
        }

    def bulk_learn_minimums(self, pairs_data: dict[str, dict[str, float]]) -> int:
        """
        Bulk learn minimums for multiple pairs (useful for initialization).

        Args:
            pairs_data: Dict mapping symbols to their minimum requirements
                       e.g., {"SOL/USDT": {"volume": 0.01, "cost": 1.0}}

        Returns:
            Number of pairs successfully learned
        """
        learned_count = 0

        for pair, minimums in pairs_data.items():
            try:
                if pair not in self.learned_minimums:
                    self.learned_minimums[pair] = {}

                self.learned_minimums[pair].update(minimums)
                self.learned_minimums[pair]['last_updated'] = time.time()
                self.learned_minimums[pair]['learn_count'] = 1
                self.learned_minimums[pair]['bulk_learned'] = True

                learned_count += 1
                logger.info(f"[MINIMUM_LEARNING] Bulk learned minimums for {pair}: {minimums}")

            except Exception as e:
                logger.error(f"[MINIMUM_LEARNING] Error bulk learning {pair}: {e}")

        if learned_count > 0:
            self._save_learned_minimums()
            self._log_learning_event({
                'type': 'bulk_learn',
                'pairs_count': learned_count,
                'pairs': list(pairs_data.keys())
            })

        return learned_count

    def get_portfolio_pairs_status(self, portfolio_pairs: list[str]) -> dict[str, bool]:
        """
        Check which portfolio pairs have learned minimums.

        Args:
            portfolio_pairs: List of trading pairs to check

        Returns:
            Dict mapping pairs to whether they have learned minimums
        """
        status = {}
        for pair in portfolio_pairs:
            status[pair] = pair in self.learned_minimums
        return status


# Global instance for easy access
minimum_discovery_learning = MinimumDiscoveryLearning()


# Convenience functions for direct usage
def learn_from_kraken_error(error_message: str, pair: str, attempted_volume: float,
                           attempted_price: float) -> bool:
    """Learn from a Kraken trading error."""
    return minimum_discovery_learning.learn_from_error(
        error_message, pair, attempted_volume, attempted_price
    )


def get_suggested_volume(pair: str, available_balance: float, current_price: float) -> tuple[float, str]:
    """Get suggested trading volume based on learned minimums."""
    return minimum_discovery_learning.suggest_trade_volume(
        pair, available_balance, current_price
    )


def get_learned_minimums(pair: str) -> Optional[dict[str, float]]:
    """Get learned minimums for a pair."""
    return minimum_discovery_learning.get_learned_minimums(pair)
