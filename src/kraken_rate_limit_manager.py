"""
Kraken Rate Limit Manager - Comprehensive Protection System
Prevents rate limit violations and manages order flow intelligently
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class KrakenRateLimitManager:
    """
    Manages rate limits per Kraken's specifications:
    - Tracks counters per trading pair
    - Implements decay rates by account tier
    - Provides intelligent order management
    """

    # Account tier configurations
    TIER_CONFIG = {
        'starter': {
            'max_counter': 60,
            'decay_rate': 1.0,  # -1 per second (simplified from -0.33/sec * 3)
            'open_orders_limit': 60
        },
        'intermediate': {
            'max_counter': 125,
            'decay_rate': 2.34,  # -2.34 per second
            'open_orders_limit': 80
        },
        'pro': {
            'max_counter': 180,
            'decay_rate': 3.75,  # -3.75 per second
            'open_orders_limit': 225
        }
    }

    # Order action costs
    ORDER_COSTS = {
        'add_order': 1,
        'amend_order': {
            'fixed': 1,
            '<5s': 3,
            '<10s': 2,
            '<15s': 1
        },
        'cancel_order': {
            '<5s': 8,
            '<10s': 6,
            '<15s': 5,
            '<45s': 4,
            '<90s': 2,
            '<300s': 1
        }
    }

    def __init__(self, account_tier: str = 'intermediate'):
        """Initialize rate limit manager with account tier"""
        self.account_tier = account_tier.lower()
        if self.account_tier not in self.TIER_CONFIG:
            logger.warning(f"Unknown tier '{account_tier}', defaulting to 'intermediate'")
            self.account_tier = 'intermediate'

        self.config = self.TIER_CONFIG[self.account_tier]
        self.counters = {}  # {pair: {'value': float, 'last_update': timestamp}}
        self.order_times = {}  # {order_id: timestamp}
        self.open_orders = {}  # {pair: count}

        # Load saved state if available
        self.state_file = Path('trading_data/cache/rate_limit_state.json')
        self.load_state()

        logger.info(f"[RATE_LIMIT] Initialized for {self.account_tier} tier")
        logger.info(f"[RATE_LIMIT] Max counter: {self.config['max_counter']}, "
                   f"Decay: {self.config['decay_rate']}/sec, "
                   f"Max orders: {self.config['open_orders_limit']}")

    def load_state(self):
        """Load saved rate limit state"""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)

                # Restore counters with decay applied
                current_time = time.time()
                for pair, data in state.get('counters', {}).items():
                    elapsed = current_time - data['last_update']
                    decayed_value = max(0, data['value'] - (elapsed * self.config['decay_rate']))

                    if decayed_value > 0:
                        self.counters[pair] = {
                            'value': decayed_value,
                            'last_update': current_time
                        }
                        logger.info(f"[RATE_LIMIT] Restored {pair} counter: {decayed_value:.1f}")

                # Restore order times (only recent ones)
                cutoff_time = current_time - 300  # Keep orders from last 5 minutes
                self.order_times = {
                    order_id: timestamp
                    for order_id, timestamp in state.get('order_times', {}).items()
                    if timestamp > cutoff_time
                }

                logger.info(f"[RATE_LIMIT] Restored state: {len(self.counters)} pairs, "
                           f"{len(self.order_times)} recent orders")
        except Exception as e:
            logger.error(f"[RATE_LIMIT] Failed to load state: {e}")

    def save_state(self):
        """Save current rate limit state"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                'timestamp': time.time(),
                'account_tier': self.account_tier,
                'counters': self.counters,
                'order_times': self.order_times,
                'open_orders': self.open_orders
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"[RATE_LIMIT] Failed to save state: {e}")

    def get_counter(self, pair: str) -> float:
        """Get current counter value for a pair with decay applied"""
        current_time = time.time()

        if pair not in self.counters:
            return 0.0

        data = self.counters[pair]
        elapsed = current_time - data['last_update']
        decayed_value = max(0, data['value'] - (elapsed * self.config['decay_rate']))

        # Update the counter with decayed value
        if decayed_value > 0:
            self.counters[pair] = {
                'value': decayed_value,
                'last_update': current_time
            }
        else:
            # Counter fully decayed, remove it
            del self.counters[pair]
            return 0.0

        return decayed_value

    def increment_counter(self, pair: str, amount: float):
        """Increment counter for a pair"""
        current_value = self.get_counter(pair)
        current_time = time.time()

        self.counters[pair] = {
            'value': current_value + amount,
            'last_update': current_time
        }

        # Save state after increment
        self.save_state()

    def can_place_order(self, pair: str) -> Tuple[bool, str]:
        """Check if we can place an order on this pair"""
        current_counter = self.get_counter(pair)

        # Check rate limit
        if current_counter + 1 > self.config['max_counter']:
            return False, f"Rate limit would be exceeded ({current_counter:.1f} + 1 > {self.config['max_counter']})"

        # Check open orders limit
        open_count = self.open_orders.get(pair, 0)
        if open_count >= self.config['open_orders_limit']:
            return False, f"Open orders limit reached ({open_count}/{self.config['open_orders_limit']})"

        return True, "OK"

    def can_cancel_order(self, pair: str, order_id: str) -> Tuple[bool, str, int]:
        """Check if we can cancel an order and return the penalty"""
        current_counter = self.get_counter(pair)

        # Get order age
        order_time = self.order_times.get(order_id, 0)
        if order_time == 0:
            # Unknown order, assume it's old
            penalty = 1
        else:
            age = time.time() - order_time

            # Calculate penalty based on age
            if age < 5:
                penalty = 8
            elif age < 10:
                penalty = 6
            elif age < 15:
                penalty = 5
            elif age < 45:
                penalty = 4
            elif age < 90:
                penalty = 2
            elif age < 300:
                penalty = 1
            else:
                penalty = 0  # No penalty for old orders

        # Check if cancel would exceed limit
        if current_counter + penalty > self.config['max_counter']:
            return False, f"Cancel would exceed rate limit ({current_counter:.1f} + {penalty} > {self.config['max_counter']})", penalty

        return True, "OK", penalty

    def record_order_placed(self, pair: str, order_id: str):
        """Record that an order was placed"""
        # Increment counter
        self.increment_counter(pair, 1)

        # Record order time
        self.order_times[order_id] = time.time()

        # Increment open orders
        self.open_orders[pair] = self.open_orders.get(pair, 0) + 1

        logger.debug(f"[RATE_LIMIT] Order placed on {pair}: counter={self.get_counter(pair):.1f}")

    def record_order_cancelled(self, pair: str, order_id: str):
        """Record that an order was cancelled"""
        # Calculate and apply penalty
        _, _, penalty = self.can_cancel_order(pair, order_id)

        if penalty > 0:
            self.increment_counter(pair, penalty)

        # Remove order time
        if order_id in self.order_times:
            del self.order_times[order_id]

        # Decrement open orders
        if pair in self.open_orders and self.open_orders[pair] > 0:
            self.open_orders[pair] -= 1

        logger.debug(f"[RATE_LIMIT] Order cancelled on {pair}: penalty={penalty}, counter={self.get_counter(pair):.1f}")

    def get_counter_status(self, pair: str) -> Dict[str, Any]:
        """Get detailed status for a pair"""
        current_counter = self.get_counter(pair)
        max_counter = self.config['max_counter']
        percentage = (current_counter / max_counter * 100) if max_counter > 0 else 0

        # Determine status level
        if percentage >= 90:
            status = "CRITICAL"
        elif percentage >= 70:
            status = "WARNING"
        elif percentage >= 50:
            status = "CAUTION"
        else:
            status = "SAFE"

        return {
            'pair': pair,
            'counter': round(current_counter, 1),
            'max': max_counter,
            'percentage': round(percentage, 1),
            'status': status,
            'can_trade': current_counter + 1 <= max_counter,
            'open_orders': self.open_orders.get(pair, 0),
            'max_orders': self.config['open_orders_limit']
        }

    def get_all_pairs_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all pairs with non-zero counters"""
        status = {}

        # Get all pairs from counters and open_orders
        all_pairs = set(self.counters.keys()) | set(self.open_orders.keys())

        for pair in all_pairs:
            pair_status = self.get_counter_status(pair)
            if pair_status['counter'] > 0 or pair_status['open_orders'] > 0:
                status[pair] = pair_status

        return status

    def get_safest_pair(self, pairs: List[str]) -> Optional[str]:
        """Find the pair with the lowest counter from a list"""
        if not pairs:
            return None

        safest_pair = None
        lowest_counter = float('inf')

        for pair in pairs:
            counter = self.get_counter(pair)
            if counter < lowest_counter:
                lowest_counter = counter
                safest_pair = pair

        return safest_pair

    def should_use_ioc_order(self, pair: str) -> bool:
        """Determine if IOC (Immediate or Cancel) orders should be used"""
        status = self.get_counter_status(pair)

        # Use IOC when counter is above 60% to avoid cancel penalties
        return status['percentage'] > 60

    def estimate_recovery_time(self, pair: str) -> Dict[str, float]:
        """Estimate time until counter recovers to various levels"""
        current_counter = self.get_counter(pair)
        decay_rate = self.config['decay_rate']

        # Time to reach different thresholds
        time_to_50_percent = max(0, (current_counter - self.config['max_counter'] * 0.5) / decay_rate)
        time_to_tradeable = max(0, (current_counter - (self.config['max_counter'] - 1)) / decay_rate)
        time_to_zero = current_counter / decay_rate

        return {
            'to_50_percent': round(time_to_50_percent, 1),
            'to_tradeable': round(time_to_tradeable, 1),
            'to_zero': round(time_to_zero, 1)
        }

    def get_safe_cancel_orders(self, pair: str, order_ids: List[str], max_penalty: int = None) -> List[str]:
        """Get list of orders that can be safely cancelled without exceeding limits"""
        if max_penalty is None:
            max_penalty = self.config['max_counter'] - self.get_counter(pair) - 5  # Keep buffer of 5

        safe_orders = []
        total_penalty = 0

        # Sort orders by age (oldest first)
        orders_with_age = []
        for order_id in order_ids:
            order_time = self.order_times.get(order_id, 0)
            age = time.time() - order_time if order_time > 0 else float('inf')
            orders_with_age.append((order_id, age))

        orders_with_age.sort(key=lambda x: x[1], reverse=True)

        # Add orders until we hit the penalty limit
        for order_id, age in orders_with_age:
            _, _, penalty = self.can_cancel_order(pair, order_id)

            if total_penalty + penalty <= max_penalty:
                safe_orders.append(order_id)
                total_penalty += penalty
            else:
                break

        return safe_orders

    def get_all_counters(self) -> Dict[str, Dict[str, Any]]:
        """Get all counter values (for persistence)"""
        # Apply decay to all counters first
        all_counters = {}
        for pair in list(self.counters.keys()):
            current_value = self.get_counter(pair)
            if current_value > 0:
                all_counters[pair] = self.counters[pair]

        return all_counters

    def restore_counters(self, counters: Dict[str, Dict[str, Any]]):
        """Restore counters from saved state"""
        current_time = time.time()

        for pair, data in counters.items():
            # Apply decay since last update
            elapsed = current_time - data.get('last_update', current_time)
            decayed_value = max(0, data.get('value', 0) - (elapsed * self.config['decay_rate']))

            if decayed_value > 0:
                self.counters[pair] = {
                    'value': decayed_value,
                    'last_update': current_time
                }
                logger.info(f"[RATE_LIMIT] Restored {pair}: {decayed_value:.1f}")


class RateLimitAwareOrderManager:
    """
    Order manager that integrates with rate limit tracking
    """

    def __init__(self, rate_limiter: KrakenRateLimitManager):
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)

    async def place_order_safe(self, exchange, symbol: str, order_type: str, side: str,
                              amount: float, price: float = None, params: Dict = None) -> Optional[Dict]:
        """Place order with rate limit checking"""

        # Check if we can place the order
        can_place, reason = self.rate_limiter.can_place_order(symbol)

        if not can_place:
            self.logger.warning(f"[ORDER] Cannot place order on {symbol}: {reason}")

            # Consider using IOC if counter is high
            if self.rate_limiter.should_use_ioc_order(symbol) and order_type == 'limit':
                self.logger.info("[ORDER] Attempting IOC order due to high counter")
                if params is None:
                    params = {}
                params['timeInForce'] = 'IOC'
            else:
                return None

        try:
            # Place the order
            order = await exchange.create_order(symbol, order_type, side, amount, price, params)

            # Record the order
            self.rate_limiter.record_order_placed(symbol, order['id'])

            # Log status
            status = self.rate_limiter.get_counter_status(symbol)
            self.logger.info(f"[ORDER] Placed on {symbol} - Counter: {status['counter']}/{status['max']} ({status['percentage']}%)")

            return order

        except Exception as e:
            self.logger.error(f"[ORDER] Failed to place order: {e}")
            raise

    async def cancel_order_safe(self, exchange, order_id: str, symbol: str) -> Optional[Dict]:
        """Cancel order with rate limit checking"""

        # Check if we can cancel
        can_cancel, reason, penalty = self.rate_limiter.can_cancel_order(symbol, order_id)

        if not can_cancel:
            self.logger.warning(f"[ORDER] Cannot cancel on {symbol}: {reason}")

            # Check if it's worth waiting
            recovery = self.rate_limiter.estimate_recovery_time(symbol)
            if recovery['to_tradeable'] < 30:
                self.logger.info(f"[ORDER] Waiting {recovery['to_tradeable']}s before cancel")
                await asyncio.sleep(recovery['to_tradeable'])
                # Retry
                can_cancel, reason, penalty = self.rate_limiter.can_cancel_order(symbol, order_id)
                if not can_cancel:
                    return None
            else:
                return None

        try:
            # Cancel the order
            result = await exchange.cancel_order(order_id, symbol)

            # Record the cancellation
            self.rate_limiter.record_order_cancelled(symbol, order_id)

            # Log status
            status = self.rate_limiter.get_counter_status(symbol)
            self.logger.warning(f"[ORDER] Cancelled on {symbol} (penalty: {penalty}) - Counter: {status['counter']}/{status['max']}")

            return result

        except Exception as e:
            self.logger.error(f"[ORDER] Failed to cancel order: {e}")
            raise

    async def cleanup_old_orders_safe(self, exchange, symbols: List[str], min_age_seconds: int = 300):
        """Clean up old orders respecting rate limits"""

        for symbol in symbols:
            try:
                # Check counter status first
                status = self.rate_limiter.get_counter_status(symbol)
                if status['percentage'] > 70:
                    self.logger.warning(f"[CLEANUP] Skipping {symbol} - counter at {status['percentage']}%")
                    continue

                # Get open orders
                open_orders = await exchange.fetch_open_orders(symbol)

                if not open_orders:
                    continue

                # Filter old orders
                current_time = time.time()
                old_order_ids = []

                for order in open_orders:
                    order_time = order['timestamp'] / 1000
                    age = current_time - order_time

                    if age > min_age_seconds:
                        old_order_ids.append(order['id'])

                if old_order_ids:
                    # Get safe cancellation list
                    safe_ids = self.rate_limiter.get_safe_cancel_orders(symbol, old_order_ids)

                    self.logger.info(f"[CLEANUP] {symbol}: Cancelling {len(safe_ids)}/{len(old_order_ids)} old orders")

                    for order_id in safe_ids:
                        await self.cancel_order_safe(exchange, order_id, symbol)
                        await asyncio.sleep(1)  # Delay between cancels

            except Exception as e:
                self.logger.error(f"[CLEANUP] Error processing {symbol}: {e}")


# Export classes
__all__ = ['KrakenRateLimitManager', 'RateLimitAwareOrderManager']
