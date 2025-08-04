"""
Kraken WebSocket V2 Implementation Package
==========================================

Comprehensive WebSocket V2 implementation for Kraken exchange with:
- Enhanced connection management and automatic reconnection
- Real-time data processors for all channel types
- Order management via WebSocket V2
- Unified data feed with intelligent source switching
- Advanced authentication with proactive token refresh
- Integration with existing trading infrastructure

Main Components:
- WebSocketV2Manager: Enhanced connection and subscription management
- WebSocketV2ChannelProcessor: Specialized channel data processors
- WebSocketV2OrderManager: Order placement and tracking via WebSocket
- UnifiedDataFeed: Primary WebSocket with REST fallback
- DataModels: Type-safe message models and validation

Usage:
    from src.websocket import WebSocketV2Manager, WebSocketV2Config
    from src.data import UnifiedDataFeed
    
    # Initialize WebSocket V2 manager
    config = WebSocketV2Config()
    ws_manager = WebSocketV2Manager(exchange_client, api_key, private_key, config)
    
    # Start WebSocket manager
    await ws_manager.start()
    
    # Subscribe to channels
    await ws_manager.subscribe_channel('ticker', {'symbol': ['BTC/USDT']})
    await ws_manager.subscribe_channel('balances', private=True)
    
    # Or use unified data feed
    data_feed = UnifiedDataFeed(exchange_client, symbols)
    await data_feed.start()
    balance = await data_feed.get_balance('USDT')
    ticker = await data_feed.get_ticker('BTC/USDT')
"""

# Enhanced WebSocket V2 components
from .websocket_v2_manager import WebSocketV2Manager, WebSocketV2Config
from .websocket_v2_channels import WebSocketV2ChannelProcessor
from .websocket_v2_orders import WebSocketV2OrderManager, OrderRequest, OrderResponse

# New V2 message handler
from .kraken_v2_message_handler import KrakenV2MessageHandler, create_kraken_v2_handler

# Legacy components (maintained for backward compatibility)
from .kraken_websocket_v2 import KrakenWebSocketV2
from .connection_manager import ConnectionManager, ConnectionState

# Data models
from .data_models import (
    WebSocketMessage,
    BalanceUpdate,
    TickerUpdate,
    OrderBookUpdate,
    OrderBookLevel,
    TradeUpdate,
    OHLCUpdate,
    SubscriptionRequest,
    SubscriptionResponse,
    ConnectionStatus
)

__all__ = [
    # Enhanced WebSocket V2 components
    'WebSocketV2Manager',
    'WebSocketV2Config',
    'WebSocketV2ChannelProcessor',
    'WebSocketV2OrderManager',
    'OrderRequest',
    'OrderResponse',
    
    # New V2 message handler
    'KrakenV2MessageHandler',
    'create_kraken_v2_handler',
    
    # Legacy components
    'KrakenWebSocketV2',
    'ConnectionManager',
    'ConnectionState',
    
    # Data models
    'WebSocketMessage',
    'BalanceUpdate',
    'TickerUpdate',
    'OrderBookUpdate',
    'OrderBookLevel',
    'TradeUpdate',
    'OHLCUpdate',
    'SubscriptionRequest',
    'SubscriptionResponse',
    'ConnectionStatus'
]

__version__ = '2.0.0'
__author__ = 'Backend-Coder Agent'