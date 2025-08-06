"""
Paper Trading Executor
Wraps the real trade executor with simulated execution
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..trading.enhanced_trade_executor_with_assistants import TradeRequest
from .paper_balance_manager import PaperBalanceManager
from .paper_config import get_paper_config

logger = logging.getLogger(__name__)

class PaperTradeExecutor:
    """Paper trading executor that simulates trade execution"""

    def __init__(self, real_executor=None, exchange=None):
        self.config = get_paper_config()
        self.real_executor = real_executor
        self.exchange = exchange

        # Initialize paper balance manager
        self.paper_balance_manager = PaperBalanceManager()

        # Track paper trading performance
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_profit_loss = 0.0
        self.trade_history = []

        logger.info("🧪 Paper Trade Executor initialized")

    async def execute(self, request: TradeRequest) -> Dict[str, Any]:
        """Execute paper trade with realistic simulation"""

        # Get current market price (use real price if available)
        current_price = await self._get_current_price(request.symbol)
        if not current_price:
            return {
                'success': False,
                'error': 'Could not get market price',
                'paper_trade': True
            }

        # Simulate network delay
        if self.config.simulate_network_delays:
            delay = random.uniform(*self.config.network_delay_range)
            await asyncio.sleep(delay)

        # Simulate order failures
        if self._should_simulate_failure():
            self.failed_trades += 1
            return {
                'success': False,
                'error': 'Simulated order failure',
                'paper_trade': True,
                'failure_type': 'network_timeout'
            }

        # Execute the paper trade
        result = await self._execute_paper_trade(request, current_price)

        # Update statistics
        self.total_trades += 1
        if result['success']:
            self.successful_trades += 1
        else:
            self.failed_trades += 1

        # Log the trade
        logger.info(
            f"🧪 PAPER TRADE: {request.side} {request.amount:.4f} {request.symbol} "
            f"@ ${current_price:.4f} - Success: {result['success']}"
        )

        return result

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price (use real exchange if available)"""
        try:
            if self.exchange and hasattr(self.exchange, 'get_ticker'):
                ticker = await self.exchange.get_ticker(symbol)
                return float(ticker.get('last', 0))
            else:
                # Fallback: simulate realistic price
                # In real implementation, you'd fetch from Kraken API
                base_prices = {
                    'BTC/USDT': 45000.0,
                    'ETH/USDT': 3000.0,
                    'SOL/USDT': 160.0,
                    'AVAX/USDT': 21.0,
                    'ALGO/USDT': 0.25,
                    'ATOM/USDT': 4.65,
                    'AI16Z/USDT': 0.186,
                    'BERA/USDT': 2.0
                }

                base_price = base_prices.get(symbol, 100.0)
                # Add some random variation (±2%)
                variation = random.uniform(-0.02, 0.02)
                return base_price * (1 + variation)

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None

    def _should_simulate_failure(self) -> bool:
        """Determine if this trade should simulate a failure"""
        return random.random() < self.config.order_failure_rate

    async def _execute_paper_trade(self, request: TradeRequest, price: float) -> Dict[str, Any]:
        """Execute the actual paper trade"""
        try:
            # Calculate trade details
            trade_amount = request.amount

            # Apply slippage if enabled
            execution_price = price
            if self.config.simulate_slippage and random.random() < self.config.slippage_probability:
                slippage = random.uniform(0, self.config.max_slippage)
                if request.side.upper() == 'BUY':
                    execution_price *= (1 + slippage)  # Buy higher
                else:
                    execution_price *= (1 - slippage)  # Sell lower

            # Calculate fees
            fee_rate = self.config.taker_fee  # Assuming market orders
            fee = trade_amount * execution_price * fee_rate if self.config.simulate_real_fees else 0

            # Update balances
            if request.side.upper() == 'BUY':
                result = await self._execute_buy(request.symbol, trade_amount, execution_price, fee)
            else:
                result = await self._execute_sell(request.symbol, trade_amount, execution_price, fee)

            # Record trade
            trade_record = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbol': request.symbol,
                'side': request.side,
                'amount': trade_amount,
                'price': execution_price,
                'fee': fee,
                'success': result.get('success', False),
                'paper_trade': True
            }

            self.trade_history.append(trade_record)

            # Save trade if configured
            if self.config.save_trades:
                await self._save_trade_record(trade_record)

            return result

        except Exception as e:
            logger.error(f"Error executing paper trade: {e}")
            return {
                'success': False,
                'error': str(e),
                'paper_trade': True
            }

    async def _execute_buy(self, symbol: str, amount: float, price: float, fee: float) -> Dict[str, Any]:
        """Execute paper buy order"""
        total_cost = amount * price + fee

        # Check if we have enough USDT
        usdt_balance = await self.paper_balance_manager.get_balance_for_asset('USDT')

        if usdt_balance < total_cost:
            return {
                'success': False,
                'error': f'Insufficient USDT balance: ${usdt_balance:.2f} < ${total_cost:.2f}',
                'paper_trade': True
            }

        # Update balances
        base_asset = symbol.split('/')[0]
        self.paper_balance_manager.balances['USDT'] -= total_cost
        current_base = self.paper_balance_manager.balances.get(base_asset, 0.0)
        self.paper_balance_manager.balances[base_asset] = current_base + amount

        # Update portfolio position
        self.paper_balance_manager.portfolio_positions[symbol] = {
            'amount': amount,
            'entry_price': price,
            'value': amount * price,
            'unrealized_pnl': 0.0,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        return {
            'success': True,
            'order_id': f'paper_{int(time.time() * 1000)}',
            'amount': amount,
            'price': price,
            'fee': fee,
            'total_cost': total_cost,
            'paper_trade': True
        }

    async def _execute_sell(self, symbol: str, amount: float, price: float, fee: float) -> Dict[str, Any]:
        """Execute paper sell order"""
        base_asset = symbol.split('/')[0]
        base_balance = await self.paper_balance_manager.get_balance_for_asset(base_asset)

        if base_balance < amount:
            return {
                'success': False,
                'error': f'Insufficient {base_asset} balance: {base_balance:.8f} < {amount:.8f}',
                'paper_trade': True
            }

        # Calculate proceeds
        gross_proceeds = amount * price
        net_proceeds = gross_proceeds - fee

        # Update balances
        self.paper_balance_manager.balances[base_asset] -= amount
        current_usdt = self.paper_balance_manager.balances.get('USDT', 0.0)
        self.paper_balance_manager.balances['USDT'] = current_usdt + net_proceeds

        # Calculate P&L if we have position data
        pnl = 0.0
        if symbol in self.paper_balance_manager.portfolio_positions:
            position = self.paper_balance_manager.portfolio_positions[symbol]
            entry_price = position.get('entry_price', price)
            pnl = (price - entry_price) * amount - fee
            self.total_profit_loss += pnl

            # Remove or update position
            if position['amount'] <= amount:
                del self.paper_balance_manager.portfolio_positions[symbol]
            else:
                position['amount'] -= amount
                position['value'] = position['amount'] * price

        return {
            'success': True,
            'order_id': f'paper_{int(time.time() * 1000)}',
            'amount': amount,
            'price': price,
            'fee': fee,
            'net_proceeds': net_proceeds,
            'pnl': pnl,
            'paper_trade': True
        }

    async def _save_trade_record(self, trade_record: Dict[str, Any]):
        """Save trade record to file"""
        try:
            import json
            trades_file = self.config.trades_file

            # Load existing trades
            trades = []
            if trades_file.exists():
                with open(trades_file) as f:
                    trades = json.load(f)

            # Add new trade
            trades.append(trade_record)

            # Save back
            with open(trades_file, 'w') as f:
                json.dump(trades, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving trade record: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        success_rate = (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        current_balance = sum(self.paper_balance_manager.balances.values())
        total_return = ((current_balance - self.config.starting_balance) / self.config.starting_balance * 100) if self.config.starting_balance > 0 else 0

        return {
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'failed_trades': self.failed_trades,
            'success_rate': success_rate,
            'total_profit_loss': self.total_profit_loss,
            'starting_balance': self.config.starting_balance,
            'current_balance': current_balance,
            'total_return_pct': total_return,
            'balances': self.paper_balance_manager.balances.copy(),
            'positions': self.paper_balance_manager.portfolio_positions.copy()
        }
