"""
High-Performance Database Manager for Crypto Trading Bot
========================================================

Main database management system optimized for D: drive storage and high-frequency
trading operations. Provides thread-safe concurrent access, connection pooling,
and optimized SQLite configuration for maximum performance.

Features:
- SQLite optimized for SSD storage with D: drive configuration
- WAL mode for concurrent read/write operations without blocking
- Connection pooling with intelligent connection reuse
- Memory-mapped file operations for frequently accessed data
- Asynchronous database operations with asyncio integration
- Transaction management with automatic rollback on failure
- Performance monitoring with real-time metrics
- Auto-recovery from database corruption or lock issues
"""

import asyncio
import logging
import os
import sqlite3
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration optimized for trading operations"""
    # Storage paths (D: drive for performance)
    database_path: str = "D:/trading_data/trading_bot.db"
    backup_path: str = "D:/trading_data/backups"
    log_path: str = "D:/trading_data/logs"
    cache_path: str = "D:/trading_data/cache"

    # Connection pool settings
    max_connections: int = 20
    min_connections: int = 5
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0  # 5 minutes

    # Performance settings
    enable_wal_mode: bool = True
    enable_memory_mapping: bool = True
    cache_size_mb: int = 64
    page_size: int = 4096
    synchronous_mode: str = "NORMAL"  # NORMAL for performance, FULL for durability

    # Query timeouts (milliseconds)
    balance_query_timeout: int = 50
    position_query_timeout: int = 100
    analytics_query_timeout: int = 1000

    # Optimization settings
    enable_query_cache: bool = True
    cache_timeout_seconds: int = 300
    enable_prepared_statements: bool = True
    enable_batch_operations: bool = True

    # Maintenance settings
    auto_vacuum: bool = True
    analyze_frequency_hours: int = 24
    checkpoint_interval_seconds: int = 300  # 5 minutes

    def __post_init__(self):
        # Ensure directories exist
        for path in [self.database_path, self.backup_path, self.log_path, self.cache_path]:
            directory = os.path.dirname(path) if '.' in os.path.basename(path) else path
            Path(directory).mkdir(parents=True, exist_ok=True)


class ConnectionPool:
    """Thread-safe database connection pool optimized for trading operations"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: List[aiosqlite.Connection] = []
        self._pool_sync: List[sqlite3.Connection] = []
        self._lock = asyncio.Lock()
        self._sync_lock = RLock()
        self._created_connections = 0
        self._active_connections = 0
        self._last_cleanup = time.time()

        # Statistics
        self._stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'connections_closed': 0,
            'pool_hits': 0,
            'pool_misses': 0,
            'avg_connection_age': 0.0
        }

    async def initialize(self):
        """Initialize connection pool with minimum connections"""
        async with self._lock:
            logger.info(f"[DATABASE_POOL] Initializing connection pool (min: {self.config.min_connections})")
            logger.info(f"[DATABASE_POOL] Database path: {self.config.database_path}")

            # Create minimum number of connections
            successful_connections = 0
            for i in range(self.config.min_connections):
                try:
                    conn = await self._create_connection()
                    if conn:
                        self._pool.append(conn)
                        self._created_connections += 1
                        successful_connections += 1
                        logger.debug(f"[DATABASE_POOL] Created connection {i + 1}/{self.config.min_connections}")
                    else:
                        logger.error(f"[DATABASE_POOL] Failed to create connection {i + 1}/{self.config.min_connections}")
                except Exception as e:
                    logger.error(f"[DATABASE_POOL] Exception creating connection {i + 1}: {e}")

            if successful_connections == 0:
                raise RuntimeError("Failed to create any database connections")

            logger.info(f"[DATABASE_POOL] Pool initialized with {successful_connections}/{self.config.min_connections} connections")

            if successful_connections < self.config.min_connections:
                logger.warning(f"[DATABASE_POOL] Only {successful_connections} of {self.config.min_connections} minimum connections created")

    async def get_connection(self) -> aiosqlite.Connection:
        """Get a database connection from the pool"""
        async with self._lock:
            # Try to reuse existing connection
            if self._pool:
                conn = self._pool.pop()
                self._stats['pool_hits'] += 1
                self._stats['connections_reused'] += 1
                self._active_connections += 1
                return conn

            # Create new connection if under limit
            if self._created_connections < self.config.max_connections:
                conn = await self._create_connection()
                if conn:
                    self._created_connections += 1
                    self._active_connections += 1
                    self._stats['pool_misses'] += 1
                    self._stats['connections_created'] += 1
                    return conn

            # Wait for connection to become available
            logger.warning("[DATABASE_POOL] Connection pool exhausted, waiting...")
            for _ in range(100):  # Wait up to 10 seconds
                await asyncio.sleep(0.1)
                if self._pool:
                    conn = self._pool.pop()
                    self._stats['pool_hits'] += 1
                    self._active_connections += 1
                    return conn

            raise RuntimeError("Database connection pool exhausted")

    async def return_connection(self, conn: aiosqlite.Connection):
        """Return a connection to the pool"""
        async with self._lock:
            if len(self._pool) < self.config.max_connections:
                self._pool.append(conn)
                self._active_connections -= 1
            else:
                # Pool is full, close connection
                await conn.close()
                self._created_connections -= 1
                self._active_connections -= 1
                self._stats['connections_closed'] += 1

    def get_sync_connection(self) -> sqlite3.Connection:
        """Get synchronous connection for blocking operations"""
        with self._sync_lock:
            if self._pool_sync:
                conn = self._pool_sync.pop()
                self._stats['pool_hits'] += 1
                return conn

            # Create new sync connection
            conn = self._create_sync_connection()
            if conn:
                self._stats['pool_misses'] += 1
                return conn

            raise RuntimeError("Failed to create sync database connection")

    def return_sync_connection(self, conn: sqlite3.Connection):
        """Return synchronous connection to pool"""
        with self._sync_lock:
            if len(self._pool_sync) < self.config.max_connections // 2:
                self._pool_sync.append(conn)
            else:
                conn.close()
                self._stats['connections_closed'] += 1

    async def _create_connection(self) -> Optional[aiosqlite.Connection]:
        """Create optimized database connection"""
        try:
            logger.debug(f"[DATABASE_POOL] Attempting to connect to: {self.config.database_path}")

            # Ensure the database directory exists
            db_dir = os.path.dirname(self.config.database_path)
            if not os.path.exists(db_dir):
                logger.info(f"[DATABASE_POOL] Creating database directory: {db_dir}")
                Path(db_dir).mkdir(parents=True, exist_ok=True)

            conn = await aiosqlite.connect(
                self.config.database_path,
                timeout=self.config.connection_timeout
            )

            logger.debug("[DATABASE_POOL] Connected successfully, applying optimizations...")

            # Apply performance optimizations
            await self._optimize_connection(conn)

            logger.debug("[DATABASE_POOL] Connection created and optimized successfully")
            return conn

        except Exception as e:
            logger.error(f"[DATABASE_POOL] Failed to create connection: {e}")
            logger.error(f"[DATABASE_POOL] Database path: {self.config.database_path}")
            logger.error(f"[DATABASE_POOL] Connection timeout: {self.config.connection_timeout}")
            return None

    def _create_sync_connection(self) -> Optional[sqlite3.Connection]:
        """Create synchronous database connection"""
        try:
            conn = sqlite3.connect(
                self.config.database_path,
                timeout=self.config.connection_timeout
            )

            # Apply performance optimizations
            self._optimize_sync_connection(conn)

            return conn

        except Exception as e:
            logger.error(f"[DATABASE_POOL] Failed to create sync connection: {e}")
            return None

    async def _optimize_connection(self, conn: aiosqlite.Connection):
        """Apply performance optimizations to connection"""
        try:
            logger.debug("[DATABASE_POOL] Applying WAL mode...")
            if self.config.enable_wal_mode:
                await conn.execute("PRAGMA journal_mode = WAL")

            logger.debug("[DATABASE_POOL] Applying basic optimizations...")
            await conn.execute(f"PRAGMA synchronous = {self.config.synchronous_mode}")
            await conn.execute(f"PRAGMA cache_size = -{self.config.cache_size_mb * 1024}")
            await conn.execute(f"PRAGMA page_size = {self.config.page_size}")
            await conn.execute("PRAGMA temp_store = MEMORY")
            await conn.execute("PRAGMA locking_mode = NORMAL")

            logger.debug("[DATABASE_POOL] Applying memory mapping...")
            if self.config.enable_memory_mapping:
                await conn.execute("PRAGMA mmap_size = 268435456")  # 256MB

            logger.debug("[DATABASE_POOL] Applying auto vacuum settings...")
            if self.config.auto_vacuum:
                await conn.execute("PRAGMA auto_vacuum = INCREMENTAL")

            logger.debug("[DATABASE_POOL] Enabling foreign keys and setting timeouts...")
            # Enable foreign keys
            await conn.execute("PRAGMA foreign_keys = ON")

            # Set busy timeout
            await conn.execute("PRAGMA busy_timeout = 30000")

            await conn.commit()
            logger.debug("[DATABASE_POOL] Connection optimization complete")

        except Exception as e:
            logger.error(f"[DATABASE_POOL] Failed to optimize connection: {e}")
            logger.error(f"[DATABASE_POOL] WAL mode enabled: {self.config.enable_wal_mode}")
            logger.error(f"[DATABASE_POOL] Memory mapping enabled: {self.config.enable_memory_mapping}")
            raise  # Re-raise to prevent using an unoptimized connection

    def _optimize_sync_connection(self, conn: sqlite3.Connection):
        """Apply performance optimizations to sync connection"""
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute(f"PRAGMA synchronous = {self.config.synchronous_mode}")
            conn.execute(f"PRAGMA cache_size = -{self.config.cache_size_mb * 1024}")
            conn.execute(f"PRAGMA page_size = {self.config.page_size}")
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA locking_mode = NORMAL")

            if self.config.enable_memory_mapping:
                conn.execute("PRAGMA mmap_size = 268435456")

            if self.config.auto_vacuum:
                conn.execute("PRAGMA auto_vacuum = INCREMENTAL")

            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 30000")

            conn.commit()

        except Exception as e:
            logger.error(f"[DATABASE_POOL] Failed to optimize sync connection: {e}")

    async def cleanup_idle_connections(self):
        """Remove idle connections from pool"""
        async with self._lock:
            current_time = time.time()

            if current_time - self._last_cleanup > self.config.idle_timeout:
                # Close idle connections beyond minimum
                while len(self._pool) > self.config.min_connections:
                    conn = self._pool.pop()
                    await conn.close()
                    self._created_connections -= 1
                    self._stats['connections_closed'] += 1

                self._last_cleanup = current_time

    async def close_all(self):
        """Close all connections in pool"""
        async with self._lock:
            # Close async connections
            for conn in self._pool:
                await conn.close()
            self._pool.clear()

            # Close sync connections
            with self._sync_lock:
                for conn in self._pool_sync:
                    conn.close()
                self._pool_sync.clear()

            self._created_connections = 0
            self._active_connections = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            'pool_size': len(self._pool),
            'sync_pool_size': len(self._pool_sync),
            'active_connections': self._active_connections,
            'created_connections': self._created_connections,
            'max_connections': self.config.max_connections,
            'statistics': dict(self._stats)
        }


class DatabaseManager:
    """
    High-performance database manager for crypto trading operations
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize database manager"""
        self.config = config or DatabaseConfig()
        self.pool = ConnectionPool(self.config)

        # State management
        self._initialized = False
        self._lock = asyncio.Lock()

        # Query cache
        self._query_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = RLock()

        # Performance monitoring
        self._query_stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'avg_query_time': 0.0,
            'slow_queries': 0,
            'failed_queries': 0
        }

        # Background tasks
        self._maintenance_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(f"[DATABASE_MANAGER] Initialized with database: {self.config.database_path}")

    async def initialize(self) -> bool:
        """Initialize database manager and connection pool"""
        if self._initialized:
            logger.warning("[DATABASE_MANAGER] Already initialized")
            return True

        try:
            async with self._lock:
                logger.info("[DATABASE_MANAGER] Starting initialization...")

                # Ensure database directory exists
                db_dir = os.path.dirname(self.config.database_path)
                Path(db_dir).mkdir(parents=True, exist_ok=True)

                # Initialize connection pool
                await self.pool.initialize()

                # Set initialized flag BEFORE testing connection to avoid circular dependency
                self._initialized = True

                # Test database connection
                try:
                    async with self.get_connection() as conn:
                        await conn.execute("SELECT 1")
                        await conn.commit()
                    logger.info("[DATABASE_MANAGER] Database connection test successful")
                except Exception as e:
                    logger.error(f"[DATABASE_MANAGER] Database connection test failed: {e}")
                    self._initialized = False
                    raise

                # Start background maintenance
                self._running = True
                self._maintenance_task = asyncio.create_task(self._maintenance_loop())

                logger.info("[DATABASE_MANAGER] Initialization complete")
                return True

        except Exception as e:
            logger.error(f"[DATABASE_MANAGER] Initialization failed: {e}")
            self._initialized = False
            return False

    async def shutdown(self):
        """Shutdown database manager"""
        if not self._initialized:
            return

        logger.info("[DATABASE_MANAGER] Shutting down...")

        self._running = False

        # Stop maintenance task
        if self._maintenance_task and not self._maintenance_task.done():
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        await self.pool.close_all()

        self._initialized = False
        logger.info("[DATABASE_MANAGER] Shutdown complete")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get database connection with automatic return to pool"""
        if not self._initialized:
            raise RuntimeError("Database manager not initialized")

        conn = await self.pool.get_connection()
        try:
            yield conn
        finally:
            await self.pool.return_connection(conn)

    @contextmanager
    def get_sync_connection(self):
        """Get synchronous database connection"""
        if not self._initialized:
            raise RuntimeError("Database manager not initialized")

        conn = self.pool.get_sync_connection()
        try:
            yield conn
        finally:
            self.pool.return_sync_connection(conn)

    async def execute_query(self, query: str, parameters: Tuple = (),
                          use_cache: bool = False, cache_timeout: int = None) -> List[Dict[str, Any]]:
        """
        Execute SELECT query with optional caching
        
        Args:
            query: SQL query string
            parameters: Query parameters
            use_cache: Enable query result caching
            cache_timeout: Cache timeout in seconds (uses config default if None)
            
        Returns:
            List of result dictionaries
        """
        start_time = time.time()
        cache_key = None

        try:
            # Check cache if enabled
            if use_cache and self.config.enable_query_cache:
                cache_key = f"{query}:{parameters}"
                cached_result = self._get_cached_result(cache_key)
                if cached_result is not None:
                    self._query_stats['cache_hits'] += 1
                    return cached_result

            # Execute query
            async with self.get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(query, parameters)
                rows = await cursor.fetchall()

                # Convert to list of dictionaries
                results = [dict(row) for row in rows]

                # Cache result if enabled
                if use_cache and cache_key and self.config.enable_query_cache:
                    timeout = cache_timeout or self.config.cache_timeout_seconds
                    self._cache_result(cache_key, results, timeout)

                # Update statistics
                query_time = time.time() - start_time
                self._update_query_stats(query_time, success=True)

                return results

        except Exception as e:
            query_time = time.time() - start_time
            self._update_query_stats(query_time, success=False)
            logger.error(f"[DATABASE_MANAGER] Query failed: {e}")
            raise

    async def execute_write(self, query: str, parameters: Tuple = (),
                          commit: bool = True) -> int:
        """
        Execute INSERT/UPDATE/DELETE query
        
        Args:
            query: SQL query string
            parameters: Query parameters
            commit: Auto-commit transaction
            
        Returns:
            Number of affected rows
        """
        start_time = time.time()

        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(query, parameters)

                if commit:
                    await conn.commit()

                affected_rows = cursor.rowcount

                # Update statistics
                query_time = time.time() - start_time
                self._update_query_stats(query_time, success=True)

                return affected_rows

        except Exception as e:
            query_time = time.time() - start_time
            self._update_query_stats(query_time, success=False)
            logger.error(f"[DATABASE_MANAGER] Write query failed: {e}")
            raise

    async def execute_batch(self, query: str, parameter_list: List[Tuple],
                          commit: bool = True) -> int:
        """
        Execute batch operation for better performance
        
        Args:
            query: SQL query string
            parameter_list: List of parameter tuples
            commit: Auto-commit transaction
            
        Returns:
            Total number of affected rows
        """
        if not self.config.enable_batch_operations:
            # Fall back to individual queries
            total_affected = 0
            for parameters in parameter_list:
                affected = await self.execute_write(query, parameters, commit=False)
                total_affected += affected

            if commit:
                async with self.get_connection() as conn:
                    await conn.commit()

            return total_affected

        start_time = time.time()

        try:
            async with self.get_connection() as conn:
                cursor = await conn.executemany(query, parameter_list)

                if commit:
                    await conn.commit()

                total_affected = cursor.rowcount

                # Update statistics
                query_time = time.time() - start_time
                self._update_query_stats(query_time, success=True)

                return total_affected

        except Exception as e:
            query_time = time.time() - start_time
            self._update_query_stats(query_time, success=False)
            logger.error(f"[DATABASE_MANAGER] Batch query failed: {e}")
            raise

    async def execute_transaction(self, operations: List[Tuple[str, Tuple]]) -> bool:
        """
        Execute multiple operations in a single transaction
        
        Args:
            operations: List of (query, parameters) tuples
            
        Returns:
            True if transaction successful
        """
        start_time = time.time()

        try:
            async with self.get_connection() as conn:
                # Begin transaction
                await conn.execute("BEGIN")

                try:
                    for query, parameters in operations:
                        await conn.execute(query, parameters)

                    # Commit transaction
                    await conn.commit()

                    # Update statistics
                    query_time = time.time() - start_time
                    self._update_query_stats(query_time, success=True)

                    return True

                except Exception as e:
                    # Rollback on error
                    await conn.rollback()
                    logger.error(f"[DATABASE_MANAGER] Transaction rolled back: {e}")
                    raise

        except Exception as e:
            query_time = time.time() - start_time
            self._update_query_stats(query_time, success=False)
            logger.error(f"[DATABASE_MANAGER] Transaction failed: {e}")
            return False

    def _get_cached_result(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached query result"""
        with self._cache_lock:
            if cache_key in self._query_cache:
                result, timestamp = self._query_cache[cache_key]

                # Check if cache entry is still valid
                if time.time() - timestamp < self.config.cache_timeout_seconds:
                    return result
                else:
                    # Remove expired entry
                    del self._query_cache[cache_key]

        return None

    def _cache_result(self, cache_key: str, result: List[Dict[str, Any]], timeout: int):
        """Cache query result"""
        with self._cache_lock:
            self._query_cache[cache_key] = (result, time.time())

            # Clean up old cache entries if needed
            if len(self._query_cache) > 1000:  # Max 1000 cached queries
                self._cleanup_cache()

    def _cleanup_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = []

        for key, (_, timestamp) in self._query_cache.items():
            if current_time - timestamp > self.config.cache_timeout_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            del self._query_cache[key]

    def _update_query_stats(self, query_time: float, success: bool):
        """Update query performance statistics"""
        self._query_stats['total_queries'] += 1

        if success:
            # Update average query time
            total_time = self._query_stats['avg_query_time'] * (self._query_stats['total_queries'] - 1)
            self._query_stats['avg_query_time'] = (total_time + query_time) / self._query_stats['total_queries']

            # Track slow queries (>1 second)
            if query_time > 1.0:
                self._query_stats['slow_queries'] += 1
        else:
            self._query_stats['failed_queries'] += 1

    async def _maintenance_loop(self):
        """Background maintenance loop"""
        while self._running:
            try:
                # Clean up idle connections
                await self.pool.cleanup_idle_connections()

                # Clean up query cache
                with self._cache_lock:
                    self._cleanup_cache()

                # WAL checkpoint (every 5 minutes)
                if self.config.enable_wal_mode:
                    try:
                        async with self.get_connection() as conn:
                            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    except Exception as e:
                        logger.warning(f"[DATABASE_MANAGER] WAL checkpoint failed: {e}")

                # Sleep until next maintenance cycle
                await asyncio.sleep(self.config.checkpoint_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[DATABASE_MANAGER] Maintenance error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def analyze_database(self):
        """Run ANALYZE to update query planner statistics"""
        try:
            async with self.get_connection() as conn:
                await conn.execute("ANALYZE")
                await conn.commit()
            logger.info("[DATABASE_MANAGER] Database analysis complete")
        except Exception as e:
            logger.error(f"[DATABASE_MANAGER] Database analysis failed: {e}")

    async def vacuum_database(self):
        """Run VACUUM to optimize database file"""
        try:
            async with self.get_connection() as conn:
                await conn.execute("VACUUM")
            logger.info("[DATABASE_MANAGER] Database vacuum complete")
        except Exception as e:
            logger.error(f"[DATABASE_MANAGER] Database vacuum failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get database manager status"""
        return {
            'initialized': self._initialized,
            'running': self._running,
            'database_path': self.config.database_path,
            'database_size_mb': self._get_database_size_mb(),
            'connection_pool': self.pool.get_stats(),
            'query_cache_size': len(self._query_cache),
            'query_statistics': dict(self._query_stats),
            'config': {
                'wal_mode': self.config.enable_wal_mode,
                'memory_mapping': self.config.enable_memory_mapping,
                'cache_size_mb': self.config.cache_size_mb,
                'max_connections': self.config.max_connections
            }
        }

    def _get_database_size_mb(self) -> float:
        """Get database file size in MB"""
        try:
            if os.path.exists(self.config.database_path):
                size_bytes = os.path.getsize(self.config.database_path)
                return round(size_bytes / (1024 * 1024), 2)
        except Exception:
            pass
        return 0.0

    # Context manager support
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()
