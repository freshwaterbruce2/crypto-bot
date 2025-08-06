"""
High-Frequency Trading Controller
=================================

Manages high-frequency micro-scalping operations for fee-free trading.
Targets 50-100+ trades per day with ultra-fast execution.

Features:
- Multi-threaded signal processing
- Queue-based order management
- Real-time performance monitoring
- Automatic throttling
- Parallel execution across multiple pairs
"""

import asyncio
import logging
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """High-frequency trading signal"""
    symbol: str
    side: str  # 'buy' or 'sell'
    confidence: float
    profit_target: float
    stop_loss: float
    timestamp: float
    metadata: Dict[str, Any]
    priority: int = 0  # Higher priority for better opportunities


@dataclass
class ExecutionResult:
    """Result of trade execution"""
    signal: TradingSignal
    success: bool
    order_id: Optional[str]
    execution_time: float
    error: Optional[str] = None


class HFTController:
    """High-frequency trading controller for micro-scalping"""

    def __init__(self, bot, config: Dict[str, Any]):
        """Initialize HFT controller"""
        self.bot = bot
        self.config = config

        # HFT parameters
        self.target_trades_per_hour = 8  # 8 trades/hour = ~100/day with 10 pairs
        self.max_concurrent_positions = config.get('fee_free_scalping', {}).get('max_concurrent_positions', 10)
        self.max_signals_per_scan = 20
        self.execution_timeout = 0.5  # 500ms max execution time

        # Performance tracking
        self.trades_last_hour = deque(maxlen=200)
        self.execution_times = deque(maxlen=100)
        self.signals_processed = 0
        self.signals_executed = 0

        # Signal queue with priority
        self.signal_queue = asyncio.PriorityQueue(maxsize=50)
        self.active_positions: Set[str] = set()
        self.position_entry_times: Dict[str, float] = {}

        # Execution control
        self.is_running = False
        self.execution_tasks = []
        self.last_execution_time = {}  # Per-symbol cooldown
        self.min_execution_interval = 10  # 10 seconds between trades on same symbol

        # Multi-threading for signal processing
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Performance metrics
        self.metrics = {
            'signals_per_minute': 0,
            'trades_per_hour': 0,
            'avg_execution_time': 0,
            'success_rate': 0,
            'queue_depth': 0
        }

        logger.info(f"[HFT_CONTROLLER] Initialized - Target: {self.target_trades_per_hour} trades/hour")

    async def start(self):
        """Start HFT controller"""
        if self.is_running:
            logger.warning("[HFT_CONTROLLER] Already running")
            return

        self.is_running = True

        # Start execution workers
        for i in range(3):  # 3 parallel execution workers
            task = asyncio.create_task(self._execution_worker(i))
            self.execution_tasks.append(task)

        # Start performance monitor
        asyncio.create_task(self._monitor_performance())

        # Start position cycler
        asyncio.create_task(self._position_cycle_monitor())

        logger.info("[HFT_CONTROLLER] Started with 3 execution workers")

    async def stop(self):
        """Stop HFT controller"""
        self.is_running = False

        # Cancel all tasks
        for task in self.execution_tasks:
            task.cancel()

        # Shutdown executor
        self.executor.shutdown(wait=False)

        logger.info("[HFT_CONTROLLER] Stopped")

    async def process_signals(self, signals: List[Dict[str, Any]]):
        """Process incoming signals for high-frequency execution"""
        try:
            self.signals_processed += len(signals)

            # Filter and prioritize signals
            prioritized_signals = await self._prioritize_signals(signals)

            # Add to execution queue
            added = 0
            for priority, signal in prioritized_signals:
                if added >= self.max_signals_per_scan:
                    break

                # Check if we can trade this symbol
                if await self._can_trade_symbol(signal.symbol):
                    try:
                        # Use negative priority for min-heap (higher priority = lower number)
                        await asyncio.wait_for(
                            self.signal_queue.put((-priority, signal)),
                            timeout=0.1
                        )
                        added += 1
                    except asyncio.TimeoutError:
                        logger.debug("[HFT_CONTROLLER] Queue full, skipping signal")
                        break

            if added > 0:
                logger.info(f"[HFT_CONTROLLER] Queued {added} high-priority signals")

        except Exception as e:
            logger.error(f"[HFT_CONTROLLER] Error processing signals: {e}")

    async def _prioritize_signals(self, signals: List[Dict[str, Any]]) -> List[tuple]:
        """Prioritize signals for execution"""
        prioritized = []

        for signal_data in signals:
            # Convert to TradingSignal
            signal = TradingSignal(
                symbol=signal_data['symbol'],
                side=signal_data.get('side', 'buy'),
                confidence=signal_data.get('confidence', 0.5),
                profit_target=signal_data.get('profit_target', 0.002),  # 0.2% default
                stop_loss=signal_data.get('stop_loss', 0.001),  # 0.1% default
                timestamp=time.time(),
                metadata=signal_data.get('metadata', {})
            )

            # Calculate priority score
            priority = self._calculate_priority(signal)
            signal.priority = priority

            prioritized.append((priority, signal))

        # Sort by priority (highest first)
        prioritized.sort(key=lambda x: x[0], reverse=True)

        return prioritized

    def _calculate_priority(self, signal: TradingSignal) -> float:
        """Calculate signal priority for execution order"""
        priority = 0.0

        # Base priority from confidence
        priority += signal.confidence * 50

        # Bonus for higher profit targets
        if signal.profit_target >= 0.003:  # 0.3%+
            priority += 20
        elif signal.profit_target >= 0.002:  # 0.2%+
            priority += 10

        # Bonus for tight stops (good risk/reward)
        if signal.stop_loss <= 0.0005:  # 0.05% stop
            priority += 15

        # Momentum bonus from metadata
        momentum = signal.metadata.get('momentum', 0)
        priority += abs(momentum) * 100

        # Volume spike bonus
        volume_spike = signal.metadata.get('volume_spike', 1.0)
        if volume_spike > 2.0:
            priority += 25
        elif volume_spike > 1.5:
            priority += 10

        # Spread penalty (prefer tighter spreads)
        spread = signal.metadata.get('spread', 0)
        if spread > 0.001:  # >0.1% spread
            priority -= 20

        return priority

    async def _can_trade_symbol(self, symbol: str) -> bool:
        """Check if we can trade this symbol"""
        # Check position limit
        if len(self.active_positions) >= self.max_concurrent_positions:
            if symbol not in self.active_positions:
                return False

        # Check cooldown
        last_trade = self.last_execution_time.get(symbol, 0)
        if time.time() - last_trade < self.min_execution_interval:
            return False

        # Check if we have fresh data
        if hasattr(self.bot, 'websocket_manager'):
            ws = self.bot.websocket_manager
            if not ws.has_fresh_data(symbol, max_age=2.0):
                return False

        return True

    async def _execution_worker(self, worker_id: int):
        """Worker that executes trades from the queue"""
        logger.info(f"[HFT_WORKER_{worker_id}] Started")

        while self.is_running:
            try:
                # Get signal from queue with timeout
                priority, signal = await asyncio.wait_for(
                    self.signal_queue.get(),
                    timeout=1.0
                )

                # Execute the trade
                start_time = time.time()
                result = await self._execute_signal(signal)
                execution_time = time.time() - start_time

                # Track execution time
                self.execution_times.append(execution_time)

                # Log result
                if result.success:
                    self.signals_executed += 1
                    self.trades_last_hour.append(time.time())
                    logger.info(
                        f"[HFT_WORKER_{worker_id}] Executed {signal.symbol} "
                        f"{signal.side} in {execution_time:.3f}s"
                    )
                else:
                    logger.warning(
                        f"[HFT_WORKER_{worker_id}] Failed {signal.symbol}: {result.error}"
                    )

            except asyncio.TimeoutError:
                # No signals in queue
                continue
            except Exception as e:
                logger.error(f"[HFT_WORKER_{worker_id}] Error: {e}")
                await asyncio.sleep(0.1)

    async def _execute_signal(self, signal: TradingSignal) -> ExecutionResult:
        """Execute a trading signal"""
        try:
            # Double-check we can still trade
            if not await self._can_trade_symbol(signal.symbol):
                return ExecutionResult(
                    signal=signal,
                    success=False,
                    order_id=None,
                    execution_time=0,
                    error="Cannot trade symbol (limit/cooldown)"
                )

            # Get position size
            position_size = await self._calculate_position_size(signal)
            if position_size < self.config.get('min_order_size_usdt', 2.0):
                return ExecutionResult(
                    signal=signal,
                    success=False,
                    order_id=None,
                    execution_time=0,
                    error="Position size too small"
                )

            # Execute with timeout
            start_time = time.time()

            # Place market order through bot
            order_result = await asyncio.wait_for(
                self.bot.place_order(
                    symbol=signal.symbol,
                    side=signal.side,
                    size=position_size,
                    order_type='market',
                    metadata={
                        'strategy': 'hft_micro_scalp',
                        'profit_target': signal.profit_target,
                        'stop_loss': signal.stop_loss,
                        'confidence': signal.confidence,
                        'priority': signal.priority
                    }
                ),
                timeout=self.execution_timeout
            )

            execution_time = time.time() - start_time

            if order_result and order_result.get('success'):
                # Track position
                self.active_positions.add(signal.symbol)
                self.position_entry_times[signal.symbol] = time.time()
                self.last_execution_time[signal.symbol] = time.time()

                return ExecutionResult(
                    signal=signal,
                    success=True,
                    order_id=order_result.get('order_id'),
                    execution_time=execution_time
                )
            else:
                error = order_result.get('error', 'Unknown error') if order_result else 'No response'
                return ExecutionResult(
                    signal=signal,
                    success=False,
                    order_id=None,
                    execution_time=execution_time,
                    error=error
                )

        except asyncio.TimeoutError:
            return ExecutionResult(
                signal=signal,
                success=False,
                order_id=None,
                execution_time=self.execution_timeout,
                error="Execution timeout"
            )
        except Exception as e:
            return ExecutionResult(
                signal=signal,
                success=False,
                order_id=None,
                execution_time=0,
                error=str(e)
            )

    async def _calculate_position_size(self, signal: TradingSignal) -> float:
        """Calculate position size for signal"""
        # Get available balance
        if hasattr(self.bot, 'balance_manager'):
            balance = await self.bot.balance_manager.get_balance_for_asset('USDT')
        else:
            balance = 100.0  # Default

        # Base position size
        base_size = balance * self.config.get('position_size_percentage', 0.7)

        # Adjust for number of positions
        if self.active_positions:
            # Reduce size when many positions open
            position_factor = max(0.5, 1.0 - len(self.active_positions) * 0.05)
            base_size *= position_factor

        # Adjust for confidence
        confidence_factor = 0.8 + (signal.confidence * 0.4)  # 0.8x to 1.2x
        base_size *= confidence_factor

        # Ensure within limits
        min_size = self.config.get('min_order_size_usdt', 2.0)
        max_size = self.config.get('max_order_size_usdt', 5.0)

        return max(min_size, min(base_size, max_size))

    async def _position_cycle_monitor(self):
        """Monitor and cycle old positions"""
        while self.is_running:
            try:
                current_time = time.time()
                max_hold_time = self.config.get('fee_free_scalping', {}).get('max_hold_time_seconds', 300)

                # Check each position
                positions_to_close = []
                for symbol, entry_time in list(self.position_entry_times.items()):
                    hold_time = current_time - entry_time

                    if hold_time > max_hold_time:
                        positions_to_close.append(symbol)
                        logger.info(f"[HFT_CONTROLLER] Position too old: {symbol} ({hold_time:.0f}s)")

                # Request position closes
                for symbol in positions_to_close:
                    if hasattr(self.bot, 'request_position_close'):
                        await self.bot.request_position_close(
                            symbol,
                            reason='max_hold_time_exceeded'
                        )

                    # Clean up tracking
                    self.active_positions.discard(symbol)
                    self.position_entry_times.pop(symbol, None)

                # Update metrics
                self.metrics['active_positions'] = len(self.active_positions)

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"[HFT_CONTROLLER] Position cycle error: {e}")
                await asyncio.sleep(30)

    async def _monitor_performance(self):
        """Monitor HFT performance metrics"""
        while self.is_running:
            try:
                current_time = time.time()

                # Calculate trades per hour
                recent_trades = [t for t in self.trades_last_hour if current_time - t < 3600]
                self.metrics['trades_per_hour'] = len(recent_trades)

                # Calculate average execution time
                if self.execution_times:
                    self.metrics['avg_execution_time'] = sum(self.execution_times) / len(self.execution_times)

                # Calculate success rate
                if self.signals_processed > 0:
                    self.metrics['success_rate'] = self.signals_executed / self.signals_processed

                # Queue depth
                self.metrics['queue_depth'] = self.signal_queue.qsize()

                # Log performance
                logger.info(
                    f"[HFT_METRICS] Trades/hr: {self.metrics['trades_per_hour']} | "
                    f"Avg exec: {self.metrics['avg_execution_time']:.3f}s | "
                    f"Success: {self.metrics['success_rate']:.1%} | "
                    f"Queue: {self.metrics['queue_depth']} | "
                    f"Active: {len(self.active_positions)}"
                )

                # Throttle if needed
                if self.metrics['trades_per_hour'] > self.target_trades_per_hour * 1.5:
                    self.min_execution_interval = min(30, self.min_execution_interval + 2)
                    logger.warning(f"[HFT_CONTROLLER] Throttling - interval now {self.min_execution_interval}s")
                elif self.metrics['trades_per_hour'] < self.target_trades_per_hour * 0.5:
                    self.min_execution_interval = max(5, self.min_execution_interval - 1)

                await asyncio.sleep(60)  # Update every minute

            except Exception as e:
                logger.error(f"[HFT_CONTROLLER] Performance monitor error: {e}")
                await asyncio.sleep(60)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current HFT metrics"""
        return {
            **self.metrics,
            'signals_processed': self.signals_processed,
            'signals_executed': self.signals_executed,
            'active_positions': list(self.active_positions),
            'position_count': len(self.active_positions)
        }

    async def on_position_closed(self, symbol: str):
        """Called when a position is closed"""
        self.active_positions.discard(symbol)
        self.position_entry_times.pop(symbol, None)
        logger.debug(f"[HFT_CONTROLLER] Position closed: {symbol}")
