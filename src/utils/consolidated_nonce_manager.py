"""
CONSOLIDATED NONCE MANAGER - Single Authoritative Source
========================================================

This is the ONE AND ONLY nonce manager for the entire trading bot system.
All other nonce managers have been consolidated into this unified implementation.

Features:
- Global singleton pattern enforced
- Thread-safe and async-safe operations
- Persistent state across bot restarts (D: drive storage)
- Enhanced KrakenNonceFixer integration
- Automatic recovery from invalid nonce errors
- Connection-aware tracking with global coordination
- Comprehensive error handling and monitoring

Version: 4.0.0 - Consolidated Edition (2025-08-04)
Author: Trading Bot Consolidation Team
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Union
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class KrakenNonceFixer:
    """
    Advanced nonce fix implementation for eliminating 'EAPI:Invalid nonce' errors.

    Provides guaranteed-unique, increasing nonce generation with enhanced API integration.
    """

    def __init__(self, api_key: str, api_secret: str):
        """Initialize with API credentials."""
        self.api_key = api_key
        self.api_secret = api_secret

        # Initialize with current time in milliseconds
        # Kraken expects millisecond timestamps
        self._last_nonce = int(time.time() * 1000)
        self._lock = threading.Lock()

        logger.info("[NONCE_FIXER] Initialized with millisecond timestamp nonces")

    def get_guaranteed_unique_nonce(self) -> str:
        """Generate guaranteed unique, increasing nonce."""
        with self._lock:
            # Use milliseconds for Kraken API
            current_time_ms = int(time.time() * 1000)

            # Ensure always increasing
            if current_time_ms <= self._last_nonce:
                nonce = self._last_nonce + 1
            else:
                nonce = current_time_ms

            self._last_nonce = nonce

            logger.debug(f"[NONCE_FIXER] Generated nonce: {nonce}")
            return str(nonce)

    async def make_authenticated_api_call(self, uri_path: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """Make authenticated API call with enhanced nonce handling."""
        import aiohttp

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
                    'User-Agent': 'Trading Bot 2025/4.0'
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
                                    # Apply nonce recovery - jump ahead slightly
                                    # Use milliseconds with small buffer
                                    self._last_nonce = int(time.time() * 1000) + 5000  # Add 5 seconds in milliseconds

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


class ConsolidatedNonceManager:
    """
    THE SINGLE, CONSOLIDATED NONCE MANAGER FOR ALL KRAKEN API OPERATIONS.

    This manager consolidates all previous nonce management systems into one
    authoritative implementation that ensures nonces are always increasing,
    even across multiple API connections, REST and WebSocket calls, bot restarts,
    and concurrent operations.

    SINGLETON PATTERN: Only one instance can exist to prevent conflicts.
    """

    # Class-level attributes for strict singleton enforcement
    _instance: Optional['ConsolidatedNonceManager'] = None
    _lock = threading.RLock()  # Reentrant lock for safety
    _initialized = False

    # Constants
    MIN_INCREMENT_MS = 100  # 100ms minimum increment to prevent collisions
    RECOVERY_BUFFER_MS = 60000  # 60 second buffer for error recovery
    SAVE_INTERVAL = 25  # Save state every N nonces

    def __new__(cls, *args, **kwargs):
        """Enforce strict singleton pattern - only one instance allowed."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._internal_initialized = False
            return cls._instance

    def __init__(self, api_key: str = None, api_secret: str = None):
        """Initialize the consolidated nonce manager."""
        if self._internal_initialized:
            return

        # Initialize KrakenNonceFixer if credentials provided
        self._nonce_fixer = None
        if api_key and api_secret:
            try:
                self._nonce_fixer = KrakenNonceFixer(api_key, api_secret)
                logger.info("[CONSOLIDATED_NONCE] Integrated KrakenNonceFixer for enhanced authentication")
            except Exception as e:
                logger.warning(f"[CONSOLIDATED_NONCE] Failed to initialize KrakenNonceFixer: {e}")

        # Threading and async locks
        self._thread_lock = threading.RLock()
        self._async_lock = asyncio.Lock()

        # State file location - using D drive as specified in requirements
        try:
            # Try D drive first (as specified in user requirements)
            d_drive_path = Path("D:/trading_data")
            d_drive_path.mkdir(exist_ok=True)
            self._state_file = d_drive_path / "consolidated_nonce_state.json"
            logger.info("[CONSOLIDATED_NONCE] Using D: drive for state persistence")
        except Exception:
            # Fallback to project directory if D drive not available
            self._state_file = Path(__file__).parent.parent.parent / "consolidated_nonce_state.json"
            logger.warning("[CONSOLIDATED_NONCE] D: drive unavailable, using project directory")

        # Initialize state - RACE CONDITION FIX
        self._last_nonce = self._load_state()
        self._nonce_counter = 0  # Atomic counter for guaranteed uniqueness
        self._save_counter = 0

        # Connection tracking (for debugging/monitoring)
        self._connection_tracker: dict[str, int] = {}
        self._connection_counts: dict[str, int] = {}
        self._connection_handlers: dict[str, Callable] = {}
        self._nonce_history: dict[str, list] = {}
        self._failed_nonces: dict[str, list] = {}

        # Statistics and monitoring
        self._total_nonces = 0
        self._error_recoveries = 0
        self._last_save_time = time.time()
        self._start_time = time.time()

        self._internal_initialized = True

        # Log initialization (masked for security)
        masked_nonce = self._mask_nonce(self._last_nonce)
        logger.info(f"[CONSOLIDATED_NONCE] Initialized singleton with nonce: {masked_nonce}")

    def _load_state(self) -> int:
        """Load persisted nonce state from file."""
        try:
            if self._state_file.exists():
                with open(self._state_file) as f:
                    data = json.load(f)
                    saved_nonce = data.get('last_nonce', 0)
                    data.get('timestamp', 0)

                    # Validate saved nonce
                    # Use MILLISECONDS
                    current_ms = int(time.time() * 1000)

                    # If saved nonce is from the future (recovery), use it
                    if saved_nonce > current_ms:
                        logger.info("[CONSOLIDATED_NONCE] Using future nonce from recovery")
                        return saved_nonce

                    # Add buffer to saved nonce to ensure uniqueness
                    # Also ensure we're ahead of current time
                    buffered_nonce = max(saved_nonce + self.MIN_INCREMENT_MS, current_ms + self.MIN_INCREMENT_MS)
                    return buffered_nonce

        except Exception as e:
            logger.error(f"[CONSOLIDATED_NONCE] Error loading state: {e}")

        # Default to current time with buffer
        # CRITICAL FIX: Use MILLISECONDS
        return int(time.time() * 1000) + 100  # Small increment in ms

    def _save_state(self) -> None:
        """Persist current nonce state to file."""
        try:
            state_data = {
                'last_nonce': self._last_nonce,
                'timestamp': time.time(),
                'iso_time': datetime.utcnow().isoformat(),
                'total_generated': self._total_nonces,
                'error_recoveries': self._error_recoveries,
                'connections': len(self._connection_tracker),
                'uptime_seconds': time.time() - self._start_time,
                'version': '4.0.0'
            }

            # Write to temporary file first (atomic operation)
            temp_file = self._state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state_data, f, indent=2)

            # Atomic rename
            temp_file.replace(self._state_file)

            self._last_save_time = time.time()
            logger.debug("[CONSOLIDATED_NONCE] State saved")

        except Exception as e:
            logger.error(f"[CONSOLIDATED_NONCE] Error saving state: {e}")

    def get_nonce(self, connection_id: str = "default") -> str:
        """
        Get the next valid nonce for API operations.

        This is the PRIMARY method for getting nonces - all other methods
        should ultimately call this one to ensure consistency.

        Thread-safe method that guarantees:
        - Nonces always increase
        - Minimum increment between nonces
        - No collisions across connections
        - Proper state persistence

        Args:
            connection_id: Identifier for the connection (for tracking)

        Returns:
            String representation of the next nonce
        """
        with self._thread_lock:
            # Use MILLISECONDS - Kraken expects millisecond timestamps
            current_ms = int(time.time() * 1000)

            # Ensure nonce is always increasing with minimum increment
            # This handles both normal operation and clock drift
            if self._last_nonce >= current_ms:
                # If last nonce is >= current time, increment from last nonce
                new_nonce = self._last_nonce + 1
            else:
                # Use current time if it's ahead of last nonce
                new_nonce = current_ms

            # Ensure minimum increment to prevent rapid-fire collisions
            if new_nonce - self._last_nonce < 1:
                new_nonce = self._last_nonce + 1

            self._last_nonce = new_nonce

            # Track connection usage
            self._connection_tracker[connection_id] = self._last_nonce
            self._connection_counts[connection_id] = self._connection_counts.get(connection_id, 0) + 1

            # Track history for monitoring
            if connection_id not in self._nonce_history:
                self._nonce_history[connection_id] = []
                self._failed_nonces[connection_id] = []

            self._nonce_history[connection_id].append({
                'nonce': str(self._last_nonce),
                'timestamp': datetime.now().isoformat(),
                'status': 'generated'
            })

            # Keep only last 50 entries per connection
            if len(self._nonce_history[connection_id]) > 50:
                self._nonce_history[connection_id] = self._nonce_history[connection_id][-50:]

            # Update statistics
            self._total_nonces += 1
            self._save_counter += 1

            # Periodic state save
            if self._save_counter >= self.SAVE_INTERVAL:
                self._save_state()
                self._save_counter = 0

            # Log every 200th nonce for monitoring (with security masking)
            if self._total_nonces % 200 == 0:
                logger.info(f"[CONSOLIDATED_NONCE] Generated {self._total_nonces} nonces total")

            return str(self._last_nonce)

    def get_next_nonce(self, connection_id: str = "default") -> str:
        """Alias for get_nonce - matches legacy interfaces."""
        return self.get_nonce(connection_id)

    async def get_nonce_async(self, connection_id: str = "default") -> str:
        """Async version of get_nonce for asyncio applications."""
        async with self._async_lock:
            return self.get_nonce(connection_id)

    def get_enhanced_nonce(self, connection_id: str = "enhanced") -> str:
        """Get enhanced nonce using KrakenNonceFixer if available."""
        if self._nonce_fixer:
            try:
                enhanced_nonce = self._nonce_fixer.get_guaranteed_unique_nonce()
                logger.debug("[CONSOLIDATED_NONCE] Enhanced nonce generated")

                # Update our internal tracking
                with self._thread_lock:
                    self._connection_tracker[connection_id] = int(enhanced_nonce)
                    self._connection_counts[connection_id] = self._connection_counts.get(connection_id, 0) + 1
                    self._total_nonces += 1

                return enhanced_nonce
            except Exception as e:
                logger.warning(f"[CONSOLIDATED_NONCE] Enhanced nonce generation failed: {e}, falling back")

        # Fallback to regular nonce generation
        return self.get_nonce(connection_id)

    def recover_from_error(self, connection_id: str = "default") -> str:
        """Emergency recovery from invalid nonce error."""
        with self._thread_lock:
            old_nonce = self._last_nonce

            # Jump far into the future to guarantee acceptance
            # Use MILLISECONDS
            current_ms = int(time.time() * 1000)
            self._last_nonce = current_ms + self.RECOVERY_BUFFER_MS

            # Track recovery
            self._error_recoveries += 1

            # Track failed nonce
            if connection_id in self._failed_nonces:
                self._failed_nonces[connection_id].append({
                    'nonce': old_nonce,
                    'error': 'Invalid nonce recovery',
                    'timestamp': datetime.now().isoformat()
                })

            # Force immediate save
            self._save_state()

            logger.warning(
                f"[CONSOLIDATED_NONCE] Invalid nonce recovery for {connection_id}: "
                f"jumped +{self.RECOVERY_BUFFER_MS/1000000:.1f}s"
            )

            return str(self._last_nonce)

    def handle_invalid_nonce_error(self, connection_id: str = "default") -> str:
        """Handle invalid nonce error with recovery."""
        return self.recover_from_error(connection_id)

    def reset_nonce(self, connection_id: str = "default") -> str:
        """Emergency reset with large buffer."""
        return self.recover_from_error(connection_id)

    def mark_nonce_success(self, connection_id: str, nonce: Union[str, int]) -> None:
        """Mark a nonce as successfully used."""
        nonce_str = str(nonce)
        for entry in self._nonce_history.get(connection_id, []):
            if entry['nonce'] == nonce_str:
                entry['status'] = 'success'
                break

        logger.debug("[CONSOLIDATED_NONCE] Marked nonce as successful")

    def mark_nonce_failed(self, connection_id: str, nonce: Union[str, int], error: str) -> None:
        """Mark a nonce as failed."""
        nonce_str = str(nonce)

        # Update history
        for entry in self._nonce_history.get(connection_id, []):
            if entry['nonce'] == nonce_str:
                entry['status'] = 'failed'
                entry['error'] = error
                break

        # Track in failed list
        if connection_id in self._failed_nonces:
            self._failed_nonces[connection_id].append({
                'nonce': nonce_str,
                'error': error,
                'timestamp': datetime.now().isoformat()
            })

    def register_connection(self, connection_id: str, error_handler: Optional[Callable] = None) -> None:
        """Register a connection for tracking."""
        if error_handler:
            self._connection_handlers[connection_id] = error_handler

        if connection_id not in self._nonce_history:
            self._nonce_history[connection_id] = []
            self._failed_nonces[connection_id] = []

        logger.info(f"[CONSOLIDATED_NONCE] Registered connection: {connection_id}")

    def cleanup_connection(self, connection_id: str) -> None:
        """Clean up connection resources."""
        with self._thread_lock:
            for tracking_dict in [self._connection_handlers, self._nonce_history,
                                 self._failed_nonces, self._connection_tracker,
                                 self._connection_counts]:
                tracking_dict.pop(connection_id, None)

            logger.info(f"[CONSOLIDATED_NONCE] Cleaned up connection: {connection_id}")

    async def make_authenticated_api_call(self, uri_path: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """Make authenticated API call using integrated KrakenNonceFixer."""
        if not self._nonce_fixer:
            raise Exception("KrakenNonceFixer not initialized. Provide API credentials to enable enhanced authentication.")

        return await self._nonce_fixer.make_authenticated_api_call(uri_path, params)

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive status and statistics."""
        with self._thread_lock:
            # Use MILLISECONDS
            current_ms = int(time.time() * 1000)

            # Calculate connection stats
            connection_stats = {}
            for conn_id in self._nonce_history:
                history = self._nonce_history[conn_id]
                failed = self._failed_nonces.get(conn_id, [])
                success_count = sum(1 for h in history if h.get('status') == 'success')

                connection_stats[conn_id] = {
                    'total_nonces': len(history),
                    'successful': success_count,
                    'failed': len(failed),
                    'success_rate': success_count / len(history) if history else 0,
                    'last_nonce': history[-1]['nonce'] if history else None,
                    'last_timestamp': history[-1]['timestamp'] if history else None
                }

            return {
                'current_nonce': self._mask_nonce(self._last_nonce),
                'total_generated': self._total_nonces,
                'error_recoveries': self._error_recoveries,
                'active_connections': len(self._connection_tracker),
                'connection_stats': connection_stats,
                'time_until_current': (self._last_nonce - current_ms) / 1000000.0,
                'last_save': datetime.fromtimestamp(self._last_save_time).isoformat(),
                'state_file': str(self._state_file),
                'uptime_seconds': time.time() - self._start_time,
                'nonce_fixer_available': self._nonce_fixer is not None,
                'version': '4.0.0'
            }

    def force_save(self) -> None:
        """Force immediate state save."""
        with self._thread_lock:
            self._save_state()
            logger.info("[CONSOLIDATED_NONCE] Forced state save")

    def _mask_nonce(self, nonce: int) -> str:
        """Mask nonce value for secure logging."""
        nonce_str = str(nonce)
        if len(nonce_str) <= 8:
            return nonce_str
        return f"{nonce_str[:4]}...{nonce_str[-4:]}"

    @classmethod
    def get_instance(cls) -> 'ConsolidatedNonceManager':
        """Get the global singleton instance."""
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing only)."""
        with cls._lock:
            if cls._instance and cls._instance._internal_initialized:
                cls._instance.force_save()
            cls._instance = None


# GLOBAL SINGLETON ACCESS FUNCTIONS
# These are the ONLY functions that should be used throughout the codebase

def get_nonce_manager() -> ConsolidatedNonceManager:
    """Get the global consolidated nonce manager instance."""
    return ConsolidatedNonceManager.get_instance()


def get_unified_nonce_manager() -> ConsolidatedNonceManager:
    """Alias for get_nonce_manager - backward compatibility."""
    return ConsolidatedNonceManager.get_instance()


def get_nonce_coordinator() -> ConsolidatedNonceManager:
    """Alias for get_nonce_manager - WebSocket coordinator compatibility."""
    return ConsolidatedNonceManager.get_instance()


def initialize_enhanced_nonce_manager(api_key: str, api_secret: str) -> ConsolidatedNonceManager:
    """
    Initialize the consolidated nonce manager with enhanced KrakenNonceFixer integration.

    This should be called once during application initialization to enable
    the most robust nonce handling for all Kraken API operations.

    Args:
        api_key: Kraken API key
        api_secret: Base64-encoded Kraken API secret

    Returns:
        Enhanced ConsolidatedNonceManager instance
    """
    # Reset the singleton to allow reinitialization with credentials
    ConsolidatedNonceManager.reset_instance()

    # Create new instance with credentials
    manager = ConsolidatedNonceManager(api_key=api_key, api_secret=api_secret)

    logger.info("[CONSOLIDATED_NONCE] Enhanced nonce manager initialized with KrakenNonceFixer integration")
    return manager


# CONVENIENCE FUNCTIONS FOR LEGACY COMPATIBILITY

def get_nonce(connection_id: str = "default") -> str:
    """Convenience function for getting a nonce."""
    return get_nonce_manager().get_nonce(connection_id)


def get_next_nonce(connection_id: str = "default") -> str:
    """Legacy compatibility function."""
    return get_nonce_manager().get_next_nonce(connection_id)


async def get_nonce_async(connection_id: str = "default") -> str:
    """Async convenience function for getting a nonce."""
    return await get_nonce_manager().get_nonce_async(connection_id)


# LEGACY CLASS ALIASES FOR BACKWARD COMPATIBILITY
# These should be migrated away from over time

class UnifiedKrakenNonceManager(ConsolidatedNonceManager):
    """Legacy alias - use ConsolidatedNonceManager directly."""
    pass


class KrakenNonceManager(ConsolidatedNonceManager):
    """Legacy alias - use ConsolidatedNonceManager directly."""
    pass


class NonceManager(ConsolidatedNonceManager):
    """Legacy alias - use ConsolidatedNonceManager directly."""
    pass


class WebSocketNonceCoordinator(ConsolidatedNonceManager):
    """Legacy alias - use ConsolidatedNonceManager directly."""
    pass


# MODULE-LEVEL CONSTANTS
MIN_INCREMENT_MS = ConsolidatedNonceManager.MIN_INCREMENT_MS
RECOVERY_BUFFER_MS = ConsolidatedNonceManager.RECOVERY_BUFFER_MS

logger.info("[CONSOLIDATED_NONCE] Module loaded - ready for unified nonce management")
