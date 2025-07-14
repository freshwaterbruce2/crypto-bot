"""
Global Constants for Kraken Trading Bot
======================================

This module defines all global constants used throughout the trading system.
Centralizing these values ensures consistency and makes updates easier.
"""

# TIER-1 TRADING LIMITS
MINIMUM_ORDER_SIZE_TIER1 = 3.5  # USDT - Global minimum for tier-1 accounts (optimized for $5 balance)

# Kraken API Tier Limits
KRAKEN_API_TIER_LIMITS = {
    'starter': {
        'min_order': 2.0,
        'max_order': 100.0,
        'rate_limit': 15,  # requests per second
        'max_open_orders': 60
    },
    'intermediate': {
        'min_order': 3.5,
        'max_order': 500.0,
        'rate_limit': 20,
        'max_open_orders': 80
    },
    'pro': {
        'min_order': 0.5,  # ENHANCED: Ultra-low minimums with fee-free trading
        'max_order': 50000.0,  # Increased for Pro tier
        'rate_limit': 180,  # Pro tier: 180 calls/counter 
        'rate_decay': 3.75,  # Pro tier: 3.75/s decay rate
        'burst_allowance': 216,  # 20% burst capacity (180 * 1.2)
        'max_open_orders': 225,
        'fee_free_trading': True,  # CRITICAL: No trading fees
        'priority_api_access': True,  # Enhanced API priority
        'advanced_order_types': True,  # Access to advanced orders
        'ioc_orders_enabled': True,  # Immediate-or-Cancel orders
        'micro_scalping_optimized': True,  # Ultra-fast execution
        'priority_websocket': True  # Priority WebSocket access
    }
}

# Kraken Minimum Order Sizes by Asset (Base Currency)
KRAKEN_MIN_ORDER_SIZES = {
    # Major cryptocurrencies
    'BTC': 0.0001,      # Bitcoin
    'ETH': 0.01,        # Ethereum
    'USDT': 1.0,        # Tether
    'USDC': 1.0,        # USD Coin
    'USD': 1.0,         # US Dollar
    'EUR': 5.0,         # Euro
    
    # Low-priced assets (good for tier-1)
    'SHIB': 100000,     # Shiba Inu
    'DOGE': 10,         # Dogecoin
    'ADA': 5,           # Cardano
    'XRP': 10,          # Ripple
    'ALGO': 5,          # Algorand
    'MATIC': 5,         # Polygon
    
    # Mid-range assets
    'DOT': 0.1,         # Polkadot
    'LINK': 0.1,        # Chainlink
    'UNI': 0.1,         # Uniswap
    'AVAX': 0.1,        # Avalanche
    'SOL': 0.01,        # Solana
    
    # Stablecoins
    'DAI': 1.0,         # DAI
    'BUSD': 1.0,        # Binance USD
}

# Trading Strategy Constants
TRADING_CONSTANTS = {
    # Profit targets for fee-free micro-scalping (PRO ACCOUNT OPTIMIZED)
    'MIN_PROFIT_TARGET': 0.001,      # 0.1% - Fee-free allows tiny profits
    'DEFAULT_PROFIT_TARGET': 0.003,  # 0.3% - Reduced for high frequency
    'MAX_PROFIT_TARGET': 0.005,      # 0.5% - Quick scalping
    
    # Stop loss settings (TIGHTER for fee-free exits)
    'DEFAULT_STOP_LOSS': 0.003,      # 0.3% - No exit fees enable tight stops
    'TIGHT_STOP_LOSS': 0.002,        # 0.2% - Ultra-tight for scalping
    'MAX_STOP_LOSS': 0.008,          # 0.8% - Reduced maximum
    
    # Position management (AGGRESSIVE for fee-free trading)
    'MAX_POSITIONS': 20,             # More positions for diversification
    'MAX_POSITION_SIZE_PCT': 0.15,   # 15% of portfolio per position
    'MIN_POSITION_SIZE_PCT': 0.005,  # 0.5% - Much smaller minimum positions
    
    # Timing constants (FASTER for high-frequency scalping)
    'MIN_HOLD_TIME': 10,             # 10 seconds minimum - faster exits
    'MAX_HOLD_TIME': 120,            # 2 minutes maximum - quick scalping
    'SIGNAL_COOLDOWN': 1,            # 1 second between signals - higher frequency
    
    # Risk management
    'MAX_DAILY_LOSS_PCT': 5.0,       # 5% maximum daily loss
    'CIRCUIT_BREAKER_THRESHOLD': 3.0, # 3% drawdown triggers circuit breaker
    
    # Signal generation
    'MIN_CONFIDENCE_THRESHOLD': 0.5,  # 50% minimum confidence for signals
}

# WebSocket Configuration
WEBSOCKET_CONFIG = {
    'PING_INTERVAL': 30,
    'PING_TIMEOUT': 10,
    'RECONNECT_DELAY': 5,
    'MAX_RECONNECT_ATTEMPTS': 10,
    'MESSAGE_TIMEOUT': 60,
}

# Performance Thresholds
PERFORMANCE_THRESHOLDS = {
    'MIN_WIN_RATE': 0.4,             # 40% minimum win rate
    'TARGET_WIN_RATE': 0.6,          # 60% target win rate
    'MIN_PROFIT_FACTOR': 1.2,        # 1.2 minimum profit factor
    'TARGET_PROFIT_FACTOR': 1.5,     # 1.5 target profit factor
}

# Self-Management Settings
SELF_MANAGEMENT_CONFIG = {
    'HEALTH_CHECK_INTERVAL': 60,     # Check health every 60 seconds
    'OPTIMIZATION_INTERVAL': 3600,   # Optimize parameters every hour
    'LEARNING_BATCH_SIZE': 100,      # Learn from last 100 trades
    'ERROR_RECOVERY_DELAY': 30,      # Wait 30 seconds before retry
    'MAX_ERROR_RETRIES': 3,          # Maximum error recovery attempts
}

# Infinity Loop Configuration (PRO ACCOUNT OPTIMIZED)
INFINITY_LOOP_CONFIG = {
    'SCAN_INTERVAL': 2,              # Faster scanning - 2 seconds (fee-free advantage)
    'BATCH_WINDOW': 1,               # Faster batching - 1 second
    'MAX_SIGNALS_PER_BATCH': 20,     # More signals per batch for higher frequency
    'CAPITAL_DEPLOYMENT_TARGET': 0.95, # Target 95% capital deployment (no fee overhead)
    'REBALANCE_THRESHOLD': 0.98,     # More aggressive rebalancing at 98%
    'MICRO_SCALPING_MODE': True,     # Enable micro-scalping for Pro accounts
    'FEE_FREE_ADVANTAGE': True,      # Flag for fee-free optimizations
}

def get_minimum_order_size(api_tier: str = 'starter') -> float:
    """Get minimum order size for given API tier"""
    return KRAKEN_API_TIER_LIMITS.get(api_tier, {}).get('min_order', MINIMUM_ORDER_SIZE_TIER1)

def get_asset_minimum(asset: str) -> float:
    """Get minimum order size for specific asset"""
    return KRAKEN_MIN_ORDER_SIZES.get(asset.upper(), 1.0)

def calculate_minimum_cost(asset: str, price: float, api_tier: str = 'starter') -> float:
    """Calculate minimum order cost in USDT with Pro account optimizations"""
    asset_min = get_asset_minimum(asset)
    min_cost = asset_min * price
    tier_min = get_minimum_order_size(api_tier)
    
    # Pro account fee-free optimization: Allow smaller trades
    if api_tier == 'pro' and KRAKEN_API_TIER_LIMITS['pro'].get('fee_free_trading', False):
        # Fee-free trading allows 50% smaller minimum positions
        base_minimum = max(min_cost, tier_min)
        return base_minimum * 0.5
    
    return max(min_cost, tier_min)

# PRO ACCOUNT FEE-FREE CONSTANTS (2025 ENHANCED OPTIMIZATION)
PRO_ACCOUNT_OPTIMIZATIONS = {
    'FEE_FREE_TRADING': True,
    'MICRO_PROFIT_THRESHOLD': 0.001,    # 0.1% minimum profit (fee-free allows this)
    'ULTRA_MICRO_THRESHOLD': 0.0005,    # 0.05% ultra-micro (NEW - only possible fee-free)
    'MAX_TRADE_FREQUENCY_PER_MINUTE': 30,  # Up to 30 trades/minute for Pro tier
    'CAPITAL_VELOCITY_TARGET': 12.0,     # ENHANCED: 12x capital velocity daily (up from 10x)
    'COMPOUND_GROWTH_MODE': True,        # Enable compound growth acceleration
    'TIGHT_SPREAD_ADVANTAGE': 0.0002,   # 0.02% tighter spreads with no fees
    'POSITION_SIZE_MULTIPLIER': 1.5,    # 50% larger positions (no fee overhead)
    'STOP_LOSS_AGGRESSIVENESS': 2.0,    # 2x more aggressive stops (free exits)
    'BURST_CAPACITY_MULTIPLIER': 1.2,   # 20% burst allowance for Pro tier
    'IOC_ORDER_OPTIMIZATION': True,      # Immediate-or-Cancel order optimization
    'MICRO_SCALPING_MODE': True,         # Ultra-fast micro-scalping enabled
}