"""
Assistant Manager - Coordinates all AI assistants in the trading bot
"""

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AssistantManager:
    """
    Manages and coordinates all AI assistants for the trading bot.
    Provides unified interface for assistant interactions and learning integration.
    """

    def __init__(self, bot, learning_manager=None, config=None):
        """Initialize assistant manager with bot reference"""
        self.bot = bot
        self.learning_manager = learning_manager
        self.config = config or {}
        self.logger = logger

        # Assistant instances
        self.assistants = {}
        self.assistant_stats = {}

        # Assistant configuration
        self.assistant_config = {
            'adaptive_selling': {
                'enabled': True,
                'module': 'src.assistants.adaptive_selling_assistant',
                'class': 'AdaptiveSellingAssistant'
            },
            'buy_logic': {
                'enabled': True,
                'module': 'src.assistants.buy_logic_assistant',
                'class': 'BuyLogicAssistant'
            },
            'sell_logic': {
                'enabled': True,
                'module': 'src.assistants.sell_logic_assistant',
                'class': 'SellLogicAssistant'
            },
            'memory': {
                'enabled': True,
                'module': 'src.assistants.memory_assistant',
                'class': 'MemoryAssistant'
            },
            'analytics': {
                'enabled': True,
                'module': 'src.assistants.logging_analytics_assistant',
                'class': 'LoggingAnalyticsAssistant'
            }
        }

        self.logger.info("[ASSISTANT_MANAGER] Assistant manager initialized")

    async def initialize(self):
        """Initialize all configured assistants"""
        self.logger.info("[ASSISTANT_MANAGER] Initializing assistants...")

        for assistant_name, config in self.assistant_config.items():
            if not config.get('enabled', True):
                continue

            try:
                # Dynamic import
                module_name = config['module']
                class_name = config['class']

                module = __import__(module_name, fromlist=[class_name])
                assistant_class = getattr(module, class_name)

                # Create assistant instance
                if assistant_name == 'adaptive_selling':
                    # Adaptive selling needs bot reference
                    self.assistants[assistant_name] = assistant_class(bot=self.bot)
                elif assistant_name == 'memory':
                    # Memory assistant needs bot reference
                    self.assistants[assistant_name] = assistant_class(bot=self.bot)
                elif assistant_name in ['analytics', 'buy_logic', 'sell_logic']:
                    # These need trade executor reference
                    # Create a mock trade executor if not available
                    trade_executor = getattr(self.bot, 'trade_executor', None)
                    if trade_executor:
                        self.assistants[assistant_name] = assistant_class(trade_executor)
                    else:
                        # Skip if trade executor not available
                        self.logger.warning(f"[ASSISTANT_MANAGER] Skipping {assistant_name} - no trade executor available")
                        continue
                else:
                    # Standard initialization
                    self.assistants[assistant_name] = assistant_class()

                # Initialize if method exists
                if hasattr(self.assistants[assistant_name], 'initialize'):
                    await self.assistants[assistant_name].initialize()

                self.assistant_stats[assistant_name] = {
                    'initialized': datetime.now(),
                    'calls': 0,
                    'errors': 0,
                    'last_call': None
                }

                self.logger.info(f"[ASSISTANT_MANAGER] Initialized {assistant_name} assistant")

            except Exception as e:
                self.logger.error(f"[ASSISTANT_MANAGER] Failed to initialize {assistant_name}: {e}")

    async def get_buy_recommendation(self, symbol: str, market_data: dict[str, Any]) -> dict[str, Any]:
        """Get buy recommendation from buy logic assistant"""
        try:
            if 'buy_logic' in self.assistants:
                self._update_stats('buy_logic')

                # Call buy logic assistant
                recommendation = await self.assistants['buy_logic'].analyze_buy_opportunity(
                    symbol=symbol,
                    market_data=market_data,
                    portfolio_state=await self._get_portfolio_state()
                )

                # Log to learning system
                if self.learning_manager:
                    self.learning_manager.record_event('buy_recommendation', {
                        'symbol': symbol,
                        'recommendation': recommendation,
                        'timestamp': datetime.now().isoformat()
                    })

                return recommendation

            return {'recommend': False, 'reason': 'Buy logic assistant not available'}

        except Exception as e:
            self.logger.error(f"[ASSISTANT_MANAGER] Error getting buy recommendation: {e}")
            self._record_error('buy_logic', str(e))
            return {'recommend': False, 'reason': f'Error: {str(e)}'}

    async def get_sell_recommendation(self, symbol: str, position: dict[str, Any]) -> dict[str, Any]:
        """Get sell recommendation from sell logic assistant"""
        try:
            # Try adaptive selling first
            if 'adaptive_selling' in self.assistants:
                self._update_stats('adaptive_selling')

                recommendation = await self.assistants['adaptive_selling'].evaluate_position(
                    symbol=symbol,
                    position=position,
                    market_data=await self._get_market_data(symbol)
                )

                # Log to learning system
                if self.learning_manager:
                    self.learning_manager.record_event('sell_recommendation', {
                        'symbol': symbol,
                        'recommendation': recommendation,
                        'assistant': 'adaptive_selling',
                        'timestamp': datetime.now().isoformat()
                    })

                return recommendation

            # Fallback to basic sell logic
            elif 'sell_logic' in self.assistants:
                self._update_stats('sell_logic')
                return await self.assistants['sell_logic'].analyze_sell_opportunity(
                    symbol=symbol,
                    position=position
                )

            return {'recommend': False, 'reason': 'Sell logic assistants not available'}

        except Exception as e:
            self.logger.error(f"[ASSISTANT_MANAGER] Error getting sell recommendation: {e}")
            self._record_error('sell_logic', str(e))
            return {'recommend': False, 'reason': f'Error: {str(e)}'}

    async def log_trade_event(self, event_type: str, trade_data: dict[str, Any]):
        """Log trade event through analytics assistant"""
        try:
            if 'analytics' in self.assistants:
                self._update_stats('analytics')
                await self.assistants['analytics'].log_event(event_type, trade_data)

            # Also log to learning system
            if self.learning_manager:
                self.learning_manager.record_event(f'trade_{event_type}', trade_data)

        except Exception as e:
            self.logger.error(f"[ASSISTANT_MANAGER] Error logging trade event: {e}")
            self._record_error('analytics', str(e))

    async def remember_pattern(self, pattern_type: str, pattern_data: dict[str, Any]):
        """Store pattern in memory assistant"""
        try:
            if 'memory' in self.assistants:
                self._update_stats('memory')
                await self.assistants['memory'].store_pattern(pattern_type, pattern_data)

            # Also store in learning system
            if self.learning_manager:
                self.learning_manager.learn_pattern(pattern_type, pattern_data)

        except Exception as e:
            self.logger.error(f"[ASSISTANT_MANAGER] Error remembering pattern: {e}")
            self._record_error('memory', str(e))

    async def get_historical_patterns(self, pattern_type: str, symbol: Optional[str] = None) -> list[dict[str, Any]]:
        """Retrieve historical patterns from memory"""
        try:
            if 'memory' in self.assistants:
                self._update_stats('memory')
                return await self.assistants['memory'].get_patterns(pattern_type, symbol)

            return []

        except Exception as e:
            self.logger.error(f"[ASSISTANT_MANAGER] Error retrieving patterns: {e}")
            self._record_error('memory', str(e))
            return []

    def _update_stats(self, assistant_name: str):
        """Update assistant usage statistics"""
        if assistant_name in self.assistant_stats:
            self.assistant_stats[assistant_name]['calls'] += 1
            self.assistant_stats[assistant_name]['last_call'] = datetime.now()

    def _record_error(self, assistant_name: str, error: str):
        """Record assistant error"""
        if assistant_name in self.assistant_stats:
            self.assistant_stats[assistant_name]['errors'] += 1

        # Log to learning system for error pattern recognition
        if self.learning_manager:
            self.learning_manager.record_error(
                component=f"assistant_{assistant_name}",
                error_message=error,
                details={
                    'assistant': assistant_name,
                    'timestamp': datetime.now().isoformat()
                }
            )

    async def _get_portfolio_state(self) -> dict[str, Any]:
        """Get current portfolio state from bot"""
        try:
            if hasattr(self.bot, 'balance_manager') and self.bot.balance_manager:
                return await self.bot.balance_manager.analyze_portfolio_state('USDT')
            return {}
        except Exception as e:
            self.logger.error(f"[ASSISTANT_MANAGER] Error getting portfolio state: {e}")
            return {}

    async def _get_market_data(self, symbol: str) -> dict[str, Any]:
        """Get current market data for symbol"""
        try:
            if hasattr(self.bot, 'exchange') and self.bot.exchange:
                ticker = await self.bot.exchange.fetch_ticker(symbol)
                return ticker
            return {}
        except Exception as e:
            self.logger.error(f"[ASSISTANT_MANAGER] Error getting market data: {e}")
            return {}

    def get_assistant_stats(self) -> dict[str, Any]:
        """Get statistics for all assistants"""
        return {
            'assistants': self.assistant_stats,
            'total_assistants': len(self.assistants),
            'active_assistants': list(self.assistants.keys()),
            'total_calls': sum(stats['calls'] for stats in self.assistant_stats.values()),
            'total_errors': sum(stats['errors'] for stats in self.assistant_stats.values())
        }

    async def shutdown(self):
        """Shutdown all assistants gracefully"""
        self.logger.info("[ASSISTANT_MANAGER] Shutting down assistants...")

        for name, assistant in self.assistants.items():
            try:
                if hasattr(assistant, 'shutdown'):
                    await assistant.shutdown()
                self.logger.info(f"[ASSISTANT_MANAGER] Shut down {name} assistant")
            except Exception as e:
                self.logger.error(f"[ASSISTANT_MANAGER] Error shutting down {name}: {e}")

        self.assistants.clear()
        self.logger.info("[ASSISTANT_MANAGER] All assistants shut down")
