"""
Credential Manager for Kraken API Authentication
===============================================

Manages secure storage and retrieval of API credentials for the trading bot.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Import Windows environment bridge for WSL support
try:
    from src.utils.windows_env_bridge import (
        get_windows_credential_status,
        get_windows_env_var,
        setup_kraken_credentials,
    )
    WINDOWS_ENV_BRIDGE_AVAILABLE = True
    logger.debug("Windows environment bridge available")
except ImportError as e:
    WINDOWS_ENV_BRIDGE_AVAILABLE = False
    logger.debug(f"Windows environment bridge not available: {e}")

# Detect if we're running in WSL
def _is_wsl() -> bool:
    """Check if we're running in WSL"""
    try:
        with open('/proc/version') as f:
            return 'microsoft' in f.read().lower()
    except:
        return False

WSL_ENVIRONMENT = _is_wsl()


class CredentialManager:
    """Manages API credentials securely"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize credential manager.
        
        Args:
            config_dir: Directory for configuration files
        """
        self.config_dir = config_dir or Path.home() / ".trading_bot"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize the credential manager (required by dependency injector).
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True

        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Validate that we can access credentials
            api_key, private_key = self.get_kraken_credentials()
            if api_key and private_key:
                logger.info("Credential manager initialized with valid API credentials")
            else:
                logger.warning("Credential manager initialized but no valid API credentials found")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize credential manager: {e}")
            return False

    def get_kraken_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get Kraken API credentials from environment variables.
        
        Priority order:
        1. KRAKEN_KEY / KRAKEN_SECRET (new unified approach)
        2. KRAKEN_API_KEY / KRAKEN_API_SECRET (legacy)
        3. API_KEY / API_SECRET (legacy fallback)
        4. Windows environment variables (if in WSL)
        
        Returns:
            Tuple of (api_key, private_key) or (None, None) if not found
        """
        # Try new unified approach first
        api_key = os.getenv('KRAKEN_KEY')
        private_key = os.getenv('KRAKEN_SECRET')
        credential_source = "unified (KRAKEN_KEY/KRAKEN_SECRET)"

        # Fallback to legacy names
        if not api_key or not private_key:
            api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
            private_key = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
            credential_source = "legacy (KRAKEN_API_KEY/KRAKEN_API_SECRET or API_KEY/API_SECRET)"

        # If still no credentials and we're in WSL, try Windows environment variables
        if (not api_key or not private_key) and WSL_ENVIRONMENT and WINDOWS_ENV_BRIDGE_AVAILABLE:
            logger.info("Attempting to load credentials from Windows environment variables...")

            try:
                windows_api_key = get_windows_env_var('KRAKEN_KEY')
                windows_private_key = get_windows_env_var('KRAKEN_SECRET')

                if windows_api_key and windows_private_key:
                    # Apply to current environment for future use
                    os.environ['KRAKEN_KEY'] = windows_api_key
                    os.environ['KRAKEN_SECRET'] = windows_private_key

                    api_key = windows_api_key
                    private_key = windows_private_key
                    credential_source = "Windows environment variables (KRAKEN_KEY/KRAKEN_SECRET)"

                    logger.info("Successfully loaded credentials from Windows environment variables")
                else:
                    # Try legacy Windows environment variable names
                    windows_api_key = get_windows_env_var('KRAKEN_API_KEY') or get_windows_env_var('API_KEY')
                    windows_private_key = get_windows_env_var('KRAKEN_API_SECRET') or get_windows_env_var('API_SECRET')

                    if windows_api_key and windows_private_key:
                        # Apply to current environment
                        os.environ['KRAKEN_KEY'] = windows_api_key
                        os.environ['KRAKEN_SECRET'] = windows_private_key

                        api_key = windows_api_key
                        private_key = windows_private_key
                        credential_source = "Windows environment variables (legacy names)"

                        logger.info("Successfully loaded credentials from Windows environment variables (legacy names)")

            except Exception as e:
                logger.warning(f"Failed to load credentials from Windows environment: {e}")

        if api_key and private_key:
            logger.info(f"Kraken API credentials loaded from environment using {credential_source}")
            return api_key, private_key
        else:
            if WSL_ENVIRONMENT and WINDOWS_ENV_BRIDGE_AVAILABLE:
                logger.warning("Kraken API credentials not found in Linux environment variables or Windows environment variables")
            else:
                logger.warning("Kraken API credentials not found in environment variables")
            return None, None

    def get_kraken_rest_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get Kraken REST API credentials from environment variables.
        These are used for trading operations and GetWebSocketsToken requests.
        
        Priority order:
        1. KRAKEN_KEY / KRAKEN_SECRET (new unified approach)
        2. KRAKEN_REST_API_KEY / KRAKEN_REST_API_SECRET (legacy specific)
        3. KRAKEN_API_KEY / KRAKEN_API_SECRET (legacy generic)
        4. API_KEY / API_SECRET (legacy fallback)
        5. Windows environment variables (if in WSL)
        
        Returns:
            Tuple of (api_key, private_key) or (None, None) if not found
        """
        # Try new unified approach first
        api_key = os.getenv('KRAKEN_KEY')
        private_key = os.getenv('KRAKEN_SECRET')
        credential_source = "unified (KRAKEN_KEY/KRAKEN_SECRET)"

        # Fallback to REST-specific credentials
        if not api_key or not private_key:
            api_key = os.getenv('KRAKEN_REST_API_KEY')
            private_key = os.getenv('KRAKEN_REST_API_SECRET')
            credential_source = "REST-specific (KRAKEN_REST_API_KEY/KRAKEN_REST_API_SECRET)"

        # Fallback to generic credentials if REST-specific ones not found
        if not api_key or not private_key:
            api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
            private_key = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
            credential_source = "legacy generic (KRAKEN_API_KEY/KRAKEN_API_SECRET or API_KEY/API_SECRET)"

        # If still no credentials and we're in WSL, try Windows environment variables
        if (not api_key or not private_key) and WSL_ENVIRONMENT and WINDOWS_ENV_BRIDGE_AVAILABLE:
            try:
                # Use the unified credentials method which already handles Windows environment variables
                api_key, private_key = self.get_kraken_credentials()
                if api_key and private_key:
                    credential_source = "Windows environment variables (via unified method)"
            except Exception as e:
                logger.warning(f"Failed to load REST credentials from Windows environment: {e}")

        if api_key and private_key:
            logger.info(f"Kraken REST API credentials loaded from environment using {credential_source}")
            return api_key, private_key
        else:
            if WSL_ENVIRONMENT and WINDOWS_ENV_BRIDGE_AVAILABLE:
                logger.warning("Kraken REST API credentials not found in Linux environment variables or Windows environment variables")
            else:
                logger.warning("Kraken REST API credentials not found in environment variables")
            return None, None

    def get_kraken_websocket_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get Kraken WebSocket API credentials from environment variables.
        These are used for WebSocket V2 data streaming connections.
        
        Priority order:
        1. KRAKEN_KEY / KRAKEN_SECRET (new unified approach)
        2. KRAKEN_WEBSOCKET_API_KEY / KRAKEN_WEBSOCKET_API_SECRET (legacy specific)
        3. KRAKEN_API_KEY / KRAKEN_API_SECRET (legacy generic)
        4. API_KEY / API_SECRET (legacy fallback)
        5. Windows environment variables (if in WSL)
        
        Returns:
            Tuple of (api_key, private_key) or (None, None) if not found
        """
        # Try new unified approach first
        api_key = os.getenv('KRAKEN_KEY')
        private_key = os.getenv('KRAKEN_SECRET')
        credential_source = "unified (KRAKEN_KEY/KRAKEN_SECRET)"

        # Fallback to WebSocket-specific credentials
        if not api_key or not private_key:
            api_key = os.getenv('KRAKEN_WEBSOCKET_API_KEY')
            private_key = os.getenv('KRAKEN_WEBSOCKET_API_SECRET')
            credential_source = "WebSocket-specific (KRAKEN_WEBSOCKET_API_KEY/KRAKEN_WEBSOCKET_API_SECRET)"

        # Fallback to generic credentials if WebSocket-specific ones not found
        if not api_key or not private_key:
            api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
            private_key = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
            credential_source = "legacy generic (KRAKEN_API_KEY/KRAKEN_API_SECRET or API_KEY/API_SECRET)"

        # If still no credentials and we're in WSL, try Windows environment variables
        if (not api_key or not private_key) and WSL_ENVIRONMENT and WINDOWS_ENV_BRIDGE_AVAILABLE:
            try:
                # Use the unified credentials method which already handles Windows environment variables
                api_key, private_key = self.get_kraken_credentials()
                if api_key and private_key:
                    credential_source = "Windows environment variables (via unified method)"
            except Exception as e:
                logger.warning(f"Failed to load WebSocket credentials from Windows environment: {e}")

        if api_key and private_key:
            logger.info(f"Kraken WebSocket API credentials loaded from environment using {credential_source}")
            return api_key, private_key
        else:
            if WSL_ENVIRONMENT and WINDOWS_ENV_BRIDGE_AVAILABLE:
                logger.warning("Kraken WebSocket API credentials not found in Linux environment variables or Windows environment variables")
            else:
                logger.warning("Kraken WebSocket API credentials not found in environment variables")
            return None, None

    def validate_credentials(self, api_key: str, private_key: str) -> bool:
        """
        Validate that credentials have the correct format.
        
        Args:
            api_key: API key to validate
            private_key: Private key to validate
            
        Returns:
            True if credentials appear valid
        """
        if not api_key or not private_key:
            return False

        # Basic format validation for Kraken credentials
        if len(api_key) < 20 or len(private_key) < 20:
            return False

        # Kraken API keys typically start with certain patterns
        if not api_key.replace('+', '').replace('/', '').replace('=', '').isalnum():
            return False

        return True

    def get_credential_status(self) -> Dict[str, Any]:
        """
        Get status of credential configuration.
        
        Returns:
            Dictionary with credential status information
        """
        # Check unified credentials
        unified_key = os.getenv('KRAKEN_KEY')
        unified_secret = os.getenv('KRAKEN_SECRET')

        # Check generic credentials
        api_key, private_key = self.get_kraken_credentials()

        # Check REST credentials
        rest_api_key, rest_private_key = self.get_kraken_rest_credentials()

        # Check WebSocket credentials
        ws_api_key, ws_private_key = self.get_kraken_websocket_credentials()

        # Check Windows environment bridge status if available
        windows_env_status = {}
        if WSL_ENVIRONMENT and WINDOWS_ENV_BRIDGE_AVAILABLE:
            try:
                windows_env_status = get_windows_credential_status()
            except Exception as e:
                windows_env_status = {"error": str(e)}

        status = {
            # New unified credentials status
            'unified_credentials': {
                'found': unified_key is not None and unified_secret is not None,
                'api_key_present': unified_key is not None,
                'private_key_present': unified_secret is not None,
                'valid': self.validate_credentials(unified_key, unified_secret) if unified_key and unified_secret else False,
                'api_key_preview': f"{unified_key[:8]}..." if unified_key and len(unified_key) > 8 else "***",
                'recommended': True  # This is the recommended approach
            },
            'generic_credentials': {
                'found': api_key is not None and private_key is not None,
                'api_key_present': api_key is not None,
                'private_key_present': private_key is not None,
                'valid': self.validate_credentials(api_key, private_key) if api_key and private_key else False,
                'api_key_preview': f"{api_key[:8]}..." if api_key and len(api_key) > 8 else "***",
                # Determine if using unified or legacy
                'using_unified': unified_key is not None and unified_secret is not None,
                'source': "unified" if (unified_key and unified_secret) else "legacy"
            },
            'rest_credentials': {
                'found': rest_api_key is not None and rest_private_key is not None,
                'api_key_present': rest_api_key is not None,
                'private_key_present': rest_private_key is not None,
                'valid': self.validate_credentials(rest_api_key, rest_private_key) if rest_api_key and rest_private_key else False,
                'api_key_preview': f"{rest_api_key[:8]}..." if rest_api_key and len(rest_api_key) > 8 else "***",
                'using_unified': unified_key is not None and unified_secret is not None,
                'source': "unified" if (unified_key and unified_secret) else "legacy"
            },
            'websocket_credentials': {
                'found': ws_api_key is not None and ws_private_key is not None,
                'api_key_present': ws_api_key is not None,
                'private_key_present': ws_private_key is not None,
                'valid': self.validate_credentials(ws_api_key, ws_private_key) if ws_api_key and ws_private_key else False,
                'api_key_preview': f"{ws_api_key[:8]}..." if ws_api_key and len(ws_api_key) > 8 else "***",
                'using_unified': unified_key is not None and unified_secret is not None,
                'source': "unified" if (unified_key and unified_secret) else "legacy"
            },
            # Legacy compatibility
            'credentials_found': api_key is not None and private_key is not None,
            'api_key_present': api_key is not None,
            'private_key_present': private_key is not None,
            'credentials_valid': self.validate_credentials(api_key, private_key) if api_key and private_key else False,
            # Migration info
            'migration_info': {
                'using_unified_approach': unified_key is not None and unified_secret is not None,
                'has_legacy_credentials': any([
                    os.getenv('KRAKEN_API_KEY'),
                    os.getenv('KRAKEN_REST_API_KEY'),
                    os.getenv('KRAKEN_WEBSOCKET_API_KEY'),
                    os.getenv('API_KEY')
                ]),
                'should_migrate': unified_key is None and unified_secret is None and api_key is not None and private_key is not None
            },
            # WSL and Windows environment bridge status
            'wsl_environment': {
                'is_wsl': WSL_ENVIRONMENT,
                'windows_env_bridge_available': WINDOWS_ENV_BRIDGE_AVAILABLE,
                'windows_env_status': windows_env_status
            }
        }

        return status

    def generate_test_credentials(self) -> Tuple[str, str]:
        """
        Generate secure test credentials for validation purposes.
        SECURITY: Never use hardcoded credentials - generate random ones.
        
        Returns:
            Tuple of randomly generated test (api_key, private_key)
        """
        import base64
        import secrets

        # Generate cryptographically secure random test credentials
        test_api_key = base64.b64encode(secrets.token_bytes(42)).decode('ascii')
        test_private_key = base64.b64encode(secrets.token_bytes(66)).decode('ascii')

        logger.info("[CREDENTIAL_MGR] Generated secure random test credentials")
        return test_api_key, test_private_key


# Global instance for easy access
credential_manager = CredentialManager()


def get_kraken_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Convenience function to get Kraken credentials"""
    return credential_manager.get_kraken_credentials()


def get_kraken_rest_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Convenience function to get Kraken REST API credentials"""
    return credential_manager.get_kraken_rest_credentials()


def get_kraken_websocket_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Convenience function to get Kraken WebSocket API credentials"""
    return credential_manager.get_kraken_websocket_credentials()


def get_credential_status() -> Dict[str, Any]:
    """Convenience function to get credential status"""
    return credential_manager.get_credential_status()


__all__ = [
    'CredentialManager',
    'credential_manager',
    'get_kraken_credentials',
    'get_kraken_rest_credentials',
    'get_kraken_websocket_credentials',
    'get_credential_status'
]
