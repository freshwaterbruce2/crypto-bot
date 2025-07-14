"""
Logging Analytics Assistant
Provides comprehensive logging analysis and performance monitoring for the trading bot
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class LoggingAnalyticsAssistant:
    """
    Advanced logging analytics and performance monitoring assistant
    Analyzes bot performance, error patterns, and system health metrics
    """
    
    def __init__(self, trade_executor=None):
        """Initialize logging analytics assistant"""
        self.trade_executor = trade_executor
        self.logger = logger
        
        # Analytics storage
        self.performance_metrics = {}
        self.error_patterns = defaultdict(int)
        self.system_health = {}
        self.trading_analytics = {}
        
        # Log processing
        self.log_buffer = deque(maxlen=10000)  # Keep last 10k log entries
        self.processed_logs = 0
        self.last_analysis_time = datetime.now()
        
        # Alert thresholds
        self.error_rate_threshold = 0.1  # 10% error rate
        self.performance_degradation_threshold = 0.2  # 20% performance drop
        self.memory_usage_threshold = 0.8  # 80% memory usage
        
        # Analytics configuration
        self.analysis_interval = 300  # 5 minutes
        self.retention_hours = 24  # 24 hours of detailed analytics
        self.alert_cooldown = 600  # 10 minutes between same alerts
        
        # Metrics tracking
        self.metrics_history = {
            'trade_performance': deque(maxlen=288),  # 24h at 5min intervals
            'error_rates': deque(maxlen=288),
            'system_performance': deque(maxlen=288),
            'bot_health_scores': deque(maxlen=288)
        }
        
        # Alert state
        self.last_alerts = {}
        self.alert_count = 0
        
        self.logger.info("[ANALYTICS] Assistant initialized")
    
    async def initialize(self):
        """Initialize analytics system"""
        try:
            # Start log monitoring
            asyncio.create_task(self._log_monitoring_loop())
            
            # Start analytics processing
            asyncio.create_task(self._analytics_processing_loop())
            
            # Start health monitoring
            asyncio.create_task(self._health_monitoring_loop())
            
            self.logger.info("[ANALYTICS] Analytics system started")
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error initializing analytics: {e}")
    
    async def process_log_entry(self, log_entry: Dict[str, Any]):
        """Process a single log entry for analytics"""
        try:
            # Add to buffer
            log_entry['processed_timestamp'] = datetime.now()
            self.log_buffer.append(log_entry)
            self.processed_logs += 1
            
            # Extract key information
            level = log_entry.get('level', 'INFO')
            message = log_entry.get('message', '')
            component = log_entry.get('component', 'unknown')
            
            # Track error patterns
            if level in ['ERROR', 'CRITICAL']:
                self._track_error_pattern(message, component)
            
            # Track performance metrics
            if 'execution_time' in message or 'latency' in message:
                self._extract_performance_metrics(message, component)
            
            # Track trading activity
            if any(keyword in message.lower() for keyword in ['trade', 'buy', 'sell', 'profit', 'loss']):
                self._track_trading_activity(message, component, log_entry.get('timestamp'))
            
            # Track system health indicators
            if any(keyword in message.lower() for keyword in ['memory', 'cpu', 'connection', 'websocket']):
                self._track_system_health(message, component)
                
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error processing log entry: {e}")
    
    async def log_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Log a specific event for analytics tracking
        Called by AssistantManager and other components
        """
        try:
            # Create standardized log entry
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'event_type': event_type,
                'message': f"Event: {event_type}",
                'component': 'trading_system',
                'event_data': event_data
            }
            
            # Process the log entry
            await self.process_log_entry(log_entry)
            
            # Special handling for trading events
            if event_type.startswith('trade_'):
                await self._handle_trading_event(event_type, event_data)
            
            # Special handling for performance events
            elif event_type.startswith('performance_'):
                await self._handle_performance_event(event_type, event_data)
            
            # Special handling for error events
            elif event_type.startswith('error_'):
                await self._handle_error_event(event_type, event_data)
            
            self.logger.debug(f"[ANALYTICS] Logged event: {event_type}")
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error logging event {event_type}: {e}")
    
    async def _handle_trading_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle trading-specific events"""
        try:
            if event_type == 'trade_successful_trade':
                # Track successful trade metrics
                symbol = event_data.get('symbol', 'unknown')
                amount = event_data.get('amount', 0)
                execution_time = event_data.get('execution_time_ms', 0)
                
                # Update trading analytics
                if symbol not in self.trading_analytics:
                    self.trading_analytics[symbol] = {
                        'total_trades': 0,
                        'successful_trades': 0,
                        'total_volume': 0,
                        'avg_execution_time': 0
                    }
                
                self.trading_analytics[symbol]['total_trades'] += 1
                self.trading_analytics[symbol]['successful_trades'] += 1
                self.trading_analytics[symbol]['total_volume'] += amount
                
                # Update average execution time
                current_avg = self.trading_analytics[symbol]['avg_execution_time']
                trade_count = self.trading_analytics[symbol]['total_trades']
                self.trading_analytics[symbol]['avg_execution_time'] = (
                    (current_avg * (trade_count - 1) + execution_time) / trade_count
                )
                
            elif event_type == 'trade_failed_trade':
                # Track failed trade metrics
                symbol = event_data.get('symbol', 'unknown')
                error = event_data.get('error', 'unknown_error')
                
                # Track error patterns
                self.error_patterns[f"trade_error_{error}"] += 1
                
                # Update trading analytics
                if symbol not in self.trading_analytics:
                    self.trading_analytics[symbol] = {
                        'total_trades': 0,
                        'successful_trades': 0,
                        'failed_trades': 0,
                        'total_volume': 0
                    }
                
                self.trading_analytics[symbol]['total_trades'] += 1
                self.trading_analytics[symbol]['failed_trades'] = (
                    self.trading_analytics[symbol].get('failed_trades', 0) + 1
                )
                
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error handling trading event: {e}")
    
    async def _handle_performance_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle performance-specific events"""
        try:
            # Track performance metrics
            if 'latency' in event_data:
                if 'latency_metrics' not in self.performance_metrics:
                    self.performance_metrics['latency_metrics'] = deque(maxlen=1000)
                self.performance_metrics['latency_metrics'].append(event_data['latency'])
            
            if 'throughput' in event_data:
                if 'throughput_metrics' not in self.performance_metrics:
                    self.performance_metrics['throughput_metrics'] = deque(maxlen=1000)
                self.performance_metrics['throughput_metrics'].append(event_data['throughput'])
                
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error handling performance event: {e}")
    
    async def _handle_error_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle error-specific events"""
        try:
            error_message = event_data.get('error', 'unknown_error')
            component = event_data.get('component', 'unknown')
            
            # Track error patterns
            error_key = f"{component}_{error_message}"
            self.error_patterns[error_key] += 1
            
            # Check if this is a critical error pattern
            if self.error_patterns[error_key] > 5:  # More than 5 occurrences
                await self._generate_error_alert(error_key, self.error_patterns[error_key])
                
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error handling error event: {e}")
    
    async def _generate_error_alert(self, error_key: str, occurrence_count: int):
        """Generate alert for repeated error patterns"""
        try:
            alert_key = f"error_pattern_{error_key}"
            current_time = datetime.now()
            
            # Check cooldown period
            if alert_key in self.last_alerts:
                time_since_last = (current_time - self.last_alerts[alert_key]).total_seconds()
                if time_since_last < self.alert_cooldown:
                    return
            
            self.last_alerts[alert_key] = current_time
            self.alert_count += 1
            
            self.logger.warning(
                f"[ANALYTICS] ALERT: Error pattern '{error_key}' occurred {occurrence_count} times. "
                f"Consider investigating this issue."
            )
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error generating error alert: {e}")
    
    async def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filter recent logs
            recent_logs = [
                entry for entry in self.log_buffer
                if entry.get('processed_timestamp', datetime.min) > cutoff_time
            ]
            
            # Calculate metrics
            total_logs = len(recent_logs)
            error_logs = len([log for log in recent_logs if log.get('level') in ['ERROR', 'CRITICAL']])
            warning_logs = len([log for log in recent_logs if log.get('level') == 'WARNING'])
            
            error_rate = error_logs / max(total_logs, 1)
            warning_rate = warning_logs / max(total_logs, 1)
            
            # Trading performance
            trading_metrics = await self._calculate_trading_metrics(recent_logs)
            
            # System performance
            system_metrics = self._calculate_system_metrics(recent_logs)
            
            # Component analysis
            component_analysis = self._analyze_components(recent_logs)
            
            # Error analysis
            error_analysis = self._analyze_errors(recent_logs)
            
            report = {
                'report_period': f"{hours} hours",
                'generated_at': datetime.now().isoformat(),
                'overview': {
                    'total_log_entries': total_logs,
                    'error_rate': error_rate,
                    'warning_rate': warning_rate,
                    'logs_processed': self.processed_logs,
                    'health_score': self._calculate_health_score(error_rate, system_metrics)
                },
                'trading_performance': trading_metrics,
                'system_performance': system_metrics,
                'component_analysis': component_analysis,
                'error_analysis': error_analysis,
                'alerts_generated': self.alert_count,
                'recommendations': self._generate_recommendations(error_rate, trading_metrics, system_metrics)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error generating performance report: {e}")
            return {}
    
    async def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in bot behavior"""
        try:
            anomalies = []
            
            # Error rate anomaly
            recent_error_rates = list(self.metrics_history['error_rates'])[-12:]  # Last hour
            if recent_error_rates:
                avg_error_rate = sum(recent_error_rates) / len(recent_error_rates)
                if avg_error_rate > self.error_rate_threshold:
                    anomalies.append({
                        'type': 'high_error_rate',
                        'severity': 'high',
                        'value': avg_error_rate,
                        'threshold': self.error_rate_threshold,
                        'description': f"Error rate {avg_error_rate:.2%} exceeds threshold {self.error_rate_threshold:.2%}"
                    })
            
            # Performance degradation
            recent_performance = list(self.metrics_history['trade_performance'])[-12:]
            if len(recent_performance) >= 6:
                recent_avg = sum(recent_performance[-6:]) / 6
                baseline_avg = sum(recent_performance[-12:-6]) / 6
                
                if baseline_avg > 0 and (baseline_avg - recent_avg) / baseline_avg > self.performance_degradation_threshold:
                    anomalies.append({
                        'type': 'performance_degradation',
                        'severity': 'medium',
                        'recent_performance': recent_avg,
                        'baseline_performance': baseline_avg,
                        'degradation_pct': (baseline_avg - recent_avg) / baseline_avg,
                        'description': f"Performance degraded by {((baseline_avg - recent_avg) / baseline_avg):.2%}"
                    })
            
            # System health anomalies
            health_scores = list(self.metrics_history['bot_health_scores'])[-6:]  # Last 30 minutes
            if health_scores:
                avg_health = sum(health_scores) / len(health_scores)
                if avg_health < 0.7:  # Health score below 70%
                    anomalies.append({
                        'type': 'poor_system_health',
                        'severity': 'high',
                        'health_score': avg_health,
                        'description': f"System health score {avg_health:.2%} is concerning"
                    })
            
            # Trading activity anomalies
            trading_anomalies = await self._detect_trading_anomalies()
            anomalies.extend(trading_anomalies)
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error detecting anomalies: {e}")
            return []
    
    async def get_error_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most common error patterns"""
        try:
            # Sort error patterns by frequency
            sorted_patterns = sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)
            
            patterns = []
            for pattern, count in sorted_patterns[:limit]:
                # Analyze pattern details
                pattern_analysis = self._analyze_error_pattern(pattern)
                
                patterns.append({
                    'pattern': pattern,
                    'count': count,
                    'severity': pattern_analysis.get('severity', 'medium'),
                    'component': pattern_analysis.get('component', 'unknown'),
                    'category': pattern_analysis.get('category', 'general'),
                    'recommended_action': pattern_analysis.get('action', 'investigate'),
                    'last_occurrence': pattern_analysis.get('last_seen', 'unknown')
                })
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error getting error patterns: {e}")
            return []
    
    async def get_component_health(self) -> Dict[str, Any]:
        """Get health status of bot components"""
        try:
            component_health = {}
            
            # Analyze each component
            components = ['exchange', 'websocket', 'balance_manager', 'trade_executor', 
                         'infinity_manager', 'strategy_manager', 'risk_manager']
            
            for component in components:
                component_logs = [
                    log for log in self.log_buffer
                    if component.lower() in log.get('component', '').lower() or 
                       component.lower() in log.get('message', '').lower()
                ]
                
                if component_logs:
                    # Calculate component metrics
                    total_logs = len(component_logs)
                    error_logs = len([log for log in component_logs if log.get('level') in ['ERROR', 'CRITICAL']])
                    warning_logs = len([log for log in component_logs if log.get('level') == 'WARNING'])
                    
                    error_rate = error_logs / max(total_logs, 1)
                    warning_rate = warning_logs / max(total_logs, 1)
                    
                    # Determine health status
                    if error_rate > 0.2:
                        status = 'critical'
                        health_score = 0.3
                    elif error_rate > 0.1:
                        status = 'warning'
                        health_score = 0.6
                    elif warning_rate > 0.3:
                        status = 'degraded'
                        health_score = 0.7
                    else:
                        status = 'healthy'
                        health_score = 0.9
                    
                    component_health[component] = {
                        'status': status,
                        'health_score': health_score,
                        'error_rate': error_rate,
                        'warning_rate': warning_rate,
                        'total_logs': total_logs,
                        'last_activity': component_logs[-1].get('processed_timestamp', datetime.now()).isoformat()
                    }
                else:
                    component_health[component] = {
                        'status': 'inactive',
                        'health_score': 0.0,
                        'error_rate': 0.0,
                        'warning_rate': 0.0,
                        'total_logs': 0,
                        'last_activity': None
                    }
            
            return component_health
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error getting component health: {e}")
            return {}
    
    def _track_error_pattern(self, message: str, component: str):
        """Track error patterns for analysis"""
        try:
            # Extract error pattern
            pattern = self._extract_error_pattern(message)
            self.error_patterns[f"{component}:{pattern}"] += 1
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error tracking error pattern: {e}")
    
    def _extract_error_pattern(self, message: str) -> str:
        """Extract error pattern from message"""
        try:
            # Remove specific values and create pattern
            pattern = re.sub(r'\d+\.\d+', '[NUMBER]', message)  # Replace decimals
            pattern = re.sub(r'\d+', '[NUMBER]', pattern)  # Replace integers
            pattern = re.sub(r"'[^']*'", '[STRING]', pattern)  # Replace quoted strings
            pattern = re.sub(r'"[^"]*"', '[STRING]', pattern)  # Replace double-quoted strings
            pattern = re.sub(r'\b[A-Z0-9]{8,}\b', '[ID]', pattern)  # Replace IDs/hashes
            
            # Truncate very long patterns
            if len(pattern) > 200:
                pattern = pattern[:200] + '...'
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error extracting error pattern: {e}")
            return message[:100]  # Fallback
    
    def _extract_performance_metrics(self, message: str, component: str):
        """Extract performance metrics from log messages"""
        try:
            # Extract execution time
            time_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ms|seconds?|s)', message.lower())
            if time_match:
                execution_time = float(time_match.group(1))
                if 'ms' in message.lower():
                    execution_time = execution_time / 1000  # Convert to seconds
                
                if component not in self.performance_metrics:
                    self.performance_metrics[component] = []
                
                self.performance_metrics[component].append({
                    'timestamp': datetime.now(),
                    'execution_time': execution_time,
                    'message': message
                })
                
                # Keep only recent metrics
                cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
                self.performance_metrics[component] = [
                    metric for metric in self.performance_metrics[component]
                    if metric['timestamp'] > cutoff_time
                ]
                
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error extracting performance metrics: {e}")
    
    def _track_trading_activity(self, message: str, component: str, timestamp: str):
        """Track trading activity metrics"""
        try:
            activity_type = None
            
            # Detect activity type
            if any(keyword in message.lower() for keyword in ['buy', 'bought', 'purchase']):
                activity_type = 'buy'
            elif any(keyword in message.lower() for keyword in ['sell', 'sold', 'exit']):
                activity_type = 'sell'
            elif any(keyword in message.lower() for keyword in ['profit', 'gain']):
                activity_type = 'profit'
            elif any(keyword in message.lower() for keyword in ['loss', 'stop']):
                activity_type = 'loss'
            
            if activity_type:
                if 'trading_activity' not in self.trading_analytics:
                    self.trading_analytics['trading_activity'] = []
                
                # Extract numeric values
                numbers = re.findall(r'\d+\.\d+', message)
                
                activity_record = {
                    'timestamp': timestamp or datetime.now().isoformat(),
                    'type': activity_type,
                    'component': component,
                    'message': message,
                    'values': numbers
                }
                
                self.trading_analytics['trading_activity'].append(activity_record)
                
                # Keep only recent activities
                cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
                self.trading_analytics['trading_activity'] = [
                    activity for activity in self.trading_analytics['trading_activity']
                    if datetime.fromisoformat(activity['timestamp']) > cutoff_time
                ]
                
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error tracking trading activity: {e}")
    
    def _track_system_health(self, message: str, component: str):
        """Track system health indicators"""
        try:
            health_indicators = {}
            
            # Memory usage
            memory_match = re.search(r'memory.*?(\d+(?:\.\d+)?)%', message.lower())
            if memory_match:
                health_indicators['memory_usage'] = float(memory_match.group(1)) / 100
            
            # CPU usage
            cpu_match = re.search(r'cpu.*?(\d+(?:\.\d+)?)%', message.lower())
            if cpu_match:
                health_indicators['cpu_usage'] = float(cpu_match.group(1)) / 100
            
            # Connection status
            if any(keyword in message.lower() for keyword in ['connected', 'connection established']):
                health_indicators['connection_status'] = 'good'
            elif any(keyword in message.lower() for keyword in ['disconnected', 'connection failed', 'timeout']):
                health_indicators['connection_status'] = 'poor'
            
            if health_indicators:
                timestamp = datetime.now()
                self.system_health[timestamp] = {
                    'component': component,
                    'indicators': health_indicators,
                    'message': message
                }
                
                # Cleanup old health data
                cutoff_time = timestamp - timedelta(hours=self.retention_hours)
                self.system_health = {
                    ts: data for ts, data in self.system_health.items()
                    if ts > cutoff_time
                }
                
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error tracking system health: {e}")
    
    async def _calculate_trading_metrics(self, recent_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trading performance metrics"""
        try:
            trading_logs = [
                log for log in recent_logs
                if any(keyword in log.get('message', '').lower() 
                      for keyword in ['trade', 'buy', 'sell', 'profit', 'loss'])
            ]
            
            metrics = {
                'total_trading_events': len(trading_logs),
                'buy_signals': len([log for log in trading_logs if 'buy' in log.get('message', '').lower()]),
                'sell_signals': len([log for log in trading_logs if 'sell' in log.get('message', '').lower()]),
                'profit_events': len([log for log in trading_logs if 'profit' in log.get('message', '').lower()]),
                'loss_events': len([log for log in trading_logs if 'loss' in log.get('message', '').lower()]),
                'error_rate_trading': 0.0,
                'avg_response_time': 0.0
            }
            
            # Calculate error rate for trading operations
            trading_errors = len([log for log in trading_logs if log.get('level') in ['ERROR', 'CRITICAL']])
            if len(trading_logs) > 0:
                metrics['error_rate_trading'] = trading_errors / len(trading_logs)
            
            # Calculate average response time for trading operations
            response_times = []
            for log in trading_logs:
                time_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ms|milliseconds)', log.get('message', ''))
                if time_match:
                    response_times.append(float(time_match.group(1)))
            
            if response_times:
                metrics['avg_response_time'] = sum(response_times) / len(response_times)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error calculating trading metrics: {e}")
            return {}
    
    def _calculate_system_metrics(self, recent_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate system performance metrics"""
        try:
            # Extract system-related logs
            system_logs = [
                log for log in recent_logs
                if any(keyword in log.get('message', '').lower() 
                      for keyword in ['memory', 'cpu', 'connection', 'websocket', 'api'])
            ]
            
            metrics = {
                'total_system_events': len(system_logs),
                'connection_events': len([log for log in system_logs if 'connection' in log.get('message', '').lower()]),
                'websocket_events': len([log for log in system_logs if 'websocket' in log.get('message', '').lower()]),
                'api_events': len([log for log in system_logs if 'api' in log.get('message', '').lower()]),
                'system_error_rate': 0.0,
                'avg_system_latency': 0.0
            }
            
            # Calculate system error rate
            system_errors = len([log for log in system_logs if log.get('level') in ['ERROR', 'CRITICAL']])
            if len(system_logs) > 0:
                metrics['system_error_rate'] = system_errors / len(system_logs)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error calculating system metrics: {e}")
            return {}
    
    def _analyze_components(self, recent_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance by component"""
        try:
            component_analysis = {}
            
            # Group logs by component
            components = defaultdict(list)
            for log in recent_logs:
                component = log.get('component', 'unknown')
                components[component].append(log)
            
            for component, logs in components.items():
                error_logs = len([log for log in logs if log.get('level') in ['ERROR', 'CRITICAL']])
                warning_logs = len([log for log in logs if log.get('level') == 'WARNING'])
                
                component_analysis[component] = {
                    'total_logs': len(logs),
                    'error_count': error_logs,
                    'warning_count': warning_logs,
                    'error_rate': error_logs / max(len(logs), 1),
                    'warning_rate': warning_logs / max(len(logs), 1),
                    'activity_level': 'high' if len(logs) > 100 else 'medium' if len(logs) > 20 else 'low'
                }
            
            return component_analysis
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error analyzing components: {e}")
            return {}
    
    def _analyze_errors(self, recent_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze error patterns and trends"""
        try:
            error_logs = [log for log in recent_logs if log.get('level') in ['ERROR', 'CRITICAL']]
            
            if not error_logs:
                return {'total_errors': 0, 'error_categories': {}, 'trending_errors': []}
            
            # Categorize errors
            error_categories = defaultdict(int)
            for log in error_logs:
                message = log.get('message', '').lower()
                
                if any(keyword in message for keyword in ['connection', 'network', 'timeout']):
                    error_categories['connectivity'] += 1
                elif any(keyword in message for keyword in ['balance', 'insufficient', 'funds']):
                    error_categories['balance'] += 1
                elif any(keyword in message for keyword in ['api', 'rate limit', 'request']):
                    error_categories['api'] += 1
                elif any(keyword in message for keyword in ['websocket', 'subscription']):
                    error_categories['websocket'] += 1
                elif any(keyword in message for keyword in ['trade', 'order', 'execution']):
                    error_categories['trading'] += 1
                else:
                    error_categories['other'] += 1
            
            # Find trending errors (errors that have increased recently)
            trending_errors = []
            for pattern, count in self.error_patterns.items():
                if count > 5:  # Only consider patterns with multiple occurrences
                    trending_errors.append({
                        'pattern': pattern,
                        'count': count,
                        'trend': 'increasing' if count > 3 else 'stable'
                    })
            
            return {
                'total_errors': len(error_logs),
                'error_categories': dict(error_categories),
                'trending_errors': sorted(trending_errors, key=lambda x: x['count'], reverse=True)[:10]
            }
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error analyzing errors: {e}")
            return {}
    
    def _calculate_health_score(self, error_rate: float, system_metrics: Dict[str, Any]) -> float:
        """Calculate overall health score"""
        try:
            health_score = 1.0
            
            # Penalize for high error rate
            health_score -= error_rate * 0.5
            
            # Penalize for system issues
            system_error_rate = system_metrics.get('system_error_rate', 0)
            health_score -= system_error_rate * 0.3
            
            # Bonus for activity (shows bot is running)
            if system_metrics.get('total_system_events', 0) > 10:
                health_score += 0.1
            
            return max(0.0, min(1.0, health_score))
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error calculating health score: {e}")
            return 0.5
    
    def _generate_recommendations(self, error_rate: float, trading_metrics: Dict[str, Any], 
                                system_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis"""
        try:
            recommendations = []
            
            # Error rate recommendations
            if error_rate > 0.1:
                recommendations.append("High error rate detected. Review error patterns and implement fixes.")
            
            # Trading performance recommendations
            trading_error_rate = trading_metrics.get('error_rate_trading', 0)
            if trading_error_rate > 0.05:
                recommendations.append("Trading operations experiencing errors. Check exchange connectivity and API limits.")
            
            # System performance recommendations
            system_error_rate = system_metrics.get('system_error_rate', 0)
            if system_error_rate > 0.15:
                recommendations.append("System components experiencing issues. Check WebSocket connections and API status.")
            
            # Activity recommendations
            if trading_metrics.get('total_trading_events', 0) < 5:
                recommendations.append("Low trading activity detected. Verify market conditions and strategy parameters.")
            
            if not recommendations:
                recommendations.append("System appears to be operating normally. Continue monitoring.")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error generating recommendations: {e}")
            return ["Error generating recommendations. Check analytics system."]
    
    def _analyze_error_pattern(self, pattern: str) -> Dict[str, Any]:
        """Analyze specific error pattern"""
        try:
            analysis = {
                'severity': 'medium',
                'component': 'unknown',
                'category': 'general',
                'action': 'investigate'
            }
            
            pattern_lower = pattern.lower()
            
            # Determine severity
            if any(keyword in pattern_lower for keyword in ['critical', 'fatal', 'failed to start']):
                analysis['severity'] = 'critical'
            elif any(keyword in pattern_lower for keyword in ['error', 'exception', 'failed']):
                analysis['severity'] = 'high'
            elif any(keyword in pattern_lower for keyword in ['warning', 'retry', 'timeout']):
                analysis['severity'] = 'medium'
            else:
                analysis['severity'] = 'low'
            
            # Determine component
            if 'exchange' in pattern_lower:
                analysis['component'] = 'exchange'
            elif 'websocket' in pattern_lower:
                analysis['component'] = 'websocket'
            elif 'balance' in pattern_lower:
                analysis['component'] = 'balance_manager'
            elif 'trade' in pattern_lower or 'executor' in pattern_lower:
                analysis['component'] = 'trade_executor'
            
            # Determine category and action
            if 'connection' in pattern_lower or 'network' in pattern_lower:
                analysis['category'] = 'connectivity'
                analysis['action'] = 'check_network_connection'
            elif 'api' in pattern_lower or 'rate limit' in pattern_lower:
                analysis['category'] = 'api'
                analysis['action'] = 'review_api_usage'
            elif 'balance' in pattern_lower or 'insufficient' in pattern_lower:
                analysis['category'] = 'balance'
                analysis['action'] = 'check_account_balance'
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error analyzing error pattern: {e}")
            return {'severity': 'unknown', 'component': 'unknown', 'category': 'unknown', 'action': 'investigate'}
    
    async def _detect_trading_anomalies(self) -> List[Dict[str, Any]]:
        """Detect trading-specific anomalies"""
        try:
            anomalies = []
            
            # Check for trading inactivity
            recent_trading = self.trading_analytics.get('trading_activity', [])
            recent_trading = [
                activity for activity in recent_trading
                if datetime.fromisoformat(activity['timestamp']) > datetime.now() - timedelta(hours=1)
            ]
            
            if len(recent_trading) == 0:
                anomalies.append({
                    'type': 'no_trading_activity',
                    'severity': 'medium',
                    'description': "No trading activity detected in the last hour"
                })
            
            # Check for excessive errors in trading
            trading_errors = [
                activity for activity in recent_trading
                if 'error' in activity.get('message', '').lower()
            ]
            
            if len(trading_errors) > len(recent_trading) * 0.3:  # >30% error rate
                anomalies.append({
                    'type': 'high_trading_error_rate',
                    'severity': 'high',
                    'error_count': len(trading_errors),
                    'total_activities': len(recent_trading),
                    'description': f"High trading error rate: {len(trading_errors)}/{len(recent_trading)} operations failed"
                })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error detecting trading anomalies: {e}")
            return []
    
    async def _log_monitoring_loop(self):
        """Main log monitoring loop"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # This would integrate with actual log monitoring
                # For now, it's a placeholder for the monitoring infrastructure
                
            except Exception as e:
                self.logger.error(f"[ANALYTICS] Error in log monitoring loop: {e}")
    
    async def _analytics_processing_loop(self):
        """Main analytics processing loop"""
        while True:
            try:
                await asyncio.sleep(self.analysis_interval)
                
                # Update metrics history
                current_time = datetime.now()
                
                # Calculate current metrics
                error_rate = self._calculate_current_error_rate()
                trade_performance = self._calculate_current_trade_performance()
                system_performance = self._calculate_current_system_performance()
                health_score = self._calculate_health_score(error_rate, {'system_error_rate': 0})
                
                # Add to history
                self.metrics_history['error_rates'].append(error_rate)
                self.metrics_history['trade_performance'].append(trade_performance)
                self.metrics_history['system_performance'].append(system_performance)
                self.metrics_history['bot_health_scores'].append(health_score)
                
                # Check for anomalies
                anomalies = await self.detect_anomalies()
                if anomalies:
                    await self._handle_anomalies(anomalies)
                
                self.last_analysis_time = current_time
                
            except Exception as e:
                self.logger.error(f"[ANALYTICS] Error in analytics processing loop: {e}")
    
    async def _health_monitoring_loop(self):
        """Health monitoring loop"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Monitor system health
                health_report = await self.get_component_health()
                
                # Check for critical issues
                critical_components = [
                    comp for comp, health in health_report.items()
                    if health.get('status') == 'critical'
                ]
                
                if critical_components and self._should_send_alert('critical_components'):
                    self.logger.error(f"[ANALYTICS] Critical components detected: {critical_components}")
                    self.alert_count += 1
                
            except Exception as e:
                self.logger.error(f"[ANALYTICS] Error in health monitoring loop: {e}")
    
    def _calculate_current_error_rate(self) -> float:
        """Calculate current error rate"""
        try:
            recent_logs = [
                log for log in self.log_buffer
                if log.get('processed_timestamp', datetime.min) > datetime.now() - timedelta(minutes=5)
            ]
            
            if not recent_logs:
                return 0.0
            
            error_logs = [log for log in recent_logs if log.get('level') in ['ERROR', 'CRITICAL']]
            return len(error_logs) / len(recent_logs)
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error calculating current error rate: {e}")
            return 0.0
    
    def _calculate_current_trade_performance(self) -> float:
        """Calculate current trade performance score"""
        try:
            # This would calculate a performance score based on recent trading activity
            # For now, return a placeholder value
            return 0.8
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error calculating trade performance: {e}")
            return 0.0
    
    def _calculate_current_system_performance(self) -> float:
        """Calculate current system performance score"""
        try:
            # This would calculate system performance based on latency, throughput, etc.
            # For now, return a placeholder value
            return 0.9
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error calculating system performance: {e}")
            return 0.0
    
    def _should_send_alert(self, alert_type: str) -> bool:
        """Check if an alert should be sent (respecting cooldown)"""
        try:
            current_time = datetime.now()
            last_alert_time = self.last_alerts.get(alert_type, datetime.min)
            
            if (current_time - last_alert_time).total_seconds() > self.alert_cooldown:
                self.last_alerts[alert_type] = current_time
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error checking alert cooldown: {e}")
            return False
    
    async def _handle_anomalies(self, anomalies: List[Dict[str, Any]]):
        """Handle detected anomalies"""
        try:
            for anomaly in anomalies:
                severity = anomaly.get('severity', 'medium')
                anomaly_type = anomaly.get('type', 'unknown')
                
                if severity == 'high' and self._should_send_alert(anomaly_type):
                    self.logger.error(f"[ANALYTICS] High severity anomaly: {anomaly['description']}")
                    self.alert_count += 1
                elif severity == 'medium' and self._should_send_alert(anomaly_type):
                    self.logger.warning(f"[ANALYTICS] Medium severity anomaly: {anomaly['description']}")
                    self.alert_count += 1
                
        except Exception as e:
            self.logger.error(f"[ANALYTICS] Error handling anomalies: {e}")
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get summary of analytics system status"""
        return {
            'processed_logs': self.processed_logs,
            'buffer_size': len(self.log_buffer),
            'error_patterns_tracked': len(self.error_patterns),
            'components_monitored': len(self.performance_metrics),
            'alerts_generated': self.alert_count,
            'last_analysis': self.last_analysis_time.isoformat(),
            'system_health': 'operational'
        }