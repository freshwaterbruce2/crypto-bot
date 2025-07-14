"""
Import redirect for legacy bot.py imports
Redirects all imports to the correct location: src.core.bot
"""

# Import everything from the actual bot location
from src.core.bot import *

# Specifically import the main class for direct access
from src.core.bot import KrakenTradingBot

# Make sure the main class is available for legacy imports
TradingBot = KrakenTradingBot  # Alias for compatibility
__all__ = ['KrakenTradingBot', 'TradingBot']
