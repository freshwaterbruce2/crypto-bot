"""
Security Utilities Module
========================

Provides security utilities for safe error handling, input validation,
and prevention of information disclosure vulnerabilities.
"""

import hashlib
import logging
import re
import traceback
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Base security-related exception"""
    pass


class InformationDisclosureError(SecurityError):
    """Exception for information disclosure attempts"""
    pass


class SecurityValidator:
    """Security validation utilities"""

    # Patterns that might indicate sensitive information
    SENSITIVE_PATTERNS = [
        r'api[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9+/=]{20,}["\']?',
        r'api[_-]?secret\s*[:=]\s*["\']?[a-zA-Z0-9+/=]{20,}["\']?',
        r'private[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9+/=]{20,}["\']?',
        r'password\s*[:=]\s*["\']?[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{8,}["\']?',
        r'token\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.]{20,}["\']?',
        r'signature\s*[:=]\s*["\']?[a-zA-Z0-9+/=]{40,}["\']?',
        r'nonce\s*[:=]\s*["\']?\d{10,}["\']?',
        r'authorization\s*:\s*["\']?bearer\s+[a-zA-Z0-9_\-\.]{20,}["\']?',
        r'x-api-key\s*:\s*["\']?[a-zA-Z0-9+/=]{20,}["\']?'
    ]

    # File paths that might contain sensitive data
    SENSITIVE_PATHS = [
        r'.*\.env.*',
        r'.*config.*\.json',
        r'.*secret.*',
        r'.*credential.*',
        r'.*\.key$',
        r'.*\.pem$',
        r'.*\.p12$'
    ]

    @classmethod
    def contains_sensitive_data(cls, text: str) -> bool:
        """
        Check if text contains potentially sensitive information

        Args:
            text: Text to check

        Returns:
            True if sensitive data is detected
        """
        if not isinstance(text, str):
            text = str(text)

        text_lower = text.lower()

        # Check for sensitive patterns
        for pattern in cls.SENSITIVE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

        return False

    @classmethod
    def sanitize_for_logging(cls, text: str) -> str:
        """
        Sanitize text for safe logging by masking sensitive information

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text safe for logging
        """
        if not isinstance(text, str):
            text = str(text)

        sanitized = text

        # Replace sensitive patterns with masked versions
        for pattern in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(
                pattern,
                '[REDACTED_SENSITIVE_DATA]',
                sanitized,
                flags=re.IGNORECASE
            )

        return sanitized

    @classmethod
    def validate_input_safe(cls, user_input: str, max_length: int = 1000) -> bool:
        """
        Validate user input for basic safety

        Args:
            user_input: Input to validate
            max_length: Maximum allowed length

        Returns:
            True if input appears safe
        """
        if not isinstance(user_input, str):
            return False

        # Check length
        if len(user_input) > max_length:
            return False

        # Check for dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript\s*:',            # JavaScript URLs
            r'on\w+\s*=',                # Event handlers
            r'eval\s*\(',                # Eval calls
            r'exec\s*\(',                # Exec calls
            r'\$\{[^}]*\}',              # Template injection
            r'{{[^}]*}}',                # Template injection
            r'\.\./.*',                  # Path traversal
            r'\.\.\\.*',                 # Path traversal (Windows)
        ]

        user_input_lower = user_input.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                return False

        return True


class SecureErrorHandler:
    """Secure error handling utilities"""

    def __init__(self, log_sensitive_details: bool = False):
        """
        Initialize secure error handler

        Args:
            log_sensitive_details: Whether to log sensitive details (dev only)
        """
        self.log_sensitive_details = log_sensitive_details

    def safe_error_message(self, error: Exception, context: str = "") -> str:
        """
        Generate safe error message that doesn't leak sensitive information

        Args:
            error: Exception to process
            context: Context information (will be sanitized)

        Returns:
            Safe error message for user-facing display
        """
        # Create a generic error message
        type(error).__name__
        safe_message = f"An error occurred during {context}" if context else "An error occurred"

        # Create error hash for tracking
        error_hash = hashlib.sha256(str(error).encode()).hexdigest()[:8]

        return f"{safe_message} (Error ID: {error_hash})"

    def log_error_securely(
        self,
        error: Exception,
        context: str = "",
        additional_info: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Log error information securely

        Args:
            error: Exception to log
            context: Context information
            additional_info: Additional information to log

        Returns:
            Error ID for tracking
        """
        # Create error ID for tracking
        error_id = hashlib.sha256(f"{str(error)}{context}".encode()).hexdigest()[:12]

        # Sanitize context and additional info
        safe_context = SecurityValidator.sanitize_for_logging(context)

        if additional_info:
            safe_additional_info = {
                key: SecurityValidator.sanitize_for_logging(str(value))
                for key, value in additional_info.items()
            }
        else:
            safe_additional_info = {}

        # Log based on configuration
        if self.log_sensitive_details:
            # Development logging with more details
            logger.error(
                f"[ERROR_ID: {error_id}] {type(error).__name__}: {str(error)} "
                f"Context: {safe_context} Additional: {safe_additional_info}"
            )

            # Log stack trace securely
            stack_trace = traceback.format_exc()
            safe_stack_trace = SecurityValidator.sanitize_for_logging(stack_trace)
            logger.debug(f"[ERROR_ID: {error_id}] Stack trace: {safe_stack_trace}")
        else:
            # Production logging with minimal details
            logger.error(
                f"[ERROR_ID: {error_id}] {type(error).__name__} in {safe_context}"
            )

        return error_id

    def handle_authentication_error(self, error: Exception) -> dict[str, Any]:
        """
        Handle authentication errors securely

        Args:
            error: Authentication error

        Returns:
            Safe error response
        """
        error_id = self.log_error_securely(error, "authentication")

        # Don't reveal specific authentication failure reasons
        return {
            'success': False,
            'error': 'Authentication failed',
            'error_id': error_id,
            'error_type': 'authentication_error'
        }

    def handle_api_error(self, error: Exception, api_endpoint: str) -> dict[str, Any]:
        """
        Handle API errors securely

        Args:
            error: API error
            api_endpoint: API endpoint (will be sanitized)

        Returns:
            Safe error response
        """
        safe_endpoint = SecurityValidator.sanitize_for_logging(api_endpoint)
        error_id = self.log_error_securely(error, f"API call to {safe_endpoint}")

        return {
            'success': False,
            'error': 'API request failed',
            'error_id': error_id,
            'error_type': 'api_error'
        }


class SecureConfig:
    """Secure configuration utilities"""

    @staticmethod
    def validate_config_value(key: str, value: Any) -> bool:
        """
        Validate configuration values for security

        Args:
            key: Configuration key
            value: Configuration value

        Returns:
            True if configuration appears safe
        """
        if not isinstance(key, str) or not key:
            return False

        # Check for suspicious configuration keys
        suspicious_keys = [
            'exec', 'eval', 'system', 'shell', 'command',
            'script', 'code', 'function', 'import'
        ]

        key_lower = key.lower()
        if any(suspicious in key_lower for suspicious in suspicious_keys):
            logger.warning(f"[SECURITY] Suspicious configuration key detected: {key}")
            return False

        # Validate value based on type
        if isinstance(value, str):
            return SecurityValidator.validate_input_safe(value)
        elif isinstance(value, (int, float, bool)):
            return True
        elif isinstance(value, (list, dict)):
            # Basic validation for complex types
            return len(str(value)) < 10000  # Prevent huge config values

        return True

    @staticmethod
    def mask_sensitive_config(config: dict[str, Any]) -> dict[str, Any]:
        """
        Mask sensitive values in configuration for logging

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with sensitive values masked
        """
        masked_config = {}

        sensitive_keys = [
            'key', 'secret', 'password', 'token', 'credential',
            'api_key', 'api_secret', 'private_key', 'auth'
        ]

        for key, value in config.items():
            key_lower = key.lower()

            # Check if key contains sensitive information
            is_sensitive = any(sensitive in key_lower for sensitive in sensitive_keys)

            if is_sensitive:
                if isinstance(value, str) and len(value) > 8:
                    masked_config[key] = f"{value[:4]}***{value[-4:]}"
                else:
                    masked_config[key] = "***MASKED***"
            else:
                # Check if value contains sensitive data
                if isinstance(value, str) and SecurityValidator.contains_sensitive_data(value):
                    masked_config[key] = "***SENSITIVE_DATA_MASKED***"
                elif isinstance(value, dict):
                    masked_config[key] = SecureConfig.mask_sensitive_config(value)
                else:
                    masked_config[key] = value

        return masked_config


# Global secure error handler instance
_global_error_handler: Optional[SecureErrorHandler] = None


def get_secure_error_handler(log_sensitive_details: bool = False) -> SecureErrorHandler:
    """Get global secure error handler instance"""
    global _global_error_handler

    if _global_error_handler is None:
        _global_error_handler = SecureErrorHandler(log_sensitive_details)

    return _global_error_handler


def secure_log_error(error: Exception, context: str = "") -> str:
    """Convenience function for secure error logging"""
    handler = get_secure_error_handler()
    return handler.log_error_securely(error, context)


def safe_error_response(error: Exception, context: str = "") -> dict[str, Any]:
    """Convenience function for safe error responses"""
    handler = get_secure_error_handler()
    error_id = handler.log_error_securely(error, context)

    return {
        'success': False,
        'error': 'An error occurred',
        'error_id': error_id
    }


# Export main utilities
__all__ = [
    'SecurityValidator',
    'SecureErrorHandler',
    'SecureConfig',
    'SecurityError',
    'InformationDisclosureError',
    'get_secure_error_handler',
    'secure_log_error',
    'safe_error_response'
]
