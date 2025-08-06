"""
Trading Bot Safety Wrapper
Prevents runaway trading and protects API keys
"""

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TradingSafetyWrapper:
    """Safety controls to prevent bot from going crazy"""

    def __init__(self):
        self.start_time = time.time()
        self.trade_count = 0
        self.order_count = 0
        self.error_count = 0
        self.last_order_time = 0
        self.circuit_breaker_active = False

        # Safety limits
        self.limits = {
            'max_orders_per_minute': 10,  # Conservative limit
            'max_trades_per_hour': 50,
            'max_errors_before_stop': 10,
            'min_order_interval_seconds': 2,  # 2 seconds between orders
            'max_daily_orders': 500,
            'emergency_stop_loss_pct': 5.0  # Stop if down 5%
        }

        # Tracking
        self.daily_pnl = 0.0
        self.orders_today = 0
        self.errors_consecutive = 0

        logger.info("[SAFETY] Trading safety wrapper initialized")

    def check_order_allowed(self, symbol: str, side: str, amount: float) -> tuple[bool, str]:
        """Check if order should be allowed"""

        # Check circuit breaker
        if self.circuit_breaker_active:
            return False, "Circuit breaker active - trading halted"

        # Check order frequency
        current_time = time.time()
        time_since_last = current_time - self.last_order_time

        if time_since_last < self.limits['min_order_interval_seconds']:
            return False, f"Too fast - wait {self.limits['min_order_interval_seconds'] - time_since_last:.1f}s"

        # Check daily order limit
        if self.orders_today >= self.limits['max_daily_orders']:
            return False, f"Daily order limit reached ({self.limits['max_daily_orders']})"

        # Check error count
        if self.error_count >= self.limits['max_errors_before_stop']:
            self.activate_circuit_breaker("Too many errors")
            return False, "Too many errors - circuit breaker activated"

        # Check for suspicious patterns
        if amount > 1000:  # Suspiciously large order
            return False, f"Order size too large: {amount} USDT"

        # All checks passed
        return True, "OK"

    def record_order_placed(self, order_id: str):
        """Record that an order was placed"""
        self.order_count += 1
        self.orders_today += 1
        self.last_order_time = time.time()
        self.errors_consecutive = 0  # Reset on success
        logger.info(f"[SAFETY] Order placed - Total today: {self.orders_today}")

    def record_error(self, error: str):
        """Record an error occurrence"""
        self.error_count += 1
        self.errors_consecutive += 1

        logger.warning(f"[SAFETY] Error #{self.error_count}: {error}")

        # Activate circuit breaker on consecutive errors
        if self.errors_consecutive >= 5:
            self.activate_circuit_breaker("5 consecutive errors")

    def activate_circuit_breaker(self, reason: str):
        """Emergency stop trading"""
        self.circuit_breaker_active = True
        logger.error(f"[SAFETY] ⚠️ CIRCUIT BREAKER ACTIVATED: {reason}")
        logger.error("[SAFETY] Trading halted - manual intervention required")

    def update_pnl(self, profit: float):
        """Update profit/loss tracking"""
        self.daily_pnl += profit

        # Check emergency stop loss
        if self.daily_pnl < 0 and abs(self.daily_pnl) > self.limits['emergency_stop_loss_pct']:
            self.activate_circuit_breaker(f"Daily loss exceeded {self.limits['emergency_stop_loss_pct']}%")

    def get_status(self) -> Dict[str, Any]:
        """Get current safety status"""
        uptime = time.time() - self.start_time

        return {
            'circuit_breaker': self.circuit_breaker_active,
            'orders_today': self.orders_today,
            'errors_total': self.error_count,
            'errors_consecutive': self.errors_consecutive,
            'daily_pnl': self.daily_pnl,
            'uptime_hours': uptime / 3600,
            'orders_per_hour': (self.order_count / uptime) * 3600 if uptime > 0 else 0
        }

    def reset_daily_counters(self):
        """Reset daily counters (call at UTC midnight)"""
        logger.info(f"[SAFETY] Daily reset - Orders: {self.orders_today}, PnL: ${self.daily_pnl:.2f}")
        self.orders_today = 0
        self.daily_pnl = 0.0


# Global safety instance
safety_wrapper = TradingSafetyWrapper()


def safe_order_check(func):
    """Decorator to check if orders are safe to place"""
    async def wrapper(*args, **kwargs):
        # Extract order details
        symbol = kwargs.get('symbol', 'unknown')
        side = kwargs.get('side', 'unknown')
        amount = kwargs.get('amount', 0)

        # Check safety
        allowed, reason = safety_wrapper.check_order_allowed(symbol, side, amount)

        if not allowed:
            logger.warning(f"[SAFETY] Order blocked: {reason}")
            logger.warning(f"[SAFETY] Attempted: {side} {amount} {symbol}")
            return {
                'success': False,
                'error': f'Safety check failed: {reason}',
                'safety_blocked': True
            }

        # Execute order
        try:
            result = await func(*args, **kwargs)

            # Record success
            if result.get('success'):
                safety_wrapper.record_order_placed(result.get('order_id'))
            else:
                safety_wrapper.record_error(result.get('error', 'Unknown error'))

            return result

        except Exception as e:
            safety_wrapper.record_error(str(e))
            raise

    return wrapper
