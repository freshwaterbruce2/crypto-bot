# DEPRECATED - DO NOT USE THIS NONCE MANAGER
# This file has been temporarily disabled to prevent nonce conflicts.
# All nonce operations should use src/utils/unified_kraken_nonce_manager.py
# 
# If you see import errors, update your imports to use UnifiedKrakenNonceManager
#
# Emergency fix applied: 2025-08-03
# Issue: Multiple nonce managers causing "EAPI:Invalid nonce" errors

"""
Kraken API Nonce Manager - 2025 Compliance - DEPRECATED
========================================================

WARNING: This module is DEPRECATED.
Use UnifiedKrakenNonceManager from utils.unified_kraken_nonce_manager instead.

This file is kept for backward compatibility but should not be used in new code.
"""

import warnings
warnings.warn(
    "auth.nonce_manager is deprecated. Use UnifiedKrakenNonceManager from utils.unified_kraken_nonce_manager",
    DeprecationWarning,
    stacklevel=2
)

import time
import threading
import json
import os
import hashlib
import logging
from typing import Dict, Optional, Any
from pathlib import Path
import asyncio
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class NonceState:
    """Nonce state data structure"""
    last_nonce: int
    timestamp: float
    api_key_hash: str
    counter: int = 0
    version: str = "2025.1.0"


class NonceManager:
    """
    Production-ready nonce manager for Kraken API 2025 compliance.
    
    Provides thread-safe, persistent nonce generation with microsecond precision
    to prevent "Invalid nonce" errors and support high-frequency trading.
    """
    
    # Class-level tracking for multiple API keys
    _instances: Dict[str, 'NonceManager'] = {}
    _global_lock = threading.Lock()
    
    def __init__(self, api_key: str, storage_dir: Optional[str] = None):
        """
        Initialize nonce manager for specific API key.
        
        Args:
            api_key: Kraken API key for unique identification
            storage_dir: Directory for nonce state files (default: project root)
        """
        self.api_key = api_key
        self.api_key_hash = self._generate_api_key_hash(api_key)
        
        # Thread safety
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        
        # Storage configuration
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.nonce_file = self.storage_dir / f"nonce_state_{self.api_key_hash}.json"
        
        # State management
        self._state = self._load_nonce_state()
        self._save_counter = 0
        self._save_frequency = 10  # Save every N nonces
        
        # Time drift protection
        self._max_future_drift = 3600  # 1 hour in seconds
        self._min_increment = 1  # Minimum nonce increment
        
        logger.info(f"[NONCE_2025] Initialized for API key hash {self.api_key_hash[:8]}... "
                   f"with last nonce: {self._state.last_nonce}")
    
    def _generate_api_key_hash(self, api_key: str) -> str:
        """Generate secure hash of API key for file naming"""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    def _load_nonce_state(self) -> NonceState:
        """Load nonce state from persistent storage with validation"""
        try:
            if self.nonce_file.exists():
                with open(self.nonce_file, 'r') as f:
                    data = json.load(f)
                
                # Validate loaded data
                state = NonceState(**data)
                
                # Validate nonce is reasonable
                current_time_us = self._get_current_time_microseconds()
                max_future_nonce = current_time_us + (self._max_future_drift * 1_000_000)
                
                if state.last_nonce > max_future_nonce:
                    logger.warning(f"[NONCE_2025] Loaded nonce {state.last_nonce} is too far in future, "
                                 f"resetting to current time")
                    state.last_nonce = current_time_us
                
                logger.info(f"[NONCE_2025] Loaded state: nonce={state.last_nonce}, "
                           f"counter={state.counter}")
                return state
                
        except Exception as e:
            logger.warning(f"[NONCE_2025] Failed to load nonce state: {e}")
        
        # Initialize with current time if no valid state found
        current_time_us = self._get_current_time_microseconds()
        state = NonceState(
            last_nonce=current_time_us,
            timestamp=time.time(),
            api_key_hash=self.api_key_hash
        )
        
        logger.info(f"[NONCE_2025] Initialized new state with nonce: {state.last_nonce}")
        return state
    
    def _save_nonce_state(self, force: bool = False) -> None:
        """Save nonce state to persistent storage"""
        try:
            if not force:
                self._save_counter += 1
                if self._save_counter < self._save_frequency:
                    return
                self._save_counter = 0
            
            # Update timestamp
            self._state.timestamp = time.time()
            
            # Atomic write using temporary file
            temp_file = self.nonce_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(asdict(self._state), f, indent=2)
            
            # Atomic replace
            temp_file.replace(self.nonce_file)
            
            logger.debug(f"[NONCE_2025] Saved state: nonce={self._state.last_nonce}")
            
        except Exception as e:
            logger.error(f"[NONCE_2025] Failed to save nonce state: {e}")
    
    def _get_current_time_microseconds(self) -> int:
        """Get current Unix timestamp in microseconds"""
        return int(time.time_ns() // 1000)  # Convert nanoseconds to microseconds
    
    def get_next_nonce(self) -> str:
        """
        Generate next unique nonce with thread safety.
        
        Returns:
            String representation of 64-bit microsecond timestamp nonce
        """
        with self._lock:
            current_time_us = self._get_current_time_microseconds()
            
            # Ensure nonce is always increasing
            if current_time_us <= self._state.last_nonce:
                # Time hasn't advanced enough, increment by minimum
                next_nonce = self._state.last_nonce + self._min_increment
            else:
                # Use current time as it's sufficiently advanced
                next_nonce = current_time_us
            
            # Update state
            self._state.last_nonce = next_nonce
            self._state.counter += 1
            
            # Periodic save
            self._save_nonce_state()
            
            logger.debug(f"[NONCE_2025] Generated nonce: {next_nonce} "
                        f"(counter: {self._state.counter})")
            
            return str(next_nonce)
    
    async def get_next_nonce_async(self) -> str:
        """
        Async version of get_next_nonce for asyncio applications.
        
        Returns:
            String representation of 64-bit microsecond timestamp nonce
        """
        async with self._async_lock:
            # Use sync method within async lock
            return self.get_next_nonce()
    
    def handle_invalid_nonce_error(self, failed_nonce: Optional[str] = None) -> str:
        """
        Handle "Invalid nonce" error with automatic recovery.
        
        Args:
            failed_nonce: The nonce that failed (for logging)
            
        Returns:
            New recovery nonce guaranteed to be valid
        """
        with self._lock:
            current_time_us = self._get_current_time_microseconds()
            
            logger.warning(f"[NONCE_2025] Invalid nonce error detected. "
                          f"Failed nonce: {failed_nonce}, "
                          f"Last nonce: {self._state.last_nonce}")
            
            # Create recovery nonce with significant buffer
            recovery_buffer = 10_000  # 10ms buffer in microseconds
            recovery_nonce = max(
                current_time_us + recovery_buffer,
                self._state.last_nonce + recovery_buffer
            )
            
            # Update state
            self._state.last_nonce = recovery_nonce
            self._state.counter += 1
            
            # Force save recovery state
            self._save_nonce_state(force=True)
            
            logger.info(f"[NONCE_2025] Recovery nonce generated: {recovery_nonce}")
            
            return str(recovery_nonce)
    
    def validate_nonce(self, nonce: str) -> bool:
        """
        Validate if a nonce would be accepted by Kraken.
        
        Args:
            nonce: Nonce string to validate
            
        Returns:
            True if nonce is valid, False otherwise
        """
        try:
            nonce_int = int(nonce)
            current_time_us = self._get_current_time_microseconds()
            
            # Check if nonce is reasonable
            min_valid_time = current_time_us - (24 * 3600 * 1_000_000)  # 24 hours ago
            max_valid_time = current_time_us + (self._max_future_drift * 1_000_000)
            
            return min_valid_time <= nonce_int <= max_valid_time
            
        except ValueError:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive nonce manager status for monitoring.
        
        Returns:
            Dictionary with current status information
        """
        with self._lock:
            current_time_us = self._get_current_time_microseconds()
            
            return {
                'api_key_hash': self.api_key_hash[:8] + '...',
                'last_nonce': self._state.last_nonce,
                'counter': self._state.counter,
                'current_time_us': current_time_us,
                'time_diff_us': current_time_us - self._state.last_nonce,
                'nonce_file': str(self.nonce_file),
                'file_exists': self.nonce_file.exists(),
                'version': self._state.version,
                'last_saved': self._state.timestamp
            }
    
    def reset_nonce_state(self, buffer_seconds: int = 60) -> None:
        """
        Emergency reset of nonce state with time buffer.
        
        Args:
            buffer_seconds: Seconds to add as buffer (default: 60)
        """
        with self._lock:
            current_time_us = self._get_current_time_microseconds()
            buffer_us = buffer_seconds * 1_000_000
            
            logger.warning(f"[NONCE_2025] EMERGENCY RESET: Current nonce={self._state.last_nonce}")
            
            # Reset with buffer
            self._state.last_nonce = current_time_us + buffer_us
            self._state.counter = 0
            self._state.timestamp = time.time()
            
            # Force save
            self._save_nonce_state(force=True)
            
            logger.info(f"[NONCE_2025] Nonce state reset to: {self._state.last_nonce} "
                       f"(+{buffer_seconds}s buffer)")
    
    def cleanup(self) -> None:
        """Cleanup resources and save final state"""
        try:
            with self._lock:
                logger.info(f"[NONCE_2025] Cleaning up nonce manager for {self.api_key_hash[:8]}...")
                self._save_nonce_state(force=True)
                logger.info("[NONCE_2025] Cleanup completed successfully")
        except Exception as e:
            logger.error(f"[NONCE_2025] Error during cleanup: {e}")
    
    @classmethod
    def get_instance(cls, api_key: str, storage_dir: Optional[str] = None) -> 'NonceManager':
        """
        Get singleton instance for API key (thread-safe).
        
        Args:
            api_key: Kraken API key
            storage_dir: Optional storage directory
            
        Returns:
            NonceManager instance for the API key
        """
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        with cls._global_lock:
            if api_key_hash not in cls._instances:
                cls._instances[api_key_hash] = cls(api_key, storage_dir)
            
            return cls._instances[api_key_hash]
    
    @classmethod
    def cleanup_all_instances(cls) -> None:
        """Cleanup all nonce manager instances"""
        with cls._global_lock:
            for instance in cls._instances.values():
                instance.cleanup()
            cls._instances.clear()
            logger.info("[NONCE_2025] All nonce manager instances cleaned up")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()