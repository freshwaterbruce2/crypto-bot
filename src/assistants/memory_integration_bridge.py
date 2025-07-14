"""
Memory Integration Bridge
=========================

This module provides the logic to connect the MemoryAssistant to the main
KrakenTradingBot application, making the persistent memory system available
to all other components.

Features:
- Attaches persistent memory (vector or lightweight) to the bot
- Handles fallback and integration automatically
- Logs integration status and errors

Usage Example:
    from src.assistants.memory_integration_bridge import setup_memory_integration
    await setup_memory_integration(bot)
"""

import logging
import sys
from typing import TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular import errors at runtime
if TYPE_CHECKING:
    from ..bot import KrakenTradingBot

from .memory_assistant import MemoryAssistant

logger = logging.getLogger(__name__)

async def setup_memory_integration(bot: 'KrakenTradingBot') -> bool:
    """
    Initializes and attaches the memory system to the main bot instance.

    This function creates an instance of the MemoryAssistant and attaches it
    and this bridge to the bot, making it accessible to other components.
    If vector memory is unavailable, the bot will use lightweight memory automatically.

    Args:
        bot (KrakenTradingBot): The main instance of the trading bot.

    Returns:
        bool: True if initialization was successful, False otherwise.

    Troubleshooting:
        - Check logs for integration errors
        - See docs/MEMORY_STATUS.md for more info
    """
    try:
        db_path = bot.config.get('memory', {}).get('vector_db_path', 'D:/trading_data/memory/vector_db')
        
        memory_assistant = MemoryAssistant(db_path=db_path)
        
        if memory_assistant.collection is None:
            logger.error("[MEMORY_BRIDGE] Failed to create MemoryAssistant. Collection is not available.")
            return False

        # Attach the memory assistant and this bridge to the bot instance
        bot.memory_assistant = memory_assistant
        bot.memory_bridge = sys.modules[__name__] # Allows calling other functions from this module
        
        logger.info("[MEMORY_BRIDGE] MemoryAssistant successfully integrated with the bot.")
        return True

    except (KeyError, ValueError, AttributeError) as e:
        logger.critical(f"[MEMORY_BRIDGE] A critical error occurred during memory integration (key/value/attribute): {e}", exc_info=True)
        bot.memory_assistant = None
        bot.memory_bridge = None
        return False
    except Exception as e:
        # Catch-all for unexpected/async/third-party errors
        logger.critical(f"[MEMORY_BRIDGE] A critical error occurred during memory integration (unexpected): {e}", exc_info=True)
        bot.memory_assistant = None
        bot.memory_bridge = None
        return False

__all__ = ["setup_memory_integration"]
