"""
Sell Performance Monitor
========================

Real-time monitoring and optimization of sell logic performance.
Tracks execution speed, profit capture efficiency, and decision accuracy.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import statistics

logger = logging.getLogger(__name__)


@dataclass
class SellExecutionMetrics:
    """Metrics for individual sell execution"""
    symbol: str
    timestamp: datetime
    decision_time_ms: float
    execution_time_ms: float
    profit_pct: float
    profit_usd: float
    confidence: float
    sell_reason: str
    urgency: str
    success: bool
    slippage_pct: float = 0.0
    market_impact_pct: float = 0.0


@dataclass
class SellPerformanceStats:
    """Aggregated sell performance statistics"""
    total_sells: int = 0
    successful_sells: int = 0
    avg_decision_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0
    avg_profit_pct: float = 0.0
    total_profit_usd: float = 0.0
    success_rate: float = 0.0
    avg_confidence: float = 0.0
    speed_percentiles: Dict[str, float] = field(default_factory=dict)
    profit_distribution: Dict[str, int] = field(default_factory=dict)


class SellPerformanceMonitor:
    """
    Real-time performance monitoring for sell logic optimization.
    Tracks speed, accuracy, and profitability of sell decisions.
    """
    
    def __init__(self, max_history: int = 1000):
        """Initialize performance monitor"""
        self.max_history = max_history
        self.execution_history = deque(maxlen=max_history)
        
        # Real-time metrics
        self.active_decisions = {}  # Track ongoing decisions
        self.performance_alerts = deque(maxlen=100)
        
        # Speed benchmarks (milliseconds)
        self.target_decision_time_ms = 50  # 50ms decision target
        self.target_execution_time_ms = 500  # 500ms execution target
        self.critical_decision_time_ms = 200  # 200ms critical threshold
        
        # Profit tracking
        self.hourly_profits = deque(maxlen=24)  # 24 hours of data
        self.daily_targets = {
            'min_profit_rate': 0.5,  # 0.5% average profit per sell
            'min_success_rate': 0.85,  # 85% success rate
            'max_avg_decision_time': 100  # 100ms average decision time
        }
        
        logger.info("[SELL_MONITOR] Performance monitor initialized")
    
    def start_decision_timing(self, symbol: str, decision_id: str) -> None:
        """Start timing a sell decision"""
        self.active_decisions[decision_id] = {
            'symbol': symbol,
            'start_time': time.time(),
            'decision_started': True
        }
    
    def record_decision_complete(self, decision_id: str, sell_signal: Dict[str, Any]) -> None:
        """Record completion of sell decision"""
        if decision_id not in self.active_decisions:
            logger.warning(f"[SELL_MONITOR] Unknown decision ID: {decision_id}")
            return
        
        decision_data = self.active_decisions[decision_id]
        decision_time_ms = (time.time() - decision_data['start_time']) * 1000
        
        # Update decision data
        decision_data.update({
            'decision_time_ms': decision_time_ms,
            'decision_complete': True,
            'sell_signal': sell_signal,
            'execution_start_time': time.time()
        })
        
        # Performance alert for slow decisions
        if decision_time_ms > self.critical_decision_time_ms:
            self._add_performance_alert(
                f"SLOW_DECISION: {decision_data['symbol']} took {decision_time_ms:.1f}ms",
                'warning'
            )
    
    def record_execution_complete(self, decision_id: str, execution_result: Dict[str, Any]) -> None:
        """Record completion of sell execution"""
        if decision_id not in self.active_decisions:
            logger.warning(f"[SELL_MONITOR] Unknown decision ID for execution: {decision_id}")
            return
        
        decision_data = self.active_decisions[decision_id]
        if 'execution_start_time' not in decision_data:
            logger.warning(f"[SELL_MONITOR] No execution start time for {decision_id}")
            return
        
        execution_time_ms = (time.time() - decision_data['execution_start_time']) * 1000
        
        # Create execution metrics
        sell_signal = decision_data.get('sell_signal', {})
        metrics = SellExecutionMetrics(
            symbol=decision_data['symbol'],
            timestamp=datetime.now(),
            decision_time_ms=decision_data.get('decision_time_ms', 0),
            execution_time_ms=execution_time_ms,
            profit_pct=execution_result.get('profit_pct', 0),
            profit_usd=execution_result.get('profit_usd', 0),
            confidence=sell_signal.get('confidence', 0),
            sell_reason=sell_signal.get('reason', 'unknown'),
            urgency=sell_signal.get('urgency', 'medium'),
            success=execution_result.get('success', False),
            slippage_pct=execution_result.get('slippage_pct', 0),
            market_impact_pct=execution_result.get('market_impact_pct', 0)
        )
        
        # Add to history
        self.execution_history.append(metrics)
        
        # Performance alerts
        if execution_time_ms > self.target_execution_time_ms:
            self._add_performance_alert(
                f"SLOW_EXECUTION: {decision_data['symbol']} took {execution_time_ms:.1f}ms",
                'warning'
            )
        
        if metrics.success and metrics.profit_pct > 0:
            self._add_performance_alert(
                f"PROFIT_CAPTURED: {decision_data['symbol']} +{metrics.profit_pct:.3f}% (${metrics.profit_usd:.2f})",
                'success'
            )
        
        # Clean up
        del self.active_decisions[decision_id]
        
        logger.info(f"[SELL_MONITOR] Recorded: {decision_data['symbol']} - "
                   f"Decision: {decision_data.get('decision_time_ms', 0):.1f}ms, "
                   f"Execution: {execution_time_ms:.1f}ms, "
                   f"Profit: {metrics.profit_pct:.3f}%")
    
    def get_performance_stats(self, time_window_hours: int = 1) -> SellPerformanceStats:
        """Get performance statistics for specified time window"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        recent_executions = [
            m for m in self.execution_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_executions:
            return SellPerformanceStats()
        
        # Calculate statistics
        total_sells = len(recent_executions)
        successful_sells = sum(1 for m in recent_executions if m.success)
        
        decision_times = [m.decision_time_ms for m in recent_executions if m.decision_time_ms > 0]
        execution_times = [m.execution_time_ms for m in recent_executions if m.execution_time_ms > 0]
        profits = [m.profit_pct for m in recent_executions if m.success]
        
        stats = SellPerformanceStats(
            total_sells=total_sells,
            successful_sells=successful_sells,
            success_rate=successful_sells / total_sells if total_sells > 0 else 0,
            avg_decision_time_ms=statistics.mean(decision_times) if decision_times else 0,
            avg_execution_time_ms=statistics.mean(execution_times) if execution_times else 0,
            avg_profit_pct=statistics.mean(profits) if profits else 0,
            total_profit_usd=sum(m.profit_usd for m in recent_executions if m.success),
            avg_confidence=statistics.mean(m.confidence for m in recent_executions)
        )
        
        # Speed percentiles
        if decision_times:
            stats.speed_percentiles = {
                'p50_decision_ms': statistics.median(decision_times),
                'p95_decision_ms': statistics.quantiles(decision_times, n=20)[18] if len(decision_times) > 10 else max(decision_times),
                'p99_decision_ms': statistics.quantiles(decision_times, n=100)[98] if len(decision_times) > 50 else max(decision_times)
            }
        
        # Profit distribution
        profit_ranges = {
            'ultra_micro': (0.1, 0.3),
            'micro': (0.3, 0.5),
            'small': (0.5, 1.0),
            'medium': (1.0, 2.0),
            'large': (2.0, float('inf'))
        }
        
        stats.profit_distribution = {}
        for range_name, (min_pct, max_pct) in profit_ranges.items():
            count = sum(1 for p in profits if min_pct <= p < max_pct)
            stats.profit_distribution[range_name] = count
        
        return stats
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics"""
        stats_1h = self.get_performance_stats(1)
        stats_24h = self.get_performance_stats(24)
        
        # Performance grades
        decision_speed_grade = self._grade_performance(
            stats_1h.avg_decision_time_ms, 
            self.target_decision_time_ms, 
            self.critical_decision_time_ms,
            lower_is_better=True
        )
        
        success_rate_grade = self._grade_performance(
            stats_1h.success_rate,
            self.daily_targets['min_success_rate'],
            0.7,
            lower_is_better=False
        )
        
        profit_rate_grade = self._grade_performance(
            stats_1h.avg_profit_pct,
            self.daily_targets['min_profit_rate'],
            0.2,
            lower_is_better=False
        )
        
        return {
            'timestamp': datetime.now().isoformat(),
            'active_decisions': len(self.active_decisions),
            'recent_alerts': list(self.performance_alerts)[-5:],  # Last 5 alerts
            'performance_grades': {
                'decision_speed': decision_speed_grade,
                'success_rate': success_rate_grade,
                'profit_rate': profit_rate_grade
            },
            'stats_1h': {
                'total_sells': stats_1h.total_sells,
                'success_rate': stats_1h.success_rate,
                'avg_decision_time_ms': stats_1h.avg_decision_time_ms,
                'avg_profit_pct': stats_1h.avg_profit_pct,
                'total_profit_usd': stats_1h.total_profit_usd
            },
            'stats_24h': {
                'total_sells': stats_24h.total_sells,
                'success_rate': stats_24h.success_rate,
                'avg_decision_time_ms': stats_24h.avg_decision_time_ms,
                'avg_profit_pct': stats_24h.avg_profit_pct,
                'total_profit_usd': stats_24h.total_profit_usd
            },
            'speed_percentiles': stats_1h.speed_percentiles,
            'profit_distribution': stats_1h.profit_distribution
        }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on performance analysis"""
        recommendations = []
        stats = self.get_performance_stats(4)  # 4-hour window
        
        # Decision speed optimization
        if stats.avg_decision_time_ms > self.target_decision_time_ms:
            recommendations.append({
                'type': 'speed_optimization',
                'priority': 'high',
                'issue': f'Average decision time {stats.avg_decision_time_ms:.1f}ms > target {self.target_decision_time_ms}ms',
                'recommendation': 'Enable batch processing and parallel validation in sell logic',
                'implementation': 'Set batch_processing=True and parallel_validation=True in config'
            })
        
        # Success rate optimization
        if stats.success_rate < self.daily_targets['min_success_rate']:
            recommendations.append({
                'type': 'success_rate',
                'priority': 'high',
                'issue': f'Success rate {stats.success_rate:.1%} < target {self.daily_targets["min_success_rate"]:.1%}',
                'recommendation': 'Adjust confidence thresholds and market order usage',
                'implementation': 'Lower min_sell_confidence and use market orders for urgent sells'
            })
        
        # Profit optimization
        if stats.avg_profit_pct < self.daily_targets['min_profit_rate']:
            recommendations.append({
                'type': 'profit_optimization',
                'priority': 'medium',
                'issue': f'Average profit {stats.avg_profit_pct:.2f}% < target {self.daily_targets["min_profit_rate"]:.2f}%',
                'recommendation': 'Optimize profit taking levels for micro-profits',
                'implementation': 'Adjust take_profit_levels to [0.001, 0.002, 0.003, 0.005]'
            })
        
        # Ultra-fast execution opportunities
        fast_profits = sum(1 for m in self.execution_history 
                          if m.decision_time_ms + m.execution_time_ms < 200 and m.profit_pct > 0.1)
        total_recent = len([m for m in self.execution_history if m.timestamp >= datetime.now() - timedelta(hours=2)])
        
        if fast_profits / max(total_recent, 1) > 0.3:  # 30% are fast profitable
            recommendations.append({
                'type': 'ultra_fast_mode',
                'priority': 'low',
                'issue': f'{fast_profits}/{total_recent} sells are ultra-fast profitable',
                'recommendation': 'Enable ultra-fast mode for micro-profit captures',
                'implementation': 'Reduce max_hold_time_minutes to 2 and enable rapid_fire_mode'
            })
        
        return recommendations
    
    def _add_performance_alert(self, message: str, level: str) -> None:
        """Add performance alert"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        self.performance_alerts.append(alert)
        
        if level in ['warning', 'error']:
            logger.warning(f"[SELL_MONITOR] {level.upper()}: {message}")
        else:
            logger.info(f"[SELL_MONITOR] {level.upper()}: {message}")
    
    def _grade_performance(self, value: float, target: float, critical: float, 
                          lower_is_better: bool = True) -> str:
        """Grade performance metric"""
        if lower_is_better:
            if value <= target:
                return 'A'
            elif value <= target * 1.5:
                return 'B'
            elif value <= critical:
                return 'C'
            else:
                return 'F'
        else:
            if value >= target:
                return 'A'
            elif value >= target * 0.8:
                return 'B'
            elif value >= critical:
                return 'C'
            else:
                return 'F'
    
    def export_performance_data(self, hours: int = 24) -> Dict[str, Any]:
        """Export performance data for analysis"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_executions = [
            {
                'symbol': m.symbol,
                'timestamp': m.timestamp.isoformat(),
                'decision_time_ms': m.decision_time_ms,
                'execution_time_ms': m.execution_time_ms,
                'profit_pct': m.profit_pct,
                'profit_usd': m.profit_usd,
                'confidence': m.confidence,
                'sell_reason': m.sell_reason,
                'urgency': m.urgency,
                'success': m.success,
                'slippage_pct': m.slippage_pct
            }
            for m in self.execution_history 
            if m.timestamp >= cutoff_time
        ]
        
        return {
            'export_timestamp': datetime.now().isoformat(),
            'time_window_hours': hours,
            'total_executions': len(recent_executions),
            'executions': recent_executions,
            'performance_stats': self.get_performance_stats(hours).__dict__,
            'optimization_recommendations': self.get_optimization_recommendations()
        }