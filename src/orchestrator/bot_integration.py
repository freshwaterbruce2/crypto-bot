"""
Trading Bot Integration with System Orchestrator

Shows how to integrate the orchestrator with the existing trading bot.
"""

import asyncio
import logging
from typing import Optional, Any, Dict

from .system_orchestrator import SystemOrchestrator
from ..core.bot import KrakenTradingBot as TradingBot
from ..strategies.base_strategy import BaseStrategy
from .startup_sequence import StartupPhase
from .health_monitor import HealthStatus
from ..auth.websocket_authentication_manager import WebSocketAuthenticationManager
from ..exchange.websocket_manager_v2 import KrakenProWebSocketManager

logger = logging.getLogger(__name__)


class OrchestratedTradingBot:
    """Trading bot with full orchestration support and WebSocket-first initialization"""
    
    def __init__(self, config_path: str = None):
        self.orchestrator = SystemOrchestrator(config_path)
        self.bot: Optional[TradingBot] = None
        self.strategy: Optional[BaseStrategy] = None
        self.websocket_auth_manager: Optional[WebSocketAuthenticationManager] = None
        self.websocket_manager: Optional[KrakenProWebSocketManager] = None
        self.websocket_first_mode = True  # Default to WebSocket-first mode
        
    async def initialize(self):
        """Initialize orchestrated trading bot with WebSocket-first pattern"""
        logger.info("Initializing Orchestrated Trading Bot (WebSocket-first mode)")
        
        # Register WebSocket-first startup sequence
        if self.websocket_first_mode:
            self.orchestrator.startup.register_websocket_first_steps()
            # Override WebSocket-specific implementation handlers
            await self._setup_websocket_handlers()
        
        # Initialize orchestrator
        success = await self.orchestrator.initialize()
        if not success:
            if self.websocket_first_mode:
                logger.warning("WebSocket-first initialization failed, falling back to REST mode")
                self.websocket_first_mode = False
                await self._fallback_to_rest_mode()
            else:
                raise RuntimeError("System orchestration failed")
            
        # Register trading bot specific steps
        await self._register_trading_components()
        
        # Get components from orchestrator
        self.bot = TradingBot()
        
        # Inject orchestrated components
        await self._inject_dependencies()
        
        logger.info("Orchestrated Trading Bot initialized")
        
    async def _setup_websocket_handlers(self):
        """Setup WebSocket-specific implementation handlers"""
        logger.info("Setting up WebSocket-first handlers")
        
        # Override startup handlers with WebSocket implementations
        startup = self.orchestrator.startup
        
        # Replace handler implementations
        startup._generate_websocket_token = self._generate_websocket_token_impl
        startup._initialize_websocket_connection = self._initialize_websocket_connection_impl
        startup._initialize_balance_stream = self._initialize_balance_stream_impl
        startup._initialize_data_pipeline = self._initialize_data_pipeline_impl
        
    async def _generate_websocket_token_impl(self):
        """Generate WebSocket authentication token with minimal REST API usage"""
        try:
            logger.info("Generating WebSocket authentication token")
            
            # Get API credentials from configuration
            config = self.orchestrator.config
            api_key = config.get('kraken.api_key')
            private_key = config.get('kraken.private_key')
            
            if not api_key or not private_key:
                raise RuntimeError("API credentials not configured")
            
            # Initialize WebSocket authentication manager
            self.websocket_auth_manager = WebSocketAuthenticationManager(
                exchange_client=None,  # Will be set later
                api_key=api_key,
                private_key=private_key,
                enable_debug=config.get('debug.websocket_auth', False)
            )
            
            # Start authentication manager
            await self.websocket_auth_manager.start()
            
            # Get initial token
            token = await self.websocket_auth_manager.get_token()
            logger.info("WebSocket authentication token generated successfully")
            
        except Exception as e:
            logger.error(f"Failed to generate WebSocket token: {e}")
            raise
            
    async def _initialize_websocket_connection_impl(self):
        """Initialize WebSocket connection with authentication"""
        try:
            logger.info("Initializing WebSocket connection")
            
            if not self.websocket_auth_manager:
                raise RuntimeError("WebSocket authentication manager not initialized")
            
            # Initialize WebSocket manager
            config = self.orchestrator.config
            self.websocket_manager = KrakenProWebSocketManager(
                auth_manager=self.websocket_auth_manager,
                config=config.get_section('websocket', {}),
                enable_debug=config.get('debug.websocket', False)
            )
            
            # Connect WebSocket
            await self.websocket_manager.connect()
            logger.info("WebSocket connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket connection: {e}")
            raise
            
    async def _initialize_balance_stream_impl(self):
        """Initialize WebSocket balance stream"""
        try:
            logger.info("Initializing WebSocket balance stream")
            
            if not self.websocket_manager:
                raise RuntimeError("WebSocket manager not initialized")
            
            # Subscribe to balance updates
            await self.websocket_manager.subscribe_to_balances()
            
            # Wait for initial balance data
            await asyncio.sleep(2)
            
            logger.info("WebSocket balance stream initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize balance stream: {e}")
            raise
            
    async def _initialize_data_pipeline_impl(self):
        """Initialize unified data pipeline for WebSocket streams"""
        try:
            logger.info("Initializing WebSocket data pipeline")
            
            if not self.websocket_manager:
                raise RuntimeError("WebSocket manager not initialized")
            
            # Subscribe to essential market data
            pairs = self.orchestrator.config.get('trading.pairs', ['BTC/USDT', 'ETH/USDT'])
            
            for pair in pairs[:5]:  # Limit initial subscriptions
                await self.websocket_manager.subscribe_to_ticker(pair)
                await asyncio.sleep(0.1)  # Rate limit subscriptions
            
            logger.info(f"WebSocket data pipeline initialized for {len(pairs)} pairs")
            
        except Exception as e:
            logger.error(f"Failed to initialize data pipeline: {e}")
            # Non-critical failure, don't raise
            logger.warning("Continuing without full data pipeline")
            
    async def _fallback_to_rest_mode(self):
        """Fallback to REST-only mode when WebSocket initialization fails"""
        logger.info("Falling back to REST-only mode")
        
        # Clean up WebSocket components
        if self.websocket_manager:
            try:
                await self.websocket_manager.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting WebSocket during fallback: {e}")
            self.websocket_manager = None
            
        if self.websocket_auth_manager:
            try:
                await self.websocket_auth_manager.stop()
            except Exception as e:
                logger.warning(f"Error stopping WebSocket auth during fallback: {e}")
            self.websocket_auth_manager = None
        
        # Re-initialize orchestrator in REST mode
        await self.orchestrator.initialize()
        
    async def _register_trading_components(self):
        """Register trading-specific components"""
        # Register trading bot initialization
        self.orchestrator.startup.register_step(
            name='trading_bot_init',
            phase=StartupPhase.STRATEGIES,
            handler=self._initialize_trading_bot,
            dependencies=['portfolio_manager_init'],
            critical=True
        )
        
        # Register strategy initialization
        self.orchestrator.startup.register_step(
            name='strategy_init',
            phase=StartupPhase.STRATEGIES,
            handler=self._initialize_strategy,
            dependencies=['trading_bot_init'],
            critical=True
        )
        
    async def _initialize_trading_bot(self):
        """Initialize the trading bot with orchestrated components"""
        # Get components from orchestrator
        exchange = await self.orchestrator.get_component(ExchangeSingleton)
        balance_manager = await self.orchestrator.get_component(UnifiedBalanceManager)
        portfolio_manager = await self.orchestrator.get_component(PortfolioManager)
        
        # Initialize bot with injected dependencies
        self.bot.exchange = exchange
        self.bot.balance_manager = balance_manager
        self.bot.portfolio_manager = portfolio_manager
        
        # Initialize bot
        await self.bot.initialize()
        
        # Register bot for health monitoring
        self.orchestrator.health.register_component('trading_bot')
        
    async def _initialize_strategy(self):
        """Initialize trading strategy"""
        strategy_name = self.orchestrator.config.get('trading.strategy', 'enhanced_fast_scalper')
        
        # Import and create strategy
        # (This is simplified - in practice you'd have a strategy factory)
        if strategy_name == 'enhanced_fast_scalper':
            from ..strategies.enhanced_fast_scalper import EnhancedFastScalper
            self.strategy = EnhancedFastScalper()
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")
            
        # Configure strategy from orchestrator config
        self.strategy.profit_target = self.orchestrator.config.get('trading.profit_target', 0.005)
        self.strategy.stop_loss = self.orchestrator.config.get('trading.stop_loss', 0.02)
        
        # Set strategy on bot
        self.bot.set_strategy(self.strategy)
        
    async def _inject_dependencies(self):
        """Inject orchestrated dependencies into bot"""
        # Inject WebSocket components if available
        if self.websocket_first_mode and self.websocket_manager:
            logger.info("Injecting WebSocket components into bot")
            self.bot.websocket_manager = self.websocket_manager
            self.bot.websocket_auth_manager = self.websocket_auth_manager
            
            # Set WebSocket-first mode flag on bot
            if hasattr(self.bot, 'set_websocket_first_mode'):
                self.bot.set_websocket_first_mode(True)
            
        # Inject orchestrated components from dependency injector
        # exchange = await self.orchestrator.get_component(ExchangeSingleton)
        # balance_manager = await self.orchestrator.get_component(UnifiedBalanceManager)
        # portfolio_manager = await self.orchestrator.get_component(PortfolioManager)
        
        # self.bot.exchange = exchange
        # self.bot.balance_manager = balance_manager
        # self.bot.portfolio_manager = portfolio_manager
        
    async def start(self):
        """Start the trading bot"""
        if not self.orchestrator.is_running:
            await self.initialize()
            
        logger.info("Starting trading bot")
        
        # Update health status
        await self.orchestrator.health.update_component_status(
            'trading_bot',
            HealthStatus.HEALTHY,
            {'status': 'running', 'strategy': self.strategy.__class__.__name__}
        )
        
        # Start bot
        await self.bot.start()
        
    async def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot")
        
        # Stop bot
        if self.bot:
            await self.bot.stop()
            
        # Update health status
        await self.orchestrator.health.update_component_status(
            'trading_bot',
            HealthStatus.UNHEALTHY,
            {'status': 'stopped'}
        )
        
        # Shutdown orchestrator
        await self.orchestrator.shutdown()
        
    async def run(self):
        """Run the trading bot with orchestration"""
        try:
            await self.start()
            
            # Keep running until shutdown
            await self.orchestrator.startup.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Trading bot error: {e}")
            raise
        finally:
            await self.stop()
            
    def get_status(self):
        """Get bot status including orchestration info"""
        status = {
            'orchestrator': self.orchestrator.get_status(),
            'bot': self.bot.get_status() if self.bot else None,
            'strategy': self.strategy.get_status() if self.strategy else None
        }
        
        return status
        
    async def update_config(self, path: str, value: Any):
        """Update configuration through orchestrator"""
        await self.orchestrator.update_config(path, value)
        
        # Apply changes to running components if needed
        if path.startswith('trading.'):
            # Update strategy parameters
            if self.strategy:
                param = path.split('.')[-1]
                if hasattr(self.strategy, param):
                    setattr(self.strategy, param, value)
                    logger.info(f"Updated strategy parameter: {param} = {value}")


# Example usage in main.py
async def main():
    """Main entry point with orchestration"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create orchestrated bot
    bot = OrchestratedTradingBot('config.json')
    
    try:
        # Run with full orchestration
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        
        # Export diagnostics on error
        await bot.orchestrator.export_diagnostics()
        
        raise
    finally:
        # Ensure clean shutdown
        await bot.stop()


# Alternative: Use as context manager
async def main_with_context():
    """Main entry point using context manager"""
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = SystemOrchestrator('config.json')
    
    async with orchestrator.startup.managed_startup():
        # System is fully initialized here
        
        # Get components
        bot = await orchestrator.get_component(TradingBot)
        
        # Run bot
        await bot.start()
        
        # Wait for shutdown
        await orchestrator.startup.shutdown_event.wait()
        
    # System is fully shutdown here


if __name__ == "__main__":
    asyncio.run(main())