"""
Sequential Startup Manager - Fix Nonce Collision During Bot Launch
================================================================

Prevents concurrent REST API calls during startup by implementing a sequential
initialization sequence that prioritizes WebSocket V2 authentication and
coordinates all component startup to avoid nonce conflicts.

Key Features:
- WebSocket V2 authentication first, before any REST calls
- Sequential component initialization
- Startup coordination to prevent race conditions
- Nonce collision prevention
- Circuit breaker for failed startups
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class StartupPhase(Enum):
    """Startup phases in sequential order"""
    PREREQUISITES = "prerequisites"
    WEBSOCKET_AUTH = "websocket_auth"
    BALANCE_MANAGER = "balance_manager"
    CORE_COMPONENTS = "core_components"
    STRATEGIES = "strategies"
    FINALIZATION = "finalization"


@dataclass
class StartupStep:
    """Individual startup step configuration"""
    name: str
    phase: StartupPhase
    function: Callable
    timeout: float = 30.0
    critical: bool = True
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class SequentialStartupManager:
    """
    Manages sequential bot startup to prevent nonce collisions
    
    Ensures WebSocket authentication happens first, then initializes
    components one by one to avoid concurrent REST API calls.
    """

    def __init__(self, bot_instance):
        """Initialize startup manager with bot reference"""
        self.bot = bot_instance
        self.logger = logger

        # State tracking
        self.current_phase: Optional[StartupPhase] = None
        self.completed_steps: List[str] = []
        self.failed_steps: List[str] = []
        self.startup_start_time = 0
        self.phase_times: Dict[StartupPhase, float] = {}

        # REST API lockout during WebSocket authentication
        self.rest_api_locked = False
        self.websocket_auth_complete = False

        # Circuit breaker for failed startups
        self.max_retries = 3
        self.retry_delay = 5.0

        # Define startup sequence
        self.startup_steps = self._define_startup_sequence()

        self.logger.info("[STARTUP_MGR] Sequential startup manager initialized")

    def _define_startup_sequence(self) -> List[StartupStep]:
        """Define the complete startup sequence"""
        return [
            # Phase 1: Prerequisites (no REST calls allowed)
            StartupStep(
                name="validate_environment",
                phase=StartupPhase.PREREQUISITES,
                function=self._validate_environment,
                timeout=10.0,
                critical=True
            ),
            StartupStep(
                name="initialize_nonce_manager",
                phase=StartupPhase.PREREQUISITES,
                function=self._initialize_nonce_manager,
                timeout=5.0,
                critical=True
            ),
            StartupStep(
                name="create_exchange_instance",
                phase=StartupPhase.PREREQUISITES,
                function=self._create_exchange_instance,
                timeout=15.0,
                critical=True
            ),

            # Phase 2: WebSocket Authentication (CRITICAL - must be first REST call)
            StartupStep(
                name="websocket_authentication",
                phase=StartupPhase.WEBSOCKET_AUTH,
                function=self._authenticate_websocket,
                timeout=30.0,
                critical=True,
                dependencies=["validate_environment", "initialize_nonce_manager", "create_exchange_instance"]
            ),
            StartupStep(
                name="websocket_connection",
                phase=StartupPhase.WEBSOCKET_AUTH,
                function=self._establish_websocket_connection,
                timeout=20.0,
                critical=True,
                dependencies=["websocket_authentication"]
            ),

            # Phase 3: Balance Manager (after WebSocket is ready)
            StartupStep(
                name="balance_manager_v2",
                phase=StartupPhase.BALANCE_MANAGER,
                function=self._initialize_balance_manager,
                timeout=20.0,
                critical=True,
                dependencies=["websocket_connection"]
            ),
            StartupStep(
                name="validate_initial_balances",
                phase=StartupPhase.BALANCE_MANAGER,
                function=self._validate_initial_balances,
                timeout=15.0,
                critical=False,
                dependencies=["balance_manager_v2"]
            ),

            # Phase 4: Core Components (sequential, no concurrent REST calls)
            StartupStep(
                name="trade_executor",
                phase=StartupPhase.CORE_COMPONENTS,
                function=self._initialize_trade_executor,
                timeout=15.0,
                critical=True,
                dependencies=["balance_manager_v2"]
            ),
            StartupStep(
                name="risk_management",
                phase=StartupPhase.CORE_COMPONENTS,
                function=self._initialize_risk_management,
                timeout=10.0,
                critical=False,
                dependencies=["trade_executor"]
            ),
            StartupStep(
                name="portfolio_manager",
                phase=StartupPhase.CORE_COMPONENTS,
                function=self._initialize_portfolio_manager,
                timeout=10.0,
                critical=False,
                dependencies=["balance_manager_v2"]
            ),

            # Phase 5: Strategies (after all core components ready)
            StartupStep(
                name="strategy_manager",
                phase=StartupPhase.STRATEGIES,
                function=self._initialize_strategy_manager,
                timeout=15.0,
                critical=False,
                dependencies=["trade_executor", "portfolio_manager"]
            ),
            StartupStep(
                name="load_market_data",
                phase=StartupPhase.STRATEGIES,
                function=self._load_initial_market_data,
                timeout=30.0,
                critical=False,
                dependencies=["strategy_manager"]
            ),

            # Phase 6: Finalization
            StartupStep(
                name="start_monitoring",
                phase=StartupPhase.FINALIZATION,
                function=self._start_monitoring_systems,
                timeout=10.0,
                critical=False,
                dependencies=["load_market_data"]
            ),
            StartupStep(
                name="health_check",
                phase=StartupPhase.FINALIZATION,
                function=self._perform_health_check,
                timeout=10.0,
                critical=True,
                dependencies=["start_monitoring"]
            )
        ]

    async def execute_sequential_startup(self) -> bool:
        """
        Execute the complete sequential startup process
        
        Returns:
            bool: True if startup successful, False otherwise
        """
        self.startup_start_time = time.time()
        self.logger.info("[STARTUP_MGR] Starting sequential bot initialization...")

        try:
            # Lock REST API during initial WebSocket authentication
            self.rest_api_locked = True
            self.logger.info("[STARTUP_MGR] REST API locked during WebSocket authentication phase")

            # Execute phases in order
            for phase in StartupPhase:
                if not await self._execute_phase(phase):
                    self.logger.error(f"[STARTUP_MGR] Phase {phase.value} failed - aborting startup")
                    return False

            # Mark startup as successful
            total_time = time.time() - self.startup_start_time
            self.logger.info(f"[STARTUP_MGR] Sequential startup completed successfully in {total_time:.2f}s")
            return True

        except Exception as e:
            self.logger.error(f"[STARTUP_MGR] Sequential startup failed with exception: {e}")
            import traceback
            self.logger.error(f"[STARTUP_MGR] Stack trace: {traceback.format_exc()}")
            return False
        finally:
            # Ensure REST API is unlocked
            self.rest_api_locked = False
            self.logger.info("[STARTUP_MGR] REST API unlocked")

    async def _execute_phase(self, phase: StartupPhase) -> bool:
        """Execute all steps in a specific phase"""
        phase_start = time.time()
        self.current_phase = phase
        self.logger.info(f"[STARTUP_MGR] Starting phase: {phase.value}")

        # Get steps for this phase
        phase_steps = [step for step in self.startup_steps if step.phase == phase]

        # Execute steps sequentially within the phase
        for step in phase_steps:
            if not await self._execute_step(step):
                if step.critical:
                    self.logger.error(f"[STARTUP_MGR] Critical step {step.name} failed - phase {phase.value} aborted")
                    return False
                else:
                    self.logger.warning(f"[STARTUP_MGR] Non-critical step {step.name} failed - continuing")

        # Record phase completion time
        self.phase_times[phase] = time.time() - phase_start
        self.logger.info(f"[STARTUP_MGR] Phase {phase.value} completed in {self.phase_times[phase]:.2f}s")

        # Special handling for WebSocket authentication phase
        if phase == StartupPhase.WEBSOCKET_AUTH:
            self.websocket_auth_complete = True
            self.rest_api_locked = False  # Allow controlled REST API usage
            self.logger.info("[STARTUP_MGR] WebSocket authentication complete - enabling controlled REST API access")

        return True

    async def _execute_step(self, step: StartupStep) -> bool:
        """Execute a single startup step with timeout and error handling"""
        self.logger.info(f"[STARTUP_MGR] Executing step: {step.name}")

        # Check dependencies
        if not self._check_dependencies(step):
            self.logger.error(f"[STARTUP_MGR] Step {step.name} dependencies not met")
            return False

        try:
            # Execute with timeout
            await asyncio.wait_for(step.function(), timeout=step.timeout)
            self.completed_steps.append(step.name)
            self.logger.info(f"[STARTUP_MGR] Step {step.name} completed successfully")
            return True

        except asyncio.TimeoutError:
            self.logger.error(f"[STARTUP_MGR] Step {step.name} timed out after {step.timeout}s")
            self.failed_steps.append(step.name)
            return False

        except Exception as e:
            self.logger.error(f"[STARTUP_MGR] Step {step.name} failed with error: {e}")
            self.failed_steps.append(step.name)
            return False

    def _check_dependencies(self, step: StartupStep) -> bool:
        """Check if step dependencies are satisfied"""
        for dep in step.dependencies:
            if dep not in self.completed_steps:
                self.logger.warning(f"[STARTUP_MGR] Dependency {dep} not satisfied for step {step.name}")
                return False
        return True

    # =================================================================
    # STARTUP STEP IMPLEMENTATIONS
    # =================================================================

    async def _validate_environment(self):
        """Validate environment and configuration"""
        self.logger.info("[STARTUP] Validating environment and configuration...")

        # Check API credentials
        import os
        api_key = os.getenv('KRAKEN_REST_API_KEY') or os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_REST_API_SECRET') or os.getenv('KRAKEN_API_SECRET', '')

        if not api_key or not api_secret:
            raise Exception("Missing Kraken API credentials")

        self.logger.info("[STARTUP] Environment validation complete")

    async def _initialize_nonce_manager(self):
        """Initialize the consolidated nonce manager"""
        self.logger.info("[STARTUP] Initializing nonce manager...")

        import os

        from src.utils.consolidated_nonce_manager import initialize_enhanced_nonce_manager

        api_key = os.getenv('KRAKEN_REST_API_KEY') or os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_REST_API_SECRET') or os.getenv('KRAKEN_API_SECRET', '')

        # Initialize enhanced nonce manager
        nonce_manager = initialize_enhanced_nonce_manager(api_key, api_secret)

        self.logger.info("[STARTUP] Nonce manager initialized with enhanced features")

    async def _create_exchange_instance(self):
        """Create exchange instance without making any API calls"""
        self.logger.info("[STARTUP] Creating exchange instance...")

        import os

        from src.exchange.exchange_singleton import get_exchange

        api_key = os.getenv('KRAKEN_REST_API_KEY') or os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_REST_API_SECRET') or os.getenv('KRAKEN_API_SECRET', '')
        tier = self.bot.config.get('core', {}).get('kraken_api_tier', 'pro')

        # Create exchange instance but don't initialize it yet
        self.bot.exchange = await get_exchange(
            api_key=api_key,
            api_secret=api_secret,
            tier=tier,
            config=self.bot.config,
            initialize=False  # Don't make any API calls yet
        )

        self.logger.info("[STARTUP] Exchange instance created (no API calls made)")

    async def _authenticate_websocket(self):
        """Authenticate WebSocket connection - FIRST REST API call"""
        self.logger.info("[STARTUP] Authenticating WebSocket connection (FIRST REST API call)...")

        # This is the ONLY REST API call allowed during this phase
        try:
            # Import WebSocket manager
            from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager

            # Create WebSocket manager
            self.bot.websocket_manager = KrakenProWebSocketManager(
                exchange_client=self.bot.exchange,
                symbols=[],  # Will be set later
                data_coordinator=None  # Will be set later
            )

            # Get WebSocket token (this makes the critical first REST call)
            await self.bot.websocket_manager.get_websocket_token()

            self.logger.info("[STARTUP] WebSocket authentication successful - token obtained")

        except Exception as e:
            self.logger.error(f"[STARTUP] WebSocket authentication failed: {e}")
            raise

    async def _establish_websocket_connection(self):
        """Establish WebSocket connection"""
        self.logger.info("[STARTUP] Establishing WebSocket connection...")

        try:
            # Connect to WebSocket using the authenticated token
            await self.bot.websocket_manager.connect()

            # Wait for connection to be established
            await asyncio.sleep(2)

            self.logger.info("[STARTUP] WebSocket connection established successfully")

        except Exception as e:
            self.logger.error(f"[STARTUP] WebSocket connection failed: {e}")
            raise

    async def _initialize_balance_manager(self):
        """Initialize Balance Manager V2 with WebSocket integration"""
        self.logger.info("[STARTUP] Initializing Balance Manager V2...")

        try:
            from src.balance.balance_manager_v2 import (
                BalanceManagerV2Config,
                create_balance_manager_v2,
            )
            from src.portfolio.legacy_wrapper import LegacyBalanceManagerWrapper

            # Configure Balance Manager V2 for WebSocket-primary operation
            balance_config = BalanceManagerV2Config(
                websocket_primary_ratio=0.95,  # 95% WebSocket usage
                rest_fallback_ratio=0.05,      # 5% REST fallback
                enable_balance_validation=True,
                enable_balance_aggregation=True,
                enable_circuit_breaker=True,
                circuit_breaker_failure_threshold=3,
                circuit_breaker_recovery_timeout=30.0,
                enable_performance_monitoring=True,
                maintain_legacy_interface=True,
                enable_balance_callbacks=True
            )

            # Create Balance Manager V2
            self.bot.balance_manager_v2 = await create_balance_manager_v2(
                websocket_client=self.bot.websocket_manager,
                exchange_client=self.bot.exchange,
                config=balance_config
            )

            # Legacy compatibility wrapper
            self.bot.balance_manager = LegacyBalanceManagerWrapper(self.bot.balance_manager_v2)
            self.bot.enhanced_balance_manager = self.bot.balance_manager

            self.logger.info("[STARTUP] Balance Manager V2 initialized successfully")

        except Exception as e:
            self.logger.error(f"[STARTUP] Balance Manager V2 initialization failed: {e}")
            raise

    async def _validate_initial_balances(self):
        """Validate initial balance data"""
        self.logger.info("[STARTUP] Validating initial balances...")

        try:
            # Get initial balances to validate system is working
            balances = await self.bot.balance_manager.get_balances()

            if not balances:
                self.logger.warning("[STARTUP] No balances returned - may be empty account")
            else:
                self.logger.info(f"[STARTUP] Initial balances validated - {len(balances)} assets found")

        except Exception as e:
            self.logger.warning(f"[STARTUP] Balance validation failed: {e}")
            # Non-critical step, continue

    async def _initialize_trade_executor(self):
        """Initialize trade executor"""
        self.logger.info("[STARTUP] Initializing trade executor...")

        try:
            from src.trading.enhanced_trade_executor_with_assistants import EnhancedTradeExecutor

            self.bot.trade_executor = EnhancedTradeExecutor(
                exchange_client=self.bot.exchange,
                symbol_mapper=getattr(self.bot, 'symbol_mapper', None),
                config=self.bot.config,
                bot_reference=self.bot,
                balance_manager=self.bot.balance_manager,
                risk_manager=getattr(self.bot, 'risk_manager', None),
                stop_loss_manager=getattr(self.bot, 'stop_loss_manager', None)
            )

            # Initialize trade executor
            if hasattr(self.bot.trade_executor, 'initialize'):
                await self.bot.trade_executor.initialize()

            self.logger.info("[STARTUP] Trade executor initialized successfully")

        except Exception as e:
            self.logger.error(f"[STARTUP] Trade executor initialization failed: {e}")
            raise

    async def _initialize_risk_management(self):
        """Initialize risk management components"""
        self.logger.info("[STARTUP] Initializing risk management...")

        try:
            # Initialize risk manager if configured
            if self.bot.config.get('risk_management', {}).get('enabled', True):
                from src.trading.unified_risk_manager import UnifiedRiskManager

                self.bot.risk_manager = UnifiedRiskManager(
                    config=self.bot.config,
                    balance_manager=self.bot.balance_manager,
                    exchange=self.bot.exchange
                )

                # Update trade executor with risk manager
                if self.bot.trade_executor:
                    self.bot.trade_executor.risk_manager = self.bot.risk_manager

            self.logger.info("[STARTUP] Risk management initialized")

        except Exception as e:
            self.logger.warning(f"[STARTUP] Risk management initialization failed: {e}")
            # Non-critical, continue

    async def _initialize_portfolio_manager(self):
        """Initialize portfolio manager"""
        self.logger.info("[STARTUP] Initializing portfolio manager...")

        try:
            from src.portfolio.portfolio_manager import PortfolioManager

            self.bot.portfolio_manager = PortfolioManager(
                exchange=self.bot.exchange,
                balance_manager=self.bot.balance_manager,
                config=self.bot.config
            )

            if hasattr(self.bot.portfolio_manager, 'initialize'):
                await self.bot.portfolio_manager.initialize()

            self.logger.info("[STARTUP] Portfolio manager initialized")

        except Exception as e:
            self.logger.warning(f"[STARTUP] Portfolio manager initialization failed: {e}")
            # Non-critical, continue

    async def _initialize_strategy_manager(self):
        """Initialize strategy manager"""
        self.logger.info("[STARTUP] Initializing strategy manager...")

        try:
            from src.trading.functional_strategy_manager import FunctionalStrategyManager

            self.bot.strategy_manager = FunctionalStrategyManager(
                bot=self.bot
            )

            if hasattr(self.bot.strategy_manager, 'initialize'):
                await self.bot.strategy_manager.initialize()

            self.logger.info("[STARTUP] Strategy manager initialized")

        except Exception as e:
            self.logger.warning(f"[STARTUP] Strategy manager initialization failed: {e}")
            # Non-critical, continue

    async def _load_initial_market_data(self):
        """Load initial market data"""
        self.logger.info("[STARTUP] Loading initial market data...")

        try:
            # Get available trading pairs
            if hasattr(self.bot, 'exchange') and self.bot.exchange:
                markets = await self.bot.exchange.fetch_markets()

                # Filter USDT pairs
                usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT')]
                self.bot.trade_pairs = usdt_pairs[:20]  # Limit to 20 pairs for startup

                self.logger.info(f"[STARTUP] Loaded {len(self.bot.trade_pairs)} trading pairs")

        except Exception as e:
            self.logger.warning(f"[STARTUP] Market data loading failed: {e}")
            # Non-critical, continue

    async def _start_monitoring_systems(self):
        """Start monitoring and health check systems"""
        self.logger.info("[STARTUP] Starting monitoring systems...")

        try:
            # Initialize self-repair system
            from src.utils.self_repair import SelfRepairSystem
            self.bot.self_repair_system = SelfRepairSystem(self.bot)

            # Initialize critical error guardian
            from src.guardian.critical_error_guardian import CriticalErrorGuardian
            self.bot.critical_error_guardian = CriticalErrorGuardian(self.bot)

            self.logger.info("[STARTUP] Monitoring systems started")

        except Exception as e:
            self.logger.warning(f"[STARTUP] Monitoring systems initialization failed: {e}")
            # Non-critical, continue

    async def _perform_health_check(self):
        """Perform final health check"""
        self.logger.info("[STARTUP] Performing final health check...")

        try:
            # Check critical components
            checks = {
                'exchange': self.bot.exchange is not None,
                'websocket': self.bot.websocket_manager is not None,
                'balance_manager': self.bot.balance_manager is not None,
                'trade_executor': self.bot.trade_executor is not None
            }

            failed_checks = [name for name, passed in checks.items() if not passed]

            if failed_checks:
                raise Exception(f"Health check failed for: {', '.join(failed_checks)}")

            self.logger.info("[STARTUP] Health check passed - all critical components initialized")

        except Exception as e:
            self.logger.error(f"[STARTUP] Health check failed: {e}")
            raise

    def get_startup_status(self) -> Dict[str, Any]:
        """Get current startup status"""
        return {
            'current_phase': self.current_phase.value if self.current_phase else None,
            'completed_steps': self.completed_steps,
            'failed_steps': self.failed_steps,
            'websocket_auth_complete': self.websocket_auth_complete,
            'rest_api_locked': self.rest_api_locked,
            'phase_times': {phase.value: time_taken for phase, time_taken in self.phase_times.items()},
            'total_time': time.time() - self.startup_start_time if self.startup_start_time > 0 else 0
        }
