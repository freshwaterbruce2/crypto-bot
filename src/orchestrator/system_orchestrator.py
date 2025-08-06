"""
Main System Orchestrator

Coordinates all system components with unified management and monitoring.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Import system components - fixed paths
from ..api.simple_kraken_rest import SimpleKrakenREST as RestAPIClient
from ..auth.auth_service import AuthService

# Import system components
from ..auth.credential_manager import CredentialManager
from ..balance.balance_manager import BalanceManager as UnifiedBalanceManager
from ..circuit_breaker.circuit_breaker import CircuitBreaker
from ..exchange.exchange_singleton import ExchangeSingleton
from ..portfolio.portfolio_manager import PortfolioManager
from ..rate_limiting.kraken_rate_limiter import KrakenRateLimiter2025
from ..storage.database_manager import DatabaseManager as StorageManager
from ..websocket.kraken_websocket_v2 import KrakenWebSocketV2 as WebSocketClient
from .config_manager import ConfigManager
from .dependency_injector import DependencyInjector
from .health_monitor import AlertLevel, HealthMonitor, HealthStatus
from .startup_sequence import ShutdownPriority, StartupPhase, StartupSequence

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
        self.components: dict[str, Any] = {}

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

                # Update component health status for successfully initialized components
                await self._update_component_health_status()

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
                account_tier=self.config.get('rate_limiting.tier', 'intermediate')
            )
        )
        self.injector.register_singleton(
            CircuitBreaker,
            factory=lambda: CircuitBreaker(name="system_circuit_breaker"),
            init_method='initialize'
        )

        # API clients
        self.injector.register_singleton(
            RestAPIClient,
            factory=self._create_rest_api_client,
            init_method=None,  # KrakenRestClient doesn't have initialize
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
            dispose_method='shutdown'
        )

        # Exchange singleton
        self.injector.register_singleton(
            ExchangeSingleton,
            factory=lambda: ExchangeSingleton.get_instance()
        )

    def _create_rest_api_client(self):
        """Factory method to create REST API client with credentials"""
        try:
            # Get account tier from config (pro for Kraken Pro)
            import os
            os.getenv('KRAKEN_TIER', 'pro').upper()

            # Map tier to AccountTier enum

            # Create simple REST client with working authentication
            # It will automatically load credentials from environment variables
            return RestAPIClient()

        except Exception as e:
            logger.error(f"Failed to create REST API client: {e}")
            # Try to provide more helpful error information
            try:
                from ..auth.credential_manager import get_kraken_rest_credentials
                api_key, private_key = get_kraken_rest_credentials()
                if not api_key or not private_key:
                    logger.error(
                        "No valid Kraken API credentials found. Please set environment variables:\n"
                        "  KRAKEN_KEY and KRAKEN_SECRET (recommended)\n"
                        "  OR KRAKEN_API_KEY and KRAKEN_API_SECRET (legacy)"
                    )
                else:
                    logger.error(f"Credentials found (api_key: {api_key[:8]}...) but REST client creation failed")
            except Exception as cred_error:
                logger.error(f"Could not check credential status: {cred_error}")
            raise

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
            handler=self._initialize_storage,
            critical=True
        )

        # WebSocket Authentication phase (minimal REST for token)
        self.startup.register_step(
            name='credentials_init',
            phase=StartupPhase.WEBSOCKET_AUTH,
            handler=self._initialize_credentials,
            critical=True
        )

        self.startup.register_step(
            name='auth_service_init',
            phase=StartupPhase.WEBSOCKET_AUTH,
            handler=self._initialize_auth_service,
            dependencies=['credentials_init'],
            critical=True
        )

        self.startup.register_step(
            name='rate_limiter_init',
            phase=StartupPhase.WEBSOCKET_AUTH,
            handler=self._initialize_rate_limiter,
            critical=True
        )

        self.startup.register_step(
            name='circuit_breaker_init',
            phase=StartupPhase.WEBSOCKET_AUTH,
            handler=self._initialize_circuit_breaker,
            critical=True
        )

        # WebSocket Initialization phase
        self.startup.register_step(
            name='websocket_init',
            phase=StartupPhase.WEBSOCKET_INIT,
            handler=self._initialize_websocket,
            dependencies=['auth_service_init', 'rate_limiter_init'],
            critical=False,
            retry_count=5
        )

        # Traditional Authentication phase (full REST API)
        self.startup.register_step(
            name='rest_api_init',
            phase=StartupPhase.AUTHENTICATION,
            handler=self._initialize_rest_api,
            dependencies=['auth_service_init', 'rate_limiter_init', 'circuit_breaker_init'],
            critical=True
        )

        # Services phase
        self.startup.register_step(
            name='balance_manager_init',
            phase=StartupPhase.SERVICES,
            handler=self._initialize_balance_manager,
            dependencies=['rest_api_init'],  # Remove websocket_init dependency since it's not critical
            critical=True
        )

        self.startup.register_step(
            name='portfolio_manager_init',
            phase=StartupPhase.SERVICES,
            handler=self._initialize_portfolio_manager,
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

    async def _update_component_health_status(self):
        """Update component health status based on successful startup completion"""
        logger.info("Updating component health status based on startup results")

        # Map startup step names to health component names
        step_to_component_map = {
            'storage_init': 'storage',
            'credentials_init': 'credentials',
            'auth_service_init': 'auth',
            'rate_limiter_init': 'rate_limiter',
            'circuit_breaker_init': 'circuit_breaker',
            'rest_api_init': 'rest_api',
            'websocket_init': 'websocket',
            'balance_manager_init': 'balance_manager',
            'portfolio_manager_init': 'portfolio_manager'
        }

        # Update health status for completed startup steps
        for step_name in self.startup.completed_steps:
            if step_name in step_to_component_map:
                component_name = step_to_component_map[step_name]
                try:
                    await self.health.update_component_status(
                        component_name,
                        HealthStatus.HEALTHY,
                        {'initialized': True, 'startup_step': step_name}
                    )
                    logger.info(f"Updated health status for {component_name}: HEALTHY")
                except Exception as e:
                    logger.warning(f"Failed to update health status for {component_name}: {e}")

        # Check if any registered components are still unknown and mark them as degraded
        for component_name in self.health.components:
            if component_name not in ['system']:  # Skip system component as it has its own health check
                component_health = self.health.components[component_name]
                if component_health.status == HealthStatus.UNKNOWN:
                    try:
                        await self.health.update_component_status(
                            component_name,
                            HealthStatus.DEGRADED,
                            {'reason': 'No startup step found', 'note': 'Component registered but not initialized'}
                        )
                        logger.warning(f"Marked {component_name} as DEGRADED (no startup step found)")
                    except Exception as e:
                        logger.warning(f"Failed to update degraded status for {component_name}: {e}")

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

    async def _initialize_storage(self):
        """Initialize storage manager"""
        logger.info("Initializing storage manager")

        try:
            storage = await self.injector.resolve(StorageManager)
            self.components['storage'] = storage
            logger.info("Storage manager initialized successfully")
            return storage
        except Exception as e:
            logger.error(f"Failed to initialize storage manager: {e}")
            raise

    async def _initialize_credentials(self):
        """Initialize credential manager"""
        logger.info("Initializing credential manager")

        try:
            credentials = await self.injector.resolve(CredentialManager)
            self.components['credentials'] = credentials
            logger.info("Credential manager initialized successfully")
            return credentials
        except Exception as e:
            logger.error(f"Failed to initialize credential manager: {e}")
            raise

    async def _initialize_auth_service(self):
        """Initialize auth service"""
        logger.info("Initializing auth service")

        try:
            auth = await self.injector.resolve(AuthService)
            self.components['auth'] = auth
            logger.info("Auth service initialized successfully")
            return auth
        except Exception as e:
            logger.error(f"Failed to initialize auth service: {e}")
            raise

    async def _initialize_rate_limiter(self):
        """Initialize rate limiter"""
        logger.info("Initializing rate limiter")

        try:
            rate_limiter = await self.injector.resolve(KrakenRateLimiter2025)
            self.components['rate_limiter'] = rate_limiter
            logger.info("Rate limiter initialized successfully")
            return rate_limiter
        except Exception as e:
            logger.error(f"Failed to initialize rate limiter: {e}")
            raise

    async def _initialize_circuit_breaker(self):
        """Initialize circuit breaker"""
        logger.info("Initializing circuit breaker")

        try:
            circuit_breaker = await self.injector.resolve(CircuitBreaker)
            self.components['circuit_breaker'] = circuit_breaker
            logger.info("Circuit breaker initialized successfully")
            return circuit_breaker
        except Exception as e:
            logger.error(f"Failed to initialize circuit breaker: {e}")
            raise

    async def _initialize_balance_manager(self):
        """Initialize balance manager"""
        logger.info("Initializing balance manager")

        try:
            balance_manager = await self.injector.resolve(UnifiedBalanceManager)
            self.components['balance_manager'] = balance_manager
            logger.info("Balance manager initialized successfully")
            return balance_manager
        except Exception as e:
            logger.error(f"Failed to initialize balance manager: {e}")
            raise

    async def _initialize_portfolio_manager(self):
        """Initialize portfolio manager"""
        logger.info("Initializing portfolio manager")

        try:
            portfolio_manager = await self.injector.resolve(PortfolioManager)
            self.components['portfolio_manager'] = portfolio_manager
            logger.info("Portfolio manager initialized successfully")
            return portfolio_manager
        except Exception as e:
            logger.error(f"Failed to initialize portfolio manager: {e}")
            raise

    async def _initialize_rest_api(self):
        """Initialize REST API with dependencies"""
        logger.info("Initializing REST API client")

        try:
            rest_client = await self.injector.resolve(RestAPIClient)

            # The REST client is already created with all dependencies via factory method
            # Just test the connection to verify credentials
            try:
                # Test authentication by getting balance
                await rest_client.get_account_balance()
                logger.info("REST API authentication successful")
            except Exception as auth_error:
                logger.error(f"REST API authentication failed: {auth_error}")
                # Try to continue anyway for development
                pass

            # Store component reference
            self.components['rest_api'] = rest_client

            logger.info("REST API client initialized successfully")
            return rest_client

        except Exception as e:
            logger.error(f"Failed to initialize REST API client: {e}")
            raise

    async def _initialize_websocket(self):
        """Initialize WebSocket with dependencies"""
        logger.info("Initializing WebSocket client")

        try:
            ws_client = await self.injector.resolve(WebSocketClient)

            # Configure from settings
            ws_client.ping_interval = self.config.get('websocket.ping_interval', 30)
            ws_client.reconnect_delay = self.config.get('websocket.reconnect_delay', 5)

            # Inject auth service if available
            try:
                ws_client.auth_service = await self.injector.resolve(AuthService)
            except Exception as e:
                logger.warning(f"Could not inject auth service into WebSocket: {e}")

            # Store component reference
            self.components['websocket'] = ws_client

            logger.info("WebSocket client initialized successfully")
            return ws_client

        except Exception as e:
            logger.error(f"Failed to initialize WebSocket client: {e}")
            # Don't re-raise since websocket is not critical
            return None

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

    async def get_component(self, component_type: type) -> Any:
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

    def get_status(self) -> dict[str, Any]:
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

    def get_diagnostics(self) -> dict[str, Any]:
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

    async def run_health_check(self) -> dict[str, Any]:
        """Run immediate health check"""
        await self.health._perform_health_checks()
        return self.health.get_all_health()

    @property
    def uptime(self) -> timedelta:
        """Get system uptime"""
        return datetime.now() - self.start_time if self.is_running else timedelta(0)
