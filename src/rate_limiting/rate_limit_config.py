"""
Rate Limit Configuration for Kraken 2025 API Specifications

This module contains all rate limiting configurations based on Kraken's 2025
API documentation. It includes endpoint mappings, tier configurations,
penalty point calculations, and backoff strategies.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

logger = logging.getLogger(__name__)


class EndpointType(Enum):
    """API endpoint types for rate limiting."""
    PRIVATE = "private"
    PUBLIC = "public"
    WEBSOCKET = "websocket"


class AccountTier(Enum):
    """Kraken account tiers with different rate limits."""
    STARTER = "starter"
    INTERMEDIATE = "intermediate"
    PRO = "pro"


@dataclass
class RateLimitConfig:
    """Rate limit configuration for specific account tiers and endpoint types."""

    # Basic rate limits (requests per minute)
    private_limit: int = 15  # 2025 spec: 15 requests per minute for private endpoints
    public_limit: int = 20   # 2025 spec: 20 requests per minute for public endpoints

    # Penalty point system
    max_penalty_points: int = 180  # Maximum before rate limiting kicks in
    penalty_decay_rate: float = 3.75  # Points per second decay rate

    # Request weights
    default_weight: int = 1
    heavy_weight: int = 2

    # Backoff configuration
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 300.0  # 5 minutes maximum
    backoff_multiplier: float = 2.0

    # Queue management
    max_queue_size: int = 1000
    priority_queue_ratio: float = 0.3  # 30% for high priority requests

    # Circuit breaker
    circuit_breaker_threshold: float = 0.9  # Open at 90% capacity
    circuit_breaker_recovery_time: float = 30.0  # 30 seconds


# Account tier configurations based on 2025 Kraken specifications
TIER_CONFIGS = {
    AccountTier.STARTER: RateLimitConfig(
        private_limit=15,
        public_limit=20,
        max_penalty_points=60,  # Starter tier limit
        penalty_decay_rate=0.33,  # 0.33 points per second
        base_backoff_seconds=2.0,
        max_backoff_seconds=120.0
    ),

    AccountTier.INTERMEDIATE: RateLimitConfig(
        private_limit=15,
        public_limit=20,
        max_penalty_points=125,  # Intermediate tier limit
        penalty_decay_rate=2.34,  # 2.34 points per second
        base_backoff_seconds=1.5,
        max_backoff_seconds=180.0
    ),

    AccountTier.PRO: RateLimitConfig(
        private_limit=15,
        public_limit=20,
        max_penalty_points=180,  # Pro tier limit
        penalty_decay_rate=3.75,  # 3.75 points per second
        base_backoff_seconds=1.0,
        max_backoff_seconds=300.0
    )
}


@dataclass
class EndpointConfig:
    """Configuration for individual API endpoints."""

    name: str
    endpoint_type: EndpointType
    weight: int = 1
    penalty_points: int = 1
    max_requests_per_minute: Optional[int] = None
    requires_auth: bool = False

    # Special handling flags
    is_trading_endpoint: bool = False
    supports_batch: bool = False
    has_age_penalty: bool = False  # For order modifications


# Kraken API endpoint configurations (2025 specifications)
ENDPOINT_CONFIGS: dict[str, EndpointConfig] = {

    # ===== PUBLIC ENDPOINTS =====
    "ServerTime": EndpointConfig(
        name="ServerTime",
        endpoint_type=EndpointType.PUBLIC,
        weight=1,
        penalty_points=0,  # No penalty for public endpoints
        max_requests_per_minute=20
    ),

    "SystemStatus": EndpointConfig(
        name="SystemStatus",
        endpoint_type=EndpointType.PUBLIC,
        weight=1,
        penalty_points=0,
        max_requests_per_minute=20
    ),

    "AssetPairs": EndpointConfig(
        name="AssetPairs",
        endpoint_type=EndpointType.PUBLIC,
        weight=1,
        penalty_points=0,
        max_requests_per_minute=20
    ),

    "Ticker": EndpointConfig(
        name="Ticker",
        endpoint_type=EndpointType.PUBLIC,
        weight=1,
        penalty_points=0,
        max_requests_per_minute=20
    ),

    "OHLC": EndpointConfig(
        name="OHLC",
        endpoint_type=EndpointType.PUBLIC,
        weight=1,
        penalty_points=0,
        max_requests_per_minute=20
    ),

    "Depth": EndpointConfig(
        name="Depth",
        endpoint_type=EndpointType.PUBLIC,
        weight=2,  # Heavier endpoint
        penalty_points=0,
        max_requests_per_minute=10  # Lower limit due to weight
    ),

    "Trades": EndpointConfig(
        name="Trades",
        endpoint_type=EndpointType.PUBLIC,
        weight=1,
        penalty_points=0,
        max_requests_per_minute=20
    ),

    "Spread": EndpointConfig(
        name="Spread",
        endpoint_type=EndpointType.PUBLIC,
        weight=1,
        penalty_points=0,
        max_requests_per_minute=20
    ),

    # ===== PRIVATE ENDPOINTS =====
    "Balance": EndpointConfig(
        name="Balance",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    "TradeBalance": EndpointConfig(
        name="TradeBalance",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    "OpenOrders": EndpointConfig(
        name="OpenOrders",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    "ClosedOrders": EndpointConfig(
        name="ClosedOrders",
        endpoint_type=EndpointType.PRIVATE,
        weight=2,
        penalty_points=2,
        max_requests_per_minute=10,
        requires_auth=True
    ),

    "QueryOrders": EndpointConfig(
        name="QueryOrders",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    "TradesHistory": EndpointConfig(
        name="TradesHistory",
        endpoint_type=EndpointType.PRIVATE,
        weight=2,
        penalty_points=2,
        max_requests_per_minute=10,
        requires_auth=True
    ),

    "QueryTrades": EndpointConfig(
        name="QueryTrades",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    "OpenPositions": EndpointConfig(
        name="OpenPositions",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    "Ledgers": EndpointConfig(
        name="Ledgers",
        endpoint_type=EndpointType.PRIVATE,
        weight=2,
        penalty_points=2,
        max_requests_per_minute=10,
        requires_auth=True
    ),

    "QueryLedgers": EndpointConfig(
        name="QueryLedgers",
        endpoint_type=EndpointType.PRIVATE,
        weight=2,
        penalty_points=2,
        max_requests_per_minute=10,
        requires_auth=True
    ),

    "TradeVolume": EndpointConfig(
        name="TradeVolume",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    "ExportStatus": EndpointConfig(
        name="ExportStatus",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    "RetrieveExport": EndpointConfig(
        name="RetrieveExport",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    "RemoveExport": EndpointConfig(
        name="RemoveExport",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True
    ),

    # ===== TRADING ENDPOINTS =====
    "AddOrder": EndpointConfig(
        name="AddOrder",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,  # Base penalty, can increase with order type
        max_requests_per_minute=15,
        requires_auth=True,
        is_trading_endpoint=True
    ),

    "AmendOrder": EndpointConfig(
        name="AmendOrder",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,  # Base penalty + age penalty
        max_requests_per_minute=15,
        requires_auth=True,
        is_trading_endpoint=True,
        has_age_penalty=True
    ),

    "EditOrder": EndpointConfig(
        name="EditOrder",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,  # Base penalty + age penalty
        max_requests_per_minute=15,
        requires_auth=True,
        is_trading_endpoint=True,
        has_age_penalty=True
    ),

    "CancelOrder": EndpointConfig(
        name="CancelOrder",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=0,  # Only age penalty applies
        max_requests_per_minute=15,
        requires_auth=True,
        is_trading_endpoint=True,
        has_age_penalty=True
    ),

    "CancelAll": EndpointConfig(
        name="CancelAll",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True,
        is_trading_endpoint=True
    ),

    "CancelAllOrdersAfter": EndpointConfig(
        name="CancelAllOrdersAfter",
        endpoint_type=EndpointType.PRIVATE,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=15,
        requires_auth=True,
        is_trading_endpoint=True
    ),

    # ===== WEBSOCKET ENDPOINTS =====
    "WS-Subscribe": EndpointConfig(
        name="WS-Subscribe",
        endpoint_type=EndpointType.WEBSOCKET,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=60,  # Higher limit for WebSocket
        requires_auth=False
    ),

    "WS-Unsubscribe": EndpointConfig(
        name="WS-Unsubscribe",
        endpoint_type=EndpointType.WEBSOCKET,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=60,
        requires_auth=False
    ),

    "WS-AddOrder": EndpointConfig(
        name="WS-AddOrder",
        endpoint_type=EndpointType.WEBSOCKET,
        weight=1,
        penalty_points=1,
        max_requests_per_minute=30,
        requires_auth=True,
        is_trading_endpoint=True
    ),

    "WS-CancelOrder": EndpointConfig(
        name="WS-CancelOrder",
        endpoint_type=EndpointType.WEBSOCKET,
        weight=1,
        penalty_points=0,  # Age penalty applies
        max_requests_per_minute=30,
        requires_auth=True,
        is_trading_endpoint=True,
        has_age_penalty=True
    ),

    "WS-EditOrder": EndpointConfig(
        name="WS-EditOrder",
        endpoint_type=EndpointType.WEBSOCKET,
        weight=1,
        penalty_points=1,  # Base + age penalty
        max_requests_per_minute=30,
        requires_auth=True,
        is_trading_endpoint=True,
        has_age_penalty=True
    )
}


def calculate_age_penalty(endpoint_name: str, order_age_seconds: float) -> int:
    """
    Calculate penalty points based on order age for modification/cancellation.

    Based on Kraken 2025 specifications:
    - AmendOrder: +3/+2/+1 penalty for <5s/<10s/<15s
    - EditOrder: +6/+5/+4/+2/+1 penalty for <5s/<10s/<15s/<45s/<90s
    - CancelOrder: +8/+6/+5/+4/+2/+1 penalty for <5s/<10s/<15s/<45s/<90s/<300s

    Args:
        endpoint_name: Name of the endpoint
        order_age_seconds: Age of the order in seconds

    Returns:
        Additional penalty points based on age
    """
    if endpoint_name in ["AmendOrder", "WS-AmendOrder"]:
        if order_age_seconds < 5:
            return 3
        elif order_age_seconds < 10:
            return 2
        elif order_age_seconds < 15:
            return 1
        else:
            return 0

    elif endpoint_name in ["EditOrder", "WS-EditOrder"]:
        if order_age_seconds < 5:
            return 6
        elif order_age_seconds < 10:
            return 5
        elif order_age_seconds < 15:
            return 4
        elif order_age_seconds < 45:
            return 2
        elif order_age_seconds < 90:
            return 1
        else:
            return 0

    elif endpoint_name in ["CancelOrder", "WS-CancelOrder"]:
        if order_age_seconds < 5:
            return 8
        elif order_age_seconds < 10:
            return 6
        elif order_age_seconds < 15:
            return 5
        elif order_age_seconds < 45:
            return 4
        elif order_age_seconds < 90:
            return 2
        elif order_age_seconds < 300:
            return 1
        else:
            return 0

    return 0


def get_endpoint_config(endpoint_name: str) -> EndpointConfig:
    """
    Get configuration for a specific endpoint.

    Args:
        endpoint_name: Name of the endpoint

    Returns:
        EndpointConfig for the endpoint

    Raises:
        KeyError: If endpoint is not configured
    """
    config = ENDPOINT_CONFIGS.get(endpoint_name)
    if config is None:
        logger.warning(f"Unknown endpoint '{endpoint_name}', using default config")
        return EndpointConfig(
            name=endpoint_name,
            endpoint_type=EndpointType.PRIVATE,  # Default to private for safety
            weight=1,
            penalty_points=1,
            max_requests_per_minute=15,
            requires_auth=True
        )
    return config


def get_tier_config(tier: Union[AccountTier, str]) -> RateLimitConfig:
    """
    Get rate limit configuration for account tier.

    Args:
        tier: Account tier (enum or string)

    Returns:
        RateLimitConfig for the tier
    """
    if isinstance(tier, str):
        tier = AccountTier(tier.lower())

    config = TIER_CONFIGS.get(tier)
    if config is None:
        logger.warning(f"Unknown tier '{tier}', using intermediate config")
        return TIER_CONFIGS[AccountTier.INTERMEDIATE]

    return config


def calculate_backoff_delay(attempt: int, base_delay: float, multiplier: float, max_delay: float) -> float:
    """
    Calculate exponential backoff delay.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        multiplier: Exponential multiplier
        max_delay: Maximum delay in seconds

    Returns:
        Delay time in seconds
    """
    delay = base_delay * (multiplier ** attempt)
    return min(delay, max_delay)


def get_endpoints_by_type(endpoint_type: EndpointType) -> list[str]:
    """
    Get all endpoint names of a specific type.

    Args:
        endpoint_type: Type of endpoint to filter by

    Returns:
        List of endpoint names
    """
    return [
        name for name, config in ENDPOINT_CONFIGS.items()
        if config.endpoint_type == endpoint_type
    ]


def is_trading_endpoint(endpoint_name: str) -> bool:
    """
    Check if endpoint is a trading endpoint.

    Args:
        endpoint_name: Name of the endpoint

    Returns:
        True if endpoint is for trading operations
    """
    config = ENDPOINT_CONFIGS.get(endpoint_name)
    return config.is_trading_endpoint if config else False


def validate_rate_limits() -> dict[str, list[str]]:
    """
    Validate rate limit configurations for consistency.

    Returns:
        Dictionary with validation results and any warnings
    """
    warnings = []
    errors = []

    # Check for duplicate endpoint names
    names = list(ENDPOINT_CONFIGS.keys())
    if len(names) != len(set(names)):
        errors.append("Duplicate endpoint names found")

    # Validate rate limits don't exceed Kraken specifications
    for name, config in ENDPOINT_CONFIGS.items():
        if config.endpoint_type == EndpointType.PRIVATE:
            if config.max_requests_per_minute and config.max_requests_per_minute > 15:
                warnings.append(f"{name}: Private endpoint exceeds 15 RPM limit")
        elif config.endpoint_type == EndpointType.PUBLIC:
            if config.max_requests_per_minute and config.max_requests_per_minute > 20:
                warnings.append(f"{name}: Public endpoint exceeds 20 RPM limit")

    # Check penalty point configurations
    for tier, config in TIER_CONFIGS.items():
        if config.penalty_decay_rate <= 0:
            errors.append(f"{tier.value}: Invalid penalty decay rate")
        if config.max_penalty_points <= 0:
            errors.append(f"{tier.value}: Invalid max penalty points")

    return {
        'warnings': warnings,
        'errors': errors,
        'valid': len(errors) == 0
    }


# Validate configurations at import time
validation_result = validate_rate_limits()
if not validation_result['valid']:
    logger.error(f"Rate limit configuration validation failed: {validation_result['errors']}")
elif validation_result['warnings']:
    logger.warning(f"Rate limit configuration warnings: {validation_result['warnings']}")
else:
    logger.info("Rate limit configurations validated successfully")
