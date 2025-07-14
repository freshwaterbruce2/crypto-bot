"""
WebSocket Nonce Coordinator - Integration layer for nonce management

This module coordinates nonce generation across multiple WebSocket connections,
ensuring thread-safe sequential nonces for Kraken authentication.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, Callable
from datetime import datetime
import json

from ..utils.kraken_nonce_manager import get_nonce_manager, KrakenNonceManager

logger = logging.getLogger(__name__)


class WebSocketNonceCoordinator:
    """
    Coordinates nonce generation for WebSocket connections.
    
    Integrates with the KrakenNonceManager to provide:
    - Connection-specific nonce sequences
    - Automatic retry with new nonces
    - Nonce monitoring and debugging
    - Integration with existing WebSocket managers
    """
    
    def __init__(self, nonce_manager: Optional[KrakenNonceManager] = None):
        """
        Initialize the coordinator.
        
        Args:
            nonce_manager: Optional custom nonce manager, uses global if None
        """
        self.nonce_manager = nonce_manager or get_nonce_manager()
        self._connection_handlers: Dict[str, Callable] = {}
        self._nonce_history: Dict[str, list] = {}
        self._failed_nonces: Dict[str, list] = {}
        
        logger.info("[NONCE_COORDINATOR] Initialized WebSocket nonce coordinator")
    
    def register_connection(self, connection_id: str, 
                          error_handler: Optional[Callable] = None) -> None:
        """
        Register a new WebSocket connection for nonce management.
        
        Args:
            connection_id: Unique identifier for the connection
            error_handler: Optional callback for nonce errors
        """
        if error_handler:
            self._connection_handlers[connection_id] = error_handler
        
        self._nonce_history[connection_id] = []
        self._failed_nonces[connection_id] = []
        
        logger.info(f"[NONCE_COORDINATOR] Registered connection: {connection_id}")
    
    def get_auth_nonce(self, connection_id: str) -> int:
        """
        Get next authentication nonce for a connection.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Next sequential nonce
        """
        # Register if not known
        if connection_id not in self._nonce_history:
            self.register_connection(connection_id)
        
        # Get nonce
        nonce = self.nonce_manager.get_nonce(connection_id)
        
        # Track history
        self._nonce_history[connection_id].append({
            'nonce': nonce,
            'timestamp': datetime.now().isoformat(),
            'status': 'generated'
        })
        
        # Keep only last 100 entries
        if len(self._nonce_history[connection_id]) > 100:
            self._nonce_history[connection_id] = self._nonce_history[connection_id][-100:]
        
        logger.debug(f"[NONCE_COORDINATOR] Generated nonce {nonce} for {connection_id}")
        return nonce
    
    def create_auth_message(self, connection_id: str, api_key: str) -> Dict[str, Any]:
        """
        Create a complete authentication message with nonce.
        
        Args:
            connection_id: Connection identifier
            api_key: Kraken API key
            
        Returns:
            Authentication message ready to send
        """
        nonce = self.get_auth_nonce(connection_id)
        
        auth_message = {
            "event": "subscribe",
            "reqid": nonce,
            "subscription": {
                "name": "ownTrades",
                "token": api_key
            }
        }
        
        logger.debug(f"[NONCE_COORDINATOR] Created auth message with nonce {nonce}")
        return auth_message
    
    def handle_nonce_error(self, connection_id: str, nonce: int, 
                          error_message: str) -> Dict[str, Any]:
        """
        Handle nonce-related errors and determine recovery strategy.
        
        Args:
            connection_id: Connection identifier
            nonce: Failed nonce
            error_message: Error details
            
        Returns:
            Recovery strategy with new nonce if applicable
        """
        # Track failed nonce
        self._failed_nonces[connection_id].append({
            'nonce': nonce,
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update history
        for entry in self._nonce_history[connection_id]:
            if entry['nonce'] == nonce:
                entry['status'] = 'failed'
                entry['error'] = error_message
                break
        
        # Determine recovery strategy
        if "EOrder:Invalid nonce" in error_message:
            # Reset connection nonces
            self.nonce_manager.reset_connection(connection_id)
            new_nonce = self.get_auth_nonce(connection_id)
            
            logger.warning(f"[NONCE_COORDINATOR] Invalid nonce {nonce}, reset to {new_nonce}")
            
            return {
                'action': 'retry',
                'new_nonce': new_nonce,
                'reset': True
            }
        
        elif "already seen nonce" in error_message.lower():
            # Just get next nonce
            new_nonce = self.get_auth_nonce(connection_id)
            
            logger.warning(f"[NONCE_COORDINATOR] Duplicate nonce {nonce}, using {new_nonce}")
            
            return {
                'action': 'retry',
                'new_nonce': new_nonce,
                'reset': False
            }
        
        else:
            # Unknown error, may not be nonce-related
            logger.error(f"[NONCE_COORDINATOR] Unknown error for nonce {nonce}: {error_message}")
            
            return {
                'action': 'escalate',
                'error': error_message
            }
    
    def mark_nonce_success(self, connection_id: str, nonce: int) -> None:
        """
        Mark a nonce as successfully used.
        
        Args:
            connection_id: Connection identifier
            nonce: Successful nonce
        """
        for entry in self._nonce_history.get(connection_id, []):
            if entry['nonce'] == nonce:
                entry['status'] = 'success'
                break
        
        logger.debug(f"[NONCE_COORDINATOR] Marked nonce {nonce} as successful")
    
    def cleanup_connection(self, connection_id: str) -> None:
        """
        Clean up resources for a disconnected connection.
        
        Args:
            connection_id: Connection to clean up
        """
        self.nonce_manager.remove_connection(connection_id)
        
        if connection_id in self._connection_handlers:
            del self._connection_handlers[connection_id]
        
        if connection_id in self._nonce_history:
            del self._nonce_history[connection_id]
        
        if connection_id in self._failed_nonces:
            del self._failed_nonces[connection_id]
        
        logger.info(f"[NONCE_COORDINATOR] Cleaned up connection: {connection_id}")
    
    def get_connection_stats(self, connection_id: str) -> Dict[str, Any]:
        """
        Get nonce statistics for a connection.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Statistics dictionary
        """
        history = self._nonce_history.get(connection_id, [])
        failed = self._failed_nonces.get(connection_id, [])
        
        success_count = sum(1 for h in history if h.get('status') == 'success')
        
        return {
            'connection_id': connection_id,
            'total_nonces': len(history),
            'successful': success_count,
            'failed': len(failed),
            'success_rate': success_count / len(history) if history else 0,
            'last_nonce': history[-1]['nonce'] if history else None,
            'last_timestamp': history[-1]['timestamp'] if history else None
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all connections.
        
        Returns:
            Complete statistics
        """
        stats = {
            'active_connections': len(self._nonce_history),
            'nonce_manager_stats': self.nonce_manager.get_statistics(),
            'connections': {}
        }
        
        for conn_id in self._nonce_history:
            stats['connections'][conn_id] = self.get_connection_stats(conn_id)
        
        return stats
    
    async def monitor_nonce_health(self, interval: int = 60) -> None:
        """
        Monitor nonce health and log warnings.
        
        Args:
            interval: Check interval in seconds
        """
        while True:
            try:
                await asyncio.sleep(interval)
                
                # Check each connection
                for conn_id in list(self._nonce_history.keys()):
                    stats = self.get_connection_stats(conn_id)
                    
                    # Warn if high failure rate
                    if stats['total_nonces'] > 10 and stats['success_rate'] < 0.8:
                        logger.warning(
                            f"[NONCE_COORDINATOR] Low success rate for {conn_id}: "
                            f"{stats['success_rate']:.1%} ({stats['failed']} failures)"
                        )
                    
                    # Check for stale connections
                    if stats['last_timestamp']:
                        last_time = datetime.fromisoformat(stats['last_timestamp'])
                        age = (datetime.now() - last_time).total_seconds()
                        
                        if age > 3600:  # 1 hour
                            logger.info(f"[NONCE_COORDINATOR] Stale connection {conn_id}, cleaning up")
                            self.cleanup_connection(conn_id)
                
            except Exception as e:
                logger.error(f"[NONCE_COORDINATOR] Monitor error: {e}")


# Integration helper for existing WebSocket managers
class NonceWebSocketWrapper:
    """
    Wrapper to add nonce coordination to existing WebSocket connections.
    """
    
    def __init__(self, websocket, coordinator: WebSocketNonceCoordinator):
        """
        Wrap a WebSocket with nonce coordination.
        
        Args:
            websocket: Original WebSocket connection
            coordinator: Nonce coordinator instance
        """
        self.websocket = websocket
        self.coordinator = coordinator
        self.connection_id = f"ws_{id(websocket)}"
        
        # Register with coordinator
        self.coordinator.register_connection(self.connection_id)
    
    async def send_authenticated(self, message: Dict[str, Any]) -> None:
        """
        Send a message with proper nonce handling.
        
        Args:
            message: Message to send (will add nonce)
        """
        # Add nonce if authentication message
        if message.get('event') == 'subscribe' and 'reqid' not in message:
            nonce = self.coordinator.get_auth_nonce(self.connection_id)
            message['reqid'] = nonce
        
        # Send message
        await self.websocket.send(json.dumps(message))
        
        # Track if it has a nonce
        if 'reqid' in message:
            logger.debug(f"[NONCE_WRAPPER] Sent message with nonce {message['reqid']}")
    
    async def close(self) -> None:
        """Close connection and cleanup."""
        await self.websocket.close()
        self.coordinator.cleanup_connection(self.connection_id)


# Global coordinator instance
_global_coordinator: Optional[WebSocketNonceCoordinator] = None


def get_nonce_coordinator() -> WebSocketNonceCoordinator:
    """Get or create global nonce coordinator."""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = WebSocketNonceCoordinator()
    return _global_coordinator