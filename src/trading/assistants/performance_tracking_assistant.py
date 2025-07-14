"""
Performance Tracking Assistant - Performance monitoring and analytics helper
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class PerformanceTrackingAssistant:
    """Assistant for tracking trading performance and metrics"""
    
    def __init__(self, manager_or_config):
        # Handle both manager object and config dict
        if hasattr(manager_or_config, 'config'):
            self.manager = manager_or_config
            self.config = manager_or_config.config
        else:
            self.manager = None
            self.config = manager_or_config
        self.logger = logging.getLogger(__name__)
        self.performance_history = []
        
    def track_trade_performance(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track individual trade performance"""
        try:
            performance_metrics = {
                'trade_id': trade_data.get('id', 'unknown'),
                'symbol': trade_data.get('symbol', 'unknown'),
                'side': trade_data.get('side', 'unknown'),
                'amount': trade_data.get('amount', 0),
                'entry_price': trade_data.get('entry_price', 0),
                'exit_price': trade_data.get('exit_price', 0),
                'profit_loss': 0,
                'profit_loss_percentage': 0,
                'duration': trade_data.get('duration', 0),
                'timestamp': datetime.now().isoformat()
            }
            
            # Calculate P&L
            if performance_metrics['entry_price'] and performance_metrics['exit_price']:
                entry = Decimal(str(performance_metrics['entry_price']))
                exit_price = Decimal(str(performance_metrics['exit_price']))
                amount = Decimal(str(performance_metrics['amount']))
                
                if performance_metrics['side'] == 'buy':
                    profit_loss = (exit_price - entry) * amount
                else:  # sell
                    profit_loss = (entry - exit_price) * amount
                    
                performance_metrics['profit_loss'] = float(profit_loss)
                performance_metrics['profit_loss_percentage'] = float(profit_loss / (entry * amount) * 100)
                
            # Store in history
            self.performance_history.append(performance_metrics)
            
            return performance_metrics
            
        except Exception as e:
            self.logger.error(f"Trade performance tracking error: {e}")
            return {}
            
    def calculate_portfolio_performance(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall portfolio performance"""
        try:
            current_value = Decimal(str(portfolio_data.get('current_value', 0)))
            initial_value = Decimal(str(portfolio_data.get('initial_value', 0)))
            
            if initial_value <= 0:
                return {
                    'total_return': 0.0,
                    'total_return_percentage': 0.0,
                    'reason': 'invalid_initial_value'
                }
                
            total_return = current_value - initial_value
            total_return_percentage = (total_return / initial_value) * 100
            
            return {
                'current_value': float(current_value),
                'initial_value': float(initial_value),
                'total_return': float(total_return),
                'total_return_percentage': float(total_return_percentage),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Portfolio performance calculation error: {e}")
            return {}
            
    def calculate_win_rate(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate win rate from trade history"""
        try:
            if not trades:
                return {
                    'win_rate': 0.0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0
                }
                
            winning_trades = sum(1 for trade in trades if trade.get('profit_loss', 0) > 0)
            losing_trades = sum(1 for trade in trades if trade.get('profit_loss', 0) < 0)
            total_trades = len(trades)
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            return {
                'win_rate': win_rate,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades
            }
            
        except Exception as e:
            self.logger.error(f"Win rate calculation error: {e}")
            return {}
            
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio for risk-adjusted returns"""
        try:
            if len(returns) < 2:
                return 0.0
                
            import numpy as np
            
            returns_array = np.array(returns)
            excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
            
            if np.std(excess_returns) == 0:
                return 0.0
                
            sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            
            return float(sharpe_ratio)
            
        except Exception as e:
            self.logger.error(f"Sharpe ratio calculation error: {e}")
            return 0.0
            
    def calculate_max_drawdown(self, equity_curve: List[float]) -> Dict[str, Any]:
        """Calculate maximum drawdown from equity curve"""
        try:
            if len(equity_curve) < 2:
                return {
                    'max_drawdown': 0.0,
                    'max_drawdown_percentage': 0.0,
                    'recovery_factor': 0.0
                }
                
            import numpy as np
            
            equity_array = np.array(equity_curve)
            running_max = np.maximum.accumulate(equity_array)
            drawdown = (running_max - equity_array) / running_max
            
            max_drawdown = np.max(drawdown)
            max_drawdown_percentage = max_drawdown * 100
            
            # Calculate recovery factor
            total_return = (equity_array[-1] - equity_array[0]) / equity_array[0]
            recovery_factor = total_return / max_drawdown if max_drawdown > 0 else 0
            
            return {
                'max_drawdown': float(max_drawdown),
                'max_drawdown_percentage': float(max_drawdown_percentage),
                'recovery_factor': float(recovery_factor)
            }
            
        except Exception as e:
            self.logger.error(f"Max drawdown calculation error: {e}")
            return {}
            
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            if not self.performance_history:
                return {
                    'message': 'No trade history available',
                    'trades_count': 0
                }
                
            # Calculate various metrics
            win_rate_data = self.calculate_win_rate(self.performance_history)
            
            total_profit_loss = sum(trade.get('profit_loss', 0) for trade in self.performance_history)
            average_profit_loss = total_profit_loss / len(self.performance_history)
            
            profitable_trades = [trade for trade in self.performance_history if trade.get('profit_loss', 0) > 0]
            losing_trades = [trade for trade in self.performance_history if trade.get('profit_loss', 0) < 0]
            
            avg_winning_trade = sum(trade.get('profit_loss', 0) for trade in profitable_trades) / len(profitable_trades) if profitable_trades else 0
            avg_losing_trade = sum(trade.get('profit_loss', 0) for trade in losing_trades) / len(losing_trades) if losing_trades else 0
            
            return {
                'total_trades': len(self.performance_history),
                'win_rate': win_rate_data.get('win_rate', 0),
                'total_profit_loss': total_profit_loss,
                'average_profit_loss': average_profit_loss,
                'average_winning_trade': avg_winning_trade,
                'average_losing_trade': avg_losing_trade,
                'profit_factor': abs(avg_winning_trade / avg_losing_trade) if avg_losing_trade != 0 else 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Performance report generation error: {e}")
            return {}
    
    # ASYNC METHODS REQUIRED BY INFINITY TRADING MANAGER
    
    async def initialize(self):
        """Initialize the performance tracking assistant"""
        try:
            self.logger.info("[PERFORMANCE_ASSISTANT] Initializing...")
            
            # Initialize performance tracking
            self.performance_history = []
            self.session_start_time = time.time()
            self.daily_metrics = {}
            self.real_time_metrics = {
                'trades_today': 0,
                'profit_today': 0.0,
                'win_rate_today': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'active_positions': 0
            }
            
            # Load historical performance if available
            if self.manager and hasattr(self.manager, 'bot'):
                # Try to load existing performance data
                pass
            
            self.logger.info("[PERFORMANCE_ASSISTANT] Initialization complete")
            
        except Exception as e:
            self.logger.error(f"[PERFORMANCE_ASSISTANT] Initialization error: {e}")
    
    async def stop(self):
        """Stop the performance tracking assistant"""
        try:
            self.logger.info("[PERFORMANCE_ASSISTANT] Stopping...")
            
            # Generate final report
            final_report = await self.generate_final_report()
            self.logger.info(f"[PERFORMANCE_ASSISTANT] Final session summary: {final_report.get('summary', 'No data')}")
            
            self.logger.info("[PERFORMANCE_ASSISTANT] Stopped successfully")
            
        except Exception as e:
            self.logger.error(f"[PERFORMANCE_ASSISTANT] Stop error: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of the performance tracking assistant"""
        try:
            # Check if we're tracking data properly
            session_duration = time.time() - getattr(self, 'session_start_time', time.time())
            data_available = len(getattr(self, 'performance_history', [])) > 0
            
            healthy = True  # Performance tracking is generally always healthy
            
            return {
                'healthy': healthy,
                'session_duration_hours': session_duration / 3600,
                'trades_tracked': len(getattr(self, 'performance_history', [])),
                'data_available': data_available,
                'real_time_metrics': getattr(self, 'real_time_metrics', {}),
                'timestamp': time.time()
            }
            
        except Exception as e:
            self.logger.error(f"[PERFORMANCE_ASSISTANT] Health check error: {e}")
            return {'healthy': False, 'error': str(e)}
    
    async def update_metrics(self, trading_state: Any):
        """Update performance metrics with current trading state"""
        try:
            if not trading_state:
                return
            
            # Update real-time metrics from trading state
            self.real_time_metrics.update({
                'active_positions': getattr(trading_state, 'active_positions', 0),
                'capital_deployed': getattr(trading_state, 'capital_deployed', 0.0),
                'capital_available': getattr(trading_state, 'capital_available', 0.0),
                'realized_pnl': getattr(trading_state, 'realized_pnl', 0.0),
                'loop_iterations': getattr(trading_state, 'loop_iterations', 0)
            })
            
            # Update daily totals
            current_date = datetime.now().date().isoformat()
            if current_date not in self.daily_metrics:
                self.daily_metrics[current_date] = {
                    'trades': 0,
                    'profit': 0.0,
                    'volume': 0.0
                }
            
            self.logger.debug(f"[PERFORMANCE_ASSISTANT] Updated metrics: {self.real_time_metrics['active_positions']} positions, ${self.real_time_metrics.get('realized_pnl', 0):.2f} PnL")
            
        except Exception as e:
            self.logger.error(f"[PERFORMANCE_ASSISTANT] Error updating metrics: {e}")
    
    async def generate_final_report(self) -> Dict[str, Any]:
        """Generate final performance report"""
        try:
            self.logger.info("[PERFORMANCE_ASSISTANT] Generating final performance report...")
            
            session_duration = time.time() - getattr(self, 'session_start_time', time.time())
            
            # Basic session summary
            summary = {
                'session_duration_hours': session_duration / 3600,
                'total_trades': len(self.performance_history),
                'final_pnl': self.real_time_metrics.get('realized_pnl', 0.0),
                'active_positions': self.real_time_metrics.get('active_positions', 0),
                'loop_iterations': self.real_time_metrics.get('loop_iterations', 0)
            }
            
            # Performance analysis if we have trade data
            if self.performance_history:
                performance_report = self.generate_performance_report()
                summary.update({
                    'win_rate': performance_report.get('win_rate', 0),
                    'average_trade': performance_report.get('average_profit_loss', 0),
                    'profit_factor': performance_report.get('profit_factor', 0),
                    'best_trade': max(trade.get('profit_loss', 0) for trade in self.performance_history),
                    'worst_trade': min(trade.get('profit_loss', 0) for trade in self.performance_history)
                })
            
            # Generate summary message
            if summary['total_trades'] > 0:
                summary['summary'] = f"Session: {summary['total_trades']} trades, ${summary['final_pnl']:.2f} PnL, {summary['win_rate']:.1f}% win rate"
            else:
                summary['summary'] = f"Session: {summary['session_duration_hours']:.1f}h runtime, no completed trades"
            
            summary['timestamp'] = datetime.now().isoformat()
            
            self.logger.info(f"[PERFORMANCE_ASSISTANT] Final report: {summary['summary']}")
            return summary
            
        except Exception as e:
            self.logger.error(f"[PERFORMANCE_ASSISTANT] Error generating final report: {e}")
            return {
                'summary': 'Error generating report',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        try:
            # Real-time performance summary
            current_performance = {
                'overall': {
                    'win_rate': 0.0,
                    'profit_factor': 1.0,
                    'total_trades': len(self.performance_history),
                    'realized_pnl': self.real_time_metrics.get('realized_pnl', 0.0),
                    'active_positions': self.real_time_metrics.get('active_positions', 0)
                },
                'today': self.real_time_metrics.copy(),
                'best_performing_symbols': []
            }
            
            # Calculate overall metrics if we have trade history
            if self.performance_history:
                win_rate_data = self.calculate_win_rate(self.performance_history)
                current_performance['overall']['win_rate'] = win_rate_data.get('win_rate', 0) / 100  # Convert to decimal
                
                # Calculate profit factor
                profitable_trades = [t for t in self.performance_history if t.get('profit_loss', 0) > 0]
                losing_trades = [t for t in self.performance_history if t.get('profit_loss', 0) < 0]
                
                total_profit = sum(t.get('profit_loss', 0) for t in profitable_trades)
                total_loss = abs(sum(t.get('profit_loss', 0) for t in losing_trades))
                
                if total_loss > 0:
                    current_performance['overall']['profit_factor'] = total_profit / total_loss
                
                # Find best performing symbols
                symbol_performance = {}
                for trade in self.performance_history:
                    symbol = trade.get('symbol', 'unknown')
                    profit = trade.get('profit_loss', 0)
                    
                    if symbol not in symbol_performance:
                        symbol_performance[symbol] = {'profit': 0, 'trades': 0}
                    
                    symbol_performance[symbol]['profit'] += profit
                    symbol_performance[symbol]['trades'] += 1
                
                # Sort by profitability
                best_symbols = sorted(
                    symbol_performance.items(),
                    key=lambda x: x[1]['profit'],
                    reverse=True
                )[:5]
                
                current_performance['best_performing_symbols'] = [
                    {'symbol': symbol, 'profit': data['profit'], 'trades': data['trades']}
                    for symbol, data in best_symbols
                ]
            
            return current_performance
            
        except Exception as e:
            self.logger.error(f"[PERFORMANCE_ASSISTANT] Error getting performance summary: {e}")
            return {
                'overall': {'win_rate': 0.0, 'profit_factor': 1.0, 'total_trades': 0, 'realized_pnl': 0.0, 'active_positions': 0},
                'today': {},
                'best_performing_symbols': [],
                'error': str(e)
            }
    
    async def track_trade_async(self, trade_data: Dict[str, Any]):
        """Async version of trade tracking"""
        try:
            # Use the existing sync method
            performance_metrics = self.track_trade_performance(trade_data)
            
            # Update real-time metrics
            if performance_metrics:
                profit = performance_metrics.get('profit_loss', 0)
                self.real_time_metrics['profit_today'] += profit
                self.real_time_metrics['trades_today'] += 1
                
                if profit > self.real_time_metrics['best_trade']:
                    self.real_time_metrics['best_trade'] = profit
                if profit < self.real_time_metrics['worst_trade']:
                    self.real_time_metrics['worst_trade'] = profit
                
                # Update win rate
                profitable_trades = len([t for t in self.performance_history if t.get('profit_loss', 0) > 0])
                total_trades = len(self.performance_history)
                self.real_time_metrics['win_rate_today'] = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
                
                self.logger.info(f"[PERFORMANCE_ASSISTANT] Tracked trade: {trade_data.get('symbol')} ${profit:.2f}")
            
            return performance_metrics
            
        except Exception as e:
            self.logger.error(f"[PERFORMANCE_ASSISTANT] Error tracking trade async: {e}")
            return {}