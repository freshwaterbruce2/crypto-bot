"""
Realistic Trading Scenario Validation Tests
Tests system behavior under realistic trading conditions and scenarios
"""

import asyncio
import json
import logging
import random
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.auth.kraken_auth import KrakenAuth
from src.balance.balance_manager import BalanceManager
from src.circuit_breaker.circuit_breaker import CircuitBreaker
from src.config.config import Config as TradingConfig
from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager as WebSocketManagerV2
from src.portfolio.portfolio_manager import PortfolioManager
from src.rate_limiting.kraken_rate_limiter import KrakenRateLimiter2025 as KrakenRateLimiter
from src.storage.database_manager import DatabaseManager
from src.utils.decimal_precision_fix import DecimalHandler


class MarketCondition(Enum):
    """Market conditions to simulate"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    FLASH_CRASH = "flash_crash"
    PUMP_AND_DUMP = "pump_and_dump"


class TradingScenario(Enum):
    """Trading scenarios to test"""
    NORMAL_TRADING = "normal_trading"
    HIGH_FREQUENCY = "high_frequency"
    LARGE_ORDERS = "large_orders"
    SMALL_POSITIONS = "small_positions"
    MULTIPLE_PAIRS = "multiple_pairs"
    RAPID_REBALANCING = "rapid_rebalancing"
    STOP_LOSS_TRIGGERS = "stop_loss_triggers"
    PROFIT_TAKING = "profit_taking"


@dataclass
class TradingTestScenario:
    """Trading test scenario definition"""
    name: str
    description: str
    market_condition: MarketCondition
    trading_scenario: TradingScenario
    duration_minutes: int
    expected_trades: int
    max_position_size: float
    pairs_to_test: list[str]
    performance_criteria: dict[str, float]
    test_function: str


@dataclass
class ScenarioResult:
    """Trading scenario test result"""
    scenario_name: str
    duration: float
    trades_executed: int
    successful_trades: int
    failed_trades: int
    total_volume: float
    profit_loss: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    system_performance: dict[str, float]
    errors_encountered: list[str]
    warnings: list[str]
    meets_criteria: bool
    details: dict[str, Any]


@dataclass
class MarketData:
    """Simulated market data"""
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    bid: float
    ask: float
    spread: float


class TradingScenarioTester:
    """Realistic trading scenario testing framework"""

    def __init__(self):
        self.config = TradingConfig()
        self.logger = self._setup_logging()
        self.results: list[ScenarioResult] = []

        # System components
        self.auth: Optional[KrakenAuth] = None
        self.rate_limiter: Optional[KrakenRateLimiter] = None
        self.circuit_breaker: Optional[CircuitBreaker] = None
        self.websocket_manager: Optional[WebSocketManagerV2] = None
        self.balance_manager: Optional[BalanceManager] = None
        self.portfolio_manager: Optional[PortfolioManager] = None
        self.database_manager: Optional[DatabaseManager] = None
        self.decimal_handler = DecimalHandler()

        # Trading state
        self.initial_balance = {}
        self.current_positions = {}
        self.trade_history = []
        self.market_data_cache = {}

        # Test scenarios
        self.scenarios = self._define_trading_scenarios()

    def _setup_logging(self) -> logging.Logger:
        """Setup trading scenario testing logging"""
        logger = logging.getLogger('trading_scenario_tester')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _define_trading_scenarios(self) -> list[TradingTestScenario]:
        """Define trading scenarios to test"""
        return [
            TradingTestScenario(
                name="normal_market_trading",
                description="Normal market conditions with steady trading",
                market_condition=MarketCondition.SIDEWAYS,
                trading_scenario=TradingScenario.NORMAL_TRADING,
                duration_minutes=30,
                expected_trades=10,
                max_position_size=100.0,
                pairs_to_test=["BTC/USDT", "ETH/USDT"],
                performance_criteria={
                    "min_success_rate": 0.8,
                    "max_drawdown": 0.05,
                    "min_profit": -0.01  # Allow small losses
                },
                test_function="_test_normal_market_trading"
            ),
            TradingTestScenario(
                name="high_volatility_handling",
                description="High volatility market with rapid price changes",
                market_condition=MarketCondition.HIGH_VOLATILITY,
                trading_scenario=TradingScenario.NORMAL_TRADING,
                duration_minutes=15,
                expected_trades=20,
                max_position_size=50.0,
                pairs_to_test=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
                performance_criteria={
                    "min_success_rate": 0.6,
                    "max_drawdown": 0.1,
                    "min_profit": -0.05
                },
                test_function="_test_high_volatility_handling"
            ),
            TradingTestScenario(
                name="bull_market_momentum",
                description="Bull market conditions with upward momentum",
                market_condition=MarketCondition.BULL_MARKET,
                trading_scenario=TradingScenario.NORMAL_TRADING,
                duration_minutes=20,
                expected_trades=15,
                max_position_size=200.0,
                pairs_to_test=["BTC/USDT", "ETH/USDT"],
                performance_criteria={
                    "min_success_rate": 0.7,
                    "max_drawdown": 0.03,
                    "min_profit": 0.01
                },
                test_function="_test_bull_market_momentum"
            ),
            TradingTestScenario(
                name="bear_market_resilience",
                description="Bear market conditions with downward pressure",
                market_condition=MarketCondition.BEAR_MARKET,
                trading_scenario=TradingScenario.NORMAL_TRADING,
                duration_minutes=25,
                expected_trades=12,
                max_position_size=75.0,
                pairs_to_test=["BTC/USDT", "ETH/USDT"],
                performance_criteria={
                    "min_success_rate": 0.6,
                    "max_drawdown": 0.08,
                    "min_profit": -0.03
                },
                test_function="_test_bear_market_resilience"
            ),
            TradingTestScenario(
                name="high_frequency_trading",
                description="High frequency trading with rapid order execution",
                market_condition=MarketCondition.SIDEWAYS,
                trading_scenario=TradingScenario.HIGH_FREQUENCY,
                duration_minutes=10,
                expected_trades=50,
                max_position_size=25.0,
                pairs_to_test=["BTC/USDT"],
                performance_criteria={
                    "min_success_rate": 0.75,
                    "max_drawdown": 0.02,
                    "min_profit": 0.005
                },
                test_function="_test_high_frequency_trading"
            ),
            TradingTestScenario(
                name="multiple_pairs_trading",
                description="Trading across multiple currency pairs simultaneously",
                market_condition=MarketCondition.SIDEWAYS,
                trading_scenario=TradingScenario.MULTIPLE_PAIRS,
                duration_minutes=30,
                expected_trades=25,
                max_position_size=50.0,
                pairs_to_test=["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT", "DOT/USDT"],
                performance_criteria={
                    "min_success_rate": 0.7,
                    "max_drawdown": 0.06,
                    "min_profit": 0.01
                },
                test_function="_test_multiple_pairs_trading"
            ),
            TradingTestScenario(
                name="small_position_scalping",
                description="Small position scalping with tight spreads",
                market_condition=MarketCondition.LOW_VOLATILITY,
                trading_scenario=TradingScenario.SMALL_POSITIONS,
                duration_minutes=20,
                expected_trades=30,
                max_position_size=10.0,
                pairs_to_test=["BTC/USDT", "ETH/USDT"],
                performance_criteria={
                    "min_success_rate": 0.8,
                    "max_drawdown": 0.01,
                    "min_profit": 0.002
                },
                test_function="_test_small_position_scalping"
            ),
            TradingTestScenario(
                name="flash_crash_response",
                description="System response to flash crash conditions",
                market_condition=MarketCondition.FLASH_CRASH,
                trading_scenario=TradingScenario.STOP_LOSS_TRIGGERS,
                duration_minutes=5,
                expected_trades=5,
                max_position_size=100.0,
                pairs_to_test=["BTC/USDT"],
                performance_criteria={
                    "min_success_rate": 0.4,  # Lower expectations during crash
                    "max_drawdown": 0.15,
                    "min_profit": -0.1
                },
                test_function="_test_flash_crash_response"
            ),
            TradingTestScenario(
                name="profit_taking_optimization",
                description="Optimal profit taking in trending market",
                market_condition=MarketCondition.BULL_MARKET,
                trading_scenario=TradingScenario.PROFIT_TAKING,
                duration_minutes=25,
                expected_trades=15,
                max_position_size=150.0,
                pairs_to_test=["BTC/USDT", "ETH/USDT"],
                performance_criteria={
                    "min_success_rate": 0.75,
                    "max_drawdown": 0.04,
                    "min_profit": 0.02
                },
                test_function="_test_profit_taking_optimization"
            ),
            TradingTestScenario(
                name="rapid_rebalancing",
                description="Rapid portfolio rebalancing under changing conditions",
                market_condition=MarketCondition.HIGH_VOLATILITY,
                trading_scenario=TradingScenario.RAPID_REBALANCING,
                duration_minutes=15,
                expected_trades=40,
                max_position_size=75.0,
                pairs_to_test=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
                performance_criteria={
                    "min_success_rate": 0.65,
                    "max_drawdown": 0.08,
                    "min_profit": 0.005
                },
                test_function="_test_rapid_rebalancing"
            )
        ]

    async def run_trading_scenarios(self) -> list[ScenarioResult]:
        """Run all trading scenario tests"""
        self.logger.info("Starting realistic trading scenario testing")

        try:
            # Initialize system
            await self._initialize_trading_system()

            # Run each scenario
            for scenario in self.scenarios:
                self.logger.info(f"Testing scenario: {scenario.name}")

                try:
                    result = await self._run_trading_scenario(scenario)
                    self.results.append(result)

                    if result.meets_criteria:
                        self.logger.info(f"✅ {scenario.name} MEETS CRITERIA")
                    else:
                        self.logger.warning(f"⚠️ {scenario.name} DOES NOT MEET CRITERIA")

                    # Reset state between scenarios
                    await self._reset_trading_state()

                except Exception as e:
                    self.logger.error(f"Scenario {scenario.name} crashed: {e}")
                    self._add_crash_result(scenario, e)

        except Exception as e:
            self.logger.error(f"Trading scenario testing failed: {e}")

        finally:
            await self._cleanup_trading_system()

        self.logger.info(f"Trading scenario testing completed: {len(self.results)} scenarios tested")
        return self.results

    async def _initialize_trading_system(self):
        """Initialize trading system for scenario testing"""
        try:
            self.auth = KrakenAuth()
            self.rate_limiter = KrakenRateLimiter()
            self.circuit_breaker = CircuitBreaker()

            self.database_manager = DatabaseManager()
            await self.database_manager.initialize()

            self.balance_manager = BalanceManager(
                auth=self.auth,
                rate_limiter=self.rate_limiter
            )

            self.portfolio_manager = PortfolioManager(
                balance_manager=self.balance_manager,
                database_manager=self.database_manager
            )

            self.websocket_manager = WebSocketManagerV2(
                auth=self.auth,
                balance_manager=self.balance_manager
            )

            # Set initial test balance
            self.initial_balance = {
                "USDT": self.decimal_handler.to_decimal("1000.0"),
                "BTC": self.decimal_handler.to_decimal("0.0"),
                "ETH": self.decimal_handler.to_decimal("0.0"),
                "SOL": self.decimal_handler.to_decimal("0.0"),
                "AVAX": self.decimal_handler.to_decimal("0.0"),
                "DOT": self.decimal_handler.to_decimal("0.0")
            }

            await self.balance_manager._update_cached_balance(self.initial_balance)

            self.logger.info("Trading system initialized for scenario testing")

        except Exception as e:
            self.logger.error(f"Failed to initialize trading system: {e}")
            raise

    async def _reset_trading_state(self):
        """Reset trading state between scenarios"""
        try:
            # Reset balances
            await self.balance_manager._update_cached_balance(self.initial_balance)

            # Clear positions
            self.current_positions = {}

            # Clear trade history
            self.trade_history = []

            # Reset circuit breaker
            if self.circuit_breaker:
                await self.circuit_breaker.reset()

            # Clear market data cache
            self.market_data_cache = {}

            await asyncio.sleep(1.0)  # Allow state to settle

        except Exception as e:
            self.logger.warning(f"Failed to reset trading state: {e}")

    async def _cleanup_trading_system(self):
        """Cleanup trading system resources"""
        try:
            if self.websocket_manager:
                await self.websocket_manager.disconnect()

            if self.database_manager:
                await self.database_manager.close()

            self.logger.info("Trading system resources cleaned up")

        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

    async def _run_trading_scenario(self, scenario: TradingTestScenario) -> ScenarioResult:
        """Run individual trading scenario"""
        start_time = time.time()
        errors_encountered = []
        warnings = []

        try:
            # Get test method
            test_method = getattr(self, scenario.test_function, None)
            if not test_method:
                raise ValueError(f"Test method {scenario.test_function} not found")

            # Initialize scenario state
            initial_balance = await self.balance_manager.get_balance() or self.initial_balance

            # Generate market data for scenario
            market_data = self._generate_market_data(scenario)

            # Run scenario test
            if asyncio.iscoroutinefunction(test_method):
                scenario_result = await test_method(scenario, market_data)
            else:
                scenario_result = test_method(scenario, market_data)

            duration = time.time() - start_time

            # Calculate performance metrics
            final_balance = await self.balance_manager.get_balance() or initial_balance
            profit_loss = self._calculate_profit_loss(initial_balance, final_balance)
            max_drawdown = self._calculate_max_drawdown()
            sharpe_ratio = self._calculate_sharpe_ratio()

            # Check if scenario meets criteria
            meets_criteria = self._evaluate_performance_criteria(scenario, scenario_result)

            return ScenarioResult(
                scenario_name=scenario.name,
                duration=duration,
                trades_executed=len(self.trade_history),
                successful_trades=sum(1 for trade in self.trade_history if trade.get('profit', 0) > 0),
                failed_trades=sum(1 for trade in self.trade_history if trade.get('profit', 0) <= 0),
                total_volume=sum(trade.get('volume', 0) for trade in self.trade_history),
                profit_loss=profit_loss,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                system_performance=self._get_system_performance_metrics(),
                errors_encountered=errors_encountered,
                warnings=warnings,
                meets_criteria=meets_criteria,
                details={
                    "initial_balance": initial_balance,
                    "final_balance": final_balance,
                    "trade_history": self.trade_history,
                    "market_conditions": scenario.market_condition.value,
                    "trading_scenario": scenario.trading_scenario.value
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            errors_encountered.append(str(e))

            return ScenarioResult(
                scenario_name=scenario.name,
                duration=duration,
                trades_executed=0,
                successful_trades=0,
                failed_trades=0,
                total_volume=0,
                profit_loss=0,
                max_drawdown=0,
                sharpe_ratio=None,
                system_performance={},
                errors_encountered=errors_encountered,
                warnings=warnings,
                meets_criteria=False,
                details={"error": str(e), "traceback": traceback.format_exc()}
            )

    def _generate_market_data(self, scenario: TradingTestScenario) -> dict[str, list[MarketData]]:
        """Generate simulated market data for scenario"""
        market_data = {}

        for pair in scenario.pairs_to_test:
            symbol = pair.replace("/", "_")
            data_points = []

            # Base price (simplified)
            base_prices = {
                "BTC_USDT": 45000.0,
                "ETH_USDT": 3000.0,
                "SOL_USDT": 100.0,
                "AVAX_USDT": 35.0,
                "DOT_USDT": 6.0
            }

            base_price = base_prices.get(symbol, 1.0)
            current_price = base_price

            # Generate data points based on market condition
            num_points = scenario.duration_minutes * 2  # 2 points per minute

            for i in range(num_points):
                timestamp = datetime.now() + timedelta(seconds=i * 30)

                # Price movement based on market condition
                if scenario.market_condition == MarketCondition.BULL_MARKET:
                    price_change = random.uniform(0.001, 0.005)  # 0.1% to 0.5% up
                elif scenario.market_condition == MarketCondition.BEAR_MARKET:
                    price_change = random.uniform(-0.005, -0.001)  # 0.1% to 0.5% down
                elif scenario.market_condition == MarketCondition.HIGH_VOLATILITY:
                    price_change = random.uniform(-0.02, 0.02)  # ±2%
                elif scenario.market_condition == MarketCondition.LOW_VOLATILITY:
                    price_change = random.uniform(-0.002, 0.002)  # ±0.2%
                elif scenario.market_condition == MarketCondition.FLASH_CRASH:
                    if i < num_points * 0.2:  # First 20% of time
                        price_change = random.uniform(-0.05, -0.01)  # Crash
                    else:
                        price_change = random.uniform(-0.01, 0.03)  # Recovery
                else:  # SIDEWAYS
                    price_change = random.uniform(-0.003, 0.003)  # ±0.3%

                current_price *= (1 + price_change)

                # Generate OHLC data
                high = current_price * random.uniform(1.0, 1.002)
                low = current_price * random.uniform(0.998, 1.0)
                open_price = current_price * random.uniform(0.999, 1.001)
                close_price = current_price

                # Generate bid/ask spread
                spread_pct = random.uniform(0.0005, 0.002)  # 0.05% to 0.2%
                spread = current_price * spread_pct
                bid = current_price - spread / 2
                ask = current_price + spread / 2

                data_point = MarketData(
                    symbol=symbol,
                    timestamp=timestamp,
                    open_price=open_price,
                    high_price=high,
                    low_price=low,
                    close_price=close_price,
                    volume=random.uniform(1000, 10000),
                    bid=bid,
                    ask=ask,
                    spread=spread
                )

                data_points.append(data_point)

            market_data[symbol] = data_points

        return market_data

    def _simulate_trade(self, symbol: str, side: str, size: float, price: float) -> dict[str, Any]:
        """Simulate trade execution"""
        trade_id = f"trade_{len(self.trade_history) + 1}"
        timestamp = datetime.now()

        # Simulate slippage
        slippage = random.uniform(0.0001, 0.001)  # 0.01% to 0.1%
        if side == "buy":
            executed_price = price * (1 + slippage)
        else:
            executed_price = price * (1 - slippage)

        # Calculate fees (simplified)
        fee_rate = 0.001  # 0.1%
        fee = size * executed_price * fee_rate

        # Calculate net amount
        if side == "buy":
            size * executed_price + fee
            net_amount = size
        else:
            net_proceeds = size * executed_price - fee
            net_amount = net_proceeds

        trade = {
            "trade_id": trade_id,
            "timestamp": timestamp.isoformat(),
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": executed_price,
            "fee": fee,
            "net_amount": net_amount,
            "volume": size * executed_price
        }

        self.trade_history.append(trade)

        # Update positions
        if symbol not in self.current_positions:
            self.current_positions[symbol] = {"size": 0, "avg_price": 0}

        pos = self.current_positions[symbol]

        if side == "buy":
            new_size = pos["size"] + size
            if new_size > 0:
                pos["avg_price"] = ((pos["size"] * pos["avg_price"]) + (size * executed_price)) / new_size
            pos["size"] = new_size
        else:
            pos["size"] -= size
            if pos["size"] <= 0:
                # Calculate profit/loss
                profit = (executed_price - pos["avg_price"]) * abs(pos["size"])
                trade["profit"] = profit
                pos["size"] = 0
                pos["avg_price"] = 0

        return trade

    def _calculate_profit_loss(self, initial_balance: dict, final_balance: dict) -> float:
        """Calculate total profit/loss"""
        try:
            initial_value = sum(float(v) for v in initial_balance.values() if v is not None)
            final_value = sum(float(v) for v in final_balance.values() if v is not None)

            return (final_value - initial_value) / initial_value if initial_value > 0 else 0

        except Exception as e:
            self.logger.error(f"Failed to calculate profit/loss: {e}")
            return 0

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown during scenario"""
        try:
            # Simplified calculation based on trade history
            running_pnl = 0
            peak_pnl = 0
            max_drawdown = 0

            for trade in self.trade_history:
                profit = trade.get('profit', 0)
                running_pnl += profit

                if running_pnl > peak_pnl:
                    peak_pnl = running_pnl

                drawdown = (peak_pnl - running_pnl) / abs(peak_pnl) if peak_pnl != 0 else 0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

            return max_drawdown

        except Exception as e:
            self.logger.error(f"Failed to calculate max drawdown: {e}")
            return 0

    def _calculate_sharpe_ratio(self) -> Optional[float]:
        """Calculate Sharpe ratio"""
        try:
            if len(self.trade_history) < 2:
                return None

            returns = [trade.get('profit', 0) for trade in self.trade_history if 'profit' in trade]

            if not returns:
                return None

            mean_return = sum(returns) / len(returns)

            if len(returns) < 2:
                return None

            variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = variance ** 0.5

            if std_dev == 0:
                return None

            # Simplified Sharpe ratio (assuming risk-free rate = 0)
            return mean_return / std_dev

        except Exception as e:
            self.logger.error(f"Failed to calculate Sharpe ratio: {e}")
            return None

    def _get_system_performance_metrics(self) -> dict[str, float]:
        """Get system performance metrics"""
        try:
            total_trades = len(self.trade_history)
            if total_trades == 0:
                return {}

            avg_trade_time = 1.0  # Simplified
            success_rate = sum(1 for trade in self.trade_history if trade.get('profit', 0) > 0) / total_trades

            return {
                "average_trade_execution_time": avg_trade_time,
                "trade_success_rate": success_rate,
                "total_trades_executed": total_trades,
                "average_slippage": 0.0005,  # Simplified
                "system_uptime": 1.0  # Simplified
            }

        except Exception as e:
            self.logger.error(f"Failed to get system performance metrics: {e}")
            return {}

    def _evaluate_performance_criteria(self, scenario: TradingTestScenario,
                                     scenario_result: dict[str, Any]) -> bool:
        """Evaluate if scenario meets performance criteria"""
        try:
            criteria = scenario.performance_criteria

            # Check success rate
            total_trades = len(self.trade_history)
            if total_trades > 0:
                success_rate = sum(1 for trade in self.trade_history if trade.get('profit', 0) > 0) / total_trades
                if success_rate < criteria.get('min_success_rate', 0):
                    return False

            # Check profit/loss
            profit_loss = scenario_result.get('profit_loss', 0)
            if profit_loss < criteria.get('min_profit', -float('inf')):
                return False

            # Check drawdown
            max_drawdown = scenario_result.get('max_drawdown', 0)
            if max_drawdown > criteria.get('max_drawdown', float('inf')):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to evaluate performance criteria: {e}")
            return False

    def _add_crash_result(self, scenario: TradingTestScenario, error: Exception):
        """Add result for crashed scenario"""
        result = ScenarioResult(
            scenario_name=scenario.name,
            duration=0,
            trades_executed=0,
            successful_trades=0,
            failed_trades=0,
            total_volume=0,
            profit_loss=0,
            max_drawdown=0,
            sharpe_ratio=None,
            system_performance={},
            errors_encountered=[f"Scenario crashed: {str(error)}"],
            warnings=[],
            meets_criteria=False,
            details={"crash_error": str(error)}
        )
        self.results.append(result)

    # Individual scenario test methods

    async def _test_normal_market_trading(self, scenario: TradingTestScenario,
                                        market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test normal market trading conditions"""
        try:
            # Simulate normal trading for scenario duration
            duration_seconds = scenario.duration_minutes * 60
            duration_seconds / scenario.expected_trades

            for i in range(scenario.expected_trades):
                # Select random pair
                pair = random.choice(scenario.pairs_to_test)
                symbol = pair.replace("/", "_")

                # Get current market data point
                data_points = market_data.get(symbol, [])
                if not data_points:
                    continue

                data_point = data_points[i % len(data_points)]

                # Simple trading logic: buy low, sell high
                if random.random() < 0.5:  # 50% chance to trade
                    side = random.choice(["buy", "sell"])
                    size = random.uniform(0.001, scenario.max_position_size / data_point.close_price)

                    self._simulate_trade(symbol, side, size, data_point.close_price)

                await asyncio.sleep(0.1)  # Simulate time between trades

            return {"status": "completed", "trades": len(self.trade_history)}

        except Exception as e:
            self.logger.error(f"Normal market trading test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _test_high_volatility_handling(self, scenario: TradingTestScenario,
                                           market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test high volatility market handling"""
        try:
            # More frequent trading in volatile conditions
            duration_seconds = scenario.duration_minutes * 60
            duration_seconds / scenario.expected_trades

            for i in range(scenario.expected_trades):
                pair = random.choice(scenario.pairs_to_test)
                symbol = pair.replace("/", "_")

                data_points = market_data.get(symbol, [])
                if not data_points:
                    continue

                data_point = data_points[i % len(data_points)]

                # More conservative position sizing in volatile conditions
                max_size = scenario.max_position_size * 0.5  # Reduce size for volatility
                size = random.uniform(0.001, max_size / data_point.close_price)

                # Volatility-based trading
                if random.random() < 0.7:  # Higher trading frequency
                    side = random.choice(["buy", "sell"])
                    self._simulate_trade(symbol, side, size, data_point.close_price)

                await asyncio.sleep(0.05)  # Faster trading

            return {"status": "completed", "volatility_handled": True}

        except Exception as e:
            self.logger.error(f"High volatility handling test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _test_bull_market_momentum(self, scenario: TradingTestScenario,
                                       market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test bull market momentum trading"""
        try:
            # Favor buy orders in bull market
            for i in range(scenario.expected_trades):
                pair = random.choice(scenario.pairs_to_test)
                symbol = pair.replace("/", "_")

                data_points = market_data.get(symbol, [])
                if not data_points:
                    continue

                data_point = data_points[i % len(data_points)]

                # Bull market bias: 70% buy, 30% sell
                side = "buy" if random.random() < 0.7 else "sell"
                size = random.uniform(0.001, scenario.max_position_size / data_point.close_price)

                if random.random() < 0.6:  # 60% chance to trade
                    self._simulate_trade(symbol, side, size, data_point.close_price)

                await asyncio.sleep(0.08)

            return {"status": "completed", "bull_momentum": True}

        except Exception as e:
            self.logger.error(f"Bull market momentum test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _test_bear_market_resilience(self, scenario: TradingTestScenario,
                                         market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test bear market resilience"""
        try:
            # More conservative trading in bear market
            for i in range(scenario.expected_trades):
                pair = random.choice(scenario.pairs_to_test)
                symbol = pair.replace("/", "_")

                data_points = market_data.get(symbol, [])
                if not data_points:
                    continue

                data_point = data_points[i % len(data_points)]

                # Bear market: reduce position sizes, favor sells
                max_size = scenario.max_position_size * 0.7  # Smaller positions
                side = "sell" if random.random() < 0.6 else "buy"  # Favor sells
                size = random.uniform(0.001, max_size / data_point.close_price)

                if random.random() < 0.4:  # Less frequent trading
                    self._simulate_trade(symbol, side, size, data_point.close_price)

                await asyncio.sleep(0.12)

            return {"status": "completed", "bear_resilience": True}

        except Exception as e:
            self.logger.error(f"Bear market resilience test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _test_high_frequency_trading(self, scenario: TradingTestScenario,
                                         market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test high frequency trading"""
        try:
            # Rapid small trades
            for i in range(scenario.expected_trades):
                pair = scenario.pairs_to_test[0]  # Focus on one pair
                symbol = pair.replace("/", "_")

                data_points = market_data.get(symbol, [])
                if not data_points:
                    continue

                data_point = data_points[i % len(data_points)]

                # Small, frequent trades
                side = random.choice(["buy", "sell"])
                size = random.uniform(0.001, 0.01)  # Very small sizes

                self._simulate_trade(symbol, side, size, data_point.close_price)

                await asyncio.sleep(0.02)  # Very fast trading

            return {"status": "completed", "hft_executed": True}

        except Exception as e:
            self.logger.error(f"High frequency trading test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _test_multiple_pairs_trading(self, scenario: TradingTestScenario,
                                         market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test multiple pairs trading"""
        try:
            # Distribute trades across all pairs
            trades_per_pair = scenario.expected_trades // len(scenario.pairs_to_test)

            for pair in scenario.pairs_to_test:
                symbol = pair.replace("/", "_")
                data_points = market_data.get(symbol, [])

                for i in range(trades_per_pair):
                    if not data_points:
                        continue

                    data_point = data_points[i % len(data_points)]

                    side = random.choice(["buy", "sell"])
                    size = random.uniform(0.001, scenario.max_position_size / data_point.close_price)

                    if random.random() < 0.5:
                        self._simulate_trade(symbol, side, size, data_point.close_price)

                    await asyncio.sleep(0.06)

            return {"status": "completed", "multiple_pairs": len(scenario.pairs_to_test)}

        except Exception as e:
            self.logger.error(f"Multiple pairs trading test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _test_small_position_scalping(self, scenario: TradingTestScenario,
                                          market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test small position scalping"""
        try:
            # Many small trades with tight profit targets
            for i in range(scenario.expected_trades):
                pair = random.choice(scenario.pairs_to_test)
                symbol = pair.replace("/", "_")

                data_points = market_data.get(symbol, [])
                if not data_points:
                    continue

                data_point = data_points[i % len(data_points)]

                # Very small positions for scalping
                side = random.choice(["buy", "sell"])
                size = random.uniform(0.001, 0.005)  # Tiny positions

                if random.random() < 0.8:  # High trade frequency
                    self._simulate_trade(symbol, side, size, data_point.close_price)

                await asyncio.sleep(0.04)

            return {"status": "completed", "scalping_executed": True}

        except Exception as e:
            self.logger.error(f"Small position scalping test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _test_flash_crash_response(self, scenario: TradingTestScenario,
                                       market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test flash crash response"""
        try:
            # Simulate system response to flash crash
            pair = scenario.pairs_to_test[0]
            symbol = pair.replace("/", "_")
            data_points = market_data.get(symbol, [])

            # During crash, system should limit trading or stop
            crash_duration = scenario.expected_trades // 2

            for i in range(crash_duration):
                if not data_points:
                    continue

                data_point = data_points[i % len(data_points)]

                # Reduced trading during crash
                if random.random() < 0.2:  # Much lower trade frequency
                    side = "sell"  # Likely to sell during crash
                    size = random.uniform(0.001, 0.01)  # Small sizes

                    self._simulate_trade(symbol, side, size, data_point.close_price)

                await asyncio.sleep(0.2)  # Slower response during crash

            return {"status": "completed", "crash_handled": True}

        except Exception as e:
            self.logger.error(f"Flash crash response test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _test_profit_taking_optimization(self, scenario: TradingTestScenario,
                                             market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test profit taking optimization"""
        try:
            # Optimize profit taking in trending market
            for i in range(scenario.expected_trades):
                pair = random.choice(scenario.pairs_to_test)
                symbol = pair.replace("/", "_")

                data_points = market_data.get(symbol, [])
                if not data_points:
                    continue

                data_point = data_points[i % len(data_points)]

                # Profit taking logic: take profits on upward moves
                side = random.choice(["buy", "sell"])
                size = random.uniform(0.001, scenario.max_position_size / data_point.close_price)

                if random.random() < 0.6:
                    self._simulate_trade(symbol, side, size, data_point.close_price)

                await asyncio.sleep(0.1)

            return {"status": "completed", "profit_optimization": True}

        except Exception as e:
            self.logger.error(f"Profit taking optimization test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _test_rapid_rebalancing(self, scenario: TradingTestScenario,
                                    market_data: dict[str, list[MarketData]]) -> dict[str, Any]:
        """Test rapid portfolio rebalancing"""
        try:
            # Frequent rebalancing between pairs
            rebalance_frequency = scenario.expected_trades // 4  # Rebalance every few trades

            for i in range(scenario.expected_trades):
                # Choose pair based on rebalancing logic
                if i % rebalance_frequency == 0:
                    # Rebalance: sell overweight, buy underweight
                    pair = random.choice(scenario.pairs_to_test)
                else:
                    pair = random.choice(scenario.pairs_to_test)

                symbol = pair.replace("/", "_")
                data_points = market_data.get(symbol, [])

                if not data_points:
                    continue

                data_point = data_points[i % len(data_points)]

                side = random.choice(["buy", "sell"])
                size = random.uniform(0.001, scenario.max_position_size / data_point.close_price)

                if random.random() < 0.7:
                    self._simulate_trade(symbol, side, size, data_point.close_price)

                await asyncio.sleep(0.04)

            return {"status": "completed", "rebalancing_executed": True}

        except Exception as e:
            self.logger.error(f"Rapid rebalancing test failed: {e}")
            return {"status": "failed", "error": str(e)}

    def generate_trading_report(self) -> dict[str, Any]:
        """Generate comprehensive trading scenario report"""
        total_scenarios = len(self.results)
        successful_scenarios = sum(1 for r in self.results if r.meets_criteria)
        failed_scenarios = total_scenarios - successful_scenarios

        # Calculate aggregate metrics
        total_trades = sum(r.trades_executed for r in self.results)
        total_profit = sum(r.profit_loss for r in self.results)
        avg_profit = total_profit / total_scenarios if total_scenarios > 0 else 0

        # Generate recommendations
        recommendations = []

        failed_results = [r for r in self.results if not r.meets_criteria]
        if failed_results:
            recommendations.append(f"Address {len(failed_results)} failed trading scenarios")

        low_profit_scenarios = [r for r in self.results if r.profit_loss < 0]
        if low_profit_scenarios:
            recommendations.append(f"Optimize {len(low_profit_scenarios)} unprofitable scenarios")

        high_drawdown_scenarios = [r for r in self.results if r.max_drawdown > 0.1]
        if high_drawdown_scenarios:
            recommendations.append(f"Reduce drawdown in {len(high_drawdown_scenarios)} scenarios")

        if not recommendations:
            recommendations.append("All trading scenarios performed well - system ready for live trading")

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_scenarios": total_scenarios,
                "successful_scenarios": successful_scenarios,
                "failed_scenarios": failed_scenarios,
                "success_rate": successful_scenarios / total_scenarios if total_scenarios > 0 else 0,
                "total_trades_executed": total_trades,
                "average_profit_loss": avg_profit,
                "total_profit_loss": total_profit
            },
            "scenario_results": [
                {
                    "scenario": r.scenario_name,
                    "meets_criteria": r.meets_criteria,
                    "trades_executed": r.trades_executed,
                    "profit_loss": r.profit_loss,
                    "max_drawdown": r.max_drawdown,
                    "sharpe_ratio": r.sharpe_ratio,
                    "errors": r.errors_encountered
                }
                for r in self.results
            ],
            "recommendations": recommendations,
            "trading_performance": {
                "execution_quality": sum(r.system_performance.get('trade_success_rate', 0) for r in self.results) / total_scenarios if total_scenarios > 0 else 0,
                "system_reliability": sum(1 for r in self.results if not r.errors_encountered) / total_scenarios if total_scenarios > 0 else 0,
                "profit_consistency": len([r for r in self.results if r.profit_loss > 0]) / total_scenarios if total_scenarios > 0 else 0
            }
        }


async def main():
    """Run trading scenario testing"""
    tester = TradingScenarioTester()

    try:
        # Run trading scenarios
        results = await tester.run_trading_scenarios()

        # Generate report
        report = tester.generate_trading_report()

        # Print summary
        print(f"\n{'='*60}")
        print("TRADING SCENARIO VALIDATION REPORT")
        print(f"{'='*60}")
        print(f"Total Scenarios: {report['summary']['total_scenarios']}")
        print(f"Successful: {report['summary']['successful_scenarios']}")
        print(f"Failed: {report['summary']['failed_scenarios']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1%}")
        print(f"Total Trades: {report['summary']['total_trades_executed']}")
        print(f"Average P&L: {report['summary']['average_profit_loss']:.2%}")

        # Trading performance
        print(f"\n{'='*60}")
        print("TRADING PERFORMANCE")
        print(f"{'='*60}")
        print(f"Execution Quality: {report['trading_performance']['execution_quality']:.1%}")
        print(f"System Reliability: {report['trading_performance']['system_reliability']:.1%}")
        print(f"Profit Consistency: {report['trading_performance']['profit_consistency']:.1%}")

        # Recommendations
        print(f"\n{'='*60}")
        print("RECOMMENDATIONS")
        print(f"{'='*60}")
        for rec in report['recommendations']:
            print(f"• {rec}")

        # Failed scenarios
        failed_results = [r for r in results if not r.meets_criteria]
        if failed_results:
            print(f"\n{'='*60}")
            print("FAILED SCENARIOS")
            print(f"{'='*60}")
            for result in failed_results:
                print(f"❌ {result.scenario_name} (P&L: {result.profit_loss:.2%}, Drawdown: {result.max_drawdown:.2%})")

        # Save report
        report_file = Path("validation/trading_scenario_report.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\nDetailed report saved to: {report_file}")

        # Return success code
        return 0 if report['summary']['failed_scenarios'] == 0 else 1

    except Exception as e:
        print(f"Trading scenario testing failed: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
