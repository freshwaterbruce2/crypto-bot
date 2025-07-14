"""
Rapid Position Cycling Engine
=============================

Manages rapid position turnover for fee-free micro-scalping.
Ensures capital is constantly deployed in the most profitable opportunities.

Features:
- Automatic position rotation
- Smart exit strategies
- Capital redeployment optimization
- Performance-based prioritization
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PositionInfo:
    """Information about an active position"""
    symbol: str
    side: str
    size: float
    entry_price: float
    entry_time: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    hold_time: float = 0.0
    profit_target: float = 0.002  # 0.2% default
    stop_loss: float = 0.001  # 0.1% default
    metadata: Dict[str, Any] = None
    
    def update_pnl(self, current_price: float):
        """Update P&L calculations"""
        self.current_price = current_price
        self.hold_time = time.time() - self.entry_time
        
        if self.side == 'buy':
            self.unrealized_pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:  # sell/short
            self.unrealized_pnl_pct = (self.entry_price - current_price) / self.entry_price
        
        self.unrealized_pnl = self.size * self.unrealized_pnl_pct


class PositionCycler:
    """Manages rapid position cycling for capital efficiency"""
    
    def __init__(self, bot, config: Dict[str, Any]):
        """Initialize position cycler"""
        self.bot = bot
        self.config = config
        
        # Cycling parameters
        self.max_hold_time = config.get('fee_free_scalping', {}).get('max_hold_time_seconds', 300)  # 5 min
        self.min_profit_exit = 0.001  # 0.1% - exit immediately if profitable
        self.stale_position_time = 120  # 2 minutes - position is "stale"
        self.force_exit_time = 300  # 5 minutes - force exit
        
        # Position tracking
        self.positions: Dict[str, PositionInfo] = {}
        self.exit_queue: List[str] = []
        self.locked_positions: Set[str] = set()  # Positions being processed
        
        # Performance tracking
        self.exits_by_reason = {
            'profit_target': 0,
            'stop_loss': 0,
            'stale': 0,
            'forced': 0,
            'reallocation': 0
        }
        
        # Cycling control
        self.is_running = False
        self.check_interval = config.get('position_cycling', {}).get('check_interval_minutes', 0.167) * 60  # Convert to seconds
        
        logger.info(f"[POSITION_CYCLER] Initialized - Max hold: {self.max_hold_time}s")
    
    async def start(self):
        """Start position cycling"""
        if self.is_running:
            return
        
        self.is_running = True
        asyncio.create_task(self._cycle_monitor())
        asyncio.create_task(self._exit_processor())
        
        logger.info("[POSITION_CYCLER] Started monitoring")
    
    async def stop(self):
        """Stop position cycling"""
        self.is_running = False
        logger.info("[POSITION_CYCLER] Stopped")
    
    def add_position(self, symbol: str, side: str, size: float, entry_price: float, 
                    profit_target: float = None, stop_loss: float = None, metadata: Dict = None):
        """Add new position to track"""
        position = PositionInfo(
            symbol=symbol,
            side=side,
            size=size,
            entry_price=entry_price,
            entry_time=time.time(),
            profit_target=profit_target or self.config.get('take_profit_pct', 0.002),
            stop_loss=stop_loss or self.config.get('stop_loss_pct', 0.001),
            metadata=metadata or {}
        )
        
        self.positions[symbol] = position
        logger.info(f"[POSITION_CYCLER] Tracking {symbol} - Target: {position.profit_target:.3%}")
    
    def remove_position(self, symbol: str, reason: str = 'unknown'):
        """Remove position from tracking"""
        if symbol in self.positions:
            position = self.positions.pop(symbol)
            self.locked_positions.discard(symbol)
            
            # Track exit reason
            if reason in self.exits_by_reason:
                self.exits_by_reason[reason] += 1
            
            logger.info(
                f"[POSITION_CYCLER] Removed {symbol} - "
                f"P&L: {position.unrealized_pnl_pct:.3%} - "
                f"Time: {position.hold_time:.0f}s - "
                f"Reason: {reason}"
            )
    
    async def _cycle_monitor(self):
        """Monitor positions and determine which need cycling"""
        while self.is_running:
            try:
                current_time = time.time()
                positions_to_exit = []
                
                # Update all positions with current prices
                await self._update_position_prices()
                
                # Analyze each position
                for symbol, position in self.positions.items():
                    if symbol in self.locked_positions:
                        continue  # Skip positions being processed
                    
                    # Determine if position should exit
                    exit_reason = self._should_exit_position(position, current_time)
                    
                    if exit_reason:
                        positions_to_exit.append((symbol, exit_reason, position.unrealized_pnl_pct))
                
                # Sort by priority (worst performers first for reallocation)
                positions_to_exit.sort(key=lambda x: x[2])  # Sort by P&L ascending
                
                # Queue exits
                for symbol, reason, _ in positions_to_exit:
                    if symbol not in self.exit_queue:
                        self.exit_queue.append(symbol)
                        self.locked_positions.add(symbol)
                        logger.info(f"[POSITION_CYCLER] Queued {symbol} for exit: {reason}")
                
                # Log cycle summary
                if self.positions:
                    avg_pnl = np.mean([p.unrealized_pnl_pct for p in self.positions.values()])
                    avg_hold = np.mean([p.hold_time for p in self.positions.values()])
                    logger.debug(
                        f"[POSITION_CYCLER] Positions: {len(self.positions)} | "
                        f"Avg P&L: {avg_pnl:.3%} | "
                        f"Avg hold: {avg_hold:.0f}s | "
                        f"Exit queue: {len(self.exit_queue)}"
                    )
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"[POSITION_CYCLER] Monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _update_position_prices(self):
        """Update current prices for all positions"""
        try:
            # Get current prices from WebSocket if available
            if hasattr(self.bot, 'websocket_manager'):
                ws = self.bot.websocket_manager
                
                for symbol, position in self.positions.items():
                    ticker = ws.get_ticker(symbol)
                    if ticker and ticker.get('last'):
                        position.update_pnl(float(ticker['last']))
                    else:
                        # Try to get from exchange
                        await self._update_single_position(symbol, position)
            else:
                # Fallback to individual updates
                for symbol, position in self.positions.items():
                    await self._update_single_position(symbol, position)
                    
        except Exception as e:
            logger.error(f"[POSITION_CYCLER] Price update error: {e}")
    
    async def _update_single_position(self, symbol: str, position: PositionInfo):
        """Update single position price"""
        try:
            if hasattr(self.bot, 'exchange'):
                ticker = await self.bot.exchange.fetch_ticker(symbol)
                if ticker and ticker.get('last'):
                    position.update_pnl(ticker['last'])
        except Exception as e:
            logger.debug(f"[POSITION_CYCLER] Failed to update {symbol}: {e}")
    
    def _should_exit_position(self, position: PositionInfo, current_time: float) -> Optional[str]:
        """Determine if position should be exited"""
        # Check profit target
        if position.unrealized_pnl_pct >= position.profit_target:
            return 'profit_target'
        
        # Check stop loss
        if position.unrealized_pnl_pct <= -position.stop_loss:
            return 'stop_loss'
        
        # Check minimum profit exit (fee-free advantage)
        if position.unrealized_pnl_pct >= self.min_profit_exit and position.hold_time > 30:
            return 'profit_target'  # Take any profit after 30 seconds
        
        # Check if position is stale but profitable
        if position.hold_time > self.stale_position_time:
            if position.unrealized_pnl_pct > 0:
                return 'stale'  # Exit stale profitable positions
        
        # Force exit after max hold time
        if position.hold_time > self.force_exit_time:
            return 'forced'
        
        # Check for reallocation opportunity
        if self._should_reallocate(position):
            return 'reallocation'
        
        return None
    
    def _should_reallocate(self, position: PositionInfo) -> bool:
        """Check if capital should be reallocated from this position"""
        # Don't reallocate if position is young
        if position.hold_time < 60:  # Less than 1 minute
            return False
        
        # Reallocate if losing and not recovering
        if position.unrealized_pnl_pct < -0.0005 and position.hold_time > 120:  # -0.05% after 2 min
            return True
        
        # Reallocate if flat for too long
        if abs(position.unrealized_pnl_pct) < 0.0002 and position.hold_time > 180:  # Flat after 3 min
            return True
        
        return False
    
    async def _exit_processor(self):
        """Process exit queue"""
        while self.is_running:
            try:
                if self.exit_queue:
                    symbol = self.exit_queue.pop(0)
                    
                    if symbol in self.positions:
                        position = self.positions[symbol]
                        
                        # Request exit through bot
                        success = await self._execute_exit(symbol, position)
                        
                        if success:
                            # Position will be removed when bot confirms close
                            logger.info(f"[POSITION_CYCLER] Exit requested for {symbol}")
                        else:
                            # Unlock if failed
                            self.locked_positions.discard(symbol)
                            logger.warning(f"[POSITION_CYCLER] Failed to exit {symbol}")
                
                await asyncio.sleep(0.5)  # Process exits rapidly
                
            except Exception as e:
                logger.error(f"[POSITION_CYCLER] Exit processor error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_exit(self, symbol: str, position: PositionInfo) -> bool:
        """Execute position exit"""
        try:
            # Determine exit side
            exit_side = 'sell' if position.side == 'buy' else 'buy'
            
            # Place market order to exit
            if hasattr(self.bot, 'place_order'):
                result = await self.bot.place_order(
                    symbol=symbol,
                    side=exit_side,
                    size=position.size,
                    order_type='market',
                    metadata={
                        'exit_reason': 'position_cycling',
                        'hold_time': position.hold_time,
                        'unrealized_pnl_pct': position.unrealized_pnl_pct
                    }
                )
                
                return result and result.get('success', False)
            
            return False
            
        except Exception as e:
            logger.error(f"[POSITION_CYCLER] Exit execution error: {e}")
            return False
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of current positions"""
        if not self.positions:
            return {
                'count': 0,
                'total_unrealized_pnl': 0,
                'avg_hold_time': 0,
                'positions': []
            }
        
        positions_list = []
        total_pnl = 0
        
        for symbol, pos in self.positions.items():
            positions_list.append({
                'symbol': symbol,
                'side': pos.side,
                'pnl_pct': pos.unrealized_pnl_pct,
                'hold_time': pos.hold_time,
                'locked': symbol in self.locked_positions
            })
            total_pnl += pos.unrealized_pnl
        
        return {
            'count': len(self.positions),
            'total_unrealized_pnl': total_pnl,
            'avg_hold_time': np.mean([p.hold_time for p in self.positions.values()]),
            'avg_pnl_pct': np.mean([p.unrealized_pnl_pct for p in self.positions.values()]),
            'positions': sorted(positions_list, key=lambda x: x['pnl_pct']),
            'exit_stats': self.exits_by_reason
        }
    
    def get_cycling_metrics(self) -> Dict[str, Any]:
        """Get position cycling metrics"""
        total_exits = sum(self.exits_by_reason.values())
        
        return {
            'total_cycles': total_exits,
            'exits_by_reason': self.exits_by_reason,
            'avg_hold_time': np.mean([p.hold_time for p in self.positions.values()]) if self.positions else 0,
            'current_positions': len(self.positions),
            'exit_queue_size': len(self.exit_queue),
            'locked_positions': len(self.locked_positions)
        }