"""
Data Analysis Assistant - Market data analysis helper
"""

import asyncio
import logging
import time
from typing import Any

import numpy as np
import pandas as pd


class DataAnalysisAssistant:
    """Assistant for market data analysis operations"""

    def __init__(self, manager_or_config):
        # Handle both manager object and config dict
        if hasattr(manager_or_config, 'config'):
            self.manager = manager_or_config
            self.config = manager_or_config.config
        else:
            self.manager = None
            self.config = manager_or_config
        self.logger = logging.getLogger(__name__)

    def analyze_price_trend(self, price_data: list[float], window: int = 10) -> dict[str, Any]:
        """Analyze price trend from price data"""
        try:
            if len(price_data) < window:
                return {'trend': 'insufficient_data', 'strength': 0.0}

            # Convert to numpy array for analysis
            prices = np.array(price_data)

            # Calculate moving averages
            short_ma = np.mean(prices[-window//2:])
            long_ma = np.mean(prices[-window:])

            # Determine trend
            if short_ma > long_ma:
                trend = 'bullish'
                strength = min((short_ma - long_ma) / long_ma, 1.0)
            elif short_ma < long_ma:
                trend = 'bearish'
                strength = min((long_ma - short_ma) / long_ma, 1.0)
            else:
                trend = 'neutral'
                strength = 0.0

            return {
                'trend': trend,
                'strength': float(strength),
                'short_ma': float(short_ma),
                'long_ma': float(long_ma)
            }

        except Exception as e:
            self.logger.error(f"Price trend analysis error: {e}")
            return {'trend': 'error', 'strength': 0.0}

    def calculate_volatility(self, price_data: list[float], window: int = 20) -> float:
        """Calculate price volatility"""
        try:
            if len(price_data) < window:
                return 0.0

            prices = np.array(price_data[-window:])
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns)

            return float(volatility)

        except Exception as e:
            self.logger.error(f"Volatility calculation error: {e}")
            return 0.0

    def detect_support_resistance(self, price_data: list[float], window: int = 10) -> dict[str, float]:
        """Detect support and resistance levels"""
        try:
            if len(price_data) < window * 2:
                return {'support': 0.0, 'resistance': 0.0}

            prices = np.array(price_data)

            # Simple support/resistance detection
            support = float(np.min(prices[-window:]))
            resistance = float(np.max(prices[-window:]))

            return {
                'support': support,
                'resistance': resistance
            }

        except Exception as e:
            self.logger.error(f"Support/resistance detection error: {e}")
            return {'support': 0.0, 'resistance': 0.0}

    def calculate_rsi(self, price_data: list[float], window: int = 14) -> float:
        """Calculate Relative Strength Index"""
        try:
            if len(price_data) < window + 1:
                return 50.0  # Neutral RSI

            prices = np.array(price_data)
            deltas = np.diff(prices)

            gains = deltas.copy()
            losses = deltas.copy()

            gains[gains < 0] = 0
            losses[losses > 0] = 0
            losses = np.abs(losses)

            # Calculate average gains and losses
            avg_gain = np.mean(gains[-window:])
            avg_loss = np.mean(losses[-window:])

            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            return float(rsi)

        except Exception as e:
            self.logger.error(f"RSI calculation error: {e}")
            return 50.0  # Neutral RSI

    async def collect_market_data(self) -> dict[str, Any]:
        """Collect current market data for analysis"""
        try:
            # Return basic market data structure
            market_data = {
                'timestamp': pd.Timestamp.now(),
                'symbols': [],
                'prices': {},
                'volumes': {},
                'status': 'collected'
            }

            # If we have a manager with exchange access, collect real data
            if self.manager and hasattr(self.manager, 'exchange'):
                try:
                    # Get ticker data for monitored symbols
                    if hasattr(self.manager, 'active_symbols'):
                        for symbol in self.manager.active_symbols[:5]:  # Limit to prevent rate limits
                            try:
                                ticker = await self.manager.exchange.fetch_ticker(symbol)
                                if ticker:
                                    market_data['symbols'].append(symbol)
                                    market_data['prices'][symbol] = ticker.get('last', 0)
                                    market_data['volumes'][symbol] = ticker.get('baseVolume', 0)
                            except Exception as ticker_error:
                                self.logger.warning(f"Failed to fetch ticker for {symbol}: {ticker_error}")
                                continue
                except Exception as exchange_error:
                    self.logger.warning(f"Exchange data collection failed: {exchange_error}")

            self.logger.info(f"Market data collected for {len(market_data['symbols'])} symbols")
            return market_data

        except Exception as e:
            self.logger.error(f"Market data collection error: {e}")
            return {
                'timestamp': pd.Timestamp.now(),
                'symbols': [],
                'prices': {},
                'volumes': {},
                'status': 'error',
                'error': str(e)
            }

    async def initialize(self):
        """Initialize the data analysis assistant"""
        try:
            self.logger.info("[DATA_ASSISTANT] Initializing...")

            # Initialize data sources
            self.data_cache = {}
            self.last_update = 0
            self.is_connected = False

            # Connect to data sources if manager has them
            if self.manager and hasattr(self.manager, 'bot'):
                if hasattr(self.manager.bot, 'websocket_manager'):
                    self.websocket_manager = self.manager.bot.websocket_manager
                    self.is_connected = True
                    self.logger.info("[DATA_ASSISTANT] Connected to WebSocket data source")

                if hasattr(self.manager.bot, 'exchange'):
                    self.exchange = self.manager.bot.exchange
                    self.logger.info("[DATA_ASSISTANT] Connected to exchange")

            self.logger.info("[DATA_ASSISTANT] Initialization complete")

        except Exception as e:
            self.logger.error(f"[DATA_ASSISTANT] Initialization error: {e}")

    async def stop(self):
        """Stop the data analysis assistant"""
        try:
            self.logger.info("[DATA_ASSISTANT] Stopping...")

            # Clear any cached data
            if hasattr(self, 'data_cache'):
                self.data_cache.clear()

            self.is_connected = False
            self.logger.info("[DATA_ASSISTANT] Stopped successfully")

        except Exception as e:
            self.logger.error(f"[DATA_ASSISTANT] Stop error: {e}")

    async def health_check(self) -> dict[str, Any]:
        """Check health of the data analysis assistant"""
        try:
            # Check data freshness
            data_fresh = (time.time() - self.last_update) < 60 if hasattr(self, 'last_update') else False

            # Check connections
            has_websocket = hasattr(self, 'websocket_manager') and self.websocket_manager is not None
            has_exchange = hasattr(self, 'exchange') and self.exchange is not None

            healthy = (has_websocket or has_exchange) and getattr(self, 'is_connected', False)

            return {
                'healthy': healthy,
                'data_fresh': data_fresh,
                'websocket_connected': has_websocket,
                'exchange_connected': has_exchange,
                'last_update': getattr(self, 'last_update', 0),
                'timestamp': time.time()
            }

        except Exception as e:
            self.logger.error(f"[DATA_ASSISTANT] Health check error: {e}")
            return {'healthy': False, 'error': str(e)}

    async def reconnect(self):
        """Reconnect data sources"""
        try:
            self.logger.info("[DATA_ASSISTANT] Reconnecting data sources...")

            # Re-initialize connections
            await self.stop()
            await asyncio.sleep(1)
            await self.initialize()

            self.logger.info("[DATA_ASSISTANT] Reconnection complete")

        except Exception as e:
            self.logger.error(f"[DATA_ASSISTANT] Reconnect error: {e}")

    async def analyze_market_conditions(self) -> dict[str, Any]:
        """Analyze overall market conditions"""
        try:
            self.logger.debug("[DATA_ASSISTANT] Analyzing market conditions...")

            # Initialize market condition counters
            conditions = {
                'trending_up': 0,
                'trending_down': 0,
                'neutral': 0,
                'high_volume': 0,
                'low_volume': 0,
                'total_symbols': 0,
                'bullish_strength': 0.0,
                'bearish_strength': 0.0,
                'average_volatility': 0.0
            }

            # Get current market data
            market_data = await self.collect_market_data()

            if market_data and market_data['symbols']:
                conditions['total_symbols'] = len(market_data['symbols'])

                for symbol in market_data['symbols']:
                    try:
                        # Get historical data for trend analysis
                        if hasattr(self, 'websocket_manager') and self.websocket_manager:
                            # Get recent price data from WebSocket
                            ticker = self.websocket_manager.get_ticker(symbol)
                            if ticker and ticker.get('last', 0) > 0:
                                # Simple trend check based on bid/ask spread
                                bid = ticker.get('bid', 0)
                                ask = ticker.get('ask', 0)
                                last = ticker.get('last', 0)

                                if last > (bid + ask) / 2:
                                    conditions['trending_up'] += 1
                                    conditions['bullish_strength'] += 0.1
                                elif last < (bid + ask) / 2:
                                    conditions['trending_down'] += 1
                                    conditions['bearish_strength'] += 0.1
                                else:
                                    conditions['neutral'] += 1

                                # Volume analysis
                                volume = ticker.get('volume', 0)
                                if volume > 1000:  # Arbitrary threshold
                                    conditions['high_volume'] += 1
                                else:
                                    conditions['low_volume'] += 1

                    except Exception as symbol_error:
                        self.logger.warning(f"[DATA_ASSISTANT] Error analyzing {symbol}: {symbol_error}")
                        continue

                # Calculate averages
                if conditions['total_symbols'] > 0:
                    conditions['bullish_strength'] /= conditions['total_symbols']
                    conditions['bearish_strength'] /= conditions['total_symbols']

            self.logger.debug(f"[DATA_ASSISTANT] Market analysis: {conditions['trending_up']} up, {conditions['trending_down']} down")
            return conditions

        except Exception as e:
            self.logger.error(f"[DATA_ASSISTANT] Market conditions analysis error: {e}")
            return {
                'trending_up': 0,
                'trending_down': 0,
                'neutral': 0,
                'high_volume': 0,
                'low_volume': 0,
                'total_symbols': 0,
                'bullish_strength': 0.0,
                'bearish_strength': 0.0,
                'average_volatility': 0.0,
                'error': str(e)
            }
