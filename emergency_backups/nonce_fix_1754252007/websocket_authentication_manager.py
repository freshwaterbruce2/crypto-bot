"""
Enhanced WebSocket Authentication Manager for Kraken Trading Bot
==============================================================

Comprehensive authentication solution for WebSocket V2 connections that solves:
- "EAPI:Invalid nonce" errors causing connection failures
- Token expiry handling with proactive refresh
- Authentication state management and recovery
- Circuit breaker integration for auth failures
- Thread-safe token lifecycle management

Features:
- Proactive token refresh every 13 minutes (before 15-minute expiry)
- Exponential backoff for failed authentication requests
- Circuit breaker pattern for authentication failures
- Secure token storage and validation
- Integration with existing REST API authentication
- Comprehensive error handling and recovery mechanisms
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import threading
from pathlib import Path
import hashlib
import base64

from .kraken_auth import KrakenAuth, KrakenAuthError
from ..utils.unified_kraken_nonce_manager import UnifiedKrakenNonceManager

logger = logging.getLogger(__name__)


@dataclass
class WebSocketToken:
    """WebSocket authentication token data structure"""
    token: str
    expires_at: float
    created_at: float
    is_valid: bool = True
    refresh_count: int = 0
    

@dataclass
class AuthenticationStats:
    """Authentication statistics tracking"""
    tokens_generated: int = 0
    tokens_refreshed: int = 0
    auth_failures: int = 0
    nonce_errors: int = 0
    successful_auths: int = 0
    circuit_breaker_trips: int = 0
    avg_token_request_time_ms: float = 0.0
    last_successful_auth: float = 0.0


class WebSocketAuthenticationError(Exception):
    """Base exception for WebSocket authentication errors"""
    pass


class TokenExpiredError(WebSocketAuthenticationError):
    """Token has expired and needs refresh"""
    pass


class NonceValidationError(WebSocketAuthenticationError):
    """Nonce validation failed"""
    pass


class CircuitBreakerOpenError(WebSocketAuthenticationError):
    """Authentication circuit breaker is open"""
    pass


class WebSocketAuthenticationManager:
    """
    Enhanced WebSocket authentication manager with proactive token management.
    
    Provides comprehensive authentication for Kraken WebSocket V2 connections
    with automatic token refresh, error recovery, and circuit breaker protection.
    """
    
    def __init__(
        self,
        exchange_client: Any,
        api_key: str,
        private_key: str,
        storage_dir: Optional[str] = None,
        enable_debug: bool = False
    ):
        """
        Initialize WebSocket authentication manager.
        
        Args:
            exchange_client: Kraken exchange client instance
            api_key: Kraken API key
            private_key: Base64-encoded Kraken private key
            storage_dir: Directory for token state storage
            enable_debug: Enable detailed debug logging
        """
        self.exchange_client = exchange_client
        self.api_key = api_key
        self.private_key = private_key
        self.enable_debug = enable_debug
        
        # Initialize REST authentication for token requests
        self.rest_auth = KrakenAuth(api_key, private_key, storage_dir, enable_debug)
        
        # Token management
        self._current_token: Optional[WebSocketToken] = None
        self._token_lock = asyncio.Lock()
        self._refresh_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Configuration
        self.token_lifetime_seconds = 15 * 60  # 15 minutes
        self.refresh_interval_seconds = 13 * 60  # 13 minutes (2 min buffer)
        self.max_retry_attempts = 3
        self.base_retry_delay = 1.0
        self.max_retry_delay = 30.0
        
        # Circuit breaker configuration
        self.circuit_breaker_threshold = 5  # failures
        self.circuit_breaker_timeout = 300  # 5 minutes
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = 0.0
        self._circuit_breaker_open = False
        
        # Statistics
        self.stats = AuthenticationStats()
        self._request_times = []
        self._max_time_samples = 50
        
        # Storage for token persistence
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        self.token_file = self.storage_dir / f"websocket_token_{api_key_hash}.json"
        
        # Event callbacks
        self._token_refresh_callback: Optional[Callable] = None
        self._auth_failure_callback: Optional[Callable] = None
        
        logger.info(f"[WS_AUTH] Initialized WebSocket authentication manager for API key: {api_key[:8]}...")
        
        if enable_debug:
            self._run_initialization_test()
    
    def _run_initialization_test(self) -> None:
        """Run initialization test to verify authentication components"""
        try:
            logger.info("[WS_AUTH] Running initialization test...")
            
            # Test REST authentication
            test_result = self.rest_auth.run_comprehensive_test()
            if not test_result.get('overall_success', False):
                logger.warning(f"[WS_AUTH] REST auth test issues: {test_result}")
            
            # Test nonce manager access
            nonce_manager = UnifiedKrakenNonceManager.get_instance()
            test_nonce = nonce_manager.get_nonce("websocket_auth_test")
            logger.debug(f"[WS_AUTH] Test nonce generated: {test_nonce}")
            
            logger.info("[WS_AUTH] Initialization test completed successfully")
            
        except Exception as e:
            logger.error(f"[WS_AUTH] Initialization test failed: {e}")
    
    async def start(self) -> bool:
        """
        Start the WebSocket authentication manager.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info("[WS_AUTH] Starting WebSocket authentication manager...")
            
            # Load any existing token state
            await self._load_token_state()
            
            # Generate initial token if needed
            token = await self.get_websocket_token()
            if not token:
                logger.error("[WS_AUTH] Failed to generate initial WebSocket token")
                return False
            
            # Start proactive refresh task
            self._is_running = True
            self._refresh_task = asyncio.create_task(self._token_refresh_loop())
            
            logger.info("[WS_AUTH] WebSocket authentication manager started successfully")
            return True
            
        except Exception as e:
            logger.error(f"[WS_AUTH] Failed to start authentication manager: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the WebSocket authentication manager"""
        try:
            logger.info("[WS_AUTH] Stopping WebSocket authentication manager...")
            
            self._is_running = False
            
            # Cancel refresh task
            if self._refresh_task and not self._refresh_task.done():
                self._refresh_task.cancel()
                try:
                    await self._refresh_task
                except asyncio.CancelledError:
                    pass
            
            # Save final token state
            await self._save_token_state()
            
            logger.info("[WS_AUTH] WebSocket authentication manager stopped")
            
        except Exception as e:
            logger.error(f"[WS_AUTH] Error stopping authentication manager: {e}")
    
    async def get_websocket_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Get current WebSocket authentication token.
        
        Args:
            force_refresh: Force token refresh even if current token is valid
            
        Returns:
            WebSocket token string or None if failed
        """
        async with self._token_lock:
            try:
                # Check if we need to refresh
                if force_refresh or not self._is_token_valid():
                    success = await self._refresh_token_internal()
                    if not success:
                        logger.error("[WS_AUTH] Failed to get valid WebSocket token")
                        return None
                
                if self._current_token and self._current_token.is_valid:
                    return self._current_token.token
                
                return None
                
            except Exception as e:
                logger.error(f"[WS_AUTH] Error getting WebSocket token: {e}")
                return None
    
    async def refresh_token_proactively(self) -> bool:
        """
        Proactively refresh the WebSocket token before expiry.
        
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            logger.info("[WS_AUTH] Proactive token refresh initiated...")
            
            async with self._token_lock:
                success = await self._refresh_token_internal()
                
                if success:
                    logger.info("[WS_AUTH] Proactive token refresh completed successfully")
                    self.stats.tokens_refreshed += 1
                    
                    # Trigger callback if registered
                    if self._token_refresh_callback:
                        try:
                            await self._token_refresh_callback(self._current_token.token)
                        except Exception as cb_error:
                            logger.warning(f"[WS_AUTH] Token refresh callback failed: {cb_error}")
                else:
                    logger.error("[WS_AUTH] Proactive token refresh failed")
                
                return success
                
        except Exception as e:
            logger.error(f"[WS_AUTH] Error in proactive token refresh: {e}")
            return False
    
    async def handle_token_expiry(self) -> Optional[str]:
        """
        Handle token expiry with immediate refresh.
        
        Returns:
            New token string or None if failed
        """
        logger.warning("[WS_AUTH] Handling token expiry - immediate refresh required")
        
        try:
            # Force refresh with exponential backoff
            for attempt in range(self.max_retry_attempts):
                token = await self.get_websocket_token(force_refresh=True)
                if token:
                    logger.info(f"[WS_AUTH] Token expiry handled successfully on attempt {attempt + 1}")
                    return token
                
                # Exponential backoff
                delay = min(self.base_retry_delay * (2 ** attempt), self.max_retry_delay)
                logger.warning(f"[WS_AUTH] Token refresh attempt {attempt + 1} failed, retrying in {delay}s")
                await asyncio.sleep(delay)
            
            logger.error("[WS_AUTH] Failed to handle token expiry after all retry attempts")
            return None
            
        except Exception as e:
            logger.error(f"[WS_AUTH] Error handling token expiry: {e}")
            return None
    
    async def validate_token(self, token: str) -> bool:
        """
        Validate if a WebSocket token is still valid.
        
        Args:
            token: Token string to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            if not token:
                return False
            
            # Check against current token
            if self._current_token and self._current_token.token == token:
                return self._is_token_valid()
            
            # For external tokens, we can't validate without making a request
            # This is a basic validation - in practice, a WebSocket connection test would be better
            return len(token) > 10  # Basic length check
            
        except Exception as e:
            logger.error(f"[WS_AUTH] Error validating token: {e}")
            return False
    
    async def handle_authentication_error(self, error_message: str) -> Optional[str]:
        """
        Handle WebSocket authentication error with recovery.
        
        Args:
            error_message: Error message from WebSocket connection
            
        Returns:
            New authentication token or None if recovery failed
        """
        logger.warning(f"[WS_AUTH] Handling authentication error: {error_message}")
        
        try:
            self.stats.auth_failures += 1
            
            # Check if circuit breaker should trip
            if self._should_trip_circuit_breaker():
                self._trip_circuit_breaker()
                raise CircuitBreakerOpenError("Authentication circuit breaker is open")
            
            # Handle specific error types
            if "nonce" in error_message.lower():
                return await self._handle_nonce_error(error_message)
            elif "token" in error_message.lower() or "expired" in error_message.lower():
                return await self._handle_token_error(error_message)
            elif "invalid" in error_message.lower():
                return await self._handle_invalid_auth_error(error_message)
            else:
                return await self._handle_generic_auth_error(error_message)
                
        except Exception as e:
            logger.error(f"[WS_AUTH] Error handling authentication error: {e}")
            
            # Trigger failure callback
            if self._auth_failure_callback:
                try:
                    await self._auth_failure_callback(error_message, str(e))
                except Exception as cb_error:
                    logger.warning(f"[WS_AUTH] Auth failure callback failed: {cb_error}")
            
            return None
    
    async def _handle_nonce_error(self, error_message: str) -> Optional[str]:
        """Handle nonce-related authentication errors"""
        logger.warning("[WS_AUTH] Handling nonce error - resetting nonce manager")
        
        self.stats.nonce_errors += 1
        
        try:
            # Get nonce manager and force reset
            nonce_manager = UnifiedKrakenNonceManager.get_instance()
            nonce_manager.handle_invalid_nonce_error("websocket_auth")
            
            # Force token refresh with new nonce
            return await self.get_websocket_token(force_refresh=True)
            
        except Exception as e:
            logger.error(f"[WS_AUTH] Nonce error recovery failed: {e}")
            return None
    
    async def _handle_token_error(self, error_message: str) -> Optional[str]:
        """Handle token-related authentication errors"""
        logger.warning("[WS_AUTH] Handling token error - forcing token refresh")
        
        try:
            # Mark current token as invalid
            if self._current_token:
                self._current_token.is_valid = False
            
            # Force refresh
            return await self.get_websocket_token(force_refresh=True)
            
        except Exception as e:
            logger.error(f"[WS_AUTH] Token error recovery failed: {e}")
            return None
    
    async def _handle_invalid_auth_error(self, error_message: str) -> Optional[str]:
        """Handle invalid authentication errors"""
        logger.warning("[WS_AUTH] Handling invalid auth error - comprehensive recovery")
        
        try:
            # Reset both nonce and token
            nonce_manager = UnifiedKrakenNonceManager.get_instance()
            nonce_manager.handle_invalid_nonce_error("websocket_auth")
            
            if self._current_token:
                self._current_token.is_valid = False
            
            # Wait a bit before retry
            await asyncio.sleep(1.0)
            
            return await self.get_websocket_token(force_refresh=True)
            
        except Exception as e:
            logger.error(f"[WS_AUTH] Invalid auth error recovery failed: {e}")
            return None
    
    async def _handle_generic_auth_error(self, error_message: str) -> Optional[str]:
        """Handle generic authentication errors"""
        logger.warning(f"[WS_AUTH] Handling generic auth error: {error_message}")
        
        try:
            # Basic recovery - just force refresh
            await asyncio.sleep(2.0)  # Brief delay
            return await self.get_websocket_token(force_refresh=True)
            
        except Exception as e:
            logger.error(f"[WS_AUTH] Generic auth error recovery failed: {e}")
            return None
    
    async def _refresh_token_internal(self) -> bool:
        """Internal token refresh implementation"""
        start_time = time.time()
        
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open():
                raise CircuitBreakerOpenError("Authentication circuit breaker is open")
            
            logger.info("[WS_AUTH] Requesting new WebSocket token from Kraken API...")
            
            # Make REST API request for WebSocket token
            token_response = await self._request_websocket_token()
            
            if token_response and 'token' in token_response:
                # Create new token object
                current_time = time.time()
                new_token = WebSocketToken(
                    token=token_response['token'],
                    expires_at=current_time + self.token_lifetime_seconds,
                    created_at=current_time,
                    is_valid=True,
                    refresh_count=self._current_token.refresh_count + 1 if self._current_token else 0
                )
                
                # Update current token
                old_token = self._current_token
                self._current_token = new_token
                
                # Update statistics
                request_time_ms = (time.time() - start_time) * 1000
                self._update_request_statistics(True, request_time_ms)
                self.stats.tokens_generated += 1
                self.stats.successful_auths += 1
                self.stats.last_successful_auth = time.time()
                
                # Reset circuit breaker on success
                self._reset_circuit_breaker()
                
                # Save token state
                await self._save_token_state()
                
                logger.info(f"[WS_AUTH] WebSocket token refreshed successfully "
                           f"(expires in {self.token_lifetime_seconds}s, "
                           f"request took {request_time_ms:.1f}ms)")
                
                if self.enable_debug and old_token:
                    logger.debug(f"[WS_AUTH] Old token: {old_token.token[:20]}... "
                                f"New token: {new_token.token[:20]}...")
                
                return True
            else:
                logger.error(f"[WS_AUTH] Invalid token response: {token_response}")
                self._record_circuit_breaker_failure()
                return False
                
        except Exception as e:
            request_time_ms = (time.time() - start_time) * 1000
            self._update_request_statistics(False, request_time_ms)
            self._record_circuit_breaker_failure()
            
            logger.error(f"[WS_AUTH] Token refresh failed after {request_time_ms:.1f}ms: {e}")
            return False
    
    async def _request_websocket_token(self) -> Optional[Dict[str, Any]]:
        """Make REST API request for WebSocket token"""
        try:
            # Use REST authentication to get WebSocket token
            uri_path = '/0/private/GetWebSocketsToken'
            
            # Get auth headers
            auth_headers = await self.rest_auth.get_auth_headers_async(uri_path)
            
            # Make request through exchange client
            if hasattr(self.exchange_client, 'make_authenticated_request'):
                response = await self.exchange_client.make_authenticated_request(
                    uri_path, {}, auth_headers
                )
            elif hasattr(self.exchange_client, '_make_request'):
                response = await self.exchange_client._make_request(
                    'POST', uri_path, headers=auth_headers
                )
            else:
                # Fallback - construct direct request
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.kraken.com{uri_path}"
                    async with session.post(url, headers=auth_headers) as resp:
                        response = await resp.json()
            
            # Parse response
            if isinstance(response, dict):
                if 'result' in response and 'token' in response['result']:
                    return {'token': response['result']['token']}
                elif 'token' in response:
                    return {'token': response['token']}
                else:
                    logger.error(f"[WS_AUTH] Unexpected token response format: {response}")
                    return None
            else:
                logger.error(f"[WS_AUTH] Invalid response type: {type(response)}")
                return None
                
        except Exception as e:
            logger.error(f"[WS_AUTH] WebSocket token request failed: {e}")
            return None
    
    def _is_token_valid(self) -> bool:
        """Check if current token is valid and not expired"""
        if not self._current_token or not self._current_token.is_valid:
            return False
        
        current_time = time.time()
        time_until_expiry = self._current_token.expires_at - current_time
        
        # Consider token invalid if it expires in less than 2 minutes
        return time_until_expiry > 120
    
    def _should_refresh_token(self) -> bool:
        """Check if token should be proactively refreshed"""
        if not self._current_token or not self._current_token.is_valid:
            return True
        
        current_time = time.time()
        time_until_expiry = self._current_token.expires_at - current_time
        
        # Refresh if less than refresh interval remaining
        return time_until_expiry <= (self.token_lifetime_seconds - self.refresh_interval_seconds)
    
    async def _token_refresh_loop(self) -> None:
        """Background task for proactive token refresh"""
        logger.info("[WS_AUTH] Starting proactive token refresh loop...")
        
        while self._is_running:
            try:
                # Check if refresh is needed
                if self._should_refresh_token():
                    logger.info("[WS_AUTH] Proactive token refresh triggered")
                    await self.refresh_token_proactively()
                
                # Sleep for a minute before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("[WS_AUTH] Token refresh loop cancelled")
                break
            except Exception as e:
                logger.error(f"[WS_AUTH] Error in token refresh loop: {e}")
                await asyncio.sleep(60)  # Continue after error
        
        logger.info("[WS_AUTH] Token refresh loop stopped")
    
    # Circuit Breaker Methods
    def _should_trip_circuit_breaker(self) -> bool:
        """Check if circuit breaker should trip"""
        return self._circuit_breaker_failures >= self.circuit_breaker_threshold
    
    def _trip_circuit_breaker(self) -> None:
        """Trip the circuit breaker"""
        self._circuit_breaker_open = True
        self._circuit_breaker_last_failure = time.time()
        self.stats.circuit_breaker_trips += 1
        logger.error(f"[WS_AUTH] Circuit breaker TRIPPED after {self._circuit_breaker_failures} failures")
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is currently open"""
        if not self._circuit_breaker_open:
            return False
        
        # Check if timeout has passed
        if time.time() - self._circuit_breaker_last_failure > self.circuit_breaker_timeout:
            logger.info("[WS_AUTH] Circuit breaker timeout expired - resetting to half-open")
            self._circuit_breaker_open = False
            self._circuit_breaker_failures = 0
            return False
        
        return True
    
    def _record_circuit_breaker_failure(self) -> None:
        """Record a failure for circuit breaker tracking"""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = time.time()
    
    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after successful operation"""
        if self._circuit_breaker_failures > 0:
            logger.info(f"[WS_AUTH] Circuit breaker reset after successful operation "
                       f"({self._circuit_breaker_failures} previous failures)")
            self._circuit_breaker_failures = 0
            self._circuit_breaker_open = False
    
    def _update_request_statistics(self, success: bool, request_time_ms: float) -> None:
        """Update request timing statistics"""
        self._request_times.append(request_time_ms)
        if len(self._request_times) > self._max_time_samples:
            self._request_times.pop(0)
        
        if self._request_times:
            self.stats.avg_token_request_time_ms = sum(self._request_times) / len(self._request_times)
    
    # Token State Persistence
    async def _save_token_state(self) -> None:
        """Save current token state to persistent storage"""
        try:
            if not self._current_token:
                return
            
            token_data = {
                'token': self._current_token.token,
                'expires_at': self._current_token.expires_at,
                'created_at': self._current_token.created_at,
                'is_valid': self._current_token.is_valid,
                'refresh_count': self._current_token.refresh_count,
                'saved_at': time.time()
            }
            
            # Write to temporary file first, then atomic rename
            temp_file = self.token_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            temp_file.replace(self.token_file)
            
            if self.enable_debug:
                logger.debug(f"[WS_AUTH] Token state saved to {self.token_file}")
                
        except Exception as e:
            logger.error(f"[WS_AUTH] Failed to save token state: {e}")
    
    async def _load_token_state(self) -> None:
        """Load token state from persistent storage"""
        try:
            if not self.token_file.exists():
                logger.debug("[WS_AUTH] No existing token state file found")
                return
            
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            # Validate loaded data
            required_fields = ['token', 'expires_at', 'created_at']
            if not all(field in token_data for field in required_fields):
                logger.warning("[WS_AUTH] Invalid token state data, ignoring")
                return
            
            # Check if token is still valid
            current_time = time.time()
            expires_at = token_data['expires_at']
            
            if expires_at > current_time + 120:  # At least 2 minutes remaining
                self._current_token = WebSocketToken(
                    token=token_data['token'],
                    expires_at=expires_at,
                    created_at=token_data['created_at'],
                    is_valid=token_data.get('is_valid', True),
                    refresh_count=token_data.get('refresh_count', 0)
                )
                
                logger.info(f"[WS_AUTH] Loaded valid token state "
                           f"(expires in {expires_at - current_time:.0f}s)")
            else:
                logger.info("[WS_AUTH] Loaded token state is expired, will refresh")
                
        except Exception as e:
            logger.error(f"[WS_AUTH] Failed to load token state: {e}")
    
    # Public Interface Methods
    def set_token_refresh_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback function for token refresh events"""
        self._token_refresh_callback = callback
        logger.info("[WS_AUTH] Token refresh callback registered")
    
    def set_auth_failure_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback function for authentication failures"""
        self._auth_failure_callback = callback
        logger.info("[WS_AUTH] Authentication failure callback registered")
    
    def get_authentication_status(self) -> Dict[str, Any]:
        """Get comprehensive authentication status"""
        current_time = time.time()
        
        status = {
            'is_running': self._is_running,
            'has_valid_token': self._is_token_valid(),
            'circuit_breaker_open': self._is_circuit_breaker_open(),
            'circuit_breaker_failures': self._circuit_breaker_failures,
            'current_time': current_time,
            'statistics': asdict(self.stats)
        }
        
        if self._current_token:
            status.update({
                'token_expires_at': self._current_token.expires_at,
                'token_expires_in_seconds': max(0, self._current_token.expires_at - current_time),
                'token_age_seconds': current_time - self._current_token.created_at,
                'token_refresh_count': self._current_token.refresh_count,
                'needs_refresh': self._should_refresh_token()
            })
        else:
            status.update({
                'token_expires_at': None,
                'token_expires_in_seconds': 0,
                'token_age_seconds': 0,
                'token_refresh_count': 0,
                'needs_refresh': True
            })
        
        return status
    
    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """Get current token information (without exposing token value)"""
        if not self._current_token:
            return None
        
        current_time = time.time()
        return {
            'token_length': len(self._current_token.token),
            'token_prefix': self._current_token.token[:8] + '...',
            'expires_at': self._current_token.expires_at,
            'expires_in_seconds': max(0, self._current_token.expires_at - current_time),
            'created_at': self._current_token.created_at,
            'age_seconds': current_time - self._current_token.created_at,
            'is_valid': self._current_token.is_valid,
            'refresh_count': self._current_token.refresh_count,
            'needs_refresh': self._should_refresh_token()
        }
    
    async def force_token_refresh(self) -> bool:
        """Force immediate token refresh (for testing/debugging)"""
        logger.info("[WS_AUTH] Force token refresh requested")
        return await self.refresh_token_proactively()
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker (for recovery)"""
        logger.info("[WS_AUTH] Manual circuit breaker reset")
        self._reset_circuit_breaker()
    
    # Context Manager Support
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
    
    def __str__(self) -> str:
        """String representation"""
        status = "valid" if self._is_token_valid() else "invalid"
        return f"WebSocketAuthenticationManager(token={status}, failures={self._circuit_breaker_failures})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return self.__str__()


# Utility functions for integration
async def create_websocket_auth_manager(
    exchange_client: Any,
    api_key: str,
    private_key: str,
    **kwargs
) -> WebSocketAuthenticationManager:
    """
    Factory function to create and start WebSocket authentication manager.
    
    Args:
        exchange_client: Kraken exchange client
        api_key: API key
        private_key: Private key
        **kwargs: Additional configuration options
        
    Returns:
        Started WebSocketAuthenticationManager instance
    """
    manager = WebSocketAuthenticationManager(
        exchange_client=exchange_client,
        api_key=api_key,
        private_key=private_key,
        **kwargs
    )
    
    success = await manager.start()
    if not success:
        raise WebSocketAuthenticationError("Failed to start WebSocket authentication manager")
    
    return manager


@asynccontextmanager
async def websocket_auth_context(
    exchange_client: Any,
    api_key: str,
    private_key: str,
    **kwargs
):
    """
    Async context manager for WebSocket authentication.
    
    Usage:
        async with websocket_auth_context(exchange, api_key, private_key) as auth_manager:
            token = await auth_manager.get_websocket_token()
            # Use token for WebSocket connection
    """
    manager = None
    try:
        manager = await create_websocket_auth_manager(
            exchange_client, api_key, private_key, **kwargs
        )
        yield manager
    finally:
        if manager:
            await manager.stop()