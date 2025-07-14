# COMPLETE TRADING BOT FIXES - KRAKEN COMPLIANT

Execute all fixes in order. This bot trades USDT pairs only on Kraken.

## 1. FIX WEBSOCKET CALLBACK MISMATCH

File: src/bot.py
Find methods _handle_ticker_data and _handle_ohlc_data
Replace with:

```python
async def _handle_ticker_data(self, msg):
    """Handle ticker updates from WebSocket v2"""
    try:
        # Extract symbol and data from WebSocket v2 message
        if isinstance(msg, dict) and 'data' in msg:
            ticker_data = msg['data'][0] if msg['data'] else {}
            symbol = ticker_data.get('symbol', '')
            
            if symbol and symbol.endswith('/USDT'):
                price = ticker_data.get('last', 0)
                volume = ticker_data.get('volume', 0)
                
                # Update price tracking
                self.latest_prices[symbol] = {
                    'price': price,
                    'volume': volume,
                    'timestamp': time.time()
                }
                
                # Notify strategies
                for strategy in self.strategies.values():
                    if hasattr(strategy, 'on_price_update'):
                        await strategy.on_price_update(symbol, price)
                        
    except Exception as e:
        logger.error(f"[TICKER] Error handling ticker data: {e}")

async def _handle_ohlc_data(self, msg):
    """Handle OHLC updates from WebSocket v2"""
    try:
        if isinstance(msg, dict) and 'data' in msg:
            for candle in msg.get('data', []):
                symbol = candle.get('symbol', '')
                if symbol and symbol.endswith('/USDT'):
                    # Store OHLC data
                    if symbol not in self.ohlc_data:
                        self.ohlc_data[symbol] = []
                    
                    self.ohlc_data[symbol].append({
                        'time': candle.get('interval_begin'),
                        'open': candle.get('open'),
                        'high': candle.get('high'),
                        'low': candle.get('low'),
                        'close': candle.get('close'),
                        'volume': candle.get('volume')
                    })
                    
                    # Keep only last 100 candles
                    self.ohlc_data[symbol] = self.ohlc_data[symbol][-100:]
                    
    except Exception as e:
        logger.error(f"[OHLC] Error handling OHLC data: {e}")
```

## 2. FIX INITIALIZATION RACE CONDITION

File: src/bot.py
Replace start() method with proper sequencing:

```python
async def start(self):
    """Start bot with proper initialization sequence"""
    try:
        logger.info("[STARTUP] Starting Kraken USDT trading bot...")
        
        # Phase 1: Core initialization
        logger.info("[STARTUP] Phase 1: Initializing core components...")
        await self._initialize_core_components()
        
        # Phase 2: Verify executor ready
        logger.info("[STARTUP] Phase 2: Waiting for trade executor...")
        if hasattr(self.components, 'trade_executor') and self.components.trade_executor:
            if hasattr(self.components.trade_executor, 'wait_until_ready'):
                await self.components.trade_executor.wait_until_ready()
            else:
                # Simple wait if method not available
                await asyncio.sleep(2)
        
        # Phase 3: Load market data
        logger.info("[STARTUP] Phase 3: Loading market data...")
        await self._load_initial_market_data()
        
        # Phase 4: Initialize strategies AFTER executor ready
        logger.info("[STARTUP] Phase 4: Initializing strategies...")
        await self._initialize_strategies()
        
        # Phase 5: Start main loop
        logger.info("[STARTUP] All components ready. Starting main loop...")
        self.running = True
        
    except Exception as e:
        logger.error(f"[STARTUP] Failed to start: {e}")
        raise

async def _initialize_core_components(self):
    """Initialize core components in correct order"""
    # 1. Balance manager first
    if hasattr(self.components, 'balance_manager'):
        await self.components.balance_manager.initialize()
        
    # 2. Risk manager
    if hasattr(self.components, 'risk_manager'):
        await self.components.risk_manager.initialize()
        
    # 3. Trade executor (depends on above)
    if hasattr(self.components, 'trade_executor'):
        await self.components.trade_executor.initialize()
        
    # 4. WebSocket manager
    if hasattr(self.components, 'websocket_manager'):
        await self.components.websocket_manager.connect()

async def _load_initial_market_data(self):
    """Load initial market data from REST API"""
    try:
        # Get active USDT pairs from Kraken
        pairs = await self._fetch_active_usdt_pairs()
        self.config['trading_pairs'] = pairs
        
        # Get initial prices
        for pair in pairs:
            ticker = await self.exchange.fetch_ticker(pair)
            if ticker:
                self.latest_prices[pair] = {
                    'price': ticker.get('last', 0),
                    'volume': ticker.get('quoteVolume', 0),
                    'timestamp': time.time()
                }
    except Exception as e:
        logger.error(f"[MARKET_DATA] Error loading initial data: {e}")
```

## 3. FIX SIGNAL EXECUTION PIPELINE

File: src/bot.py
Update run_once() method to properly route signals:

```python
async def run_once(self):
    """Main loop iteration with proper signal execution"""
    try:
        # Collect signals from all sources
        all_signals = []
        
        # 1. Get signals from opportunity scanner
        if hasattr(self, 'opportunity_scanner') and self.opportunity_scanner:
            opportunities = await self.opportunity_scanner.scan_opportunities()
            for opp in opportunities:
                if opp.get('symbol', '').endswith('/USDT'):
                    all_signals.append({
                        'symbol': opp['symbol'],
                        'side': opp.get('action', 'buy'),
                        'confidence': opp.get('confidence', 0.5),
                        'strategy': 'opportunity_scanner',
                        'price': opp.get('entry_price'),
                        'amount_usdt': 10.0  # Fixed 10 USDT per trade
                    })
        
        # 2. Get signals from strategy manager
        if hasattr(self, 'strategy_manager') and self.strategy_manager:
            strategy_signals = await self.strategy_manager.get_signals()
            for sig in strategy_signals:
                if sig.get('symbol', '').endswith('/USDT'):
                    all_signals.append({
                        'symbol': sig['symbol'],
                        'side': sig.get('side', 'buy'),
                        'confidence': sig.get('confidence', 0.5),
                        'strategy': sig.get('strategy_name', 'unknown'),
                        'price': self.latest_prices.get(sig['symbol'], {}).get('price', 0),
                        'amount_usdt': 10.0
                    })
        
        # 3. Execute signals through trade executor
        if all_signals and hasattr(self.components, 'trade_executor'):
            # Sort by confidence
            all_signals.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Execute top signals (respecting rate limits)
            max_trades_per_cycle = 3
            for signal in all_signals[:max_trades_per_cycle]:
                if signal['confidence'] > 0.7:  # Min confidence threshold
                    await self._execute_signal(signal)
                    await asyncio.sleep(0.5)  # Rate limit protection
                    
    except Exception as e:
        logger.error(f"[RUN_ONCE] Error in main loop: {e}")

async def _execute_signal(self, signal):
    """Execute a trading signal"""
    try:
        symbol = signal['symbol']
        side = signal['side']
        amount_usdt = signal['amount_usdt']
        
        # Validate minimum order size (Kraken: $5 USDT minimum)
        if amount_usdt < 5.0:
            amount_usdt = 5.0
            
        # Check USDT balance
        balance = await self.components.balance_manager.get_available_balance('USDT')
        if balance < amount_usdt:
            logger.warning(f"[EXECUTE] Insufficient USDT: {balance} < {amount_usdt}")
            return
            
        # Execute through trade executor
        result = await self.components.trade_executor.execute_trade(
            symbol=symbol,
            side=side,
            amount=amount_usdt,
            signal=signal
        )
        
        if result and result.get('success'):
            logger.info(f"[EXECUTE] Trade successful: {side} {amount_usdt} USDT of {symbol}")
        else:
            logger.warning(f"[EXECUTE] Trade failed: {result}")
            
    except Exception as e:
        logger.error(f"[EXECUTE] Error executing signal: {e}")
```

## 4. UPDATE WEBSOCKET MANAGER FOR KRAKEN V2

File: src/websocket_manager.py
Replace WebSocket URLs and message handling:

```python
class WebSocketManager:
    def __init__(self, config):
        self.config = config
        self.public_url = "wss://ws.kraken.com/v2"
        self.private_url = "wss://ws-auth.kraken.com/v2"
        self.callbacks = {}
        self.subscriptions = set()
        self.token = None
        
    async def connect(self):
        """Connect to Kraken WebSocket v2"""
        try:
            # Get auth token for private channels
            self.token = await self._get_websocket_token()
            
            # Connect to public WebSocket
            self.ws = await websockets.connect(self.public_url)
            
            # Start message handler
            asyncio.create_task(self._handle_messages())
            
            # Subscribe to USDT pairs
            await self._subscribe_to_channels()
            
        except Exception as e:
            logger.error(f"[WS] Connection error: {e}")
            
    async def _get_websocket_token(self):
        """Get WebSocket token from REST API"""
        try:
            # This would call Kraken REST API GetWebSocketsToken
            # For now, return placeholder
            return "token_placeholder"
        except Exception as e:
            logger.error(f"[WS] Token error: {e}")
            return None
            
    async def _subscribe_to_channels(self):
        """Subscribe to ticker and OHLC for USDT pairs"""
        pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "MATIC/USDT"]
        
        # Subscribe to ticker
        ticker_msg = {
            "method": "subscribe",
            "params": {
                "channel": "ticker",
                "symbol": pairs,
                "snapshot": True
            }
        }
        await self.ws.send(json.dumps(ticker_msg))
        
        # Subscribe to OHLC
        ohlc_msg = {
            "method": "subscribe", 
            "params": {
                "channel": "ohlc",
                "symbol": pairs,
                "interval": 5,  # 5 minute candles
                "snapshot": True
            }
        }
        await self.ws.send(json.dumps(ohlc_msg))
        
    async def _handle_messages(self):
        """Handle incoming WebSocket messages"""
        async for message in self.ws:
            try:
                msg = json.loads(message)
                
                # Route to appropriate callback
                if msg.get('channel') == 'ticker' and 'ticker' in self.callbacks:
                    await self.callbacks['ticker'](msg)
                elif msg.get('channel') == 'ohlc' and 'ohlc' in self.callbacks:
                    await self.callbacks['ohlc'](msg)
                elif msg.get('channel') == 'status':
                    logger.info(f"[WS] Status: {msg}")
                    
            except Exception as e:
                logger.error(f"[WS] Message handling error: {e}")
```

## 5. IMPLEMENT SELF-LEARNING/DIAGNOSING/REPAIRING

File: src/learning/self_diagnostic_system.py (NEW FILE)
```python
import asyncio
import time
import json
from typing import Dict, List, Any
from ..utils.custom_logging import logger

class SelfDiagnosticSystem:
    """Self-diagnosing, learning, and repairing system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.health_metrics = {
            'trades_executed': 0,
            'trades_successful': 0,
            'errors_encountered': 0,
            'last_profit': 0.0,
            'uptime_start': time.time(),
            'component_status': {}
        }
        self.error_patterns = {}
        self.repair_strategies = {
            'websocket_disconnected': self._repair_websocket,
            'insufficient_balance': self._handle_insufficient_balance,
            'rate_limit_exceeded': self._handle_rate_limit,
            'order_minimum_not_met': self._adjust_order_size
        }
        
    async def run_diagnostics(self):
        """Run continuous diagnostics"""
        while True:
            try:
                # Check component health
                await self._check_component_health()
                
                # Analyze performance
                await self._analyze_performance()
                
                # Auto-repair if needed
                await self._auto_repair()
                
                # Learn from patterns
                await self._learn_from_patterns()
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"[DIAGNOSTIC] Error: {e}")
                
    async def _check_component_health(self):
        """Check health of all components"""
        components = {
            'websocket': self._check_websocket_health,
            'executor': self._check_executor_health,
            'balance': self._check_balance_health,
            'strategies': self._check_strategy_health
        }
        
        for name, check_func in components.items():
            try:
                status = await check_func()
                self.health_metrics['component_status'][name] = status
            except Exception as e:
                logger.error(f"[DIAGNOSTIC] {name} health check failed: {e}")
                self.health_metrics['component_status'][name] = 'error'
                
    async def _analyze_performance(self):
        """Analyze trading performance and optimize"""
        try:
            # Calculate win rate
            if self.health_metrics['trades_executed'] > 0:
                win_rate = self.health_metrics['trades_successful'] / self.health_metrics['trades_executed']
                
                # Adjust strategy confidence thresholds
                if win_rate < 0.4:
                    logger.info("[LEARNING] Low win rate - increasing confidence threshold")
                    if hasattr(self.bot, 'min_confidence'):
                        self.bot.min_confidence = min(0.9, self.bot.min_confidence + 0.05)
                elif win_rate > 0.7:
                    logger.info("[LEARNING] High win rate - decreasing confidence threshold")
                    if hasattr(self.bot, 'min_confidence'):
                        self.bot.min_confidence = max(0.6, self.bot.min_confidence - 0.05)
                        
        except Exception as e:
            logger.error(f"[DIAGNOSTIC] Performance analysis error: {e}")
            
    async def _auto_repair(self):
        """Automatically repair detected issues"""
        for component, status in self.health_metrics['component_status'].items():
            if status == 'error' or status == 'disconnected':
                logger.info(f"[REPAIR] Attempting to repair {component}")
                
                repair_key = f"{component}_disconnected"
                if repair_key in self.repair_strategies:
                    await self.repair_strategies[repair_key]()
                    
    async def _repair_websocket(self):
        """Repair WebSocket connection"""
        try:
            if hasattr(self.bot.components, 'websocket_manager'):
                await self.bot.components.websocket_manager.reconnect()
                logger.info("[REPAIR] WebSocket reconnected")
        except Exception as e:
            logger.error(f"[REPAIR] WebSocket repair failed: {e}")
            
    async def _handle_insufficient_balance(self):
        """Handle insufficient balance by checking deployed funds"""
        try:
            # Check if funds are deployed in positions
            if hasattr(self.bot.components, 'balance_manager'):
                deployment_status = await self.bot.components.balance_manager.get_deployment_status('USDT')
                if deployment_status == 'funds_deployed':
                    logger.info("[REPAIR] Funds are deployed in positions - waiting for exits")
                else:
                    logger.warning("[REPAIR] Truly insufficient funds - need deposit")
        except Exception as e:
            logger.error(f"[REPAIR] Balance check error: {e}")
            
    async def _handle_rate_limit(self):
        """Handle rate limit by adjusting trading frequency"""
        try:
            logger.info("[REPAIR] Rate limit hit - increasing trade intervals")
            if hasattr(self.bot, 'trade_interval'):
                self.bot.trade_interval = min(60, self.bot.trade_interval * 1.5)
        except Exception as e:
            logger.error(f"[REPAIR] Rate limit handling error: {e}")
            
    async def _adjust_order_size(self):
        """Adjust order size to meet minimums"""
        try:
            logger.info("[REPAIR] Adjusting order size to meet $5 USDT minimum")
            if hasattr(self.bot, 'default_order_size'):
                self.bot.default_order_size = max(5.0, self.bot.default_order_size)
        except Exception as e:
            logger.error(f"[REPAIR] Order size adjustment error: {e}")
```

## 6. FETCH SYMBOLS FROM KRAKEN

File: src/bot.py
Add method to fetch active USDT pairs:

```python
async def _fetch_active_usdt_pairs(self):
    """Fetch active USDT trading pairs from Kraken"""
    try:
        # Get all markets
        markets = await self.exchange.load_markets()
        
        # Filter for USDT pairs with good volume
        usdt_pairs = []
        for symbol, market in markets.items():
            if symbol.endswith('/USDT') and market.get('active', False):
                # Check if it meets minimum requirements
                info = market.get('info', {})
                if info.get('status') == 'online':
                    usdt_pairs.append(symbol)
                    
        # Get top 10 by volume
        if len(usdt_pairs) > 10:
            # Fetch tickers to sort by volume
            tickers = await self.exchange.fetch_tickers(usdt_pairs)
            sorted_pairs = sorted(
                usdt_pairs,
                key=lambda x: tickers.get(x, {}).get('quoteVolume', 0),
                reverse=True
            )
            usdt_pairs = sorted_pairs[:10]
            
        logger.info(f"[SYMBOLS] Active USDT pairs: {usdt_pairs}")
        return usdt_pairs
        
    except Exception as e:
        logger.error(f"[SYMBOLS] Error fetching pairs: {e}")
        # Fallback to default pairs
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "MATIC/USDT"]
```

## 7. CLEAN UP PROJECT STRUCTURE

Delete these redundant files:
- src/kraken_compliance_*.py (merge into single kraken_compliance.py)
- src/initialization_recovery_system.py (merge with error handling)
- Any backup or test files
- Old strategy files not using USDT

## 8. FINAL CONFIG.JSON

```json
{
    "exchange": {
        "name": "kraken",
        "api_key": "YOUR_KEY",
        "api_secret": "YOUR_SECRET"
    },
    "trading": {
        "quote_currency": "USDT",
        "position_size": 10.0,
        "min_position_size": 5.0,
        "max_position_size": 100.0,
        "take_profit_pct": 0.5,
        "stop_loss_pct": 0.8,
        "enable_micro_trades": true,
        "min_confidence": 0.7
    },
    "risk_management": {
        "max_open_positions": 5,
        "max_daily_loss": 50.0,
        "max_position_pct": 20.0
    },
    "intervals": {
        "trade_interval": 10,
        "market_scan_interval": 5,
        "balance_check_interval": 30
    }
}
```

Execute all changes in order. Test with python scripts/simple_bot_launcher.py