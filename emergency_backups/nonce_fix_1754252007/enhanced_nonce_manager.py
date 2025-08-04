"""
Enhanced Nonce Manager for Kraken API 2025 - DEPRECATED
========================================================

WARNING: This module is DEPRECATED.
Use UnifiedKrakenNonceManager from utils.unified_kraken_nonce_manager instead.

This file is kept for backward compatibility but should not be used in new code.
"""

import warnings
warnings.warn(
    "enhanced_nonce_manager is deprecated. Use UnifiedKrakenNonceManager from utils.unified_kraken_nonce_manager",
    DeprecationWarning,
    stacklevel=2
)

import time
import threading
import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EnhancedNonceManager:
    """Enhanced nonce manager with microsecond precision and persistence"""
    
    def __init__(self, api_key: str, nonce_file_dir: str = None):
        """
        Initialize enhanced nonce manager
        
        Args:
            api_key: API key for unique nonce tracking
            nonce_file_dir: Directory to store nonce state files
        """
        self.api_key = api_key
        self.lock = threading.Lock()
        
        # Use project directory for nonce files
        if nonce_file_dir is None:
            nonce_file_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Create unique nonce state file per API key
        api_key_hash = hash(api_key) % 1000000  # Simple hash for filename
        self.nonce_file = os.path.join(nonce_file_dir, f"nonce_state_{api_key_hash}.json")
        
        # Initialize nonce state
        self.last_nonce = self._load_last_nonce()
        self.nonce_offset = 0  # For collision recovery
        
        logger.info(f"[NONCE_2025] Enhanced nonce manager initialized with last nonce: {self.last_nonce}")
    
    def _load_last_nonce(self) -> int:
        """Load last used nonce from persistent storage"""
        try:
            if os.path.exists(self.nonce_file):
                with open(self.nonce_file, 'r') as f:
                    data = json.load(f)
                    return int(data.get('last_nonce', 0))
            else:
                # Initialize with current microsecond timestamp
                return int(time.time() * 1000000)
        except Exception as e:
            logger.warning(f"[NONCE_2025] Failed to load nonce state: {e}")
            return int(time.time() * 1000000)
    
    def _save_nonce_state(self, nonce: int) -> None:
        """Save nonce state to persistent storage"""
        try:
            with open(self.nonce_file, 'w') as f:
                json.dump({
                    'last_nonce': nonce,
                    'timestamp': time.time(),
                    'api_key_hash': hash(self.api_key) % 1000000
                }, f)
        except Exception as e:
            logger.warning(f"[NONCE_2025] Failed to save nonce state: {e}")
    
    def get_next_nonce(self) -> str:
        """
        Generate next unique nonce with microsecond precision
        
        Returns:
            String nonce guaranteed to be unique and increasing
        """
        with self.lock:
            # Get current microsecond timestamp
            current_micro = int(time.time() * 1000000)
            
            # Ensure nonce is always increasing
            if current_micro <= self.last_nonce:
                # If time hasn't advanced enough, use last nonce + offset
                next_nonce = self.last_nonce + 1 + self.nonce_offset
                self.nonce_offset += 1
                
                # Reset offset periodically to avoid large values
                if self.nonce_offset > 1000:
                    self.nonce_offset = 0
                    
            else:
                # Time has advanced, use current timestamp
                next_nonce = current_micro
                self.nonce_offset = 0
            
            # Update last nonce
            self.last_nonce = next_nonce
            
            # Save state periodically (every 10 nonces to reduce I/O)
            if next_nonce % 10 == 0:
                self._save_nonce_state(next_nonce)
            
            logger.debug(f"[NONCE_2025] Generated nonce: {next_nonce}")
            return str(next_nonce)
    
    def handle_invalid_nonce_error(self) -> str:
        """
        Handle "Invalid nonce" error by generating a fresh nonce
        
        Returns:
            New nonce guaranteed to be valid
        """
        with self.lock:
            logger.warning("[NONCE_2025] Invalid nonce error - generating recovery nonce")
            
            # Force refresh with current time + large offset
            current_micro = int(time.time() * 1000000)
            recovery_nonce = max(current_micro, self.last_nonce + 10000)
            
            self.last_nonce = recovery_nonce
            self.nonce_offset = 0
            
            # Immediately save recovery state
            self._save_nonce_state(recovery_nonce)
            
            logger.info(f"[NONCE_2025] Recovery nonce generated: {recovery_nonce}")
            return str(recovery_nonce)
    
    def get_nonce_status(self) -> dict:
        """Get current nonce manager status for debugging"""
        with self.lock:
            return {
                'last_nonce': self.last_nonce,
                'current_offset': self.nonce_offset,
                'current_time_micro': int(time.time() * 1000000),
                'nonce_file': self.nonce_file,
                'file_exists': os.path.exists(self.nonce_file)
            }
    
    def reset_nonce_state(self) -> None:
        """Reset nonce state (use only for testing or emergency recovery)"""
        with self.lock:
            logger.warning("[NONCE_2025] EMERGENCY: Resetting nonce state")
            
            # Set to current time with buffer
            self.last_nonce = int(time.time() * 1000000) + 1000
            self.nonce_offset = 0
            
            # Save immediately
            self._save_nonce_state(self.last_nonce)
            
            logger.info(f"[NONCE_2025] Nonce state reset to: {self.last_nonce}")
    
    def cleanup(self) -> None:
        """Cleanup resources and save final state"""
        try:
            with self.lock:
                if self.last_nonce > 0:
                    self._save_nonce_state(self.last_nonce)
                logger.info("[NONCE_2025] Nonce manager cleanup complete")
        except Exception as e:
            logger.error(f"[NONCE_2025] Error during cleanup: {e}")