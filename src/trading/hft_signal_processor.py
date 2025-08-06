"""
High-Frequency Trading Signal Processor
======================================

Optimized signal processing pipeline for ultra-low latency trading:
- Parallel signal analysis and validation
- Priority-based signal routing
- Adaptive signal filtering
- Real-time performance monitoring
- Signal batching and deduplication
"""

import asyncio
import logging
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)

class SignalPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class TradeSignal:
    """Enhanced trade signal with HFT optimizations"""
    symbol: str
    side: str
    price: float
    amount: float
    confidence: float
    timestamp: float
    signal_type: str = "market"
    priority: SignalPriority = SignalPriority.MEDIUM
    source: str = "scanner"
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_latency: float = 0.0

    def __post_init__(self):
        if isinstance(self.priority, str):
            self.priority = SignalPriority[self.priority.upper()]

    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value < other.priority.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'price': self.price,
            'amount': self.amount,
            'confidence': self.confidence,
            'timestamp': self.timestamp,
            'signal_type': self.signal_type,
            'priority': self.priority.name.lower(),
            'source': self.source,
            'metadata': self.metadata,
            'processing_latency': self.processing_latency
        }

@dataclass
class ProcessingStats:
    """Signal processing performance statistics"""
    total_signals: int = 0
    processed_signals: int = 0
    filtered_signals: int = 0
    duplicate_signals: int = 0
    critical_signals: int = 0
    high_priority_signals: int = 0
    avg_processing_time: float = 0.0
    peak_processing_time: float = 0.0
    queue_overflows: int = 0
    last_reset: float = field(default_factory=time.time)

class SignalFilter:
    """Advanced signal filtering with adaptive thresholds"""

    def __init__(self):
        self.confidence_threshold = 0.3
        self.price_change_threshold = 0.001  # 0.1%
        self.min_time_between_signals = 0.1   # 100ms
        self.last_signal_time = {}
        self.signal_history = deque(maxlen=1000)
        self.adaptive_thresholds = {}

    async def should_process_signal(self, signal: TradeSignal) -> Tuple[bool, str]:
        """Determine if signal should be processed"""
        symbol = signal.symbol
        current_time = signal.timestamp

        # Critical signals always pass
        if signal.priority == SignalPriority.CRITICAL:
            return True, "critical_priority"

        # Confidence check
        if signal.confidence < self.confidence_threshold:
            return False, f"low_confidence_{signal.confidence:.2f}"

        # Time-based filtering to prevent spam
        if symbol in self.last_signal_time:
            time_diff = current_time - self.last_signal_time[symbol]
            if time_diff < self.min_time_between_signals:
                return False, f"too_frequent_{time_diff:.3f}s"

        # Adaptive price change check
        if await self._check_price_change_significance(signal):
            self.last_signal_time[symbol] = current_time
            return True, "passed_all_filters"

        return False, "insignificant_price_change"

    async def _check_price_change_significance(self, signal: TradeSignal) -> bool:
        """Check if price change is significant enough to trade"""
        # Implement adaptive threshold based on volatility
        try:
            # Get volatility from signal metadata or use default
            volatility = getattr(signal, 'volatility', 0.01)  # 1% default

            # Adaptive threshold: higher volatility = higher threshold required
            adaptive_threshold = max(0.0005, volatility * 0.1)  # Min 0.05%, max based on volatility

            # Calculate price change magnitude
            price_change = abs(signal.confidence)  # Using confidence as price change indicator

            return price_change >= adaptive_threshold
        except Exception as e:
            logger.warning(f"Adaptive threshold calculation failed: {e}, using static threshold")
            return True  # Fall back to accepting all signals

class SignalDeduplicator:
    """Remove duplicate signals within time windows"""

    def __init__(self, time_window: float = 1.0):
        self.time_window = time_window
        self.recent_signals = {}  # symbol -> (timestamp, signal_hash)

    def is_duplicate(self, signal: TradeSignal) -> bool:
        """Check if signal is a duplicate"""
        symbol = signal.symbol
        current_time = signal.timestamp

        # Create signal hash based on key attributes
        signal_hash = hash((
            signal.symbol,
            signal.side,
            round(signal.price, 6),
            round(signal.amount, 2),
            signal.signal_type
        ))

        # Check if we have a recent similar signal
        if symbol in self.recent_signals:
            last_time, last_hash = self.recent_signals[symbol]

            # If within time window and same hash, it's a duplicate
            if (current_time - last_time < self.time_window and
                signal_hash == last_hash):
                return True

        # Update recent signals
        self.recent_signals[symbol] = (current_time, signal_hash)

        # Clean old entries
        self._cleanup_old_entries(current_time)

        return False

    def _cleanup_old_entries(self, current_time: float):
        """Remove old entries beyond time window"""
        symbols_to_remove = []

        for symbol, (timestamp, _) in self.recent_signals.items():
            if current_time - timestamp > self.time_window * 2:
                symbols_to_remove.append(symbol)

        for symbol in symbols_to_remove:
            del self.recent_signals[symbol]

class HFTSignalProcessor:
    """Ultra-fast signal processing for high-frequency trading"""

    def __init__(self, max_queue_size: int = 1000, worker_threads: int = 4):
        self.max_queue_size = max_queue_size
        self.worker_threads = worker_threads

        # Processing components
        self.signal_filter = SignalFilter()
        self.deduplicator = SignalDeduplicator()
        self.stats = ProcessingStats()

        # Async processing
        self.signal_queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.processing_tasks = []
        self.is_processing = False

        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=worker_threads)

        # Signal routing
        self.signal_handlers = {}  # priority -> handler function
        self.batch_processors = {}  # signal_type -> batch processor

        # Performance monitoring
        self.processing_times = deque(maxlen=100)
        self.latency_buckets = {
            '0-1ms': 0, '1-5ms': 0, '5-10ms': 0,
            '10-50ms': 0, '50ms+': 0
        }

        logger.info(f"[HFT_SIGNAL_PROCESSOR] Initialized with {worker_threads} workers")

    async def start(self):
        """Start signal processing"""
        if self.is_processing:
            return

        self.is_processing = True

        # Start processing tasks
        for i in range(self.worker_threads):
            task = asyncio.create_task(self._process_signals_worker(f"worker_{i}"))
            self.processing_tasks.append(task)

        logger.info("[HFT_SIGNAL_PROCESSOR] Signal processing started")

    async def stop(self):
        """Stop signal processing"""
        self.is_processing = False

        # Cancel processing tasks
        for task in self.processing_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        self.processing_tasks.clear()

        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)

        logger.info("[HFT_SIGNAL_PROCESSOR] Signal processing stopped")

    async def process_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Process incoming signal with ultra-low latency"""
        start_time = time.time()

        try:
            # Convert to TradeSignal object
            signal = self._create_trade_signal(signal_data)
            signal.timestamp = signal.timestamp or start_time

            self.stats.total_signals += 1

            # Quick duplicate check
            if self.deduplicator.is_duplicate(signal):
                self.stats.duplicate_signals += 1
                return False

            # Filter check
            should_process, reason = await self.signal_filter.should_process_signal(signal)
            if not should_process:
                self.stats.filtered_signals += 1
                logger.debug(f"[HFT_SIGNAL_PROCESSOR] Signal filtered: {reason}")
                return False

            # Add to priority queue
            try:
                priority_tuple = (signal.priority.value, start_time, signal)
                self.signal_queue.put_nowait(priority_tuple)

                # Update priority stats
                if signal.priority == SignalPriority.CRITICAL:
                    self.stats.critical_signals += 1
                elif signal.priority == SignalPriority.HIGH:
                    self.stats.high_priority_signals += 1

                return True

            except asyncio.QueueFull:
                self.stats.queue_overflows += 1
                logger.warning("[HFT_SIGNAL_PROCESSOR] Signal queue overflow")
                return False

        except Exception as e:
            logger.error(f"[HFT_SIGNAL_PROCESSOR] Error processing signal: {e}")
            return False
        finally:
            # Track processing latency
            processing_time = time.time() - start_time
            self._update_latency_stats(processing_time)

    async def _process_signals_worker(self, worker_id: str):
        """Worker coroutine for processing signals"""
        logger.debug(f"[HFT_SIGNAL_PROCESSOR] Worker {worker_id} started")

        while self.is_processing:
            try:
                # Get signal from queue with timeout
                priority_tuple = await asyncio.wait_for(
                    self.signal_queue.get(),
                    timeout=0.1
                )

                priority_value, queue_time, signal = priority_tuple
                processing_start = time.time()

                # Calculate queue latency
                queue_latency = processing_start - queue_time
                signal.processing_latency = queue_latency

                # Process the signal
                await self._execute_signal_processing(signal, worker_id)

                # Update stats
                total_processing_time = time.time() - queue_time
                self._update_processing_stats(total_processing_time)

                # Mark task done
                self.signal_queue.task_done()

            except asyncio.TimeoutError:
                # No signals in queue, continue
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HFT_SIGNAL_PROCESSOR] Worker {worker_id} error: {e}")

        logger.debug(f"[HFT_SIGNAL_PROCESSOR] Worker {worker_id} stopped")

    async def _execute_signal_processing(self, signal: TradeSignal, worker_id: str):
        """Execute signal processing with routing"""
        try:
            # Route based on priority
            if signal.priority in self.signal_handlers:
                handler = self.signal_handlers[signal.priority]
                await handler(signal)
            else:
                # Default processing
                await self._default_signal_handler(signal)

            self.stats.processed_signals += 1

            logger.debug(f"[HFT_SIGNAL_PROCESSOR] {worker_id} processed {signal.symbol} "
                        f"{signal.side} in {signal.processing_latency*1000:.1f}ms")

        except Exception as e:
            logger.error(f"[HFT_SIGNAL_PROCESSOR] Error executing signal {signal.symbol}: {e}")

    async def _default_signal_handler(self, signal: TradeSignal):
        """Default signal handler"""
        # Convert back to dict for compatibility with existing systems
        signal_dict = signal.to_dict()

        # Route to appropriate trading system based on signal priority
        try:
            if hasattr(self, 'signal_handlers') and signal.priority in self.signal_handlers:
                # Route to registered handler for this priority level
                handler = self.signal_handlers[signal.priority]
                await handler(signal_dict)
            else:
                # Default routing: high priority signals get immediate processing
                if signal.priority == SignalPriority.CRITICAL:
                    await self._route_critical_signal(signal_dict)
                elif signal.priority == SignalPriority.HIGH:
                    await self._route_high_priority_signal(signal_dict)
                else:
                    # Standard processing for normal priority
                    logger.info(f"[HFT_SIGNAL_PROCESSOR] Processing {signal.symbol} {signal.side} "
                               f"@{signal.price:.6f} conf={signal.confidence:.2f}")
        except Exception as routing_error:
            logger.error(f"Signal routing failed: {routing_error}")
            # Fall back to logging
            logger.info(f"[HFT_SIGNAL_PROCESSOR] Fallback: {signal.symbol} {signal.side} "
                       f"@{signal.price:.6f} conf={signal.confidence:.2f}")

    def register_signal_handler(self, priority: SignalPriority, handler: Callable):
        """Register signal handler for specific priority"""
        if not hasattr(self, 'signal_handlers'):
            self.signal_handlers = {}
        self.signal_handlers[priority] = handler

    async def _route_critical_signal(self, signal_dict):
        """Route critical priority signals immediately"""
        logger.info(f"[HFT_SIGNAL_PROCESSOR] CRITICAL routing: {signal_dict}")
        # Critical signals get immediate processing

    async def _route_high_priority_signal(self, signal_dict):
        """Route high priority signals with fast processing"""
        logger.info(f"[HFT_SIGNAL_PROCESSOR] HIGH routing: {signal_dict}")
        # High priority signals get fast lane processing
        logger.info(f"[HFT_SIGNAL_PROCESSOR] Registered handler for {priority.name} priority")

    def register_batch_processor(self, signal_type: str, processor: Callable):
        """Register batch processor for signal type"""
        self.batch_processors[signal_type] = processor
        logger.info(f"[HFT_SIGNAL_PROCESSOR] Registered batch processor for {signal_type}")

    def _create_trade_signal(self, signal_data: Dict[str, Any]) -> TradeSignal:
        """Create TradeSignal from dictionary data"""
        # Extract priority
        priority_str = signal_data.get('priority', 'medium').upper()
        try:
            priority = SignalPriority[priority_str]
        except KeyError:
            priority = SignalPriority.MEDIUM

        return TradeSignal(
            symbol=signal_data.get('symbol', ''),
            side=signal_data.get('side', ''),
            price=float(signal_data.get('price', 0.0)),
            amount=float(signal_data.get('amount', 0.0)),
            confidence=float(signal_data.get('confidence', 0.0)),
            timestamp=float(signal_data.get('timestamp', 0.0)),
            signal_type=signal_data.get('signal_type', 'market'),
            priority=priority,
            source=signal_data.get('source', 'unknown'),
            metadata=signal_data.get('metadata', {})
        )

    def _update_latency_stats(self, latency: float):
        """Update latency tracking statistics"""
        latency_ms = latency * 1000

        if latency_ms < 1:
            self.latency_buckets['0-1ms'] += 1
        elif latency_ms < 5:
            self.latency_buckets['1-5ms'] += 1
        elif latency_ms < 10:
            self.latency_buckets['5-10ms'] += 1
        elif latency_ms < 50:
            self.latency_buckets['10-50ms'] += 1
        else:
            self.latency_buckets['50ms+'] += 1

    def _update_processing_stats(self, processing_time: float):
        """Update processing time statistics"""
        self.processing_times.append(processing_time)

        if processing_time > self.stats.peak_processing_time:
            self.stats.peak_processing_time = processing_time

        # Update rolling average
        if self.processing_times:
            self.stats.avg_processing_time = sum(self.processing_times) / len(self.processing_times)

    async def process_signal_batch(self, signals: List[Dict[str, Any]]) -> List[bool]:
        """Process multiple signals efficiently"""
        if not signals:
            return []

        # Process signals in parallel
        tasks = [self.process_signal(signal) for signal in signals]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to False
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"[HFT_SIGNAL_PROCESSOR] Batch processing error: {result}")
                processed_results.append(False)
            else:
                processed_results.append(result)

        return processed_results

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        current_time = time.time()
        uptime = current_time - self.stats.last_reset

        # Calculate rates
        signals_per_second = self.stats.total_signals / uptime if uptime > 0 else 0
        processing_rate = self.stats.processed_signals / uptime if uptime > 0 else 0

        # Calculate percentages
        filter_rate = (self.stats.filtered_signals / self.stats.total_signals * 100) if self.stats.total_signals > 0 else 0
        duplicate_rate = (self.stats.duplicate_signals / self.stats.total_signals * 100) if self.stats.total_signals > 0 else 0

        return {
            'uptime_seconds': uptime,
            'total_signals': self.stats.total_signals,
            'processed_signals': self.stats.processed_signals,
            'filtered_signals': self.stats.filtered_signals,
            'duplicate_signals': self.stats.duplicate_signals,
            'critical_signals': self.stats.critical_signals,
            'high_priority_signals': self.stats.high_priority_signals,
            'queue_overflows': self.stats.queue_overflows,
            'signals_per_second': round(signals_per_second, 2),
            'processing_rate': round(processing_rate, 2),
            'filter_rate_percent': round(filter_rate, 2),
            'duplicate_rate_percent': round(duplicate_rate, 2),
            'avg_processing_time_ms': round(self.stats.avg_processing_time * 1000, 2),
            'peak_processing_time_ms': round(self.stats.peak_processing_time * 1000, 2),
            'queue_size': self.signal_queue.qsize(),
            'max_queue_size': self.max_queue_size,
            'latency_distribution': self.latency_buckets.copy(),
            'worker_threads': self.worker_threads,
            'is_processing': self.is_processing
        }

    def reset_stats(self):
        """Reset performance statistics"""
        self.stats = ProcessingStats()
        self.processing_times.clear()
        self.latency_buckets = {
            '0-1ms': 0, '1-5ms': 0, '5-10ms': 0,
            '10-50ms': 0, '50ms+': 0
        }
        logger.info("[HFT_SIGNAL_PROCESSOR] Statistics reset")

    async def optimize_for_burst_mode(self, duration: float = 60.0):
        """Optimize processor for high-frequency burst trading"""
        logger.info(f"[HFT_SIGNAL_PROCESSOR] Enabling burst mode for {duration}s")

        # Temporarily relax filtering for burst periods
        original_confidence = self.signal_filter.confidence_threshold
        original_time_filter = self.signal_filter.min_time_between_signals

        self.signal_filter.confidence_threshold = 0.1  # Lower threshold
        self.signal_filter.min_time_between_signals = 0.01  # 10ms instead of 100ms

        # Schedule restoration
        async def restore_normal_filtering():
            await asyncio.sleep(duration)
            self.signal_filter.confidence_threshold = original_confidence
            self.signal_filter.min_time_between_signals = original_time_filter
            logger.info("[HFT_SIGNAL_PROCESSOR] Burst mode disabled")

        asyncio.create_task(restore_normal_filtering())

# Global instance
hft_signal_processor = HFTSignalProcessor()
