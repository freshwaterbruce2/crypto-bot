# C:\projects050625\projects\active\tool-crypto-trading-bot-2025\src\utils\__init__.py

from .custom_logging import logger, configure_logging, log_trade_opportunity
from .path_manager import PathManager
from .trade_rules import (
    KrakenTradeRules,
    trade_rules,
    check_order,
    can_sell,
    get_minimum_buy,
    format_order_amount
)

# Network and rate limiting
from .network import ResilientRequest, resilient_get, resilient_post, check_connectivity
from .kraken_rl import KrakenRateLimiter
from .rate_limit_handler import safe_exchange_call, safe_api_call, RateLimitError

# Core system components that exist
from .self_repair import SelfRepairSystem, RepairAction

# Enhanced components
from .trade_helpers import (
    TradeMetrics,
    TradeRecord,
    calculate_snowball_position_size,
    calculate_micro_scalp_targets,
    is_profitable_exit,
    analyze_trade_performance
)
from .safe_import import (
    safe_import,
    register_fallback,
    register_repair_callback,
    validate_dependencies,
    ensure_module_installed,
    SafeImporter
)

__all__ = [
    'logger',
    'configure_logging',
    'log_trade_opportunity',
    'PathManager',
    'KrakenTradeRules',
    'trade_rules',
    'check_order',
    'can_sell',
    'get_minimum_buy',
    'format_order_amount',
    # Network and rate limiting
    'ResilientRequest',
    'resilient_get',
    'resilient_post',
    'check_connectivity',
    'KrakenRateLimiter',
    'safe_exchange_call',
    'safe_api_call',
    'RateLimitError',
    # Core system
    'SelfRepairSystem',
    'RepairAction',
    # Enhanced trading
    'TradeMetrics',
    'TradeRecord',
    'calculate_snowball_position_size',
    'calculate_micro_scalp_targets',
    'is_profitable_exit',
    'analyze_trade_performance',
    # Safe imports
    'safe_import',
    'register_fallback',
    'register_repair_callback',
    'validate_dependencies',
    'ensure_module_installed',
    'SafeImporter'
]