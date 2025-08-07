# C:\projects050625\projects\active\tool-crypto-trading-bot-2025\src\utils\__init__.py

from .custom_logging import configure_logging, log_trade_opportunity, logger
from .kraken_rl import KrakenRateLimiter

# Network and rate limiting
from .network import ResilientRequest, check_connectivity, resilient_get, resilient_post
from .path_manager import PathManager
from .rate_limit_handler import RateLimitError, safe_api_call, safe_exchange_call
from .safe_import import (
    SafeImporter,
    ensure_module_installed,
    register_fallback,
    register_repair_callback,
    safe_import,
    validate_dependencies,
)

# Core system components that exist
from .self_repair import RepairAction, SelfRepairSystem

# Enhanced components
from .trade_helpers import (
    TradeMetrics,
    TradeRecord,
    analyze_trade_performance,
    calculate_micro_scalp_targets,
    calculate_snowball_position_size,
    is_profitable_exit,
)
from .trade_rules import (
    KrakenTradeRules,
    can_sell,
    check_order,
    format_order_amount,
    get_minimum_buy,
    trade_rules,
)

__all__ = [
    "logger",
    "configure_logging",
    "log_trade_opportunity",
    "PathManager",
    "KrakenTradeRules",
    "trade_rules",
    "check_order",
    "can_sell",
    "get_minimum_buy",
    "format_order_amount",
    # Network and rate limiting
    "ResilientRequest",
    "resilient_get",
    "resilient_post",
    "check_connectivity",
    "KrakenRateLimiter",
    "safe_exchange_call",
    "safe_api_call",
    "RateLimitError",
    # Core system
    "SelfRepairSystem",
    "RepairAction",
    # Enhanced trading
    "TradeMetrics",
    "TradeRecord",
    "calculate_snowball_position_size",
    "calculate_micro_scalp_targets",
    "is_profitable_exit",
    "analyze_trade_performance",
    # Safe imports
    "safe_import",
    "register_fallback",
    "register_repair_callback",
    "validate_dependencies",
    "ensure_module_installed",
    "SafeImporter",
]
