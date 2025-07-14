"""
Kraken Nonce Manager - Thread-safe nonce generation for WebSocket connections

This module provides a thread-safe nonce management system with microsecond
precision for Kraken API authentication. Each connection gets its own
sequential nonce sequence to prevent conflicts.
"""

import threading
import time
from typing import Dict, Optional
import logging
from collections import defaultdict
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class KrakenNonceManager:
    """
    Thread-safe nonce manager for Kraken WebSocket connections.
    
    Features:
    - Microsecond precision timestamps
    - Per-connection nonce sequences
    - Thread-safe operations
    - Automatic cleanup of stale connections
    - Nonce gap prevention
    """
    
    def __init__(self, cleanup_after_seconds: int = 3600):
        """
        Initialize the nonce manager.
        
        Args:
            cleanup_after_seconds: Remove connection nonces after this many seconds of inactivity
        """
        # Start with current microsecond timestamp
        self._base_nonce = int(time.time() * 1000000)
        
        # Thread lock for all operations
        self._lock = threading.Lock()
        
        # Per-connection nonce tracking
        self._connection_nonces: Dict[str, int] = {}
        
        # Track last access time for cleanup
        self._last_access: Dict[str, float] = {}
        
        # Cleanup configuration
        self._cleanup_after_seconds = cleanup_after_seconds
        
        # Global counter for fallback
        self._global_counter = 0
        
        # Statistics
        self._stats = defaultdict(int)
        
        # SECURITY FIX: Mask sensitive nonce data in logs
        masked_nonce = self._mask_sensitive_data(self._base_nonce)
        logger.info(f"[NONCE_MANAGER] Initialized with base nonce: {masked_nonce}")
    
    def get_nonce(self, connection_id: str) -> int:
        """
        Get the next nonce for a specific connection.
        
        Thread-safe method that ensures each connection gets sequential nonces.
        
        Args:
            connection_id: Unique identifier for the connection
            
        Returns:
            Next sequential nonce for this connection
        """
        with self._lock:
            current_time = time.time()
            
            # Initialize connection if new
            if connection_id not in self._connection_nonces:
                # Start slightly ahead of base to avoid conflicts
                offset = len(self._connection_nonces) * 1000
                self._connection_nonces[connection_id] = self._base_nonce + offset
                # SECURITY FIX: Mask sensitive nonce data in logs
                masked_nonce = self._mask_sensitive_data(self._connection_nonces[connection_id])
                logger.debug(f"[NONCE_MANAGER] New connection {connection_id} starting at {masked_nonce}")
            
            # Increment nonce for this connection
            self._connection_nonces[connection_id] += 1
            nonce = self._connection_nonces[connection_id]
            
            # Update last access time
            self._last_access[connection_id] = current_time
            
            # Update statistics
            self._stats['total_nonces'] += 1
            self._stats[f'connection_{connection_id}'] += 1
            
            # Claude Flow Fix: Enhanced nonce validation and recovery with 2025 buffer increase
            current_microseconds = int(current_time * 1000000)
            if nonce <= current_microseconds:
                # Jump ahead if we've fallen behind real time - CRITICAL FIX: 1000+ microsecond buffer
                self._connection_nonces[connection_id] = current_microseconds + 1500  # MASSIVE buffer for 2025 API changes
                nonce = self._connection_nonces[connection_id]
                # SECURITY FIX: Mask sensitive nonce data in logs
                masked_nonce = self._mask_sensitive_data(nonce)
                logger.debug(f"[NONCE_MANAGER] Nonce advanced for {connection_id}: {masked_nonce}")
            
            # Prevent nonce overflow (keep within reasonable bounds)
            max_nonce = int((current_time + 86400) * 1000000)  # Max 24h in future
            if nonce > max_nonce:
                logger.warning(f"[NONCE_MANAGER] Nonce reset for {connection_id} - was too far in future")
                self._connection_nonces[connection_id] = current_microseconds + 1
                nonce = self._connection_nonces[connection_id]
                self._stats['time_jumps'] += 1
                # SECURITY FIX: Mask sensitive nonce data in logs
                masked_nonce = self._mask_sensitive_data(nonce)
                logger.warning(f"[NONCE_MANAGER] Time jump for {connection_id}, new nonce: {masked_nonce}")
            
            # Periodic cleanup check (every 1000 nonces)
            if self._stats['total_nonces'] % 1000 == 0:
                self._cleanup_stale_connections(current_time)
            
            return nonce
    
    def get_batch_nonces(self, connection_id: str, count: int) -> list[int]:
        """
        Get multiple sequential nonces for batch operations.
        
        Args:
            connection_id: Unique identifier for the connection
            count: Number of nonces to generate
            
        Returns:
            List of sequential nonces
        """
        with self._lock:
            nonces = []
            
            # Get current nonce or initialize
            if connection_id not in self._connection_nonces:
                self.get_nonce(connection_id)  # Initialize
            
            start_nonce = self._connection_nonces[connection_id]
            
            # Generate sequential nonces
            for i in range(count):
                self._connection_nonces[connection_id] += 1
                nonces.append(self._connection_nonces[connection_id])
            
            # Update last access
            self._last_access[connection_id] = time.time()
            
            # Update statistics
            self._stats['total_nonces'] += count
            self._stats[f'connection_{connection_id}'] += count
            self._stats['batch_operations'] += 1
            
            # SECURITY FIX: Mask sensitive nonce data in logs
            masked_start = self._mask_sensitive_data(start_nonce+1)
            masked_end = self._mask_sensitive_data(self._connection_nonces[connection_id])
            logger.debug(f"[NONCE_MANAGER] Batch of {count} nonces for {connection_id}: {masked_start} to {masked_end}")
            
            return nonces
    
    def reset_connection(self, connection_id: str) -> None:
        """
        Reset nonce sequence for a connection (e.g., after reconnection).
        
        Args:
            connection_id: Connection to reset
        """
        with self._lock:
            if connection_id in self._connection_nonces:
                old_nonce = self._connection_nonces[connection_id]
                # Jump significantly ahead to avoid any conflicts
                new_nonce = int(time.time() * 1000000) + 10000
                self._connection_nonces[connection_id] = new_nonce
                # SECURITY FIX: Mask sensitive nonce data in logs
                masked_old = self._mask_sensitive_data(old_nonce)
                masked_new = self._mask_sensitive_data(new_nonce)
                logger.info(f"[NONCE_MANAGER] Reset {connection_id} from {masked_old} to {masked_new}")
                self._stats['resets'] += 1
            else:
                logger.warning(f"[NONCE_MANAGER] Attempted to reset unknown connection: {connection_id}")
    
    def remove_connection(self, connection_id: str) -> None:
        """
        Remove a connection from tracking (cleanup).
        
        Args:
            connection_id: Connection to remove
        """
        with self._lock:
            if connection_id in self._connection_nonces:
                del self._connection_nonces[connection_id]
                del self._last_access[connection_id]
                logger.info(f"[NONCE_MANAGER] Removed connection: {connection_id}")
                self._stats['removed_connections'] += 1
    
    def _cleanup_stale_connections(self, current_time: float) -> None:
        """
        Remove connections that haven't been used recently.
        
        Args:
            current_time: Current timestamp for comparison
        """
        stale_connections = []
        
        for conn_id, last_access in self._last_access.items():
            if current_time - last_access > self._cleanup_after_seconds:
                stale_connections.append(conn_id)
        
        for conn_id in stale_connections:
            del self._connection_nonces[conn_id]
            del self._last_access[conn_id]
            self._stats['auto_cleaned'] += 1
        
        if stale_connections:
            logger.info(f"[NONCE_MANAGER] Cleaned {len(stale_connections)} stale connections")
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get usage statistics for monitoring.
        
        Returns:
            Dictionary of statistics
        """
        with self._lock:
            stats = dict(self._stats)
            stats['active_connections'] = len(self._connection_nonces)
            stats['base_nonce'] = self._base_nonce
            
            # Add per-connection info
            connection_info = {}
            for conn_id, nonce in self._connection_nonces.items():
                connection_info[conn_id] = {
                    'current_nonce': nonce,
                    'last_access': self._last_access.get(conn_id, 0),
                    'count': self._stats.get(f'connection_{conn_id}', 0)
                }
            stats['connections'] = connection_info
            
            return stats
    
    def _mask_sensitive_data(self, value) -> str:
        """
        SECURITY FIX: Mask sensitive nonce data for logging
        Shows first 4 digits and masks the rest to prevent credential exposure
        """
        try:
            str_value = str(value)
            if len(str_value) <= 4:
                return str_value
            return f"{str_value[:4]}{'*' * (len(str_value) - 4)}"
        except Exception:
            return "****"
    
    def validate_nonce_sequence(self, connection_id: str, nonces: list[int]) -> bool:
        """
        Validate that a sequence of nonces is properly sequential.
        
        Args:
            connection_id: Connection to validate
            nonces: List of nonces to check
            
        Returns:
            True if sequence is valid
        """
        if not nonces:
            return True
        
        # Check sequential
        for i in range(1, len(nonces)):
            if nonces[i] != nonces[i-1] + 1:
                logger.error(f"[NONCE_MANAGER] Non-sequential nonces for {connection_id}: {nonces[i-1]} -> {nonces[i]}")
                return False
        
        # Check all are unique
        if len(set(nonces)) != len(nonces):
            logger.error(f"[NONCE_MANAGER] Duplicate nonces detected for {connection_id}")
            return False
        
        return True


class NonceGenerationError(Exception):
    """Raised when nonce generation fails"""
    pass


# Global instance for convenience
_global_nonce_manager: Optional[KrakenNonceManager] = None


def get_nonce_manager() -> KrakenNonceManager:
    """
    Get or create the global nonce manager instance.
    
    Returns:
        Global KrakenNonceManager instance
    """
    global _global_nonce_manager
    if _global_nonce_manager is None:
        _global_nonce_manager = KrakenNonceManager()
    return _global_nonce_manager


def initialize_nonce_manager(cleanup_after_seconds: int = 3600) -> KrakenNonceManager:
    """
    Initialize the global nonce manager with custom settings.
    
    Args:
        cleanup_after_seconds: Cleanup timeout for stale connections
        
    Returns:
        Initialized KrakenNonceManager instance
    """
    global _global_nonce_manager
    _global_nonce_manager = KrakenNonceManager(cleanup_after_seconds)
    logger.info("[NONCE_MANAGER] Global instance initialized")
    return _global_nonce_manager