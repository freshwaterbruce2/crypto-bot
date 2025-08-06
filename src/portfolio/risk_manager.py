"""
Risk Manager
============

Comprehensive risk assessment and management system with position limits,
drawdown monitoring, volatility tracking, and automated risk controls.

Features:
- Real-time risk metric calculation (VaR, Sharpe ratio, drawdown)
- Position size limits and exposure controls
- Volatility-based position sizing
- Drawdown protection and circuit breakers
- Correlation-based risk assessment
- Risk budgeting and allocation
- Automated risk limit enforcement
"""

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from enum import Enum
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .position_tracker import PositionTracker

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAction(Enum):
    """Risk action enumeration"""
    ALLOW = "allow"
    WARN = "warn"
    LIMIT = "limit"
    BLOCK = "block"
    LIQUIDATE = "liquidate"


@dataclass
class RiskLimits:
    """Risk limits configuration"""
    # Portfolio limits
    max_portfolio_risk_pct: float = 2.0  # Maximum portfolio risk percentage
    max_single_position_pct: float = 20.0  # Maximum single position as % of portfolio
    max_symbol_exposure_pct: float = 30.0  # Maximum exposure to single symbol
    max_correlation_exposure: float = 0.5  # Maximum correlation-based exposure

    # Drawdown limits
    max_daily_drawdown_pct: float = 5.0  # Maximum daily drawdown
    max_total_drawdown_pct: float = 15.0  # Maximum total drawdown
    max_consecutive_losses: int = 5  # Maximum consecutive losing trades

    # Position limits
    max_positions: int = 20  # Maximum concurrent positions
    max_position_size_usd: float = 1000.0  # Maximum position size in USD
    min_position_size_usd: float = 1.0  # Minimum position size in USD

    # Leverage and margin
    max_leverage: float = 1.0  # Maximum leverage (1.0 = no leverage)
    margin_call_threshold: float = 0.8  # Margin call at 80% maintenance

    # Time-based limits
    max_trades_per_hour: int = 100  # Maximum trades per hour
    max_trades_per_day: int = 1000  # Maximum trades per day
    cooling_period_minutes: int = 5  # Cooling period after risk violation

    # Volatility limits
    max_position_volatility: float = 0.05  # Maximum position volatility (5%)
    volatility_lookback_hours: int = 24  # Volatility calculation lookback

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class RiskMetrics:
    """Risk metrics data structure"""
    timestamp: float

    # Portfolio metrics
    total_exposure: float
    portfolio_value: float
    available_capital: float
    capital_utilization_pct: float

    # Risk metrics
    portfolio_var_95: float  # 95% Value at Risk
    portfolio_var_99: float  # 99% Value at Risk
    expected_shortfall: float  # Conditional VaR
    max_drawdown_pct: float
    current_drawdown_pct: float

    # Performance metrics
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float

    # Volatility metrics
    portfolio_volatility: float
    avg_position_volatility: float
    volatility_scaled_exposure: float

    # Position metrics
    active_positions: int
    largest_position_pct: float
    concentration_risk: float

    # Risk level
    overall_risk_level: RiskLevel
    risk_score: float  # 0-100 risk score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['overall_risk_level'] = self.overall_risk_level.value
        return data


class RiskManager:
    """
    Comprehensive risk management system
    """

    def __init__(self, position_tracker: PositionTracker, balance_manager=None,
                 limits: Optional[RiskLimits] = None, data_path: str = "D:/trading_data"):
        """
        Initialize risk manager
        
        Args:
            position_tracker: Position tracker instance
            balance_manager: Balance manager instance
            limits: Risk limits configuration
            data_path: Data storage path
        """
        self.position_tracker = position_tracker
        self.balance_manager = balance_manager
        self.limits = limits or RiskLimits()
        self.data_path = data_path

        # Risk state
        self._lock = RLock()
        self._async_lock = asyncio.Lock()

        # Risk tracking
        self._risk_metrics_history: deque = deque(maxlen=1000)
        self._portfolio_value_history: deque = deque(maxlen=1000)
        self._drawdown_history: deque = deque(maxlen=100)

        # Trade tracking for limits
        self._hourly_trade_count: deque = deque(maxlen=60)  # Last 60 minutes
        self._daily_trade_count: deque = deque(maxlen=24)   # Last 24 hours
        self._last_trade_times: List[float] = []

        # Risk violations
        self._risk_violations: List[Dict[str, Any]] = []
        self._cooling_off_until: float = 0.0

        # Peak tracking for drawdown
        self._peak_portfolio_value: float = 0.0
        self._peak_timestamp: float = 0.0

        # Volatility tracking
        self._price_history: Dict[str, deque] = {}
        self._volatility_cache: Dict[str, Tuple[float, float]] = {}  # symbol -> (volatility, timestamp)

        # Files
        self.risk_file = f"{data_path}/risk_metrics.json"
        self.violations_file = f"{data_path}/risk_violations.json"

        logger.info("[RISK_MANAGER] Initialized risk management system")

    async def initialize(self) -> bool:
        """Initialize the risk manager"""
        try:
            async with self._async_lock:
                # Load historical data
                await self._load_risk_history()
                await self._load_violations()

                # Initialize peak tracking
                if self.balance_manager:
                    current_balance = await self._get_current_portfolio_value()
                    self._peak_portfolio_value = current_balance
                    self._peak_timestamp = time.time()

                logger.info("[RISK_MANAGER] Risk manager initialized successfully")
                return True

        except Exception as e:
            logger.error(f"[RISK_MANAGER] Initialization failed: {e}")
            return False

    async def calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        async with self._async_lock:
            try:
                # Get current portfolio state
                portfolio_summary = self.position_tracker.get_portfolio_summary()
                current_value = await self._get_current_portfolio_value()

                # Update peak and drawdown
                if current_value > self._peak_portfolio_value:
                    self._peak_portfolio_value = current_value
                    self._peak_timestamp = time.time()

                current_drawdown = self._calculate_current_drawdown(current_value)
                max_drawdown = self._calculate_max_drawdown()

                # Calculate VaR and risk metrics
                var_95, var_99 = self._calculate_var(current_value)
                expected_shortfall = self._calculate_expected_shortfall(current_value)

                # Performance metrics
                sharpe_ratio = self._calculate_sharpe_ratio()
                sortino_ratio = self._calculate_sortino_ratio()
                calmar_ratio = self._calculate_calmar_ratio()
                win_rate = self._calculate_win_rate()

                # Volatility metrics
                portfolio_volatility = self._calculate_portfolio_volatility()
                avg_position_volatility = self._calculate_average_position_volatility()

                # Position metrics
                active_positions = portfolio_summary['total_positions']
                largest_position_pct = self._calculate_largest_position_percentage(current_value)
                concentration_risk = self._calculate_concentration_risk()

                # Overall risk assessment
                risk_score = self._calculate_risk_score(
                    current_drawdown, max_drawdown, portfolio_volatility,
                    concentration_risk, active_positions
                )
                risk_level = self._determine_risk_level(risk_score)

                # Create metrics object
                metrics = RiskMetrics(
                    timestamp=time.time(),
                    total_exposure=portfolio_summary['total_value'],
                    portfolio_value=current_value,
                    available_capital=current_value - portfolio_summary['total_value'],
                    capital_utilization_pct=(portfolio_summary['total_value'] / current_value) * 100 if current_value > 0 else 0,
                    portfolio_var_95=var_95,
                    portfolio_var_99=var_99,
                    expected_shortfall=expected_shortfall,
                    max_drawdown_pct=max_drawdown,
                    current_drawdown_pct=current_drawdown,
                    sharpe_ratio=sharpe_ratio,
                    sortino_ratio=sortino_ratio,
                    calmar_ratio=calmar_ratio,
                    win_rate=win_rate,
                    portfolio_volatility=portfolio_volatility,
                    avg_position_volatility=avg_position_volatility,
                    volatility_scaled_exposure=portfolio_summary['total_value'] * portfolio_volatility,
                    active_positions=active_positions,
                    largest_position_pct=largest_position_pct,
                    concentration_risk=concentration_risk,
                    overall_risk_level=risk_level,
                    risk_score=risk_score
                )

                # Store metrics
                self._risk_metrics_history.append(metrics)
                self._portfolio_value_history.append((time.time(), current_value))

                # Save to file
                await self._save_risk_metrics(metrics)

                return metrics

            except Exception as e:
                logger.error(f"[RISK_MANAGER] Error calculating risk metrics: {e}")
                raise

    async def check_position_risk(self, symbol: str, size: float, price: float,
                                 position_type: str = "long") -> Tuple[RiskAction, str]:
        """
        Check if a position meets risk requirements
        
        Returns:
            Tuple of (action, reason)
        """
        try:
            # Check if in cooling period
            if time.time() < self._cooling_off_until:
                remaining = int(self._cooling_off_until - time.time())
                return RiskAction.BLOCK, f"Risk cooling period active ({remaining}s remaining)"

            # Calculate position value
            position_value = size * price
            current_portfolio_value = await self._get_current_portfolio_value()

            # Check position size limits
            if position_value > self.limits.max_position_size_usd:
                return RiskAction.BLOCK, f"Position size ${position_value:.2f} exceeds max ${self.limits.max_position_size_usd}"

            if position_value < self.limits.min_position_size_usd:
                return RiskAction.BLOCK, f"Position size ${position_value:.2f} below min ${self.limits.min_position_size_usd}"

            # Check portfolio percentage
            position_pct = (position_value / current_portfolio_value) * 100 if current_portfolio_value > 0 else 0
            if position_pct > self.limits.max_single_position_pct:
                return RiskAction.BLOCK, f"Position {position_pct:.1f}% exceeds max {self.limits.max_single_position_pct}%"

            # Check symbol exposure
            current_exposure = self._get_symbol_exposure(symbol)
            total_exposure_pct = ((current_exposure + position_value) / current_portfolio_value) * 100 if current_portfolio_value > 0 else 0
            if total_exposure_pct > self.limits.max_symbol_exposure_pct:
                return RiskAction.LIMIT, f"Symbol exposure {total_exposure_pct:.1f}% exceeds max {self.limits.max_symbol_exposure_pct}%"

            # Check maximum positions
            open_positions = len(self.position_tracker.get_all_open_positions())
            if open_positions >= self.limits.max_positions:
                return RiskAction.BLOCK, f"Maximum positions ({self.limits.max_positions}) reached"

            # Check trade frequency limits
            trade_frequency_action = self._check_trade_frequency()
            if trade_frequency_action != RiskAction.ALLOW:
                return trade_frequency_action, "Trade frequency limits exceeded"

            # Check volatility limits
            symbol_volatility = await self._get_symbol_volatility(symbol)
            if symbol_volatility > self.limits.max_position_volatility:
                return RiskAction.WARN, f"High volatility {symbol_volatility:.3f} > {self.limits.max_position_volatility:.3f}"

            # Check drawdown limits
            current_metrics = await self.calculate_risk_metrics()
            if current_metrics.current_drawdown_pct > self.limits.max_daily_drawdown_pct:
                return RiskAction.LIMIT, f"Daily drawdown {current_metrics.current_drawdown_pct:.1f}% exceeds limit"

            # All checks passed
            return RiskAction.ALLOW, "Position approved"

        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error checking position risk: {e}")
            return RiskAction.BLOCK, f"Risk check error: {str(e)}"

    async def calculate_optimal_position_size(self, symbol: str, price: float,
                                            volatility: float = None,
                                            confidence: float = 0.95) -> Dict[str, Any]:
        """
        Calculate optimal position size based on risk management principles
        
        Args:
            symbol: Trading symbol
            price: Current price
            volatility: Symbol volatility (calculated if not provided)
            confidence: Confidence level for risk calculation
            
        Returns:
            Dict with position sizing recommendations
        """
        try:
            # SECURITY FIX: Validate price to prevent division by zero
            if price <= 0:
                logger.error(f"[RISK_MANAGER] Invalid price {price} for {symbol} - cannot calculate position size")
                return {
                    'error': f'Invalid price {price} for position sizing',
                    'symbol': symbol,
                    'current_price': price
                }

            current_portfolio_value = await self._get_current_portfolio_value()

            # SECURITY FIX: Validate portfolio value
            if current_portfolio_value <= 0:
                logger.error(f"[RISK_MANAGER] Invalid portfolio value {current_portfolio_value} - cannot calculate position size")
                return {
                    'error': f'Invalid portfolio value {current_portfolio_value}',
                    'symbol': symbol,
                    'current_price': price
                }

            if volatility is None:
                volatility = await self._get_symbol_volatility(symbol)

            # Kelly Criterion position sizing
            win_rate = self._calculate_symbol_win_rate(symbol)
            avg_win_loss_ratio = self._calculate_avg_win_loss_ratio(symbol)

            if win_rate > 0 and avg_win_loss_ratio > 0:
                kelly_pct = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
                kelly_pct = max(0, min(kelly_pct, 0.25))  # Cap at 25%
            else:
                kelly_pct = 0.01  # Conservative 1% if no history

            # Volatility-adjusted sizing
            vol_adjusted_pct = self.limits.max_single_position_pct * (0.02 / max(volatility, 0.001))

            # Risk budget allocation
            risk_budget_pct = self.limits.max_portfolio_risk_pct / max(volatility, 0.001)

            # Take the most conservative size
            recommended_pct = min(
                kelly_pct * 100,
                vol_adjusted_pct,
                risk_budget_pct,
                self.limits.max_single_position_pct
            )

            # Calculate position sizes with SECURE DIVISION
            recommended_size_usd = (recommended_pct / 100) * current_portfolio_value
            recommended_size_units = self._safe_divide(recommended_size_usd, price, 0.0)

            # Conservative size (50% of recommended)
            conservative_size_usd = recommended_size_usd * 0.5
            conservative_size_units = self._safe_divide(conservative_size_usd, price, 0.0)

            # Aggressive size (150% of recommended, capped by limits)
            aggressive_pct = min(recommended_pct * 1.5, self.limits.max_single_position_pct)
            aggressive_size_usd = (aggressive_pct / 100) * current_portfolio_value
            aggressive_size_units = self._safe_divide(aggressive_size_usd, price, 0.0)

            return {
                'symbol': symbol,
                'current_price': price,
                'portfolio_value': current_portfolio_value,
                'volatility': volatility,
                'kelly_percentage': kelly_pct * 100,
                'recommended': {
                    'percentage': recommended_pct,
                    'size_usd': recommended_size_usd,
                    'size_units': recommended_size_units
                },
                'conservative': {
                    'percentage': recommended_pct * 0.5,
                    'size_usd': conservative_size_usd,
                    'size_units': conservative_size_units
                },
                'aggressive': {
                    'percentage': aggressive_pct,
                    'size_usd': aggressive_size_usd,
                    'size_units': aggressive_size_units
                },
                'risk_metrics': {
                    'win_rate': win_rate,
                    'avg_win_loss_ratio': avg_win_loss_ratio,
                    'vol_adjusted_pct': vol_adjusted_pct,
                    'risk_budget_pct': risk_budget_pct
                }
            }

        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error calculating optimal position size: {e}")
            return {
                'error': str(e),
                'symbol': symbol,
                'current_price': price
            }

    def update_limits(self, new_limits: RiskLimits) -> None:
        """Update risk limits"""
        with self._lock:
            self.limits = new_limits
            logger.info("[RISK_MANAGER] Risk limits updated")

    def get_current_limits(self) -> RiskLimits:
        """Get current risk limits"""
        return self.limits

    async def get_risk_report(self) -> Dict[str, Any]:
        """Get comprehensive risk report"""
        try:
            current_metrics = await self.calculate_risk_metrics()
            portfolio_summary = self.position_tracker.get_portfolio_summary()

            # Recent violations
            recent_violations = [
                v for v in self._risk_violations
                if v['timestamp'] > time.time() - 86400  # Last 24 hours
            ]

            # Position concentration analysis
            concentration_analysis = self._analyze_concentration_risk()

            return {
                'timestamp': time.time(),
                'current_metrics': current_metrics.to_dict(),
                'portfolio_summary': portfolio_summary,
                'risk_limits': self.limits.to_dict(),
                'recent_violations': recent_violations,
                'concentration_analysis': concentration_analysis,
                'recommendations': self._generate_risk_recommendations(current_metrics),
                'cooling_period_active': time.time() < self._cooling_off_until,
                'cooling_period_remaining': max(0, int(self._cooling_off_until - time.time()))
            }

        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error generating risk report: {e}")
            return {'error': str(e)}

    def _calculate_current_drawdown(self, current_value: float) -> float:
        """Calculate current drawdown from peak"""
        if self._peak_portfolio_value <= 0:
            return 0.0

        drawdown = ((self._peak_portfolio_value - current_value) / self._peak_portfolio_value) * 100
        return max(0, drawdown)

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from history"""
        if len(self._portfolio_value_history) < 2:
            return 0.0

        values = [v[1] for v in self._portfolio_value_history]
        peak = values[0]
        max_dd = 0.0

        for value in values[1:]:
            if value > peak:
                peak = value
            else:
                drawdown = ((peak - value) / peak) * 100
                max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_var(self, current_value: float) -> Tuple[float, float]:
        """Calculate Value at Risk at 95% and 99% confidence levels"""
        if len(self._portfolio_value_history) < 10:
            return 0.0, 0.0

        returns = []
        values = [v[1] for v in self._portfolio_value_history]

        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)

        if len(returns) < 5:
            return 0.0, 0.0

        returns_array = np.array(returns)
        var_95 = np.percentile(returns_array, 5) * current_value  # 5th percentile for 95% VaR
        var_99 = np.percentile(returns_array, 1) * current_value  # 1st percentile for 99% VaR

        return abs(var_95), abs(var_99)

    def _calculate_expected_shortfall(self, current_value: float) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if len(self._portfolio_value_history) < 10:
            return 0.0

        returns = []
        values = [v[1] for v in self._portfolio_value_history]

        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)

        if len(returns) < 5:
            return 0.0

        returns_array = np.array(returns)
        var_95 = np.percentile(returns_array, 5)

        # Expected shortfall is the average of returns below VaR
        shortfall_returns = returns_array[returns_array <= var_95]
        if len(shortfall_returns) > 0:
            expected_shortfall = np.mean(shortfall_returns) * current_value
            return abs(expected_shortfall)

        return 0.0

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(self._portfolio_value_history) < 10:
            return 0.0

        returns = []
        values = [v[1] for v in self._portfolio_value_history]

        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)

        if len(returns) < 5:
            return 0.0

        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate

        if np.std(excess_returns) == 0:
            return 0.0

        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)  # Annualized

    def _calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if len(self._portfolio_value_history) < 10:
            return 0.0

        returns = []
        values = [v[1] for v in self._portfolio_value_history]

        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)

        if len(returns) < 5:
            return 0.0

        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return float('inf')

        downside_deviation = np.std(downside_returns)
        if downside_deviation == 0:
            return 0.0

        return np.mean(excess_returns) / downside_deviation * np.sqrt(252)

    def _calculate_calmar_ratio(self) -> float:
        """Calculate Calmar ratio (return/max drawdown)"""
        if len(self._portfolio_value_history) < 10:
            return 0.0

        values = [v[1] for v in self._portfolio_value_history]
        total_return = (values[-1] - values[0]) / values[0] if values[0] > 0 else 0
        max_drawdown = self._calculate_max_drawdown() / 100  # Convert to decimal

        if max_drawdown == 0:
            return float('inf') if total_return > 0 else 0.0

        return total_return / max_drawdown

    def _calculate_win_rate(self) -> float:
        """Calculate overall win rate from closed positions"""
        closed_positions = self.position_tracker.get_closed_positions()

        if not closed_positions:
            return 0.0

        winning_positions = sum(1 for pos in closed_positions if pos.realized_pnl > 0)
        return winning_positions / len(closed_positions)

    def _calculate_portfolio_volatility(self) -> float:
        """Calculate portfolio volatility"""
        if len(self._portfolio_value_history) < 10:
            return 0.0

        returns = []
        values = [v[1] for v in self._portfolio_value_history]

        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)

        if len(returns) < 5:
            return 0.0

        return float(np.std(returns) * np.sqrt(252))  # Annualized volatility

    def _calculate_average_position_volatility(self) -> float:
        """Calculate average volatility of open positions"""
        open_positions = self.position_tracker.get_all_open_positions()

        if not open_positions:
            return 0.0

        total_volatility = 0.0
        valid_positions = 0

        for position in open_positions.values():
            symbol_vol = self._get_cached_volatility(position.symbol)
            if symbol_vol > 0:
                total_volatility += symbol_vol
                valid_positions += 1

        return total_volatility / valid_positions if valid_positions > 0 else 0.0

    def _calculate_largest_position_percentage(self, portfolio_value: float) -> float:
        """Calculate largest position as percentage of portfolio"""
        if portfolio_value <= 0:
            return 0.0

        open_positions = self.position_tracker.get_all_open_positions()

        if not open_positions:
            return 0.0

        largest_value = max(float(pos.current_value) for pos in open_positions.values())
        return (largest_value / portfolio_value) * 100

    def _calculate_concentration_risk(self) -> float:
        """Calculate concentration risk (Herfindahl index)"""
        portfolio_summary = self.position_tracker.get_portfolio_summary()

        if portfolio_summary['total_value'] <= 0:
            return 0.0

        # Calculate Herfindahl index for position concentration
        concentration_index = 0.0

        for symbol_data in portfolio_summary['symbol_breakdown'].values():
            weight = symbol_data['total_value'] / portfolio_summary['total_value']
            concentration_index += weight ** 2

        return concentration_index

    def _calculate_risk_score(self, current_drawdown: float, max_drawdown: float,
                            volatility: float, concentration: float, positions: int) -> float:
        """Calculate overall risk score (0-100)"""
        score = 0.0

        # Drawdown component (0-30 points)
        drawdown_score = min(current_drawdown / self.limits.max_daily_drawdown_pct, 1.0) * 30
        score += drawdown_score

        # Volatility component (0-25 points)
        vol_score = min(volatility / 0.3, 1.0) * 25  # Cap at 30% volatility
        score += vol_score

        # Concentration component (0-25 points)
        conc_score = min(concentration, 1.0) * 25
        score += conc_score

        # Position count component (0-20 points)
        if positions > self.limits.max_positions * 0.8:  # Near limit
            pos_score = ((positions - self.limits.max_positions * 0.8) / (self.limits.max_positions * 0.2)) * 20
            score += min(pos_score, 20)

        return min(score, 100.0)

    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from risk score"""
        if risk_score < 25:
            return RiskLevel.LOW
        elif risk_score < 50:
            return RiskLevel.MEDIUM
        elif risk_score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    async def _get_current_portfolio_value(self) -> float:
        """Get current portfolio value in USD"""
        if self.balance_manager:
            try:
                balances = await self.balance_manager.get_all_balances()
                total_value_usd = 0.0

                for asset, balance_data in balances.items():
                    balance_amount = balance_data.get('balance', 0)

                    # CURRENCY CONVERSION FIX: Convert each asset to USD equivalent
                    if balance_amount <= 0:
                        continue

                    # Convert to USD equivalent
                    if asset.upper() == 'USD':
                        # Already in USD
                        asset_value_usd = balance_amount
                    elif asset.upper() == 'USDT':
                        # CRITICAL FIX: Don't assume 1:1 USDT/USD ratio
                        # Get USDT/USD exchange rate (fallback to 1.0 if unavailable)
                        usdt_usd_rate = await self._get_currency_conversion_rate('USDT', 'USD')
                        asset_value_usd = balance_amount * usdt_usd_rate
                    else:
                        # For other assets, get USD price
                        asset_price_usd = await self._get_asset_price_usd(asset)
                        asset_value_usd = balance_amount * asset_price_usd

                    total_value_usd += asset_value_usd

                return total_value_usd
            except Exception as e:
                logger.error(f"[RISK_MANAGER] Error getting portfolio value: {e}")
                return 0.0

        # Fallback to position tracker
        try:
            portfolio_summary = self.position_tracker.get_portfolio_summary()
            # CURRENCY CONVERSION FIX: Ensure position tracker also uses USD values
            return portfolio_summary.get('total_value_usd', portfolio_summary.get('total_value', 0.0))
        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error getting portfolio value from position tracker: {e}")
            return 0.0

    async def _get_currency_conversion_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Get currency conversion rate between two currencies
        
        Args:
            from_currency: Source currency (e.g., 'USDT')
            to_currency: Target currency (e.g., 'USD')
            
        Returns:
            Exchange rate (defaults to 1.0 if unavailable)
        """
        try:
            if from_currency.upper() == to_currency.upper():
                return 1.0

            # Special case for USDT/USD - use small variation from 1.0
            if from_currency.upper() == 'USDT' and to_currency.upper() == 'USD':
                # In reality, USDT slightly deviates from 1:1 USD parity
                # For now, use 0.9995 as a reasonable approximation
                # TODO: Integrate with real-time exchange rate API
                return 0.9995

            # For other currency pairs, attempt to get rate from exchange
            if hasattr(self, 'balance_manager') and hasattr(self.balance_manager, 'exchange_client'):
                try:
                    # Attempt to get ticker data for currency pair
                    ticker_symbol = f"{from_currency}/{to_currency}"
                    ticker_data = await self.balance_manager.exchange_client.get_ticker(ticker_symbol)
                    if ticker_data and 'price' in ticker_data:
                        return float(ticker_data['price'])
                except Exception:
                    pass

            # Fallback to 1:1 ratio with warning
            logger.warning(f"[RISK_MANAGER] Could not get conversion rate for {from_currency}/{to_currency}, using 1:1 ratio")
            return 1.0

        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error getting currency conversion rate: {e}")
            return 1.0

    async def _get_asset_price_usd(self, asset: str) -> float:
        """
        Get USD price for an asset
        
        Args:
            asset: Asset symbol (e.g., 'BTC', 'ETH', 'SHIB')
            
        Returns:
            Asset price in USD (defaults to 0.0 if unavailable)
        """
        try:
            if asset.upper() == 'USD':
                return 1.0

            # Try to get price from balance manager's exchange client
            if hasattr(self, 'balance_manager') and hasattr(self.balance_manager, 'exchange_client'):
                try:
                    # Try USD pair first
                    usd_symbol = f"{asset}/USD"
                    ticker_data = await self.balance_manager.exchange_client.get_ticker(usd_symbol)
                    if ticker_data and 'price' in ticker_data:
                        return float(ticker_data['price'])
                except Exception:
                    pass

                try:
                    # Fallback to USDT pair and convert to USD
                    usdt_symbol = f"{asset}/USDT"
                    ticker_data = await self.balance_manager.exchange_client.get_ticker(usdt_symbol)
                    if ticker_data and 'price' in ticker_data:
                        usdt_price = float(ticker_data['price'])
                        # Convert USDT price to USD
                        usdt_usd_rate = await self._get_currency_conversion_rate('USDT', 'USD')
                        return usdt_price * usdt_usd_rate
                except Exception:
                    pass

            # Log warning for missing price data
            logger.warning(f"[RISK_MANAGER] Could not get USD price for {asset}, treating as 0 value")
            return 0.0

        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error getting USD price for {asset}: {e}")
            return 0.0

    def _get_symbol_exposure(self, symbol: str) -> float:
        """Get current exposure to a symbol"""
        positions = self.position_tracker.get_positions_by_symbol(symbol)
        return sum(float(pos.current_value) for pos in positions)

    async def _get_symbol_volatility(self, symbol: str) -> float:
        """Get volatility for a symbol"""
        # Check cache first
        cached_vol, cached_time = self._volatility_cache.get(symbol, (0.0, 0.0))
        if cached_time > time.time() - 3600:  # 1 hour cache
            return cached_vol

        # Calculate volatility from price history
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=100)

        price_history = self._price_history[symbol]

        if len(price_history) < 10:
            # Default volatility estimate
            volatility = 0.02  # 2% default
        else:
            prices = list(price_history)
            returns = []

            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    ret = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(ret)

            if returns:
                volatility = float(np.std(returns) * np.sqrt(24))  # Daily volatility
            else:
                volatility = 0.02

        # Cache the result
        self._volatility_cache[symbol] = (volatility, time.time())

        return volatility

    def _get_cached_volatility(self, symbol: str) -> float:
        """Get cached volatility for a symbol"""
        cached_vol, cached_time = self._volatility_cache.get(symbol, (0.0, 0.0))
        if cached_time > time.time() - 3600:  # 1 hour cache
            return cached_vol
        return 0.0

    def _check_trade_frequency(self) -> RiskAction:
        """Check trade frequency limits"""
        current_time = time.time()

        # Clean old entries
        self._last_trade_times = [t for t in self._last_trade_times if current_time - t < 86400]

        # Check hourly limit
        hourly_trades = sum(1 for t in self._last_trade_times if current_time - t < 3600)
        if hourly_trades >= self.limits.max_trades_per_hour:
            return RiskAction.BLOCK

        # Check daily limit
        if len(self._last_trade_times) >= self.limits.max_trades_per_day:
            return RiskAction.BLOCK

        return RiskAction.ALLOW

    def _calculate_symbol_win_rate(self, symbol: str) -> float:
        """Calculate win rate for a specific symbol"""
        closed_positions = self.position_tracker.get_closed_positions(symbol)

        if not closed_positions:
            return 0.5  # Default 50% if no history

        winning_positions = sum(1 for pos in closed_positions if pos.realized_pnl > 0)
        return winning_positions / len(closed_positions)

    def _calculate_avg_win_loss_ratio(self, symbol: str) -> float:
        """Calculate average win/loss ratio for a symbol"""
        closed_positions = self.position_tracker.get_closed_positions(symbol)

        if not closed_positions:
            return 1.0  # Default 1:1 if no history

        winning_trades = [float(pos.realized_pnl) for pos in closed_positions if pos.realized_pnl > 0]
        losing_trades = [abs(float(pos.realized_pnl)) for pos in closed_positions if pos.realized_pnl < 0]

        if not winning_trades or not losing_trades:
            return 1.0

        avg_win = np.mean(winning_trades)
        avg_loss = np.mean(losing_trades)

        return self._safe_divide(avg_win, avg_loss, 1.0)

    def _safe_divide(self, numerator: float, denominator: float, default: float = 0.0) -> float:
        """
        Safely perform division with zero and error checking
        
        Args:
            numerator: Numerator value
            denominator: Denominator value  
            default: Value to return if division cannot be performed
            
        Returns:
            Result of division or default value
        """
        try:
            # Check for zero denominator
            if denominator == 0 or abs(denominator) < 1e-10:
                logger.debug(f"[RISK_MANAGER] Division by zero prevented: {numerator} / {denominator}")
                return default

            # Check for invalid values
            if not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)):
                logger.warning(f"[RISK_MANAGER] Invalid division operands: {numerator} / {denominator}")
                return default

            # Perform safe division
            result = numerator / denominator

            # Check for invalid results
            if not isinstance(result, (int, float)) or not np.isfinite(result):
                logger.warning(f"[RISK_MANAGER] Division resulted in invalid value: {numerator} / {denominator} = {result}")
                return default

            return result

        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error in safe division {numerator} / {denominator}: {e}")
            return default

    def _analyze_concentration_risk(self) -> Dict[str, Any]:
        """Analyze portfolio concentration risk"""
        portfolio_summary = self.position_tracker.get_portfolio_summary()

        symbol_weights = {}
        for symbol, data in portfolio_summary['symbol_breakdown'].items():
            weight = data['total_value'] / portfolio_summary['total_value'] if portfolio_summary['total_value'] > 0 else 0
            symbol_weights[symbol] = weight

        # Sort by weight
        sorted_symbols = sorted(symbol_weights.items(), key=lambda x: x[1], reverse=True)

        # Calculate concentration metrics
        top_3_concentration = sum(weight for _, weight in sorted_symbols[:3])
        top_5_concentration = sum(weight for _, weight in sorted_symbols[:5])

        return {
            'symbol_weights': symbol_weights,
            'top_positions': sorted_symbols[:5],
            'top_3_concentration': top_3_concentration,
            'top_5_concentration': top_5_concentration,
            'herfindahl_index': self._calculate_concentration_risk(),
            'diversification_ratio': 1 / len(symbol_weights) if symbol_weights else 0
        }

    def _generate_risk_recommendations(self, metrics: RiskMetrics) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []

        # Drawdown recommendations
        if metrics.current_drawdown_pct > self.limits.max_daily_drawdown_pct * 0.8:
            recommendations.append("Consider reducing position sizes due to elevated drawdown")

        # Volatility recommendations
        if metrics.portfolio_volatility > 0.3:
            recommendations.append("Portfolio volatility is high - consider diversification")

        # Concentration recommendations
        if metrics.concentration_risk > 0.5:
            recommendations.append("Portfolio is highly concentrated - consider diversifying")

        # Position count recommendations
        if metrics.active_positions > self.limits.max_positions * 0.9:
            recommendations.append("Approaching maximum position limit - consider consolidating")

        # Risk level recommendations
        if metrics.overall_risk_level == RiskLevel.HIGH:
            recommendations.append("Risk level is HIGH - implement defensive measures")
        elif metrics.overall_risk_level == RiskLevel.CRITICAL:
            recommendations.append("CRITICAL risk level - consider immediate position reduction")

        return recommendations

    async def _save_risk_metrics(self, metrics: RiskMetrics) -> None:
        """Save risk metrics to file"""
        try:
            with open(self.risk_file, 'w') as f:
                json.dump(metrics.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error saving risk metrics: {e}")

    async def _load_risk_history(self) -> None:
        """Load risk history from file"""
        try:
            with open(self.risk_file) as f:
                data = json.load(f)
                # Could restore last metrics if needed
            logger.debug("[RISK_MANAGER] Risk history loaded")
        except FileNotFoundError:
            logger.info("[RISK_MANAGER] No existing risk history found")
        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error loading risk history: {e}")

    async def _load_violations(self) -> None:
        """Load violation history from file"""
        try:
            with open(self.violations_file) as f:
                self._risk_violations = json.load(f)
            logger.debug(f"[RISK_MANAGER] Loaded {len(self._risk_violations)} risk violations")
        except FileNotFoundError:
            logger.info("[RISK_MANAGER] No existing violations found")
        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error loading violations: {e}")

    def record_trade(self, symbol: str, size: float, price: float) -> None:
        """Record a trade for frequency tracking"""
        self._last_trade_times.append(time.time())

        # Update price history for volatility calculation
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=100)

        self._price_history[symbol].append(price)

    def record_violation(self, violation_type: str, description: str,
                        action_taken: str = None) -> None:
        """Record a risk violation"""
        violation = {
            'timestamp': time.time(),
            'type': violation_type,
            'description': description,
            'action_taken': action_taken
        }

        self._risk_violations.append(violation)

        # Activate cooling period
        if violation_type in ['drawdown_exceeded', 'position_limit_exceeded']:
            self._cooling_off_until = time.time() + (self.limits.cooling_period_minutes * 60)

        logger.warning(f"[RISK_MANAGER] Risk violation recorded: {description}")

        # Save violations
        try:
            with open(self.violations_file, 'w') as f:
                json.dump(self._risk_violations, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[RISK_MANAGER] Error saving violations: {e}")
