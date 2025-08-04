"""
WebSocket Connection Pool for High-Performance Trading
====================================================

Connection pooling and management system to reduce WebSocket overhead
and improve connection reliability for high-frequency trading.
"""

import asyncio
import logging
import time
import weakref
from typing import Dict, Any, Optional, List, Callable, Set
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import aiohttp

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ConnectionMetrics:
    """Connection performance metrics"""
    created_at: float
    last_used: float
    message_count: int
    error_count: int
    reconnect_count: int
    avg_latency: float


class PooledConnection:
    """Wrapper for pooled WebSocket connections"""
    
    def __init__(self, connection_id: str, ws_client, pool_manager):
        self.connection_id = connection_id
        self.ws_client = ws_client
        self.pool_manager = pool_manager
        self.state = ConnectionState.IDLE
        self.metrics = ConnectionMetrics(
            created_at=time.time(),
            last_used=time.time(),
            message_count=0,
            error_count=0,
            reconnect_count=0,
            avg_latency=0.0
        )
        self.subscribers: Set[str] = set()
        self.last_heartbeat = time.time()
        
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message through this connection"""
        try:
            if self.state != ConnectionState.ACTIVE:
                logger.warning(f"[POOL] Connection {self.connection_id} not active: {self.state}")
                return False
            
            start_time = time.time()
            
            # Send message through WebSocket client
            if hasattr(self.ws_client, 'send'):
                await self.ws_client.send(message)
            elif hasattr(self.ws_client, 'subscribe'):
                # Handle subscription messages
                if 'method' in message and message['method'] == 'subscribe':
                    await self.ws_client.subscribe(
                        message.get('params', {}).get('channel', ''),
                        message.get('params', {}).get('symbols', [])
                    )
            
            # Update metrics
            latency = time.time() - start_time
            self.metrics.message_count += 1
            self.metrics.last_used = time.time()
            self.metrics.avg_latency = (
                (self.metrics.avg_latency * (self.metrics.message_count - 1) + latency) / 
                self.metrics.message_count
            )
            
            return True
            
        except Exception as e:
            logger.error(f"[POOL] Error sending message on connection {self.connection_id}: {e}")
            self.metrics.error_count += 1
            self.state = ConnectionState.ERROR
            return False
    
    def add_subscriber(self, subscriber_id: str):
        """Add subscriber to this connection"""
        self.subscribers.add(subscriber_id)
        self.metrics.last_used = time.time()
    
    def remove_subscriber(self, subscriber_id: str):
        """Remove subscriber from this connection"""
        self.subscribers.discard(subscriber_id)
    
    def is_idle(self, idle_timeout: float = 300.0) -> bool:
        """Check if connection is idle"""
        return (
            len(self.subscribers) == 0 and 
            time.time() - self.metrics.last_used > idle_timeout
        )
    
    async def close(self):
        """Close the connection"""
        try:
            if hasattr(self.ws_client, 'close'):
                await self.ws_client.close()
            self.state = ConnectionState.DISCONNECTED
        except Exception as e:
            logger.error(f"[POOL] Error closing connection {self.connection_id}: {e}")


class WebSocketConnectionPool:
    """High-performance WebSocket connection pool"""
    
    def __init__(self, 
                 max_connections: int = 5,
                 connection_timeout: float = 30.0,
                 idle_timeout: float = 300.0,
                 cleanup_interval: float = 60.0):
        
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        self.cleanup_interval = cleanup_interval
        
        self.connections: Dict[str, PooledConnection] = {}
        self.connection_queue = deque()  # For round-robin assignment
        self.subscriber_to_connection: Dict[str, str] = {}
        
        self.total_connections_created = 0
        self.total_messages_sent = 0
        self.pool_hits = 0
        self.pool_misses = 0
        
        self._cleanup_task: Optional[asyncio.Task] = None
        self._connection_factory = None
        
        logger.info(f"[POOL] Initialized with max_connections={max_connections}")
    
    def set_connection_factory(self, factory: Callable):
        """Set the factory function for creating new connections"""
        self._connection_factory = factory
    
    async def get_connection(self, subscriber_id: str, 
                           preferred_symbols: List[str] = None) -> Optional[PooledConnection]:
        """Get or create a connection for the subscriber"""
        
        # Check if subscriber already has a connection
        if subscriber_id in self.subscriber_to_connection:
            connection_id = self.subscriber_to_connection[subscriber_id]
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                if connection.state == ConnectionState.ACTIVE:
                    self.pool_hits += 1
                    return connection
                else:
                    # Connection is not active, remove mapping
                    del self.subscriber_to_connection[subscriber_id]
        
        # Try to find an existing connection with capacity
        available_connection = self._find_available_connection()
        if available_connection:
            available_connection.add_subscriber(subscriber_id)
            self.subscriber_to_connection[subscriber_id] = available_connection.connection_id
            self.pool_hits += 1
            return available_connection
        
        # Create new connection if under limit
        if len(self.connections) < self.max_connections:
            connection = await self._create_connection(subscriber_id)
            if connection:
                self.pool_misses += 1
                return connection
        
        # Pool is full, use round-robin
        if self.connection_queue:
            connection_id = self.connection_queue.popleft()
            self.connection_queue.append(connection_id)  # Move to end
            
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                connection.add_subscriber(subscriber_id)
                self.subscriber_to_connection[subscriber_id] = connection_id
                self.pool_hits += 1
                return connection
        
        logger.error("[POOL] Failed to get connection - pool exhausted")
        return None
    
    def _find_available_connection(self) -> Optional[PooledConnection]:
        """Find an available connection with capacity"""
        for connection in self.connections.values():
            if (connection.state == ConnectionState.ACTIVE and 
                len(connection.subscribers) < 10):  # Max 10 subscribers per connection
                return connection
        return None
    
    async def _create_connection(self, subscriber_id: str) -> Optional[PooledConnection]:
        """Create a new pooled connection"""
        if not self._connection_factory:
            logger.error("[POOL] No connection factory set")
            return None
        
        try:
            connection_id = f"pool_conn_{self.total_connections_created}"
            self.total_connections_created += 1
            
            logger.info(f"[POOL] Creating new connection: {connection_id}")
            
            # Create WebSocket client using factory
            ws_client = await self._connection_factory()
            
            # Create pooled connection wrapper
            connection = PooledConnection(connection_id, ws_client, self)
            connection.state = ConnectionState.ACTIVE
            connection.add_subscriber(subscriber_id)
            
            # Store connection
            self.connections[connection_id] = connection
            self.connection_queue.append(connection_id)
            self.subscriber_to_connection[subscriber_id] = connection_id
            
            logger.info(f"[POOL] Created connection {connection_id} for subscriber {subscriber_id}")
            return connection
            
        except Exception as e:
            logger.error(f"[POOL] Failed to create connection: {e}")
            return None
    
    async def release_subscriber(self, subscriber_id: str):
        """Release a subscriber from their connection"""
        if subscriber_id not in self.subscriber_to_connection:
            return
        
        connection_id = self.subscriber_to_connection[subscriber_id]
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.remove_subscriber(subscriber_id)
        
        del self.subscriber_to_connection[subscriber_id]
    
    async def send_message(self, subscriber_id: str, message: Dict[str, Any]) -> bool:
        """Send message through subscriber's connection"""
        connection = await self.get_connection(subscriber_id)
        if connection:
            success = await connection.send_message(message)
            if success:
                self.total_messages_sent += 1
            return success
        return False
    
    async def cleanup_idle_connections(self):
        """Clean up idle and error connections"""
        to_remove = []
        
        for connection_id, connection in self.connections.items():
            if connection.is_idle(self.idle_timeout) or connection.state == ConnectionState.ERROR:
                to_remove.append(connection_id)
                logger.info(f"[POOL] Marking connection {connection_id} for cleanup: "
                          f"idle={connection.is_idle()}, state={connection.state}")
        
        for connection_id in to_remove:
            await self._remove_connection(connection_id)
    
    async def _remove_connection(self, connection_id: str):
        """Remove a connection from the pool"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # Remove subscribers mapping
        subscribers_to_remove = []
        for sub_id, conn_id in self.subscriber_to_connection.items():
            if conn_id == connection_id:
                subscribers_to_remove.append(sub_id)
        
        for sub_id in subscribers_to_remove:
            del self.subscriber_to_connection[sub_id]
        
        # Close connection
        await connection.close()
        
        # Remove from pool
        del self.connections[connection_id]
        if connection_id in self.connection_queue:
            self.connection_queue.remove(connection_id)
        
        logger.info(f"[POOL] Removed connection {connection_id}")
    
    async def start_cleanup_task(self):
        """Start the cleanup background task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_idle_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[POOL] Cleanup loop error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        active_connections = sum(1 for c in self.connections.values() 
                               if c.state == ConnectionState.ACTIVE)
        total_subscribers = len(self.subscriber_to_connection)
        
        return {
            "total_connections": len(self.connections),
            "active_connections": active_connections,
            "total_subscribers": total_subscribers,
            "connections_created": self.total_connections_created,
            "messages_sent": self.total_messages_sent,
            "pool_hit_rate": (self.pool_hits / max(self.pool_hits + self.pool_misses, 1)) * 100,
            "avg_subscribers_per_connection": total_subscribers / max(active_connections, 1)
        }
    
    async def close_all(self):
        """Close all connections and cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        for connection in list(self.connections.values()):
            await connection.close()
        
        self.connections.clear()
        self.connection_queue.clear()
        self.subscriber_to_connection.clear()
        
        logger.info("[POOL] All connections closed")


# Global connection pool instance
_global_pool: Optional[WebSocketConnectionPool] = None

def get_connection_pool() -> WebSocketConnectionPool:
    """Get or create the global connection pool"""
    global _global_pool
    if _global_pool is None:
        _global_pool = WebSocketConnectionPool()
    return _global_pool

def set_connection_factory(factory: Callable):
    """Set the global connection factory"""
    pool = get_connection_pool()
    pool.set_connection_factory(factory)

async def start_connection_pool():
    """Start the global connection pool"""
    pool = get_connection_pool()
    await pool.start_cleanup_task()

async def close_connection_pool():
    """Close the global connection pool"""
    global _global_pool
    if _global_pool:
        await _global_pool.close_all()
        _global_pool = None