"""
High-Performance Trading Data Storage System
==========================================

Optimized data storage system specifically designed for cryptocurrency trading bot
high-frequency data operations. All data is stored on D: drive for maximum performance.

Features:
- SQLite database optimized for D: drive storage and SSD performance
- Efficient indexing for balance and position queries with microsecond response times
- Thread-safe concurrent access supporting multiple trading processes
- Automatic backup and recovery with configurable retention policies
- Balance history tracking with millisecond precision timestamps
- Position tracking with fast P&L calculation queries optimized for real-time trading
- Portfolio analytics with pre-computed aggregations for instant reporting
- Data retention policies with automatic cleanup and archival
- Memory-mapped file operations for ultra-fast data access
- Write-ahead logging (WAL) mode for maximum concurrency and durability

Components:
- DatabaseManager: Main database connection and transaction management
- SchemaManager: Database schema creation and migration handling
- QueryOptimizer: Pre-compiled optimized queries for trading operations
- BackupManager: Automated backup and recovery with point-in-time restore
- DataRetention: Intelligent data cleanup and archival system
- PerformanceMonitor: Real-time database performance tracking

Storage Architecture:
- Primary Database: D:/trading_data/trading_bot.db (main trading data)
- Backup Location: D:/trading_data/backups/ (automated backups)
- Archive Location: D:/trading_data/archives/ (historical data)
- Logs Location: D:/trading_data/logs/ (transaction and performance logs)
- Cache Location: D:/trading_data/cache/ (query result caching)

Performance Optimizations:
- WAL mode for concurrent read/write operations
- Memory-mapped file access for frequently accessed data
- Prepared statements for all trading queries
- Batch insert operations for balance updates
- Asynchronous I/O for non-blocking database operations
- Connection pooling for multiple trading processes
- Query result caching with intelligent invalidation
- Index optimization for time-series balance data
- Partitioned tables for historical data management
"""

from .database_manager import DatabaseManager, DatabaseConfig, ConnectionPool
from .schemas import (
    SchemaManager, BalanceHistorySchema, PositionSchema, 
    TradeHistorySchema, PortfolioMetricsSchema, PerformanceSchema
)
from .query_optimizer import (
    QueryOptimizer, BalanceQueries, PositionQueries, 
    PortfolioQueries, AnalyticsQueries
)
from .backup_manager import BackupManager, BackupConfig, RecoveryManager
from .data_retention import DataRetentionManager, RetentionPolicy, ArchivalManager

__version__ = "1.0.0"
__author__ = "Database-Optimizer Agent"

# Export main classes for easy imports
__all__ = [
    # Core database management
    'DatabaseManager',
    'DatabaseConfig', 
    'ConnectionPool',
    
    # Schema management
    'SchemaManager',
    'BalanceHistorySchema',
    'PositionSchema',
    'TradeHistorySchema', 
    'PortfolioMetricsSchema',
    'PerformanceSchema',
    
    # Query optimization
    'QueryOptimizer',
    'BalanceQueries',
    'PositionQueries',
    'PortfolioQueries', 
    'AnalyticsQueries',
    
    # Backup and recovery
    'BackupManager',
    'BackupConfig',
    'RecoveryManager',
    
    # Data retention and cleanup
    'DataRetentionManager',
    'RetentionPolicy',
    'ArchivalManager'
]

# Default configuration for D: drive optimization
DEFAULT_DATABASE_PATH = "D:/trading_data/trading_bot.db"
DEFAULT_BACKUP_PATH = "D:/trading_data/backups"
DEFAULT_ARCHIVE_PATH = "D:/trading_data/archives"
DEFAULT_LOG_PATH = "D:/trading_data/logs"
DEFAULT_CACHE_PATH = "D:/trading_data/cache"

# Performance constants optimized for trading operations
MAX_CONNECTION_POOL_SIZE = 20
DEFAULT_CACHE_TIMEOUT = 300  # 5 minutes
BALANCE_QUERY_TIMEOUT = 50   # 50ms for balance queries
POSITION_QUERY_TIMEOUT = 100 # 100ms for position queries
ANALYTICS_QUERY_TIMEOUT = 1000 # 1 second for analytics
BACKUP_RETENTION_DAYS = 30
ARCHIVE_RETENTION_MONTHS = 12