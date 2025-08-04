"""
Database module for Crypto Trading Bot
Provides comprehensive database operations following 2025 best practices
"""

from .database_manager import (
    DatabaseManager,
    TradeRecord,
    OrderRecord,
    BalanceRecord,
    get_database_manager
)

__all__ = [
    'DatabaseManager',
    'TradeRecord', 
    'OrderRecord',
    'BalanceRecord',
    'get_database_manager'
]

__version__ = '1.0.0'