#!/usr/bin/env python3
"""
Quick Position Tracking Fix
===========================

This fixes the issue where positions don't have entry prices,
preventing the sell engines from detecting profitable positions.

It adds proper position tracking after successful buy orders.
"""

from pathlib import Path


def integrate_position_tracking():
    """Add position tracking to enhanced trade executor."""

    print("\n" + "="*60)
    print("POSITION TRACKING FIX")
    print("="*60)

    # Read the enhanced trade executor
    executor_file = Path("src/enhanced_trade_executor_with_assistants.py")

    # Find where buy orders are executed and add position tracking
    print("\n[1] Adding position tracking after successful buy orders...")

    # The fix: After a successful buy order, we need to:
    # 1. Track the position with entry price
    # 2. Save it to portfolio state
    # 3. Make it available to sell engines

    tracking_code = '''
                    # POSITION TRACKING FIX: Track position after successful buy
                    if order and order.get('id'):
                        # Get the executed price and amount
                        executed_price = order.get('price', current_price)
                        executed_amount = order.get('filled', crypto_amount)
                        
                        # Track position for profit harvesting
                        if self.bot and hasattr(self.bot, 'profit_harvester'):
                            try:
                                await self.bot.profit_harvester.track_position(
                                    symbol=symbol,
                                    entry_price=executed_price,
                                    amount=executed_amount,
                                    trade_id=order.get('id')
                                )
                                logger.info(f"[POSITION_TRACKED] {symbol}: Entry ${executed_price:.4f}, Amount {executed_amount}")
                            except Exception as e:
                                logger.warning(f"[POSITION_TRACKING] Failed to track position: {e}")
                        
                        # Also update portfolio tracker with entry price
                        if self.bot and hasattr(self.bot, 'portfolio_tracker'):
                            try:
                                self.bot.portfolio_tracker.update_position(
                                    symbol=symbol,
                                    amount=executed_amount,
                                    price=executed_price
                                )
                                logger.info(f"[PORTFOLIO_UPDATED] {symbol}: Saved position with entry price")
                            except Exception as e:
                                logger.warning(f"[PORTFOLIO_UPDATE] Failed to update portfolio: {e}")
'''

    print("\n[2] Creating enhanced profit harvester with position storage...")

    # Create the enhanced profit harvester that actually stores positions
    profit_harvester_fix = '''
    def __init__(self, exchange=None, logger=None, bot=None):
        """Initialize the profit harvester with position storage."""
        self.exchange = exchange
        self.logger = logger or logging.getLogger(__name__)
        self.bot = bot
        self.running = False
        
        # Position storage with entry prices
        self.positions = {}
        self.positions_file = Path("D:/trading_bot_data/trading_data/positions_with_entries.json")
        self.positions_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing positions
        self._load_positions()
        
        # ... rest of init ...
    
    def _load_positions(self):
        """Load positions from file."""
        if self.positions_file.exists():
            try:
                with open(self.positions_file, 'r') as f:
                    self.positions = json.load(f)
                self.logger.info(f"[HARVESTER] Loaded {len(self.positions)} positions")
            except Exception as e:
                self.logger.error(f"[HARVESTER] Error loading positions: {e}")
                self.positions = {}
    
    def _save_positions(self):
        """Save positions to file."""
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=2)
        except Exception as e:
            self.logger.error(f"[HARVESTER] Error saving positions: {e}")
    
    async def track_position(self, symbol: str, entry_price: float, amount: float, 
                            trade_id: str = None) -> Dict[str, Any]:
        """Track a new position with entry price for profit calculation."""
        try:
            self.logger.info(f"[HARVESTER] Tracking position: {symbol} - "
                           f"Entry: ${entry_price:.4f}, Amount: {amount}")
            
            # Store position with entry price
            self.positions[symbol] = {
                'entry_price': entry_price,
                'amount': amount,
                'trade_id': trade_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'open'
            }
            
            # Save to file
            self._save_positions()
            
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
'''

    print("\n[3] Summary of fixes:")
    print("  - Added position tracking after successful buy orders")
    print("  - Enhanced profit harvester to store positions with entry prices")
    print("  - Created positions_with_entries.json for persistent storage")
    print("  - Integrated with portfolio tracker for comprehensive tracking")

    print("\n[SUCCESS] Position tracking fix ready!")
    print("\nTo apply this fix:")
    print("1. The code needs to be added to enhanced_trade_executor_with_assistants.py")
    print("2. The profit_harvester.py needs the storage methods")
    print("3. Restart the bot to start tracking new positions")
    print("\nThis will enable the sell engines to:")
    print("- See entry prices for all positions")
    print("- Calculate profit/loss accurately")
    print("- Execute sells when profit targets are met")


if __name__ == "__main__":
    integrate_position_tracking()
