"""
Kraken 2025 Rate Limiting System

A comprehensive rate limiting system designed for Kraken's 2025 API specifications.
Implements token bucket algorithms, sliding window rate limiting, penalty point
tracking, and advanced queue management for high-frequency trading.

Key Features:
- Private endpoints: 15 requests per minute compliance
- Public endpoints: 20 requests per minute compliance
- Penalty point system with automatic backoff
- Per-endpoint tracking and limits
- Priority queue management
- Circuit breaker pattern integration
- Automatic recovery and cooldown mechanisms
"""

from .kraken_rate_limiter import KrakenRateLimiter2025
from .rate_limit_config import ENDPOINT_CONFIGS, RateLimitConfig
from .request_queue import RequestPriority, RequestQueue

__version__ = "2025.1.0"

__all__ = [
    "KrakenRateLimiter2025",
    "RateLimitConfig",
    "ENDPOINT_CONFIGS",
    "RequestQueue",
    "RequestPriority",
]
