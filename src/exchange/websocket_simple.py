"""
Direct Kraken WebSocket V2 Implementation
=========================================

Direct WebSocket V2 connection to Kraken when python-kraken-sdk is not available.
Implements native WebSocket connection with proper message handling.
"""

import asyncio
import json
import logging
import time
import websockets
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger(__name__)


class SimpleKrakenWebSocket:
    """
    Direct Kraken WebSocket V2 implementation
    """
    
    def __init__(self, symbols: List[str], ticker_callback: Callable = None, 
                 ohlc_callback: Callable = None, config: Dict = None, rest_client=None):
        """Initialize direct WebSocket V2 connection"""
        self.symbols = symbols
        self.ticker_callback = ticker_callback
        self.ohlc_callback = ohlc_callback
        self.config = config or {}
        self.rest_client = rest_client
        
        # WebSocket connection
        self.websocket = None
        self.ws_url = "wss://ws.kraken.com/v2"
        
        # State
        self.is_connected = False
        self.is_healthy = True
        self.last_message_time = time.time()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Data storage
        self.current_tickers = {}
        self.last_price_update = {}
        self.ticker_data = {}
        
        # Message tracking
        self.req_id = 1
        
        logger.info(f"[DIRECT_WS] Initialized with {len(symbols)} symbols")
    
    def _convert_symbol_to_kraken(self, symbol: str) -> str:
        """Convert symbol format for Kraken WebSocket"""
        # BTC/USDT -> BTC/USDT (Kraken uses same format)
        return symbol.upper()
    
    def _convert_symbol_from_kraken(self, symbol: str) -> str:
        """Convert symbol back from Kraken format"""
        return symbol.replace('/', '_')
    
    async def connect(self) -> bool:
        """Connect to Kraken WebSocket V2"""
        try:
            logger.info("[DIRECT_WS] Connecting to Kraken WebSocket V2...")
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            self.is_healthy = True
            self.reconnect_attempts = 0
            
            logger.info("[DIRECT_WS] Connected successfully")
            
            # Subscribe to channels
            await self._subscribe_to_channels()
            
            return True
            
        except Exception as e:
            logger.error(f"[DIRECT_WS] Connection failed: {e}")
            self.is_connected = False
            return False
    
    async def _subscribe_to_channels(self):
        """Subscribe to ticker and OHLC channels"""
        try:
            # Debug log symbols input
            logger.info(f"[DIRECT_WS] Input symbols type: {type(self.symbols)}, value: {self.symbols}")
            
            # Ensure symbols is a list
            if isinstance(self.symbols, str):
                logger.warning(f"[DIRECT_WS] Symbols is string, converting to list: {self.symbols}")
                symbols_list = [self.symbols] if self.symbols else []
            else:
                symbols_list = list(self.symbols) if self.symbols else []
            
            # Subscribe to ticker for all symbols
            kraken_symbols = [self._convert_symbol_to_kraken(symbol) for symbol in symbols_list]
            
            ticker_msg = {
                "method": "subscribe",
                "params": {
                    "channel": "ticker",
                    "symbol": kraken_symbols
                },
                "req_id": self.req_id
            }
            
            logger.info(f"[DIRECT_WS] Kraken symbols for ticker: {kraken_symbols}")
            await self.websocket.send(json.dumps(ticker_msg))
            self.req_id += 1
            logger.info(f"[DIRECT_WS] Subscribed to ticker for {len(kraken_symbols)} symbols")
            
            # Subscribe to OHLC (1 minute)
            ohlc_msg = {
                "method": "subscribe", 
                "params": {
                    "channel": "ohlc",
                    "symbol": kraken_symbols,
                    "interval": 1
                },
                "req_id": self.req_id
            }
            
            logger.info(f"[DIRECT_WS] Kraken symbols for OHLC: {kraken_symbols}")
            await self.websocket.send(json.dumps(ohlc_msg))
            self.req_id += 1
            logger.info(f"[DIRECT_WS] Subscribed to OHLC for {len(kraken_symbols)} symbols")
            
        except Exception as e:
            logger.error(f"[DIRECT_WS] Subscription failed: {e}")
    
    async def subscribe_to_channels(self):
        """Public method for subscription (already done in connect)"""
        logger.info("[DIRECT_WS] Channels already subscribed")
        return True
    
    async def run(self):
        """Main message processing loop"""
        logger.info("[DIRECT_WS] Starting message processing loop...")
        
        while self.is_connected:
            try:
                if not self.websocket:
                    await asyncio.sleep(1)
                    continue
                
                # Wait for message with timeout
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=30.0
                    )
                    
                    await self._handle_message(message)
                    self.last_message_time = time.time()
                    
                except asyncio.TimeoutError:
                    logger.warning("[DIRECT_WS] No message received in 30s")
                    # Send ping to check connection
                    await self.websocket.ping()
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("[DIRECT_WS] Connection closed, attempting reconnect...")
                await self._reconnect()
                
            except Exception as e:
                logger.error(f"[DIRECT_WS] Error in message loop: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if data.get("channel") == "ticker":
                await self._handle_ticker_message(data)
            elif data.get("channel") == "ohlc":
                await self._handle_ohlc_message(data)
            elif data.get("method") == "subscribe":
                # Subscription confirmation
                success = data.get("success", False)
                result = data.get("result", {})
                channel_name = result.get("channel")
                if success:
                    logger.info(f"[DIRECT_WS] Subscription confirmed: {channel_name}")
                else:
                    logger.error(f"[DIRECT_WS] Subscription failed: {data}")
            
        except json.JSONDecodeError as e:
            logger.error(f"[DIRECT_WS] Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"[DIRECT_WS] Message handling error: {e}")
            logger.debug(f"[DIRECT_WS] Failed message: {message}")
    
    async def _handle_ticker_message(self, data: Dict[str, Any]):
        """Handle ticker update"""
        try:
            # V2 format: data contains array of ticker objects
            ticker_data = data.get("data", [])
            
            for ticker in ticker_data:
                symbol = ticker.get("symbol", "")
                if not symbol:
                    continue
                    
                # Convert symbol format
                standard_symbol = self._convert_symbol_from_kraken(symbol)
                
                # Extract ticker information (V2 format)
                ticker_info = {
                    'bid': float(ticker.get('bid', 0)),
                    'ask': float(ticker.get('ask', 0)),
                    'last': float(ticker.get('last', 0)),
                    'volume': float(ticker.get('volume', 0)),
                    'high': float(ticker.get('high', 0)),
                    'low': float(ticker.get('low', 0)),
                    'vwap': float(ticker.get('vwap', 0)),
                    'timestamp': time.time()
                }
                
                # Store data in multiple formats
                self.current_tickers[symbol] = ticker_info
                self.ticker_data[standard_symbol] = ticker_info
                self.ticker_data[symbol] = ticker_info  # Also store with original symbol
                
                self.last_price_update[symbol] = {
                    'price': ticker_info['last'],
                    'timestamp': time.time()
                }
                
                # Log successful update
                if ticker_info['last'] > 0:
                    logger.debug(f"[DIRECT_WS] Ticker update for {symbol}: ${ticker_info['last']:.8f}")
                
                # Call registered callback
                if self.ticker_callback:
                    await self.ticker_callback(symbol, ticker_info)
                    
        except Exception as e:
            logger.error(f"[DIRECT_WS] Ticker handling error: {e}")
            logger.debug(f"[DIRECT_WS] Failed ticker data: {data}")
    
    async def _handle_ohlc_message(self, data: Dict[str, Any]):
        """Handle OHLC update"""
        try:
            # V2 format: data contains array of OHLC objects
            ohlc_data = data.get("data", [])
            
            for ohlc in ohlc_data:
                symbol = ohlc.get("symbol", "")
                if not symbol:
                    continue
                    
                # Handle timestamp - it comes as ISO string in V2
                timestamp_str = ohlc.get('timestamp', '')
                if timestamp_str and isinstance(timestamp_str, str):
                    # Convert ISO timestamp to Unix timestamp
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamp = dt.timestamp()
                    except:
                        timestamp = time.time()
                else:
                    timestamp = float(ohlc.get('timestamp', time.time()))
                
                ohlc_info = {
                    'timestamp': timestamp,
                    'open': float(ohlc.get('open', 0)),
                    'high': float(ohlc.get('high', 0)),
                    'low': float(ohlc.get('low', 0)),
                    'close': float(ohlc.get('close', 0)),
                    'volume': float(ohlc.get('volume', 0))
                }
                
                # Log successful update
                logger.debug(f"[DIRECT_WS] OHLC update for {symbol}")
                
                # Call registered callback
                if self.ohlc_callback:
                    await self.ohlc_callback(symbol, ohlc_info)
                    
        except Exception as e:
            logger.error(f"[DIRECT_WS] OHLC handling error: {e}")
            logger.debug(f"[DIRECT_WS] Failed OHLC data: {data}")
    
    async def _reconnect(self):
        """Reconnect to WebSocket"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("[DIRECT_WS] Max reconnect attempts reached")
            self.is_connected = False
            return
            
        self.reconnect_attempts += 1
        wait_time = min(2 ** self.reconnect_attempts, 30)
        
        logger.info(f"[DIRECT_WS] Reconnecting in {wait_time}s (attempt {self.reconnect_attempts})")
        await asyncio.sleep(wait_time)
        
        await self.disconnect()
        await self.connect()
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            self.is_connected = False
            logger.info("[DIRECT_WS] Disconnected")
            
        except Exception as e:
            logger.error(f"[DIRECT_WS] Disconnect error: {e}")
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data for symbol"""
        # Try original symbol first
        ticker = self.current_tickers.get(symbol) or self.ticker_data.get(symbol)
        if ticker and ticker.get('last', 0) > 0:
            return ticker
        
        # Try converted format
        standard_symbol = self._convert_symbol_from_kraken(symbol)
        ticker = self.ticker_data.get(standard_symbol)
        if ticker and ticker.get('last', 0) > 0:
            return ticker
            
        # Debug log if no data found
        if not ticker:
            available = [s for s in self.ticker_data.keys() if self.ticker_data[s].get('last', 0) > 0]
            if available:
                logger.debug(f"[DIRECT_WS] No data for {symbol}. Available: {available[:5]}...")
            
        return None
    
    def has_fresh_data(self, symbol: str, max_age: float = 5.0) -> bool:
        """Check if we have fresh data for symbol"""
        if symbol in self.last_price_update:
            age = time.time() - self.last_price_update[symbol].get('timestamp', 0)
            return age <= max_age
        return False
    
    async def check_data_freshness(self):
        """Check data freshness for all symbols"""
        current_time = time.time()
        stale_symbols = []
        
        for symbol in self.symbols:
            if symbol not in self.last_price_update:
                stale_symbols.append(symbol)
            else:
                age = current_time - self.last_price_update[symbol].get('timestamp', 0)
                if age > 30:  # 30 seconds
                    stale_symbols.append(symbol)
        
        if stale_symbols:
            logger.warning(f"[DIRECT_WS] Stale data for: {stale_symbols}")
    
    def set_circuit_breaker_callback(self, callback):
        """Set circuit breaker callback"""
        self.circuit_breaker_callback = callback