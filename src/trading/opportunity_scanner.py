"""
Opportunity Scanner - Enhanced Implementation for Autonomous Trading

This module provides the OpportunityScanner class that actively scans
for profitable trading opportunities using multiple strategies.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OpportunitySignal:
    """Signal data structure for trading opportunities."""
    symbol: str
    signal_type: str
    confidence: float
    timestamp: float
    side: str = "buy"
    price: float = 0.0
    volume: float = 0.0
    profit_potential: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class OpportunityScanner:
    """Enhanced opportunity scanner for autonomous profit detection."""

    def __init__(self, bot: Any = None, symbols: List[str] = None, config: Dict[str, Any] = None,
                 scan_interval: int = 5, exchange_client: Any = None, symbol_mapper: Any = None,
                 bot_ref: Any = None):
        """Initialize the opportunity scanner with flexible parameter support.
        
        Args:
            bot: Trading bot instance (legacy parameter)
            symbols: List of trading symbols to monitor (legacy parameter)
            config: Configuration dictionary
            scan_interval: Scanning interval in seconds
            exchange_client: Exchange client instance (new parameter)
            symbol_mapper: Symbol mapper instance (new parameter)
            bot_ref: Bot reference (new parameter)
        """
        # Initialize logger FIRST before any logging calls
        self.logger = logging.getLogger(__name__)

        # Handle both parameter formats for compatibility
        if exchange_client and config:
            # New format from bot initialization
            self.bot = bot_ref or bot  # Use bot_ref if available, fallback to bot
            self.exchange_client = exchange_client
            self.symbol_mapper = symbol_mapper
            self.config = config
            self.symbols = config.get('trade_pairs', [])
            # Also add symbols if passed as parameter
            if symbols:
                self.symbols = symbols
        else:
            # Legacy format
            self.bot = bot
            self.exchange_client = getattr(bot, 'exchange', None) if bot else None
            self.symbol_mapper = None
            self.config = config or {}
            self.symbols = symbols or []

        # SHIB/USDT ultra-aggressive scanning for maximum profit generation
        # Optimized for single-pair micro-scalping with 0% fees
        self.scan_interval = 2  # 2 seconds for ultra-rapid opportunity detection
        self.logger.info(f"[SHIB_PROFIT_OPTIMIZER] Ultra-aggressive scanning: {self.scan_interval}s interval for SHIB/USDT maximum profit capture")

        self.running = False
        self._scan_task = None

        # Cache for recent ticker data
        self._ticker_cache = {}
        self._last_scan_time = 0

        # SHIB/USDT ULTRA-AGGRESSIVE optimization parameters
        # OPTIMIZED: Extreme micro-profit thresholds for maximum frequency
        self.min_profit_threshold = 0.0008  # 0.08% minimum profit - matches strategy
        self.max_opportunities_per_scan = 50  # Maximum opportunities for single-pair focus

        # SHIB/USDT optimized profit tier thresholds for maximum compounding
        self.profit_tiers = {
            'ultra_micro': 0.0008,  # 0.08% - ultra-micro scalping
            'micro': 0.0015,        # 0.15% - micro scalping
            'fast': 0.0025,         # 0.25% - fast scalping
            'medium': 0.004,        # 0.4% - medium scalping
            'aggressive': 0.006     # 0.6% - aggressive scalping
        }

        # SHIB/USDT specific volatility parameters
        self.shib_volatility_threshold = 0.001  # 0.1% volatility for SHIB signals
        self.shib_momentum_threshold = 0.0005   # 0.05% momentum for ultra-fast entries

        # Ultra-aggressive parameters for fee-free advantage
        self.regime_change_confidence = 0.5   # Lower threshold for more signals
        self.mean_reversion_confidence = 0.5  # Lower threshold for more signals
        self.arbitrage_threshold = 0.003      # 0.3% arbitrage minimum
        self.momentum_threshold = 0.0005      # 0.05% momentum - ULTRA LOW for maximum signals
        self.volume_threshold = 1.1  # 1.1x average volume

        # Storage for found opportunities
        self.found_opportunities = []

        # Capital deployment state tracking
        capital_config = self.config.get('capital_deployment', {})
        self.capital_deployment_enabled = capital_config.get('enabled', True)
        self.capital_deployed_state = False
        self.min_available_usdt = capital_config.get('min_available_usdt', 2.0)  # Minimum USDT to consider for trading
        self.max_deployment_percentage = capital_config.get('max_deployment_percentage', 95.0)  # Maximum capital deployment percentage

        # Balance cache to reduce API calls
        self._balance_cache = {}
        self._balance_cache_time = 0
        self._balance_cache_ttl = 30  # Cache for 30 seconds
        self.last_deployment_check = 0
        self.deployment_check_interval = capital_config.get('deployment_check_interval', 30)  # Check every 30 seconds
        self.prioritize_exits_when_deployed = capital_config.get('prioritize_exits_when_deployed', True)
        self.log_deployment_status = capital_config.get('log_deployment_status', True)

        # Rapid-fire mode configuration
        self.rapid_fire_mode = self.config.get('rapid_fire_mode', {}).get('enabled', False)
        self.rapid_fire_symbols = self.config.get('rapid_fire_mode', {}).get('pairs_for_rapid_fire', [])
        self.rapid_fire_threshold = self.config.get('rapid_fire_mode', {}).get('consecutive_profit_threshold', 0.003)
        self.rapid_fire_history = {}  # Track consecutive profits by symbol
        self.max_consecutive = self.config.get('rapid_fire_mode', {}).get('max_consecutive_trades', 5)

        self.logger.info(f"[SCANNER] OpportunityScanner initialized for {len(self.symbols)} symbols")
        if self.rapid_fire_mode:
            self.logger.info(f"[SCANNER] Rapid-fire mode ENABLED for: {self.rapid_fire_symbols}")

    async def start(self) -> None:
        """Start the scanning process."""
        if self.running:
            return
        self.running = True
        self.logger.info("[SCANNER] Opportunity scanning started")
        self._scan_task = asyncio.create_task(self._scanning_loop())

    async def stop(self) -> None:
        """Stop the scanning process."""
        self.running = False
        if self._scan_task:
            self._scan_task.cancel()
        self.logger.info("[SCANNER] Opportunity scanning stopped")

    async def scan_once(self) -> List[Dict[str, Any]]:
        """Perform a single scan for opportunities without waiting."""
        try:
            self.logger.info("[SCANNER] Performing single opportunity scan...")
            opportunities = await self.scan_opportunities()
            if opportunities:
                self.logger.info(f"[SCANNER] Single scan found {len(opportunities)} opportunities")
                self.found_opportunities = opportunities
            return opportunities
        except Exception as e:
            self.logger.error(f"[SCANNER] Error in single scan: {e}")
            return []

    async def _scanning_loop(self) -> None:
        """Main scanning loop - continuously scan for opportunities."""
        # Perform immediate scan on startup
        try:
            self.logger.info("[SCANNER] Performing initial opportunity scan...")
            opportunities = await self.scan_opportunities()
            if opportunities:
                self.logger.info(f"[SCANNER] Initial scan found {len(opportunities)} opportunities")
        except Exception as e:
            self.logger.error(f"[SCANNER] Error in initial scan: {e}")

        while self.running:
            try:
                # Wait for scan interval
                await asyncio.sleep(self.scan_interval)

                # Don't scan too frequently
                current_time = time.time()
                if current_time - self._last_scan_time < self.scan_interval:
                    continue

                self._last_scan_time = current_time

                # Scan for opportunities
                opportunities = await self.scan_opportunities()

                if opportunities:
                    self.logger.info(f"[SCANNER] Found {len(opportunities)} opportunities in scan")
                    # Store opportunities for retrieval
                    self.found_opportunities = opportunities

            except asyncio.CancelledError:
                self.logger.info("[SCANNER] Scanning loop cancelled.")
                break
            except Exception as e:
                self.logger.error(f"[SCANNER] Error in scan loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def scan_opportunities(self) -> List[Dict[str, Any]]:
        """
        Scan all symbols for trading opportunities.
        
        Returns:
            List of opportunity dictionaries with trading signals
        """
        opportunities = []

        try:
            # Check capital deployment state periodically if enabled
            if self.capital_deployment_enabled:
                current_time = time.time()
                if current_time - self.last_deployment_check > self.deployment_check_interval:
                    deployment_status = await self._check_capital_deployment()
                    self.last_deployment_check = current_time

                    if self.log_deployment_status:
                        if deployment_status['fully_deployed']:
                            self.logger.info(f"[SCANNER] CAPITAL FULLY DEPLOYED ({deployment_status['deployment_percentage']:.1f}%) - "
                                           f"Available: ${deployment_status['available_usdt']:.2f} - EXIT-ONLY MODE ACTIVE")
                        else:
                            self.logger.info(f"[SCANNER] CAPITAL AVAILABLE - Deployment: {deployment_status['deployment_percentage']:.1f}% - "
                                            f"Available: ${deployment_status['available_usdt']:.2f} - ACTIVELY SEEKING OPPORTUNITIES")

            # Log scan start with deployment status
            mode = "EXIT-ONLY MODE" if self.capital_deployed_state else "FULL TRADING MODE"
            self.logger.info(f"[SCANNER] Scanning {len(self.symbols)} symbols for opportunities in {mode}")
            self.logger.debug(f"[SCANNER] Symbols to scan: {self.symbols}")

            # CRITICAL: In EXIT-ONLY mode, prioritize checking held positions
            if self.capital_deployed_state:
                # First, get all held positions to ensure we generate sell signals
                self.logger.info("[SCANNER] EXIT-ONLY MODE: Checking all held positions first")
                held_positions = await self._get_all_held_positions()
                if held_positions:
                    self.logger.info(f"[SCANNER] Found {len(held_positions)} held positions to check for exit")
                    # Add any held position symbols that aren't in our scan list
                    for asset, amount in held_positions.items():
                        symbol = f"{asset}/USDT"
                        if symbol not in self.symbols and amount > 0.0001:
                            self.logger.info(f"[SCANNER] Adding held position {symbol} to scan list")
                            self.symbols.append(symbol)

            # Track scan progress
            symbols_processed = 0
            symbols_with_data = 0

            # Get current market data for all symbols
            for symbol in self.symbols:
                try:
                    # Check if we have ticker data
                    ticker_data = await self._get_ticker_data(symbol)
                    if ticker_data and ticker_data.get('last', 0) > 0:
                        symbols_with_data += 1

                    opportunity = await self._analyze_symbol(symbol)
                    symbols_processed += 1

                    if opportunity:
                        opportunities.append(opportunity)
                        self.logger.info(f"[SCANNER] Found opportunity: {symbol} {opportunity.get('side')} conf={opportunity.get('confidence', 0):.2f}")

                except Exception as e:
                    self.logger.debug(f"[SCANNER] Error analyzing {symbol}: {e}")
                    symbols_processed += 1
                    continue

            # Log scan summary with mode
            mode_str = "[EXIT-ONLY]" if self.capital_deployed_state else "[FULL-TRADING]"
            self.logger.info(f"[SCANNER] {mode_str} Scan complete: {symbols_processed}/{len(self.symbols)} symbols processed, "
                           f"{symbols_with_data} with data, {len(opportunities)} opportunities found")

            # Sort by confidence and profit potential
            # CRITICAL: Prioritize SELL signals when capital is fully deployed
            if self.capital_deployment_enabled and self.capital_deployed_state and self.prioritize_exits_when_deployed:
                # Put sell signals first when fully deployed
                sell_opportunities = [o for o in opportunities if o.get('side') == 'sell']
                buy_opportunities = [o for o in opportunities if o.get('side') == 'buy']

                # Sort each group by confidence
                sell_opportunities.sort(key=lambda x: (x.get('confidence', 0), x.get('profit_potential', 0)), reverse=True)
                buy_opportunities.sort(key=lambda x: (x.get('confidence', 0), x.get('profit_potential', 0)), reverse=True)

                # Combine with sells first
                opportunities = sell_opportunities + buy_opportunities

                if sell_opportunities:
                    self.logger.info(f"[SCANNER] Capital deployed - prioritizing {len(sell_opportunities)} SELL signals")
            else:
                opportunities.sort(
                    key=lambda x: (x.get('confidence', 0), x.get('profit_potential', 0)),
                    reverse=True
                )

            # Return top opportunities
            return opportunities[:self.max_opportunities_per_scan]

        except Exception as e:
            self.logger.error(f"[SCANNER] Error in scan_opportunities: {e}")
            return []

    async def _analyze_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a single symbol for trading opportunities.
        PORTFOLIO-AWARE: Checks existing positions and generates SELL signals for held assets,
        BUY signals for new opportunities.
        
        Args:
            symbol: Trading symbol to analyze
            
        Returns:
            Opportunity dictionary if found, None otherwise
        """
        try:
            # Get market data
            ticker_data = await self._get_ticker_data(symbol)
            if not ticker_data:
                # Log data availability for troubleshooting
                self.logger.debug(f"[SCANNER] No ticker data available for {symbol}")
                return None

            current_price = float(ticker_data.get('last', 0))
            if current_price <= 0:
                return None

            # CRITICAL: Check if we already hold this asset
            base_asset = symbol.split('/')[0]  # Extract base currency (e.g., BTC from BTC/USD)
            holds_position = await self._check_existing_position(base_asset)

            # Log scanning progress for monitoring (limited to avoid spam)
            if self.symbols.index(symbol) < 3 or self.symbols.index(symbol) == len(self.symbols) - 1:
                position_status = "HELD" if holds_position else "AVAILABLE"
                self.logger.info(f"[SCANNER] [{self.symbols.index(symbol)+1}/{len(self.symbols)}] {symbol} - Price: ${current_price:.2f}, Status: {position_status}")

            # Add general scan progress logging
            self.logger.debug(f"[SCANNER] Analyzing {symbol}: price=${current_price:.6f}, holds={holds_position}")

            # Get technical indicators if available
            rsi = await self._get_rsi(symbol)
            volume_ratio = await self._get_volume_ratio(symbol)

            # Log technical indicators for first symbol to monitor data quality
            if self.symbols.index(symbol) == 0:
                self.logger.debug(f"[SCANNER] Technical indicators for {symbol} - RSI: {rsi:.2f}, Volume Ratio: {volume_ratio:.2f}")

            # [TARGET] PORTFOLIO-AWARE SIGNAL GENERATION
            opportunity = None

            if holds_position:
                # [PROFIT] WE HOLD THIS ASSET - GENERATE SELL SIGNALS FOR PROFIT TAKING
                # First verify we actually have a meaningful position
                position_amount = 0
                try:
                    if hasattr(self.bot, 'balance_manager') and self.bot.balance_manager:
                        position_amount = await self.bot.balance_manager.get_balance_for_asset(base_asset)

                        # CRITICAL FIX: If balance manager returns 0, check exchange directly
                        if position_amount <= 0.0001 and hasattr(self.bot, 'exchange') and self.bot.exchange:
                            self.logger.info(f"[SCANNER] Balance manager returned 0 for {base_asset}, checking exchange")
                            exchange_balance = await self.bot.exchange.fetch_balance()
                            if isinstance(exchange_balance, dict):
                                # Check total balance (free + used)
                                total_dict = exchange_balance.get('total', {})
                                for key in [base_asset, base_asset.upper(), base_asset.lower()]:
                                    if key in total_dict:
                                        position_amount = float(total_dict[key])
                                        if position_amount > 0:
                                            self.logger.info(f"[SCANNER] Found {base_asset} from exchange: {position_amount:.8f}")
                                            break
                except Exception as e:
                    self.logger.debug(f"[SCANNER] Error checking position amount: {e}")

                # Skip sell signal if position is too small (dust) or zero
                # Calculate position value in USD
                position_value = position_amount * current_price
                min_trade_value = 1.0  # $1 minimum to avoid dust trades

                # CRITICAL: In EXIT-ONLY mode OR if we have a valid position, generate sell signal
                if (self.capital_deployed_state and holds_position) or position_value >= min_trade_value:
                    # For EXIT-ONLY mode with 0 balance, assume minimum position
                    if position_value < min_trade_value and self.capital_deployed_state:
                        self.logger.info(f"[SCANNER] EXIT-ONLY MODE: Forcing sell signal for known held {base_asset}")
                        position_value = min(3.5, self.bot.config.get('tier_1_trade_limit', 3.5))  # Use config tier limit
                        position_amount = position_value / current_price

                    self.logger.info(f"[SCANNER] {symbol} - We hold {base_asset} ({position_amount:.8f} worth ${position_value:.2f}), generating SELL signal")

                    # CRITICAL: Always generate sell signals for held positions
                    mode_str = "[EXIT-ONLY]" if self.capital_deployed_state else "[FULL-TRADING]"

                    # Generate sell signal for any held position
                    sell_confidence = 0.85
                    profit_potential = 0.015  # 1.5% profit target

                    opportunity = {
                        'symbol': symbol,
                        'signal_type': 'exit_only_sell' if self.capital_deployed_state else 'position_exit',
                        'side': 'sell',
                        'action': 'sell',  # For compatibility
                        'price': current_price,
                        'confidence': sell_confidence,
                        'profit_potential': profit_potential,
                        'reason': f'{mode_str} Liquidate held {base_asset} position',
                        'timestamp': time.time(),
                        'priority': 'high'  # Always high priority for exits
                    }
                    price_str = f"{current_price:.8f}" if current_price < 0.01 else f"{current_price:.2f}"
                    self.logger.info(f"[SCANNER] {mode_str} SELL signal generated for held {base_asset} at ${price_str}")
                    self.logger.info(f"[SCANNER] Generated sell opportunity: {opportunity}")
                    return opportunity  # CRITICAL FIX: Return the sell opportunity immediately

            else:
                # [BUY] WE DON'T HOLD THIS ASSET - GENERATE BUY SIGNALS FOR NEW OPPORTUNITIES
                # CRITICAL: Check if we have capital available before generating buy signals
                if self.capital_deployment_enabled and self.capital_deployed_state:
                    self.logger.debug(f"[SCANNER] {symbol} - Capital fully deployed, skipping BUY signal generation")
                    return None

                self.logger.debug(f"[SCANNER] {symbol} - We don't hold {base_asset}, checking for BUY opportunities")

                # Mean reversion opportunity (oversold) - good for buying
                if rsi and rsi < 45:  # More aggressive threshold for micro-scalping
                    confidence = 0.9 if rsi < 30 else 0.8 if rsi < 35 else 0.7
                    profit_potential = 0.005  # 0.5% profit target for quick trades

                    # Check for rapid-fire mode
                    if self.rapid_fire_mode and symbol in self.rapid_fire_symbols:
                        # Boost confidence for rapid-fire symbols
                        confidence = min(confidence * 1.2, 0.95)
                        # Track consecutive trades
                        self.rapid_fire_history.setdefault(symbol, 0)
                        if self.rapid_fire_history[symbol] < self.max_consecutive:
                            profit_potential = self.rapid_fire_threshold  # Use rapid-fire threshold
                            self.logger.info(f"[SCANNER] RAPID-FIRE opportunity on {symbol}")

                    opportunity = {
                        'symbol': symbol,
                        'signal_type': 'mean_reversion',
                        'side': 'buy',
                        'action': 'buy',  # For compatibility
                        'price': current_price,
                        'confidence': confidence,
                        'profit_potential': profit_potential,
                        'reason': f'BUY - RSI oversold at {rsi:.1f}',
                        'timestamp': time.time()
                    }
                    self.logger.info(f"[SCANNER] [EMOJI] Mean reversion BUY signal for {base_asset} - RSI {rsi:.1f}")

                # Volume spike opportunity
                elif volume_ratio and volume_ratio > 2.0:
                    confidence = 0.75
                    profit_potential = 0.015  # 1.5%

                    opportunity = {
                        'symbol': symbol,
                        'signal_type': 'volume_breakout',
                        'side': 'buy',
                        'action': 'buy',  # For compatibility
                        'price': current_price,
                        'confidence': confidence,
                        'profit_potential': profit_potential,
                        'reason': f'BUY - Volume spike {volume_ratio:.1f}x average',
                        'timestamp': time.time()
                    }
                    self.logger.info(f"[SCANNER] [EMOJI] Volume breakout BUY signal for {base_asset}")

                # Check for micro-profit opportunities (fee-free advantage)
                elif rsi and 45 < rsi < 55:  # Near neutral, good for scalping
                    bid_ask_spread = await self._get_bid_ask_spread(symbol)
                    if bid_ask_spread and bid_ask_spread > 0.003:  # 0.3% spread
                        confidence = 0.65
                        profit_potential = bid_ask_spread * 0.7  # Capture 70% of spread

                        opportunity = {
                            'symbol': symbol,
                            'signal_type': 'scalping',
                            'side': 'buy',
                            'action': 'buy',  # For compatibility
                            'price': current_price,
                            'confidence': confidence,
                            'profit_potential': profit_potential,
                            'reason': f'BUY - Spread arbitrage {bid_ask_spread*100:.2f}%',
                            'timestamp': time.time()
                        }
                        self.logger.info(f"[SCANNER] [EMOJI] Scalping BUY signal for {base_asset}")

                # FALLBACK: Basic micro-scalping opportunity (always generate signals)
                if not opportunity and current_price > 0:
                    # Use simple price-based opportunity detection
                    confidence = 0.60  # Base confidence for micro-scalping
                    profit_potential = 0.005  # 0.5% profit target

                    # Check momentum even without RSI
                    momentum_check = await self._check_simple_momentum(symbol, current_price)

                    # Debug log momentum check
                    self.logger.debug(f"[SCANNER] {symbol} momentum: {momentum_check:.4f}")

                    # Adjusted threshold per CLAUDE.md (0.1% = 0.001)
                    if momentum_check > 0.001:  # 0.1% positive momentum
                        confidence += 0.10  # Increased boost for positive momentum
                        self.logger.debug(f"[SCANNER] {symbol} positive momentum detected, boosting confidence")

                    opportunity = {
                        'symbol': symbol,
                        'signal_type': 'micro_scalping',
                        'side': 'buy',
                        'action': 'buy',  # For compatibility
                        'price': current_price,
                        'confidence': confidence,
                        'profit_potential': profit_potential,
                        'reason': f'Micro-scalping BUY opportunity at ${current_price:.8f}' if current_price < 0.01 else f'Micro-scalping BUY opportunity at ${current_price:.2f}',
                        'timestamp': time.time()
                    }
                    price_str = f"{current_price:.8f}" if current_price < 0.01 else f"{current_price:.2f}"
                    self.logger.info(f"[SCANNER] [SIGNAL_FOUND] BUY signal for new {base_asset} at ${price_str} conf={confidence}")

            # Log when we decide not to generate a signal
            if not opportunity:
                self.logger.debug(f"[SCANNER] No opportunity found for {symbol} - RSI: {rsi}, holds: {holds_position}")

            return opportunity

        except Exception as e:
            self.logger.debug(f"[SCANNER] Error analyzing {symbol}: {e}")
            return None

    async def _get_all_held_positions(self) -> Dict[str, float]:
        """
        Get all held positions from balance manager and exchange.
        
        Returns:
            Dict[str, float]: Dictionary of asset -> amount
        """
        try:
            held_positions = {}

            # Method 1: Check balance manager
            if hasattr(self.bot, 'balance_manager') and self.bot.balance_manager:
                try:
                    all_balances = await self.bot.balance_manager.get_all_balances()
                    for asset, balance in all_balances.items():
                        if asset not in ['USDT', 'USD', 'EUR'] and balance > 0.0001:
                            held_positions[asset] = balance
                            self.logger.info(f"[SCANNER] Balance manager shows {asset}: {balance:.8f}")
                except Exception as e:
                    self.logger.debug(f"[SCANNER] Error getting balances from manager: {e}")

            # Method 2: Check exchange directly if balance manager has no data
            if not held_positions and hasattr(self.bot, 'exchange') and self.bot.exchange:
                try:
                    exchange_balance = await self.bot.exchange.fetch_balance()
                    if isinstance(exchange_balance, dict):
                        # Check total balance
                        total_dict = exchange_balance.get('total', {})
                        for asset, balance in total_dict.items():
                            if asset not in ['USDT', 'USD', 'EUR'] and balance > 0.0001:
                                held_positions[asset] = balance
                                self.logger.info(f"[SCANNER] Exchange shows {asset}: {balance:.8f}")
                except Exception as e:
                    self.logger.debug(f"[SCANNER] Error getting exchange balance: {e}")

            return held_positions

        except Exception as e:
            self.logger.error(f"[SCANNER] Error getting all held positions: {e}")
            return {}

    async def _check_existing_position(self, base_asset: str) -> bool:
        """
        Check if we currently hold a position in the given asset.
        
        Args:
            base_asset: The base currency to check (e.g., 'BTC', 'ETH')
            
        Returns:
            bool: True if we hold a position, False otherwise
        """
        try:
            # Check cache first
            current_time = time.time()
            if (base_asset in self._balance_cache and
                current_time - self._balance_cache_time < self._balance_cache_ttl):
                balance = self._balance_cache[base_asset]
                return balance > 0.0001

            # Simple check via unified balance manager
            if hasattr(self.bot, 'balance_manager') and self.bot.balance_manager:
                balance = await self.bot.balance_manager.get_balance_for_asset(base_asset)

                # CRITICAL FIX: Also check exchange directly if balance manager returns 0
                if balance <= 0.0001 and hasattr(self.bot, 'exchange') and self.bot.exchange:
                    try:
                        # Get fresh balance from exchange
                        self.logger.info(f"[POSITION_CHECK] Balance manager returned 0 for {base_asset}, checking exchange directly")
                        exchange_balance = await self.bot.exchange.fetch_balance()
                        if isinstance(exchange_balance, dict):
                            # Check for the asset in various formats
                            for key in [base_asset, base_asset.upper(), base_asset.lower()]:
                                if key in exchange_balance:
                                    balance = float(exchange_balance[key].get('free', 0) + exchange_balance[key].get('used', 0))
                                    if balance > 0:
                                        self.logger.info(f"[POSITION_CHECK] Found {base_asset} balance from exchange: {balance:.8f}")
                                        break
                    except Exception as e:
                        self.logger.debug(f"[POSITION_CHECK] Error checking exchange balance: {e}")

                # Update cache
                self._balance_cache[base_asset] = balance
                self._balance_cache_time = current_time

                if balance > 0.0001:  # Small threshold to ignore dust
                    self.logger.info(f"[POSITION_CHECK] Holds {base_asset}: {balance:.8f}")
                    return True
                return False

            # Method 2: Check via portfolio analysis (fallback)
            elif hasattr(self.bot, 'enhanced_balance_manager') and self.bot.enhanced_balance_manager:
                try:
                    portfolio = await self.bot.enhanced_balance_manager.analyze_portfolio()
                    deployed_assets = portfolio.get('deployed_assets', [])

                    for asset_info in deployed_assets:
                        if asset_info.get('asset') == base_asset and asset_info.get('amount', 0) > 0.0001:
                            self.logger.debug(f"[POSITION_CHECK] Portfolio holds {base_asset}: {asset_info.get('amount', 0):.8f}")
                            return True
                except Exception as e:
                    self.logger.debug(f"[POSITION_CHECK] Error checking portfolio for {base_asset}: {e}")

            # Method 3: Check via exchange balance (fallback)
            elif hasattr(self.bot, 'exchange') and self.bot.exchange:
                try:
                    balance_info = await self.bot.exchange.fetch_balance()
                    if balance_info and base_asset in balance_info:
                        if isinstance(balance_info[base_asset], dict):
                            balance = float(balance_info[base_asset].get('free', 0))
                        else:
                            balance = float(balance_info[base_asset])

                        if balance > 0.0001:  # Small threshold to ignore dust
                            self.logger.debug(f"[POSITION_CHECK] Exchange holds {base_asset}: {balance:.8f}")
                            return True
                except Exception as e:
                    self.logger.debug(f"[POSITION_CHECK] Error checking exchange balance for {base_asset}: {e}")

            # No position found
            self.logger.debug(f"[POSITION_CHECK] No position in {base_asset}")
            return False

        except Exception as e:
            self.logger.error(f"[POSITION_CHECK] Error checking position for {base_asset}: {e}")
            return False

    async def _get_ticker_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data for a symbol from WebSocket feed."""
        try:
            # First check if we have real-time ticker data from WebSocket
            if self.bot and hasattr(self.bot, 'websocket_manager') and self.bot.websocket_manager:
                ws_manager = self.bot.websocket_manager

                # Check multiple locations for ticker data
                ticker_data = None

                # Check WebSocket V2 get_ticker method first
                if hasattr(ws_manager, 'get_ticker'):
                    ticker_data = ws_manager.get_ticker(symbol)
                    if ticker_data:
                        self.logger.debug(f"[SCANNER] Found ticker via get_ticker for {symbol}")
                        return ticker_data

                # Check current_tickers (compatibility property)
                if hasattr(ws_manager, 'current_tickers') and symbol in ws_manager.current_tickers:
                    ticker_data = ws_manager.current_tickers[symbol]
                    self.logger.debug(f"[SCANNER] Found ticker in current_tickers for {symbol}")
                    return ticker_data

                # Check ticker_data directly (V2 storage)
                if hasattr(ws_manager, 'ticker_data'):
                    standard_symbol = symbol.replace('/', '_')
                    if standard_symbol in ws_manager.ticker_data:
                        ticker_data = ws_manager.ticker_data[standard_symbol]
                        self.logger.debug(f"[SCANNER] Found ticker in ticker_data for {symbol}")
                        return ticker_data

                # Check direct WebSocket fallback if available
                if hasattr(ws_manager, 'direct_websocket') and ws_manager.direct_websocket:
                    fallback_ticker = ws_manager.direct_websocket.get_ticker(symbol)
                    if fallback_ticker:
                        self.logger.debug(f"[SCANNER] Found ticker via direct WebSocket fallback for {symbol}")
                        return fallback_ticker

                # Check last_price_update (old compatibility)
                elif hasattr(ws_manager, 'last_price_update') and symbol in ws_manager.last_price_update:
                    ticker = ws_manager.last_price_update[symbol]
                    self.logger.debug(f"[SCANNER] Found ticker in last_price_update for {symbol}: ${ticker.get('price', 0):.2f}")
                    # Return in the expected format
                    return {
                        'symbol': symbol,
                        'last': ticker.get('price', 0),
                        'bid': ticker.get('bid', 0),
                        'ask': ticker.get('ask', 0),
                        'high': ticker.get('high', 0),
                        'low': ticker.get('low', 0),
                        'volume': ticker.get('volume', 0),
                        'percentage': 0  # WebSocket doesn't provide percentage
                    }
                else:
                    # Debug log what's available
                    if ws_manager:
                        self.logger.debug(f"[SCANNER] WebSocket data not found for {symbol}. Available: current_tickers={hasattr(ws_manager, 'current_tickers')}, last_price_update={hasattr(ws_manager, 'last_price_update')}")

            # Fallback: Try to get from exchange if available
            if self.exchange_client:
                try:
                    self.logger.debug(f"[SCANNER] Using fallback ticker fetch for {symbol}")
                    ticker = await self.exchange_client.fetch_ticker(symbol)
                    if ticker:
                        self.logger.debug(f"[SCANNER] Got ticker for {symbol}: last=${ticker.get('last', 0):.2f}")
                        return ticker
                except Exception as e:
                    self.logger.debug(f"[SCANNER] Fallback ticker fetch failed for {symbol}: {e}")

            self.logger.debug(f"[SCANNER] No ticker data available for {symbol}")
            return None

        except Exception as e:
            self.logger.debug(f"[SCANNER] Error getting ticker for {symbol}: {e}")
            return None

    async def _get_rsi(self, symbol: str) -> Optional[float]:
        """Get RSI indicator for a symbol."""
        try:
            # Get from strategy manager if available
            if hasattr(self.bot.components, 'strategy_manager'):
                strategy = getattr(self.bot.components.strategy_manager, 'active_strategies', {}).get(symbol)
                if strategy and hasattr(strategy, 'latest_indicators'):
                    indicators = strategy.latest_indicators
                    if indicators and 'rsi' in indicators:
                        return float(indicators['rsi'])

            # Try to get from real-time data store
            if hasattr(self.bot.components, 'real_time_data_store'):
                indicators = self.bot.components.real_time_data_store.get_latest_indicators(symbol)
                if indicators and 'rsi' in indicators:
                    return float(indicators['rsi'])

            return None

        except Exception as e:
            self.logger.debug(f"[SCANNER] Error getting RSI for {symbol}: {e}")
            return None

    async def _get_volume_ratio(self, symbol: str) -> Optional[float]:
        """Get volume ratio (current vs average) for a symbol."""
        try:
            # Get from real-time data store
            if hasattr(self.bot.components, 'real_time_data_store'):
                latest_candle = self.bot.components.real_time_data_store.get_latest_candle(symbol)
                if latest_candle and 'volume' in latest_candle:
                    current_volume = float(latest_candle['volume'])

                    # Get average volume
                    candles = self.bot.components.real_time_data_store.get_candles(symbol, limit=20)
                    if candles and len(candles) > 5:
                        avg_volume = sum(float(c.get('volume', 0)) for c in candles[:-1]) / (len(candles) - 1)
                        if avg_volume > 0:
                            return current_volume / avg_volume

            return None

        except Exception as e:
            self.logger.debug(f"[SCANNER] Error getting volume ratio for {symbol}: {e}")
            return None

    async def _check_simple_momentum(self, symbol: str, current_price: float) -> float:
        """Check simple price momentum without full indicators."""
        try:
            # Check if we have recent price history in ticker cache
            if symbol in self._ticker_cache:
                cached_data, cache_time = self._ticker_cache[symbol]
                if time.time() - cache_time < 60:  # Within last minute
                    old_price = cached_data.get('last', current_price)
                    if old_price > 0:
                        momentum = (current_price - old_price) / old_price
                        return momentum

            # Update cache with current price
            self._ticker_cache[symbol] = ({'last': current_price}, time.time())
            return 0.0

        except Exception as e:
            self.logger.debug(f"[SCANNER] Error checking momentum for {symbol}: {e}")
            return 0.0

    async def _get_bid_ask_spread(self, symbol: str) -> Optional[float]:
        """Get bid-ask spread percentage for a symbol."""
        try:
            if hasattr(self.bot, 'exchange') and self.bot.exchange:
                orderbook = await self.bot.exchange.fetch_order_book(symbol, limit=5)

                if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                    if orderbook['bids'] and orderbook['asks']:
                        best_bid = float(orderbook['bids'][0][0])
                        best_ask = float(orderbook['asks'][0][0])

                        if best_bid > 0:
                            spread = (best_ask - best_bid) / best_bid
                            return spread

            return None

        except Exception as e:
            self.logger.debug(f"[SCANNER] Error getting spread for {symbol}: {e}")
            return None

    def process_ticker_data(self, symbol: str, data: Any) -> None:
        """Process ticker data for opportunity detection.
        
        Args:
            symbol: Trading symbol
            data: Ticker data
        """
        try:
            # Update cache
            self._ticker_cache[f"ticker_{symbol}"] = (data, time.time())

        except Exception as e:
            self.logger.debug(f"[SCANNER] Error processing ticker for {symbol}: {e}")

    async def scan_for_opportunities(self) -> List[Dict[str, Any]]:
        """
        Scan all symbols for trading opportunities.
        
        Returns:
            List of trading signals with structure:
            {
                'symbol': str,
                'action': 'buy',
                'price': float,
                'confidence': float (0-1),
                'reason': str
            }
        """
        # First, try to use the new scanning method
        if hasattr(self, 'found_opportunities') and self.found_opportunities:
            # Return and clear the found opportunities
            opportunities = self.found_opportunities.copy()
            self.found_opportunities = []
            return opportunities

        # Otherwise, do a direct scan
        return await self.scan_opportunities()

    async def check_liquidation_opportunities(self, target_symbol: str, needed_amount: float) -> List[Dict[str, Any]]:
        """
        CRITICAL: Identify which positions should be liquidated to enable new opportunities.
        This enables the bot to sell existing positions when a better opportunity arises.
        
        Args:
            target_symbol: The new opportunity we want to trade
            needed_amount: How much quote currency we need
            
        Returns:
            List of liquidation recommendations
        """
        try:
            if not hasattr(self.bot, 'enhanced_balance_manager') or not self.bot.enhanced_balance_manager:
                return []

            balance_manager = self.bot.enhanced_balance_manager

            # Get portfolio analysis
            # Use analyze_portfolio instead of non-existent analyze_portfolio_deployment
            portfolio_analysis = await balance_manager.analyze_portfolio()
            deployed_assets = portfolio_analysis.get('deployed_assets', [])

            liquidation_candidates = []
            quote_currency = target_symbol.split('/')[1]
            target_base = target_symbol.split('/')[0]

            for asset_info in deployed_assets:
                asset = asset_info['asset']
                value_usd = asset_info['value_usd']

                # Skip the target asset we want to buy
                if asset == target_base:
                    continue

                # Only consider significant positions
                if value_usd >= needed_amount * 0.5:
                    liquidation_candidates.append({
                        'asset': asset,
                        'symbol': f"{asset}/{quote_currency}",
                        'current_value': value_usd,
                        'action': 'sell',
                        'reason': f'Liquidate {asset} (${value_usd:.2f}) to fund {target_symbol} opportunity',
                        'priority': value_usd,  # Higher value = higher priority
                        'confidence': 0.9,  # High confidence for liquidation
                        'type': 'liquidation'
                    })

            # Sort by priority (value) - liquidate largest positions first
            liquidation_candidates.sort(key=lambda x: x['priority'], reverse=True)

            if liquidation_candidates:
                self.logger.info(f"[LIQUIDATION_SCANNER] Found {len(liquidation_candidates)} liquidation opportunities for {target_symbol}")

            return liquidation_candidates

        except Exception as e:
            self.logger.error(f"[LIQUIDATION_SCANNER] Error checking liquidation opportunities: {e}")
            return []

    async def _check_capital_deployment(self) -> Dict[str, Any]:
        """
        Check current capital deployment state and determine if we can trade.
        
        Returns:
            Dict with deployment status:
            - 'fully_deployed': bool - True if capital is fully deployed
            - 'available_usdt': float - Available USDT amount
            - 'deployment_percentage': float - Percentage of capital deployed
            - 'can_trade': bool - Whether we have enough capital to trade
        """
        try:
            # Get available USDT balance
            available_usdt = 0.0
            total_portfolio_value = 0.0

            # Method 1: Use balance manager if available
            if hasattr(self.bot, 'balance_manager') and self.bot.balance_manager:
                available_usdt = await self.bot.balance_manager.get_balance_for_asset('USDT')
                # Get total portfolio value for deployment percentage
                if hasattr(self.bot.balance_manager, 'get_total_portfolio_value'):
                    total_portfolio_value = await self.bot.balance_manager.get_total_portfolio_value()

            # Method 2: Use enhanced balance manager
            elif hasattr(self.bot, 'enhanced_balance_manager') and self.bot.enhanced_balance_manager:
                try:
                    portfolio = await self.bot.enhanced_balance_manager.analyze_portfolio()
                    available_usdt = portfolio.get('available_quote', 0.0)
                    total_portfolio_value = portfolio.get('total_value_usd', 0.0)
                except Exception as e:
                    self.logger.debug(f"[CAPITAL_CHECK] Error getting from enhanced balance manager: {e}")

            # Method 3: Direct exchange query as fallback
            elif hasattr(self.bot, 'exchange') and self.bot.exchange:
                try:
                    balance_info = await self.bot.exchange.fetch_balance()
                    if balance_info and 'USDT' in balance_info:
                        if isinstance(balance_info['USDT'], dict):
                            available_usdt = float(balance_info['USDT'].get('free', 0))
                        else:
                            available_usdt = float(balance_info['USDT'])
                except Exception as e:
                    self.logger.debug(f"[CAPITAL_CHECK] Error getting from exchange: {e}")

            # Calculate deployment percentage
            deployment_percentage = 0.0
            if total_portfolio_value > 0:
                deployed_value = total_portfolio_value - available_usdt
                deployment_percentage = (deployed_value / total_portfolio_value) * 100

            # Determine if capital is fully deployed
            fully_deployed = (
                available_usdt < self.min_available_usdt or
                deployment_percentage > self.max_deployment_percentage
            )

            # Update internal state
            self.capital_deployed_state = fully_deployed

            # Can trade if we have more than minimum USDT available
            can_trade = available_usdt >= self.min_available_usdt

            return {
                'fully_deployed': fully_deployed,
                'available_usdt': available_usdt,
                'deployment_percentage': deployment_percentage,
                'can_trade': can_trade,
                'total_portfolio_value': total_portfolio_value
            }

        except Exception as e:
            self.logger.error(f"[CAPITAL_CHECK] Error checking capital deployment: {e}")
            # Default to not fully deployed on error to avoid blocking trades
            return {
                'fully_deployed': False,
                'available_usdt': 0.0,
                'deployment_percentage': 0.0,
                'can_trade': False,
                'total_portfolio_value': 0.0
            }

    async def force_capital_check(self) -> Dict[str, Any]:
        """
        Force an immediate capital deployment check.
        Useful after trades are executed.
        """
        deployment_status = await self._check_capital_deployment()
        self.last_deployment_check = time.time()
        return deployment_status
