# Kraken Trading Bot 2025 - Integration Guide

This guide covers the integration of all major components within the trading bot system, including proper initialization sequences, component relationships, and best practices.

## Table of Contents
1. [Core System Integration](#core-system-integration)
2. [Exchange Integration](#exchange-integration)
3. [Strategy Integration](#strategy-integration)
4. [Learning System Integration](#learning-system-integration)
5. [Dashboard Integration](#dashboard-integration)
6. [MCP Server Integration](#mcp-server-integration)
7. [Testing Integration](#testing-integration)

## Core System Integration

### Main Bot Initialization

The primary bot class (`src/core/bot.py`) serves as the central orchestrator. Here's the proper initialization sequence:

```python
# src/core/bot.py
import asyncio
from typing import Optional, Dict, Any
from decimal import Decimal

from src.config.config import load_config
from src.exchange.kraken_sdk_exchange import KrakenSDKExchange
from src.trading.unified_balance_manager import UnifiedBalanceManager
from src.trading.opportunity_scanner import OpportunityScanner
from src.trading.enhanced_trade_executor_with_assistants import EnhancedTradeExecutor
from src.learning.unified_learning_system import UnifiedLearningSystem
from src.utils.custom_logging import setup_logging
from src.utils.self_repair import SelfRepairSystem

class TradingBot:
    """Main trading bot orchestrator with full system integration."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the trading bot with all required components."""
        
        # Load configuration
        self.config = load_config(config_path)
        
        # Setup logging
        self.logger = setup_logging(self.config.get('logging', {}))
        
        # Initialize core components
        self.exchange = None
        self.balance_manager = None
        self.opportunity_scanner = None
        self.trade_executor = None
        self.learning_system = None
        self.self_repair = None
        
        # Runtime state
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self) -> bool:
        """Initialize all bot components in proper order."""
        try:
            self.logger.info("[INIT] Starting bot initialization...")
            
            # 1. Initialize exchange connection
            await self._initialize_exchange()
            
            # 2. Initialize balance management
            await self._initialize_balance_manager()
            
            # 3. Initialize trading components
            await self._initialize_trading_components()
            
            # 4. Initialize learning system
            await self._initialize_learning_system()
            
            # 5. Initialize self-repair system
            await self._initialize_self_repair()
            
            # 6. Perform system validation
            await self._validate_system()
            
            self.logger.info("[INIT] Bot initialization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"[INIT] Initialization failed: {e}")
            return False
    
    async def _initialize_exchange(self):
        """Initialize exchange connection and authentication."""
        self.exchange = KrakenSDKExchange(
            api_key=self.config['kraken_api_key'],
            api_secret=self.config['kraken_api_secret'],
            config=self.config.get('exchange_config', {})
        )
        
        # Test connection and authentication
        await self.exchange.initialize()
        
        # Start WebSocket connections
        await self.exchange.start_websocket()
        
    async def _initialize_balance_manager(self):
        """Initialize balance management system."""
        self.balance_manager = UnifiedBalanceManager(
            exchange=self.exchange,
            config=self.config.get('balance_config', {})
        )
        
        await self.balance_manager.initialize()
        
    async def _initialize_trading_components(self):
        """Initialize trading-related components."""
        
        # Opportunity scanner
        self.opportunity_scanner = OpportunityScanner(
            exchange=self.exchange,
            balance_manager=self.balance_manager,
            config=self.config.get('scanner_config', {})
        )
        
        # Trade executor with AI assistants
        self.trade_executor = EnhancedTradeExecutor(
            exchange=self.exchange,
            balance_manager=self.balance_manager,
            config=self.config.get('executor_config', {})
        )
        
        await self.opportunity_scanner.initialize()
        await self.trade_executor.initialize()
        
    async def _initialize_learning_system(self):
        """Initialize AI learning and adaptation system."""
        self.learning_system = UnifiedLearningSystem(
            exchange=self.exchange,
            balance_manager=self.balance_manager,
            trade_executor=self.trade_executor,
            config=self.config.get('learning_config', {})
        )
        
        await self.learning_system.initialize()
        
    async def _initialize_self_repair(self):
        """Initialize self-healing and repair system."""
        self.self_repair = SelfRepairSystem(
            bot=self,
            config=self.config.get('self_repair_config', {})
        )
        
        await self.self_repair.initialize()
```

## Exchange Integration

### Kraken SDK Integration

The bot uses the official Kraken SDK with custom enhancements:

```python
# src/exchange/kraken_sdk_exchange.py
from kraken.sdk import Kraken
from src.utils.rate_limit_handler import RateLimitHandler
from src.utils.decimal_precision_fix import safe_decimal

class KrakenSDKExchange:
    """Enhanced Kraken SDK wrapper with rate limiting and error handling."""
    
    def __init__(self, api_key: str, api_secret: str, config: Dict[str, Any]):
        self.kraken = Kraken(api_key=api_key, api_secret=api_secret)
        self.rate_limiter = RateLimitHandler(config.get('rate_limit_config', {}))
        self.config = config
        
    async def get_balance(self) -> Dict[str, Decimal]:
        """Get account balance with decimal precision."""
        async with self.rate_limiter:
            balance = await self.kraken.get_balance()
            return {k: safe_decimal(v) for k, v in balance.items()}
    
    async def place_order(self, pair: str, side: str, amount: Decimal, price: Decimal = None) -> Dict:
        """Place order with enhanced error handling."""
        async with self.rate_limiter:
            return await self.kraken.place_order(
                pair=pair,
                side=side,
                amount=str(amount),
                price=str(price) if price else None
            )
```

### WebSocket V2 Integration

```python
# src/exchange/websocket_manager_v2.py
from kraken.sdk import WebSocketManager
from src.utils.event_bus import EventBus

class WebSocketManagerV2:
    """WebSocket V2 manager with event-driven architecture."""
    
    def __init__(self, exchange, event_bus: EventBus):
        self.exchange = exchange
        self.event_bus = event_bus
        self.ws_manager = WebSocketManager()
        
    async def start_data_feeds(self, pairs: List[str]):
        """Start real-time data feeds for specified pairs."""
        
        # Subscribe to ticker data
        await self.ws_manager.subscribe_ticker(
            pairs=pairs,
            callback=self._on_ticker_update
        )
        
        # Subscribe to order book updates
        await self.ws_manager.subscribe_book(
            pairs=pairs,
            callback=self._on_book_update
        )
    
    async def _on_ticker_update(self, data):
        """Handle ticker updates."""
        await self.event_bus.emit('ticker_update', data)
    
    async def _on_book_update(self, data):
        """Handle order book updates."""
        await self.event_bus.emit('book_update', data)
```

## Strategy Integration

### Multi-Strategy Architecture

```python
# src/strategies/enhanced_portfolio_strategy.py
from src.strategies.base_strategy import BaseStrategy
from src.learning.pattern_recognition import PatternRecognition

class EnhancedPortfolioStrategy(BaseStrategy):
    """Portfolio-aware strategy with AI integration."""
    
    def __init__(self, exchange, balance_manager, learning_system, config):
        super().__init__(config)
        self.exchange = exchange
        self.balance_manager = balance_manager
        self.learning_system = learning_system
        self.pattern_recognition = PatternRecognition(config)
        
    async def generate_signals(self, market_data: Dict) -> List[Dict]:
        """Generate trading signals based on portfolio state and AI insights."""
        
        # Get current portfolio state
        portfolio = await self.balance_manager.get_portfolio_summary()
        
        # Get AI-generated insights
        insights = await self.learning_system.get_market_insights(market_data)
        
        # Generate signals using pattern recognition
        patterns = await self.pattern_recognition.analyze(market_data)
        
        # Combine all factors to generate final signals
        signals = await self._combine_factors(portfolio, insights, patterns)
        
        return signals
```

## Learning System Integration

### Unified Learning Architecture

```python
# src/learning/unified_learning_system.py
from src.learning.neural_pattern_engine import NeuralPatternEngine
from src.learning.advanced_memory_manager import AdvancedMemoryManager

class UnifiedLearningSystem:
    """Central learning system coordinating all AI components."""
    
    def __init__(self, exchange, balance_manager, trade_executor, config):
        self.exchange = exchange
        self.balance_manager = balance_manager
        self.trade_executor = trade_executor
        
        # Initialize learning components
        self.pattern_engine = NeuralPatternEngine(config)
        self.memory_manager = AdvancedMemoryManager(config)
        
    async def learn_from_trade(self, trade_data: Dict):
        """Learn from completed trade."""
        
        # Extract features from trade
        features = await self._extract_trade_features(trade_data)
        
        # Update pattern recognition
        await self.pattern_engine.update_patterns(features)
        
        # Store in memory
        await self.memory_manager.store_experience(trade_data, features)
        
    async def get_market_insights(self, market_data: Dict) -> Dict:
        """Generate market insights based on learned patterns."""
        
        # Analyze current market conditions
        current_patterns = await self.pattern_engine.analyze(market_data)
        
        # Retrieve relevant historical experiences
        similar_experiences = await self.memory_manager.find_similar_situations(current_patterns)
        
        # Generate insights
        insights = await self._generate_insights(current_patterns, similar_experiences)
        
        return insights
```

## Dashboard Integration

### Real-Time Data Pipeline

```python
# dashboard/backend/main.py
from fastapi import FastAPI, WebSocket
from src.utils.event_bus import EventBus

app = FastAPI()
event_bus = EventBus()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await websocket.accept()
    
    # Subscribe to bot events
    async def send_update(event_type: str, data: Dict):
        await websocket.send_json({
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        })
    
    event_bus.subscribe('balance_update', send_update)
    event_bus.subscribe('trade_executed', send_update)
    event_bus.subscribe('signal_generated', send_update)
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        event_bus.unsubscribe_all(send_update)
```

### Frontend Integration

```jsx
// dashboard/frontend/src/hooks/useBotData.js
import { useState, useEffect } from 'react';

export const useBotData = () => {
    const [botData, setBotData] = useState({
        balance: {},
        positions: [],
        trades: [],
        performance: {}
    });
    
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            switch (message.type) {
                case 'balance_update':
                    setBotData(prev => ({
                        ...prev,
                        balance: message.data
                    }));
                    break;
                    
                case 'trade_executed':
                    setBotData(prev => ({
                        ...prev,
                        trades: [message.data, ...prev.trades.slice(0, 99)]
                    }));
                    break;
            }
        };
        
        return () => ws.close();
    }, []);
    
    return botData;
};
```

## MCP Server Integration

### Server Setup

```python
# mcp_server/trading_bot_context.py
from mcp.server import Server
from mcp.types import Resource, Tool

class TradingBotMCPServer:
    """MCP server providing bot context and diagnostic tools."""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.server = Server("trading-bot")
        self._register_resources()
        self._register_tools()
    
    def _register_resources(self):
        """Register bot resources for MCP access."""
        
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            return [
                Resource(
                    uri="bot://balance",
                    name="Current Balance",
                    mimeType="application/json"
                ),
                Resource(
                    uri="bot://positions",
                    name="Active Positions",
                    mimeType="application/json"
                ),
                Resource(
                    uri="bot://performance",
                    name="Performance Metrics",
                    mimeType="application/json"
                )
            ]
    
    def _register_tools(self):
        """Register diagnostic tools."""
        
        @self.server.call_tool()
        async def diagnose_system(arguments: dict) -> list[dict]:
            """Run comprehensive system diagnostics."""
            return await self.bot.self_repair.run_diagnostics()
        
        @self.server.call_tool()
        async def emergency_stop(arguments: dict) -> dict:
            """Emergency stop all trading activities."""
            await self.bot.emergency_stop()
            return {"status": "stopped", "timestamp": time.time()}
```

## Testing Integration

### Integration Test Setup

```python
# tests/integration/test_full_system.py
import pytest
import asyncio
from src.core.bot import KrakenTradingBot
from tests.fixtures.mock_exchange import MockExchange

@pytest.fixture
async def bot_instance():
    """Create bot instance for testing."""
    config = {
        'exchange': 'mock',
        'trading_pairs': ['BTC/USDT'],
        'position_size_usdt': 10.0
    }
    
    bot = KrakenTradingBot(config)
    
    # Replace exchange with mock
    bot.exchange = MockExchange()
    
    await bot.initialize()
    yield bot
    await bot.shutdown()

@pytest.mark.asyncio
async def test_full_trading_cycle(bot_instance):
    """Test complete trading cycle integration."""
    
    # 1. Generate market opportunity
    opportunity = await bot_instance.opportunity_scanner.scan_for_opportunities()
    assert len(opportunity) > 0
    
    # 2. Execute trade
    trade_result = await bot_instance.trade_executor.execute_opportunity(opportunity[0])
    assert trade_result['status'] == 'success'
    
    # 3. Verify balance update
    balance = await bot_instance.balance_manager.get_balance()
    assert balance['USDT'] > 0
    
    # 4. Verify learning system update
    insights = await bot_instance.learning_system.get_market_insights({})
    assert 'confidence' in insights
```

## Best Practices

### Error Handling
- Always wrap async operations in try-catch blocks
- Use circuit breakers for external API calls
- Implement graceful degradation for non-critical features
- Log all errors with sufficient context

### Performance Optimization
- Use connection pooling for database operations
- Implement caching for frequently accessed data
- Use async/await consistently throughout the codebase
- Monitor memory usage and implement cleanup routines

### Security Considerations
- Never log sensitive information (API keys, private data)
- Validate all external inputs
- Use secure communication protocols
- Implement rate limiting and request throttling

### Monitoring and Observability
- Emit events for all significant operations
- Track performance metrics continuously
- Implement health checks for all components
- Use structured logging with correlation IDs

---

**Integration Status**: All systems integrated and operational
**Last Updated**: July 30, 2025
**Version**: 2.1.0
