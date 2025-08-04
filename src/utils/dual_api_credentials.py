"""
Dual API Credentials Manager
===========================

Manages separate API keys for REST and WebSocket operations to eliminate nonce collisions.
Provides a unified interface for accessing the appropriate credentials for each service.
"""

import os
import logging
from typing import Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class APICredentials:
    """Container for API key and secret"""
    api_key: str
    api_secret: str
    service_type: str  # "rest" or "websocket"
    
    def __post_init__(self):
        # Validate credentials are not empty
        if not self.api_key or not self.api_secret:
            raise ValueError(f"Empty credentials for {self.service_type} service")
        
        # Log credential loading (masked for security)
        masked_key = self.api_key[:8] + "..." if len(self.api_key) > 8 else "***"
        logger.info(f"[DUAL_API] Loaded {self.service_type} credentials: {masked_key}")


class DualAPICredentialsManager:
    """
    Manages dual API key setup for REST and WebSocket services
    """
    
    def __init__(self):
        self._rest_credentials: Optional[APICredentials] = None
        self._websocket_credentials: Optional[APICredentials] = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials from environment variables"""
        try:
            # Load REST API credentials
            rest_key = os.getenv('KRAKEN_REST_API_KEY')
            rest_secret = os.getenv('KRAKEN_REST_API_SECRET')
            
            # Load WebSocket API credentials
            websocket_key = os.getenv('KRAKEN_WEBSOCKET_API_KEY')
            websocket_secret = os.getenv('KRAKEN_WEBSOCKET_API_SECRET')
            
            # Fallback to legacy credentials if dual setup not available
            if not rest_key or not rest_secret:
                logger.warning("[DUAL_API] REST credentials not found, falling back to legacy")
                rest_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
                rest_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
            
            if not websocket_key or not websocket_secret:
                logger.warning("[DUAL_API] WebSocket credentials not found, falling back to legacy")
                websocket_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
                websocket_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
            
            # Create credential objects
            if rest_key and rest_secret:
                self._rest_credentials = APICredentials(rest_key, rest_secret, "rest")
            else:
                raise ValueError("No REST API credentials found")
            
            if websocket_key and websocket_secret:
                self._websocket_credentials = APICredentials(websocket_key, websocket_secret, "websocket")
            else:
                logger.warning("[DUAL_API] No WebSocket credentials, using REST credentials")
                self._websocket_credentials = self._rest_credentials
            
            # Check if we have truly separate keys
            if (self._rest_credentials and self._websocket_credentials and 
                self._rest_credentials.api_key == self._websocket_credentials.api_key):
                logger.warning("[DUAL_API] Using same API key for both services - nonce collisions may occur")
                logger.info("[DUAL_API] For optimal performance, create separate API keys")
            else:
                logger.info("[DUAL_API] Dual API key setup detected - nonce collision protection active")
            
        except Exception as e:
            logger.error(f"[DUAL_API] Failed to load credentials: {e}")
            raise
    
    def get_rest_credentials(self) -> APICredentials:
        """Get credentials for REST API operations"""
        if not self._rest_credentials:
            raise ValueError("REST API credentials not available")
        return self._rest_credentials
    
    def get_websocket_credentials(self) -> APICredentials:
        """Get credentials for WebSocket operations"""
        if not self._websocket_credentials:
            raise ValueError("WebSocket API credentials not available")
        return self._websocket_credentials
    
    def get_legacy_credentials(self) -> Tuple[str, str]:
        """Get legacy format credentials (api_key, api_secret) - uses REST credentials"""
        rest_creds = self.get_rest_credentials()
        return rest_creds.api_key, rest_creds.api_secret
    
    def has_separate_keys(self) -> bool:
        """Check if separate API keys are configured"""
        return (self._rest_credentials and self._websocket_credentials and 
                self._rest_credentials.api_key != self._websocket_credentials.api_key)
    
    def get_status(self) -> dict:
        """Get status information about credential configuration"""
        status = {
            "rest_available": self._rest_credentials is not None,
            "websocket_available": self._websocket_credentials is not None,
            "separate_keys": self.has_separate_keys(),
            "nonce_collision_protected": self.has_separate_keys()
        }
        
        if self._rest_credentials:
            status["rest_key_preview"] = self._rest_credentials.api_key[:8] + "..."
        
        if self._websocket_credentials:
            status["websocket_key_preview"] = self._websocket_credentials.api_key[:8] + "..."
        
        return status


# Global instance for easy access
_credentials_manager: Optional[DualAPICredentialsManager] = None


def get_credentials_manager() -> DualAPICredentialsManager:
    """Get the global credentials manager instance"""
    global _credentials_manager
    if _credentials_manager is None:
        _credentials_manager = DualAPICredentialsManager()
    return _credentials_manager


def get_rest_credentials() -> APICredentials:
    """Convenience function to get REST credentials"""
    return get_credentials_manager().get_rest_credentials()


def get_websocket_credentials() -> APICredentials:
    """Convenience function to get WebSocket credentials"""
    return get_credentials_manager().get_websocket_credentials()


def get_legacy_credentials() -> Tuple[str, str]:
    """Convenience function to get legacy format credentials"""
    return get_credentials_manager().get_legacy_credentials()


def has_dual_key_setup() -> bool:
    """Check if dual key setup is properly configured"""
    return get_credentials_manager().has_separate_keys()


# Export main functions
__all__ = [
    'DualAPICredentialsManager',
    'APICredentials', 
    'get_credentials_manager',
    'get_rest_credentials',
    'get_websocket_credentials',
    'get_legacy_credentials',
    'has_dual_key_setup'
]