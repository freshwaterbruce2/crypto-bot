"""
Global Constants for Kraken Trading Bot
======================================

This module defines all global constants used throughout the trading system.
Centralizing these values ensures consistency and makes updates easier.

CRITICAL: KRAKEN MINIMUM ORDER REQUIREMENTS
==========================================

Kraken enforces the following minimum order sizes:

1. FIAT PAIRS (e.g., BTC/USD, ETH/EUR):
   - USD, EUR, GBP, CAD, AUD, CHF: 1 unit minimum
   - JPY: 110 JPY minimum

2. CRYPTO-TO-CRYPTO PAIRS:
   - General minimum: $1 USD equivalent
   - TIER-1 pairs (SHIB/USDT, DOGE/USDT, etc.): $2 USD minimum

3. SPECIFIC ASSET MINIMUMS:
   - BTC pairs: 0.0001 BTC minimum
   - ETH pairs: 0.01 ETH minimum
   - Other assets: As specified in KRAKEN_MIN_ORDER_SIZES

IMPORTANT NOTES:
- These minimums apply to ALL account types (Starter, Intermediate, Pro)
- Pro accounts get fee-free trading but NOT reduced minimums
- Violating these minimums results in order rejection
- TIER-1 pairs require $2 USD minimum regardless of Pro account status

SOURCE: https://support.kraken.com/hc/en-us/articles/205893708-Minimum-order-size
"""

# TIER-1 TRADING LIMITS
# CRITICAL: Kraken requires $2 USD minimum for TIER-1 pairs (like SHIB/USDT)
MINIMUM_ORDER_SIZE_TIER1 = 2.0  # USDT - CORRECTED: Kraken TIER-1 minimum requirement

# Kraken API Tier Limits
KRAKEN_API_TIER_LIMITS = {
    'starter': {
        'min_order': 2.0,  # CORRECTED: Kraken requires $2 USD minimum for TIER-1 pairs
        'max_order': 100.0,
        'rate_limit': 15,  # requests per second
        'max_open_orders': 60
    },
    'intermediate': {
        'min_order': 2.0,  # CORRECTED: Kraken requires $2 USD minimum for TIER-1 pairs
        'max_order': 500.0,
        'rate_limit': 20,
        'max_open_orders': 80
    },
    'pro': {
        'min_order': 2.0,  # CORRECTED: Kraken requires $2 USD minimum for TIER-1 pairs
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
# SOURCE: https://support.kraken.com/hc/en-us/articles/205893708-Minimum-order-size
# CRITICAL: These are Kraken's official minimum order requirements
KRAKEN_MIN_ORDER_SIZES = {
    # Major cryptocurrencies
    'BTC': 0.0001,      # Bitcoin - 0.0001 BTC minimum
    'ETH': 0.01,        # Ethereum - 0.01 ETH minimum
    'USDT': 1.0,        # Tether - $1 USD equivalent minimum
    'USDC': 1.0,        # USD Coin - $1 USD equivalent minimum
    'USD': 1.0,         # US Dollar - $1 USD minimum
    'EUR': 1.0,         # Euro - 1 EUR minimum
    'GBP': 1.0,         # British Pound - 1 GBP minimum
    'CAD': 1.0,         # Canadian Dollar - 1 CAD minimum
    'AUD': 1.0,         # Australian Dollar - 1 AUD minimum
    'CHF': 1.0,         # Swiss Franc - 1 CHF minimum
    'JPY': 110.0,       # Japanese Yen - 110 JPY minimum

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

    # Timing constants (COMPLIANCE: Increased for rate limit safety)
    'MIN_HOLD_TIME': 60,             # 60 seconds minimum - compliance requirement
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

# Infinity Loop Configuration (RATE LIMIT COMPLIANT)
INFINITY_LOOP_CONFIG = {
    'SCAN_INTERVAL': 15,             # FIXED: Sustainable scanning - 15 seconds (rate limit compliant)
    'BATCH_WINDOW': 5,               # FIXED: Slower batching - 5 seconds (prevent API flooding)
    'MAX_SIGNALS_PER_BATCH': 5,      # FIXED: Fewer signals per batch for rate limit compliance
    'CAPITAL_DEPLOYMENT_TARGET': 0.70, # COMPLIANCE: Reduced to 70% for risk management
    'REBALANCE_THRESHOLD': 0.95,     # FIXED: Less aggressive rebalancing at 95%
    'MICRO_SCALPING_MODE': False,    # DISABLED: Micro-scalping causes rate limit violations
    'FEE_FREE_ADVANTAGE': True,      # Keep fee-free optimizations
}

def get_minimum_order_size(api_tier: str = 'starter') -> float:
    """Get minimum order size for given API tier"""
    return KRAKEN_API_TIER_LIMITS.get(api_tier, {}).get('min_order', MINIMUM_ORDER_SIZE_TIER1)

def get_asset_minimum(asset: str) -> float:
    """Get minimum order size for specific asset"""
    return KRAKEN_MIN_ORDER_SIZES.get(asset.upper(), 1.0)

def calculate_minimum_cost(asset: str, price: float, api_tier: str = 'starter') -> float:
    """
    Calculate minimum order cost in USDT according to Kraken's requirements

    CRITICAL: Kraken requirements:
    - Fiat pairs: 1 unit minimum (USD, EUR, etc.), 110 JPY
    - Crypto-to-crypto pairs: $1 USD equivalent minimum
    - TIER-1 pairs (SHIB/USDT, etc.): $2 USD minimum
    - BTC pairs: 0.0001 BTC minimum
    - ETH pairs: 0.01 ETH minimum

    Args:
        asset: Asset symbol (e.g., 'SHIB', 'BTC')
        price: Current price of the asset
        api_tier: API tier ('starter', 'intermediate', 'pro')

    Returns:
        Minimum order cost in USDT
    """
    asset_min = get_asset_minimum(asset)
    min_cost = asset_min * price
    tier_min = get_minimum_order_size(api_tier)

    # TIER-1 pairs require $2 USD minimum (like SHIB/USDT)
    # This is a Kraken exchange requirement, not related to Pro account features
    tier1_assets = ['SHIB', 'DOGE', 'ADA', 'XRP', 'ALGO', 'MATIC']
    if asset.upper() in tier1_assets:
        tier_min = max(tier_min, MINIMUM_ORDER_SIZE_TIER1)  # Ensure $2 minimum

    # The final minimum is the higher of asset minimum cost or tier minimum
    final_minimum = max(min_cost, tier_min)

    # IMPORTANT: Do NOT reduce minimums for Pro accounts
    # Kraken's minimum order requirements apply to ALL account types
    return final_minimum

# PRO ACCOUNT FEE-FREE CONSTANTS (2025 ENHANCED OPTIMIZATION)
PRO_ACCOUNT_OPTIMIZATIONS = {
    'FEE_FREE_TRADING': True,
    'MICRO_PROFIT_THRESHOLD': 0.001,    # 0.1% minimum profit (fee-free allows this)
    'ULTRA_MICRO_THRESHOLD': 0.0005,    # 0.05% ultra-micro (NEW - only possible fee-free)
    'MAX_TRADE_FREQUENCY_PER_MINUTE': 5,   # FIXED: Reduced to 5 trades/minute for rate limit compliance
    'CAPITAL_VELOCITY_TARGET': 3.0,      # FIXED: Reduced to 3x daily velocity (sustainable)
    'COMPOUND_GROWTH_MODE': True,        # Enable compound growth acceleration
    'TIGHT_SPREAD_ADVANTAGE': 0.0002,   # 0.02% tighter spreads with no fees
    'POSITION_SIZE_MULTIPLIER': 1.5,    # 50% larger positions (no fee overhead)
    'STOP_LOSS_AGGRESSIVENESS': 2.0,    # 2x more aggressive stops (free exits)
    'BURST_CAPACITY_MULTIPLIER': 1.2,   # 20% burst allowance for Pro tier
    'IOC_ORDER_OPTIMIZATION': True,      # Immediate-or-Cancel order optimization
    'MICRO_SCALPING_MODE': True,         # Ultra-fast micro-scalping enabled
}
