"""
Trading Configuration Manager
Handles trading-specific parameters and optimization with API protection
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class TradingConfig:
    """Simple trading configuration class for validation"""
    
    def __init__(self):
        """Initialize with default trading configuration"""
        self.pairs = [
            "SHIB/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT", 
            "AVAX/USDT", "DOT/USDT", "LINK/USDT", "MATIC/USDT"
        ]
        self.position_size_usdt = 4.2
        self.profit_target_pct = 0.2
        self.stop_loss_pct = 0.15
        self.strategy = "pro_fee_free_micro_scalper"
        self.max_hold_time_minutes = 5


class TradingConfigManager:
    """Trading configuration manager"""
    
    def __init__(self, core_config: Dict[str, Any]):
        """Initialize trading config manager"""
        self.core_config = core_config
        self.trading_config = self._get_trading_defaults()
    
    def _get_trading_defaults(self) -> Dict[str, Any]:
        """Get default trading configuration"""
        # Detect Pro account tier from core config
        api_tier = self.core_config.get("kraken_api_tier", "starter")
        is_pro_account = api_tier == "pro"
        
        base_config = {
            # Position sizing (Neural optimized based on 65.7% accuracy improvement)
            "position_size_usdt": self.core_config.get("position_size_usdt", 4.2 if is_pro_account else 2.4),
            "tier_1_trade_limit": self.core_config.get("tier_1_trade_limit", 55.0 if is_pro_account else 2.4),
            "min_order_size_usdt": self.core_config.get("min_order_size_usdt", 2.0),  # Kraken requires $2 minimum for TIER-1
            
            # Trading strategy (Pro fee-free optimized)
            "strategy": "pro_fee_free_micro_scalper" if is_pro_account else "standard_scalper",
            "profit_target_pct": 0.2 if is_pro_account else 0.5,  # Tiny profits for Pro
            "stop_loss_pct": 0.15 if is_pro_account else 0.3,     # Tighter stops for Pro
            "max_hold_time_minutes": 5 if is_pro_account else 30, # Faster scalping for Pro
            
            # Pairs - Pro accounts can trade all pairs due to fee-free advantage
            "trading_pairs": self.core_config.get("trading_pairs", 
                # Pro account: All available pairs for maximum opportunity
                [
                    "BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT", "DOT/USDT", 
                    "LINK/USDT", "MATIC/USDT", "ADA/USDT", "ALGO/USDT", "ATOM/USDT",
                    "AI16Z/USDT", "BERA/USDT", "MANA/USDT", "SHIB/USDT", "DOGE/USDT",
                    "APE/USDT", "BCH/USDT", "BNB/USDT", "CRO/USDT"
                ] if is_pro_account else [
                    # Standard account: Low minimum pairs only
                    "BTC/USDT", "SOL/USDT", "DOT/USDT", "LINK/USDT",
                    "MATIC/USDT", "AI16Z/USDT", "BERA/USDT", "MANA/USDT", "SHIB/USDT"
                ]
            ),
            
            # Avoid pairs (Pro accounts avoid nothing due to fee-free trading)
            "avoid_pairs": [] if is_pro_account else [
                "ADA/USDT", "ALGO/USDT", "ATOM/USDT", "AVAX/USDT", 
                "APE/USDT", "BCH/USDT", "BNB/USDT", "CRO/USDT", "DOGE/USDT"
            ],
            
            # Execution (Pro optimized)
            "order_type": "limit" if is_pro_account else "market",  # Pro: IOC limit orders
            "slippage_tolerance": 0.05 if is_pro_account else 0.1,  # Tighter for Pro
            "execution_delay_ms": 50 if is_pro_account else 100,    # Faster execution
            
            # Pro account specific features
            "fee_free_trading": is_pro_account,
            "micro_scalping_enabled": is_pro_account,
            "max_trades_per_minute": 30 if is_pro_account else 10,
            "capital_velocity_mode": is_pro_account,
            "compound_growth_optimization": is_pro_account,
            
            # API Protection Settings (2025 Enhancement)
            "api_protection_enabled": True,
            "comprehensive_rate_limiting": True,
            "circuit_breaker_protection": True,
            "emergency_mode_threshold": 5,  # consecutive errors before emergency mode
            "nonce_collision_prevention": True,
            "api_health_monitoring": True,
            
            # Balance API specific protection
            "balance_api_rate_limit": 1.0,    # 1 second between balance calls
            "balance_retry_attempts": 3,      # retry attempts for balance calls
            "balance_timeout_seconds": 30,    # timeout for balance calls
        }
        
        return base_config
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all trading settings"""
        return self.trading_config
    
    def get_trading_pairs(self) -> List[str]:
        """Get trading pairs"""
        return self.trading_config["trading_pairs"]
    
    def get_position_size(self) -> float:
        """Get position size in USDT"""
        return self.trading_config["position_size_usdt"]