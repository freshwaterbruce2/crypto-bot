"""
Portfolio Tracker - Persistent Implementation

This module provides a robust PortfolioTracker class that persists its state
to a file, ensuring that position data is preserved across bot restarts.
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class PortfolioTracker:
    """Portfolio tracker with file-based persistence."""

    def __init__(self, exchange: Any = None, config: Dict[str, Any] = None,
                 symbol_mapper: Any = None, bot_ref: Any = None,
                 account_manager: Any = None, rate_limiter: Any = None,
                 target_pairs: List[str] = None,
                 storage_path: str = "trading_data/portfolio_state.json"):
        """
        Initialize the portfolio tracker with flexible parameter support.
        Supports both old and new parameter formats for compatibility.
        """
        if exchange and config:
            self.exchange = exchange
            self.config = config
            self.symbol_mapper = symbol_mapper
            self.bot = bot_ref
            self.target_pairs = config.get('trade_pairs', [])
            self.account_manager = getattr(bot_ref, 'account', None) if bot_ref else None
            self.rate_limiter = None
        else:
            self.account_manager = account_manager
            self.rate_limiter = rate_limiter
            self.target_pairs = target_pairs or []
            self.exchange = None
            self.config = {}
            self.symbol_mapper = None
            self.bot = None

        self.logger = logging.getLogger(__name__)
        # Create storage directory if it doesn't exist
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.positions: Dict[str, Dict] = {}
        self._load_state()
        self.logger.info(f"[PORTFOLIO] PortfolioTracker initialized with persistence at {self.storage_path}")

    def _load_state(self):
        """Load portfolio state from the storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    self.positions = json.load(f)
                self.logger.info(f"[PORTFOLIO] Loaded {len(self.positions)} positions from {self.storage_path}")
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"[PORTFOLIO] Error loading state: {e}")

    def _save_state(self):
        """Save portfolio state to the storage file."""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self.positions, f, indent=2)
            self.logger.info(f"[PORTFOLIO] Saved {len(self.positions)} positions to {self.storage_path}")
        except IOError as e:
            self.logger.error(f"[PORTFOLIO] Error saving state: {e}")

    def update_position(self, symbol: str, amount: float, price: float) -> None:
        """Update position for a symbol with enhanced P&L tracking."""
        import time
        
        if amount > 0:
            # Check if this is a new position or update
            if symbol not in self.positions:
                # New position
                self.positions[symbol] = {
                    'amount': amount,
                    'price': price,  # Entry price
                    'entry_price': price,  # Explicit entry price
                    'value': amount * price,
                    'current_price': price,
                    'current_value': amount * price,
                    'entry_time': time.time(),
                    'unrealized_pnl': 0.0,
                    'unrealized_pnl_pct': 0.0,
                    'realized_pnl': 0.0,
                    'trade_count': 1,
                    'hold_time_hours': 0.0
                }
                self.logger.info(f"[PORTFOLIO] New position: {symbol} - {amount} @ ${price:.4f}")
                # Save state immediately after new position
                self._save_state()
            else:
                # Update existing position (averaging)
                pos = self.positions[symbol]
                old_amount = pos['amount']
                old_value = old_amount * pos['price']
                new_value = amount * price
                total_value = old_value + new_value
                total_amount = old_amount + amount
                
                # Calculate weighted average entry price
                avg_price = total_value / total_amount if total_amount > 0 else price
                
                self.positions[symbol].update({
                    'amount': total_amount,
                    'price': avg_price,  # Weighted average
                    'value': total_value,
                    'current_price': price,
                    'current_value': total_amount * price,
                    'trade_count': pos.get('trade_count', 0) + 1
                })
                self._update_pnl(symbol)
                self.logger.info(f"[PORTFOLIO] Updated position: {symbol} - total: {total_amount} @ avg: ${avg_price:.4f}")
        elif symbol in self.positions:
            # Position closed
            pos = self.positions[symbol]
            final_value = pos['amount'] * price
            entry_value = pos['amount'] * pos.get('entry_price', pos['price'])
            realized_pnl = final_value - entry_value
            
            self.logger.info(
                f"[PORTFOLIO] Position closed: {symbol} - "
                f"P&L: ${realized_pnl:.2f} ({(realized_pnl/entry_value)*100:.1f}%)"
            )
            
            # Store closed position data for history
            self._record_closed_position(symbol, pos, price, realized_pnl)
            
            del self.positions[symbol]
        self._save_state()

    def get_total_value(self) -> float:
        """Get total portfolio value."""
        return sum(pos['value'] for pos in self.positions.values())

    def get_position(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get position for a symbol."""
        return self.positions.get(symbol)

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions with detailed P&L info."""
        import time
        
        open_positions = []
        for symbol, position in self.positions.items():
            if position.get('amount', 0) > 0:
                # Update P&L before returning
                self._update_pnl(symbol)
                
                open_positions.append({
                    'symbol': symbol,
                    'amount': position['amount'],
                    'entry_price': position.get('entry_price', position['price']),
                    'current_price': position.get('current_price', position['price']),
                    'entry_value': position['value'],
                    'current_value': position.get('current_value', position['value']),
                    'unrealized_pnl': position.get('unrealized_pnl', 0),
                    'unrealized_pnl_pct': position.get('unrealized_pnl_pct', 0),
                    'hold_time_hours': position.get('hold_time_hours', 0),
                    'trade_count': position.get('trade_count', 1)
                })
        return open_positions
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary with P&L."""
        positions = self.get_open_positions()
        
        total_value = sum(p['current_value'] for p in positions)
        total_entry_value = sum(p['entry_value'] for p in positions)
        total_unrealized_pnl = sum(p['unrealized_pnl'] for p in positions)
        
        return {
            'total_positions': len(positions),
            'total_value': total_value,
            'total_entry_value': total_entry_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_unrealized_pnl_pct': (total_unrealized_pnl / total_entry_value * 100) if total_entry_value > 0 else 0,
            'positions': positions,
            'best_performer': max(positions, key=lambda x: x['unrealized_pnl_pct']) if positions else None,
            'worst_performer': min(positions, key=lambda x: x['unrealized_pnl_pct']) if positions else None
        }
    
    def update_price(self, symbol: str, current_price: float) -> None:
        """Update current price for a symbol and calculate P&L."""
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos['current_price'] = current_price
            pos['current_value'] = pos['amount'] * current_price
            self._update_pnl(symbol)
            # Don't save on every price update to avoid excessive disk I/O
            # Only save on position changes
        else:
            # Create a price tracking entry even if no position
            self.positions[symbol] = {
                'amount': 0,
                'price': current_price,
                'current_price': current_price,
                'value': 0,
                'current_value': 0,
                'unrealized_pnl': 0.0,
                'unrealized_pnl_pct': 0.0
            }
    
    def _update_pnl(self, symbol: str) -> None:
        """Update P&L calculations for a position."""
        import time
        
        if symbol not in self.positions:
            return
            
        pos = self.positions[symbol]
        if pos['amount'] <= 0:
            return
            
        # Calculate unrealized P&L
        entry_value = pos['amount'] * pos.get('entry_price', pos['price'])
        current_value = pos['amount'] * pos.get('current_price', pos['price'])
        
        pos['unrealized_pnl'] = current_value - entry_value
        pos['unrealized_pnl_pct'] = (pos['unrealized_pnl'] / entry_value * 100) if entry_value > 0 else 0
        
        # Update hold time
        if 'entry_time' in pos:
            pos['hold_time_hours'] = (time.time() - pos['entry_time']) / 3600
    
    def _record_closed_position(self, symbol: str, position: Dict, close_price: float, realized_pnl: float) -> None:
        """Record closed position for history tracking."""
        import time
        import json
        from pathlib import Path
        
        try:
            history_file = self.storage_path.parent / "closed_positions_history.json"
            
            # Load existing history
            history = []
            if history_file.exists():
                try:
                    with open(history_file, 'r') as f:
                        history = json.load(f)
                except:
                    pass
            
            # Add new closed position
            history.append({
                'symbol': symbol,
                'close_time': time.time(),
                'close_price': close_price,
                'amount': position['amount'],
                'entry_price': position.get('entry_price', position['price']),
                'realized_pnl': realized_pnl,
                'realized_pnl_pct': (realized_pnl / (position['amount'] * position['price']) * 100) if position['price'] > 0 else 0,
                'hold_time_hours': position.get('hold_time_hours', 0),
                'trade_count': position.get('trade_count', 1)
            })
            
            # Keep only last 1000 records
            history = history[-1000:]
            
            # Save updated history
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"[PORTFOLIO] Error recording closed position: {e}")

    async def get_optimal_trading_pairs(self, target_count: int) -> List[str]:
        """Returns the default target pairs for this minimal implementation."""
        return self.target_pairs[:target_count]

    async def update_from_trade(self, trade_data: Dict[str, Any]) -> None:
        """
        Update portfolio based on WebSocket trade data.
        """
        try:
            if not trade_data:
                return

            symbol = trade_data.get('symbol')
            side = trade_data.get('side')
            price = float(trade_data.get('price', 0))
            amount = float(trade_data.get('amount', 0))

            if not symbol or price <= 0 or amount <= 0:
                return

            if side == 'buy':
                current_pos = self.positions.get(symbol, {'amount': 0, 'price': 0, 'value': 0})
                new_amount = current_pos['amount'] + amount
                if current_pos['amount'] > 0:
                    avg_price = ((current_pos['amount'] * current_pos['price']) + (amount * price)) / new_amount
                else:
                    avg_price = price

                self.update_position(symbol, new_amount, avg_price)
                logging.info(f"[PORTFOLIO] Added {amount} {symbol} @ ${price:.4f}")

            elif side == 'sell':
                current_pos = self.positions.get(symbol)
                if current_pos and current_pos['amount'] >= amount:
                    new_amount = current_pos['amount'] - amount
                    if new_amount > 0:
                        self.update_position(symbol, new_amount, current_pos['price'])
                    else:
                        del self.positions[symbol]
                        self._save_state()
                    logging.info(f"[PORTFOLIO] Sold {amount} {symbol} @ ${price:.4f}")

        except Exception as e:
            logging.error(f"[PORTFOLIO] Error updating from trade: {e}")

    def get_active_positions(self) -> List[Dict[str, Any]]:
        """
        Get all active positions for order execution analysis.
        This method provides compatibility with OrderExecutionAssistant.
        
        Returns:
            List of active position dictionaries
        """
        try:
            # Leverage existing get_open_positions method
            open_positions = self.get_open_positions()
            
            # Format for order execution assistant
            active_positions = []
            for pos in open_positions:
                active_positions.append({
                    'symbol': pos['symbol'],
                    'side': 'long',  # Assuming all positions are long for spot trading
                    'size': pos['amount'],
                    'entry_price': pos['entry_price'],
                    'current_price': pos['current_price'],
                    'unrealized_pnl': pos['unrealized_pnl'],
                    'unrealized_pnl_pct': pos['unrealized_pnl_pct'],
                    'market_value': pos['current_value'],
                    'status': 'open',
                    'hold_time_hours': pos.get('hold_time_hours', 0)
                })
            
            self.logger.debug(f"[PORTFOLIO] Returning {len(active_positions)} active positions")
            return active_positions
            
        except Exception as e:
            self.logger.error(f"[PORTFOLIO] Error getting active positions: {e}")
            return []

    async def force_sync_with_exchange(self, exchange: Any, balance_manager: Any = None) -> Dict[str, Any]:
        """
        Force synchronization with actual exchange balances.
        This method will detect mismatches and update tracked positions accordingly.
        
        Args:
            exchange: Exchange instance or balance manager
            balance_manager: Optional balance manager for enhanced balance detection
            
        Returns:
            Dictionary with sync results and any mismatches found
        """
        try:
            self.logger.warning("[PORTFOLIO] Starting forced sync with exchange balances...")
            
            # Get current exchange balances
            if balance_manager:
                # Use balance manager for better detection
                all_balances = await balance_manager.get_all_balances()
                portfolio_state = await balance_manager.analyze_portfolio_state('USDT')
                deployed_assets = portfolio_state.get('deployed_assets', [])
            else:
                # Fallback to direct exchange fetch
                balance_data = await exchange.fetch_balance()
                all_balances = balance_data
                deployed_assets = []
            
            # Track mismatches
            mismatches = []
            synced_positions = []
            removed_positions = []
            
            # Process all non-USDT balances from exchange
            for asset, balance_info in all_balances.items():
                if asset in ['USDT', 'ZUSDT', 'USD', 'ZUSD']:
                    continue
                symbol = f"{asset}/USDT"
                
                # Get actual balance
                if isinstance(balance_info, dict):
                    actual_balance = float(balance_info.get('free', 0) + balance_info.get('used', 0))
                else:
                    actual_balance = float(balance_info)
                
                # Skip if no balance
                if actual_balance < 0.0001:
                    continue
                
                # Check tracked position
                tracked_pos = self.positions.get(symbol, {})
                tracked_amount = tracked_pos.get('amount', 0)
                
                # Detect mismatch (more than 0.1% difference)
                if abs(tracked_amount - actual_balance) > (actual_balance * 0.001):
                    mismatches.append({
                        'symbol': symbol,
                        'tracked': tracked_amount,
                        'actual': actual_balance,
                        'difference': actual_balance - tracked_amount
                    })
                    
                    # Get current price
                    current_price = 0
                    for asset_info in deployed_assets:
                        if asset_info.get('asset') == asset:
                            current_price = asset_info.get('price', 0)
                            break
                    
                    if current_price == 0 and exchange:
                        # Try to fetch current price
                        try:
                            ticker = await exchange.fetch_ticker(symbol)
                            current_price = ticker.get('last', 0)
                        except:
                            pass
                    
                    if current_price > 0:
                        # Update position to match actual balance
                        if tracked_amount == 0:
                            # New position - use current price as entry
                            self.update_position(symbol, actual_balance, current_price)
                        else:
                            # Existing position - adjust amount but keep weighted average price
                            old_entry_price = tracked_pos.get('price', current_price)
                            self.positions[symbol]['amount'] = actual_balance
                            self.positions[symbol]['value'] = actual_balance * old_entry_price
                            self.positions[symbol]['current_value'] = actual_balance * current_price
                            self._update_pnl(symbol)
                            self._save_state()
                        
                        synced_positions.append({
                            'symbol': symbol,
                            'old_amount': tracked_amount,
                            'new_amount': actual_balance,
                            'price': current_price
                        })
                        self.logger.warning(
                            f"[PORTFOLIO] Synced {symbol}: {tracked_amount:.6f} -> {actual_balance:.6f} @ ${current_price:.6f}"
                        )
            
            # Check for positions that should be removed (no balance on exchange)
            for symbol, position in list(self.positions.items()):
                asset = symbol.split('/')[0]
                
                # Check if we have balance for this asset
                actual_balance = 0
                if asset in all_balances:
                    bal = all_balances[asset]
                    if isinstance(bal, dict):
                        actual_balance = float(bal.get('free', 0) + bal.get('used', 0))
                    else:
                        actual_balance = float(bal)
                
                if actual_balance < 0.0001 and position.get('amount', 0) > 0:
                    removed_positions.append({
                        'symbol': symbol,
                        'tracked_amount': position.get('amount', 0)
                    })
                    del self.positions[symbol]
                    self.logger.warning(f"[PORTFOLIO] Removed {symbol} - no balance on exchange")
            
            # Save updated state
            self._save_state()
            
            # Return sync results
            results = {
                'success': True,
                'mismatches_found': len(mismatches),
                'positions_synced': len(synced_positions),
                'positions_removed': len(removed_positions),
                'mismatches': mismatches,
                'synced': synced_positions,
                'removed': removed_positions,
                'current_positions': len(self.positions)
            }
            
            self.logger.warning(
                f"[PORTFOLIO] Sync complete: {len(mismatches)} mismatches fixed, "
                f"{len(synced_positions)} synced, {len(removed_positions)} removed"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"[PORTFOLIO] Error during forced sync: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'current_positions': len(self.positions)
            }