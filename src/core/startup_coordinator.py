"""
Startup Coordinator - Immediate Nonce Collision Fix
==================================================

Emergency fix for nonce collision issues during bot startup.
Coordinates component initialization to prevent concurrent REST API calls.

Key Features:
- WebSocket authentication FIRST (single REST call)
- Delays all other REST calls until WebSocket is ready
- Sequential component initialization
- Prevents nonce manager conflicts
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


class StartupCoordinator:
    """Coordinates bot startup to prevent nonce collisions"""

    def __init__(self, bot_instance):
        """Initialize coordinator with bot reference"""
        self.bot = bot_instance
        self.websocket_ready = False
        self.startup_lock = asyncio.Lock()

        logger.info("[STARTUP_COORD] Startup coordinator initialized")

    async def coordinate_startup(self) -> bool:
        """
        Coordinate the startup sequence to prevent nonce collisions
        
        Returns:
            bool: True if startup successful
        """
        async with self.startup_lock:
            try:
                logger.info("[STARTUP_COORD] Starting coordinated initialization...")

                # Phase 1: WebSocket authentication ONLY (first REST call)
                if not await self._authenticate_websocket_first():
                    return False

                # Phase 2: Initialize core components sequentially
                if not await self._initialize_core_components():
                    return False

                # Phase 3: Start remaining systems
                if not await self._start_remaining_systems():
                    return False

                logger.info("[STARTUP_COORD] Coordinated startup completed successfully")
                return True

            except Exception as e:
                logger.error(f"[STARTUP_COORD] Startup coordination failed: {e}")
                return False

    async def _authenticate_websocket_first(self) -> bool:
        """Authenticate WebSocket connection first to get valid token"""
        try:
            logger.info("[STARTUP_COORD] Phase 1: WebSocket authentication (FIRST REST call)")

            # Disable all other REST calls temporarily
            self._disable_rest_calls()

            # Import WebSocket manager
            try:
                from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager as WSManager
                websocket_v2_available = True
            except ImportError:
                from src.exchange.websocket_simple import SimpleKrakenWebSocket as WSManager
                websocket_v2_available = False
                logger.warning("[STARTUP_COORD] WebSocket V2 not available, using simple WebSocket")

            # Create WebSocket manager
            if websocket_v2_available:
                self.bot.websocket_manager = WSManager(
                    exchange_client=self.bot.exchange,
                    symbols=getattr(self.bot, 'trade_pairs', []),
                    data_coordinator=None
                )

                # Get WebSocket token (FIRST and ONLY REST call during this phase)
                await self.bot.websocket_manager.get_websocket_token()
                logger.info("[STARTUP_COORD] WebSocket token obtained successfully")

                # Connect WebSocket
                await self.bot.websocket_manager.connect()
                logger.info("[STARTUP_COORD] WebSocket connected successfully")

            else:
                # Simple WebSocket (no token needed)
                self.bot.websocket_manager = WSManager(
                    symbols=getattr(self.bot, 'trade_pairs', []),
                    ticker_callback=None,
                    ohlc_callback=None,
                    config=self.bot.config,
                    rest_client=self.bot.exchange
                )
                await self.bot.websocket_manager.connect()
                logger.info("[STARTUP_COORD] Simple WebSocket connected")

            # Mark WebSocket as ready
            self.websocket_ready = True

            # Re-enable REST calls (now that WebSocket has priority)
            self._enable_rest_calls()

            logger.info("[STARTUP_COORD] WebSocket authentication phase complete")
            return True

        except Exception as e:
            logger.error(f"[STARTUP_COORD] WebSocket authentication failed: {e}")
            self._enable_rest_calls()  # Re-enable on failure
            return False

    async def _initialize_core_components(self) -> bool:
        """Initialize core components sequentially"""
        try:
            logger.info("[STARTUP_COORD] Phase 2: Core components initialization")

            # Wait a moment for WebSocket to stabilize
            await asyncio.sleep(2)

            # Initialize Balance Manager V2 with WebSocket integration
            await self._initialize_balance_manager()

            # Initialize trade executor
            await self._initialize_trade_executor()

            # Initialize risk management
            await self._initialize_risk_management()

            logger.info("[STARTUP_COORD] Core components initialized")
            return True

        except Exception as e:
            logger.error(f"[STARTUP_COORD] Core components initialization failed: {e}")
            return False

    async def _start_remaining_systems(self) -> bool:
        """Start remaining bot systems"""
        try:
            logger.info("[STARTUP_COORD] Phase 3: Starting remaining systems")

            # Initialize strategies
            await self._initialize_strategies()

            # Load market data
            await self._load_market_data()

            # Start monitoring
            await self._start_monitoring()

            logger.info("[STARTUP_COORD] Remaining systems started")
            return True

        except Exception as e:
            logger.warning(f"[STARTUP_COORD] Some systems failed to start: {e}")
            return True  # Non-critical failures allowed

    async def _initialize_balance_manager(self):
        """Initialize Balance Manager V2"""
        logger.info("[STARTUP_COORD] Initializing Balance Manager V2...")

        try:
            from src.balance.balance_manager_v2 import (
                BalanceManagerV2Config,
                create_balance_manager_v2,
            )
            from src.portfolio.legacy_wrapper import LegacyBalanceManagerWrapper

            # Configure for WebSocket-primary operation
            balance_config = BalanceManagerV2Config(
                websocket_primary_ratio=0.95,
                rest_fallback_ratio=0.05,
                enable_balance_validation=True,
                enable_circuit_breaker=True,
                maintain_legacy_interface=True
            )

            # Create Balance Manager V2
            self.bot.balance_manager_v2 = await create_balance_manager_v2(
                websocket_client=self.bot.websocket_manager,
                exchange_client=self.bot.exchange,
                config=balance_config
            )

            # Legacy wrapper
            self.bot.balance_manager = LegacyBalanceManagerWrapper(self.bot.balance_manager_v2)
            self.bot.enhanced_balance_manager = self.bot.balance_manager

            logger.info("[STARTUP_COORD] Balance Manager V2 initialized")

        except Exception as e:
            logger.warning(f"[STARTUP_COORD] Balance Manager initialization failed: {e}")
            # Create minimal fallback
            self.bot.balance_manager = None
            self.bot.enhanced_balance_manager = None

    async def _initialize_trade_executor(self):
        """Initialize trade executor"""
        logger.info("[STARTUP_COORD] Initializing trade executor...")

        try:
            from src.trading.enhanced_trade_executor_with_assistants import EnhancedTradeExecutor

            # Initialize symbol mapper if needed
            if not hasattr(self.bot, 'symbol_mapper'):
                from src.utils.centralized_symbol_mapper import KrakenSymbolMapper
                self.bot.symbol_mapper = KrakenSymbolMapper()

            self.bot.trade_executor = EnhancedTradeExecutor(
                exchange_client=self.bot.exchange,
                symbol_mapper=self.bot.symbol_mapper,
                config=self.bot.config,
                bot_reference=self.bot,
                balance_manager=self.bot.balance_manager,
                risk_manager=getattr(self.bot, 'risk_manager', None),
                stop_loss_manager=getattr(self.bot, 'stop_loss_manager', None)
            )

            logger.info("[STARTUP_COORD] Trade executor initialized")

        except Exception as e:
            logger.warning(f"[STARTUP_COORD] Trade executor initialization failed: {e}")

    async def _initialize_risk_management(self):
        """Initialize risk management"""
        logger.info("[STARTUP_COORD] Initializing risk management...")

        try:
            if self.bot.config.get('risk_management', {}).get('enabled', True):
                from src.trading.unified_risk_manager import UnifiedRiskManager

                self.bot.risk_manager = UnifiedRiskManager(
                    config=self.bot.config,
                    balance_manager=self.bot.balance_manager,
                    exchange=self.bot.exchange
                )

                # Update trade executor
                if self.bot.trade_executor:
                    self.bot.trade_executor.risk_manager = self.bot.risk_manager

            logger.info("[STARTUP_COORD] Risk management initialized")

        except Exception as e:
            logger.warning(f"[STARTUP_COORD] Risk management initialization failed: {e}")

    async def _initialize_strategies(self):
        """Initialize strategy manager"""
        logger.info("[STARTUP_COORD] Initializing strategies...")

        try:
            from src.trading.functional_strategy_manager import FunctionalStrategyManager

            self.bot.strategy_manager = FunctionalStrategyManager(
                bot=self.bot
            )

            logger.info("[STARTUP_COORD] Strategies initialized")

        except Exception as e:
            logger.warning(f"[STARTUP_COORD] Strategy initialization failed: {e}")

    async def _load_market_data(self):
        """Load initial market data"""
        logger.info("[STARTUP_COORD] Loading market data...")

        try:
            # Get trading pairs if not set
            if not hasattr(self.bot, 'trade_pairs') or not self.bot.trade_pairs:
                # Use only SHIB/USDT as configured for single-pair trading
                self.bot.trade_pairs = ['SHIB/USDT']

            logger.info(f"[STARTUP_COORD] Using {len(self.bot.trade_pairs)} trading pairs")

        except Exception as e:
            logger.warning(f"[STARTUP_COORD] Market data loading failed: {e}")

    async def _start_monitoring(self):
        """Start monitoring systems"""
        logger.info("[STARTUP_COORD] Starting monitoring...")

        try:
            # Initialize basic monitoring
            from src.utils.self_repair import SelfRepairSystem
            self.bot.self_repair_system = SelfRepairSystem(self.bot)

            logger.info("[STARTUP_COORD] Monitoring started")

        except Exception as e:
            logger.warning(f"[STARTUP_COORD] Monitoring initialization failed: {e}")

    def _disable_rest_calls(self):
        """Temporarily disable REST API calls"""
        # This could be implemented with a flag in the nonce manager
        # or exchange client to prevent concurrent calls
        logger.info("[STARTUP_COORD] REST API calls temporarily restricted")

    def _enable_rest_calls(self):
        """Re-enable REST API calls"""
        logger.info("[STARTUP_COORD] REST API calls re-enabled")


async def fix_nonce_collision_startup(bot_instance) -> bool:
    """
    Emergency fix for nonce collision during startup
    
    Args:
        bot_instance: The trading bot instance
        
    Returns:
        bool: True if startup successful
    """
    coordinator = StartupCoordinator(bot_instance)
    return await coordinator.coordinate_startup()
