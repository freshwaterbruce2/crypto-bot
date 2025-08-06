"""
Performance Analytics Dashboard for Claude-Flow Trading System
Real-time monitoring and analytics for multi-agent trading performance
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime
    neural_accuracy: float
    execution_time: float
    success_rate: float
    portfolio_value: float
    liquid_balance: float
    agent_coordination_score: float
    reallocation_efficiency: float
    circuit_breaker_events: int
    trades_executed: int
    profit_loss: float

@dataclass
class AgentPerformance:
    """Individual agent performance metrics"""
    agent_id: str
    agent_type: str
    tasks_completed: int
    success_rate: float
    avg_execution_time: float
    error_count: int
    last_activity: datetime
    performance_score: float

class PerformanceDashboard:
    """Real-time performance analytics dashboard"""

    def __init__(self, swarm_id: str, neural_model_id: str):
        self.swarm_id = swarm_id
        self.neural_model_id = neural_model_id
        self.metrics_history: List[PerformanceMetrics] = []
        self.agent_performance: Dict[str, AgentPerformance] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.monitoring_active = False

        # Performance thresholds
        self.thresholds = {
            'neural_accuracy': 0.75,
            'execution_time': 5.0,
            'success_rate': 0.85,
            'reallocation_efficiency': 0.9,
            'agent_coordination': 0.8
        }

        # Dashboard state
        self.dashboard_data = {
            'last_update': None,
            'system_health': 'unknown',
            'performance_grade': 'unknown',
            'alerts_count': 0,
            'uptime': 0
        }

        self.start_time = time.time()

    async def start_monitoring(self, interval: float = 10.0):
        """Start real-time performance monitoring"""
        self.monitoring_active = True
        logger.info(f"[DASHBOARD] Starting performance monitoring (interval: {interval}s)")

        while self.monitoring_active:
            try:
                await self._collect_metrics()
                await self._update_dashboard()
                await self._check_alerts()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"[DASHBOARD] Monitoring error: {e}")
                await asyncio.sleep(5.0)

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        logger.info("[DASHBOARD] Performance monitoring stopped")

    async def _collect_metrics(self):
        """Collect current performance metrics"""
        try:
            # Simulate collection from claude-flow agents
            current_time = datetime.now()

            # Get neural model performance
            neural_performance = await self._get_neural_performance()

            # Get swarm performance
            swarm_metrics = await self._get_swarm_metrics()

            # Get trading performance
            trading_performance = await self._get_trading_performance()

            # Create performance snapshot
            metrics = PerformanceMetrics(
                timestamp=current_time,
                neural_accuracy=neural_performance.get('accuracy', 0.68),
                execution_time=swarm_metrics.get('avg_execution_time', 6.0),
                success_rate=swarm_metrics.get('success_rate', 0.81),
                portfolio_value=trading_performance.get('portfolio_value', 201.93),
                liquid_balance=trading_performance.get('liquid_balance', 5.0),
                agent_coordination_score=swarm_metrics.get('coordination_score', 0.85),
                reallocation_efficiency=trading_performance.get('reallocation_efficiency', 0.8),
                circuit_breaker_events=swarm_metrics.get('circuit_breaker_events', 0),
                trades_executed=trading_performance.get('trades_executed', 0),
                profit_loss=trading_performance.get('profit_loss', 0.0)
            )

            self.metrics_history.append(metrics)

            # Keep only last 1000 metrics for memory efficiency
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]

            logger.debug(f"[DASHBOARD] Collected metrics: accuracy={metrics.neural_accuracy:.3f}, "
                        f"execution_time={metrics.execution_time:.2f}s, "
                        f"success_rate={metrics.success_rate:.3f}")

        except Exception as e:
            logger.error(f"[DASHBOARD] Error collecting metrics: {e}")

    async def _get_neural_performance(self) -> Dict[str, Any]:
        """Get neural model performance metrics"""
        try:
            # Simulate neural performance query
            return {
                'accuracy': 0.68 + (time.time() % 100) * 0.001,  # Simulate improvement
                'training_epochs': 50,
                'learning_rate': 0.001,
                'loss': 0.32
            }
        except Exception as e:
            logger.error(f"[DASHBOARD] Neural performance query failed: {e}")
            return {'accuracy': 0.68, 'training_epochs': 0}

    async def _get_swarm_metrics(self) -> Dict[str, Any]:
        """Get swarm performance metrics"""
        try:
            # Simulate swarm metrics query
            return {
                'avg_execution_time': 6.0 - (time.time() % 60) * 0.02,  # Simulate improvement
                'success_rate': 0.81 + (time.time() % 30) * 0.005,  # Simulate improvement
                'coordination_score': 0.85,
                'circuit_breaker_events': 0,
                'active_agents': 4
            }
        except Exception as e:
            logger.error(f"[DASHBOARD] Swarm metrics query failed: {e}")
            return {'avg_execution_time': 6.0, 'success_rate': 0.81}

    async def _get_trading_performance(self) -> Dict[str, Any]:
        """Get trading performance metrics"""
        try:
            # Simulate trading performance query
            return {
                'portfolio_value': 201.93,
                'liquid_balance': 5.0,
                'reallocation_efficiency': 0.8,
                'trades_executed': int(time.time() % 100),
                'profit_loss': (time.time() % 1000) * 0.001
            }
        except Exception as e:
            logger.error(f"[DASHBOARD] Trading performance query failed: {e}")
            return {'portfolio_value': 201.93, 'liquid_balance': 5.0}

    async def _update_dashboard(self):
        """Update dashboard state"""
        try:
            if not self.metrics_history:
                return

            latest_metrics = self.metrics_history[-1]

            # Calculate system health
            health_score = self._calculate_health_score(latest_metrics)

            # Update dashboard data
            self.dashboard_data.update({
                'last_update': latest_metrics.timestamp,
                'system_health': self._get_health_status(health_score),
                'performance_grade': self._get_performance_grade(latest_metrics),
                'alerts_count': len(self.alerts),
                'uptime': time.time() - self.start_time
            })

        except Exception as e:
            logger.error(f"[DASHBOARD] Error updating dashboard: {e}")

    def _calculate_health_score(self, metrics: PerformanceMetrics) -> float:
        """Calculate overall system health score"""
        score = 0.0

        # Neural accuracy score
        if metrics.neural_accuracy >= self.thresholds['neural_accuracy']:
            score += 0.25
        else:
            score += 0.25 * (metrics.neural_accuracy / self.thresholds['neural_accuracy'])

        # Execution time score (lower is better)
        if metrics.execution_time <= self.thresholds['execution_time']:
            score += 0.25
        else:
            score += 0.25 * (self.thresholds['execution_time'] / metrics.execution_time)

        # Success rate score
        if metrics.success_rate >= self.thresholds['success_rate']:
            score += 0.25
        else:
            score += 0.25 * (metrics.success_rate / self.thresholds['success_rate'])

        # Agent coordination score
        if metrics.agent_coordination_score >= self.thresholds['agent_coordination']:
            score += 0.25
        else:
            score += 0.25 * (metrics.agent_coordination_score / self.thresholds['agent_coordination'])

        return min(1.0, score)

    def _get_health_status(self, health_score: float) -> str:
        """Get health status string"""
        if health_score >= 0.9:
            return 'excellent'
        elif health_score >= 0.8:
            return 'good'
        elif health_score >= 0.7:
            return 'fair'
        elif health_score >= 0.6:
            return 'poor'
        else:
            return 'critical'

    def _get_performance_grade(self, metrics: PerformanceMetrics) -> str:
        """Get performance grade"""
        score = 0

        # Grade based on multiple factors
        if metrics.neural_accuracy >= 0.75:
            score += 2
        elif metrics.neural_accuracy >= 0.7:
            score += 1

        if metrics.execution_time <= 5.0:
            score += 2
        elif metrics.execution_time <= 6.0:
            score += 1

        if metrics.success_rate >= 0.85:
            score += 2
        elif metrics.success_rate >= 0.8:
            score += 1

        if metrics.reallocation_efficiency >= 0.9:
            score += 2
        elif metrics.reallocation_efficiency >= 0.8:
            score += 1

        # Convert to grade
        if score >= 7:
            return 'A'
        elif score >= 6:
            return 'B+'
        elif score >= 5:
            return 'B'
        elif score >= 4:
            return 'C+'
        elif score >= 3:
            return 'C'
        else:
            return 'D'

    async def _check_alerts(self):
        """Check for performance alerts"""
        try:
            if not self.metrics_history:
                return

            latest_metrics = self.metrics_history[-1]
            new_alerts = []

            # Neural accuracy alert
            if latest_metrics.neural_accuracy < self.thresholds['neural_accuracy']:
                new_alerts.append({
                    'type': 'neural_accuracy',
                    'level': 'warning',
                    'message': f"Neural accuracy ({latest_metrics.neural_accuracy:.3f}) below threshold ({self.thresholds['neural_accuracy']:.3f})",
                    'timestamp': latest_metrics.timestamp
                })

            # Execution time alert
            if latest_metrics.execution_time > self.thresholds['execution_time']:
                new_alerts.append({
                    'type': 'execution_time',
                    'level': 'warning',
                    'message': f"Execution time ({latest_metrics.execution_time:.2f}s) above threshold ({self.thresholds['execution_time']:.2f}s)",
                    'timestamp': latest_metrics.timestamp
                })

            # Success rate alert
            if latest_metrics.success_rate < self.thresholds['success_rate']:
                new_alerts.append({
                    'type': 'success_rate',
                    'level': 'critical' if latest_metrics.success_rate < 0.7 else 'warning',
                    'message': f"Success rate ({latest_metrics.success_rate:.3f}) below threshold ({self.thresholds['success_rate']:.3f})",
                    'timestamp': latest_metrics.timestamp
                })

            # Circuit breaker alert
            if latest_metrics.circuit_breaker_events > 0:
                new_alerts.append({
                    'type': 'circuit_breaker',
                    'level': 'warning',
                    'message': f"Circuit breaker events detected: {latest_metrics.circuit_breaker_events}",
                    'timestamp': latest_metrics.timestamp
                })

            # Add new alerts
            self.alerts.extend(new_alerts)

            # Keep only last 100 alerts
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]

            # Log critical alerts
            for alert in new_alerts:
                if alert['level'] == 'critical':
                    logger.error(f"[DASHBOARD] CRITICAL ALERT: {alert['message']}")
                elif alert['level'] == 'warning':
                    logger.warning(f"[DASHBOARD] WARNING: {alert['message']}")

        except Exception as e:
            logger.error(f"[DASHBOARD] Error checking alerts: {e}")

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary"""
        try:
            if not self.metrics_history:
                return {'status': 'no_data', 'message': 'No metrics collected yet'}

            latest_metrics = self.metrics_history[-1]

            # Calculate trends
            trends = self._calculate_trends()

            return {
                'status': 'active',
                'last_update': latest_metrics.timestamp.isoformat(),
                'system_health': self.dashboard_data['system_health'],
                'performance_grade': self.dashboard_data['performance_grade'],
                'uptime_seconds': int(self.dashboard_data['uptime']),
                'current_metrics': {
                    'neural_accuracy': latest_metrics.neural_accuracy,
                    'execution_time': latest_metrics.execution_time,
                    'success_rate': latest_metrics.success_rate,
                    'portfolio_value': latest_metrics.portfolio_value,
                    'liquid_balance': latest_metrics.liquid_balance,
                    'agent_coordination': latest_metrics.agent_coordination_score,
                    'reallocation_efficiency': latest_metrics.reallocation_efficiency,
                    'trades_executed': latest_metrics.trades_executed
                },
                'trends': trends,
                'alerts_summary': {
                    'total_alerts': len(self.alerts),
                    'critical_alerts': len([a for a in self.alerts if a['level'] == 'critical']),
                    'warning_alerts': len([a for a in self.alerts if a['level'] == 'warning']),
                    'recent_alerts': self.alerts[-5:] if self.alerts else []
                },
                'thresholds': self.thresholds,
                'metrics_collected': len(self.metrics_history)
            }

        except Exception as e:
            logger.error(f"[DASHBOARD] Error getting dashboard summary: {e}")
            return {'status': 'error', 'message': str(e)}

    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate performance trends"""
        try:
            if len(self.metrics_history) < 10:
                return {'insufficient_data': 'true'}

            # Get recent metrics for trend calculation
            recent_metrics = self.metrics_history[-10:]
            older_metrics = self.metrics_history[-20:-10] if len(self.metrics_history) >= 20 else recent_metrics[:5]

            trends = {}

            # Neural accuracy trend
            recent_accuracy = sum(m.neural_accuracy for m in recent_metrics) / len(recent_metrics)
            older_accuracy = sum(m.neural_accuracy for m in older_metrics) / len(older_metrics)
            trends['neural_accuracy'] = 'improving' if recent_accuracy > older_accuracy else 'declining'

            # Execution time trend
            recent_time = sum(m.execution_time for m in recent_metrics) / len(recent_metrics)
            older_time = sum(m.execution_time for m in older_metrics) / len(older_metrics)
            trends['execution_time'] = 'improving' if recent_time < older_time else 'declining'

            # Success rate trend
            recent_success = sum(m.success_rate for m in recent_metrics) / len(recent_metrics)
            older_success = sum(m.success_rate for m in older_metrics) / len(older_metrics)
            trends['success_rate'] = 'improving' if recent_success > older_success else 'declining'

            return trends

        except Exception as e:
            logger.error(f"[DASHBOARD] Error calculating trends: {e}")
            return {'error': 'trend_calculation_failed'}

# Global dashboard instance
_dashboard = None

def get_dashboard(swarm_id: str = None, neural_model_id: str = None) -> PerformanceDashboard:
    """Get or create dashboard instance"""
    global _dashboard

    if _dashboard is None:
        _dashboard = PerformanceDashboard(
            swarm_id=swarm_id or "swarm_1752495725359_0an5zsd30",
            neural_model_id=neural_model_id or "model_optimization_1752495806047"
        )

    return _dashboard

async def start_dashboard_monitoring(interval: float = 10.0):
    """Start dashboard monitoring"""
    dashboard = get_dashboard()
    await dashboard.start_monitoring(interval)

def stop_dashboard_monitoring():
    """Stop dashboard monitoring"""
    global _dashboard
    if _dashboard:
        _dashboard.stop_monitoring()
