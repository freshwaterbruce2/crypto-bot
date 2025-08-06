"""
REST API Module for Crypto Trading Bot
=====================================

Strategic REST API implementation designed to work alongside WebSocket V2
to minimize nonce conflicts while providing essential fallback functionality.

Components:
- StrategicRestClient: Minimalist REST client with smart batching
- RestDataValidator: Cross-validation between REST and WebSocket data
- RestFallbackManager: Emergency fallback and service degradation management

Usage:
    from src.rest import StrategicRestClient, RestDataValidator, RestFallbackManager

    # Initialize components
    rest_client = StrategicRestClient(api_key, private_key)
    validator = RestDataValidator(rest_client, websocket_manager)
    fallback_manager = RestFallbackManager(rest_client, websocket_manager)
"""

from .rest_data_validator import RestDataValidator
from .rest_fallback_manager import OperationPriority, RestFallbackManager, ServiceLevel
from .strategic_rest_client import RestWebSocketCoordinator, StrategicRestClient

__all__ = [
    'StrategicRestClient',
    'RestWebSocketCoordinator',
    'RestDataValidator',
    'RestFallbackManager',
    'ServiceLevel',
    'OperationPriority'
]
