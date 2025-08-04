"""
Optimized Database Schemas for Crypto Trading Bot
=================================================

High-performance database schemas specifically designed for cryptocurrency trading
operations. All schemas are optimized for D: drive storage with efficient indexing
strategies for balance queries, position tracking, and portfolio analytics.

Features:
- Time-series optimized balance history with microsecond timestamps
- Position tracking with real-time P&L calculation support
- Trade history with comprehensive execution details
- Portfolio metrics with pre-computed aggregations
- Performance analytics with benchmark comparisons
- Efficient indexing strategies for high-frequency queries
- Foreign key relationships for data integrity
- Partitioning support for historical data management
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class TableType(Enum):
    """Database table types for different data categories"""
    BALANCE_HISTORY = "balance_history"
    POSITION_TRACKING = "position_tracking"
    TRADE_HISTORY = "trade_history"
    PORTFOLIO_METRICS = "portfolio_metrics"
    PERFORMANCE_ANALYTICS = "performance_analytics"
    SYSTEM_METADATA = "system_metadata"


@dataclass
class IndexConfig:
    """Index configuration for optimal query performance"""
    name: str
    table: str
    columns: List[str]
    unique: bool = False
    partial_condition: Optional[str] = None
    index_type: str = "BTREE"  # BTREE, HASH (SQLite uses BTREE)
    
    def get_create_sql(self) -> str:
        """Generate CREATE INDEX SQL"""
        unique_clause = "UNIQUE " if self.unique else ""
        columns_clause = ", ".join(self.columns)
        
        sql = f"CREATE {unique_clause}INDEX IF NOT EXISTS {self.name} ON {self.table} ({columns_clause})"
        
        if self.partial_condition:
            sql += f" WHERE {self.partial_condition}"
        
        return sql


class BalanceHistorySchema:
    """Schema for balance history tracking with time-series optimization"""
    
    TABLE_NAME = "balance_history"
    
    @staticmethod
    def get_create_table_sql() -> str:
        """Get CREATE TABLE SQL for balance history"""
        return f"""
        CREATE TABLE IF NOT EXISTS {BalanceHistorySchema.TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset TEXT NOT NULL,
            balance DECIMAL(20, 8) NOT NULL DEFAULT 0.0,
            hold_trade DECIMAL(20, 8) NOT NULL DEFAULT 0.0,
            free_balance DECIMAL(20, 8) GENERATED ALWAYS AS (balance - hold_trade) STORED,
            source TEXT NOT NULL DEFAULT 'unknown',
            change_reason TEXT,
            timestamp_ms INTEGER NOT NULL,
            timestamp_readable TEXT NOT NULL,
            balance_change DECIMAL(20, 8) DEFAULT 0.0,
            percentage_change REAL DEFAULT 0.0,
            running_total DECIMAL(20, 8),
            validation_status TEXT DEFAULT 'valid',
            metadata TEXT,  -- JSON for additional data
            created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
            
            -- Constraints
            CHECK (balance >= 0),
            CHECK (hold_trade >= 0),
            CHECK (hold_trade <= balance),
            CHECK (timestamp_ms > 0)
        )
        """
    
    @staticmethod
    def get_indexes() -> List[IndexConfig]:
        """Get optimized indexes for balance history queries"""
        return [
            # Primary time-series index for recent balance queries
            IndexConfig(
                name="idx_balance_asset_timestamp",
                table=BalanceHistorySchema.TABLE_NAME,
                columns=["asset", "timestamp_ms DESC"],
                unique=False
            ),
            
            # Index for balance change tracking
            IndexConfig(
                name="idx_balance_changes",
                table=BalanceHistorySchema.TABLE_NAME,
                columns=["asset", "balance_change", "timestamp_ms DESC"],
                unique=False,
                partial_condition="balance_change != 0"
            ),
            
            # Index for source-based queries
            IndexConfig(
                name="idx_balance_source_time",
                table=BalanceHistorySchema.TABLE_NAME,
                columns=["source", "timestamp_ms DESC"],
                unique=False
            ),
            
            # Index for validation status queries
            IndexConfig(
                name="idx_balance_validation",
                table=BalanceHistorySchema.TABLE_NAME,
                columns=["validation_status", "timestamp_ms DESC"],
                unique=False,
                partial_condition="validation_status != 'valid'"
            ),
            
            # Composite index for analytics queries
            IndexConfig(
                name="idx_balance_analytics",
                table=BalanceHistorySchema.TABLE_NAME,
                columns=["asset", "source", "timestamp_ms DESC"],
                unique=False
            )
        ]
    
    @staticmethod
    def get_partitioning_sql() -> List[str]:
        """Get partitioning SQL for historical data management"""
        # SQLite doesn't support native partitioning, but we can create views
        # and separate tables for different time periods
        return [
            f"""
            CREATE VIEW IF NOT EXISTS {BalanceHistorySchema.TABLE_NAME}_recent AS
            SELECT * FROM {BalanceHistorySchema.TABLE_NAME}
            WHERE timestamp_ms >= (strftime('%s', 'now') - 86400) * 1000  -- Last 24 hours
            """,
            
            f"""
            CREATE VIEW IF NOT EXISTS {BalanceHistorySchema.TABLE_NAME}_daily AS
            SELECT 
                asset,
                DATE(timestamp_ms/1000, 'unixepoch') as date,
                MIN(balance) as min_balance,
                MAX(balance) as max_balance,
                AVG(balance) as avg_balance,
                MIN(timestamp_ms) as first_timestamp,
                MAX(timestamp_ms) as last_timestamp,
                COUNT(*) as update_count
            FROM {BalanceHistorySchema.TABLE_NAME}
            GROUP BY asset, DATE(timestamp_ms/1000, 'unixepoch')
            """
        ]


class PositionSchema:
    """Schema for position tracking with real-time P&L calculation"""
    
    TABLE_NAME = "positions"
    
    @staticmethod
    def get_create_table_sql() -> str:
        """Get CREATE TABLE SQL for positions"""
        return f"""
        CREATE TABLE IF NOT EXISTS {PositionSchema.TABLE_NAME} (
            position_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            position_type TEXT NOT NULL CHECK (position_type IN ('LONG', 'SHORT')),
            status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'PARTIAL', 'CANCELLED')),
            
            -- Size and pricing
            original_size DECIMAL(20, 8) NOT NULL,
            current_size DECIMAL(20, 8) NOT NULL,
            avg_entry_price DECIMAL(20, 8) NOT NULL,
            current_price DECIMAL(20, 8),
            
            -- P&L tracking
            realized_pnl DECIMAL(20, 8) DEFAULT 0.0,
            unrealized_pnl DECIMAL(20, 8) DEFAULT 0.0,
            total_pnl DECIMAL(20, 8) GENERATED ALWAYS AS (realized_pnl + unrealized_pnl) STORED,
            
            -- Fees and costs
            total_fees DECIMAL(20, 8) DEFAULT 0.0,
            entry_fees DECIMAL(20, 8) DEFAULT 0.0,
            exit_fees DECIMAL(20, 8) DEFAULT 0.0,
            
            -- Timestamps
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now') * 1000),
            updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now') * 1000),
            closed_at INTEGER,
            
            -- Strategy and metadata
            strategy TEXT,
            tags TEXT,  -- JSON array of tags
            metadata TEXT,  -- JSON for additional data
            
            -- Risk metrics
            max_drawdown DECIMAL(20, 8) DEFAULT 0.0,
            max_profit DECIMAL(20, 8) DEFAULT 0.0,
            hold_time_seconds INTEGER DEFAULT 0,
            
            -- Constraints
            CHECK (original_size > 0),
            CHECK (current_size >= 0),
            CHECK (current_size <= original_size),
            CHECK (avg_entry_price > 0),
            CHECK (created_at > 0)
        )
        """
    
    @staticmethod
    def get_indexes() -> List[IndexConfig]:
        """Get optimized indexes for position queries"""
        return [
            # Primary symbol-based queries
            IndexConfig(
                name="idx_positions_symbol_status",
                table=PositionSchema.TABLE_NAME,
                columns=["symbol", "status", "created_at DESC"],
                unique=False
            ),
            
            # Open positions query optimization
            IndexConfig(
                name="idx_positions_open",
                table=PositionSchema.TABLE_NAME,
                columns=["status", "symbol", "updated_at DESC"],
                unique=False,
                partial_condition="status = 'OPEN'"
            ),
            
            # P&L analysis queries
            IndexConfig(
                name="idx_positions_pnl",
                table=PositionSchema.TABLE_NAME,
                columns=["symbol", "total_pnl DESC", "created_at DESC"],
                unique=False
            ),
            
            # Strategy-based queries
            IndexConfig(
                name="idx_positions_strategy",
                table=PositionSchema.TABLE_NAME,
                columns=["strategy", "status", "created_at DESC"],
                unique=False,
                partial_condition="strategy IS NOT NULL"
            ),
            
            # Time-based queries for analytics
            IndexConfig(
                name="idx_positions_time_analysis",
                table=PositionSchema.TABLE_NAME,
                columns=["created_at DESC", "status"],
                unique=False
            ),
            
            # Risk metrics queries
            IndexConfig(
                name="idx_positions_risk",
                table=PositionSchema.TABLE_NAME,
                columns=["symbol", "max_drawdown DESC", "max_profit DESC"],
                unique=False
            )
        ]
    
    @staticmethod
    def get_triggers() -> List[str]:
        """Get triggers for automatic position updates"""
        return [
            # Update timestamp trigger
            f"""
            CREATE TRIGGER IF NOT EXISTS update_position_timestamp 
            AFTER UPDATE ON {PositionSchema.TABLE_NAME}
            FOR EACH ROW
            BEGIN
                UPDATE {PositionSchema.TABLE_NAME} 
                SET updated_at = strftime('%s', 'now') * 1000
                WHERE position_id = NEW.position_id;
            END
            """,
            
            # Auto-close position when size reaches zero
            f"""
            CREATE TRIGGER IF NOT EXISTS auto_close_position
            AFTER UPDATE OF current_size ON {PositionSchema.TABLE_NAME}
            FOR EACH ROW
            WHEN NEW.current_size = 0 AND OLD.current_size > 0
            BEGIN
                UPDATE {PositionSchema.TABLE_NAME}
                SET 
                    status = 'CLOSED',
                    closed_at = strftime('%s', 'now') * 1000,
                    hold_time_seconds = (strftime('%s', 'now') * 1000 - created_at) / 1000
                WHERE position_id = NEW.position_id;
            END
            """
        ]


class TradeHistorySchema:
    """Schema for comprehensive trade execution history"""
    
    TABLE_NAME = "trade_history"
    
    @staticmethod
    def get_create_table_sql() -> str:
        """Get CREATE TABLE SQL for trade history"""
        return f"""
        CREATE TABLE IF NOT EXISTS {TradeHistorySchema.TABLE_NAME} (
            trade_id TEXT PRIMARY KEY,
            position_id TEXT,
            order_id TEXT,
            symbol TEXT NOT NULL,
            
            -- Trade details
            trade_type TEXT NOT NULL CHECK (trade_type IN ('BUY', 'SELL')),
            order_type TEXT NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')),
            size DECIMAL(20, 8) NOT NULL,
            price DECIMAL(20, 8) NOT NULL,
            
            -- Execution details
            executed_size DECIMAL(20, 8) NOT NULL,
            executed_price DECIMAL(20, 8) NOT NULL,
            fees DECIMAL(20, 8) NOT NULL DEFAULT 0.0,
            fee_currency TEXT,
            
            -- Status and timing
            status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'REJECTED', 'PARTIAL')),
            execution_time INTEGER,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now') * 1000),
            
            -- Strategy and metadata
            strategy TEXT,
            execution_venue TEXT DEFAULT 'kraken',
            slippage DECIMAL(10, 6),
            market_impact DECIMAL(10, 6),
            
            -- P&L for this specific trade
            trade_pnl DECIMAL(20, 8),
            cumulative_pnl DECIMAL(20, 8),
            
            -- Market data at execution
            bid_price DECIMAL(20, 8),
            ask_price DECIMAL(20, 8),
            spread DECIMAL(20, 8),
            volume_24h DECIMAL(20, 8),
            
            -- Additional metadata
            metadata TEXT,  -- JSON for additional data
            error_message TEXT,
            
            -- Foreign key relationship
            FOREIGN KEY (position_id) REFERENCES {PositionSchema.TABLE_NAME}(position_id),
            
            -- Constraints
            CHECK (size > 0),
            CHECK (price > 0),
            CHECK (executed_size >= 0),
            CHECK (executed_size <= size),
            CHECK (fees >= 0),
            CHECK (created_at > 0)
        )
        """
    
    @staticmethod
    def get_indexes() -> List[IndexConfig]:
        """Get optimized indexes for trade history queries"""
        return [
            # Primary symbol-based queries
            IndexConfig(
                name="idx_trades_symbol_time",
                table=TradeHistorySchema.TABLE_NAME,
                columns=["symbol", "execution_time DESC"],
                unique=False
            ),
            
            # Position-based queries
            IndexConfig(
                name="idx_trades_position",
                table=TradeHistorySchema.TABLE_NAME,
                columns=["position_id", "execution_time DESC"],
                unique=False,
                partial_condition="position_id IS NOT NULL"
            ),
            
            # Status-based queries
            IndexConfig(
                name="idx_trades_status_time",
                table=TradeHistorySchema.TABLE_NAME,
                columns=["status", "created_at DESC"],
                unique=False
            ),
            
            # Strategy analysis queries
            IndexConfig(
                name="idx_trades_strategy_pnl",
                table=TradeHistorySchema.TABLE_NAME,
                columns=["strategy", "trade_pnl DESC", "execution_time DESC"],
                unique=False,
                partial_condition="strategy IS NOT NULL"
            ),
            
            # P&L analysis queries
            IndexConfig(
                name="idx_trades_pnl_analysis",
                table=TradeHistorySchema.TABLE_NAME,
                columns=["symbol", "trade_pnl DESC", "execution_time DESC"],
                unique=False,
                partial_condition="trade_pnl IS NOT NULL"
            ),
            
            # Fee analysis queries
            IndexConfig(
                name="idx_trades_fees",
                table=TradeHistorySchema.TABLE_NAME,
                columns=["symbol", "fees DESC", "execution_time DESC"],
                unique=False
            )
        ]


class PortfolioMetricsSchema:
    """Schema for portfolio-level metrics and analytics"""
    
    TABLE_NAME = "portfolio_metrics"
    
    @staticmethod
    def get_create_table_sql() -> str:
        """Get CREATE TABLE SQL for portfolio metrics"""
        return f"""
        CREATE TABLE IF NOT EXISTS {PortfolioMetricsSchema.TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_ms INTEGER NOT NULL,
            timestamp_readable TEXT NOT NULL,
            
            -- Portfolio value metrics
            total_value DECIMAL(20, 8) NOT NULL,
            cash_balance DECIMAL(20, 8) NOT NULL DEFAULT 0.0,
            position_value DECIMAL(20, 8) NOT NULL DEFAULT 0.0,
            total_pnl DECIMAL(20, 8) NOT NULL DEFAULT 0.0,
            
            -- Performance metrics
            daily_pnl DECIMAL(20, 8) DEFAULT 0.0,
            daily_return_pct DECIMAL(10, 6) DEFAULT 0.0,
            total_return_pct DECIMAL(10, 6) DEFAULT 0.0,
            sharpe_ratio DECIMAL(10, 6),
            max_drawdown_pct DECIMAL(10, 6) DEFAULT 0.0,
            
            -- Risk metrics
            portfolio_beta DECIMAL(10, 6),
            value_at_risk DECIMAL(20, 8),
            expected_shortfall DECIMAL(20, 8),
            volatility DECIMAL(10, 6),
            
            -- Position metrics
            open_positions INTEGER DEFAULT 0,
            long_positions INTEGER DEFAULT 0,
            short_positions INTEGER DEFAULT 0,
            winning_positions INTEGER DEFAULT 0,
            losing_positions INTEGER DEFAULT 0,
            
            -- Asset allocation (top 5 positions)
            allocation_1_symbol TEXT,
            allocation_1_weight DECIMAL(10, 6),
            allocation_2_symbol TEXT,
            allocation_2_weight DECIMAL(10, 6),
            allocation_3_symbol TEXT,
            allocation_3_weight DECIMAL(10, 6),
            allocation_4_symbol TEXT,
            allocation_4_weight DECIMAL(10, 6),
            allocation_5_symbol TEXT,
            allocation_5_weight DECIMAL(10, 6),
            
            -- Trading activity
            trades_today INTEGER DEFAULT 0,
            volume_today DECIMAL(20, 8) DEFAULT 0.0,
            fees_today DECIMAL(20, 8) DEFAULT 0.0,
            
            -- Additional metadata
            market_regime TEXT,  -- bull, bear, sideways
            strategy_distribution TEXT,  -- JSON
            metadata TEXT,  -- JSON for additional metrics
            
            -- Constraints
            CHECK (total_value >= 0),
            CHECK (timestamp_ms > 0),
            CHECK (open_positions >= 0),
            CHECK (long_positions >= 0),
            CHECK (short_positions >= 0)
        )
        """
    
    @staticmethod
    def get_indexes() -> List[IndexConfig]:
        """Get optimized indexes for portfolio metrics queries"""
        return [
            # Time-series analysis
            IndexConfig(
                name="idx_portfolio_time_series",
                table=PortfolioMetricsSchema.TABLE_NAME,
                columns=["timestamp_ms DESC"],
                unique=False
            ),
            
            # Performance analysis
            IndexConfig(
                name="idx_portfolio_performance",
                table=PortfolioMetricsSchema.TABLE_NAME,
                columns=["daily_return_pct DESC", "timestamp_ms DESC"],
                unique=False
            ),
            
            # Risk analysis
            IndexConfig(
                name="idx_portfolio_risk",
                table=PortfolioMetricsSchema.TABLE_NAME,
                columns=["max_drawdown_pct DESC", "volatility DESC", "timestamp_ms DESC"],
                unique=False
            ),
            
            # Trading activity analysis
            IndexConfig(
                name="idx_portfolio_activity",
                table=PortfolioMetricsSchema.TABLE_NAME,
                columns=["trades_today DESC", "volume_today DESC", "timestamp_ms DESC"],
                unique=False
            )
        ]


class PerformanceSchema:
    """Schema for detailed performance analytics and benchmarking"""
    
    TABLE_NAME = "performance_analytics"
    
    @staticmethod
    def get_create_table_sql() -> str:
        """Get CREATE TABLE SQL for performance analytics"""
        return f"""
        CREATE TABLE IF NOT EXISTS {PerformanceSchema.TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_type TEXT NOT NULL CHECK (period_type IN ('HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY')),
            period_start INTEGER NOT NULL,
            period_end INTEGER NOT NULL,
            
            -- Basic performance metrics
            start_value DECIMAL(20, 8) NOT NULL,
            end_value DECIMAL(20, 8) NOT NULL,
            total_return DECIMAL(20, 8) NOT NULL,
            total_return_pct DECIMAL(10, 6) NOT NULL,
            
            -- Risk-adjusted returns
            sharpe_ratio DECIMAL(10, 6),
            sortino_ratio DECIMAL(10, 6),
            calmar_ratio DECIMAL(10, 6),
            information_ratio DECIMAL(10, 6),
            
            -- Drawdown analysis
            max_drawdown DECIMAL(20, 8),
            max_drawdown_pct DECIMAL(10, 6),
            max_drawdown_duration INTEGER,
            current_drawdown DECIMAL(20, 8),
            
            -- Volatility metrics
            volatility DECIMAL(10, 6),
            downside_volatility DECIMAL(10, 6),
            upside_volatility DECIMAL(10, 6),
            
            -- Trading statistics
            total_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            win_rate DECIMAL(10, 6),
            avg_win DECIMAL(20, 8),
            avg_loss DECIMAL(20, 8),
            profit_factor DECIMAL(10, 6),
            
            -- Benchmark comparison
            benchmark_return DECIMAL(20, 8),
            benchmark_return_pct DECIMAL(10, 6),
            alpha DECIMAL(10, 6),
            beta DECIMAL(10, 6),
            tracking_error DECIMAL(10, 6),
            
            -- Additional metrics
            total_fees DECIMAL(20, 8) DEFAULT 0.0,
            total_volume DECIMAL(20, 8) DEFAULT 0.0,
            avg_position_size DECIMAL(20, 8),
            max_position_size DECIMAL(20, 8),
            
            -- Market correlation
            market_correlation DECIMAL(10, 6),
            market_beta DECIMAL(10, 6),
            
            -- Strategy breakdown (top 3 strategies)
            strategy_1_name TEXT,
            strategy_1_return DECIMAL(20, 8),
            strategy_2_name TEXT,
            strategy_2_return DECIMAL(20, 8),
            strategy_3_name TEXT,
            strategy_3_return DECIMAL(20, 8),
            
            -- Metadata
            metadata TEXT,  -- JSON for additional analytics
            created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
            
            -- Constraints
            CHECK (period_start < period_end),
            CHECK (start_value > 0),
            CHECK (end_value > 0),
            CHECK (total_trades >= 0),
            CHECK (winning_trades >= 0),
            CHECK (losing_trades >= 0),
            CHECK (winning_trades + losing_trades <= total_trades)
        )
        """
    
    @staticmethod
    def get_indexes() -> List[IndexConfig]:
        """Get optimized indexes for performance analytics queries"""
        return [
            # Period-based queries
            IndexConfig(
                name="idx_perf_period_type",
                table=PerformanceSchema.TABLE_NAME,
                columns=["period_type", "period_end DESC"],
                unique=False
            ),
            
            # Performance ranking queries
            IndexConfig(
                name="idx_perf_returns",
                table=PerformanceSchema.TABLE_NAME,
                columns=["total_return_pct DESC", "period_end DESC"],
                unique=False
            ),
            
            # Risk-adjusted performance
            IndexConfig(
                name="idx_perf_risk_adjusted",
                table=PerformanceSchema.TABLE_NAME,
                columns=["sharpe_ratio DESC", "period_type", "period_end DESC"],
                unique=False
            ),
            
            # Drawdown analysis
            IndexConfig(
                name="idx_perf_drawdown",
                table=PerformanceSchema.TABLE_NAME,
                columns=["max_drawdown_pct DESC", "period_end DESC"],
                unique=False
            ),
            
            # Trading performance
            IndexConfig(
                name="idx_perf_trading",
                table=PerformanceSchema.TABLE_NAME,
                columns=["win_rate DESC", "profit_factor DESC", "period_end DESC"],
                unique=False
            )
        ]


class SchemaManager:
    """
    Manages database schema creation, updates, and optimizations
    """
    
    def __init__(self, database_manager):
        """Initialize schema manager"""
        self.db = database_manager
        self.schemas = {
            TableType.BALANCE_HISTORY: BalanceHistorySchema,
            TableType.POSITION_TRACKING: PositionSchema,
            TableType.TRADE_HISTORY: TradeHistorySchema,
            TableType.PORTFOLIO_METRICS: PortfolioMetricsSchema,
            TableType.PERFORMANCE_ANALYTICS: PerformanceSchema
        }
        
        logger.info("[SCHEMA_MANAGER] Initialized schema management system")
    
    async def create_all_tables(self) -> bool:
        """Create all database tables with optimized schemas"""
        try:
            logger.info("[SCHEMA_MANAGER] Creating all database tables...")
            
            operations = []
            
            # Create all tables
            for table_type, schema_class in self.schemas.items():
                create_sql = schema_class.get_create_table_sql()
                operations.append((create_sql, ()))
                logger.debug(f"[SCHEMA_MANAGER] Prepared table creation: {table_type.value}")
            
            # Execute table creation in transaction
            success = await self.db.execute_transaction(operations)
            
            if success:
                logger.info("[SCHEMA_MANAGER] All tables created successfully")
                return True
            else:
                logger.error("[SCHEMA_MANAGER] Failed to create tables")
                return False
                
        except Exception as e:
            logger.error(f"[SCHEMA_MANAGER] Error creating tables: {e}")
            return False
    
    async def create_all_indexes(self) -> bool:
        """Create all optimized indexes for high-performance queries"""
        try:
            logger.info("[SCHEMA_MANAGER] Creating optimized indexes...")
            
            total_indexes = 0
            
            for table_type, schema_class in self.schemas.items():
                if hasattr(schema_class, 'get_indexes'):
                    indexes = schema_class.get_indexes()
                    
                    for index_config in indexes:
                        try:
                            create_sql = index_config.get_create_sql()
                            await self.db.execute_write(create_sql)
                            total_indexes += 1
                            logger.debug(f"[SCHEMA_MANAGER] Created index: {index_config.name}")
                        except Exception as e:
                            logger.error(f"[SCHEMA_MANAGER] Failed to create index {index_config.name}: {e}")
            
            logger.info(f"[SCHEMA_MANAGER] Created {total_indexes} optimized indexes")
            return True
            
        except Exception as e:
            logger.error(f"[SCHEMA_MANAGER] Error creating indexes: {e}")
            return False
    
    async def create_triggers(self) -> bool:
        """Create database triggers for automatic data management"""
        try:
            logger.info("[SCHEMA_MANAGER] Creating database triggers...")
            
            total_triggers = 0
            
            for table_type, schema_class in self.schemas.items():
                if hasattr(schema_class, 'get_triggers'):
                    triggers = schema_class.get_triggers()
                    
                    for trigger_sql in triggers:
                        try:
                            await self.db.execute_write(trigger_sql)
                            total_triggers += 1
                            logger.debug(f"[SCHEMA_MANAGER] Created trigger for {table_type.value}")
                        except Exception as e:
                            logger.error(f"[SCHEMA_MANAGER] Failed to create trigger: {e}")
            
            logger.info(f"[SCHEMA_MANAGER] Created {total_triggers} database triggers")
            return True
            
        except Exception as e:
            logger.error(f"[SCHEMA_MANAGER] Error creating triggers: {e}")
            return False
    
    async def create_views(self) -> bool:
        """Create database views for common queries and analytics"""
        try:
            logger.info("[SCHEMA_MANAGER] Creating database views...")
            
            total_views = 0
            
            for table_type, schema_class in self.schemas.items():
                if hasattr(schema_class, 'get_partitioning_sql'):
                    views = schema_class.get_partitioning_sql()
                    
                    for view_sql in views:
                        try:
                            await self.db.execute_write(view_sql)
                            total_views += 1
                            logger.debug(f"[SCHEMA_MANAGER] Created view for {table_type.value}")
                        except Exception as e:
                            logger.error(f"[SCHEMA_MANAGER] Failed to create view: {e}")
            
            logger.info(f"[SCHEMA_MANAGER] Created {total_views} database views")
            return True
            
        except Exception as e:
            logger.error(f"[SCHEMA_MANAGER] Error creating views: {e}")
            return False
    
    async def initialize_complete_schema(self) -> bool:
        """Initialize complete database schema with all optimizations"""
        try:
            logger.info("[SCHEMA_MANAGER] Initializing complete database schema...")
            
            # Create tables
            if not await self.create_all_tables():
                return False
            
            # Create indexes
            if not await self.create_all_indexes():
                return False
            
            # Create triggers
            if not await self.create_triggers():
                return False
            
            # Create views
            if not await self.create_views():
                return False
            
            # Run analyze to update statistics
            await self.db.analyze_database()
            
            logger.info("[SCHEMA_MANAGER] Complete database schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"[SCHEMA_MANAGER] Error initializing schema: {e}")
            return False
    
    async def get_schema_info(self) -> Dict[str, Any]:
        """Get comprehensive schema information"""
        try:
            schema_info = {
                'tables': {},
                'indexes': {},
                'views': {},
                'triggers': {}
            }
            
            # Get table information
            tables_query = """
            SELECT name, sql FROM sqlite_master 
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
            
            tables = await self.db.execute_query(tables_query)
            for table in tables:
                schema_info['tables'][table['name']] = {
                    'sql': table['sql'],
                    'row_count': await self._get_table_row_count(table['name'])
                }
            
            # Get index information
            indexes_query = """
            SELECT name, tbl_name, sql FROM sqlite_master 
            WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
            ORDER BY tbl_name, name
            """
            
            indexes = await self.db.execute_query(indexes_query)
            for index in indexes:
                if index['tbl_name'] not in schema_info['indexes']:
                    schema_info['indexes'][index['tbl_name']] = []
                
                schema_info['indexes'][index['tbl_name']].append({
                    'name': index['name'],
                    'sql': index['sql']
                })
            
            # Get view information
            views_query = """
            SELECT name, sql FROM sqlite_master 
            WHERE type = 'view'
            ORDER BY name
            """
            
            views = await self.db.execute_query(views_query)
            for view in views:
                schema_info['views'][view['name']] = view['sql']
            
            # Get trigger information
            triggers_query = """
            SELECT name, tbl_name, sql FROM sqlite_master 
            WHERE type = 'trigger'
            ORDER BY tbl_name, name
            """
            
            triggers = await self.db.execute_query(triggers_query)
            for trigger in triggers:
                if trigger['tbl_name'] not in schema_info['triggers']:
                    schema_info['triggers'][trigger['tbl_name']] = []
                
                schema_info['triggers'][trigger['tbl_name']].append({
                    'name': trigger['name'],
                    'sql': trigger['sql']
                })
            
            return schema_info
            
        except Exception as e:
            logger.error(f"[SCHEMA_MANAGER] Error getting schema info: {e}")
            return {}
    
    async def _get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table"""
        try:
            result = await self.db.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            return result[0]['count'] if result else 0
        except Exception:
            return 0
    
    async def validate_schema(self) -> Dict[str, Any]:
        """Validate database schema integrity"""
        try:
            validation_results = {
                'valid': True,
                'issues': [],
                'table_checks': {},
                'index_checks': {},
                'foreign_key_checks': []
            }
            
            # Check each table exists and has expected structure
            for table_type, schema_class in self.schemas.items():
                table_name = table_type.value
                
                # Check if table exists
                check_query = """
                SELECT name FROM sqlite_master 
                WHERE type = 'table' AND name = ?
                """
                
                result = await self.db.execute_query(check_query, (table_name,))
                
                if not result:
                    validation_results['valid'] = False
                    validation_results['issues'].append(f"Missing table: {table_name}")
                    validation_results['table_checks'][table_name] = False
                else:
                    validation_results['table_checks'][table_name] = True
                    
                    # Check indexes for this table
                    if hasattr(schema_class, 'get_indexes'):
                        expected_indexes = schema_class.get_indexes()
                        for index_config in expected_indexes:
                            index_check_query = """
                            SELECT name FROM sqlite_master 
                            WHERE type = 'index' AND name = ?
                            """
                            
                            index_result = await self.db.execute_query(index_check_query, (index_config.name,))
                            
                            if not index_result:
                                validation_results['valid'] = False
                                validation_results['issues'].append(f"Missing index: {index_config.name}")
                                validation_results['index_checks'][index_config.name] = False
                            else:
                                validation_results['index_checks'][index_config.name] = True
            
            # Check foreign key constraints
            foreign_key_check = await self.db.execute_query("PRAGMA foreign_key_check")
            if foreign_key_check:
                validation_results['valid'] = False
                validation_results['foreign_key_checks'] = foreign_key_check
                validation_results['issues'].append("Foreign key constraint violations found")
            
            logger.info(f"[SCHEMA_MANAGER] Schema validation complete: {'VALID' if validation_results['valid'] else 'INVALID'}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"[SCHEMA_MANAGER] Error validating schema: {e}")
            return {'valid': False, 'error': str(e)}
    
    async def optimize_schema(self) -> bool:
        """Optimize database schema for better performance"""
        try:
            logger.info("[SCHEMA_MANAGER] Optimizing database schema...")
            
            # Update table statistics
            await self.db.analyze_database()
            
            # Reindex all indexes
            reindex_query = """
            SELECT name FROM sqlite_master 
            WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
            """
            
            indexes = await self.db.execute_query(reindex_query)
            
            for index in indexes:
                try:
                    await self.db.execute_write(f"REINDEX {index['name']}")
                    logger.debug(f"[SCHEMA_MANAGER] Reindexed: {index['name']}")
                except Exception as e:
                    logger.warning(f"[SCHEMA_MANAGER] Failed to reindex {index['name']}: {e}")
            
            # Vacuum database if needed
            await self.db.vacuum_database()
            
            logger.info("[SCHEMA_MANAGER] Schema optimization complete")
            return True
            
        except Exception as e:
            logger.error(f"[SCHEMA_MANAGER] Error optimizing schema: {e}")
            return False