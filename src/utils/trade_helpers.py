"""
Trade Helpers
Trading calculation utilities and trade record management
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradeMetrics:
    """Trade performance metrics"""
    profit_pct: float
    profit_usd: float
    fees_paid: float
    hold_time_seconds: float
    entry_price: float
    exit_price: float
    amount: float


@dataclass
class TradeRecord:
    """Complete trade record"""
    symbol: str
    side: str
    amount: float
    price: float
    timestamp: float
    order_id: Optional[str] = None
    fees: float = 0.0
    status: str = "pending"


def calculate_snowball_position_size(current_balance: float, base_size: float = 2.0,
                                   profit_multiplier: float = 1.1) -> float:
    """Calculate position size based on snowball effect"""
    if current_balance <= base_size:
        return base_size

    # Gradually increase position size as balance grows
    multiplier = min(profit_multiplier, current_balance / base_size)
    new_size = base_size * multiplier

    # Cap at reasonable limits
    return min(new_size, base_size * 2.0)


def calculate_micro_scalp_targets(entry_price: float, amount: float,
                                target_profit_pct: float = 0.5) -> Dict[str, float]:
    """Calculate micro-scalping targets"""
    target_price = entry_price * (1 + target_profit_pct / 100)
    profit_usd = (target_price - entry_price) * amount

    return {
        'target_price': target_price,
        'profit_usd': profit_usd,
        'profit_pct': target_profit_pct,
        'min_sell_price': entry_price * 1.001  # Minimum 0.1% profit
    }


def is_profitable_exit(entry_price: float, current_price: float,
                      min_profit_pct: float = 0.3) -> bool:
    """Check if current price represents a profitable exit"""
    profit_pct = ((current_price - entry_price) / entry_price) * 100
    return profit_pct >= min_profit_pct


def analyze_trade_performance(trade_record: TradeRecord,
                            exit_price: float, exit_time: float) -> TradeMetrics:
    """Analyze completed trade performance"""
    hold_time = exit_time - trade_record.timestamp
    profit_usd = (exit_price - trade_record.price) * trade_record.amount
    profit_pct = (profit_usd / (trade_record.price * trade_record.amount)) * 100

    return TradeMetrics(
        profit_pct=profit_pct,
        profit_usd=profit_usd,
        fees_paid=trade_record.fees,
        hold_time_seconds=hold_time,
        entry_price=trade_record.price,
        exit_price=exit_price,
        amount=trade_record.amount
    )
