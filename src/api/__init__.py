"""
Kraken API Client Package
========================

Comprehensive async REST API client for Kraken with full integration support.

Components:
- KrakenRestClient: Main async client with session management
- Endpoint definitions and mappings
- Pydantic response models for validation
- Custom exception classes for error handling
- Circuit breaker and rate limiting integration
- Authentication and retry logic

Usage:
    from src.api import KrakenRestClient, KrakenAPIError
    
    async with KrakenRestClient(api_key, private_key) as client:
        balance = await client.get_account_balance()
        order = await client.add_order('XBTUSD', 'buy', 'market', volume=0.001)

Features:
- Full async/await support with aiohttp
- Connection pooling and session management
- Automatic authentication with signature generation
- Rate limiting with penalty point tracking
- Circuit breaker protection against failures
- Comprehensive error handling and retry logic
- Request/response validation with Pydantic
- Performance monitoring and metrics
- Thread-safe operations for concurrent use
"""

from .endpoints import (
    KRAKEN_ENDPOINTS,
    EndpointDefinition,
    EndpointType,
    HttpMethod,
    get_endpoint_definition,
)
from .exceptions import (
    AuthenticationError,
    InsufficientFundsError,
    KrakenAPIError,
    NetworkError,
    OrderError,
    RateLimitError,
    ValidationError,
)
from .exceptions import SystemError as KrakenSystemError
from .kraken_rest_client import ClientMetrics, KrakenRestClient, RequestConfig, RetryConfig
from .response_models import (
    AssetPairResponse,
    BalanceResponse,
    CancelOrderResponse,
    KrakenResponse,
    OrderBookResponse,
    OrderResponse,
    OrderStatus,
    SystemStatusResponse,
    TickerResponse,
    TradeHistoryResponse,
)

__version__ = "1.0.0"
__author__ = "Kraken Trading Bot 2025"

# Package-level constants
DEFAULT_BASE_URL = "https://api.kraken.com"
DEFAULT_API_VERSION = "0"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3

# Quick client factory
def create_client(
    api_key: str,
    private_key: str,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    enable_rate_limiting: bool = True,
    enable_circuit_breaker: bool = True
) -> KrakenRestClient:
    """
    Quick factory function to create a configured Kraken REST client.
    
    Args:
        api_key: Kraken API key
        private_key: Kraken private key (base64 encoded)
        base_url: Base URL for Kraken API
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        enable_rate_limiting: Enable rate limiting protection
        enable_circuit_breaker: Enable circuit breaker protection
        
    Returns:
        Configured KrakenRestClient instance
    """
    return KrakenRestClient(
        api_key=api_key,
        private_key=private_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        enable_rate_limiting=enable_rate_limiting,
        enable_circuit_breaker=enable_circuit_breaker
    )

# Alias for backward compatibility
create_kraken_client = create_client

__all__ = [
    # Main client
    'KrakenRestClient',
    'create_client',
    'create_kraken_client',

    # Configuration classes
    'RequestConfig',
    'RetryConfig',
    'ClientMetrics',

    # Exceptions
    'KrakenAPIError',
    'AuthenticationError',
    'RateLimitError',
    'ValidationError',
    'NetworkError',
    'InsufficientFundsError',
    'OrderError',
    'KrakenSystemError',

    # Endpoints
    'EndpointDefinition',
    'KRAKEN_ENDPOINTS',
    'get_endpoint_definition',
    'EndpointType',
    'HttpMethod',

    # Response models
    'KrakenResponse',
    'BalanceResponse',
    'TickerResponse',
    'OrderBookResponse',
    'TradeHistoryResponse',
    'OrderResponse',
    'OrderStatus',
    'CancelOrderResponse',
    'SystemStatusResponse',
    'AssetPairResponse',

    # Constants
    'DEFAULT_BASE_URL',
    'DEFAULT_API_VERSION',
    'DEFAULT_TIMEOUT',
    'DEFAULT_MAX_RETRIES'
]
