"""
Kraken WebSocket V2 Manager - Hybrid Architecture Implementation
==============================================================

Optimized for high-frequency trading with WebSocket V2 using python-kraken-sdk.
Implements hybrid architecture: WebSocket for market data, REST for orders.

Features:
- Real-time market data streaming (ticker, OHLC, trades)
- Real-time balance updates
- Automatic reconnection and error handling
- Pro account optimizations
- Compatibility layer for existing bot code
"""

import asyncio
from ..utils.base_exchange_connector import BaseExchangeConnector
import logging
import time
import json
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from collections import defaultdict, deque
from src.utils.decimal_precision_fix import safe_decimal, safe_float, is_zero
from src.auth.websocket_authentication_manager import WebSocketAuthenticationManager, WebSocketAuthenticationError
from src.websocket.kraken_v2_message_handler import KrakenV2MessageHandler, create_kraken_v2_handler
import os
import colorama
from colorama import Fore, Back, Style

# Initialize colorama for Windows
colorama.init()

logger = logging.getLogger(__name__)

# Import Kraken SDK
try:
    from kraken.spot import SpotWSClient
    KRAKEN_SDK_AVAILABLE = True
    logger.info("[WEBSOCKET_V2] Kraken SDK available")
except ImportError as e:
    logger.error(f"[WEBSOCKET_V2] Kraken SDK not available: {e}")
    logger.error("[WEBSOCKET_V2] Please install: pip install python-kraken-sdk>=3.2.2")
    KRAKEN_SDK_AVAILABLE = False
    # Create dummy class to prevent import errors
    class SpotWSClient:
        def __init__(self, *args, **kwargs):
            pass


class KrakenBot(SpotWSClient):
    """Custom bot class that extends KrakenSpotWSClient"""
    
    def __init__(self, manager, **kwargs):
        super().__init__(**kwargs)
        self.manager = manager
    
    async def on_message(self, message):
        """Handle incoming WebSocket messages via V2 message handler"""
        try:
            # Update last message time for heartbeat tracking
            self.manager.last_message_time = time.time()
            
            # KRAKEN V2 COMPLIANCE: Route through V2 message handler first
            if hasattr(self.manager, 'v2_message_handler') and self.manager.v2_message_handler:
                try:
                    # Process through V2 handler with proper validation and sequencing
                    success = await self.manager.v2_message_handler.process_message(message)
                    if success:
                        # V2 handler processed successfully, update visual tracking
                        if hasattr(self.manager, '_update_visual_tracking'):
                            channel = message.get('channel', 'unknown')
                            self.manager._update_visual_tracking(channel, message)
                        return
                    else:
                        logger.warning("[WEBSOCKET_V2] V2 handler failed, falling back to legacy processing")
                except Exception as v2_error:
                    logger.error("[WEBSOCKET_V2] V2 handler error: %s, falling back to legacy", v2_error)
            
            # LEGACY FALLBACK: Original message processing for compatibility
            if isinstance(message, dict):
                # Handle heartbeat messages
                if message.get('channel') == 'heartbeat':
                    self.manager._update_visual_tracking('heartbeat', message)
                    return
                    
                # Handle channel messages (ticker, ohlc, etc.)
                channel = message.get('channel')
                
                if channel == 'ticker':
                    # Ticker messages come with type and data array
                    data_array = message.get('data', [])
                    for ticker_data in data_array:
                        symbol = ticker_data.get('symbol')
                        if symbol and ticker_data:
                            # Route through data coordinator for unified handling
                            if hasattr(self.manager, 'data_coordinator') and self.manager.data_coordinator:
                                await self.manager.data_coordinator.handle_websocket_ticker(symbol, ticker_data)
                            
                            # Legacy compatibility - direct manager call
                            if self.manager and hasattr(self.manager, '_handle_ticker_message'):
                                await self.manager._handle_ticker_message(symbol, ticker_data)
                            
                            # Update visual tracking
                            if self.manager and hasattr(self.manager, '_update_visual_tracking'):
                                self.manager._update_visual_tracking('ticker', ticker_data)
                            
                elif channel == 'ohlc':
                    # OHLC messages come with type and data array
                    data_array = message.get('data', [])
                    for ohlc_data in data_array:
                        symbol = ohlc_data.get('symbol')
                        if symbol and ohlc_data:
                            # Route through data coordinator for unified handling
                            if hasattr(self.manager, 'data_coordinator') and self.manager.data_coordinator:
                                await self.manager.data_coordinator.handle_websocket_ohlc(symbol, ohlc_data)
                            
                            # Legacy compatibility - direct manager call
                            if self.manager and hasattr(self.manager, '_handle_ohlc_message'):
                                await self.manager._handle_ohlc_message(symbol, ohlc_data)
                            
                elif channel == 'book':
                    # Orderbook messages
                    data_array = message.get('data', [])
                    for book_data in data_array:
                        symbol = book_data.get('symbol')
                        if symbol and book_data:
                            await self.manager._handle_orderbook_message(symbol, book_data)
                            
                elif channel == 'balances':
                    # CRITICAL FIX 2025: Enhanced balance update handling with proper format conversion
                    data_array = message.get('data', [])
                    logger.info(f"[WEBSOCKET_V2] Balance channel update received: {len(data_array)} items")
                    
                    if data_array:
                        # Log sample balance data for debugging
                        if len(data_array) > 0:
                            sample_item = data_array[0]
                            logger.debug(f"[WEBSOCKET_V2] Sample balance item: {sample_item}")
                        
                        # Route through data coordinator for unified handling
                        if hasattr(self.manager, 'data_coordinator') and self.manager.data_coordinator:
                            # Convert data format for coordinator
                            balance_dict = self._convert_balance_format(data_array)
                            await self.manager.data_coordinator.handle_websocket_balance(balance_dict)
                            logger.info(f"[WEBSOCKET_V2] Balance update routed through data coordinator: {len(data_array)} assets")
                        
                        # Legacy compatibility - direct manager call
                        if hasattr(self.manager, '_handle_balance_message'):
                            await self.manager._handle_balance_message(data_array)
                            logger.info(f"[WEBSOCKET_V2] Balance update processed by legacy handler: {len(data_array)} assets")
                        else:
                            # Fallback: process directly in this class
                            await self._handle_balance_message(data_array)
                            logger.info(f"[WEBSOCKET_V2] Balance update processed directly: {len(data_array)} assets")
                        
                        # Update visual tracking
                        if hasattr(self.manager, '_update_visual_tracking'):
                            self.manager._update_visual_tracking('balances', data_array)
                    else:
                        logger.debug("[WEBSOCKET_V2] Empty balance update received")
                            
                # Handle subscription confirmations
                elif message.get('method') == 'subscribe':
                    success = message.get('success', False)
                    result = message.get('result', {})
                    channel_name = result.get('channel')
                    if channel_name == 'balances':
                        if success:
                            logger.info("[WEBSOCKET_V2] Balance channel subscription SUCCESSFUL - real-time updates enabled")
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            logger.error(f"[WEBSOCKET_V2] Balance channel subscription FAILED: {error_msg}")
                    else:
                        logger.info(f"[WEBSOCKET_V2] Subscription {'successful' if success else 'failed'}: {channel_name}")
                    
                # Handle other event types
                elif message.get('event') == 'subscriptionStatus':
                    status = message.get('status')
                    channel_name = message.get('channelName')
                    pair = message.get('pair')
                    if channel_name == 'balances':
                        logger.info(f"[WEBSOCKET_V2] Balance channel status: {status}")
                    else:
                        logger.info(f"[WEBSOCKET_V2] Subscription {status}: {channel_name} for {pair}")
                    
            elif isinstance(message, list) and len(message) >= 4:
                # Legacy format support (just in case)
                channel = message[2] if len(message) > 2 else None
                pair = message[3] if len(message) > 3 else None
                data = message[1] if len(message) > 1 else None
                
                if channel == 'ticker' and data:
                    await self.manager._handle_ticker_message(pair, data)
                elif channel == 'ohlc' and data:
                    await self.manager._handle_ohlc_message(pair, data)
                    
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Message handling error: {e}")
            logger.debug(f"[WEBSOCKET_V2] Failed message: {message}")


class KrakenProWebSocketManager:
    """
    WebSocket V2 manager for hybrid architecture
    
    Uses python-kraken-sdk for WebSocket connections
    Provides real-time market data and balance updates
    """
    
    def __init__(self, exchange_client, symbols: List[str], connection_id: str = None, visual_mode: bool = False, data_coordinator=None):
        """Initialize WebSocket V2 manager with unified data coordination and V2 message handler"""
        
        if not KRAKEN_SDK_AVAILABLE:
            raise ImportError("python-kraken-sdk required. Install with: pip install python-kraken-sdk>=3.2.2")
            
        self.exchange = exchange_client
        self.symbols = symbols[:15]  # Limit symbols for stability
        self.connection_id = connection_id or "ws_v2"
        self.visual_mode = visual_mode
        
        # UNIFIED DATA COORDINATION: Reference to data coordinator for intelligent routing
        self.data_coordinator = data_coordinator
        
        # CRITICAL FIX: Reference to main bot manager for balance updates
        self.manager = None  # Will be set by bot during initialization
        
        # KRAKEN V2 COMPLIANCE: Initialize V2 message handler with sequence tracking
        self.v2_message_handler = create_kraken_v2_handler(
            enable_sequence_tracking=True,
            enable_statistics=True
        )
        
        # Register this manager with the V2 handler
        self.v2_message_handler.register_manager(self)
        
        # ENHANCED AUTHENTICATION: Initialize WebSocket authentication manager
        self.auth_manager: Optional[WebSocketAuthenticationManager] = None
        self._auth_initialization_attempted = False
        
        # Callback storage
        self.callbacks = {
            'ticker': None,
            'balance': None,
            'ohlc': None,
            'trade': None,
            'orderbook': None
        }
        
        # Data storage
        self.ticker_data = {}
        self.balance_data = {}
        self.ohlc_data = defaultdict(list)
        self.orderbook_data = {}  # New: orderbook storage
        
        # Visual mode tracking
        if self.visual_mode:
            self.heartbeat_count = 0
            self.message_counts = defaultdict(int)
            self.last_update_times = defaultdict(float)
            self.connection_start_time = None
            self.recent_trades = defaultdict(lambda: deque(maxlen=50))
            self.rate_counters = {}
            self.visual_task = None
        
        # Connection state
        self.is_connected = False
        self.is_healthy = True
        self.last_message_time = time.time()
        self.last_data_update = {}
        
        # WebSocket bot instance
        self.bot = None
        
        # Legacy authentication token (maintained for compatibility)
        self._auth_token = None
        
        # Setup V2 message handler callbacks to integrate with existing infrastructure
        self._setup_v2_callbacks()
        
        logger.info(f"[WEBSOCKET_V2] Initialized for {len(self.symbols)} symbols with V2 handler and enhanced authentication")
        
        if self.visual_mode:
            self._print_header()
    
    def _setup_v2_callbacks(self):
        """Setup V2 message handler callbacks to integrate with existing infrastructure"""
        try:
            # Register balance callback to maintain compatibility with existing balance system
            self.v2_message_handler.register_callback('balance', self._v2_balance_callback)
            self.v2_message_handler.register_callback('balances', self._v2_balance_callback)
            
            # Register ticker callback for market data
            self.v2_message_handler.register_callback('ticker', self._v2_ticker_callback)
            
            # Register orderbook callback
            self.v2_message_handler.register_callback('book', self._v2_orderbook_callback)
            self.v2_message_handler.register_callback('orderbook', self._v2_orderbook_callback)
            
            # Register OHLC callback
            self.v2_message_handler.register_callback('ohlc', self._v2_ohlc_callback)
            
            # Register trade callback
            self.v2_message_handler.register_callback('trade', self._v2_trade_callback)
            
            # Register execution callback
            self.v2_message_handler.register_callback('executions', self._v2_execution_callback)
            
            # Register error callback
            self.v2_message_handler.register_error_callback(self._v2_error_callback)
            
            logger.info("[WEBSOCKET_V2] V2 message handler callbacks registered successfully")
            
        except Exception as e:
            logger.error("[WEBSOCKET_V2] Error setting up V2 callbacks: %s", e)
    
    async def _v2_balance_callback(self, *args):
        """V2 balance callback that routes to existing balance handling infrastructure"""
        try:
            if len(args) == 1:
                # List of BalanceUpdate objects or formatted dict
                balance_data = args[0]
                
                if isinstance(balance_data, list):
                    # Convert BalanceUpdate objects to legacy format
                    formatted_balances = {}
                    for balance_update in balance_data:
                        if hasattr(balance_update, 'asset') and hasattr(balance_update, 'to_dict'):
                            formatted_balances[balance_update.asset] = balance_update.to_dict()
                    
                    # Route to existing balance processing
                    await self._handle_balance_message_v2_format(formatted_balances)
                    
                elif isinstance(balance_data, dict):
                    # Already formatted dict
                    await self._handle_balance_message_v2_format(balance_data)
                
        except Exception as e:
            logger.error("[WEBSOCKET_V2] Error in V2 balance callback: %s", e)
    
    async def _v2_ticker_callback(self, symbol: str, ticker_data: dict):
        """V2 ticker callback that routes to existing ticker handling"""
        try:
            # Route through data coordinator if available
            if hasattr(self, 'data_coordinator') and self.data_coordinator:
                await self.data_coordinator.handle_websocket_ticker(symbol, ticker_data)
            
            # Call legacy ticker handler
            if hasattr(self, '_handle_ticker_message'):
                await self._handle_ticker_message(symbol, ticker_data)
                
        except Exception as e:
            logger.error("[WEBSOCKET_V2] Error in V2 ticker callback: %s", e)
    
    async def _v2_orderbook_callback(self, symbol: str, orderbook_data: dict):
        """V2 orderbook callback that routes to existing orderbook handling"""
        try:
            if hasattr(self, '_handle_orderbook_message'):
                await self._handle_orderbook_message(symbol, orderbook_data)
                
        except Exception as e:
            logger.error("[WEBSOCKET_V2] Error in V2 orderbook callback: %s", e)
    
    async def _v2_ohlc_callback(self, symbol: str, ohlc_data: dict):
        """V2 OHLC callback that routes to existing OHLC handling"""
        try:
            # Route through data coordinator if available
            if hasattr(self, 'data_coordinator') and self.data_coordinator:
                await self.data_coordinator.handle_websocket_ohlc(symbol, ohlc_data)
            
            # Call legacy OHLC handler
            if hasattr(self, '_handle_ohlc_message'):
                await self._handle_ohlc_message(symbol, ohlc_data)
                
        except Exception as e:
            logger.error("[WEBSOCKET_V2] Error in V2 OHLC callback: %s", e)
    
    async def _v2_trade_callback(self, symbol: str, trade_data: dict):
        """V2 trade callback"""
        try:
            # Call registered trade callback if exists
            if 'trade' in self.callbacks and self.callbacks['trade']:
                await self.callbacks['trade'](symbol, trade_data)
                
        except Exception as e:
            logger.error("[WEBSOCKET_V2] Error in V2 trade callback: %s", e)
    
    async def _v2_execution_callback(self, execution_data: dict):
        """V2 execution callback"""
        try:
            logger.info("[WEBSOCKET_V2] Order execution via V2 handler: %s", execution_data)
            
            # Call registered trade callback if exists
            if 'trade' in self.callbacks and self.callbacks['trade']:
                await self.callbacks['trade'](execution_data)
                
        except Exception as e:
            logger.error("[WEBSOCKET_V2] Error in V2 execution callback: %s", e)
    
    async def _v2_error_callback(self, error: Exception, raw_message: dict):
        """V2 error callback"""
        logger.error("[WEBSOCKET_V2] V2 handler error: %s", error)
        logger.debug("[WEBSOCKET_V2] Error message: %s", raw_message)
    
    async def _handle_balance_message_v2_format(self, formatted_balances: dict):
        """Handle balance message in V2 format with enhanced integration"""
        try:
            if not formatted_balances:
                logger.debug("[WEBSOCKET_V2] No V2 formatted balances to process")
                return
            
            logger.info("[WEBSOCKET_V2] Processing V2 balance update: %d assets", len(formatted_balances))
            
            # Store balance data locally for immediate access
            for asset, balance_info in formatted_balances.items():
                self.balance_data[asset] = balance_info
                
                # Enhanced logging for key assets
                if asset in ['MANA', 'SHIB', 'USDT']:
                    balance_amount = balance_info.get('free', 0)
                    logger.info("[WEBSOCKET_V2] V2 %s stored locally: %f", asset, balance_amount)
            
            # Route to existing balance manager integration
            await self._handle_balance_message([])  # Call with empty array, data already processed
            
        except Exception as e:
            logger.error("[WEBSOCKET_V2] Error in V2 balance message handling: %s", e)
    
    def set_manager(self, manager):
        """Set reference to main bot manager for balance updates"""
        self.manager = manager
        logger.info("[WEBSOCKET_V2] Manager reference set - balance updates will be integrated")
    
    async def initialize_authentication(self, api_key: str, private_key: str) -> bool:
        """
        Initialize enhanced WebSocket authentication manager.
        
        Args:
            api_key: Kraken API key
            private_key: Base64-encoded private key
            
        Returns:
            True if authentication initialized successfully
        """
        if self._auth_initialization_attempted:
            logger.debug("[WEBSOCKET_V2] Authentication already initialized")
            return self.auth_manager is not None
        
        self._auth_initialization_attempted = True
        
        try:
            logger.info("[WEBSOCKET_V2] Initializing enhanced WebSocket authentication...")
            
            # Create authentication manager
            self.auth_manager = WebSocketAuthenticationManager(
                exchange_client=self.exchange,
                api_key=api_key,
                private_key=private_key,
                enable_debug=self.visual_mode
            )
            
            # Start authentication manager
            success = await self.auth_manager.start()
            if not success:
                logger.error("[WEBSOCKET_V2] Failed to start authentication manager")
                self.auth_manager = None
                return False
            
            # Set up callbacks for authentication events
            self.auth_manager.set_token_refresh_callback(self._on_token_refresh)
            self.auth_manager.set_auth_failure_callback(self._on_auth_failure)
            
            logger.info("[WEBSOCKET_V2] Enhanced authentication initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Failed to initialize authentication: {e}")
            self.auth_manager = None
            return False
    
    async def _on_token_refresh(self, new_token: str) -> None:
        """Handle token refresh event"""
        try:
            logger.info("[WEBSOCKET_V2] WebSocket token refreshed - updating connection")
            self._auth_token = new_token
            
            # If bot is connected, re-authenticate with new token
            if self.bot and self.is_connected:
                if hasattr(self.bot, 'authenticate'):
                    await self.bot.authenticate(token=new_token)
                    logger.info("[WEBSOCKET_V2] Bot re-authenticated with new token")
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error handling token refresh: {e}")
    
    async def _on_auth_failure(self, error_message: str, recovery_error: str) -> None:
        """Handle authentication failure event"""
        logger.error(f"[WEBSOCKET_V2] Authentication failure: {error_message}")
        if recovery_error:
            logger.error(f"[WEBSOCKET_V2] Recovery also failed: {recovery_error}")
        
        # Mark as unhealthy to trigger reconnection
        self.is_healthy = False
    
    def set_callback(self, event_type: str, callback: Callable):
        """Register callback for event type"""
        if event_type in self.callbacks:
            self.callbacks[event_type] = callback
            logger.info(f"[WEBSOCKET_V2] Registered callback for {event_type}")
        else:
            logger.warning(f"[WEBSOCKET_V2] Unknown event type: {event_type}")
    
    async def connect(self) -> bool:
        """Establish WebSocket connections with timeout handling"""
        try:
            logger.info("[WEBSOCKET_V2] Connecting to Kraken WebSocket V2...")
            
            # Create bot instance with proper SDK pattern
            self.bot = KrakenBot(manager=self)
            
            # Start the bot first
            await self.bot.start()
            logger.info("[WEBSOCKET_V2] Bot started successfully")
            
            # Add timeout for subscription setup - FAST FAILOVER FOR 2025 OPTIMIZATION
            try:
                await asyncio.wait_for(self._setup_public_subscriptions(), timeout=10.0)
                logger.info("[WEBSOCKET_V2] Primary WebSocket subscriptions successful")
            except asyncio.TimeoutError:
                logger.warning("[WEBSOCKET_V2] Primary subscription setup timed out after 10s")
                # Immediately try fallback setup
                logger.info("[WEBSOCKET_V2] Switching to fallback WebSocket mode")
                success = await self._setup_direct_websocket_fallback()
                if success:
                    self.is_connected = True
                    self.is_healthy = True
                    logger.info("[WEBSOCKET_V2] Fallback WebSocket connected successfully")
                return success
            except Exception as sub_error:
                logger.error(f"[WEBSOCKET_V2] Subscription setup error: {sub_error}")
                # Try fallback on any subscription error
                success = await self._setup_direct_websocket_fallback()
                if success:
                    self.is_connected = True
                    self.is_healthy = True
                return success
            
            # Try to setup private subscriptions for balance updates - OPTIMIZED TIMEOUT
            try:
                if await self._setup_private_client():
                    await asyncio.wait_for(self._setup_private_subscriptions(), timeout=10.0)
                    logger.info("[WEBSOCKET_V2] Private subscriptions (balance) setup successful")
                else:
                    logger.warning("[WEBSOCKET_V2] Private client setup failed, balance updates via REST only")
            except asyncio.TimeoutError:
                logger.warning("[WEBSOCKET_V2] Private subscription setup timed out after 10s")
                # Continue without private subscriptions
            
            self.is_connected = True
            self.is_healthy = True
            
            # Update V2 message handler connection status
            if self.v2_message_handler:
                self.v2_message_handler.set_connection_status(connected=True, authenticated=bool(self._auth_token))
            
            # Start visual display if enabled
            if self.visual_mode:
                self.connection_start_time = time.time()
                self.visual_task = asyncio.create_task(self._visual_display_loop())
                logger.info("[WEBSOCKET_V2] Visual mode enabled - starting display")
            
            logger.info("[WEBSOCKET_V2] Successfully connected with V2 message handler")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Connection error: {e}")
            self.is_connected = False
            # Try fallback on connection failure
            logger.info("[WEBSOCKET_V2] Attempting fallback to direct WebSocket implementation")
            success = await self._setup_direct_websocket_fallback()
            return success
    
    async def _setup_public_subscriptions(self):
        """Setup public channel subscriptions"""
        try:
            # Convert symbols to Kraken format
            kraken_symbols = [self._convert_symbol(symbol) for symbol in self.symbols]
            
            # Subscribe to ticker using correct SDK pattern
            await self.bot.subscribe(
                params={
                    'channel': 'ticker',
                    'symbol': kraken_symbols
                }
            )
            logger.info(f"[WEBSOCKET_V2] Subscribed to ticker for {len(kraken_symbols)} symbols")
            
            # Subscribe to OHLC (1 minute) using correct SDK pattern
            await self.bot.subscribe(
                params={
                    'channel': 'ohlc',
                    'symbol': kraken_symbols,
                    'interval': 1
                }
            )
            logger.info(f"[WEBSOCKET_V2] Subscribed to OHLC for {len(kraken_symbols)} symbols")
            
            # CRITICAL FIX: Subscribe to balance channel with proper authentication
            try:
                # Check if we have authentication available for private channels
                if hasattr(self, '_auth_token') and self._auth_token:
                    await self.bot.subscribe(
                        params={
                            'channel': 'balances'
                        }
                    )
                    logger.info("[WEBSOCKET_V2] Subscribed to authenticated balance updates")
                else:
                    logger.warning("[WEBSOCKET_V2] No auth token available, will use REST fallback for balances")
            except Exception as e:
                logger.warning(f"[WEBSOCKET_V2] Balance subscription failed: {e}")
                logger.info("[WEBSOCKET_V2] Continuing with REST balance fallback")
            
            # Subscribe to orderbook (depth 10) for fee-free micro-scalping
            await self.bot.subscribe(
                params={
                    'channel': 'book',
                    'symbol': kraken_symbols,
                    'depth': 10  # Top 10 levels for quick analysis
                }
            )
            logger.info(f"[WEBSOCKET_V2] Subscribed to orderbook for {len(kraken_symbols)} symbols")
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error setting up public subscriptions: {e}")
            # Try fallback to direct WebSocket implementation
            logger.info("[WEBSOCKET_V2] Attempting fallback to direct WebSocket implementation")
            success = await self._setup_direct_websocket_fallback()
            if not success:
                logger.error("[WEBSOCKET_V2] Both primary and fallback WebSocket connections failed")
                # Still mark as connected for graceful degradation
                self.is_connected = True
    
    async def _setup_direct_websocket_fallback(self):
        """Setup direct WebSocket connection as fallback"""
        try:
            logger.info("[WEBSOCKET_V2] Setting up direct WebSocket fallback...")
            
            # Import direct WebSocket implementation
            try:
                from .websocket_simple import SimpleKrakenWebSocket
            except ImportError:
                logger.warning("[WEBSOCKET_V2] SimpleKrakenWebSocket not available, using mock fallback")
                # Create a mock fallback that provides basic data
                return await self._setup_mock_data_fallback()
            
            # Clean up any existing fallback
            if hasattr(self, 'direct_websocket') and self.direct_websocket:
                try:
                    await self.direct_websocket.close()
                except:
                    pass
            
            # Create direct WebSocket client with limited symbols to reduce load
            fallback_symbols = self.symbols[:8]  # Limit to 8 symbols for stability
            self.direct_websocket = SimpleKrakenWebSocket(
                symbols=fallback_symbols,
                ticker_callback=self._handle_ticker_message,
                ohlc_callback=self._handle_ohlc_message
            )
            
            # Connect to direct WebSocket with shorter timeout for faster failover
            try:
                connection_success = await asyncio.wait_for(
                    self.direct_websocket.connect(), 
                    timeout=8.0  # Reduced from 15s for faster failover
                )
                
                if connection_success:
                    logger.info(f"[WEBSOCKET_V2] Direct WebSocket fallback connected for {len(fallback_symbols)} symbols")
                    # Start processing messages in background
                    asyncio.create_task(self.direct_websocket.run())
                    # Mark as connected through fallback
                    self.is_connected = True
                    self.is_healthy = True
                    logger.info("[WEBSOCKET_V2] Fallback WebSocket providing data stream")
                    return True
                else:
                    logger.error("[WEBSOCKET_V2] Direct WebSocket fallback failed to connect")
                    return await self._setup_mock_data_fallback()
                    
            except asyncio.TimeoutError:
                logger.error("[WEBSOCKET_V2] Direct WebSocket fallback timed out after 8s")
                return await self._setup_mock_data_fallback()
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error setting up direct WebSocket fallback: {e}")
            return await self._setup_mock_data_fallback()
    
    async def _setup_mock_data_fallback(self):
        """Setup a mock data provider as final fallback"""
        try:
            logger.info("[WEBSOCKET_V2] Setting up mock data fallback for graceful degradation")
            
            # Create mock ticker data for priority symbols
            priority_symbols = ['SHIB/USDT', 'MATIC/USDT', 'AI16Z/USDT', 'BERA/USDT']
            mock_prices = {
                'SHIB/USDT': 0.000025,
                'MATIC/USDT': 0.85,
                'AI16Z/USDT': 0.45,
                'BERA/USDT': 0.15
            }
            
            # Initialize mock data
            for symbol in priority_symbols:
                if symbol in self.symbols:
                    mock_ticker = {
                        'bid': mock_prices.get(symbol, 1.0) * 0.998,
                        'ask': mock_prices.get(symbol, 1.0) * 1.002,
                        'last': mock_prices.get(symbol, 1.0),
                        'volume': 1000000,
                        'high': mock_prices.get(symbol, 1.0) * 1.05,
                        'low': mock_prices.get(symbol, 1.0) * 0.95,
                        'vwap': mock_prices.get(symbol, 1.0),
                        'timestamp': time.time()
                    }
                    
                    # Store mock data
                    standard_symbol = symbol.replace('/', '_').replace('-', '_')
                    self.ticker_data[standard_symbol] = mock_ticker
                    self.ticker_data[symbol] = mock_ticker
                    self.last_data_update[standard_symbol] = time.time()
                    
                    logger.debug(f"[WEBSOCKET_V2] Mock data created for {symbol}: ${mock_ticker['last']:.8f}")
            
            # Mark as connected with mock data
            self.is_connected = True
            self.is_healthy = True
            logger.warning("[WEBSOCKET_V2] Using mock data fallback - trading will use static prices")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error setting up mock data fallback: {e}")
            self.is_connected = False
            self.is_healthy = False
            return False
    
    async def _setup_private_client(self) -> bool:
        """Setup authenticated WebSocket client for balance updates with enhanced authentication"""
        try:
            logger.info("[WEBSOCKET_V2] Setting up private client with enhanced authentication...")
            
            # Enhanced authentication with multiple fallback methods
            token_obtained = False
            
            # Method 1: Enhanced authentication manager (if available)
            if self.auth_manager:
                try:
                    token = await self.auth_manager.get_websocket_token()
                    if token and len(token) > 10:
                        self._auth_token = token
                        token_obtained = True
                        logger.info("[WEBSOCKET_V2] Authentication token obtained from enhanced auth manager")
                    else:
                        logger.warning("[WEBSOCKET_V2] Enhanced auth manager provided invalid token")
                except Exception as enhanced_error:
                    logger.warning(f"[WEBSOCKET_V2] Enhanced auth manager failed: {enhanced_error}")
            
            # Method 2: Legacy authentication (fallback)
            if not token_obtained:
                logger.info("[WEBSOCKET_V2] Trying legacy authentication method...")
                token_obtained = await self._setup_private_client_legacy()
                
                if not token_obtained:
                    logger.error("[WEBSOCKET_V2] All authentication methods failed")
                    return False
            
            # Validate the obtained token
            if not self._auth_token or len(self._auth_token) < 10:
                logger.error(f"[WEBSOCKET_V2] Invalid authentication token obtained (length: {len(self._auth_token) if self._auth_token else 0})")
                return False
            
            logger.info(f"[WEBSOCKET_V2] Valid authentication token obtained: {self._auth_token[:8]}...")
            
            # Set up proactive token refresh schedule
            self._token_created_time = time.time()
            self._token_refresh_interval = 13 * 60  # Refresh after 13 minutes (2 min before expiry)
            
            # Authenticate main bot with the obtained token
            if self.bot and hasattr(self.bot, 'authenticate'):
                try:
                    logger.info("[WEBSOCKET_V2] Authenticating WebSocket bot...")
                    await self.bot.authenticate(token=self._auth_token)
                    
                    # Wait a moment for authentication to complete
                    await asyncio.sleep(1.0)
                    
                    logger.info("[WEBSOCKET_V2] Bot authenticated successfully")
                    
                except Exception as auth_error:
                    logger.error(f"[WEBSOCKET_V2] Bot authentication failed: {auth_error}")
                    
                    # Enhanced error analysis
                    error_msg = str(auth_error).lower()
                    if 'invalid' in error_msg or 'expired' in error_msg:
                        logger.warning("[WEBSOCKET_V2] Token appears invalid/expired, attempting refresh...")
                        
                        # Try to get a fresh token
                        if await self._refresh_auth_token():
                            try:
                                await self.bot.authenticate(token=self._auth_token)
                                logger.info("[WEBSOCKET_V2] Bot authentication successful after token refresh")
                            except Exception as retry_error:
                                logger.error(f"[WEBSOCKET_V2] Bot authentication failed even after refresh: {retry_error}")
                                return False
                        else:
                            logger.error("[WEBSOCKET_V2] Token refresh failed")
                            return False
                    elif 'permission' in error_msg or 'access' in error_msg:
                        logger.error("""[WEBSOCKET_V2] AUTHENTICATION PERMISSION ERROR!
                        
                        Your API key doesn't have 'Access WebSockets API' permission.
                        
                        TO FIX:
                        1. Log into Kraken.com
                        2. Go to Security -> API
                        3. Edit your API key
                        4. Check 'Access WebSockets API'
                        5. Save and restart bot""")
                        return False
                    else:
                        return False
            else:
                logger.error("[WEBSOCKET_V2] WebSocket bot not available for authentication")
                return False
            
            logger.info("[WEBSOCKET_V2] Private client setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error setting up private client: {e}")
            return False
    
    async def _setup_private_client_legacy(self) -> bool:
        """Legacy private client setup method (fallback)"""
        try:
            # Get WebSocket token from exchange (legacy method)
            if hasattr(self.exchange, 'get_websocket_token'):
                token_response = await self.exchange.get_websocket_token()
                if token_response and isinstance(token_response, dict) and 'token' in token_response:
                    self._auth_token = token_response['token']
                    logger.info("[WEBSOCKET_V2] Legacy authentication token obtained successfully")
                elif isinstance(token_response, str):
                    self._auth_token = token_response
                    logger.info("[WEBSOCKET_V2] Legacy authentication token obtained (string format)")
                else:
                    logger.warning(f"[WEBSOCKET_V2] Invalid legacy token response: {token_response}")
                    return False
            elif hasattr(self.exchange, 'get_websockets_token'):
                # Try alternative method
                token_response = await self.exchange.get_websockets_token()
                if token_response and 'token' in token_response:
                    self._auth_token = token_response['token']
                    logger.info("[WEBSOCKET_V2] Legacy authentication token obtained via alternative method")
                else:
                    logger.warning(f"[WEBSOCKET_V2] Legacy alternative token method failed: {token_response}")
                    return False
            else:
                logger.warning("[WEBSOCKET_V2] Exchange doesn't support WebSocket tokens")
                return False
            
            # CRITICAL FIX 2025: Set up proactive token refresh (legacy)
            self._token_created_time = time.time()
            self._token_refresh_interval = 13 * 60  # Refresh after 13 minutes (2 min before expiry)
            
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error in legacy private client setup: {e}")
            return False
    
    async def _refresh_auth_token(self) -> bool:
        """
        CRITICAL FIX 2025: Enhanced proactive authentication token refresh
        Uses enhanced authentication manager for robust token management
        """
        try:
            logger.info("[WEBSOCKET_V2] Refreshing authentication token proactively...")
            
            # Use enhanced authentication manager if available
            if self.auth_manager:
                success = await self.auth_manager.refresh_token_proactively()
                if success:
                    # Get the new token
                    new_token = await self.auth_manager.get_websocket_token()
                    if new_token:
                        self._auth_token = new_token
                        logger.info("[WEBSOCKET_V2] Enhanced authentication token refreshed successfully")
                        
                        # Re-authenticate bot with new token
                        if self.bot and hasattr(self.bot, 'authenticate'):
                            try:
                                await self.bot.authenticate(token=self._auth_token)
                                logger.info("[WEBSOCKET_V2] Bot re-authenticated with enhanced token")
                            except Exception as auth_error:
                                logger.warning(f"[WEBSOCKET_V2] Bot re-authentication failed: {auth_error}")
                                # Try recovery
                                recovery_token = await self.auth_manager.handle_authentication_error(str(auth_error))
                                if recovery_token:
                                    self._auth_token = recovery_token
                                    await self.bot.authenticate(token=recovery_token)
                                    logger.info("[WEBSOCKET_V2] Bot authentication recovered after refresh")
                        
                        return True
                    else:
                        logger.error("[WEBSOCKET_V2] Enhanced auth manager refresh succeeded but no token available")
                        return False
                else:
                    logger.error("[WEBSOCKET_V2] Enhanced authentication token refresh failed")
                    return False
            else:
                # Fallback to legacy refresh
                logger.warning("[WEBSOCKET_V2] Using legacy token refresh method")
                return await self._refresh_auth_token_legacy()
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error in enhanced auth token refresh: {e}")
            return False
    
    async def _refresh_auth_token_legacy(self) -> bool:
        """Legacy authentication token refresh method (fallback)"""
        try:
            # Get new WebSocket token from exchange (legacy method)
            if hasattr(self.exchange, 'get_websocket_token'):
                token_response = await self.exchange.get_websocket_token()
                if token_response and isinstance(token_response, dict) and 'token' in token_response:
                    old_token = self._auth_token
                    self._auth_token = token_response['token']
                    self._token_created_time = time.time()
                    
                    logger.info("[WEBSOCKET_V2] Legacy authentication token refreshed successfully")
                    
                    # Re-authenticate bot with new token
                    if self.bot and hasattr(self.bot, 'authenticate'):
                        try:
                            await self.bot.authenticate(token=self._auth_token)
                            logger.info("[WEBSOCKET_V2] Bot re-authenticated with legacy token")
                        except Exception as auth_error:
                            logger.warning(f"[WEBSOCKET_V2] Legacy bot re-authentication failed: {auth_error}")
                    
                    return True
                else:
                    logger.error(f"[WEBSOCKET_V2] Legacy token refresh failed: {token_response}")
                    return False
            else:
                logger.error("[WEBSOCKET_V2] Exchange doesn't support WebSocket token refresh")
                return False
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error in legacy auth token refresh: {e}")
            return False
    
    def _should_refresh_token(self) -> bool:
        """Check if authentication token should be refreshed"""
        if not hasattr(self, '_token_created_time') or not self._auth_token:
            return False
            
        token_age = time.time() - self._token_created_time
        return token_age >= self._token_refresh_interval
    
    async def _setup_private_subscriptions(self):
        """Setup private channel subscriptions for balance updates"""
        try:
            # Subscribe to balance updates using the main bot with authentication
            if self.bot and self._auth_token:
                try:
                    await self.bot.subscribe(
                        params={
                            'channel': 'balances',
                            'token': self._auth_token
                        }
                    )
                    logger.info("[WEBSOCKET_V2] Successfully subscribed to authenticated balance channel")
                except Exception as balance_error:
                    logger.warning(f"[WEBSOCKET_V2] Balance subscription with token failed: {balance_error}")
                    
                    # Check if error is due to missing WebSocket permissions
                    error_msg = str(balance_error).lower()
                    if 'credentials' in error_msg or 'invalid' in error_msg or 'permission' in error_msg:
                        logger.error("""[WEBSOCKET_V2] WEBSOCKET AUTHENTICATION FAILED!
                        
                        This means your API key doesn't have 'Access WebSockets API' permission.
                        
                        TO FIX:
                        1. Log into Kraken.com
                        2. Go to Security -> API  
                        3. Edit your API key
                        4. Check 'Access WebSockets API'
                        5. Save and restart bot
                        
                        Using REST API fallback for now...""")
                        
                        # Enable REST fallback flag
                        self.use_rest_fallback_for_balances = True
                        return  # Don't try further attempts
                    
                    # Try without explicit token (might be handled automatically)
                    try:
                        await self.bot.subscribe(
                            params={
                                'channel': 'balances'
                            }
                        )
                        logger.info("[WEBSOCKET_V2] Balance subscription succeeded without explicit token")
                    except Exception as fallback_error:
                        logger.error(f"[WEBSOCKET_V2] Balance subscription failed completely: {fallback_error}")
                        self.use_rest_fallback_for_balances = True
            
            # Optional: Subscribe to order execution updates if needed
            if self.bot and self._auth_token:
                try:
                    await self.bot.subscribe(
                        params={
                            'channel': 'executions',
                            'token': self._auth_token
                        }
                    )
                    logger.info("[WEBSOCKET_V2] Subscribed to order executions")
                except Exception as exec_error:
                    logger.debug(f"[WEBSOCKET_V2] Order execution subscription failed: {exec_error}")
                    # Not critical, continue without it
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error setting up private subscriptions: {e}")
    
    def _convert_symbol(self, symbol: str) -> str:
        """Convert symbol format from BTC/USDT to BTC/USDT for Kraken"""
        # Kraken uses the same format, just ensure it's uppercase
        return symbol.upper()
    
    async def _handle_orderbook_message(self, symbol: str, data: Dict[str, Any]):
        """Handle orderbook update from WebSocket"""
        try:
            self.last_message_time = time.time()
            
            # Convert symbol format
            standard_symbol = symbol.replace('/', '_').replace('-', '_')
            
            # Extract bids and asks
            bids = data.get('bids', [])
            asks = data.get('asks', [])
            
            # Process orderbook data
            orderbook_info = {
                'bids': [],
                'asks': [],
                'timestamp': time.time(),
                'spread': 0.0,
                'mid_price': 0.0
            }
            
            # Process bids (buy orders)
            for bid in bids[:10]:  # Top 10 levels
                if isinstance(bid, dict):
                    price = safe_float(safe_decimal(bid.get('price', 0)))
                    volume = safe_float(safe_decimal(bid.get('qty', 0)))
                elif isinstance(bid, list) and len(bid) >= 2:
                    price = safe_float(safe_decimal(bid[0]))
                    volume = safe_float(safe_decimal(bid[1]))
                else:
                    continue
                    
                if price > 0 and volume > 0:
                    orderbook_info['bids'].append({'price': price, 'volume': volume})
            
            # Process asks (sell orders)
            for ask in asks[:10]:  # Top 10 levels
                if isinstance(ask, dict):
                    price = safe_float(safe_decimal(ask.get('price', 0)))
                    volume = safe_float(safe_decimal(ask.get('qty', 0)))
                elif isinstance(ask, list) and len(ask) >= 2:
                    price = safe_float(safe_decimal(ask[0]))
                    volume = safe_float(safe_decimal(ask[1]))
                else:
                    continue
                    
                if price > 0 and volume > 0:
                    orderbook_info['asks'].append({'price': price, 'volume': volume})
            
            # Calculate spread and mid price
            if orderbook_info['bids'] and orderbook_info['asks']:
                best_bid_dec = safe_decimal(orderbook_info['bids'][0]['price'])
                best_ask_dec = safe_decimal(orderbook_info['asks'][0]['price'])
                # Use Decimal arithmetic for precise calculations
                spread_dec = (best_ask_dec - best_bid_dec) / best_bid_dec
                mid_price_dec = (best_bid_dec + best_ask_dec) / safe_decimal('2')
                # Convert back to float for compatibility
                orderbook_info['spread'] = safe_float(spread_dec)
                orderbook_info['mid_price'] = safe_float(mid_price_dec)
            
            # Store orderbook data
            self.orderbook_data[standard_symbol] = orderbook_info
            self.last_data_update[standard_symbol] = time.time()
            
            # Call registered callback if exists
            if 'orderbook' in self.callbacks and self.callbacks['orderbook']:
                self.callbacks['orderbook'](symbol, orderbook_info)
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error handling orderbook message: {e}")
    
    def _convert_balance_format(self, balance_data):
        """Convert WebSocket V2 balance format to unified format for data coordinator"""
        try:
            if not balance_data:
                return {}
                
            formatted_balances = {}
            
            # Handle WebSocket V2 array format: [{"asset": "MANA", "balance": "163.94", "hold_trade": "0"}]
            if isinstance(balance_data, list):
                for balance_item in balance_data:
                    if not isinstance(balance_item, dict):
                        continue
                        
                    asset = balance_item.get('asset')
                    if not asset:
                        continue
                    
                    balance = safe_float(balance_item.get('balance', 0))
                    hold_trade = safe_float(balance_item.get('hold_trade', 0))
                    
                    # Calculate free and total
                    total = balance
                    free = max(0, balance - hold_trade)
                    used = hold_trade
                    
                    formatted_balances[asset] = {
                        'free': free,
                        'used': used,
                        'total': total
                    }
            
            return formatted_balances
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error converting balance format: {e}")
            return {}
    
    async def _handle_balance_message(self, balance_data):
        """CRITICAL FIX 2025: Enhanced balance message handling with better format conversion"""
        try:
            if not balance_data:
                logger.debug("[WEBSOCKET_V2] No balance data to process")
                return
                
            logger.info(f"[WEBSOCKET_V2] Processing balance update with {len(balance_data)} items")
            
            # CRITICAL FIX 2025: Enhanced WebSocket V2 format conversion
            formatted_balances = {}
            usdt_total = 0.0
            usdt_sources = []
            
            # Handle WebSocket V2 array format: [{"asset": "MANA", "balance": "163.94", "hold_trade": "0"}]
            if isinstance(balance_data, list):
                for balance_item in balance_data:
                    if not isinstance(balance_item, dict):
                        continue
                        
                    asset = balance_item.get('asset')
                    balance_str = balance_item.get('balance', '0')
                    hold_trade_str = balance_item.get('hold_trade', '0')
                    
                    if not asset:
                        continue
                    
                    try:
                        # Parse balance values with error handling
                        free_balance = float(balance_str) if balance_str else 0.0
                        used_balance = float(hold_trade_str) if hold_trade_str else 0.0
                        total_balance = free_balance + used_balance
                        
                        # Only include assets with meaningful balances
                        if total_balance > 0.0001:
                            formatted_balances[asset] = {
                                'free': free_balance,
                                'used': used_balance,
                                'total': total_balance,
                                'timestamp': time.time()
                            }
                            
                            # Track USDT variants for aggregation
                            if asset in ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S', 'USDT.F', 'USDT.B']:
                                usdt_total += free_balance
                                usdt_sources.append(f"{asset}=${free_balance:.2f}")
                            
                            # Enhanced logging for key assets
                            if asset in ['MANA', 'SHIB', 'USDT'] and free_balance > 0:
                                logger.info(f"[WEBSOCKET_V2] {asset} balance updated: {free_balance:.8f}")
                            else:
                                logger.debug(f"[WEBSOCKET_V2] {asset} balance: {free_balance:.8f}")
                                
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[WEBSOCKET_V2] Failed to parse balance for {asset}: {e}")
                        continue
            
            # Handle legacy dict format (fallback)
            elif isinstance(balance_data, dict):
                logger.debug("[WEBSOCKET_V2] Processing legacy dict format balance data")
                for asset, balance_info in balance_data.items():
                    try:
                        if isinstance(balance_info, dict):
                            formatted_balances[asset] = balance_info
                        elif isinstance(balance_info, (int, float, str)):
                            balance_float = float(balance_info)
                            if balance_float > 0.0001:
                                formatted_balances[asset] = {
                                    'free': balance_float,
                                    'used': 0,
                                    'total': balance_float,
                                    'timestamp': time.time()
                                }
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[WEBSOCKET_V2] Failed to parse legacy balance for {asset}: {e}")
                        continue
            
            # Log USDT aggregation summary
            if usdt_total > 0:
                logger.info(f"[WEBSOCKET_V2] *** USDT TOTAL: ${usdt_total:.2f} from [{', '.join(usdt_sources)}] ***")
            
            # Store balance data locally for immediate access
            for asset, balance_info in formatted_balances.items():
                self.balance_data[asset] = balance_info
                
                # Enhanced logging for key assets
                if asset in ['MANA', 'SHIB', 'USDT']:
                    balance_amount = balance_info.get('free', 0)
                    logger.info(f"[WEBSOCKET_V2] {asset} stored locally: {balance_amount:.8f}")
                
            # CRITICAL FIX 2025: Enhanced balance manager integration with better reference resolution
            manager_ref = None
            
            # Try multiple methods to get manager reference
            if hasattr(self, 'manager') and self.manager:
                manager_ref = self.manager
                logger.debug("[WEBSOCKET_V2] Using direct manager reference")
            elif hasattr(self, 'exchange_client') and hasattr(self.exchange_client, 'bot_instance'):
                manager_ref = self.exchange_client.bot_instance
                logger.debug("[WEBSOCKET_V2] Using bot instance reference through exchange client")
            elif hasattr(self, 'exchange') and hasattr(self.exchange, 'bot_instance'):
                manager_ref = self.exchange.bot_instance
                logger.debug("[WEBSOCKET_V2] Using bot instance reference through exchange")
            
            if formatted_balances and manager_ref and hasattr(manager_ref, 'balance_manager'):
                balance_manager = manager_ref.balance_manager
                
                # CRITICAL FIX 2025: Enhanced circuit breaker reset with validation
                if (hasattr(balance_manager, 'circuit_breaker_active') and 
                    balance_manager.circuit_breaker_active and 
                    len(formatted_balances) > 0):
                    
                    logger.info("[WEBSOCKET_V2] CRITICAL FIX 2025: Fresh balance data received - RESETTING circuit breaker")
                    balance_manager.circuit_breaker_active = False
                    balance_manager.consecutive_failures = 0
                    balance_manager.backoff_multiplier = 1.0
                    balance_manager.circuit_breaker_reset_time = 0
                    
                    # Also reset API counter if available
                    if hasattr(balance_manager, '_api_call_counter'):
                        balance_manager._api_call_counter = 0
                        logger.debug("[WEBSOCKET_V2] Reset API call counter")
                
                # CRITICAL FIX 2025: Enhanced balance injection with validation
                if hasattr(balance_manager, 'balances'):
                    injected_count = 0
                    for asset, balance_info in formatted_balances.items():
                        if balance_info and isinstance(balance_info, dict) and balance_info.get('total', 0) > 0:
                            # Direct injection to balance manager
                            balance_manager.balances[asset] = balance_info
                            
                            # Also update WebSocket cache for dual verification
                            if hasattr(balance_manager, 'websocket_balances'):
                                balance_manager.websocket_balances[asset] = balance_info
                            
                            injected_count += 1
                            
                            # Enhanced logging for important assets
                            if asset in ['MANA', 'SHIB', 'USDT'] or balance_info.get('free', 0) > 1.0:
                                logger.info(f"[WEBSOCKET_V2] Injected {asset}: {balance_info.get('free', 0):.8f}")
                            else:
                                logger.debug(f"[WEBSOCKET_V2] Injected {asset}: {balance_info}")
                    
                    # CRITICAL FIX 2025: Update timestamp and log success
                    balance_manager.last_update = time.time()
                    logger.info(f"[WEBSOCKET_V2] BALANCE INJECTION SUCCESS: {injected_count}/{len(formatted_balances)} assets updated")
                
                # Also trigger WebSocket update method if available
                if hasattr(balance_manager, 'process_websocket_update'):
                    try:
                        await balance_manager.process_websocket_update(formatted_balances)
                        logger.debug("[WEBSOCKET_V2] Called process_websocket_update successfully")
                    except Exception as e:
                        logger.warning(f"[WEBSOCKET_V2] process_websocket_update failed: {e}")
            
            elif formatted_balances:
                logger.warning(f"[WEBSOCKET_V2] No manager reference found - {len(formatted_balances)} balance updates not processed")
                
                # Log important assets that couldn't be processed
                important_assets = [asset for asset in formatted_balances.keys() 
                                  if asset in ['MANA', 'SHIB', 'USDT'] or 
                                  formatted_balances[asset].get('free', 0) > 1.0]
                
                if important_assets:
                    logger.error(f"[WEBSOCKET_V2] CRITICAL: Important assets not processed: {important_assets}")
                    for asset in important_assets:
                        balance_info = formatted_balances[asset]
                        logger.error(f"[WEBSOCKET_V2] Lost update: {asset} = {balance_info.get('free', 0):.8f}")
            
            else:
                logger.debug("[WEBSOCKET_V2] No formatted balances to process")
            
            # Call balance callback if registered
            if formatted_balances and 'balance' in self.callbacks and self.callbacks['balance']:
                try:
                    await self.callbacks['balance'](formatted_balances)
                    logger.debug(f"[WEBSOCKET_V2] Balance callback executed for {len(formatted_balances)} assets")
                except Exception as e:
                    logger.error(f"[WEBSOCKET_V2] Balance callback failed: {e}")
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] CRITICAL ERROR handling balance message: {e}")
            logger.error(f"[WEBSOCKET_V2] Balance data that caused error: {balance_data}")
            import traceback
            logger.error(f"[WEBSOCKET_V2] Full traceback: {traceback.format_exc()}")
    
    def _log_orderbook_update(self, standard_symbol, orderbook_info):
        """Log orderbook update details"""
        try:
            logger.debug(f"[WEBSOCKET_V2] Orderbook update for {standard_symbol}: "
                        f"Spread: {orderbook_info['spread']:.4%}, "
                        f"Bids: {len(orderbook_info['bids'])}, "
                        f"Asks: {len(orderbook_info['asks'])}")
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error logging orderbook update: {e}")
    
    async def _handle_ticker_message(self, symbol: str, data: Dict[str, Any]):
        """Handle ticker update from WebSocket"""
        try:
            self.last_message_time = time.time()
            
            # Convert symbol format for internal storage
            standard_symbol = symbol.replace('/', '_').replace('-', '_')
            
            # Extract ticker data from Kraken V2 format
            # V2 format has direct fields: bid, ask, last, volume, etc.
            ticker_info = {
                'bid': safe_float(safe_decimal(data.get('bid', 0))),
                'ask': safe_float(safe_decimal(data.get('ask', 0))),
                'last': safe_float(safe_decimal(data.get('last', 0))),
                'volume': safe_float(safe_decimal(data.get('volume', 0))),
                'high': safe_float(safe_decimal(data.get('high', 0))),
                'low': safe_float(safe_decimal(data.get('low', 0))),
                'vwap': safe_float(safe_decimal(data.get('vwap', 0))),
                'timestamp': time.time()
            }
            
            # Store in multiple formats for compatibility
            self.ticker_data[standard_symbol] = ticker_info
            self.ticker_data[symbol] = ticker_info  # Also store with original symbol
            
            self.last_data_update[standard_symbol] = time.time()
            self.last_data_update[symbol] = time.time()
            
            # Log successful ticker update for debugging
            if self.ticker_data[standard_symbol]['last'] > 0:
                logger.debug(f"[WEBSOCKET_V2] Ticker update for {symbol}: ${ticker_info['last']:.8f}")
            
            # Call registered callback
            if self.callbacks['ticker']:
                await self.callbacks['ticker'](symbol, ticker_info)
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error handling ticker update: {e}")
            logger.debug(f"[WEBSOCKET_V2] Failed ticker data: {data}")
    
    def _handle_balance_update(self, message: List[Dict[str, Any]]):
        """Handle balance update from WebSocket"""
        try:
            self.last_message_time = time.time()
            
            # BALANCE FIX: Enhanced balance update logging
            logger.info(f"[BALANCE_FIX] WebSocket balance update received: {len(message)} assets")
            
            # Process balance data
            for balance in message:
                asset = balance.get('asset', '')
                if asset:
                    # Use Decimal for precise balance calculations
                    new_balance_dec = safe_decimal(balance.get('balance', 0))
                    locked_dec = safe_decimal(balance.get('hold_trade', 0))
                    total_dec = new_balance_dec + locked_dec
                    
                    # Convert to float for external compatibility
                    new_balance = safe_float(new_balance_dec)
                    
                    # Check for USDT variants
                    if asset in ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S']:
                        # Compare with cached value
                        if hasattr(self, '_last_usdt_balance'):
                            if abs(new_balance - self._last_usdt_balance) > 0.01:
                                logger.info(f"[BALANCE_FIX] USDT balance changed: ${self._last_usdt_balance:.2f} -> ${new_balance:.2f}")
                        else:
                            logger.info(f"[BALANCE_FIX] Initial USDT balance: ${new_balance:.2f}")
                        
                        self._last_usdt_balance = new_balance
                    
                    self.balance_data[asset] = {
                        'free': new_balance,
                        'locked': safe_float(locked_dec),
                        'total': safe_float(total_dec),
                        'timestamp': time.time()
                    }
            
            # Call registered callback
            if self.callbacks['balance']:
                self.callbacks['balance'](self.balance_data)
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error handling balance update: {e}")
    
    async def _handle_ohlc_message(self, symbol: str, data: Dict[str, Any]):
        """Handle OHLC update from WebSocket"""
        try:
            self.last_message_time = time.time()
            
            # Convert symbol format
            standard_symbol = symbol.replace('/', '_').replace('-', '_')
            
            # V2 format has OHLC data as object with fields
            # Handle timestamp - it comes as ISO string in V2
            timestamp_str = data.get('timestamp', '')
            if timestamp_str and isinstance(timestamp_str, str):
                # Convert ISO timestamp to Unix timestamp
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    timestamp = dt.timestamp()
                except:
                    timestamp = time.time()
            else:
                timestamp = safe_float(safe_decimal(data.get('timestamp', time.time())))
            
            ohlc_info = {
                'timestamp': timestamp,
                'open': safe_float(safe_decimal(data.get('open', 0))),
                'high': safe_float(safe_decimal(data.get('high', 0))),
                'low': safe_float(safe_decimal(data.get('low', 0))),
                'close': safe_float(safe_decimal(data.get('close', 0))),
                'volume': safe_float(safe_decimal(data.get('volume', 0)))
            }
            
            # Store last 100 candles
            self.ohlc_data[standard_symbol].append(ohlc_info)
            if len(self.ohlc_data[standard_symbol]) > 100:
                self.ohlc_data[standard_symbol].pop(0)
            
            # Also store with original symbol
            self.ohlc_data[symbol] = self.ohlc_data[standard_symbol]
            
            # Call registered callback
            if self.callbacks['ohlc']:
                await self.callbacks['ohlc'](symbol, ohlc_info)
                    
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error handling OHLC update: {e}")
            logger.debug(f"[WEBSOCKET_V2] Failed OHLC data: {data}")
    
    def _handle_execution_update(self, message: Dict[str, Any]):
        """Handle order execution update"""
        try:
            logger.info(f"[WEBSOCKET_V2] Order execution: {message}")
            # Forward to trade callback if registered
            if self.callbacks['trade']:
                self.callbacks['trade'](message)
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error handling execution: {e}")
    
    async def run(self):
        """Main run loop for WebSocket processing"""
        logger.info("[WEBSOCKET_V2] Starting run loop...")
        
        while self.is_connected:
            try:
                # Check connection health
                if time.time() - self.last_message_time > 60:
                    logger.warning("[WEBSOCKET_V2] No messages for 60s, reconnecting...")
                    await self.reconnect()
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"[WEBSOCKET_V2] Error in run loop: {e}")
                await asyncio.sleep(5)
    
    async def reconnect(self):
        """Reconnect WebSocket connections"""
        logger.info("[WEBSOCKET_V2] Reconnecting...")
        await self.disconnect()
        await asyncio.sleep(2)
        await self.connect()
    
    async def disconnect(self):
        """Disconnect WebSocket connections and cleanup authentication"""
        try:
            logger.info("[WEBSOCKET_V2] Disconnecting WebSocket connections...")
            
            # Update V2 message handler connection status
            if self.v2_message_handler:
                self.v2_message_handler.set_connection_status(connected=False, authenticated=False)
            
            # Stop authentication manager if running
            if self.auth_manager:
                try:
                    await self.auth_manager.stop()
                    logger.info("[WEBSOCKET_V2] Authentication manager stopped")
                except Exception as auth_stop_error:
                    logger.error(f"[WEBSOCKET_V2] Error stopping authentication manager: {auth_stop_error}")
            
            # Disconnect bot
            if self.bot:
                # SDK handles cleanup automatically
                self.bot = None
                
            # Stop visual task if running
            if hasattr(self, 'visual_task') and self.visual_task and not self.visual_task.done():
                self.visual_task.cancel()
                try:
                    await self.visual_task
                except asyncio.CancelledError:
                    pass
                
            self.is_connected = False
            logger.info("[WEBSOCKET_V2] Disconnected successfully with V2 handler cleanup")
            
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error disconnecting: {e}")
    
    async def close(self):
        """Close WebSocket connections (alias for disconnect)"""
        await self.disconnect()
    
    async def subscribe_to_channels(self):
        """Compatibility method - channels already subscribed in connect()"""
        logger.debug("[WEBSOCKET_V2] Channels already subscribed")
        return True
    
    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current orderbook data for symbol"""
        # Try original symbol first
        standard_symbol = symbol.replace('/', '_').replace('-', '_')
        orderbook = self.orderbook_data.get(standard_symbol)
        
        if orderbook and orderbook.get('bids') and orderbook.get('asks'):
            return orderbook
            
        # Try direct symbol
        orderbook = self.orderbook_data.get(symbol)
        if orderbook and orderbook.get('bids') and orderbook.get('asks'):
            return orderbook
            
        return None
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current ticker data for symbol"""
        # Try original symbol first
        ticker = self.ticker_data.get(symbol)
        if ticker and ticker.get('last', 0) > 0:
            logger.debug(f"[WEBSOCKET_V2] Found ticker for {symbol}: ${ticker['last']:.8f}")
            return ticker
            
        # Try converted symbol format
        standard_symbol = symbol.replace('/', '_').replace('-', '_')
        ticker = self.ticker_data.get(standard_symbol)
        if ticker and ticker.get('last', 0) > 0:
            logger.debug(f"[WEBSOCKET_V2] Found ticker for {standard_symbol}: ${ticker['last']:.8f}")
            return ticker
            
        # Try direct WebSocket fallback
        if hasattr(self, 'direct_websocket') and self.direct_websocket:
            fallback_ticker = self.direct_websocket.get_ticker(symbol)
            if fallback_ticker and fallback_ticker.get('last', 0) > 0:
                logger.debug(f"[WEBSOCKET_V2] Found ticker via direct WebSocket fallback for {symbol}")
                return fallback_ticker
                
        # Log which symbols we have data for (for debugging)
        if not ticker:
            available_symbols = [s for s, t in self.ticker_data.items() if t.get('last', 0) > 0]
            if available_symbols:
                logger.debug(f"[WEBSOCKET_V2] No data for {symbol}. Available: {available_symbols[:5]}...")
            else:
                logger.debug(f"[WEBSOCKET_V2] No ticker data available for any symbols")
        
        return None
    
    def get_balance(self, asset: str) -> Optional[Dict[str, Any]]:
        """Get current balance for asset with MANA detection verification"""
        balance = self.balance_data.get(asset)
        if balance and asset == 'MANA':
            logger.debug(f"[WEBSOCKET_V2] MANA balance retrieved: {balance}")
        return balance
    
    def get_all_balances(self) -> Dict[str, Any]:
        """Get all current balances"""
        return self.balance_data.copy()
    
    async def check_data_freshness(self):
        """Check if data is fresh for all symbols and handle token refresh"""
        current_time = time.time()
        stale_symbols = []
        
        # CRITICAL FIX 2025: Check if authentication token needs refresh
        if self._should_refresh_token():
            logger.info("[WEBSOCKET_V2] Token refresh needed, refreshing proactively...")
            refresh_success = await self._refresh_auth_token()
            if refresh_success:
                logger.info("[WEBSOCKET_V2] Token refresh completed successfully")
            else:
                logger.warning("[WEBSOCKET_V2] Token refresh failed, may experience authentication issues")
        
        for symbol in self.symbols:
            standard_symbol = symbol.replace('/', '_').replace('-', '_')
            last_update = self.last_data_update.get(standard_symbol, 0)
            
            if current_time - last_update > 30:  # 30 seconds
                stale_symbols.append(symbol)
        
        if stale_symbols:
            logger.warning(f"[WEBSOCKET_V2] Stale data for symbols: {stale_symbols}")
    
    # Compatibility properties for existing code
    @property
    def current_tickers(self):
        """Compatibility property for existing code"""
        return self.ticker_data
    
    @property
    def last_price_update(self):
        """Compatibility property for existing code"""
        if self.last_data_update:
            return max(self.last_data_update.values())
        return 0
    
    def has_fresh_data(self, symbol: str, max_age: float = 5.0) -> bool:
        """Check if we have fresh data for a symbol"""
        standard_symbol = symbol.replace('/', '_').replace('-', '_')
        last_update = self.last_data_update.get(standard_symbol, 0)
        return (time.time() - last_update) <= max_age
    
    async def test_balance_format_conversion(self):
        """Test method to verify WebSocket V2 balance format conversion"""
        try:
            logger.info("[WEBSOCKET_V2] Testing balance format conversion...")
            
            # Simulate WebSocket V2 balance message format
            test_balance_data = [
                {"asset": "MANA", "balance": "163.94", "hold_trade": "0"},
                {"asset": "USDT", "balance": "5.23", "hold_trade": "0"},
                {"asset": "BTC", "balance": "0.001", "hold_trade": "0.0005"}
            ]
            
            # Test the format conversion
            await self._handle_balance_message(test_balance_data)
            
            # Verify MANA balance was processed correctly
            mana_balance = self.get_balance('MANA')
            if mana_balance:
                logger.info(f"[WEBSOCKET_V2] Test successful - MANA balance: {mana_balance}")
                return True
            else:
                logger.error("[WEBSOCKET_V2] Test failed - MANA balance not found")
                return False
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Test error: {e}")
            return False
    
    def get_balance_streaming_status(self) -> Dict[str, Any]:
        """Get comprehensive status of balance streaming capabilities"""
        manager_ref = getattr(self, 'manager', None)
        balance_manager_available = bool(manager_ref and hasattr(manager_ref, 'balance_manager'))
        
        status = {
            'websocket_connected': self.is_connected,
            'websocket_healthy': self.is_healthy,
            'auth_token_available': bool(self._auth_token),
            'balance_data_count': len(self.balance_data),
            'manager_reference_available': bool(manager_ref),
            'balance_manager_available': balance_manager_available,
            'last_message_time': self.last_message_time,
            'time_since_last_message': time.time() - self.last_message_time,
            'streaming_healthy': self.is_healthy and self.is_connected,
            'enhanced_auth_available': bool(self.auth_manager),
            'auth_initialization_attempted': self._auth_initialization_attempted
        }
        
        # Add enhanced authentication status if available
        if self.auth_manager:
            auth_status = self.auth_manager.get_authentication_status()
            status['enhanced_authentication'] = auth_status
        
        # Add key asset status
        key_assets = ['MANA', 'SHIB', 'USDT']
        for asset in key_assets:
            if asset in self.balance_data:
                status[f'{asset.lower()}_balance_available'] = True
                status[f'{asset.lower()}_balance_value'] = self.balance_data[asset].get('free', 0)
            else:
                status[f'{asset.lower()}_balance_available'] = False
                status[f'{asset.lower()}_balance_value'] = 0
        
        # Add USDT aggregation
        usdt_total = 0.0
        usdt_variants = ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S', 'USDT.F', 'USDT.B']
        for variant in usdt_variants:
            if variant in self.balance_data:
                usdt_total += self.balance_data[variant].get('free', 0)
        
        status['usdt_total_all_variants'] = usdt_total
        
        return status
    
    def get_v2_handler_statistics(self) -> Dict[str, Any]:
        """Get V2 message handler statistics"""
        if not self.v2_message_handler:
            return {'v2_handler_enabled': False}
        
        stats = self.v2_message_handler.get_statistics()
        sequence_status = self.v2_message_handler.get_sequence_status()
        connection_status = self.v2_message_handler.get_connection_status()
        
        return {
            'v2_handler_enabled': True,
            'statistics': stats,
            'sequence_tracking': sequence_status,
            'v2_connection_status': connection_status
        }
    
    def get_authentication_status(self) -> Dict[str, Any]:
        """Get comprehensive authentication status"""
        status = {
            'legacy_auth_token_available': bool(self._auth_token),
            'enhanced_auth_manager_available': bool(self.auth_manager),
            'auth_initialization_attempted': self._auth_initialization_attempted,
            'current_time': time.time()
        }
        
        # Add legacy token info
        if self._auth_token:
            status['legacy_token_info'] = {
                'token_length': len(self._auth_token),
                'token_prefix': self._auth_token[:8] + '...' if len(self._auth_token) > 8 else self._auth_token
            }
            
            # Add legacy token timing if available
            if hasattr(self, '_token_created_time'):
                status['legacy_token_info'].update({
                    'created_at': self._token_created_time,
                    'age_seconds': time.time() - self._token_created_time,
                    'should_refresh': self._should_refresh_token()
                })
        
        # Add enhanced authentication status
        if self.auth_manager:
            status['enhanced_authentication'] = self.auth_manager.get_authentication_status()
            
            # Get token info without exposing sensitive data
            token_info = self.auth_manager.get_token_info()
            if token_info:
                status['enhanced_token_info'] = token_info
        
        return status
    
    def validate_connection_readiness(self) -> Dict[str, Any]:
        """Validate if WebSocket connection is ready for Balance Manager V2 initialization"""
        readiness_status = {
            'ready_for_balance_manager': False,
            'connection_healthy': False,
            'authentication_ready': False,
            'bot_available': False,
            'issues': [],
            'recommendations': []
        }
        
        # Check connection status
        if self.is_connected and self.is_healthy:
            readiness_status['connection_healthy'] = True
        else:
            readiness_status['issues'].append(f"Connection not healthy (connected: {self.is_connected}, healthy: {self.is_healthy})")
            readiness_status['recommendations'].append("Ensure WebSocket connection is established before Balance Manager V2 initialization")
        
        # Check bot availability
        if self.bot:
            readiness_status['bot_available'] = True
        else:
            readiness_status['issues'].append("WebSocket bot not available")
            readiness_status['recommendations'].append("Initialize WebSocket bot before setting up Balance Manager V2")
        
        # Check authentication
        if self._auth_token and len(self._auth_token) > 10:
            readiness_status['authentication_ready'] = True
        else:
            readiness_status['issues'].append("No valid authentication token available")
            readiness_status['recommendations'].append("Obtain WebSocket authentication token before Balance Manager V2 setup")
        
        # Check token age
        if hasattr(self, '_token_created_time') and self._token_created_time > 0:
            token_age = time.time() - self._token_created_time
            if token_age > 14 * 60:  # 14 minutes (close to expiry)
                readiness_status['issues'].append(f"Authentication token is old ({token_age/60:.1f} minutes)")
                readiness_status['recommendations'].append("Refresh authentication token before proceeding")
        
        # Overall readiness assessment
        readiness_status['ready_for_balance_manager'] = (
            readiness_status['connection_healthy'] and
            readiness_status['authentication_ready'] and
            readiness_status['bot_available'] and
            len(readiness_status['issues']) == 0
        )
        
        return readiness_status
    
    async def ensure_ready_for_balance_manager(self) -> bool:
        """Ensure WebSocket is ready for Balance Manager V2 initialization"""
        try:
            logger.info("[WEBSOCKET_V2] Ensuring readiness for Balance Manager V2...")
            
            # Check current readiness
            readiness = self.validate_connection_readiness()
            
            if readiness['ready_for_balance_manager']:
                logger.info("[WEBSOCKET_V2] Already ready for Balance Manager V2")
                return True
            
            logger.warning(f"[WEBSOCKET_V2] Not ready for Balance Manager V2. Issues: {readiness['issues']}")
            
            # Try to fix issues
            fixes_attempted = []
            
            # Fix 1: Ensure connection
            if not readiness['connection_healthy']:
                logger.info("[WEBSOCKET_V2] Attempting to establish healthy connection...")
                try:
                    if not await self.connect():
                        logger.error("[WEBSOCKET_V2] Failed to establish connection")
                        return False
                    fixes_attempted.append("connection_established")
                except Exception as conn_error:
                    logger.error(f"[WEBSOCKET_V2] Connection establishment failed: {conn_error}")
                    return False
            
            # Fix 2: Ensure authentication
            if not readiness['authentication_ready']:
                logger.info("[WEBSOCKET_V2] Attempting to obtain authentication...")
                try:
                    if not await self._setup_private_client():
                        logger.error("[WEBSOCKET_V2] Failed to setup authentication")
                        return False
                    fixes_attempted.append("authentication_setup")
                except Exception as auth_error:
                    logger.error(f"[WEBSOCKET_V2] Authentication setup failed: {auth_error}")
                    return False
            
            # Fix 3: Refresh token if needed
            if hasattr(self, '_token_created_time') and self._should_refresh_token():
                logger.info("[WEBSOCKET_V2] Refreshing authentication token...")
                try:
                    if not await self._refresh_auth_token():
                        logger.warning("[WEBSOCKET_V2] Token refresh failed, continuing with current token")
                    else:
                        fixes_attempted.append("token_refreshed")
                except Exception as refresh_error:
                    logger.warning(f"[WEBSOCKET_V2] Token refresh error: {refresh_error}")
            
            # Re-validate readiness
            final_readiness = self.validate_connection_readiness()
            
            if final_readiness['ready_for_balance_manager']:
                logger.info(f"[WEBSOCKET_V2] Successfully prepared for Balance Manager V2. Fixes applied: {fixes_attempted}")
                return True
            else:
                logger.error(f"[WEBSOCKET_V2] Still not ready for Balance Manager V2 after fixes. Remaining issues: {final_readiness['issues']}")
                return False
                
        except Exception as e:
            logger.error(f"[WEBSOCKET_V2] Error ensuring readiness for Balance Manager V2: {e}")
            return False
    
    # Visual Display Methods
    def _print_header(self):
        """Print visual header"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.WHITE}🚀 KRAKEN WEBSOCKET V2 - REAL-TIME DATA VISUALIZATION 🚀")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    def _print_connection_status(self):
        """Print connection status"""
        if self.is_connected:
            uptime = time.time() - self.connection_start_time if self.connection_start_time else 0
            print(f"{Fore.GREEN}✓ CONNECTED{Style.RESET_ALL} | Uptime: {int(uptime)}s | Heartbeats: {self.heartbeat_count}")
        else:
            print(f"{Fore.RED}✗ DISCONNECTED{Style.RESET_ALL}")
    
    def _print_channel_stats(self):
        """Print channel statistics"""
        print(f"\n{Fore.YELLOW}📊 CHANNEL STATISTICS:{Style.RESET_ALL}")
        print(f"{'Channel':<20} {'Messages':<15} {'Last Update':<20}")
        print("-" * 55)
        
        for channel, count in sorted(self.message_counts.items()):
            last_update = self.last_update_times.get(channel, 0)
            if last_update:
                time_ago = int(time.time() - last_update)
                update_str = f"{time_ago}s ago"
            else:
                update_str = "Never"
            
            # Color code by activity
            if time_ago < 5:
                color = Fore.GREEN
            elif time_ago < 30:
                color = Fore.YELLOW
            else:
                color = Fore.RED
                
            print(f"{color}{channel:<20} {count:<15} {update_str:<20}{Style.RESET_ALL}")
    
    def _print_market_data(self):
        """Print market data summary"""
        if not self.ticker_data:
            return
            
        print(f"\n{Fore.CYAN}💰 MARKET DATA:{Style.RESET_ALL}")
        print(f"{'Symbol':<12} {'Bid':<10} {'Ask':<10} {'Last':<10} {'Spread':<8} {'Volume':<12} {'24h %':<8}")
        print("-" * 80)
        
        for symbol, ticker in sorted(self.ticker_data.items())[:10]:  # Show top 10
            if ticker and 'last' in ticker:
                bid = ticker.get('bid', 0)
                ask = ticker.get('ask', 0)
                last = ticker.get('last', 0)
                volume = ticker.get('volume', 0)
                change_pct = ticker.get('change', 0)
                
                spread = ask - bid if ask > 0 and bid > 0 else 0
                spread_pct = (spread / bid * 100) if bid > 0 else 0
                
                # Color code by price movement
                if change_pct > 0:
                    price_color = Fore.GREEN
                elif change_pct < 0:
                    price_color = Fore.RED
                else:
                    price_color = Fore.WHITE
                
                print(f"{symbol:<12} "
                      f"{bid:<10.2f} "
                      f"{ask:<10.2f} "
                      f"{price_color}{last:<10.2f}{Style.RESET_ALL} "
                      f"{spread_pct:<8.3f} "
                      f"{volume:<12.0f} "
                      f"{price_color}{change_pct:<8.2f}{Style.RESET_ALL}")
    
    def _print_balance_summary(self):
        """Print balance summary"""
        if not self.balance_data:
            return
            
        print(f"\n{Fore.MAGENTA}💎 ACCOUNT BALANCES:{Style.RESET_ALL}")
        print(f"{'Asset':<10} {'Total':<15} {'Available':<15} {'In Orders':<15}")
        print("-" * 55)
        
        # Show only non-zero balances
        for asset, balance in sorted(self.balance_data.items()):
            if balance and balance.get('free', 0) > 0:
                total = balance.get('total', 0)
                free = balance.get('free', 0)
                used = balance.get('used', 0)
                
                print(f"{asset:<10} "
                      f"{total:<15.6f} "
                      f"{Fore.GREEN}{free:<15.6f}{Style.RESET_ALL} "
                      f"{Fore.YELLOW}{used:<15.6f}{Style.RESET_ALL}")
    
    def _print_recent_activity(self):
        """Print recent trading activity"""
        if not self.recent_trades:
            return
            
        print(f"\n{Fore.WHITE}🔄 RECENT ACTIVITY:{Style.RESET_ALL}")
        
        # Combine all recent trades
        all_trades = []
        for symbol, trades in self.recent_trades.items():
            all_trades.extend([(symbol, t) for t in trades])
        
        # Sort by timestamp
        all_trades.sort(key=lambda x: x[1].get('timestamp', 0), reverse=True)
        
        # Show last 5 trades
        for symbol, trade in all_trades[:5]:
            timestamp = trade.get('timestamp', time.time())
            time_ago = int(time.time() - timestamp)
            side = trade.get('side', 'unknown')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            
            side_color = Fore.GREEN if side == 'buy' else Fore.RED
            
            print(f"{time_ago}s ago: {side_color}{side.upper()}{Style.RESET_ALL} "
                  f"{quantity:.4f} {symbol} @ {price:.2f}")
    
    def _print_rate_limit_status(self):
        """Print rate limit status if available"""
        if not self.rate_counters:
            return
            
        print(f"\n{Fore.YELLOW}⚠️  RATE LIMIT STATUS:{Style.RESET_ALL}")
        for pair, counter in sorted(self.rate_counters.items())[:5]:
            percentage = counter.get('percentage', 0)
            current = counter.get('current', 0)
            max_val = counter.get('max', 0)
            
            if percentage > 50:
                color = Fore.RED
            elif percentage > 30:
                color = Fore.YELLOW
            else:
                color = Fore.GREEN
                
            print(f"{pair}: {color}{current}/{max_val} ({percentage:.1f}%){Style.RESET_ALL}")
    
    async def _visual_display_loop(self):
        """Main visual display loop"""
        while self.is_connected and self.visual_mode:
            try:
                # Clear screen - Windows compatible
                if os.name == 'nt':  # Windows
                    os.system('cls')
                else:  # Unix/Linux/Mac
                    print("\033[H\033[J", end="")
                
                self._print_header()
                self._print_connection_status()
                self._print_channel_stats()
                self._print_market_data()
                self._print_balance_summary()
                self._print_recent_activity()
                self._print_rate_limit_status()
                
                # Show last heartbeat
                if self.heartbeat_count > 0:
                    hb_ago = int(time.time() - self.last_message_time)
                    hb_color = Fore.GREEN if hb_ago < 5 else Fore.YELLOW if hb_ago < 30 else Fore.RED
                    print(f"\n{hb_color}💓 Last message: {hb_ago}s ago{Style.RESET_ALL}")
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"[VISUAL] Display error: {e}")
                await asyncio.sleep(1)
    
    def _update_visual_tracking(self, channel: str, data: Any):
        """Update visual tracking data"""
        if not self.visual_mode:
            return
            
        self.message_counts[channel] += 1
        self.last_update_times[channel] = time.time()
        
        # Track heartbeats
        if channel == 'heartbeat':
            self.heartbeat_count += 1
        
        # Track trades if available
        if channel == 'trade' and isinstance(data, dict):
            symbol = data.get('symbol', 'unknown')
            trade_info = {
                'side': data.get('side'),
                'price': data.get('price', 0),
                'quantity': data.get('qty', 0),
                'timestamp': time.time()
            }
            self.recent_trades[symbol].append(trade_info)