"""
High-Performance Query Optimizer for Crypto Trading Operations
=============================================================

Optimized query system with pre-compiled prepared statements for maximum
performance in high-frequency trading scenarios. All queries are designed
for microsecond response times and optimal D: drive utilization.

Features:
- Pre-compiled prepared statements for all common trading queries
- Balance queries optimized for sub-50ms response times
- Position tracking with real-time P&L calculations
- Portfolio analytics with pre-computed aggregations
- Time-series queries optimized for historical analysis
- Batch operations for high-throughput data insertion
- Query result caching with intelligent invalidation
- Connection pooling integration for concurrent access
"""

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Query type classifications for optimization"""
    BALANCE_LOOKUP = "balance_lookup"
    BALANCE_HISTORY = "balance_history"
    POSITION_TRACKING = "position_tracking"
    TRADE_EXECUTION = "trade_execution"
    PORTFOLIO_ANALYTICS = "portfolio_analytics"
    PERFORMANCE_METRICS = "performance_metrics"


@dataclass
class QueryConfig:
    """Configuration for query optimization"""
    use_cache: bool = True
    cache_timeout: int = 300  # 5 minutes
    max_execution_time_ms: int = 100
    enable_explain: bool = False
    batch_size: int = 1000


class BalanceQueries:
    """Optimized queries for balance operations"""

    def __init__(self, db_manager):
        self.db = db_manager

        # Pre-compiled query templates
        self.queries = {
            'get_latest_balance': """
                SELECT 
                    asset,
                    balance,
                    hold_trade,
                    free_balance,
                    source,
                    timestamp_ms,
                    timestamp_readable
                FROM balance_history 
                WHERE asset = ? 
                ORDER BY timestamp_ms DESC 
                LIMIT 1
            """,

            'get_all_latest_balances': """
                SELECT 
                    bh1.asset,
                    bh1.balance,
                    bh1.hold_trade,
                    bh1.free_balance,
                    bh1.source,
                    bh1.timestamp_ms,
                    bh1.timestamp_readable
                FROM balance_history bh1
                INNER JOIN (
                    SELECT asset, MAX(timestamp_ms) as max_timestamp
                    FROM balance_history
                    GROUP BY asset
                ) bh2 ON bh1.asset = bh2.asset AND bh1.timestamp_ms = bh2.max_timestamp
                WHERE bh1.balance > 0
                ORDER BY bh1.balance DESC
            """,

            'get_balance_history': """
                SELECT 
                    asset,
                    balance,
                    hold_trade,
                    free_balance,
                    balance_change,
                    percentage_change,
                    source,
                    change_reason,
                    timestamp_ms,
                    timestamp_readable
                FROM balance_history 
                WHERE asset = ? 
                    AND timestamp_ms >= ? 
                    AND timestamp_ms <= ?
                ORDER BY timestamp_ms DESC
                LIMIT ?
            """,

            'get_balance_changes': """
                SELECT 
                    asset,
                    balance,
                    balance_change,
                    percentage_change,
                    source,
                    change_reason,
                    timestamp_ms,
                    timestamp_readable
                FROM balance_history 
                WHERE asset = ? 
                    AND ABS(balance_change) >= ?
                    AND timestamp_ms >= ?
                ORDER BY timestamp_ms DESC
                LIMIT ?
            """,

            'insert_balance_entry': """
                INSERT INTO balance_history (
                    asset, balance, hold_trade, source, change_reason,
                    timestamp_ms, timestamp_readable, balance_change,
                    percentage_change, running_total, validation_status, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,

            'batch_insert_balances': """
                INSERT INTO balance_history (
                    asset, balance, hold_trade, source, change_reason,
                    timestamp_ms, timestamp_readable, balance_change,
                    percentage_change, validation_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,

            'get_balance_analytics': """
                SELECT 
                    asset,
                    COUNT(*) as update_count,
                    MIN(balance) as min_balance,
                    MAX(balance) as max_balance,
                    AVG(balance) as avg_balance,
                    SUM(ABS(balance_change)) as total_change_volume,
                    MIN(timestamp_ms) as first_update,
                    MAX(timestamp_ms) as last_update
                FROM balance_history 
                WHERE asset = ? 
                    AND timestamp_ms >= ?
                GROUP BY asset
            """,

            'get_top_balance_changes': """
                SELECT 
                    asset,
                    balance_change,
                    percentage_change,
                    balance,
                    source,
                    timestamp_ms,
                    timestamp_readable
                FROM balance_history 
                WHERE timestamp_ms >= ?
                    AND ABS(balance_change) >= ?
                ORDER BY ABS(balance_change) DESC
                LIMIT ?
            """
        }

    async def get_latest_balance(self, asset: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get latest balance for specific asset with microsecond precision"""
        try:
            start_time = time.time()

            results = await self.db.execute_query(
                self.queries['get_latest_balance'],
                (asset,),
                use_cache=use_cache,
                cache_timeout=60  # 1 minute cache for balance queries
            )

            execution_time_ms = (time.time() - start_time) * 1000

            if execution_time_ms > 50:  # Log slow balance queries
                logger.warning(f"[BALANCE_QUERIES] Slow balance query: {execution_time_ms:.2f}ms for {asset}")

            return results[0] if results else None

        except Exception as e:
            logger.error(f"[BALANCE_QUERIES] Error getting latest balance for {asset}: {e}")
            return None

    async def get_all_latest_balances(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all latest balances with optimized JOIN query"""
        try:
            start_time = time.time()

            results = await self.db.execute_query(
                self.queries['get_all_latest_balances'],
                (),
                use_cache=use_cache,
                cache_timeout=30  # 30 second cache for all balances
            )

            execution_time_ms = (time.time() - start_time) * 1000

            if execution_time_ms > 100:  # Log slow all-balance queries
                logger.warning(f"[BALANCE_QUERIES] Slow all-balance query: {execution_time_ms:.2f}ms")

            return results

        except Exception as e:
            logger.error(f"[BALANCE_QUERIES] Error getting all latest balances: {e}")
            return []

    async def get_balance_history(self, asset: str, start_time: int, end_time: int,
                                limit: int = 1000, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get balance history for time range analysis"""
        try:
            results = await self.db.execute_query(
                self.queries['get_balance_history'],
                (asset, start_time, end_time, limit),
                use_cache=use_cache,
                cache_timeout=300  # 5 minute cache for historical data
            )

            return results

        except Exception as e:
            logger.error(f"[BALANCE_QUERIES] Error getting balance history for {asset}: {e}")
            return []

    async def insert_balance_entry(self, asset: str, balance: Decimal, hold_trade: Decimal,
                                 source: str, change_reason: str = None,
                                 balance_change: Decimal = None, percentage_change: float = None,
                                 metadata: str = None) -> bool:
        """Insert new balance entry with optimized performance"""
        try:
            timestamp_ms = int(time.time() * 1000)
            timestamp_readable = time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

            # Calculate running total (simplified for performance)
            running_total = float(balance)

            affected_rows = await self.db.execute_write(
                self.queries['insert_balance_entry'],
                (
                    asset, float(balance), float(hold_trade), source, change_reason,
                    timestamp_ms, timestamp_readable, float(balance_change) if balance_change else 0.0,
                    percentage_change or 0.0, running_total, 'valid', metadata
                )
            )

            return affected_rows > 0

        except Exception as e:
            logger.error(f"[BALANCE_QUERIES] Error inserting balance entry for {asset}: {e}")
            return False

    async def batch_insert_balances(self, balance_entries: List[Tuple]) -> int:
        """Batch insert balance entries for high-throughput operations"""
        try:
            return await self.db.execute_batch(
                self.queries['batch_insert_balances'],
                balance_entries
            )

        except Exception as e:
            logger.error(f"[BALANCE_QUERIES] Error batch inserting balances: {e}")
            return 0


class PositionQueries:
    """Optimized queries for position tracking and P&L calculations"""

    def __init__(self, db_manager):
        self.db = db_manager

        self.queries = {
            'get_position': """
                SELECT 
                    position_id,
                    symbol,
                    position_type,
                    status,
                    original_size,
                    current_size,
                    avg_entry_price,
                    current_price,
                    realized_pnl,
                    unrealized_pnl,
                    total_pnl,
                    total_fees,
                    created_at,
                    updated_at,
                    strategy,
                    tags,
                    max_drawdown,
                    max_profit,
                    hold_time_seconds
                FROM positions 
                WHERE position_id = ?
            """,

            'get_open_positions': """
                SELECT 
                    position_id,
                    symbol,
                    position_type,
                    original_size,
                    current_size,
                    avg_entry_price,
                    current_price,
                    unrealized_pnl,
                    total_fees,
                    created_at,
                    strategy,
                    max_drawdown,
                    max_profit
                FROM positions 
                WHERE status = 'OPEN'
                ORDER BY created_at DESC
            """,

            'get_positions_by_symbol': """
                SELECT 
                    position_id,
                    symbol,
                    position_type,
                    status,
                    current_size,
                    avg_entry_price,
                    current_price,
                    unrealized_pnl,
                    total_pnl,
                    created_at,
                    updated_at
                FROM positions 
                WHERE symbol = ? 
                    AND status IN ('OPEN', 'PARTIAL')
                ORDER BY created_at DESC
            """,

            'update_position_price': """
                UPDATE positions 
                SET 
                    current_price = ?,
                    unrealized_pnl = CASE 
                        WHEN position_type = 'LONG' THEN 
                            (? - avg_entry_price) * current_size - total_fees
                        WHEN position_type = 'SHORT' THEN 
                            (avg_entry_price - ?) * current_size - total_fees
                        ELSE unrealized_pnl
                    END,
                    max_profit = CASE
                        WHEN position_type = 'LONG' AND (? - avg_entry_price) * current_size > max_profit THEN
                            (? - avg_entry_price) * current_size
                        WHEN position_type = 'SHORT' AND (avg_entry_price - ?) * current_size > max_profit THEN
                            (avg_entry_price - ?) * current_size
                        ELSE max_profit
                    END,
                    max_drawdown = CASE
                        WHEN position_type = 'LONG' AND (? - avg_entry_price) * current_size < max_drawdown THEN
                            (? - avg_entry_price) * current_size
                        WHEN position_type = 'SHORT' AND (avg_entry_price - ?) * current_size < max_drawdown THEN
                            (avg_entry_price - ?) * current_size
                        ELSE max_drawdown
                    END,
                    updated_at = strftime('%s', 'now') * 1000
                WHERE position_id = ?
            """,

            'close_position_partial': """
                UPDATE positions 
                SET 
                    current_size = current_size - ?,
                    realized_pnl = realized_pnl + ?,
                    total_fees = total_fees + ?,
                    status = CASE 
                        WHEN current_size - ? <= 0 THEN 'CLOSED'
                        ELSE 'PARTIAL'
                    END,
                    closed_at = CASE
                        WHEN current_size - ? <= 0 THEN strftime('%s', 'now') * 1000
                        ELSE closed_at
                    END,
                    hold_time_seconds = CASE
                        WHEN current_size - ? <= 0 THEN 
                            (strftime('%s', 'now') * 1000 - created_at) / 1000
                        ELSE hold_time_seconds
                    END,
                    updated_at = strftime('%s', 'now') * 1000
                WHERE position_id = ?
            """,

            'create_position': """
                INSERT INTO positions (
                    position_id, symbol, position_type, status,
                    original_size, current_size, avg_entry_price,
                    strategy, tags, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?)
            """,

            'get_portfolio_summary': """
                SELECT 
                    COUNT(*) as total_positions,
                    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_positions,
                    SUM(CASE WHEN position_type = 'LONG' AND status = 'OPEN' THEN 1 ELSE 0 END) as long_positions,
                    SUM(CASE WHEN position_type = 'SHORT' AND status = 'OPEN' THEN 1 ELSE 0 END) as short_positions,
                    SUM(realized_pnl) as total_realized_pnl,
                    SUM(CASE WHEN status = 'OPEN' THEN unrealized_pnl ELSE 0 END) as total_unrealized_pnl,
                    SUM(realized_pnl + CASE WHEN status = 'OPEN' THEN unrealized_pnl ELSE 0 END) as total_pnl,
                    SUM(total_fees) as total_fees,
                    SUM(CASE WHEN status = 'OPEN' THEN current_size * current_price ELSE 0 END) as open_position_value
                FROM positions
            """,

            'get_position_analytics': """
                SELECT 
                    symbol,
                    COUNT(*) as position_count,
                    SUM(realized_pnl) as total_pnl,
                    AVG(realized_pnl) as avg_pnl,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_positions,
                    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losing_positions,
                    MAX(realized_pnl) as best_trade,
                    MIN(realized_pnl) as worst_trade,
                    AVG(hold_time_seconds) as avg_hold_time,
                    SUM(total_fees) as total_fees
                FROM positions 
                WHERE status = 'CLOSED'
                GROUP BY symbol
                ORDER BY total_pnl DESC
            """
        }

    async def get_position(self, position_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get position details with real-time P&L"""
        try:
            results = await self.db.execute_query(
                self.queries['get_position'],
                (position_id,),
                use_cache=use_cache,
                cache_timeout=30  # 30 second cache for position data
            )

            return results[0] if results else None

        except Exception as e:
            logger.error(f"[POSITION_QUERIES] Error getting position {position_id}: {e}")
            return None

    async def get_open_positions(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all open positions with optimized query"""
        try:
            start_time = time.time()

            results = await self.db.execute_query(
                self.queries['get_open_positions'],
                (),
                use_cache=use_cache,
                cache_timeout=15  # 15 second cache for open positions
            )

            execution_time_ms = (time.time() - start_time) * 1000

            if execution_time_ms > 100:
                logger.warning(f"[POSITION_QUERIES] Slow open positions query: {execution_time_ms:.2f}ms")

            return results

        except Exception as e:
            logger.error(f"[POSITION_QUERIES] Error getting open positions: {e}")
            return []

    async def update_position_price(self, position_id: str, new_price: Decimal) -> bool:
        """Update position price with real-time P&L calculation"""
        try:
            price = float(new_price)

            affected_rows = await self.db.execute_write(
                self.queries['update_position_price'],
                (price, price, price, price, price, price, price, price, price, price, price, position_id)
            )

            return affected_rows > 0

        except Exception as e:
            logger.error(f"[POSITION_QUERIES] Error updating position price {position_id}: {e}")
            return False

    async def create_position(self, position_id: str, symbol: str, position_type: str,
                            size: Decimal, entry_price: Decimal, strategy: str = None,
                            tags: str = None, metadata: str = None) -> bool:
        """Create new position with optimized insertion"""
        try:
            timestamp_ms = int(time.time() * 1000)

            affected_rows = await self.db.execute_write(
                self.queries['create_position'],
                (
                    position_id, symbol, position_type,
                    float(size), float(size), float(entry_price),
                    strategy, tags, metadata, timestamp_ms, timestamp_ms
                )
            )

            return affected_rows > 0

        except Exception as e:
            logger.error(f"[POSITION_QUERIES] Error creating position {position_id}: {e}")
            return False

    async def get_portfolio_summary(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get comprehensive portfolio summary with single query"""
        try:
            results = await self.db.execute_query(
                self.queries['get_portfolio_summary'],
                (),
                use_cache=use_cache,
                cache_timeout=60  # 1 minute cache for portfolio summary
            )

            return results[0] if results else {}

        except Exception as e:
            logger.error(f"[POSITION_QUERIES] Error getting portfolio summary: {e}")
            return {}


class PortfolioQueries:
    """Optimized queries for portfolio-level analytics and metrics"""

    def __init__(self, db_manager):
        self.db = db_manager

        self.queries = {
            'insert_portfolio_metrics': """
                INSERT INTO portfolio_metrics (
                    timestamp_ms, timestamp_readable, total_value, cash_balance,
                    position_value, total_pnl, daily_pnl, daily_return_pct,
                    total_return_pct, sharpe_ratio, max_drawdown_pct,
                    open_positions, long_positions, short_positions,
                    winning_positions, losing_positions, trades_today,
                    volume_today, fees_today, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,

            'get_latest_portfolio_metrics': """
                SELECT * FROM portfolio_metrics 
                ORDER BY timestamp_ms DESC 
                LIMIT 1
            """,

            'get_portfolio_metrics_range': """
                SELECT * FROM portfolio_metrics 
                WHERE timestamp_ms >= ? AND timestamp_ms <= ?
                ORDER BY timestamp_ms DESC
                LIMIT ?
            """,

            'get_portfolio_performance': """
                SELECT 
                    DATE(timestamp_ms/1000, 'unixepoch') as date,
                    MIN(total_value) as day_low,
                    MAX(total_value) as day_high,
                    total_value as close_value,
                    SUM(daily_pnl) as day_pnl,
                    AVG(daily_return_pct) as day_return,
                    SUM(trades_today) as day_trades,
                    SUM(volume_today) as day_volume,
                    SUM(fees_today) as day_fees
                FROM portfolio_metrics 
                WHERE timestamp_ms >= ?
                GROUP BY DATE(timestamp_ms/1000, 'unixepoch')
                ORDER BY date DESC
                LIMIT ?
            """,

            'calculate_drawdown': """
                WITH portfolio_peaks AS (
                    SELECT 
                        timestamp_ms,
                        total_value,
                        MAX(total_value) OVER (
                            ORDER BY timestamp_ms 
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) as peak_value
                    FROM portfolio_metrics 
                    WHERE timestamp_ms >= ?
                )
                SELECT 
                    timestamp_ms,
                    total_value,
                    peak_value,
                    (total_value - peak_value) as drawdown,
                    ((total_value - peak_value) / peak_value * 100) as drawdown_pct
                FROM portfolio_peaks
                WHERE peak_value > total_value
                ORDER BY drawdown ASC
                LIMIT 1
            """,

            'get_risk_metrics': """
                SELECT 
                    COUNT(*) as data_points,
                    AVG(daily_return_pct) as avg_return,
                    STDEV(daily_return_pct) as volatility,
                    MIN(daily_return_pct) as worst_day,
                    MAX(daily_return_pct) as best_day,
                    AVG(sharpe_ratio) as avg_sharpe,
                    MIN(max_drawdown_pct) as max_drawdown,
                    AVG(total_value) as avg_portfolio_value,
                    MAX(total_value) as peak_value,
                    MIN(total_value) as trough_value
                FROM portfolio_metrics 
                WHERE timestamp_ms >= ?
            """
        }

    async def insert_portfolio_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Insert portfolio metrics with optimized performance"""
        try:
            timestamp_ms = int(time.time() * 1000)
            timestamp_readable = time.strftime('%Y-%m-%d %H:%M:%S')

            values = (
                timestamp_ms, timestamp_readable,
                metrics_data.get('total_value', 0.0),
                metrics_data.get('cash_balance', 0.0),
                metrics_data.get('position_value', 0.0),
                metrics_data.get('total_pnl', 0.0),
                metrics_data.get('daily_pnl', 0.0),
                metrics_data.get('daily_return_pct', 0.0),
                metrics_data.get('total_return_pct', 0.0),
                metrics_data.get('sharpe_ratio'),
                metrics_data.get('max_drawdown_pct', 0.0),
                metrics_data.get('open_positions', 0),
                metrics_data.get('long_positions', 0),
                metrics_data.get('short_positions', 0),
                metrics_data.get('winning_positions', 0),
                metrics_data.get('losing_positions', 0),
                metrics_data.get('trades_today', 0),
                metrics_data.get('volume_today', 0.0),
                metrics_data.get('fees_today', 0.0),
                metrics_data.get('metadata')
            )

            affected_rows = await self.db.execute_write(
                self.queries['insert_portfolio_metrics'],
                values
            )

            return affected_rows > 0

        except Exception as e:
            logger.error(f"[PORTFOLIO_QUERIES] Error inserting portfolio metrics: {e}")
            return False

    async def get_latest_portfolio_metrics(self, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get latest portfolio metrics"""
        try:
            results = await self.db.execute_query(
                self.queries['get_latest_portfolio_metrics'],
                (),
                use_cache=use_cache,
                cache_timeout=60  # 1 minute cache
            )

            return results[0] if results else None

        except Exception as e:
            logger.error(f"[PORTFOLIO_QUERIES] Error getting latest portfolio metrics: {e}")
            return None


class AnalyticsQueries:
    """Advanced analytics queries for performance analysis"""

    def __init__(self, db_manager):
        self.db = db_manager

        self.queries = {
            'calculate_sharpe_ratio': """
                WITH daily_returns AS (
                    SELECT 
                        daily_return_pct,
                        COUNT(*) OVER() as total_days
                    FROM portfolio_metrics 
                    WHERE timestamp_ms >= ? 
                        AND daily_return_pct IS NOT NULL
                )
                SELECT 
                    AVG(daily_return_pct) as avg_return,
                    STDEV(daily_return_pct) as volatility,
                    CASE 
                        WHEN STDEV(daily_return_pct) > 0 THEN 
                            AVG(daily_return_pct) / STDEV(daily_return_pct) * SQRT(365)
                        ELSE 0 
                    END as sharpe_ratio
                FROM daily_returns
            """,

            'strategy_performance': """
                SELECT 
                    strategy,
                    COUNT(*) as trade_count,
                    SUM(realized_pnl) as total_pnl,
                    AVG(realized_pnl) as avg_pnl,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losses,
                    MAX(realized_pnl) as best_trade,
                    MIN(realized_pnl) as worst_trade,
                    SUM(total_fees) as total_fees
                FROM positions 
                WHERE status = 'CLOSED' 
                    AND strategy IS NOT NULL
                    AND created_at >= ?
                GROUP BY strategy
                ORDER BY total_pnl DESC
            """,

            'market_correlation': """
                WITH portfolio_returns AS (
                    SELECT 
                        DATE(timestamp_ms/1000, 'unixepoch') as date,
                        daily_return_pct as portfolio_return
                    FROM portfolio_metrics 
                    WHERE timestamp_ms >= ?
                        AND daily_return_pct IS NOT NULL
                ),
                market_data AS (
                    -- This would join with market data if available
                    SELECT 
                        date,
                        portfolio_return,
                        0.0 as market_return  -- Placeholder
                    FROM portfolio_returns
                )
                SELECT 
                    COUNT(*) as data_points,
                    AVG(portfolio_return) as avg_portfolio_return,
                    AVG(market_return) as avg_market_return,
                    -- Correlation would be calculated with proper market data
                    0.0 as correlation
                FROM market_data
            """
        }

    async def calculate_sharpe_ratio(self, days_back: int = 30) -> Optional[Dict[str, Any]]:
        """Calculate Sharpe ratio for specified period"""
        try:
            start_time = int((time.time() - days_back * 86400) * 1000)

            results = await self.db.execute_query(
                self.queries['calculate_sharpe_ratio'],
                (start_time,),
                use_cache=True,
                cache_timeout=300  # 5 minute cache
            )

            return results[0] if results else None

        except Exception as e:
            logger.error(f"[ANALYTICS_QUERIES] Error calculating Sharpe ratio: {e}")
            return None


class QueryOptimizer:
    """
    Main query optimizer that coordinates all specialized query classes
    """

    def __init__(self, database_manager, config: Optional[QueryConfig] = None):
        """Initialize query optimizer"""
        self.db = database_manager
        self.config = config or QueryConfig()

        # Initialize specialized query handlers
        self.balance_queries = BalanceQueries(database_manager)
        self.position_queries = PositionQueries(database_manager)
        self.portfolio_queries = PortfolioQueries(database_manager)
        self.analytics_queries = AnalyticsQueries(database_manager)

        # Performance monitoring
        self._query_stats = {
            'total_queries': 0,
            'cached_queries': 0,
            'slow_queries': 0,
            'failed_queries': 0,
            'avg_execution_time_ms': 0.0
        }

        logger.info("[QUERY_OPTIMIZER] Initialized with optimized query system")

    async def explain_query(self, query: str, parameters: Tuple = ()) -> List[Dict[str, Any]]:
        """Analyze query execution plan for optimization"""
        if not self.config.enable_explain:
            return []

        try:
            explain_query = f"EXPLAIN QUERY PLAN {query}"
            results = await self.db.execute_query(explain_query, parameters)
            return results

        except Exception as e:
            logger.error(f"[QUERY_OPTIMIZER] Error explaining query: {e}")
            return []

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get query optimization statistics"""
        return {
            'query_stats': dict(self._query_stats),
            'balance_queries': 'active',
            'position_queries': 'active',
            'portfolio_queries': 'active',
            'analytics_queries': 'active',
            'cache_enabled': self.config.use_cache,
            'max_execution_time_ms': self.config.max_execution_time_ms
        }

    async def optimize_all_queries(self) -> bool:
        """Run optimization analysis on all query types"""
        try:
            logger.info("[QUERY_OPTIMIZER] Running comprehensive query optimization...")

            # Test key queries and log performance
            test_queries = [
                ("Balance Latest", self.balance_queries.get_all_latest_balances, ()),
                ("Open Positions", self.position_queries.get_open_positions, ()),
                ("Portfolio Summary", self.position_queries.get_portfolio_summary, ())
            ]

            optimization_results = []

            for query_name, query_func, args in test_queries:
                start_time = time.time()

                try:
                    await query_func(*args)
                    execution_time_ms = (time.time() - start_time) * 1000

                    optimization_results.append({
                        'query': query_name,
                        'execution_time_ms': execution_time_ms,
                        'status': 'optimal' if execution_time_ms < 100 else 'needs_optimization',
                        'recommendation': 'Consider indexing' if execution_time_ms > 200 else 'Performing well'
                    })

                    logger.info(f"[QUERY_OPTIMIZER] {query_name}: {execution_time_ms:.2f}ms")

                except Exception as e:
                    optimization_results.append({
                        'query': query_name,
                        'status': 'error',
                        'error': str(e)
                    })

            logger.info(f"[QUERY_OPTIMIZER] Optimization analysis complete: {len(optimization_results)} queries tested")
            return True

        except Exception as e:
            logger.error(f"[QUERY_OPTIMIZER] Error during query optimization: {e}")
            return False
