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

from .kraken_auth import KrakenAuth
from .signature_generator import SignatureGenerator
from .credential_manager import CredentialManager, credential_manager, get_kraken_credentials
from .websocket_authentication_manager import (
    WebSocketAuthenticationManager,
    WebSocketAuthenticationError,
    TokenExpiredError,
    NonceValidationError,
    CircuitBreakerOpenError,
    websocket_auth_context,
    create_websocket_auth_manager
)
# NonceManager is deprecated - use UnifiedKrakenNonceManager from utils.unified_kraken_nonce_manager

__all__ = [
    'KrakenAuth', 
    'SignatureGenerator', 
    'CredentialManager', 
    'credential_manager', 
    'get_kraken_credentials',
    'WebSocketAuthenticationManager',
    'WebSocketAuthenticationError',
    'TokenExpiredError',
    'NonceValidationError',
    'CircuitBreakerOpenError',
    'websocket_auth_context',
    'create_websocket_auth_manager'
]

__version__ = '2025.1.0'