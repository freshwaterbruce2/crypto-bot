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
import hashlib
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from ..utils.consolidated_nonce_manager import ConsolidatedNonceManager
from .kraken_auth import KrakenAuth

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
        api_key: str = None,
        private_key: str = None,
        credential_manager: Any = None,
        storage_dir: Optional[str] = None,
        enable_debug: bool = False
    ):
        """
        Initialize WebSocket authentication manager.

        Args:
            exchange_client: Kraken exchange client instance
            api_key: Kraken REST API key (for GetWebSocketsToken requests)
            private_key: Base64-encoded Kraken REST private key
            credential_manager: CredentialManager instance for automatic credential retrieval
            storage_dir: Directory for token state storage
            enable_debug: Enable detailed debug logging
        """
        self.exchange_client = exchange_client
        self.credential_manager = credential_manager
        self.enable_debug = enable_debug

        # Get API credentials (used for GetWebSocketsToken endpoint)
        # The unified approach means both REST and WebSocket use the same credentials
        if api_key and private_key:
            self.api_key = api_key
            self.private_key = private_key
            logger.info("[WS_AUTH] Using provided API credentials for WebSocket token requests")
        elif credential_manager:
            # Use the unified credential approach - get_kraken_rest_credentials now checks KRAKEN_KEY/KRAKEN_SECRET first
            rest_api_key, rest_private_key = credential_manager.get_kraken_rest_credentials()
            if rest_api_key and rest_private_key:
                self.api_key = rest_api_key
                self.private_key = rest_private_key
                logger.info("[WS_AUTH] Using API credentials from credential manager for WebSocket token requests")
            else:
                raise ValueError("No valid API credentials found - required for GetWebSocketsToken requests")
        else:
            # Fallback to environment variables - now checks unified credentials first
            from .credential_manager import get_kraken_rest_credentials
            rest_api_key, rest_private_key = get_kraken_rest_credentials()
            if rest_api_key and rest_private_key:
                self.api_key = rest_api_key
                self.private_key = rest_private_key
                logger.info("[WS_AUTH] Using API credentials from environment for WebSocket token requests")
            else:
                raise ValueError("No valid API credentials found in environment - required for GetWebSocketsToken requests")

        # Initialize REST authentication for token requests (uses REST credentials)
        self.rest_auth = KrakenAuth(self.api_key, self.private_key, storage_dir, enable_debug)

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

        # August 2025 API enhancements
        self.api_tier: Optional[str] = None  # Detected API tier (Starter/Intermediate/Pro)
        self.rate_limit_info: dict[str, Any] = {}  # Rate limit tier information
        self.derivatives_support: bool = False  # October 2025 derivatives readiness

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

        # Initialize API tier detection
        asyncio.create_task(self._detect_api_tier())

    def _run_initialization_test(self) -> None:
        """Run initialization test to verify authentication components"""
        try:
            logger.info("[WS_AUTH] Running initialization test...")

            # Test REST authentication
            test_result = self.rest_auth.run_comprehensive_test()
            if not test_result.get('overall_success', False):
                logger.warning(f"[WS_AUTH] REST auth test issues: {test_result}")

            # Test nonce manager access
            nonce_manager = ConsolidatedNonceManager.get_instance()
            test_nonce = nonce_manager.get_nonce("websocket_auth_test")
            logger.debug(f"[WS_AUTH] Test nonce generated: {test_nonce}")

            logger.info("[WS_AUTH] Initialization test completed successfully")

        except Exception as e:
            logger.error(f"[WS_AUTH] Initialization test failed: {e}")

    async def _detect_api_tier(self) -> None:
        """Detect API tier for optimized rate limiting (August 2025 enhancement)"""
        try:
            logger.info("[WS_AUTH] Detecting API tier for optimized rate limiting...")

            # Make a minimal API call to detect tier from response headers
            import aiohttp
            uri_path = '/0/public/SystemStatus'  # Public endpoint, no authentication needed

            async with aiohttp.ClientSession() as session:
                url = f"https://api.kraken.com{uri_path}"
                async with session.get(url) as response:
                    headers = response.headers

                    # Check for rate limit headers (August 2025 spec)
                    if 'API-Rate-Limit-Tier' in headers:
                        self.api_tier = headers['API-Rate-Limit-Tier']
                        logger.info(f"[WS_AUTH] API tier detected: {self.api_tier}")

                        # Set tier-specific rate limits
                        self._configure_rate_limits_for_tier(self.api_tier)
                    else:
                        # Fallback detection based on common patterns
                        self.api_tier = "Pro"  # Default assumption for trading bots
                        logger.info("[WS_AUTH] API tier not in headers, assuming Pro tier")
                        self._configure_rate_limits_for_tier("Pro")

                    # Check for derivatives support (October 2025 readiness)
                    if 'API-Derivatives-Support' in headers:
                        self.derivatives_support = headers['API-Derivatives-Support'].lower() == 'true'
                        logger.info(f"[WS_AUTH] Derivatives support: {self.derivatives_support}")

        except Exception as e:
            logger.warning(f"[WS_AUTH] API tier detection failed: {e}, assuming Pro tier")
            self.api_tier = "Pro"
            self._configure_rate_limits_for_tier("Pro")

    def _configure_rate_limits_for_tier(self, tier: str) -> None:
        """Configure rate limits based on detected API tier"""
        tier_configs = {
            "Starter": {"calls_per_minute": 60, "burst_limit": 15, "websocket_tokens_per_hour": 10},
            "Intermediate": {"calls_per_minute": 120, "burst_limit": 20, "websocket_tokens_per_hour": 20},
            "Pro": {"calls_per_minute": 180, "burst_limit": 20, "websocket_tokens_per_hour": 40}
        }

        config = tier_configs.get(tier, tier_configs["Pro"])
        self.rate_limit_info = {
            'tier': tier,
            'calls_per_minute': config['calls_per_minute'],
            'burst_limit': config['burst_limit'],
            'websocket_tokens_per_hour': config['websocket_tokens_per_hour'],
            'recommended_token_refresh_interval': 13 * 60 if tier == "Pro" else 14 * 60  # More conservative for lower tiers
        }

        # Adjust token refresh interval based on tier
        if tier != "Pro":
            self.refresh_interval_seconds = self.rate_limit_info['recommended_token_refresh_interval']

        logger.info(f"[WS_AUTH] Rate limits configured for {tier} tier: {config}")

    def _parse_v2_error_message(self, error_message: str) -> dict[str, Any]:
        """Parse V2 error format for enhanced error handling (August 2025)"""
        try:
            # V2 error format: {"error": {"code": "EAPI:Invalid nonce", "message": "...", "details": {...}}}
            if isinstance(error_message, str) and error_message.startswith('{"error"'):
                import json
                error_data = json.loads(error_message)
                if 'error' in error_data and isinstance(error_data['error'], dict):
                    return {
                        'code': error_data['error'].get('code', 'UNKNOWN'),
                        'message': error_data['error'].get('message', error_message),
                        'details': error_data['error'].get('details', {}),
                        'is_v2_format': True
                    }

            # Legacy format handling
            return {
                'code': 'LEGACY_FORMAT',
                'message': str(error_message),
                'details': {},
                'is_v2_format': False
            }

        except Exception as e:
            logger.warning(f"[WS_AUTH] Error parsing V2 error format: {e}")
            return {
                'code': 'PARSE_ERROR',
                'message': str(error_message),
                'details': {'parse_error': str(e)},
                'is_v2_format': False
            }

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
        Handle WebSocket authentication error with V2 enhanced recovery.

        Args:
            error_message: Error message from WebSocket connection

        Returns:
            New authentication token or None if recovery failed
        """
        logger.warning(f"[WS_AUTH] Handling authentication error: {error_message}")

        try:
            self.stats.auth_failures += 1

            # Parse V2 error format for enhanced handling
            error_info = self._parse_v2_error_message(error_message)
            error_code = error_info['code']
            error_info['details']

            logger.info(f"[WS_AUTH] V2 Error analysis - Code: {error_code}, Format: {'V2' if error_info['is_v2_format'] else 'Legacy'}")

            # Check if circuit breaker should trip
            if self._should_trip_circuit_breaker():
                self._trip_circuit_breaker()
                raise CircuitBreakerOpenError("Authentication circuit breaker is open")

            # Enhanced V2 error type handling
            if "nonce" in error_code.lower() or "nonce" in error_message.lower():
                return await self._handle_nonce_error_v2(error_message, error_info)
            elif "token" in error_code.lower() or "expired" in error_code.lower() or "token" in error_message.lower():
                return await self._handle_token_error_v2(error_message, error_info)
            elif "invalid" in error_code.lower() or "permission" in error_code.lower():
                return await self._handle_invalid_auth_error_v2(error_message, error_info)
            elif "rate" in error_code.lower() or "limit" in error_code.lower():
                return await self._handle_rate_limit_error_v2(error_message, error_info)
            else:
                return await self._handle_generic_auth_error_v2(error_message, error_info)

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
            nonce_manager = ConsolidatedNonceManager.get_instance()
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
            nonce_manager = ConsolidatedNonceManager.get_instance()
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

    # August 2025 V2 Enhanced Error Handlers
    async def _handle_nonce_error_v2(self, error_message: str, error_info: dict[str, Any]) -> Optional[str]:
        """Handle V2 nonce-related authentication errors with enhanced recovery"""
        logger.warning(f"[WS_AUTH] V2 Nonce error recovery - Code: {error_info['code']}")

        self.stats.nonce_errors += 1

        try:
            # Extract nonce details from V2 error if available
            nonce_details = error_info['details'].get('nonce_info', {})
            if nonce_details:
                logger.info(f"[WS_AUTH] V2 Nonce details: {nonce_details}")

            # Get nonce manager and force reset
            nonce_manager = ConsolidatedNonceManager.get_instance()
            nonce_manager.handle_invalid_nonce_error("websocket_auth_v2")

            # More aggressive delay for V2 nonce errors
            await asyncio.sleep(3.0)

            # Force token refresh with new nonce
            return await self.get_websocket_token(force_refresh=True)

        except Exception as e:
            logger.error(f"[WS_AUTH] V2 Nonce error recovery failed: {e}")
            return None

    async def _handle_token_error_v2(self, error_message: str, error_info: dict[str, Any]) -> Optional[str]:
        """Handle V2 token-related authentication errors"""
        logger.warning(f"[WS_AUTH] V2 Token error recovery - Code: {error_info['code']}")

        try:
            # Extract token details from V2 error if available
            token_details = error_info['details'].get('token_info', {})
            if token_details:
                logger.info(f"[WS_AUTH] V2 Token details: {token_details}")

                # Check if token expiry time is provided
                if 'expires_at' in token_details:
                    logger.info(f"[WS_AUTH] Token expired at: {token_details['expires_at']}")

            # Mark current token as invalid
            if self._current_token:
                self._current_token.is_valid = False

            # Force refresh with tier-appropriate delay
            delay = 2.0 if self.api_tier == "Pro" else 4.0  # More conservative for lower tiers
            await asyncio.sleep(delay)

            return await self.get_websocket_token(force_refresh=True)

        except Exception as e:
            logger.error(f"[WS_AUTH] V2 Token error recovery failed: {e}")
            return None

    async def _handle_invalid_auth_error_v2(self, error_message: str, error_info: dict[str, Any]) -> Optional[str]:
        """Handle V2 invalid authentication errors"""
        logger.warning(f"[WS_AUTH] V2 Invalid auth error recovery - Code: {error_info['code']}")

        try:
            # Extract permission details from V2 error if available
            permission_details = error_info['details'].get('permissions', {})
            if permission_details:
                logger.error(f"[WS_AUTH] V2 Permission details: {permission_details}")
                required_permissions = permission_details.get('required', [])
                if required_permissions:
                    logger.error(f"[WS_AUTH] Required permissions: {required_permissions}")

            # Reset both nonce and token for comprehensive recovery
            nonce_manager = ConsolidatedNonceManager.get_instance()
            nonce_manager.handle_invalid_nonce_error("websocket_auth_invalid_v2")

            if self._current_token:
                self._current_token.is_valid = False

            # Wait longer for permission-related errors
            await asyncio.sleep(5.0)

            return await self.get_websocket_token(force_refresh=True)

        except Exception as e:
            logger.error(f"[WS_AUTH] V2 Invalid auth error recovery failed: {e}")
            return None

    async def _handle_rate_limit_error_v2(self, error_message: str, error_info: dict[str, Any]) -> Optional[str]:
        """Handle V2 rate limit errors (August 2025 enhancement)"""
        logger.warning(f"[WS_AUTH] V2 Rate limit error - Code: {error_info['code']}")

        try:
            # Extract rate limit details from V2 error
            rate_limit_details = error_info['details'].get('rate_limit', {})
            if rate_limit_details:
                reset_time = rate_limit_details.get('reset_time', 60)
                current_calls = rate_limit_details.get('current_calls', 0)
                limit = rate_limit_details.get('limit', 0)

                logger.warning(f"[WS_AUTH] Rate limit exceeded: {current_calls}/{limit}, reset in {reset_time}s")

                # Update rate limit info if more accurate data is available
                if 'tier' in rate_limit_details:
                    detected_tier = rate_limit_details['tier']
                    if detected_tier != self.api_tier:
                        logger.info(f"[WS_AUTH] Updating API tier from {self.api_tier} to {detected_tier}")
                        self.api_tier = detected_tier
                        self._configure_rate_limits_for_tier(detected_tier)

                # Wait for rate limit reset with tier-appropriate backoff
                wait_time = min(reset_time + 10, 300)  # Max 5 minutes
                logger.info(f"[WS_AUTH] Waiting {wait_time}s for rate limit reset...")
                await asyncio.sleep(wait_time)
            else:
                # Fallback delay based on tier
                delay = 60 if self.api_tier == "Pro" else 120
                logger.info(f"[WS_AUTH] Using tier-based delay: {delay}s")
                await asyncio.sleep(delay)

            return await self.get_websocket_token(force_refresh=True)

        except Exception as e:
            logger.error(f"[WS_AUTH] V2 Rate limit error recovery failed: {e}")
            return None

    async def _handle_generic_auth_error_v2(self, error_message: str, error_info: dict[str, Any]) -> Optional[str]:
        """Handle V2 generic authentication errors with enhanced context"""
        logger.warning(f"[WS_AUTH] V2 Generic auth error - Code: {error_info['code']}")

        try:
            # Log additional V2 context if available
            if error_info['details']:
                logger.info(f"[WS_AUTH] V2 Error details: {error_info['details']}")

            # Tier-appropriate delay
            delay = 2.0 if self.api_tier == "Pro" else 4.0
            await asyncio.sleep(delay)

            return await self.get_websocket_token(force_refresh=True)

        except Exception as e:
            logger.error(f"[WS_AUTH] V2 Generic auth error recovery failed: {e}")
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
            token_response = await self._request_websocket_token_enhanced()

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

    async def _request_websocket_token(self) -> Optional[dict[str, Any]]:
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

    async def _request_websocket_token_enhanced(self) -> Optional[dict[str, Any]]:
        """Enhanced WebSocket token request with comprehensive error handling"""
        max_retries = 5
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                logger.info(f"🔑 Enhanced WebSocket token request (attempt {attempt + 1}/{max_retries})")

                # Get fresh nonce with collision prevention
                nonce_manager = ConsolidatedNonceManager.get_instance()
                nonce = await nonce_manager.get_nonce_async("websocket_token_enhanced")

                # Add small delay to prevent nonce collisions
                await asyncio.sleep(0.1)

                # Create signature with debug info
                uri_path = '/0/private/GetWebSocketsToken'
                post_data = f"nonce={nonce}"

                # Generate signature
                import base64
                import hashlib
                import hmac

                sha256_hash = hashlib.sha256(post_data.encode('utf-8')).digest()
                message = uri_path.encode('utf-8') + sha256_hash
                secret = base64.b64decode(self.private_key)
                signature = base64.b64encode(hmac.new(secret, message, hashlib.sha512).digest()).decode('utf-8')

                # Prepare headers with User-Agent for better API compatibility
                headers = {
                    'API-Key': self.api_key,
                    'API-Sign': signature,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Kraken-Trading-Bot/2025.1'
                }

                # Make request with comprehensive error handling
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.kraken.com{uri_path}"
                    async with session.post(url, headers=headers, data=post_data, timeout=30) as resp:
                        result = await resp.json()

                        if resp.status == 200 and 'result' in result and 'token' in result['result']:
                            logger.info(f"✅ WebSocket token obtained successfully (attempt {attempt + 1})")
                            return {'token': result['result']['token']}
                        else:
                            error_info = result.get('error', [f'HTTP {resp.status}'])
                            raise Exception(f"API error: {error_info}")

            except Exception as e:
                error_str = str(e).lower()
                logger.warning(f"⚠️  Token request attempt {attempt + 1} failed: {e}")

                # Handle specific permission denied errors
                if 'EGeneral:Permission denied' in str(e):
                    logger.error("❌ CRITICAL: API credentials lack WebSocket permissions")
                    logger.error("📋 Required permissions in Kraken account:")
                    logger.error("   - Query Funds: REQUIRED")
                    logger.error("   - WebSocket Feeds: REQUIRED (if available)")
                    logger.error("   - Query Private Data: RECOMMENDED")
                    logger.error("💡 Fix: Update API permissions in Kraken Settings → API")
                    return None

                if 'permission denied' in error_str:
                    logger.error("❌ Permission denied - stopping retry attempts")
                    logger.error("🔧 This requires Kraken account settings changes, not retry")
                    return None
                elif 'nonce' in error_str and attempt < max_retries - 1:
                    # Handle nonce error with recovery
                    logger.info("🔄 Applying nonce error recovery...")
                    nonce_manager = ConsolidatedNonceManager.get_instance()
                    recovery_nonce = nonce_manager.handle_invalid_nonce_error("websocket_token_recovery")
                    logger.info(f"🔄 Recovery nonce: {recovery_nonce}")

                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"⏳ Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ All token request attempts failed: {e}")
                    return None

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

            with open(self.token_file) as f:
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

    def get_authentication_status(self) -> dict[str, Any]:
        """Get comprehensive authentication status with V2 enhancements"""
        current_time = time.time()

        status = {
            'is_running': self._is_running,
            'has_valid_token': self._is_token_valid(),
            'circuit_breaker_open': self._is_circuit_breaker_open(),
            'circuit_breaker_failures': self._circuit_breaker_failures,
            'current_time': current_time,
            'statistics': asdict(self.stats),
            # August 2025 V2 enhancements
            'api_tier': self.api_tier,
            'rate_limit_info': self.rate_limit_info,
            'derivatives_support': self.derivatives_support
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

    def get_token_info(self) -> Optional[dict[str, Any]]:
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
    api_key: str = None,
    private_key: str = None,
    credential_manager: Any = None,
    **kwargs
) -> WebSocketAuthenticationManager:
    """
    Factory function to create and start WebSocket authentication manager.

    Args:
        exchange_client: Kraken exchange client
        api_key: REST API key (for GetWebSocketsToken requests)
        private_key: REST Private key
        credential_manager: CredentialManager instance for automatic credential retrieval
        **kwargs: Additional configuration options

    Returns:
        Started WebSocketAuthenticationManager instance
    """
    manager = WebSocketAuthenticationManager(
        exchange_client=exchange_client,
        api_key=api_key,
        private_key=private_key,
        credential_manager=credential_manager,
        **kwargs
    )

    success = await manager.start()
    if not success:
        raise WebSocketAuthenticationError("Failed to start WebSocket authentication manager")

    return manager


@asynccontextmanager
async def websocket_auth_context(
    exchange_client: Any,
    api_key: str = None,
    private_key: str = None,
    credential_manager: Any = None,
    **kwargs
):
    """
    Async context manager for WebSocket authentication.

    Usage:
        async with websocket_auth_context(exchange, credential_manager=cred_mgr) as auth_manager:
            token = await auth_manager.get_websocket_token()
            # Use token for WebSocket connection
    """
    manager = None
    try:
        manager = await create_websocket_auth_manager(
            exchange_client, api_key, private_key, credential_manager, **kwargs
        )
        yield manager
    finally:
        if manager:
            await manager.stop()
