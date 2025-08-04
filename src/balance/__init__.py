"""
Balance Management System
========================

Unified balance management system for the crypto trading bot with:
- Real-time balance streaming via WebSocket V2
- REST API fallback for balance queries
- Intelligent caching with TTL and LRU eviction
- Thread-safe operations for concurrent trading
- Balance history tracking and analysis
- Circuit breaker integration for resilience
- Decimal precision for accurate financial calculations

Main Components:
- BalanceManager: Main balance management system
- BalanceCache: Intelligent caching with TTL and LRU
- BalanceValidator: Balance validation and consistency checks
- BalanceHistory: Balance history tracking and analysis

Usage:
    from src.balance import BalanceManager
    
    manager = BalanceManager(websocket_client, rest_client)
    await manager.initialize()
    
    # Get current balance
    usdt_balance = await manager.get_balance("USDT")
    
    # Get all balances
    balances = await manager.get_all_balances()
    
    # Register for balance updates
    manager.register_callback(my_balance_callback)
"""

from .balance_manager import BalanceManager
from .balance_cache import BalanceCache, BalanceCacheEntry
from .balance_validator import BalanceValidator, BalanceValidationResult
from .balance_history import BalanceHistory, BalanceHistoryEntry

__all__ = [
    'BalanceManager',
    'BalanceCache',
    'BalanceCacheEntry',
    'BalanceValidator',
    'BalanceValidationResult',
    'BalanceHistory',
    'BalanceHistoryEntry'
]