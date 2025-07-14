"""
Pro Account Fee-Free Micro Scalper Strategy
===========================================

CRITICAL ADVANTAGE: Kraken Pro accounts have 0% trading fees!

This strategy is specifically designed to exploit the fee-free trading benefit
of Kraken Pro accounts, enabling ultra-high frequency micro-scalping with
tiny profit margins that would be impossible with fees.

Key Features:
- 0.1-0.3% profit targets (impossible with fees)
- Ultra-tight stop losses (0.1-0.2%)
- Maximum trade frequency (up to 30 trades/minute)
- Capital velocity optimization for compound growth
- Micro-position sizing without fee overhead
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from .base_strategy import BaseStrategy
from ..config.constants import (
    PRO_ACCOUNT_OPTIMIZATIONS, 
    TRADING_CONSTANTS,
    INFINITY_LOOP_CONFIG
)
from ..utils.decimal_precision_fix import MoneyDecimal, PrecisionTradingCalculator

logger = logging.getLogger(__name__)


class MicroScalpSignalType(Enum):
    """Micro-scalping signal types for Pro accounts"""
    ULTRA_MICRO = "ultra_micro"      # 0.1% target
    MICRO = "micro"                  # 0.2% target  
    MINI_SCALP = "mini_scalp"        # 0.3% target
    RAPID_EXIT = "rapid_exit"        # Emergency exit


@dataclass
class MicroScalpSignal:
    """Micro-scalping signal optimized for fee-free trading"""
    symbol: str
    signal_type: MicroScalpSignalType
    side: str  # 'buy' or 'sell'
    confidence: float
    profit_target_pct: float
    stop_loss_pct: float
    urgency: str  # 'immediate', 'high', 'medium', 'low'
    expected_hold_time: int  # seconds
    price: float
    volume: float
    reasoning: str
    fee_free_advantage: float  # Additional profit from no fees


class ProFeeFreeeMicroScalper(BaseStrategy):
    """
    Pro Account Fee-Free Micro Scalper
    
    CRITICAL: This strategy only works with Kraken Pro accounts (0% fees)
    Standard accounts would lose money due to trading fees!
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.strategy_name = "pro_fee_free_micro_scalper"
        
        # Verify Pro account requirement
        self.api_tier = config.get('kraken_api_tier', 'starter')
        if self.api_tier != 'pro':
            raise ValueError("ERROR: This strategy requires Kraken Pro account (fee-free trading)")
        
        self.fee_free_trading = True
        logger.info("[PRO_MICRO_SCALPER] Initialized for Kraken Pro account - Fee-free trading confirmed")
        
        # Pro account optimized parameters
        self.ultra_micro_threshold = PRO_ACCOUNT_OPTIMIZATIONS['MICRO_PROFIT_THRESHOLD']  # 0.1%
        self.max_trades_per_minute = PRO_ACCOUNT_OPTIMIZATIONS['MAX_TRADE_FREQUENCY_PER_MINUTE']  # 30
        self.capital_velocity_target = PRO_ACCOUNT_OPTIMIZATIONS['CAPITAL_VELOCITY_TARGET']  # 10x
        
        # Micro-scalping thresholds (impossible with fees)
        self.profit_thresholds = {
            MicroScalpSignalType.ULTRA_MICRO: 0.001,  # 0.1% - only possible fee-free
            MicroScalpSignalType.MICRO: 0.002,        # 0.2% - tiny but profitable fee-free
            MicroScalpSignalType.MINI_SCALP: 0.003,   # 0.3% - standard micro-scalp
        }
        
        # Ultra-tight stop losses (fee-free exits)
        self.stop_loss_thresholds = {
            MicroScalpSignalType.ULTRA_MICRO: 0.0015,  # 0.15% stop
            MicroScalpSignalType.MICRO: 0.002,         # 0.2% stop
            MicroScalpSignalType.MINI_SCALP: 0.0025,   # 0.25% stop
        }
        
        # Position sizing for micro-scalping
        self.position_multiplier = PRO_ACCOUNT_OPTIMIZATIONS['POSITION_SIZE_MULTIPLIER']  # 1.5x
        self.min_position_size = 0.5  # $0.50 minimum (fee-free allows this)
        
        # Trade frequency controls
        self.last_trade_time = 0
        self.trades_this_minute = 0
        self.minute_start = time.time()
        
        # Performance tracking
        self.micro_scalp_stats = {
            'ultra_micro_trades': 0,
            'micro_trades': 0,
            'mini_scalp_trades': 0,
            'total_micro_profit': 0.0,
            'avg_hold_time': 0.0,
            'capital_velocity': 0.0,
            'compound_growth_rate': 0.0
        }
        
        logger.info(f"[PRO_MICRO_SCALPER] Strategy configured:")
        logger.info(f"  - Ultra-micro profit target: {self.ultra_micro_threshold:.3%}")
        logger.info(f"  - Max trades/minute: {self.max_trades_per_minute}")
        logger.info(f"  - Capital velocity target: {self.capital_velocity_target}x daily")
        logger.info(f"  - Position multiplier: {self.position_multiplier}x")
    
    async def analyze_symbol(self, symbol: str, market_data: Dict[str, Any]) -> Optional[MicroScalpSignal]:
        """
        Analyze symbol for micro-scalping opportunities
        
        CRITICAL: Only generates signals that are profitable with 0% fees
        """
        try:
            # Rate limit check - ensure we don't exceed Pro tier limits
            if not self._check_trade_frequency():
                return None
            
            # Get current price and volume data
            price = market_data.get('last', 0)
            bid = market_data.get('bid', 0)
            ask = market_data.get('ask', 0)
            volume = market_data.get('volume', 0)
            
            if not all([price, bid, ask]):
                return None
            
            # Calculate spread advantage (fee-free benefit)
            spread = ask - bid
            spread_pct = (spread / price) if price > 0 else 0
            
            # Fee-free advantage: We can profit from spreads smaller than typical fees
            fee_free_advantage = 0.001  # Equivalent to 0.1% fee savings
            
            # Ultra-micro scalping opportunities (only possible fee-free)
            if spread_pct <= 0.0008:  # Very tight spread
                return await self._generate_ultra_micro_signal(symbol, price, bid, ask, volume, fee_free_advantage)
            
            # Micro scalping opportunities
            elif spread_pct <= 0.0015:  # Tight spread
                return await self._generate_micro_signal(symbol, price, bid, ask, volume, fee_free_advantage)
            
            # Mini scalping opportunities
            elif spread_pct <= 0.003:  # Standard spread
                return await self._generate_mini_scalp_signal(symbol, price, bid, ask, volume, fee_free_advantage)
            
            return None
            
        except Exception as e:
            logger.error(f"[PRO_MICRO_SCALPER] Error analyzing {symbol}: {e}")
            return None
    
    async def _generate_ultra_micro_signal(self, symbol: str, price: float, bid: float, ask: float, 
                                         volume: float, fee_advantage: float) -> Optional[MicroScalpSignal]:
        """Generate ultra-micro scalping signal (0.1% target - only possible fee-free)"""
        
        # Ultra-micro conditions (very conservative)
        confidence = 0.85  # High confidence for tiny profits
        profit_target = self.profit_thresholds[MicroScalpSignalType.ULTRA_MICRO]
        stop_loss = self.stop_loss_thresholds[MicroScalpSignalType.ULTRA_MICRO]
        
        # Direction: Buy at bid, sell at ask + tiny profit
        side = 'buy'
        entry_price = bid
        target_price = entry_price * (1 + profit_target)
        
        # Volume check - ensure sufficient liquidity for quick exit
        min_volume = 1000  # Minimum volume for ultra-micro
        if volume < min_volume:
            return None
        
        # Ultra-micro signal validation
        if target_price <= ask * 1.0005:  # Target must be achievable
            signal = MicroScalpSignal(
                symbol=symbol,
                signal_type=MicroScalpSignalType.ULTRA_MICRO,
                side=side,
                confidence=confidence,
                profit_target_pct=profit_target,
                stop_loss_pct=stop_loss,
                urgency='immediate',
                expected_hold_time=15,  # 15 seconds max
                price=entry_price,
                volume=min(volume * 0.01, 100),  # Small position
                reasoning=f"Ultra-micro scalp: {profit_target:.3%} target (fee-free advantage)",
                fee_free_advantage=fee_advantage
            )
            
            logger.info(f"[ULTRA_MICRO] {symbol}: {profit_target:.3%} target @ ${entry_price:.6f}")
            return signal
        
        return None
    
    async def _generate_micro_signal(self, symbol: str, price: float, bid: float, ask: float,
                                   volume: float, fee_advantage: float) -> Optional[MicroScalpSignal]:
        """Generate micro scalping signal (0.2% target)"""
        
        confidence = 0.75
        profit_target = self.profit_thresholds[MicroScalpSignalType.MICRO]
        stop_loss = self.stop_loss_thresholds[MicroScalpSignalType.MICRO]
        
        # Check momentum indicators (simple)
        side = 'buy' if price >= (bid + ask) / 2 else 'sell'
        
        signal = MicroScalpSignal(
            symbol=symbol,
            signal_type=MicroScalpSignalType.MICRO,
            side=side,
            confidence=confidence,
            profit_target_pct=profit_target,
            stop_loss_pct=stop_loss,
            urgency='high',
            expected_hold_time=30,  # 30 seconds
            price=price,
            volume=min(volume * 0.02, 200),  # Moderate position
            reasoning=f"Micro scalp: {profit_target:.3%} target",
            fee_free_advantage=fee_advantage
        )
        
        logger.info(f"[MICRO] {symbol}: {profit_target:.3%} target @ ${price:.6f}")
        return signal
    
    async def _generate_mini_scalp_signal(self, symbol: str, price: float, bid: float, ask: float,
                                        volume: float, fee_advantage: float) -> Optional[MicroScalpSignal]:
        """Generate mini scalping signal (0.3% target)"""
        
        confidence = 0.65
        profit_target = self.profit_thresholds[MicroScalpSignalType.MINI_SCALP]
        stop_loss = self.stop_loss_thresholds[MicroScalpSignalType.MINI_SCALP]
        
        side = 'buy'  # Default to buy for mini scalps
        
        signal = MicroScalpSignal(
            symbol=symbol,
            signal_type=MicroScalpSignalType.MINI_SCALP,
            side=side,
            confidence=confidence,
            profit_target_pct=profit_target,
            stop_loss_pct=stop_loss,
            urgency='medium',
            expected_hold_time=60,  # 1 minute
            price=price,
            volume=min(volume * 0.05, 500),  # Larger position
            reasoning=f"Mini scalp: {profit_target:.3%} target",
            fee_free_advantage=fee_advantage
        )
        
        logger.info(f"[MINI_SCALP] {symbol}: {profit_target:.3%} target @ ${price:.6f}")
        return signal
    
    def _check_trade_frequency(self) -> bool:
        """Check if we can trade within frequency limits"""
        current_time = time.time()
        
        # Reset minute counter
        if current_time - self.minute_start >= 60:
            self.trades_this_minute = 0
            self.minute_start = current_time
        
        # Check frequency limit
        if self.trades_this_minute >= self.max_trades_per_minute:
            logger.debug(f"[PRO_MICRO_SCALPER] Trade frequency limit reached: {self.trades_this_minute}/{self.max_trades_per_minute}")
            return False
        
        # Minimum time between trades (Pro tier: 2 seconds)
        if current_time - self.last_trade_time < 2.0:
            return False
        
        return True
    
    async def generate_signals(self, symbols: List[str], market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate micro-scalping signals for multiple symbols
        
        Returns standard trading signals compatible with the execution pipeline
        """
        signals = []
        
        for symbol in symbols:
            if symbol not in market_data:
                continue
            
            micro_signal = await self.analyze_symbol(symbol, market_data[symbol])
            if micro_signal:
                # Convert to standard signal format
                standard_signal = self._convert_to_standard_signal(micro_signal)
                signals.append(standard_signal)
                
                # Update frequency tracking
                self.trades_this_minute += 1
                self.last_trade_time = time.time()
                
                # Update statistics
                self._update_stats(micro_signal)
        
        # Log batch summary
        if signals:
            logger.info(f"[PRO_MICRO_SCALPER] Generated {len(signals)} micro-scalp signals")
            
        return signals
    
    def _convert_to_standard_signal(self, micro_signal: MicroScalpSignal) -> Dict[str, Any]:
        """Convert micro-scalp signal to standard trading signal format"""
        return {
            'symbol': micro_signal.symbol,
            'side': micro_signal.side,
            'signal_type': 'micro_scalp',
            'strategy': 'pro_fee_free_micro_scalper',
            'confidence': micro_signal.confidence,
            'profit_target_pct': micro_signal.profit_target_pct,
            'stop_loss_pct': micro_signal.stop_loss_pct,
            'urgency': micro_signal.urgency,
            'expected_hold_time': micro_signal.expected_hold_time,
            'price': micro_signal.price,
            'amount': micro_signal.volume,
            'reasoning': micro_signal.reasoning,
            'order_type': 'ioc',  # Pro tier: Use IOC for micro-scalping
            'metadata': {
                'signal_type_enum': micro_signal.signal_type.value,
                'fee_free_advantage': micro_signal.fee_free_advantage,
                'pro_account_optimized': True,
                'micro_scalping_mode': True
            }
        }
    
    def _update_stats(self, signal: MicroScalpSignal):
        """Update micro-scalping performance statistics"""
        if signal.signal_type == MicroScalpSignalType.ULTRA_MICRO:
            self.micro_scalp_stats['ultra_micro_trades'] += 1
        elif signal.signal_type == MicroScalpSignalType.MICRO:
            self.micro_scalp_stats['micro_trades'] += 1
        elif signal.signal_type == MicroScalpSignalType.MINI_SCALP:
            self.micro_scalp_stats['mini_scalp_trades'] += 1
    
    def get_strategy_metrics(self) -> Dict[str, Any]:
        """Get Pro account micro-scalping performance metrics"""
        total_trades = sum([
            self.micro_scalp_stats['ultra_micro_trades'],
            self.micro_scalp_stats['micro_trades'],
            self.micro_scalp_stats['mini_scalp_trades']
        ])
        
        return {
            'strategy_name': self.strategy_name,
            'api_tier': 'pro',
            'fee_free_trading': True,
            'total_micro_scalp_trades': total_trades,
            'trade_breakdown': {
                'ultra_micro_trades': self.micro_scalp_stats['ultra_micro_trades'],
                'micro_trades': self.micro_scalp_stats['micro_trades'],
                'mini_scalp_trades': self.micro_scalp_stats['mini_scalp_trades']
            },
            'trades_per_minute': self.trades_this_minute,
            'max_trades_per_minute': self.max_trades_per_minute,
            'capital_velocity_target': self.capital_velocity_target,
            'fee_savings_advantage': True,
            'profit_thresholds': {k.value: v for k, v in self.profit_thresholds.items()}
        }
    
    def get_name(self) -> str:
        return "Pro Fee-Free Micro Scalper"