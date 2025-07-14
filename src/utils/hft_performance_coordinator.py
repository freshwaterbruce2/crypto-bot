"""
HFT Performance Coordinator
===========================

Central coordination system for all high-frequency trading optimizations:
- Circuit breaker optimization coordination
- WebSocket performance management
- Rate limiting optimization
- Memory usage optimization
- Signal processing coordination
- Performance monitoring and reporting
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

# Import HFT optimization modules
from src.utils.circuit_breaker import circuit_breaker_manager, CircuitBreakerConfig
from src.exchange.hft_websocket_optimizer import hft_websocket_optimizer, HFTWebSocketConfig
from src.helpers.kraken_rate_limiter import KrakenRateLimitManager
from src.utils.hft_memory_optimizer import hft_memory_optimizer
from src.trading.hft_signal_processor import hft_signal_processor

logger = logging.getLogger(__name__)

@dataclass
class HFTConfig:
    """Configuration for HFT optimizations"""
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    adaptive_thresholds: bool = True
    burst_mode_enabled: bool = True
    
    # WebSocket settings
    websocket_optimization: bool = True
    max_connections: int = 5
    auto_reconnect: bool = True
    
    # Rate limiting settings
    rate_limit_optimization: bool = True
    predictive_throttling: bool = True
    burst_trading_enabled: bool = True
    
    # Memory settings
    memory_optimization: bool = True
    memory_monitoring: bool = True
    auto_gc_enabled: bool = True
    
    # Signal processing settings
    signal_processing_optimization: bool = True
    parallel_processing: bool = True
    adaptive_filtering: bool = True
    
    # Performance monitoring
    performance_monitoring: bool = True
    metrics_collection: bool = True
    auto_optimization: bool = True

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    timestamp: float = field(default_factory=time.time)
    
    # Latency metrics (milliseconds)
    avg_signal_latency: float = 0.0
    peak_signal_latency: float = 0.0
    avg_execution_latency: float = 0.0
    peak_execution_latency: float = 0.0
    
    # Throughput metrics
    signals_per_second: float = 0.0
    trades_per_second: float = 0.0
    api_calls_per_second: float = 0.0
    
    # Efficiency metrics
    signal_processing_efficiency: float = 0.0
    memory_efficiency: float = 0.0
    rate_limit_efficiency: float = 0.0
    circuit_breaker_efficiency: float = 0.0
    
    # Error metrics
    circuit_breaker_opens: int = 0
    rate_limit_hits: int = 0
    memory_warnings: int = 0
    connection_drops: int = 0

class HFTPerformanceCoordinator:
    """Central coordinator for all HFT performance optimizations"""
    
    def __init__(self, config: Optional[HFTConfig] = None):
        self.config = config or HFTConfig()
        self.is_running = False
        self.start_time = time.time()
        
        # Performance tracking
        self.metrics_history = []
        self.current_metrics = PerformanceMetrics()
        self.optimization_tasks = []
        
        # Component references
        self.circuit_breaker_manager = circuit_breaker_manager
        self.websocket_optimizer = hft_websocket_optimizer
        self.memory_optimizer = hft_memory_optimizer
        self.signal_processor = hft_signal_processor
        self.rate_limiters = {}  # symbol -> rate limiter
        
        # Coordination state
        self.burst_mode_active = False
        self.emergency_mode_active = False
        self.last_optimization_time = time.time()
        
        # Performance callbacks
        self.performance_callbacks = []
        
        logger.info("[HFT_COORDINATOR] Performance coordinator initialized")
    
    async def start(self):
        """Start the HFT performance coordination system"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_time = time.time()
        
        logger.info("[HFT_COORDINATOR] Starting HFT performance optimization")
        
        # Initialize components
        await self._initialize_components()
        
        # Start monitoring and optimization tasks
        await self._start_optimization_tasks()
        
        logger.info("[HFT_COORDINATOR] HFT performance optimization started")
    
    async def stop(self):
        """Stop the HFT performance coordination system"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        logger.info("[HFT_COORDINATOR] Stopping HFT performance optimization")
        
        # Stop optimization tasks
        for task in self.optimization_tasks:
            task.cancel()
        
        await asyncio.gather(*self.optimization_tasks, return_exceptions=True)
        self.optimization_tasks.clear()
        
        # Stop signal processor
        await self.signal_processor.stop()
        
        logger.info("[HFT_COORDINATOR] HFT performance optimization stopped")
    
    async def _initialize_components(self):
        """Initialize all HFT optimization components"""
        
        # Initialize memory optimizer
        if self.config.memory_optimization:
            if self.config.memory_monitoring:
                self.memory_optimizer.start_memory_monitoring()
        
        # Initialize signal processor
        if self.config.signal_processing_optimization:
            await self.signal_processor.start()
            
            # Register signal handlers
            await self._setup_signal_handlers()
        
        # Initialize circuit breakers with HFT config
        if self.config.circuit_breaker_enabled:
            cb_config = CircuitBreakerConfig(
                adaptive_threshold=self.config.adaptive_thresholds,
                burst_mode_enabled=self.config.burst_mode_enabled,
                performance_mode=True
            )
            # Circuit breakers are created on-demand
        
        logger.info("[HFT_COORDINATOR] Components initialized")
    
    async def _setup_signal_handlers(self):
        """Setup optimized signal handlers"""
        from src.trading.hft_signal_processor import SignalPriority
        
        # Critical signals - immediate processing
        async def critical_signal_handler(signal):
            await self._process_critical_signal(signal)
        
        # High priority signals - fast processing
        async def high_priority_handler(signal):
            await self._process_high_priority_signal(signal)
        
        self.signal_processor.register_signal_handler(
            SignalPriority.CRITICAL, critical_signal_handler
        )
        self.signal_processor.register_signal_handler(
            SignalPriority.HIGH, high_priority_handler
        )
    
    async def _start_optimization_tasks(self):
        """Start background optimization tasks"""
        
        # Performance monitoring task
        if self.config.performance_monitoring:
            task = asyncio.create_task(self._performance_monitoring_loop())
            self.optimization_tasks.append(task)
        
        # Auto-optimization task
        if self.config.auto_optimization:
            task = asyncio.create_task(self._auto_optimization_loop())
            self.optimization_tasks.append(task)
        
        # Memory optimization task
        if self.config.memory_optimization and self.config.auto_gc_enabled:
            task = asyncio.create_task(self._memory_optimization_loop())
            self.optimization_tasks.append(task)
        
        logger.info(f"[HFT_COORDINATOR] Started {len(self.optimization_tasks)} optimization tasks")
    
    async def _performance_monitoring_loop(self):
        """Continuous performance monitoring"""
        while self.is_running:
            try:
                # Collect metrics from all components
                metrics = await self._collect_performance_metrics()
                
                # Update current metrics
                self.current_metrics = metrics
                
                # Store in history
                self.metrics_history.append(metrics)
                
                # Keep only last 1000 metrics (roughly 16 minutes at 1s intervals)
                if len(self.metrics_history) > 1000:
                    self.metrics_history.pop(0)
                
                # Check for performance issues
                await self._check_performance_alerts(metrics)
                
                # Notify callbacks
                for callback in self.performance_callbacks:
                    try:
                        await callback(metrics)
                    except Exception as e:
                        logger.error(f"[HFT_COORDINATOR] Performance callback error: {e}")
                
                await asyncio.sleep(1.0)  # 1-second monitoring interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HFT_COORDINATOR] Performance monitoring error: {e}")
                await asyncio.sleep(5.0)
    
    async def _auto_optimization_loop(self):
        """Automatic optimization based on performance metrics"""
        while self.is_running:
            try:
                current_time = time.time()
                
                # Run optimization every 30 seconds
                if current_time - self.last_optimization_time > 30.0:
                    await self._run_auto_optimization()
                    self.last_optimization_time = current_time
                
                await asyncio.sleep(10.0)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HFT_COORDINATOR] Auto-optimization error: {e}")
                await asyncio.sleep(30.0)
    
    async def _memory_optimization_loop(self):
        """Automatic memory optimization"""
        while self.is_running:
            try:
                # Run memory optimization every 60 seconds
                self.memory_optimizer.optimize_garbage_collection()
                
                # Take memory snapshot
                if self.config.memory_monitoring:
                    self.memory_optimizer.take_memory_snapshot()
                
                await asyncio.sleep(60.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HFT_COORDINATOR] Memory optimization error: {e}")
                await asyncio.sleep(60.0)
    
    async def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect comprehensive performance metrics"""
        metrics = PerformanceMetrics()
        
        try:
            # Signal processor metrics
            if self.config.signal_processing_optimization:
                signal_stats = self.signal_processor.get_performance_stats()
                metrics.signals_per_second = signal_stats.get('signals_per_second', 0.0)
                metrics.avg_signal_latency = signal_stats.get('avg_processing_time_ms', 0.0)
                metrics.peak_signal_latency = signal_stats.get('peak_processing_time_ms', 0.0)
                metrics.signal_processing_efficiency = min(100.0, signal_stats.get('processing_rate', 0.0))
            
            # Memory metrics
            if self.config.memory_optimization:
                memory_stats = self.memory_optimizer.get_memory_stats()
                cache_stats = memory_stats.get('caches', {})
                
                # Calculate average cache hit rate
                total_hits = sum(cache.get('hits', 0) for cache in cache_stats.values())
                total_requests = sum(cache.get('hits', 0) + cache.get('misses', 0) for cache in cache_stats.values())
                metrics.memory_efficiency = (total_hits / total_requests * 100) if total_requests > 0 else 0
            
            # Circuit breaker metrics
            if self.config.circuit_breaker_enabled:
                cb_summary = self.circuit_breaker_manager.get_summary()
                metrics.circuit_breaker_opens = cb_summary.get('states', {}).get('open', 0)
                
                # Calculate efficiency (percentage of closed circuits)
                total_circuits = cb_summary.get('total', 1)
                closed_circuits = cb_summary.get('states', {}).get('closed', 0)
                metrics.circuit_breaker_efficiency = (closed_circuits / total_circuits * 100) if total_circuits > 0 else 100
            
            # Rate limiting metrics
            total_efficiency = 0
            rate_limiter_count = 0
            for symbol, rate_limiter in self.rate_limiters.items():
                if hasattr(rate_limiter, 'get_pro_optimization_stats'):
                    stats = rate_limiter.get_pro_optimization_stats()
                    if 'current_utilization' in stats:
                        utilization = stats['current_utilization'].get(symbol, 0)
                        efficiency = max(0, 100 - utilization)
                        total_efficiency += efficiency
                        rate_limiter_count += 1
            
            if rate_limiter_count > 0:
                metrics.rate_limit_efficiency = total_efficiency / rate_limiter_count
            else:
                metrics.rate_limit_efficiency = 100.0
            
        except Exception as e:
            logger.error(f"[HFT_COORDINATOR] Error collecting metrics: {e}")
        
        return metrics
    
    async def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """Check for performance issues and trigger alerts"""
        
        # High latency alert
        if metrics.avg_signal_latency > 50.0:  # 50ms threshold
            logger.warning(f"[HFT_COORDINATOR] High signal latency: {metrics.avg_signal_latency:.1f}ms")
            await self._handle_high_latency_alert()
        
        # Low efficiency alerts
        if metrics.signal_processing_efficiency < 50.0:
            logger.warning(f"[HFT_COORDINATOR] Low signal processing efficiency: {metrics.signal_processing_efficiency:.1f}%")
        
        if metrics.memory_efficiency < 30.0:
            logger.warning(f"[HFT_COORDINATOR] Low memory efficiency: {metrics.memory_efficiency:.1f}%")
            self.memory_optimizer.clear_all_caches()
        
        if metrics.circuit_breaker_efficiency < 80.0:
            logger.warning(f"[HFT_COORDINATOR] Circuit breaker issues: {metrics.circuit_breaker_efficiency:.1f}% efficiency")
            await self._handle_circuit_breaker_issues()
    
    async def _handle_high_latency_alert(self):
        """Handle high latency situation"""
        if not self.burst_mode_active:
            logger.info("[HFT_COORDINATOR] Activating burst mode due to high latency")
            await self.enable_burst_mode(30.0)  # 30-second burst mode
    
    async def _handle_circuit_breaker_issues(self):
        """Handle circuit breaker issues"""
        # Reset circuit breakers that have been open too long
        cb_status = self.circuit_breaker_manager.get_all_status()
        
        for name, status in cb_status.items():
            if status['state'] == 'open' and status['time_in_state'] > 60:  # 1 minute
                logger.info(f"[HFT_COORDINATOR] Resetting circuit breaker: {name}")
                cb = self.circuit_breaker_manager.get_or_create(name)
                cb.reset()
    
    async def _run_auto_optimization(self):
        """Run automatic optimization based on current performance"""
        metrics = self.current_metrics
        
        # Optimize based on signal processing performance
        if metrics.signals_per_second > 50 and not self.burst_mode_active:
            logger.info("[HFT_COORDINATOR] High signal volume detected, enabling optimizations")
            await self.signal_processor.optimize_for_burst_mode(60.0)
            self.memory_optimizer.optimize_for_hft_burst()
        
        # Optimize memory if efficiency is low
        if metrics.memory_efficiency < 50.0:
            logger.info("[HFT_COORDINATOR] Low memory efficiency, triggering optimization")
            self.memory_optimizer.optimize_garbage_collection()
        
        logger.debug("[HFT_COORDINATOR] Auto-optimization completed")
    
    async def _process_critical_signal(self, signal):
        """Process critical priority signals with maximum performance"""
        start_time = time.time()
        
        try:
            # Critical signals bypass most checks
            symbol = signal.symbol
            
            # Get or create rate limiter
            if symbol not in self.rate_limiters:
                self.rate_limiters[symbol] = KrakenRateLimitManager("pro")
            
            rate_limiter = self.rate_limiters[symbol]
            
            # Check if we can trade (with high priority flag)
            if rate_limiter.can_trade(symbol, high_priority=True):
                # Process signal immediately
                logger.info(f"[HFT_COORDINATOR] CRITICAL signal: {symbol} {signal.side} "
                           f"@{signal.price:.6f} conf={signal.confidence:.2f}")
                
                # TODO: Route to trade executor with emergency bypass
                # This would integrate with the existing trading system
                
            else:
                logger.warning(f"[HFT_COORDINATOR] CRITICAL signal blocked by rate limits: {symbol}")
        
        except Exception as e:
            logger.error(f"[HFT_COORDINATOR] Error processing critical signal: {e}")
        finally:
            processing_time = time.time() - start_time
            if processing_time > 0.001:  # 1ms threshold for critical signals
                logger.warning(f"[HFT_COORDINATOR] Slow critical signal processing: {processing_time*1000:.1f}ms")
    
    async def _process_high_priority_signal(self, signal):
        """Process high priority signals with enhanced performance"""
        # Similar to critical but with some additional checks
        await self._process_critical_signal(signal)  # Simplified for now
    
    async def enable_burst_mode(self, duration: float = 60.0):
        """Enable coordinated burst mode across all components"""
        if self.burst_mode_active:
            return
        
        self.burst_mode_active = True
        logger.info(f"[HFT_COORDINATOR] Enabling coordinated burst mode for {duration}s")
        
        try:
            # Enable burst mode in all components
            if self.config.signal_processing_optimization:
                await self.signal_processor.optimize_for_burst_mode(duration)
            
            if self.config.memory_optimization:
                self.memory_optimizer.optimize_for_hft_burst()
            
            if self.config.websocket_optimization:
                await self.websocket_optimizer.enable_burst_mode(duration)
            
            # Schedule burst mode deactivation
            async def deactivate_burst_mode():
                await asyncio.sleep(duration)
                self.burst_mode_active = False
                
                if self.config.memory_optimization:
                    self.memory_optimizer.restore_normal_mode()
                
                logger.info("[HFT_COORDINATOR] Burst mode deactivated")
            
            asyncio.create_task(deactivate_burst_mode())
            
        except Exception as e:
            logger.error(f"[HFT_COORDINATOR] Error enabling burst mode: {e}")
            self.burst_mode_active = False
    
    async def enable_emergency_mode(self):
        """Enable emergency mode for critical trading situations"""
        if self.emergency_mode_active:
            return
        
        self.emergency_mode_active = True
        logger.warning("[HFT_COORDINATOR] EMERGENCY MODE ACTIVATED")
        
        try:
            # Reset all circuit breakers
            self.circuit_breaker_manager.reset_all()
            
            # Clear memory caches
            self.memory_optimizer.clear_all_caches()
            
            # Enable maximum performance mode
            await self.enable_burst_mode(300.0)  # 5-minute emergency mode
            
            # Schedule emergency mode deactivation
            async def deactivate_emergency_mode():
                await asyncio.sleep(300.0)
                self.emergency_mode_active = False
                logger.info("[HFT_COORDINATOR] Emergency mode deactivated")
            
            asyncio.create_task(deactivate_emergency_mode())
            
        except Exception as e:
            logger.error(f"[HFT_COORDINATOR] Error in emergency mode: {e}")
    
    def register_performance_callback(self, callback: Callable):
        """Register callback for performance metrics updates"""
        self.performance_callbacks.append(callback)
        logger.info("[HFT_COORDINATOR] Performance callback registered")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        uptime = time.time() - self.start_time
        
        report = {
            'coordinator': {
                'uptime_seconds': uptime,
                'is_running': self.is_running,
                'burst_mode_active': self.burst_mode_active,
                'emergency_mode_active': self.emergency_mode_active,
                'config': {
                    'circuit_breaker_enabled': self.config.circuit_breaker_enabled,
                    'websocket_optimization': self.config.websocket_optimization,
                    'rate_limit_optimization': self.config.rate_limit_optimization,
                    'memory_optimization': self.config.memory_optimization,
                    'signal_processing_optimization': self.config.signal_processing_optimization
                }
            },
            'current_metrics': {
                'avg_signal_latency_ms': self.current_metrics.avg_signal_latency,
                'signals_per_second': self.current_metrics.signals_per_second,
                'signal_processing_efficiency': self.current_metrics.signal_processing_efficiency,
                'memory_efficiency': self.current_metrics.memory_efficiency,
                'rate_limit_efficiency': self.current_metrics.rate_limit_efficiency,
                'circuit_breaker_efficiency': self.current_metrics.circuit_breaker_efficiency
            },
            'component_stats': {}
        }
        
        # Add component-specific stats
        if self.config.signal_processing_optimization:
            report['component_stats']['signal_processor'] = self.signal_processor.get_performance_stats()
        
        if self.config.memory_optimization:
            report['component_stats']['memory_optimizer'] = self.memory_optimizer.get_memory_stats()
        
        if self.config.circuit_breaker_enabled:
            report['component_stats']['circuit_breakers'] = self.circuit_breaker_manager.get_all_status()
        
        if self.config.websocket_optimization:
            report['component_stats']['websocket_optimizer'] = self.websocket_optimizer.get_performance_stats()
        
        return report
    
    def export_performance_data(self, filepath: str):
        """Export performance data to file"""
        try:
            data = {
                'export_timestamp': time.time(),
                'coordinator_report': self.get_performance_report(),
                'metrics_history': [
                    {
                        'timestamp': m.timestamp,
                        'avg_signal_latency': m.avg_signal_latency,
                        'signals_per_second': m.signals_per_second,
                        'signal_processing_efficiency': m.signal_processing_efficiency,
                        'memory_efficiency': m.memory_efficiency,
                        'rate_limit_efficiency': m.rate_limit_efficiency,
                        'circuit_breaker_efficiency': m.circuit_breaker_efficiency
                    }
                    for m in self.metrics_history[-100:]  # Last 100 metrics
                ]
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"[HFT_COORDINATOR] Performance data exported to {filepath}")
            
        except Exception as e:
            logger.error(f"[HFT_COORDINATOR] Error exporting performance data: {e}")

# Global instance
hft_coordinator = HFTPerformanceCoordinator()