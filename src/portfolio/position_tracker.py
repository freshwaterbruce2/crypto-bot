"""
Position Tracker
================

Real-time position tracking with P&L calculation, entry/exit price management,
and comprehensive position lifecycle management.

Features:
- Real-time position tracking with entry/exit prices
- Unrealized and realized P&L calculation
- Position lifecycle management (OPEN, PARTIAL, CLOSED)
- Thread-safe operations for concurrent trading
- Historical position data persistence
- Integration with balance manager for accurate tracking
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Any, Dict, List, Optional, Union

from ..utils.decimal_precision_fix import safe_decimal

logger = logging.getLogger(__name__)


class PositionStatus(Enum):
    """Position status enumeration"""
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PositionType(Enum):
    """Position type enumeration"""
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    """Position data structure"""
    symbol: str
    position_id: str
    position_type: PositionType
    status: PositionStatus

    # Size information
    original_size: Decimal
    current_size: Decimal
    filled_size: Decimal

    # Price information
    entry_price: Decimal
    current_price: Decimal
    average_entry_price: Decimal

    # P&L information
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    realized_pnl_pct: Decimal

    # Cost basis
    cost_basis: Decimal
    current_value: Decimal

    # Timestamps
    created_at: float
    updated_at: float
    closed_at: Optional[float] = None

    # Strategy information
    strategy: Optional[str] = None
    tags: Optional[List[str]] = None

    # Trading information
    fees_paid: Decimal = safe_decimal("0")
    trades_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary"""
        data = asdict(self)

        # Convert Decimal and Enum values for JSON serialization
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
            elif isinstance(value, Enum):
                data[key] = value.value

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create position from dictionary"""
        # Convert string values back to enums
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = PositionStatus(data['status'])
        if 'position_type' in data and isinstance(data['position_type'], str):
            data['position_type'] = PositionType(data['position_type'])

        # Convert float values back to Decimal
        decimal_fields = [
            'original_size', 'current_size', 'filled_size',
            'entry_price', 'current_price', 'average_entry_price',
            'unrealized_pnl', 'realized_pnl', 'unrealized_pnl_pct', 'realized_pnl_pct',
            'cost_basis', 'current_value', 'fees_paid'
        ]

        for field in decimal_fields:
            if field in data:
                data[field] = safe_decimal(data[field])

        return cls(**data)

    def update_current_price(self, price: Union[float, Decimal]) -> bool:
        """
        Update current price and recalculate P&L
        
        Returns:
            True if price changed significantly
        """
        new_price = safe_decimal(price)
        price_changed = abs(new_price - self.current_price) > safe_decimal("0.000001")

        if price_changed:
            self.current_price = new_price
            self._recalculate_pnl()
            self.updated_at = time.time()

        return price_changed

    def add_fill(self, size: Union[float, Decimal], price: Union[float, Decimal],
                 fees: Union[float, Decimal] = 0) -> None:
        """Add a fill to the position"""
        fill_size = safe_decimal(size)
        fill_price = safe_decimal(price)
        fill_fees = safe_decimal(fees)

        # Update average entry price
        total_cost = (self.filled_size * self.average_entry_price) + (fill_size * fill_price)
        self.filled_size += fill_size
        self.average_entry_price = total_cost / self.filled_size if self.filled_size > 0 else fill_price

        # Update position size
        self.current_size = self.filled_size

        # Update fees
        self.fees_paid += fill_fees
        self.trades_count += 1

        # Update cost basis
        self.cost_basis = self.filled_size * self.average_entry_price + self.fees_paid

        # Update status
        if self.filled_size >= self.original_size:
            self.status = PositionStatus.OPEN
        else:
            self.status = PositionStatus.PARTIAL

        self._recalculate_pnl()
        self.updated_at = time.time()

    def close_partial(self, size: Union[float, Decimal], price: Union[float, Decimal],
                     fees: Union[float, Decimal] = 0) -> Decimal:
        """
        Close part of the position
        
        Returns:
            Realized P&L from the partial close
        """
        close_size = safe_decimal(size)
        close_price = safe_decimal(price)
        close_fees = safe_decimal(fees)

        if close_size > self.current_size:
            close_size = self.current_size

        # Calculate realized P&L for the closed portion
        if self.position_type == PositionType.LONG:
            realized_pnl = (close_price - self.average_entry_price) * close_size - close_fees
        else:  # SHORT
            realized_pnl = (self.average_entry_price - close_price) * close_size - close_fees

        # Update position
        self.current_size -= close_size
        self.realized_pnl += realized_pnl
        self.fees_paid += close_fees
        self.trades_count += 1

        # Update status
        if self.current_size <= safe_decimal("0.000001"):
            self.status = PositionStatus.CLOSED
            self.closed_at = time.time()
        else:
            self.status = PositionStatus.PARTIAL

        self._recalculate_pnl()
        self.updated_at = time.time()

        return realized_pnl

    def _recalculate_pnl(self) -> None:
        """Recalculate unrealized P&L based on current price"""
        if self.current_size <= 0:
            self.unrealized_pnl = safe_decimal("0")
            self.unrealized_pnl_pct = safe_decimal("0")
            self.current_value = safe_decimal("0")
            return

        # Calculate current value
        self.current_value = self.current_size * self.current_price

        # Calculate unrealized P&L
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (self.current_price - self.average_entry_price) * self.current_size
        else:  # SHORT
            self.unrealized_pnl = (self.average_entry_price - self.current_price) * self.current_size

        # Calculate P&L percentages
        if self.cost_basis > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / self.cost_basis) * 100

        if self.cost_basis > 0:
            self.realized_pnl_pct = (self.realized_pnl / self.cost_basis) * 100


class PositionTracker:
    """
    Real-time position tracking system
    """

    def __init__(self, balance_manager=None, data_path: str = "D:/trading_data"):
        """
        Initialize position tracker
        
        Args:
            balance_manager: Balance manager instance for integration
            data_path: Path for data persistence
        """
        self.balance_manager = balance_manager
        self.data_path = data_path

        # Position storage
        self._positions: Dict[str, Position] = {}
        self._closed_positions: List[Position] = []

        # Thread safety
        self._lock = RLock()
        self._async_lock = asyncio.Lock()

        # Configuration
        self.position_file = f"{data_path}/positions.json"
        self.closed_positions_file = f"{data_path}/closed_positions.json"

        # Statistics
        self._stats = {
            'total_positions': 0,
            'open_positions': 0,
            'closed_positions': 0,
            'total_realized_pnl': 0.0,
            'total_unrealized_pnl': 0.0,
            'total_fees_paid': 0.0,
            'winning_positions': 0,
            'losing_positions': 0,
            'last_update': 0.0
        }

        # Price update tracking
        self._price_callbacks: List[callable] = []
        self._last_price_updates: Dict[str, float] = {}

        logger.info("[POSITION_TRACKER] Initialized position tracking system")

    async def initialize(self) -> bool:
        """Initialize the position tracker"""
        try:
            async with self._async_lock:
                # Load existing positions
                await self._load_positions()
                await self._load_closed_positions()

                # Update statistics
                self._update_statistics()

                logger.info(f"[POSITION_TRACKER] Initialized with {len(self._positions)} open positions, "
                           f"{len(self._closed_positions)} closed positions")
                return True

        except Exception as e:
            logger.error(f"[POSITION_TRACKER] Initialization failed: {e}")
            return False

    async def create_position(self, symbol: str, position_type: PositionType,
                            size: Union[float, Decimal], entry_price: Union[float, Decimal],
                            strategy: str = None, tags: List[str] = None) -> Position:
        """
        Create a new position
        
        Args:
            symbol: Trading pair symbol
            position_type: LONG or SHORT
            size: Position size
            entry_price: Entry price
            strategy: Strategy name
            tags: Optional tags for categorization
            
        Returns:
            Created position
        """
        async with self._async_lock:
            position_id = f"{symbol}_{int(time.time() * 1000)}"

            position = Position(
                symbol=symbol,
                position_id=position_id,
                position_type=position_type,
                status=PositionStatus.PARTIAL,
                original_size=safe_decimal(size),
                current_size=safe_decimal("0"),
                filled_size=safe_decimal("0"),
                entry_price=safe_decimal(entry_price),
                current_price=safe_decimal(entry_price),
                average_entry_price=safe_decimal(entry_price),
                unrealized_pnl=safe_decimal("0"),
                realized_pnl=safe_decimal("0"),
                unrealized_pnl_pct=safe_decimal("0"),
                realized_pnl_pct=safe_decimal("0"),
                cost_basis=safe_decimal("0"),
                current_value=safe_decimal("0"),
                created_at=time.time(),
                updated_at=time.time(),
                strategy=strategy,
                tags=tags or []
            )

            self._positions[position_id] = position
            self._stats['total_positions'] += 1
            self._stats['open_positions'] += 1

            await self._save_positions()

            logger.info(f"[POSITION_TRACKER] Created {position_type.value} position {position_id} for {symbol}")
            return position

    async def update_position_price(self, symbol: str, price: Union[float, Decimal]) -> List[str]:
        """
        Update price for all positions of a symbol
        
        Returns:
            List of updated position IDs
        """
        updated_positions = []

        async with self._async_lock:
            for position_id, position in self._positions.items():
                if position.symbol == symbol and position.status != PositionStatus.CLOSED:
                    if position.update_current_price(price):
                        updated_positions.append(position_id)

            if updated_positions:
                self._update_statistics()
                await self._save_positions()

                # Track price update
                self._last_price_updates[symbol] = time.time()

        if updated_positions:
            logger.debug(f"[POSITION_TRACKER] Updated {len(updated_positions)} positions for {symbol} @ ${price}")

        return updated_positions

    async def add_fill_to_position(self, position_id: str, size: Union[float, Decimal],
                                  price: Union[float, Decimal], fees: Union[float, Decimal] = 0) -> bool:
        """Add a fill to an existing position"""
        if position_id not in self._positions:
            logger.warning(f"[POSITION_TRACKER] Position {position_id} not found")
            return False

        async with self._async_lock:
            position = self._positions[position_id]
            position.add_fill(size, price, fees)

            self._update_statistics()
            await self._save_positions()

            logger.info(f"[POSITION_TRACKER] Added fill to {position_id}: {size} @ ${price}")
            return True

    async def close_position_partial(self, position_id: str, size: Union[float, Decimal],
                                   price: Union[float, Decimal], fees: Union[float, Decimal] = 0) -> Optional[Decimal]:
        """Close part of a position"""
        if position_id not in self._positions:
            logger.warning(f"[POSITION_TRACKER] Position {position_id} not found")
            return None

        async with self._async_lock:
            position = self._positions[position_id]
            realized_pnl = position.close_partial(size, price, fees)

            # If position is fully closed, move to closed positions
            if position.status == PositionStatus.CLOSED:
                self._closed_positions.append(position)
                del self._positions[position_id]
                self._stats['open_positions'] -= 1
                self._stats['closed_positions'] += 1

                await self._save_closed_positions()

            self._update_statistics()
            await self._save_positions()

            logger.info(f"[POSITION_TRACKER] Closed partial {position_id}: {size} @ ${price}, "
                       f"realized P&L: ${realized_pnl}")

            return realized_pnl

    async def close_position_full(self, position_id: str, price: Union[float, Decimal],
                                 fees: Union[float, Decimal] = 0) -> Optional[Decimal]:
        """Close a position completely"""
        if position_id not in self._positions:
            logger.warning(f"[POSITION_TRACKER] Position {position_id} not found")
            return None

        position = self._positions[position_id]
        return await self.close_position_partial(position_id, position.current_size, price, fees)

    def get_position(self, position_id: str) -> Optional[Position]:
        """Get a specific position"""
        return self._positions.get(position_id)

    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Get all positions for a symbol"""
        return [pos for pos in self._positions.values() if pos.symbol == symbol]

    def get_all_open_positions(self) -> Dict[str, Position]:
        """Get all open positions"""
        return dict(self._positions)

    def get_closed_positions(self, symbol: str = None, limit: int = None) -> List[Position]:
        """Get closed positions with optional filters"""
        positions = self._closed_positions

        if symbol:
            positions = [pos for pos in positions if pos.symbol == symbol]

        if limit:
            positions = positions[-limit:]

        return positions

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary with P&L information"""
        with self._lock:
            total_value = safe_decimal("0")
            total_cost = safe_decimal("0")
            total_unrealized_pnl = safe_decimal("0")
            total_realized_pnl = safe_decimal("0")

            symbol_breakdown = {}

            for position in self._positions.values():
                if position.status != PositionStatus.CLOSED:
                    total_value += position.current_value
                    total_cost += position.cost_basis
                    total_unrealized_pnl += position.unrealized_pnl

                    if position.symbol not in symbol_breakdown:
                        symbol_breakdown[position.symbol] = {
                            'positions': 0,
                            'total_size': safe_decimal("0"),
                            'total_value': safe_decimal("0"),
                            'total_pnl': safe_decimal("0"),
                            'avg_entry_price': safe_decimal("0"),
                            'current_price': position.current_price
                        }

                    breakdown = symbol_breakdown[position.symbol]
                    breakdown['positions'] += 1
                    breakdown['total_size'] += position.current_size
                    breakdown['total_value'] += position.current_value
                    breakdown['total_pnl'] += position.unrealized_pnl

            # Calculate realized P&L from closed positions
            for position in self._closed_positions:
                total_realized_pnl += position.realized_pnl

            # Calculate overall P&L percentage
            total_pnl_pct = safe_decimal("0")
            if total_cost > 0:
                total_pnl_pct = ((total_unrealized_pnl + total_realized_pnl) / total_cost) * 100

            return {
                'total_positions': len(self._positions),
                'total_value': float(total_value),
                'total_cost': float(total_cost),
                'total_unrealized_pnl': float(total_unrealized_pnl),
                'total_realized_pnl': float(total_realized_pnl),
                'total_pnl': float(total_unrealized_pnl + total_realized_pnl),
                'total_pnl_pct': float(total_pnl_pct),
                'symbol_breakdown': {
                    symbol: {
                        'positions': data['positions'],
                        'total_size': float(data['total_size']),
                        'total_value': float(data['total_value']),
                        'total_pnl': float(data['total_pnl']),
                        'current_price': float(data['current_price'])
                    }
                    for symbol, data in symbol_breakdown.items()
                },
                'statistics': dict(self._stats)
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics"""
        return dict(self._stats)

    def _update_statistics(self) -> None:
        """Update internal statistics"""
        total_unrealized_pnl = safe_decimal("0")
        total_realized_pnl = safe_decimal("0")
        total_fees = safe_decimal("0")
        winning_positions = 0
        losing_positions = 0

        # Open positions
        for position in self._positions.values():
            total_unrealized_pnl += position.unrealized_pnl
            total_fees += position.fees_paid

        # Closed positions
        for position in self._closed_positions:
            total_realized_pnl += position.realized_pnl
            total_fees += position.fees_paid

            if position.realized_pnl > 0:
                winning_positions += 1
            elif position.realized_pnl < 0:
                losing_positions += 1

        self._stats.update({
            'open_positions': len(self._positions),
            'closed_positions': len(self._closed_positions),
            'total_unrealized_pnl': float(total_unrealized_pnl),
            'total_realized_pnl': float(total_realized_pnl),
            'total_fees_paid': float(total_fees),
            'winning_positions': winning_positions,
            'losing_positions': losing_positions,
            'last_update': time.time()
        })

    async def _load_positions(self) -> None:
        """Load positions from file"""
        try:
            with open(self.position_file) as f:
                data = json.load(f)

            for position_data in data:
                position = Position.from_dict(position_data)
                self._positions[position.position_id] = position

            logger.debug(f"[POSITION_TRACKER] Loaded {len(self._positions)} positions")

        except FileNotFoundError:
            logger.info("[POSITION_TRACKER] No existing positions file found")
        except Exception as e:
            logger.error(f"[POSITION_TRACKER] Error loading positions: {e}")

    async def _save_positions(self) -> None:
        """Save positions to file"""
        try:
            data = [pos.to_dict() for pos in self._positions.values()]

            with open(self.position_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"[POSITION_TRACKER] Error saving positions: {e}")

    async def _load_closed_positions(self) -> None:
        """Load closed positions from file"""
        try:
            with open(self.closed_positions_file) as f:
                data = json.load(f)

            self._closed_positions = [Position.from_dict(pos_data) for pos_data in data]

            logger.debug(f"[POSITION_TRACKER] Loaded {len(self._closed_positions)} closed positions")

        except FileNotFoundError:
            logger.info("[POSITION_TRACKER] No existing closed positions file found")
        except Exception as e:
            logger.error(f"[POSITION_TRACKER] Error loading closed positions: {e}")

    async def _save_closed_positions(self) -> None:
        """Save closed positions to file"""
        try:
            data = [pos.to_dict() for pos in self._closed_positions]

            with open(self.closed_positions_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"[POSITION_TRACKER] Error saving closed positions: {e}")

    def register_price_callback(self, callback: callable) -> None:
        """Register callback for price updates"""
        self._price_callbacks.append(callback)

    async def cleanup_old_closed_positions(self, days_old: int = 30) -> int:
        """Clean up old closed positions"""
        cutoff_time = time.time() - (days_old * 24 * 3600)

        original_count = len(self._closed_positions)
        self._closed_positions = [
            pos for pos in self._closed_positions
            if pos.closed_at and pos.closed_at > cutoff_time
        ]

        cleaned_count = original_count - len(self._closed_positions)

        if cleaned_count > 0:
            await self._save_closed_positions()
            logger.info(f"[POSITION_TRACKER] Cleaned up {cleaned_count} old closed positions")

        return cleaned_count
