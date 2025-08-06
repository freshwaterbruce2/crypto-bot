"""
WebSocket Token Manager
======================

Handles WebSocket authentication tokens using the correct WebSocket API credentials.
Ensures WebSocket operations use separate API key from REST trading operations.
"""

import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional

from .dual_api_credentials import get_websocket_credentials
from .network import RequestConfig, ResilientRequest

logger = logging.getLogger(__name__)


class WebSocketTokenManager:
    """Manages WebSocket authentication tokens using WebSocket-specific API credentials"""

    def __init__(self):
        self.ws_credentials = get_websocket_credentials()
        self.current_token: Optional[str] = None
        self.token_expires_at: float = 0
        self.token_refresh_buffer: float = 300  # 5 minutes before expiry

        # Setup request handler for WebSocket token requests
        request_config = RequestConfig(
            max_retries=3,
            timeout=30.0,
            backoff_factor=2.0
        )
        self.resilient_request = ResilientRequest(request_config)

        # Kraken API endpoints
        self.base_url = "https://api.kraken.com"
        self.api_version = "0"

        logger.info(f"[WS_TOKEN] Initialized with WebSocket credentials: {self.ws_credentials.api_key[:8]}...")

    def _get_nonce(self) -> str:
        """Generate nonce for WebSocket API requests"""
        # Use microsecond precision for WebSocket requests
        return str(int(time.time() * 1000000))

    def _create_signature(self, path: str, data: str, nonce: str) -> str:
        """Create API signature for WebSocket credentials"""
        try:
            # Decode the secret
            secret = base64.b64decode(self.ws_credentials.api_secret)

            # Create the message to sign
            message = path.encode() + hashlib.sha256((nonce + data).encode()).digest()

            # Create HMAC signature
            signature = hmac.new(secret, message, hashlib.sha512)

            # Return base64 encoded signature
            return base64.b64encode(signature.digest()).decode()

        except Exception as e:
            logger.error(f"[WS_TOKEN] Error creating signature: {e}")
            raise

    async def get_websocket_token(self) -> Optional[str]:
        """Get WebSocket authentication token using WebSocket API credentials"""
        try:
            # Check if current token is still valid
            if (self.current_token and
                time.time() < (self.token_expires_at - self.token_refresh_buffer)):
                logger.debug("[WS_TOKEN] Using cached WebSocket token")
                return self.current_token

            logger.info("[WS_TOKEN] Requesting new WebSocket authentication token...")

            # Prepare request
            path = f"/{self.api_version}/private/GetWebSocketsToken"
            url = self.base_url + path

            nonce = self._get_nonce()
            data = f"nonce={nonce}"

            # Create signature using WebSocket credentials
            signature = self._create_signature(path, data, nonce)

            # Prepare headers
            headers = {
                'API-Key': self.ws_credentials.api_key,
                'API-Sign': signature,
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            # Make request using WebSocket credentials
            logger.debug(f"[WS_TOKEN] Making token request with WebSocket key: {self.ws_credentials.api_key[:8]}...")

            response = await self.resilient_request.post(
                url=url,
                headers=headers,
                data=data
            )

            if response and 'result' in response:
                token_data = response['result']

                if isinstance(token_data, dict) and 'token' in token_data:
                    self.current_token = token_data['token']

                    # Set expiry time (tokens typically last 15 minutes)
                    expires_in = token_data.get('expires', 900)  # Default 15 minutes
                    self.token_expires_at = time.time() + expires_in

                    logger.info(f"[WS_TOKEN] WebSocket token obtained successfully (expires in {expires_in}s)")
                    return self.current_token
                else:
                    logger.error(f"[WS_TOKEN] Invalid token response format: {token_data}")
                    return None
            elif response and 'error' in response:
                # Enhanced error handling for Kraken Pro accounts
                error_msg = response['error'][0] if isinstance(response['error'], list) else str(response['error'])
                logger.error(f"[WS_TOKEN] Kraken API Error: {error_msg}")

                if "permission" in error_msg.lower() or "denied" in error_msg.lower():
                    logger.error("[WS_TOKEN] WEBSOCKET PERMISSION DENIED - KRAKEN PRO ACCOUNT ISSUE")
                    logger.error("[WS_TOKEN] Your API key works for REST but lacks WebSocket permissions")
                    logger.error("[WS_TOKEN] SOLUTION:")
                    logger.error("[WS_TOKEN] 1. Log into your Kraken account")
                    logger.error("[WS_TOKEN] 2. Go to Settings → API → Edit your API key")
                    logger.error("[WS_TOKEN] 3. Ensure 'Access WebSockets API' permission is enabled")
                    logger.error("[WS_TOKEN] 4. For Kraken Pro: Check Pro-specific WebSocket permissions")
                    logger.error("[WS_TOKEN] 5. Save changes and wait 5-10 minutes")
                elif "nonce" in error_msg.lower():
                    logger.error("[WS_TOKEN] NONCE ERROR - Try again in a few seconds")
                    logger.error("[WS_TOKEN] Ensure system time is synchronized")

                return None
            else:
                logger.error(f"[WS_TOKEN] Failed to get WebSocket token: {response}")
                logger.error("[WS_TOKEN] This may indicate API format issues or network problems")
                return None

        except Exception as e:
            logger.error(f"[WS_TOKEN] Error getting WebSocket token: {e}")
            return None

    async def refresh_token_if_needed(self) -> bool:
        """Refresh token if it's close to expiry"""
        try:
            if (not self.current_token or
                time.time() >= (self.token_expires_at - self.token_refresh_buffer)):

                logger.info("[WS_TOKEN] Token refresh needed")
                new_token = await self.get_websocket_token()
                return new_token is not None

            return True  # Token is still valid

        except Exception as e:
            logger.error(f"[WS_TOKEN] Error refreshing token: {e}")
            return False

    def is_token_valid(self) -> bool:
        """Check if current token is valid"""
        return (self.current_token and
                time.time() < (self.token_expires_at - self.token_refresh_buffer))

    def get_status(self) -> Dict[str, Any]:
        """Get token manager status"""
        return {
            'has_token': self.current_token is not None,
            'token_valid': self.is_token_valid(),
            'expires_at': self.token_expires_at,
            'time_until_expiry': max(0, self.token_expires_at - time.time()),
            'websocket_key_preview': self.ws_credentials.api_key[:8] + "..."
        }


# Global instance
_token_manager: Optional[WebSocketTokenManager] = None


def get_websocket_token_manager() -> WebSocketTokenManager:
    """Get the global WebSocket token manager"""
    global _token_manager
    if _token_manager is None:
        _token_manager = WebSocketTokenManager()
    return _token_manager


async def get_websocket_auth_token() -> Optional[str]:
    """Convenience function to get WebSocket authentication token"""
    return await get_websocket_token_manager().get_websocket_token()


# Export main functions
__all__ = [
    'WebSocketTokenManager',
    'get_websocket_token_manager',
    'get_websocket_auth_token'
]
