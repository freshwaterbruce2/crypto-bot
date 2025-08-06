"""
Paper Trading Configuration
Controls paper trading mode settings and behavior
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

@dataclass
class PaperTradingConfig:
    """Configuration for paper trading mode"""

    # Core settings
    enabled: bool = True
    starting_balance: float = 1000.0  # Starting USDT for paper trading
    simulate_real_fees: bool = True
    simulate_slippage: bool = True
    use_real_market_data: bool = True  # Use live prices from Kraken

    # Performance tracking
    track_performance: bool = True
    save_trades: bool = True
    generate_reports: bool = True
    report_interval: int = 3600  # Generate reports every hour

    # Risk simulation
    simulate_network_delays: bool = True
    simulate_order_failures: bool = True
    order_failure_rate: float = 0.02  # 2% of orders fail (realistic)
    network_delay_range: tuple = (0.1, 0.5)  # 100-500ms delays

    # Kraken fee structure - FEE-FREE TRADING ACCOUNT
    maker_fee: float = 0.0000  # Fee-free trading
    taker_fee: float = 0.0000  # Fee-free trading

    # Slippage simulation
    max_slippage: float = 0.001  # 0.1% max slippage
    slippage_probability: float = 0.3  # 30% chance of slippage

    # File paths
    data_dir: Optional[Path] = None
    trades_file: Optional[Path] = None
    performance_file: Optional[Path] = None
    reports_dir: Optional[Path] = None

    def __post_init__(self):
        """Initialize file paths if not provided"""
        if self.data_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.data_dir = project_root / "paper_trading_data"

        # Ensure directory exists
        self.data_dir.mkdir(exist_ok=True)

        # Set file paths
        if self.trades_file is None:
            self.trades_file = self.data_dir / "paper_trades.json"

        if self.performance_file is None:
            self.performance_file = self.data_dir / "paper_performance.json"

        if self.reports_dir is None:
            self.reports_dir = self.data_dir / "reports"
            self.reports_dir.mkdir(exist_ok=True)

    @classmethod
    def from_env(cls) -> 'PaperTradingConfig':
        """Load configuration from environment variables"""
        return cls(
            enabled=os.getenv('PAPER_TRADING_ENABLED', 'true').lower() == 'true',
            starting_balance=float(os.getenv('PAPER_STARTING_BALANCE', '1000.0')),
            simulate_real_fees=os.getenv('PAPER_SIMULATE_FEES', 'true').lower() == 'true',
            simulate_slippage=os.getenv('PAPER_SIMULATE_SLIPPAGE', 'true').lower() == 'true',
            use_real_market_data=os.getenv('PAPER_USE_REAL_DATA', 'true').lower() == 'true',
            track_performance=os.getenv('PAPER_TRACK_PERFORMANCE', 'true').lower() == 'true'
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'enabled': self.enabled,
            'starting_balance': self.starting_balance,
            'simulate_real_fees': self.simulate_real_fees,
            'simulate_slippage': self.simulate_slippage,
            'use_real_market_data': self.use_real_market_data,
            'track_performance': self.track_performance,
            'save_trades': self.save_trades,
            'generate_reports': self.generate_reports,
            'report_interval': self.report_interval,
            'simulate_network_delays': self.simulate_network_delays,
            'simulate_order_failures': self.simulate_order_failures,
            'order_failure_rate': self.order_failure_rate,
            'network_delay_range': self.network_delay_range,
            'maker_fee': self.maker_fee,
            'taker_fee': self.taker_fee,
            'max_slippage': self.max_slippage,
            'slippage_probability': self.slippage_probability
        }

    def log_config(self):
        """Log current configuration"""
        logger.info("🧪 PAPER TRADING CONFIGURATION")
        logger.info(f"   Enabled: {self.enabled}")
        logger.info(f"   Starting Balance: ${self.starting_balance:,.2f}")
        logger.info(f"   Simulate Fees: {self.simulate_real_fees}")
        logger.info(f"   Simulate Slippage: {self.simulate_slippage}")
        logger.info(f"   Use Real Market Data: {self.use_real_market_data}")
        logger.info(f"   Track Performance: {self.track_performance}")
        logger.info(f"   Data Directory: {self.data_dir}")


# Global configuration instance
_config = None

def get_paper_config() -> PaperTradingConfig:
    """Get the global paper trading configuration"""
    global _config
    if _config is None:
        _config = PaperTradingConfig.from_env()
    return _config

def set_paper_config(config: PaperTradingConfig):
    """Set the global paper trading configuration"""
    global _config
    _config = config

def is_paper_trading_enabled() -> bool:
    """Check if paper trading is enabled"""
    return get_paper_config().enabled
