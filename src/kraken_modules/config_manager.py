"""
Kraken Intelligent Configuration Manager - Modular Architecture Demo

Demonstrates breaking large kraken_exchange.py into focused modules.
"""

import logging
from typing import Dict, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AccountTier(Enum):
    """Kraken account tier levels."""
    STARTER = "starter"
    INTERMEDIATE = "intermediate" 
    PRO = "pro"


@dataclass
class OptimizedConfig:
    """Configuration optimized for proven trading patterns."""
    max_counter: int
    decay_rate: float
    max_open_orders: int
    base_position_percent: float = 3.5  # Based on successful $8.40 trades
    profit_target: float = 0.015  # 1.5%
    min_order_usd: float = 8.0


class KrakenConfigManager:
    """
    INTELLIGENT CONFIGURATION MANAGER
    
    Demonstrates modular approach with intelligent optimization.
    """
    
    def __init__(self, tier: str = "starter", fee_free: bool = True):
        """Initialize with tier-based configuration."""
        self.tier = AccountTier(tier.lower())
        self.fee_free_enabled = fee_free
        self.metrics = {"total_trades": 0, "winning_trades": 0, "win_rate": 0.0}
        self.config = self._create_optimized_config()
        logger.info(f"[CONFIG] Initialized {self.tier.value} tier, fee-free: {fee_free}")

    
    def _create_optimized_config(self) -> OptimizedConfig:
        """Create tier-specific optimized configuration."""
        # Kraken official rate limits per tier
        tier_configs = {
            AccountTier.STARTER: OptimizedConfig(
                max_counter=60, decay_rate=1.0, max_open_orders=60
            ),
            AccountTier.INTERMEDIATE: OptimizedConfig(
                max_counter=125, decay_rate=2.34, max_open_orders=80  
            ),
            AccountTier.PRO: OptimizedConfig(
                max_counter=180, decay_rate=3.75, max_open_orders=225
            )
        }
        
        config = tier_configs[self.tier]
        
        # Fee-free optimizations (leverage the advantage)
        if self.fee_free_enabled:
            config.profit_target *= 0.7  # Lower targets viable without fees
            config.min_order_usd *= 0.6  # Smaller positions profitable
            logger.info("[CONFIG] Fee-free optimizations applied")
            
        return config
    
    def get_config(self) -> Dict[str, Any]:
        """Get current optimized configuration."""
        return {
            "tier": self.tier.value,
            "rate_limits": {
                "max_counter": self.config.max_counter,
                "decay_rate": self.config.decay_rate,
                "max_open_orders": self.config.max_open_orders
            },
            "trading": {
                "position_percent": self.config.base_position_percent,
                "profit_target": self.config.profit_target,
                "min_order_usd": self.config.min_order_usd
            }
        }

    
    def update_performance(self, trades: int, wins: int, profit: float):
        """Update performance metrics and optimize configuration."""
        self.metrics["total_trades"] += trades
        self.metrics["winning_trades"] += wins
        
        if self.metrics["total_trades"] > 0:
            self.metrics["win_rate"] = self.metrics["winning_trades"] / self.metrics["total_trades"]
            
        # Auto-optimize based on performance
        self._auto_optimize()
    
    def _auto_optimize(self):
        """Automatically optimize configuration based on performance."""
        win_rate = self.metrics["win_rate"]
        
        # Proven strategy: If win rate is high, increase position size
        if win_rate > 0.7 and self.metrics["total_trades"] >= 5:
            old_percent = self.config.base_position_percent
            self.config.base_position_percent = min(old_percent * 1.1, 10.0)
            logger.info(f"[AUTO_OPT] Win rate {win_rate:.1%} -> increased position to {self.config.base_position_percent:.1f}%")
            
        # If win rate is low, be more conservative  
        elif win_rate < 0.4 and self.metrics["total_trades"] >= 5:
            self.config.base_position_percent *= 0.9
            logger.info(f"[AUTO_OPT] Win rate {win_rate:.1%} -> decreased position to {self.config.base_position_percent:.1f}%")
    
    def get_symbol_config(self, symbol: str) -> Dict[str, Any]:
        """Get symbol-specific configuration with intelligent defaults."""
        # Extract currencies
        base_currency = symbol.split('/')[0] if '/' in symbol else symbol
        quote_currency = symbol.split('/')[1] if '/' in symbol else 'USD'
        
        # Base configuration
        config = {
            "profit_target": self.config.profit_target,
            "position_multiplier": 1.0,
            "priority": 5
        }
        
        # Currency-specific optimizations based on memory patterns
        if base_currency in ['BTC', 'ETH']:
            config["position_multiplier"] = 1.2  # Higher allocation for liquid pairs
            config["profit_target"] = self.config.profit_target * 0.7  # Lower targets
            
        elif base_currency == 'SHIB':  # Based on successful SHIB trading
            config["position_multiplier"] = 0.8  # Lower allocation for volatile
            config["profit_target"] = self.config.profit_target * 1.5  # Higher targets
            
        # USDT vs USD preference (based on memory showing USDT success)
        if quote_currency == 'USDT':
            config["priority"] = 10
        elif quote_currency == 'USD':
            config["priority"] = 8
            
        return config


# Export for use in other modules
__all__ = ["KrakenConfigManager", "AccountTier", "OptimizedConfig"]
