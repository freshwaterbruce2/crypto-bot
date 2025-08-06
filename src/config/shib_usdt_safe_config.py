"""
SHIB/USDT Focused Trading Configuration
Optimized for circuit breaker recovery and rate limit compliance
"""

import json
import logging
from typing import Any

# Configure logging for circuit breaker monitoring
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler('shib_usdt_trading.log'),
        logging.StreamHandler()
    ]
)

# SHIB/USDT Trading Configuration
SHIB_USDT_TRADING_CONFIG = {
    "trading": {
        "symbol": "SHIB/USDT",
        "base_currency": "SHIB",
        "quote_currency": "USDT",
        "focus_mode": True,  # Only trade this pair
        "min_order_value": 2.50,  # Above Kraken's $2 minimum
        "max_position_size": 1000.0,  # Maximum USDT position
        "profit_target_pct": 0.75,  # 0.75% profit target
        "stop_loss_pct": 1.5,      # 1.5% stop loss
        "order_lifetime_minutes": 15,  # Orders live for 15 minutes max
        "max_open_orders": 2,      # Conservative limit
        "trading_interval_seconds": 30  # 30 seconds between trading decisions
    },

    "api_protection": {
        "tier": "pro",
        "circuit_breaker_enabled": True,
        "rate_limit_compliance": "strict",
        "api_call_spacing_seconds": 3.0,  # 3 seconds between API calls
        "max_api_calls_per_minute": 15,   # Very conservative
        "emergency_shutdown_enabled": True,
        "circuit_breaker_wait_timeout": 600,  # 10 minutes max wait
        "retry_attempts": 2,
        "exponential_backoff": True
    },

    "balance_management": {
        "check_interval_seconds": 60,  # Check balance every minute
        "use_balance_ex_endpoint": True,
        "fallback_to_standard_balance": True,
        "minimum_usdt_balance": 5.0,   # Keep $5 minimum
        "balance_safety_margin": 0.95,  # Use 95% of available balance
        "emergency_liquidation_threshold": 0.90  # Emergency if 90% loss
    },

    "error_handling": {
        "circuit_breaker_detection": True,
        "auto_recovery": True,
        "graceful_degradation": True,
        "log_all_errors": True,
        "alert_on_circuit_breaker": True,
        "max_consecutive_errors": 3,
        "error_cooldown_seconds": 300,  # 5 minutes
        "retry_strategies": {
            "circuit_breaker": "wait_full_timeout",
            "rate_limit": "exponential_backoff",
            "temporary": "linear_backoff",
            "network": "immediate_retry"
        }
    },

    "monitoring": {
        "log_level": "INFO",
        "circuit_breaker_alerts": True,
        "performance_tracking": True,
        "api_call_tracking": True,
        "profit_loss_tracking": True,
        "real_time_status": True,
        "status_report_interval": 300,  # 5 minutes
        "health_check_interval": 60     # 1 minute
    }
}

# Circuit Breaker Recovery Procedures
RECOVERY_PROCEDURES = {
    "circuit_breaker_open": {
        "immediate_actions": [
            "Stop all new API calls",
            "Cancel any pending orders (if safe)",
            "Log circuit breaker event",
            "Parse remaining timeout from error"
        ],
        "wait_actions": [
            "Wait for full timeout period",
            "Log progress every 30 seconds",
            "Monitor for early recovery signals",
            "Prepare for gradual resumption"
        ],
        "recovery_actions": [
            "Test with single balance call",
            "Verify circuit breaker is closed",
            "Resume trading with reduced frequency",
            "Gradually increase to normal operation"
        ]
    },

    "emergency_mode": {
        "triggers": [
            "More than 5 consecutive circuit breaker errors",
            "API ban or lockout detected",
            "Account security issues",
            "Excessive losses (>10% in 1 hour)"
        ],
        "actions": [
            "Stop all trading immediately",
            "Cancel all open orders",
            "Log emergency event",
            "Send alerts to monitoring",
            "Wait 15 minutes before any retry"
        ]
    }
}

# Safe Launch Sequence
SAFE_LAUNCH_SEQUENCE = [
    {
        "step": 1,
        "name": "Pre-flight System Check",
        "actions": [
            "Load Kraken API credentials",
            "Initialize circuit breaker protection",
            "Verify network connectivity",
            "Check Kraken system status"
        ]
    },
    {
        "step": 2,
        "name": "API Health Check",
        "actions": [
            "Test basic API connectivity",
            "Verify authentication",
            "Check current circuit breaker status",
            "Validate SHIB/USDT market availability"
        ]
    },
    {
        "step": 3,
        "name": "Balance and Market Check",
        "actions": [
            "Fetch account balance (with circuit breaker protection)",
            "Verify sufficient USDT for trading",
            "Check SHIB/USDT market data",
            "Validate minimum order requirements"
        ]
    },
    {
        "step": 4,
        "name": "Gradual Trading Start",
        "actions": [
            "Start with conservative settings",
            "Monitor circuit breaker status closely",
            "Make first small test order",
            "Verify all systems working correctly"
        ]
    }
]


def create_safe_config() -> dict[str, Any]:
    """Create safe configuration for SHIB/USDT trading with circuit breaker protection"""
    return {
        "trading_config": SHIB_USDT_TRADING_CONFIG,
        "recovery_procedures": RECOVERY_PROCEDURES,
        "launch_sequence": SAFE_LAUNCH_SEQUENCE,
        "timestamp": "2025-08-01T16:52:00Z",
        "version": "1.0.0-circuit-breaker-fix"
    }


def save_safe_config(filepath: str = "shib_usdt_safe_config.json"):
    """Save the safe configuration to file"""
    config = create_safe_config()
    with open(filepath, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Safe configuration saved to {filepath}")


if __name__ == "__main__":
    # Create and save the safe configuration
    config = create_safe_config()
    print("SHIB/USDT Safe Trading Configuration Created")
    print("Circuit Breaker Protection: ENABLED")
    print("Rate Limit Compliance: STRICT")
    print("Emergency Recovery: ENABLED")

    # Save configuration
    save_safe_config()
