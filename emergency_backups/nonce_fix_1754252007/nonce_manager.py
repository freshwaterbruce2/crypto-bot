"""
Nonce Manager - DEPRECATED - Use UnifiedKrakenNonceManager instead
===================================================================

WARNING: This module is DEPRECATED in favor of UnifiedKrakenNonceManager.
Use UnifiedKrakenNonceManager from utils.unified_kraken_nonce_manager for new code.

This file is kept for backward compatibility but will be removed in future versions.
"""

import warnings
warnings.warn(
    "utils.nonce_manager is deprecated. Use UnifiedKrakenNonceManager from utils.unified_kraken_nonce_manager",
    DeprecationWarning,
    stacklevel=2
)

import os
import json
import time
import logging
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class NonceManager:
    """Manages nonce persistence to prevent 'Invalid nonce' errors"""
    
    # Class-level lock for thread safety across instances
    _global_lock = threading.Lock()
    _instances: Dict[str, 'NonceManager'] = {}
    
    def __new__(cls, api_key: str):
        """Ensure singleton per API key"""
        key_hash = api_key[:8] if api_key else "default"
        
        with cls._global_lock:
            if key_hash not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[key_hash] = instance
                instance._initialized = False
            return cls._instances[key_hash]
    
    def __init__(self, api_key: str):
        """Initialize nonce manager with API key identifier"""
        if self._initialized:
            return
            
        self.api_key_hash = api_key[:8] if api_key else "default"  # Use first 8 chars as identifier
        self.nonce_file = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", 
            f"nonce_state_{self.api_key_hash}.json"
        )
        self._local_lock = threading.Lock()
        self.last_nonce = self._load_last_nonce()
        self._save_counter = 0
        self._initialized = True
        logger.info(f"[NONCE_MANAGER] Initialized with last nonce: {self.last_nonce}")
    
    def _load_last_nonce(self) -> int:
        """Load the last used nonce from file"""
        try:
            if os.path.exists(self.nonce_file):
                with open(self.nonce_file, 'r') as f:
                    data = json.load(f)
                    saved_nonce = data.get('last_nonce', 0)
                    logger.info(f"[NONCE_MANAGER] Loaded saved nonce: {saved_nonce}")
                    
                    # Check if saved nonce is in the future (from emergency reset)
                    current_time_us = int(time.time() * 1000000)
                    if saved_nonce > current_time_us:
                        logger.info(f"[NONCE_MANAGER] Using future nonce from emergency reset: {saved_nonce}")
                        return saved_nonce
                    
                    # Always add a buffer to be safe (1 second in microseconds)
                    buffer = 1000000  # 1 second worth of microseconds
                    return saved_nonce + buffer
        except Exception as e:
            logger.warning(f"[NONCE_MANAGER] Error loading nonce file: {e}")
        
        # If no file or error, use current time in microseconds
        return int(time.time() * 1000000)  # MICROSECONDS for Kraken
    
    def get_next_nonce(self) -> str:
        """Get the next valid nonce - thread-safe"""
        with self._local_lock:
            current_time_us = int(time.time() * 1000000)  # MICROSECONDS for Kraken
            
            # Always increment by at least 1 to ensure uniqueness
            if current_time_us <= self.last_nonce:
                self.last_nonce += 1
            else:
                # Jump to current time if it's significantly ahead
                self.last_nonce = current_time_us
            
            # Increment save counter
            self._save_counter += 1
            
            # Save periodically (every 50 nonces) or if significant jump
            if self._save_counter >= 50 or (current_time_us - self.last_nonce) > 10000000:  # 10 seconds in microseconds
                self._save_nonce()
                self._save_counter = 0
            
            return str(self.last_nonce)
    
    def _save_nonce(self):
        """Save the current nonce to file"""
        try:
            data = {
                'last_nonce': self.last_nonce,
                'timestamp': time.time(),
                'api_key_hash': self.api_key_hash
            }
            with open(self.nonce_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"[NONCE_MANAGER] Saved nonce: {self.last_nonce}")
        except Exception as e:
            logger.error(f"[NONCE_MANAGER] Error saving nonce: {e}")
    
    def force_save(self):
        """Force save the current nonce state"""
        with self._local_lock:
            self._save_nonce()
            logger.info(f"[NONCE_MANAGER] Force saved nonce: {self.last_nonce}")
    
    def reset_with_buffer(self, buffer_us: int = 60000000):  # 60 seconds in microseconds
        """Reset nonce with a future buffer to fix Invalid nonce errors"""
        with self._local_lock:
            new_nonce = int(time.time() * 1000000) + buffer_us  # MICROSECONDS for Kraken
            if new_nonce > self.last_nonce:
                self.last_nonce = new_nonce
                self._save_nonce()
                logger.warning(f"[NONCE_MANAGER] Reset nonce to {self.last_nonce} with {buffer_us}us buffer")
            else:
                logger.info(f"[NONCE_MANAGER] Current nonce {self.last_nonce} already ahead of reset value")
    
    @classmethod
    def cleanup_all(cls):
        """Cleanup all instances and force save"""
        with cls._global_lock:
            for instance in cls._instances.values():
                instance.force_save()
            cls._instances.clear()
