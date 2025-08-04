"""
Centralized Configuration Manager

Manages all system configurations with validation, environment support, and hot reloading.
"""

import json
import os
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from pathlib import Path
import asyncio
from datetime import datetime
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


@dataclass
class ConfigSection:
    """Configuration section with validation and defaults"""
    name: str
    data: Dict[str, Any]
    validators: List[Callable] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> bool:
        """Validate configuration section"""
        for validator in self.validators:
            if not validator(self.data):
                return False
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback to defaults"""
        return self.data.get(key, self.defaults.get(key, default))


class ConfigFileHandler(FileSystemEventHandler):
    """Handle configuration file changes"""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            logger.info(f"Configuration file modified: {event.src_path}")
            asyncio.create_task(self.config_manager.reload_config(event.src_path))


class ConfigManager:
    """Centralized configuration management system"""
    
    def __init__(self, config_path: str = None):
        # Handle both file paths and directory paths
        if config_path and config_path.endswith('.json'):
            # It's a file path
            self.config_file = Path(config_path)
            self.config_dir = self.config_file.parent
        else:
            # It's a directory path
            self.config_dir = Path(config_path or os.getenv('CONFIG_DIR', './config'))
            self.config_file = self.config_dir / 'config.json'
        
        # Create directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
        self.sections: Dict[str, ConfigSection] = {}
        self.observers: List[Callable] = []
        self.file_observer: Optional[Observer] = None
        self._lock = asyncio.Lock()
        
        # Default configuration structure
        self.default_structure = {
            'system': {
                'debug': False,
                'log_level': 'INFO',
                'timezone': 'UTC',
                'health_check_interval': 60
            },
            'exchange': {
                'name': 'kraken',
                'api_version': 'v2',
                'timeout': 30,
                'max_retries': 3
            },
            'websocket': {
                'ping_interval': 30,
                'reconnect_delay': 5,
                'max_reconnect_attempts': 10,
                'heartbeat_timeout': 60
            },
            'rate_limiting': {
                'tier': 'pro',
                'burst_multiplier': 1.5,
                'cooldown_period': 60,
                'adaptive_mode': True
            },
            'circuit_breaker': {
                'failure_threshold': 5,
                'recovery_timeout': 60,
                'half_open_max_calls': 3,
                'monitoring_period': 300
            },
            'trading': {
                'max_position_size': 100.0,
                'min_position_size': 10.0,
                'profit_target': 0.005,
                'stop_loss': 0.02,
                'fee_rate': 0.0016
            },
            'portfolio': {
                'max_open_positions': 10,
                'reserve_balance': 50.0,
                'rebalance_threshold': 0.1,
                'risk_per_trade': 0.02
            },
            'monitoring': {
                'metrics_interval': 10,
                'alert_thresholds': {
                    'cpu_percent': 80,
                    'memory_percent': 85,
                    'error_rate': 0.05
                }
            }
        }
        
    async def initialize(self):
        """Initialize configuration manager"""
        logger.info("Initializing configuration manager")
        
        # Load all configuration files
        await self._load_configurations()
        
        # Start file watcher for hot reloading
        self._start_file_watcher()
        
        # Validate all configurations
        self._validate_all()
        
        logger.info("Configuration manager initialized")
        
    async def shutdown(self):
        """Shutdown configuration manager"""
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            
    async def _load_configurations(self):
        """Load all configuration files"""
        async with self._lock:
            # Load main config.json
            main_config_path = self.config_dir.parent / 'config.json'
            if main_config_path.exists():
                await self._load_config_file(main_config_path, 'main')
                
            # Load section-specific configs
            for config_file in self.config_dir.glob('*.json'):
                section_name = config_file.stem
                await self._load_config_file(config_file, section_name)
                
            # Apply environment overrides
            self._apply_env_overrides()
            
            # Fill in missing sections with defaults
            for section, defaults in self.default_structure.items():
                if section not in self.sections:
                    self.sections[section] = ConfigSection(
                        name=section,
                        data=defaults.copy(),
                        defaults=defaults
                    )
                    
    async def _load_config_file(self, file_path: Path, section_name: str):
        """Load a configuration file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Handle nested sections in main config
            if section_name == 'main':
                for key, value in data.items():
                    if isinstance(value, dict):
                        self.sections[key] = ConfigSection(
                            name=key,
                            data=value,
                            defaults=self.default_structure.get(key, {})
                        )
            else:
                self.sections[section_name] = ConfigSection(
                    name=section_name,
                    data=data,
                    defaults=self.default_structure.get(section_name, {})
                )
                
            logger.info(f"Loaded configuration: {section_name} from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load config {file_path}: {e}")
            
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # Format: TRADINGBOT_SECTION_KEY=value
        prefix = 'TRADINGBOT_'
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split('_', 1)
                if len(parts) == 2:
                    section, config_key = parts
                    if section in self.sections:
                        # Convert value types
                        try:
                            if value.lower() in ('true', 'false'):
                                value = value.lower() == 'true'
                            elif value.isdigit():
                                value = int(value)
                            elif '.' in value and value.replace('.', '').isdigit():
                                value = float(value)
                        except:
                            pass
                            
                        self.sections[section].data[config_key] = value
                        logger.info(f"Applied env override: {section}.{config_key} = {value}")
                        
    def _start_file_watcher(self):
        """Start watching configuration files for changes"""
        try:
            self.file_observer = Observer()
            handler = ConfigFileHandler(self)
            
            # Watch main config
            self.file_observer.schedule(handler, str(self.config_dir.parent), recursive=False)
            
            # Watch config directory
            self.file_observer.schedule(handler, str(self.config_dir), recursive=False)
            
            self.file_observer.start()
            logger.info("Configuration file watcher started")
            
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            
    def _validate_all(self):
        """Validate all configuration sections"""
        for section in self.sections.values():
            if not section.validate():
                logger.warning(f"Configuration validation failed for section: {section.name}")
                
    async def reload_config(self, file_path: str = None):
        """Reload configuration from files"""
        logger.info(f"Reloading configuration{f' from {file_path}' if file_path else ''}")
        
        if file_path:
            path = Path(file_path)
            if path.name == 'config.json':
                await self._load_config_file(path, 'main')
            else:
                section_name = path.stem
                await self._load_config_file(path, section_name)
        else:
            await self._load_configurations()
            
        # Notify observers
        await self._notify_observers()
        
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by path (e.g., 'trading.max_position_size')"""
        parts = path.split('.')
        if not parts:
            return default
            
        section_name = parts[0]
        if section_name not in self.sections:
            return default
            
        if len(parts) == 1:
            return self.sections[section_name].data
            
        # Navigate nested structure
        value = self.sections[section_name].data
        for key in parts[1:]:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
                
        return value
        
    def set(self, path: str, value: Any):
        """Set configuration value by path"""
        parts = path.split('.')
        if not parts:
            return
            
        section_name = parts[0]
        if section_name not in self.sections:
            self.sections[section_name] = ConfigSection(name=section_name, data={})
            
        if len(parts) == 1:
            self.sections[section_name].data = value
        else:
            # Navigate to parent
            current = self.sections[section_name].data
            for key in parts[1:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
                
            # Set the value
            current[parts[-1]] = value
            
        # Mark as updated
        self.sections[section_name].last_updated = datetime.now()
        
        # Notify observers
        asyncio.create_task(self._notify_observers())
        
    def get_section(self, name: str) -> Optional[ConfigSection]:
        """Get entire configuration section"""
        return self.sections.get(name)
        
    def add_validator(self, section: str, validator: Callable):
        """Add validator for configuration section"""
        if section in self.sections:
            self.sections[section].validators.append(validator)
            
    def subscribe(self, callback: Callable):
        """Subscribe to configuration changes"""
        self.observers.append(callback)
        
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from configuration changes"""
        if callback in self.observers:
            self.observers.remove(callback)
            
    async def _notify_observers(self):
        """Notify all observers of configuration changes"""
        for callback in self.observers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self)
                else:
                    callback(self)
            except Exception as e:
                logger.error(f"Error notifying config observer: {e}")
                
    def export_config(self, section: str = None) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        if section:
            return self.sections[section].data if section in self.sections else {}
            
        return {name: section.data for name, section in self.sections.items()}
        
    async def save_config(self, section: str = None):
        """Save configuration to files"""
        async with self._lock:
            if section and section in self.sections:
                # Save specific section
                file_path = self.config_dir / f"{section}.json"
                with open(file_path, 'w') as f:
                    json.dump(self.sections[section].data, f, indent=2)
                logger.info(f"Saved configuration section: {section}")
            else:
                # Save all sections to main config
                config = self.export_config()
                file_path = self.config_dir.parent / 'config.json'
                with open(file_path, 'w') as f:
                    json.dump(config, f, indent=2)
                logger.info("Saved all configuration sections")
                
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get configuration diagnostics"""
        return {
            'config_dir': str(self.config_dir),
            'sections': list(self.sections.keys()),
            'section_details': {
                name: {
                    'keys': list(section.data.keys()),
                    'last_updated': section.last_updated.isoformat(),
                    'validators': len(section.validators),
                    'is_valid': section.validate()
                }
                for name, section in self.sections.items()
            },
            'observers': len(self.observers),
            'file_watcher_active': self.file_observer is not None and self.file_observer.is_alive()
        }