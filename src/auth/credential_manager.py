"""
Credential Manager for Kraken API Authentication
===============================================

Manages secure storage and retrieval of API credentials for the trading bot.
"""

import os
import logging
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


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
        
    def get_kraken_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get Kraken API credentials from environment variables.
        
        Returns:
            Tuple of (api_key, private_key) or (None, None) if not found
        """
        api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
        private_key = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')
        
        if api_key and private_key:
            logger.info("Kraken API credentials loaded from environment")
            return api_key, private_key
        else:
            logger.warning("Kraken API credentials not found in environment variables")
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
        api_key, private_key = self.get_kraken_credentials()
        
        status = {
            'credentials_found': api_key is not None and private_key is not None,
            'api_key_present': api_key is not None,
            'private_key_present': private_key is not None,
            'credentials_valid': False
        }
        
        if api_key and private_key:
            status['credentials_valid'] = self.validate_credentials(api_key, private_key)
            status['api_key_preview'] = f"{api_key[:8]}..." if len(api_key) > 8 else "***"
        
        return status
    
    def set_test_credentials(self) -> Tuple[str, str]:
        """
        Return test credentials for validation purposes.
        
        Returns:
            Tuple of test (api_key, private_key)
        """
        test_api_key = "test_api_key_12345678901234567890"
        test_private_key = "test_private_key_base64_encoded_1234567890123456789012345678901234567890"
        
        return test_api_key, test_private_key


# Global instance for easy access
credential_manager = CredentialManager()


def get_kraken_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Convenience function to get Kraken credentials"""
    return credential_manager.get_kraken_credentials()


def get_credential_status() -> Dict[str, Any]:
    """Convenience function to get credential status"""
    return credential_manager.get_credential_status()


__all__ = [
    'CredentialManager',
    'credential_manager',
    'get_kraken_credentials',
    'get_credential_status'
]