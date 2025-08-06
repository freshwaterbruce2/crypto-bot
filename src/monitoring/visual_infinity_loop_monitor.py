"""
Visual Infinity Loop Monitor - Real-time Trading Cycle Visualization
Provides real-time monitoring of the autonomous trading infinity loop

Features:
- Visual cycle tracking: Buy Low -> Sell High -> Profit -> Reinvest -> Repeat
- Anti-circular loop detection and visualization
- Performance metrics dashboard
- Self-healing status monitoring
- Portfolio allocation visualization
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class TradingCycle:
    """Represents one complete trading cycle"""
    cycle_id: str
    start_time: float
    end_time: Optional[float]
    entry_asset: str
    entry_amount: float
    entry_price: float
    exit_asset: str
    exit_amount: float
    exit_price: float
    profit_usd: float
    profit_percentage: float
    cycle_duration: float
    status: str  # 'active', 'completed', 'failed'

class VisualInfinityLoopMonitor:
    """
    Real-time monitoring system for the autonomous trading infinity loop
    Tracks and visualizes the continuous Buy Low -> Sell High -> Profit -> Reinvest cycle
    """

    def __init__(self, reallocation_engine=None):
        """Initialize the visual monitor"""
        self.reallocation_engine = reallocation_engine
        self.active_cycles: Dict[str, TradingCycle] = {}
        self.completed_cycles: List[TradingCycle] = []
        self.cycle_counter = 0

        # Performance tracking
        self.infinity_metrics = {
            'total_cycles': 0,
            'successful_cycles': 0,
            'failed_cycles': 0,
            'total_profit': 0.0,
            'avg_cycle_duration': 0.0,
            'avg_profit_per_cycle': 0.0,
            'best_cycle_profit': 0.0,
            'worst_cycle_loss': 0.0,
            'current_streak': 0,
            'longest_streak': 0,
            'cycles_per_hour': 0.0,
            'infinity_loop_health': 'HEALTHY'
        }

        # Visual states for monitoring
        self.visual_state = {
            'current_phase': 'SCANNING',  # SCANNING, BUYING, HOLDING, SELLING, REINVESTING
            'portfolio_allocation': {},
            'top_opportunities': [],
            'active_trades': 0,
            'circular_locks': 0,
            'emergency_mode': False,
            'last_profit': 0.0,
            'profit_trend': 'NEUTRAL'
        }

        # Anti-circular monitoring
        self.circular_detection = {
            'blocked_trades': 0,
            'circular_attempts': [],
            'last_circular_block': 0,
            'prevention_saves': 0
        }

        logger.info("[INFINITY_MONITOR] Visual infinity loop monitor initialized")

    def start_new_cycle(self, entry_asset: str, entry_amount: float, entry_price: float) -> str:
        """Start tracking a new trading cycle"""
        try:
            self.cycle_counter += 1
            cycle_id = f"CYCLE_{self.cycle_counter}_{int(time.time())}"

            cycle = TradingCycle(
                cycle_id=cycle_id,
                start_time=time.time(),
                end_time=None,
                entry_asset=entry_asset,
                entry_amount=entry_amount,
                entry_price=entry_price,
                exit_asset='',
                exit_amount=0.0,
                exit_price=0.0,
                profit_usd=0.0,
                profit_percentage=0.0,
                cycle_duration=0.0,
                status='active'
            )

            self.active_cycles[cycle_id] = cycle
            self.visual_state['current_phase'] = 'BUYING'

            logger.info(f"[INFINITY_CYCLE] Started new cycle {cycle_id}: {entry_amount:.6f} {entry_asset} @ ${entry_price:.2f}")
            return cycle_id

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error starting new cycle: {e}")
            return ""

    def complete_cycle(self, cycle_id: str, exit_asset: str, exit_amount: float, exit_price: float) -> None:
        """Complete a trading cycle and calculate profits"""
        try:
            if cycle_id not in self.active_cycles:
                logger.warning(f"[INFINITY_MONITOR] Cycle {cycle_id} not found in active cycles")
                return

            cycle = self.active_cycles[cycle_id]
            cycle.end_time = time.time()
            cycle.exit_asset = exit_asset
            cycle.exit_amount = exit_amount
            cycle.exit_price = exit_price
            cycle.cycle_duration = cycle.end_time - cycle.start_time

            # Calculate profit
            entry_value = cycle.entry_amount * cycle.entry_price
            exit_value = exit_amount * exit_price
            cycle.profit_usd = exit_value - entry_value
            cycle.profit_percentage = (cycle.profit_usd / entry_value) * 100 if entry_value > 0 else 0

            # Determine cycle status
            if cycle.profit_usd > 0:
                cycle.status = 'completed'
                self.infinity_metrics['successful_cycles'] += 1
                self.infinity_metrics['current_streak'] += 1
                self.infinity_metrics['longest_streak'] = max(
                    self.infinity_metrics['longest_streak'],
                    self.infinity_metrics['current_streak']
                )
            else:
                cycle.status = 'failed'
                self.infinity_metrics['failed_cycles'] += 1
                self.infinity_metrics['current_streak'] = 0

            # Update metrics
            self.infinity_metrics['total_cycles'] += 1
            self.infinity_metrics['total_profit'] += cycle.profit_usd
            self.infinity_metrics['best_cycle_profit'] = max(
                self.infinity_metrics['best_cycle_profit'],
                cycle.profit_usd
            )
            self.infinity_metrics['worst_cycle_loss'] = min(
                self.infinity_metrics['worst_cycle_loss'],
                cycle.profit_usd
            )

            # Calculate averages
            if self.infinity_metrics['total_cycles'] > 0:
                self.infinity_metrics['avg_profit_per_cycle'] = (
                    self.infinity_metrics['total_profit'] / self.infinity_metrics['total_cycles']
                )

            # Move to completed cycles
            self.completed_cycles.append(cycle)
            del self.active_cycles[cycle_id]

            # Update visual state
            self.visual_state['last_profit'] = cycle.profit_usd
            self.visual_state['profit_trend'] = 'UP' if cycle.profit_usd > 0 else 'DOWN'
            self.visual_state['current_phase'] = 'REINVESTING' if cycle.profit_usd > 0 else 'SCANNING'

            # Keep only last 1000 completed cycles
            if len(self.completed_cycles) > 1000:
                self.completed_cycles = self.completed_cycles[-1000:]

            logger.info(f"[INFINITY_CYCLE] Completed cycle {cycle_id}: "
                       f"Profit: ${cycle.profit_usd:.2f} ({cycle.profit_percentage:.2f}%) "
                       f"Duration: {cycle.cycle_duration:.1f}s")

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error completing cycle: {e}")

    def record_circular_block(self, from_asset: str, to_asset: str, reason: str) -> None:
        """Record when a circular trade was blocked"""
        try:
            block_record = {
                'timestamp': time.time(),
                'from_asset': from_asset,
                'to_asset': to_asset,
                'reason': reason,
                'datetime': datetime.now().isoformat()
            }

            self.circular_detection['circular_attempts'].append(block_record)
            self.circular_detection['blocked_trades'] += 1
            self.circular_detection['last_circular_block'] = time.time()
            self.circular_detection['prevention_saves'] += 1

            # Keep only last 100 blocks
            if len(self.circular_detection['circular_attempts']) > 100:
                self.circular_detection['circular_attempts'] = self.circular_detection['circular_attempts'][-100:]

            logger.info(f"[ANTI_CIRCULAR] Blocked circular trade: {from_asset} -> {to_asset} ({reason})")

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error recording circular block: {e}")

    def update_visual_state(self, portfolio_data: Dict, opportunities: List, emergency_mode: bool = False) -> None:
        """Update the current visual state of the infinity loop"""
        try:
            # Update portfolio allocation
            total_value = sum(portfolio_data.values())
            if total_value > 0:
                self.visual_state['portfolio_allocation'] = {
                    asset: (value / total_value * 100)
                    for asset, value in portfolio_data.items()
                    if value > 0.01  # Filter dust
                }

            # Update opportunities
            self.visual_state['top_opportunities'] = opportunities[:5]  # Top 5

            # Update status
            self.visual_state['active_trades'] = len(self.active_cycles)
            self.visual_state['emergency_mode'] = emergency_mode

            if self.reallocation_engine:
                self.visual_state['circular_locks'] = len(self.reallocation_engine.circular_lock)

            # Update metrics
            self._update_performance_metrics()
            self._update_health_status()

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error updating visual state: {e}")

    def _update_performance_metrics(self) -> None:
        """Update performance metrics for the infinity loop"""
        try:
            current_time = time.time()

            # Calculate cycles per hour
            if len(self.completed_cycles) >= 2:
                recent_cycles = [c for c in self.completed_cycles if current_time - c.end_time < 3600]
                self.infinity_metrics['cycles_per_hour'] = len(recent_cycles)

            # Calculate average cycle duration
            if self.completed_cycles:
                total_duration = sum(c.cycle_duration for c in self.completed_cycles[-20:])  # Last 20 cycles
                self.infinity_metrics['avg_cycle_duration'] = total_duration / min(20, len(self.completed_cycles))

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error updating performance metrics: {e}")

    def _update_health_status(self) -> None:
        """Update the overall health status of the infinity loop"""
        try:
            health_score = 100

            # Check emergency mode
            if self.visual_state['emergency_mode']:
                health_score -= 50

            # Check recent performance
            if len(self.completed_cycles) >= 5:
                recent_cycles = self.completed_cycles[-5:]
                recent_profits = [c.profit_usd for c in recent_cycles]

                if all(p < 0 for p in recent_profits):
                    health_score -= 30  # All recent trades lost money
                elif sum(recent_profits) < 0:
                    health_score -= 15  # Net loss in recent trades

            # Check circular blocks
            recent_blocks = sum(1 for attempt in self.circular_detection['circular_attempts']
                              if time.time() - attempt['timestamp'] < 300)  # Last 5 minutes
            if recent_blocks > 5:
                health_score -= 20

            # Check activity level
            if self.infinity_metrics['cycles_per_hour'] < 1:
                health_score -= 10

            # Determine health status
            if health_score >= 90:
                self.infinity_metrics['infinity_loop_health'] = 'EXCELLENT'
            elif health_score >= 75:
                self.infinity_metrics['infinity_loop_health'] = 'HEALTHY'
            elif health_score >= 50:
                self.infinity_metrics['infinity_loop_health'] = 'WARNING'
            elif health_score >= 25:
                self.infinity_metrics['infinity_loop_health'] = 'DEGRADED'
            else:
                self.infinity_metrics['infinity_loop_health'] = 'CRITICAL'

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error updating health status: {e}")

    def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data for visualization"""
        try:
            return {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'infinity_metrics': self.infinity_metrics.copy(),
                'visual_state': self.visual_state.copy(),
                'circular_detection': self.circular_detection.copy(),
                'active_cycles': [asdict(cycle) for cycle in self.active_cycles.values()],
                'recent_cycles': [asdict(cycle) for cycle in self.completed_cycles[-10:]],
                'performance_summary': {
                    'total_profit': self.infinity_metrics['total_profit'],
                    'success_rate': (
                        self.infinity_metrics['successful_cycles'] / max(1, self.infinity_metrics['total_cycles']) * 100
                    ),
                    'avg_profit_per_cycle': self.infinity_metrics['avg_profit_per_cycle'],
                    'current_streak': self.infinity_metrics['current_streak'],
                    'health_status': self.infinity_metrics['infinity_loop_health']
                }
            }

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error getting dashboard data: {e}")
            return {}

    def get_infinity_loop_status(self) -> str:
        """Get current infinity loop status as formatted string"""
        try:
            status_lines = [
                "=" * 60,
                "[SYNC] AUTONOMOUS TRADING INFINITY LOOP STATUS [SYNC]",
                "=" * 60,
                f"Health Status: {self.infinity_metrics['infinity_loop_health']}",
                f"Current Phase: {self.visual_state['current_phase']}",
                f"Active Cycles: {len(self.active_cycles)}",
                f"Total Profit: ${self.infinity_metrics['total_profit']:.2f}",
                f"Success Rate: {(self.infinity_metrics['successful_cycles'] / max(1, self.infinity_metrics['total_cycles']) * 100):.1f}%",
                f"Current Streak: {self.infinity_metrics['current_streak']} cycles",
                f"Cycles/Hour: {self.infinity_metrics['cycles_per_hour']:.1f}",
                "",
                "Portfolio Allocation:",
            ]

            for asset, percentage in self.visual_state['portfolio_allocation'].items():
                status_lines.append(f"  {asset}: {percentage:.1f}%")

            status_lines.extend([
                "",
                f"Anti-Circular Protection: {self.circular_detection['prevention_saves']} saves",
                f"Emergency Mode: {'ACTIVE' if self.visual_state['emergency_mode'] else 'STANDBY'}",
                "=" * 60
            ])

            return "\n".join(status_lines)

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error getting status: {e}")
            return "Error generating status"

    async def save_dashboard_to_file(self, filepath: str = "D:/trading_data/infinity_loop_dashboard.json") -> None:
        """Save dashboard data to file for external monitoring"""
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            dashboard_data = self.get_dashboard_data()

            with open(filepath, 'w') as f:
                json.dump(dashboard_data, f, indent=2, default=str)

            logger.debug(f"[INFINITY_MONITOR] Dashboard saved to {filepath}")

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error saving dashboard: {e}")

    def log_infinity_loop_summary(self) -> None:
        """Log a comprehensive summary of the infinity loop performance"""
        try:
            logger.info(self.get_infinity_loop_status())

            if self.completed_cycles:
                recent_cycle = self.completed_cycles[-1]
                logger.info(f"[LAST_CYCLE] {recent_cycle.entry_asset} -> {recent_cycle.exit_asset}: "
                           f"${recent_cycle.profit_usd:.2f} in {recent_cycle.cycle_duration:.1f}s")

        except Exception as e:
            logger.error(f"[INFINITY_MONITOR] Error logging summary: {e}")
