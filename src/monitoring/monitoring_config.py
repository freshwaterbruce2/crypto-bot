"""
Production Monitoring Configuration
==================================

Configuration management for the production monitoring system.
Provides default configurations, validation, and easy setup.
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from .production_monitor import AlertConfig, MetricThresholds

logger = logging.getLogger(__name__)


@dataclass
class DashboardConfig:
    """Dashboard server configuration"""
    enabled: bool = True
    port: int = 8000
    host: str = "127.0.0.1"
    auto_open_browser: bool = False
    enable_https: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None


@dataclass
class MonitoringConfig:
    """Complete monitoring system configuration"""
    # Health check intervals
    health_check_interval: float = 300.0  # 5 minutes
    metrics_collection_interval: float = 30.0  # 30 seconds

    # Data retention
    metric_history_hours: int = 24
    alert_history_hours: int = 48

    # Logging
    enable_monitoring_logs: bool = True
    log_level: str = "INFO"
    log_file_path: Optional[str] = None

    # Component monitoring
    monitor_balance_manager: bool = True
    monitor_websocket: bool = True
    monitor_nonce_system: bool = True
    monitor_trading_performance: bool = True
    monitor_system_resources: bool = True

    # Emergency controls
    enable_emergency_shutdown: bool = True
    emergency_conditions: list[str] = None

    # Integration settings
    non_intrusive_mode: bool = True
    fallback_on_errors: bool = True

    def __post_init__(self):
        if self.emergency_conditions is None:
            self.emergency_conditions = [
                "memory_usage_critical",
                "api_error_rate_critical",
                "daily_loss_limit_exceeded"
            ]


class ConfigurationManager:
    """Manages monitoring configuration with validation and defaults"""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file
        self._config_cache = {}

    def load_config(self, config_file: Optional[Path] = None) -> dict[str, Any]:
        """Load configuration from file or return defaults"""
        config_path = config_file or self.config_file

        if config_path and config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                logger.info(f"Loaded monitoring config from {config_path}")
                return self._validate_and_merge_config(config)
            except Exception as e:
                logger.error(f"Error loading config from {config_path}: {e}")
                logger.info("Using default configuration")

        return self.get_default_config()

    def save_config(self, config: dict[str, Any], config_file: Optional[Path] = None):
        """Save configuration to file"""
        config_path = config_file or self.config_file

        if not config_path:
            raise ValueError("No config file path specified")

        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Saved monitoring config to {config_path}")

        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")
            raise

    def get_default_config(self) -> dict[str, Any]:
        """Get default monitoring configuration"""
        return {
            'monitoring': asdict(MonitoringConfig()),
            'thresholds': asdict(MetricThresholds()),
            'alerts': asdict(AlertConfig()),
            'dashboard': asdict(DashboardConfig())
        }

    def get_production_config(self) -> dict[str, Any]:
        """Get production-optimized configuration"""
        config = self.get_default_config()

        # Production-specific thresholds
        config['thresholds'].update({
            'memory_usage_mb': 400.0,
            'trading_success_rate_percent': 90.0,
            'daily_pnl_loss_limit': -25.0,
            'api_error_rate_percent': 0.05
        })

        # Production alert settings
        config['alerts'].update({
            'console_alerts': False,
            'log_alerts': True,
            'email_notifications': True,
            'webhook_notifications': True
        })

        # Production monitoring settings
        config['monitoring'].update({
            'health_check_interval': 180.0,  # 3 minutes
            'metrics_collection_interval': 15.0,  # 15 seconds
            'enable_emergency_shutdown': True
        })

        return config

    def get_development_config(self) -> dict[str, Any]:
        """Get development-optimized configuration"""
        config = self.get_default_config()

        # Development-specific thresholds (more lenient)
        config['thresholds'].update({
            'memory_usage_mb': 600.0,
            'trading_success_rate_percent': 75.0,
            'daily_pnl_loss_limit': -100.0,
            'api_error_rate_percent': 0.5
        })

        # Development alert settings
        config['alerts'].update({
            'console_alerts': True,
            'log_alerts': True,
            'email_notifications': False,
            'webhook_notifications': False
        })

        # Development monitoring settings
        config['monitoring'].update({
            'health_check_interval': 600.0,  # 10 minutes
            'metrics_collection_interval': 60.0,  # 1 minute
            'enable_emergency_shutdown': False
        })

        return config

    def _validate_and_merge_config(self, user_config: dict[str, Any]) -> dict[str, Any]:
        """Validate user config and merge with defaults"""
        default_config = self.get_default_config()

        # Deep merge configuration
        merged_config = self._deep_merge(default_config, user_config)

        # Validate configuration
        self._validate_config(merged_config)

        return merged_config

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_config(self, config: dict[str, Any]):
        """Validate configuration values"""
        try:
            # Validate monitoring config
            monitoring = config.get('monitoring', {})
            if monitoring.get('health_check_interval', 0) < 30:
                logger.warning("Health check interval less than 30 seconds, using 30")
                monitoring['health_check_interval'] = 30.0

            # Validate thresholds
            thresholds = config.get('thresholds', {})
            if thresholds.get('memory_usage_mb', 0) < 100:
                logger.warning("Memory threshold too low, using 100MB minimum")
                thresholds['memory_usage_mb'] = 100.0

            # Validate dashboard config
            dashboard = config.get('dashboard', {})
            port = dashboard.get('port', 8000)
            if not (1024 <= port <= 65535):
                logger.warning(f"Invalid dashboard port {port}, using 8000")
                dashboard['port'] = 8000

        except Exception as e:
            logger.error(f"Config validation error: {e}")
            raise


def create_monitoring_config_objects(config_dict: dict[str, Any]) -> tuple:
    """
    Create monitoring object instances from configuration dictionary

    Returns:
        tuple: (MonitoringConfig, MetricThresholds, AlertConfig, DashboardConfig)
    """
    monitoring_config = MonitoringConfig(**config_dict.get('monitoring', {}))
    thresholds = MetricThresholds(**config_dict.get('thresholds', {}))
    alert_config = AlertConfig(**config_dict.get('alerts', {}))
    dashboard_config = DashboardConfig(**config_dict.get('dashboard', {}))

    return monitoring_config, thresholds, alert_config, dashboard_config


def setup_monitoring_from_config(config_path: Optional[Path] = None,
                                config_type: str = "default") -> dict[str, Any]:
    """
    Setup monitoring configuration from file or defaults

    Args:
        config_path: Path to configuration file
        config_type: Type of config - "default", "production", "development"

    Returns:
        Complete configuration dictionary
    """
    manager = ConfigurationManager(config_path)

    if config_type == "production":
        config = manager.get_production_config()
    elif config_type == "development":
        config = manager.get_development_config()
    elif config_path and config_path.exists():
        config = manager.load_config()
    else:
        config = manager.get_default_config()

    return config


# Pre-defined configurations for different environments
CONFIGS = {
    'default': {
        'monitoring': {
            'health_check_interval': 300.0,
            'metrics_collection_interval': 30.0,
            'enable_emergency_shutdown': True
        },
        'thresholds': {
            'memory_usage_mb': 500.0,
            'log_file_size_mb': 8.0,
            'nonce_generation_rate': 1000.0,
            'websocket_reconnects_per_hour': 5,
            'api_error_rate_percent': 0.1,
            'trading_success_rate_percent': 85.0,
            'daily_pnl_loss_limit': -50.0
        },
        'alerts': {
            'enabled': True,
            'console_alerts': True,
            'log_alerts': True
        },
        'dashboard': {
            'enabled': True,
            'port': 8000
        }
    },

    'production': {
        'monitoring': {
            'health_check_interval': 180.0,
            'metrics_collection_interval': 15.0,
            'enable_emergency_shutdown': True
        },
        'thresholds': {
            'memory_usage_mb': 400.0,
            'api_error_rate_percent': 0.05,
            'trading_success_rate_percent': 90.0,
            'daily_pnl_loss_limit': -25.0
        },
        'alerts': {
            'enabled': True,
            'console_alerts': False,
            'log_alerts': True,
            'email_notifications': True
        },
        'dashboard': {
            'enabled': True,
            'port': 8000
        }
    },

    'development': {
        'monitoring': {
            'health_check_interval': 600.0,
            'metrics_collection_interval': 60.0,
            'enable_emergency_shutdown': False
        },
        'thresholds': {
            'memory_usage_mb': 600.0,
            'trading_success_rate_percent': 75.0,
            'daily_pnl_loss_limit': -100.0,
            'api_error_rate_percent': 0.5
        },
        'alerts': {
            'enabled': True,
            'console_alerts': True,
            'log_alerts': True,
            'email_notifications': False
        },
        'dashboard': {
            'enabled': True,
            'port': 8001
        }
    },

    'minimal': {
        'monitoring': {
            'health_check_interval': 900.0,  # 15 minutes
            'metrics_collection_interval': 120.0,  # 2 minutes
            'enable_emergency_shutdown': False
        },
        'thresholds': {
            'memory_usage_mb': 800.0,
            'daily_pnl_loss_limit': -200.0
        },
        'alerts': {
            'enabled': False
        },
        'dashboard': {
            'enabled': False
        }
    }
}


def get_config_by_name(config_name: str) -> dict[str, Any]:
    """Get predefined configuration by name"""
    if config_name not in CONFIGS:
        raise ValueError(f"Unknown config name: {config_name}. Available: {list(CONFIGS.keys())}")

    base_config = ConfigurationManager().get_default_config()
    named_config = CONFIGS[config_name]

    # Deep merge
    manager = ConfigurationManager()
    return manager._deep_merge(base_config, named_config)


# Example usage and testing
if __name__ == "__main__":

    def test_configs():
        """Test configuration loading and validation"""
        manager = ConfigurationManager()

        # Test default config
        default = manager.get_default_config()
        print("Default config keys:", list(default.keys()))

        # Test production config
        production = manager.get_production_config()
        print("Production memory threshold:", production['thresholds']['memory_usage_mb'])

        # Test development config
        development = manager.get_development_config()
        print("Development health check interval:", development['monitoring']['health_check_interval'])

        # Test named configs
        for name in CONFIGS.keys():
            config = get_config_by_name(name)
            print(f"{name} config dashboard enabled:", config['dashboard']['enabled'])

    test_configs()
