"""
High-Frequency Trading WebSocket Optimization Layer
==================================================

Performance optimizations for WebSocket connections in high-frequency trading:
- Connection pooling and persistent connections
- Adaptive reconnection strategies
- Message queuing and batch processing
- Latency monitoring and optimization
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, Callable, List, Queue
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
import weakref

logger = logging.getLogger(__name__)

@dataclass
class ConnectionMetrics:
    """WebSocket connection performance metrics"""
    connect_time: float = 0.0
    last_message_time: float = 0.0
    messages_received: int = 0
    messages_sent: int = 0
    reconnect_count: int = 0
    avg_latency: float = 0.0
    peak_latency: float = 0.0
    connection_drops: int = 0
    
@dataclass
class HFTWebSocketConfig:
    """Configuration for HFT WebSocket optimizations"""
    # Connection optimization
    max_connections: int = 5
    connection_timeout: float = 5.0
    persistent_connections: bool = True
    
    # Reconnection strategy
    initial_reconnect_delay: float = 0.1  # 100ms
    max_reconnect_delay: float = 2.0      # 2 seconds max
    reconnect_multiplier: float = 1.2
    max_reconnect_attempts: int = 100
    
    # Performance optimization
    message_queue_size: int = 10000
    batch_size: int = 50
    batch_timeout: float = 0.01  # 10ms batching
    latency_threshold: float = 0.05  # 50ms warning threshold
    
    # Memory optimization
    max_message_history: int = 1000
    cleanup_interval: float = 30.0  # 30 seconds


class MessageBatcher:
    """Batches messages for efficient processing"""
    
    def __init__(self, config: HFTWebSocketConfig):
        self.config = config
        self.batch_queue = deque()
        self.last_batch_time = time.time()
        self.processor_task = None
        
    async def add_message(self, message: Dict[str, Any], processor: Callable):
        """Add message to batch for processing"""
        self.batch_queue.append((message, processor, time.time()))
        
        # Process batch if it's full or timeout reached
        if (len(self.batch_queue) >= self.config.batch_size or 
            time.time() - self.last_batch_time >= self.config.batch_timeout):
            await self._process_batch()
    
    async def _process_batch(self):
        """Process current batch of messages"""
        if not self.batch_queue:
            return
            
        batch = []
        processors = []
        
        # Extract batch
        for _ in range(min(len(self.batch_queue), self.config.batch_size)):
            if self.batch_queue:
                message, processor, timestamp = self.batch_queue.popleft()
                batch.append(message)
                processors.append(processor)
        
        # Process batch in parallel
        if batch:
            start_time = time.time()
            tasks = [proc(msg) for msg, proc in zip(batch, processors)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            processing_time = time.time() - start_time
            if processing_time > 0.01:  # 10ms threshold
                logger.debug(f"[HFT_BATCH] Processed {len(batch)} messages in {processing_time*1000:.1f}ms")
        
        self.last_batch_time = time.time()


class AdaptiveReconnector:
    """Intelligent reconnection strategy for HFT"""
    
    def __init__(self, config: HFTWebSocketConfig):
        self.config = config
        self.reconnect_count = 0
        self.last_disconnect = None
        self.connection_stability = 1.0  # 0-1 score
        self.reconnect_delays = deque(maxlen=10)
        
    def get_reconnect_delay(self) -> float:
        """Calculate adaptive reconnect delay"""
        base_delay = self.config.initial_reconnect_delay
        
        # Exponential backoff with jitter
        delay = base_delay * (self.config.reconnect_multiplier ** min(self.reconnect_count, 10))
        delay = min(delay, self.config.max_reconnect_delay)
        
        # Stability-based adjustment
        if self.connection_stability > 0.8:
            delay *= 0.5  # Faster reconnect for stable connections
        elif self.connection_stability < 0.3:
            delay *= 1.5  # Slower reconnect for unstable connections
            
        # Add jitter (±20%)
        import random
        jitter = random.uniform(0.8, 1.2)
        delay *= jitter
        
        self.reconnect_delays.append(delay)
        return delay
    
    def on_connect_success(self):
        """Update metrics on successful connection"""
        if self.last_disconnect:
            disconnect_duration = time.time() - self.last_disconnect
            # Update stability based on how long connection lasted
            if disconnect_duration > 300:  # 5 minutes = stable
                self.connection_stability = min(1.0, self.connection_stability + 0.1)
            elif disconnect_duration < 30:  # < 30 seconds = unstable
                self.connection_stability = max(0.1, self.connection_stability - 0.2)
        
        # Reset reconnect count on successful connection
        if self.reconnect_count > 0:
            logger.info(f"[HFT_RECONNECT] Connection restored after {self.reconnect_count} attempts")
        self.reconnect_count = 0
        self.last_disconnect = None
    
    def on_disconnect(self):
        """Update metrics on disconnection"""
        self.last_disconnect = time.time()
        self.reconnect_count += 1
        self.connection_stability = max(0.1, self.connection_stability - 0.05)
        
    def should_reconnect(self) -> bool:
        """Check if should attempt reconnection"""
        return self.reconnect_count < self.config.max_reconnect_attempts


class LatencyMonitor:
    """Monitor and optimize WebSocket latency"""
    
    def __init__(self, config: HFTWebSocketConfig):
        self.config = config
        self.latencies = deque(maxlen=100)
        self.warning_count = 0
        self.last_warning = 0
        
    def record_latency(self, latency: float):
        """Record message latency"""
        self.latencies.append(latency)
        
        # Check for high latency
        if latency > self.config.latency_threshold:
            current_time = time.time()
            if current_time - self.last_warning > 10:  # Throttle warnings
                self.warning_count += 1
                self.last_warning = current_time
                logger.warning(f"[HFT_LATENCY] High latency detected: {latency*1000:.1f}ms "
                             f"(warning #{self.warning_count})")
    
    def get_stats(self) -> Dict[str, float]:
        """Get latency statistics"""
        if not self.latencies:
            return {}
            
        latencies_list = list(self.latencies)
        return {
            'avg_latency': sum(latencies_list) / len(latencies_list),
            'min_latency': min(latencies_list),
            'max_latency': max(latencies_list),
            'p95_latency': sorted(latencies_list)[int(len(latencies_list) * 0.95)] if len(latencies_list) > 1 else latencies_list[0],
            'warning_count': self.warning_count
        }


class HFTWebSocketOptimizer:
    """High-frequency trading WebSocket optimization manager"""
    
    def __init__(self, config: Optional[HFTWebSocketConfig] = None):
        self.config = config or HFTWebSocketConfig()
        self.connections = {}  # symbol -> connection
        self.metrics = {}      # symbol -> ConnectionMetrics
        self.message_batcher = MessageBatcher(self.config)
        self.reconnectors = {}  # symbol -> AdaptiveReconnector
        self.latency_monitors = {}  # symbol -> LatencyMonitor
        
        # Performance tracking
        self.total_messages = 0
        self.start_time = time.time()
        self.last_cleanup = time.time()
        
        # Connection pool
        self._connection_pool = asyncio.Queue(maxsize=self.config.max_connections)
        self._pool_initialized = False
        
        logger.info(f"[HFT_WEBSOCKET] Optimizer initialized with {self.config.max_connections} max connections")
    
    async def optimize_connection(self, websocket_manager, symbol: str) -> bool:
        """Apply HFT optimizations to WebSocket connection"""
        try:
            # Initialize metrics if needed
            if symbol not in self.metrics:
                self.metrics[symbol] = ConnectionMetrics()
                self.reconnectors[symbol] = AdaptiveReconnector(self.config)
                self.latency_monitors[symbol] = LatencyMonitor(self.config)
            
            # Apply connection optimizations
            await self._optimize_connection_settings(websocket_manager, symbol)
            
            # Set up message processing optimization
            original_handler = getattr(websocket_manager, '_handle_message', None)
            if original_handler:
                optimized_handler = self._create_optimized_handler(original_handler, symbol)
                websocket_manager._handle_message = optimized_handler
            
            logger.info(f"[HFT_WEBSOCKET] Applied optimizations to {symbol} connection")
            return True
            
        except Exception as e:
            logger.error(f"[HFT_WEBSOCKET] Failed to optimize {symbol}: {e}")
            return False
    
    async def _optimize_connection_settings(self, websocket_manager, symbol: str):
        """Apply low-level connection optimizations"""
        # Set TCP_NODELAY for low latency
        if hasattr(websocket_manager, '_websocket') and websocket_manager._websocket:
            try:
                # Enable TCP_NODELAY to disable Nagle's algorithm
                transport = websocket_manager._websocket.transport
                if transport and hasattr(transport, 'get_extra_info'):
                    sock = transport.get_extra_info('socket')
                    if sock:
                        import socket
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        # Set buffer sizes for optimal throughput
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                        logger.debug(f"[HFT_WEBSOCKET] Applied TCP optimizations to {symbol}")
            except Exception as e:
                logger.debug(f"[HFT_WEBSOCKET] TCP optimization failed for {symbol}: {e}")
    
    def _create_optimized_handler(self, original_handler: Callable, symbol: str) -> Callable:
        """Create optimized message handler with batching and latency monitoring"""
        
        async def optimized_handler(message):
            start_time = time.time()
            
            # Update metrics
            metrics = self.metrics[symbol]
            metrics.messages_received += 1
            metrics.last_message_time = start_time
            self.total_messages += 1
            
            # Add to batch processor
            await self.message_batcher.add_message(message, original_handler)
            
            # Record latency
            latency = time.time() - start_time
            self.latency_monitors[symbol].record_latency(latency)
            
            # Update average latency
            if metrics.avg_latency == 0:
                metrics.avg_latency = latency
            else:
                metrics.avg_latency = (metrics.avg_latency * 0.9) + (latency * 0.1)
            
            # Update peak latency
            metrics.peak_latency = max(metrics.peak_latency, latency)
            
            # Periodic cleanup
            await self._periodic_cleanup()
        
        return optimized_handler
    
    async def _periodic_cleanup(self):
        """Perform periodic cleanup and optimization"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.config.cleanup_interval:
            self.last_cleanup = current_time
            
            # Clean up old metrics
            for symbol, metrics in self.metrics.items():
                if current_time - metrics.last_message_time > 300:  # 5 minutes idle
                    logger.debug(f"[HFT_WEBSOCKET] Cleaning up idle connection metrics for {symbol}")
            
            # Log performance summary
            uptime = current_time - self.start_time
            msg_per_sec = self.total_messages / uptime if uptime > 0 else 0
            logger.info(f"[HFT_WEBSOCKET] Performance: {msg_per_sec:.1f} msg/sec, "
                       f"{len(self.connections)} active connections")
    
    async def handle_reconnection(self, websocket_manager, symbol: str) -> bool:
        """Handle reconnection with adaptive strategy"""
        if symbol not in self.reconnectors:
            self.reconnectors[symbol] = AdaptiveReconnector(self.config)
        
        reconnector = self.reconnectors[symbol]
        
        if not reconnector.should_reconnect():
            logger.error(f"[HFT_WEBSOCKET] Max reconnection attempts reached for {symbol}")
            return False
        
        # Calculate delay
        delay = reconnector.get_reconnect_delay()
        logger.info(f"[HFT_WEBSOCKET] Reconnecting {symbol} in {delay:.2f}s "
                   f"(attempt {reconnector.reconnect_count})")
        
        await asyncio.sleep(delay)
        
        try:
            # Attempt reconnection
            success = await self._attempt_reconnection(websocket_manager, symbol)
            
            if success:
                reconnector.on_connect_success()
                await self.optimize_connection(websocket_manager, symbol)
                return True
            else:
                reconnector.on_disconnect()
                return False
                
        except Exception as e:
            logger.error(f"[HFT_WEBSOCKET] Reconnection failed for {symbol}: {e}")
            reconnector.on_disconnect()
            return False
    
    async def _attempt_reconnection(self, websocket_manager, symbol: str) -> bool:
        """Attempt to reconnect WebSocket"""
        try:
            # Use the websocket manager's reconnection method if available
            if hasattr(websocket_manager, 'reconnect'):
                await websocket_manager.reconnect()
            elif hasattr(websocket_manager, 'connect'):
                await websocket_manager.connect()
            else:
                logger.warning(f"[HFT_WEBSOCKET] No reconnection method found for {symbol}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[HFT_WEBSOCKET] Reconnection attempt failed for {symbol}: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        stats = {
            'uptime': uptime,
            'total_messages': self.total_messages,
            'messages_per_second': self.total_messages / uptime if uptime > 0 else 0,
            'active_connections': len(self.connections),
            'connections': {}
        }
        
        # Per-connection stats
        for symbol, metrics in self.metrics.items():
            connection_stats = {
                'messages_received': metrics.messages_received,
                'avg_latency_ms': metrics.avg_latency * 1000,
                'peak_latency_ms': metrics.peak_latency * 1000,
                'reconnect_count': metrics.reconnect_count,
                'connection_drops': metrics.connection_drops
            }
            
            # Add latency monitor stats
            if symbol in self.latency_monitors:
                latency_stats = self.latency_monitors[symbol].get_stats()
                connection_stats.update({
                    f'latency_{k}': v * 1000 for k, v in latency_stats.items()
                    if k != 'warning_count'
                })
                connection_stats['latency_warnings'] = latency_stats.get('warning_count', 0)
            
            stats['connections'][symbol] = connection_stats
        
        return stats
    
    async def enable_burst_mode(self, duration: float = 60.0):
        """Enable burst mode for high-frequency trading periods"""
        logger.info(f"[HFT_WEBSOCKET] Enabling burst mode for {duration}s")
        
        # Reduce batch timeout for faster processing
        original_batch_timeout = self.config.batch_timeout
        self.config.batch_timeout = 0.005  # 5ms for burst mode
        
        # Increase batch size for better throughput
        original_batch_size = self.config.batch_size
        self.config.batch_size = 100
        
        # Schedule restoration of normal settings
        async def restore_normal_mode():
            await asyncio.sleep(duration)
            self.config.batch_timeout = original_batch_timeout
            self.config.batch_size = original_batch_size
            logger.info("[HFT_WEBSOCKET] Burst mode disabled, returning to normal operation")
        
        # Start restoration task
        asyncio.create_task(restore_normal_mode())


# Global instance for use across the bot
hft_websocket_optimizer = HFTWebSocketOptimizer()