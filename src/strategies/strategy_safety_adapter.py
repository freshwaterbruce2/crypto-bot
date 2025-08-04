"""
Strategy Safety Adapter - Integration Layer for Order Safety System
==================================================================

CRITICAL: This adapter ensures all trading strategies use the new Order Safety System
to prevent systematic order rejections and comply with Kraken 2025 requirements.

Key Features:
- Wraps all strategy order execution with safety checks
- Integrates atomic balance verification
- Applies fee buffers and minimum validations
- Provides WebSocket V2 data integration
- Circuit breaker protection
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union
from decimal import Decimal

from ..utils.order_safety_system import (
    OrderSafetySystem, 
    OrderRequest, 
    OrderType,
    safe_buy_order,
    safe_sell_order,
    validate_order_feasibility
)
from ..utils.secure_credentials import get_safe_key_id

logger = logging.getLogger(__name__)


class StrategySafetyAdapter:
    """
    Safety adapter that wraps trading strategies with comprehensive protection
    
    This ensures all strategies benefit from:
    - P0 critical fixes (atomic balance, fee buffers, minimums)
    - WebSocket V2 optimizations
    - Circuit breaker protection
    - Comprehensive error handling
    """
    
    def __init__(self, strategy_instance, exchange_wrapper=None, config: Dict[str, Any] = None):
        self.strategy = strategy_instance
        self.exchange = exchange_wrapper
        self.config = config or {}
        
        # Initialize safety system
        self.safety_system = OrderSafetySystem(exchange_wrapper, config)
        
        # Strategy performance tracking
        self.total_orders = 0
        self.successful_orders = 0
        self.rejected_orders = 0
        self.last_order_time = 0
        
        logger.info(f"[STRATEGY_SAFETY] Safety adapter initialized for {self.strategy.__class__.__name__}")
        logger.info(f"[STRATEGY_SAFETY] API Key ID: {get_safe_key_id()}")
    
    async def safe_execute_buy_order(self, 
                                   symbol: str, 
                                   amount: Union[float, Decimal],
                                   price: Optional[Union[float, Decimal]] = None,
                                   **kwargs) -> Dict[str, Any]:
        """
        Safely execute buy order with all P0 protections
        
        This replaces direct exchange.create_order() calls in strategies
        """
        try:
            self.total_orders += 1
            
            logger.info(f"[STRATEGY_SAFETY] Executing safe buy order: {amount} {symbol}")
            
            # Use the safe order system instead of direct exchange calls
            result = await safe_buy_order(
                symbol=symbol,
                amount=amount,
                exchange_wrapper=self.exchange,
                config=self.config
            )
            
            self.successful_orders += 1
            self.last_order_time = asyncio.get_event_loop().time()
            
            logger.info(f"[STRATEGY_SAFETY] Buy order successful: {result.get('id', 'unknown')}")
            return result
            
        except Exception as e:
            self.rejected_orders += 1
            logger.error(f"[STRATEGY_SAFETY] Buy order failed: {e}")
            
            # Return standardized error response
            return {
                'status': 'failed',
                'error': str(e),
                'order_type': 'buy',
                'symbol': symbol,
                'amount': float(amount),
                'safety_protected': True
            }
    
    async def safe_execute_sell_order(self,
                                    symbol: str,
                                    amount: Union[float, Decimal], 
                                    price: Optional[Union[float, Decimal]] = None,
                                    **kwargs) -> Dict[str, Any]:
        """
        Safely execute sell order with all P0 protections
        """
        try:
            self.total_orders += 1
            
            logger.info(f"[STRATEGY_SAFETY] Executing safe sell order: {amount} {symbol}")
            
            # Use the safe order system
            result = await safe_sell_order(
                symbol=symbol,
                amount=amount,
                exchange_wrapper=self.exchange,
                config=self.config
            )
            
            self.successful_orders += 1
            self.last_order_time = asyncio.get_event_loop().time()
            
            logger.info(f"[STRATEGY_SAFETY] Sell order successful: {result.get('id', 'unknown')}")
            return result
            
        except Exception as e:
            self.rejected_orders += 1
            logger.error(f"[STRATEGY_SAFETY] Sell order failed: {e}")
            
            return {
                'status': 'failed',
                'error': str(e),
                'order_type': 'sell',
                'symbol': symbol,
                'amount': float(amount),
                'safety_protected': True
            }
    
    async def validate_strategy_order(self,
                                    symbol: str,
                                    side: str,
                                    amount: Union[float, Decimal]) -> Dict[str, Any]:
        """
        Validate order feasibility before strategy execution
        
        This allows strategies to check if orders will succeed before committing
        """
        try:
            result = await validate_order_feasibility(
                symbol=symbol,
                side=side,
                amount=amount,
                exchange_wrapper=self.exchange,
                config=self.config
            )
            
            logger.debug(f"[STRATEGY_SAFETY] Order validation: {symbol} {side} {amount} -> {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"[STRATEGY_SAFETY] Order validation failed: {e}")
            return {
                'status': 'invalid',
                'can_execute': False,
                'error': str(e)
            }
    
    def get_websocket_price_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time WebSocket V2 price data instead of REST API calls
        
        This optimizes strategies to use WebSocket V2 data streams
        """
        try:
            # This would integrate with your WebSocket V2 manager
            # For now, return a standardized format
            
            # Check if WebSocket data is available
            if hasattr(self.exchange, 'websocket_manager'):
                ws_data = self.exchange.websocket_manager.get_ticker_data(symbol)
                if ws_data:
                    return {
                        'price': ws_data.get('last', 0),
                        'bid': ws_data.get('bid', 0),
                        'ask': ws_data.get('ask', 0),
                        'volume': ws_data.get('volume', 0),
                        'timestamp': ws_data.get('timestamp', 0),
                        'source': 'websocket_v2'
                    }
            
            # Fallback to exchange if WebSocket not available
            logger.warning(f"[STRATEGY_SAFETY] WebSocket data not available for {symbol}, using fallback")
            return {
                'price': 0,
                'source': 'fallback'
            }
            
        except Exception as e:
            logger.error(f"[STRATEGY_SAFETY] Error getting WebSocket price data: {e}")
            return {'price': 0, 'source': 'error'}
    
    def get_strategy_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive strategy performance metrics"""
        success_rate = (self.successful_orders / self.total_orders * 100) if self.total_orders > 0 else 0
        
        return {
            'strategy_name': self.strategy.__class__.__name__,
            'total_orders': self.total_orders,
            'successful_orders': self.successful_orders,
            'rejected_orders': self.rejected_orders,
            'success_rate_pct': round(success_rate, 2),
            'last_order_time': self.last_order_time,
            'safety_system_active': True,
            'order_safety_status': self.safety_system.get_safety_status()
        }
    
    async def execute_strategy_with_safety(self, 
                                         symbol: str, 
                                         timeframe: str = '1m') -> Dict[str, Any]:
        """
        Execute strategy analysis with safety checks and optimizations
        
        This wraps the strategy's analyze() method with additional safety
        """
        try:
            # Get WebSocket V2 optimized data
            price_data = self.get_websocket_price_data(symbol)
            
            if price_data['price'] <= 0:
                return {
                    'action': 'HOLD',
                    'confidence': 0,
                    'reason': 'No price data available',
                    'safety_protected': True
                }
            
            # Execute strategy analysis
            if hasattr(self.strategy, 'analyze'):
                result = await self.strategy.analyze(symbol, timeframe)
            else:
                logger.error(f"[STRATEGY_SAFETY] Strategy {self.strategy.__class__.__name__} missing analyze() method")
                return {
                    'action': 'HOLD',
                    'confidence': 0,
                    'reason': 'Strategy analyze method not found',
                    'safety_protected': True
                }
            
            # Add safety metadata
            result['safety_protected'] = True
            result['websocket_data_used'] = price_data['source'] == 'websocket_v2'
            result['price_data_age'] = asyncio.get_event_loop().time() - price_data.get('timestamp', 0)
            
            # Validate any orders before execution
            if result.get('action') in ['BUY', 'SELL'] and result.get('confidence', 0) > 0:
                # Get suggested order size from strategy or use default
                order_size = result.get('order_size', self.config.get('position_size_usdt', 5.0))
                
                # Validate order feasibility
                validation = await self.validate_strategy_order(
                    symbol=symbol,
                    side=result['action'].lower(),
                    amount=order_size
                )
                
                if not validation.get('can_execute', False):
                    logger.warning(f"[STRATEGY_SAFETY] Order validation failed: {validation.get('error')}")
                    result['action'] = 'HOLD'
                    result['confidence'] = 0
                    result['reason'] = f"Order validation failed: {validation.get('error')}"
            
            return result
            
        except Exception as e:
            logger.error(f"[STRATEGY_SAFETY] Strategy execution error: {e}")
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reason': f'Strategy execution error: {str(e)}',
                'safety_protected': True
            }


# Convenience function for easy strategy wrapping
def wrap_strategy_with_safety(strategy_instance, 
                            exchange_wrapper=None, 
                            config: Dict[str, Any] = None) -> StrategySafetyAdapter:
    """
    Wrap any strategy with comprehensive safety protection
    
    Usage:
        original_strategy = QuantumFluctuationScalper(config)
        safe_strategy = wrap_strategy_with_safety(original_strategy, exchange, config)
        
        # Now use safe_strategy instead of original_strategy
        result = await safe_strategy.execute_strategy_with_safety(symbol)
    """
    return StrategySafetyAdapter(strategy_instance, exchange_wrapper, config)


# Decorator for automatic safety wrapping
def safety_protected_strategy(exchange_wrapper=None, config=None):
    """
    Decorator to automatically wrap strategy methods with safety protection
    
    Usage:
        @safety_protected_strategy(exchange, config)
        class MyStrategy(BaseStrategy):
            async def analyze(self, symbol, timeframe):
                # Strategy logic here
                pass
    """
    def decorator(strategy_class):
        original_init = strategy_class.__init__
        
        def wrapped_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._safety_adapter = StrategySafetyAdapter(self, exchange_wrapper, config)
        
        strategy_class.__init__ = wrapped_init
        return strategy_class
    
    return decorator