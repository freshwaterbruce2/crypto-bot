"""
Enhanced Asset Configuration Manager
Dynamic asset discovery, correlation tracking, and intelligent tier management
"""

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import aiohttp
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AssetMetrics:
    """Comprehensive asset metrics for dynamic configuration"""
    symbol: str
    market_cap_rank: int
    volume_24h: float
    price_change_24h: float
    volatility_30d: float
    sharpe_ratio_30d: float
    max_drawdown_30d: float
    correlation_to_btc: float
    liquidity_score: float
    quality_score: float
    tier: str
    sector: str
    last_updated: datetime


@dataclass
class AssetConfiguration:
    """Enhanced asset configuration with dynamic parameters"""
    symbol: str
    enabled: bool
    tier: str
    sector: str

    # Position sizing
    position_size_multiplier: float
    max_position_size: float
    min_order_size: float

    # Risk parameters
    volatility_adjustment: float
    correlation_penalty: float
    quality_bonus: float

    # Strategy weights (dynamic based on market conditions)
    strategy_weights: dict[str, float]

    # Trading constraints
    max_daily_trades: int
    cooldown_period_minutes: int

    # Performance tracking
    sharpe_ratio: float
    win_rate: float
    avg_profit: float
    max_drawdown: float

    # Dynamic flags
    trending: bool
    oversold: bool
    overbought: bool
    high_volume: bool

    last_updated: datetime


class EnhancedAssetConfigManager:
    """Enhanced asset configuration manager with dynamic optimization"""

    def __init__(self, config_dir: str = "config/assets", enable_dynamic_discovery: bool = True):
        """Initialize enhanced asset config manager"""
        self.config_dir = Path(config_dir)
        self.enable_dynamic_discovery = enable_dynamic_discovery

        # Asset storage
        self.asset_configs: dict[str, AssetConfiguration] = {}
        self.asset_metrics: dict[str, AssetMetrics] = {}
        self.price_history: dict[str, list[float]] = defaultdict(list)
        self.correlation_matrix: dict[str, dict[str, float]] = {}

        # Dynamic discovery parameters
        self.min_market_cap_rank = 100  # Top 100 cryptocurrencies
        self.min_volume_24h = 1000000  # $1M minimum daily volume
        self.min_liquidity_score = 0.3  # Minimum liquidity threshold
        self.discovery_interval_hours = 6  # Discover new assets every 6 hours

        # Tier classification thresholds
        self.tier_thresholds = {
            'tier1': {'market_cap_rank': 10, 'volume_24h': 100000000, 'quality_score': 0.8},
            'tier2': {'market_cap_rank': 50, 'volume_24h': 10000000, 'quality_score': 0.6},
            'tier3': {'market_cap_rank': 100, 'volume_24h': 1000000, 'quality_score': 0.4}
        }

        # Sector classification patterns
        self.sector_keywords = {
            'defi': ['defi', 'dex', 'swap', 'yield', 'farm', 'compound', 'aave', 'uniswap'],
            'smart_contracts': ['ethereum', 'smart', 'contract', 'dapp', 'platform'],
            'layer1': ['blockchain', 'consensus', 'proof', 'mining', 'validator'],
            'layer2': ['scaling', 'rollup', 'sidechain', 'polygon', 'arbitrum'],
            'oracle': ['oracle', 'chainlink', 'price', 'feed', 'data'],
            'metaverse': ['metaverse', 'virtual', 'gaming', 'nft', 'land'],
            'meme': ['meme', 'dog', 'shiba', 'doge', 'community'],
            'ai': ['artificial', 'intelligence', 'ai', 'machine', 'learning'],
            'storage': ['storage', 'file', 'data', 'decentralized'],
            'privacy': ['privacy', 'anonymous', 'zero', 'knowledge', 'private']
        }

        # Cache for external data
        self.market_data_cache = {}
        self.cache_expiry = timedelta(hours=1)
        self.last_discovery = None

        logger.info("[ENHANCED_ASSET_CONFIG] Enhanced asset config manager initialized")

    async def initialize(self) -> bool:
        """Initialize the asset configuration manager"""
        try:
            # Create directories
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Load existing configurations
            await self._load_existing_configs()

            # Perform initial asset discovery if enabled
            if self.enable_dynamic_discovery:
                await self.discover_new_assets()

            # Calculate initial correlation matrix
            await self._update_correlation_matrix()

            logger.info(f"[ENHANCED_ASSET_CONFIG] Initialized with {len(self.asset_configs)} assets")
            return True

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Initialization error: {e}")
            return False

    async def discover_new_assets(self) -> list[str]:
        """Discover new tradeable assets based on market criteria"""
        try:
            if (self.last_discovery and
                datetime.now() - self.last_discovery < timedelta(hours=self.discovery_interval_hours)):
                return []

            logger.info("[ENHANCED_ASSET_CONFIG] Starting asset discovery...")

            # Fetch market data from multiple sources
            market_data = await self._fetch_market_data()

            new_assets = []
            for asset_data in market_data:
                symbol = asset_data.get('symbol', '').upper()

                # Skip if already configured
                if symbol in self.asset_configs:
                    continue

                # Apply discovery criteria
                if self._meets_discovery_criteria(asset_data):
                    # Create asset metrics
                    metrics = await self._create_asset_metrics(asset_data)

                    # Create asset configuration
                    config = await self._create_dynamic_asset_config(metrics)

                    # Store new asset
                    self.asset_metrics[symbol] = metrics
                    self.asset_configs[symbol] = config
                    new_assets.append(symbol)

                    logger.info(f"[ENHANCED_ASSET_CONFIG] Discovered new asset: {symbol} ({metrics.tier})")

            if new_assets:
                await self._save_all_configs()
                await self._update_correlation_matrix()

            self.last_discovery = datetime.now()

            logger.info(f"[ENHANCED_ASSET_CONFIG] Discovery complete. Found {len(new_assets)} new assets")
            return new_assets

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Asset discovery error: {e}")
            return []

    async def _fetch_market_data(self) -> list[dict[str, Any]]:
        """Fetch market data from external APIs"""
        try:
            # Check cache first
            if (self.market_data_cache.get('timestamp') and
                datetime.now() - self.market_data_cache['timestamp'] < self.cache_expiry):
                return self.market_data_cache['data']

            # Fetch from CoinGecko API (free tier)
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 100,
                'page': 1,
                'sparkline': False,
                'price_change_percentage': '24h,7d,30d'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Transform to our format
                        market_data = []
                        for coin in data:
                            market_data.append({
                                'symbol': coin.get('symbol', '').upper(),
                                'name': coin.get('name', ''),
                                'market_cap_rank': coin.get('market_cap_rank', 999),
                                'market_cap': coin.get('market_cap', 0),
                                'volume_24h': coin.get('total_volume', 0),
                                'price': coin.get('current_price', 0),
                                'price_change_24h': coin.get('price_change_percentage_24h', 0),
                                'price_change_7d': coin.get('price_change_percentage_7d_in_currency', 0),
                                'price_change_30d': coin.get('price_change_percentage_30d_in_currency', 0),
                                'circulating_supply': coin.get('circulating_supply', 0)
                            })

                        # Update cache
                        self.market_data_cache = {
                            'data': market_data,
                            'timestamp': datetime.now()
                        }

                        return market_data
                    else:
                        logger.warning(f"[ENHANCED_ASSET_CONFIG] API request failed: {response.status}")
                        return []

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error fetching market data: {e}")
            return []

    def _meets_discovery_criteria(self, asset_data: dict[str, Any]) -> bool:
        """Check if asset meets discovery criteria"""
        try:
            market_cap_rank = asset_data.get('market_cap_rank', 999)
            volume_24h = asset_data.get('volume_24h', 0)
            market_cap = asset_data.get('market_cap', 0)

            # Basic criteria
            if market_cap_rank > self.min_market_cap_rank:
                return False

            if volume_24h < self.min_volume_24h:
                return False

            if market_cap < 10000000:  # Minimum $10M market cap
                return False

            # Additional quality filters
            price_change_24h = abs(asset_data.get('price_change_24h', 0))
            if price_change_24h > 50:  # Exclude extremely volatile assets
                return False

            return True

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error checking discovery criteria: {e}")
            return False

    async def _create_asset_metrics(self, asset_data: dict[str, Any]) -> AssetMetrics:
        """Create asset metrics from market data"""
        try:
            symbol = asset_data['symbol']

            # Calculate quality score based on multiple factors
            market_cap_score = min(1.0, (101 - asset_data.get('market_cap_rank', 100)) / 100)
            volume_score = min(1.0, asset_data.get('volume_24h', 0) / 100000000)  # Normalize by $100M

            # Volatility estimation (simplified)
            price_changes = [
                asset_data.get('price_change_24h', 0),
                asset_data.get('price_change_7d', 0) / 7,  # Daily average
                asset_data.get('price_change_30d', 0) / 30  # Daily average
            ]
            volatility_30d = np.std([abs(change) for change in price_changes if change is not None])

            # Quality score combination
            quality_score = (market_cap_score * 0.4 + volume_score * 0.3 +
                           max(0, 1 - volatility_30d / 10) * 0.3)  # Penalize high volatility

            # Determine tier
            tier = self._determine_asset_tier(asset_data, quality_score)

            # Determine sector
            sector = self._determine_asset_sector(asset_data)

            # Liquidity score (simplified)
            liquidity_score = min(1.0, volume_score * 2)

            return AssetMetrics(
                symbol=symbol,
                market_cap_rank=asset_data.get('market_cap_rank', 999),
                volume_24h=asset_data.get('volume_24h', 0),
                price_change_24h=asset_data.get('price_change_24h', 0),
                volatility_30d=volatility_30d,
                sharpe_ratio_30d=0.0,  # Would need historical data
                max_drawdown_30d=0.0,  # Would need historical data
                correlation_to_btc=0.5,  # Default moderate correlation
                liquidity_score=liquidity_score,
                quality_score=quality_score,
                tier=tier,
                sector=sector,
                last_updated=datetime.now()
            )

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error creating asset metrics: {e}")
            return AssetMetrics(
                symbol=asset_data.get('symbol', 'UNKNOWN'),
                market_cap_rank=999, volume_24h=0, price_change_24h=0,
                volatility_30d=0.1, sharpe_ratio_30d=0, max_drawdown_30d=0,
                correlation_to_btc=0.5, liquidity_score=0.3, quality_score=0.3,
                tier='tier3', sector='other', last_updated=datetime.now()
            )

    def _determine_asset_tier(self, asset_data: dict[str, Any], quality_score: float) -> str:
        """Determine asset tier based on metrics"""
        market_cap_rank = asset_data.get('market_cap_rank', 999)
        volume_24h = asset_data.get('volume_24h', 0)

        # Check tier 1 criteria
        tier1 = self.tier_thresholds['tier1']
        if (market_cap_rank <= tier1['market_cap_rank'] and
            volume_24h >= tier1['volume_24h'] and
            quality_score >= tier1['quality_score']):
            return 'tier1'

        # Check tier 2 criteria
        tier2 = self.tier_thresholds['tier2']
        if (market_cap_rank <= tier2['market_cap_rank'] and
            volume_24h >= tier2['volume_24h'] and
            quality_score >= tier2['quality_score']):
            return 'tier2'

        return 'tier3'

    def _determine_asset_sector(self, asset_data: dict[str, Any]) -> str:
        """Determine asset sector based on name and description"""
        name = asset_data.get('name', '').lower()
        symbol = asset_data.get('symbol', '').lower()

        # Check for sector keywords
        for sector, keywords in self.sector_keywords.items():
            for keyword in keywords:
                if keyword in name or keyword in symbol:
                    return sector

        # Default classifications for known assets
        if symbol in ['btc', 'bitcoin']:
            return 'store_of_value'
        elif symbol in ['eth', 'ethereum']:
            return 'smart_contracts'
        elif 'defi' in name or 'swap' in name:
            return 'defi'
        elif 'chain' in name or 'network' in name:
            return 'layer1'

        return 'other'

    async def _create_dynamic_asset_config(self, metrics: AssetMetrics) -> AssetConfiguration:
        """Create dynamic asset configuration based on metrics"""
        try:
            # Base configuration based on tier
            if metrics.tier == 'tier1':
                base_config = {
                    'position_size_multiplier': 1.2,
                    'max_position_size': 0.20,
                    'min_order_size': 10.0,
                    'volatility_adjustment': 0.8,
                    'max_daily_trades': 5,
                    'cooldown_period_minutes': 30
                }
            elif metrics.tier == 'tier2':
                base_config = {
                    'position_size_multiplier': 1.0,
                    'max_position_size': 0.15,
                    'min_order_size': 5.0,
                    'volatility_adjustment': 1.0,
                    'max_daily_trades': 3,
                    'cooldown_period_minutes': 45
                }
            else:  # tier3
                base_config = {
                    'position_size_multiplier': 0.8,
                    'max_position_size': 0.10,
                    'min_order_size': 3.0,
                    'volatility_adjustment': 1.2,
                    'max_daily_trades': 2,
                    'cooldown_period_minutes': 60
                }

            # Dynamic strategy weights based on asset characteristics
            strategy_weights = self._calculate_dynamic_strategy_weights(metrics)

            # Risk adjustments
            correlation_penalty = max(0, metrics.correlation_to_btc - 0.5) * 0.5
            quality_bonus = metrics.quality_score * 0.3

            # Market condition flags (simplified)
            trending = abs(metrics.price_change_24h) > 5
            oversold = metrics.price_change_24h < -10
            overbought = metrics.price_change_24h > 15
            high_volume = metrics.volume_24h > 50000000  # $50M

            return AssetConfiguration(
                symbol=metrics.symbol,
                enabled=True,
                tier=metrics.tier,
                sector=metrics.sector,
                position_size_multiplier=base_config['position_size_multiplier'],
                max_position_size=base_config['max_position_size'],
                min_order_size=base_config['min_order_size'],
                volatility_adjustment=base_config['volatility_adjustment'],
                correlation_penalty=correlation_penalty,
                quality_bonus=quality_bonus,
                strategy_weights=strategy_weights,
                max_daily_trades=base_config['max_daily_trades'],
                cooldown_period_minutes=base_config['cooldown_period_minutes'],
                sharpe_ratio=metrics.sharpe_ratio_30d,
                win_rate=0.5,  # Default
                avg_profit=0.0,  # Default
                max_drawdown=metrics.max_drawdown_30d,
                trending=trending,
                oversold=oversold,
                overbought=overbought,
                high_volume=high_volume,
                last_updated=datetime.now()
            )

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error creating dynamic config: {e}")
            # Return safe default config
            return AssetConfiguration(
                symbol=metrics.symbol, enabled=True, tier='tier3', sector='other',
                position_size_multiplier=0.8, max_position_size=0.10, min_order_size=3.0,
                volatility_adjustment=1.0, correlation_penalty=0.0, quality_bonus=0.0,
                strategy_weights={'momentum': 0.25, 'mean_reversion': 0.25, 'quality': 0.25, 'diversification': 0.25},
                max_daily_trades=2, cooldown_period_minutes=60,
                sharpe_ratio=0.0, win_rate=0.5, avg_profit=0.0, max_drawdown=0.0,
                trending=False, oversold=False, overbought=False, high_volume=False,
                last_updated=datetime.now()
            )

    def _calculate_dynamic_strategy_weights(self, metrics: AssetMetrics) -> dict[str, float]:
        """Calculate dynamic strategy weights based on asset characteristics"""
        try:
            # Base weights
            weights = {
                'momentum': 0.25,
                'mean_reversion': 0.25,
                'quality': 0.25,
                'diversification': 0.25
            }

            # Adjust based on volatility
            if metrics.volatility_30d > 0.1:  # High volatility
                weights['mean_reversion'] += 0.1
                weights['momentum'] -= 0.1
            elif metrics.volatility_30d < 0.03:  # Low volatility
                weights['momentum'] += 0.1
                weights['mean_reversion'] -= 0.1

            # Adjust based on quality score
            if metrics.quality_score > 0.8:  # High quality
                weights['quality'] += 0.1
                weights['diversification'] -= 0.1
            elif metrics.quality_score < 0.4:  # Low quality
                weights['diversification'] += 0.1
                weights['quality'] -= 0.1

            # Adjust based on sector
            if metrics.sector in ['meme', 'other']:
                weights['mean_reversion'] += 0.15
                weights['momentum'] -= 0.15
            elif metrics.sector in ['defi', 'smart_contracts']:
                weights['momentum'] += 0.1
                weights['mean_reversion'] -= 0.1

            # Normalize weights
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}

            return weights

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error calculating dynamic weights: {e}")
            return {'momentum': 0.25, 'mean_reversion': 0.25, 'quality': 0.25, 'diversification': 0.25}

    async def update_asset_performance(self, symbol: str, trade_result: dict[str, Any]) -> None:
        """Update asset configuration based on trading performance"""
        try:
            if symbol not in self.asset_configs:
                return

            config = self.asset_configs[symbol]

            # Update performance metrics
            profit_pct = trade_result.get('profit_pct', 0)
            was_winner = profit_pct > 0

            # Update win rate (EWMA)
            alpha = 0.1  # Learning rate
            config.win_rate = (1 - alpha) * config.win_rate + alpha * (1 if was_winner else 0)

            # Update average profit
            config.avg_profit = (1 - alpha) * config.avg_profit + alpha * profit_pct

            # Update Sharpe ratio approximation
            if hasattr(config, 'profit_history'):
                config.profit_history.append(profit_pct)
                if len(config.profit_history) > 30:
                    config.profit_history = config.profit_history[-30:]

                profits = np.array(config.profit_history)
                if np.std(profits) > 0:
                    config.sharpe_ratio = np.mean(profits) / np.std(profits)
            else:
                config.profit_history = [profit_pct]

            # Adjust strategy weights based on performance
            if was_winner:
                # Boost strategy that worked
                winning_strategy = trade_result.get('strategy', 'momentum')
                if winning_strategy in config.strategy_weights:
                    # Slight increase for winning strategy
                    config.strategy_weights[winning_strategy] *= 1.05
            else:
                # Reduce strategy that failed
                losing_strategy = trade_result.get('strategy', 'momentum')
                if losing_strategy in config.strategy_weights:
                    config.strategy_weights[losing_strategy] *= 0.95

            # Normalize strategy weights
            total_weight = sum(config.strategy_weights.values())
            if total_weight > 0:
                config.strategy_weights = {
                    k: v / total_weight for k, v in config.strategy_weights.items()
                }

            config.last_updated = datetime.now()

            # Save updated configuration
            await self._save_asset_config(symbol)

            logger.debug(f"[ENHANCED_ASSET_CONFIG] Updated performance for {symbol}: "
                        f"win_rate={config.win_rate:.2f}, avg_profit={config.avg_profit:.2%}")

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error updating asset performance: {e}")

    async def get_optimal_asset_allocation(self, available_capital: float,
                                         market_regime: str = 'neutral') -> dict[str, float]:
        """Get optimal asset allocation based on current configurations and market regime"""
        try:
            allocations = {}
            total_score = 0

            # Calculate allocation scores for each asset
            asset_scores = {}
            for symbol, config in self.asset_configs.items():
                if not config.enabled:
                    continue

                # Base score from quality and performance
                base_score = (
                    config.quality_bonus * 0.3 +
                    config.sharpe_ratio * 0.2 +
                    config.win_rate * 0.2 +
                    (1 - config.correlation_penalty) * 0.3
                )

                # Regime adjustments
                if market_regime == 'bull':
                    # Favor momentum and growth assets
                    regime_multiplier = 1 + config.strategy_weights.get('momentum', 0)
                elif market_regime == 'bear':
                    # Favor quality and defensive assets
                    tier_bonus = {'tier1': 1.3, 'tier2': 1.1, 'tier3': 0.8}
                    regime_multiplier = tier_bonus.get(config.tier, 1.0)
                elif market_regime == 'high_volatility':
                    # Favor low-volatility assets
                    regime_multiplier = 1 / (1 + config.volatility_adjustment)
                else:
                    regime_multiplier = 1.0

                # Market condition adjustments
                if config.oversold:
                    regime_multiplier *= 1.2  # Opportunity
                elif config.overbought:
                    regime_multiplier *= 0.8  # Caution

                final_score = base_score * regime_multiplier * config.position_size_multiplier
                asset_scores[symbol] = max(0, final_score)
                total_score += asset_scores[symbol]

            # Calculate allocations
            if total_score > 0:
                for symbol, score in asset_scores.items():
                    config = self.asset_configs[symbol]

                    # Base allocation from score
                    base_allocation = (score / total_score) * available_capital

                    # Apply position size constraints
                    max_allocation = available_capital * config.max_position_size
                    min_allocation = config.min_order_size

                    allocation = max(min_allocation, min(max_allocation, base_allocation))

                    if allocation >= min_allocation:
                        allocations[symbol] = allocation

            logger.info(f"[ENHANCED_ASSET_CONFIG] Optimal allocation for {len(allocations)} assets "
                       f"in {market_regime} regime")

            return allocations

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error calculating optimal allocation: {e}")
            return {}

    async def _update_correlation_matrix(self) -> None:
        """Update correlation matrix for all assets"""
        try:
            symbols = list(self.asset_configs.keys())

            for symbol1 in symbols:
                if symbol1 not in self.correlation_matrix:
                    self.correlation_matrix[symbol1] = {}

                for symbol2 in symbols:
                    if symbol1 == symbol2:
                        self.correlation_matrix[symbol1][symbol2] = 1.0
                    elif symbol2 not in self.correlation_matrix[symbol1]:
                        # Calculate correlation if we have price history
                        corr = await self._calculate_correlation(symbol1, symbol2)
                        self.correlation_matrix[symbol1][symbol2] = corr

                        # Ensure symmetry
                        if symbol2 not in self.correlation_matrix:
                            self.correlation_matrix[symbol2] = {}
                        self.correlation_matrix[symbol2][symbol1] = corr

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error updating correlation matrix: {e}")

    async def _calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate correlation between two assets"""
        try:
            # This would ideally use actual price history
            # For now, return estimated correlation based on sectors

            if symbol1 not in self.asset_configs or symbol2 not in self.asset_configs:
                return 0.5  # Default moderate correlation

            config1 = self.asset_configs[symbol1]
            config2 = self.asset_configs[symbol2]

            # Same sector = higher correlation
            if config1.sector == config2.sector:
                base_correlation = 0.7
            else:
                base_correlation = 0.3

            # Same tier = higher correlation
            if config1.tier == config2.tier:
                base_correlation += 0.1

            # Both trending = higher correlation
            if config1.trending and config2.trending:
                base_correlation += 0.1

            return min(0.95, max(0.05, base_correlation))

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error calculating correlation: {e}")
            return 0.5

    async def _load_existing_configs(self) -> None:
        """Load existing asset configurations"""
        try:
            config_files = list(self.config_dir.glob("*.json"))

            for config_file in config_files:
                if config_file.stem == 'correlation_matrix':
                    continue

                try:
                    with open(config_file) as f:
                        data = json.load(f)

                    # Convert to AssetConfiguration
                    config = AssetConfiguration(**data)
                    self.asset_configs[config.symbol] = config

                except Exception as e:
                    logger.error(f"[ENHANCED_ASSET_CONFIG] Error loading {config_file}: {e}")

            # Load correlation matrix if exists
            corr_file = self.config_dir / "correlation_matrix.json"
            if corr_file.exists():
                try:
                    with open(corr_file) as f:
                        self.correlation_matrix = json.load(f)
                except Exception as e:
                    logger.error(f"[ENHANCED_ASSET_CONFIG] Error loading correlation matrix: {e}")

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error loading existing configs: {e}")

    async def _save_asset_config(self, symbol: str) -> None:
        """Save individual asset configuration"""
        try:
            if symbol not in self.asset_configs:
                return

            config = self.asset_configs[symbol]
            config_file = self.config_dir / f"{symbol}.json"

            # Convert to dict for JSON serialization
            config_dict = asdict(config)
            config_dict['last_updated'] = config.last_updated.isoformat()

            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error saving config for {symbol}: {e}")

    async def _save_all_configs(self) -> None:
        """Save all configurations"""
        try:
            # Save individual configs
            for symbol in self.asset_configs:
                await self._save_asset_config(symbol)

            # Save correlation matrix
            corr_file = self.config_dir / "correlation_matrix.json"
            with open(corr_file, 'w') as f:
                json.dump(self.correlation_matrix, f, indent=2)

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error saving all configs: {e}")

    async def get_config(self, symbol: str) -> Optional[AssetConfiguration]:
        """Get configuration for specific asset"""
        return self.asset_configs.get(symbol)

    async def get_metrics(self, symbol: str) -> Optional[AssetMetrics]:
        """Get metrics for specific asset"""
        return self.asset_metrics.get(symbol)

    def get_enabled_assets(self) -> list[str]:
        """Get list of enabled assets"""
        return [symbol for symbol, config in self.asset_configs.items() if config.enabled]

    def get_assets_by_tier(self, tier: str) -> list[str]:
        """Get assets by tier"""
        return [symbol for symbol, config in self.asset_configs.items()
                if config.tier == tier and config.enabled]

    def get_assets_by_sector(self, sector: str) -> list[str]:
        """Get assets by sector"""
        return [symbol for symbol, config in self.asset_configs.items()
                if config.sector == sector and config.enabled]

    async def get_diversification_opportunities(self, current_holdings: list[str]) -> list[str]:
        """Get assets that would improve portfolio diversification"""
        try:
            opportunities = []

            for symbol, config in self.asset_configs.items():
                if not config.enabled or symbol in current_holdings:
                    continue

                # Check if asset would improve diversification
                avg_correlation = 0
                if symbol in self.correlation_matrix:
                    correlations = [
                        abs(self.correlation_matrix[symbol].get(holding, 0.5))
                        for holding in current_holdings
                        if holding in self.correlation_matrix[symbol]
                    ]
                    avg_correlation = np.mean(correlations) if correlations else 0.5

                # Lower correlation = better diversification
                if avg_correlation < 0.6:
                    opportunities.append(symbol)

            # Sort by quality score
            opportunities.sort(key=lambda x: self.asset_configs[x].quality_bonus, reverse=True)

            return opportunities[:10]  # Top 10 opportunities

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error finding diversification opportunities: {e}")
            return []

    def get_manager_stats(self) -> dict[str, Any]:
        """Get enhanced asset manager statistics"""
        try:
            tier_counts = defaultdict(int)
            sector_counts = defaultdict(int)
            enabled_count = 0

            for config in self.asset_configs.values():
                tier_counts[config.tier] += 1
                sector_counts[config.sector] += 1
                if config.enabled:
                    enabled_count += 1

            return {
                'total_assets': len(self.asset_configs),
                'enabled_assets': enabled_count,
                'tier_distribution': dict(tier_counts),
                'sector_distribution': dict(sector_counts),
                'discovery_enabled': self.enable_dynamic_discovery,
                'last_discovery': self.last_discovery.isoformat() if self.last_discovery else None,
                'correlation_matrix_size': len(self.correlation_matrix),
                'cache_status': 'active' if self.market_data_cache else 'empty'
            }

        except Exception as e:
            logger.error(f"[ENHANCED_ASSET_CONFIG] Error getting manager stats: {e}")
            return {}


# Global enhanced asset config manager instance
_global_enhanced_asset_manager = None


def get_enhanced_asset_manager() -> EnhancedAssetConfigManager:
    """Get global enhanced asset config manager instance"""
    global _global_enhanced_asset_manager
    if _global_enhanced_asset_manager is None:
        _global_enhanced_asset_manager = EnhancedAssetConfigManager()
    return _global_enhanced_asset_manager
