"""
Profit Harvester - Minimal Implementation for Bot Compatibility

This module provides a basic ProfitHarvester class to maintain
bot functionality while keeping the system lightweight.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, List
import json
from pathlib import Path
from datetime import datetime
import time
from decimal import Decimal, ROUND_HALF_UP
from src.utils.decimal_precision_fix import MoneyDecimal, PrecisionTradingCalculator



class ProfitHarvester:
    """Enhanced profit harvester with automatic reinvestment cycle."""
    
    def __init__(self, bot: Any = None, exchange: Any = None, min_profit_pct: float = 1.0,
                 portfolio_tracker: Any = None, config: Dict = None, 
                 trade_executor: Any = None, bot_ref: Any = None):
        """Initialize the profit harvester with flexible parameter support.
        
        Args:
            bot: Trading bot instance (legacy parameter)
            exchange: Exchange instance (legacy parameter)
            min_profit_pct: Minimum profit percentage to harvest
            portfolio_tracker: Portfolio tracker instance (new parameter)
            config: Configuration dictionary (new parameter)
            trade_executor: Trade executor instance (new parameter)
            bot_ref: Bot reference (new parameter)
        """
        # Handle both parameter formats for compatibility
        if portfolio_tracker and config:
            # New format from bot initialization
            self.bot = bot_ref
            self.portfolio_tracker = portfolio_tracker
            self.trade_executor = trade_executor
            self.config = config
            self.exchange = getattr(bot_ref, 'exchange', None) if bot_ref else None
            self.min_profit_pct = config.get('min_profit_pct', min_profit_pct)
        else:
            # Legacy format
            self.bot = bot
            self.exchange = exchange
            self.portfolio_tracker = None
            self.trade_executor = None
            self.config = {}
            self.min_profit_pct = min_profit_pct
            
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Position tracking with entry prices
        self.positions = {}
        
        # Reinvestment tracking
        self.last_balance_check = 0
        self.profit_proceeds = 0.0
        self.total_profits_harvested = 0.0
        self.reinvestment_enabled = config.get('auto_reinvest', True) if config else True
        self.reinvestment_percentage = config.get('reinvestment_pct', 90) if config else 90  # Reinvest 90% of profits
        
        # Emergency rebalance tracking
        self._last_rebalance_time = 0.0
        self._rebalance_cooldown = 3600  # 1 hour cooldown between emergency rebalances
        
        # Progressive profit-taking settings
        self.profit_levels = config.get('profit_levels', [
            {'threshold': 1.0, 'sell_pct': 100, 'confidence': 0.85},  # 1% profit - sell full position for $2 trades
            {'threshold': 1.5, 'sell_pct': 100, 'confidence': 0.90},  # 1.5% profit - sell full position
            {'threshold': 2.0, 'sell_pct': 100, 'confidence': 0.95}   # 2% profit - sell full position
        ]) if config else [
            {'threshold': 1.0, 'sell_pct': 100, 'confidence': 0.85},
            {'threshold': 1.5, 'sell_pct': 100, 'confidence': 0.90},
            {'threshold': 2.0, 'sell_pct': 100, 'confidence': 0.95}
        ]
        
        # Traditional settings for fallback - updated for $2 positions
        self.target_profit_pct = config.get('target_profit_pct', 1.5) if config else 1.5  # 1.5% target
        self.stop_loss_pct = config.get('stop_loss_pct', 2.0) if config else 2.0  # 2.0% stop loss
        self.progressive_selling = config.get('progressive_selling', True) if config else True
        
        self.logger.info(f"[HARVESTER] Enhanced ProfitHarvester initialized:")
        self.logger.info(f"  - Progressive Selling: {self.progressive_selling}")
        if self.progressive_selling:
            for level in self.profit_levels:
                self.logger.info(f"    * {level['sell_pct']}% at {level['threshold']}% profit (confidence: {level['confidence']})")
        else:
            self.logger.info(f"  - Target Profit: {self.target_profit_pct}%")
        self.logger.info(f"  - Stop Loss: {self.stop_loss_pct}%") 
        self.logger.info(f"  - Auto Reinvestment: {self.reinvestment_enabled} ({self.reinvestment_percentage}%)")
        self.logger.info(f"  - Minimum Threshold: {self.min_profit_pct}%")
        
        # WebSocket manager for real-time prices
        self.websocket_manager = None
        if self.bot and hasattr(self.bot, 'websocket_manager'):
            self.websocket_manager = self.bot.websocket_manager
            self.logger.info("  - Using WebSocket V2 for real-time prices")
    
    @property
    def is_harvesting(self) -> bool:
        """Check if the harvester is currently running."""
        return self.running
    
    async def _get_realtime_price(self, symbol: str) -> Optional[float]:
        """Get real-time price from WebSocket V2 only"""
        try:
            if self.websocket_manager:
                ticker = await self.websocket_manager.get_ticker(symbol)
                if ticker and 'last' in ticker:
                    return float(ticker['last'])
                    
            self.logger.debug(f"[HARVESTER] No WebSocket price available for {symbol}")
            return None
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error getting real-time price for {symbol}: {e}")
            return None
    
    def start_harvesting_loop(self) -> None:
        """Start the harvesting process."""
        self.running = True
        self.logger.info("[HARVESTER] Profit harvesting started")
    
    async def start(self) -> None:
        """Start the harvester - async version."""
        self.start_harvesting_loop()
        asyncio.create_task(self.harvest_profits())
    
    def stop_harvesting_loop(self) -> None:
        """Stop the harvesting process."""
        self.running = False
        self.logger.info("[HARVESTER] Profit harvesting stopped")
    
    async def harvest_profits(self) -> None:
        """Main harvesting loop - minimal implementation."""
        while self.running:
            try:
                # Check positions for profit
                await self.check_positions()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"[HARVESTER] Error in harvest loop: {e}")
                break
    
    def get_profit_metrics(self) -> Dict[str, Any]:
        """Get profit harvesting metrics."""
        return {
            "total_positions": 0,
            "profitable_positions": 0,
            "total_profit": 0.0,
            "harvesting_enabled": self.running,
            "min_profit_pct": self.min_profit_pct,
            "positions_monitored": [],
            "last_harvest_time": None,
            "harvest_count_today": 0,
            "total_harvest_profit": 0.0
        }
    
    async def track_position(self, symbol: str, entry_price: float, amount: float, 
                            trade_id: str = None) -> Dict[str, Any]:
        """
        Track a new position for profit harvesting.
        
        Args:
            symbol: Trading pair symbol
            entry_price: Entry price of the position
            amount: Amount of the position
            trade_id: Optional trade ID for tracking
            
        Returns:
            Dict with tracking status
        """
        try:
            self.logger.info(f"[HARVESTER] Tracking position: {symbol} - "
                           f"Entry: {entry_price}, Amount: {amount}")
            
            # Store position with entry price for profit tracking
            position_data = {
                'symbol': symbol,
                'entry_price': entry_price,
                'amount': amount,
                'original_amount': amount,  # Track original size for progressive selling
                'trade_id': trade_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'open',
                'partial_sells': [],  # Track progressive sells
                'profit_levels_hit': []  # Track which profit levels have been triggered
            }
            
            # Store in positions dictionary
            self.positions[symbol] = position_data
            
            # Update portfolio tracker as PRIMARY source of truth
            if hasattr(self, 'bot') and self.bot and hasattr(self.bot, 'portfolio_tracker'):
                try:
                    self.bot.portfolio_tracker.update_position(symbol, amount, entry_price)
                    self.logger.info(f"[HARVESTER] [OK] Portfolio tracker updated (PRIMARY source): {symbol}")
                except Exception as e:
                    self.logger.warning(f"[HARVESTER] Failed to update portfolio tracker: {e}")
            else:
                self.logger.warning(f"[HARVESTER] No portfolio tracker available - position tracking may be incomplete")
            
            # Save positions to file for persistence
            try:
                positions_file = Path("trading_data/positions_with_entries.json")
                positions_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Load existing positions
                existing_positions = {}
                if positions_file.exists():
                    with open(positions_file, 'r') as f:
                        existing_positions = json.load(f)
                
                # Update with new position
                existing_positions[symbol] = position_data
                
                # Save back
                with open(positions_file, 'w') as f:
                    json.dump(existing_positions, f, indent=2)
                    
                self.logger.info(f"[HARVESTER] Position saved to file for {symbol}")
            except Exception as e:
                self.logger.error(f"[HARVESTER] Error saving position to file: {e}")
            
            return {
                "success": True,
                "symbol": symbol,
                "entry_price": entry_price,
                "amount": amount,
                "trade_id": trade_id,
                "message": "Position tracked and saved successfully"
            }
            
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error tracking position {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to track position"
            }
    
    async def check_positions(self) -> List[Dict[str, Any]]:
        """
        Check all positions for profit opportunities with micro-profit optimization.
        
        Returns:
            List of sell signals for profitable positions
        """
        sell_signals = []
        check_start_time = time.time()
        
        try:
            # PRIORITY 1: Use portfolio tracker as primary source of truth
            if self.portfolio_tracker or (hasattr(self, 'bot') and self.bot and hasattr(self.bot, 'portfolio_tracker')):
                # Get portfolio tracker instance
                tracker = self.portfolio_tracker or self.bot.portfolio_tracker
                
                # First, update current prices for all positions
                try:
                    if self.exchange or (self.bot and hasattr(self.bot, 'exchange')):
                        exchange = self.exchange or self.bot.exchange
                        
                        # Batch fetch prices for efficiency (micro-profit optimization)
                        symbols_to_update = [
                            symbol for symbol in list(tracker.positions.keys())
                            if tracker.positions[symbol].get('amount', 0) > 0
                        ]
                        
                        if symbols_to_update:
                            # Get real-time prices from WebSocket V2
                            prices = {}
                            for symbol in symbols_to_update:
                                price = await self._get_realtime_price(symbol)
                                if price:
                                    prices[symbol] = price
                                else:
                                    self.logger.warning(f"[HARVESTER] No real-time price for {symbol}, skipping")
                            
                            # Update tracker with real-time prices
                            for symbol, price in prices.items():
                                tracker.update_price(symbol, price)
                                self.logger.debug(f"[HARVESTER] Updated {symbol} price to ${price:.6f}")
                except Exception as e:
                    self.logger.error(f"[HARVESTER] Error updating prices: {e}")
                
                positions = tracker.get_open_positions()
                
                for position in positions:
                    symbol = position.get('symbol')
                    if position.get('amount', 0) <= 0:
                        continue
                        
                    entry_price = position.get('entry_price', 0)
                    current_price = position.get('current_price', 0)
                    amount = position.get('amount', 0)
                    
                    # If no entry price but we have current price, log warning and use emergency logic
                    if entry_price == 0 and current_price > 0 and amount > 0:
                        self.logger.warning(f"[HARVESTER] {symbol}: No entry price tracked, considering emergency rebalance")
                        # Calculate position value
                        position_value = amount * current_price
                        if position_value >= 10.0:  # Only consider positions worth $10+
                            # Create emergency sell signal for position without entry price
                            emergency_signal = {
                                'symbol': symbol,
                                'side': 'sell',
                                'confidence': 0.75,
                                'source': 'profit_harvester_no_entry',
                                'reason': f'No entry price - emergency rebalance (${position_value:.2f})',
                                'metadata': {
                                    'amount': amount,
                                    'current_price': current_price,
                                    'value_usd': position_value,
                                    'no_entry_price': True
                                }
                            }
                            sell_signals.append(emergency_signal)
                            self.logger.info(f"[HARVESTER] Added emergency sell for {symbol} worth ${position_value:.2f}")
                    elif entry_price > 0 and current_price > 0:
                        profit_pct = PrecisionTradingCalculator.calculate_percentage_gain(entry_price, current_price)
                        
                        # Progressive profit-taking logic
                        if self.progressive_selling:
                            sell_signals.extend(self._check_progressive_profit_levels(position, profit_pct))
                        else:
                            # Traditional profit-taking logic
                            profit_threshold = max(self.target_profit_pct, self.min_profit_pct)
                            
                            # Check for both profit targets and stop losses
                            should_sell = False
                            sell_reason = ""
                            sell_confidence = 0.5
                            
                            # Ultra-micro-profit optimization: Quick sell for 0.1-0.5% profits
                            if 0.1 <= profit_pct <= 0.5:
                                should_sell = True
                                sell_reason = f"Ultra-micro-profit target: {profit_pct:.3f}%"
                                sell_confidence = 0.95  # Very high confidence for ultra-micro-profits
                            # Fast micro-profit optimization: Quick sell for 0.5-2.0% profits  
                            elif 0.5 <= profit_pct <= 2.0:
                                should_sell = True
                                sell_reason = f"Fast micro-profit target: {profit_pct:.3f}%"
                                sell_confidence = 0.9  # High confidence for micro-profits
                            
                            if profit_pct >= profit_threshold:
                                should_sell = True
                                sell_reason = f'Profit target reached: {profit_pct:.2f}%'
                                sell_confidence = min(0.9, 0.5 + profit_pct / 10)  # Higher confidence with more profit
                            elif profit_pct <= -self.stop_loss_pct:
                                should_sell = True
                                sell_reason = f'Stop loss triggered: {profit_pct:.2f}%'
                                sell_confidence = 0.8  # High confidence for stop loss
                            
                            if should_sell:
                                self.logger.info(
                                    f"[HARVESTER] {symbol}: Sell trigger! "
                                    f"P&L: {profit_pct:.2f}% (${entry_price:.6f} -> ${current_price:.6f}) - {sell_reason}"
                                )
                                
                                # Create sell signal
                                sell_signal = {
                                    'symbol': symbol,
                                    'side': 'sell',
                                    'confidence': sell_confidence,
                                    'source': 'profit_harvester',
                                    'reason': sell_reason,
                                    'metadata': {
                                        'entry_price': entry_price,
                                        'current_price': current_price,
                                        'profit_pct': profit_pct,
                                        'amount': amount,
                                        'profit_usd': float(PrecisionTradingCalculator.calculate_profit(entry_price, current_price, amount)) if entry_price > 0 else 0
                                    }
                                }
                                
                                sell_signals.append(sell_signal)
                        
                        # Check stop loss for both progressive and traditional
                        if profit_pct <= -self.stop_loss_pct:
                            stop_loss_signal = {
                                'symbol': symbol,
                                'side': 'sell',
                                'confidence': 0.9,  # High confidence for stop loss
                                'source': 'profit_harvester_stop_loss',
                                'reason': f'Stop loss triggered: {profit_pct:.2f}%',
                                'metadata': {
                                    'entry_price': entry_price,
                                    'current_price': current_price,
                                    'profit_pct': profit_pct,
                                    'amount': amount,  # Sell entire position on stop loss
                                    'profit_usd': float(PrecisionTradingCalculator.calculate_profit(entry_price, current_price, amount)) if entry_price > 0 else 0,
                                    'sell_type': 'stop_loss'
                                }
                            }
                            
                            self.logger.warning(
                                f"[HARVESTER] {symbol}: [EMOJI] STOP LOSS triggered! "
                                f"Loss: {profit_pct:.2f}% - selling entire position"
                            )
                            
                            sell_signals.append(stop_loss_signal)
            
            # PRIORITY 2: Fallback to internal positions if no portfolio tracker
            elif self.positions:
                self.logger.info("[HARVESTER] Using fallback position tracking (portfolio tracker unavailable)")
                for symbol, pos_data in self.positions.items():
                    try:
                        # Get current price from WebSocket V2
                        current_price = await self._get_realtime_price(symbol)
                        if current_price:
                            entry_price = pos_data.get('entry_price', 0)
                            
                            if entry_price > 0 and current_price > 0:
                                profit_pct = PrecisionTradingCalculator.calculate_percentage_gain(entry_price, current_price)
                                
                                if profit_pct >= self.min_profit_pct:
                                    self.logger.info(
                                        f"[HARVESTER] {symbol}: Profit opportunity! "
                                        f"{profit_pct:.2f}% gain"
                                    )
                                    
                                    sell_signals.append({
                                        'symbol': symbol,
                                        'side': 'sell',
                                        'confidence': 0.7,
                                        'source': 'profit_harvester',
                                        'reason': f'Profit: {profit_pct:.2f}%'
                                    })
                    except Exception as e:
                        self.logger.debug(f"[HARVESTER] Error checking {symbol}: {e}")
            
            if sell_signals:
                self.logger.info(f"[HARVESTER] Generated {len(sell_signals)} sell signals")
            
            # Track execution time for micro-profit optimization
            check_time = (time.time() - check_start_time) * 1000  # ms
            if check_time < 100:  # Under 100ms target
                self.logger.debug(f"[HARVESTER] [EMOJI] Fast position check: {check_time:.1f}ms")
            else:
                self.logger.debug(f"[HARVESTER] Position check took {check_time:.1f}ms")
                
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error checking positions: {e}")
            
        return sell_signals
    
    async def emergency_rebalance(self, target_usdt_amount: float = 20.0, hours_without_trade: float = 1.0) -> List[Dict[str, Any]]:
        """
        Emergency rebalancing when positions don't have entry prices.
        This will generate sell signals for positions to free up capital.
        
        Args:
            target_usdt_amount: Target USDT amount to free up
            hours_without_trade: Hours without trades before triggering
            
        Returns:
            List of sell signals
        """
        sell_signals = []
        
        # Check cooldown period
        current_time = time.time()
        if self._last_rebalance_time and current_time - self._last_rebalance_time < self._rebalance_cooldown:
            time_remaining = self._rebalance_cooldown - (current_time - self._last_rebalance_time)
            self.logger.info(f"[HARVESTER] Emergency rebalance on cooldown for {time_remaining/60:.1f} more minutes")
            return []
        
        # Don't trigger immediately - need at least 1 hour without trades
        if hours_without_trade < 1.0:
            self.logger.debug(f"[HARVESTER] Not enough time without trades ({hours_without_trade:.1f}h < 1.0h)")
            return []
        
        try:
            self.logger.warning(f"[HARVESTER] EMERGENCY REBALANCE: Attempting to free ${target_usdt_amount:.2f}")
            
            # Get current portfolio state
            if hasattr(self, 'bot') and self.bot and hasattr(self.bot, 'balance_manager'):
                # First verify we actually have sufficient USDT before selling
                usdt_balance = await self.bot.balance_manager.get_balance_for_asset('USDT', force_refresh=True)
                if usdt_balance >= 5.0:  # Enough for 2 trades with buffer
                    self.logger.info(f"[HARVESTER] Sufficient USDT balance ${usdt_balance:.2f} - no emergency rebalance needed")
                    return []
                
                portfolio_analysis = await self.bot.balance_manager.analyze_portfolio_state('USDT')
                deployed_assets = portfolio_analysis.get('deployed_assets', [])
                
                # Sort by value to sell smallest positions first
                deployed_assets.sort(key=lambda x: x.get('value_usd', 0))
                
                freed_amount = 0.0
                
                for asset in deployed_assets:
                    if freed_amount >= target_usdt_amount:
                        break
                    
                    # Skip if too small
                    if asset.get('value_usd', 0) < 5.0:
                        continue
                    
                    symbol = f"{asset['asset']}/USDT"
                    amount = asset.get('amount', 0)
                    value_usd = asset.get('value_usd', 0)
                    
                    self.logger.info(f"[HARVESTER] Emergency sell: {symbol} - {amount} units (${value_usd:.2f})")
                    
                    sell_signal = {
                        'symbol': symbol,
                        'side': 'sell',
                        'confidence': 0.85,  # High confidence for emergency rebalance
                        'source': 'emergency_rebalance',
                        'reason': f'Emergency rebalance - freeing ${value_usd:.2f}',
                        'metadata': {
                            'amount': amount,
                            'value_usd': value_usd,
                            'emergency': True,
                            'no_entry_price': True
                        }
                    }
                    
                    sell_signals.append(sell_signal)
                    freed_amount += value_usd
                
                if sell_signals:
                    self.logger.warning(
                        f"[HARVESTER] Emergency rebalance generated {len(sell_signals)} sell signals "
                        f"to free ~${freed_amount:.2f}"
                    )
                    # Update rebalance timestamp
                    self._last_rebalance_time = current_time
                else:
                    self.logger.warning("[HARVESTER] No suitable positions found for emergency rebalance")
            
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error in emergency rebalance: {e}")
        
        return sell_signals
    
    async def scan_for_profitable_positions(self):
        """Scan all positions for profitable sell opportunities."""
        if not self.running:
            return []
        
        profitable_positions = []
        try:
            # First, load positions from file to ensure we have all tracked positions
            try:
                positions_file = Path("trading_data/positions_with_entries.json")
                if positions_file.exists():
                    with open(positions_file, 'r') as f:
                        saved_positions = json.load(f)
                        # Update our internal positions
                        for symbol, pos_data in saved_positions.items():
                            if symbol not in self.positions:
                                self.positions[symbol] = pos_data
            except Exception as e:
                self.logger.warning(f"[HARVESTER] Error loading saved positions: {e}")
            
            # Get current prices for all tracked positions
            for symbol, position_data in self.positions.items():
                if position_data.get('status') == 'open':
                    try:
                        # Get current price from WebSocket V2
                        current_price = await self._get_realtime_price(symbol)
                        if not current_price:
                            current_price = 0
                            self.logger.warning(f"[HARVESTER] No real-time price for {symbol}")
                        
                        entry_price = position_data.get('entry_price', 0)
                        amount = position_data.get('amount', 0)
                        
                        if entry_price > 0 and current_price > 0:
                            profit_pct = PrecisionTradingCalculator.calculate_percentage_gain(entry_price, current_price)
                            profit_usd = float(PrecisionTradingCalculator.calculate_profit(entry_price, current_price, amount))
                            
                            # Check if ANY profit (user wants micro profits)
                            if profit_usd > 0.01:  # Any profit above $0.01
                                position = {
                                    'symbol': symbol,
                                    'amount': amount,
                                    'entry_price': entry_price,
                                    'current_price': current_price,
                                    'profit_pct': profit_pct,
                                    'profit_usd': profit_usd
                                }
                                profitable_positions.append(position)
                                self.logger.info(f"[HARVESTER] {symbol}: ${profit_usd:.2f} profit ({profit_pct:.2f}%) - READY TO HARVEST!")
                    except Exception as e:
                        self.logger.debug(f"[HARVESTER] Error checking {symbol}: {e}")
            
            # Also check portfolio tracker positions
            if self.portfolio_tracker:
                positions = self.portfolio_tracker.get_open_positions()
                
                for position in positions:
                    symbol = position.get('symbol', '')
                    entry_price = position.get('entry_price', position.get('price', 0))
                    current_price = position.get('current_price', 0)
                    
                    if entry_price > 0 and current_price > 0:
                        profit_pct = PrecisionTradingCalculator.calculate_percentage_gain(entry_price, current_price)
                        
                        if profit_pct >= self.min_profit_pct * 100:
                            position['profit_pct'] = profit_pct
                            position['profit_usd'] = float(PrecisionTradingCalculator.calculate_profit(entry_price, current_price, position.get('amount', 0)))
                            profitable_positions.append(position)
                            self.logger.info(f"[HARVESTER] {symbol}: {profit_pct:.2f}% profit opportunity")
        
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error scanning positions: {e}")
        
        return profitable_positions
    
    async def check_positions(self) -> list:
        """
        Check all positions for profit harvesting opportunities.
        This method is called by the main bot loop.
        
        Returns:
            List of sell signals for profitable positions
        """
        sell_signals = []
        
        try:
            # Get profitable positions
            profitable_positions = await self.scan_for_profitable_positions()
            
            # Convert profitable positions to sell signals
            for position in profitable_positions:
                sell_signal = {
                    'symbol': position.get('symbol'),
                    'side': 'sell',
                    'amount': position.get('amount', 0),
                    'confidence': min(position.get('profit_pct', 0) / 10 + 0.7, 1.0),  # Scale confidence based on profit
                    'source': 'profit_harvester',
                    'metadata': {
                        'entry_price': position.get('entry_price'),
                        'current_price': position.get('current_price'),
                        'profit_pct': position.get('profit_pct'),
                        'profit_usd': position.get('profit_usd'),
                        'reason': f"Profit harvest: {position.get('profit_pct', 0):.2f}%"
                    }
                }
                sell_signals.append(sell_signal)
                
                self.logger.info(f"[HARVESTER] Generated sell signal for {position.get('symbol')} "
                               f"with {position.get('profit_pct', 0):.2f}% profit")
            
            return sell_signals
            
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error checking positions: {e}")
            return []
    
    def _check_progressive_profit_levels(self, position: Dict[str, Any], profit_pct: float) -> List[Dict[str, Any]]:
        """
        Check if position has hit any progressive profit levels and generate partial sell signals.
        
        Args:
            position: Position data from portfolio tracker
            profit_pct: Current profit percentage
            
        Returns:
            List of sell signals for triggered profit levels
        """
        sell_signals = []
        symbol = position.get('symbol')
        entry_price = position.get('entry_price', 0)
        current_price = position.get('current_price', 0)
        amount = position.get('amount', 0)
        
        if not symbol or entry_price <= 0 or current_price <= 0 or amount <= 0:
            return sell_signals
        
        # Get position data from internal tracking (for partial sells tracking)
        position_data = self.positions.get(symbol, {})
        profit_levels_hit = position_data.get('profit_levels_hit', [])
        original_amount = position_data.get('original_amount', amount)
        
        # Skip progressive profit taking for small positions ($10 or less)
        position_value = amount * current_price
        if position_value <= 10.0:
            # For small positions, use full position sell at profit targets
            if profit_pct >= 1.0:  # 1% minimum profit for small positions
                sell_signal = {
                    'symbol': symbol,
                    'side': 'sell',
                    'confidence': 0.85,
                    'source': 'profit_harvester_small_position',
                    'reason': f'Small position profit target: {profit_pct:.2f}%',
                    'metadata': {
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'profit_pct': profit_pct,
                        'amount': amount,  # Sell full amount
                        'profit_usd': amount * (current_price - entry_price),
                        'sell_type': 'full_position_small',
                        'position_value': position_value
                    }
                }
                sell_signals.append(sell_signal)
                self.logger.info(f"[HARVESTER] {symbol}: Small position (${position_value:.2f}) - selling full position at {profit_pct:.2f}% profit")
            return sell_signals
        
        # Check each profit level for larger positions
        for level in self.profit_levels:
            level_threshold = level['threshold']
            sell_percentage = level['sell_pct']
            confidence = level['confidence']
            
            # Check if this level should be triggered
            if profit_pct >= level_threshold and level_threshold not in profit_levels_hit:
                # Calculate partial sell amount
                partial_sell_amount = (original_amount * sell_percentage / 100)
                
                # Ensure we don't sell more than we have
                actual_sell_amount = min(partial_sell_amount, amount)
                
                if actual_sell_amount >= 0.01:  # Minimum viable sell amount
                    sell_signal = {
                        'symbol': symbol,
                        'side': 'sell',
                        'confidence': confidence,
                        'source': 'profit_harvester_progressive',
                        'reason': f'Progressive profit: {sell_percentage}% at {level_threshold}% profit level',
                        'metadata': {
                            'entry_price': entry_price,
                            'current_price': current_price,
                            'profit_pct': profit_pct,
                            'amount': actual_sell_amount,
                            'sell_percentage': sell_percentage,
                            'profit_level': level_threshold,
                            'profit_usd': float(PrecisionTradingCalculator.calculate_profit(entry_price, current_price, actual_sell_amount)) if entry_price > 0 else 0,
                            'sell_type': 'progressive_profit',
                            'remaining_amount': amount - actual_sell_amount
                        }
                    }
                    
                    sell_signals.append(sell_signal)
                    
                    # Mark this level as hit
                    profit_levels_hit.append(level_threshold)
                    
                    self.logger.info(
                        f"[HARVESTER] {symbol}: [UP] Progressive profit level {level_threshold}% hit! "
                        f"Selling {sell_percentage}% ({actual_sell_amount:.6f}) at {profit_pct:.2f}% profit"
                    )
        
        # Update position tracking
        if profit_levels_hit and symbol in self.positions:
            self.positions[symbol]['profit_levels_hit'] = profit_levels_hit
        
        return sell_signals
    
    async def handle_successful_sell(self, symbol: str, proceeds_usdt: float, profit_usdt: float) -> Dict[str, Any]:
        """
        Handle successful sell order completion and trigger reinvestment cycle.
        
        Args:
            symbol: Symbol that was sold
            proceeds_usdt: Total USDT received from sell
            profit_usdt: Pure profit amount in USDT
            
        Returns:
            Dict with reinvestment status
        """
        try:
            self.logger.info(f"[HARVESTER] [MONEY] Successful sell: {symbol} - Profit: ${profit_usdt:.2f}")
            
            # Update tracking
            self.total_profits_harvested += profit_usdt
            self.profit_proceeds += proceeds_usdt
            
            # Remove from position tracking
            if symbol in self.positions:
                del self.positions[symbol]
                self.logger.info(f"[HARVESTER] Removed {symbol} from position tracking")
            
            # Update portfolio tracker
            if hasattr(self, 'bot') and self.bot and hasattr(self.bot, 'portfolio_tracker'):
                try:
                    self.bot.portfolio_tracker.close_position(symbol, profit_usdt)
                except Exception as e:
                    self.logger.warning(f"[HARVESTER] Failed to update portfolio tracker: {e}")
            
            # Trigger balance refresh in balance manager  
            if hasattr(self, 'bot') and self.bot and hasattr(self.bot, 'balance_manager'):
                try:
                    # Force balance refresh to capture new USDT
                    await self.bot.balance_manager.get_balance(force_refresh=True)
                    self.logger.info(f"[HARVESTER] [OK] Balance refreshed after sell completion")
                except Exception as e:
                    self.logger.warning(f"[HARVESTER] Failed to refresh balance: {e}")
            
            # Trigger automatic reinvestment if enabled
            reinvestment_result = {'reinvestment_triggered': False}
            
            # For tier-1, reinvest any proceeds immediately to maintain capital deployment
            is_tier_1 = self.config.get('kraken_api_tier', 'starter') == 'starter'
            min_reinvest = 0.10 if not is_tier_1 else 0.01  # Lower threshold for tier-1
            
            if self.reinvestment_enabled and (profit_usdt > min_reinvest or is_tier_1):
                # For tier-1, reinvest the full proceeds to maintain deployment
                amount_to_reinvest = proceeds_usdt if is_tier_1 else profit_usdt
                reinvestment_result = await self._trigger_reinvestment(amount_to_reinvest, profit_usdt, is_tier_1)
            
            return {
                'success': True,
                'symbol': symbol,
                'proceeds_usdt': proceeds_usdt,
                'profit_usdt': profit_usdt,
                'total_profits': self.total_profits_harvested,
                'reinvestment': reinvestment_result
            }
            
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error handling successful sell: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _trigger_reinvestment(self, amount_to_reinvest: float, profit_usdt: float, is_tier_1: bool = False) -> Dict[str, Any]:
        """
        Trigger automatic reinvestment of profit proceeds into new opportunities.
        
        Args:
            amount_to_reinvest: Amount to reinvest (proceeds for tier-1, profit % for others)
            profit_usdt: Pure profit amount
            is_tier_1: Whether this is a tier-1 account
            
        Returns:
            Dict with reinvestment status
        """
        try:
            # For tier-1, reinvest full amount; for others, apply percentage
            if is_tier_1:
                tier_limit = self.config.get('tier_1_trade_limit', 3.5)
                reinvest_amount = min(amount_to_reinvest, tier_limit)  # Tier-1 limited by config
                self.logger.info(f"[HARVESTER] [SYNC] Tier-1 reinvestment: ${reinvest_amount:.2f} from ${amount_to_reinvest:.2f} proceeds")
            else:
                reinvest_amount = amount_to_reinvest * (self.reinvestment_percentage / 100)
            
            self.logger.info(f"[HARVESTER] [SYNC] Triggering reinvestment: ${reinvest_amount:.2f} ({self.reinvestment_percentage}% of ${profit_usdt:.2f} profit)")
            
            # Get best reinvestment opportunities
            reinvestment_symbols = await self._get_reinvestment_opportunities()
            
            if reinvestment_symbols:
                # Use the first suitable symbol
                target_symbol = reinvestment_symbols[0]
                
                # Create reinvestment signal with tier-1 appropriate amount
                tier_limit = self.config.get('tier_1_trade_limit', 3.5)
                signal_amount = tier_limit if is_tier_1 else max(tier_limit, reinvest_amount)
                
                reinvestment_signal = {
                    'symbol': target_symbol,
                    'side': 'buy',
                    'amount': signal_amount,
                    'confidence': 0.85,  # High confidence for reinvestment
                    'source': 'profit_reinvestment',
                    'metadata': {
                        'source_symbol': 'profit_harvest',
                        'profit_reinvested': profit_usdt,
                        'reinvestment_amount': reinvest_amount,
                        'is_tier_1': is_tier_1,
                        'reason': f'Seamless reinvestment from profit harvesting'
                    }
                }
                
                # Add to bot's signal queue for immediate processing
                if hasattr(self.bot, 'signal_queue'):
                    await self.bot.signal_queue.put(reinvestment_signal)
                    self.logger.info(f"[HARVESTER] [BULLSEYE] Reinvestment signal queued: {target_symbol} for ${signal_amount:.2f}")
                    
                    # Also trigger opportunity scanner for additional opportunities
                    if hasattr(self.bot, 'opportunity_scanner'):
                        asyncio.create_task(self.bot.opportunity_scanner.scan_once())
                    
                    return {
                        'reinvestment_triggered': True,
                        'symbol': target_symbol,
                        'amount': signal_amount,
                        'confidence': 0.85
                    }
            
            # Fallback: trigger general opportunity scanning for new investments
            self.logger.info(f"[HARVESTER] No immediate opportunities found, profit will be available for next scan cycle")
            return {
                'reinvestment_triggered': False,
                'reason': 'No suitable opportunities found',
                'amount_available': reinvest_amount
            }
            
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error in reinvestment trigger: {e}")
            return {
                'reinvestment_triggered': False,
                'error': str(e)
            }
    
    async def _get_reinvestment_opportunities(self) -> List[str]:
        """
        Get suitable symbols for reinvestment based on current market conditions.
        Prioritizes symbols not currently in portfolio to maximize diversification.
        """
        try:
            # Get current portfolio positions
            portfolio_symbols = set()
            if self.portfolio_tracker or (hasattr(self, 'bot') and self.bot and hasattr(self.bot, 'portfolio_tracker')):
                tracker = self.portfolio_tracker or self.bot.portfolio_tracker
                positions = tracker.get_open_positions()
                portfolio_symbols = {pos['symbol'] for pos in positions if pos.get('amount', 0) > 0}
            
            # Get available trade pairs from bot
            available_pairs = []
            if hasattr(self, 'bot') and self.bot:
                available_pairs = getattr(self.bot, 'trade_pairs', [])
            
            # Filter out symbols already in portfolio for diversification
            non_portfolio_pairs = [p for p in available_pairs if p not in portfolio_symbols]
            
            # If all pairs are in portfolio, use all available pairs
            candidate_pairs = non_portfolio_pairs if non_portfolio_pairs else available_pairs
            
            # For tier-1, prioritize liquid pairs
            tier_1_priority = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT', 'SHIB/USDT']
            
            # Sort by priority
            prioritized_pairs = []
            for pair in tier_1_priority:
                if pair in candidate_pairs:
                    prioritized_pairs.append(pair)
            
            # Add remaining pairs
            for pair in candidate_pairs:
                if pair not in prioritized_pairs:
                    prioritized_pairs.append(pair)
            
            return prioritized_pairs[:3]  # Return top 3 opportunities
            
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error getting reinvestment opportunities: {e}")
            # Fallback to default liquid pairs
            return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
