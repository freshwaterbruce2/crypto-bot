"""
Kraken WebSocket V2 Integration Example
=======================================

Example integration of the WebSocket V2 system with the existing trading bot.
Shows how to set up real-time balance streaming, market data, and event handling.
"""

import asyncio
import logging
from typing import List, Dict, Any

from .kraken_websocket_v2 import KrakenWebSocketV2, KrakenWebSocketConfig
from .data_models import BalanceUpdate, TickerUpdate, OrderBookUpdate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketIntegrationExample:
    """Example integration class showing WebSocket V2 usage"""
    
    def __init__(self, api_key: str, api_secret: str):
        """Initialize with API credentials"""
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Create WebSocket client with custom config
        config = KrakenWebSocketConfig(
            ping_interval=20.0,
            heartbeat_timeout=60.0,
            message_queue_size=5000,
            subscription_rate_limit=3  # Conservative rate limiting
        )
        
        self.ws_client = KrakenWebSocketV2(
            api_key=api_key,
            api_secret=api_secret,
            config=config
        )
        
        # Trading pairs to monitor
        self.trading_pairs = [
            'BTC/USDT', 'ETH/USDT', 'SHIB/USDT', 'MANA/USDT',
            'MATIC/USDT', 'AI16Z/USDT', 'ADA/USDT', 'DOT/USDT'
        ]
        
        # Data storage for processing
        self.current_balances: Dict[str, Dict[str, Any]] = {}
        self.current_tickers: Dict[str, Dict[str, Any]] = {}
        self.current_orderbooks: Dict[str, Dict[str, Any]] = {}
        
        # Integration with existing bot systems
        self.balance_manager = None  # Will be set from main bot
        self.trading_engine = None   # Will be set from main bot
        
        logger.info("[WS_INTEGRATION] Initialized WebSocket integration example")
    
    def set_balance_manager(self, balance_manager):
        """Set reference to existing balance manager for integration"""
        self.balance_manager = balance_manager
        logger.info("[WS_INTEGRATION] Balance manager reference set")
    
    def set_trading_engine(self, trading_engine):
        """Set reference to existing trading engine for integration"""
        self.trading_engine = trading_engine
        logger.info("[WS_INTEGRATION] Trading engine reference set")
    
    async def start(self):
        """Start WebSocket integration"""
        logger.info("[WS_INTEGRATION] Starting WebSocket V2 integration")
        
        try:
            # Set up event callbacks
            self._setup_callbacks()
            
            # Connect to WebSocket
            success = await self.ws_client.connect(private_channels=True)
            if not success:
                logger.error("[WS_INTEGRATION] Failed to connect to WebSocket")
                return False
            
            # Set up subscriptions
            await self._setup_subscriptions()
            
            logger.info("[WS_INTEGRATION] WebSocket V2 integration started successfully")
            return True
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error starting WebSocket integration: {e}")
            return False
    
    async def stop(self):
        """Stop WebSocket integration"""
        logger.info("[WS_INTEGRATION] Stopping WebSocket V2 integration")
        await self.ws_client.disconnect()
        logger.info("[WS_INTEGRATION] WebSocket V2 integration stopped")
    
    def _setup_callbacks(self):
        """Set up WebSocket event callbacks"""
        
        # Balance update callback
        self.ws_client.register_callback('balance', self._handle_balance_updates)
        
        # Market data callbacks
        self.ws_client.register_callback('ticker', self._handle_ticker_updates)
        self.ws_client.register_callback('orderbook', self._handle_orderbook_updates)
        self.ws_client.register_callback('trade', self._handle_trade_updates)
        
        # Connection event callbacks
        self.ws_client.register_callback('connected', self._handle_connected)
        self.ws_client.register_callback('disconnected', self._handle_disconnected)
        self.ws_client.register_callback('authenticated', self._handle_authenticated)
        self.ws_client.register_callback('error', self._handle_error)
        
        logger.info("[WS_INTEGRATION] Event callbacks registered")
    
    async def _setup_subscriptions(self):
        """Set up WebSocket subscriptions"""
        try:
            # Subscribe to balance updates (private channel)
            if self.ws_client.is_authenticated():
                balance_success = await self.ws_client.subscribe_balance()
                if balance_success:
                    logger.info("[WS_INTEGRATION] Subscribed to balance updates")
                else:
                    logger.warning("[WS_INTEGRATION] Failed to subscribe to balance updates")
            
            # Subscribe to ticker updates for trading pairs
            ticker_success = await self.ws_client.subscribe_ticker(self.trading_pairs)
            if ticker_success:
                logger.info(f"[WS_INTEGRATION] Subscribed to ticker updates for {len(self.trading_pairs)} pairs")
            
            # Subscribe to orderbook updates (depth 10 for fast processing)
            orderbook_success = await self.ws_client.subscribe_orderbook(self.trading_pairs, depth=10)
            if orderbook_success:
                logger.info(f"[WS_INTEGRATION] Subscribed to orderbook updates for {len(self.trading_pairs)} pairs")
            
            # Subscribe to OHLC data (1-minute candles)
            ohlc_success = await self.ws_client.subscribe_ohlc(self.trading_pairs, interval=1)
            if ohlc_success:
                logger.info(f"[WS_INTEGRATION] Subscribed to OHLC updates for {len(self.trading_pairs)} pairs")
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error setting up subscriptions: {e}")
    
    # Event Handlers
    
    async def _handle_balance_updates(self, balance_updates: List[BalanceUpdate]):
        """Handle real-time balance updates"""
        try:
            logger.info(f"[WS_INTEGRATION] Received {len(balance_updates)} balance updates")
            
            for balance_update in balance_updates:
                asset = balance_update.asset
                balance_dict = balance_update.to_dict()
                
                # Store current balance
                self.current_balances[asset] = balance_dict
                
                # Log significant balance changes
                if balance_update.free_balance > 0 and asset in ['USDT', 'BTC', 'ETH', 'SHIB', 'MANA']:
                    logger.info(f"[WS_INTEGRATION] {asset} balance: {balance_update.free_balance:.8f}")
                
                # Integrate with existing balance manager
                if self.balance_manager:
                    await self._integrate_balance_update(asset, balance_dict)
            
            # Trigger balance-dependent actions
            await self._handle_balance_change()
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error handling balance updates: {e}")
    
    async def _handle_ticker_updates(self, ticker_updates: List[TickerUpdate]):
        """Handle real-time ticker updates"""
        try:
            for ticker_update in ticker_updates:
                symbol = ticker_update.symbol
                ticker_dict = ticker_update.to_dict()
                
                # Store current ticker
                self.current_tickers[symbol] = ticker_dict
                
                # Log price changes for monitored pairs
                if symbol in self.trading_pairs:
                    logger.debug(f"[WS_INTEGRATION] {symbol} ticker: ${ticker_update.last:.8f} (spread: {ticker_update.spread_percentage:.4f}%)")
                
                # Integrate with trading engine for price-based decisions
                if self.trading_engine:
                    await self._integrate_ticker_update(symbol, ticker_dict)
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error handling ticker updates: {e}")
    
    async def _handle_orderbook_updates(self, orderbook_updates: List[OrderBookUpdate]):
        """Handle real-time orderbook updates"""
        try:
            for orderbook_update in orderbook_updates:
                symbol = orderbook_update.symbol
                orderbook_dict = orderbook_update.to_dict()
                
                # Store current orderbook
                self.current_orderbooks[symbol] = orderbook_dict
                
                # Log orderbook changes for high-value pairs
                if symbol in ['BTC/USDT', 'ETH/USDT'] and orderbook_update.best_bid and orderbook_update.best_ask:
                    spread = orderbook_update.spread
                    logger.debug(f"[WS_INTEGRATION] {symbol} orderbook: spread={spread:.8f}")
                
                # Use orderbook data for optimal order placement
                if self.trading_engine:
                    await self._integrate_orderbook_update(symbol, orderbook_dict)
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error handling orderbook updates: {e}")
    
    async def _handle_trade_updates(self, trade_updates):
        """Handle real-time trade updates"""
        try:
            for trade_update in trade_updates:
                logger.debug(f"[WS_INTEGRATION] Trade: {trade_update.symbol} {trade_update.side} {trade_update.volume} @ ${trade_update.price}")
                
                # Use trade data for market analysis
                if self.trading_engine:
                    await self._integrate_trade_update(trade_update)
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error handling trade updates: {e}")
    
    # Connection Event Handlers
    
    async def _handle_connected(self):
        """Handle WebSocket connection established"""
        logger.info("[WS_INTEGRATION] WebSocket connected successfully")
        
        # Resume trading operations if they were paused
        if self.trading_engine and hasattr(self.trading_engine, 'resume_trading'):
            await self.trading_engine.resume_trading()
    
    async def _handle_disconnected(self):
        """Handle WebSocket disconnection"""
        logger.warning("[WS_INTEGRATION] WebSocket disconnected")
        
        # Pause trading operations until reconnection
        if self.trading_engine and hasattr(self.trading_engine, 'pause_trading'):
            await self.trading_engine.pause_trading()
    
    async def _handle_authenticated(self):
        """Handle successful authentication"""
        logger.info("[WS_INTEGRATION] WebSocket authenticated successfully")
        
        # Set up private channel subscriptions
        await self.ws_client.subscribe_balance()
    
    async def _handle_error(self, error: Exception):
        """Handle WebSocket errors"""
        logger.error(f"[WS_INTEGRATION] WebSocket error: {error}")
        
        # Implement error recovery logic
        await self._handle_websocket_error(error)
    
    # Integration Methods
    
    async def _integrate_balance_update(self, asset: str, balance_dict: Dict[str, Any]):
        """Integrate balance update with existing balance manager"""
        try:
            if hasattr(self.balance_manager, 'balances'):
                # Direct injection to balance manager
                self.balance_manager.balances[asset] = balance_dict
                
                # Reset circuit breaker if active
                if hasattr(self.balance_manager, 'circuit_breaker_active') and self.balance_manager.circuit_breaker_active:
                    logger.info(f"[WS_INTEGRATION] Resetting circuit breaker due to fresh {asset} balance data")
                    self.balance_manager.circuit_breaker_active = False
                    self.balance_manager.consecutive_failures = 0
                
                # Update timestamp
                self.balance_manager.last_update = asyncio.get_event_loop().time()
                
                logger.debug(f"[WS_INTEGRATION] Integrated {asset} balance into balance manager")
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error integrating balance update: {e}")
    
    async def _integrate_ticker_update(self, symbol: str, ticker_dict: Dict[str, Any]):
        """Integrate ticker update with trading engine"""
        try:
            if hasattr(self.trading_engine, 'update_market_data'):
                await self.trading_engine.update_market_data(symbol, 'ticker', ticker_dict)
            
            # Check for trading opportunities based on price movement
            if hasattr(self.trading_engine, 'check_trading_opportunity'):
                await self.trading_engine.check_trading_opportunity(symbol, ticker_dict)
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error integrating ticker update: {e}")
    
    async def _integrate_orderbook_update(self, symbol: str, orderbook_dict: Dict[str, Any]):
        """Integrate orderbook update with trading engine"""
        try:
            if hasattr(self.trading_engine, 'update_market_data'):
                await self.trading_engine.update_market_data(symbol, 'orderbook', orderbook_dict)
            
            # Use orderbook for optimal order placement
            if hasattr(self.trading_engine, 'update_order_placement_data'):
                await self.trading_engine.update_order_placement_data(symbol, orderbook_dict)
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error integrating orderbook update: {e}")
    
    async def _integrate_trade_update(self, trade_update):
        """Integrate trade update with trading engine"""
        try:
            trade_dict = trade_update.to_dict()
            
            if hasattr(self.trading_engine, 'process_trade_data'):
                await self.trading_engine.process_trade_data(trade_update.symbol, trade_dict)
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error integrating trade update: {e}")
    
    # Action Handlers
    
    async def _handle_balance_change(self):
        """Handle significant balance changes"""
        try:
            # Check for USDT balance changes that might affect trading
            usdt_balance = self.current_balances.get('USDT', {})
            if usdt_balance:
                free_usdt = usdt_balance.get('free', 0)
                
                # Resume trading if USDT becomes available
                if free_usdt > 5.0 and self.trading_engine:
                    if hasattr(self.trading_engine, 'resume_trading'):
                        await self.trading_engine.resume_trading()
                        logger.info(f"[WS_INTEGRATION] Resumed trading with {free_usdt:.2f} USDT available")
            
            # Check for asset balances that might need selling
            for asset, balance_dict in self.current_balances.items():
                if asset != 'USDT' and balance_dict.get('free', 0) > 0:
                    # Notify trading engine of sellable balance
                    if self.trading_engine and hasattr(self.trading_engine, 'notify_sellable_balance'):
                        await self.trading_engine.notify_sellable_balance(asset, balance_dict)
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error handling balance change: {e}")
    
    async def _handle_websocket_error(self, error: Exception):
        """Handle WebSocket errors with recovery logic"""
        try:
            error_str = str(error).lower()
            
            # Handle authentication errors
            if 'authentication' in error_str or 'unauthorized' in error_str:
                logger.error("[WS_INTEGRATION] Authentication error - may need to refresh token")
                # Token refresh is handled automatically by the WebSocket client
            
            # Handle connection errors
            elif 'connection' in error_str or 'network' in error_str:
                logger.warning("[WS_INTEGRATION] Connection error - reconnection will be attempted")
                # Reconnection is handled automatically by the connection manager
            
            # Handle rate limiting errors
            elif 'rate limit' in error_str or 'too many' in error_str:
                logger.warning("[WS_INTEGRATION] Rate limit error - reducing subscription rate")
                # Implement backoff strategy
                await asyncio.sleep(5)
            
            else:
                logger.error(f"[WS_INTEGRATION] Unhandled WebSocket error: {error}")
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error in error handler: {e}")
    
    # Public API Methods
    
    def get_current_balance(self, asset: str) -> Dict[str, Any]:
        """Get current balance for asset from WebSocket data"""
        return self.current_balances.get(asset, {})
    
    def get_current_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker for symbol from WebSocket data"""
        return self.current_tickers.get(symbol, {})
    
    def get_current_orderbook(self, symbol: str) -> Dict[str, Any]:
        """Get current orderbook for symbol from WebSocket data"""
        return self.current_orderbooks.get(symbol, {})
    
    def is_websocket_healthy(self) -> bool:
        """Check if WebSocket connection is healthy"""
        return self.ws_client.is_connected() and self.ws_client.is_authenticated()
    
    def get_websocket_status(self) -> Dict[str, Any]:
        """Get detailed WebSocket status"""
        return self.ws_client.get_connection_status()
    
    async def refresh_subscriptions(self):
        """Refresh all subscriptions (useful after reconnection)"""
        try:
            logger.info("[WS_INTEGRATION] Refreshing WebSocket subscriptions")
            await self._setup_subscriptions()
            logger.info("[WS_INTEGRATION] WebSocket subscriptions refreshed")
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error refreshing subscriptions: {e}")


# Usage Example
async def main():
    """Example usage of WebSocket V2 integration"""
    
    # Initialize with API credentials
    ws_integration = WebSocketIntegrationExample(
        api_key="your_api_key_here",
        api_secret="your_api_secret_here"
    )
    
    try:
        # Start WebSocket integration
        success = await ws_integration.start()
        if not success:
            logger.error("Failed to start WebSocket integration")
            return
        
        # Run for demonstration
        logger.info("WebSocket integration running... (Press Ctrl+C to stop)")
        
        # Monitor for 60 seconds
        for i in range(60):
            await asyncio.sleep(1)
            
            # Print status every 10 seconds
            if i % 10 == 0:
                status = ws_integration.get_websocket_status()
                logger.info(f"WebSocket status: Connected={status.get('is_running', False)}, "
                           f"Balances={status.get('data_counts', {}).get('balances', 0)}, "
                           f"Tickers={status.get('data_counts', {}).get('tickers', 0)}")
        
    except KeyboardInterrupt:
        logger.info("Stopping WebSocket integration...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Stop WebSocket integration
        await ws_integration.stop()
        logger.info("WebSocket integration stopped")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())