"""
Fee-Free Trading Configuration
Optimized settings for Kraken fee-free accounts
"""

import os

from .paper_config import PaperTradingConfig


class FeeFreeTradingConfig(PaperTradingConfig):
    """Configuration optimized for fee-free Kraken trading"""

    def __init__(self, **kwargs):
        # Override defaults for fee-free trading
        defaults = {
            'simulate_real_fees': False,  # No fees to simulate
            'maker_fee': 0.0000,
            'taker_fee': 0.0000,
            'starting_balance': 1000.0,
            'simulate_slippage': True,  # Still simulate slippage
            'max_slippage': 0.0005,  # Reduce max slippage (0.05%)
            'slippage_probability': 0.2,  # Lower probability
        }

        # Merge with any provided kwargs
        defaults.update(kwargs)
        super().__init__(**defaults)

    @classmethod
    def from_env(cls) -> 'FeeFreeTradingConfig':
        """Load fee-free configuration from environment"""
        return cls(
            enabled=os.getenv('PAPER_TRADING_ENABLED', 'true').lower() == 'true',
            starting_balance=float(os.getenv('PAPER_STARTING_BALANCE', '1000.0')),
            simulate_real_fees=False,  # Always false for fee-free
            simulate_slippage=os.getenv('PAPER_SIMULATE_SLIPPAGE', 'true').lower() == 'true',
            use_real_market_data=os.getenv('PAPER_USE_REAL_DATA', 'true').lower() == 'true',
            track_performance=os.getenv('PAPER_TRACK_PERFORMANCE', 'true').lower() == 'true'
        )

    def log_config(self):
        """Log fee-free specific configuration"""
        print("🆓 FEE-FREE TRADING CONFIGURATION")
        print("=" * 50)
        print(f"   Enabled: {self.enabled}")
        print(f"   Starting Balance: ${self.starting_balance:,.2f}")
        print("   Fee-Free Trading: ✅ ENABLED")
        print(f"   Maker Fee: {self.maker_fee:.4f}% (FREE)")
        print(f"   Taker Fee: {self.taker_fee:.4f}% (FREE)")
        print(f"   Simulate Slippage: {self.simulate_slippage}")
        print(f"   Use Real Market Data: {self.use_real_market_data}")
        print("   ")
        print("🎯 ADVANTAGES:")
        print("   • Every profitable signal = pure profit")
        print("   • No minimum profit threshold needed")
        print("   • High-frequency strategies viable")
        print("   • Position scaling without penalty")
        print("=" * 50)

def get_fee_free_config():
    """Get fee-free trading configuration"""
    return FeeFreeTradingConfig.from_env()
