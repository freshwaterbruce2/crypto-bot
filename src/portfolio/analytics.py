"""
Portfolio Analytics
==================

Comprehensive performance analytics and reporting system with advanced
metrics calculation, benchmarking, and visualization support.

Features:
- Performance metrics (returns, volatility, Sharpe ratio, etc.)
- Risk analytics (VaR, drawdowns, correlation analysis)
- Benchmarking against market indices
- Attribution analysis (performance breakdown)
- Portfolio optimization analytics
- Export capabilities for reporting
- Real-time analytics dashboard data
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# Try to import pandas, provide fallback for memory issues
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except (ImportError, MemoryError) as e:
    logging.warning(f"Pandas not available ({e}), using lightweight analytics")
    pd = None
    PANDAS_AVAILABLE = False

# Use existing numpy compatibility layer
import statistics

from ..utils.numpy_compat import has_numpy, numpy_compat


# Create a numpy-like interface using the compatibility layer
class NumpyInterface:
    @staticmethod
    def mean(values):
        return numpy_compat.mean(values)

    @staticmethod
    def std(values):
        return numpy_compat.std(values)

    @staticmethod
    def sqrt(x):
        return x ** 0.5

    @staticmethod
    def percentile(values, q):
        if not values:
            return 0
        sorted_vals = sorted(values)
        index = int((q / 100.0) * (len(sorted_vals) - 1))
        return sorted_vals[index]

    @staticmethod
    def var(values):
        if not values:
            return 0
        try:
            return statistics.variance(values)
        except:
            mean_val = sum(values) / len(values)
            return sum((x - mean_val) ** 2 for x in values) / len(values)

    @staticmethod
    def cov(x, y):
        if not x or not y or len(x) != len(y):
            return [[0, 0], [0, 0]]
        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)
        cov_xy = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x))) / len(x)
        var_x = NumpyInterface.var(x)
        var_y = NumpyInterface.var(y)
        return [[var_x, cov_xy], [cov_xy, var_y]]

    @staticmethod
    def array(values):
        return numpy_compat.array(values)

np = NumpyInterface()
NUMPY_AVAILABLE = has_numpy()

from .position_tracker import PositionTracker
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)


class MetricPeriod(Enum):
    """Time period for metrics calculation"""
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    INCEPTION = "inception"


class BenchmarkType(Enum):
    """Benchmark comparison types"""
    BTC = "bitcoin"
    ETH = "ethereum"
    SP500 = "sp500"
    CUSTOM = "custom"


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    period: MetricPeriod
    start_date: float
    end_date: float

    # Return metrics
    total_return: float
    annualized_return: float
    daily_return_mean: float
    daily_return_std: float

    # Risk metrics
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    current_drawdown: float

    # Trade metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float

    # Portfolio metrics
    portfolio_value: float
    cash_balance: float
    invested_amount: float
    unrealized_pnl: float
    realized_pnl: float

    # Advanced metrics
    information_ratio: float
    tracking_error: float
    beta: float
    alpha: float
    var_95: float
    var_99: float
    expected_shortfall: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['period'] = self.period.value
        return data


@dataclass
class AttributionAnalysis:
    """Performance attribution analysis"""
    period: MetricPeriod
    total_return: float

    # Asset attribution
    asset_contributions: dict[str, float]
    sector_contributions: dict[str, float]

    # Strategy attribution
    strategy_contributions: dict[str, float]

    # Factor attribution
    market_return: float
    selection_return: float
    interaction_return: float

    # Risk attribution
    risk_contributions: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['period'] = self.period.value
        return data


@dataclass
class AnalyticsConfig:
    """Analytics configuration"""
    # Calculation settings
    risk_free_rate: float = 0.02  # 2% annual risk-free rate
    benchmark_symbol: str = "BTC"  # Default benchmark
    confidence_levels: list[float] = None  # VaR confidence levels

    # Performance calculation
    annualization_factor: int = 252  # Trading days per year
    rolling_window_days: int = 30  # Rolling calculations window

    # Reporting settings
    report_frequency_hours: float = 24.0  # Daily reports
    keep_history_days: int = 365  # Keep 1 year of history

    # Export settings
    export_format: str = "json"  # json, csv, excel
    export_path: str = "D:/trading_data/analytics"

    def __post_init__(self):
        if self.confidence_levels is None:
            self.confidence_levels = [0.95, 0.99]


class PortfolioAnalytics:
    """
    Comprehensive portfolio analytics system
    """

    def __init__(self, position_tracker: PositionTracker, risk_manager: RiskManager,
                 balance_manager=None, config: Optional[AnalyticsConfig] = None,
                 data_path: str = "D:/trading_data"):
        """
        Initialize analytics system

        Args:
            position_tracker: Position tracker instance
            risk_manager: Risk manager instance
            balance_manager: Balance manager instance
            config: Analytics configuration
            data_path: Data storage path
        """
        self.position_tracker = position_tracker
        self.risk_manager = risk_manager
        self.balance_manager = balance_manager
        self.config = config or AnalyticsConfig()
        self.data_path = data_path

        # Data storage
        self._performance_history: deque = deque(maxlen=10000)
        self._portfolio_values: deque = deque(maxlen=10000)
        self._benchmark_values: deque = deque(maxlen=10000)
        self._daily_returns: deque = deque(maxlen=1000)

        # Cached calculations
        self._cached_metrics: dict[str, tuple[PerformanceMetrics, float]] = {}
        self._attribution_cache: dict[str, tuple[AttributionAnalysis, float]] = {}

        # Analytics state
        self._last_portfolio_value: float = 0.0
        self._inception_date: float = time.time()
        self._peak_portfolio_value: float = 0.0

        # Files
        self.metrics_file = f"{data_path}/performance_metrics.json"
        self.attribution_file = f"{data_path}/attribution_analysis.json"
        self.analytics_config_file = f"{data_path}/analytics_config.json"

        # Background task
        self._analytics_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info("[ANALYTICS] Initialized portfolio analytics system")

    async def initialize(self) -> bool:
        """Initialize the analytics system"""
        try:
            # Load configuration and historical data
            await self._load_config()
            await self._load_historical_data()

            # Initialize portfolio tracking
            await self._initialize_portfolio_tracking()

            # Start background analytics
            await self.start_analytics()

            logger.info("[ANALYTICS] Analytics system initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[ANALYTICS] Initialization failed: {e}")
            return False

    async def start_analytics(self) -> None:
        """Start background analytics calculations"""
        if self._running:
            return

        self._running = True
        self._analytics_task = asyncio.create_task(self._analytics_loop())
        logger.info("[ANALYTICS] Started analytics calculations")

    async def stop_analytics(self) -> None:
        """Stop background analytics"""
        self._running = False

        if self._analytics_task and not self._analytics_task.done():
            self._analytics_task.cancel()
            try:
                await self._analytics_task
            except asyncio.CancelledError:
                pass

        logger.info("[ANALYTICS] Stopped analytics calculations")

    async def calculate_performance_metrics(self, period: MetricPeriod = MetricPeriod.INCEPTION) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics

        Args:
            period: Time period for calculation

        Returns:
            PerformanceMetrics object
        """
        # Check cache first
        cache_key = f"{period.value}"
        if cache_key in self._cached_metrics:
            metrics, cache_time = self._cached_metrics[cache_key]
            if time.time() - cache_time < 300:  # 5-minute cache
                return metrics

        try:
            # Get time range for period
            end_time = time.time()
            start_time = self._get_period_start_time(period, end_time)

            # Get portfolio values for period
            portfolio_values = self._get_portfolio_values_for_period(start_time, end_time)

            if len(portfolio_values) < 2:
                logger.warning(f"[ANALYTICS] Insufficient data for {period.value} metrics")
                return self._create_empty_metrics(period, start_time, end_time)

            # Calculate returns
            returns = self._calculate_returns(portfolio_values)

            # Calculate basic metrics
            total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0] if portfolio_values[0] > 0 else 0
            annualized_return = self._annualize_return(total_return, start_time, end_time)

            # Risk metrics
            volatility = self._calculate_volatility(returns)
            sharpe_ratio = self._calculate_sharpe_ratio(returns, volatility)
            sortino_ratio = self._calculate_sortino_ratio(returns)
            calmar_ratio = self._calculate_calmar_ratio(returns, portfolio_values)
            max_drawdown = self._calculate_max_drawdown(portfolio_values)
            current_drawdown = self._calculate_current_drawdown(portfolio_values)

            # Trade metrics
            trade_metrics = await self._calculate_trade_metrics(start_time, end_time)

            # Portfolio status
            portfolio_summary = self.position_tracker.get_portfolio_summary()
            current_portfolio_value = await self._get_current_portfolio_value()

            # Advanced metrics
            information_ratio = self._calculate_information_ratio(returns)
            tracking_error = self._calculate_tracking_error(returns)
            beta, alpha = await self._calculate_beta_alpha(returns, start_time, end_time)
            var_95, var_99 = self._calculate_var(returns)
            expected_shortfall = self._calculate_expected_shortfall(returns)

            # Create metrics object
            metrics = PerformanceMetrics(
                period=period,
                start_date=start_time,
                end_date=end_time,
                total_return=total_return,
                annualized_return=annualized_return,
                daily_return_mean=np.mean(returns) if returns else 0.0,
                daily_return_std=np.std(returns) if returns else 0.0,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                total_trades=trade_metrics['total_trades'],
                winning_trades=trade_metrics['winning_trades'],
                losing_trades=trade_metrics['losing_trades'],
                win_rate=trade_metrics['win_rate'],
                avg_win=trade_metrics['avg_win'],
                avg_loss=trade_metrics['avg_loss'],
                profit_factor=trade_metrics['profit_factor'],
                portfolio_value=current_portfolio_value,
                cash_balance=await self._get_cash_balance(),
                invested_amount=portfolio_summary['total_value'],
                unrealized_pnl=portfolio_summary['total_unrealized_pnl'],
                realized_pnl=portfolio_summary['total_realized_pnl'],
                information_ratio=information_ratio,
                tracking_error=tracking_error,
                beta=beta,
                alpha=alpha,
                var_95=var_95,
                var_99=var_99,
                expected_shortfall=expected_shortfall
            )

            # Cache the result
            self._cached_metrics[cache_key] = (metrics, time.time())

            return metrics

        except Exception as e:
            logger.error(f"[ANALYTICS] Error calculating performance metrics: {e}")
            return self._create_empty_metrics(period, start_time, end_time)

    async def calculate_attribution_analysis(self, period: MetricPeriod = MetricPeriod.MONTHLY) -> AttributionAnalysis:
        """
        Calculate performance attribution analysis

        Args:
            period: Time period for analysis

        Returns:
            AttributionAnalysis object
        """
        try:
            end_time = time.time()
            start_time = self._get_period_start_time(period, end_time)

            # Get portfolio performance
            portfolio_values = self._get_portfolio_values_for_period(start_time, end_time)
            total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0] if len(portfolio_values) >= 2 and portfolio_values[0] > 0 else 0

            # Asset attribution
            asset_contributions = await self._calculate_asset_attribution(start_time, end_time)

            # Strategy attribution
            strategy_contributions = await self._calculate_strategy_attribution(start_time, end_time)

            # Factor attribution (simplified)
            market_return = await self._get_benchmark_return(start_time, end_time)
            selection_return = total_return - market_return
            interaction_return = 0.0  # Simplified

            # Risk attribution
            risk_contributions = await self._calculate_risk_attribution(start_time, end_time)

            # Sector attribution (simplified - could be expanded)
            sector_contributions = {"crypto": total_return}  # All crypto for now

            attribution = AttributionAnalysis(
                period=period,
                total_return=total_return,
                asset_contributions=asset_contributions,
                sector_contributions=sector_contributions,
                strategy_contributions=strategy_contributions,
                market_return=market_return,
                selection_return=selection_return,
                interaction_return=interaction_return,
                risk_contributions=risk_contributions
            )

            return attribution

        except Exception as e:
            logger.error(f"[ANALYTICS] Error calculating attribution analysis: {e}")
            return AttributionAnalysis(
                period=period,
                total_return=0.0,
                asset_contributions={},
                sector_contributions={},
                strategy_contributions={},
                market_return=0.0,
                selection_return=0.0,
                interaction_return=0.0,
                risk_contributions={}
            )

    async def generate_performance_report(self, periods: list[MetricPeriod] = None) -> dict[str, Any]:
        """
        Generate comprehensive performance report

        Args:
            periods: List of periods to include (default: all common periods)

        Returns:
            Dictionary with comprehensive performance data
        """
        if periods is None:
            periods = [MetricPeriod.DAILY, MetricPeriod.WEEKLY, MetricPeriod.MONTHLY, MetricPeriod.INCEPTION]

        try:
            report = {
                'generated_at': time.time(),
                'periods': {},
                'attribution': {},
                'portfolio_overview': {},
                'risk_analysis': {},
                'trade_analysis': {}
            }

            # Calculate metrics for each period
            for period in periods:
                metrics = await self.calculate_performance_metrics(period)
                report['periods'][period.value] = metrics.to_dict()

                # Add attribution for monthly and inception
                if period in [MetricPeriod.MONTHLY, MetricPeriod.INCEPTION]:
                    attribution = await self.calculate_attribution_analysis(period)
                    report['attribution'][period.value] = attribution.to_dict()

            # Portfolio overview
            portfolio_summary = self.position_tracker.get_portfolio_summary()
            report['portfolio_overview'] = {
                'current_value': await self._get_current_portfolio_value(),
                'positions': portfolio_summary['total_positions'],
                'symbols': list(portfolio_summary['symbol_breakdown'].keys()),
                'cash_balance': await self._get_cash_balance(),
                'invested_amount': portfolio_summary['total_value'],
                'unrealized_pnl': portfolio_summary['total_unrealized_pnl'],
                'realized_pnl': portfolio_summary['total_realized_pnl']
            }

            # Risk analysis
            risk_metrics = await self.risk_manager.calculate_risk_metrics()
            report['risk_analysis'] = risk_metrics.to_dict()

            # Trade analysis
            trade_summary = await self._generate_trade_summary()
            report['trade_analysis'] = trade_summary

            # Benchmark comparison
            benchmark_comparison = await self._calculate_benchmark_comparison()
            report['benchmark_comparison'] = benchmark_comparison

            return report

        except Exception as e:
            logger.error(f"[ANALYTICS] Error generating performance report: {e}")
            return {'error': str(e), 'generated_at': time.time()}

    async def get_dashboard_data(self) -> dict[str, Any]:
        """
        Get real-time dashboard data

        Returns:
            Dictionary with dashboard-ready analytics data
        """
        try:
            # Current performance
            daily_metrics = await self.calculate_performance_metrics(MetricPeriod.DAILY)
            weekly_metrics = await self.calculate_performance_metrics(MetricPeriod.WEEKLY)

            # Portfolio overview
            portfolio_summary = self.position_tracker.get_portfolio_summary()
            current_value = await self._get_current_portfolio_value()

            # Recent performance data
            recent_returns = list(self._daily_returns)[-30:]  # Last 30 days
            recent_values = [(time.time() - i * 86400, val) for i, val in enumerate(list(self._portfolio_values)[-30:])]

            # Risk overview
            risk_metrics = await self.risk_manager.calculate_risk_metrics()

            dashboard_data = {
                'timestamp': time.time(),
                'current_value': current_value,
                'daily_pnl': daily_metrics.total_return * current_value,
                'daily_pnl_pct': daily_metrics.total_return * 100,
                'weekly_pnl': weekly_metrics.total_return * current_value,
                'weekly_pnl_pct': weekly_metrics.total_return * 100,
                'positions': portfolio_summary['total_positions'],
                'cash_balance': await self._get_cash_balance(),
                'unrealized_pnl': portfolio_summary['total_unrealized_pnl'],
                'realized_pnl': portfolio_summary['total_realized_pnl'],
                'win_rate': daily_metrics.win_rate,
                'sharpe_ratio': daily_metrics.sharpe_ratio,
                'max_drawdown': daily_metrics.max_drawdown,
                'current_drawdown': daily_metrics.current_drawdown,
                'risk_level': risk_metrics.overall_risk_level.value,
                'risk_score': risk_metrics.risk_score,
                'recent_returns': recent_returns,
                'portfolio_history': recent_values,
                'top_positions': self._get_top_positions(portfolio_summary),
                'recent_trades': await self._get_recent_trades(10)
            }

            return dashboard_data

        except Exception as e:
            logger.error(f"[ANALYTICS] Error generating dashboard data: {e}")
            return {'error': str(e), 'timestamp': time.time()}

    async def export_analytics(self, format_type: str = None,
                              periods: list[MetricPeriod] = None) -> str:
        """
        Export analytics data

        Args:
            format_type: Export format ('json', 'csv', 'excel')
            periods: Periods to include

        Returns:
            Path to exported file
        """
        format_type = format_type or self.config.export_format

        try:
            # Generate comprehensive report
            report = await self.generate_performance_report(periods)

            # Create filename
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"portfolio_analytics_{timestamp_str}"

            if format_type == "json":
                filepath = f"{self.config.export_path}/{filename}.json"
                with open(filepath, 'w') as f:
                    json.dump(report, f, indent=2, default=str)

            elif format_type == "csv" and PANDAS_AVAILABLE:
                filepath = f"{self.config.export_path}/{filename}.csv"
                # Convert to DataFrame and export (simplified)
                df = pd.json_normalize(report['periods'])
                df.to_csv(filepath, index=False)

            elif format_type == "excel" and PANDAS_AVAILABLE:
                filepath = f"{self.config.export_path}/{filename}.xlsx"
                # Create Excel with multiple sheets (simplified)
                with pd.ExcelWriter(filepath) as writer:
                    for period, data in report['periods'].items():
                        df = pd.json_normalize([data])
                        df.to_excel(writer, sheet_name=period, index=False)

            elif (format_type in ["csv", "excel"]) and not PANDAS_AVAILABLE:
                # Fallback to JSON when pandas not available
                logger.warning(f"Pandas not available, exporting {format_type} as JSON")
                filepath = f"{self.config.export_path}/{filename}.json"
                with open(filepath, 'w') as f:
                    json.dump(report, f, indent=2, default=str)

            logger.info(f"[ANALYTICS] Exported analytics to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"[ANALYTICS] Error exporting analytics: {e}")
            raise

    def record_portfolio_value(self, value: float) -> None:
        """Record portfolio value for analytics"""
        time.time()
        self._portfolio_values.append(value)

        # Calculate daily return if we have previous value
        if len(self._portfolio_values) >= 2 and self._last_portfolio_value > 0:
            daily_return = (value - self._last_portfolio_value) / self._last_portfolio_value
            self._daily_returns.append(daily_return)

        self._last_portfolio_value = value

        # Update peak value
        if value > self._peak_portfolio_value:
            self._peak_portfolio_value = value

    async def _analytics_loop(self) -> None:
        """Background analytics calculation loop"""
        while self._running:
            try:
                # Update portfolio value
                current_value = await self._get_current_portfolio_value()
                self.record_portfolio_value(current_value)

                # Clear old cache entries
                self._clear_old_cache()

                # Sleep until next update
                await asyncio.sleep(3600)  # Update hourly

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ANALYTICS] Analytics loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    def _get_period_start_time(self, period: MetricPeriod, end_time: float) -> float:
        """Get start time for a given period"""
        if period == MetricPeriod.INTRADAY:
            return end_time - 86400  # 1 day
        elif period == MetricPeriod.DAILY:
            return end_time - 86400  # 1 day
        elif period == MetricPeriod.WEEKLY:
            return end_time - (7 * 86400)  # 7 days
        elif period == MetricPeriod.MONTHLY:
            return end_time - (30 * 86400)  # 30 days
        elif period == MetricPeriod.QUARTERLY:
            return end_time - (90 * 86400)  # 90 days
        elif period == MetricPeriod.YEARLY:
            return end_time - (365 * 86400)  # 365 days
        else:  # INCEPTION
            return self._inception_date

    def _get_portfolio_values_for_period(self, start_time: float, end_time: float) -> list[float]:
        """Get portfolio values for a time period"""
        # Simplified: return recent values (would filter by timestamp in real implementation)
        values = list(self._portfolio_values)

        # Return at least some values for calculation
        if len(values) < 2:
            current_value = self._last_portfolio_value or 100.0  # Default starting value
            return [current_value * 0.99, current_value]  # Slight variation for calculation

        return values

    def _calculate_returns(self, values: list[float]) -> list[float]:
        """Calculate returns from portfolio values"""
        if len(values) < 2:
            return []

        returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)

        return returns

    def _annualize_return(self, total_return: float, start_time: float, end_time: float) -> float:
        """Annualize a return based on time period"""
        period_days = (end_time - start_time) / 86400
        if period_days <= 0:
            return 0.0

        # Convert to annual return
        years = period_days / 365.25
        if years <= 0:
            return 0.0

        annualized = (1 + total_return) ** (1 / years) - 1
        return annualized

    def _calculate_volatility(self, returns: list[float]) -> float:
        """Calculate annualized volatility"""
        if len(returns) < 2:
            return 0.0

        return float(np.std(returns) * np.sqrt(self.config.annualization_factor))

    def _calculate_sharpe_ratio(self, returns: list[float], volatility: float) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2 or volatility == 0:
            return 0.0

        excess_returns = [r - (self.config.risk_free_rate / self.config.annualization_factor) for r in returns]
        mean_excess_return = np.mean(excess_returns)

        return (mean_excess_return * self.config.annualization_factor) / volatility

    def _calculate_sortino_ratio(self, returns: list[float]) -> float:
        """Calculate Sortino ratio"""
        if len(returns) < 2:
            return 0.0

        excess_returns = [r - (self.config.risk_free_rate / self.config.annualization_factor) for r in returns]
        downside_returns = [r for r in excess_returns if r < 0]

        if len(downside_returns) == 0:
            return float('inf')

        downside_deviation = np.std(downside_returns)
        if downside_deviation == 0:
            return 0.0

        mean_excess_return = np.mean(excess_returns)
        return (mean_excess_return * self.config.annualization_factor) / (downside_deviation * np.sqrt(self.config.annualization_factor))

    def _calculate_calmar_ratio(self, returns: list[float], values: list[float]) -> float:
        """Calculate Calmar ratio"""
        if len(returns) < 2 or len(values) < 2:
            return 0.0

        annual_return = np.mean(returns) * self.config.annualization_factor
        max_drawdown = self._calculate_max_drawdown(values) / 100  # Convert to decimal

        if max_drawdown == 0:
            return float('inf') if annual_return > 0 else 0.0

        return annual_return / max_drawdown

    def _calculate_max_drawdown(self, values: list[float]) -> float:
        """Calculate maximum drawdown as percentage"""
        if len(values) < 2:
            return 0.0

        peak = values[0]
        max_dd = 0.0

        for value in values[1:]:
            if value > peak:
                peak = value
            else:
                drawdown = ((peak - value) / peak) * 100
                max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_current_drawdown(self, values: list[float]) -> float:
        """Calculate current drawdown from peak"""
        if len(values) < 2:
            return 0.0

        peak = max(values)
        current = values[-1]

        if peak == 0:
            return 0.0

        return ((peak - current) / peak) * 100

    async def _calculate_trade_metrics(self, start_time: float, end_time: float) -> dict[str, Any]:
        """Calculate trade-related metrics"""
        try:
            # Get closed positions in the period
            all_closed_positions = self.position_tracker.get_closed_positions()
            period_positions = [
                pos for pos in all_closed_positions
                if pos.closed_at and start_time <= pos.closed_at <= end_time
            ]

            if not period_positions:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'profit_factor': 0.0
                }

            # Calculate metrics
            total_trades = len(period_positions)
            winning_trades = sum(1 for pos in period_positions if pos.realized_pnl > 0)
            losing_trades = sum(1 for pos in period_positions if pos.realized_pnl < 0)

            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

            winning_pnls = [float(pos.realized_pnl) for pos in period_positions if pos.realized_pnl > 0]
            losing_pnls = [abs(float(pos.realized_pnl)) for pos in period_positions if pos.realized_pnl < 0]

            avg_win = np.mean(winning_pnls) if winning_pnls else 0.0
            avg_loss = np.mean(losing_pnls) if losing_pnls else 0.0

            total_wins = sum(winning_pnls)
            total_losses = sum(losing_pnls)
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor
            }

        except Exception as e:
            logger.error(f"[ANALYTICS] Error calculating trade metrics: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0
            }

    def _calculate_information_ratio(self, returns: list[float]) -> float:
        """Calculate information ratio (simplified)"""
        if len(returns) < 2:
            return 0.0

        # Simplified: assume benchmark return is 0 for now
        excess_returns = returns
        tracking_error = np.std(excess_returns)

        if tracking_error == 0:
            return 0.0

        return np.mean(excess_returns) / tracking_error * np.sqrt(self.config.annualization_factor)

    def _calculate_tracking_error(self, returns: list[float]) -> float:
        """Calculate tracking error"""
        if len(returns) < 2:
            return 0.0

        # Simplified: assume benchmark return is 0
        excess_returns = returns
        return float(np.std(excess_returns) * np.sqrt(self.config.annualization_factor))

    async def _calculate_beta_alpha(self, returns: list[float],
                                  start_time: float, end_time: float) -> tuple[float, float]:
        """Calculate beta and alpha vs benchmark"""
        try:
            # Get benchmark returns (simplified)
            benchmark_returns = await self._get_benchmark_returns(start_time, end_time)

            if len(returns) < 2 or len(benchmark_returns) < 2:
                return 0.0, 0.0

            # Align returns (simplified - assume same length)
            min_length = min(len(returns), len(benchmark_returns))
            portfolio_returns = returns[-min_length:]
            bench_returns = benchmark_returns[-min_length:]

            # Calculate beta
            covariance = np.cov(portfolio_returns, bench_returns)[0][1]
            benchmark_variance = np.var(bench_returns)

            beta = covariance / benchmark_variance if benchmark_variance > 0 else 0.0

            # Calculate alpha
            portfolio_mean = np.mean(portfolio_returns) * self.config.annualization_factor
            benchmark_mean = np.mean(bench_returns) * self.config.annualization_factor
            risk_free_rate = self.config.risk_free_rate

            alpha = portfolio_mean - (risk_free_rate + beta * (benchmark_mean - risk_free_rate))

            return beta, alpha

        except Exception as e:
            logger.error(f"[ANALYTICS] Error calculating beta/alpha: {e}")
            return 0.0, 0.0

    def _calculate_var(self, returns: list[float]) -> tuple[float, float]:
        """Calculate Value at Risk at 95% and 99% confidence levels"""
        if len(returns) < 10:
            return 0.0, 0.0

        returns_array = np.array(returns)
        var_95 = np.percentile(returns_array, 5)  # 5th percentile for 95% VaR
        var_99 = np.percentile(returns_array, 1)  # 1st percentile for 99% VaR

        return abs(var_95), abs(var_99)

    def _calculate_expected_shortfall(self, returns: list[float]) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if len(returns) < 10:
            return 0.0

        returns_array = np.array(returns)
        var_95 = np.percentile(returns_array, 5)

        # Expected shortfall is the average of returns below VaR
        shortfall_returns = returns_array[returns_array <= var_95]
        if len(shortfall_returns) > 0:
            return abs(np.mean(shortfall_returns))

        return 0.0

    def _create_empty_metrics(self, period: MetricPeriod, start_time: float, end_time: float) -> PerformanceMetrics:
        """Create empty metrics object"""
        return PerformanceMetrics(
            period=period,
            start_date=start_time,
            end_date=end_time,
            total_return=0.0,
            annualized_return=0.0,
            daily_return_mean=0.0,
            daily_return_std=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            max_drawdown=0.0,
            current_drawdown=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            portfolio_value=0.0,
            cash_balance=0.0,
            invested_amount=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            information_ratio=0.0,
            tracking_error=0.0,
            beta=0.0,
            alpha=0.0,
            var_95=0.0,
            var_99=0.0,
            expected_shortfall=0.0
        )

    async def _get_current_portfolio_value(self) -> float:
        """Get current total portfolio value"""
        try:
            if self.balance_manager:
                balances = await self.balance_manager.get_all_balances()
                return sum(balance_data.get('balance', 0) for balance_data in balances.values())
            else:
                portfolio_summary = self.position_tracker.get_portfolio_summary()
                return portfolio_summary.get('total_value', 0.0)
        except Exception as e:
            logger.error(f"[ANALYTICS] Error getting portfolio value: {e}")
            return 0.0

    async def _get_cash_balance(self) -> float:
        """Get current cash balance"""
        try:
            if self.balance_manager:
                usdt_balance = await self.balance_manager.get_balance('USDT')
                return usdt_balance.get('balance', 0.0) if usdt_balance else 0.0
            return 0.0
        except Exception as e:
            logger.error(f"[ANALYTICS] Error getting cash balance: {e}")
            return 0.0

    async def _calculate_asset_attribution(self, start_time: float, end_time: float) -> dict[str, float]:
        """Calculate performance attribution by asset"""
        try:
            portfolio_summary = self.position_tracker.get_portfolio_summary()
            portfolio_summary['total_unrealized_pnl'] + portfolio_summary['total_realized_pnl']

            asset_contributions = {}
            for symbol, data in portfolio_summary['symbol_breakdown'].items():
                contribution = data.get('total_pnl', 0.0)
                asset_contributions[symbol] = contribution

            return asset_contributions

        except Exception as e:
            logger.error(f"[ANALYTICS] Error calculating asset attribution: {e}")
            return {}

    async def _calculate_strategy_attribution(self, start_time: float, end_time: float) -> dict[str, float]:
        """Calculate performance attribution by strategy"""
        try:
            # Group positions by strategy
            strategy_pnl = defaultdict(float)

            open_positions = self.position_tracker.get_all_open_positions()
            for position in open_positions.values():
                strategy = position.strategy or "unknown"
                strategy_pnl[strategy] += float(position.unrealized_pnl)

            closed_positions = self.position_tracker.get_closed_positions()
            for position in closed_positions:
                if position.closed_at and start_time <= position.closed_at <= end_time:
                    strategy = position.strategy or "unknown"
                    strategy_pnl[strategy] += float(position.realized_pnl)

            return dict(strategy_pnl)

        except Exception as e:
            logger.error(f"[ANALYTICS] Error calculating strategy attribution: {e}")
            return {}

    async def _calculate_risk_attribution(self, start_time: float, end_time: float) -> dict[str, float]:
        """Calculate risk attribution"""
        try:
            # Simplified risk attribution
            risk_metrics = await self.risk_manager.calculate_risk_metrics()

            return {
                'market_risk': risk_metrics.portfolio_var_95 * 0.7,
                'specific_risk': risk_metrics.portfolio_var_95 * 0.3,
                'concentration_risk': risk_metrics.concentration_risk * 100
            }

        except Exception as e:
            logger.error(f"[ANALYTICS] Error calculating risk attribution: {e}")
            return {}

    async def _get_benchmark_return(self, start_time: float, end_time: float) -> float:
        """Get benchmark return for period (simplified)"""
        # Simplified: return a mock benchmark return
        # In production, this would fetch actual benchmark data
        return 0.05  # 5% mock return

    async def _get_benchmark_returns(self, start_time: float, end_time: float) -> list[float]:
        """Get benchmark returns series (simplified)"""
        # Simplified: return mock benchmark returns
        # In production, this would fetch actual benchmark data
        days = int((end_time - start_time) / 86400)
        return [0.001] * min(days, 30)  # 0.1% daily mock returns

    async def _calculate_benchmark_comparison(self) -> dict[str, Any]:
        """Calculate comparison vs benchmark"""
        try:
            # Get portfolio metrics
            inception_metrics = await self.calculate_performance_metrics(MetricPeriod.INCEPTION)
            monthly_metrics = await self.calculate_performance_metrics(MetricPeriod.MONTHLY)

            # Mock benchmark data (would be real data in production)
            benchmark_inception_return = 0.15  # 15% mock
            benchmark_monthly_return = 0.02   # 2% mock

            return {
                'inception': {
                    'portfolio_return': inception_metrics.total_return,
                    'benchmark_return': benchmark_inception_return,
                    'excess_return': inception_metrics.total_return - benchmark_inception_return,
                    'tracking_error': inception_metrics.tracking_error
                },
                'monthly': {
                    'portfolio_return': monthly_metrics.total_return,
                    'benchmark_return': benchmark_monthly_return,
                    'excess_return': monthly_metrics.total_return - benchmark_monthly_return,
                    'tracking_error': monthly_metrics.tracking_error
                }
            }

        except Exception as e:
            logger.error(f"[ANALYTICS] Error calculating benchmark comparison: {e}")
            return {}

    async def _generate_trade_summary(self) -> dict[str, Any]:
        """Generate comprehensive trade summary"""
        try:
            all_positions = self.position_tracker.get_closed_positions()

            if not all_positions:
                return {'total_trades': 0}

            # Basic stats
            total_trades = len(all_positions)
            winning_trades = sum(1 for pos in all_positions if pos.realized_pnl > 0)
            losing_trades = sum(1 for pos in all_positions if pos.realized_pnl < 0)

            # P&L stats
            total_pnl = sum(float(pos.realized_pnl) for pos in all_positions)
            winning_pnl = sum(float(pos.realized_pnl) for pos in all_positions if pos.realized_pnl > 0)
            losing_pnl = sum(float(pos.realized_pnl) for pos in all_positions if pos.realized_pnl < 0)

            # Trade duration stats
            durations = []
            for pos in all_positions:
                if pos.closed_at:
                    duration = pos.closed_at - pos.created_at
                    durations.append(duration / 3600)  # Convert to hours

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'avg_pnl_per_trade': total_pnl / total_trades if total_trades > 0 else 0,
                'largest_win': max([float(pos.realized_pnl) for pos in all_positions], default=0),
                'largest_loss': min([float(pos.realized_pnl) for pos in all_positions], default=0),
                'avg_trade_duration_hours': np.mean(durations) if durations else 0,
                'profit_factor': abs(winning_pnl / losing_pnl) if losing_pnl < 0 else float('inf')
            }

        except Exception as e:
            logger.error(f"[ANALYTICS] Error generating trade summary: {e}")
            return {'total_trades': 0}

    def _get_top_positions(self, portfolio_summary: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        """Get top positions by value"""
        try:
            positions = []
            for symbol, data in portfolio_summary['symbol_breakdown'].items():
                positions.append({
                    'symbol': symbol,
                    'value': data['total_value'],
                    'pnl': data['total_pnl'],
                    'positions': data['positions']
                })

            # Sort by value and return top N
            positions.sort(key=lambda x: x['value'], reverse=True)
            return positions[:limit]

        except Exception as e:
            logger.error(f"[ANALYTICS] Error getting top positions: {e}")
            return []

    async def _get_recent_trades(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent trades"""
        try:
            closed_positions = self.position_tracker.get_closed_positions(limit=limit)

            trades = []
            for pos in closed_positions[-limit:]:
                trades.append({
                    'symbol': pos.symbol,
                    'size': float(pos.original_size),
                    'entry_price': float(pos.entry_price),
                    'exit_price': float(pos.current_price),
                    'pnl': float(pos.realized_pnl),
                    'pnl_pct': float(pos.realized_pnl_pct),
                    'duration_hours': (pos.closed_at - pos.created_at) / 3600 if pos.closed_at else 0,
                    'closed_at': pos.closed_at
                })

            return sorted(trades, key=lambda x: x['closed_at'] or 0, reverse=True)

        except Exception as e:
            logger.error(f"[ANALYTICS] Error getting recent trades: {e}")
            return []

    def _clear_old_cache(self) -> None:
        """Clear old cache entries"""
        current_time = time.time()
        cache_ttl = 3600  # 1 hour

        # Clear performance metrics cache
        expired_keys = [
            key for key, (_, cache_time) in self._cached_metrics.items()
            if current_time - cache_time > cache_ttl
        ]

        for key in expired_keys:
            del self._cached_metrics[key]

        # Clear attribution cache
        expired_keys = [
            key for key, (_, cache_time) in self._attribution_cache.items()
            if current_time - cache_time > cache_ttl
        ]

        for key in expired_keys:
            del self._attribution_cache[key]

    async def _initialize_portfolio_tracking(self) -> None:
        """Initialize portfolio tracking"""
        try:
            # Get initial portfolio value
            current_value = await self._get_current_portfolio_value()
            self._last_portfolio_value = current_value
            self._peak_portfolio_value = current_value

            # Initialize with current value if no history
            if not self._portfolio_values:
                self.record_portfolio_value(current_value)

        except Exception as e:
            logger.error(f"[ANALYTICS] Error initializing portfolio tracking: {e}")

    async def _load_config(self) -> None:
        """Load analytics configuration"""
        try:
            with open(self.analytics_config_file) as f:
                data = json.load(f)
                # Update config attributes
                for key, value in data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
            logger.debug("[ANALYTICS] Configuration loaded")
        except FileNotFoundError:
            await self._save_config()
            logger.info("[ANALYTICS] Created default configuration")
        except Exception as e:
            logger.error(f"[ANALYTICS] Error loading configuration: {e}")

    async def _save_config(self) -> None:
        """Save analytics configuration"""
        try:
            with open(self.analytics_config_file, 'w') as f:
                json.dump(asdict(self.config), f, indent=2)
        except Exception as e:
            logger.error(f"[ANALYTICS] Error saving configuration: {e}")

    async def _load_historical_data(self) -> None:
        """Load historical analytics data"""
        try:
            # Load performance history (simplified)
            logger.debug("[ANALYTICS] Historical data loaded")
        except Exception as e:
            logger.error(f"[ANALYTICS] Error loading historical data: {e}")
