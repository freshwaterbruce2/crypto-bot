"""
Fast Start Strategy
Quick profit-oriented trading strategy for immediate market opportunities
"""

import asyncio
import logging
import time
from ..utils.position_sizing import calculate_position_size
from typing import Dict, Any, Optional, List, Union
from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class FastStartStrategy(BaseStrategy):
    """Fast start strategy for quick profits"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize fast start strategy"""
        # Extract required parameters for BaseStrategy constructor
        exchange = config.get('exchange')
        symbol = config.get('symbol', 'BTC/USDT')  # Default symbol if not provided
        bot_reference = config.get('bot_ref')
        
        # Call BaseStrategy constructor with proper parameters (2025 compliant)
        super().__init__(
            name="fast_start",
            exchange=exchange,
            symbol=symbol,
            stop_loss_pct=config.get('fast_start_config', {}).get('stop_loss', 2.0) / 100,  # Convert to decimal
            take_profit_pct=config.get('fast_start_config', {}).get('profit_target', 1.5) / 100,  # Convert to decimal
            order_size_usdt=config.get('position_size_usdt', 2.0),
            bot_reference=bot_reference
        )
        
        # Fast start specific parameters
        self.profit_target = config.get('fast_start_config', {}).get('profit_target', 1.5)
        self.stop_loss = config.get('fast_start_config', {}).get('stop_loss', 2.0)
        # NEURAL OPTIMIZATION: Reduced confidence threshold from 0.6 to 0.35 (Neural insight: 0% success rate fix)
        self.min_confidence = config.get('fast_start_config', {}).get('min_confidence', 0.35)
        
        # Store balance manager reference from config
        self.balance_manager = config.get('balance_manager')
        
        # Quick execution settings
        self.max_analysis_time = 5  # Max 5 seconds for analysis
        self.priority_pairs = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOGE/USDT']
        
        logger.info(f"[FAST_START] Strategy initialized with {self.profit_target}% target")
    
    async def analyze(self, symbol: str, timeframe: str = '1m') -> Dict[str, Any]:
        """Fast analysis for immediate trading decisions"""
        start_time = time.time()
        
        try:
            # Get basic market data
            ticker = await self.exchange.fetch_ticker(symbol) if self.exchange else {}
            
            if not ticker:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'No ticker data'}
            
            current_price = ticker.get('last', 0)
            if current_price <= 0:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'Invalid price'}
            
            # Quick momentum check
            price_change_24h = ticker.get('percentage', 0)
            volume = ticker.get('quoteVolume', 0)
            
            # NEURAL OPTIMIZATION: Enhanced signal generation for better accuracy
            confidence = 0.4  # Start with higher base confidence
            action = 'HOLD'
            reason = 'Neutral market'
            
            # Enhanced bullish signals (Neural insight: better signal detection)
            if price_change_24h > 0.3:  # Lower threshold for positive momentum (was 0.5)
                confidence += 0.25  # Higher confidence boost (was 0.2)
                action = 'BUY'
                reason = 'Positive momentum detected'
            
            # Volume confirmation (Neural optimization: lower volume threshold)
            if volume > 500000:  # Reduced from 1M for better coverage
                confidence += 0.15  # Higher volume boost (was 0.1)
            
            # Priority pair bonus (Neural enhancement)
            if symbol in self.priority_pairs:
                confidence += 0.15  # Increased from 0.1
                reason += ' (priority pair)'
            
            # Enhanced sell signal (Neural insight: better sell detection)
            if price_change_24h < -0.5:  # More sensitive threshold (was -1.0)
                action = 'SELL'
                confidence = max(confidence, 0.55)  # Reduced from 0.6 to be more accessible
                reason = 'Decline detected'
            
            # Check execution time
            execution_time = time.time() - start_time
            if execution_time > self.max_analysis_time:
                logger.warning(f"[FAST_START] Analysis took {execution_time:.2f}s for {symbol}")
            
            return {
                'action': action,
                'confidence': min(confidence, 1.0),
                'reason': reason,
                'price': current_price,
                'execution_time': execution_time,
                'metadata': {
                    'price_change_24h': price_change_24h,
                    'volume': volume,
                    'is_priority': symbol in self.priority_pairs
                }
            }
            
        except Exception as e:
            logger.error(f"[FAST_START] Error analyzing {symbol}: {e}")
            return {'action': 'HOLD', 'confidence': 0, 'reason': f'Analysis error: {e}'}
    
    async def should_buy(self, symbol: str, analysis: Dict[str, Any]) -> bool:
        """Quick buy decision"""
        try:
            if analysis.get('action') != 'BUY':
                return False
            
            confidence = analysis.get('confidence', 0)
            if confidence < self.min_confidence:
                return False
            
            # Check available balance quickly
            if self.balance_manager:
                usdt_balance = await self.balance_manager.get_balance_for_asset('USDT')
                if usdt_balance < 2.0:  # Minimum trade size
                    return False
            
            logger.info(f"[FAST_START] Buy signal for {symbol} (confidence: {confidence:.3f})")
            return True
            
        except Exception as e:
            logger.error(f"[FAST_START] Error in buy decision for {symbol}: {e}")
            return False
    
    async def should_sell(self, symbol: str, analysis: Dict[str, Any]) -> bool:
        """Quick sell decision"""
        try:
            if analysis.get('action') != 'SELL':
                return False
            
            confidence = analysis.get('confidence', 0)
            if confidence < self.min_confidence:
                return False
            
            # Check if we have position
            if self.balance_manager:
                asset = symbol.split('/')[0]
                balance = await self.balance_manager.get_balance_for_asset(asset)
                if balance <= 0:
                    return False
            
            logger.info(f"[FAST_START] Sell signal for {symbol} (confidence: {confidence:.3f})")
            return True
            
        except Exception as e:
            logger.error(f"[FAST_START] Error in sell decision for {symbol}: {e}")
            return False
    
    async def generate_signals(self, market_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Generate trading signals based on market data.
        Required implementation for BaseStrategy abstract method.
        """
        try:
            # If market_data is a list, use the latest data
            if isinstance(market_data, list):
                if not market_data:
                    return {'action': 'HOLD', 'confidence': 0, 'reason': 'No market data'}
                data = market_data[-1]  # Use most recent data
            else:
                data = market_data
            
            # Extract relevant data
            symbol = data.get('symbol', '')
            current_price = float(data.get('close', 0))
            volume = float(data.get('volume', 0))
            
            if current_price <= 0:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'Invalid price data'}
            
            # Quick momentum analysis
            if len(market_data) > 5 and isinstance(market_data, list):
                # Calculate simple momentum
                prices = [float(d.get('close', 0)) for d in market_data[-5:]]
                momentum = (prices[-1] - prices[0]) / prices[0] * 100 if prices[0] > 0 else 0
                
                # Generate signal based on momentum
                if momentum > 1.0:  # 1% positive momentum
                    return {
                        'action': 'BUY',
                        'confidence': min(0.8, 0.6 + momentum * 0.1),
                        'reason': f'Positive momentum: {momentum:.2f}%',
                        'price': current_price,
                        'volume': volume
                    }
                elif momentum < -1.0:  # 1% negative momentum
                    return {
                        'action': 'SELL',
                        'confidence': min(0.8, 0.6 + abs(momentum) * 0.1),
                        'reason': f'Negative momentum: {momentum:.2f}%',
                        'price': current_price,
                        'volume': volume
                    }
            
            # Default to HOLD
            return {
                'action': 'HOLD',
                'confidence': 0.5,
                'reason': 'Insufficient momentum',
                'price': current_price,
                'volume': volume
            }
            
        except Exception as e:
            logger.error(f"[FAST_START] Error generating signals: {e}")
            return {'action': 'HOLD', 'confidence': 0, 'reason': f'Error: {str(e)}'}
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        return {
            'name': 'FastStartStrategy',
            'version': '1.0.0',
            'type': 'momentum',
            'timeframe': '1m',
            'profit_target': self.profit_target,
            'stop_loss': self.stop_loss,
            'min_confidence': self.min_confidence,
            'priority_pairs': self.priority_pairs,
            'max_analysis_time': self.max_analysis_time
        }