"""
Kraken Pro Account Configuration
================================

CRITICAL: This configuration is specifically designed for Kraken Pro accounts
with fee-free trading. Standard accounts will lose money with these settings!

Pro Account Benefits:
- 0% trading fees (maker and taker)
- 180 calls/counter rate limit (vs 60 for starter)
- 3.75/s decay rate (vs 1.0/s for starter)
- Priority API access
- Advanced order types
- WebSocket priority

This configuration optimizes for:
1. Micro-scalping with tiny profit margins (0.1-0.3%)
2. Maximum trade frequency (up to 30 trades/minute)
3. Capital velocity optimization
4. Compound growth acceleration
5. Rapid portfolio rebalancing
"""

import logging
from typing import Dict, Any, List
from ..config.constants import PRO_ACCOUNT_OPTIMIZATIONS, INFINITY_LOOP_CONFIG

logger = logging.getLogger(__name__)


class ProAccountOptimizer:
    """Pro Account Configuration Optimizer"""
    
    def __init__(self):
        self.pro_features_enabled = False
        self.optimization_level = "maximum"  # conservative, moderate, maximum
        
    def get_pro_optimized_config(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get Pro account optimized configuration
        
        WARNING: Only use with Kraken Pro accounts (fee-free trading)
        """
        
        # Verify Pro account requirement
        api_tier = base_config.get('kraken_api_tier', 'starter')
        if api_tier != 'pro':
            logger.error("ERROR: Pro account optimizations require Kraken Pro tier")
            raise ValueError("Pro account optimizations require Kraken Pro tier")
        
        logger.info("[PRO_OPTIMIZER] Configuring for Kraken Pro account - Fee-free trading enabled")
        
        # Base optimized config
        pro_config = base_config.copy()
        
        # ==================================================
        # CORE PRO ACCOUNT OPTIMIZATIONS
        # ==================================================
        
        # Trading parameters (fee-free optimized)
        pro_config.update({
            # CRITICAL: Kraken requires $2 minimum for TIER-1 pairs - this applies to ALL accounts
            'min_order_size_usdt': 2.0,         # Kraken TIER-1 minimum requirement
            'position_size_usdt': 3.5,          # Optimized for $5 balance
            'tier_1_trade_limit': 50.0,         # Much higher limit
            
            # Micro-scalping profit targets (impossible with fees)
            'min_profit_target_pct': 0.001,     # 0.1% minimum
            'default_profit_target_pct': 0.003, # 0.3% default
            'max_profit_target_pct': 0.005,     # 0.5% maximum
            
            # Ultra-tight stop losses (free exits)
            'min_stop_loss_pct': 0.0008,        # 0.08% minimum (ENHANCED)
            'default_stop_loss_pct': 0.002,     # 0.2% default (TIGHTER)
            'max_stop_loss_pct': 0.005,         # 0.5% maximum (REDUCED)
            
            # Position management (aggressive)
            'max_positions': 20,                # More concurrent positions
            'max_position_size_pct': 0.15,      # 15% of portfolio
            'min_position_size_pct': 0.005,     # 0.5% minimum
            
            # Timing (high frequency)
            'min_hold_time_seconds': 10,        # 10 seconds minimum
            'max_hold_time_seconds': 120,       # 2 minutes maximum
            'signal_cooldown_seconds': 1,       # 1 second between signals
            
            # Rate limiting (Pro tier specifications)
            'rate_limit_threshold': 180,        # Pro tier: 180 calls/counter
            'rate_decay_per_second': 3.75,      # Pro tier: 3.75/s decay
            'burst_allowance_multiplier': 1.2,  # 20% burst capacity
            
            # Fee-free specific features
            'fee_free_trading': True,
            'micro_scalping_enabled': True,
            'capital_velocity_mode': True,
            'compound_growth_optimization': True,
            'rapid_rebalancing_enabled': True,
        })
        
        # ==================================================
        # TRADING STRATEGY CONFIGURATION
        # ==================================================
        
        pro_config['trading_strategy'] = {
            'primary_strategy': 'pro_fee_free_micro_scalper',
            'strategy_parameters': {
                'ultra_micro_threshold': 0.001,     # 0.1% ultra-micro
                'micro_threshold': 0.002,           # 0.2% micro  
                'mini_scalp_threshold': 0.003,      # 0.3% mini-scalp
                'max_trades_per_minute': 30,        # High frequency
                'capital_velocity_target': 10.0,    # 10x daily velocity
                'position_size_multiplier': 1.5,    # 50% larger positions
                'stop_loss_aggressiveness': 2.0,    # 2x more aggressive
            }
        }
        
        # ==================================================
        # TRADING PAIRS (ALL PAIRS FOR PRO ACCOUNTS)
        # ==================================================
        
        # Pro accounts can trade all pairs due to fee-free advantage
        pro_config['trading_pairs'] = self._get_pro_optimized_pairs()
        pro_config['avoid_pairs'] = []  # Pro accounts avoid no pairs
        
        # ==================================================
        # EXECUTION PARAMETERS
        # ==================================================
        
        pro_config['execution'] = {
            'order_type': 'limit',              # IOC limit orders for Pro
            'use_ioc_orders': True,             # Immediate-or-cancel
            'slippage_tolerance': 0.05,         # Tighter tolerance
            'execution_delay_ms': 50,           # Faster execution
            'retry_attempts': 3,                # More retries
            'timeout_seconds': 10,              # Shorter timeout
        }
        
        # ==================================================
        # RISK MANAGEMENT (OPTIMIZED FOR FEE-FREE)
        # ==================================================
        
        pro_config['risk_management'] = {
            'max_daily_loss_pct': 3.0,          # Lower due to higher frequency
            'circuit_breaker_threshold': 2.0,   # More sensitive
            'position_correlation_limit': 0.7,  # Manage correlation
            'drawdown_alert_threshold': 1.5,    # Early warning
            'rebalance_frequency_minutes': 5,   # Frequent rebalancing
        }
        
        # ==================================================
        # PERFORMANCE MONITORING
        # ==================================================
        
        pro_config['performance_tracking'] = {
            'track_micro_profits': True,
            'calculate_capital_velocity': True,
            'monitor_compound_growth': True,
            'log_fee_savings': True,
            'benchmark_against_fees': True,
        }
        
        # ==================================================
        # INFINITY LOOP OPTIMIZATION
        # ==================================================
        
        pro_config['infinity_loop'] = {
            'scan_interval_seconds': 2,         # Faster scanning
            'batch_window_seconds': 1,          # Faster batching  
            'max_signals_per_batch': 20,        # More signals
            'capital_deployment_target': 0.95,  # 95% deployment
            'rebalance_threshold': 0.98,        # Aggressive rebalancing
            'micro_scalping_mode': True,
            'fee_free_advantage': True,
        }
        
        self.pro_features_enabled = True
        logger.info(f"[PRO_OPTIMIZER] Configuration optimized for Pro account:")
        logger.info(f"  - Fee-free trading: ENABLED")
        logger.info(f"  - Micro-scalping: ENABLED (0.1-0.5% targets)")
        logger.info(f"  - High frequency: {pro_config['trading_strategy']['strategy_parameters']['max_trades_per_minute']} trades/min")
        logger.info(f"  - Capital velocity: {pro_config['trading_strategy']['strategy_parameters']['capital_velocity_target']}x daily")
        logger.info(f"  - Trading pairs: {len(pro_config['trading_pairs'])} pairs enabled")
        
        return pro_config
    
    def _get_pro_optimized_pairs(self) -> List[str]:
        """Get all trading pairs optimized for Pro accounts"""
        
        # Pro accounts can trade ALL pairs due to fee-free advantage
        # No need to avoid high-minimum pairs since there are no fees
        return [
            # Major pairs
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT", "DOT/USDT",
            
            # DeFi and Layer 1
            "LINK/USDT", "MATIC/USDT", "ADA/USDT", "ALGO/USDT", "ATOM/USDT",
            
            # Newer/trending assets
            "AI16Z/USDT", "BERA/USDT", "MANA/USDT", "APE/USDT",
            
            # High volume pairs
            "SHIB/USDT", "DOGE/USDT", "BCH/USDT", "BNB/USDT", "CRO/USDT",
            
            # Additional opportunities (Pro accounts only)
            "XRP/USDT", "LTC/USDT", "UNI/USDT", "AAVE/USDT", "COMP/USDT",
            "MKR/USDT", "SNX/USDT", "YFI/USDT", "SUSHI/USDT", "BAL/USDT"
        ]
    
    def get_fee_savings_projection(self, daily_volume: float) -> Dict[str, float]:
        """
        Calculate projected fee savings for Pro account
        
        Args:
            daily_volume: Estimated daily trading volume in USDT
            
        Returns:
            Dictionary with fee savings projections
        """
        
        # Standard Kraken fees (without Pro)
        maker_fee = 0.0016  # 0.16%
        taker_fee = 0.0026  # 0.26%
        avg_fee = (maker_fee + taker_fee) / 2  # 0.21% average
        
        # Calculate savings
        daily_fee_savings = daily_volume * avg_fee
        monthly_fee_savings = daily_fee_savings * 30
        yearly_fee_savings = daily_fee_savings * 365
        
        return {
            'daily_volume_usdt': daily_volume,
            'avg_fee_rate': avg_fee,
            'daily_fee_savings': daily_fee_savings,
            'monthly_fee_savings': monthly_fee_savings,
            'yearly_fee_savings': yearly_fee_savings,
            'break_even_volume': 100,  # Volume needed to justify Pro subscription
        }
    
    def validate_pro_account_requirements(self, config: Dict[str, Any]) -> bool:
        """Validate that Pro account requirements are met"""
        
        required_settings = [
            ('kraken_api_tier', 'pro'),
            ('fee_free_trading', True),
        ]
        
        for setting, expected_value in required_settings:
            if config.get(setting) != expected_value:
                logger.error(f"[PRO_VALIDATOR] Missing requirement: {setting} = {expected_value}")
                return False
        
        logger.info("[PRO_VALIDATOR] All Pro account requirements validated")
        return True
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of Pro account optimizations"""
        
        if not self.pro_features_enabled:
            return {"error": "Pro features not enabled"}
        
        return {
            "pro_account_optimizations": {
                "fee_free_trading": True,
                "micro_scalping_enabled": True,
                "capital_velocity_mode": True,
                "compound_growth_optimization": True,
                "rapid_rebalancing": True,
            },
            "performance_advantages": {
                "min_profit_target": "0.1% (vs 0.5% for standard)",
                "max_trades_per_minute": "30 (vs 10 for standard)",
                "capital_velocity_target": "10x daily (vs 3x for standard)",
                "position_size_multiplier": "1.5x (vs 1.0x for standard)",
                "stop_loss_aggressiveness": "2x tighter (free exits)",
            },
            "rate_limit_advantages": {
                "threshold": "180 calls/counter (vs 60 for starter)",
                "decay_rate": "3.75/s (vs 1.0/s for starter)", 
                "burst_allowance": "20% higher capacity",
                "priority_access": True,
            },
            "trading_pair_advantages": {
                "total_pairs_available": "25+ pairs",
                "avoided_pairs": "None (fee-free allows all)",
                "high_minimum_pairs_enabled": True,
            }
        }


# Global Pro account optimizer instance
pro_optimizer = ProAccountOptimizer()


def get_pro_optimized_config(base_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get Pro account optimized configuration (convenience function)"""
    return pro_optimizer.get_pro_optimized_config(base_config)


def validate_pro_account(config: Dict[str, Any]) -> bool:
    """Validate Pro account configuration (convenience function)"""
    return pro_optimizer.validate_pro_account_requirements(config)