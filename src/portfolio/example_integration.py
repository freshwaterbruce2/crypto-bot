"""
Portfolio Management System - Integration Example
===============================================

Example showing how to integrate and use the portfolio management system
with the existing balance manager and trading components.

This example demonstrates:
- Portfolio manager initialization
- Position tracking integration
- Risk management configuration
- Rebalancing setup
- Performance analytics
- Event handling and callbacks
"""

import asyncio
import logging
from typing import Any, Dict

from .analytics import MetricPeriod
from .portfolio_manager import PortfolioConfig, PortfolioManager, PortfolioStrategy
from .position_tracker import PositionType
from .rebalancer import RebalanceStrategy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockTradeExecutor:
    """Mock trade executor for testing"""

    async def execute_buy(self, symbol: str, size_usd: float, reason: str = None) -> Dict[str, Any]:
        """Mock buy execution"""
        return {
            'success': True,
            'symbol': symbol,
            'size': size_usd / 50000,  # Mock price
            'price': 50000,
            'fee': size_usd * 0.001,  # 0.1% fee
            'order_id': f"mock_buy_{symbol}_{int(asyncio.get_event_loop().time())}"
        }

    async def execute_sell(self, symbol: str, size_usd: float, reason: str = None) -> Dict[str, Any]:
        """Mock sell execution"""
        return {
            'success': True,
            'symbol': symbol,
            'size': size_usd / 50000,  # Mock price
            'price': 50000,
            'fee': size_usd * 0.001,  # 0.1% fee
            'order_id': f"mock_sell_{symbol}_{int(asyncio.get_event_loop().time())}"
        }


class PortfolioEventHandler:
    """Example event handler for portfolio events"""

    def __init__(self):
        self.events_received = []

    async def on_position_opened(self, position):
        """Handle position opened event"""
        logger.info(f"🟢 Position opened: {position.symbol} - {position.position_type.value} - ${position.cost_basis:.2f}")
        self.events_received.append(('position_opened', position))

    async def on_position_closed(self, data):
        """Handle position closed event"""
        position = data['position']
        realized_pnl = data['realized_pnl']
        logger.info(f"🔴 Position closed: {position.symbol} - P&L: ${realized_pnl:.2f}")
        self.events_received.append(('position_closed', data))

    async def on_risk_limit_exceeded(self, risk_metrics):
        """Handle risk limit exceeded event"""
        logger.warning(f"⚠️ Risk limit exceeded: {risk_metrics.overall_risk_level.value} - Score: {risk_metrics.risk_score:.1f}")
        self.events_received.append(('risk_limit_exceeded', risk_metrics))

    async def on_rebalance_completed(self, result):
        """Handle rebalance completed event"""
        logger.info(f"⚖️ Rebalance completed: {result.actual_trades} trades, ${result.actual_cost:.2f} cost")
        self.events_received.append(('rebalance_completed', result))

    async def on_performance_update(self, metrics):
        """Handle performance update event"""
        logger.info(f"📊 Performance update: {metrics.total_return:.2%} return, {metrics.sharpe_ratio:.2f} Sharpe")
        self.events_received.append(('performance_update', metrics))

    async def on_status_changed(self, status):
        """Handle status changed event"""
        logger.info(f"🔄 Status changed: {status.value}")
        self.events_received.append(('status_changed', status))

    async def on_error(self, error):
        """Handle error event"""
        logger.error(f"❌ Portfolio error: {error}")
        self.events_received.append(('error', error))


async def portfolio_integration_example():
    """
    Comprehensive portfolio management integration example
    """
    logger.info("🚀 Starting Portfolio Management Integration Example")

    # Step 1: Create mock components (in real use, these would be your actual instances)
    mock_balance_manager = None  # Would be your actual balance manager
    mock_trade_executor = MockTradeExecutor()

    # Step 2: Configure portfolio strategy
    config = PortfolioConfig(
        strategy=PortfolioStrategy.BALANCED,
        target_allocations={
            "BTC/USDT": 0.4,    # 40% Bitcoin
            "ETH/USDT": 0.3,    # 30% Ethereum
            "SHIB/USDT": 0.2,   # 20% Shiba Inu
            "ADA/USDT": 0.1     # 10% Cardano
        },
        max_portfolio_risk_pct=2.5,  # 2.5% max portfolio risk
        max_single_position_pct=25.0,  # 25% max single position
        max_drawdown_pct=20.0,  # 20% max drawdown
        rebalance_enabled=True,
        rebalance_threshold_pct=15.0,  # Rebalance when drift > 15%
        rebalance_interval_hours=24.0,  # Daily rebalancing check
        benchmark_symbol="BTC",
        performance_tracking=True,
        analytics_enabled=True,
        data_path="D:/trading_data/portfolio_example"
    )

    # Step 3: Create event handler
    event_handler = PortfolioEventHandler()

    # Step 4: Initialize portfolio manager
    portfolio_manager = PortfolioManager(
        balance_manager=mock_balance_manager,
        trade_executor=mock_trade_executor,
        config=config
    )

    # Step 5: Register event callbacks
    portfolio_manager.register_callback('position_opened', event_handler.on_position_opened)
    portfolio_manager.register_callback('position_closed', event_handler.on_position_closed)
    portfolio_manager.register_callback('risk_limit_exceeded', event_handler.on_risk_limit_exceeded)
    portfolio_manager.register_callback('rebalance_completed', event_handler.on_rebalance_completed)
    portfolio_manager.register_callback('performance_update', event_handler.on_performance_update)
    portfolio_manager.register_callback('status_changed', event_handler.on_status_changed)
    portfolio_manager.register_callback('error', event_handler.on_error)

    try:
        # Step 6: Initialize the portfolio management system
        logger.info("📋 Initializing portfolio management system...")
        success = await portfolio_manager.initialize()

        if not success:
            logger.error("❌ Failed to initialize portfolio manager")
            return

        logger.info("✅ Portfolio management system initialized successfully")

        # Step 7: Create some example positions
        logger.info("💼 Creating example positions...")

        # Create BTC position
        btc_position = await portfolio_manager.create_position(
            symbol="BTC/USDT",
            position_type=PositionType.LONG,
            size=0.01,  # 0.01 BTC
            entry_price=50000,  # $50,000
            strategy="trend_following",
            tags=["crypto", "large_cap"]
        )

        # Create ETH position
        eth_position = await portfolio_manager.create_position(
            symbol="ETH/USDT",
            position_type=PositionType.LONG,
            size=0.5,  # 0.5 ETH
            entry_price=3000,  # $3,000
            strategy="mean_reversion",
            tags=["crypto", "defi"]
        )

        # Create SHIB position
        shib_position = await portfolio_manager.create_position(
            symbol="SHIB/USDT",
            position_type=PositionType.LONG,
            size=1000000,  # 1M SHIB
            entry_price=0.00001,  # $0.00001
            strategy="momentum",
            tags=["crypto", "meme"]
        )

        # Step 8: Update prices to simulate market movement
        logger.info("📈 Simulating market movements...")

        await portfolio_manager.update_position_price("BTC/USDT", 52000)  # +4% BTC
        await portfolio_manager.update_position_price("ETH/USDT", 2900)   # -3.33% ETH
        await portfolio_manager.update_position_price("SHIB/USDT", 0.000011)  # +10% SHIB

        # Step 9: Get portfolio summary
        logger.info("📊 Getting portfolio summary...")
        summary = await portfolio_manager.get_portfolio_summary()

        logger.info(f"💰 Portfolio Value: ${summary['total_value']:.2f}")
        logger.info(f"📈 Total P&L: ${summary['positions']['total_unrealized_pnl']:.2f}")
        logger.info(f"🎯 Risk Level: {summary['risk_metrics']['overall_risk_level']}")
        logger.info(f"⚖️ Requires Rebalance: {summary['drift_analysis']['requires_rebalance']}")

        # Step 10: Generate performance report
        logger.info("📋 Generating performance report...")
        performance_report = await portfolio_manager.get_performance_report([
            MetricPeriod.DAILY,
            MetricPeriod.INCEPTION
        ])

        if 'error' not in performance_report:
            daily_metrics = performance_report['periods']['daily']
            logger.info(f"📊 Daily Return: {daily_metrics['total_return']:.2%}")
            logger.info(f"📉 Max Drawdown: {daily_metrics['max_drawdown']:.2%}")
            logger.info(f"⚡ Sharpe Ratio: {daily_metrics['sharpe_ratio']:.2f}")

        # Step 11: Test rebalancing
        logger.info("⚖️ Testing portfolio rebalancing...")
        rebalance_result = await portfolio_manager.rebalance_portfolio(
            strategy=RebalanceStrategy.THRESHOLD
        )

        if rebalance_result and rebalance_result.success:
            logger.info(f"✅ Rebalancing successful: {len(rebalance_result.targets)} targets")
        else:
            logger.info("ℹ️ No rebalancing needed or failed")

        # Step 12: Test risk management
        logger.info("🛡️ Testing risk management...")
        risk_report = await portfolio_manager.get_risk_report()

        if 'error' not in risk_report:
            current_metrics = risk_report['current_metrics']
            logger.info(f"🎯 Risk Score: {current_metrics['risk_score']:.1f}/100")
            logger.info(f"📊 Portfolio VaR (95%): ${current_metrics['portfolio_var_95']:.2f}")
            logger.info(f"🔄 Active Positions: {current_metrics['active_positions']}")

        # Step 13: Close a position
        logger.info("🔒 Closing SHIB position...")
        if shib_position:
            closed = await portfolio_manager.close_position(
                position_id=shib_position.position_id,
                price=0.000012,  # Exit at higher price
                fees=0.10  # $0.10 fee
            )

            if closed:
                logger.info("✅ Position closed successfully")

        # Step 14: Test portfolio liquidation (partial)
        logger.info("🚨 Testing emergency liquidation...")

        # First, create another small position for liquidation test
        test_position = await portfolio_manager.create_position(
            symbol="ADA/USDT",
            position_type=PositionType.LONG,
            size=100,  # 100 ADA
            entry_price=0.50,  # $0.50
            strategy="test"
        )

        if test_position:
            # Liquidate just this position by closing it
            await portfolio_manager.close_position(
                position_id=test_position.position_id,
                price=0.52  # Small profit
            )

        # Step 15: Export portfolio data
        logger.info("💾 Exporting portfolio data...")
        export_path = await portfolio_manager.export_data("json")
        logger.info(f"📁 Data exported to: {export_path}")

        # Step 16: Display final portfolio state
        logger.info("📊 Final portfolio state...")
        final_summary = await portfolio_manager.get_portfolio_summary()

        logger.info(f"Final Portfolio Value: ${final_summary['total_value']:.2f}")
        logger.info(f"Total Positions: {final_summary['positions']['total_positions']}")
        logger.info(f"Total Realized P&L: ${final_summary['positions']['total_realized_pnl']:.2f}")
        logger.info(f"Total Unrealized P&L: ${final_summary['positions']['total_unrealized_pnl']:.2f}")

        # Step 17: Display events received
        logger.info(f"📢 Total events received: {len(event_handler.events_received)}")
        for i, (event_type, data) in enumerate(event_handler.events_received[-5:], 1):
            logger.info(f"  {i}. {event_type}")

        # Allow system to process final events
        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"❌ Portfolio integration example failed: {e}")
        raise

    finally:
        # Step 18: Cleanup
        logger.info("🧹 Cleaning up...")
        await portfolio_manager.shutdown()
        logger.info("✅ Portfolio management example completed")


async def simple_portfolio_example():
    """
    Simple portfolio usage example
    """
    logger.info("🎯 Simple Portfolio Example")

    # Basic configuration
    config = PortfolioConfig(
        strategy=PortfolioStrategy.CONSERVATIVE,
        target_allocations={"SHIB/USDT": 1.0},  # 100% SHIB for simplicity
        max_single_position_pct=100.0,  # Allow full allocation
        rebalance_enabled=False,  # Disable for simple example
        analytics_enabled=True
    )

    # Create portfolio manager
    async with PortfolioManager(config=config) as portfolio:
        # Create a position
        position = await portfolio.create_position(
            symbol="SHIB/USDT",
            position_type=PositionType.LONG,
            size=1000000,  # 1M SHIB
            entry_price=0.00001
        )

        if position:
            logger.info(f"Created position: {position.symbol} - ${position.cost_basis:.2f}")

            # Update price
            await portfolio.update_position_price("SHIB/USDT", 0.000012)  # +20%

            # Get summary
            summary = await portfolio.get_portfolio_summary()
            logger.info(f"Portfolio P&L: ${summary['positions']['total_unrealized_pnl']:.2f}")

            # Close position
            await portfolio.close_position(position.position_id, 0.000012)
            logger.info("Position closed")


if __name__ == "__main__":
    # Run the comprehensive example
    asyncio.run(portfolio_integration_example())

    # Uncomment to run simple example instead
    # asyncio.run(simple_portfolio_example())
