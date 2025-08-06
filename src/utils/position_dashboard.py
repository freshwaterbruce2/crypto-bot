"""
Position Dashboard Module
=========================
Real-time position tracking and visualization for the crypto trading bot.
Provides consolidated view of all open positions, P&L, and portfolio metrics.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.utils.decimal_precision_fix import safe_decimal

logger = logging.getLogger(__name__)


@dataclass
class PositionMetrics:
    """Metrics for a single position"""
    symbol: str
    entry_price: Decimal
    current_price: Decimal
    quantity: Decimal
    value_usd: Decimal
    pnl_usd: Decimal
    pnl_percent: float
    time_held: int  # seconds
    status: str = "active"
    last_update: datetime = field(default_factory=datetime.now)


class PositionDashboard:
    """
    Real-time position tracking and portfolio visualization.
    Integrates with balance manager and websocket for live updates.
    """

    def __init__(self, bot):
        """Initialize position dashboard with bot reference"""
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)

        # Position tracking
        self.positions: Dict[str, PositionMetrics] = {}
        self.position_history: List[Dict[str, Any]] = []

        # Portfolio metrics
        self.total_value = Decimal('0')
        self.total_pnl = Decimal('0')
        self.total_pnl_percent = 0.0

        # Update tracking
        self.last_update = datetime.now()
        self.update_interval = 5  # seconds
        self.update_task = None

        self.logger.info("[POSITION_DASHBOARD] Initialized")

    async def start(self):
        """Start position tracking"""
        self.logger.info("[POSITION_DASHBOARD] Starting position tracking...")

        # Initial position scan
        await self.scan_positions()

        # Start update loop
        self.update_task = asyncio.create_task(self._update_loop())

        self.logger.info("[POSITION_DASHBOARD] Position tracking started")

    async def stop(self):
        """Stop position tracking"""
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass

        self.logger.info("[POSITION_DASHBOARD] Position tracking stopped")

    async def scan_positions(self) -> Dict[str, PositionMetrics]:
        """Scan all current positions from balance manager"""
        try:
            if not hasattr(self.bot, 'balance_manager') or not self.bot.balance_manager:
                self.logger.warning("[POSITION_DASHBOARD] Balance manager not available")
                return {}

            # Get deployed positions
            deployed = await self.bot.balance_manager.get_deployed_capital()

            # Clear old positions
            self.positions.clear()

            # Process each deployed position
            for symbol, info in deployed.items():
                if symbol == 'USDT' or not info.get('amount', 0):
                    continue

                # Create position metrics
                metrics = PositionMetrics(
                    symbol=symbol,
                    entry_price=safe_decimal(info.get('average_price', '0')),
                    current_price=safe_decimal(info.get('current_price', '0')),
                    quantity=safe_decimal(info.get('amount', '0')),
                    value_usd=safe_decimal(info.get('value_usd', '0')),
                    pnl_usd=safe_decimal(info.get('pnl_usd', '0')),
                    pnl_percent=float(info.get('pnl_percent', 0)),
                    time_held=0  # Will be calculated from order history
                )

                self.positions[symbol] = metrics

            # Update portfolio totals
            await self._update_totals()

            self.logger.info(f"[POSITION_DASHBOARD] Scanned {len(self.positions)} positions")
            return self.positions

        except Exception as e:
            self.logger.error(f"[POSITION_DASHBOARD] Position scan error: {e}")
            return {}

    async def _update_loop(self):
        """Continuous position update loop"""
        while True:
            try:
                await asyncio.sleep(self.update_interval)

                # Update positions
                await self.update_positions()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"[POSITION_DASHBOARD] Update loop error: {e}")
                await asyncio.sleep(10)  # Wait longer on error

    async def update_positions(self):
        """Update all position metrics with latest prices"""
        try:
            # Get latest prices from websocket or exchange
            for symbol, position in self.positions.items():
                # Get current price
                current_price = await self._get_current_price(symbol)
                if current_price:
                    position.current_price = safe_decimal(current_price)

                    # Recalculate metrics
                    position.value_usd = position.quantity * position.current_price
                    position.pnl_usd = (position.current_price - position.entry_price) * position.quantity

                    if position.entry_price > 0:
                        position.pnl_percent = float((position.current_price - position.entry_price) / position.entry_price * 100)

                    # Update time held
                    position.time_held = int((datetime.now() - position.last_update).total_seconds())
                    position.last_update = datetime.now()

            # Update totals
            await self._update_totals()

            self.last_update = datetime.now()

        except Exception as e:
            self.logger.error(f"[POSITION_DASHBOARD] Position update error: {e}")

    async def _get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current price for symbol"""
        try:
            # Try websocket first
            if hasattr(self.bot, 'websocket_manager') and self.bot.websocket_manager:
                ticker_data = self.bot.websocket_manager.get_ticker_data(f"{symbol}/USDT")
                if ticker_data and 'last' in ticker_data:
                    return safe_decimal(ticker_data['last'])

            # Fallback to exchange
            if hasattr(self.bot, 'exchange') and self.bot.exchange:
                ticker = await self.bot.exchange.fetch_ticker(f"{symbol}/USDT")
                if ticker and 'last' in ticker:
                    return safe_decimal(ticker['last'])

            return None

        except Exception as e:
            self.logger.error(f"[POSITION_DASHBOARD] Price fetch error for {symbol}: {e}")
            return None

    async def _update_totals(self):
        """Update portfolio totals"""
        self.total_value = sum(p.value_usd for p in self.positions.values())
        self.total_pnl = sum(p.pnl_usd for p in self.positions.values())

        # Add liquid balance
        if hasattr(self.bot, 'balance_manager') and self.bot.balance_manager:
            liquid = await self.bot.balance_manager.get_liquid_capital()
            self.total_value += safe_decimal(liquid)

        # Calculate total P&L percentage
        if self.total_value > 0:
            self.total_pnl_percent = float(self.total_pnl / self.total_value * 100)

    def get_summary(self) -> Dict[str, Any]:
        """Get dashboard summary"""
        return {
            'positions_count': len(self.positions),
            'total_value': float(self.total_value),
            'total_pnl': float(self.total_pnl),
            'total_pnl_percent': self.total_pnl_percent,
            'last_update': self.last_update.isoformat(),
            'positions': {
                symbol: {
                    'entry_price': float(p.entry_price),
                    'current_price': float(p.current_price),
                    'quantity': float(p.quantity),
                    'value_usd': float(p.value_usd),
                    'pnl_usd': float(p.pnl_usd),
                    'pnl_percent': p.pnl_percent,
                    'time_held_minutes': p.time_held // 60,
                    'status': p.status
                }
                for symbol, p in self.positions.items()
            }
        }

    def display_dashboard(self):
        """Display formatted dashboard in logs"""
        summary = self.get_summary()

        self.logger.info("=" * 60)
        self.logger.info("POSITION DASHBOARD")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Portfolio Value: ${summary['total_value']:,.2f}")
        self.logger.info(f"Total P&L: ${summary['total_pnl']:,.2f} ({summary['total_pnl_percent']:+.2f}%)")
        self.logger.info(f"Active Positions: {summary['positions_count']}")
        self.logger.info("-" * 60)

        for symbol, pos in summary['positions'].items():
            pnl_sign = "+" if pos['pnl_percent'] >= 0 else ""
            self.logger.info(
                f"{symbol}: ${pos['value_usd']:,.2f} | "
                f"P&L: ${pos['pnl_usd']:,.2f} ({pnl_sign}{pos['pnl_percent']:.2f}%) | "
                f"Held: {pos['time_held_minutes']}m"
            )

        self.logger.info("=" * 60)

    async def add_position(self, symbol: str, entry_price: float, quantity: float):
        """Manually add a position (called after order execution)"""
        try:
            metrics = PositionMetrics(
                symbol=symbol,
                entry_price=safe_decimal(entry_price),
                current_price=safe_decimal(entry_price),  # Will be updated
                quantity=safe_decimal(quantity),
                value_usd=safe_decimal(entry_price * quantity),
                pnl_usd=Decimal('0'),
                pnl_percent=0.0,
                time_held=0
            )

            self.positions[symbol] = metrics
            self.logger.info(f"[POSITION_DASHBOARD] Added position: {symbol} @ ${entry_price}")

            # Update immediately
            await self.update_positions()

        except Exception as e:
            self.logger.error(f"[POSITION_DASHBOARD] Error adding position: {e}")

    async def remove_position(self, symbol: str):
        """Remove a position (called after sell order)"""
        if symbol in self.positions:
            # Archive to history
            pos = self.positions[symbol]
            self.position_history.append({
                'symbol': symbol,
                'entry_price': float(pos.entry_price),
                'exit_price': float(pos.current_price),
                'pnl': float(pos.pnl_usd),
                'pnl_percent': pos.pnl_percent,
                'time_held': pos.time_held,
                'closed_at': datetime.now().isoformat()
            })

            # Remove from active
            del self.positions[symbol]
            self.logger.info(f"[POSITION_DASHBOARD] Closed position: {symbol} | P&L: ${pos.pnl_usd:.2f}")

            # Update totals
            await self._update_totals()
