"""
Paper Trading Integration
Integrates paper trading with the main bot
"""

import logging
from typing import Optional

from .paper_balance_manager import PaperBalanceManager
from .paper_config import get_paper_config, is_paper_trading_enabled
from .paper_executor import PaperTradeExecutor
from .paper_performance_tracker import PaperPerformanceTracker

logger = logging.getLogger(__name__)

class PaperTradingIntegration:
    """Manages paper trading integration with the main bot"""

    def __init__(self):
        self.config = get_paper_config()
        self.paper_executor: Optional[PaperTradeExecutor] = None
        self.performance_tracker: Optional[PaperPerformanceTracker] = None
        self.enabled = is_paper_trading_enabled()

        if self.enabled:
            self.performance_tracker = PaperPerformanceTracker()
            logger.info("🧪 Paper Trading Integration initialized")

    def wrap_executor(self, real_executor, exchange=None):
        """Wrap the real executor with paper trading if enabled"""
        if not self.enabled:
            return real_executor

        self.paper_executor = PaperTradeExecutor(real_executor, exchange)
        logger.info("🧪 Trade executor wrapped with paper trading")
        return self.paper_executor

    def wrap_balance_manager(self, real_balance_manager):
        """Wrap the balance manager with paper trading if enabled"""
        if not self.enabled:
            return real_balance_manager

        # For paper trading, we use our own balance manager
        # but we can still query the real one for market data
        if hasattr(self.paper_executor, 'paper_balance_manager'):
            return self.paper_executor.paper_balance_manager

        return PaperBalanceManager()

    def get_performance_report(self) -> dict:
        """Get current performance report"""
        if not self.enabled or not self.paper_executor:
            return {'error': 'Paper trading not enabled or executor not initialized'}

        return self.performance_tracker.generate_report(self.paper_executor)

    def print_performance(self):
        """Print performance summary"""
        if not self.enabled or not self.paper_executor:
            logger.warning("Paper trading not enabled")
            return

        performance = self.paper_executor.get_performance_summary()
        self.performance_tracker.print_summary(performance)


# Global integration instance
_integration = PaperTradingIntegration()

def get_paper_integration():
    """Get the global paper trading integration"""
    return _integration

def enable_paper_trading():
    """Enable paper trading for this session"""
    global _integration
    _integration.enabled = True
    _integration.config.enabled = True
    logger.info("🧪 Paper trading enabled for this session")

def disable_paper_trading():
    """Disable paper trading for this session"""
    global _integration
    _integration.enabled = False
    logger.info("🧪 Paper trading disabled for this session")
