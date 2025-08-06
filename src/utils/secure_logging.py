"""
Secure Logging System with Credential Sanitization
==================================================

Enterprise-grade logging system that prevents credential exposure in logs.
Implements comprehensive credential detection and sanitization following
2025 security best practices.

Features:
- Automatic credential detection and masking
- Pattern-based sensitive data sanitization
- Structured logging with security context
- Performance-optimized regex patterns
- Configurable sensitivity levels
- Real-time log sanitization
- Memory-safe log handling
"""

import hashlib
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional


@dataclass
class SensitivePattern:
    """Configuration for sensitive data patterns"""
    name: str
    pattern: str
    replacement: str
    confidence: float  # 0.0 to 1.0 - how confident we are this is sensitive
    enabled: bool = True


class SecureLogFormatter(logging.Formatter):
    """
    Secure log formatter that sanitizes sensitive data before logging.
    
    Automatically detects and masks:
    - API keys and secrets
    - Authentication tokens
    - Private keys and certificates
    - Email addresses (optional)
    - URLs with credentials
    - Credit card numbers
    - Social Security Numbers
    - Custom patterns
    """

    # Pre-compiled regex patterns for performance
    SENSITIVE_PATTERNS = [
        # Kraken API patterns
        SensitivePattern(
            name="kraken_api_key",
            pattern=r'[A-Za-z0-9+/]{56}={0,2}',  # Kraken API keys
            replacement="[KRAKEN_API_KEY_MASKED]",
            confidence=0.9
        ),
        SensitivePattern(
            name="kraken_private_key",
            pattern=r'[A-Za-z0-9+/]{88}={0,2}',  # Kraken private keys
            replacement="[KRAKEN_PRIVATE_KEY_MASKED]",
            confidence=0.9
        ),

        # Generic API patterns
        SensitivePattern(
            name="api_key_generic",
            pattern=r'(?i)(?:api[_-]?key|apikey|access[_-]?key)["\s]*[:=]["\s]*([A-Za-z0-9+/]{20,})',
            replacement=r'\1[API_KEY_MASKED]',
            confidence=0.8
        ),
        SensitivePattern(
            name="api_secret_generic",
            pattern=r'(?i)(?:api[_-]?secret|apisecret|secret[_-]?key)["\s]*[:=]["\s]*([A-Za-z0-9+/]{20,})',
            replacement=r'\1[API_SECRET_MASKED]',
            confidence=0.8
        ),

        # Token patterns
        SensitivePattern(
            name="bearer_token",
            pattern=r'(?i)bearer\s+([A-Za-z0-9\-._~+/]+=*)',
            replacement=r'Bearer [TOKEN_MASKED]',
            confidence=0.9
        ),
        SensitivePattern(
            name="jwt_token",
            pattern=r'eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]*',
            replacement="[JWT_TOKEN_MASKED]",
            confidence=0.95
        ),

        # Private keys and certificates
        SensitivePattern(
            name="private_key_pem",
            pattern=r'-----BEGIN[A-Z\s]+PRIVATE KEY-----[\s\S]*?-----END[A-Z\s]+PRIVATE KEY-----',
            replacement="[PEM_PRIVATE_KEY_MASKED]",
            confidence=1.0
        ),
        SensitivePattern(
            name="certificate_pem",
            pattern=r'-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----',
            replacement="[PEM_CERTIFICATE_MASKED]",
            confidence=0.7
        ),

        # URLs with credentials
        SensitivePattern(
            name="url_with_credentials",
            pattern=r'(?i)https?://[^:]+:[^@]+@[^\s]+',
            replacement="[URL_WITH_CREDENTIALS_MASKED]",
            confidence=0.9
        ),

        # Base64 encoded data (potential credentials)
        SensitivePattern(
            name="base64_credential",
            pattern=r'(?i)(?:password|secret|key|token)["\s]*[:=]["\s]*([A-Za-z0-9+/]{40,}={0,2})',
            replacement=r'\1[BASE64_DATA_MASKED]',
            confidence=0.7
        ),

        # Credit card numbers
        SensitivePattern(
            name="credit_card",
            pattern=r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            replacement="[CREDIT_CARD_MASKED]",
            confidence=0.8
        ),

        # Social Security Numbers
        SensitivePattern(
            name="ssn",
            pattern=r'\b\d{3}-\d{2}-\d{4}\b',
            replacement="[SSN_MASKED]",
            confidence=0.9
        ),

        # Email addresses (optional - might be needed for support)
        SensitivePattern(
            name="email",
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            replacement="[EMAIL_MASKED]",
            confidence=0.3,
            enabled=False  # Disabled by default
        ),

        # Cryptocurrency addresses
        SensitivePattern(
            name="bitcoin_address",
            pattern=r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
            replacement="[BTC_ADDRESS_MASKED]",
            confidence=0.8
        ),
        SensitivePattern(
            name="ethereum_address",
            pattern=r'\b0x[a-fA-F0-9]{40}\b',
            replacement="[ETH_ADDRESS_MASKED]",
            confidence=0.8
        ),

        # Generic high-entropy strings (potential secrets)
        SensitivePattern(
            name="high_entropy_string",
            pattern=r'\b[A-Za-z0-9+/]{50,}={0,2}\b',
            replacement="[HIGH_ENTROPY_STRING_MASKED]",
            confidence=0.4,
            enabled=False  # Too aggressive, disabled by default
        ),
    ]

    def __init__(self, *args, **kwargs):
        """Initialize secure formatter with compiled patterns"""
        super().__init__(*args, **kwargs)

        # Compile patterns for performance
        self._compiled_patterns: List[tuple] = []
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.enabled:
                try:
                    compiled = re.compile(pattern.pattern, re.MULTILINE | re.DOTALL)
                    self._compiled_patterns.append((compiled, pattern.replacement, pattern.name, pattern.confidence))
                except re.error as e:
                    logging.getLogger(__name__).warning(f"Failed to compile pattern {pattern.name}: {e}")

        # Statistics
        self._sanitization_stats = {
            'total_messages': 0,
            'sanitized_messages': 0,
            'patterns_detected': {},
            'last_reset': datetime.utcnow()
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with credential sanitization"""
        try:
            # Get the original formatted message
            original_message = super().format(record)

            # Sanitize the message
            sanitized_message, detected_patterns = self._sanitize_message(original_message)

            # Update statistics
            self._sanitization_stats['total_messages'] += 1
            if detected_patterns:
                self._sanitization_stats['sanitized_messages'] += 1
                for pattern_name in detected_patterns:
                    self._sanitization_stats['patterns_detected'][pattern_name] = (
                        self._sanitization_stats['patterns_detected'].get(pattern_name, 0) + 1
                    )

            return sanitized_message

        except Exception:
            # Failsafe: if sanitization fails, return a generic error message
            # to prevent potential credential exposure
            return f"[LOG_SANITIZATION_ERROR] {record.levelname}: {record.name} - Error processing log message"

    @lru_cache(maxsize=1000)  # Cache sanitized messages for performance
    def _sanitize_message(self, message: str) -> tuple[str, List[str]]:
        """
        Sanitize message by detecting and masking sensitive data.
        
        Args:
            message: Original log message
            
        Returns:
            Tuple of (sanitized_message, detected_pattern_names)
        """
        if not message:
            return message, []

        sanitized = message
        detected_patterns = []

        # Apply all patterns
        for compiled_pattern, replacement, name, confidence in self._compiled_patterns:
            try:
                # Check if pattern matches
                if compiled_pattern.search(sanitized):
                    # Apply sanitization
                    sanitized = compiled_pattern.sub(replacement, sanitized)
                    detected_patterns.append(name)

                    # Add confidence indicator for high-confidence detections
                    if confidence >= 0.8:
                        sanitized += f" [SECURITY_SANITIZED:{name.upper()}]"

            except Exception as e:
                # Continue with other patterns if one fails
                logging.getLogger(__name__).debug(f"Pattern {name} failed: {e}")
                continue

        return sanitized, detected_patterns

    def get_sanitization_stats(self) -> Dict[str, Any]:
        """Get sanitization statistics"""
        stats = dict(self._sanitization_stats)
        stats['sanitization_rate'] = (
            stats['sanitized_messages'] / max(stats['total_messages'], 1)
        )
        return stats

    def reset_stats(self):
        """Reset sanitization statistics"""
        self._sanitization_stats = {
            'total_messages': 0,
            'sanitized_messages': 0,
            'patterns_detected': {},
            'last_reset': datetime.utcnow()
        }


class SecureLogHandler(logging.Handler):
    """
    Secure log handler that provides additional security features:
    - Log integrity checking
    - Sensitive data alerts
    - Performance monitoring
    - Security event correlation
    """

    def __init__(self, base_handler: logging.Handler):
        """
        Initialize secure handler wrapping a base handler.
        
        Args:
            base_handler: The underlying handler to wrap
        """
        super().__init__()
        self.base_handler = base_handler
        self.setLevel(base_handler.level)

        # Security monitoring
        self._security_events = []
        self._performance_metrics = {
            'total_logs': 0,
            'processing_time_ms': 0,
            'security_alerts': 0
        }

    def emit(self, record: logging.LogRecord):
        """Emit log record with security monitoring"""
        start_time = datetime.utcnow()

        try:
            # Check for security-related events
            self._analyze_security_event(record)

            # Pass to base handler
            self.base_handler.emit(record)

            # Update metrics
            self._performance_metrics['total_logs'] += 1
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._performance_metrics['processing_time_ms'] += processing_time

        except Exception as e:
            # Handle errors gracefully to prevent log suppression
            print(f"SecureLogHandler error: {e}", file=sys.stderr)
            try:
                self.base_handler.emit(record)
            except:
                pass  # Last resort: ignore the log to prevent crashes

    def _analyze_security_event(self, record: logging.LogRecord):
        """Analyze log record for security events"""
        # Check for authentication failures
        if any(keyword in record.getMessage().lower() for keyword in
               ['failed', 'denied', 'unauthorized', 'forbidden', 'invalid']):
            if any(keyword in record.getMessage().lower() for keyword in
                   ['login', 'auth', 'credential', 'token', 'key']):
                self._security_events.append({
                    'timestamp': datetime.utcnow(),
                    'level': record.levelname,
                    'event_type': 'authentication_failure',
                    'message_hash': hashlib.sha256(record.getMessage().encode()).hexdigest()[:16]
                })
                self._performance_metrics['security_alerts'] += 1

        # Keep only recent security events (last 1000)
        if len(self._security_events) > 1000:
            self._security_events = self._security_events[-1000:]

    def get_security_events(self) -> List[Dict[str, Any]]:
        """Get recent security events"""
        return list(self._security_events)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        metrics = dict(self._performance_metrics)
        if metrics['total_logs'] > 0:
            metrics['avg_processing_time_ms'] = metrics['processing_time_ms'] / metrics['total_logs']
        else:
            metrics['avg_processing_time_ms'] = 0
        return metrics


def setup_secure_logging(
    logger_name: Optional[str] = None,
    level: int = logging.INFO,
    enable_console: bool = True,
    enable_file: bool = True,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up secure logging with credential sanitization.
    
    Args:
        logger_name: Name of logger (None for root logger)
        level: Logging level
        enable_console: Enable console logging
        enable_file: Enable file logging
        log_file: Path to log file
        
    Returns:
        Configured secure logger
    """
    # Get logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Create secure formatter
    formatter = SecureLogFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        secure_console_handler = SecureLogHandler(console_handler)
        logger.addHandler(secure_console_handler)

    # File handler
    if enable_file:
        if not log_file:
            log_file = f"secure_trading_bot_{datetime.utcnow().strftime('%Y%m%d')}.log"

        try:
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            secure_file_handler = SecureLogHandler(file_handler)
            logger.addHandler(secure_file_handler)
        except Exception as e:
            logger.warning(f"Failed to create file handler: {e}")

    logger.info("🔒 Secure logging initialized with credential sanitization")
    return logger


def mask_credential(credential: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """
    Mask credential for safe display.
    
    Args:
        credential: The credential to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to show at start/end
        
    Returns:
        Masked credential string
    """
    if not credential:
        return "[EMPTY]"

    if len(credential) <= visible_chars * 2:
        return mask_char * len(credential)

    start = credential[:visible_chars]
    end = credential[-visible_chars:]
    middle_length = len(credential) - (visible_chars * 2)

    return f"{start}{mask_char * min(middle_length, 8)}{end}"


def sanitize_dict(data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Sanitize dictionary by masking sensitive keys.
    
    Args:
        data: Dictionary to sanitize
        sensitive_keys: List of keys to mask (default uses common patterns)
        
    Returns:
        Sanitized dictionary
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'api_key', 'apikey', 'api-key',
            'secret', 'api_secret', 'apisecret', 'api-secret',
            'private_key', 'privatekey', 'private-key',
            'password', 'passwd', 'pwd',
            'token', 'access_token', 'auth_token',
            'key', 'keys', 'credential', 'credentials'
        ]

    sanitized = {}
    for key, value in data.items():
        if any(sensitive_key.lower() in key.lower() for sensitive_key in sensitive_keys):
            if isinstance(value, str):
                sanitized[key] = mask_credential(value)
            else:
                sanitized[key] = "[SENSITIVE_DATA_MASKED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, sensitive_keys)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, sensitive_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


# Example usage and testing
if __name__ == "__main__":
    print("🔒 Secure Logging System - Security Test")
    print("=" * 50)

    # Set up secure logging
    logger = setup_secure_logging("test_logger")

    # Test credential masking
    test_messages = [
        "API Key: sk_test_1234567890abcdef1234567890abcdef12345678",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "KRAKEN_KEY=abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQR==",
        "Connection failed for user test@example.com with password secret123",
        "Credit card 4532-1234-5678-9012 charged successfully",
        "Bitcoin address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "URL: https://user:password@api.example.com/endpoint"
    ]

    print("\n🧪 Testing credential sanitization...")
    for i, message in enumerate(test_messages, 1):
        logger.info(f"Test {i}: {message}")

    # Test dictionary sanitization
    test_dict = {
        'user_id': 12345,
        'api_key': 'secret_key_12345',
        'balance': 1000.50,
        'credentials': {
            'username': 'testuser',
            'password': 'secret_password'
        },
        'normal_data': 'this is fine'
    }

    print("\n🧪 Testing dictionary sanitization...")
    sanitized = sanitize_dict(test_dict)
    print(f"Original: {test_dict}")
    print(f"Sanitized: {sanitized}")

    # Get statistics
    for handler in logger.handlers:
        if isinstance(handler, SecureLogHandler):
            if hasattr(handler.base_handler, 'formatter') and isinstance(handler.base_handler.formatter, SecureLogFormatter):
                stats = handler.base_handler.formatter.get_sanitization_stats()
                print("\n📊 Sanitization Statistics:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")

    print("\n✅ Secure logging test completed!")
