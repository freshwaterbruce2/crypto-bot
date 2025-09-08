#!/usr/bin/env python3
"""
Kraken-Optimized Trading Configuration
Clean, validated configuration class with Kraken-specific optimizations
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TradingConfig:
    """
    Kraken-optimized trading configuration with validation
    """

    # Core trading pair settings
    pair: str = "XLM/USD"
    kraken_pair: str = "XLM/USD"  # WebSocket v2 format
    description: str = "XLM/USD optimized for Kraken's fee structure"

    # Position sizing (Kraken-specific minimums)
    minimum_order: Decimal = Decimal("24")  # XLM minimum
    max_position_size_xlm: Decimal = Decimal("100")
    max_cost_usd_per_trade: Decimal = Decimal("25.0")
    balance_utilization_pct: Decimal = Decimal("0.75")

    # Profit targets (optimized for Kraken fees)
    profit_target: Decimal = Decimal("0.007")  # 0.7%
    quick_profit: Decimal = Decimal("0.004")  # 0.4%
    quick_profit_window_secs: int = 30
    enable_breakeven_stop: bool = True
    breakeven_arm_pct: Decimal = Decimal("0.003")

    # Risk management
    stop_loss: Decimal = Decimal("-0.004")  # -0.4%
    stale_exit_max_drawdown: Decimal = Decimal("0.0004")
    cooldown_after_loss_secs: int = 15

    # Market conditions
    spread_threshold: Decimal = Decimal("0.05")
    momentum_threshold: Decimal = Decimal("0.05")
    volatility: str = "High"
    volatility_window_minutes: int = 60

    # Execution parameters (Kraken-optimized)
    taker_fee_rate: Decimal = Decimal("0.0026")  # Kraken current taker fee
    maker_fee_rate: Decimal = Decimal("0.0016")  # Kraken current maker fee
    slippage_buffer_rate: Decimal = Decimal("0.001")
    enable_maker_first_quick_tp: bool = True
    min_usd_profit: Decimal = Decimal("0.02")

    # Timing controls
    cooldown_between_entries_secs: Decimal = Decimal("0.3")
    cooldown_after_exit_secs: int = 1
    position_check_interval: int = 3
    deadman_timeout_secs: int = 300  # Kraken's 5-minute limit

    # Advanced features
    enable_trailing_exit: bool = True
    trailing_arm_pct: Decimal = Decimal("0.0025")
    trailing_step_pct: Decimal = Decimal("0.0015")
    enable_size_scaling: bool = True
    scaling_winrate_threshold: int = 45
    scaling_increase_pct: Decimal = Decimal("0.1")
    scaling_max_position_xlm: Decimal = Decimal("100")
    enable_autotune: bool = True
    autotune_window_trades: int = 50

    # WebSocket configuration (Kraken v2 optimized)
    enable_ws_v2: bool = True
    ws_stale_threshold_secs: int = 20
    enable_rest_fallback_on_stale: bool = True
    rest_fallback_delay_secs: int = 60
    rest_fallback_window_secs: int = 120

    # Logging and debugging
    enable_gate_block_logging: bool = True
    debug_trading_signals: bool = True
    debug_market_conditions: bool = True

    # Performance features
    session_bias_enabled: bool = True
    session_bias_spread_relax: Decimal = Decimal("0.00005")
    enable_micro_momentum: bool = True
    micro_momentum_window_secs: int = 6
    enable_volume_confirmation: bool = True
    volume_confirmation_ratio: Decimal = Decimal("1.2")

    # Risk Manager Configuration
    risk_manager_type: str = "enhanced"  # "enhanced" or "basic"
    kelly_fraction: Decimal = Decimal("0.5")  # Conservative Kelly fraction
    performance_score_enabled: bool = True

    # Metadata
    version: str = "2.0"
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: Optional[datetime] = None

    def __post_init__(self):
        """Post-initialization validation and normalization"""
        self._validate_config()
        self._normalize_values()
        # Ensure kraken_pair follows Kraken REST symbol format (e.g., XXLMZUSD)
        if self.kraken_pair == self.pair:
            base, quote = self.pair.split("/", 1)
            if quote == "USD":
                self.kraken_pair = f"X{base}ZUSD"
            else:
                self.kraken_pair = f"X{base}Z{quote}"

    def _validate_config(self):
        """Validate configuration parameters"""
        if self.minimum_order < 0:
            raise ValueError("minimum_order must be positive")

        if self.profit_target <= 0:
            raise ValueError("profit_target must be positive")

        if self.stop_loss >= 0:
            raise ValueError("stop_loss must be negative")

        if self.taker_fee_rate < 0 or self.taker_fee_rate > 1:
            raise ValueError("taker_fee_rate must be between 0 and 1")

        if self.deadman_timeout_secs < 60 or self.deadman_timeout_secs > 600:
            raise ValueError("deadman_timeout_secs must be between 60 and 600 seconds")

        # Risk manager validation
        if self.risk_manager_type not in ["enhanced", "basic"]:
            raise ValueError("risk_manager_type must be 'enhanced' or 'basic'")

        if not (Decimal("0.1") <= self.kelly_fraction <= Decimal("1.0")):
            raise ValueError("kelly_fraction must be between 0.1 and 1.0")

    def _normalize_values(self):
        """Normalize decimal values for precision"""
        # Ensure all Decimal fields maintain precision
        decimal_fields = [
            "minimum_order",
            "max_position_size_xlm",
            "max_cost_usd_per_trade",
            "balance_utilization_pct",
            "profit_target",
            "quick_profit",
            "breakeven_arm_pct",
            "stop_loss",
            "stale_exit_max_drawdown",
            "spread_threshold",
            "momentum_threshold",
            "taker_fee_rate",
            "maker_fee_rate",
            "slippage_buffer_rate",
            "min_usd_profit",
            "cooldown_between_entries_secs",
            "trailing_arm_pct",
            "trailing_step_pct",
            "scaling_increase_pct",
            "scaling_max_position_xlm",
            "session_bias_spread_relax",
            "volume_confirmation_ratio",
            "kelly_fraction",
        ]

        for field_name in decimal_fields:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if isinstance(value, (int, float)):
                    setattr(self, field_name, Decimal(str(value)))

    def update_from_dict(self, config_dict: Dict[str, Any]) -> "TradingConfig":
        """
        Update configuration from dictionary with validation

        Args:
            config_dict: Dictionary containing configuration updates

        Returns:
            Updated TradingConfig instance
        """
        # Create updated config dict
        updated_dict = {}

        # Get current values
        for field_name in self.__dataclass_fields__:
            if field_name != "last_updated":
                updated_dict[field_name] = getattr(self, field_name)

        # Apply updates
        for key, value in config_dict.items():
            if key in self.__dataclass_fields__:
                updated_dict[key] = value

        # Update timestamp
        updated_dict["last_updated"] = datetime.now()

        # Create new instance (this will trigger validation)
        return TradingConfig(**updated_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        result = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if isinstance(value, Decimal):
                result[field_name] = float(value)
            elif isinstance(value, datetime):
                result[field_name] = value.isoformat()
            else:
                result[field_name] = value
        return result

    def get_kraken_fee_adjusted_target(self) -> Decimal:
        """
        Get profit target adjusted for Kraken's fee structure
        Ensures profitability after fees
        """
        # Minimum profitable target accounting for taker fee
        min_profitable = self.taker_fee_rate * Decimal("2")  # Round trip fees

        # Use the higher of configured target or minimum profitable
        return max(
            self.profit_target, min_profitable + Decimal("0.001")
        )  # Add 0.1% buffer

    def get_position_size_limits(self) -> Dict[str, Decimal]:
        """
        Get position size limits optimized for Kraken
        """
        return {
            "min_order": self.minimum_order,
            "max_position": self.max_position_size_xlm,
            "max_cost_usd": self.max_cost_usd_per_trade,
        }

    def is_kraken_optimized(self) -> bool:
        """
        Check if configuration is optimized for Kraken
        """
        checks = [
            self.enable_ws_v2,
            self.deadman_timeout_secs == 300,  # Kraken's 5-minute limit
            self.taker_fee_rate == Decimal("0.0026"),  # Current Kraken taker fee
            self.enable_rest_fallback_on_stale,
            self.ws_stale_threshold_secs <= 20,
        ]

        return all(checks)

    def __str__(self) -> str:
        """String representation for logging"""
        return f"TradingConfig(pair={self.pair}, profit_target={self.profit_target}, stop_loss={self.stop_loss})"
