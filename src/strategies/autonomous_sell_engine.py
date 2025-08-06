"""
Autonomous Sell Engine
Intelligent sell order management system with dynamic optimization
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SellTrigger(Enum):
    """Sell trigger types"""
    PROFIT_TARGET = "profit_target"
    STOP_LOSS = "stop_loss"
    TIME_BASED = "time_based"
    MARKET_CONDITION = "market_condition"
    RISK_MANAGEMENT = "risk_management"
    REBALANCING = "rebalancing"
    EMERGENCY = "emergency"


class SellUrgency(Enum):
    """Sell urgency levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SellEngineConfig:
    """Configuration for autonomous sell engine"""
    # OPTIMIZED: Ultra-aggressive profit-taking for immediate gains
    min_profit_pct: float = 0.03  # 0.03% minimum (ULTRA aggressive)
    target_profit_pct: float = 0.08  # 0.08% target (ULTRA fast)
    fast_profit_pct: float = 0.08  # 0.08% fast target
    max_profit_pct: float = 0.25  # 0.25% maximum before immediate sell

    # OPTIMIZED: Ultra-aggressive time-based selling for immediate profits
    max_hold_time_minutes: int = 1  # 1 minute max hold (ULTRA fast)
    force_sell_after_minutes: int = 8  # 8 minutes force sell (reduced from 15)
    micro_profit_hold_minutes: int = 1  # 1 minute for micro-profits (reduced from 2)
    profit_decay_enabled: bool = True

    # Enhanced risk management
    stop_loss_pct: float = 0.08  # 0.08% aligned with config micro stop
    trailing_stop_enabled: bool = True
    trailing_stop_pct: float = 0.03  # 0.03% tighter trailing

    # Market conditions
    volatility_sell_threshold: float = 5.0
    volume_drop_threshold: float = 0.5

    # Execution settings
    max_retries: int = 3
    retry_delay_seconds: float = 2.0
    emergency_market_order: bool = True

    # Performance optimization
    batch_processing: bool = True
    parallel_execution: bool = True
    priority_queue_enabled: bool = True


@dataclass
class SellOrder:
    """Sell order with metadata"""
    symbol: str
    amount: float
    trigger: SellTrigger
    urgency: SellUrgency
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    entry_price: float = 0.0
    entry_time: float = 0.0
    current_profit_pct: float = 0.0
    retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def age_minutes(self) -> float:
        """Get order age in minutes"""
        return (time.time() - self.created_at) / 60

    def hold_time_minutes(self) -> float:
        """Get position hold time in minutes"""
        if self.entry_time > 0:
            return (time.time() - self.entry_time) / 60
        return 0

    def update_profit(self, current_price: float):
        """Update current profit percentage"""
        if self.entry_price > 0:
            self.current_profit_pct = ((current_price - self.entry_price) / self.entry_price) * 100


class AutonomousSellEngine:
    """Autonomous sell order management engine"""

    def __init__(self, config: SellEngineConfig, exchange=None, balance_manager=None):
        """Initialize autonomous sell engine"""
        self.config = config
        self.exchange = exchange
        self.balance_manager = balance_manager

        # Order management
        self.pending_sells = {}  # symbol -> SellOrder
        self.sell_queue = []
        self.execution_lock = asyncio.Lock()

        # Performance tracking
        self.successful_sells = 0
        self.failed_sells = 0
        self.total_profit = 0.0

        # Market data cache
        self.price_cache = {}
        self.last_price_update = {}

        # Engine state
        self.is_running = False
        self.last_processing_time = 0

        logger.info("[SELL_ENGINE] Autonomous sell engine initialized")

    async def start(self):
        """Start the autonomous sell engine"""
        try:
            self.is_running = True
            logger.info("[SELL_ENGINE] Starting autonomous sell engine")

            # Start background processing task
            self.processing_task = asyncio.create_task(self._processing_loop())

            return True
        except Exception as e:
            logger.error(f"[SELL_ENGINE] Error starting engine: {e}")
            return False

    async def stop(self):
        """Stop the autonomous sell engine"""
        try:
            self.is_running = False

            if hasattr(self, 'processing_task'):
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass

            logger.info("[SELL_ENGINE] Autonomous sell engine stopped")
        except Exception as e:
            logger.error(f"[SELL_ENGINE] Error stopping engine: {e}")

    def schedule_sell(self, symbol: str, amount: float, trigger: SellTrigger,
                     urgency: SellUrgency = SellUrgency.MEDIUM,
                     entry_price: float = 0.0, entry_time: float = 0.0,
                     metadata: Dict[str, Any] = None) -> bool:
        """Schedule a sell order"""
        try:
            sell_order = SellOrder(
                symbol=symbol,
                amount=amount,
                trigger=trigger,
                urgency=urgency,
                entry_price=entry_price,
                entry_time=entry_time or time.time(),
                metadata=metadata or {}
            )

            # Calculate target prices
            self._calculate_target_prices(sell_order)

            # Add to pending sells
            self.pending_sells[symbol] = sell_order

            # Add to queue for processing
            self.sell_queue.append(sell_order)

            # Sort queue by urgency and age
            self._sort_sell_queue()

            logger.info(f"[SELL_ENGINE] Scheduled {trigger.value} sell for {symbol}: {amount} @ {urgency.value}")
            return True

        except Exception as e:
            logger.error(f"[SELL_ENGINE] Error scheduling sell for {symbol}: {e}")
            return False

    def cancel_sell(self, symbol: str) -> bool:
        """Cancel pending sell order"""
        try:
            if symbol in self.pending_sells:
                del self.pending_sells[symbol]

                # Remove from queue
                self.sell_queue = [order for order in self.sell_queue if order.symbol != symbol]

                logger.info(f"[SELL_ENGINE] Cancelled sell order for {symbol}")
                return True
            else:
                logger.warning(f"[SELL_ENGINE] No pending sell found for {symbol}")
                return False

        except Exception as e:
            logger.error(f"[SELL_ENGINE] Error cancelling sell for {symbol}: {e}")
            return False

    def get_pending_sells(self) -> List[SellOrder]:
        """Get all pending sell orders"""
        return list(self.pending_sells.values())

    def get_sell_status(self, symbol: str) -> Optional[SellOrder]:
        """Get sell order status for symbol"""
        return self.pending_sells.get(symbol)

    async def _processing_loop(self):
        """Main processing loop for sell orders"""
        while self.is_running:
            try:
                # Update market data
                await self._update_market_data()

                # Process pending sells
                await self._process_pending_sells()

                # Update profit tracking
                self._update_profit_tracking()

                self.last_processing_time = time.time()

                # Wait before next iteration
                await asyncio.sleep(1)  # Process every second

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SELL_ENGINE] Error in processing loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def _process_pending_sells(self):
        """Process all pending sell orders"""
        if not self.sell_queue:
            return

        async with self.execution_lock:
            # Process orders by priority
            orders_to_process = self.sell_queue.copy()

            for sell_order in orders_to_process:
                try:
                    # Check if order should be executed
                    should_execute, reason = self._should_execute_sell(sell_order)

                    if should_execute:
                        success = await self._execute_sell_order(sell_order, reason)

                        if success:
                            # Remove from pending and queue
                            if sell_order.symbol in self.pending_sells:
                                del self.pending_sells[sell_order.symbol]
                            if sell_order in self.sell_queue:
                                self.sell_queue.remove(sell_order)

                            self.successful_sells += 1
                        else:
                            sell_order.retries += 1
                            if sell_order.retries >= self.config.max_retries:
                                logger.error(f"[SELL_ENGINE] Max retries reached for {sell_order.symbol}")
                                # Remove failed order
                                if sell_order.symbol in self.pending_sells:
                                    del self.pending_sells[sell_order.symbol]
                                if sell_order in self.sell_queue:
                                    self.sell_queue.remove(sell_order)
                                self.failed_sells += 1

                except Exception as e:
                    logger.error(f"[SELL_ENGINE] Error processing sell order for {sell_order.symbol}: {e}")

    def _should_execute_sell(self, sell_order: SellOrder) -> Tuple[bool, str]:
        """Enhanced sell execution logic with micro-profit optimization"""
        try:
            current_price = self.price_cache.get(sell_order.symbol, 0)
            if current_price <= 0:
                return False, "No current price data"

            # Update profit
            sell_order.update_profit(current_price)
            profit_pct = sell_order.current_profit_pct
            hold_time = sell_order.hold_time_minutes()

            # PRIORITY 1: Emergency and critical sells
            if sell_order.urgency == SellUrgency.CRITICAL or sell_order.trigger == SellTrigger.EMERGENCY:
                return True, f"Emergency/Critical sell: {profit_pct:.3f}%"

            # PRIORITY 2: Stop loss protection
            if profit_pct <= -self.config.stop_loss_pct:
                return True, f"Stop loss triggered: {profit_pct:.3f}%"

            # PRIORITY 3: Fast micro-profit execution (0.1-0.5%)
            if self.config.min_profit_pct <= profit_pct <= self.config.max_profit_pct:
                # Execute immediately if profit is in the sweet spot
                if hold_time <= self.config.micro_profit_hold_minutes:  # Within 2 minutes
                    return True, f"Fast micro-profit: {profit_pct:.3f}% in {hold_time:.1f}min"
                elif profit_pct >= self.config.fast_profit_pct:  # 0.15%+ profit
                    return True, f"Fast profit threshold: {profit_pct:.3f}%"

            # PRIORITY 4: Target profit reached
            if profit_pct >= self.config.target_profit_pct:
                return True, f"Target profit reached: {profit_pct:.3f}%"

            # PRIORITY 5: Large profits - immediate execution
            if profit_pct >= self.config.max_profit_pct:
                return True, f"Large profit - immediate sell: {profit_pct:.3f}%"

            # PRIORITY 6: Time-adjusted minimum profit
            min_profit = self._calculate_time_adjusted_profit(sell_order)
            if profit_pct >= min_profit and hold_time >= 1.0:  # At least 1 minute hold
                return True, f"Time-adjusted profit: {profit_pct:.3f}% (min: {min_profit:.3f}%)"

            # PRIORITY 7: Force sell conditions
            if hold_time >= self.config.force_sell_after_minutes:
                return True, f"Force sell after {hold_time:.1f} minutes"

            # PRIORITY 8: Any profit after max hold time
            if hold_time >= self.config.max_hold_time_minutes and profit_pct > 0:
                return True, f"Max hold time with profit: {profit_pct:.3f}% after {hold_time:.1f}min"

            return False, f"No trigger: {profit_pct:.3f}% profit, {hold_time:.1f}min hold"

        except Exception as e:
            logger.error(f"[SELL_ENGINE] Error evaluating sell condition for {sell_order.symbol}: {e}")
            return False, f"Error: {e}"

    async def _execute_sell_order(self, sell_order: SellOrder, reason: str) -> bool:
        """Execute the sell order"""
        try:
            if not self.exchange:
                logger.error("[SELL_ENGINE] No exchange available for execution")
                return False

            logger.info(f"[SELL_ENGINE] Executing sell for {sell_order.symbol}: {sell_order.amount} - {reason}")

            # Execute the sell order
            result = await self.exchange.create_market_sell_order(
                symbol=sell_order.symbol,
                amount=sell_order.amount
            )

            if result and result.get('id'):
                logger.info(f"[SELL_ENGINE] Sell executed successfully for {sell_order.symbol}: {result['id']}")

                # Update profit tracking
                if sell_order.current_profit_pct > 0:
                    self.total_profit += sell_order.current_profit_pct

                return True
            else:
                logger.error(f"[SELL_ENGINE] Sell execution failed for {sell_order.symbol}")
                return False

        except Exception as e:
            logger.error(f"[SELL_ENGINE] Error executing sell for {sell_order.symbol}: {e}")
            return False

    def _calculate_target_prices(self, sell_order: SellOrder):
        """Calculate target and stop loss prices"""
        if sell_order.entry_price > 0:
            # Calculate profit target price
            sell_order.target_price = sell_order.entry_price * (1 + self.config.target_profit_pct / 100)

            # Calculate stop loss price
            sell_order.stop_loss_price = sell_order.entry_price * (1 - self.config.stop_loss_pct / 100)

    def _calculate_time_adjusted_profit(self, sell_order: SellOrder) -> float:
        """Enhanced time-adjusted profit with micro-profit optimization"""
        if not self.config.profit_decay_enabled:
            return self.config.min_profit_pct

        hold_time = sell_order.hold_time_minutes()

        # Aggressive decay for micro-profit scalping
        if hold_time <= 1.0:  # First minute - require minimum profit
            return self.config.min_profit_pct
        elif hold_time <= 3.0:  # 1-3 minutes - start decay
            decay_factor = 1.0 - ((hold_time - 1.0) / 4.0)  # Decay over 4 minutes
            return max(0.05, self.config.min_profit_pct * decay_factor)  # Minimum 0.05%
        elif hold_time <= self.config.max_hold_time_minutes:  # 3-5 minutes
            return 0.05  # Accept any reasonable profit
        else:  # Over max hold time
            return 0.01  # Accept minimal profit to exit position

    async def _update_market_data(self):
        """Update cached market data"""
        try:
            if not self.exchange or not self.pending_sells:
                return

            # Get symbols we need prices for
            symbols = list(self.pending_sells.keys())

            # Update prices (in a real implementation, you'd get these from the exchange)
            for symbol in symbols:
                try:
                    ticker = await self.exchange.fetch_ticker(symbol)
                    if ticker and 'last' in ticker:
                        self.price_cache[symbol] = float(ticker['last'])
                        self.last_price_update[symbol] = time.time()
                except Exception as e:
                    logger.debug(f"[SELL_ENGINE] Error updating price for {symbol}: {e}")

        except Exception as e:
            logger.error(f"[SELL_ENGINE] Error updating market data: {e}")

    def _sort_sell_queue(self):
        """Sort sell queue by priority"""
        def priority_key(order):
            urgency_weights = {
                SellUrgency.CRITICAL: 4,
                SellUrgency.HIGH: 3,
                SellUrgency.MEDIUM: 2,
                SellUrgency.LOW: 1
            }
            return (urgency_weights.get(order.urgency, 1), -order.age_minutes())

        self.sell_queue.sort(key=priority_key, reverse=True)

    def _update_profit_tracking(self):
        """Update profit tracking for all pending orders"""
        for sell_order in self.pending_sells.values():
            current_price = self.price_cache.get(sell_order.symbol, 0)
            if current_price > 0:
                sell_order.update_profit(current_price)

    async def on_position_update(self, symbol: str, position_data: Dict[str, Any]):
        """
        Handle position updates from portfolio scanner (2025 compliant).
        
        Args:
            symbol: Trading symbol (e.g., 'ALGO/USDT')
            position_data: Position information with amount, entry_price, etc.
        """
        try:
            amount = float(position_data.get('amount', 0))
            entry_price = float(position_data.get('entry_price', 0))
            entry_time = float(position_data.get('entry_time', time.time()))

            if amount > 0 and entry_price > 0:
                # Schedule sell order for this position
                success = self.schedule_sell(
                    symbol=symbol,
                    amount=amount,
                    trigger=SellTrigger.PROFIT_TARGET,
                    urgency=SellUrgency.MEDIUM,
                    entry_price=entry_price,
                    entry_time=entry_time,
                    metadata={
                        'source': 'portfolio_recovery',
                        'value_usd': position_data.get('value_usd', amount * entry_price),
                        'recovery_timestamp': time.time()
                    }
                )

                if success:
                    logger.info(f"[SELL_ENGINE] Scheduled sell for recovered position: {symbol} {amount:.8f} @ ${entry_price:.6f}")
                else:
                    logger.warning(f"[SELL_ENGINE] Failed to schedule sell for {symbol}")
            else:
                logger.warning(f"[SELL_ENGINE] Invalid position data for {symbol}: amount={amount}, entry_price={entry_price}")

        except Exception as e:
            logger.error(f"[SELL_ENGINE] Error handling position update for {symbol}: {e}")

    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine performance statistics"""
        return {
            'is_running': self.is_running,
            'pending_sells': len(self.pending_sells),
            'queue_length': len(self.sell_queue),
            'successful_sells': self.successful_sells,
            'failed_sells': self.failed_sells,
            'total_profit': self.total_profit,
            'last_processing_time': self.last_processing_time,
            'cache_size': len(self.price_cache)
        }


# Convenience functions
async def create_autonomous_sell_engine(exchange=None, balance_manager=None,
                                      config: Optional[SellEngineConfig] = None) -> AutonomousSellEngine:
    """Create and start autonomous sell engine"""
    if config is None:
        config = SellEngineConfig()

    engine = AutonomousSellEngine(config, exchange, balance_manager)
    await engine.start()
    return engine
