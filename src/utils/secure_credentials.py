"""
Secure Credentials Utility - Security Fix for API Key Protection
===============================================================

CRITICAL SECURITY FIX: This utility prevents credential exposure in logs
and provides secure handling of API keys and secrets throughout the system.

Key Features:
- Safe credential masking for logs
- Secure validation without exposure
- Environment variable loading with validation
- Prevention of accidental credential leakage
"""

import hashlib
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SecureCredentials:
    """
    Secure credential management system

    Features:
    - Secure API key/secret loading
    - Safe logging without credential exposure
    - Validation without revealing credentials
    - Hash-based identification
    """

    def __init__(self):
        self._api_key = None
        self._api_secret = None
        self._api_key_hash = None
        self._is_loaded = False

    def load_credentials(self) -> bool:
        """
        Securely load credentials from environment

        Returns:
            True if credentials loaded successfully
        """
        try:
            api_key = os.getenv('KRAKEN_API_KEY') or os.getenv('API_KEY')
            api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('API_SECRET')

            if not api_key or not api_secret:
                logger.error("[SECURE_CREDS] API credentials not found in environment")
                return False

            # Validate credential format
            if not self._validate_credential_format(api_key, api_secret):
                logger.error("[SECURE_CREDS] Invalid credential format")
                return False

            self._api_key = api_key
            self._api_secret = api_secret
            self._api_key_hash = self._create_safe_hash(api_key)
            self._is_loaded = True

            logger.info("[SECURE_CREDS] Credentials loaded successfully")
            logger.info(f"[SECURE_CREDS] API Key ID: {self.get_safe_key_identifier()}")
            logger.info(f"[SECURE_CREDS] Credentials validated: {self.get_validation_status()}")

            return True

        except Exception as e:
            logger.error(f"[SECURE_CREDS] Failed to load credentials: {e}")
            return False

    def _validate_credential_format(self, api_key: str, api_secret: str) -> bool:
        """Validate credential format without logging sensitive data"""
        # API key should be ~56 characters
        if not api_key or len(api_key) < 50 or len(api_key) > 80:
            logger.error(f"[SECURE_CREDS] Invalid API key length: {len(api_key) if api_key else 0}")
            return False

        # API secret should be ~88 characters (base64 encoded)
        if not api_secret or len(api_secret) < 80 or len(api_secret) > 100:
            logger.error(f"[SECURE_CREDS] Invalid API secret length: {len(api_secret) if api_secret else 0}")
            return False

        # Check for placeholder values
        placeholder_values = [
            'your_api_key_here',
            'your_api_secret_here',
            'replace_with_actual_key',
            'placeholder'
        ]

        if api_key.lower() in placeholder_values or api_secret.lower() in placeholder_values:
            logger.error("[SECURE_CREDS] Placeholder credentials detected")
            return False

        return True

    def _create_safe_hash(self, credential: str) -> str:
        """Create safe hash for identification without revealing credential"""
        return hashlib.sha256(credential.encode()).hexdigest()[:8]

    def get_api_key(self) -> Optional[str]:
        """Get API key (only if credentials are loaded)"""
        if not self._is_loaded:
            logger.error("[SECURE_CREDS] Credentials not loaded - call load_credentials() first")
            return None
        return self._api_key

    def get_api_secret(self) -> Optional[str]:
        """Get API secret (only if credentials are loaded)"""
        if not self._is_loaded:
            logger.error("[SECURE_CREDS] Credentials not loaded - call load_credentials() first")
            return None
        return self._api_secret

    def get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Get both credentials as tuple"""
        return self.get_api_key(), self.get_api_secret()

    def get_safe_key_identifier(self) -> str:
        """Get safe identifier for API key (for logging)"""
        if not self._api_key_hash:
            return "unknown"
        return f"key_{self._api_key_hash}"

    def get_validation_status(self) -> dict[str, Any]:
        """Get validation status without exposing credentials"""
        if not self._is_loaded:
            return {
                'loaded': False,
                'valid': False,
                'key_length': 0,
                'secret_length': 0
            }

        return {
            'loaded': True,
            'valid': True,
            'key_length': len(self._api_key) if self._api_key else 0,
            'secret_length': len(self._api_secret) if self._api_secret else 0,
            'key_identifier': self.get_safe_key_identifier()
        }

    def is_loaded(self) -> bool:
        """Check if credentials are loaded and valid"""
        return self._is_loaded

    def clear_credentials(self):
        """Securely clear credentials from memory"""
        if self._api_key:
            self._api_key = "0" * len(self._api_key)  # Overwrite memory
        if self._api_secret:
            self._api_secret = "0" * len(self._api_secret)  # Overwrite memory

        self._api_key = None
        self._api_secret = None
        self._api_key_hash = None
        self._is_loaded = False

        logger.info("[SECURE_CREDS] Credentials cleared from memory")


# Global instance for application-wide use
_global_credentials: Optional[SecureCredentials] = None


def get_secure_credentials() -> SecureCredentials:
    """Get global secure credentials instance"""
    global _global_credentials

    if _global_credentials is None:
        _global_credentials = SecureCredentials()

    return _global_credentials


def load_credentials() -> bool:
    """Load credentials using global instance"""
    return get_secure_credentials().load_credentials()


def get_api_credentials() -> tuple[Optional[str], Optional[str]]:
    """Get API credentials using global instance"""
    return get_secure_credentials().get_credentials()


def get_safe_key_id() -> str:
    """Get safe key identifier for logging"""
    return get_secure_credentials().get_safe_key_identifier()


def mask_credential(credential: str, show_chars: int = 4) -> str:
    """
    Safely mask credential for logging

    Args:
        credential: The credential to mask
        show_chars: Number of characters to show at start/end

    Returns:
        Masked credential safe for logging
    """
    if not credential:
        return "***empty***"

    if len(credential) < show_chars * 2:
        return "***"

    return f"{credential[:show_chars]}***{credential[-show_chars:]}"


def safe_log_credentials():
    """Safely log credential status without exposing sensitive data"""
    creds = get_secure_credentials()
    status = creds.get_validation_status()

    if status['loaded']:
        logger.info("[SECURE_CREDS] ✅ API credentials loaded and validated")
        logger.info(f"[SECURE_CREDS] ✅ Key ID: {status['key_identifier']}")
        logger.info(f"[SECURE_CREDS] ✅ Key length: {status['key_length']} chars")
        logger.info(f"[SECURE_CREDS] ✅ Secret length: {status['secret_length']} chars")
    else:
        logger.error("[SECURE_CREDS] ❌ API credentials not loaded or invalid")


# Security validation functions
def validate_no_credential_logging(text: str) -> bool:
    """
    Validate that text doesn't contain exposed credentials

    Returns:
        False if credentials are detected in text
    """
    # Common patterns that might indicate credential exposure
    dangerous_patterns = [
        r'api_key\s*=\s*[a-zA-Z0-9]{15,}',
        r'api_secret\s*=\s*[a-zA-Z0-9]{15,}',
        r'KRAKEN_API_KEY\s*=\s*[a-zA-Z0-9]{15,}',
        r'KRAKEN_API_SECRET\s*=\s*[a-zA-Z0-9]{15,}'
    ]

    import re
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False

    return True


def secure_print(message: str, *args, **kwargs):
    """
    Secure print function that prevents credential exposure

    Use this instead of print() for any message that might contain credentials
    """
    if not validate_no_credential_logging(message):
        logger.warning("[SECURE_CREDS] Blocked potentially unsafe print containing credentials")
        print("*** Message blocked - potential credential exposure ***")
        return

    print(message, *args, **kwargs)


def secure_logger_wrapper(original_logger):
    """
    Wrap logger to prevent credential exposure

    Usage:
        logger = secure_logger_wrapper(logging.getLogger(__name__))
    """
    class SecureLogger:
        def __init__(self, logger):
            self._logger = logger

        def _safe_log(self, level, message, *args, **kwargs):
            if isinstance(message, str) and not validate_no_credential_logging(message):
                self._logger.log(level, "*** Log message blocked - potential credential exposure ***")
                return
            self._logger.log(level, message, *args, **kwargs)

        def debug(self, message, *args, **kwargs):
            self._safe_log(logging.DEBUG, message, *args, **kwargs)

        def info(self, message, *args, **kwargs):
            self._safe_log(logging.INFO, message, *args, **kwargs)

        def warning(self, message, *args, **kwargs):
            self._safe_log(logging.WARNING, message, *args, **kwargs)

        def error(self, message, *args, **kwargs):
            self._safe_log(logging.ERROR, message, *args, **kwargs)

        def critical(self, message, *args, **kwargs):
            self._safe_log(logging.CRITICAL, message, *args, **kwargs)

    return SecureLogger(original_logger)
