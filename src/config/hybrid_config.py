"""
Kraken Bot Configuration - Hybrid Approach
WebSocket v2 for real-time data, REST API for trading
Updated: July 2025
"""

# API Configuration
KRAKEN_CONFIG = {
    # Connection endpoints (2025 current)
    "endpoints": {
        "rest_api": "https://api.kraken.com",
        "ws_v2_public": "wss://ws.kraken.com/v2",
        "ws_v2_private": "wss://ws-auth.kraken.com/v2",
        "ws_v1_public": "wss://ws.kraken.com",  # Legacy, not used
        "ws_v1_private": "wss://ws-auth.kraken.com"  # Legacy, not used
    },
    
    # Hybrid approach settings
    "hybrid_mode": {
        "use_websocket_for": ["ticker", "orderbook", "ohlc", "trades", "spread"],
        "use_rest_api_for": ["place_order", "cancel_order", "modify_order", "get_balance", "get_positions"],
        "balance_update_method": "websocket_with_rest_fallback",
        "order_updates": "websocket_executions_channel"
    },
    
    # WebSocket v2 specific settings
    "websocket_v2": {
        "reconnect_delay": 5,
        "max_reconnect_attempts": 10,
        "heartbeat_interval": 30,
        "token_refresh_minutes": 10,  # Refresh before 15 min expiry
        "channels": {
            "public": ["ticker", "book", "ohlc", "trade", "spread"],
            "private": ["executions", "balances"]
        },
        "orderbook_depth": 10,
        "ohlc_interval": 1  # 1 minute candles
    },
    
    # Trading settings
    "trading": {
        "max_orders_per_pair": 3,
        "min_order_size_usdt": 1.0,
        "max_order_size_pct": 0.7,  # 70% of balance
        "profit_target_pct": 0.5,   # 0.5% micro profit
        "stop_loss_pct": 0.001,     # 0.1% tight stop
        "use_ioc_orders": True,     # Immediate or Cancel for scalping
        "order_timeout_seconds": 300  # 5 minutes
    },
    
    # Rate limiting (pro tier)
    "rate_limits": {
        "rest_api_counter_max": 20,
        "rest_api_decay_per_sec": 1.0,
        "trading_counter_max": 180,
        "trading_decay_per_sec": 3.75,
        "ws_reconnect_per_10min": 150,
        "order_rate_per_minute": 30
    },
    
    # Symbols to trade (using v2 format)
    "trading_pairs": [
        "SHIB/USDT",
        "AI16Z/USDT", 
        "BERA/USDT",
        "MANA/USDT",
        "DOT/USDT",
        "LINK/USDT",
        "SOL/USDT",
        "BTC/USDT"
    ],
    
    # Error handling
    "error_handling": {
        "nonce_errors_max_retries": 3,
        "api_error_backoff_seconds": 2,
        "insufficient_funds_retry_delay": 60,
        "connection_timeout": 30
    }
}

# Safe startup procedure
STARTUP_SEQUENCE = [
    "1. Initialize REST API connection",
    "2. Test API key permissions", 
    "3. Get WebSocket token via GetWebSocketsToken",
    "4. Connect to WebSocket v2 public channels",
    "5. Connect to WebSocket v2 private channels",
    "6. Verify data flow from all channels",
    "7. Fetch initial balances via REST",
    "8. Start trading logic"
]

# Critical checks
CRITICAL_CHECKS = {
    "api_key_permissions": [
        "Query Funds",
        "Query open orders & trades",
        "Query closed orders & trades", 
        "Create & modify orders",
        "Cancel & close orders",
        "Access WebSockets API"  # MOST IMPORTANT
    ],
    "websocket_token_valid": "Must use within 15 minutes",
    "symbol_format": "Use BTC/USDT not XBTUSD",
    "decimal_precision": "Use string format for prices"
}
