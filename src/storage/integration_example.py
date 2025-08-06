"""
Complete Storage System Integration Example
==========================================

This example demonstrates how to integrate and use the complete high-performance
storage system for the crypto trading bot. Shows initialization, configuration,
and typical usage patterns for real-time trading operations.

Features Demonstrated:
- Database manager initialization with D: drive optimization
- Schema creation with optimized indexes for trading queries
- Query optimizer usage for high-performance data retrieval
- Backup system configuration and automated backups
- Data retention policies with intelligent cleanup
- Integration with existing balance and portfolio managers
- Performance monitoring and optimization
- Error handling and recovery procedures
"""

import asyncio
import logging
import time
from datetime import datetime
from decimal import Decimal

from .backup_manager import BackupConfig, BackupManager
from .data_retention import DataRetentionManager

# Import the complete storage system
from .database_manager import DatabaseConfig, DatabaseManager
from .query_optimizer import QueryConfig, QueryOptimizer
from .schemas import SchemaManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingBotStorageSystem:
    """
    Complete trading bot storage system integration
    """

    def __init__(self):
        """Initialize the complete storage system"""
        # Database configuration optimized for D: drive
        self.db_config = DatabaseConfig(
            database_path="D:/trading_data/trading_bot.db",
            backup_path="D:/trading_data/backups",
            log_path="D:/trading_data/logs",
            cache_path="D:/trading_data/cache",
            max_connections=20,
            enable_wal_mode=True,
            enable_memory_mapping=True,
            cache_size_mb=128,  # 128MB cache for high-frequency trading
            enable_query_cache=True,
            enable_batch_operations=True
        )

        # Initialize core components
        self.db_manager = DatabaseManager(self.db_config)
        self.schema_manager = SchemaManager(self.db_manager)

        # Query optimizer configuration
        query_config = QueryConfig(
            use_cache=True,
            cache_timeout=300,
            max_execution_time_ms=50,  # 50ms max for balance queries
            enable_explain=True
        )
        self.query_optimizer = QueryOptimizer(self.db_manager, query_config)

        # Backup configuration
        backup_config = BackupConfig(
            backup_base_path="D:/trading_data/backups",
            archive_path="D:/trading_data/archives",
            full_backup_interval_hours=24,
            incremental_backup_interval_hours=6,
            keep_full_backups_days=30,
            enable_compression=True,
            verify_backups=True
        )
        self.backup_manager = BackupManager(self.db_manager, backup_config)

        # Data retention manager
        self.retention_manager = DataRetentionManager(
            self.db_manager,
            self.backup_manager,
            "D:/trading_data/archives"
        )

        logger.info("[STORAGE_SYSTEM] Initialized complete trading bot storage system")

    async def initialize(self) -> bool:
        """Initialize the complete storage system"""
        try:
            logger.info("[STORAGE_SYSTEM] Starting complete storage system initialization...")

            # 1. Initialize database manager
            logger.info("[STORAGE_SYSTEM] Initializing database manager...")
            if not await self.db_manager.initialize():
                logger.error("[STORAGE_SYSTEM] Database manager initialization failed")
                return False

            # 2. Create database schema with optimized indexes
            logger.info("[STORAGE_SYSTEM] Creating optimized database schema...")
            if not await self.schema_manager.initialize_complete_schema():
                logger.error("[STORAGE_SYSTEM] Schema initialization failed")
                return False

            # 3. Initialize backup system
            logger.info("[STORAGE_SYSTEM] Initializing backup system...")
            if not await self.backup_manager.initialize():
                logger.error("[STORAGE_SYSTEM] Backup system initialization failed")
                return False

            # 4. Initialize data retention system
            logger.info("[STORAGE_SYSTEM] Initializing data retention system...")
            if not await self.retention_manager.initialize():
                logger.error("[STORAGE_SYSTEM] Data retention initialization failed")
                return False

            # 5. Run initial optimization
            logger.info("[STORAGE_SYSTEM] Running initial query optimization...")
            await self.query_optimizer.optimize_all_queries()

            # 6. Validate system integrity
            validation_result = await self.schema_manager.validate_schema()
            if not validation_result['valid']:
                logger.warning(f"[STORAGE_SYSTEM] Schema validation issues: {validation_result['issues']}")

            logger.info("[STORAGE_SYSTEM] Complete storage system initialization successful!")
            return True

        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Storage system initialization failed: {e}")
            return False

    async def shutdown(self):
        """Shutdown the complete storage system"""
        logger.info("[STORAGE_SYSTEM] Shutting down storage system...")

        # Shutdown in reverse order
        await self.retention_manager.shutdown()
        await self.backup_manager.shutdown()
        await self.db_manager.shutdown()

        logger.info("[STORAGE_SYSTEM] Storage system shutdown complete")

    # Balance Operations (High-Frequency)

    async def record_balance_update(self, asset: str, balance: Decimal,
                                  hold_trade: Decimal, source: str,
                                  change_reason: str = None) -> bool:
        """Record a balance update with optimized performance"""
        try:
            start_time = time.time()

            # Use optimized balance queries
            success = await self.query_optimizer.balance_queries.insert_balance_entry(
                asset=asset,
                balance=balance,
                hold_trade=hold_trade,
                source=source,
                change_reason=change_reason
            )

            execution_time_ms = (time.time() - start_time) * 1000

            if execution_time_ms > 10:  # Log slow balance updates
                logger.warning(f"[STORAGE_SYSTEM] Slow balance update: {execution_time_ms:.2f}ms for {asset}")

            return success

        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error recording balance update: {e}")
            return False

    async def get_latest_balance(self, asset: str) -> Optional[Dict[str, Any]]:
        """Get latest balance with sub-50ms performance"""
        try:
            return await self.query_optimizer.balance_queries.get_latest_balance(
                asset, use_cache=True
            )
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error getting latest balance: {e}")
            return None

    async def get_all_balances(self) -> List[Dict[str, Any]]:
        """Get all latest balances with optimized query"""
        try:
            return await self.query_optimizer.balance_queries.get_all_latest_balances(
                use_cache=True
            )
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error getting all balances: {e}")
            return []

    async def batch_update_balances(self, balance_updates: List[Tuple]) -> int:
        """Batch update multiple balances for high-throughput operations"""
        try:
            return await self.query_optimizer.balance_queries.batch_insert_balances(
                balance_updates
            )
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error in batch balance update: {e}")
            return 0

    # Position Operations

    async def create_position(self, position_id: str, symbol: str, position_type: str,
                            size: Decimal, entry_price: Decimal, strategy: str = None) -> bool:
        """Create new position with optimized insertion"""
        try:
            return await self.query_optimizer.position_queries.create_position(
                position_id=position_id,
                symbol=symbol,
                position_type=position_type,
                size=size,
                entry_price=entry_price,
                strategy=strategy
            )
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error creating position: {e}")
            return False

    async def update_position_price(self, position_id: str, new_price: Decimal) -> bool:
        """Update position price with real-time P&L calculation"""
        try:
            return await self.query_optimizer.position_queries.update_position_price(
                position_id, new_price
            )
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error updating position price: {e}")
            return False

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions with sub-100ms performance"""
        try:
            return await self.query_optimizer.position_queries.get_open_positions(
                use_cache=True
            )
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error getting open positions: {e}")
            return []

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary with single optimized query"""
        try:
            return await self.query_optimizer.position_queries.get_portfolio_summary(
                use_cache=True
            )
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error getting portfolio summary: {e}")
            return {}

    # Portfolio Analytics

    async def record_portfolio_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Record portfolio metrics for analytics"""
        try:
            return await self.query_optimizer.portfolio_queries.insert_portfolio_metrics(
                metrics_data
            )
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error recording portfolio metrics: {e}")
            return False

    async def get_performance_analytics(self, days_back: int = 30) -> Optional[Dict[str, Any]]:
        """Get performance analytics with caching"""
        try:
            return await self.query_optimizer.analytics_queries.calculate_sharpe_ratio(days_back)
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error getting performance analytics: {e}")
            return None

    # Backup Operations

    async def create_backup(self, backup_type: str = "incremental") -> bool:
        """Create database backup"""
        try:
            if backup_type == "full":
                backup = await self.backup_manager.create_full_backup()
            else:
                backup = await self.backup_manager.create_incremental_backup()

            return backup is not None

        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error creating backup: {e}")
            return False

    def get_backup_status(self) -> Dict[str, Any]:
        """Get backup system status"""
        return self.backup_manager.get_backup_status()

    # Data Retention Operations

    async def cleanup_old_data(self, policy_name: str = None) -> bool:
        """Force cleanup of old data"""
        try:
            return await self.retention_manager.force_cleanup(policy_name)
        except Exception as e:
            logger.error(f"[STORAGE_SYSTEM] Error in data cleanup: {e}")
            return False

    def get_retention_status(self) -> Dict[str, Any]:
        """Get data retention status"""
        return self.retention_manager.get_retention_status()

    # System Monitoring

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'database': self.db_manager.get_status(),
            'backups': self.backup_manager.get_backup_status(),
            'retention': self.retention_manager.get_retention_summary(),
            'query_optimization': self.query_optimizer.get_optimization_stats(),
            'timestamp': time.time()
        }

    async def run_performance_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive performance diagnostics"""
        results = {
            'timestamp': time.time(),
            'tests': []
        }

        # Test balance query performance
        start_time = time.time()
        balances = await self.get_all_balances()
        balance_time = (time.time() - start_time) * 1000

        results['tests'].append({
            'test': 'All Balances Query',
            'execution_time_ms': balance_time,
            'result_count': len(balances),
            'status': 'optimal' if balance_time < 100 else 'needs_optimization'
        })

        # Test position query performance
        start_time = time.time()
        positions = await self.get_open_positions()
        position_time = (time.time() - start_time) * 1000

        results['tests'].append({
            'test': 'Open Positions Query',
            'execution_time_ms': position_time,
            'result_count': len(positions),
            'status': 'optimal' if position_time < 100 else 'needs_optimization'
        })

        # Test portfolio summary performance
        start_time = time.time()
        await self.get_portfolio_summary()
        summary_time = (time.time() - start_time) * 1000

        results['tests'].append({
            'test': 'Portfolio Summary Query',
            'execution_time_ms': summary_time,
            'status': 'optimal' if summary_time < 50 else 'needs_optimization'
        })

        # Overall assessment
        avg_time = sum(test['execution_time_ms'] for test in results['tests']) / len(results['tests'])
        results['overall_status'] = 'optimal' if avg_time < 75 else 'needs_optimization'
        results['average_query_time_ms'] = avg_time

        return results

    # Context manager support
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()


# Example usage and integration
async def main():
    """Example of using the complete storage system"""

    # Initialize storage system
    storage = TradingBotStorageSystem()

    try:
        # Initialize system
        success = await storage.initialize()
        if not success:
            logger.error("Failed to initialize storage system")
            return

        logger.info("Storage system initialized successfully!")

        # Example: Record balance updates (high-frequency operation)
        logger.info("Testing balance operations...")

        # Single balance update
        await storage.record_balance_update(
            asset="USDT",
            balance=Decimal("1000.50"),
            hold_trade=Decimal("50.25"),
            source="websocket",
            change_reason="trade_execution"
        )

        # Batch balance updates for high-throughput
        balance_updates = [
            ("BTC", 0.5, 0.0, "websocket", "price_update", int(time.time() * 1000),
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0.01, 2.1, 'valid'),
            ("ETH", 2.3, 0.1, "websocket", "price_update", int(time.time() * 1000),
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0.05, 2.2, 'valid'),
        ]

        inserted_count = await storage.batch_update_balances(balance_updates)
        logger.info(f"Batch inserted {inserted_count} balance updates")

        # Get latest balances (should be sub-50ms)
        latest_balance = await storage.get_latest_balance("USDT")
        logger.info(f"Latest USDT balance: {latest_balance}")

        all_balances = await storage.get_all_balances()
        logger.info(f"Retrieved {len(all_balances)} balances")

        # Example: Position operations
        logger.info("Testing position operations...")

        # Create a position
        await storage.create_position(
            position_id="pos_001",
            symbol="BTC/USDT",
            position_type="LONG",
            size=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            strategy="scalping"
        )

        # Update position price (real-time P&L calculation)
        await storage.update_position_price("pos_001", Decimal("45500.00"))

        # Get portfolio summary
        portfolio_summary = await storage.get_portfolio_summary()
        logger.info(f"Portfolio summary: {portfolio_summary}")

        # Example: Create backup
        logger.info("Testing backup operations...")
        backup_success = await storage.create_backup("incremental")
        logger.info(f"Backup created: {backup_success}")

        # Example: Data retention
        logger.info("Testing data retention...")
        cleanup_success = await storage.cleanup_old_data()
        logger.info(f"Data cleanup completed: {cleanup_success}")

        # Run performance diagnostics
        logger.info("Running performance diagnostics...")
        diagnostics = await storage.run_performance_diagnostics()
        logger.info(f"Performance diagnostics: {diagnostics}")

        # Get system status
        system_status = storage.get_system_status()
        logger.info(f"System status: Database size: {system_status['database']['database_size_mb']}MB")

        logger.info("Storage system test completed successfully!")

    except Exception as e:
        logger.error(f"Storage system test failed: {e}")

    finally:
        # Always shutdown properly
        await storage.shutdown()


# Integration with existing trading bot components
class StorageIntegrationBridge:
    """
    Bridge to integrate storage system with existing trading bot components
    """

    def __init__(self, storage_system: TradingBotStorageSystem):
        self.storage = storage_system

    async def integrate_with_balance_manager(self, balance_manager):
        """Integrate with existing balance manager"""
        # Register callback for balance updates
        balance_manager.register_callback(
            'balance_update',
            self._handle_balance_update
        )

        # Override balance retrieval methods to use optimized storage
        original_get_balance = balance_manager.get_balance

        async def optimized_get_balance(asset: str, force_refresh: bool = False):
            if not force_refresh:
                # Try optimized storage first
                balance = await self.storage.get_latest_balance(asset)
                if balance:
                    return balance

            # Fall back to original method
            return await original_get_balance(asset, force_refresh)

        balance_manager.get_balance = optimized_get_balance

    async def integrate_with_portfolio_manager(self, portfolio_manager):
        """Integrate with existing portfolio manager"""
        # Register callback for position updates
        portfolio_manager.register_callback(
            'position_opened',
            self._handle_position_opened
        )

        portfolio_manager.register_callback(
            'position_closed',
            self._handle_position_closed
        )

    async def _handle_balance_update(self, balance_data: Dict[str, Any]):
        """Handle balance update from balance manager"""
        await self.storage.record_balance_update(
            asset=balance_data['asset'],
            balance=Decimal(str(balance_data['balance'])),
            hold_trade=Decimal(str(balance_data.get('hold_trade', 0))),
            source=balance_data.get('source', 'unknown'),
            change_reason='balance_manager_update'
        )

    async def _handle_position_opened(self, position_data):
        """Handle position opened event"""
        position = position_data if hasattr(position_data, 'position_id') else position_data['position']

        await self.storage.create_position(
            position_id=position.position_id,
            symbol=position.symbol,
            position_type=position.position_type.value,
            size=position.original_size,
            entry_price=position.avg_entry_price,
            strategy=position.strategy
        )

    async def _handle_position_closed(self, position_data):
        """Handle position closed event"""
        # Position is already closed in the position tracker
        # We just need to ensure the data is synced in our storage
        pass


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
