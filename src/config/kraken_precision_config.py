"""
Kraken Price and Volume Precision Configuration
Based on official Kraken API documentation: https://api.kraken.com/0/public/AssetPairs
Updated: 2025-08-01
"""

# Kraken precision requirements for USDT pairs your bot trades
KRAKEN_PRECISION_CONFIG = {
    # Your current trading pairs with exact Kraken requirements
    'SHIB/USDT': {
        'price_decimals': 8,      # Maximum price precision
        'min_volume': 160000,     # Minimum volume (160,000 SHIB)
        'base_precision': 0,      # Integer SHIB amounts only
        'quote_precision': 8,     # USDT precision
    },
    'AI16Z/USDT': {
        'price_decimals': 4,      # Maximum price precision
        'min_volume': 5,          # Minimum volume (5 AI16Z)
        'base_precision': 3,      # AI16Z precision
        'quote_precision': 4,     # USDT precision
    },
    'BERA/USDT': {
        'price_decimals': 4,      # Maximum price precision
        'min_volume': 0.5,        # Minimum volume (0.5 BERA)
        'base_precision': 1,      # BERA precision
        'quote_precision': 4,     # USDT precision
    },
    'MANA/USDT': {
        'price_decimals': 5,      # Maximum price precision
        'min_volume': 8,          # Minimum volume (8 MANA)
        'base_precision': 0,      # Integer MANA amounts
        'quote_precision': 5,     # USDT precision
    },
    'DOT/USDT': {
        'price_decimals': 4,      # Maximum price precision
        'min_volume': 1.2,        # Minimum volume (1.2 DOT)
        'base_precision': 1,      # DOT precision
        'quote_precision': 4,     # USDT precision
    },
    'LINK/USDT': {
        'price_decimals': 5,      # Maximum price precision
        'min_volume': 0.7,        # Minimum volume (0.7 LINK)
        'base_precision': 1,      # LINK precision
        'quote_precision': 5,     # USDT precision
    },
    'SOL/USDT': {
        'price_decimals': 2,      # Maximum price precision
        'min_volume': 0.02,       # Minimum volume (0.02 SOL)
        'base_precision': 2,      # SOL precision
        'quote_precision': 2,     # USDT precision
    },
    'BTC/USDT': {
        'price_decimals': 1,      # Maximum price precision
        'min_volume': 0.00005,    # Minimum volume (0.00005 BTC)
        'base_precision': 5,      # BTC precision
        'quote_precision': 1,     # USDT precision
    },
}

# Additional important USDT pairs for reference
EXTENDED_PRECISION_CONFIG = {
    'DOGE/USDT': {
        'price_decimals': 5,
        'min_volume': 13,
        'base_precision': 0,
        'quote_precision': 5,
    },
    'ADA/USDT': {
        'price_decimals': 6,
        'min_volume': 4.4,
        'base_precision': 1,
        'quote_precision': 6,
    },
    'AVAX/USDT': {
        'price_decimals': 2,
        'min_volume': 0.5,
        'base_precision': 1,
        'quote_precision': 2,
    },
    'ATOM/USDT': {
        'price_decimals': 4,
        'min_volume': 0.7,
        'base_precision': 1,
        'quote_precision': 4,
    },
}

def get_precision_config(symbol: str) -> dict:
    """Get precision configuration for a trading pair"""
    # Normalize symbol format
    if '/' not in symbol:
        # Handle symbols like SHIBUSD -> SHIB/USDT
        if symbol.endswith('USDT'):
            base = symbol[:-4]
            symbol = f"{base}/USDT"
        elif symbol.endswith('USD'):
            base = symbol[:-3]
            symbol = f"{base}/USDT"

    # Get config
    config = KRAKEN_PRECISION_CONFIG.get(symbol) or EXTENDED_PRECISION_CONFIG.get(symbol)

    if not config:
        # Default safe values for unknown pairs
        return {
            'price_decimals': 5,
            'min_volume': 1.0,
            'base_precision': 2,
            'quote_precision': 5,
        }

    return config

def format_price(price: float, symbol: str) -> str:
    """Format price according to Kraken precision requirements"""
    config = get_precision_config(symbol)
    decimals = config['price_decimals']

    # Truncate (round down) as per Kraken documentation
    multiplier = 10 ** decimals
    truncated_price = int(price * multiplier) / multiplier

    return f"{truncated_price:.{decimals}f}"

def format_volume(volume: float, symbol: str) -> str:
    """Format volume according to Kraken precision requirements"""
    config = get_precision_config(symbol)
    decimals = config['base_precision']

    # Ensure minimum volume
    min_vol = config['min_volume']
    if volume < min_vol:
        volume = min_vol

    # Format with proper precision
    if decimals == 0:
        return str(int(volume))
    else:
        return f"{volume:.{decimals}f}"

def validate_order_params(symbol: str, price: float, volume: float) -> tuple[bool, str]:
    """Validate order parameters against Kraken requirements"""
    config = get_precision_config(symbol)

    # Check minimum volume
    if volume < config['min_volume']:
        return False, f"Volume {volume} below minimum {config['min_volume']} for {symbol}"

    # Check price precision
    price_str = format_price(price, symbol)
    if len(price_str.split('.')[-1]) > config['price_decimals']:
        return False, f"Price precision exceeds {config['price_decimals']} decimals for {symbol}"

    return True, "Valid"

# Quick reference for your bot's main pairs
MAIN_PAIRS_SUMMARY = {
    'SHIB/USDT': 'Price: 8 decimals, Min: 160,000 SHIB',
    'AI16Z/USDT': 'Price: 4 decimals, Min: 5 AI16Z',
    'BERA/USDT': 'Price: 4 decimals, Min: 0.5 BERA',
    'MANA/USDT': 'Price: 5 decimals, Min: 8 MANA',
    'DOT/USDT': 'Price: 4 decimals, Min: 1.2 DOT',
    'LINK/USDT': 'Price: 5 decimals, Min: 0.7 LINK',
    'SOL/USDT': 'Price: 2 decimals, Min: 0.02 SOL',
    'BTC/USDT': 'Price: 1 decimal, Min: 0.00005 BTC',
}
