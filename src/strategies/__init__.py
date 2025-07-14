"""
Strategies Package - USDT Trading Optimized

This package contains all trading strategies for the Kraken trading bot,
optimized for high-frequency USDT pair micro-profit trading.
"""

# NumPy 2.x compatibility - MUST be loaded first
try:
    from .. import numpy_compat
except ImportError:
    try:
        import sys
        sys.path.insert(0, '..')
        import numpy_compat
    except ImportError:
        pass

# Import all strategy classes for easy access
from .base_strategy import BaseStrategy
from .autonomous_sell_engine import AutonomousSellEngine, SellEngineConfig
from .fast_start_strategy import FastStartStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .rsi_macd_strategy import RsiMacdStrategy
from .micro_scalper_strategy import MicroScalperStrategy
from .quantum_fluctuation_scalper import QuantumFluctuationScalper
from .asset_config_loader import AssetConfigLoader

# Import portfolio intelligence components if available
try:
    from .portfolio_aware_strategy import PortfolioAwareStrategy
except ImportError:
    PortfolioAwareStrategy = None

# Import buy/sell separation logic if available
try:
    from .buy_logic_handler import BuyLogicHandler
    from .sell_logic_handler import SellLogicHandler
except ImportError:
    BuyLogicHandler = None
    SellLogicHandler = None

__all__ = [
    "BaseStrategy",
    "AutonomousSellEngine", 
    "SellEngineConfig",
    "FastStartStrategy",
    "MeanReversionStrategy",
    "RsiMacdStrategy",
    "MicroScalperStrategy",
    "QuantumFluctuationScalper",
    "AssetConfigLoader",
    "PortfolioAwareStrategy",
    "BuyLogicHandler",
    "SellLogicHandler"
]

# Strategy version for compatibility checking
STRATEGY_VERSION = "2.0.0"  # Major update for USDT optimization
