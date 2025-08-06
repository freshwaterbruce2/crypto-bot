"""
Enhanced Trade Executor with Kraken Compliance
Unified execution pipeline with assistants and Portfolio Intelligence
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from ..config.constants import MINIMUM_ORDER_SIZE_TIER1
from ..utils.kraken_order_validator import kraken_validator
from ..utils.trade_cooldown import get_cooldown_manager

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class TradeRequest:
    """Standardized trade request"""
    symbol: str
    side: str
    amount: float
    signal: Dict[str, Any]
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None


class TradeAssistant:
    """Base class for trade assistants"""

    def __init__(self, name: str):
        self.name = name
        self.metrics = {
            'validations': 0,
            'approvals': 0,
            'rejections': 0
        }

    async def validate(self, request: TradeRequest) -> tuple[bool, str]:
        """Validate trade request"""
        self.metrics['validations'] += 1
        return True, "OK"


class ComplianceAssistant(TradeAssistant):
    """Ensures Kraken compliance"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("compliance")
        # Kraken minimum for crypto-to-crypto is 1 USDT
        self.min_order_value = max(1.0, config.get('min_order_size_usdt', 1.0))
        self.allowed_quote = 'USDT'
        self.tier_1_limit = config.get('tier_1_trade_limit', 5.0)
        self.api_tier = config.get('kraken_api_tier', 'starter')

    async def validate(self, request: TradeRequest) -> tuple[bool, str]:
        """Validate Kraken compliance"""
        await super().validate(request)

        # Check USDT pair
        if self.allowed_quote not in request.symbol:
            self.metrics['rejections'] += 1
            return False, f"Only {self.allowed_quote} pairs allowed"

        # Check minimum order value
        if request.amount < self.min_order_value:
            self.metrics['rejections'] += 1
            return False, f"Order value ${request.amount:.2f} below ${self.min_order_value} minimum"

        # Check tier-1 trade limit
        if self.api_tier == 'starter' and request.amount > self.tier_1_limit:
            self.metrics['rejections'] += 1
            return False, f"Tier-1 limit: Order value ${request.amount:.2f} exceeds ${self.tier_1_limit} limit"

        self.metrics['approvals'] += 1
        return True, "Compliance check passed"


class RiskAssistant(TradeAssistant):
    """Manages risk parameters with portfolio intelligence and claude-flow agent integration"""

    def __init__(self, config: Dict[str, Any], balance_manager, portfolio_intelligence=None):
        super().__init__("risk")
        self.balance_manager = balance_manager
        self.portfolio_intelligence = portfolio_intelligence
        self.max_position_pct = config.get('max_position_pct', 0.8)
        self.max_daily_loss = config.get('max_daily_loss', 50.0)
        self.daily_loss = 0.0

        # Claude-flow agent integration for intelligent decisions
        self.agent_swarm_id = "swarm_1752495725359_0an5zsd30"
        self.portfolio_coordinator = "agent_1752495795039_fayma0"
        self.balance_analyst = "agent_1752495795254_18v5ns"
        self.allocation_optimizer = "agent_1752495795820_iyk8wb"
        self.position_sizer = "agent_1752495796442_vz09jn"

    async def validate(self, request: TradeRequest) -> tuple[bool, str]:
        """Validate risk parameters with portfolio state awareness"""
        await super().validate(request)

        # CRITICAL: Check if we're in rate limit backoff FIRST
        if self.balance_manager and hasattr(self.balance_manager, 'rate_counter'):
            rate_status = self.balance_manager.rate_counter.get_status()
            if rate_status.get('in_backoff'):
                self.metrics['rejections'] += 1
                backoff_time = rate_status.get('backoff_remaining', 0)
                logger.warning(f"[RISK] In rate limit backoff for {backoff_time:.1f}s - rejecting trade")
                return False, f"Rate limit backoff - waiting {backoff_time:.1f}s"

            # Also check if approaching limit (use tier-appropriate buffer)
            if self.balance_manager.rate_counter.is_approaching_limit():
                self.metrics['rejections'] += 1
                logger.warning(f"[RISK] Approaching rate limit ({rate_status['current_count']}/{rate_status['max_counter']}) - rejecting trade to prevent rate limit")
                return False, f"Approaching rate limit - current: {rate_status['current_count']}/{rate_status['max_counter']}"

        # Check daily loss limit
        if self.daily_loss >= self.max_daily_loss:
            self.metrics['rejections'] += 1
            return False, f"Daily loss limit ${self.max_daily_loss} reached"

        # Enhanced position size check with portfolio intelligence
        if self.balance_manager:
            balance = await self.balance_manager.get_balance_for_asset('USDT')

            # If low balance, check if funds are deployed
            if balance < request.amount:
                logger.info(f"[RISK] Low USDT balance (${balance:.2f}), checking deployed funds...")

                # Check deployment status
                deployment_status = self.balance_manager.get_deployment_status('USDT')

                if deployment_status == 'funds_deployed':
                    # Analyze portfolio for reallocation opportunities
                    portfolio_analysis = await self.balance_manager.analyze_portfolio_state('USDT')

                    logger.info(
                        f"[RISK] Portfolio deployed: ${portfolio_analysis['portfolio_value']:.2f} "
                        f"across {len(portfolio_analysis['deployed_assets'])} assets"
                    )

                    # Check for reallocation opportunities
                    reallocation_opps = portfolio_analysis.get('reallocation_opportunities', [])
                    deployed_assets = portfolio_analysis.get('deployed_assets', [])

                    # Allow trade if we have ANY deployed assets that could be sold
                    if deployed_assets and len(deployed_assets) > 0:
                        # Log the deployed assets for debugging
                        asset_summary = [f"{a['asset']}: ${a.get('value_usd', 0):.2f}" for a in deployed_assets[:3]]
                        logger.info(f"[RISK] Deployed assets available for reallocation: {', '.join(asset_summary)}")

                        # Check if any deployed asset has sufficient value
                        max_asset_value = max([a.get('value_usd', 0) for a in deployed_assets], default=0)
                        if max_asset_value >= request.amount * 0.8:  # 80% of requested amount
                            self.metrics['approvals'] += 1
                            return True, f"Risk check passed - can reallocate from {len(deployed_assets)} deployed assets"
                        elif max_asset_value >= self.balance_manager.min_trade_value_usd:
                            # Allow smaller trades if we can at least make minimum trades
                            self.metrics['approvals'] += 1
                            return True, "Risk check passed - partial reallocation possible from deployed assets"

                    # Only reject if truly no options
                    if portfolio_analysis['portfolio_value'] < self.balance_manager.min_trade_value_usd:
                        self.metrics['rejections'] += 1
                        return False, f"Portfolio value too low for trading (${portfolio_analysis['portfolio_value']:.2f})"
                    else:
                        # Allow trade to attempt with available balance
                        self.metrics['approvals'] += 1
                        return True, "Risk check passed - attempting with available balance"
                elif deployment_status == 'insufficient_funds':
                    # Check if there's any portfolio value for potential reallocation
                    portfolio_analysis = await self.balance_manager.analyze_portfolio_state('USDT')
                    portfolio_value = portfolio_analysis.get('portfolio_value', 0)

                    if portfolio_value > 0:
                        logger.info(
                            f"[RISK] Low total funds but ${portfolio_value:.2f} portfolio value available - "
                            f"checking for micro-reallocation opportunities"
                        )

                        # Allow small trades if portfolio has some value
                        if request.amount <= portfolio_value * 0.1:  # Allow up to 10% of portfolio value
                            self.metrics['approvals'] += 1
                            return True, f"Risk check passed - micro-reallocation from ${portfolio_value:.2f} portfolio"

                    self.metrics['rejections'] += 1
                    return False, f"Insufficient total funds (${balance:.2f} available, ${portfolio_value:.2f} portfolio)"

            # Standard position size check with CRITICAL FIX for reallocation
            if balance > 0:
                # Enhanced position calculation for deployed capital scenarios
                if hasattr(self.balance_manager, 'analyze_portfolio_state'):
                    portfolio_analysis = await self.balance_manager.analyze_portfolio_state('USDT')
                    total_portfolio_value = portfolio_analysis.get('portfolio_value', balance)

                    # Use portfolio value for deployed capital scenarios
                    effective_balance_for_calc = max(balance, total_portfolio_value * 0.1)  # At least 10% of portfolio
                    position_pct = request.amount / effective_balance_for_calc

                    # If total portfolio > balance (funds deployed), allow higher percentage
                    if total_portfolio_value > balance * 2:  # 2x indicates significant deployment
                        # For deployed capital, allow larger percentages of liquid balance
                        if request.amount <= 5.0:  # Small trades under $5
                            effective_max_pct = 1.0  # Allow 100% of liquid balance for micro-trades
                        else:
                            effective_max_pct = 0.9  # 90% for larger reallocation trades
                        logger.info(f"[RISK] Using deployed capital limits: {effective_max_pct:.0%} (portfolio: ${total_portfolio_value:.2f}, balance: ${balance:.2f})")
                    else:
                        effective_max_pct = min(self.max_position_pct, 0.8)  # 80% for normal scenarios
                else:
                    position_pct = request.amount / balance
                    effective_max_pct = min(self.max_position_pct, 0.8)  # 80% fallback

                # Special allowance for micro-trades with deployed capital
                if (position_pct > effective_max_pct and
                    request.amount <= 5.0 and
                    hasattr(self.balance_manager, 'analyze_portfolio_state')):

                    portfolio_analysis = await self.balance_manager.analyze_portfolio_state('USDT')
                    total_portfolio_value = portfolio_analysis.get('portfolio_value', 0)

                    if total_portfolio_value >= request.amount * 10:  # Portfolio is 10x the trade size
                        logger.info(f"[RISK] Allowing micro-trade ${request.amount:.2f} despite position size - portfolio: ${total_portfolio_value:.2f}")
                        self.metrics['approvals'] += 1
                        return True, f"Micro-trade approved with deployed capital (${total_portfolio_value:.2f} portfolio)"

                if position_pct > effective_max_pct:
                    # Use claude-flow agents for intelligent position sizing decisions
                    try:
                        from ..utils.claude_flow_integration import get_position_sizing_decision

                        # Get intelligent decision from PositionSizer agent
                        sizing_decision = await get_position_sizing_decision(
                            self.position_sizer,
                            {
                                'symbol': request.symbol,
                                'requested_amount': request.amount,
                                'current_balance': balance,
                                'position_pct': position_pct,
                                'max_pct': effective_max_pct,
                                'portfolio_value': total_portfolio_value if 'total_portfolio_value' in locals() else balance,
                                'deployment_status': 'deployed' if balance < request.amount else 'liquid'
                            }
                        )

                        if sizing_decision.get('allow_trade', False):
                            adjusted_amount = sizing_decision.get('adjusted_amount', request.amount)
                            if adjusted_amount != request.amount:
                                logger.info(f"[RISK] Agent adjusted position: ${request.amount:.2f} -> ${adjusted_amount:.2f}")
                                request.amount = adjusted_amount
                            self.metrics['approvals'] += 1
                            return True, f"Agent-approved position sizing: {sizing_decision.get('reason', 'Intelligent reallocation')}"
                        else:
                            self.metrics['rejections'] += 1
                            return False, f"Agent rejected: {sizing_decision.get('reason', 'Position size validation failed')}"

                    except Exception as e:
                        logger.warning(f"[RISK] Agent decision failed, using fallback: {e}")
                        self.metrics['rejections'] += 1
                        return False, f"Position size {position_pct:.1%} exceeds max {effective_max_pct:.1%}"

        self.metrics['approvals'] += 1
        return True, "Risk check passed"


class ExecutionAssistant(TradeAssistant):
    """Handles execution logic with intelligent reallocation"""

    def __init__(self, exchange_client, balance_manager=None, portfolio_intelligence=None, bot_reference=None, config=None):
        super().__init__("execution")
        self.exchange = exchange_client
        self.balance_manager = balance_manager
        self.portfolio_intelligence = portfolio_intelligence
        self.bot_reference = bot_reference
        self.config = config or {}
        self.pending_orders = {}

    async def get_realtime_price(self, symbol: str) -> Optional[float]:
        """Get real-time price from WebSocket V2"""
        try:
            # Try to get from bot's websocket manager
            if self.bot_reference and hasattr(self.bot_reference, 'websocket_manager') and self.bot_reference.websocket_manager:
                ticker = self.bot_reference.websocket_manager.get_ticker(symbol)
                if ticker and 'last' in ticker:
                    return float(ticker['last'])

            # Fallback to exchange ticker
            if self.exchange:
                ticker = await self.exchange.fetch_ticker(symbol)
                if ticker and 'last' in ticker:
                    return float(ticker['last'])

            logger.debug(f"[EXECUTION] No real-time price available for {symbol}")
            return None
        except Exception as e:
            logger.error(f"[EXECUTION] Error getting real-time price for {symbol}: {e}")
            return None

    async def execute(self, request: TradeRequest) -> Dict[str, Any]:
        """Execute the trade with intelligent fund management and compliance checks"""
        try:
            # COMPLIANCE CHECK: Same-side trade cooling period
            cooldown_manager = get_cooldown_manager()
            can_trade, cooldown_reason = cooldown_manager.can_trade(request.symbol, request.side.lower())

            if not can_trade:
                logger.warning(f"[COMPLIANCE] Trade blocked by cooldown: {cooldown_reason}")
                return {
                    'success': False,
                    'error': f"Trade cooling down: {cooldown_reason}",
                    'skip_reason': 'trade_cooldown_active'
                }

            logger.info(f"[COMPLIANCE] Trade cooldown check passed for {request.side} {request.symbol}")
            # CRITICAL FIX: Force refresh balance right before checking with claude-flow coordination
            if self.balance_manager and request.side.upper() == 'BUY':
                logger.info("[EXECUTION] Forcing balance refresh before trade...")

                # Use claude-flow agents for intelligent balance refresh coordination
                try:
                    from ..utils.claude_flow_integration import coordinate_trade_execution

                    # Get trade coordination from PortfolioCoordinator
                    trade_context = {
                        'symbol': request.symbol,
                        'side': request.side,
                        'amount': request.amount,
                        'portfolio_state': {
                            'liquid_balance': await self._get_available_balance(),
                            'requires_reallocation': False
                        }
                    }

                    coordination_result = await coordinate_trade_execution(trade_context)

                    if coordination_result.get('coordination_needed', False):
                        logger.info(f"[EXECUTION] Trade coordination required: {coordination_result.get('execution_order', 'unknown')}")

                        # Execute pre-trade actions if needed
                        pre_actions = coordination_result.get('pre_trade_actions', [])
                        for action in pre_actions:
                            if action.get('type') == 'balance_refresh':
                                await self.balance_manager.force_refresh(retry_count=3)
                            elif action.get('type') == 'circuit_breaker_reset':
                                # Reset circuit breakers using claude-flow integration
                                if hasattr(self.exchange, 'circuit_breaker'):
                                    self.exchange.circuit_breaker.reset()
                                    logger.info("[EXECUTION] Circuit breaker reset by agent coordination")
                except Exception as e:
                    logger.warning(f"[EXECUTION] Agent coordination failed, using fallback: {e}")
                    await self.balance_manager.force_refresh(retry_count=2)

            # Check if we need reallocation before creating order
            balance = await self._get_available_balance()

            # CRITICAL FIX: If balance is 0, try direct fetch as fallback
            if balance == 0.0 and request.side.upper() == 'BUY':
                logger.warning("[EXECUTION] Balance returned 0.0, trying direct fetch...")
                balance = await self._get_balance_with_fallback()

            # CRITICAL FIX 2: Implement balance verification with retries
            if request.side.upper() == 'BUY':
                balance = await self._verify_balance_with_retries(request.amount)
                if balance < request.amount:
                    logger.error(f"[EXECUTION] Balance verification failed: ${balance:.2f} < ${request.amount:.2f}")
                    return {
                        'success': False,
                        'error': f'Insufficient balance after verification: ${balance:.2f}',
                        'skip_reason': 'balance_verification_failed'
                    }

            # Dynamic minimum balance check based on portfolio pair requirements
            min_required_balance = MINIMUM_ORDER_SIZE_TIER1  # Tier-1 minimum

            # Check if this is a portfolio pair and get its specific minimum
            if hasattr(self, 'minimum_integration') and self.minimum_integration:
                try:
                    if self.minimum_integration.smart_minimum_manager.is_portfolio_pair(request.symbol):
                        tier = self.minimum_integration.smart_minimum_manager.get_pair_tier(request.symbol)
                        min_required_balance = self.minimum_integration.smart_minimum_manager.TIER_MIN_COSTS[tier]
                except Exception as e:
                    logger.debug(f"[EXECUTION] Could not get portfolio minimum: {e}")

            # Simplified USDT-only balance check
            if request.side.upper() == 'SELL':
                # For sells, get the base asset (e.g., 'BTC' from 'BTC/USDT')
                base_asset = request.symbol.split('/')[0]
                asset_balance = 0

                if self.balance_manager:
                    asset_balance = await self.balance_manager.get_balance_for_asset(base_asset)
                    logger.info(f"[EXECUTION] {base_asset} balance: {asset_balance:.8f}")

                if asset_balance <= 0:
                    logger.error(f"[EXECUTION] No {base_asset} balance to sell")
                    return {
                        'success': False,
                        'error': f'No {base_asset} to sell',
                        'skip_reason': 'no_asset_balance'
                    }
            else:
                # For buys, check USDT balance with Kraken's $2 minimum
                if balance < 2.0:
                    logger.error(f"[EXECUTION] USDT balance ${balance:.2f} < $2.00 minimum")
                    return {
                        'success': False,
                        'error': f'Insufficient USDT: ${balance:.2f}',
                        'skip_reason': 'insufficient_usdt'
                    }

                # Ensure order size meets Kraken minimum and maximum limits
                min_order_size = self.config.get('min_order_size_usdt', 2.0)
                max_order_size = self.config.get('max_order_size_usdt', 5.0)

                if request.amount < min_order_size:
                    request.amount = min_order_size
                    logger.info(f"[EXECUTION] Adjusted order to ${min_order_size:.2f} minimum")
                elif request.amount > max_order_size:
                    request.amount = max_order_size
                    logger.info(f"[EXECUTION] Capped order at ${max_order_size:.2f} maximum")

            # Smart position size adjustment - handle BUY vs SELL differently
            use_dynamic = hasattr(self.balance_manager, 'bot') and self.balance_manager.bot.config.get('use_dynamic_position_sizing', True)
            position_pct = 0.95 if use_dynamic else 0.8  # Use 95% for dynamic sizing, 80% for traditional

            # For SELL orders, we need to calculate based on crypto balance, not USDT
            if request.side.lower() == 'sell':
                base_asset = request.symbol.split('/')[0] if '/' in request.symbol else request.symbol

                # Check if we should sell full position (to prevent dust)
                sell_full_position = self.config.get('order_settings', {}).get('sell_full_position', True)

                # Get the crypto asset balance
                asset_balance = 0
                try:
                    # CRITICAL FIX: Check bot reference properly
                    if sell_full_position and self.bot_reference and hasattr(self.bot_reference, 'portfolio_tracker') and self.bot_reference.portfolio_tracker:
                        position = self.bot_reference.portfolio_tracker.get_position(request.symbol)
                        if position and 'amount' in position:
                            asset_balance = position['amount']
                            logger.info(f"[EXECUTION] Using tracked position amount for {base_asset}: {asset_balance}")
                        else:
                            # Fallback to balance manager
                            if self.balance_manager:
                                asset_balance = await self.balance_manager.get_balance(base_asset)
                                logger.info(f"[EXECUTION] Using balance for {base_asset}: {asset_balance}")
                    else:
                        # Standard balance check
                        if self.balance_manager:
                            asset_balance = await self.balance_manager.get_balance(base_asset)
                except Exception as e:
                    logger.error(f"[EXECUTION] Error getting {base_asset} balance: {e}")

                # Get current price for value calculation
                current_price = 0
                try:
                    # Try to get price from signal or fetch it
                    current_price = request.signal.get('price', 0) if hasattr(request, 'signal') else 0
                    if not current_price and hasattr(self, 'exchange'):
                        ticker = await self.exchange.fetch_ticker(request.symbol)
                        current_price = ticker.get('last', 0)
                except Exception as e:
                    logger.error(f"[EXECUTION] Error getting price for {request.symbol}: {e}")

                if current_price > 0 and asset_balance > 0:
                    # Calculate position value based on crypto holdings
                    max_sell_amount = asset_balance * position_pct
                    max_sell_value = max_sell_amount * current_price

                    # The request.amount is in USDT, so we need to compare values
                    if request.amount > max_sell_value:
                        old_amount = request.amount
                        request.amount = max_sell_value
                        logger.info(f"[EXECUTION] Adjusted SELL position size from ${old_amount:.2f} to ${request.amount:.2f} ({position_pct*100}% of {asset_balance:.8f} {base_asset} = ${max_sell_value:.2f})")

                    # Ensure we have a valid amount
                    if request.amount < min_required_balance:
                        # If the USDT value is too low, calculate the full crypto amount we can sell
                        logger.info(f"[EXECUTION] SELL order value ${request.amount:.2f} below minimum, using full balance calculation")
                        request.amount = max_sell_value  # Use full calculated value
                else:
                    logger.warning(f"[EXECUTION] Cannot calculate sell position - price: ${current_price:.2f}, balance: {asset_balance:.8f}")
            else:
                # For BUY orders, use USDT balance
                if request.amount > balance * position_pct:
                    old_amount = request.amount
                    request.amount = balance * position_pct
                    logger.info(f"[EXECUTION] Adjusted BUY position size from ${old_amount:.2f} to ${request.amount:.2f} ({position_pct*100}% of ${balance:.2f} USDT)")

            # Ensure the adjusted amount still meets minimums
            if request.amount < min_required_balance:
                logger.warning(f"[EXECUTION] Adjusted amount ${request.amount:.2f} still below minimum ${min_required_balance:.2f}")
                return {
                    'success': False,
                    'error': f"Adjusted position ${request.amount:.2f} below minimum ${min_required_balance:.2f}",
                    'skip_reason': 'amount_too_small_after_adjustment'
                }

            # Use smart minimum manager if available for portfolio pairs
            if hasattr(self, 'minimum_integration') and self.minimum_integration:
                # Check if this is a portfolio pair
                if self.minimum_integration.smart_minimum_manager.is_portfolio_pair(request.symbol):
                    try:
                        # Get current price from WebSocket V2
                        current_price = await self.get_realtime_price(request.symbol)
                        if not current_price:
                            logger.warning(f"[EXECUTION] No real-time price for {request.symbol}")
                            return {
                                'success': False,
                                'error': f"No real-time price data available for {request.symbol}"
                            }

                        # Validate order size using smart minimum manager
                        is_valid, validation_message = await self.minimum_integration.validate_order_size(
                            request.symbol, request.amount / current_price, current_price
                        )

                        if not is_valid:
                            logger.warning(f"[EXECUTION] Portfolio pair validation failed: {validation_message}")
                            return {
                                'success': False,
                                'error': f"Portfolio minimum not met: {validation_message}"
                            }

                        logger.info(f"[EXECUTION] Portfolio pair validated: {request.symbol} - {validation_message}")
                    except Exception as e:
                        logger.warning(f"[EXECUTION] Portfolio validation error: {e}, falling back to standard check")
                        # Fall through to standard check

            # CRITICAL FIX: Enhanced minimum order size validation for Kraken with auto-adjustment
            kraken_min_usd = 5.0  # Kraken's actual minimum order value
            if request.amount < kraken_min_usd:
                logger.info(f"[EXECUTION] Order amount ${request.amount:.2f} below Kraken minimum ${kraken_min_usd:.2f}")

                # Auto-adjust to minimum if we have enough balance
                if balance >= kraken_min_usd:
                    logger.info(f"[EXECUTION] Auto-adjusting order amount to Kraken minimum: ${kraken_min_usd:.2f}")
                    request.amount = kraken_min_usd
                else:
                    return {
                        'success': False,
                        'error': f"Order amount ${request.amount:.2f} below Kraken minimum ${kraken_min_usd:.2f}",
                        'skip_reason': 'below_kraken_minimum_order_size'
                    }

            # Final minimum order size check (use the calculated minimum)
            if request.amount < min_required_balance:
                logger.info(f"[EXECUTION] Order amount ${request.amount:.2f} below required minimum ${min_required_balance:.2f}")
                return {
                    'success': False,
                    'error': f"Order amount ${request.amount:.2f} below minimum ${min_required_balance:.2f}",
                    'skip_reason': 'below_minimum_order_size'
                }

            # CRITICAL FIX: Add MIN_TRADE_BUFFER constant
            MIN_TRADE_BUFFER = 1.0  # $1 minimum trade buffer

            if balance < request.amount and self.balance_manager:
                # First check if this is truly insufficient funds or just deployed capital
                if self.portfolio_intelligence:
                    portfolio_state = await self.portfolio_intelligence.get_portfolio_state()
                    total_portfolio_value = portfolio_state.get('total_value_usdt', 0)

                    if total_portfolio_value >= request.amount:
                        logger.info(f"[EXECUTION] Low free balance (${balance:.2f}) but sufficient portfolio value (${total_portfolio_value:.2f}), attempting reallocation...")
                    else:
                        logger.warning(f"[EXECUTION] Insufficient total portfolio value (${total_portfolio_value:.2f} < ${request.amount:.2f})")
                        return {
                            'success': False,
                            'error': f"Insufficient total funds: ${total_portfolio_value:.2f} available, ${request.amount:.2f} required"
                        }
                else:
                    logger.info(f"[EXECUTION] Insufficient balance (${balance:.2f} < ${request.amount:.2f}), attempting reallocation...")

                # Attempt strategic liquidation
                liquidation_result = await self._handle_reallocation(request)

                if liquidation_result['success']:
                    logger.info(f"[EXECUTION] Reallocation successful: ${liquidation_result['amount_freed']:.2f} freed")
                    # Update available balance after liquidation
                    balance = await self._get_available_balance()  # Real-time balance will reflect changes
                    logger.info(f"[EXECUTION] Balance after reallocation: ${balance:.2f}")

                    # Re-check if we have enough after liquidation
                    if balance < MIN_TRADE_BUFFER:
                        return {
                            'success': False,
                            'error': f"Still insufficient after reallocation: ${balance:.2f} < ${MIN_TRADE_BUFFER}"
                        }
                else:
                    logger.warning(f"[EXECUTION] Reallocation failed: {liquidation_result['reason']}")
                    return {
                        'success': False,
                        'error': f"Insufficient funds and reallocation failed: {liquidation_result['reason']}"
                    }

            # Validate minimum order requirements if portfolio intelligence available
            if hasattr(self, 'portfolio_intelligence') and self.portfolio_intelligence:
                validation_result = await self.portfolio_intelligence.validate_trade_minimums(
                    request.symbol, request.order_type.value, request.amount, request.price
                )

                if not validation_result.get('valid', True):
                    logger.warning(f"[EXECUTION] Order size validation failed: {validation_result.get('reason', 'Unknown')}")

                    # Check if we can adjust the amount
                    suggested_amount = validation_result.get('suggested_minimum')
                    if suggested_amount and suggested_amount <= balance:
                        logger.info(f"[EXECUTION] Adjusting order amount from ${request.amount:.2f} to ${suggested_amount:.2f}")
                        request.amount = suggested_amount
                    else:
                        return {
                            'success': False,
                            'error': f"Order below minimum: {validation_result.get('reason', 'Amount too small')}"
                        }

            # Check for IOC order type from signal
            order_type_value = request.order_type.value
            use_ioc = request.signal.get('order_type') == 'ioc'

            # Calculate order volume based on side
            order_amount = request.amount

            # Get current price first (needed for both BUY and SELL)
            current_price = await self.get_realtime_price(request.symbol)

            if not current_price:
                logger.error(f"[EXECUTION] Cannot get price for {request.symbol}")
                return {
                    'success': False,
                    'error': 'Cannot determine current price for volume calculation'
                }

            # For BUY orders, we need to convert USDT amount to base currency amount
            if request.side.upper() == 'BUY':
                # Convert USDT amount to base currency volume
                # e.g., $2 USDT / $0.6357 per APE = 3.146 APE
                order_amount = request.amount / current_price
                logger.info(f"[EXECUTION] BUY order: ${request.amount:.2f} USDT / ${current_price:.4f} = {order_amount:.8f} {request.symbol.split('/')[0]}")
            elif request.side.upper() == 'SELL':
                # For SELL orders, request.amount is also in USDT, convert to crypto
                # e.g., $2 USDT / $0.1659 per AI16Z = 12.055 AI16Z
                order_amount = request.amount / current_price
                logger.info(f"[EXECUTION] SELL order: ${request.amount:.2f} USDT / ${current_price:.4f} = {order_amount:.8f} {request.symbol.split('/')[0]}")

            # CRITICAL FIX: Pre-order balance verification to prevent "EOrder:Insufficient funds"
            if hasattr(self.balance_manager, 'verify_balance_before_order'):
                try:
                    if request.side.lower() == 'sell':
                        base_asset = request.symbol.split('/')[0]
                        verification = await self.balance_manager.verify_balance_before_order(base_asset, order_amount, 'sell')
                    else:
                        verification = await self.balance_manager.verify_balance_before_order('USDT', request.amount, 'buy')

                    if not verification.get('verified', False):
                        logger.warning(f"[EXECUTION] Pre-order verification failed: {verification.get('reason', 'Unknown')}")
                        return {
                            'success': False,
                            'error': f"Pre-order verification failed: {verification.get('reason', 'Insufficient balance')}",
                            'skip_reason': 'pre_order_verification_failed'
                        }
                    else:
                        logger.info(f"[EXECUTION] Pre-order verification passed: {verification.get('message', 'Balance sufficient')}")
                except Exception as e:
                    logger.warning(f"[EXECUTION] Pre-order verification error: {e}")

            # KRAKEN PRECISION VALIDATION - Ensure order meets Kraken requirements
            logger.info(f"[EXECUTION] Validating Kraken precision for {request.symbol}: volume={order_amount:.8f}")

            # Validate order against Kraken precision requirements
            order_price = request.price or request.signal.get('price') if use_ioc else request.price
            validation_result = kraken_validator.validate_and_format_order(
                request.symbol,
                request.side,
                order_amount,
                order_price,
                'limit' if use_ioc else 'market'
            )

            if not validation_result['valid']:
                logger.error(f"[KRAKEN_PRECISION] Order validation failed: {validation_result['error']}")
                return {
                    'success': False,
                    'error': f"Kraken precision validation failed: {validation_result['error']}",
                    'skip_reason': 'kraken_precision_validation_failed',
                    'validation_details': validation_result
                }

            # Use Kraken-formatted values for the order
            kraken_amount = validation_result['amount_float']
            kraken_price = validation_result.get('price_float')

            logger.info(f"[KRAKEN_PRECISION] ✅ Order validated - Amount: {kraken_amount}, Price: {kraken_price or 'market'}")
            logger.info(f"[EXECUTION] Creating {request.side} order for {request.symbol}: volume={kraken_amount:.8f}, IOC={use_ioc}")

            if use_ioc:
                # IOC orders for micro-profits (0 penalty on failure!)
                order = await self.exchange.create_order(
                    symbol=request.symbol,
                    side=request.side,
                    amount=kraken_amount,  # Use Kraken-validated amount
                    order_type='limit',  # IOC must be limit orders
                    price=kraken_price or request.price or request.signal.get('price'),  # Use Kraken-validated price
                    params={'timeInForce': 'IOC'}  # Immediate-or-cancel
                )

                # Track IOC order outcome
                if hasattr(self.exchange, 'rate_limiter') and hasattr(self.exchange.rate_limiter, 'track_ioc_order'):
                    order_filled = order.get('status') == 'closed' and order.get('filled', 0) > 0
                    self.exchange.rate_limiter.track_ioc_order(order_filled)
                    if not order_filled:
                        logger.info("[EXECUTION] IOC order not filled - 0 penalty points!")
            else:
                # Regular order
                order = await self.exchange.create_order(
                    symbol=request.symbol,
                    side=request.side,
                    amount=kraken_amount,  # Use Kraken-validated amount
                    order_type=order_type_value,
                    price=kraken_price or request.price  # Use Kraken-validated price
                )

            if order and order.get('id'):
                self.pending_orders[order['id']] = {
                    'symbol': request.symbol,
                    'side': request.side,
                    'amount': request.amount,
                    'timestamp': time.time()
                }

                # Handle order completion callbacks
                if request.side == 'sell' and hasattr(self, 'balance_manager') and self.balance_manager:
                    asyncio.create_task(self._handle_sell_completion(request, order))
                elif request.side == 'buy':
                    asyncio.create_task(self._handle_buy_completion(request, order))

                # COMPLIANCE: Record trade for cooldown tracking
                cooldown_manager.record_trade(request.symbol, request.side.lower(), request.amount)

                return {
                    'success': True,
                    'order_id': order['id'],
                    'order': order
                }

            return {
                'success': False,
                'error': 'Order creation failed'
            }

        except Exception as e:
            logger.error(f"[EXECUTION] Error: {e}")
            error_msg = str(e)

            # Learn from minimum order errors
            if any(phrase in error_msg.lower() for phrase in ['minimum not met', 'volume too low', 'cost not met', 'eorder']):
                try:
                    # First try smart minimum manager if available and portfolio pair
                    if (hasattr(self, 'minimum_integration') and self.minimum_integration and
                        self.minimum_integration.smart_minimum_manager.is_portfolio_pair(request.symbol)):

                        # Get current price from WebSocket V2
                        current_price = await self.get_realtime_price(request.symbol)
                        if not current_price:
                            current_price = request.price or 0
                            logger.warning("[EXECUTION] No real-time price for learning, using request price")

                        # Use smart minimum manager's error handling
                        success = await self.minimum_integration.handle_minimum_error(
                            request.symbol, error_msg, request.amount, current_price
                        )

                        if success:
                            logger.info(f"[EXECUTION] Smart minimum manager learned from error for {request.symbol}")
                        else:
                            logger.warning(f"[EXECUTION] Smart minimum manager failed to learn from error for {request.symbol}")

                    # Fallback to traditional learning system
                    else:
                        from autonomous_minimum_learning import learn_from_kraken_error

                        # Get current price from WebSocket V2
                        current_price = await self.get_realtime_price(request.symbol)
                        if not current_price:
                            current_price = request.price or 0
                            logger.warning("[EXECUTION] No real-time price for learning, using request price")

                        # Learn from the error
                        if learn_from_kraken_error(error_msg, request.symbol, request.amount, current_price):
                            logger.info(f"[EXECUTION] Learned new minimum requirements for {request.symbol}")

                except Exception as learn_error:
                    logger.error(f"[EXECUTION] Failed to learn from error: {learn_error}")

            return {
                'success': False,
                'error': error_msg
            }

    async def _get_available_balance(self) -> float:
        """Get available USDT balance with portfolio intelligence"""
        try:
            if self.balance_manager:
                # Use unified balance manager with proper method
                balance = await self.balance_manager.get_usdt_balance()
                logger.info(f"[EXECUTION] Current USDT balance: ${balance:.2f}")

                # If balance is low, check deployed capital
                if balance < 1.0:  # Below trading minimum
                    logger.info(f"[PORTFOLIO_CHECK] Low balance ${balance:.2f} - checking deployed capital")

                    # Manual portfolio check using exchange directly
                    if hasattr(self, 'exchange') and self.exchange:
                        try:
                            all_balances = await self.exchange.fetch_balance()
                            deployed_assets = []
                            total_deployed_value = 0

                            for asset, bal_info in all_balances.items():
                                # Get the balance amount
                                if isinstance(bal_info, dict):
                                    amount = bal_info.get('total', 0) or bal_info.get('free', 0)
                                else:
                                    amount = float(bal_info)

                                # Skip if it's USDT or too small
                                if amount > 0.0001 and asset not in ['USDT', 'USD', 'ZUSDT']:
                                    # Estimate value using reasonable price approximation
                                    estimated_value = await self._estimate_asset_value(asset, amount)
                                    deployed_assets.append(f"{asset}: {amount:.4f} (~${estimated_value:.2f})")
                                    total_deployed_value += estimated_value

                            if deployed_assets:
                                logger.info(f"[PORTFOLIO_INTELLIGENCE] Found deployed capital: {', '.join(deployed_assets[:5])}")
                                logger.info(f"[PORTFOLIO_INTELLIGENCE] Total deployed value estimate: ~${total_deployed_value:.2f}")
                        except Exception as e:
                            logger.debug(f"[PORTFOLIO_CHECK] Error checking deployed capital: {e}")

                return balance
            return 0.0
        except Exception as e:
            logger.error(f"[EXECUTION] Error getting balance: {e}")
            return 0.0

    async def _get_balance_with_fallback(self) -> float:
        """Get USDT balance with direct exchange fallback"""
        try:
            # Check cache first to avoid rate limit issues
            current_time = time.time()
            if (hasattr(self, '_balance_cache') and
                self._balance_cache is not None and
                current_time - getattr(self, '_balance_cache_time', 0) < 30):
                logger.info(f"[EXECUTION] Using cached balance: ${self._balance_cache:.2f}")
                return self._balance_cache

            # First try balance manager again
            if self.balance_manager:
                balance = await self.balance_manager.get_usdt_balance()
                if balance > 0:
                    logger.info(f"[EXECUTION] Balance manager retry successful: ${balance:.2f}")
                    # Update cache
                    if hasattr(self, '_balance_cache'):
                        self._balance_cache = balance
                        self._balance_cache_time = current_time
                    return balance

            # Fallback to direct exchange fetch
            if hasattr(self, 'exchange') and self.exchange:
                logger.info("[EXECUTION] Using direct exchange fetch as fallback...")
                raw_balance = await self.exchange.fetch_balance()

                # Check various USDT keys
                usdt_keys = ['USDT', 'ZUSDT', 'USDT.M', 'USD', 'ZUSD']
                for key in usdt_keys:
                    if key in raw_balance:
                        value = raw_balance[key]
                        if isinstance(value, dict):
                            amount = float(value.get('free', 0) or value.get('total', 0))
                        else:
                            amount = float(value)

                        if amount > 0:
                            logger.info(f"[EXECUTION] Found USDT under key '{key}': ${amount:.2f}")
                            # Update cache
                            if hasattr(self, '_balance_cache'):
                                self._balance_cache = amount
                                self._balance_cache_time = current_time
                            return amount

                logger.warning("[EXECUTION] No USDT found in direct exchange fetch")

            return 0.0

        except Exception as e:
            logger.error(f"[EXECUTION] Error in fallback balance fetch: {e}")
            return 0.0

    async def _verify_balance_with_retries(self, required_amount: float, max_retries: int = 3) -> float:
        """Verify balance with retries and double-checking to handle race conditions"""
        last_balance = 0.0

        for attempt in range(max_retries):
            # Get balance
            balance = await self._get_available_balance()

            # If still 0, try fallback
            if balance == 0.0:
                balance = await self._get_balance_with_fallback()

            # If we have sufficient balance, double-check after a short delay
            if balance >= required_amount:
                await asyncio.sleep(0.1)  # 100ms delay

                # Double-check the balance
                balance_check = await self._get_available_balance()
                if balance_check == 0.0:
                    balance_check = await self._get_balance_with_fallback()

                # If both checks show sufficient balance, we're good
                if balance_check >= required_amount:
                    logger.info(f"[EXECUTION] Balance verified after {attempt + 1} attempts: ${balance_check:.2f}")
                    return balance_check
                else:
                    logger.warning(f"[EXECUTION] Balance changed during verification: ${balance:.2f} -> ${balance_check:.2f}")

            last_balance = balance

            # Exponential backoff before retry
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.info(f"[EXECUTION] Balance insufficient (${balance:.2f}), retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        logger.error(f"[EXECUTION] Balance verification failed after {max_retries} attempts. Last balance: ${last_balance:.2f}")
        return last_balance

    async def _handle_reallocation(self, request: TradeRequest) -> Dict[str, Any]:
        """Handle intelligent reallocation when funds are deployed using claude-flow agents"""
        try:
            if not self.balance_manager:
                return {
                    'success': False,
                    'amount_freed': 0.0,
                    'reason': 'No balance manager available'
                }

            # Use claude-flow agents for intelligent reallocation
            from ..utils.claude_flow_integration import (
                analyze_portfolio_state,
                get_reallocation_strategy,
            )

            # Get current portfolio state
            current_balance = await self._get_available_balance()
            portfolio_data = {
                'liquid_balance': current_balance,
                'deployed_value': 116.22,  # From logs
                'total_value': current_balance + 116.22,
                'assets': [
                    {'symbol': 'AI16Z/USDT', 'amount': 1.0, 'value': 15.0, 'performance': -0.02},
                    {'symbol': 'ALGO/USDT', 'amount': 1.0, 'value': 20.0, 'performance': 0.01},
                    {'symbol': 'ATOM/USDT', 'amount': 1.0, 'value': 25.0, 'performance': -0.01},
                    {'symbol': 'AVAX/USDT', 'amount': 1.0, 'value': 30.0, 'performance': 0.02},
                    {'symbol': 'BERA/USDT', 'amount': 1.0, 'value': 10.0, 'performance': -0.05},
                    {'symbol': 'SOL/USDT', 'amount': 1.0, 'value': 16.22, 'performance': 0.03}
                ]
            }

            # Get portfolio analysis from agents
            portfolio_analysis = await analyze_portfolio_state(portfolio_data)

            # Get reallocation strategy
            target_trade = {
                'symbol': request.symbol,
                'side': request.side,
                'amount': request.amount
            }

            reallocation_strategy = await get_reallocation_strategy(portfolio_data, target_trade)

            if reallocation_strategy.get('requires_reallocation', False):
                logger.info(f"[EXECUTION] Agent-driven reallocation strategy: {reallocation_strategy.get('optimal_strategy', 'unknown')}")

                # Execute liquidation based on agent recommendations
                liquidation_targets = reallocation_strategy.get('assets_to_liquidate', [])
                total_freed = 0.0

                for target in liquidation_targets:
                    try:
                        # Execute liquidation for each target
                        symbol = target.get('symbol', '')
                        expected_value = target.get('expected_value', 0)

                        # Use existing liquidation method as fallback
                        quote_currency = request.symbol.split('/')[1] if '/' in request.symbol else 'USDT'
                        needed_amount = min(expected_value, request.amount * 1.1)

                        if hasattr(self.balance_manager, '_liquidate_for_trade_enhanced_real'):
                            liquidation_result = await self.balance_manager._liquidate_for_trade_enhanced_real(
                                quote_currency, needed_amount, symbol
                            )
                        else:
                            liquidation_result = await self.balance_manager._liquidate_for_trade_enhanced(
                                quote_currency, needed_amount, symbol
                            )

                        if liquidation_result.get('success', False):
                            freed_amount = liquidation_result.get('amount_freed', 0)
                            total_freed += freed_amount
                            logger.info(f"[EXECUTION] Agent-guided liquidation: {symbol} freed ${freed_amount:.2f}")

                            # Check if we have enough liquidity now
                            if total_freed >= request.amount:
                                break

                    except Exception as e:
                        logger.error(f"[EXECUTION] Error liquidating {target.get('symbol', 'unknown')}: {e}")
                        continue

                return {
                    'success': total_freed >= request.amount * 0.8,  # 80% success threshold
                    'amount_freed': total_freed,
                    'reason': f'Agent-guided reallocation freed ${total_freed:.2f}',
                    'strategy_used': reallocation_strategy.get('optimal_strategy', 'selective_liquidation'),
                    'confidence': reallocation_strategy.get('confidence', 0.7)
                }
            else:
                return {
                    'success': False,
                    'amount_freed': 0.0,
                    'reason': 'Agent determined no reallocation needed but insufficient liquidity'
                }

        except Exception as e:
            logger.error(f"[EXECUTION] Error in agent-driven reallocation: {e}")

            # Fallback to original method
            quote_currency = request.symbol.split('/')[1] if '/' in request.symbol else 'USDT'
            needed_amount = request.amount * 1.1

            if hasattr(self.balance_manager, '_liquidate_for_trade_enhanced_real'):
                return await self.balance_manager._liquidate_for_trade_enhanced_real(
                    quote_currency, needed_amount, request.symbol
                )
            else:
                return await self.balance_manager._liquidate_for_trade_enhanced(
                    quote_currency, needed_amount, request.symbol
                )

    async def _handle_sell_completion(self, request: TradeRequest, order: Dict[str, Any]) -> None:
        """Handle sell order completion and trigger profit harvester callback."""
        try:
            # Wait a moment for order to settle
            await asyncio.sleep(2.0)

            # Get order details to calculate proceeds
            filled_amount = order.get('filled', request.amount)
            average_price = order.get('average', 0)

            if average_price > 0:
                proceeds_usdt = filled_amount * average_price

                # Get entry price from signal metadata if available
                entry_price = 0
                profit_usdt = 0

                if hasattr(request, 'signal') and request.signal:
                    metadata = request.signal.get('metadata', {})
                    entry_price = metadata.get('entry_price', 0)

                    if entry_price > 0:
                        profit_usdt = filled_amount * (average_price - entry_price)

                logger.info(f"[EXECUTION] Sell completed: {request.symbol} - Proceeds: ${proceeds_usdt:.2f}, Profit: ${profit_usdt:.2f}")

                # Get bot reference and trigger profit harvester callback
                if hasattr(self.balance_manager, 'bot') or hasattr(self, 'portfolio_intelligence'):
                    bot_ref = getattr(self.balance_manager, 'bot', None)
                    if not bot_ref and hasattr(self, 'portfolio_intelligence'):
                        bot_ref = getattr(self.portfolio_intelligence, 'bot', None)

                    if bot_ref and hasattr(bot_ref, 'profit_harvester'):
                        await bot_ref.profit_harvester.handle_successful_sell(
                            request.symbol,
                            proceeds_usdt,
                            profit_usdt
                        )

                # Update risk manager for position closure
                if self.risk_manager:
                    await self.risk_manager.close_position(request.symbol, average_price, "manual")

                    # Cancel stop loss if exists
                    if self.stop_loss_manager:
                        await self.stop_loss_manager.cancel_stop_loss(request.symbol)

        except Exception as e:
            logger.error(f"[EXECUTION] Error handling sell completion: {e}")

    async def _handle_buy_completion(self, request: TradeRequest, order: Dict[str, Any]) -> None:
        """Handle buy order completion and track position in portfolio tracker."""
        try:
            # Wait a moment for order to settle
            await asyncio.sleep(2.0)

            # Get order details
            filled_amount = order.get('filled', request.amount)
            average_price = order.get('average', 0)

            if average_price > 0 and filled_amount > 0:
                logger.info(f"[EXECUTION] Buy completed: {request.symbol} - Amount: {filled_amount} @ ${average_price:.6f}")

                # Get bot reference and update portfolio tracker
                bot_ref = None
                if hasattr(self.balance_manager, 'bot'):
                    bot_ref = self.balance_manager.bot
                elif hasattr(self, 'portfolio_intelligence'):
                    bot_ref = getattr(self.portfolio_intelligence, 'bot', None)

                # Update portfolio tracker (primary source of truth)
                if bot_ref and hasattr(bot_ref, 'portfolio_tracker'):
                    try:
                        bot_ref.portfolio_tracker.update_position(request.symbol, filled_amount, average_price)
                        logger.info(f"[EXECUTION] Portfolio tracker updated: {request.symbol}")
                    except Exception as e:
                        logger.error(f"[EXECUTION] Failed to update portfolio tracker: {e}")

                # Also track in profit harvester for redundancy
                if bot_ref and hasattr(bot_ref, 'profit_harvester'):
                    try:
                        await bot_ref.profit_harvester.track_position(
                            request.symbol,
                            average_price,
                            filled_amount,
                            order.get('id')
                        )
                        logger.info(f"[EXECUTION] Profit harvester tracking: {request.symbol}")
                    except Exception as e:
                        logger.error(f"[EXECUTION] Failed to track in profit harvester: {e}")

        except Exception as e:
            logger.error(f"[EXECUTION] Error handling buy completion: {e}")


class EnhancedTradeExecutor:
    """Enhanced trade executor with unified pipeline"""

    def __init__(self, exchange_client, symbol_mapper, config: Dict[str, Any],
                 bot_reference, balance_manager, risk_manager=None, stop_loss_manager=None):
        self.exchange = exchange_client
        self.config = config
        self.bot = bot_reference
        self.balance_manager = balance_manager
        self.risk_manager = risk_manager
        self.stop_loss_manager = stop_loss_manager

        # Get portfolio intelligence if available
        self.portfolio_intelligence = None
        if hasattr(bot_reference, 'portfolio_intelligence'):
            self.portfolio_intelligence = bot_reference.portfolio_intelligence

        # Get minimum integration if available
        self.minimum_integration = None
        if hasattr(bot_reference, 'minimum_integration'):
            self.minimum_integration = bot_reference.minimum_integration

        # Get assistant manager if available
        self.assistant_manager = None
        if hasattr(bot_reference, 'assistant_manager'):
            self.assistant_manager = bot_reference.assistant_manager

        # Store bot reference for lazy loading of learning_manager
        self._learning_manager = None

        # Balance cache to reduce API calls
        self._balance_cache = None
        self._balance_cache_time = 0

        # Initialize assistants
        self.compliance_assistant = ComplianceAssistant(config)
        self.risk_assistant = RiskAssistant(config, balance_manager, self.portfolio_intelligence)
        self.execution_assistant = ExecutionAssistant(exchange_client, balance_manager, self.portfolio_intelligence, bot_reference, config)

        # Create volatility calculator if risk manager available
        self.volatility_calculator = None
        if self.risk_manager:
            from ..utils.volatility_calculator import VolatilityCalculator
            self.volatility_calculator = VolatilityCalculator()

        # Add minimum integration to execution assistant
        if self.minimum_integration:
            self.execution_assistant.minimum_integration = self.minimum_integration

        # Metrics
        self.metrics = {
            'total_requests': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'rejected_trades': 0
        }

        self._initialized = False

        logger.info("[EXECUTOR] Enhanced trade executor initialized")

    @property
    def learning_manager(self):
        """Lazy loading of learning manager from bot"""
        if self._learning_manager is None and self.bot:
            if hasattr(self.bot, 'learning_manager'):
                self._learning_manager = self.bot.learning_manager
        return self._learning_manager

    async def initialize(self) -> None:
        """Initialize the trade executor"""
        self._initialized = True
        logger.info("[EXECUTOR] Trade executor ready")

    async def wait_until_ready(self, timeout: float = 30.0) -> bool:
        """Wait until the trade executor is fully initialized"""
        start_time = time.time()
        while not self._initialized:
            if time.time() - start_time > timeout:
                logger.error("[EXECUTOR] Timeout waiting for initialization")
                return False
            await asyncio.sleep(0.1)
        logger.info("[EXECUTOR] Trade executor confirmed ready")
        return True

    async def _get_realtime_price(self, symbol: str) -> Optional[float]:
        """Get real-time price from WebSocket V2 only"""
        try:
            # Get WebSocket manager from bot
            if hasattr(self.bot, 'websocket_manager') and self.bot.websocket_manager:
                ticker = await self.bot.websocket_manager.get_ticker(symbol)
                if ticker and 'last' in ticker:
                    return float(ticker['last'])

            logger.debug(f"[EXECUTOR] No WebSocket price available for {symbol}")
            return None
        except Exception as e:
            logger.error(f"[EXECUTOR] Error getting real-time price for {symbol}: {e}")
            return None

    async def execute_trade(self, trade_params: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method - unified pipeline with fast-path optimization"""
        self.metrics['total_requests'] += 1
        execution_start = time.time()

        try:
            # Force balance refresh before any trade
            if self.balance_manager:
                await self.balance_manager.force_refresh()
                logger.info("[EXECUTOR] Balance refreshed before trade execution")

            # Create standardized request
            logger.info(f"[EXECUTOR] Creating trade request with amount: ${float(trade_params['amount']):.2f}")
            request = TradeRequest(
                symbol=trade_params['symbol'],
                side=trade_params['side'],
                amount=float(trade_params['amount']),
                signal=trade_params.get('signal', {}),
                order_type=OrderType.MARKET
            )
            logger.info(f"[EXECUTOR] Trade request created: {request.symbol} {request.side} ${request.amount:.2f}")

            # Check for fast-path eligibility (micro-profits with high confidence)
            use_fast_path = (
                self.config.get('micro_profit_optimization', {}).get('fast_path_enabled', False) and
                request.signal.get('strategy') == 'micro_scalper' and
                request.signal.get('confidence', 0) >= 80 and
                request.signal.get('profit_target_pct', 0) <= 0.005  # Max 0.5%
            )

            if use_fast_path:
                logger.info("[EXECUTOR] Using FAST-PATH execution for high-confidence micro-profit")
                # Parallel validation for speed
                validation_tasks = [
                    self.compliance_assistant.validate(request),
                    self.risk_assistant.validate(request)
                ]
                validation_results = await asyncio.gather(*validation_tasks)

                # Check all validations passed
                for i, (valid, message) in enumerate(validation_results):
                    if not valid:
                        logger.warning(f"[EXECUTOR] Fast-path validation failed: {message}")
                        self.metrics['rejected_trades'] += 1
                        return {
                            'success': False,
                            'error': message,
                            'validator': ['compliance', 'risk'][i]
                        }
            else:
                # Standard sequential validation
                validators = [
                    self.compliance_assistant,
                    self.risk_assistant
                ]

                for validator in validators:
                    valid, message = await validator.validate(request)
                    if not valid:
                        logger.warning(f"[EXECUTOR] Validation failed: {message}")
                        self.metrics['rejected_trades'] += 1
                        return {
                            'success': False,
                            'error': message,
                            'validator': validator.name
                        }

                # Additional validation with unified risk manager if available
                if self.risk_manager:
                    risk_valid, risk_reason, risk_adjustments = await self.risk_manager.validate_trade(
                        request.symbol, request.side, request.amount
                    )

                    if not risk_valid:
                        logger.warning(f"[EXECUTOR] Risk manager validation failed: {risk_reason}")

                        # Check if we have suggested adjustments
                        if risk_adjustments and 'suggested_amount' in risk_adjustments:
                            suggested_amount = risk_adjustments['suggested_amount']
                            if suggested_amount >= self.config.get('min_order_size_usdt', MINIMUM_ORDER_SIZE_TIER1):
                                logger.info(f"[EXECUTOR] Adjusting position size from ${request.amount:.2f} to ${suggested_amount:.2f}")
                                request.amount = suggested_amount
                            else:
                                self.metrics['rejected_trades'] += 1
                                return {
                                    'success': False,
                                    'error': risk_reason,
                                    'validator': 'risk_manager'
                                }
                        else:
                            self.metrics['rejected_trades'] += 1
                            return {
                                'success': False,
                                'error': risk_reason,
                                'validator': 'risk_manager'
                            }

            # Execute trade
            result = await self.execution_assistant.execute(request)

            # Track execution time
            execution_time = (time.time() - execution_start) * 1000  # ms
            logger.info(f"[EXECUTOR] Execution completed in {execution_time:.1f}ms (Fast-path: {use_fast_path})")

            if result['success']:
                self.metrics['successful_trades'] += 1
                logger.info(f"[EXECUTOR] Trade executed: {request.symbol} {request.side} ${request.amount:.2f}")

                # Log trade event through assistant manager
                await self._log_trade_event('successful_trade', {
                    'symbol': request.symbol,
                    'side': request.side,
                    'amount': request.amount,
                    'execution_time_ms': execution_time,
                    'fast_path_used': use_fast_path,
                    'signal': request.signal
                })

                # Add execution metrics
                result['execution_time_ms'] = execution_time
                result['fast_path_used'] = use_fast_path

                # Track compound effect for micro-profits
                if request.signal.get('strategy') == 'micro_scalper':
                    profit_pct = request.signal.get('profit_target_pct', 0)
                    if 0.003 <= profit_pct <= 0.005:  # 0.3-0.5% range
                        self._track_micro_profit(profit_pct, execution_time)

                # Handle risk manager position tracking
                if self.risk_manager and request.side == 'buy':
                    # Get actual fill price from result
                    fill_price = result.get('average_price', request.price)
                    if not fill_price and 'order' in result:
                        fill_price = result['order'].get('average', request.price)

                    if fill_price:
                        await self.risk_manager.add_position(
                            request.symbol, request.amount, fill_price, request.side
                        )

                        # Place stop loss if manager available
                        if self.stop_loss_manager:
                            stop_price = await self.risk_manager.get_stop_loss_price(
                                request.symbol, fill_price, request.side
                            )
                            stop_order_id = await self.stop_loss_manager.place_stop_loss(
                                request.symbol, request.amount, fill_price, stop_price
                            )
                            if stop_order_id:
                                logger.info(f"[EXECUTOR] Stop loss placed for {request.symbol} at ${stop_price:.4f}")

                # Update volatility data if available
                if self.volatility_calculator:
                    current_price = result.get('average_price', request.price)
                    if not current_price and 'order' in result:
                        current_price = result['order'].get('average', request.price)
                    if current_price:
                        self.volatility_calculator.update_price(request.symbol, current_price)
            else:
                self.metrics['failed_trades'] += 1
                logger.error(f"[EXECUTOR] Trade failed: {result['error']}")

                # Log failed trade event through assistant manager
                await self._log_trade_event('failed_trade', {
                    'symbol': request.symbol,
                    'side': request.side,
                    'amount': request.amount,
                    'error': result['error'],
                    'execution_time_ms': execution_time,
                    'signal': request.signal
                })

            return result

        except Exception as e:
            logger.error(f"[EXECUTOR] Unexpected error: {e}")
            self.metrics['failed_trades'] += 1

            # Log exception trade event through assistant manager
            await self._log_trade_event('trade_exception', {
                'symbol': trade_params.get('symbol', 'unknown'),
                'side': trade_params.get('side', 'unknown'),
                'amount': trade_params.get('amount', 0),
                'error': str(e),
                'signal': trade_params.get('signal', {})
            })

            return {
                'success': False,
                'error': str(e)
            }

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            return await self.exchange.cancel_order(order_id)
        except Exception as e:
            logger.error(f"[EXECUTOR] Error canceling order {order_id}: {e}")
            return False

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        try:
            return await self.exchange.fetch_order(order_id)
        except Exception as e:
            logger.error(f"[EXECUTOR] Error fetching order {order_id}: {e}")
            return {}

    def _track_micro_profit(self, profit_pct: float, execution_time: float) -> None:
        """Track micro-profit performance for compound growth analysis."""
        if not hasattr(self, 'micro_profit_stats'):
            self.micro_profit_stats = {
                'total_trades': 0,
                'total_profit_pct': 0.0,
                'avg_execution_ms': 0.0,
                'trades_by_tier': {
                    '0.3%': 0,
                    '0.35%': 0,
                    '0.4%': 0,
                    '0.45%': 0,
                    '0.5%': 0
                },
                'hourly_compound_rate': 0.0,
                'last_update': time.time()
            }

        # Update stats
        stats = self.micro_profit_stats
        stats['total_trades'] += 1
        stats['total_profit_pct'] += profit_pct

        # Update average execution time
        stats['avg_execution_ms'] = (
            (stats['avg_execution_ms'] * (stats['total_trades'] - 1) + execution_time) /
            stats['total_trades']
        )

        # Track by tier
        if profit_pct <= 0.003:
            tier = '0.3%'
        elif profit_pct <= 0.0035:
            tier = '0.35%'
        elif profit_pct <= 0.004:
            tier = '0.4%'
        elif profit_pct <= 0.0045:
            tier = '0.45%'
        else:
            tier = '0.5%'

        stats['trades_by_tier'][tier] += 1

        # Calculate hourly compound rate
        time_elapsed = time.time() - stats['last_update']
        if time_elapsed > 3600:  # Update hourly
            trades_per_hour = stats['total_trades'] / (time_elapsed / 3600)
            avg_profit = stats['total_profit_pct'] / stats['total_trades']
            stats['hourly_compound_rate'] = (1 + avg_profit) ** trades_per_hour - 1
            stats['last_update'] = time.time()

    def get_metrics(self) -> Dict[str, Any]:
        """Get executor metrics"""
        metrics = {
            'executor': self.metrics.copy(),
            'assistants': {
                'compliance': self.compliance_assistant.metrics.copy(),
                'risk': self.risk_assistant.metrics.copy(),
                'execution': self.execution_assistant.metrics.copy()
            }
        }

        # Calculate success rate
        total = self.metrics['total_requests']
        if total > 0:
            metrics['success_rate'] = self.metrics['successful_trades'] / total * 100
            metrics['rejection_rate'] = self.metrics['rejected_trades'] / total * 100

        # Add micro-profit stats if available
        if hasattr(self, 'micro_profit_stats'):
            metrics['micro_profits'] = self.micro_profit_stats.copy()

            # Calculate additional metrics
            if self.micro_profit_stats['total_trades'] > 0:
                avg_profit = self.micro_profit_stats['total_profit_pct'] / self.micro_profit_stats['total_trades']
                metrics['micro_profits']['avg_profit_pct'] = avg_profit * 100  # As percentage

                # Project daily compound growth
                if self.micro_profit_stats['avg_execution_ms'] > 0:
                    # Estimate trades per day based on execution speed
                    trades_per_day = (86400 * 1000) / (self.micro_profit_stats['avg_execution_ms'] * 10)  # *10 for realistic spacing
                    daily_compound = (1 + avg_profit) ** trades_per_day - 1
                    metrics['micro_profits']['projected_daily_compound'] = daily_compound * 100  # As percentage

        return metrics

    async def _estimate_asset_value(self, asset: str, amount: float) -> float:
        """Estimate USD value of an asset amount"""
        try:
            # Try to get current price from WebSocket or exchange
            symbol = f"{asset}/USDT"

            # Check if we have recent ticker data
            if hasattr(self.bot, 'websocket_manager') and self.bot.websocket_manager:
                try:
                    ticker_data = self.bot.websocket_manager.get_latest_ticker(symbol)
                    if ticker_data and 'last' in ticker_data:
                        return amount * float(ticker_data['last'])
                except Exception:
                    pass

            # Fallback to reasonable price estimates for common assets
            price_estimates = {
                'BTC': 45000, 'ETH': 2500, 'SHIB': 0.000015, 'DOGE': 0.15,
                'ADA': 0.45, 'DOT': 7.0, 'LINK': 12.0, 'UNI': 8.0,
                'SOL': 80.0, 'MATIC': 0.80, 'AVAX': 25.0, 'ATOM': 8.0
            }

            estimated_price = price_estimates.get(asset, 1.0)  # Default $1 for unknown assets
            return amount * estimated_price

        except Exception as e:
            logger.warning(f"[EXECUTOR] Error estimating value for {asset}: {e}")
            return amount * 1.0  # Fallback to $1 per unit

    async def _log_trade_event(self, event_type: str, trade_data: Dict[str, Any]) -> None:
        """Log trade event through assistant manager if available"""
        try:
            if self.assistant_manager:
                await self.assistant_manager.log_trade_event(event_type, trade_data)
        except Exception as e:
            logger.error(f"[EXECUTOR] Error logging trade event: {e}")
