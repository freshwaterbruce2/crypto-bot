"""
Unified Kraken Nonce Manager - Single authoritative source for all nonce generation

This is the ONLY nonce manager that should be used across the entire application.
It provides:
- Global singleton pattern to prevent multiple instances
- Microsecond precision with guaranteed minimum increments
- Thread-safe and async-safe operations
- Persistent state across bot restarts
- Automatic recovery from invalid nonce errors
- Connection-aware tracking with global coordination
- Enhanced KrakenNonceFixer integration for guaranteed-unique nonces

Author: Trading Bot Team
Version: 3.0.0 (2025 Enhanced Edition with Advanced Nonce Fix)
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union, Any

logger = logging.getLogger(__name__)


class KrakenNonceFixer:
    """
    Advanced nonce fix implementation for eliminating 'EAPI:Invalid nonce' errors.
    
    This class provides:
    - Smart nonce initialization with large offset to avoid conflicts
    - Guaranteed-unique, increasing nonce generation
    - Enhanced API call function with fixed nonce handling
    - Integration with existing authentication systems
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize the Kraken nonce fixer.
        
        Args:
            api_key: Kraken API key
            api_secret: Base64-encoded Kraken API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Initialize with large offset to avoid conflicts
        self._base_nonce = int(time.time() * 1000000) + 100000000  # Add 100 seconds buffer
        self._nonce_counter = 0
        self._last_nonce = 0
        
        logger.info(f"[NONCE_FIXER] Initialized with base nonce offset: {self._base_nonce}")
    
    def get_guaranteed_unique_nonce(self) -> str:
        """
        Generate a guaranteed unique, increasing nonce.
        
        This method ensures:
        - Nonces are always increasing
        - No collisions even with rapid requests
        - Large buffer to avoid server-side conflicts
        
        Returns:
            String representation of unique nonce
        """
        self._nonce_counter += 1
        current_time_us = int(time.time() * 1000000)
        
        # Use the maximum of current time or incremented base to ensure increasing sequence
        nonce = max(current_time_us, self._base_nonce + self._nonce_counter * 1000)
        
        # Ensure we always move forward
        if nonce <= self._last_nonce:
            nonce = self._last_nonce + 1000  # Add 1ms minimum increment
        
        self._last_nonce = nonce
        
        logger.debug(f"[NONCE_FIXER] Generated guaranteed unique nonce: {nonce}")
        return str(nonce)
    
    async def make_authenticated_api_call(self, uri_path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make an authenticated API call with enhanced nonce handling.
        
        Args:
            uri_path: API endpoint path (e.g., '/0/private/Balance')
            params: Request parameters
            
        Returns:
            API response dictionary
            
        Raises:
            Exception: If API call fails after retries
        """
        import aiohttp
        import hmac
        import hashlib
        import base64
        from urllib.parse import urlencode
        
        if params is None:
            params = {}
        
        max_retries = 5
        base_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                # Get guaranteed unique nonce
                nonce = self.get_guaranteed_unique_nonce()
                
                # Add nonce to parameters
                api_params = params.copy()
                api_params['nonce'] = nonce
                
                # Create post data
                post_data = urlencode(api_params)
                
                # Generate signature
                sha256_hash = hashlib.sha256(post_data.encode('utf-8')).digest()
                message = uri_path.encode('utf-8') + sha256_hash
                secret = base64.b64decode(self.api_secret)
                signature = base64.b64encode(hmac.new(secret, message, hashlib.sha512).digest()).decode('utf-8')
                
                # Prepare headers
                headers = {
                    'API-Key': self.api_key,
                    'API-Sign': signature,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Trading Bot 2025/3.0'
                }
                
                # Make API request
                url = f"https://api.kraken.com{uri_path}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, data=post_data, timeout=30) as response:
                        result = await response.json()
                        
                        # Check for nonce errors
                        if 'error' in result and result['error']:
                            error_messages = result['error']
                            if any('nonce' in str(err).lower() for err in error_messages):
                                logger.warning(f"[NONCE_FIXER] Nonce error on attempt {attempt + 1}: {error_messages}")
                                
                                if attempt < max_retries - 1:
                                    # Apply nonce recovery - jump ahead significantly
                                    self._base_nonce = int(time.time() * 1000000) + 200000000  # Add 200 seconds
                                    self._nonce_counter = 0
                                    
                                    # Wait before retry
                                    await asyncio.sleep(base_delay * (2 ** attempt))
                                    continue
                                else:
                                    raise Exception(f"Nonce error after all retries: {error_messages}")
                            else:
                                # Non-nonce error
                                raise Exception(f"API error: {error_messages}")
                        
                        # Success
                        logger.debug(f"[NONCE_FIXER] API call successful on attempt {attempt + 1}")
                        return result
                        
            except asyncio.TimeoutError:
                logger.warning(f"[NONCE_FIXER] Timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (2 ** attempt))
                    continue
                else:
                    raise Exception("API call timeout after all retries")
                    
            except Exception as e:
                logger.error(f"[NONCE_FIXER] API call error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (2 ** attempt))
                    continue
                else:
                    raise
        
        raise Exception("API call failed after all retries")
    
    def test_nonce_fix(self) -> Dict[str, Any]:
        """
        Test the nonce fix implementation.
        
        Returns:
            Test results dictionary
        """
        try:
            # Generate several nonces to test uniqueness
            nonces = []
            for i in range(10):
                nonce = self.get_guaranteed_unique_nonce()
                nonces.append(int(nonce))
                time.sleep(0.001)  # Small delay
            
            # Verify they are all increasing
            is_increasing = all(nonces[i] < nonces[i+1] for i in range(len(nonces)-1))
            
            return {
                'success': True,
                'nonces_generated': len(nonces),
                'sequence_increasing': is_increasing,
                'first_nonce': nonces[0],
                'last_nonce': nonces[-1],
                'range_span': nonces[-1] - nonces[0],
                'base_nonce': self._base_nonce
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class UnifiedKrakenNonceManager:
    """
    The single, unified nonce manager for all Kraken API operations.
    
    This manager ensures that nonces are always increasing, even across:
    - Multiple API connections
    - REST and WebSocket calls
    - Bot restarts
    - Concurrent operations
    """
    
    # Class-level attributes for singleton pattern
    _instance: Optional['UnifiedKrakenNonceManager'] = None
    _lock = threading.Lock()
    
    # Constants
    MIN_INCREMENT_US = 10000  # 10ms minimum increment to prevent collisions
    RECOVERY_BUFFER_US = 60000000  # 60 second buffer for error recovery
    SAVE_INTERVAL = 50  # Save state every N nonces
    
    def __new__(cls):
        """Enforce singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """Initialize the unified nonce manager"""
        if self._initialized:
            return
            
        # Initialize KrakenNonceFixer if credentials provided
        self._nonce_fixer = None
        if api_key and api_secret:
            try:
                self._nonce_fixer = KrakenNonceFixer(api_key, api_secret)
                logger.info("[UNIFIED_NONCE] Integrated KrakenNonceFixer for enhanced authentication")
            except Exception as e:
                logger.warning(f"[UNIFIED_NONCE] Failed to initialize KrakenNonceFixer: {e}")
            
        # Threading and async locks - using RLock for reentrant locking
        self._thread_lock = threading.RLock()
        self._async_lock = asyncio.Lock()
        
        # State file location - using D drive as specified in requirements
        try:
            # Try D drive first (as specified in user requirements)
            d_drive_path = Path("D:/trading_data")
            d_drive_path.mkdir(exist_ok=True)
            self._state_file = d_drive_path / "nonce_state.json"
        except Exception:
            # Fallback to project directory if D drive not available
            self._state_file = Path(__file__).parent.parent.parent / "unified_nonce_state.json"
        
        # Initialize state
        self._last_nonce = self._load_state()
        self._save_counter = 0
        
        # Connection tracking (for debugging/monitoring)
        self._connection_tracker: Dict[str, int] = {}
        self._connection_counts: Dict[str, int] = {}
        
        # Statistics
        self._total_nonces = 0
        self._error_recoveries = 0
        self._last_save_time = time.time()
        
        self._initialized = True
        
        # Log initialization (masked for security)
        masked_nonce = self._mask_nonce(self._last_nonce)
        logger.info(f"[UNIFIED_NONCE] Initialized with nonce: {masked_nonce}")
    
    def _load_state(self) -> int:
        """Load persisted nonce state from file"""
        try:
            if self._state_file.exists():
                with open(self._state_file, 'r') as f:
                    data = json.load(f)
                    saved_nonce = data.get('last_nonce', 0)
                    saved_time = data.get('timestamp', 0)
                    
                    # Validate saved nonce
                    current_us = int(time.time() * 1000000)
                    
                    # If saved nonce is from the future (recovery), use it
                    if saved_nonce > current_us:
                        logger.info(f"[UNIFIED_NONCE] Using future nonce from recovery: {self._mask_nonce(saved_nonce)}")
                        return saved_nonce
                    
                    # Add buffer to saved nonce to ensure uniqueness
                    return saved_nonce + self.MIN_INCREMENT_US
                    
        except Exception as e:
            logger.error(f"[UNIFIED_NONCE] Error loading state: {e}")
        
        # Default to current time with buffer
        return int(time.time() * 1000000) + self.MIN_INCREMENT_US
    
    def _save_state(self) -> None:
        """Persist current nonce state to file"""
        try:
            state_data = {
                'last_nonce': self._last_nonce,
                'timestamp': time.time(),
                'iso_time': datetime.utcnow().isoformat(),
                'total_generated': self._total_nonces,
                'error_recoveries': self._error_recoveries,
                'connections': len(self._connection_tracker)
            }
            
            # Write to temporary file first (atomic operation)
            temp_file = self._state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            # Atomic rename
            temp_file.replace(self._state_file)
            
            self._last_save_time = time.time()
            logger.debug(f"[UNIFIED_NONCE] State saved: {self._mask_nonce(self._last_nonce)}")
            
        except Exception as e:
            logger.error(f"[UNIFIED_NONCE] Error saving state: {e}")
    
    def get_nonce(self, connection_id: str = "default") -> str:
        """
        Get the next valid nonce for API operations.
        
        Thread-safe method that guarantees:
        - Nonces always increase
        - Minimum increment of 10ms between nonces
        - No collisions across connections
        
        Args:
            connection_id: Identifier for the connection (for tracking)
            
        Returns:
            String representation of the next nonce
        """
        with self._thread_lock:
            current_us = int(time.time() * 1000000)
            
            # Ensure we always move forward by at least MIN_INCREMENT_US
            if self._last_nonce >= current_us:
                # We're ahead of real time, increment by minimum
                self._last_nonce += self.MIN_INCREMENT_US
            else:
                # We're behind real time, jump forward with buffer
                # This handles clock adjustments and long pauses
                self._last_nonce = current_us + self.MIN_INCREMENT_US
            
            # Track connection usage
            self._connection_tracker[connection_id] = self._last_nonce
            self._connection_counts[connection_id] = self._connection_counts.get(connection_id, 0) + 1
            
            # Update statistics
            self._total_nonces += 1
            self._save_counter += 1
            
            # Periodic state save
            if self._save_counter >= self.SAVE_INTERVAL:
                self._save_state()
                self._save_counter = 0
            
            # Log every 100th nonce for monitoring
            if self._total_nonces % 100 == 0:
                logger.debug(f"[UNIFIED_NONCE] Generated {self._total_nonces} nonces, "
                           f"current: {self._mask_nonce(self._last_nonce)}")
            
            return str(self._last_nonce)
    
    def get_next_nonce(self, connection_id: str = "default") -> str:
        """Alias for get_nonce - matches other nonce manager interfaces"""
        return self.get_nonce(connection_id)
    
    async def get_nonce_async(self, connection_id: str = "default") -> str:
        """
        Async version of get_nonce for asyncio applications.
        
        Uses asyncio lock for async contexts while maintaining thread safety.
        
        Args:
            connection_id: Identifier for the connection
            
        Returns:
            String representation of the next nonce
        """
        async with self._async_lock:
            # Use thread lock inside async lock for complete safety
            return self.get_nonce(connection_id)
    
    def recover_from_error(self, connection_id: str = "default") -> str:
        """
        Emergency recovery from invalid nonce error.
        
        Jumps significantly into the future to ensure the next nonce
        will be accepted by Kraken's API.
        
        Args:
            connection_id: Connection that experienced the error
            
        Returns:
            New recovery nonce
        """
        with self._thread_lock:
            old_nonce = self._last_nonce
            
            # Jump far into the future to guarantee acceptance
            current_us = int(time.time() * 1000000)
            self._last_nonce = current_us + self.RECOVERY_BUFFER_US
            
            # Track recovery
            self._error_recoveries += 1
            
            # Force immediate save
            self._save_state()
            
            logger.warning(
                f"[UNIFIED_NONCE] Invalid nonce recovery for {connection_id}: "
                f"{self._mask_nonce(old_nonce)} -> {self._mask_nonce(self._last_nonce)} "
                f"(+{self.RECOVERY_BUFFER_US/1000000:.1f}s buffer)"
            )
            
            return str(self._last_nonce)
    
    def handle_invalid_nonce_error(self, connection_id: str = "default") -> str:
        """Backward compatibility alias for recover_from_error"""
        return self.recover_from_error(connection_id)
    
    def reset_nonce(self, connection_id: str = "default") -> str:
        """Emergency reset with large buffer - creates a 60-second jump ahead"""
        return self.recover_from_error(connection_id)
    
    def get_status(self) -> Dict[str, any]:
        """
        Get current status and statistics.
        
        Returns:
            Dictionary with status information
        """
        with self._thread_lock:
            current_us = int(time.time() * 1000000)
            
            return {
                'current_nonce': self._mask_nonce(self._last_nonce),
                'total_generated': self._total_nonces,
                'error_recoveries': self._error_recoveries,
                'active_connections': len(self._connection_tracker),
                'connection_stats': {
                    conn_id: {
                        'count': count,
                        'last_nonce': self._mask_nonce(self._connection_tracker.get(conn_id, 0))
                    }
                    for conn_id, count in self._connection_counts.items()
                },
                'time_until_current': (self._last_nonce - current_us) / 1000000.0,
                'last_save': datetime.fromtimestamp(self._last_save_time).isoformat(),
                'state_file': str(self._state_file)
            }
    
    def force_save(self) -> None:
        """Force immediate state save"""
        with self._thread_lock:
            self._save_state()
            logger.info(f"[UNIFIED_NONCE] Forced state save at nonce: {self._mask_nonce(self._last_nonce)}")
    
    def get_enhanced_nonce(self, connection_id: str = "enhanced") -> str:
        """
        Get enhanced nonce using KrakenNonceFixer if available.
        
        This method provides the most robust nonce generation for critical operations
        like WebSocket token authentication.
        
        Args:
            connection_id: Identifier for the connection
            
        Returns:
            Enhanced nonce string
        """
        if self._nonce_fixer:
            try:
                enhanced_nonce = self._nonce_fixer.get_guaranteed_unique_nonce()
                logger.debug(f"[UNIFIED_NONCE] Enhanced nonce generated: {self._mask_nonce(int(enhanced_nonce))}")
                
                # Update our internal tracking
                with self._thread_lock:
                    self._connection_tracker[connection_id] = int(enhanced_nonce)
                    self._connection_counts[connection_id] = self._connection_counts.get(connection_id, 0) + 1
                    self._total_nonces += 1
                
                return enhanced_nonce
            except Exception as e:
                logger.warning(f"[UNIFIED_NONCE] Enhanced nonce generation failed: {e}, falling back to regular nonce")
        
        # Fallback to regular nonce generation
        return self.get_nonce(connection_id)
    
    async def make_authenticated_api_call(self, uri_path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make authenticated API call using the integrated KrakenNonceFixer.
        
        This method provides the most robust API authentication with automatic
        nonce error recovery and retry logic.
        
        Args:
            uri_path: API endpoint path
            params: Request parameters
            
        Returns:
            API response dictionary
            
        Raises:
            Exception: If nonce fixer is not available or API call fails
        """
        if not self._nonce_fixer:
            raise Exception("KrakenNonceFixer not initialized. Provide API credentials to enable enhanced authentication.")
        
        return await self._nonce_fixer.make_authenticated_api_call(uri_path, params)
    
    def test_enhanced_nonce_system(self) -> Dict[str, Any]:
        """
        Test the enhanced nonce system including KrakenNonceFixer.
        
        Returns:
            Comprehensive test results
        """
        results = {
            'unified_manager_test': {},
            'nonce_fixer_test': {},
            'integration_test': {}
        }
        
        # Test unified manager
        try:
            test_nonces = []
            for i in range(5):
                nonce = self.get_nonce(f"test_{i}")
                test_nonces.append(int(nonce))
            
            results['unified_manager_test'] = {
                'success': True,
                'nonces_generated': len(test_nonces),
                'sequence_valid': all(test_nonces[i] < test_nonces[i+1] for i in range(len(test_nonces)-1)),
                'nonce_range': f"{test_nonces[0]} - {test_nonces[-1]}"
            }
        except Exception as e:
            results['unified_manager_test'] = {'success': False, 'error': str(e)}
        
        # Test nonce fixer if available
        if self._nonce_fixer:
            results['nonce_fixer_test'] = self._nonce_fixer.test_nonce_fix()
        else:
            results['nonce_fixer_test'] = {'success': False, 'error': 'KrakenNonceFixer not initialized'}
        
        # Test integration
        try:
            enhanced_nonces = []
            for i in range(3):
                nonce = self.get_enhanced_nonce(f"integration_test_{i}")
                enhanced_nonces.append(int(nonce))
            
            results['integration_test'] = {
                'success': True,
                'enhanced_nonces_generated': len(enhanced_nonces),
                'sequence_valid': all(enhanced_nonces[i] < enhanced_nonces[i+1] for i in range(len(enhanced_nonces)-1)),
                'nonce_range': f"{enhanced_nonces[0]} - {enhanced_nonces[-1]}"
            }
        except Exception as e:
            results['integration_test'] = {'success': False, 'error': str(e)}
        
        return results
    
    def _mask_nonce(self, nonce: int) -> str:
        """Mask nonce value for secure logging"""
        nonce_str = str(nonce)
        if len(nonce_str) <= 8:
            return nonce_str
        return f"{nonce_str[:4]}...{nonce_str[-4:]}"
    
    @classmethod
    def get_instance(cls) -> 'UnifiedKrakenNonceManager':
        """
        Get the global singleton instance.
        
        Returns:
            The single UnifiedKrakenNonceManager instance
        """
        return cls()
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing only)"""
        with cls._lock:
            if cls._instance:
                cls._instance.force_save()
            cls._instance = None


# Convenience function for getting the global instance
def get_unified_nonce_manager() -> UnifiedKrakenNonceManager:
    """Get the global unified nonce manager instance"""
    return UnifiedKrakenNonceManager.get_instance()


def initialize_enhanced_nonce_manager(api_key: str, api_secret: str) -> UnifiedKrakenNonceManager:
    """
    Initialize the unified nonce manager with enhanced KrakenNonceFixer integration.
    
    This should be called once during application initialization to enable
    the most robust nonce handling for all Kraken API operations.
    
    Args:
        api_key: Kraken API key
        api_secret: Base64-encoded Kraken API secret
        
    Returns:
        Enhanced UnifiedKrakenNonceManager instance
    """
    # Reset the singleton to allow reinitialization with credentials
    UnifiedKrakenNonceManager.reset_instance()
    
    # Create new instance with credentials
    manager = UnifiedKrakenNonceManager(api_key=api_key, api_secret=api_secret)
    
    logger.info("[UNIFIED_NONCE] Enhanced nonce manager initialized with KrakenNonceFixer integration")
    return manager


# For backward compatibility during migration
def get_nonce(connection_id: str = "default") -> str:
    """Convenience function for getting a nonce"""
    return get_unified_nonce_manager().get_nonce(connection_id)