"""
Circuit Breaker Pattern System for Trading Bot
=============================================

Comprehensive circuit breaker implementation with health monitoring,
failure detection, and integration with authentication and rate limiting systems.

Features:
- Three-state machine: CLOSED → OPEN → HALF-OPEN
- Configurable failure thresholds and timeouts
- Auto-recovery with exponential backoff
- Health monitoring and metrics collection
- Thread-safe operations for concurrent trading
- Persistent state across restarts
- Integration hooks for API clients

Usage:
    from src.circuit_breaker import CircuitBreakerManager, CircuitBreakerConfig
    
    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        health_check_interval=10.0
    )
    
    cb_manager = CircuitBreakerManager(config)
    await cb_manager.start()
    
    # Use circuit breaker for API calls
    async with cb_manager.get_breaker('kraken_api') as breaker:
        result = await breaker.execute(api_call, *args, **kwargs)
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitBreakerState,
    CircuitBreakerConfig,
    CircuitBreakerError,
    BreakerOpenError,
    BreakerTimeoutError
)

from .health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthMetrics,
    ServiceHealth,
    HealthCheckResult
)

from .failure_detector import (
    FailureDetector,
    FailurePattern,
    FailureAnalysis,
    FailureCategory,
    FailureClassifier
)

__all__ = [
    # Core circuit breaker
    'CircuitBreaker',
    'CircuitBreakerManager',
    'CircuitBreakerState',
    'CircuitBreakerConfig',
    'CircuitBreakerError',
    'BreakerOpenError',
    'BreakerTimeoutError',
    
    # Health monitoring
    'HealthMonitor',
    'HealthStatus',
    'HealthMetrics',
    'ServiceHealth',
    'HealthCheckResult',
    
    # Failure detection
    'FailureDetector',
    'FailurePattern',
    'FailureAnalysis',
    'FailureCategory',
    'FailureClassifier'
]

__version__ = '1.0.0'
__author__ = 'Trading Bot Team'
__description__ = 'Robust circuit breaker pattern system for trading bot operations'
