"""
Real-time P&L Tracker
Continuous monitoring of profit/loss with optimization triggers
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RealtimePnLTracker:
    """Track real-time P&L and trigger optimization actions"""
    
    def __init__(self, balance_manager, trade_executor):
        self.balance_manager = balance_manager
        self.trade_executor = trade_executor
        
        # OPTIMIZED: Ultra-aggressive tracking intervals
        self.update_interval = 10  # 10 seconds for real-time tracking
        self.profit_check_interval = 5  # 5 seconds for profit opportunities
        
        # Performance metrics
        self.start_time = time.time()
        self.start_value = 0.0
        self.current_value = 0.0
        self.peak_value = 0.0
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        
        # OPTIMIZED: Ultra-fast profit-taking thresholds
        self.quick_profit_threshold = 0.0005  # 0.05% immediate profit
        self.auto_sell_threshold = 0.001      # 0.1% auto-sell trigger
        self.fast_sell_threshold = 0.002      # 0.2% fast sell
        
        # Position tracking
        self.position_history = []
        self.last_portfolio_state = {}
        
        # Running status
        self.is_running = False
        self.task = None
        
    async def start_tracking(self):
        """Start real-time P&L tracking"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Get initial portfolio value
        self.start_value = await self._calculate_portfolio_value()
        self.current_value = self.start_value
        self.peak_value = self.start_value
        
        logger.info(f"[PNL_TRACKER] Started tracking - Initial value: ${self.start_value:.2f}")
        
        # Start tracking task
        self.task = asyncio.create_task(self._tracking_loop())
        
    async def stop_tracking(self):
        """Stop P&L tracking"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            
    async def _tracking_loop(self):
        """Main tracking loop with optimization triggers"""
        while self.is_running:
            try:
                # Update portfolio metrics
                await self._update_portfolio_metrics()
                
                # Check for profit-taking opportunities
                await self._check_profit_opportunities()
                
                # Log performance every minute
                if time.time() % 60 < 10:  # Every minute (approximately)
                    await self._log_performance_summary()
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"[PNL_TRACKER] Error in tracking loop: {e}")
                await asyncio.sleep(self.update_interval)
                
    async def _update_portfolio_metrics(self):
        """Update real-time portfolio metrics"""
        try:
            # Get current portfolio value
            current_value = await self._calculate_portfolio_value()
            
            # Update tracking metrics
            self.current_value = current_value
            self.peak_value = max(self.peak_value, current_value)
            
            # Calculate P&L
            self.total_unrealized_pnl = current_value - self.start_value
            unrealized_pct = (self.total_unrealized_pnl / self.start_value) * 100
            
            # Track in position history
            self.position_history.append({
                'timestamp': time.time(),
                'value': current_value,
                'unrealized_pnl': self.total_unrealized_pnl,
                'unrealized_pct': unrealized_pct
            })
            
            # Keep only last 100 entries
            if len(self.position_history) > 100:
                self.position_history = self.position_history[-100:]
                
        except Exception as e:
            logger.error(f"[PNL_TRACKER] Error updating metrics: {e}")
            
    async def _calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value in USD"""
        try:
            # Read current portfolio state
            with open('trading_data/portfolio_state.json', 'r') as f:
                portfolio = json.load(f)
                
            total_value = 0.0
            for symbol, data in portfolio.items():
                total_value += data.get('current_value', 0.0)
                
            # Add available USDT
            if hasattr(self.balance_manager, 'get_direct_kraken_balance'):
                balance = await self.balance_manager.get_direct_kraken_balance()
                usdt_balance = float(balance.get('USDT', 0))
                total_value += usdt_balance
                
            return total_value
            
        except Exception as e:
            logger.error(f"[PNL_TRACKER] Error calculating portfolio value: {e}")
            return self.current_value  # Return last known value
            
    async def _check_profit_opportunities(self):
        """Check for profit-taking opportunities and execute if thresholds met"""
        try:
            # Read current portfolio
            with open('trading_data/portfolio_state.json', 'r') as f:
                portfolio = json.load(f)
                
            for symbol, data in portfolio.items():
                await self._check_position_profit(symbol, data)
                
        except Exception as e:
            logger.error(f"[PNL_TRACKER] Error checking profit opportunities: {e}")
            
    async def _check_position_profit(self, symbol: str, position_data: Dict[str, Any]):
        """Check individual position for profit-taking"""
        try:
            current_price = position_data.get('current_price', 0)
            entry_price = position_data.get('entry_price', 0)
            amount = position_data.get('amount', 0)
            
            if current_price <= 0 or entry_price <= 0 or amount <= 0:
                return
                
            # Calculate profit percentage
            profit_pct = ((current_price - entry_price) / entry_price)
            
            # OPTIMIZED: Ultra-aggressive profit triggers
            if profit_pct >= self.auto_sell_threshold:
                logger.info(f"[PNL_TRACKER] 🎯 AUTO-SELL TRIGGER: {symbol} profit {profit_pct:.4f}% >= {self.auto_sell_threshold:.4f}%")
                
                # Trigger immediate sell via trade executor
                if hasattr(self.trade_executor, 'execute_immediate_sell'):
                    await self.trade_executor.execute_immediate_sell(symbol, amount, 'profit_target')
                    
            elif profit_pct >= self.quick_profit_threshold:
                logger.info(f"[PNL_TRACKER] 💰 QUICK PROFIT: {symbol} at {profit_pct:.4f}% profit - monitoring for sell")
                
        except Exception as e:
            logger.error(f"[PNL_TRACKER] Error checking position profit for {symbol}: {e}")
            
    async def _log_performance_summary(self):
        """Log performance summary"""
        try:
            runtime_hours = (time.time() - self.start_time) / 3600
            profit_pct = (self.total_unrealized_pnl / self.start_value) * 100 if self.start_value > 0 else 0
            
            logger.info(f"[PNL_TRACKER] 📊 Performance: ${self.current_value:.2f} ({profit_pct:+.3f}%) | Peak: ${self.peak_value:.2f} | Runtime: {runtime_hours:.1f}h")
            
        except Exception as e:
            logger.error(f"[PNL_TRACKER] Error logging summary: {e}")
            
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        runtime_hours = (time.time() - self.start_time) / 3600
        profit_pct = (self.total_unrealized_pnl / self.start_value) * 100 if self.start_value > 0 else 0
        
        return {
            'start_value': self.start_value,
            'current_value': self.current_value,
            'peak_value': self.peak_value,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_realized_pnl': self.total_realized_pnl,
            'profit_pct': profit_pct,
            'runtime_hours': runtime_hours,
            'position_count': len(self.last_portfolio_state),
            'is_tracking': self.is_running
        }