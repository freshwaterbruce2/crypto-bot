"""
Strategy Manager - Kraken-Compliant Quick Profit Trading

Manages multiple trading strategies and coordinates signal generation.
Handles confidence formatting and strategy lifecycle management.

KRAKEN COMPLIANT OPTIMIZATIONS:
- Kraken rate limit awareness and compliance
- Proper error handling for Kraken-specific errors
- Order validation against Kraken minimums
- Symbol format validation (BTC/USD style)
- Authentication token management
- Fee-free trading advantage with 0.5-1% profit targets

Key Features:
- Multi-strategy coordination optimized for quick profits
- Kraken WebSocket v2 API compliance
- Proper confidence value formatting (0.85 -> 85%)
- Buy/Sell separation architecture with aggressive settings
- Real-time OHLC data distribution
- Kraken rate limit monitoring and management
- Strategy performance tracking
"""

import asyncio
import time
import traceback
from typing import Any, Optional

# Import strategy components
from src.strategies.base_strategy import BaseStrategy
from src.strategies.fast_start_strategy import FastStartStrategy

# from ..strategies.autonomous_sell_engine import AutonomousSellEngine, SellEngineConfig  # DISABLED: Using unified sell coordinator
from src.utils.custom_logging import configure_logging
from src.utils.kraken_order_validator import KrakenOrderValidator

# Import Kraken helpers
from src.utils.kraken_rl import KrakenRateLimiter as KrakenRateLimitManager

logger = configure_logging()



class FunctionalStrategyManager:
    """
    Kraken-compliant strategy manager for quick profit trading.

    KRAKEN COMPLIANCE FEATURES:
    - Rate limit awareness and management
    - Order validation against Kraken minimums
    - Proper error handling for Kraken-specific errors
    - Symbol format validation (BTC/USD style)
    - WebSocket v2 API compliance

    TRADING OPTIMIZATION:
    - Aggressive 0.5% profit targets for "snowball effect"
    - Lower confidence thresholds for more trading opportunities
    - Faster signal generation and execution
    - Tight risk management with 0.8% stop losses
    - Multiple concurrent positions for maximum output
    """

    def __init__(self, bot=None, kraken_tier: str = "intermediate"):
        """
        Initialize the Kraken-compliant strategy manager.

        Args:
            bot: Reference to the main bot instance
            kraken_tier: Kraken account tier (starter, intermediate, pro)
        """
        self.bot = bot
        self.strategies = {}  # symbol -> strategy instance
        # self.sell_engines = {}  # symbol -> sell engine instance  # DISABLED: Using unified sell coordinator
        self.active_strategies = []
        self.last_ohlc_update = {}
        self._pending_signals = []  # Store pending signals for execution

        # Historical data cache for strategy warm-up
        self.price_history = {}  # symbol -> historical OHLC data
        self.historical_data_provided = False

        # Kraken compliance components
        self.rate_limit_manager = KrakenRateLimitManager(kraken_tier)
        self.order_validator = KrakenOrderValidator()

        # Performance metrics
        self.performance_metrics = {
            "signals_generated": 0,
            "signals_executed": 0,
            "signals_blocked_by_rate_limit": 0,
            "signals_failed_validation": 0,
            "strategies_active": 0,
            "last_signal_time": None,
            "kraken_errors": 0
        }

        # Kraken error handling
        self.kraken_error_handlers = {
            "EOrder:Rate limit exceeded": self._handle_rate_limit_error,
            "EOrder:Order minimum not met": self._handle_order_minimum_error,
            "EOrder:Cost minimum not met": self._handle_cost_minimum_error,
            "EOrder:Insufficient funds": self._handle_insufficient_funds_error,
            "EGeneral:Invalid arguments": self._handle_invalid_arguments_error
        }

        logger.info(f"[STRATEGY_MANAGER] Initialized Kraken-compliant manager for {kraken_tier} tier")

    def set_historical_data(self, historical_data: dict[str, list[list]]):
        """
        Set historical OHLCV data for strategy warm-up.

        Args:
            historical_data: Dict mapping symbol to OHLCV data
        """
        try:
            self.price_history = historical_data
            self.historical_data_provided = True
            logger.info(f"[STRATEGY_MANAGER] Set historical data for {len(historical_data)} symbols")

            # Log sample counts
            for symbol, data in historical_data.items():
                if data:
                    logger.debug(f"[HISTORICAL_DATA] {symbol}: {len(data)} candles available")

        except Exception as e:
            logger.error(f"[STRATEGY_MANAGER] Error setting historical data: {e}")

    async def initialize_strategies(self, symbols: list[str], config: dict[str, Any]):
        """
        Initialize Kraken-compliant strategies for the given symbols.

        Args:
            symbols: List of trading symbols (must be Kraken v2 format: BTC/USD)
            config: Configuration dictionary
        """
        try:
            # Validate symbol formats for Kraken v2 compliance
            validated_symbols = self._validate_kraken_symbols(symbols)

            for symbol in validated_symbols:
                # Initialize buy strategy (FastStartStrategy)
                buy_strategy = await self._create_buy_strategy(symbol, config)
                if buy_strategy:
                    self.strategies[symbol] = buy_strategy
                    self.active_strategies.append(symbol)
                    logger.info(f"[STRATEGY_INIT] {symbol}: Kraken-compliant buy strategy initialized")

                # # Initialize sell engine (AutonomousSellEngine)  # DISABLED: Using unified sell coordinator
                # sell_engine = await self._create_sell_engine(symbol, config)
                # if sell_engine:
                #     self.sell_engines[symbol] = sell_engine
                #     logger.info(f"[STRATEGY_INIT] {symbol}: Kraken-compliant sell engine initialized")

            self.performance_metrics["strategies_active"] = len(self.active_strategies)
            logger.info(
                f"[STRATEGY_MANAGER] Initialized {len(self.strategies)} buy strategies "
                # f"and {len(self.sell_engines)} sell engines for Kraken trading"  # DISABLED: Using unified sell coordinator
                f"for Kraken trading"
            )

        except Exception as e:
            logger.error(f"[STRATEGY_MANAGER] Error initializing Kraken-compliant strategies: {e}")
            logger.error(traceback.format_exc())

    def _validate_kraken_symbols(self, symbols: list[str]) -> list[str]:
        """Validate and format symbols for Kraken v2 compliance."""
        validated = []

        for symbol in symbols:
            # Ensure BTC/USD format (not XBT/USD for v2)
            if symbol == "XBT/USD":
                symbol = "BTC/USD"
                logger.info("[SYMBOL_VALIDATION] Converted XBT/USD to BTC/USD for Kraken v2")

            # Validate format
            if "/" in symbol and len(symbol.split("/")) == 2:
                validated.append(symbol)
                logger.debug(f"[SYMBOL_VALIDATION] {symbol}: Valid Kraken v2 format")
            else:
                logger.warning(f"[SYMBOL_VALIDATION] {symbol}: Invalid format, skipping")

        return validated

    async def get_signals(self) -> list[dict[str, Any]]:
        """
        Get trading signals from all active strategies with Kraken compliance.

        KRAKEN COMPLIANCE:
        - Rate limit checking before signal generation
        - Order validation against Kraken minimums
        - Proper error handling for Kraken-specific errors

        TRADING OPTIMIZATION:
        - Lower confidence thresholds for more trading opportunities
        - Aggressive settings for "snowball effect" profit accumulation

        Returns:
            List of Kraken-compliant formatted trading signals
        """
        all_signals = []

        # AGGRESSIVE SETTINGS for maximum trading opportunities
        MIN_CONFIDENCE_THRESHOLD = 0.25  # 25% minimum (lowered for more trades)
        MAX_CONCURRENT_SIGNALS = 8       # Allow more positions for quick profits

        try:
            for symbol, strategy in self.strategies.items():
                if strategy.status != "Ready":
                    continue

                # KRAKEN COMPLIANCE: Check rate limits before generating signals
                if not self.rate_limit_manager.can_trade(symbol):
                    self.performance_metrics["signals_blocked_by_rate_limit"] += 1
                    logger.warning(f"[RATE_LIMIT] {symbol}: Skipping signal generation due to rate limits")
                    continue

                # Get signals from strategy
                signals = await strategy.generate_signals(None)

                if signals and isinstance(signals, list):
                    for signal in signals:
                        # CRITICAL FIX: Format confidence value properly
                        formatted_signal = self._format_signal(signal)
                        if formatted_signal:
                            # KRAKEN COMPLIANCE: Validate order against minimums
                            validation_result = await self._validate_signal_for_kraken(formatted_signal)

                            if not validation_result["valid"]:
                                self.performance_metrics["signals_failed_validation"] += 1
                                logger.warning(
                                    f"[VALIDATION] {symbol}: Signal failed Kraken validation: "
                                    f"{validation_result['errors']}"
                                )
                                continue

                            # AGGRESSIVE FILTERING: Accept lower confidence signals for more trades
                            signal_confidence = formatted_signal.get('confidence', 0)

                            if signal_confidence >= MIN_CONFIDENCE_THRESHOLD:
                                all_signals.append(formatted_signal)
                                logger.info(f"[SIGNAL_ACCEPTED] {symbol}: Confidence {signal_confidence:.2f} >= {MIN_CONFIDENCE_THRESHOLD}")

                                # Increment rate counter for signal generation
                                self.rate_limit_manager.increment_counter(symbol, 1)
                            else:
                                logger.warning(f"[SIGNAL_REJECTED] {symbol}: Confidence {signal_confidence:.2f} < {MIN_CONFIDENCE_THRESHOLD}")

                                # Update metrics
                                self.performance_metrics["signals_generated"] += 1
                                self.performance_metrics["last_signal_time"] = time.time()

                                # Log signal with proper confidence
                                confidence_pct = formatted_signal.get('confidence', 0) * 100
                                logger.info(
                                    f"[SIGNAL] {symbol}: {formatted_signal.get('side', 'unknown').upper()} "
                                    f"signal generated - Confidence: {confidence_pct:.0f}%, "
                                    f"Reason: {formatted_signal.get('reason', 'unknown')} "
                                    f"[KRAKEN_COMPLIANT_QUICK_PROFIT]"
                                )

            # AGGRESSIVE POSITION MANAGEMENT: Allow more concurrent positions
            if len(all_signals) > MAX_CONCURRENT_SIGNALS:
                # Sort by confidence and take the best ones
                all_signals = sorted(all_signals, key=lambda x: x['confidence'], reverse=True)[:MAX_CONCURRENT_SIGNALS]
                logger.info(f"[SIGNAL_LIMIT] Reduced signals to top {MAX_CONCURRENT_SIGNALS} for Kraken risk management")

            return all_signals

        except Exception as e:
            logger.error(f"[STRATEGY_MANAGER] Error getting Kraken-compliant signals: {e}")
            self.performance_metrics["kraken_errors"] += 1
            return []

    def _format_signal(self, signal: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Format signal for Kraken compliance and proper display.

        CRITICAL: Ensures confidence is properly formatted as decimal (0.85)
        for calculations and percentage display (85%).

        KRAKEN COMPLIANCE: Ensures signal format matches Kraken WebSocket v2 API.

        Args:
            signal: Raw signal from strategy

        Returns:
            Kraken-compliant formatted signal or None if invalid
        """
        try:
            # Validate required fields
            if not signal or not isinstance(signal, dict):
                return None

            # Handle both 'pair' and 'symbol' fields
            if 'symbol' in signal and 'pair' not in signal:
                signal['pair'] = signal['symbol']
            elif 'pair' not in signal and 'symbol' not in signal:
                logger.warning(f"[SIGNAL_FORMAT] Missing symbol/pair in signal: {signal}")
                return None

            # Handle both 'type' and 'side' fields
            if 'type' in signal and 'side' not in signal:
                signal['side'] = signal['type']
            elif 'side' not in signal and 'type' not in signal:
                logger.warning(f"[SIGNAL_FORMAT] Missing side/type in signal: {signal}")
                return None

            required_fields = ['pair', 'side', 'confidence']
            if not all(field in signal for field in required_fields):
                logger.warning(f"[SIGNAL_FORMAT] Missing required fields in signal: {signal}")
                return None

            # CRITICAL FIX: Ensure confidence is a proper decimal
            raw_confidence = signal.get('confidence', 0)

            # Handle different confidence formats
            if isinstance(raw_confidence, (int, float)):
                # If confidence is already a percentage (> 1), convert to decimal
                if raw_confidence > 1:
                    confidence_decimal = raw_confidence / 100.0
                else:
                    confidence_decimal = float(raw_confidence)
            else:
                # Default confidence if invalid
                confidence_decimal = 0.6
                logger.warning(f"[SIGNAL_FORMAT] Invalid confidence type: {type(raw_confidence)}")

            # Ensure confidence is within valid range
            confidence_decimal = max(0.0, min(1.0, confidence_decimal))

            # KRAKEN COMPLIANCE: Format signal for WebSocket v2 API
            formatted_signal = {
                'symbol': signal.get('pair', ''),  # Some strategies use 'pair'
                'pair': signal.get('pair', signal.get('symbol', '')),  # Ensure both fields
                'side': signal.get('side', '').lower(),  # Kraken expects lowercase
                'confidence': confidence_decimal,  # Store as decimal for calculations
                'confidence_pct': confidence_decimal * 100,  # Store percentage for display
                'size': signal.get('size', 0),
                'price': signal.get('price', 0),
                'reason': signal.get('reason', 'unknown'),
                'strategy': signal.get('strategy', 'unknown'),
                'timestamp': time.time(),
                'kraken_compliant': True  # Mark as Kraken validated
            }

            # Add optional fields if present
            optional_fields = ['take_profit', 'stop_loss', 'velocity', 'momentum_strength']
            for field in optional_fields:
                if field in signal:
                    formatted_signal[field] = signal[field]

            return formatted_signal

        except Exception as e:
            logger.error(f"[SIGNAL_FORMAT] Error formatting signal for Kraken: {e}")
            return None

    async def _validate_signal_for_kraken(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Validate signal against Kraken order requirements."""
        try:
            symbol = signal.get('symbol', signal.get('pair', ''))
            price = signal.get('price', 0)
            size = signal.get('size', 0)

            if not symbol or not price or not size:
                return {
                    "valid": False,
                    "errors": ["Missing required signal fields: symbol, price, or size"]
                }

            # Validate against Kraken order requirements
            validation_result = self.order_validator.validate_order(symbol, size, price)

            return validation_result

        except Exception as e:
            logger.error(f"[SIGNAL_VALIDATION] Error validating signal for Kraken: {e}")
            return {"valid": False, "errors": [str(e)]}

    async def handle_kraken_error(self, error_message: str, symbol: str = None):
        """Handle Kraken-specific errors with appropriate responses."""
        try:
            self.performance_metrics["kraken_errors"] += 1

            # Find appropriate error handler
            handler = None
            for error_type, error_handler in self.kraken_error_handlers.items():
                if error_type in error_message:
                    handler = error_handler
                    break

            if handler:
                await handler(error_message, symbol)
            else:
                logger.error(f"[KRAKEN_ERROR] Unhandled error: {error_message}")

        except Exception as e:
            logger.error(f"[KRAKEN_ERROR] Error handling Kraken error: {e}")

    async def _handle_rate_limit_error(self, error_message: str, symbol: str = None):
        """Handle Kraken rate limit exceeded error."""
        logger.warning(f"[KRAKEN_RATE_LIMIT] {symbol}: Rate limit exceeded - pausing trading")
        if symbol:
            # Force rate counter to maximum to prevent immediate retry
            self.rate_limit_manager.rate_counters[symbol] = self.rate_limit_manager.params["threshold"]

    async def _handle_order_minimum_error(self, error_message: str, symbol: str = None):
        """Handle Kraken order minimum not met error."""
        logger.warning(f"[KRAKEN_ORDER_MIN] {symbol}: Order below minimum size")

    async def _handle_cost_minimum_error(self, error_message: str, symbol: str = None):
        """Handle Kraken cost minimum not met error."""
        logger.warning(f"[KRAKEN_COST_MIN] {symbol}: Order cost below minimum")

    async def _handle_insufficient_funds_error(self, error_message: str, symbol: str = None):
        """Handle Kraken insufficient funds error."""
        logger.warning(f"[KRAKEN_FUNDS] {symbol}: Insufficient funds for order")

    async def _handle_invalid_arguments_error(self, error_message: str, symbol: str = None):
        """Handle Kraken invalid arguments error."""
        logger.error(f"[KRAKEN_INVALID_ARGS] {symbol}: Invalid order arguments")

    def get_kraken_compliance_metrics(self) -> dict[str, Any]:
        """Get Kraken-specific compliance and performance metrics."""
        try:
            # Calculate quick profit statistics
            total_signals = self.performance_metrics.get("signals_generated", 0)
            executed_signals = self.performance_metrics.get("signals_executed", 0)
            blocked_signals = self.performance_metrics.get("signals_blocked_by_rate_limit", 0)
            failed_validation = self.performance_metrics.get("signals_failed_validation", 0)

            return {
                "strategy_type": "kraken_compliant_quick_profit_snowball",
                "kraken_compliance": {
                    "rate_limit_tier": self.rate_limit_manager.tier,
                    "rate_limit_threshold": self.rate_limit_manager.params["threshold"],
                    "signals_blocked_by_rate_limit": blocked_signals,
                    "signals_failed_validation": failed_validation,
                    "kraken_errors": self.performance_metrics.get("kraken_errors", 0),
                    "validation_success_rate": (
                        (total_signals - failed_validation) / total_signals * 100
                        if total_signals > 0 else 100
                    )
                },
                "trading_performance": {
                    "total_signals_generated": total_signals,
                    "signals_executed": executed_signals,
                    "execution_rate": (executed_signals / total_signals * 100) if total_signals > 0 else 0,
                    "target_profit_per_trade": "0.5%",
                    "stop_loss_per_trade": "0.8%",
                    "risk_reward_ratio": 0.625,  # 0.5% profit / 0.8% loss
                },
                "system_status": {
                    "active_strategies": len(self.active_strategies),
                    "last_signal_time": self.performance_metrics.get("last_signal_time"),
                    "kraken_api_compliance": "WebSocket v2",
                    "symbol_format": "BTC/USD style"
                },
                "philosophy": {
                    "snowball_effect": "Small frequent profits accumulate to significant returns",
                    "fee_advantage": "Fee-free trading enables micro-profit capture",
                    "kraken_optimization": "Compliant with all Kraken rate limits and order requirements"
                }
            }

        except Exception as e:
            logger.error(f"[STRATEGY_MANAGER] Error calculating Kraken compliance metrics: {e}")
            return {"error": str(e)}

    def get_active_strategies(self) -> list[str]:
        """Get list of active strategy symbols."""
        return self.active_strategies

    def has_strategies(self) -> bool:
        """Check if any strategies are active."""
        return len(self.strategies) > 0

    async def _create_buy_strategy(self, symbol: str, config: dict[str, Any]) -> Optional[BaseStrategy]:
        """
        Create a Kraken-compliant buy strategy for the given symbol.

        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            config: Configuration dictionary

        Returns:
            Initialized buy strategy or None if creation failed
        """
        try:
            # Create strategy parameters
            strategy_params = {
                'config': {
                    'fast_start_config': {
                        'profit_target': config.get('take_profit_pct', 0.5),  # 0.5% quick profits
                        'stop_loss': config.get('stop_loss_pct', 0.8),        # 0.8% tight stops
                        'min_confidence': config.get('fast_start_config', {}).get('min_confidence', 60.0)
                    }
                },
                'position_size_usd': config.get('position_size_usdt', 2.0),  # Use position_size_usdt from config
                'kraken_tier': getattr(self.rate_limit_manager, 'tier', 'starter'),
                'enable_aggressive_mode': True,  # For maximum trading opportunities
                'snowball_mode': True,           # For profit accumulation
                'bot_ref': self.bot             # Pass bot reference for balance manager access
            }

            # Initialize the strategy with correct parameters
            strategy_config = {
                'fast_start_config': {
                    'profit_target': 1.5,
                    'stop_loss': 2.0,
                    'min_confidence': 0.6
                },
                'position_size_usdt': config.get('position_size_usdt', 3.5),
                'symbol': symbol,
                'exchange': getattr(self.bot, 'exchange', None),
                'balance_manager': getattr(self.bot, 'balance_manager', None),
                'bot_ref': self.bot,
                'strategy_params': strategy_params,
                'rate_limiter': self.rate_limit_manager
            }

            buy_strategy = FastStartStrategy(strategy_config)

            # Provide historical data if available
            if self.historical_data_provided and symbol in self.price_history:
                if hasattr(buy_strategy, 'set_historical_data'):
                    buy_strategy.set_historical_data(self.price_history[symbol])
                    logger.info(f"[STRATEGY_CREATE] {symbol}: Provided {len(self.price_history[symbol])} historical candles")

            # Set strategy status
            buy_strategy.status = "Ready"

            # CRITICAL: Connect portfolio intelligence
            if hasattr(buy_strategy, 'connect_portfolio_intelligence') and self.bot:
                buy_strategy.connect_portfolio_intelligence(self.bot)
                logger.info(f"[STRATEGY_CREATE] {symbol}: Connected portfolio intelligence")

            logger.info(f"[STRATEGY_CREATE] {symbol}: FastStartStrategy created with {strategy_params['config']['fast_start_config']['profit_target']}% profit target")
            return buy_strategy

        except Exception as e:
            logger.error(f"[STRATEGY_CREATE] Error creating buy strategy for {symbol}: {e}")
            return None

    # # DISABLED: Using unified sell coordinator
    # async def _create_sell_engine(self, symbol: str, config: Dict[str, Any]) -> Optional['AutonomousSellEngine']:
    #     """
    #     Create a Kraken-compliant sell engine for the given symbol.
    #
    #     Args:
    #         symbol: Trading symbol (e.g., 'BTC/USDT')
    #         config: Configuration dictionary
    #
    #     Returns:
    #         Initialized sell engine or None if creation failed
    #     """
    #     # This method was deprecated in favor of the enhanced sell logic system
    #     # Keeping placeholder for potential future enhancements
    #     pass

    async def update_ohlc_data(self, symbol: str, ohlc_data: dict[str, Any]):
        """
        Update OHLC data for strategies and generate signals.

        Args:
            symbol: Trading symbol
            ohlc_data: OHLC candle data
        """
        try:
            self.last_ohlc_update[symbol] = time.time()

            # Update buy strategy if available
            if symbol in self.strategies:
                strategy = self.strategies[symbol]
                if hasattr(strategy, 'update_ohlc'):
                    await strategy.update_ohlc(ohlc_data)

                # CRITICAL FIX: Generate signal after OHLC update
                if hasattr(strategy, 'generate_signal'):
                    signal = await strategy.generate_signal()
                    if signal and signal.get('side'):
                        # Format and validate the signal
                        formatted_signal = self._format_signal_for_kraken(signal)
                        if formatted_signal:
                            # Add to signals list for execution
                            self._pending_signals.append(formatted_signal)
                            logger.info(f"[SIGNAL] {symbol}: Generated {signal.get('side')} signal with {signal.get('confidence', 0)*100:.1f}% confidence")
                    else:
                        logger.debug(f"[SIGNAL] {symbol}: No signal generated from strategy")

            # # Update sell engine if available  # DISABLED: Using unified sell coordinator
            # if symbol in self.sell_engines:
            #     sell_engine = self.sell_engines[symbol]
            #     if hasattr(sell_engine, 'update_price'):
            #         current_price = ohlc_data.get('close', 0)
            #         if current_price > 0:
            #             await sell_engine.update_price(current_price)

        except Exception as e:
            logger.error(f"[OHLC_UPDATE] Error updating OHLC data for {symbol}: {e}")

    async def cleanup(self):
        """Clean up all strategies and sell engines with Kraken compliance."""
        try:
            # # Stop all sell engines  # DISABLED: Using unified sell coordinator
            # for symbol, engine in self.sell_engines.items():
            #     await engine.stop_monitoring()
            #     logger.info(f"[CLEANUP] {symbol}: Stopped Kraken-compliant sell engine")

            # Clean up strategies
            for symbol, strategy in self.strategies.items():
                if hasattr(strategy, 'cleanup'):
                    strategy.cleanup()
                logger.info(f"[CLEANUP] {symbol}: Cleaned up Kraken-compliant strategy")

            # Clear references
            self.strategies.clear()
            # self.sell_engines.clear()  # DISABLED: Using unified sell coordinator
            self.active_strategies.clear()

            logger.info("[STRATEGY_MANAGER] Kraken-compliant cleanup completed")

        except Exception as e:
            logger.error(f"[STRATEGY_MANAGER] Error during Kraken-compliant cleanup: {e}")

    def _format_signal_for_kraken(self, signal: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Format signal for Kraken compliance with proper validation."""
        try:
            if not signal:
                return None

            # Handle both 'pair' and 'symbol' fields
            if 'symbol' in signal and 'pair' not in signal:
                signal['pair'] = signal['symbol']
            elif 'pair' in signal and 'symbol' not in signal:
                signal['symbol'] = signal['pair']
            elif 'pair' not in signal and 'symbol' not in signal:
                logger.warning(f"[SIGNAL_FORMAT] Missing symbol/pair in signal: {signal}")
                return None

            # Handle both 'type' and 'side' fields
            if 'type' in signal and 'side' not in signal:
                signal['side'] = signal['type']
            elif 'side' not in signal and 'type' not in signal:
                logger.warning(f"[SIGNAL_FORMAT] Missing side/type in signal: {signal}")
                return None

            # Check if we have a valid side after translation
            if not signal.get('side'):
                return None

            # Ensure required fields
            formatted = {
                'symbol': signal.get('symbol', signal.get('pair', '')),
                'pair': signal.get('pair', signal.get('symbol', '')),
                'side': signal.get('side', ''),
                'confidence': float(signal.get('confidence', 0.5)),
                'price': float(signal.get('price', 0)),
                'reason': signal.get('reason', 'Strategy signal'),
                'signal_type': signal.get('signal_type', 'strategy'),
                'timestamp': signal.get('timestamp', time.time()),
                'source': signal.get('source', 'strategy')
            }

            # Validate symbol format
            if '/' not in formatted['symbol']:
                logger.warning(f"[SIGNAL_FORMAT] Invalid symbol format: {formatted['symbol']}")
                return None

            # Validate side
            if formatted['side'] not in ['buy', 'sell']:
                logger.warning(f"[SIGNAL_FORMAT] Invalid side: {formatted['side']}")
                return None

            # Validate confidence
            if not 0 <= formatted['confidence'] <= 1:
                formatted['confidence'] = max(0, min(1, formatted['confidence']))

            # Log successful format
            logger.debug(f"[SIGNAL_ACCEPTED] Formatted signal: {formatted['symbol']} {formatted['side']} conf={formatted['confidence']:.2f}")

            return formatted

        except Exception as e:
            logger.error(f"[SIGNAL_FORMAT] Error formatting signal: {e}")
            return None

    async def process_ohlc_update(self, symbol: str, ohlc_data: dict[str, Any]):
        """
        Process incoming OHLC data and generate signals for Kraken trading.

        KRAKEN COMPLIANT: Handles WebSocket v2 data format and rate limits.
        """
        try:
            # Store OHLC update time
            self.last_ohlc_update[symbol] = time.time()

            # Update strategy with OHLC data
            if symbol in self.strategies:
                strategy = self.strategies[symbol]
                if hasattr(strategy, 'update_ohlc'):
                    await strategy.update_ohlc(ohlc_data)

                # CRITICAL FIX: Generate signal after OHLC update
                if hasattr(strategy, 'generate_signal'):
                    signal = await strategy.generate_signal()
                    if signal and signal.get('side'):
                        # Format and validate the signal
                        formatted_signal = self._format_signal_for_kraken(signal)
                        if formatted_signal:
                            # Add to signals list for execution
                            self._pending_signals.append(formatted_signal)
                            logger.info(f"[SIGNAL] {symbol}: Generated {signal.get('side')} signal with {signal.get('confidence', 0)*100:.1f}% confidence")
                    else:
                        logger.debug(f"[SIGNAL] {symbol}: No signal generated from strategy")

            # # Update sell engine if available  # DISABLED: Using unified sell coordinator
            # if symbol in self.sell_engines:
            #     sell_engine = self.sell_engines[symbol]
            #     if hasattr(sell_engine, 'update_price'):
            #         current_price = ohlc_data.get('close', 0)
            #         if current_price > 0:
            #             await sell_engine.update_price(current_price)

        except Exception as e:
            logger.error(f"[OHLC_UPDATE] Error updating OHLC data for {symbol}: {e}")

    async def execute_pending_signals(self) -> None:
        """
        Execute any pending signals through the trade executor.
        This bridges the gap between signal generation and execution.
        """
        if not self._pending_signals:
            return

        # Process signals in order of confidence
        sorted_signals = sorted(self._pending_signals,
                               key=lambda x: x.get('confidence', 0),
                               reverse=True)

        # Execute the best signal
        if sorted_signals and self.bot and hasattr(self.bot, 'trade_executor'):
            best_signal = sorted_signals[0]

            # Check rate limits
            if not self.rate_limit_manager.can_add_order(best_signal.get('symbol', '')):
                logger.warning(f"[STRATEGY] Rate limit prevents execution of {best_signal.get('symbol')}")
                return

            # Execute through bot's executor
            if hasattr(self.bot.trade_executor, 'execute_opportunity'):
                result = await self.bot.trade_executor.execute_opportunity(best_signal)
            else:
                # Fallback to execute_trade
                result = await self.bot.trade_executor.execute_trade({
                    'symbol': best_signal.get('symbol'),
                    'side': best_signal.get('side', 'buy'),
                    'amount': self.bot.position_size_usd if hasattr(self.bot, 'position_size_usd') else 2.0,
                    'signal': best_signal
                })

            if result.get('success'):
                logger.info(f"[STRATEGY] [EMOJI] Signal executed: {best_signal.get('symbol')}")
                # Remove executed signal
                self._pending_signals.remove(best_signal)
            else:
                logger.error(f"[STRATEGY] [EMOJI] Signal execution failed: {result.get('error')}")

    def get_pending_signals(self) -> list[dict[str, Any]]:
        """Get and clear pending signals generated from OHLC updates."""
        signals = self._pending_signals.copy()
        self._pending_signals.clear()
        return signals

    async def check_all_strategies(self) -> list[dict[str, Any]]:
        """
        Check all strategies for trading signals.
        This method is called by the main bot loop.

        Returns:
            List of trading signals from all active strategies
        """
        all_signals = []

        try:
            # Check all buy strategies
            for symbol, strategy in self.strategies.items():
                if hasattr(strategy, 'generate_signal'):
                    signal = await strategy.generate_signal()
                    if signal and signal.get('side'):
                        # Format for Kraken compliance
                        formatted_signal = self._format_signal_for_kraken(signal)
                        if formatted_signal:
                            all_signals.append(formatted_signal)
                            logger.debug(f"[STRATEGY] {symbol}: Generated {signal.get('side')} signal")

            # Also return any pending signals from OHLC updates
            if self._pending_signals:
                all_signals.extend(self._pending_signals)
                self._pending_signals.clear()

            return all_signals

        except Exception as e:
            logger.error(f"[STRATEGY] Error checking strategies: {e}")
            return []

    async def check_all_strategies_concurrent(self) -> list[dict[str, Any]]:
        """
        Check all strategies concurrently with individual timeouts.
        This provides better performance and partial result handling.

        Returns:
            List of trading signals from all active strategies
        """
        all_signals = []
        self._partial_results = []  # Store partial results for timeout recovery

        try:
            # Get portfolio state for context-aware signal generation
            portfolio_context = await self._get_portfolio_context()

            # Create tasks for all strategy checks
            tasks = []
            for symbol, strategy in self.strategies.items():
                if hasattr(strategy, 'generate_signal'):
                    # Add portfolio context to strategy if supported
                    if hasattr(strategy, 'set_portfolio_context'):
                        strategy.set_portfolio_context(portfolio_context)

                    # Wrap each strategy check in its own timeout
                    task = asyncio.create_task(
                        self._check_strategy_with_timeout(symbol, strategy, portfolio_context)
                    )
                    tasks.append((symbol, task))

            # Wait for all tasks with gather (doesn't fail on individual errors)
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

            # Process results
            for (symbol, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    if isinstance(result, asyncio.TimeoutError):
                        logger.warning(f"[STRATEGY] {symbol}: Strategy check timed out")
                    else:
                        logger.error(f"[STRATEGY] {symbol}: Strategy error: {result}")
                elif result:
                    # Format for Kraken compliance
                    logger.info(f"[STRATEGY] {symbol}: Raw signal: {result}")
                    formatted_signal = self._format_signal_for_kraken(result)
                    if formatted_signal:
                        all_signals.append(formatted_signal)
                        self._partial_results.append(formatted_signal)  # Store for partial recovery
                        logger.info(f"[SIGNAL_COLLECTED] {symbol}: {formatted_signal.get('side')} signal with confidence={formatted_signal.get('confidence', 0):.2f}")
                    else:
                        logger.warning(f"[SIGNAL_REJECTED] {symbol}: Failed to format signal")

            # Also return any pending signals from OHLC updates
            if self._pending_signals:
                all_signals.extend(self._pending_signals)
                self._pending_signals.clear()

            return all_signals

        except Exception as e:
            logger.error(f"[STRATEGY_MANAGER] Error in concurrent strategy check: {e}")
            return self._partial_results  # Return partial results on error

    async def _get_portfolio_context(self) -> dict[str, Any]:
        """
        Get current portfolio context for strategy awareness.

        Returns:
            Dict with portfolio state information
        """
        try:
            context = {
                'total_positions': 0,
                'positions_by_symbol': {},
                'total_value_usdt': 0.0,
                'available_usdt': 0.0,
                'deployment_pct': 0.0,
                'is_tier_1': self.bot.config.get('kraken_api_tier', 'starter') == 'starter' if self.bot else True
            }

            # Get portfolio positions
            if self.bot and hasattr(self.bot, 'portfolio_manager'):
                positions = await self.bot.portfolio_manager.get_open_positions()
                context['total_positions'] = len(positions) if positions else 0

                for pos in positions:
                    symbol = pos.get('symbol')
                    context['positions_by_symbol'][symbol] = {
                        'amount': pos.get('amount', 0),
                        'entry_price': pos.get('entry_price', 0),
                        'current_value': pos.get('current_value', 0),
                        'unrealized_pnl_pct': pos.get('unrealized_pnl_pct', 0)
                    }
                    context['total_value_usdt'] += pos.get('current_value', 0)

            # Get available balance
            if self.bot and hasattr(self.bot, 'balance_manager'):
                balance = await self.bot.balance_manager.get_balance_for_asset('USDT')
                # Convert to float to avoid Decimal/float mixing
                context['available_usdt'] = float(balance) if balance is not None else 0.0

                # Calculate deployment percentage
                total_capital = context['total_value_usdt'] + context['available_usdt']
                if total_capital > 0:
                    context['deployment_pct'] = (context['total_value_usdt'] / total_capital) * 100

            return context

        except Exception as e:
            logger.error(f"[STRATEGY] Error getting portfolio context: {e}")
            return {
                'total_positions': 0,
                'positions_by_symbol': {},
                'total_value_usdt': 0.0,
                'available_usdt': 0.0,
                'deployment_pct': 0.0,
                'is_tier_1': True
            }

    async def _check_strategy_with_timeout(self, symbol: str, strategy: Any, portfolio_context: dict[str, Any] = None, timeout: float = 3.0) -> Optional[dict[str, Any]]:
        """
        Check a single strategy with timeout protection and portfolio awareness.

        Args:
            symbol: Trading symbol
            strategy: Strategy instance
            portfolio_context: Current portfolio state for context-aware signals
            timeout: Maximum time allowed for strategy check

        Returns:
            Trading signal or None
        """
        try:
            # Record start time for performance tracking
            start_time = time.time()

            # Run strategy with timeout
            signal = await asyncio.wait_for(
                strategy.generate_signal(),
                timeout=timeout
            )

            # Track performance
            elapsed = time.time() - start_time
            if elapsed > timeout * 0.8:  # Strategy took >80% of timeout
                if not hasattr(self, '_slow_strategies'):
                    self._slow_strategies = set()
                self._slow_strategies.add(symbol)
                logger.warning(f"[STRATEGY] {symbol}: Slow strategy detected ({elapsed:.2f}s)")

            # Enhance signal with portfolio context if available
            if signal and portfolio_context:
                signal = self._enhance_signal_with_context(signal, portfolio_context)

            return signal

        except asyncio.TimeoutError:
            logger.warning(f"[STRATEGY] {symbol}: Strategy timed out after {timeout}s")
            raise
        except Exception as e:
            logger.error(f"[STRATEGY] {symbol}: Error in strategy check: {e}")
            raise

    def get_partial_results(self) -> list[dict[str, Any]]:
        """Get partial results from incomplete strategy checks"""
        return self._partial_results.copy() if hasattr(self, '_partial_results') else []

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get strategy performance metrics including slow strategy detection"""
        metrics = self.performance_metrics.copy()

        # Add slow strategy information
        if hasattr(self, '_slow_strategies'):
            metrics['slow_strategies'] = list(self._slow_strategies)

        return metrics

    def _enhance_signal_with_context(self, signal: dict[str, Any], portfolio_context: dict[str, Any]) -> dict[str, Any]:
        """
        Enhance trading signal with portfolio context for better decision making.

        Args:
            signal: Original trading signal
            portfolio_context: Current portfolio state

        Returns:
            Enhanced signal with portfolio awareness
        """
        try:
            enhanced_signal = signal.copy()
            symbol = signal.get('symbol', '')

            # Add portfolio context to metadata
            if 'metadata' not in enhanced_signal:
                enhanced_signal['metadata'] = {}

            enhanced_signal['metadata']['portfolio_context'] = {
                'total_positions': portfolio_context['total_positions'],
                'deployment_pct': portfolio_context['deployment_pct'],
                'available_usdt': portfolio_context['available_usdt'],
                'is_tier_1': portfolio_context['is_tier_1']
            }

            # Adjust confidence based on portfolio state
            original_confidence = signal.get('confidence', 0.5)
            adjusted_confidence = original_confidence

            # Boost confidence for sells if we have a position with profit
            if signal.get('side') == 'sell' and symbol in portfolio_context['positions_by_symbol']:
                position = portfolio_context['positions_by_symbol'][symbol]
                if position['unrealized_pnl_pct'] > 0.1:  # Position in profit
                    adjusted_confidence = min(1.0, original_confidence * 1.2)
                    enhanced_signal['metadata']['confidence_boost'] = 'position_in_profit'

            # Boost confidence for buys if we're under-deployed
            elif signal.get('side') == 'buy' and portfolio_context['deployment_pct'] < 50:
                adjusted_confidence = min(1.0, original_confidence * 1.15)
                enhanced_signal['metadata']['confidence_boost'] = 'under_deployed'

            # For tier-1, prioritize signals that maintain deployment
            if portfolio_context['is_tier_1']:
                if signal.get('side') == 'buy' and portfolio_context['available_usdt'] >= 5.0:
                    adjusted_confidence = min(1.0, original_confidence * 1.1)
                    enhanced_signal['metadata']['tier_1_priority'] = True

            enhanced_signal['confidence'] = adjusted_confidence

            # Log context enhancement
            if adjusted_confidence != original_confidence:
                logger.debug(f"[STRATEGY] {symbol}: Confidence adjusted from {original_confidence:.2f} to {adjusted_confidence:.2f} based on portfolio context")

            return enhanced_signal

        except Exception as e:
            logger.error(f"[STRATEGY] Error enhancing signal with context: {e}")
            return signal  # Return original signal on error

    async def notify_existing_positions(self, positions: list[dict[str, Any]]) -> None:
        """
        Notify strategy manager about existing positions detected at startup.
        Creates autonomous sell engines for each position to enable profit taking.

        Args:
            positions: List of position dictionaries from portfolio scanner
        """
        try:
            logger.info(f"[STRATEGY] Processing {len(positions)} existing positions")

            for position in positions:
                symbol = position.get('symbol', '')
                if not symbol or '/' not in symbol:
                    continue

                # # Create sell engine for this position if not exists  # DISABLED: Using unified sell coordinator
                # if symbol not in self.sell_engines:
                #     logger.info(f"[STRATEGY] Creating sell engine for existing position: {symbol}")
                #
                #     # Use position data to configure sell engine
                #     entry_price = position.get('entry_price', 0)
                #     amount = position.get('amount', 0)
                #
                #     if entry_price > 0 and amount > 0:
                #         # Create sell engine with tighter profit targets for existing positions
                #         sell_engine = await self._create_sell_engine(symbol, {
                #             'take_profit_pct': 0.3,  # 0.3% for quick profits on existing positions
                #             'stop_loss_pct': 0.8,
                #             'trailing_stop_pct': 0.2,
                #             'check_interval': 3
                #         })
                #
                #         if sell_engine:
                #             self.sell_engines[symbol] = sell_engine
                #
                #             # Notify sell engine about the position
                #             if hasattr(sell_engine, 'on_position_update'):
                #                 await sell_engine.on_position_update(
                #                     symbol=symbol,
                #                     position={
                #                         'entry_price': entry_price,
                #                         'amount': amount,
                #                         'timestamp': position.get('timestamp', time.time())
                #                     }
                #                 )
                #
                #             logger.info(
                #                 f"[STRATEGY] Sell engine created for {symbol}: "
                #                 f"{amount:.8f} @ ${entry_price:.6f}"
                #             )

                # Also ensure we have a buy strategy for this symbol
                if symbol not in self.strategies:
                    logger.info(f"[STRATEGY] Creating buy strategy for {symbol}")
                    # Create config dictionary for FastStartStrategy
                    strategy_config = {
                        'fast_start_config': {
                            'profit_target': 1.5,
                            'stop_loss': 2.0,
                            'min_confidence': 0.6
                        },
                        'position_size_usdt': getattr(self.bot, 'config', {}).get('position_size_usdt', 3.5),
                        'symbol': symbol,
                        'exchange': getattr(self.bot, 'exchange', None),
                        'balance_manager': getattr(self.bot, 'balance_manager', None),
                        'bot_ref': self.bot
                    }

                    strategy = FastStartStrategy(strategy_config)
                    self.strategies[symbol] = strategy

        except Exception as e:
            logger.error(f"[STRATEGY] Error processing existing positions: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def process_ohlc_update(self, symbol: str, ohlc_data: dict[str, Any]):
        """
        Process OHLC update for a symbol.
        Alias for update_ohlc_data to match bot expectations.
        """
        await self.update_ohlc_data(symbol, ohlc_data)


# For backward compatibility - some code might import StrategyOrchestrator
StrategyOrchestrator = FunctionalStrategyManager

__all__ = ['FunctionalStrategyManager', 'StrategyOrchestrator']
