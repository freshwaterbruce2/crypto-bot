"""
Kraken Trading Modules - Intelligent Modular Architecture

Specialized modules for Kraken exchange integration, broken down from
the monolithic kraken_exchange.py for better maintainability while
preserving proven profit-generating functionality.
"""

# Version info
__version__ = "2025.1.0"
__author__ = "Kraken Trading Bot 2025"

# Import and export main components
from .config_manager import AccountTier, KrakenConfigManager, OptimizedConfig
from .connection_manager import ConnectionState, KrakenConnectionManager

__all__ = [
    "KrakenConfigManager",
    "AccountTier",
    "OptimizedConfig",
    "KrakenConnectionManager",
    "ConnectionState",
]
