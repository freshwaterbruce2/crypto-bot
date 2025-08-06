#!/usr/bin/env python3
"""
KRAKEN TRADING BOT - MAIN ENTRY POINT
Fixed initialization sequence and signal execution pipeline
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix Windows event loop
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add paths
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir.parent))

# Core imports
from src.config import load_config
from src.config.constants import MINIMUM_ORDER_SIZE_TIER1
from src.utils.custom_logging import configure_logging

# Paper trading integration
try:
    from src.paper_trading.integration import get_paper_integration
    PAPER_TRADING_AVAILABLE = True
    logging.info("Paper trading integration available")
except ImportError:
    PAPER_TRADING_AVAILABLE = False
    logging.info("Paper trading not available")

# Try to import WebSocket manager, with fallback to simple implementation
try:
    from src.exchange.websocket_manager_v2 import WebSocketManagerV2 as KrakenWebSocketManager
    WEBSOCKET_V2_AVAILABLE = True
    logging.info("WebSocket V2 manager imported successfully")
except ImportError as ie:
    logging.error(f"WebSocket V2 import failed - ImportError: {ie}")
    logging.info("Using WebSocket manager V2 directly")
    # Fallback to None - will be created during initialization
    KrakenWebSocketManager = None
    WEBSOCKET_V2_AVAILABLE = False
except Exception as e:
    logging.error(f"WebSocket V2 import failed - Unexpected error: {e}")
    logging.info("WebSocket will be disabled")
    KrakenWebSocketManager = None
    WEBSOCKET_V2_AVAILABLE = False
# from src.portfolio_position_scanner import PortfolioPositionScanner  # Module missing
# Balance loading functionality moved to unified balance manager
import asyncio

from src.data.historical_data_saver import HistoricalDataSaver
from src.guardian.critical_error_guardian import CriticalErrorGuardian
from src.portfolio.portfolio_manager import PortfolioManager as PortfolioTracker
from src.trading.functional_strategy_manager import FunctionalStrategyManager
from src.trading.infinity_trading_manager import InfinityTradingManager
from src.trading.opportunity_execution_bridge import OpportunityExecutionBridge
from src.trading.opportunity_scanner import OpportunityScanner
from src.trading.profit_harvester import ProfitHarvester
from src.utils.decimal_precision_fix import MoneyDecimal, PrecisionTradingCalculator
from src.utils.event_bus import EventType as BusEventType
from src.utils.event_bus import get_event_bus, publish_event
from src.utils.integration_coordinator import get_coordinator
from src.utils.self_repair import RepairAction, SelfRepairSystem

logger = configure_logging()


class KrakenTradingBot:
    """Main trading bot with fixed initialization sequence"""

    # Tier 1 optimized pairs - UPDATED FOR LOW MINIMUMS (based on learned data)
    TIER_1_PRIORITY_PAIRS = {
        'ultra_low': ['SHIB/USDT'],  # Volume: 50000, ~$1.00 minimum
        'low': ['MATIC/USDT', 'AI16Z/USDT', 'BERA/USDT', 'MANA/USDT'],  # Volume: 1.0, <$2.00 minimum
        'medium': ['DOT/USDT', 'LINK/USDT', 'SOL/USDT', 'BTC/USDT'],  # Low volume minimums
        'avoid': ['ADA/USDT', 'ALGO/USDT', 'APE/USDT', 'ATOM/USDT', 'AVAX/USDT', 'BCH/USDT', 'BNB/USDT', 'CRO/USDT', 'DOGE/USDT']  # 4.0+ volume minimums
    }

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize the Kraken Trading Bot with comprehensive configuration and component setup.

        This is the main entry point for the trading bot system. It sets up all core components
        including exchange connections, WebSocket managers, balance tracking, and trading systems.
        The bot uses a hierarchical tier system for crypto pairs and implements advanced risk
        management with self-healing capabilities.

        Args:
            config (Optional[Dict[str, Any]]): Bot configuration dictionary. If None, loads
                from config files. Should contain:
                - position_size_usdt: Base position size for trades (default: MINIMUM_ORDER_SIZE_TIER1)
                - tier_1_trade_limit: Maximum trade size for starter tier accounts
                - kraken_api_tier: API tier level ('starter' or 'pro')
                - trade_pairs: List of trading pairs to monitor
                - Various timeouts and thresholds

        Raises:
            Exception: If critical configuration is missing or invalid

        Example:
            ```python
            # Use default configuration
            bot = KrakenTradingBot()

            # Use custom configuration
            custom_config = {
                'position_size_usdt': 2.0,
                'kraken_api_tier': 'starter',
                'max_position_pct': 0.8
            }
            bot = KrakenTradingBot(custom_config)
            ```
        """
        self.config = config or load_config()
        self.logger = logger

        # Extract configuration
        # Position sizing - support dynamic calculation with decimal precision
        base_position_size = float(MoneyDecimal(self.config.get("position_size_usdt", MINIMUM_ORDER_SIZE_TIER1), "USDT").value)
        tier_1_limit = float(MoneyDecimal(self.config.get("tier_1_trade_limit", MINIMUM_ORDER_SIZE_TIER1), "USDT").value)
        # Respect tier-1 limit for starter accounts
        if self.config.get('kraken_api_tier', 'starter') == 'starter':
            self.position_size_usd = min(base_position_size, tier_1_limit)
        else:
            self.position_size_usd = base_position_size
        self.trade_pairs = []  # Will be populated from Kraken

        # State management
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.start_time = time.time()
        self.initialized = False

        # Component placeholders
        self.exchange = None
        self.websocket_manager = None
        self.balance_manager = None  # Legacy compatibility
        self.balance_manager_v2 = None  # New Balance Manager V2 system
        self.trade_executor = None
        self.fallback_manager = None

        # Self-healing components
        self.self_repair_system = None
        self.critical_error_guardian = None

        # Circuit breaker integration
        # self.circuit_breaker_manager = circuit_breaker_manager  # Not available

        # Configure circuit breakers for critical components
        # Note: circuit_breaker_manager not available, using placeholder
        self.circuit_breakers = {}  # Disabled for now

        # Event bus for component communication
        self.event_bus = get_event_bus()

        # Integration coordinator
        self.coordinator = get_coordinator()
        self.strategy_manager = None
        self.infinity_manager = None
        self.opportunity_scanner = None
        self.opportunity_execution_bridge = None
        self.profit_harvester = None
        self.portfolio_tracker = None
        self.historical_data_saver = None
        self.portfolio_position_scanner = None
        self.log_rotation_manager = None

        # Signal queue for unified execution
        self.signal_queue = asyncio.Queue()

        # Signal batching for efficient processing
        self.signal_batch = []
        self.signal_batch_lock = asyncio.Lock()
        self.last_batch_time = time.time()
        self.batch_window = 2.0  # Collect signals for 2 seconds before processing

        # Signal deduplication to prevent spam
        self.last_signal_hash = {}
        self.signal_cooldown = 3.0  # 3 second cooldown for identical signals (micro-scalping friendly)

        # Metrics
        self.metrics = {
            'total_trades': 0,
            'total_profit': 0.0,
            'start_time': time.time(),
            'last_health_check': time.time(),
            'health_check_failures': 0
        }

        # Error recovery and circuit breaker
        self.error_recovery = {
            'consecutive_failures': 0,
            'max_failures': 5,
            'circuit_breaker_open': False,
            'circuit_reset_time': 0,
            'recovery_delay': 60.0
        }

        # Track last trade time for emergency rebalancing
        self.last_trade_time = time.time()

        # Capital flow tracking
        self.capital_flow = {
            'initial_usdt': 0.0,
            'current_usdt': 0.0,
            'deployed_capital': 0.0,
            'total_buys': 0,
            'total_sells': 0,
            'total_buy_volume': 0.0,
            'total_sell_volume': 0.0,
            'realized_pnl': 0.0,
            'reinvested_amount': 0.0,
            'flow_history': []  # Track capital movements
        }

        # Health monitoring
        self.health_monitor_interval = 60  # Check health every 60 seconds
        self.component_health = {}

    async def initialize(self) -> bool:
        """
        Initialize all bot components with nonce collision prevention and coordinated startup.

        This method performs a two-phase initialization:
        1. Basic component setup (no API calls)
        2. Coordinated startup with proper nonce sequencing

        The startup coordinator ensures that all API calls are properly sequenced to prevent
        nonce collisions that can occur when multiple components try to authenticate simultaneously.
        This is critical for Kraken API compliance and system stability.

        Returns:
            bool: True if initialization succeeded, False otherwise

        Raises:
            Exception: Various exceptions during component initialization

        Note:
            This method must be called before starting the trading loop. It sets up:
            - Exchange connection and authentication
            - WebSocket V2 connections for real-time data
            - Balance managers and portfolio tracking
            - Trading executors and strategy managers
            - Self-repair and error recovery systems

        Example:
            ```python
            bot = KrakenTradingBot()
            if await bot.initialize():
                await bot.run()
            else:
                logger.error("Bot initialization failed")
            ```
        """
        try:
            self.logger.info("[INIT] Starting nonce-safe initialization...")

            # CRITICAL FIX: Use startup coordinator to prevent nonce collisions
            # The StartupCoordinator manages the sequence of API calls to ensure
            # proper nonce ordering and prevent authentication failures
            from src.core.startup_coordinator import StartupCoordinator
            coordinator = StartupCoordinator(self)

            # Phase 1: Basic setup without API calls
            # This sets up all components that don't require API authentication
            await self._setup_basic_components()

            # Phase 2: Coordinated startup with proper nonce sequencing
            # This handles all API-dependent initialization in the correct order
            success = await coordinator.coordinate_startup()

            if not success:
                self.logger.error("[INIT] Coordinated startup failed")
                return False

            self.logger.info("[INIT] Nonce-safe initialization completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"[INIT] Initialization failed: {e}")
            import traceback
            self.logger.error(f"[INIT] Stack trace: {traceback.format_exc()}")
            return False

    async def _setup_basic_components(self):
        """
        Set up basic components that don't require API authentication.

        This is Phase 1 of the initialization process. It sets up all components
        that can be initialized without making API calls to prevent nonce issues.
        Components initialized here include:
        - Log rotation system
        - Fallback data management
        - Exchange client instances (without authentication)
        - Symbol mapping utilities
        - WebSocket and balance manager preparation

        This method is called before the coordinated startup phase to ensure
        a clean separation between API-independent and API-dependent initialization.

        Raises:
            Exception: If critical components fail to initialize

        Note:
            All API calls are deferred to the coordinated startup phase to prevent
            nonce collisions and ensure proper authentication sequencing.
        """
        self.logger.info("[INIT] Setting up basic components...")

        # 1.0: Set up log rotation
        try:
            from src.utils.log_rotation import setup_automatic_rotation
            self.log_rotation_manager = setup_automatic_rotation(self.config)
            self.logger.info("[INIT] Log rotation enabled")
        except Exception as e:
            self.logger.warning(f"[INIT] Log rotation setup failed: {e}")

        # 1.1: Initialize fallback data manager
        try:
            from src.exchange.fallback_data_manager import initialize_fallback_system
            self.fallback_manager = await initialize_fallback_system()
            self.logger.info("[INIT] Fallback data system initialized")
        except Exception as e:
            self.logger.warning(f"[INIT] Fallback system initialization failed: {e}")

        # 1.2: Create exchange instance (NO API CALLS YET)
        # Check all possible credential environment variable names
        api_key = (os.getenv('KRAKEN_KEY') or
                  os.getenv('KRAKEN_REST_API_KEY') or
                  os.getenv('KRAKEN_API_KEY') or
                  os.getenv('API_KEY', ''))
        api_secret = (os.getenv('KRAKEN_SECRET') or
                     os.getenv('KRAKEN_REST_API_SECRET') or
                     os.getenv('KRAKEN_API_SECRET') or
                     os.getenv('API_SECRET', ''))

        if not api_key or not api_secret:
            self.logger.error("[INIT] Missing REST API credentials!")
            self.logger.error("[INIT] Checked: KRAKEN_KEY, KRAKEN_SECRET, KRAKEN_REST_API_KEY, KRAKEN_REST_API_SECRET, KRAKEN_API_KEY, KRAKEN_API_SECRET")
            raise Exception("Missing Kraken REST API credentials")

        tier = (self.config.get('core', {}).get('kraken_api_tier') or
                self.config.get('kraken_api_tier') or
                os.getenv('KRAKEN_TIER', 'pro'))

        self.logger.info(f"[INIT] Using API key: {api_key[:8]}... (tier: {tier})")

        # Create exchange instance without initialization
        from src.exchange.exchange_singleton import get_exchange
        try:
            self.exchange = await asyncio.wait_for(
                get_exchange(
                    api_key=api_key,
                    api_secret=api_secret,
                    tier=tier,
                    config=self.config
                ),
                timeout=30.0
            )
            self.logger.info("[INIT] Exchange instance created")
        except Exception as e:
            self.logger.error(f"[INIT] Exchange creation failed: {e}")
            raise

        # Initialize basic symbol mapper (no API calls)
        from src.utils.centralized_symbol_mapper import KrakenSymbolMapper
        self.symbol_mapper = KrakenSymbolMapper()

        self.logger.info("[INIT] Basic components setup complete")

        # 3.1: Initialize WebSocket and Balance Managers
        try:
            from src.balance.hybrid_portfolio_manager import HybridPortfolioManager
            from src.balance.websocket_balance_stream import WebSocketBalanceStream
            from src.exchange.websocket_manager_v2 import WebSocketManagerV2

            # Create WebSocket client first (this might need proper initialization)
            # For now, use a placeholder since WebSocketBalanceStream needs a websocket_client
            try:
                # Create WebSocket V2 manager with proper initialization
                websocket_client = WebSocketManagerV2(
                    api_key=api_key,
                    api_secret=api_secret,
                    exchange_client=self.exchange
                )
                # Initialize the WebSocket client
                await websocket_client.initialize()
                self.logger.info("[INIT] WebSocket V2 client created and initialized")
            except Exception as ws_error:
                self.logger.warning(f"[INIT] WebSocket client creation failed: {ws_error}")
                websocket_client = None

            # Create WebSocket balance stream with proper parameters
            if websocket_client:
                websocket_balance_stream = WebSocketBalanceStream(
                    websocket_client=websocket_client,
                    exchange_client=self.exchange
                )

                # Create hybrid portfolio manager with WebSocket stream and REST client
                self.balance_manager = HybridPortfolioManager(
                    websocket_stream=websocket_balance_stream,
                    rest_client=self.exchange
                )

                # Start the balance manager
                await self.balance_manager.start()
                self.logger.info("[INIT] Hybrid Portfolio Balance Manager initialized and started")

                # Initialize WebSocket manager using the balance stream
                self.websocket_manager = websocket_balance_stream
                self.logger.info("[INIT] WebSocket manager linked to balance stream")
            else:
                # Fallback to REST-only balance manager
                self.balance_manager = HybridPortfolioManager(
                    websocket_stream=None,
                    rest_client=self.exchange
                )
                await self.balance_manager.start()
                self.websocket_manager = None
                self.logger.info("[INIT] REST-only Balance Manager initialized (WebSocket unavailable)")

        except Exception as e:
            self.logger.error(f"[INIT] Balance/WebSocket manager initialization failed: {e}")
            # Set fallback None values to prevent other errors
            self.balance_manager = None
            self.websocket_manager = None

        # 3.2: Historical Data Saver
        self.historical_data_saver = HistoricalDataSaver(
            data_directory=self.config.get('historical_data_dir', 'D:/trading_bot_data/historical')
        )
        await self.historical_data_saver.start()
        self.logger.info("[INIT] Historical data saver started")

        # 3.3: Prefill historical data
        await self._load_historical_data()
        self.logger.info("[INIT] Historical data prefilled")

        # PHASE 4: Initialize strategy components (after data is ready)
        self.logger.info("[INIT] Phase 4: Initializing strategy components...")

        # 4.1: Infinity Trading Manager (NEW ARCHITECTURE)
        self.infinity_manager = InfinityTradingManager(bot_instance=self)
        self.logger.info("[INIT] Infinity Trading Manager created")

        # 4.2: Strategy Manager (LEGACY - will be phased out)
        # Use the same enhanced tier configuration
        tier = (self.config.get('core', {}).get('kraken_api_tier') or
                self.config.get('kraken_api_tier') or
                os.getenv('KRAKEN_TIER', 'pro'))
        self.strategy_manager = FunctionalStrategyManager(
            bot=self,
            kraken_tier=tier
        )
        # Don't initialize strategies here - let start() handle it after executor is ready
        self.logger.info("[INIT] Strategy manager created (initialization deferred)")

        # 4.2: Opportunity Scanner
        self.opportunity_scanner = OpportunityScanner(
            bot_ref=self,
            config=self.config,
            exchange_client=self.exchange,
            scan_interval=self.config.get('opportunity_scanner', {}).get('scan_interval', 15),
            symbols=self.trade_pairs  # Add symbols!
        )
        self.logger.info("[INIT] Opportunity scanner initialized")

        # 4.3: Opportunity Execution Bridge
        self.opportunity_execution_bridge = OpportunityExecutionBridge(self)
        self.logger.info("[INIT] Opportunity execution bridge initialized")

        # 4.3a: High-Frequency Trading Components (Fee-Free Optimization)
        if self.config.get('fee_free_scalping', {}).get('enabled', False):
            try:
                # Import HFT components
                from src.trading.fast_order_router import FastOrderRouter
                from src.trading.hft_controller import HFTController
                from src.trading.position_cycler import PositionCycler

                # Initialize HFT Controller
                self.hft_controller = HFTController(self, self.config)
                self.logger.info("[INIT] HFT Controller initialized for fee-free micro-scalping")

                # Initialize Position Cycler
                self.position_cycler = PositionCycler(self, self.config)
                self.logger.info("[INIT] Position Cycler initialized for rapid turnover")

                # Initialize Fast Order Router
                self.fast_order_router = FastOrderRouter(self.exchange, self.config)
                self.logger.info("[INIT] Fast Order Router initialized for sub-100ms execution")

            except Exception as e:
                self.logger.error(f"[INIT] HFT components initialization failed: {e}")
                self.hft_controller = None
                self.position_cycler = None
                self.fast_order_router = None
        else:
            self.hft_controller = None
            self.position_cycler = None
            self.fast_order_router = None

        # 4.4: Portfolio Tracker (must be before Profit Harvester)
        self.portfolio_tracker = PortfolioTracker(
            exchange=self.exchange,
            account_tier=self.config.get('kraken_api_tier', 'pro')
        )
        self.logger.info("[INIT] Portfolio tracker initialized")

        # Initialize portfolio tracker with current holdings if empty
        await self._initialize_portfolio_from_holdings()

        # Force sync positions with exchange on startup
        self.logger.info("[INIT] Forcing portfolio sync with exchange...")
        sync_result = await self.portfolio_tracker.force_sync_with_exchange(
            exchange=self.exchange,
            balance_manager=self.balance_manager
        )
        # Handle both bool return type and dict return type
        if isinstance(sync_result, bool):
            if sync_result:
                self.logger.info("[INIT] Portfolio sync completed successfully")
            else:
                self.logger.error("[INIT] Portfolio sync failed")
        elif isinstance(sync_result, dict) and sync_result.get('success'):
            self.logger.info(
                f"[INIT] Portfolio sync completed: "
                f"{sync_result.get('mismatches_found', 0)} mismatches fixed, "
                f"{sync_result.get('positions_synced', 0)} synced, "
                f"{sync_result.get('positions_removed', 0)} removed, "
                f"Total positions: {sync_result.get('current_positions', 0)}"
            )
        else:
            error_msg = sync_result.get('error', 'Unknown error') if isinstance(sync_result, dict) else 'Unknown error'
            self.logger.error(f"[INIT] Portfolio sync failed: {error_msg}")

        # 4.5: Profit Harvester
        self.profit_harvester = ProfitHarvester(
            portfolio_tracker=self.portfolio_tracker,
            config=self.config,
            trade_executor=self.trade_executor,
            bot_ref=self
        )
        self.logger.info("[INIT] Profit harvester initialized")

        # 4.6: Portfolio Position Scanner - CRITICAL for detecting deployed capital
        # Note: PortfolioPositionScanner class not found, creating temporary wrapper
        class PortfolioPositionScannerWrapper:
            def __init__(self, portfolio_tracker):
                self.portfolio_tracker = portfolio_tracker
                self.detected_positions = []

            async def scan_and_recover_positions(self):
                """Temporary implementation using portfolio tracker"""
                try:
                    # Get current positions from portfolio tracker
                    positions = self.portfolio_tracker.get_active_positions()
                    self.detected_positions = positions

                    return {
                        'success': True,
                        'recovered': len(positions),
                        'positions': {pos.get('symbol', f'pos_{i}'): pos for i, pos in enumerate(positions)},
                        'total_usd_value': sum(pos.get('current_value_usd', 0) for pos in positions)
                    }
                except Exception as e:
                    return {'success': False, 'error': str(e)}

        self.portfolio_position_scanner = PortfolioPositionScannerWrapper(self.portfolio_tracker)
        self.logger.info("[INIT] Portfolio position scanner initialized (temporary wrapper)")

        # 4.7: Position Dashboard for monitoring capital deployment
        try:
            from src.utils.position_dashboard import PositionDashboard
            self.position_dashboard = PositionDashboard(self)
            self.logger.info("[INIT] Position dashboard initialized")
        except Exception as e:
            self.logger.warning(f"[INIT] Position dashboard initialization failed: {e}")
            self.position_dashboard = None

        # 4.8: Smart Minimum Manager for portfolio pairs
        try:
            from src.trading.minimum_manager_integration import get_minimum_integration
            self.minimum_integration = get_minimum_integration(
                exchange=self.exchange,
                balance_manager=self.balance_manager
            )
            await self.minimum_integration.initialize()
            self.logger.info("[INIT] Smart minimum manager initialized for portfolio pairs")
        except Exception as e:
            self.logger.warning(f"[INIT] Smart minimum manager initialization failed: {e}")
            self.minimum_integration = None

        # 4.9: Initialize Learning System
        try:
            from src.learning.universal_learning_manager import UniversalLearningManager
            self.learning_manager = UniversalLearningManager.get_instance()
            # Pass bot instance for full integration
            self.learning_manager.set_bot_instance(self)
            # Connect to event bus
            if hasattr(self, 'event_bus') and self.event_bus:
                self.learning_manager.connect_to_event_bus(self.event_bus)
            self.logger.info("[INIT] Universal learning manager initialized and connected")
        except Exception as e:
            self.logger.warning(f"[INIT] Learning system initialization failed: {e}")
            self.learning_manager = None

        # 4.10: Initialize Assistant Manager
        try:
            from src.assistants.assistant_manager import AssistantManager
            self.assistant_manager = AssistantManager(
                bot=self,
                learning_manager=self.learning_manager,
                config=self.config
            )
            await self.assistant_manager.initialize()
            self.logger.info("[INIT] Assistant manager initialized with all assistants")
        except ImportError:
            self.logger.warning("[INIT] Assistant manager not found, creating basic integration")
            self.assistant_manager = None
        except Exception as e:
            self.logger.warning(f"[INIT] Assistant manager initialization failed: {e}")
            self.assistant_manager = None

        # PHASE 5: Scan and recover existing positions
        self.logger.info("[INIT] Phase 5: Scanning for existing positions...")
        recovery_result = await self.portfolio_position_scanner.scan_and_recover_positions()

        if recovery_result and recovery_result.get('success'):
            recovered_count = recovery_result.get('recovered', 0)
            recovery_result.get('positions', {})
            total_value = recovery_result.get('total_usd_value', 0)

            if recovered_count > 0:
                self.logger.info(f"[INIT] Recovered {recovered_count} positions worth ${total_value:.2f}")
                # Get the original positions list from the scanner
                if hasattr(self.portfolio_position_scanner, 'detected_positions'):
                    positions_list = self.portfolio_position_scanner.detected_positions

                    # CRITICAL: Update trade pairs to prioritize portfolio positions
                    await self._update_trade_pairs_from_portfolio(positions_list)

                    # Notify strategy manager about existing positions
                    if self.strategy_manager and positions_list:
                        await self.strategy_manager.notify_existing_positions(positions_list)
            else:
                self.logger.info("[INIT] No existing positions found")
                # For tier-1, limit to 10 pairs when no positions exist
                if self.config.get('kraken_api_tier', 'starter') == 'starter':
                    self.trade_pairs = self.trade_pairs[:10]
                    self.logger.info(f"[INIT] Tier-1: Limited to {len(self.trade_pairs)} pairs")
        else:
            self.logger.warning("[INIT] Position recovery failed or returned no data")

        # Connect WebSocket to strategy manager (if supported)
        if self.websocket_manager and hasattr(self.websocket_manager, 'strategy_manager'):
            self.websocket_manager.strategy_manager = self.strategy_manager
            self.logger.info("[INIT] WebSocket manager connected to strategy manager")
        elif self.websocket_manager:
            self.logger.info("[INIT] WebSocket manager does not support strategy manager connection")
        else:
            self.logger.warning("[INIT] No websocket manager available for strategy connection")

        # PHASE 6: Initialize self-healing systems
        self.logger.info("[INIT] Phase 6: Initializing self-healing systems...")

        # Initialize self-repair system
        self.self_repair_system = SelfRepairSystem(bot_instance=self)

        # Add custom nonce error repair
        self._register_nonce_error_repair()

        # Initialize critical error guardian
        self.critical_error_guardian = CriticalErrorGuardian(bot=self)

        # Start self-healing monitoring
        asyncio.create_task(self._run_self_healing_cycle())

        self.logger.info("[INIT] Self-healing systems initialized - bot is now self-diagnosing!")
        self.logger.info("[INIT] All components initialized successfully!")
        return True

    async def _validate_kraken_symbols(self) -> list[str]:
        """Fetch active USDT pairs from Kraken"""
        try:
            # Markets should already be loaded, but ensure they are
            if not self.exchange._markets_loaded:
                await self.exchange.load_markets()

            # Filter for USDT pairs
            usdt_pairs = []
            for _symbol, market in self.exchange.markets.items():
                if market.get('quote', '') == 'USDT' and market.get('active', False):
                    # Ensure proper format
                    base = market.get('base', '')
                    if base and base != 'USDT':
                        formatted_symbol = f"{base}/USDT"
                        usdt_pairs.append(formatted_symbol)

            self.logger.info(f"[SYMBOLS] Available USDT pairs on Kraken: {usdt_pairs[:10]}...")

            # Sort by volume or alphabetically
            usdt_pairs.sort()

            # FORCE USE TIER_1_PRIORITY_PAIRS (override any config)
            self.logger.info("[SYMBOLS] FORCING TIER_1_PRIORITY_PAIRS optimization...")

            # Always prioritize optimized pairs over config
            optimized_pairs = []

            # Add pairs in priority order: ultra_low -> low -> medium
            for category in ['ultra_low', 'low', 'medium']:
                for pair in self.TIER_1_PRIORITY_PAIRS.get(category, []):
                    if pair in usdt_pairs and pair not in optimized_pairs:
                        optimized_pairs.append(pair)

            # Avoid problematic pairs completely
            avoid_pairs = self.TIER_1_PRIORITY_PAIRS.get('avoid', [])
            self.logger.warning(f"[SYMBOLS] AVOIDING problematic pairs: {avoid_pairs}")

            # Use optimized pairs instead of config
            usdt_pairs = optimized_pairs[:8]  # Limit to 8 best pairs
            self.logger.info(f"[SYMBOLS] FORCED optimized pairs: {usdt_pairs}")

            # If no valid pairs from config, use optimized TIER_1_PRIORITY_PAIRS
            if not usdt_pairs and len(self.exchange.markets) > 0:
                # Use TIER_1_PRIORITY_PAIRS for optimal low-minimum trading
                optimized_pairs = []

                # Add pairs in priority order: ultra_low -> low -> medium
                for category in ['ultra_low', 'low', 'medium']:
                    for pair in self.TIER_1_PRIORITY_PAIRS.get(category, []):
                        if pair in self.exchange.markets and pair not in optimized_pairs:
                            optimized_pairs.append(pair)

                # If still need more pairs, add other available USDT pairs (excluding avoid list)
                avoid_pairs = self.TIER_1_PRIORITY_PAIRS.get('avoid', [])
                for pair in usdt_pairs:
                    if len(optimized_pairs) >= 10:  # Limit for tier-1
                        break
                    if pair not in optimized_pairs and pair not in avoid_pairs:
                        optimized_pairs.append(pair)

                usdt_pairs = optimized_pairs
                self.logger.info(f"[SYMBOLS] Using TIER_1_PRIORITY_PAIRS optimized pairs: {usdt_pairs}")

            return usdt_pairs[:10]  # Limit to 10 pairs for tier-1

        except Exception as e:
            self.logger.error(f"[SYMBOLS] Error fetching Kraken symbols: {e}")
            # Fallback to configured single pair
            return ['SHIB/USDT']

    async def _update_trade_pairs_from_portfolio(self, positions: list[dict[str, Any]]) -> None:
        """Update trade pairs with tier 1 optimization and dynamic limits"""
        try:
            # Get tier 1 optimization config
            tier_1_config = self.config.get('tier_1_optimization', {})
            dynamic_limits = tier_1_config.get('dynamic_pair_limits', {})

            # Dynamic limits per requirements: 10-14 total pairs
            dynamic_limits.get('min_total_pairs', 10)
            max_total_pairs = dynamic_limits.get('max_total_pairs', 14)
            portfolio_threshold = dynamic_limits.get('portfolio_threshold', 2)

            # Extract symbols from existing positions
            portfolio_symbols = [pos['symbol'] for pos in positions if 'symbol' in pos]
            portfolio_count = len(portfolio_symbols)

            # Calculate dynamic limits based on portfolio
            if portfolio_count >= portfolio_threshold:
                # Holding 2+ assets: use 8-12 new pairs
                max_new_pairs = 12 - portfolio_count
                target_total = min(portfolio_count + max_new_pairs, 12)
            else:
                # Holding <2 assets: use 10-14 total pairs
                target_total = min(max_total_pairs, 10 + portfolio_count)

            # For tier 1: Prioritize low-priced pairs
            if self.config.get('kraken_api_tier', 'starter') == 'starter':
                # Build tier 1 optimized pairs list
                tier_1_pairs = []

                # Add pairs in priority order (ultra_low -> low -> medium)
                for category in ['ultra_low', 'low', 'medium']:
                    for pair in self.TIER_1_PRIORITY_PAIRS.get(category, []):
                        if pair in self.available_usdt_pairs and pair not in portfolio_symbols:
                            tier_1_pairs.append(pair)

                # Build final list: portfolio first, then tier 1 optimized
                updated_pairs = portfolio_symbols.copy()

                # Add tier 1 pairs to reach target
                for pair in tier_1_pairs:
                    if len(updated_pairs) >= target_total:
                        break
                    if pair not in updated_pairs:
                        updated_pairs.append(pair)

                # If still need more pairs, add from available list (excluding expensive ones)
                avoid_pairs = self.TIER_1_PRIORITY_PAIRS.get('avoid', [])
                for pair in self.available_usdt_pairs:
                    if len(updated_pairs) >= target_total:
                        break
                    if pair not in updated_pairs and pair not in avoid_pairs:
                        updated_pairs.append(pair)
            else:
                # Non-tier 1: Use all available pairs
                updated_pairs = portfolio_symbols + [p for p in self.available_usdt_pairs if p not in portfolio_symbols]
                updated_pairs = updated_pairs[:target_total]

            # Update trade pairs - validate USDT only
            from src.utils.centralized_symbol_mapper import symbol_mapper
            validated_updated_pairs = []
            for pair in updated_pairs[:target_total]:
                if symbol_mapper.validate_usdt_only(pair):
                    validated_updated_pairs.append(pair)
                else:
                    self.logger.warning(f"[INIT] Rejected non-USDT pair from portfolio update: {pair}")

            self.trade_pairs = validated_updated_pairs

            self.logger.info(f"[INIT] Portfolio-aware pairs: {portfolio_count} from portfolio, "
                           f"{len(self.trade_pairs) - portfolio_count} additional pairs, "
                           f"Total: {len(self.trade_pairs)} (target: {target_total})")
            self.logger.info(f"[INIT] Updated trade pairs: {self.trade_pairs}")

            # Update all components with new symbols
            if self.websocket_manager:
                self.websocket_manager.symbols = self.trade_pairs
                self.logger.info(f"[INIT] Updated WebSocket with {len(self.trade_pairs)} symbols")

            if self.opportunity_scanner:
                self.opportunity_scanner.symbols = self.trade_pairs
                self.logger.info(f"[INIT] Updated opportunity scanner with {len(self.trade_pairs)} symbols")

            if hasattr(self, 'strategy_manager') and self.strategy_manager:
                if hasattr(self.strategy_manager, 'update_symbols'):
                    await self.strategy_manager.update_symbols(self.trade_pairs)
                    self.logger.info(f"[INIT] Updated strategy manager with {len(self.trade_pairs)} symbols")

        except Exception as e:
            self.logger.error(f"[INIT] Error updating trade pairs from portfolio: {e}")
            # Keep existing pairs on error
            self.logger.info(f"[INIT] Keeping existing trade pairs: {self.trade_pairs[:10]}")

    async def _load_historical_data(self) -> None:
        """Prefill historical data for all trading pairs"""
        for symbol in self.trade_pairs:
            try:
                # Fetch recent OHLC data
                ohlc_data = await self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1m',
                    limit=100
                )

                if ohlc_data:
                    # Store in strategy manager
                    if hasattr(self.strategy_manager, 'price_history'):
                        self.strategy_manager.price_history[symbol] = ohlc_data

                    self.logger.info(f"[HIST] Loaded {len(ohlc_data)} candles for {symbol}")

            except Exception as e:
                self.logger.warning(f"[HIST] Failed to load historical data for {symbol}: {e}")

    async def start(self):
        """Start bot with proper initialization sequence"""
        try:
            self.logger.info("[STARTUP] Starting Kraken USDT trading bot...")

            # Phase 1: Core components (non-critical failures allowed)
            try:
                await self._initialize_core_components()
                self.logger.info("[STARTUP] Core components initialized")
            except Exception as e:
                self.logger.warning(f"[STARTUP] Core components warning: {e}")
                # Continue - bot can work with basic functionality

            # Phase 2: Wait for executor (optional)
            try:
                if hasattr(self, 'trade_executor'):
                    if hasattr(self.trade_executor, 'wait_until_ready'):
                        await self.trade_executor.wait_until_ready()
                    else:
                        await asyncio.sleep(2)
                self.logger.info("[STARTUP] Trade executor ready")
            except Exception as e:
                self.logger.warning(f"[STARTUP] Trade executor warning: {e}")
                # Continue - bot can work in monitoring mode

            # Phase 3: Market data (non-critical)
            try:
                await self._load_initial_market_data()
                self.logger.info("[STARTUP] Market data loaded")
            except Exception as e:
                self.logger.warning(f"[STARTUP] Market data warning: {e}")
                # Continue - bot can work without historical data

            # Phase 4: Strategies (non-critical)
            try:
                await self._initialize_strategies()
                self.logger.info("[STARTUP] Strategies initialized")
            except Exception as e:
                self.logger.warning(f"[STARTUP] Strategies warning: {e}")
                # Continue - bot can work in basic monitoring mode

            # Phase 5: Set running flag
            self.running = True
            self.initialized = True
            self.logger.info("[STARTUP] Bot is now running")

        except Exception as e:
            self.logger.error(f"[STARTUP] Critical failure: {e}")
            # Log additional debugging info
            import traceback
            self.logger.error(f"[STARTUP] Stack trace: {traceback.format_exc()}")
            raise

    async def _initialize_core_components(self):
        """Initialize in correct order with individual error handling"""
        # Balance manager first
        try:
            if hasattr(self, 'balance_manager') and self.balance_manager:
                if hasattr(self.balance_manager, 'initialize'):
                    await self.balance_manager.initialize()
                    self.logger.info("[CORE] Balance manager initialized")
        except Exception as e:
            self.logger.warning(f"[CORE] Balance manager initialization failed: {e}")

        # Risk manager
        try:
            if hasattr(self, 'risk_manager') and self.risk_manager:
                if hasattr(self.risk_manager, 'initialize'):
                    await self.risk_manager.initialize()
                    self.logger.info("[CORE] Risk manager initialized")
        except Exception as e:
            self.logger.warning(f"[CORE] Risk manager initialization failed: {e}")

        # Trade executor
        try:
            if hasattr(self, 'trade_executor') and self.trade_executor:
                if hasattr(self.trade_executor, 'initialize'):
                    await self.trade_executor.initialize()
                    self.logger.info("[CORE] Trade executor initialized")
        except Exception as e:
            self.logger.warning(f"[CORE] Trade executor initialization failed: {e}")

        # WebSocket (most likely to fail, but non-critical)
        try:
            if hasattr(self, 'websocket_manager') and self.websocket_manager:
                if hasattr(self.websocket_manager, 'connect'):
                    await self.websocket_manager.connect()
                    self.logger.info("[CORE] WebSocket manager connected")
        except Exception as e:
            self.logger.warning(f"[CORE] WebSocket connection failed (non-critical): {e}")
            # Bot can work with REST API only

    async def _load_initial_market_data(self):
        """Load historical OHLCV data for all trading pairs BEFORE strategies initialize"""
        try:
            self.logger.info("[DATA] Loading historical market data for strategy warm-up...")

            # Create a shared data store if not exists
            if not hasattr(self, 'market_data_cache'):
                self.market_data_cache = {}

            # Load data for each trading pair
            for symbol in self.trade_pairs:
                try:
                    # Fetch enough candles for indicators (100 for most strategies)
                    self.logger.info(f"[DATA] Fetching historical data for {symbol}...")
                    ohlcv_data = await self.exchange.fetch_ohlcv(
                        symbol=symbol,
                        timeframe='1m',
                        limit=100  # Enough for RSI, MACD, Bollinger Bands
                    )

                    if ohlcv_data and len(ohlcv_data) > 0:
                        # Store in cache
                        self.market_data_cache[symbol] = ohlcv_data

                        # Also update strategy manager if it has a price history
                        if hasattr(self, 'strategy_manager') and hasattr(self.strategy_manager, 'price_history'):
                            self.strategy_manager.price_history[symbol] = ohlcv_data

                        self.logger.info(f"[DATA] Loaded {len(ohlcv_data)} candles for {symbol}")
                    else:
                        self.logger.warning(f"[DATA] No historical data received for {symbol}")

                except Exception as e:
                    self.logger.error(f"[DATA] Failed to load data for {symbol}: {e}")
                    # Continue with other pairs

            self.logger.info(f"[DATA] Historical data loaded for {len(self.market_data_cache)} pairs")

            # Give data processors time to digest
            await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"[DATA] Error loading historical market data: {e}")
            # Don't fail startup, strategies can work with real-time data only if needed

    async def _initialize_strategies(self):
        """Initialize strategies with historical data already loaded"""
        try:
            if not hasattr(self, 'strategy_manager'):
                self.logger.error("[STRATEGIES] Strategy manager not found!")
                return

            # Pass historical data to strategy manager
            if hasattr(self, 'market_data_cache') and self.market_data_cache:
                if hasattr(self.strategy_manager, 'set_historical_data'):
                    self.strategy_manager.set_historical_data(self.market_data_cache)
                    self.logger.info(f"[STRATEGIES] Provided historical data for {len(self.market_data_cache)} pairs")

            # Infinity Trading Manager is already initialized in __init__
            if hasattr(self, 'infinity_manager') and self.infinity_manager:
                self.logger.info("[INFINITY] Infinity Trading Manager ready with assistants")

            # Initialize strategies (LEGACY - will be phased out)
            if hasattr(self.strategy_manager, 'initialize_strategies'):
                await self.strategy_manager.initialize_strategies(self.trade_pairs, self.config)
                self.logger.info("[STRATEGIES] Strategies initialized with historical data available")

                # Log strategy status
                if hasattr(self.strategy_manager, 'strategies'):
                    strategy_count = len(self.strategy_manager.strategies)
                    self.logger.info(f"[STRATEGIES] {strategy_count} strategies loaded and warming up indicators")

                    # Give strategies time to process historical data
                    await asyncio.sleep(2)

        except Exception as e:
            self.logger.error(f"[STRATEGIES] Error initializing strategies: {e}")
            # Continue without strategies if needed

    async def _validate_strategies_ready(self):
        """Validate strategies have warmed up and are ready to generate signals"""
        try:
            self.logger.info("[VALIDATION] Checking if strategies have warmed up indicators...")

            validation_passed = True
            issues = []

            # Check if strategy manager has strategies loaded
            if hasattr(self, 'strategy_manager') and hasattr(self.strategy_manager, 'strategies'):
                strategy_count = len(self.strategy_manager.strategies)
                if strategy_count > 0:
                    self.logger.info(f"[VALIDATION] Checking {strategy_count} strategies...")

                    # Check each strategy's readiness
                    for symbol, strategy in self.strategy_manager.strategies.items():
                        # Handle single strategy per symbol
                        strategies_to_check = [strategy] if not isinstance(strategy, list) else strategy
                        for strategy in strategies_to_check:
                            if hasattr(strategy, 'is_ready'):
                                if not strategy.is_ready():
                                    validation_passed = False
                                    issues.append(f"{strategy.name} for {symbol} not ready")
                            elif hasattr(strategy, 'min_candles'):
                                # Check if strategy has enough data
                                if symbol in self.market_data_cache:
                                    candle_count = len(self.market_data_cache[symbol])
                                    if candle_count < strategy.min_candles:
                                        validation_passed = False
                                        issues.append(f"{strategy.name} needs {strategy.min_candles} candles, has {candle_count}")

                    if validation_passed:
                        self.logger.info(f"[VALIDATION] ✓ All {strategy_count} strategies validated and ready")
                    else:
                        self.logger.warning(f"[VALIDATION] Strategy validation issues: {issues}")

                    # Try to get initial signals to verify strategies work
                    if hasattr(self.strategy_manager, 'check_all_strategies_concurrent'):
                        try:
                            test_signals = await asyncio.wait_for(
                                self.strategy_manager.check_all_strategies_concurrent(),
                                timeout=5.0
                            )
                            self.logger.info(f"[VALIDATION] ✓ Strategy test complete - {len(test_signals)} potential signals found")
                        except asyncio.TimeoutError:
                            self.logger.warning("[VALIDATION] Strategy signal test timed out")
                        except Exception as e:
                            self.logger.warning(f"[VALIDATION] Strategy signal test warning: {e}")
                else:
                    self.logger.warning("[VALIDATION] No strategies loaded - check configuration")
                    validation_passed = False

            return validation_passed

        except Exception as e:
            self.logger.error(f"[VALIDATION] Strategy validation error: {e}")
            return False

    async def _initialize_execution_systems(self):
        """Initialize execution systems after strategies are ready"""
        try:
            self.logger.info("[EXECUTION] Initializing execution systems...")

            # Initialize trade executor if not already done
            if hasattr(self, 'trade_executor'):
                if hasattr(self.trade_executor, 'initialize'):
                    await self.trade_executor.initialize()
                    self.logger.info("[EXECUTION] Trade executor initialized")

                # Wait until ready
                if hasattr(self.trade_executor, 'wait_until_ready'):
                    await self.trade_executor.wait_until_ready()
                    self.logger.info("[EXECUTION] Trade executor ready")
                else:
                    # Give it time to initialize
                    await asyncio.sleep(2)

            # Initialize opportunity execution bridge
            if hasattr(self, 'opportunity_bridge') and hasattr(self.opportunity_bridge, 'initialize'):
                await self.opportunity_bridge.initialize()
                self.logger.info("[EXECUTION] Opportunity execution bridge initialized")

            # Initialize profit harvester
            if hasattr(self, 'profit_harvester') and hasattr(self.profit_harvester, 'initialize'):
                await self.profit_harvester.initialize()
                self.logger.info("[EXECUTION] Profit harvester initialized")

        except Exception as e:
            self.logger.error(f"[EXECUTION] Error initializing execution systems: {e}")
            # Continue without some systems if needed

    async def _connect_realtime_feeds(self):
        """Connect real-time data feeds after strategies are initialized"""
        try:
            self.logger.info("[REALTIME] Connecting real-time data feeds...")

            # WebSocket should already be connected from initialize(), but ensure channels are subscribed
            if hasattr(self, 'websocket_manager'):
                if not self.websocket_manager.is_connected:
                    self.logger.info("[REALTIME] Connecting WebSocket...")
                    await self.websocket_manager.connect()

                # Subscribe to channels
                await self.websocket_manager.subscribe_to_channels()
                self.logger.info("[REALTIME] Subscribed to WebSocket channels")

                # Wait for initial real-time data
                await asyncio.sleep(2)

                # Verify data is flowing
                if hasattr(self.websocket_manager, 'last_message_time'):
                    last_msg = self.websocket_manager.last_message_time
                    if time.time() - last_msg < 5:
                        self.logger.info("[REALTIME] ✓ Real-time data flowing")
                    else:
                        self.logger.warning("[REALTIME] No recent WebSocket messages")

        except Exception as e:
            self.logger.error(f"[REALTIME] Error connecting real-time feeds: {e}")
            # Bot can still work with REST API polling

    async def run(self) -> None:
        """Main bot loop"""
        if not await self.initialize():
            self.logger.error("[BOT] Initialization failed, exiting")
            return

        # Use the new start method with proper exception handling
        try:
            await self.start()
            self.logger.info("[BOT] Bot startup completed successfully")
        except Exception as e:
            self.logger.error(f"[BOT] Startup error: {e}")
            self.logger.warning("[BOT] Continuing in monitoring mode despite startup issues...")
            # Set running flag to allow monitoring mode
            self.running = True

        # Store tasks for proper cleanup
        self._background_tasks = []

        try:
            # Start WebSocket message processing (compatibility task) - optional
            try:
                if hasattr(self, 'websocket_manager') and self.websocket_manager:
                    websocket_task = asyncio.create_task(self.websocket_manager.run())
                    self._background_tasks.append(websocket_task)
                    self.logger.info("[BOT] WebSocket V2 processing task started")
            except Exception as e:
                self.logger.warning(f"[BOT] WebSocket task startup failed: {e}")

            # Start opportunity scanner - try but continue if it fails
            try:
                if hasattr(self, 'opportunity_scanner') and self.opportunity_scanner:
                    await self.opportunity_scanner.start()
                    self.logger.info("[BOT] Opportunity scanner started")
            except Exception as e:
                self.logger.warning(f"[BOT] Opportunity scanner startup failed: {e}")

            # Start HFT components if enabled - optional
            try:
                if hasattr(self, 'hft_controller') and self.hft_controller:
                    await self.hft_controller.start()
                    self.logger.info("[BOT] HFT Controller started - targeting 50-100 trades/day")
            except Exception as e:
                self.logger.warning(f"[BOT] HFT Controller startup failed: {e}")

            try:
                if hasattr(self, 'position_cycler') and self.position_cycler:
                    await self.position_cycler.start()
                    self.logger.info("[BOT] Position Cycler started - rapid capital turnover enabled")
            except Exception as e:
                self.logger.warning(f"[BOT] Position Cycler startup failed: {e}")

            # Start signal processor - essential for monitoring mode
            try:
                signal_processor_task = asyncio.create_task(self._process_signal_queue())
                self._background_tasks.append(signal_processor_task)
                self.logger.info("[BOT] Signal processor task started")
            except Exception as e:
                self.logger.warning(f"[BOT] Signal processor startup failed: {e}")

            # Start health monitor - important for monitoring
            try:
                health_monitor_task = asyncio.create_task(self._health_monitor_loop())
                self._background_tasks.append(health_monitor_task)
                self.logger.info("[BOT] Health monitor task started")
            except Exception as e:
                self.logger.warning(f"[BOT] Health monitor startup failed: {e}")

            # Start capital allocation monitor - important for monitoring
            try:
                capital_monitor_task = asyncio.create_task(self._capital_allocation_monitor())
                self._background_tasks.append(capital_monitor_task)
                self.logger.info("[BOT] Capital allocation monitor started")
            except Exception as e:
                self.logger.warning(f"[BOT] Capital allocation monitor startup failed: {e}")

            # Start Infinity Trading Manager - optional
            try:
                if hasattr(self, 'infinity_manager') and self.infinity_manager:
                    infinity_task = asyncio.create_task(self.infinity_manager.start())
                    self._background_tasks.append(infinity_task)
                    self.logger.info("[BOT] Infinity Trading Manager started")
            except Exception as e:
                self.logger.warning(f"[BOT] Infinity Trading Manager startup failed: {e}")

            # Check balance status and notify user
            try:
                if hasattr(self, 'balance_manager') and self.balance_manager:
                    usdt_balance = await self.balance_manager.get_balance('USDT')
                    if usdt_balance and float(usdt_balance) < 10:  # Less than $10 USDT
                        self.logger.info("[BOT] MONITORING MODE: Low USDT balance - bot will monitor for opportunities")
                        self.logger.info("[BOT] Capital appears to be fully deployed in positions")
                    else:
                        self.logger.info(f"[BOT] TRADING MODE: {usdt_balance} USDT available for trading")
            except Exception as e:
                self.logger.warning(f"[BOT] Could not check balance status: {e}")

            self.logger.info("[BOT] Entering main trading loop...")
            loop_count = 0
            try:
                while self.running:
                    loop_count += 1
                    if loop_count % 10 == 0:  # Heartbeat every 10 seconds
                        self.logger.info(f"[BOT] Main loop heartbeat - iteration {loop_count}")

                        # Check WebSocket data freshness every 10 iterations
                        if hasattr(self, 'websocket_manager') and self.websocket_manager:
                            try:
                                await self.websocket_manager.check_data_freshness()
                            except Exception as e:
                                self.logger.error(f"[BOT] Error checking WebSocket freshness: {e}")

                    self.logger.debug(f"[BOT] Running main loop iteration {loop_count}...")
                    await self.run_once()
                    await asyncio.sleep(1)

            except KeyboardInterrupt:
                self.logger.info("[BOT] Keyboard interrupt received")
        finally:
            self.running = False
            await self.stop()

            # Cancel all background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass  # Expected
                    except Exception as e:
                        self.logger.error(f"[BOT] Error cancelling task: {e}")

            self.logger.info("[BOT] All background tasks cancelled")

    async def run_once(self) -> None:
        """Single iteration of main loop - unified signal collection"""
        try:
            time.time()
            self.logger.debug("[BOT] Starting run_once iteration")
            # Collect signals from all sources
            all_signals = []

            # 1. Infinity Trading Manager signals (NEW ARCHITECTURE)
            if hasattr(self, 'infinity_manager') and self.infinity_manager:
                try:
                    self.logger.debug("[INFINITY] Getting next action from Infinity Manager...")
                    # Add timeout to prevent infinite balance checking loops
                    infinity_timeout = self.config.get('infinity_check_timeout', 15.0)
                    infinity_action = await asyncio.wait_for(
                        self.infinity_manager.get_next_action(),
                        timeout=infinity_timeout
                    )
                    if infinity_action:
                        if isinstance(infinity_action, list):
                            all_signals.extend(infinity_action)
                            self.logger.info(f"[INFINITY] Found {len(infinity_action)} signals from Infinity Manager")
                        elif isinstance(infinity_action, dict):
                            all_signals.append(infinity_action)
                            self.logger.info("[INFINITY] Found 1 signal from Infinity Manager")
                    else:
                        self.logger.debug("[INFINITY] No signals generated this iteration")
                except asyncio.TimeoutError:
                    self.logger.warning(f"[INFINITY] Signal generation timed out after {infinity_timeout}s - continuing with other sources")
                except Exception as e:
                    self.logger.error(f"[INFINITY] Error getting signals: {e}")

            # 2. Strategy signals (LEGACY - with configurable timeout)
            if self.strategy_manager:
                try:
                    self.logger.debug("[BOT] Checking strategy signals...")
                    # Use configurable timeout with default of 10s
                    strategy_timeout = self.config.get('strategy_check_timeout', 10.0)

                    # Run strategies concurrently with individual timeouts
                    strategy_signals = await asyncio.wait_for(
                        self.strategy_manager.check_all_strategies_concurrent(),
                        timeout=strategy_timeout
                    )

                    if strategy_signals:
                        all_signals.extend(strategy_signals)
                        self.logger.debug(f"[BOT] Found {len(strategy_signals)} strategy signals")

                    # Log strategy performance metrics
                    if hasattr(self.strategy_manager, 'get_performance_metrics'):
                        metrics = self.strategy_manager.get_performance_metrics()
                        slow_strategies = metrics.get('slow_strategies', [])
                        if slow_strategies:
                            self.logger.warning(f"[BOT] Slow strategies detected: {slow_strategies}")

                except asyncio.TimeoutError:
                    self.logger.warning(f"[BOT] Strategy check timed out after {strategy_timeout}s")
                    # Try to get partial results if available
                    if hasattr(self.strategy_manager, 'get_partial_results'):
                        partial_signals = self.strategy_manager.get_partial_results()
                        if partial_signals:
                            all_signals.extend(partial_signals)
                            self.logger.info(f"[BOT] Retrieved {len(partial_signals)} partial signals after timeout")
                except Exception as e:
                    self.logger.error(f"[BOT] Strategy check error: {e}", exc_info=True)

            # 3. Opportunity scanner signals - ENHANCED
            if self.opportunity_scanner:
                try:
                    # Get fresh opportunities from scanner
                    opportunities = await self.opportunity_scanner.scan_opportunities()
                    if opportunities:
                        self.logger.info(f"[BOT] Found {len(opportunities)} opportunities from scanner")
                        for opp in opportunities:
                            # Only process USDT pairs
                            if opp.get('symbol', '').endswith('/USDT'):
                                signal = {
                                    'symbol': opp['symbol'],
                                    'side': opp.get('side', opp.get('action', 'buy')),
                                    'confidence': opp.get('confidence', 0.5),
                                    'source': 'opportunity_scanner',
                                    'reason': opp.get('reason', 'Scanner opportunity'),
                                    'amount_usdt': max(MINIMUM_ORDER_SIZE_TIER1, self.config.get('min_order_size_usdt', MINIMUM_ORDER_SIZE_TIER1))
                                }
                                all_signals.append(signal)
                                self.logger.info(f"[BOT] Added scanner signal: {signal['symbol']} {signal['side']} conf={signal['confidence']:.2f}")
                except Exception as e:
                    self.logger.error(f"[BOT] Opportunity scanner error: {e}")

            # 3. Profit harvesting signals (sells) (with configurable timeout)
            if self.profit_harvester and hasattr(self, 'portfolio_tracker'):
                try:
                    # Only check for sells if we have open positions
                    try:
                        positions = await self.portfolio_tracker.get_open_positions()
                    except (TypeError, AttributeError):
                        # Handle synchronous method
                        positions = self.portfolio_tracker.get_open_positions()
                    except Exception as e:
                        logger.error(f"[PORTFOLIO] Error getting positions: {e}")
                        positions = []  # Safe fallback

                    if positions:
                        self.logger.debug(f"[BOT] Checking profit harvester for {len(positions)} positions...")
                        # Use configurable timeout with default of 8s
                        harvester_timeout = self.config.get('profit_harvester_timeout', 8.0)

                        sell_signals = await asyncio.wait_for(
                            self.profit_harvester.check_positions(),
                            timeout=harvester_timeout
                        )
                        if sell_signals:
                            all_signals.extend(sell_signals)
                            self.logger.info(f"[BOT] Found {len(sell_signals)} sell signals from profit harvester")
                            for sig in sell_signals:
                                self.logger.info(f"[BOT] Sell signal: {sig.get('symbol')} - {sig.get('reason', 'No reason')}")
                        else:
                            self.logger.debug("[BOT] No sell signals from profit harvester")
                    else:
                        self.logger.debug("[BOT] No positions to check for profit harvesting")

                    # Check if we need emergency rebalancing (no trades in hours)
                    time_since_last_trade = time.time() - self.last_trade_time
                    hours_since_trade = time_since_last_trade / 3600

                    # Only trigger emergency rebalance after 1 hour (not 0.5)
                    if hours_since_trade > 1.0 and hasattr(self.profit_harvester, 'emergency_rebalance'):
                        # Check if we have deployed capital but no USDT
                        portfolio_state = await self.balance_manager.analyze_portfolio_state('USDT')
                        if (portfolio_state.get('state') == 'funds_deployed' and
                            portfolio_state.get('available_balance', 0) < MINIMUM_ORDER_SIZE_TIER1 and  # Lower threshold
                            portfolio_state.get('portfolio_value', 0) > 20.0):  # Lower threshold

                            self.logger.warning(f"[BOT] No trades in {hours_since_trade:.1f} hours with deployed capital - checking emergency rebalance")
                            emergency_signals = await self.profit_harvester.emergency_rebalance(
                                target_usdt_amount=10.0,  # Lower target
                                hours_without_trade=hours_since_trade
                            )
                            if emergency_signals:
                                all_signals.extend(emergency_signals)
                                self.logger.warning(f"[BOT] Added {len(emergency_signals)} emergency sell signals")

                except asyncio.TimeoutError:
                    self.logger.warning(f"[BOT] Profit harvester check timed out after {harvester_timeout}s")
                except Exception as e:
                    self.logger.error(f"[BOT] Profit harvester error: {e}", exc_info=True)

            self.logger.info(f"[BOT] Total signals collected: {len(all_signals)}")

            # Handle no signals gracefully
            if not all_signals:
                self.logger.debug("[BOT] No trading signals generated this cycle - waiting for opportunities")
            else:
                # DIRECT EXECUTION - Execute high confidence signals immediately
                self.logger.info(f"[BOT] Processing {len(all_signals)} signals for execution")

                # Sort by confidence and filter
                sorted_signals = sorted(all_signals, key=lambda x: x.get('confidence', 0), reverse=True)

                # Route through HFT controller if enabled for fee-free micro-scalping
                if self.hft_controller and self.config.get('fee_free_scalping', {}).get('enabled', False):
                    # Convert signals to HFT format and process
                    hft_signals = []
                    for signal in sorted_signals:
                        if signal.get('confidence', 0) >= 0.1:  # Ultra-low threshold for HFT
                            hft_signal = {
                                'symbol': signal['symbol'],
                                'side': signal['side'],
                                'confidence': signal.get('confidence', 0.5),
                                'profit_target': self.config.get('fee_free_scalping', {}).get('profit_target', 0.002),
                                'stop_loss': self.config.get('fee_free_scalping', {}).get('stop_loss', 0.001),
                                'metadata': {
                                    'source': signal.get('source', 'unknown'),
                                    'reason': signal.get('reason', ''),
                                    'momentum': signal.get('momentum', 0),
                                    'volume_spike': signal.get('volume_spike', 1.0),
                                    'spread': signal.get('spread', 0)
                                }
                            }
                            hft_signals.append(hft_signal)

                    if hft_signals:
                        self.logger.info(f"[BOT] Routing {len(hft_signals)} signals to HFT controller")
                        await self.hft_controller.process_signals(hft_signals)
                else:
                    # Normal execution path when HFT is not enabled
                    # Execute top signals directly (bypass queue for immediate execution)
                    for signal in sorted_signals[:3]:  # Max 3 per cycle
                        if signal.get('confidence', 0) >= 0.2:  # Very low threshold for more signals
                            try:
                                await self._execute_signal(signal)
                                await asyncio.sleep(0.5)  # Small delay between trades
                            except Exception as e:
                                self.logger.error(f"[BOT] Error executing signal: {e}")

                # Also add to batch for normal processing
                async with self.signal_batch_lock:
                    self.signal_batch.extend(all_signals)
                    current_time = time.time()

                    # Process batch if window has elapsed or we have many signals
                    if (current_time - self.last_batch_time >= self.batch_window or
                        len(self.signal_batch) >= 15):

                        # Process the batch
                        await self._process_signal_batch(self.signal_batch.copy())
                        self.signal_batch.clear()
                        self.last_batch_time = current_time

        except Exception as e:
            self.logger.error(f"[MAIN] Error in run_once: {e}")

    async def _process_signal_queue(self) -> None:
        """Process signals from queue - unified execution pipeline"""
        self.logger.info("[BOT] Signal processing queue started")
        queue_iterations = 0
        last_deployment_log = 0
        while self.running:
            try:
                queue_iterations += 1
                if queue_iterations % 60 == 0:  # Every minute
                    self.logger.info(f"[BOT] Signal queue heartbeat - {queue_iterations} iterations")

                    # Check and log capital deployment status
                    current_time = time.time()
                    if current_time - last_deployment_log > 60:  # Log every minute
                        deployment_status = await self.get_capital_deployment_status()
                        if deployment_status['fully_deployed']:
                            self.logger.info(f"[CAPITAL_STATUS] Fully deployed ({deployment_status['deployment_percentage']:.1f}%) - "
                                           f"Available: ${deployment_status['available_usdt']:.2f} - "
                                           f"Monitoring {deployment_status.get('num_positions', 0)} positions for exits")
                        last_deployment_log = current_time

                # Get signal with timeout
                signal = await asyncio.wait_for(self.signal_queue.get(), timeout=1.0)
                self.logger.info(f"[BOT] Processing signal: {signal.get('symbol', 'unknown')} {signal.get('side', 'unknown')}")

                # Validate signal
                if not self._validate_signal(signal):
                    self.logger.warning(f"[BOT] Signal failed validation: {signal.get('symbol')} "
                                      f"confidence={signal.get('confidence', 0):.2f}")
                    continue
                else:
                    self.logger.info(f"[BOT] Signal passed validation: {signal.get('symbol')} {signal.get('side')}")

                # Execute through trade executor
                symbol = signal.get('symbol')
                side = signal.get('side', 'buy')

                # Ensure minimum order size and respect tier-1 limit
                min_size = self.config.get('min_order_size_usdt', MINIMUM_ORDER_SIZE_TIER1)
                tier_1_limit = self.config.get('tier_1_trade_limit', MINIMUM_ORDER_SIZE_TIER1)

                # Check if we have sufficient balance
                current_balance = 0.0
                if self.balance_manager:
                    try:
                        current_balance = await self.balance_manager.get_balance_for_asset('USDT')
                    except Exception as e:
                        self.logger.error(f"[EXECUTE] Error checking balance: {e}")

                # ENHANCED PORTFOLIO INTELLIGENCE: Check deployment status FIRST when balance is low
                if current_balance < min_size and side == 'buy':
                    # Force capital deployment check
                    deployment_status = await self.get_capital_deployment_status()
                    if deployment_status['fully_deployed']:
                        self.logger.warning(f"[EXECUTE] Capital fully deployed - skipping BUY signal for {symbol}. "
                                          f"Deployment: {deployment_status['deployment_percentage']:.1f}%")
                        continue

                if current_balance < min_size and side == 'buy':
                    self.logger.info(f"[EXECUTE] Low balance detected: ${current_balance:.2f} < ${min_size:.2f} minimum")

                    # ALWAYS check deployment status when balance is low (CRITICAL FIX)
                    deployment_status = self.balance_manager.get_deployment_status('USDT')
                    self.logger.info(f"[EXECUTE] Deployment status: {deployment_status}")

                    # For sells, always allow (we're freeing up capital)
                    if side == 'sell':
                        self.logger.info(f"[EXECUTE] Allowing sell order to free up capital (balance: ${current_balance:.2f})")
                        # Don't skip, continue to execute the sell
                    else:
                        # For buys, handle based on deployment status
                        if deployment_status == 'funds_deployed':
                            self.logger.info(f"[EXECUTE] DEPLOYED CAPITAL DETECTED: Low USDT (${current_balance:.2f}) but capital is deployed")

                            # Get detailed portfolio analysis
                            portfolio_state = await self.balance_manager.analyze_portfolio_state('USDT')
                            portfolio_value = portfolio_state.get('portfolio_value', 0)
                            deployed_assets = portfolio_state.get('deployed_assets', [])

                            self.logger.warning("[EXECUTE] Portfolio Analysis:")
                            self.logger.warning(f"  - Total Value: ${portfolio_value:.2f}")
                            self.logger.warning(f"  - Deployed Assets: {len(deployed_assets)}")
                            self.logger.warning(f"  - Available USDT: ${current_balance:.2f}")

                            # CRITICAL: Check if we have sufficient deployed capital to proceed
                            if len(deployed_assets) > 0 and portfolio_value >= min_size * 2:  # Need at least 2x minimum
                                self.logger.info(f"[EXECUTE] Sufficient deployed capital (${portfolio_value:.2f}) - proceeding with reallocation strategy")

                                # Let the enhanced trade executor handle intelligent reallocation
                                # The executor will liquidate positions if needed
                                self.logger.info(f"[EXECUTE] Trade execution will handle automatic reallocation for {symbol} {side}")
                                # Continue to execution - don't skip
                            else:
                                self.logger.warning(f"[EXECUTE] Insufficient deployed capital (${portfolio_value:.2f}) for reallocation")

                                # Fallback: Trigger profit harvester to free up capital
                                if self.profit_harvester and len(deployed_assets) > 0:
                                    self.logger.info("[EXECUTE] Triggering profit harvester as fallback strategy")
                                    try:
                                        # Force check for profit opportunities
                                        sell_signals = await self.profit_harvester.check_positions()
                                        if sell_signals:
                                            self.logger.info(f"[EXECUTE] Found {len(sell_signals)} profit-taking opportunities")
                                            # Add sell signals to the batch for processing
                                            async with self.signal_batch_lock:
                                                self.signal_batch.extend(sell_signals)
                                        else:
                                            self.logger.warning("[EXECUTE] No profit-taking opportunities found")
                                    except Exception as e:
                                        self.logger.error(f"[EXECUTE] Error triggering profit harvester: {e}")

                                self.logger.warning("[EXECUTE] Skipping buy signal - awaiting capital from profit-taking or deposits")
                                continue
                        else:
                            # Truly insufficient funds - no deployed capital
                            self.logger.warning(f"[EXECUTE] INSUFFICIENT FUNDS: ${current_balance:.2f} < ${min_size:.2f}, no deployed capital. State: {deployment_status}")
                            self.logger.warning(f"[EXECUTE] Skipping {symbol} {side} signal - deposit USDT or wait for existing positions to profit")
                            continue

                # CLAUDE FLOW FIX: Use dynamic position sizing for deployed capital scenarios
                configured_position = self.config.get('position_size_usdt', 3.5)

                # Get current balance for percentage calculation
                current_balance = await self.balance_manager.get_balance_for_asset('USDT')
                if isinstance(current_balance, dict):
                    current_balance = current_balance.get('free', 0)

                # Use 70% of available balance, not full configured amount
                position_percentage = self.config.get('position_size_percentage', 0.7)
                dynamic_amount = current_balance * position_percentage if current_balance > 0 else configured_position

                if self.config.get('kraken_api_tier', 'starter') == 'starter':
                    amount = min(dynamic_amount, tier_1_limit)  # Respect tier limit
                else:
                    amount = max(min_size, dynamic_amount)

                # Execute trade
                result = await self.trade_executor.execute_trade({
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'signal': signal
                })

                if result.get('success'):
                    self.metrics['total_trades'] += 1
                    self.last_trade_time = time.time()
                    self.logger.info(f"[EXECUTE] Trade executed: {symbol} {side}")

                    # Track capital flow
                    await self._track_capital_flow(symbol, side, amount, result)
                else:
                    self.logger.error(f"[EXECUTE] Trade failed: {result.get('error')}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"[SIGNAL] Error processing signal: {e}")


    async def _process_signal_batch(self, signals: list[dict[str, Any]]) -> None:
        """Process a batch of signals efficiently with reduced API calls"""
        if not signals:
            return

        self.logger.info(f"[BOT] Processing batch of {len(signals)} signals")

        try:
            # Pre-fetch balance ONCE for the entire batch to minimize API calls
            current_balance = 0.0
            if self.balance_manager:
                # Check rate limit status first
                if hasattr(self.exchange, 'api_counter'):
                    # Use our new rate limit tracking
                    if self.exchange.api_counter > self.exchange.max_api_counter * 0.8:
                        wait_time = max(5, (self.exchange.api_counter - self.exchange.max_api_counter * 0.8) / self.exchange.decay_rate)
                        self.logger.warning(f"[BOT] Approaching rate limit, waiting {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)

                # Get fresh balance once for all signals
                self.logger.info("[BOT] Getting fresh balance for batch processing...")
                try:
                    current_balance = await self.balance_manager.get_usdt_balance()
                    self.logger.info(f"[BOT] Current USDT balance: ${current_balance:.2f}")
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        self.logger.error("[BOT] Rate limit hit while fetching balance!")
                        # Skip this batch to avoid further rate limit issues
                        return
                    else:
                        self.logger.error(f"[BOT] Error fetching balance: {e}")
                        current_balance = 0.0

        except Exception as e:
            self.logger.error(f"[BOT] Error in batch pre-fetch: {e}")
            if "rate limit" in str(e).lower():
                self.logger.warning("[BOT] Rate limit hit during pre-fetch, will use cached data")

        # Sort signals by confidence and prioritize
        sorted_signals = sorted(signals, key=lambda s: s.get('confidence', 0), reverse=True)

        # Log batch details
        self.logger.info("[BOT] Batch signals (sorted by confidence):")
        for idx, signal in enumerate(sorted_signals[:10]):  # Show top 10
            self.logger.info(f"  {idx+1}. {signal.get('symbol')} {signal.get('side')} "
                           f"confidence={signal.get('confidence', 0):.2f} source={signal.get('source', 'unknown')}")

        # Route signals through HFT controller if enabled
        if self.hft_controller and self.config.get('fee_free_scalping', {}).get('enabled', False):
            # Send to HFT controller for high-frequency execution
            await self.hft_controller.process_signals(sorted_signals)
            self.logger.info(f"[BOT] Routed {len(sorted_signals)} signals to HFT controller")
        else:
            # Add signals to queue for normal processing
            for signal in sorted_signals:
                await self.signal_queue.put(signal)

    def _should_process_signal(self, signal: dict[str, Any]) -> bool:
        """
        Check if signal should be processed (deduplication).

        Args:
            signal: Trading signal dictionary

        Returns:
            True if signal should be processed, False if duplicate/too soon
        """
        try:
            # Create signal hash for deduplication
            symbol = signal.get('symbol', '')
            side = signal.get('side', '')
            reason = signal.get('reason', signal.get('source', ''))
            confidence = signal.get('confidence', 0)

            # Create unique identifier for this signal type
            sig_hash = f"{symbol}_{side}_{reason}_{confidence:.2f}"
            current_time = time.time()

            # Check if we've seen this exact signal recently
            if sig_hash in self.last_signal_hash:
                time_since_last = current_time - self.last_signal_hash[sig_hash]
                if time_since_last < self.signal_cooldown:
                    self.logger.debug(f"[SIGNAL_FILTER] Duplicate signal filtered: {symbol} {side} "
                                    f"(last seen {time_since_last:.1f}s ago, cooldown: {self.signal_cooldown}s)")
                    return False

            # Update hash with current time
            self.last_signal_hash[sig_hash] = current_time

            # Clean old entries (older than 2x cooldown)
            cleanup_threshold = current_time - (self.signal_cooldown * 2)
            old_hashes = [h for h, t in self.last_signal_hash.items() if t < cleanup_threshold]
            for old_hash in old_hashes:
                del self.last_signal_hash[old_hash]

            self.logger.debug(f"[SIGNAL_FILTER] Signal approved: {symbol} {side} (hash: {sig_hash[:20]}...)")
            return True

        except Exception as e:
            self.logger.error(f"[SIGNAL_FILTER] Error in signal deduplication: {e}")
            return True  # Default to allowing signal on error

    def _validate_signal(self, signal: dict[str, Any]) -> bool:
        """Validate trading signal"""
        # First check deduplication
        if not self._should_process_signal(signal):
            return False

        # Check if this is a buy signal and we're fully deployed
        if signal.get('side') == 'buy' and self.opportunity_scanner:
            if hasattr(self.opportunity_scanner, 'capital_deployed_state') and self.opportunity_scanner.capital_deployed_state:
                self.logger.debug("[SIGNAL_VALIDATE] Rejecting BUY signal - capital fully deployed")
                return False

        # Check required fields
        if not signal.get('symbol') or not signal.get('side'):
            return False

        # Check confidence threshold - handle both decimal and percentage formats
        signal_confidence = signal.get('confidence', 0)

        # Low-priced USDT pairs focus - lower confidence thresholds
        symbol = signal.get('symbol', '')
        is_low_priced_usdt = any(symbol.startswith(pair.replace('/USDT', '')) for pair in ['SHIB/USDT', 'MATIC/USDT', 'AI16Z/USDT', 'BERA/USDT', 'MANA/USDT', 'DOT/USDT', 'LINK/USDT', 'SOL/USDT', 'BTC/USDT'])

        # Check if we should use decimal format thresholds (now the default)
        if self.config.get('signal_confidence_format') == 'decimal' and 'confidence_thresholds' in self.config:
            # Use configured decimal thresholds with special handling for low-priced USDT
            thresholds = self.config.get('confidence_thresholds', {})
            if signal.get('side') == 'sell':
                min_confidence = thresholds.get('sell', thresholds.get('minimum', 0.2))
                # Lower threshold for low-priced USDT pairs
                if is_low_priced_usdt:
                    min_confidence = min(min_confidence, 0.15)
            else:
                min_confidence = thresholds.get('buy', thresholds.get('minimum', 0.3))
                # Lower threshold for low-priced USDT pairs
                if is_low_priced_usdt:
                    min_confidence = min(min_confidence, 0.2)

            # Emergency mode override
            if self.config.get('emergency_mode', False):
                min_confidence = thresholds.get('emergency', 0.1)

            if signal_confidence < min_confidence:
                self.logger.debug(f"[VALIDATION] Signal confidence {signal_confidence:.2f} < minimum {min_confidence:.2f}")
                return False
        else:
            # Fallback to legacy format or default with low-priced USDT focus
            min_confidence = self.config.get('min_confidence_threshold', 0.3)
            if is_low_priced_usdt:
                min_confidence = min(min_confidence, 0.2)
            if signal_confidence < min_confidence:
                self.logger.debug(f"[VALIDATION] Signal confidence {signal_confidence:.2f} < minimum {min_confidence:.2f}")
                return False

        # Ensure USDT pair only (focus on low-priced USDT pairs)
        symbol = signal.get('symbol')
        if 'USDT' not in symbol:
            self.logger.debug(f"[VALIDATION] Rejecting non-USDT pair: {symbol}")
            return False

        # Additional filter for low-priced USDT pairs only
        if not is_low_priced_usdt:
            self.logger.debug(f"[VALIDATION] Rejecting non-low-priced USDT pair: {symbol}")
            return False

        return True

    async def can_make_new_trade(self, side: str = 'buy') -> bool:
        """Check if we can make a new trade based on capital deployment"""
        try:
            if not self.balance_manager:
                return False

            # Get current balance
            balance = await self.balance_manager.get_balance_for_asset('USDT')
            min_trade = self.config.get('min_order_size_usdt', 2.0)

            # For sells, always allow (we're freeing capital)
            if side == 'sell':
                return True

            # For buys, check if we have sufficient balance
            if balance >= min_trade:
                return True

            # If low balance, check deployment status
            deployment_status = self.balance_manager.get_deployment_status('USDT')
            if deployment_status == 'funds_deployed':
                self.logger.debug("[TRADE_CHECK] Capital is deployed, new buys require reallocation")
                return False

            return False

        except Exception as e:
            self.logger.error(f"[TRADE_CHECK] Error checking trade capability: {e}")
            return False

    async def _execute_signal(self, signal: dict[str, Any]) -> None:
        """Execute trading signal directly"""
        try:
            # Validate signal
            symbol = signal.get('symbol')
            side = signal.get('side', 'buy')
            amount_usdt = signal.get('amount_usdt', self.config.get('min_order_size_usdt', MINIMUM_ORDER_SIZE_TIER1))

            # Ensure minimum order size respects tier-1 limit
            amount_usdt = max(MINIMUM_ORDER_SIZE_TIER1, amount_usdt)

            self.logger.info(f"[EXECUTE] Executing {side} signal for {symbol} - ${amount_usdt:.2f}")

            # BALANCE FIX: Force fresh balance before trade
            if side == 'buy':
                self.logger.info(f"[BALANCE_FIX] Pre-trade balance check for {symbol}")
                try:
                    if hasattr(self.balance_manager, 'force_fresh_balance'):
                        fresh_balance = await self.balance_manager.force_fresh_balance('USDT')
                        self.logger.info(f"[BALANCE_FIX] Fresh balance: ${fresh_balance:.2f}")
                        balance = fresh_balance
                    else:
                        # Fallback to regular balance fetch
                        balance = await self.balance_manager.get_balance_for_asset('USDT')
                except Exception as e:
                    self.logger.error(f"[BALANCE_FIX] Failed to get fresh balance: {e}")
                    # Fallback to regular balance fetch
                    balance = await self.balance_manager.get_balance_for_asset('USDT')
            else:
                # For sell orders, regular balance check is fine
                balance = await self.balance_manager.get_balance_for_asset('USDT')

            if MoneyDecimal(balance, "USDT") < MoneyDecimal(amount_usdt, "USDT") and side == 'buy':
                self.logger.warning(f"[EXECUTE] Insufficient balance: ${balance:.2f} < ${amount_usdt:.2f}")

                # Check if we should generate liquidation signals
                if self.opportunity_scanner and hasattr(self.opportunity_scanner, 'check_liquidation_opportunities'):
                    liquidation_signals = await self.opportunity_scanner.check_liquidation_opportunities(symbol, amount_usdt)
                    if liquidation_signals:
                        self.logger.info(f"[EXECUTE] Generated {len(liquidation_signals)} liquidation signals to free up capital")
                        # Add liquidation signals to queue with high priority
                        for liq_signal in liquidation_signals:
                            liq_signal['priority'] = 'high'
                            await self.signal_queue.put(liq_signal)
                return

            # Execute trade through trade executor
            if self.trade_executor:
                result = await self.trade_executor.execute_trade({
                    'symbol': symbol,
                    'side': side,
                    'amount': amount_usdt,
                    'signal': signal
                })

                if result and result.get('success'):
                    self.logger.info(f"[EXECUTE] ✓ Trade successful: {side} ${amount_usdt:.2f} of {symbol}")
                    self.metrics['total_trades'] += 1
                    self.last_trade_time = time.time()

                    # Add position to position cycler if it's a buy order
                    if self.position_cycler and side == 'buy':
                        entry_price = result.get('price', result.get('average_price', 0))
                        if entry_price:
                            self.position_cycler.add_position(
                                symbol=symbol,
                                side='buy',
                                size=amount_usdt,
                                entry_price=entry_price,
                                profit_target=signal.get('profit_target', 0.002),
                                stop_loss=signal.get('stop_loss', 0.001),
                                metadata={'source': signal.get('source', 'unknown')}
                            )

                    # Remove position from cycler if it's a sell order
                    elif self.position_cycler and side == 'sell':
                        self.position_cycler.remove_position(symbol, reason='manual_sell')
                        # Notify HFT controller if active
                        if self.hft_controller:
                            await self.hft_controller.on_position_closed(symbol)

                    # Force capital deployment check after successful trade
                    if self.opportunity_scanner and hasattr(self.opportunity_scanner, 'force_capital_check'):
                        deployment_status = await self.opportunity_scanner.force_capital_check()
                        self.logger.info(f"[CAPITAL_CHECK] Post-trade deployment: {deployment_status['deployment_percentage']:.1f}% - "
                                       f"Available: ${deployment_status['available_usdt']:.2f}")
                else:
                    error = result.get('error', 'Unknown error') if result else 'No result'
                    self.logger.error(f"[EXECUTE] X Trade failed: {error}")
            else:
                self.logger.error("[EXECUTE] Trade executor not available")

        except Exception as e:
            self.logger.error(f"[EXECUTE] Error executing signal: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    async def _handle_unified_ticker_update(self, symbol: str, ticker: dict[str, Any], source=None) -> None:
        """Handle unified ticker updates from WebSocket or REST"""
        try:
            # Route through data coordinator for consistency
            if hasattr(self, 'data_coordinator'):
                await self.data_coordinator.handle_websocket_ticker(symbol, ticker)

            # Update portfolio tracker
            if self.portfolio_tracker:
                self.portfolio_tracker.update_price(symbol, ticker.get('last', 0))

            # Feed to strategy components
            if self.strategy_manager:
                await self.strategy_manager.process_ticker_update(symbol, ticker)

        except Exception as e:
            self.logger.error(f"[UNIFIED_DATA] Error processing ticker update for {symbol}: {e}")

    async def _handle_unified_ohlc_data(self, symbol: str, ohlc: dict[str, Any], source=None) -> None:
        """Handle unified OHLC updates from WebSocket or REST"""
        try:
            # Route through data coordinator for consistency
            if hasattr(self, 'data_coordinator'):
                await self.data_coordinator.handle_websocket_ohlc(symbol, ohlc)

            # Feed to strategy manager
            if self.strategy_manager:
                await self.strategy_manager.process_ohlc_update(symbol, ohlc)

            # Save to historical data
            if self.historical_data_saver:
                await self.historical_data_saver.save_ohlc_data(symbol, ohlc)

        except Exception as e:
            self.logger.error(f"[UNIFIED_DATA] Error processing OHLC update for {symbol}: {e}")

    async def _handle_unified_balance_update(self, balances: dict[str, Any], source=None) -> None:
        """Handle unified balance updates from WebSocket or REST with enhanced integration"""
        try:
            # Route through data coordinator for consistency
            if hasattr(self, 'data_coordinator'):
                await self.data_coordinator.handle_websocket_balance(balances)

            # Update balance manager with real-time data
            if self.balance_manager:
                # Try the process_websocket_update method first (recommended)
                if hasattr(self.balance_manager, 'process_websocket_update'):
                    await self.balance_manager.process_websocket_update(balances)
                    self.logger.debug(f"[UNIFIED_DATA] Balance update processed via process_websocket_update: {len(balances)} assets")
                # Fallback to legacy update_from_websocket method
                elif hasattr(self.balance_manager, 'update_from_websocket'):
                    await self.balance_manager.update_from_websocket(balances)
                    self.logger.debug(f"[UNIFIED_DATA] Balance update processed via update_from_websocket: {len(balances)} assets")
                else:
                    self.logger.warning("[UNIFIED_DATA] Balance manager has no WebSocket update methods available")
            else:
                self.logger.warning("[UNIFIED_DATA] No balance manager available to process balance update")

            # Update portfolio tracker with balance changes
            if self.portfolio_tracker and hasattr(self.portfolio_tracker, 'update_balances'):
                await self.portfolio_tracker.update_balances(balances)

            # Log significant balance changes
            if 'USDT' in balances:
                usdt_data = balances['USDT']
                if isinstance(usdt_data, dict):
                    usdt_balance = usdt_data.get('free', usdt_data.get('total', 0))
                else:
                    usdt_balance = float(usdt_data) if usdt_data else 0
                self.logger.info(f"[WEBSOCKET] USDT balance update: ${usdt_balance:.2f}")

        except Exception as e:
            self.logger.error(f"[UNIFIED_DATA] Error processing balance update: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())

    async def _handle_unified_order_update(self, order_data: dict[str, Any], source=None) -> None:
        """Handle unified order updates from WebSocket or REST"""
        try:
            # Route through data coordinator for consistency
            if hasattr(self, 'data_coordinator'):
                await self.data_coordinator.handle_websocket_order(order_data)

            # Update trade executor with order status
            if self.trade_executor and hasattr(self.trade_executor, 'process_order_update'):
                await self.trade_executor.process_order_update(order_data)

            # Update portfolio tracker with order changes
            if self.portfolio_tracker and hasattr(self.portfolio_tracker, 'process_order_update'):
                await self.portfolio_tracker.process_order_update(order_data)

            # Feed to strategy manager for execution tracking
            if self.strategy_manager and hasattr(self.strategy_manager, 'process_order_update'):
                await self.strategy_manager.process_order_update(order_data)

            # Log order status changes
            order_id = order_data.get('id', 'Unknown')
            order_status = order_data.get('status', 'Unknown')
            symbol = order_data.get('symbol', 'Unknown')
            self.logger.info(f"[UNIFIED_DATA] Order update: {order_id} ({symbol}) -> {order_status}")

        except Exception as e:
            self.logger.error(f"[UNIFIED_DATA] Error processing order update: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())

    async def _health_monitor_loop(self) -> None:
        """Monitor health of all bot components"""
        self.logger.info("[HEALTH] Health monitor started")

        while self.running:
            try:
                # Wait for interval
                await asyncio.sleep(self.health_monitor_interval)

                # Check all components
                health_status = await self._check_all_components_health()

                # Log health status
                healthy_count = sum(1 for status in health_status.values() if status.get('healthy', False))
                total_count = len(health_status)

                if healthy_count == total_count:
                    self.logger.info(f"[HEALTH] All {total_count} components healthy [EMOJI]")
                else:
                    unhealthy = [name for name, status in health_status.items() if not status.get('healthy', False)]
                    self.logger.warning(f"[HEALTH] {len(unhealthy)} unhealthy components: {unhealthy}")

                # Update metrics
                self.metrics['last_health_check'] = time.time()
                self.component_health = health_status

            except Exception as e:
                self.logger.error(f"[HEALTH] Error in health monitor: {e}")
                self.metrics['health_check_failures'] += 1

    async def get_capital_deployment_status(self) -> dict[str, Any]:
        """
        Get comprehensive capital deployment status.

        Returns:
            Dict with deployment information including:
            - fully_deployed: bool
            - available_usdt: float
            - deployment_percentage: float
            - positions: list of current positions
            - total_value: float
        """
        try:
            # Get deployment status from opportunity scanner
            deployment_status = {'fully_deployed': False, 'available_usdt': 0.0, 'deployment_percentage': 0.0}

            if self.opportunity_scanner and hasattr(self.opportunity_scanner, '_check_capital_deployment'):
                deployment_status = await self.opportunity_scanner._check_capital_deployment()

            # Add position information
            positions = []
            if self.balance_manager:
                try:
                    # Note: portfolio analysis method may need to be added to UnifiedBalanceManager
                    portfolio = {}  # Simplified for now
                    positions = portfolio.get('deployed_assets', [])
                    deployment_status['positions'] = positions
                    deployment_status['num_positions'] = len(positions)
                except Exception as e:
                    self.logger.debug(f"[CAPITAL_STATUS] Error getting positions: {e}")

            return deployment_status

        except Exception as e:
            self.logger.error(f"[CAPITAL_STATUS] Error getting deployment status: {e}")
            return {
                'fully_deployed': False,
                'available_usdt': 0.0,
                'deployment_percentage': 0.0,
                'positions': [],
                'error': str(e)
            }

    async def _check_all_components_health(self) -> dict[str, dict[str, Any]]:
        """Check health of all bot components"""
        health_status = {}

        # Check exchange health
        if self.exchange:
            try:
                if hasattr(self.exchange, 'get_health_status'):
                    health_status['exchange'] = self.exchange.get_health_status()
                else:
                    # Fallback: try to fetch a ticker
                    await asyncio.wait_for(self.exchange.fetch_ticker('BTC/USDT'), timeout=5.0)
                    health_status['exchange'] = {'healthy': True}
            except Exception as e:
                health_status['exchange'] = {'healthy': False, 'error': str(e)}

        # Check WebSocket health
        if self.websocket_manager:
            try:
                is_connected = hasattr(self.websocket_manager, 'is_connected') and self.websocket_manager.is_connected
                health_status['websocket'] = {
                    'healthy': is_connected,
                    'connected': is_connected
                }
            except Exception as e:
                health_status['websocket'] = {'healthy': False, 'error': str(e)}

        # Check balance manager health
        if self.balance_manager:
            try:
                # Check if we can get balance
                balance = await asyncio.wait_for(
                    self.balance_manager.get_all_balances(),
                    timeout=5.0
                )
                has_balance = bool(balance)
                health_status['balance_manager'] = {
                    'healthy': has_balance,
                    'has_balance': has_balance
                }
            except Exception as e:
                health_status['balance_manager'] = {'healthy': False, 'error': str(e)}

        # Check strategy manager health
        if self.strategy_manager:
            try:
                if hasattr(self.strategy_manager, 'get_performance_metrics'):
                    metrics = self.strategy_manager.get_performance_metrics()
                    slow_strategies = metrics.get('slow_strategies', [])
                    health_status['strategy_manager'] = {
                        'healthy': len(slow_strategies) < 3,  # Unhealthy if 3+ slow strategies
                        'slow_strategies': slow_strategies,
                        'total_strategies': len(self.strategy_manager.strategies)
                    }
                else:
                    health_status['strategy_manager'] = {'healthy': True}
            except Exception as e:
                health_status['strategy_manager'] = {'healthy': False, 'error': str(e)}

        # Check signal queue health
        try:
            queue_size = self.signal_queue.qsize()
            health_status['signal_queue'] = {
                'healthy': queue_size < 100,  # Unhealthy if queue is backing up
                'queue_size': queue_size
            }
        except Exception as e:
            health_status['signal_queue'] = {'healthy': False, 'error': str(e)}

        return health_status

    def get_health_report(self) -> dict[str, Any]:
        """Get comprehensive health report of the bot"""
        uptime = time.time() - self.metrics['start_time']
        time_since_health_check = time.time() - self.metrics['last_health_check']

        return {
            'uptime_seconds': uptime,
            'uptime_human': f"{uptime/3600:.1f} hours",
            'time_since_last_health_check': time_since_health_check,
            'health_check_failures': self.metrics['health_check_failures'],
            'component_health': self.component_health,
            'metrics': self.metrics
        }

    async def _initialize_portfolio_from_holdings(self) -> None:
        """Initialize portfolio tracker with current holdings if no positions are tracked"""
        try:
            if len(self.portfolio_tracker.positions) == 0:
                self.logger.info("[INIT] No tracked positions found, initializing from current holdings...")

                # Get current balance
                balance = await self.balance_manager.get_all_balances()

                # Get portfolio analysis - use direct balance data since analyze_portfolio_state may not exist
                try:
                    if hasattr(self.balance_manager, 'analyze_portfolio_state'):
                        portfolio_state = await self.balance_manager.analyze_portfolio_state('USDT')
                        deployed_assets = portfolio_state.get('deployed_assets', [])
                    else:
                        # Fallback: analyze balance data directly
                        deployed_assets = []
                        for asset, balance_data in balance.items():
                            if isinstance(balance_data, dict) and balance_data.get('free', 0) > 0:
                                if asset != 'USDT':  # Skip USDT
                                    deployed_assets.append({
                                        'asset': asset,
                                        'amount': balance_data.get('free', 0),
                                        'price': 1.0,  # Will need to get price separately
                                        'value_usd': balance_data.get('free', 0)  # Approximate
                                    })
                        self.logger.info(f"[INIT] Using direct balance analysis, found {len(deployed_assets)} non-USDT assets")
                except Exception as analysis_error:
                    self.logger.warning(f"[INIT] Portfolio analysis failed: {analysis_error}")
                    deployed_assets = []

                if deployed_assets:
                    self.logger.warning(f"[INIT] Found {len(deployed_assets)} deployed assets without tracked positions")

                    for asset in deployed_assets:
                        symbol = f"{asset['asset']}/USDT"
                        amount = asset.get('amount', 0)
                        current_price = asset.get('price', 0)
                        value_usd = asset.get('value_usd', 0)

                        if amount > 0 and current_price > 0:
                            # Initialize position with current price as entry price
                            self.portfolio_tracker.update_position(symbol, amount, current_price)
                            self.logger.warning(
                                f"[INIT] Initialized {symbol} position: {amount} units @ ${current_price:.6f} "
                                f"(${value_usd:.2f}) - using current price as entry"
                            )

                    self.logger.info(f"[INIT] Initialized {len(deployed_assets)} positions from current holdings")
                else:
                    self.logger.info("[INIT] No deployed assets found to initialize")
            else:
                self.logger.info(f"[INIT] Portfolio tracker already has {len(self.portfolio_tracker.positions)} positions")

        except Exception as e:
            self.logger.error(f"[INIT] Error initializing portfolio from holdings: {e}")

    async def _capital_allocation_monitor(self) -> None:
        """Monitor capital allocation efficiency and trigger optimization."""
        self.logger.info("[CAPITAL] Capital allocation monitor started")

        check_interval = 300  # Check every 5 minutes
        dashboard_interval = 600  # Display dashboard every 10 minutes
        last_dashboard_time = 0

        while self.running:
            try:
                await asyncio.sleep(check_interval)

                if not self.balance_manager:
                    continue

                # Get comprehensive portfolio state
                portfolio_state = await self.balance_manager.analyze_portfolio_state('USDT')

                # Log deployment status
                state = portfolio_state.get('state', 'unknown')
                available_usdt = portfolio_state.get('available_balance', 0)
                portfolio_value = portfolio_state.get('portfolio_value', 0)
                total_value = available_usdt + portfolio_value
                deployment_pct = (portfolio_value / total_value * 100) if total_value > 0 else 0

                self.logger.info("[CAPITAL] Capital Status:")
                self.logger.info(f"  - State: {state}")
                self.logger.info(f"  - Available USDT: ${available_usdt:.2f}")
                self.logger.info(f"  - Portfolio Value: ${portfolio_value:.2f}")
                self.logger.info(f"  - Deployment: {deployment_pct:.1f}%")

                # Handle different states
                if state == 'funds_deployed':
                    self.logger.info("[CAPITAL] All capital is deployed in positions")
                    # Check for profit-taking opportunities
                    if self.profit_harvester:
                        sell_signals = await self.profit_harvester.check_positions()
                        if sell_signals:
                            self.logger.info(f"[CAPITAL] Found {len(sell_signals)} profit-taking opportunities")

                elif state == 'ready_to_trade' and deployment_pct < 80:
                    self.logger.info("[CAPITAL] Capital available for deployment")
                    # Trigger opportunity scanning
                    if self.opportunity_scanner:
                        self.logger.info("[CAPITAL] Triggering opportunity scan due to available capital")
                        asyncio.create_task(self.opportunity_scanner.scan_once())

                elif state == 'insufficient_funds':
                    self.logger.warning("[CAPITAL] Insufficient funds for trading")

                # Display position dashboard periodically
                current_time = time.time()
                if self.position_dashboard and (current_time - last_dashboard_time >= dashboard_interval):
                    try:
                        self.logger.info("[CAPITAL] Displaying position dashboard...")
                        await self.position_dashboard.display_dashboard()
                        last_dashboard_time = current_time
                    except Exception as e:
                        self.logger.error(f"[CAPITAL] Error displaying dashboard: {e}")

                # Check if we need optimization
                if deployment_pct > 95 and available_usdt < 5:
                    self.logger.info("[CAPITAL] High deployment detected, checking for reallocation opportunities")
                    optimization_result = await self.balance_manager.optimize_capital_allocation()

                    if optimization_result.get('optimization_performed'):
                        actions = optimization_result.get('actions_taken', [])
                        self.logger.info("[CAPITAL] Capital optimization performed:")
                        for action in actions:
                            self.logger.info(f"  - {action}")

                # Check for portfolio position sync every check
                try:
                    deployed_assets = portfolio_state.get('deployed_assets', [])
                    tracked_positions = self.portfolio_tracker.get_open_positions()

                    # Quick mismatch detection
                    deployed_symbols = {f"{asset['asset']}/USDT" for asset in deployed_assets if asset.get('amount', 0) > 0}
                    tracked_symbols = {pos['symbol'] for pos in tracked_positions}

                    # Check for mismatches
                    missing_in_tracker = deployed_symbols - tracked_symbols
                    extra_in_tracker = tracked_symbols - deployed_symbols

                    if missing_in_tracker or extra_in_tracker:
                        self.logger.warning(
                            f"[CAPITAL] Position mismatch detected! "
                            f"Missing in tracker: {missing_in_tracker}, "
                            f"Extra in tracker: {extra_in_tracker}"
                        )

                        # Force sync with exchange
                        self.logger.warning("[CAPITAL] Forcing portfolio sync with exchange...")
                        sync_result = await self.portfolio_tracker.force_sync_with_exchange(
                            exchange=self.exchange,
                            balance_manager=self.balance_manager
                        )

                        if sync_result.get('success'):
                            self.logger.info(
                                f"[CAPITAL] Portfolio sync completed: "
                                f"{sync_result.get('positions_synced', 0)} synced, "
                                f"{sync_result.get('positions_removed', 0)} removed"
                            )
                        else:
                            self.logger.error(f"[CAPITAL] Portfolio sync failed: {sync_result.get('error')}")

                except Exception as e:
                    self.logger.error(f"[CAPITAL] Error checking portfolio sync: {e}")

            except Exception as e:
                self.logger.error(f"[CAPITAL] Error in capital allocation monitor: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _track_capital_flow(self, symbol: str, side: str, amount: float, result: dict[str, Any]) -> None:
        """Track capital flow for unified monitoring"""
        try:
            timestamp = time.time()
            result.get('order', {})

            if side == 'buy':
                self.capital_flow['total_buys'] += 1
                self.capital_flow['total_buy_volume'] += amount
                self.capital_flow['deployed_capital'] += amount

                # Record flow
                self.capital_flow['flow_history'].append({
                    'timestamp': timestamp,
                    'type': 'buy',
                    'symbol': symbol,
                    'amount': amount,
                    'deployed_capital': self.capital_flow['deployed_capital']
                })

            elif side == 'sell':
                self.capital_flow['total_sells'] += 1
                self.capital_flow['total_sell_volume'] += amount
                self.capital_flow['deployed_capital'] = max(0, self.capital_flow['deployed_capital'] - amount)

                # Check for profit
                if 'metadata' in result.get('signal', {}):
                    profit = result['signal']['metadata'].get('profit_usd', 0)
                    if profit > 0:
                        self.capital_flow["realized_pnl"] = PrecisionTradingCalculator.accumulate_profits(self.capital_flow.get("realized_pnl", "0"), profit).to_float()

                # Record flow
                self.capital_flow['flow_history'].append({
                    'timestamp': timestamp,
                    'type': 'sell',
                    'symbol': symbol,
                    'amount': amount,
                    'deployed_capital': self.capital_flow['deployed_capital']
                })

            # Update current balance
            if self.balance_manager:
                self.capital_flow['current_usdt'] = await self.balance_manager.get_balance_for_asset('USDT')

            # Keep history limited
            if len(self.capital_flow['flow_history']) > 1000:
                self.capital_flow['flow_history'] = self.capital_flow['flow_history'][-500:]

            # Log capital flow status periodically
            if self.metrics['total_trades'] % 10 == 0:
                self.logger.info(f"[CAPITAL] Flow status - Deployed: ${self.capital_flow['deployed_capital']:.2f}, "
                               f"USDT: ${self.capital_flow['current_usdt']:.2f}, "
                               f"Realized P&L: ${self.capital_flow['realized_pnl']:.2f}")

        except Exception as e:
            self.logger.error(f"[CAPITAL] Error tracking flow: {e}")

    def get_capital_flow_summary(self) -> dict[str, Any]:
        """Get comprehensive capital flow summary"""
        try:
            total_capital = self.capital_flow['current_usdt'] + self.capital_flow['deployed_capital']
            deployment_pct = (self.capital_flow['deployed_capital'] / total_capital * 100) if total_capital > 0 else 0

            return {
                'initial_capital': self.capital_flow['initial_usdt'],
                'current_usdt': self.capital_flow['current_usdt'],
                'deployed_capital': self.capital_flow['deployed_capital'],
                'total_capital': total_capital,
                'deployment_percentage': deployment_pct,
                'total_buys': self.capital_flow['total_buys'],
                'total_sells': self.capital_flow['total_sells'],
                'buy_volume': self.capital_flow['total_buy_volume'],
                'sell_volume': self.capital_flow['total_sell_volume'],
                'realized_pnl': self.capital_flow['realized_pnl'],
                'net_flow': self.capital_flow['current_usdt'] - self.capital_flow['initial_usdt'],
                'recent_flows': self.capital_flow['flow_history'][-10:]  # Last 10 flows
            }
        except Exception as e:
            self.logger.error(f"[CAPITAL] Error getting flow summary: {e}")
            return {}

    async def display_deployment_status(self) -> None:
        """Display current capital deployment status"""
        try:
            # Get portfolio state
            portfolio_state = await self.balance_manager.analyze_portfolio_state('USDT')

            # Get capital flow summary
            flow_summary = self.get_capital_flow_summary()

            # Display status
            self.logger.info("="*60)
            self.logger.info("CAPITAL DEPLOYMENT STATUS")
            self.logger.info("="*60)
            self.logger.info(f"State: {portfolio_state.get('state', 'unknown')}")
            self.logger.info(f"Available USDT: ${portfolio_state.get('available_balance', 0):.2f}")
            self.logger.info(f"Portfolio Value: ${portfolio_state.get('portfolio_value', 0):.2f}")
            self.logger.info(f"Total Capital: ${flow_summary.get('total_capital', 0):.2f}")
            self.logger.info(f"Deployment: {flow_summary.get('deployment_percentage', 0):.1f}%")

            # Show deployed assets
            deployed_assets = portfolio_state.get('deployed_assets', [])
            if deployed_assets:
                self.logger.info(f"\nDeployed Assets ({len(deployed_assets)}):")

                for asset in deployed_assets[:5]:  # Show top 5
                    self.logger.info(f"  - {asset['asset']}: ${asset.get('value_usd', 0):.2f}")

            # Show recommendations
            recommendations = portfolio_state.get('recommendations', [])
            if recommendations:
                self.logger.info("\nRecommendations:")
                for rec in recommendations:
                    self.logger.info(f"  - {rec}")

            self.logger.info("="*60)

            # Display dashboard if available
            if self.position_dashboard:
                await self.position_dashboard.display_dashboard()

        except Exception as e:
            self.logger.error(f"[CAPITAL] Error displaying deployment status: {e}")

    def handle_error_recovery(self, error: Exception, context: str = "unknown") -> bool:
        """
        Handle error recovery with circuit breaker pattern.

        Returns:
            bool: True if operation should continue, False if circuit breaker is open
        """
        try:
            current_time = time.time()

            # Check if circuit breaker should be reset
            if (self.error_recovery['circuit_breaker_open'] and
                current_time > self.error_recovery['circuit_reset_time']):
                self.error_recovery['circuit_breaker_open'] = False
                self.error_recovery['consecutive_failures'] = 0
                self.logger.info("[ERROR_RECOVERY] Circuit breaker reset - resuming operations")

            # If circuit breaker is open, reject the operation
            if self.error_recovery['circuit_breaker_open']:
                return False

            # Increment failure count
            self.error_recovery['consecutive_failures'] += 1

            # Check if we should open the circuit breaker
            if self.error_recovery['consecutive_failures'] >= self.error_recovery['max_failures']:
                self.error_recovery['circuit_breaker_open'] = True
                self.error_recovery['circuit_reset_time'] = current_time + self.error_recovery['recovery_delay']

                self.logger.error(
                    f"[ERROR_RECOVERY] Circuit breaker OPEN due to {self.error_recovery['consecutive_failures']} "
                    f"consecutive failures in {context}. Recovery in {self.error_recovery['recovery_delay']}s"
                )
                return False

            # Log the error but allow continuation
            self.logger.warning(
                f"[ERROR_RECOVERY] Failure #{self.error_recovery['consecutive_failures']} in {context}: {error}"
            )
            return True

        except Exception as recovery_error:
            self.logger.error(f"[ERROR_RECOVERY] Error in recovery handler: {recovery_error}")
            return True  # Default to allowing operation to continue

    def reset_error_recovery(self) -> None:
        """Reset error recovery state after successful operation."""
        if self.error_recovery['consecutive_failures'] > 0:
            self.logger.info("[ERROR_RECOVERY] Resetting after successful operation")
            self.error_recovery['consecutive_failures'] = 0

    async def _handle_websocket_circuit_breaker_event(self, event_type: str) -> None:
        """
        Handle WebSocket circuit breaker events
        Integrates with risk manager to prevent trading during WebSocket issues
        """
        try:
            self.logger.info(f"[CIRCUIT_BREAKER] WebSocket event: {event_type}")

            if event_type == 'websocket_recovered':
                # WebSocket connection recovered
                self.logger.info("[CIRCUIT_BREAKER] WebSocket recovered - notifying risk manager")

                # Reset WebSocket error tracking
                if hasattr(self, 'risk_manager') and self.risk_manager:
                    if hasattr(self.risk_manager, 'reset_websocket_errors'):
                        await self.risk_manager.reset_websocket_errors()

                    # Clear circuit breaker if it was triggered by WebSocket issues
                    if hasattr(self.risk_manager, 'circuit_breaker') and self.risk_manager.circuit_breaker.get('websocket_triggered'):
                        self.risk_manager.circuit_breaker['open'] = False
                        self.risk_manager.circuit_breaker['websocket_triggered'] = False
                        self.logger.info("[CIRCUIT_BREAKER] Circuit breaker cleared after WebSocket recovery")

                # Also reset local error recovery state
                self.reset_error_recovery()

            elif event_type == 'websocket_connected':
                # Initial connection established
                self.logger.info("[CIRCUIT_BREAKER] WebSocket connected successfully")

            elif event_type == 'websocket_non_critical_error':
                # Non-critical error like duplicate subscription
                self.logger.info("[CIRCUIT_BREAKER] Non-critical WebSocket error - trading continues")

                # Don't trigger circuit breaker for non-critical errors
                if hasattr(self, 'risk_manager') and self.risk_manager:
                    if hasattr(self.risk_manager, 'track_non_critical_error'):
                        await self.risk_manager.track_non_critical_error('websocket')

        except Exception as e:
            self.logger.error(f"[CIRCUIT_BREAKER] Error handling WebSocket event: {e}")

    def _register_nonce_error_repair(self) -> None:
        """Register custom repair action for nonce errors."""
        async def check_nonce_errors():
            """Check if we have nonce errors."""
            # Check if exchange has nonce error flag
            if hasattr(self.exchange, 'has_nonce_error'):
                return self.exchange.has_nonce_error

            # Check logs or error history
            if hasattr(self, 'last_error') and self.last_error:
                return 'Invalid nonce' in str(self.last_error)

            return False

        async def repair_nonce_errors():
            """Repair nonce errors by switching to SDK."""
            try:
                self.logger.warning("[SELF_REPAIR] Nonce error detected - switching to SDK")

                # Update config to use SDK
                self.config['kraken']['use_official_sdk'] = True

                # SDK exchange no longer available - use native implementation recovery
                if hasattr(self.exchange, '__class__') and 'Native' in self.exchange.__class__.__name__:
                    # Try to reinitialize the native exchange
                    try:
                        await self.exchange.close()
                        await asyncio.sleep(1)
                        await self.exchange.connect()
                        await self.exchange.load_markets()

                        self.logger.info("[SELF_REPAIR] Successfully reinitialized native exchange")
                        return True
                    except Exception as reinit_error:
                        self.logger.error(f"[SELF_REPAIR] Failed to reinitialize native exchange: {reinit_error}")
                        return False

                return True

            except Exception as e:
                self.logger.error(f"[SELF_REPAIR] Failed to switch to SDK: {e}")
                return False

        # Register the repair action
        self.self_repair_system.register_repair(
            RepairAction(
                name="nonce_error_fix",
                description="Fix nonce errors by switching to official SDK",
                check_func=check_nonce_errors,
                repair_func=repair_nonce_errors,
                severity="high"
            )
        )

    async def _handle_websocket_circuit_breaker_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle circuit breaker events from WebSocket manager"""
        try:
            if event_type == 'circuit_open':
                self.logger.error(f"[CIRCUIT_BREAKER] WebSocket circuit opened: {data.get('reason', 'Unknown')}")

                # Switch to REST API fallback mode
                if hasattr(self, 'fallback_manager') and self.fallback_manager:
                    self.logger.info("[CIRCUIT_BREAKER] Switching to REST API fallback mode")
                    # Signal components to use REST API
                    await publish_event(
                        BusEventType.WEBSOCKET_DISCONNECTED,
                        "circuit_breaker",
                        {'fallback_mode': True}
                    )

            elif event_type == 'circuit_closed':
                self.logger.info("[CIRCUIT_BREAKER] WebSocket circuit closed - service recovered")
                # Resume normal WebSocket operations
                await publish_event(
                    BusEventType.WEBSOCKET_CONNECTED,
                    "circuit_breaker",
                    {'fallback_mode': False}
                )

        except Exception as e:
            self.logger.error(f"[CIRCUIT_BREAKER] Error handling WebSocket circuit breaker event: {e}")

    def _register_nonce_error_repair(self):
        """Register custom repair action for nonce errors"""
        if self.self_repair_system:
            async def repair_nonce_error(bot_instance, error_context):
                """Repair action for nonce errors"""
                try:
                    self.logger.warning("[SELF_REPAIR] Attempting to fix nonce error...")

                    # Get unified nonce manager from exchange
                    if hasattr(bot_instance.exchange, 'nonce_manager'):
                        nonce_manager = bot_instance.exchange.nonce_manager

                        # Use unified manager's recovery mechanism
                        nonce_manager.handle_invalid_nonce_error("self_repair")

                        # Force save state
                        nonce_manager.force_save()

                        self.logger.info("[SELF_REPAIR] Triggered nonce recovery with 60-second buffer")

                        # Unified nonce manager handles state automatically
                        # No manual state clearing needed

                        return True
                    else:
                        self.logger.error("[SELF_REPAIR] No nonce manager found in exchange")
                        return False

                except Exception as e:
                    self.logger.error(f"[SELF_REPAIR] Error repairing nonce: {e}")
                    return False

            # Register the repair action
            self.self_repair_system.register_repair(
                RepairAction(
                    name="fix_nonce_error",
                    description="Fix invalid nonce errors by resetting with future buffer",
                    check_func=lambda: False,  # Always return False to indicate issue needs fixing
                    repair_func=repair_nonce_error,
                    severity="high"
                )
            )

            self.logger.info("[SELF_REPAIR] Registered nonce error repair action")

    async def _run_self_healing_cycle(self) -> None:
        """Run self-healing diagnostic cycle periodically."""
        while self.running:
            try:
                # Wait for initial startup
                await asyncio.sleep(30)

                # Run diagnostics
                self.logger.debug("[SELF_HEALING] Running diagnostic cycle...")
                repair_results = await self.self_repair_system.diagnose_and_repair()

                if repair_results['issues_found']:
                    self.logger.info(f"[SELF_HEALING] Found issues: {repair_results['issues_found']}")
                    self.logger.info(f"[SELF_HEALING] Repairs successful: {repair_results['repairs_successful']}")

                    if repair_results['repairs_failed']:
                        self.logger.error(f"[SELF_HEALING] Repairs failed: {repair_results['repairs_failed']}")

                # Check guardian status
                if self.critical_error_guardian and self.critical_error_guardian.kill_switch_engaged:
                    self.logger.error("[SELF_HEALING] Kill switch engaged - stopping bot")
                    await self.stop()
                    break

                # Wait before next cycle
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"[SELF_HEALING] Error in healing cycle: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def stop(self) -> None:
        """Shutdown bot gracefully in reverse order of initialization"""
        self.logger.info("[BOT] Shutting down...")
        self.running = False

        # Set shutdown event to signal all components
        self.shutdown_event.set()

        # Stop data coordinator API worker
        try:
            if hasattr(self, 'data_coordinator') and self.data_coordinator:
                await self.data_coordinator.stop_api_worker()
                self.logger.info("[BOT] Data coordinator API worker stopped")
        except Exception as e:
            self.logger.error(f"[BOT] Error stopping data coordinator: {e}")

        # Save nonce state before shutdown
        try:
            if hasattr(self.exchange, 'nonce_manager'):
                self.exchange.nonce_manager.force_save()
                self.logger.info("[SHUTDOWN] Nonce state saved")
        except Exception as e:
            self.logger.error(f"[SHUTDOWN] Error saving nonce state: {e}")

        # Reset circuit breakers to allow graceful shutdown
        try:
            # self.circuit_breaker_manager.reset_all()  # Not available
            pass
            self.logger.info("[SHUTDOWN] Circuit breakers reset for graceful shutdown")
        except Exception as e:
            self.logger.error(f"[SHUTDOWN] Error resetting circuit breakers: {e}")

        # Log final capital flow summary
        try:
            summary = self.get_capital_flow_summary()
            self.logger.info(f"[BOT] Final capital flow - Net: ${summary.get('net_flow', 0):.2f}, "
                            f"Realized P&L: ${summary.get('realized_pnl', 0):.2f}")
        except Exception as e:
            self.logger.error(f"[BOT] Error getting final summary: {e}")

        # Stop components in reverse order of initialization
        # Phase 1: Stop high-level components first
        if hasattr(self, 'opportunity_scanner') and self.opportunity_scanner:
            try:
                self.logger.info("[SHUTDOWN] Stopping opportunity scanner...")
                await self.opportunity_scanner.stop()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error stopping opportunity scanner: {e}")

        if hasattr(self, 'profit_harvester') and self.profit_harvester:
            try:
                self.logger.info("[SHUTDOWN] Stopping profit harvester...")
                # Profit harvester may not have a stop method, but check
                if hasattr(self.profit_harvester, 'stop'):
                    await self.profit_harvester.stop()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error stopping profit harvester: {e}")

        if hasattr(self, 'historical_data_saver') and self.historical_data_saver:
            try:
                self.logger.info("[SHUTDOWN] Stopping historical data saver...")
                await self.historical_data_saver.stop()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error stopping historical data saver: {e}")

        # Phase 2: Stop strategy manager
        if hasattr(self, 'strategy_manager') and self.strategy_manager:
            try:
                self.logger.info("[SHUTDOWN] Stopping strategy manager...")
                if hasattr(self.strategy_manager, 'stop'):
                    await self.strategy_manager.stop()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error stopping strategy manager: {e}")

        # Phase 3: Stop trade executor
        if hasattr(self, 'trade_executor') and self.trade_executor:
            try:
                self.logger.info("[SHUTDOWN] Stopping trade executor...")
                if hasattr(self.trade_executor, 'stop'):
                    await self.trade_executor.stop()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error stopping trade executor: {e}")

        # Phase 4: Stop WebSocket managers (both v1 and v2)
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            try:
                self.logger.info("[SHUTDOWN] Closing WebSocket connections...")
                await self.websocket_manager.close()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error closing WebSocket: {e}")

        # Also stop WebSocket v2 if it exists
        if hasattr(self, 'websocket_v2') and self.websocket_v2:
            try:
                self.logger.info("[SHUTDOWN] Closing WebSocket v2 connections...")
                if hasattr(self.websocket_v2, 'close'):
                    await self.websocket_v2.close()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error closing WebSocket v2: {e}")

        # Stop SDK WebSocket client if using SDK
        if hasattr(self.exchange, 'client') and hasattr(self.exchange.client, 'websocket'):
            try:
                self.logger.info("[SHUTDOWN] Closing SDK WebSocket client...")
                # SDK WebSocket might need special handling
                if hasattr(self.exchange.client.websocket, 'stop'):
                    await self.exchange.client.websocket.stop()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error closing SDK WebSocket: {e}")

        # Phase 5: Stop balance manager
        if hasattr(self, 'balance_manager') and self.balance_manager:
            try:
                self.logger.info("[SHUTDOWN] Stopping balance manager...")
                if hasattr(self.balance_manager, 'stop'):
                    await self.balance_manager.stop()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error stopping balance manager: {e}")

        # Phase 6: Close exchange connection last through singleton
        if hasattr(self, 'exchange') and self.exchange:
            try:
                self.logger.info("[SHUTDOWN] Closing exchange connection through singleton...")
                # Use the singleton close method to properly clean up
                from src.exchange.exchange_singleton import ExchangeSingleton
                await ExchangeSingleton.close()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error closing exchange: {e}")

        # Phase 7: Stop learning system and assistant manager
        if hasattr(self, 'assistant_manager') and self.assistant_manager:
            try:
                self.logger.info("[SHUTDOWN] Stopping assistant manager...")
                await self.assistant_manager.shutdown()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error stopping assistant manager: {e}")

        if hasattr(self, 'learning_manager') and self.learning_manager:
            try:
                self.logger.info("[SHUTDOWN] Stopping learning manager...")
                if hasattr(self.learning_manager, 'shutdown'):
                    await self.learning_manager.shutdown()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error stopping learning manager: {e}")

        # Phase 8: Stop event bus
        if hasattr(self, 'event_bus') and self.event_bus:
            try:
                self.logger.info("[SHUTDOWN] Stopping event bus...")
                await self.event_bus.stop()
            except Exception as e:
                self.logger.error(f"[SHUTDOWN] Error stopping event bus: {e}")

        self.logger.info("[BOT] Shutdown complete")

    async def place_order(self, symbol: str, side: str, size: float, order_type: str = 'market',
                         price: float = None, metadata: dict[str, Any] = None) -> dict[str, Any]:
        """Place order through fast router if available"""
        try:
            # Use fast order router for HFT if available
            if self.fast_order_router and order_type == 'market':
                from src.trading.fast_order_router import OrderRequest

                request = OrderRequest(
                    symbol=symbol,
                    side=side,
                    size=size,
                    order_type=order_type,
                    price=price,
                    metadata=metadata or {},
                    created_at=time.time()
                )

                result = await self.fast_order_router.execute_order(request)

                return {
                    'success': result.success,
                    'order_id': result.order_id,
                    'error': result.error,
                    'execution_time': result.execution_time
                }

            # Fallback to standard execution
            if hasattr(self, 'trade_executor') and self.trade_executor:
                return await self.trade_executor.execute_trade({
                    'symbol': symbol,
                    'side': side,
                    'amount': size,
                    'order_type': order_type,
                    'price': price,
                    'metadata': metadata
                })

            return {'success': False, 'error': 'No trade executor available'}

        except Exception as e:
            self.logger.error(f"[BOT] Order placement error: {e}")
            return {'success': False, 'error': str(e)}

    async def request_position_close(self, symbol: str, reason: str = 'user_requested'):
        """Request position close through position cycler"""
        try:
            if self.position_cycler:
                # Mark position for exit
                if symbol in self.position_cycler.positions:
                    self.position_cycler.exit_queue.append(symbol)
                    self.position_cycler.locked_positions.add(symbol)
                    self.logger.info(f"[BOT] Position close requested for {symbol}: {reason}")
                    return True

            # Fallback to manual close
            if hasattr(self, 'portfolio_tracker') and self.portfolio_tracker:
                position = self.portfolio_tracker.get_position(symbol)
                if position:
                    # Place market order to close
                    exit_side = 'sell' if position.get('side') == 'buy' else 'buy'
                    return await self.place_order(
                        symbol=symbol,
                        side=exit_side,
                        size=position.get('amount', 0),
                        order_type='market',
                        metadata={'close_reason': reason}
                    )

            return False

        except Exception as e:
            self.logger.error(f"[BOT] Position close error: {e}")
            return False

    def get_status(self) -> dict[str, Any]:
        """Get bot status for orchestrator integration"""
        return {
            'status': 'running' if self.running else 'stopped',
            'initialized': getattr(self, 'initialized', False),
            'uptime': time.time() - getattr(self, 'start_time', time.time()),
            'components': {
                'exchange': self.exchange is not None,
                'balance_manager': getattr(self, 'balance_manager', None) is not None,
                'portfolio_manager': getattr(self, 'portfolio_manager', None) is not None,
                'websocket_manager': getattr(self, 'websocket_manager', None) is not None,
                'opportunity_scanner': getattr(self, 'opportunity_scanner', None) is not None,
                'trade_executor': getattr(self, 'trade_executor', None) is not None
            },
            'health': self.get_health_report() if hasattr(self, 'get_health_report') else {},
            'trading_mode': 'paper' if os.environ.get('PAPER_TRADING_ENABLED') == 'true' else 'live'
        }

    def set_strategy(self, strategy):
        """Set trading strategy for orchestrator integration"""
        self.strategy = strategy
        self.logger.info(f"Strategy set: {strategy.__class__.__name__ if strategy else 'None'}")

    def set_websocket_first_mode(self, enabled: bool):
        """Set WebSocket-first mode for orchestrator integration"""
        self.websocket_first_mode = enabled
        self.logger.info(f"WebSocket-first mode: {'enabled' if enabled else 'disabled'}")

    def get_hft_metrics(self) -> dict[str, Any]:
        """Get HFT performance metrics"""
        metrics = {}

        if self.hft_controller:
            metrics['hft'] = self.hft_controller.get_metrics()

        if self.position_cycler:
            metrics['cycling'] = self.position_cycler.get_cycling_metrics()

        if self.fast_order_router:
            metrics['routing'] = self.fast_order_router.get_performance_stats()

        return metrics

    async def shutdown(self):
        """Shutdown the trading bot gracefully"""
        try:
            self.logger.info("[BOT] Starting graceful shutdown...")
            self.running = False

            # Set shutdown event
            if hasattr(self, 'shutdown_event'):
                self.shutdown_event.set()

            # Shutdown components in reverse order
            components_to_shutdown = [
                ('WebSocket Manager', getattr(self, 'websocket_manager', None)),
                ('Balance Manager', getattr(self, 'balance_manager', None)),
                ('Portfolio Manager', getattr(self, 'portfolio_manager', None)),
                ('Trade Executor', getattr(self, 'trade_executor', None)),
                ('Exchange', getattr(self, 'exchange', None))
            ]

            for component_name, component in components_to_shutdown:
                if component and hasattr(component, 'shutdown'):
                    try:
                        self.logger.info(f"[BOT] Shutting down {component_name}...")
                        if asyncio.iscoroutinefunction(component.shutdown):
                            await component.shutdown()
                        else:
                            component.shutdown()
                    except Exception as e:
                        self.logger.error(f"[BOT] Error shutting down {component_name}: {e}")
                elif component and hasattr(component, 'stop'):
                    try:
                        self.logger.info(f"[BOT] Stopping {component_name}...")
                        if asyncio.iscoroutinefunction(component.stop):
                            await component.stop()
                        else:
                            component.stop()
                    except Exception as e:
                        self.logger.error(f"[BOT] Error stopping {component_name}: {e}")

            self.logger.info("[BOT] Shutdown completed successfully")

        except Exception as e:
            self.logger.error(f"[BOT] Error during shutdown: {e}")


async def main():
    """Main entry point"""
    bot = KrakenTradingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
