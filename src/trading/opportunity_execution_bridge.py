"""
Opportunity Execution Bridge
Connects opportunity scanner to trade executor
"""

import logging
import asyncio

logger = logging.getLogger(__name__)

class OpportunityExecutionBridge:
    """Bridges opportunity scanner with trade executor"""
    
    def __init__(self, bot):
        self.bot = bot
        self.execution_queue = asyncio.Queue()
        self.executing = False
    
    async def process_opportunities(self, opportunities):
        """Process opportunities and execute trades"""
        if not opportunities:
            return
        
        # Check executor readiness
        if not self._is_ready_for_execution():
            logger.warning("[OPP_BRIDGE] Executor not ready, queueing opportunities")
            for opp in opportunities:
                await self.execution_queue.put(opp)
            return
        
        # Execute best opportunity
        best_opp = self._select_best_opportunity(opportunities)
        if best_opp:
            await self.execute_opportunity(best_opp)
    
    async def execute_opportunity(self, opportunity):
        """Execute a single opportunity"""
        try:
            self.executing = True
            
            symbol = opportunity.get('symbol')
            side = opportunity.get('side', 'buy')
            confidence = opportunity.get('confidence', 0)
            
            logger.info(f"[OPP_BRIDGE] Executing {symbol} {side} (confidence: {confidence:.1%})")
            
            # Dynamic position sizing based on available balance
            position_size = await self._calculate_dynamic_position_size(symbol)
            
            if position_size is None:
                logger.info(f"[OPP_BRIDGE] [PAUSE][EMOJI]  SKIPPING {symbol} - insufficient balance for minimum order")
                return
            
            logger.info(f"[OPP_BRIDGE] Dynamic position size: ${position_size:.2f} (bot config: ${self.bot.position_size_usd:.2f})")
            
            # Execute trade
            trade_params = {
                'symbol': symbol,
                'side': side,
                'amount': position_size,
                'signal': opportunity
            }
            logger.info(f"[OPP_BRIDGE] Sending to executor: {trade_params['symbol']} {trade_params['side']} ${trade_params['amount']:.2f}")
            result = await self.bot.trade_executor.execute_trade(trade_params)
            
            if result.get('success'):
                logger.info(f"[OPP_BRIDGE] [EMOJI] Trade executed: {symbol}")
            else:
                logger.error(f"[OPP_BRIDGE] [EMOJI] Trade failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"[OPP_BRIDGE] Execution error: {e}")
        finally:
            self.executing = False
    
    def _is_ready_for_execution(self):
        """Check if ready to execute trades"""
        return (self.bot.running and
                hasattr(self.bot, 'trade_executor') and
                self.bot.trade_executor is not None and
                not self.executing)
    
    def _select_best_opportunity(self, opportunities):
        """Select best opportunity to execute"""
        # Filter by minimum confidence
        min_confidence = 0.3  # Lower threshold for testing
        valid_opps = [o for o in opportunities if o.get('confidence', 0) >= min_confidence]
        
        if not valid_opps:
            return None
        
        # Sort by confidence
        return max(valid_opps, key=lambda x: x.get('confidence', 0))
    
    async def process_queued_opportunities(self):
        """Process any queued opportunities"""
        while not self.execution_queue.empty() and self._is_ready_for_execution():
            opportunity = await self.execution_queue.get()
            await self.execute_opportunity(opportunity)
    
    async def _calculate_dynamic_position_size(self, symbol):
        """Calculate dynamic position size based on available balance and pair requirements"""
        try:
            # Get configuration values
            use_dynamic = self.bot.config.get('use_dynamic_position_sizing', True)
            position_pct = self.bot.config.get('position_size_percentage', 0.7)
            max_position = self.bot.config.get('max_order_size_usdt', 10.0)
            
            # Get available balance
            if hasattr(self.bot, 'balance_manager'):
                balance = await self.bot.balance_manager.get_balance_for_asset('USDT')
                available_balance = balance if isinstance(balance, (int, float)) else balance.get('free', 0)
            else:
                logger.warning("[OPP_BRIDGE] No balance manager available")
                return None
            
            # Check if this is a portfolio pair and get its requirements
            # Respect tier-1 limit for starter accounts
            tier_1_limit = self.bot.config.get('tier_1_trade_limit', 3.5)
            portfolio_min_cost = min(3.5, tier_1_limit)  # Default minimum respecting tier limit
            if hasattr(self.bot, 'minimum_integration') and self.bot.minimum_integration:
                try:
                    # Add null checks for nested attributes
                    if hasattr(self.bot.minimum_integration, 'smart_minimum_manager'):
                        smm = self.bot.minimum_integration.smart_minimum_manager
                        if hasattr(smm, 'is_portfolio_pair') and smm.is_portfolio_pair(symbol):
                            if hasattr(smm, 'get_pair_tier'):
                                tier = smm.get_pair_tier(symbol)
                                if hasattr(smm, 'TIER_MIN_COSTS') and tier in smm.TIER_MIN_COSTS:
                                    portfolio_min_cost = smm.TIER_MIN_COSTS[tier]
                                    logger.debug(f"[OPP_BRIDGE] Portfolio pair {symbol} requires ${portfolio_min_cost:.2f} minimum")
                except Exception as e:
                    logger.warning(f"[OPP_BRIDGE] Error getting portfolio minimums: {e}")
                    # Continue with default minimum
            
            # Dynamic position sizing logic
            if use_dynamic and available_balance > 0:
                if available_balance >= portfolio_min_cost:
                    # Use percentage of available balance, capped at max_position
                    position_size = min(available_balance * position_pct, max_position)
                    
                    # Ensure it meets minimum requirements
                    if position_size >= portfolio_min_cost:
                        logger.info(f"[OPP_BRIDGE] Dynamic sizing: ${position_size:.2f} ({position_pct*100}% of ${available_balance:.2f})")
                        return position_size
                    else:
                        # Adjust to minimum if close
                        if available_balance >= portfolio_min_cost:
                            logger.info(f"[OPP_BRIDGE] Adjusting to minimum: ${portfolio_min_cost:.2f}")
                            return portfolio_min_cost
                
                # Balance too low for this pair
                logger.info(f"[OPP_BRIDGE] Balance ${available_balance:.2f} below minimum ${portfolio_min_cost:.2f} for {symbol}")
                return None
            else:
                # Fallback to configured position size
                configured_size = self.bot.position_size_usd  # Already respects tier limit
                if available_balance >= configured_size:
                    return configured_size
                else:
                    logger.info(f"[OPP_BRIDGE] Balance ${available_balance:.2f} below configured size ${configured_size:.2f}")
                    return None
                    
        except Exception as e:
            logger.error(f"[OPP_BRIDGE] Error calculating position size: {e}")
            # Fallback to conservative sizing
            try:
                balance = await self.bot.balance_manager.get_balance_for_asset('USDT')
                available_balance = balance if isinstance(balance, (int, float)) else balance.get('free', 0)
                tier_1_limit = self.bot.config.get('tier_1_trade_limit', 3.5)
                min_required = min(3.5, tier_1_limit)
                if available_balance >= min_required:
                    # Use 90% of available, but cap at tier limit
                    size = available_balance * 0.9
                    if self.bot.config.get('kraken_api_tier', 'starter') == 'starter':
                        size = min(size, tier_1_limit)
                    return size
            except:
                pass
            return None
