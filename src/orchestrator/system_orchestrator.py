"""
Main System Orchestrator

Coordinates all system components with unified management and monitoring.
"""

import asyncio
from typing import Dict, Any, Optional, List, Type
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path

from .config_manager import ConfigManager
from .dependency_injector import DependencyInjector, ServiceLifetime
from .health_monitor import HealthMonitor, HealthStatus, AlertLevel
from .startup_sequence import StartupSequence, StartupPhase, ShutdownPriority

# Import system components
from ..auth.credential_manager import CredentialManager
from ..auth.auth_service import AuthService
from ..rate_limiting.kraken_rate_limiter import KrakenRateLimiter2025
from ..circuit_breaker.circuit_breaker import CircuitBreaker
# Import system components - fixed paths
from ..api.kraken_rest_client import KrakenRestClient as RestAPIClient
from ..websocket.kraken_websocket_v2 import KrakenWebSocketV2 as WebSocketClient
from ..balance.balance_manager import BalanceManager as UnifiedBalanceManager
from ..portfolio.portfolio_manager import PortfolioManager
from ..storage.database_manager import DatabaseManager as StorageManager
from ..exchange.exchange_singleton import ExchangeSingleton

logger = logging.getLogger(__name__)


class SystemOrchestrator:
    """Main system orchestrator for coordinating all components"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.start_time = datetime.now()
        
        # Core components
        self.config = ConfigManager(config_path)
        self.injector = DependencyInjector()
        self.health = HealthMonitor()
        self.startup = StartupSequence()
        
        # Component references
        self.components: Dict[str, Any] = {}
        
        # System state
        self.is_initialized = False
        self.is_running = False
        
        # Performance metrics
        self.metrics = {
            'startup_time': None,
            'component_init_times': {},
            'health_checks': 0,
            'errors': 0
        }
        
    async def initialize(self):
        """Initialize the orchestrator and all systems"""
        logger.info("Initializing System Orchestrator")
        
        try:
            # Initialize core components
            await self.config.initialize()
            
            # Register all services
            self._register_services()
            
            # Register startup sequence
            self._register_startup_sequence()
            
            # Register health checks
            self._register_health_checks()
            
            # Execute startup
            success = await self.startup.startup()
            
            if success:
                self.is_initialized = True
                self.is_running = True
                self.metrics['startup_time'] = (datetime.now() - self.start_time).total_seconds()
                
                logger.info(f"System Orchestrator initialized in {self.metrics['startup_time']:.2f}s")
                
                # Start monitoring
                await self.health.initialize()
                
                return True
            else:
                logger.error("System startup failed")
                return False
                
        except Exception as e:
            logger.error(f"Orchestrator initialization failed: {e}")
            self.metrics['errors'] += 1
            raise
            
    def _register_services(self):
        """Register all services with dependency injection"""
        logger.info("Registering services")
        
        # Core services
        self.injector.register_instance(ConfigManager, self.config)
        self.injector.register_instance(HealthMonitor, self.health)
        
        # Authentication
        self.injector.register_singleton(
            CredentialManager,
            init_method='initialize',
            dispose_method='cleanup'
        )
        self.injector.register_singleton(
            AuthService,
            init_method='initialize',
            dispose_method='shutdown'
        )
        
        # Rate limiting and circuit breaker
        self.injector.register_singleton(
            KrakenRateLimiter2025,
            factory=lambda: KrakenRateLimiter2025(
                tier=self.config.get('rate_limiting.tier', 'pro')
            )
        )
        self.injector.register_singleton(
            CircuitBreaker,
            init_method='initialize'
        )
        
        # API clients
        self.injector.register_singleton(
            RestAPIClient,
            init_method='initialize',
            dispose_method='close'
        )
        self.injector.register_singleton(
            WebSocketClient,
            init_method='connect',
            dispose_method='disconnect'
        )
        
        # Trading components
        self.injector.register_singleton(
            UnifiedBalanceManager,
            init_method='initialize',
            dispose_method='shutdown'
        )
        self.injector.register_singleton(
            PortfolioManager,
            init_method='initialize',
            dispose_method='shutdown'
        )
        
        # Storage
        self.injector.register_singleton(
            StorageManager,
            init_method='initialize',
            dispose_method='close'
        )
        
        # Exchange singleton
        self.injector.register_singleton(
            ExchangeSingleton,
            factory=lambda: ExchangeSingleton.get_instance()
        )
        
    def _register_startup_sequence(self):
        """Register startup sequence steps"""
        logger.info("Registering startup sequence")
        
        # Core phase
        self.startup.register_step(
            name='config_validation',
            phase=StartupPhase.CORE,
            handler=self._validate_configuration,
            critical=True
        )
        
        # Infrastructure phase
        self.startup.register_step(
            name='storage_init',
            phase=StartupPhase.INFRASTRUCTURE,
            handler=lambda: self.injector.resolve(StorageManager),
            critical=True
        )
        
        # Authentication phase
        self.startup.register_step(
            name='credentials_init',
            phase=StartupPhase.AUTHENTICATION,
            handler=lambda: self.injector.resolve(CredentialManager),
            critical=True
        )
        
        self.startup.register_step(
            name='auth_service_init',
            phase=StartupPhase.AUTHENTICATION,
            handler=lambda: self.injector.resolve(AuthService),
            dependencies=['credentials_init'],
            critical=True
        )
        
        # Networking phase
        self.startup.register_step(
            name='rate_limiter_init',
            phase=StartupPhase.NETWORKING,
            handler=lambda: self.injector.resolve(KrakenRateLimiter2025),
            critical=True
        )
        
        self.startup.register_step(
            name='circuit_breaker_init',
            phase=StartupPhase.NETWORKING,
            handler=lambda: self.injector.resolve(CircuitBreaker),
            critical=True
        )
        
        self.startup.register_step(
            name='rest_api_init',
            phase=StartupPhase.NETWORKING,
            handler=self._initialize_rest_api,
            dependencies=['auth_service_init', 'rate_limiter_init', 'circuit_breaker_init'],
            critical=True
        )
        
        self.startup.register_step(
            name='websocket_init',
            phase=StartupPhase.NETWORKING,
            handler=self._initialize_websocket,
            dependencies=['auth_service_init'],
            critical=False,
            retry_count=5
        )
        
        # Services phase
        self.startup.register_step(
            name='balance_manager_init',
            phase=StartupPhase.SERVICES,
            handler=lambda: self.injector.resolve(UnifiedBalanceManager),
            dependencies=['rest_api_init', 'websocket_init'],
            critical=True
        )
        
        self.startup.register_step(
            name='portfolio_manager_init',
            phase=StartupPhase.SERVICES,
            handler=lambda: self.injector.resolve(PortfolioManager),
            dependencies=['balance_manager_init'],
            critical=True
        )
        
        # Register shutdown handlers
        self.startup.register_shutdown_handler(
            self._shutdown_websocket,
            ShutdownPriority.NETWORKING
        )
        
        self.startup.register_shutdown_handler(
            self._shutdown_services,
            ShutdownPriority.SERVICES
        )
        
        self.startup.register_shutdown_handler(
            self.injector.dispose_all,
            ShutdownPriority.CORE
        )
        
    def _register_health_checks(self):
        """Register component health checks"""
        # Components automatically register themselves
        components = [
            'storage', 'credentials', 'auth', 'rate_limiter',
            'circuit_breaker', 'rest_api', 'websocket',
            'balance_manager', 'portfolio_manager'
        ]
        
        for component in components:
            self.health.register_component(component)
            
        # Register recovery handlers
        self.health.register_recovery_handler('websocket', self._recover_websocket)
        self.health.register_recovery_handler('rest_api', self._recover_rest_api)
        
        # Register alert handler
        self.health.register_alert_handler(self._handle_health_alert)
        
    async def _validate_configuration(self):
        """Validate system configuration"""
        logger.info("Validating configuration")
        
        required_sections = ['exchange', 'trading', 'rate_limiting']
        for section in required_sections:
            if not self.config.get_section(section):
                raise ValueError(f"Missing required configuration section: {section}")
                
        # Validate API credentials exist
        if not self.config.get('exchange.api_key') and not self.config.get('exchange.use_env_vars', True):
            raise ValueError("API credentials not configured")
            
    async def _initialize_rest_api(self):
        """Initialize REST API with dependencies"""
        rest_client = await self.injector.resolve(RestAPIClient)
        
        # Inject dependencies
        rest_client.rate_limiter = await self.injector.resolve(KrakenRateLimiter2025)
        rest_client.circuit_breaker = await self.injector.resolve(CircuitBreaker)
        rest_client.auth_service = await self.injector.resolve(AuthService)
        
        return rest_client
        
    async def _initialize_websocket(self):
        """Initialize WebSocket with dependencies"""
        ws_client = await self.injector.resolve(WebSocketClient)
        
        # Configure from settings
        ws_client.ping_interval = self.config.get('websocket.ping_interval', 30)
        ws_client.reconnect_delay = self.config.get('websocket.reconnect_delay', 5)
        
        return ws_client
        
    async def _shutdown_websocket(self):
        """Gracefully shutdown WebSocket"""
        try:
            ws_client = await self.injector.resolve(WebSocketClient)
            await ws_client.disconnect()
        except Exception as e:
            logger.error(f"Error shutting down WebSocket: {e}")
            
    async def _shutdown_services(self):
        """Shutdown all services"""
        logger.info("Shutting down services")
        
        # Services will be disposed by dependency injector
        # This is for any additional cleanup
        
    async def _recover_websocket(self):
        """Attempt to recover WebSocket connection"""
        logger.info("Attempting WebSocket recovery")
        
        try:
            ws_client = await self.injector.resolve(WebSocketClient)
            await ws_client.reconnect()
            
            # Update health status
            await self.health.update_component_status(
                'websocket',
                HealthStatus.HEALTHY
            )
            
        except Exception as e:
            logger.error(f"WebSocket recovery failed: {e}")
            
    async def _recover_rest_api(self):
        """Attempt to recover REST API"""
        logger.info("Attempting REST API recovery")
        
        try:
            # Reset circuit breaker
            circuit_breaker = await self.injector.resolve(CircuitBreaker)
            circuit_breaker.reset()
            
            # Test connection
            rest_client = await self.injector.resolve(RestAPIClient)
            await rest_client.test_connection()
            
            # Update health status
            await self.health.update_component_status(
                'rest_api',
                HealthStatus.HEALTHY
            )
            
        except Exception as e:
            logger.error(f"REST API recovery failed: {e}")
            
    async def _handle_health_alert(self, alert):
        """Handle health alerts"""
        logger.info(f"Health alert: {alert.component} - {alert.level.value}: {alert.message}")
        
        # Store alert for diagnostics
        if alert.level in (AlertLevel.ERROR, AlertLevel.CRITICAL):
            self.metrics['errors'] += 1
            
        # Could implement additional alert handling (notifications, etc.)
        
    async def get_component(self, component_type: Type) -> Any:
        """Get a component instance"""
        return await self.injector.resolve(component_type)
        
    async def update_config(self, path: str, value: Any):
        """Update configuration value"""
        self.config.set(path, value)
        
        # Save if specified
        if self.config.get('system.auto_save_config', False):
            await self.config.save_config()
            
    async def shutdown(self):
        """Shutdown the orchestrator"""
        logger.info("Shutting down System Orchestrator")
        
        self.is_running = False
        
        # Shutdown sequence
        await self.startup.shutdown()
        
        # Shutdown health monitor
        await self.health.shutdown()
        
        # Shutdown config manager
        await self.config.shutdown()
        
        logger.info("System Orchestrator shutdown complete")
        
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'uptime': (datetime.now() - self.start_time).total_seconds() if self.is_running else 0,
            'health': self.health.get_system_status().value,
            'metrics': self.metrics,
            'components': {
                name: info['instance_created']
                for name, info in self.injector.get_all_services().items()
            }
        }
        
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get comprehensive system diagnostics"""
        return {
            'status': self.get_status(),
            'config': self.config.get_diagnostics(),
            'dependencies': self.injector.get_diagnostics(),
            'health': self.health.get_diagnostics(),
            'startup': self.startup.get_diagnostics()
        }
        
    async def export_diagnostics(self, file_path: str = None):
        """Export diagnostics to file"""
        diagnostics = self.get_diagnostics()
        
        if not file_path:
            file_path = f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(diagnostics, f, indent=2, default=str)
            
        logger.info(f"Diagnostics exported to: {path}")
        
    async def run_health_check(self) -> Dict[str, Any]:
        """Run immediate health check"""
        await self.health._perform_health_checks()
        return self.health.get_all_health()
        
    @property
    def uptime(self) -> timedelta:
        """Get system uptime"""
        return datetime.now() - self.start_time if self.is_running else timedelta(0)