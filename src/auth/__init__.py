"""
Kraken API Authentication System for 2025
========================================

Modern, secure authentication system for Kraken API with:
- 64-bit microsecond precision nonces
- Thread-safe nonce management with persistence
- HMAC-SHA512 signature generation per Kraken specs
- Support for multiple API keys
- Automatic nonce recovery and validation
- Production-ready error handling and logging
- Enhanced WebSocket authentication with proactive token management

Components:
- KrakenAuth: Main authentication handler for REST API
- WebSocketAuthenticationManager: Enhanced WebSocket authentication with token management
- SignatureGenerator: HMAC-SHA512 signature generation
- CredentialManager: Secure credential storage and management
"""

from .credential_manager import (
    CredentialManager,
    credential_manager,
    get_kraken_credentials,
    get_kraken_rest_credentials,
    get_kraken_websocket_credentials,
)
from .kraken_auth import KrakenAuth
from .signature_generator import SignatureGenerator
from .websocket_authentication_manager import (
    CircuitBreakerOpenError,
    NonceValidationError,
    TokenExpiredError,
    WebSocketAuthenticationError,
    WebSocketAuthenticationManager,
    create_websocket_auth_manager,
    websocket_auth_context,
)

# NonceManager is deprecated - use ConsolidatedNonceManager from utils.consolidated_nonce_manager

__all__ = [
    "KrakenAuth",
    "SignatureGenerator",
    "CredentialManager",
    "credential_manager",
    "get_kraken_credentials",
    "get_kraken_rest_credentials",
    "get_kraken_websocket_credentials",
    "WebSocketAuthenticationManager",
    "WebSocketAuthenticationError",
    "TokenExpiredError",
    "NonceValidationError",
    "CircuitBreakerOpenError",
    "websocket_auth_context",
    "create_websocket_auth_manager",
]

__version__ = "2025.1.0"
