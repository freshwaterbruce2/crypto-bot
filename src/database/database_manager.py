"""
Database Manager for Crypto Trading Bot
Provides high-level database operations following 2025 best practices
"""

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TradeRecord:
    """Trade record structure"""
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: float
    price: float
    total_value: float
    fee: float = 0.0
    fee_currency: Optional[str] = None
    timestamp: Optional[int] = None
    exchange: str = "kraken"
    order_id: Optional[str] = None
    strategy: Optional[str] = None
    status: str = "filled"
    profit_loss: Optional[float] = None


@dataclass
class OrderRecord:
    """Order record structure"""
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit', 'stop_loss', 'take_profit'
    amount: float
    price: Optional[float] = None
    filled_amount: float = 0.0
    remaining_amount: Optional[float] = None
    status: str = "pending"
    exchange: str = "kraken"
    strategy: Optional[str] = None
    timestamp: Optional[int] = None


@dataclass
class BalanceRecord:
    """Balance record structure"""
    exchange: str
    asset: str
    available_balance: float
    locked_balance: float = 0.0
    usd_value: Optional[float] = None
    last_updated: Optional[int] = None


class DatabaseManager:
    """High-performance database manager for crypto trading bot"""

    def __init__(self, db_path: str, config: Optional[Dict] = None):
        self.db_path = db_path
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

        # Initialize database if it doesn't exist
        self._ensure_database_exists()

        # Configure performance settings
        self._configure_database()

    def _ensure_database_exists(self):
        """Ensure database file and directory exist"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        if not Path(self.db_path).exists():
            self.logger.info(f"Creating new database at {self.db_path}")
            # Run initialization script
            from scripts.init_database import create_database_tables
            create_database_tables(self.db_path)

    def _configure_database(self):
        """Apply performance optimizations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Performance settings from config
            perf_config = self.config.get('performance_optimizations', {})

            if perf_config.get('wal_mode', True):
                cursor.execute("PRAGMA journal_mode = WAL")

            sync_mode = perf_config.get('synchronous', 'NORMAL')
            cursor.execute(f"PRAGMA synchronous = {sync_mode}")

            cache_size = perf_config.get('cache_size', 10000)
            cursor.execute(f"PRAGMA cache_size = {cache_size}")

            temp_store = perf_config.get('temp_store', 'MEMORY')
            cursor.execute(f"PRAGMA temp_store = {temp_store}")

            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            with self._lock:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # Trade Operations
    def insert_trade(self, trade: TradeRecord) -> int:
        """Insert a new trade record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            timestamp = trade.timestamp or int(datetime.now().timestamp())

            cursor.execute("""
                INSERT INTO trades (
                    symbol, side, amount, price, total_value, fee, fee_currency,
                    timestamp, exchange, order_id, strategy, status, profit_loss
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.symbol, trade.side, trade.amount, trade.price,
                trade.total_value, trade.fee, trade.fee_currency,
                timestamp, trade.exchange, trade.order_id,
                trade.strategy, trade.status, trade.profit_loss
            ))

            trade_id = cursor.lastrowid
            conn.commit()

            self.logger.info(f"Inserted trade {trade_id}: {trade.side} {trade.amount} {trade.symbol} @ {trade.price}")
            return trade_id

    def get_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get trade records with optional filtering"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if symbol:
                cursor.execute("""
                    SELECT * FROM trades 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (symbol, limit))
            else:
                cursor.execute("""
                    SELECT * FROM trades 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def calculate_pnl(self, symbol: Optional[str] = None) -> Dict[str, float]:
        """Calculate profit and loss metrics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clause = "WHERE symbol = ?" if symbol else ""
            params = [symbol] if symbol else []

            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(profit_loss) as total_pnl,
                    AVG(profit_loss) as avg_pnl,
                    MAX(profit_loss) as max_win,
                    MIN(profit_loss) as max_loss
                FROM trades 
                {where_clause}
                AND profit_loss IS NOT NULL
            """, params)

            result = cursor.fetchone()

            if result:
                row = dict(result)
                if row['total_trades'] > 0:
                    row['win_rate'] = (row['winning_trades'] / row['total_trades']) * 100
                else:
                    row['win_rate'] = 0.0
                return row

            return {}

    # Order Operations
    def insert_order(self, order: OrderRecord) -> int:
        """Insert a new order record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            timestamp = order.timestamp or int(datetime.now().timestamp())

            cursor.execute("""
                INSERT INTO crypto_orders (
                    order_id, symbol, side, order_type, amount, price,
                    filled_amount, remaining_amount, status, exchange,
                    strategy, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id, order.symbol, order.side, order.order_type,
                order.amount, order.price, order.filled_amount,
                order.remaining_amount, order.status, order.exchange,
                order.strategy, timestamp
            ))

            order_db_id = cursor.lastrowid
            conn.commit()

            self.logger.info(f"Inserted order {order_db_id}: {order.order_id}")
            return order_db_id

    def update_order_status(self, order_id: str, status: str, filled_amount: Optional[float] = None):
        """Update order status and fill information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            update_fields = ["status = ?", "updated_at = strftime('%s', 'now')"]
            params = [status]

            if filled_amount is not None:
                update_fields.append("filled_amount = ?")
                params.append(filled_amount)

            if status == 'filled':
                update_fields.append("filled_at = strftime('%s', 'now')")
            elif status == 'canceled':
                update_fields.append("canceled_at = strftime('%s', 'now')")

            params.append(order_id)

            cursor.execute(f"""
                UPDATE crypto_orders 
                SET {', '.join(update_fields)}
                WHERE order_id = ?
            """, params)

            conn.commit()
            self.logger.info(f"Updated order {order_id} status to {status}")

    # Balance Operations
    def update_balance(self, balance: BalanceRecord):
        """Update wallet balance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            timestamp = balance.last_updated or int(datetime.now().timestamp())

            # Insert or update balance
            cursor.execute("""
                INSERT OR REPLACE INTO wallets (
                    exchange, asset, available_balance, locked_balance,
                    usd_value, last_updated, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
            """, (
                balance.exchange, balance.asset, balance.available_balance,
                balance.locked_balance, balance.usd_value, timestamp
            ))

            # Insert into balance history
            cursor.execute("""
                INSERT INTO balance_history (
                    exchange, asset, balance, usd_value, timestamp, balance_type
                ) VALUES (?, ?, ?, ?, ?, 'total')
            """, (
                balance.exchange, balance.asset,
                balance.available_balance + balance.locked_balance,
                balance.usd_value, timestamp
            ))

            conn.commit()

    def get_balances(self, exchange: str = "kraken") -> List[Dict]:
        """Get current wallet balances"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM wallets 
                WHERE exchange = ? 
                AND total_balance > 0
                ORDER BY usd_value DESC NULLS LAST
            """, (exchange,))

            return [dict(row) for row in cursor.fetchall()]

    # Market Data Operations
    def insert_market_data(self, symbol: str, timeframe: str, ohlcv_data: List[Dict]):
        """Insert OHLCV market data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            for candle in ohlcv_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data (
                        symbol, timestamp, open_price, high_price, low_price,
                        close_price, volume, timeframe, exchange
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, candle['timestamp'], candle['open'],
                    candle['high'], candle['low'], candle['close'],
                    candle['volume'], timeframe, "kraken"
                ))

            conn.commit()
            self.logger.debug(f"Inserted {len(ohlcv_data)} {timeframe} candles for {symbol}")

    # Performance Metrics
    def update_daily_performance(self, date: str, metrics: Dict[str, Any]):
        """Update daily performance metrics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO performance_metrics (
                    date, total_portfolio_value, daily_pnl, daily_pnl_percent,
                    total_trades, winning_trades, losing_trades, win_rate,
                    sharpe_ratio, max_drawdown, strategy, exchange
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date, metrics.get('portfolio_value', 0),
                metrics.get('daily_pnl', 0), metrics.get('daily_pnl_percent', 0),
                metrics.get('total_trades', 0), metrics.get('winning_trades', 0),
                metrics.get('losing_trades', 0), metrics.get('win_rate', 0),
                metrics.get('sharpe_ratio'), metrics.get('max_drawdown'),
                metrics.get('strategy', 'default'), metrics.get('exchange', 'kraken')
            ))

            conn.commit()

    # Logging Operations
    def log_event(self, level: str, message: str, module: Optional[str] = None,
                  strategy: Optional[str] = None, exchange: Optional[str] = None,
                  symbol: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log bot events to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            timestamp = int(datetime.now().timestamp())
            metadata_json = json.dumps(metadata) if metadata else None

            cursor.execute("""
                INSERT INTO bot_logs (
                    timestamp, level, message, module, strategy,
                    exchange, symbol, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, level, message, module, strategy,
                exchange, symbol, metadata_json
            ))

            conn.commit()

    # Utility Methods
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health metrics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Table counts
            tables = [
                'trades', 'crypto_orders', 'positions', 'market_data',
                'tickers', 'performance_metrics', 'portfolio_snapshots',
                'bot_config', 'bot_logs', 'wallets', 'balance_history'
            ]

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]

            # Database size
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            stats['database_size_bytes'] = page_count * page_size
            stats['database_size_mb'] = round(stats['database_size_bytes'] / (1024 * 1024), 2)

            # Recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM trades 
                WHERE timestamp > strftime('%s', 'now', '-24 hours')
            """)
            stats['trades_last_24h'] = cursor.fetchone()[0]

            return stats

    def cleanup_old_data(self):
        """Clean up old data based on retention policies"""
        retention_config = self.config.get('data_retention', {})

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Clean old debug logs
            debug_days = retention_config.get('debug_logs_days', 30)
            cursor.execute(f"""
                DELETE FROM bot_logs 
                WHERE level = 'DEBUG' 
                AND timestamp < strftime('%s', 'now', '-{debug_days} days')
            """)

            # Clean old market data
            market_days = retention_config.get('market_data_days', 365)
            cursor.execute(f"""
                DELETE FROM market_data 
                WHERE timestamp < strftime('%s', 'now', '-{market_days} days')
            """)

            # Clean old balance history
            balance_days = retention_config.get('balance_history_days', 730)
            cursor.execute(f"""
                DELETE FROM balance_history 
                WHERE timestamp < strftime('%s', 'now', '-{balance_days} days')
            """)

            conn.commit()

            # Vacuum database to reclaim space
            cursor.execute("VACUUM")

            self.logger.info("Database cleanup completed")


# Convenience function for easy integration
def get_database_manager(config_path: Optional[str] = None) -> DatabaseManager:
    """Get configured database manager instance"""
    if config_path:
        with open(config_path) as f:
            config = json.load(f)
    else:
        # Load from default location
        config_file = Path(__file__).parent.parent.parent / "config.json"
        with open(config_file) as f:
            config = json.load(f)

    db_config = config.get('database_config', {})
    db_path = db_config.get('database_path', 'D:/trading_data/crypto_bot.db')

    return DatabaseManager(db_path, db_config)
