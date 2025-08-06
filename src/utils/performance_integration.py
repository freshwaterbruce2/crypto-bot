"""
Performance Integration System - Unified Optimization Layer
==========================================================

Unified performance optimization system that integrates all performance enhancements
including memory optimization, database connection pooling, priority message queues,
and async pattern optimizations.

This module provides a single point of integration for all performance optimizations
in the crypto trading bot system.
"""

import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from .batch_processor import TradingMessageProcessor
from .bounded_cache import TradingDataCache, get_trading_cache
from .connection_pool import WebSocketConnectionPool, get_connection_pool, start_connection_pool

# Import all optimization modules
from .optimized_calculations import BatchCalculator
from .structured_logging import get_logger, timed_operation
from .vectorized_math import HAS_NUMPY, portfolio_analyzer

logger = get_logger(__name__)


class PerformanceManager:
    """Central manager for all performance optimizations"""

    def __init__(self):
        self.connection_pool: Optional[WebSocketConnectionPool] = None
        self.trading_cache: Optional[TradingDataCache] = None
        self.message_processor: Optional[TradingMessageProcessor] = None
        self.is_initialized = False

        # Performance metrics
        self.metrics = {
            'initialization_time': 0.0,
            'operations_optimized': 0,
            'memory_saved_mb': 0.0,
            'throughput_improvement': 0.0
        }

        logger.info("[PERF] Performance manager created")

    async def initialize(self,
                        exchange_manager=None,
                        balance_manager=None,
                        enable_connection_pool: bool = True,
                        enable_message_batching: bool = True,
                        enable_caching: bool = True) -> None:
        """Initialize all performance optimizations"""

        start_time = time.time()
        logger.info("[PERF] Initializing performance optimizations...")

        try:
            # Initialize connection pool
            if enable_connection_pool:
                self.connection_pool = get_connection_pool()
                await start_connection_pool()
                logger.info("[PERF] Connection pool initialized")

            # Initialize trading cache
            if enable_caching:
                self.trading_cache = get_trading_cache()
                logger.info("[PERF] Trading cache initialized")

            # Initialize message processor
            if enable_message_batching and exchange_manager:
                self.message_processor = TradingMessageProcessor(
                    exchange_manager, balance_manager
                )
                await self.message_processor.start()
                logger.info("[PERF] Message processor initialized")

            self.is_initialized = True
            initialization_time = time.time() - start_time
            self.metrics['initialization_time'] = initialization_time

            logger.info(f"[PERF] Performance optimizations initialized in {initialization_time:.3f}s")

            # Log available optimizations
            self._log_available_optimizations()

        except Exception as e:
            logger.error(f"[PERF] Failed to initialize performance optimizations: {e}")
            raise

    def _log_available_optimizations(self):
        """Log available performance optimizations"""
        optimizations = []

        if self.connection_pool:
            optimizations.append("WebSocket Connection Pooling")

        if self.trading_cache:
            optimizations.append("Bounded Memory Caching")

        if self.message_processor:
            optimizations.append("Batch Message Processing")

        if HAS_NUMPY:
            optimizations.append("Vectorized Calculations (NumPy)")

        optimizations.extend([
            "Optimized Decimal Operations",
            "Structured Logging"
        ])

        logger.info(f"[PERF] Available optimizations: {', '.join(optimizations)}")

    @timed_operation("portfolio_analysis")
    async def analyze_portfolio_performance(self, positions: List[Dict[str, Any]],
                                          price_history: Dict[str, List[float]] = None) -> Dict[str, Any]:
        """High-performance portfolio analysis"""

        if not positions:
            return {}

        # Use vectorized analysis if available
        if HAS_NUMPY:
            result = portfolio_analyzer.analyze_portfolio_performance(positions, price_history or {})
            self.metrics['operations_optimized'] += 1
            return result

        # Fallback to basic analysis
        return self._basic_portfolio_analysis(positions)

    def _basic_portfolio_analysis(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback portfolio analysis without NumPy"""
        total_value = sum(pos.get('value', 0) for pos in positions)
        total_invested = sum(pos.get('entry_value', 0) for pos in positions)
        unrealized_pnl = total_value - total_invested

        return {
            'total_value': total_value,
            'total_invested': total_invested,
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pnl_pct': (unrealized_pnl / total_invested * 100) if total_invested > 0 else 0,
            'position_count': len(positions),
            'used_numpy': False
        }

    @timed_operation("batch_calculation")
    def calculate_multiple_profits(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate profits for multiple trades efficiently"""

        # Use batch calculator for performance
        results = BatchCalculator.batch_profit_calculations(trades)
        self.metrics['operations_optimized'] += len(trades)

        return results

    @timed_operation("position_sizing_batch")
    def calculate_position_sizes_batch(self,
                                     balances: List[float],
                                     risk_percentages: List[float],
                                     prices: List[float]) -> List[float]:
        """Calculate position sizes for multiple assets"""

        if HAS_NUMPY:
            from .vectorized_math import risk_calculator
            sizes = risk_calculator.calculate_position_sizes_batch(
                balances, risk_percentages, prices
            )
            self.metrics['operations_optimized'] += len(balances)
            return sizes

        # Fallback calculation
        results = []
        for balance, risk_pct, price in zip(balances, risk_percentages, prices):
            position_value = balance * (risk_pct / 100.0)
            size = position_value / price if price > 0 else 0
            results.append(size)

        return results

    def get_cached_price(self, symbol: str) -> Optional[float]:
        """Get cached price with fallback"""
        if self.trading_cache:
            return self.trading_cache.get_price(symbol)
        return None

    def cache_price(self, symbol: str, price: float) -> bool:
        """Cache price data"""
        if self.trading_cache:
            self.trading_cache.cache_price(symbol, price)
            return True
        return False

    async def process_websocket_message(self, message: Dict[str, Any]) -> bool:
        """Process WebSocket message through batch processor"""
        if self.message_processor:
            self.message_processor.process_message(message)
            return True
        return False

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        stats = {
            'manager_metrics': self.metrics,
            'initialization_complete': self.is_initialized,
            'optimizations_active': []
        }

        if self.connection_pool:
            stats['connection_pool'] = self.connection_pool.get_stats()
            stats['optimizations_active'].append('connection_pooling')

        if self.trading_cache:
            stats['trading_cache'] = self.trading_cache.get_all_stats()
            stats['optimizations_active'].append('bounded_caching')

        if self.message_processor:
            stats['message_processor'] = self.message_processor.get_all_stats()
            stats['optimizations_active'].append('batch_processing')

        if HAS_NUMPY:
            stats['numpy_available'] = True
            stats['optimizations_active'].append('vectorized_math')

        return stats

    async def cleanup(self):
        """Cleanup all performance optimizations"""
        logger.info("[PERF] Cleaning up performance optimizations...")

        try:
            if self.message_processor:
                await self.message_processor.stop()

            if self.connection_pool:
                await self.connection_pool.close_all()

            if self.trading_cache:
                self.trading_cache.close_all()

            logger.info("[PERF] Performance optimizations cleanup complete")

        except Exception as e:
            logger.error(f"[PERF] Error during cleanup: {e}")


# Global performance manager instance
_global_performance_manager: Optional[PerformanceManager] = None

def get_performance_manager() -> PerformanceManager:
    """Get or create the global performance manager"""
    global _global_performance_manager
    if _global_performance_manager is None:
        _global_performance_manager = PerformanceManager()
    return _global_performance_manager


@asynccontextmanager
async def performance_context(exchange_manager=None,
                            balance_manager=None,
                            **init_kwargs):
    """Context manager for performance-optimized operations"""
    manager = get_performance_manager()

    try:
        if not manager.is_initialized:
            await manager.initialize(
                exchange_manager=exchange_manager,
                balance_manager=balance_manager,
                **init_kwargs
            )

        yield manager

    finally:
        # Cleanup is handled when the application shuts down
        pass


# High-level performance functions
async def optimized_portfolio_analysis(positions: List[Dict[str, Any]],
                                     price_history: Dict[str, List[float]] = None) -> Dict[str, Any]:
    """High-level function for optimized portfolio analysis"""
    manager = get_performance_manager()
    return await manager.analyze_portfolio_performance(positions, price_history)


def optimized_profit_calculations(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level function for optimized profit calculations"""
    manager = get_performance_manager()
    return manager.calculate_multiple_profits(trades)


def optimized_position_sizing(balances: List[float],
                            risk_percentages: List[float],
                            prices: List[float]) -> List[float]:
    """High-level function for optimized position sizing"""
    manager = get_performance_manager()
    return manager.calculate_position_sizes_batch(balances, risk_percentages, prices)


async def initialize_performance_optimizations(exchange_manager=None,
                                             balance_manager=None,
                                             **kwargs) -> PerformanceManager:
    """Initialize all performance optimizations"""
    manager = get_performance_manager()
    await manager.initialize(
        exchange_manager=exchange_manager,
        balance_manager=balance_manager,
        **kwargs
    )
    return manager


async def cleanup_performance_optimizations():
    """Cleanup all performance optimizations"""
    global _global_performance_manager
    if _global_performance_manager:
        await _global_performance_manager.cleanup()
        _global_performance_manager = None


# Export main components
__all__ = [
    'PerformanceManager',
    'get_performance_manager',
    'performance_context',
    'optimized_portfolio_analysis',
    'optimized_profit_calculations',
    'optimized_position_sizing',
    'initialize_performance_optimizations',
    'cleanup_performance_optimizations'
]
