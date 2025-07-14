"""
Portfolio Position Scanner - Enhanced for Real-Time Position Tracking

This module provides comprehensive portfolio position scanning and analysis
for the Kraken trading bot, enabling intelligent decision-making based on
current holdings and market conditions.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from .utils.custom_logging import configure_logging
from .utils.decimal_precision_fix import safe_decimal, safe_float, is_zero
logger = configure_logging()
# Temporarily set to DEBUG for portfolio scanner
import logging
logger.setLevel(logging.DEBUG)


class PortfolioPositionScanner:
    """
    Portfolio Position Scanner for Automatic Position Recovery

    This scanner automatically detects existing crypto holdings and estimates
    entry prices to enable immediate profit extraction after bot restarts.
    """

    def __init__(self, bot=None, bot_reference=None, **kwargs) -> None:
        """Initialize portfolio position scanner."""
        self.bot = bot or bot_reference  # Handle both parameter names
        self.detected_positions = []
        self.last_scan_time = 0

        logger.info("[PORTFOLIO_SCANNER] Portfolio Position Scanner initialized")

    async def scan_existing_positions(self) -> List[Dict[str, Any]]:
        """
        Scan account for existing positions and estimate entry prices.

        Returns:
            List of detected positions with estimated entry prices
        """
        positions = []

        try:
            # Try to get balance manager first (preferred)
            balance_manager = None
            if hasattr(self.bot, 'balance_manager') and self.bot.balance_manager:
                balance_manager = self.bot.balance_manager
                logger.info("[PORTFOLIO_SCANNER] Using balance manager for portfolio scan")
            
            # Fallback to exchange if no balance manager
            exchange = None
            if not balance_manager:
                if hasattr(self.bot, 'exchange'):
                    exchange = self.bot.exchange
                elif hasattr(self.bot, 'account'):
                    exchange = self.bot.account
                
                if not exchange:
                    logger.warning("[PORTFOLIO_SCANNER] No exchange or balance manager available")
                    return positions

            # Get account balance
            if balance_manager:
                logger.info("[PORTFOLIO_SCANNER] Fetching balance via balance manager...")
                balance = await balance_manager.get_all_balances()
            else:
                logger.info("[PORTFOLIO_SCANNER] Fetching balance from exchange...")
                balance = await exchange.fetch_balance()

            if not balance:
                logger.warning("[PORTFOLIO_SCANNER] Could not fetch account balance")
                return positions
            
            # Debug: Log the balance structure
            logger.info(f"[PORTFOLIO_SCANNER] Balance structure keys: {list(balance.keys())}")
            
            # Check if balance has info key (ccxt style)
            if 'info' in balance:
                logger.info("[PORTFOLIO_SCANNER] Balance has 'info' key, checking for actual balances...")
                
            # Check different possible balance structures
            total_balance = balance.get('total', {})
            free_balance = balance.get('free', {})
            
            # Check if balance contains currency keys directly
            potential_currencies = []
            if not total_balance and not free_balance and isinstance(balance, dict):
                # Check if balance contains currency keys directly
                potential_currencies = [k for k in balance.keys() if k not in ['info', 'free', 'used', 'total', 'timestamp']]
                if potential_currencies:
                    logger.info(f"[PORTFOLIO_SCANNER] Balance contains direct currency keys: {potential_currencies[:5]}...")
                else:
                    logger.info(f"[PORTFOLIO_SCANNER] Found {len(total_balance)} total assets, {len(free_balance)} free assets")
            else:
                logger.info(f"[PORTFOLIO_SCANNER] Found {len(total_balance)} total assets, {len(free_balance)} free assets")

            # Check for significant crypto holdings
            holdings = balance.get("total", balance.get("free", {}))

            # Also check free balance if total is empty
            if not holdings:
                holdings = free_balance
                logger.info("[PORTFOLIO_SCANNER] Using free balance as total was empty")
                
            # If still no holdings, check if balance is the holdings dict itself
            if not holdings and potential_currencies:
                holdings = balance
                logger.info("[PORTFOLIO_SCANNER] Using balance dict directly as holdings")
                
            for currency, amount in holdings.items():
                # Convert amount to Decimal for precise comparison
                dec_amount = safe_decimal(amount)
                
                if not is_zero(dec_amount):
                    logger.info(f"[PORTFOLIO_SCANNER] Found {currency}: {amount}")
                    
                if currency in ["USD", "USDT", "EUR", "ZUSD", "ZEUR"] or dec_amount <= safe_decimal("0.001"):
                    logger.debug(f"[PORTFOLIO_SCANNER] Skipping {currency} (fiat or tiny amount)")
                    continue  # Skip fiat currencies and tiny amounts

                # CRITICAL FIX: Clean currency name and handle .F fork tokens
                clean_currency = self._clean_currency_name(currency)

                if not clean_currency:  # Skip if cleaning resulted in invalid currency
                    continue

                # Create trading symbol with cleaned currency - use USDT for Kraken
                symbol = f"{clean_currency}/USDT"
                
                # Skip if symbol not available on exchange
                if hasattr(self.bot, 'exchange') and hasattr(self.bot.exchange, 'markets'):
                    if symbol not in self.bot.exchange.markets:
                        logger.debug(f"[PORTFOLIO_SCANNER] Skipping {symbol} - not available on Kraken")
                        continue

                # Estimate entry price (simplified - could be enhanced with trade history)
                entry_price = await self._estimate_entry_price(symbol, amount)

                if entry_price and not is_zero(safe_decimal(entry_price)):
                    # Convert amounts to Decimal for precise calculations
                    dec_amount = safe_decimal(amount)
                    dec_entry_price = safe_decimal(entry_price)
                    
                    position = {
                        "symbol": symbol,
                        "amount": safe_float(dec_amount),  # Store as float for compatibility
                        "entry_price": safe_float(dec_entry_price),
                        "current_value": safe_float(dec_amount * dec_entry_price),
                        "confidence": "medium",
                        "detection_method": "balance_scan",
                        "timestamp": time.time(),
                    }

                    positions.append(position)
                    logger.info(
                        f"[PORTFOLIO_SCANNER] Detected position: {clean_currency} {amount:.8f} @ ${entry_price:.6f}"
                    )

            self.detected_positions = positions
            self.last_scan_time = time.time()

            total_value = sum(p["current_value"] for p in positions)
            logger.info(
                f"[PORTFOLIO_SCANNER] Scan complete: {len(positions)} positions worth ${total_value:.2f}"
            )

            return positions

        except Exception as e:
            logger.error(f"[PORTFOLIO_SCANNER] Error scanning positions: {e}")
            return []

    def _clean_currency_name(self, currency: str) -> Optional[str]:
        """
        CRITICAL FIX: Clean currency names to handle .F fork tokens and other variants.

        Args:
            currency: Raw currency symbol from balance (e.g., 'ADA.F', 'SOL.F')

        Returns:
            Clean currency symbol or None if invalid
        """
        try:
            if not currency or not isinstance(currency, str):
                return None

            # Remove common suffixes from fork tokens
            clean = currency.upper().strip()

            # Handle .F fork tokens (ADA.F -> ADA)
            if clean.endswith(".F"):
                clean = clean[:-2]
                logger.debug(
                    f"[PORTFOLIO_SCANNER] Cleaned fork token: {currency} -> {clean}"
                )

            # Handle other known suffixes
            if clean.endswith(".D"):  # Staking derivatives
                clean = clean[:-2]

            # Skip if cleaned name is too short or invalid
            if len(clean) < 2:
                logger.warning(
                    f"[PORTFOLIO_SCANNER] Skipping invalid currency after cleaning: {currency} -> {clean}"
                )
                return None

            # CRITICAL FIX: Skip known problematic currencies and .F tokens that can't be traded
            skip_currencies = {
                "KFEE",
                "EARN",
                "REPV2",
                "XXRP",
                "ADA.F",
                "SOL.F",
                "BTC.F",
                "ETH.F",
                "AI16Z",      # Not available on Kraken
                "BERA",       # Not available on Kraken
                "EURR",       # Not a crypto
                "FARTCOIN",   # Not available on Kraken
                "USD.HOLD",   # Not tradeable
                "ZUSD",       # USD equivalent
                "USD"         # Fiat currency
            }
            if currency in skip_currencies or clean in skip_currencies:
                logger.debug(
                    f"[PORTFOLIO_SCANNER] Skipping known problematic currency: {currency}"
                )
                return None

            return clean

        except Exception as e:
            logger.warning(
                f"[PORTFOLIO_SCANNER] Error cleaning currency name '{currency}': {e}"
            )
            return None

    async def _estimate_entry_price(
        self, symbol: str, amount: Union[float, Decimal]
    ) -> Optional[float]:
        """
        Estimate entry price for a position.

        Args:
            symbol: Trading symbol (e.g., 'BTC/USD')
            amount: Position amount

        Returns:
            Estimated entry price or None
        """
        try:
            # Try WebSocket ticker data first (fastest)
            websocket_manager = getattr(self.bot, 'websocket_manager', None)
            if websocket_manager:
                # Try current_tickers first (websocket_manager_v2)
                if hasattr(websocket_manager, 'current_tickers') and websocket_manager.current_tickers:
                    ticker_data = websocket_manager.current_tickers
                    if isinstance(ticker_data, dict) and symbol in ticker_data:
                        ws_price = ticker_data[symbol].get('last', 0)
                        if not is_zero(safe_decimal(ws_price)):
                            logger.debug(f"[PORTFOLIO_SCANNER] Using WebSocket price for {symbol}: ${ws_price}")
                            return safe_float(safe_decimal(ws_price))
                
                # Try ticker_data directly
                elif hasattr(websocket_manager, 'ticker_data') and isinstance(websocket_manager.ticker_data, dict):
                    if symbol in websocket_manager.ticker_data:
                        ws_price = websocket_manager.ticker_data[symbol].get('last', 0)
                        if not is_zero(safe_decimal(ws_price)):
                            logger.debug(f"[PORTFOLIO_SCANNER] Using WebSocket ticker_data price for {symbol}: ${ws_price}")
                            return safe_float(safe_decimal(ws_price))
                
                # Legacy support - only if last_price_update is a dict
                elif hasattr(websocket_manager, 'last_price_update') and isinstance(websocket_manager.last_price_update, dict):
                    if symbol in websocket_manager.last_price_update:
                        ws_price = websocket_manager.last_price_update[symbol].get('price', 0)
                        if not is_zero(safe_decimal(ws_price)):
                            logger.debug(f"[PORTFOLIO_SCANNER] Using legacy WebSocket price for {symbol}: ${ws_price}")
                            return safe_float(safe_decimal(ws_price))
            
            # Try balance manager ticker cache next
            balance_manager = getattr(self.bot, 'balance_manager', None)
            if balance_manager and hasattr(balance_manager, 'ticker_cache'):
                cached_price = balance_manager.ticker_cache.get_price(symbol)
                if cached_price and not is_zero(safe_decimal(cached_price)):
                    logger.debug(f"[PORTFOLIO_SCANNER] Using cached price for {symbol}: ${cached_price}")
                    return safe_float(safe_decimal(cached_price))
            
            # Skip API call - use fallback prices to avoid delays
            logger.debug(f"[PORTFOLIO_SCANNER] Using fallback price for {symbol} to avoid API call")

            # Fallback price estimation - updated for USDT pairs
            fallback_prices = {
                "BTC/USDT": 107000.0,
                "ETH/USDT": 2750.0,
                "SOL/USDT": 160.0,
                "ADA/USDT": 0.65,
                "SHIB/USDT": 0.000013,
                "DOGE/USDT": 0.15,
                "DOT/USDT": 6.5,
                "ALGO/USDT": 0.18,
                "ATOM/USDT": 10.5,
                "XRP/USDT": 0.65,
                "AVAX/USDT": 30.0,   # Added AVAX
                "AI16Z/USDT": 0.56,  # Approximate price for AI16Z
            }

            return fallback_prices.get(symbol, 1.0)

        except Exception as e:
            logger.error(
                f"[PORTFOLIO_SCANNER] Error estimating entry price for {symbol}: {e}"
            )
            return None

    async def notify_autonomous_sell_engines(
        self, positions: List[Dict[str, Any]]
    ) -> None:
        """
        Notify autonomous sell engines about detected positions.

        Args:
            positions: List of detected positions
        """
        try:
            # Import ENHANCED autonomous sell engine for position recovery
            from .strategies.autonomous_sell_engine import AutonomousSellEngine, SellEngineConfig
            
            # Initialize autonomous sell engines if not already done
            if not hasattr(self.bot, "autonomous_sell_engines"):
                self.bot.autonomous_sell_engines = {}
                logger.info("[PORTFOLIO_SCANNER] Initialized autonomous sell engines container")

            engines = self.bot.autonomous_sell_engines

            for position in positions:
                symbol = position["symbol"]

                if symbol not in engines:
                    # Create new autonomous sell engine for this symbol
                    try:
                        config = SellEngineConfig(
                            target_profit_pct=1.5,  # 1.5% profit target for $2 positions
                            stop_loss_pct=2.0,    # 2.0% stop loss for $2 positions  
                            trailing_stop_pct=0.5, # 0.5% trailing stop
                        )
                        
                        # Create sell engine with exchange reference
                        exchange = getattr(self.bot, 'exchange', None)
                        if not exchange:
                            logger.warning(f"[PORTFOLIO_SCANNER] No exchange reference for {symbol}")
                            continue
                            
                        sell_engine = AutonomousSellEngine(
                            config=config,
                            exchange=exchange,
                            balance_manager=getattr(self.bot, 'balance_manager', None)
                        )
                        
                        engines[symbol] = sell_engine
                        logger.info(f"[PORTFOLIO_SCANNER] Created autonomous sell engine for {symbol}")
                        
                    except Exception as e:
                        logger.error(f"[PORTFOLIO_SCANNER] Error creating sell engine for {symbol}: {e}")
                        continue

                # Get the sell engine
                engine = engines[symbol]

                # Notify engine about position
                if hasattr(engine, "on_position_update"):
                    # Create position dict for the method
                    # Use Decimal for precise value calculation
                    dec_amount = safe_decimal(position["amount"])
                    dec_current_price = safe_decimal(position.get("current_price", position["entry_price"]))
                    
                    position_data = {
                        'amount': position["amount"],
                        'entry_price': position["entry_price"],
                        'entry_time': position["timestamp"],
                        'current_price': safe_float(dec_current_price),
                        'value_usd': safe_float(dec_amount * dec_current_price)
                    }
                    await engine.on_position_update(symbol, position_data)

                    logger.info(
                        f"[PORTFOLIO_SCANNER] Notified sell engine for {symbol} - "
                        f"Position: {position['amount']:.8f} @ ${position['entry_price']:.6f}"
                    )
                else:
                    logger.warning(
                        f"[PORTFOLIO_SCANNER] Sell engine for {symbol} missing on_position_update method"
                    )

        except Exception as e:
            logger.error(f"[PORTFOLIO_SCANNER] Error notifying sell engines: {e}")

    async def scan_and_recover_positions(self) -> Dict[str, Any]:
        """
        MISSING METHOD FIX: Main method called by bot.py for automatic position recovery.

        This is the primary entry point that bot.py calls during initialization
        to automatically scan and recover existing positions.

        Returns:
            Dict with recovery results and statistics
        """
        try:
            logger.info(
                "[POSITION_RECOVERY] Starting automatic scan and recovery process..."
            )

            # Scan for existing positions
            positions = await self.scan_existing_positions()

            recovered_count = 0
            total_usd_value = 0.0
            errors = []

            if positions:
                # Log detailed position information
                logger.info("[POSITION_RECOVERY] ===== DETECTED POSITIONS =====")
                for pos in positions:
                    logger.info(
                        f"[POSITION_RECOVERY] {pos['symbol']}: "
                        f"{pos['amount']:.8f} units @ ${pos['entry_price']:.6f} = "
                        f"${pos['current_value']:.2f}"
                    )
                logger.info("[POSITION_RECOVERY] =============================")
                
                # Calculate totals
                recovered_count = len(positions)
                total_usd_value = sum(p.get("current_value", 0) for p in positions)

                # Notify autonomous sell engines about discovered positions
                try:
                    await self.notify_autonomous_sell_engines(positions)
                    logger.info(
                        f"[POSITION_RECOVERY] Notified sell engines about {recovered_count} positions"
                    )
                except Exception as e:
                    error_msg = f"Failed to notify sell engines: {e}"
                    errors.append(error_msg)
                    logger.error(f"[POSITION_RECOVERY] {error_msg}")

                # Create position dictionary for easy access
                positions_dict = {}
                for pos in positions:
                    symbol = pos["symbol"]
                    positions_dict[symbol] = {
                        "amount": pos["amount"],
                        "estimated_entry_price": pos["entry_price"],
                        "current_value": pos["current_value"],
                        "confidence": pos["confidence"],
                    }

                logger.info(
                    f"[POSITION_RECOVERY] [OK] SUCCESS: Recovered {recovered_count} positions worth ${total_usd_value:.2f}"
                )

                return {
                    "success": True,
                    "recovered": recovered_count,
                    "total_usd_value": total_usd_value,
                    "positions": positions_dict,
                    "errors": errors,
                    "scan_time": time.time(),
                }
            else:
                logger.info(
                    "[POSITION_RECOVERY] No existing positions found - ready for new trades"
                )

                return {
                    "success": True,
                    "recovered": 0,
                    "total_usd_value": 0.0,
                    "positions": {},
                    "errors": errors,
                    "scan_time": time.time(),
                }

        except Exception as e:
            error_msg = f"Critical error in scan and recovery: {e}"
            logger.error(f"[POSITION_RECOVERY] {error_msg}")

            return {
                "success": False,
                "recovered": 0,
                "total_usd_value": 0.0,
                "positions": {},
                "errors": [error_msg],
                "scan_time": time.time(),
            }

    async def recover_all_positions(self) -> Dict[str, Any]:
        """
        Complete position recovery process.

        Returns:
            Recovery summary with statistics
        """
        try:
            logger.info("[PORTFOLIO_SCANNER] Starting complete position recovery")

            # Scan for existing positions
            positions = await self.scan_existing_positions()

            if positions:
                # Notify autonomous sell engines
                await self.notify_autonomous_sell_engines(positions)

                # Calculate summary
                total_positions = len(positions)
                total_value = sum(p["current_value"] for p in positions)

                summary = {
                    "success": True,
                    "positions_recovered": total_positions,
                    "total_value": total_value,
                    "positions": positions,
                    "recovery_time": time.time(),
                }

                logger.info(
                    f"[PORTFOLIO_SCANNER] Recovery complete: {total_positions} positions, ${total_value:.2f} total value"
                )

                return summary
            else:
                logger.info("[PORTFOLIO_SCANNER] No positions found to recover")
                return {
                    "success": True,
                    "positions_recovered": 0,
                    "total_value": 0.0,
                    "positions": [],
                    "recovery_time": time.time(),
                }

        except Exception as e:
            logger.error(f"[PORTFOLIO_SCANNER] Error in position recovery: {e}")
            return {
                "success": False,
                "error": str(e),
                "positions_recovered": 0,
                "total_value": 0.0,
                "positions": [],
                "recovery_time": time.time(),
            }

    def get_detected_positions(self) -> List[Dict[str, Any]]:
        """Get currently detected positions."""
        return self.detected_positions.copy()

    def get_statistics(self) -> Dict[str, Any]:
        """Get scanner statistics."""
        return {
            "positions_detected": len(self.detected_positions),
            "last_scan_time": self.last_scan_time,
            "total_value": sum(
                p.get("current_value", 0) for p in self.detected_positions
            ),
        }


__all__ = ["PortfolioPositionScanner"]
