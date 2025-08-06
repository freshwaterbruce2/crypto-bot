"""
Authentication Service for Trading Bot
=====================================

High-level authentication service that provides a unified interface
for all authentication operations in the trading bot.
"""

import logging
from typing import Any, Dict, Optional

from .credential_manager import CredentialManager
from .kraken_auth import KrakenAuth

logger = logging.getLogger(__name__)


class AuthService:
    """
    High-level authentication service for the trading bot.
    
    Provides a unified interface for authentication operations,
    credential management, and authentication status monitoring.
    """

    def __init__(self):
        """Initialize the authentication service"""
        self.credential_manager = CredentialManager()
        self.kraken_auth: Optional[KrakenAuth] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize the authentication service with REST API credentials.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Get REST API credentials (used for trading operations)
            api_key, private_key = self.credential_manager.get_kraken_rest_credentials()

            if not api_key or not private_key:
                logger.warning("No REST API credentials found for authentication service")
                return False

            # Validate credentials
            if not self.credential_manager.validate_credentials(api_key, private_key):
                logger.error("Invalid REST API credentials format")
                return False

            # Initialize Kraken auth with REST credentials
            self.kraken_auth = KrakenAuth(api_key, private_key)

            # Test authentication
            test_headers = self.kraken_auth.get_auth_headers("/0/private/Balance")
            if not test_headers:
                logger.error("Failed to generate authentication headers")
                return False

            self._initialized = True
            logger.info("Authentication service initialized successfully with REST API credentials")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize authentication service: {e}")
            return False

    def is_initialized(self) -> bool:
        """Check if the service is properly initialized"""
        return self._initialized and self.kraken_auth is not None

    def get_auth_headers(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Get authentication headers for an API request.
        
        Args:
            endpoint: API endpoint path
            params: Request parameters
            
        Returns:
            Dictionary of authentication headers
        """
        if not self.is_initialized():
            raise RuntimeError("Authentication service not initialized")

        return self.kraken_auth.get_auth_headers(endpoint, params or {})

    async def get_auth_headers_async(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Get authentication headers asynchronously.
        
        Args:
            endpoint: API endpoint path
            params: Request parameters
            
        Returns:
            Dictionary of authentication headers
        """
        if not self.is_initialized():
            raise RuntimeError("Authentication service not initialized")

        return await self.kraken_auth.get_auth_headers_async(endpoint, params or {})

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the authentication service.
        
        Returns:
            Dictionary with service status information
        """
        credential_status = self.credential_manager.get_credential_status()

        status = {
            'service_initialized': self._initialized,
            'kraken_auth_available': self.kraken_auth is not None,
            'credentials_status': credential_status
        }

        if self.kraken_auth:
            auth_status = self.kraken_auth.get_comprehensive_status()
            status['auth_performance'] = auth_status.get('auth_stats', {})
            status['nonce_status'] = auth_status.get('nonce_status', {})

        return status

    async def test_authentication(self) -> bool:
        """
        Test authentication by generating headers for a test endpoint.
        
        Returns:
            True if authentication test passes
        """
        try:
            if not self.is_initialized():
                return False

            # Test header generation
            headers = await self.get_auth_headers_async("/0/private/Balance")

            # Basic validation
            required_headers = ['API-Key', 'API-Sign']
            for header in required_headers:
                if header not in headers:
                    logger.error(f"Missing required header: {header}")
                    return False

            logger.info("Authentication test passed")
            return True

        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            return False

    async def shutdown(self):
        """Shutdown the authentication service and cleanup resources"""
        if self.kraken_auth:
            self.kraken_auth = None

        self._initialized = False
        logger.info("Authentication service shutdown completed")


# Global service instance
auth_service = AuthService()


async def get_auth_service() -> AuthService:
    """Get the global authentication service instance"""
    if not auth_service.is_initialized():
        await auth_service.initialize()
    return auth_service


__all__ = [
    'AuthService',
    'auth_service',
    'get_auth_service'
]
