"""
Asset Config Loader
Loads and manages asset-specific configuration and trading parameters
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class AssetConfigLoader:
    """Loads and manages asset-specific configurations"""
    
    def __init__(self, config_dir: str = "config/assets"):
        """Initialize asset config loader"""
        self.config_dir = Path(config_dir)
        self.asset_configs = {}
        self.default_config = {}
        self.config_cache = {}
        self.last_update = {}
        
        # Default asset configuration template
        self.default_asset_config = {
            'enabled': True,
            'position_size_multiplier': 1.0,
            'profit_target_pct': 1.0,
            'stop_loss_pct': 0.8,
            'max_position_size': 5.0,
            'min_order_size': 2.0,
            'volatility_threshold': 2.0,
            'confidence_threshold': 0.6,
            'strategy_weights': {
                'fast_start': 0.25,
                'mean_reversion': 0.25,
                'rsi_macd': 0.25,
                'micro_scalper': 0.25
            },
            'risk_multiplier': 1.0,
            'trading_hours': {
                'enabled': False,
                'start_hour': 0,
                'end_hour': 24
            },
            'pair_specific': {
                'spread_threshold': 0.001,
                'volume_threshold': 100000,
                'price_precision': 8,
                'amount_precision': 8
            }
        }
        
        logger.info("[ASSET_CONFIG] Asset config loader initialized")
    
    async def load_configs(self) -> bool:
        """Load all asset configurations"""
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Load default configuration
            await self._load_default_config()
            
            # Load individual asset configurations
            config_files = list(self.config_dir.glob("*.json"))
            
            for config_file in config_files:
                try:
                    await self._load_asset_config(config_file)
                except Exception as e:
                    logger.error(f"[ASSET_CONFIG] Error loading {config_file}: {e}")
            
            logger.info(f"[ASSET_CONFIG] Loaded {len(self.asset_configs)} asset configurations")
            return True
            
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error loading configurations: {e}")
            return False
    
    async def get_asset_config(self, symbol: str) -> Dict[str, Any]:
        """Get configuration for specific asset"""
        try:
            # Check cache first
            if symbol in self.config_cache:
                return self.config_cache[symbol].copy()
            
            # Get asset from symbol (e.g., 'BTC' from 'BTC/USDT')
            asset = symbol.split('/')[0] if '/' in symbol else symbol
            
            # Get asset-specific config or use default
            if asset in self.asset_configs:
                config = self._merge_configs(self.default_asset_config, self.asset_configs[asset])
            else:
                config = self.default_asset_config.copy()
            
            # Add symbol-specific information
            config['symbol'] = symbol
            config['asset'] = asset
            
            # Cache the config
            self.config_cache[symbol] = config.copy()
            
            return config
            
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error getting config for {symbol}: {e}")
            return self.default_asset_config.copy()
    
    async def get_enabled_assets(self) -> List[str]:
        """Get list of enabled assets"""
        try:
            enabled = []
            
            for asset, config in self.asset_configs.items():
                if config.get('enabled', True):
                    enabled.append(asset)
            
            return enabled
            
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error getting enabled assets: {e}")
            return []
    
    async def update_asset_config(self, asset: str, config_updates: Dict[str, Any]) -> bool:
        """Update configuration for specific asset"""
        try:
            if asset not in self.asset_configs:
                self.asset_configs[asset] = self.default_asset_config.copy()
            
            # Update configuration
            self.asset_configs[asset].update(config_updates)
            
            # Clear cache
            self._clear_cache_for_asset(asset)
            
            # Save to file
            await self._save_asset_config(asset)
            
            logger.info(f"[ASSET_CONFIG] Updated configuration for {asset}")
            return True
            
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error updating config for {asset}: {e}")
            return False
    
    async def create_default_configs(self, symbols: List[str]) -> bool:
        """Create default configurations for list of symbols"""
        try:
            created_count = 0
            
            for symbol in symbols:
                asset = symbol.split('/')[0] if '/' in symbol else symbol
                
                if asset not in self.asset_configs:
                    # Create default config with symbol-specific adjustments
                    config = self.default_asset_config.copy()
                    
                    # Adjust config based on asset type
                    config = self._adjust_config_for_asset(asset, config)
                    
                    self.asset_configs[asset] = config
                    await self._save_asset_config(asset)
                    created_count += 1
            
            if created_count > 0:
                logger.info(f"[ASSET_CONFIG] Created {created_count} default configurations")
            
            return True
            
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error creating default configs: {e}")
            return False
    
    def get_strategy_weight(self, symbol: str, strategy_name: str) -> float:
        """Get strategy weight for specific symbol"""
        try:
            config = self.config_cache.get(symbol)
            if not config:
                # Load config synchronously for weight lookup
                asset = symbol.split('/')[0] if '/' in symbol else symbol
                config = self.asset_configs.get(asset, self.default_asset_config)
            
            weights = config.get('strategy_weights', {})
            return weights.get(strategy_name, 0.25)  # Default 25% weight
            
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error getting strategy weight for {symbol}: {e}")
            return 0.25
    
    def get_risk_multiplier(self, symbol: str) -> float:
        """Get risk multiplier for symbol"""
        try:
            config = self.config_cache.get(symbol)
            if not config:
                asset = symbol.split('/')[0] if '/' in symbol else symbol
                config = self.asset_configs.get(asset, self.default_asset_config)
            
            return config.get('risk_multiplier', 1.0)
            
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error getting risk multiplier for {symbol}: {e}")
            return 1.0
    
    async def _load_default_config(self):
        """Load default configuration"""
        try:
            default_file = self.config_dir / "default.json"
            
            if default_file.exists():
                with open(default_file, 'r') as f:
                    file_config = json.load(f)
                    self.default_config = file_config
                    # Merge with template
                    self.default_asset_config = self._merge_configs(
                        self.default_asset_config, file_config
                    )
            else:
                # Create default config file
                with open(default_file, 'w') as f:
                    json.dump(self.default_asset_config, f, indent=2)
                    
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error loading default config: {e}")
    
    async def _load_asset_config(self, config_file: Path):
        """Load individual asset configuration"""
        try:
            asset = config_file.stem  # Filename without extension
            
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.asset_configs[asset] = config
                self.last_update[asset] = config_file.stat().st_mtime
                
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error loading {config_file}: {e}")
    
    async def _save_asset_config(self, asset: str):
        """Save asset configuration to file"""
        try:
            config_file = self.config_dir / f"{asset}.json"
            
            with open(config_file, 'w') as f:
                json.dump(self.asset_configs[asset], f, indent=2)
                
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error saving config for {asset}: {e}")
    
    def _merge_configs(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries"""
        merged = base_config.copy()
        
        for key, value in override_config.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _adjust_config_for_asset(self, asset: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust configuration based on asset characteristics"""
        try:
            # Asset-specific adjustments
            if asset in ['BTC', 'ETH']:  # High-value assets
                config['position_size_multiplier'] = 0.8
                config['confidence_threshold'] = 0.7
                config['strategy_weights']['fast_start'] = 0.3
                config['strategy_weights']['mean_reversion'] = 0.4
                config['strategy_weights']['rsi_macd'] = 0.2
                config['strategy_weights']['micro_scalper'] = 0.1
            
            elif asset in ['DOGE', 'SHIB']:  # High-volatility meme coins
                config['position_size_multiplier'] = 1.2
                config['volatility_threshold'] = 5.0
                config['confidence_threshold'] = 0.55
                config['strategy_weights']['micro_scalper'] = 0.4
                config['strategy_weights']['fast_start'] = 0.3
                config['strategy_weights']['mean_reversion'] = 0.2
                config['strategy_weights']['rsi_macd'] = 0.1
            
            elif asset in ['ADA', 'DOT', 'ALGO']:  # Mid-tier alts
                config['position_size_multiplier'] = 1.0
                config['confidence_threshold'] = 0.6
                # Keep balanced strategy weights
            
            return config
            
        except Exception as e:
            logger.error(f"[ASSET_CONFIG] Error adjusting config for {asset}: {e}")
            return config
    
    def _clear_cache_for_asset(self, asset: str):
        """Clear cache entries for asset"""
        symbols_to_clear = []
        
        for symbol in self.config_cache:
            if symbol.startswith(asset + '/') or symbol == asset:
                symbols_to_clear.append(symbol)
        
        for symbol in symbols_to_clear:
            del self.config_cache[symbol]
    
    def get_loader_stats(self) -> Dict[str, Any]:
        """Get asset config loader statistics"""
        return {
            'total_configs': len(self.asset_configs),
            'cached_configs': len(self.config_cache),
            'config_directory': str(self.config_dir),
            'enabled_assets': len([a for a, c in self.asset_configs.items() if c.get('enabled', True)]),
            'last_updates': self.last_update
        }


# Global asset config loader instance
_global_asset_loader = None


def get_asset_config_loader() -> AssetConfigLoader:
    """Get global asset config loader instance"""
    global _global_asset_loader
    if _global_asset_loader is None:
        _global_asset_loader = AssetConfigLoader()
    return _global_asset_loader


async def load_asset_config(symbol: str) -> Dict[str, Any]:
    """Global function to load asset config"""
    loader = get_asset_config_loader()
    return await loader.get_asset_config(symbol)