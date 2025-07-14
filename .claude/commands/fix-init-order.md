# FIX 2: INITIALIZATION ORDER

File: src/bot.py

Replace the start() method to fix race condition:

```python
async def start(self):
    """Start bot with proper initialization sequence"""
    try:
        logger.info("[STARTUP] Starting Kraken USDT trading bot...")
        
        # Phase 1: Core components
        await self._initialize_core_components()
        
        # Phase 2: Wait for executor
        if hasattr(self.components, 'trade_executor'):
            if hasattr(self.components.trade_executor, 'wait_until_ready'):
                await self.components.trade_executor.wait_until_ready()
            else:
                await asyncio.sleep(2)
        
        # Phase 3: Market data
        await self._load_initial_market_data()
        
        # Phase 4: Strategies AFTER executor
        await self._initialize_strategies()
        
        # Phase 5: Start
        self.running = True
        
    except Exception as e:
        logger.error(f"[STARTUP] Failed: {e}")
        raise

async def _initialize_core_components(self):
    """Initialize in correct order"""
    # Balance manager first
    if hasattr(self.components, 'balance_manager'):
        await self.components.balance_manager.initialize()
        
    # Risk manager
    if hasattr(self.components, 'risk_manager'):
        await self.components.risk_manager.initialize()
        
    # Trade executor
    if hasattr(self.components, 'trade_executor'):
        await self.components.trade_executor.initialize()
        
    # WebSocket
    if hasattr(self.components, 'websocket_manager'):
        await self.components.websocket_manager.connect()
```