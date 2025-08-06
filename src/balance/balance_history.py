"""
Balance History System
=====================

Comprehensive balance history tracking and analysis system for the crypto trading bot.
Maintains historical balance data, provides trend analysis, and supports balance
change detection with configurable retention policies.

Features:
- Historical balance tracking with timestamps
- Balance change detection and analysis
- Trend analysis and statistics
- Configurable data retention policies
- Efficient storage with periodic cleanup
- Export/import capabilities for persistence
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ..utils.decimal_precision_fix import safe_decimal

logger = logging.getLogger(__name__)


@dataclass
class BalanceHistoryEntry:
    """Individual balance history entry"""
    asset: str
    balance: Decimal
    hold_trade: Decimal
    free_balance: Decimal
    timestamp: float
    source: str
    change_reason: Optional[str] = None  # 'trade', 'deposit', 'withdrawal', 'adjustment'
    previous_balance: Optional[Decimal] = None
    balance_change: Optional[Decimal] = None

    def __post_init__(self):
        """Ensure decimal types and calculate changes"""
        self.balance = safe_decimal(self.balance)
        self.hold_trade = safe_decimal(self.hold_trade)
        self.free_balance = self.balance - self.hold_trade

        if self.previous_balance is not None:
            self.previous_balance = safe_decimal(self.previous_balance)
            self.balance_change = self.balance - self.previous_balance

        if self.timestamp == 0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'asset': self.asset,
            'balance': float(self.balance),
            'hold_trade': float(self.hold_trade),
            'free_balance': float(self.free_balance),
            'timestamp': self.timestamp,
            'source': self.source,
            'change_reason': self.change_reason,
            'previous_balance': float(self.previous_balance) if self.previous_balance else None,
            'balance_change': float(self.balance_change) if self.balance_change else None,
            'age_seconds': time.time() - self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BalanceHistoryEntry':
        """Create entry from dictionary"""
        return cls(
            asset=data['asset'],
            balance=safe_decimal(data['balance']),
            hold_trade=safe_decimal(data.get('hold_trade', 0)),
            free_balance=safe_decimal(data.get('free_balance', data['balance'])),
            timestamp=data['timestamp'],
            source=data['source'],
            change_reason=data.get('change_reason'),
            previous_balance=safe_decimal(data['previous_balance']) if data.get('previous_balance') else None,
            balance_change=safe_decimal(data['balance_change']) if data.get('balance_change') else None
        )


@dataclass
class BalanceTrend:
    """Balance trend analysis result"""
    asset: str
    trend_direction: str  # 'increasing', 'decreasing', 'stable', 'volatile'
    trend_strength: float  # 0.0 to 1.0
    average_balance: Decimal
    min_balance: Decimal
    max_balance: Decimal
    total_change: Decimal
    change_count: int
    analysis_period_hours: float
    volatility_score: float  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'asset': self.asset,
            'trend_direction': self.trend_direction,
            'trend_strength': self.trend_strength,
            'average_balance': float(self.average_balance),
            'min_balance': float(self.min_balance),
            'max_balance': float(self.max_balance),
            'total_change': float(self.total_change),
            'change_count': self.change_count,
            'analysis_period_hours': self.analysis_period_hours,
            'volatility_score': self.volatility_score
        }


class BalanceHistory:
    """
    Comprehensive balance history tracking and analysis system
    """

    def __init__(self,
                 max_entries_per_asset: int = 10000,
                 retention_hours: float = 24 * 7,  # 1 week
                 cleanup_interval_seconds: float = 3600,  # 1 hour
                 persistence_file: Optional[str] = None):
        """
        Initialize balance history system
        
        Args:
            max_entries_per_asset: Maximum history entries per asset
            retention_hours: How long to keep history data
            cleanup_interval_seconds: How often to run cleanup
            persistence_file: Optional file for persistent storage
        """
        self.max_entries_per_asset = max_entries_per_asset
        self.retention_hours = retention_hours
        self.cleanup_interval = cleanup_interval_seconds
        self.persistence_file = persistence_file

        # History storage: asset -> deque of entries
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_entries_per_asset))

        # Current balance tracking for change detection
        self._current_balances: Dict[str, BalanceHistoryEntry] = {}

        # Thread safety
        self._lock = RLock()
        self._async_lock = asyncio.Lock()

        # Statistics
        self._stats = {
            'total_entries': 0,
            'entries_added': 0,
            'entries_removed': 0,
            'cleanup_runs': 0,
            'persistence_saves': 0,
            'persistence_loads': 0
        }

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Change detection callbacks
        self._change_callbacks: List[Callable] = []

        # Trend analysis cache
        self._trend_cache: Dict[str, Tuple[BalanceTrend, float]] = {}  # asset -> (trend, cache_time)
        self._trend_cache_ttl = 300  # 5 minutes

        logger.info(f"[BALANCE_HISTORY] Initialized with retention={retention_hours}h, max_entries={max_entries_per_asset}")

    async def start(self):
        """Start the history system and load persistence"""
        if self._running:
            return

        self._running = True

        # Load from persistence file if available
        if self.persistence_file:
            await self._load_from_file()

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("[BALANCE_HISTORY] History system started")

    async def stop(self):
        """Stop the history system and save persistence"""
        if not self._running:
            return

        self._running = False

        # Stop cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Save to persistence file if available
        if self.persistence_file:
            await self._save_to_file()

        logger.info("[BALANCE_HISTORY] History system stopped")

    async def add_balance_entry(self,
                               asset: str,
                               balance: Union[Decimal, float, str],
                               hold_trade: Union[Decimal, float, str] = 0,
                               source: str = 'unknown',
                               change_reason: Optional[str] = None,
                               timestamp: Optional[float] = None) -> BalanceHistoryEntry:
        """
        Add a new balance entry
        
        Args:
            asset: Asset symbol
            balance: Total balance
            hold_trade: Amount held in trades
            source: Source of balance data
            change_reason: Reason for balance change
            timestamp: Timestamp (uses current time if None)
            
        Returns:
            The created history entry
        """
        async with self._async_lock:
            with self._lock:
                # Convert values
                balance_decimal = safe_decimal(balance)
                hold_decimal = safe_decimal(hold_trade)
                entry_timestamp = timestamp or time.time()

                # Get previous balance for change detection
                previous_entry = self._current_balances.get(asset)
                previous_balance = previous_entry.balance if previous_entry else None

                # Create new entry
                entry = BalanceHistoryEntry(
                    asset=asset,
                    balance=balance_decimal,
                    hold_trade=hold_decimal,
                    free_balance=balance_decimal - hold_decimal,
                    timestamp=entry_timestamp,
                    source=source,
                    change_reason=change_reason,
                    previous_balance=previous_balance
                )

                # Add to history
                self._history[asset].append(entry)
                self._current_balances[asset] = entry

                self._stats['entries_added'] += 1
                self._stats['total_entries'] += 1

                # Invalidate trend cache for this asset
                if asset in self._trend_cache:
                    del self._trend_cache[asset]

                # Call change detection callbacks if there's a change
                if entry.balance_change and entry.balance_change != 0:
                    await self._call_change_callbacks(entry)

                logger.debug(f"[BALANCE_HISTORY] Added entry for {asset}: {balance_decimal} (change: {entry.balance_change})")

                return entry

    def get_asset_history(self,
                         asset: str,
                         limit: Optional[int] = None,
                         since_timestamp: Optional[float] = None) -> List[BalanceHistoryEntry]:
        """
        Get history entries for a specific asset
        
        Args:
            asset: Asset symbol
            limit: Maximum number of entries to return
            since_timestamp: Only return entries after this timestamp
            
        Returns:
            List of history entries (newest first)
        """
        with self._lock:
            entries = list(self._history.get(asset, []))

            # Filter by timestamp if specified
            if since_timestamp:
                entries = [entry for entry in entries if entry.timestamp >= since_timestamp]

            # Sort by timestamp (newest first)
            entries.sort(key=lambda x: x.timestamp, reverse=True)

            # Apply limit
            if limit:
                entries = entries[:limit]

            return entries

    def get_current_balance(self, asset: str) -> Optional[BalanceHistoryEntry]:
        """Get the most recent balance entry for an asset"""
        with self._lock:
            return self._current_balances.get(asset)

    def get_all_current_balances(self) -> Dict[str, BalanceHistoryEntry]:
        """Get current balance entries for all assets"""
        with self._lock:
            return dict(self._current_balances)

    def get_balance_at_timestamp(self, asset: str, timestamp: float) -> Optional[BalanceHistoryEntry]:
        """
        Get balance entry closest to a specific timestamp
        
        Args:
            asset: Asset symbol
            timestamp: Target timestamp
            
        Returns:
            Closest balance entry or None if not found
        """
        with self._lock:
            entries = list(self._history.get(asset, []))

            if not entries:
                return None

            # Find entry with timestamp closest to target
            closest_entry = min(entries, key=lambda x: abs(x.timestamp - timestamp))
            return closest_entry

    def get_balance_changes(self,
                           asset: str,
                           since_timestamp: Optional[float] = None,
                           change_threshold: Optional[Decimal] = None) -> List[BalanceHistoryEntry]:
        """
        Get balance entries that represent significant changes
        
        Args:
            asset: Asset symbol
            since_timestamp: Only consider changes after this timestamp
            change_threshold: Minimum change amount to include
            
        Returns:
            List of entries with significant balance changes
        """
        with self._lock:
            entries = self.get_asset_history(asset, since_timestamp=since_timestamp)

            changes = []
            for entry in entries:
                if entry.balance_change is None:
                    continue

                # Check if change meets threshold
                if change_threshold is None or abs(entry.balance_change) >= change_threshold:
                    changes.append(entry)

            return changes

    async def analyze_balance_trend(self,
                                   asset: str,
                                   analysis_hours: float = 24.0,
                                   use_cache: bool = True) -> Optional[BalanceTrend]:
        """
        Analyze balance trend for an asset
        
        Args:
            asset: Asset symbol
            analysis_hours: How many hours back to analyze
            use_cache: Whether to use cached results
            
        Returns:
            Balance trend analysis or None if insufficient data
        """
        # Check cache first
        if use_cache and asset in self._trend_cache:
            trend, cache_time = self._trend_cache[asset]
            if time.time() - cache_time < self._trend_cache_ttl:
                return trend

        async with self._async_lock:
            with self._lock:
                # Get recent history
                since_timestamp = time.time() - (analysis_hours * 3600)
                entries = self.get_asset_history(asset, since_timestamp=since_timestamp)

                if len(entries) < 2:
                    return None

                # Calculate trend metrics
                balances = [entry.balance for entry in entries]
                timestamps = [entry.timestamp for entry in entries]

                # Basic statistics
                avg_balance = sum(balances) / len(balances)
                min_balance = min(balances)
                max_balance = max(balances)
                total_change = balances[0] - balances[-1]  # Most recent - oldest

                # Trend direction and strength
                trend_direction, trend_strength = self._calculate_trend_direction(balances, timestamps)

                # Volatility score
                volatility_score = self._calculate_volatility(balances)

                # Count significant changes
                change_count = len([e for e in entries if e.balance_change and abs(e.balance_change) > avg_balance * safe_decimal("0.01")])

                trend = BalanceTrend(
                    asset=asset,
                    trend_direction=trend_direction,
                    trend_strength=trend_strength,
                    average_balance=avg_balance,
                    min_balance=min_balance,
                    max_balance=max_balance,
                    total_change=total_change,
                    change_count=change_count,
                    analysis_period_hours=analysis_hours,
                    volatility_score=volatility_score
                )

                # Cache the result
                self._trend_cache[asset] = (trend, time.time())

                return trend

    def _calculate_trend_direction(self, balances: List[Decimal], timestamps: List[float]) -> Tuple[str, float]:
        """Calculate trend direction and strength using linear regression"""
        if len(balances) < 2:
            return 'stable', 0.0

        try:
            # Simple linear regression
            n = len(balances)
            x_vals = list(range(n))
            y_vals = [float(b) for b in balances]

            # Calculate slope
            x_mean = sum(x_vals) / n
            y_mean = sum(y_vals) / n

            numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
            denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

            if denominator == 0:
                return 'stable', 0.0

            slope = numerator / denominator

            # Calculate R-squared for strength
            y_pred = [x * slope + (y_mean - x_mean * slope) for x in x_vals]
            ss_res = sum((y_vals[i] - y_pred[i]) ** 2 for i in range(n))
            ss_tot = sum((y_vals[i] - y_mean) ** 2 for i in range(n))

            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            strength = max(0.0, min(1.0, r_squared))

            # Determine direction
            if abs(slope) < 0.001:  # Very small slope
                direction = 'stable'
            elif slope > 0:
                direction = 'increasing'
            else:
                direction = 'decreasing'

            # Check for high volatility
            if self._calculate_volatility(balances) > 0.5:
                direction = 'volatile'

            return direction, strength

        except Exception as e:
            logger.warning(f"[BALANCE_HISTORY] Trend calculation error for {balances[0] if balances else 'unknown'}: {e}")
            return 'stable', 0.0

    def _calculate_volatility(self, balances: List[Decimal]) -> float:
        """Calculate volatility score (0.0 to 1.0)"""
        if len(balances) < 2:
            return 0.0

        try:
            # Calculate coefficient of variation
            balance_floats = [float(b) for b in balances]
            mean_balance = sum(balance_floats) / len(balance_floats)

            if mean_balance == 0:
                return 0.0

            variance = sum((b - mean_balance) ** 2 for b in balance_floats) / len(balance_floats)
            std_dev = variance ** 0.5

            coefficient_of_variation = std_dev / mean_balance

            # Normalize to 0-1 range (cap at 100% CV)
            return min(1.0, coefficient_of_variation)

        except Exception as e:
            logger.warning(f"[BALANCE_HISTORY] Volatility calculation error: {e}")
            return 0.0

    async def _cleanup_loop(self):
        """Background cleanup task to remove old entries"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)

                if not self._running:
                    break

                await self._cleanup_old_entries()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[BALANCE_HISTORY] Cleanup error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def _cleanup_old_entries(self):
        """Remove entries older than retention period"""
        async with self._async_lock:
            with self._lock:
                cutoff_time = time.time() - (self.retention_hours * 3600)
                removed_count = 0

                for asset, entries in self._history.items():
                    # Convert deque to list for easier manipulation
                    entries_list = list(entries)

                    # Filter out old entries
                    new_entries = [entry for entry in entries_list if entry.timestamp >= cutoff_time]
                    removed_this_asset = len(entries_list) - len(new_entries)

                    if removed_this_asset > 0:
                        # Replace deque contents
                        entries.clear()
                        entries.extend(new_entries)
                        removed_count += removed_this_asset

                if removed_count > 0:
                    self._stats['entries_removed'] += removed_count
                    self._stats['total_entries'] -= removed_count
                    logger.debug(f"[BALANCE_HISTORY] Cleaned up {removed_count} old entries")

                self._stats['cleanup_runs'] += 1

    async def _save_to_file(self):
        """Save history to persistence file"""
        if not self.persistence_file:
            return

        try:
            async with self._async_lock:
                with self._lock:
                    # Prepare data for serialization
                    data = {
                        'metadata': {
                            'version': '1.0',
                            'timestamp': time.time(),
                            'retention_hours': self.retention_hours,
                            'max_entries_per_asset': self.max_entries_per_asset
                        },
                        'statistics': dict(self._stats),
                        'current_balances': {
                            asset: entry.to_dict()
                            for asset, entry in self._current_balances.items()
                        },
                        'history': {
                            asset: [entry.to_dict() for entry in entries]
                            for asset, entries in self._history.items()
                        }
                    }

                    # Write to file
                    path = Path(self.persistence_file)
                    path.parent.mkdir(parents=True, exist_ok=True)

                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, default=str)

                    self._stats['persistence_saves'] += 1
                    logger.info(f"[BALANCE_HISTORY] Saved {self._stats['total_entries']} entries to {self.persistence_file}")

        except Exception as e:
            logger.error(f"[BALANCE_HISTORY] Failed to save to file: {e}")

    async def _load_from_file(self):
        """Load history from persistence file"""
        if not self.persistence_file or not Path(self.persistence_file).exists():
            return

        try:
            async with self._async_lock:
                with self._lock:
                    with open(self.persistence_file, encoding='utf-8') as f:
                        data = json.load(f)

                    # Load statistics
                    if 'statistics' in data:
                        self._stats.update(data['statistics'])

                    # Load current balances
                    if 'current_balances' in data:
                        self._current_balances = {
                            asset: BalanceHistoryEntry.from_dict(entry_data)
                            for asset, entry_data in data['current_balances'].items()
                        }

                    # Load history
                    if 'history' in data:
                        for asset, entries_data in data['history'].items():
                            entries = deque(maxlen=self.max_entries_per_asset)
                            for entry_data in entries_data:
                                entries.append(BalanceHistoryEntry.from_dict(entry_data))
                            self._history[asset] = entries

                    self._stats['persistence_loads'] += 1
                    logger.info(f"[BALANCE_HISTORY] Loaded {self._stats['total_entries']} entries from {self.persistence_file}")

        except Exception as e:
            logger.error(f"[BALANCE_HISTORY] Failed to load from file: {e}")

    def register_change_callback(self, callback: Callable):
        """Register callback for balance changes"""
        self._change_callbacks.append(callback)
        logger.debug("[BALANCE_HISTORY] Registered change callback")

    def unregister_change_callback(self, callback: Callable):
        """Remove change callback"""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
            logger.debug("[BALANCE_HISTORY] Unregistered change callback")

    async def _call_change_callbacks(self, entry: BalanceHistoryEntry):
        """Call registered change callbacks"""
        for callback in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(entry)
                else:
                    callback(entry)
            except Exception as e:
                logger.error(f"[BALANCE_HISTORY] Change callback error: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get history statistics"""
        with self._lock:
            return {
                'total_assets': len(self._history),
                'total_entries': self._stats['total_entries'],
                'retention_hours': self.retention_hours,
                'max_entries_per_asset': self.max_entries_per_asset,
                'statistics': dict(self._stats),
                'asset_entry_counts': {
                    asset: len(entries) for asset, entries in self._history.items()
                },
                'memory_usage_estimate': self._estimate_memory_usage(),
                'trend_cache_size': len(self._trend_cache)
            }

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes"""
        with self._lock:
            # Rough estimate: each entry ~800 bytes
            total_entries = sum(len(entries) for entries in self._history.values())
            return total_entries * 800

    # Context manager support
    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
