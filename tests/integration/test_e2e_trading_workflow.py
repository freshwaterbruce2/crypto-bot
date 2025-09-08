#!/usr/bin/env python3
"""
End-to-End Trading Workflow Tests
Complete trading lifecycle from market signal to order execution and state management
"""

import asyncio
import pytest
import time
import json
from decimal import Decimal
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile

from engine.trading.trading_config import TradingConfig
from engine.market_data.market_data_processor import MarketDataProcessor
from engine.risk_manager_enhanced import EnhancedRiskManager
from engine.order_execution.order_executor import OrderExecutor
from engine.state.state_manager import StateManager
from engine.config.config_manager import ConfigManager
from engine.risk.circuit_breaker import CircuitBreaker


class MockTradingEnvironment:
    """Complete mock trading environment for E2E testing"""

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "test_config.json"
        self.state_file = self.temp_dir / "test_state.json"

        # Market data simulation
        self.current_price = Decimal("0.35")
        self.price_history = [self.current_price]
        self.volatility = Decimal("0.015")
        self.spread = Decimal("0.001")

        # Account simulation
        self.account_balance = {"XXLM": "1000.0", "ZUSD": "500.0"}
        self.open_orders = {}
        self.order_history = []
        self.trade_history = []

        # Risk tracking
        self.daily_pnl = Decimal("0.0")
        self.consecutive_losses = 0

    def generate_market_update(self) -> Dict[str, Any]:
        """Generate realistic market data update"""
        # Simulate price movement with some randomness
        price_change = Decimal(
            str((time.time() % 10 - 5) * 0.0001)
        )  # Small random movement
        self.current_price += price_change
        self.price_history.append(self.current_price)

        # Keep history manageable
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]

        return {
            "symbol": "XLM/USD",
            "last_price": str(self.current_price),
            "bid": str(self.current_price - self.spread / 2),
            "ask": str(self.current_price + self.spread / 2),
            "volume": "15000.0",
            "timestamp": str(time.time()),
        }

    def simulate_order_fill(self, order_id: str, side: str, quantity: str, price: str):
        """Simulate order execution"""
        if order_id in self.open_orders:
            order = self.open_orders[order_id]
            order["status"] = "filled"
            order["filled_quantity"] = quantity
            order["filled_price"] = price
            order["fill_timestamp"] = str(time.time())

            # Update account balance
            qty_decimal = Decimal(quantity)
            price_decimal = Decimal(price)

            if side == "buy":
                cost = qty_decimal * price_decimal * Decimal("1.0026")  # Include fee
                self.account_balance["ZUSD"] = str(
                    Decimal(self.account_balance["ZUSD"]) - cost
                )
                self.account_balance["XXLM"] = str(
                    Decimal(self.account_balance["XXLM"]) + qty_decimal
                )
            elif side == "sell":
                revenue = qty_decimal * price_decimal * Decimal("0.9974")  # Include fee
                self.account_balance["XXLM"] = str(
                    Decimal(self.account_balance["XXLM"]) - qty_decimal
                )
                self.account_balance["ZUSD"] = str(
                    Decimal(self.account_balance["ZUSD"]) + revenue
                )

            # Record trade
            pnl_val = Decimal(
                self.calculate_pnl(order, side, qty_decimal, price_decimal)
            )
            # Accumulate daily P&L
            self.daily_pnl += pnl_val

            trade = {
                "order_id": order_id,
                "side": side,
                "quantity": quantity,
                "price": price,
                "timestamp": str(time.time()),
                "pnl": str(pnl_val),
            }
            self.trade_history.append(trade)

            return trade
        return None

    def calculate_pnl(
        self, order: Dict, side: str, qty: Decimal, price: Decimal
    ) -> str:
        """Calculate P&L for a trade"""
        # Simplified P&L calculation
        if side == "buy":
            return "0.0"  # Entry trade, no P&L yet
        else:
            # For sell orders, calculate profit/loss
            entry_price = Decimal(order.get("price", "0"))
            pnl = (price - entry_price) * qty
            return str(pnl)

    def get_account_summary(self) -> Dict[str, Any]:
        """Get current account summary"""
        total_value = Decimal(
            self.account_balance["XXLM"]
        ) * self.current_price + Decimal(self.account_balance["ZUSD"])

        return {
            "balance": self.account_balance.copy(),
            "total_value_usd": str(total_value),
            "daily_pnl": str(self.daily_pnl),
            "open_orders": len(self.open_orders),
            "total_trades": len(self.trade_history),
        }


@pytest.fixture
def trading_environment():
    """Setup complete trading environment for E2E testing"""
    env = MockTradingEnvironment()

    # Create test configuration matching trading_config schema
    config_data = {
        "pair": "XLM/USD",
        "kraken_pair": "XXLMZUSD",
        "profit_target": 0.007,
        "stop_loss": -0.004,
        "minimum_order": 12.0,
        "max_position_size_xlm": 100.0,
        "taker_fee_rate": 0.0026,
        "maker_fee_rate": 0.0016,
    }

    with open(env.config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    # Initialize components
    config_manager = ConfigManager()
    # Point ConfigManager to the test config file and load consolidated config
    config_manager.config_files = {
        "trading_config": Path(str(env.config_file)),
    }
    asyncio.get_event_loop().run_until_complete(
        config_manager.load_consolidated_config()
    )

    trading_config = TradingConfig()
    trading_config.risk_manager_type = "enhanced"

    # Mock external dependencies
    with (
        patch("src.exchange.kraken_ws_client_unified.KrakenWebSocketUnified"),
        patch("src.exchange.kraken_rest_client.KrakenRESTClient"),
    ):
        market_processor = MarketDataProcessor(trading_config, config_manager)
        risk_manager = EnhancedRiskManager(trading_config, config_manager)
        circuit_breaker = CircuitBreaker()
        order_executor = OrderExecutor(trading_config, config_manager, circuit_breaker)
        state_manager = StateManager(
            str(env.state_file), trading_config, config_manager
        )

        # Provide a mocked REST client that records created orders into env.open_orders
        async def _mock_place_order(**kwargs):
            # generate a pseudo txid
            txid = f"INT_{int(time.time() * 1000)}"
            # record order in env.open_orders for simulation
            env.open_orders[txid] = {
                "symbol": kwargs.get("pair"),
                "side": kwargs.get("type") or kwargs.get("ordertype") or "buy",
                "price": kwargs.get("price"),
                "quantity": kwargs.get("volume"),
                "status": "pending",
                "timestamp": str(time.time()),
            }
            return {"txid": [txid], "descr": {"order": "mocked"}}

        mock_rest = AsyncMock()
        mock_rest.place_order.side_effect = _mock_place_order
        order_executor.rest_client = mock_rest

    asyncio.get_event_loop().run_until_complete(state_manager.load_state())

    # Return environment dict (tests expect a direct dict)
    return {
        "env": env,
        "config_manager": config_manager,
        "trading_config": trading_config,
        "market_processor": market_processor,
        "risk_manager": risk_manager,
        "order_executor": order_executor,
        "state_manager": state_manager,
    }


class TestE2ETradingWorkflow:
    """End-to-end trading workflow test suite"""

    @pytest.mark.asyncio
    async def test_complete_buy_order_workflow(self, trading_environment):
        """Test complete buy order workflow from signal to execution"""
        setup = trading_environment
        env = setup["env"]

        # Step 1: Market Data Reception
        market_update = env.generate_market_update()
        success = setup["market_processor"].process_message(
            {"channel": "ticker", "type": "update", "data": [market_update]}
        )
        assert success

        # Step 2: Risk Assessment
        market_data = setup["market_processor"].get_current_market_data()
        account_balance = Decimal(env.account_balance["ZUSD"])

        approved, reason, risk_metrics = await setup[
            "risk_manager"
        ].evaluate_trade_risk_enhanced(
            position_size=Decimal("25.0"),
            entry_price=market_data["last_price"],
            account_balance=account_balance,
            market_data=market_data,
        )

        assert approved, f"Risk check failed: {reason}"

        # Step 3: Order Placement
        order_result = await setup["order_executor"].execute_order(
            order_type="buy", volume="25.0", price=str(market_data["last_price"])
        )

        assert "order_id" in order_result

        # Step 4: Order Fill Simulation
        trade = env.simulate_order_fill(
            order_result["order_id"], "buy", "25.0", str(market_data["last_price"])
        )
        assert trade is not None

        # Step 5: State Update
        setup["state_manager"].update_market_data_state(market_data)
        await setup["state_manager"].persist_state()

        # Step 6: Verify Final State
        account_summary = env.get_account_summary()
        assert Decimal(account_summary["balance"]["XXLM"]) > Decimal(
            "1000.0"
        )  # Position increased
        assert Decimal(account_summary["balance"]["ZUSD"]) < Decimal(
            "500.0"
        )  # Balance decreased

    @pytest.mark.asyncio
    async def test_buy_sell_round_trip_workflow(self, trading_environment):
        """Test complete buy-sell round trip workflow"""
        setup = trading_environment
        env = setup["env"]

        # === BUY ORDER ===
        market_update = env.generate_market_update()
        setup["market_processor"].process_message(
            {"channel": "ticker", "type": "update", "data": [market_update]}
        )

        market_data = setup["market_processor"].get_current_market_data()

        # Buy order
        approved, _, _ = await setup["risk_manager"].evaluate_trade_risk_enhanced(
            position_size=Decimal("20.0"),
            entry_price=market_data["last_price"],
            account_balance=Decimal(env.account_balance["ZUSD"]),
            market_data=market_data,
        )
        assert approved

        buy_order = await setup["order_executor"].execute_order(
            order_type="buy", volume="20.0", price=str(market_data["last_price"])
        )

        env.simulate_order_fill(
            buy_order["order_id"], "buy", "20.0", str(market_data["last_price"])
        )

        # === PRICE MOVEMENT SIMULATION ===
        # Simulate price increase for profit
        env.current_price *= Decimal("1.01")  # 1% price increase

        # === SELL ORDER ===
        market_update = env.generate_market_update()
        setup["market_processor"].process_message(
            {"channel": "ticker", "type": "update", "data": [market_update]}
        )

        market_data = setup["market_processor"].get_current_market_data()

        # Sell order
        sell_approved, _, _ = await setup["risk_manager"].evaluate_trade_risk_enhanced(
            position_size=Decimal("20.0"),
            entry_price=market_data["last_price"],
            account_balance=Decimal(env.account_balance["ZUSD"]),
            market_data=market_data,
        )

        if sell_approved:  # Risk check might reject if conditions changed
            sell_order = await setup["order_executor"].execute_order(
                order_type="sell", volume="20.0", price=str(market_data["last_price"])
            )

            trade = env.simulate_order_fill(
                sell_order["order_id"], "sell", "20.0", str(market_data["last_price"])
            )

            # Verify round trip
            account_summary = env.get_account_summary()
            assert Decimal(account_summary["daily_pnl"]) != 0  # Should have P&L

    @pytest.mark.asyncio
    async def test_risk_rejection_workflow(self, trading_environment):
        """Test workflow when risk management rejects a trade"""
        setup = trading_environment
        env = setup["env"]

        # Setup high-risk conditions
        env.volatility = Decimal("0.05")  # Very high volatility
        env.spread = Decimal("0.005")  # Wide spread

        # Generate market data with high risk
        market_update = env.generate_market_update()
        setup["market_processor"].process_message(
            {"channel": "ticker", "type": "update", "data": [market_update]}
        )

        market_data = setup["market_processor"].get_current_market_data()

        # Attempt high-risk trade
        approved, reason, risk_metrics = await setup[
            "risk_manager"
        ].evaluate_trade_risk_enhanced(
            position_size=Decimal("50.0"),  # Large position
            entry_price=market_data["last_price"],
            account_balance=Decimal("100.0"),  # Small balance
            market_data=market_data,
        )

        # Should be rejected due to high risk
        assert not approved
        assert len(reason) > 0
        assert risk_metrics["market_condition_risk"] > Decimal("1.0")

        # Verify no order was placed
        assert len(env.open_orders) == 0
        assert len(env.trade_history) == 0

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, trading_environment):
        """Test error recovery and system resilience"""
        setup = trading_environment
        env = setup["env"]

        # Step 1: Normal operation
        market_update = env.generate_market_update()
        setup["market_processor"].process_message(
            {"channel": "ticker", "type": "update", "data": [market_update]}
        )

        # Step 2: Simulate connection failure
        with patch.object(
            setup["market_processor"],
            "process_message",
            side_effect=Exception("Connection lost"),
        ):
            try:
                setup["market_processor"].process_message(
                    {"channel": "ticker", "type": "update", "data": [{}]}
                )
            except Exception:
                pass  # Expected to fail

        # Step 3: Verify system continues to function
        market_data = setup["market_processor"].get_current_market_data()
        assert market_data["last_price"] > 0  # Should still have previous data

        # Step 4: Test risk evaluation still works
        approved, reason, _ = await setup["risk_manager"].evaluate_trade_risk_enhanced(
            position_size=Decimal("10.0"),
            entry_price=market_data["last_price"],
            account_balance=Decimal(env.account_balance["ZUSD"]),
            market_data=market_data,
        )

        assert isinstance(approved, bool)  # Should not crash

    @pytest.mark.asyncio
    async def test_state_persistence_workflow(self, trading_environment):
        """Test state persistence across system restart"""
        setup = trading_environment
        env = setup["env"]

        # Step 1: Execute some trading activity
        market_update = env.generate_market_update()
        setup["market_processor"].process_message(
            {"channel": "ticker", "type": "update", "data": [market_update]}
        )

        market_data = setup["market_processor"].get_current_market_data()

        # Execute a trade
        approved, _, _ = await setup["risk_manager"].evaluate_trade_risk_enhanced(
            position_size=Decimal("15.0"),
            entry_price=market_data["last_price"],
            account_balance=Decimal(env.account_balance["ZUSD"]),
            market_data=market_data,
        )
        assert approved

        order = await setup["order_executor"].execute_order(
            order_type="buy", volume="15.0", price=str(market_data["last_price"])
        )

        env.simulate_order_fill(
            order["order_id"], "buy", "15.0", str(market_data["last_price"])
        )

        # Step 2: Persist state
        await setup["state_manager"].update_market_data_state(market_data)
        await setup["state_manager"].persist_state()

        # Step 3: Simulate system restart
        new_state_manager = StateManager(
            str(env.state_file), setup["trading_config"], setup["config_manager"]
        )
        await new_state_manager.load_state()

        # Step 4: Verify state recovery
        recovered_market_data = await new_state_manager.get_market_data_state()
        assert "last_price" in recovered_market_data
        assert recovered_market_data["last_price"] == market_data["last_price"]

    @pytest.mark.asyncio
    async def test_performance_workflow_under_load(self, trading_environment):
        """Test complete workflow performance under load"""
        setup = trading_environment
        env = setup["env"]

        # Test parameters
        num_iterations = 20
        total_start_time = time.time()

        performance_results = {
            "market_data_processing": [],
            "risk_evaluation": [],
            "order_execution": [],
            "state_updates": [],
        }

        for i in range(num_iterations):
            # Market data processing
            start_time = time.time()
            market_update = env.generate_market_update()
            setup["market_processor"].process_message(
                {"channel": "ticker", "type": "update", "data": [market_update]}
            )
            performance_results["market_data_processing"].append(
                time.time() - start_time
            )

            # Risk evaluation
            market_data = setup["market_processor"].get_current_market_data()
            start_time = time.time()
            approved, _, _ = await setup["risk_manager"].evaluate_trade_risk_enhanced(
                position_size=Decimal("10.0"),
                entry_price=market_data["last_price"],
                account_balance=Decimal(env.account_balance["ZUSD"]),
                market_data=market_data,
            )
            performance_results["risk_evaluation"].append(time.time() - start_time)

            if approved:
                # Order execution
                start_time = time.time()
                order = await setup["order_executor"].execute_order(
                    order_type="buy" if i % 2 == 0 else "sell",
                    volume="10.0",
                    price=str(market_data["last_price"]),
                )
                performance_results["order_execution"].append(time.time() - start_time)

                # Simulate fill
                if order["order_id"]:
                    env.simulate_order_fill(
                        order["order_id"],
                        "buy" if i % 2 == 0 else "sell",
                        "10.0",
                        str(market_data["last_price"]),
                    )

            # State update
            start_time = time.time()
            setup["state_manager"].update_market_data_state(market_data)
            await setup["state_manager"].persist_state()
            performance_results["state_updates"].append(time.time() - start_time)

        total_time = time.time() - total_start_time

        # Performance assertions
        avg_market_data_time = sum(performance_results["market_data_processing"]) / len(
            performance_results["market_data_processing"]
        )
        avg_risk_time = sum(performance_results["risk_evaluation"]) / len(
            performance_results["risk_evaluation"]
        )
        avg_order_time = (
            sum(performance_results["order_execution"])
            / len(performance_results["order_execution"])
            if performance_results["order_execution"]
            else 0
        )
        avg_state_time = sum(performance_results["state_updates"]) / len(
            performance_results["state_updates"]
        )

        # Performance requirements
        assert avg_market_data_time < 0.01  # < 10ms per market data update
        assert avg_risk_time < 0.05  # < 50ms per risk evaluation
        assert avg_order_time < 0.1  # < 100ms per order execution
        assert avg_state_time < 0.02  # < 20ms per state update
        assert total_time < 10.0  # < 10 seconds for 20 iterations

    @pytest.mark.asyncio
    async def test_multi_step_trading_strategy(self, trading_environment):
        """Test multi-step trading strategy execution"""
        setup = trading_environment
        env = setup["env"]

        # Strategy: Scale into position with multiple orders
        total_target_size = Decimal("50.0")
        executed_size = Decimal("0.0")
        orders = []

        for step in range(3):  # 3-step scaling
            step_size = total_target_size / 3

            # Get current market data
            market_update = env.generate_market_update()
            setup["market_processor"].process_message(
                {"channel": "ticker", "type": "update", "data": [market_update]}
            )

            market_data = setup["market_processor"].get_current_market_data()

            # Risk check for this step
            approved, _, _ = await setup["risk_manager"].evaluate_trade_risk_enhanced(
                position_size=step_size,
                entry_price=market_data["last_price"],
                account_balance=Decimal(env.account_balance["ZUSD"]),
                market_data=market_data,
            )

            if approved:
                # Execute order
                order = await setup["order_executor"].execute_order(
                    order_type="buy",
                    volume=str(step_size),
                    price=str(market_data["last_price"]),
                )

                # Simulate fill
                env.simulate_order_fill(
                    order["order_id"],
                    "buy",
                    str(step_size),
                    str(market_data["last_price"]),
                )

                executed_size += step_size
                orders.append(order)

            # Small delay between orders
            await asyncio.sleep(0.1)

        # Verify scaling strategy execution
        assert len(orders) > 0
        assert executed_size > 0
        account_summary = env.get_account_summary()
        assert (
            Decimal(account_summary["balance"]["XXLM"])
            >= Decimal("1000.0") + executed_size
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
